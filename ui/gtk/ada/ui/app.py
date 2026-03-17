"""
Application - Main GTK application for Ada
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Application(Adw.Application):
    """
    Main GTK Application for Ada.

    Features:
    - Single instance application
    - Command-line handling
    - Background service integration
    """

    APPLICATION_ID = "org.nebula.Ada"

    def __init__(self, agent=None):
        super().__init__(
            application_id=self.APPLICATION_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )

        self.agent = agent
        self._main_window: Optional[Gtk.Window] = None
        self._settings: Optional[Gio.Settings] = None

        # Add command line options
        self.add_main_option(
            "query",
            ord("q"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            "Process a query and exit",
            "QUERY"
        )

        self.add_main_option(
            "daemon",
            ord("d"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Run as daemon (background service)",
            None
        )

        self.add_main_option(
            "version",
            ord("v"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Show version and exit",
            None
        )

    def do_startup(self):
        """Application startup"""
        Adw.Application.do_startup(self)

        # Load CSS
        self._load_css()

        # Setup actions
        self._setup_actions()

        # Initialize settings
        try:
            self._settings = Gio.Settings.new(self.APPLICATION_ID)
        except Exception:
            logger.debug("GSettings schema not found, using defaults")

        logger.info("Ada application started")

    def do_activate(self):
        """Application activation - show main window"""
        if not self._main_window:
            from .window import MainWindow
            self._main_window = MainWindow(self, self.agent)

        self._main_window.present()

    def do_command_line(self, command_line):
        """Handle command line arguments"""
        options = command_line.get_options_dict()

        # Version
        if options.contains("version"):
            print("Ada AI Assistant v0.1.0")
            return 0

        # Daemon mode
        if options.contains("daemon"):
            # Run in background
            self.hold()  # Keep running
            return 0

        # Query mode
        if options.contains("query"):
            query = options.lookup_value("query", None).get_string()
            # Process query without showing UI
            asyncio.create_task(self._process_query(query))
            return 0

        # Default: activate
        self.activate()
        return 0

    def _setup_actions(self):
        """Setup application actions"""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        # Preferences action
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        self.add_action(prefs_action)

        # Keyboard shortcuts
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.preferences", ["<Control>comma"])

    def _load_css(self):
        """Load custom CSS"""
        css_provider = Gtk.CssProvider()

        css = """
        .ada-title {
            font-size: 24px;
            font-weight: bold;
        }

        .ada-message {
            padding: 12px;
            border-radius: 12px;
            margin: 4px;
        }

        .ada-user-message {
            background: @accent_bg_color;
            color: @accent_fg_color;
        }

        .ada-assistant-message {
            background: @card_bg_color;
        }

        .ada-thinking {
            font-style: italic;
            color: @insensitive_fg_color;
        }
        """

        css_provider.load_from_data(css.encode())

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    async def _process_query(self, query: str):
        """Process a query without UI"""
        if self.agent:
            result = await self.agent.process(query)
            print(result.message)

    def _on_quit(self, action, param):
        """Quit application"""
        self.quit()

    def _on_about(self, action, param):
        """Show about dialog"""
        about = Adw.AboutWindow(
            transient_for=self._main_window,
            application_name="Ada",
            application_icon="ada",
            version="0.1.0",
            comments="AI Assistant for NebulaOS",
            website="https://github.com/nebula/ada",
            issue_url="https://github.com/nebula/ada/issues",
            developers=["Nebula Team"],
            copyright="© 2024 Nebula Team",
            license_type=Gtk.License.MIT_X11,
        )
        about.present()

    def _on_preferences(self, action, param):
        """Show preferences"""
        from .preferences import PreferencesWindow
        prefs = PreferencesWindow(self)
        prefs.present()


def main():
    """Main entry point for GTK application"""
    app = Application()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
