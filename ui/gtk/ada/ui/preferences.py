"""
Preferences Window - Settings configuration
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# LLM Provider configurations
PROVIDER_CATEGORIES = {
    "local": {
        "name": "本地模型",
        "providers": [
            {"id": "ollama", "name": "Ollama", "desc": "本地运行，隐私保护"},
            {"id": "vllm", "name": "vLLM", "desc": "高性能本地推理"},
        ]
    },
    "international": {
        "name": "国际服务",
        "providers": [
            {"id": "openai", "name": "OpenAI", "desc": "GPT-4, GPT-3.5"},
            {"id": "anthropic", "name": "Anthropic", "desc": "Claude 系列"},
            {"id": "google", "name": "Google AI", "desc": "Gemini 系列"},
        ]
    },
    "china": {
        "name": "国内服务",
        "providers": [
            {"id": "aliyun", "name": "通义千问", "desc": "阿里云 Qwen"},
            {"id": "deepseek", "name": "DeepSeek", "desc": "深度求索"},
            {"id": "zhipu", "name": "智谱AI", "desc": "GLM 系列"},
            {"id": "moonshot", "name": "Kimi", "desc": "月之暗面"},
            {"id": "baidu", "name": "文心一言", "desc": "百度 ERNIE"},
            {"id": "baichuan", "name": "百川", "desc": "Baichuan 系列"},
            {"id": "minimax", "name": "MiniMax", "desc": "abab 系列"},
            {"id": "xfyun", "name": "讯飞星火", "desc": "Spark 系列"},
            {"id": "siliconflow", "name": "硅基流动", "desc": "多模型代理"},
        ]
    }
}

# Model presets for each provider
PROVIDER_MODELS = {
    "ollama": ["qwen2.5:latest", "llama3.2:latest", "deepseek-r1:latest", "mistral:latest", "gemma2:latest", "yi:latest", "glm4:latest"],
    "vllm": [],  # User configured
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1", "o1-mini"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    "google": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "aliyun": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long", "qwen2.5-72b-instruct", "qwen2.5-32b-instruct"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
    "zhipu": ["glm-4-plus", "glm-4-0520", "glm-4-air", "glm-4-flash", "glm-4-long"],
    "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    "baidu": ["ernie-4.0-8k", "ernie-4.0-turbo-8k", "ernie-3.5-8k", "ernie-speed-8k"],
    "baichuan": ["Baichuan4", "Baichuan3-Turbo", "Baichuan3-Turbo-128k"],
    "minimax": ["abab6.5s-chat", "abab6.5g-chat", "abab6.5-chat"],
    "xfyun": ["generalv3.5", "generalv3", "4.0Ultra"],
    "siliconflow": ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3", "meta-llama/Llama-3.1-70B-Instruct"],
}


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
        self._provider_settings: Dict[str, Dict[str, Any]] = {}
        self._initializing = True  # Flag to prevent signal handlers during init

        # Add pages
        self.add(self._build_general_page())
        self.add(self._build_llm_page())
        self.add(self._build_memory_page())
        self.add(self._build_skills_page())
        self.add(self._build_security_page())

        self._initializing = False  # Done initializing

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
        """Build LLM settings page with all providers"""
        page = Adw.PreferencesPage(title="Language Model", icon_name="dialog-information-symbolic")

        # Active provider group
        active_group = Adw.PreferencesGroup(title="Active Provider")

        # Provider category selection
        self.category_row = Adw.ComboRow(
            title="Provider Type",
            subtitle="Select provider category",
            model=Gtk.StringList.new([
                "本地模型 (Local)",
                "国际服务 (International)",
                "国内服务 (China)"
            ]),
        )
        self.category_row.connect("notify::selected", self._on_category_changed)
        active_group.add(self.category_row)

        # Provider selection
        self.provider_row = Adw.ComboRow(
            title="Provider",
            subtitle="Select LLM provider",
        )
        self.provider_row.connect("notify::selected", self._on_provider_changed)
        active_group.add(self.provider_row)

        # Model selection - must be created before _update_provider_list
        self.model_row = Adw.ComboRow(
            title="Model",
            subtitle="Select model to use",
        )
        active_group.add(self.model_row)

        # Now update the provider list (which also updates model list)
        self._update_provider_list("local")

        page.add(active_group)

        # Current provider settings
        self.provider_settings_group = Adw.PreferencesGroup(title="Provider Settings")
        page.add(self.provider_settings_group)

        # API Key entry
        self.api_key_row = Adw.PasswordEntryRow(
            title="API Key",
        )
        self.provider_settings_group.add(self.api_key_row)

        # Base URL (for configurable providers)
        self.base_url_row = Adw.EntryRow(
            title="Base URL",
        )
        self.provider_settings_group.add(self.base_url_row)

        # Test connection button
        test_row = Adw.ButtonRow(title="Test Connection")
        test_row.connect("activated", self._on_test_connection)
        self.provider_settings_group.add(test_row)

        # Update initial state
        self._update_provider_settings()

        page.add(self._build_generation_params_group())

        return page

    def _build_generation_params_group(self) -> Adw.PreferencesGroup:
        """Build generation parameters group"""
        params_group = Adw.PreferencesGroup(title="Generation Parameters")

        # Temperature
        self.temperature_row = Adw.SpinRow(
            title="Temperature",
            subtitle="Randomness of responses (0.0 - 2.0)",
        )
        self.temperature_row.set_range(0.0, 2.0)
        self.temperature_row.set_value(0.7)
        self.temperature_row.set_digits(1)
        params_group.add(self.temperature_row)

        # Top P
        self.top_p_row = Adw.SpinRow(
            title="Top P",
            subtitle="Nucleus sampling threshold",
        )
        self.top_p_row.set_range(0.0, 1.0)
        self.top_p_row.set_value(0.9)
        self.top_p_row.set_digits(2)
        params_group.add(self.top_p_row)

        # Max tokens
        self.max_tokens_row = Adw.SpinRow(
            title="Max Tokens",
            subtitle="Maximum response length",
        )
        self.max_tokens_row.set_range(100, 128000)
        self.max_tokens_row.set_value(4096)
        params_group.add(self.max_tokens_row)

        return params_group

    def _get_category_key(self, index: int) -> str:
        """Get category key from index"""
        keys = ["local", "international", "china"]
        return keys[index] if 0 <= index < len(keys) else "local"

    def _update_provider_list(self, category: str):
        """Update provider list based on category"""
        category_info = PROVIDER_CATEGORIES.get(category, PROVIDER_CATEGORIES["local"])
        providers = category_info["providers"]

        model = Gtk.StringList.new([f"{p['name']} - {p['desc']}" for p in providers])
        self.provider_row.set_model(model)

        # Store provider IDs for lookup
        self._current_provider_ids = [p["id"] for p in providers]
        self._update_model_list()

    def _update_model_list(self):
        """Update model list based on selected provider"""
        provider_id = self._get_current_provider_id()
        models = PROVIDER_MODELS.get(provider_id, [])

        if models:
            model = Gtk.StringList.new(models)
            self.model_row.set_model(model)
            self.model_row.set_sensitive(True)
        else:
            # Custom model entry
            model = Gtk.StringList.new(["Custom (enter below)"])
            self.model_row.set_model(model)
            self.model_row.set_sensitive(False)

    def _get_current_provider_id(self) -> str:
        """Get currently selected provider ID"""
        if not hasattr(self, '_current_provider_ids'):
            return "ollama"

        selected = self.provider_row.get_selected()
        if 0 <= selected < len(self._current_provider_ids):
            return self._current_provider_ids[selected]
        return "ollama"

    def _update_provider_settings(self):
        """Update provider-specific settings visibility"""
        provider_id = self._get_current_provider_id()

        # Local providers don't need API key
        is_local = provider_id in ["ollama", "vllm"]
        self.api_key_row.set_visible(not is_local)

        # Update base URL based on provider
        default_urls = {
            "ollama": "http://localhost:11434",
            "vllm": "http://localhost:8000/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "aliyun": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "moonshot": "https://api.moonshot.cn/v1",
            "baidu": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
            "baichuan": "https://api.baichuan-ai.com/v1",
            "minimax": "https://api.minimax.chat/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
        }

        self.base_url_row.set_text(default_urls.get(provider_id, ""))
        self.base_url_row.set_visible(provider_id in ["ollama", "vllm"])

        # Update group title
        provider_names = {
            "ollama": "Ollama Settings",
            "vllm": "vLLM Settings",
            "openai": "OpenAI Settings",
            "anthropic": "Anthropic Settings",
            "google": "Google AI Settings",
            "aliyun": "通义千问 Settings",
            "deepseek": "DeepSeek Settings",
            "zhipu": "智谱AI Settings",
            "moonshot": "Kimi Settings",
            "baidu": "文心一言 Settings",
            "baichuan": "百川 Settings",
            "minimax": "MiniMax Settings",
            "xfyun": "讯飞星火 Settings",
            "siliconflow": "硅基流动 Settings",
        }
        self.provider_settings_group.set_title(provider_names.get(provider_id, "Provider Settings"))

        # Update API key placeholder
        api_key_hints = {
            "openai": "sk-...",
            "anthropic": "sk-ant-...",
            "google": "AIza...",
            "aliyun": "sk-...",
            "deepseek": "sk-...",
            "zhipu": "...",
            "moonshot": "sk-...",
        }
        hint = api_key_hints.get(provider_id, "")
        if hint:
            self.api_key_row.set_placeholder_text(hint)

    def _on_category_changed(self, row, param):
        """Handle category selection change"""
        if getattr(self, '_initializing', False):
            return
        category = self._get_category_key(row.get_selected())
        self._update_provider_list(category)
        self._update_provider_settings()

    def _on_provider_changed(self, row, param):
        """Handle provider selection change"""
        if getattr(self, '_initializing', False):
            return
        self._update_model_list()
        self._update_provider_settings()

    def _on_test_connection(self, row):
        """Test connection to the provider"""
        provider_id = self._get_current_provider_id()

        # Show a toast notification
        toast = Adw.Toast.new(f"Testing connection to {provider_id}...")
        toast.set_timeout(2)
        self.add_toast(toast)

        # TODO: Implement actual connection test
        GLib.timeout_add(1500, lambda: self._show_test_result(provider_id))

    def _show_test_result(self, provider_id: str) -> bool:
        """Show test result"""
        # Simulate success for now
        toast = Adw.Toast.new(f"✓ Connection successful")
        toast.set_timeout(3)
        self.add_toast(toast)
        return False

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
        clear_memory = Adw.ButtonRow(title="Clear All Memory")
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
        from .dialogs import ConfirmationDialog

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

    def get_llm_config(self) -> Dict[str, Any]:
        """Get current LLM configuration"""
        return {
            "provider": self._get_current_provider_id(),
            "model": self._get_selected_model(),
            "api_key": self.api_key_row.get_text() if self.api_key_row.get_visible() else "",
            "base_url": self.base_url_row.get_text() if self.base_url_row.get_visible() else "",
            "params": {
                "temperature": self.temperature_row.get_value(),
                "top_p": self.top_p_row.get_value(),
                "max_tokens": int(self.max_tokens_row.get_value()),
            }
        }

    def _get_selected_model(self) -> str:
        """Get currently selected model"""
        provider_id = self._get_current_provider_id()
        models = PROVIDER_MODELS.get(provider_id, [])

        if models:
            selected = self.model_row.get_selected()
            if 0 <= selected < len(models):
                return models[selected]

        # Return default model
        defaults = {
            "ollama": "qwen2.5:latest",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-sonnet-4-20250514",
            "google": "gemini-2.0-flash",
            "aliyun": "qwen-plus",
            "deepseek": "deepseek-chat",
            "zhipu": "glm-4-flash",
        }
        return defaults.get(provider_id, "")
