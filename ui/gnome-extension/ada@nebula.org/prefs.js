/**
 * Ada Extension Preferences
 */

import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';

import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';


export default class AdaPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const page = new Adw.PreferencesPage();

        // General settings
        const generalGroup = new Adw.PreferencesGroup({
            title: _('General'),
        });

        // Enable/disable
        const enabledRow = new Adw.SwitchRow({
            title: _('Enable Ada'),
            subtitle: _('Show Ada in the system tray'),
        });

        const settings = this.getSettings();
        settings.bind('enabled', enabledRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        generalGroup.add(enabledRow);

        // Keyboard shortcut
        const shortcutRow = new Adw.ActionRow({
            title: _('Keyboard Shortcut'),
            subtitle: _('Shortcut to toggle Ada'),
        });

        const shortcutLabel = new Gtk.ShortcutLabel({
            accelerator: settings.get_strv('toggle-ada')[0] || '<Super>a',
            halign: Gtk.Align.END,
            valign: Gtk.Align.CENTER,
        });

        shortcutRow.add_suffix(shortcutLabel);
        generalGroup.add(shortcutRow);

        page.add(generalGroup);

        // Behavior settings
        const behaviorGroup = new Adw.PreferencesGroup({
            title: _('Behavior'),
        });

        // Auto-start
        const autostartRow = new Adw.SwitchRow({
            title: _('Start Automatically'),
            subtitle: _('Start Ada when you log in'),
        });

        settings.bind('autostart', autostartRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        behaviorGroup.add(autostartRow);

        // Notifications
        const notificationsRow = new Adw.SwitchRow({
            title: _('Show Notifications'),
            subtitle: _('Display notifications for responses'),
        });

        settings.bind('show-notifications', notificationsRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        behaviorGroup.add(notificationsRow);

        page.add(behaviorGroup);

        // LLM settings
        const llmGroup = new Adw.PreferencesGroup({
            title: _('Language Model'),
        });

        // Backend selection
        const backendRow = new Adw.ComboRow({
            title: _('Backend'),
            subtitle: _('LLM backend to use'),
            model: Gtk.StringList.new(['Ollama (Local)', 'OpenAI', 'Anthropic']),
        });

        settings.bind('llm-backend', backendRow, 'selected', Gio.SettingsBindFlags.DEFAULT);
        llmGroup.add(backendRow);

        // Model
        const modelRow = new Adw.EntryRow({
            title: _('Model'),
            text: settings.get_string('llm-model') || 'llama3.2',
        });

        modelRow.connect('changed', (row) => {
            settings.set_string('llm-model', row.get_text());
        });

        llmGroup.add(modelRow);

        page.add(llmGroup);

        window.add(page);
    }
}
