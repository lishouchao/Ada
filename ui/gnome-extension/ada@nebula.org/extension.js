/**
 * Ada GNOME Shell Extension
 *
 * Provides quick access to Ada AI assistant from the system tray.
 */

import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';

import {Extension, gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';


const D_BUS_NAME = 'org.nebula.Ada';
const D_BUS_PATH = '/org/nebula/Ada';
const D_BUS_IFACE = 'org.nebula.Ada.Agent';


const AdaIndicator = GObject.registerClass(
class AdaIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Ada');

        this._extension = extension;
        this._dbusProxy = null;

        // Create icon
        const icon = new St.Icon({
            gicon: Gio.icon_new_for_string(
                GLib.build_filenamev([extension.path, 'icons', 'ada-symbolic.svg'])
            ),
            style_class: 'system-status-icon',
        });

        this.add_child(icon);

        // Build menu
        this._buildMenu();

        // Setup D-Bus connection
        this._setupDBus();
    }

    _buildMenu() {
        // Input section
        const inputBox = new St.BoxLayout({
            style_class: 'ada-input-box',
            vertical: false,
        });

        this._inputEntry = new St.Entry({
            hint_text: _('Ask Ada...'),
            can_focus: true,
            x_expand: true,
        });

        this._inputEntry.clutter_text.connect('activate', this._onSubmit.bind(this));

        inputBox.add(this._inputEntry);

        const inputMenuItem = new PopupMenu.PopupBaseMenuItem({
            reactive: false,
            can_focus: false,
        });
        inputMenuItem.add(inputBox);
        this.menu.addMenuItem(inputMenuItem);

        // Separator
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Quick actions
        const quickActions = [
            {label: _('Open Firefox'), action: 'open firefox'},
            {label: _('Organize Downloads'), action: 'organize downloads folder'},
            {label: _('System Info'), action: 'show system info'},
        ];

        for (const item of quickActions) {
            const menuItem = new PopupMenu.PopupMenuItem(item.label);
            menuItem.connect('activate', () => {
                this._sendQuery(item.action);
            });
            this.menu.addMenuItem(menuItem);
        }

        // Separator
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Open main window
        const openItem = new PopupMenu.PopupMenuItem(_('Open Ada'));
        openItem.connect('activate', () => {
            this._openMainWindow();
        });
        this.menu.addMenuItem(openItem);

        // Settings
        const settingsItem = new PopupMenu.PopupMenuItem(_('Settings'));
        settingsItem.connect('activate', () => {
            this._extension.openPreferences();
        });
        this.menu.addMenuItem(settingsItem);
    }

    _setupDBus() {
        try {
            const bus = Gio.DBus.session;

            // Create proxy
            this._dbusProxy = new Gio.DBusProxy({
                g_connection: bus,
                g_name: D_BUS_NAME,
                g_object_path: D_BUS_PATH,
                g_interface_name: D_BUS_IFACE,
            });

            // Try to connect
            this._dbusProxy.init_async(GLib.PRIORITY_DEFAULT, null, (proxy, result) => {
                try {
                    proxy.init_finish(result);
                    this._updateStatus(true);
                } catch (e) {
                    this._updateStatus(false);
                }
            });

        } catch (e) {
            this._updateStatus(false);
        }
    }

    _updateStatus(connected) {
        this._connected = connected;

        if (!connected) {
            this._inputEntry.set_hint_text(_('Ada not running'));
        } else {
            this._inputEntry.set_hint_text(_('Ask Ada...'));
        }
    }

    _onSubmit() {
        const text = this._inputEntry.get_text();
        if (!text)
            return;

        this._sendQuery(text);
        this._inputEntry.set_text('');
        this.menu.close();
    }

    _sendQuery(query) {
        if (!this._dbusProxy) {
            this._showNotification(_('Ada not available'), _('The Ada service is not running.'));
            return;
        }

        try {
            const result = this._dbusProxy.call_sync(
                'ProcessInput',
                new GLib.Variant('(s)', [query]),
                Gio.DBusCallFlags.NONE,
                5000,
                null
            );

            const [response] = result.deepUnpack();
            const data = JSON.parse(response);

            if (data.error) {
                this._showNotification(_('Ada Error'), data.error);
            } else {
                this._showNotification(_('Ada'), data.message || _('Done'));
            }

        } catch (e) {
            this._showNotification(_('Error'), e.message);
        }
    }

    _openMainWindow() {
        try {
            Gio.AppInfo.launch_default_for_uri('app://org.nebula.Ada', null);
        } catch (e) {
            // Try to spawn directly
            try {
                GLib.spawn_command_line_async('ada-gui');
            } catch (spawnError) {
                this._showNotification(_('Error'), _('Could not open Ada'));
            }
        }
    }

    _showNotification(title, message) {
        const source = new MessageTray.Source({
            title: 'Ada',
            icon_name: 'dialog-information-symbolic',
        });

        Main.messageTray.add(source);

        const notification = new MessageTray.Notification({
            source: source,
            title: title,
            body: message,
        });

        source.addNotification(notification);
    }

    destroy() {
        if (this._dbusProxy) {
            this._dbusProxy = null;
        }
        super.destroy();
    }
});


export default class AdaExtension extends Extension {
    enable() {
        this._indicator = new AdaIndicator(this);
        Main.panel.addToStatusArea('ada', this._indicator);

        // Register keybinding
        this._settings = this.getSettings();

        Main.wm.addKeybinding(
            'toggle-ada',
            this._settings,
            Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.ALL,
            this._onToggle.bind(this)
        );
    }

    disable() {
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }

        if (this._settings) {
            Main.wm.removeKeybinding('toggle-ada');
            this._settings = null;
        }
    }

    _onToggle() {
        if (this._indicator) {
            this._indicator.menu.toggle();
        }
    }
}
