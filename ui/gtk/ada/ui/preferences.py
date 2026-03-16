"""
Preferences Window - Settings configuration
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PreferencesWindow(Adw.PreferencesWindow):
    """
    Preferences window for Ada settings.

    Pages:
    - General: Basic settings
    - LLM: Language model configuration
    - Memory: Memory and storage
    - Skills: Skill management
    - Security: Security and privacy
    """

    def __init__(self, app):
        super().__init__(
            transient_for=app.get_active_window(),
            title="Preferences",
        )

        self.app = app

        # Add pages
        self.add(self._build_general_page())
        self.add(self._build_llm_page())
        self.add(self._build_memory_page())
        self.add(self._build_skills_page())
        self.add(self._build_security_page())

    def _build_general_page(self) -> Adw.PreferencesPage:
        """Build general settings page"""
        page = Adw.PreferencesPage(title="General", icon_name="preferences-system-symbolic")

        # Appearance group
        appearance_group = Adw.PreferencesGroup(title="Appearance")

        # Dark mode
        dark_mode = Adw.SwitchRow(
            title="Dark Mode",
            subtitle="Use dark color scheme",
        )
        dark_mode.connect("notify::active", self._on_dark_mode_changed)
        appearance_group.add(dark_mode)

        # Language
        language = Adw.ComboRow(
            title="Language",
            subtitle="Interface language",
            model=Gtk.StringList.new(["Auto", "English", "中文"]),
        )
        appearance_group.add(language)

        page.add(appearance_group)

        # Behavior group
        behavior_group = Adw.PreferencesGroup(title="Behavior")

        # Auto-start
        autostart = Adw.SwitchRow(
            title="Start Automatically",
            subtitle="Start Ada when you log in",
        )
        behavior_group.add(autostart)

        # Notifications
        notifications = Adw.SwitchRow(
            title="Show Notifications",
            subtitle="Display desktop notifications",
            active=True,
        )
        behavior_group.add(notifications)

        page.add(behavior_group)

        return page

    def _build_llm_page(self) -> Adw.PreferencesPage:
        """Build LLM settings page"""
        page = Adw.PreferencesPage(title="Language Model", icon_name="dialog-information-symbolic")

        # Backend group
        backend_group = Adw.PreferencesGroup(title="Backend")

        # Backend selection
        backend = Adw.ComboRow(
            title="Backend",
            subtitle="LLM backend to use",
            model=Gtk.StringList.new(["Ollama (Local)", "OpenAI", "Anthropic"]),
        )
        backend_group.add(backend)

        page.add(backend_group)

        # Ollama settings
        ollama_group = Adw.PreferencesGroup(title="Ollama Settings")

        # Base URL
        ollama_url = Adw.EntryRow(
            title="Server URL",
            text="http://localhost:11434",
        )
        ollama_group.add(ollama_url)

        # Model selection
        ollama_model = Adw.ComboRow(
            title="Model",
            subtitle="Model to use for inference",
            model=Gtk.StringList.new(["llama3.2", "llama3.1", "mistral", "qwen2.5"]),
        )
        ollama_group.add(ollama_model)

        page.add(ollama_group)

        # API settings
        api_group = Adw.PreferencesGroup(title="API Settings")

        # API Key
        api_key = Adw.PasswordEntryRow(
            title="API Key",
        )
        api_group.add(api_key)

        page.add(api_group)

        # Generation parameters
        params_group = Adw.PreferencesGroup(title="Generation Parameters")

        # Temperature
        temperature = Adw.SpinRow(
            title="Temperature",
            subtitle="Randomness of responses (0.0 - 2.0)",
        )
        temperature.set_range(0.0, 2.0)
        temperature.set_value(0.7)
        params_group.add(temperature)

        # Max tokens
        max_tokens = Adw.SpinRow(
            title="Max Tokens",
            subtitle="Maximum response length",
        )
        max_tokens.set_range(100, 8000)
        max_tokens.set_value(2000)
        params_group.add(max_tokens)

        page.add(params_group)

        return page

    def _build_memory_page(self) -> Adw.PreferencesPage:
        """Build memory settings page"""
        page = Adw.PreferencesPage(title="Memory", icon_name="folder-documents-symbolic")

        # Storage group
        storage_group = Adw.PreferencesGroup(title="Storage")

        # Memory enabled
        memory_enabled = Adw.SwitchRow(
            title="Enable Memory",
            subtitle="Remember conversations and context",
            active=True,
        )
        storage_group.add(memory_enabled)

        # Vector search
        vector_search = Adw.SwitchRow(
            title="Semantic Search",
            subtitle="Enable semantic (meaning-based) search",
            active=True,
        )
        storage_group.add(vector_search)

        page.add(storage_group)

        # Retention group
        retention_group = Adw.PreferencesGroup(title="Retention")

        # Conversation retention
        conv_retention = Adw.SpinRow(
            title="Conversation Retention (days)",
            subtitle="How long to keep conversation history",
        )
        conv_retention.set_range(1, 365)
        conv_retention.set_value(30)
        retention_group.add(conv_retention)

        # Clear memory button
        clear_memory = Adw.ButtonRow(
            title="Clear All Memory",
            subtitle="Delete all stored memories (cannot be undone)",
        )
        clear_memory.connect("activated", self._on_clear_memory)
        retention_group.add(clear_memory)

        page.add(retention_group)

        return page

    def _build_skills_page(self) -> Adw.PreferencesPage:
        """Build skills settings page"""
        page = Adw.PreferencesPage(title="Skills", icon_name="system-run-symbolic")

        # General group
        general_group = Adw.PreferencesGroup(title="General")

        # Auto-discover
        auto_discover = Adw.SwitchRow(
            title="Auto-discover Skills",
            subtitle="Automatically find and load skills",
            active=True,
        )
        general_group.add(auto_discover)

        # Default permission
        default_perm = Adw.ComboRow(
            title="Default Permission",
            subtitle="Default action for skill permissions",
            model=Gtk.StringList.new(["Ask", "Allow", "Deny"]),
        )
        general_group.add(default_perm)

        page.add(general_group)

        # Installed skills group
        skills_group = Adw.PreferencesGroup(title="Installed Skills")

        # Placeholder - would be populated from registry
        skill_row = Adw.ActionRow(
            title="File Organizer",
            subtitle="Organize files by type, date, or size",
        )
        skill_row.add_suffix(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
        skills_group.add(skill_row)

        skill_row2 = Adw.ActionRow(
            title="App Launcher",
            subtitle="Launch and manage applications",
        )
        skill_row2.add_suffix(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
        skills_group.add(skill_row2)

        page.add(skills_group)

        return page

    def _build_security_page(self) -> Adw.PreferencesPage:
        """Build security settings page"""
        page = Adw.PreferencesPage(title="Security", icon_name="security-high-symbolic")

        # Security mode group
        mode_group = Adw.PreferencesGroup(title="Security Mode")

        # Mode selection
        mode = Adw.ComboRow(
            title="Security Level",
            subtitle="Balance between security and convenience",
            model=Gtk.StringList.new(["Permissive", "Balanced", "Strict"]),
        )
        mode.set_selected(1)  # Balanced by default
        mode_group.add(mode)

        page.add(mode_group)

        # Confirmation group
        confirm_group = Adw.PreferencesGroup(title="Confirmations")

        # Destructive actions
        destructive = Adw.SwitchRow(
            title="Destructive Actions",
            subtitle="Require confirmation for destructive actions",
            active=True,
        )
        confirm_group.add(destructive)

        # System actions
        system = Adw.SwitchRow(
            title="System Actions",
            subtitle="Require confirmation for system operations",
            active=True,
        )
        confirm_group.add(system)

        # Network actions
        network = Adw.SwitchRow(
            title="Network Actions",
            subtitle="Require confirmation before network access",
            active=True,
        )
        confirm_group.add(network)

        page.add(confirm_group)

        # Sandbox group
        sandbox_group = Adw.PreferencesGroup(title="Sandboxing")

        # Enable sandbox
        sandbox_enabled = Adw.SwitchRow(
            title="Enable Sandbox",
            subtitle="Run external commands in isolated environment",
            active=True,
        )
        sandbox_group.add(sandbox_enabled)

        # Network in sandbox
        sandbox_network = Adw.SwitchRow(
            title="Allow Network",
            subtitle="Allow network access in sandbox",
            active=False,
        )
        sandbox_group.add(sandbox_network)

        page.add(sandbox_group)

        # Privacy group
        privacy_group = Adw.PreferencesGroup(title="Privacy")

        # Audit log
        audit_log = Adw.SwitchRow(
            title="Audit Logging",
            subtitle="Log all actions for security audit",
            active=True,
        )
        privacy_group.add(audit_log)

        page.add(privacy_group)

        return page

    def _on_dark_mode_changed(self, switch, param):
        """Handle dark mode toggle"""
        # Apply dark mode using Adw.StyleManager
        style_manager = Adw.StyleManager.get_default()
        if switch.get_active():
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

    def _on_clear_memory(self, row):
        """Handle clear memory button"""
        from ada.ui.dialogs import ConfirmationDialog

        def on_confirm():
            # Clear memory
            logger.info("Clearing all memory...")
            # TODO: Implement memory clearing

        dialog = ConfirmationDialog(
            parent=self,
            title="Clear All Memory",
            message="This will permanently delete all stored memories and conversation history. This action cannot be undone.",
            confirm_label="Clear",
            destructive=True,
            on_confirm=on_confirm,
        )
        dialog.present()
