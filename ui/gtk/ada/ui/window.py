"""
Main Window - Primary UI for Ada
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Pango, Gio

import asyncio
import logging
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Ada Agent
try:
    from ada.core.agent import AdaAgent
    from ada.core.context import AgentConfig
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False
    AdaAgent = None
    AgentConfig = None

logger = logging.getLogger(__name__)

# Ada System Prompt - 定义 Ada 的身份和能力
ADA_SYSTEM_PROMPT = """你是 Ada，一个友好的 AI 助手，运行在 NebulaOS 桌面系统上。

你的能力包括：
- 回答问题和提供建议
- 启动和管理应用程序
- 整理文件和文件夹
- 控制系统设置（音量、亮度等）
- 设置提醒和日程
- 搜索网络获取信息

请用简洁、友好的方式回应用户。如果需要执行操作，请确认用户意图。"""

# Config file path
CONFIG_FILE = Path.home() / ".config" / "ada" / "config.json"

# 提供商配置
PROVIDERS = [
    {
        "id": "ollama",
        "name": "Ollama",
        "prefix": "O",
        "need_key": False,
        "default_url": "http://localhost:11434/v1",
        "models": [
            {"id": "qwen2.5:latest", "name": "Qwen 2.5"},
            {"id": "llama3.2:latest", "name": "Llama 3.2"},
            {"id": "deepseek-r1:latest", "name": "DeepSeek R1"},
            {"id": "mistral:latest", "name": "Mistral"},
        ]
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "prefix": "",
        "need_key": True,
        "default_url": "https://api.deepseek.com/v1",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner"},
        ]
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "prefix": "",
        "need_key": True,
        "default_url": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
        ]
    },
    {
        "id": "aliyun",
        "name": "通义千问",
        "prefix": "",
        "need_key": True,
        "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": [
            {"id": "qwen-max", "name": "Qwen Max"},
            {"id": "qwen-plus", "name": "Qwen Plus"},
        ]
    },
    {
        "id": "zhipu",
        "name": "智谱AI",
        "prefix": "",
        "need_key": True,
        "default_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            {"id": "glm-4-plus", "name": "GLM-4 Plus"},
            {"id": "glm-4-flash", "name": "GLM-4 Flash"},
        ]
    },
    {
        "id": "moonshot",
        "name": "Kimi",
        "prefix": "",
        "need_key": True,
        "default_url": "https://api.moonshot.cn/v1",
        "models": [
            {"id": "moonshot-v1-8k", "name": "Moonshot V1 8K"},
        ]
    },
]

# 生成扁平化的 ALL_MODELS
def _build_all_models():
    result = []
    for provider in PROVIDERS:
        prefix = provider["prefix"]
        for model in provider["models"]:
            model_id = f"{provider['id']}:{model['id']}"
            name = f"{prefix}: {model['name']}" if prefix else model["name"]
            result.append({
                "id": model_id,
                "name": name,
                "provider": provider["id"],
                "model": model["id"],
                "url": provider["default_url"]
            })
    return result

ALL_MODELS = _build_all_models()

def load_config() -> Dict[str, Any]:
    """Load full configuration from file"""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    return {}

def get_model_by_id(model_id: str) -> Optional[Dict]:
    """Get model info by ID"""
    for model in ALL_MODELS:
        if model["id"] == model_id:
            return model
    return None

def get_enabled_models(config: Dict) -> List[Dict]:
    """Get list of enabled models"""
    enabled_ids = config.get("enabled_models", [])
    # 如果没有启用任何模型，默认启用 ollama:qwen2.5:latest
    if not enabled_ids:
        enabled_ids = ["ollama:qwen2.5:latest"]
    return [m for m in ALL_MODELS if m["id"] in enabled_ids]


class Message:
    """A chat message"""

    def __init__(self, content: str, is_user: bool, timestamp: datetime = None):
        self.content = content
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()
        self.thinking: Optional[str] = None


class MessageRow(Gtk.ListBoxRow):
    """A row in the message list"""

    def __init__(self, message: Message):
        super().__init__()
        self.message = message
        self.set_activatable(True)
        self.set_selectable(True)
        self.add_css_class("ada-message-row")

        # Outer container for alignment
        outer_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            margin_start=8,
            margin_end=8,
            margin_top=2,
            margin_bottom=2,
        )

        # Message bubble container
        bubble_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )
        bubble_box.add_css_class("ada-message")

        # Message content
        label = Gtk.Label(
            label=message.content,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            xalign=0,
        )

        # Style based on sender
        if message.is_user:
            bubble_box.add_css_class("ada-user-message")
            outer_box.set_halign(Gtk.Align.END)
            outer_box.set_hexpand(True)
            label.set_xalign(1)
        else:
            bubble_box.add_css_class("ada-assistant-message")
            outer_box.set_halign(Gtk.Align.START)
            outer_box.set_hexpand(True)
            label.set_xalign(0)

        bubble_box.append(label)

        # Thinking indicator
        if message.thinking:
            thinking_label = Gtk.Label(
                label=message.thinking,
                wrap=True,
                xalign=0,
            )
            thinking_label.add_css_class("ada-thinking")
            bubble_box.append(thinking_label)

        outer_box.append(bubble_box)
        self.set_child(outer_box)


class MainWindow(Adw.ApplicationWindow):
    """
    Main application window for Ada.

    Features:
    - Chat interface (left panel)
    - Side panels for settings, browser, etc. (right panel)
    - Message history
    - Input field with voice option
    - Status indicator
    """

    def __init__(self, app, agent=None):
        super().__init__(application=app, title="Ada")

        self.agent = agent
        self._messages: List[Message] = []
        self._config = load_config()
        self._current_model_id = self._config.get("current_model", "ollama:qwen2.5:latest")

        # Initialize Ada Agent if not provided
        if self.agent is None and HAS_AGENT:
            self._init_agent()

        # Window setup
        self.set_default_size(400, 875)
        self.set_size_request(350, 600)

        # Build UI
        self._build_ui()

        # Load saved state
        self._load_state()

        # Update status label with current provider
        self._update_status()

    def _init_agent(self):
        """Initialize Ada Agent in background"""
        def init_async():
            try:
                from ada.core.context import LLMConfig
                provider, model, api_key = self._get_current_model_config()

                llm_config = LLMConfig(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                )
                config = AgentConfig(llm=llm_config)

                self.agent = AdaAgent(config)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.agent.initialize())
                self.agent._initialized = True  # Mark as initialized
                logger.info("Ada Agent initialized")
            except Exception as e:
                logger.error(f"Failed to initialize agent: {e}")
                self.agent = None

        thread = threading.Thread(target=init_async, daemon=True)
        thread.start()

    def _build_ui(self):
        """Build the user interface - 主窗口只包含聊天界面"""
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Ada", subtitle="AI Assistant"))

        # Settings button (LLM config) - 打开独立设置窗口
        self._settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        self._settings_btn.set_tooltip_text("设置")
        self._settings_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(self._settings_btn)

        # Menu button
        menu = Gio.Menu()
        menu.append("关于", "app.about")
        menu_button = Gtk.MenuButton(menu_model=menu)
        header.pack_end(menu_button)

        # Model selector button (left side of header)
        self._model_btn = Gtk.Button()
        self._model_btn.add_css_class("flat")
        self._model_btn.set_tooltip_text("点击切换模型")
        self._model_btn.connect("clicked", self._on_model_selector_clicked)

        # Button content: icon + label
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._model_icon = Gtk.Image(icon_name="user-available-symbolic")
        self._model_label = Gtk.Label(label="Ollama · qwen2.5")
        self._model_label.add_css_class("caption")
        btn_box.append(self._model_icon)
        btn_box.append(self._model_label)
        self._model_btn.set_child(btn_box)

        header.pack_start(self._model_btn)

        main_box.append(header)

        # Content area with chat
        content = Adw.Clamp(maximum_size=800)

        # Message list
        self._message_list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.MULTIPLE,
            valign=Gtk.Align.END,
        )
        self._message_list.add_css_class("ada-message-list")

        # Right-click context menu
        self._setup_context_menu()

        # Scroll view for messages
        scroll = Gtk.ScrolledWindow(
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        scroll.set_child(self._message_list)

        content.set_child(scroll)
        main_box.append(content)

        # Input area
        input_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=6,
            margin_bottom=6,
        )

        # Input entry
        self._input_entry = Gtk.Entry(
            placeholder_text="Ask Ada anything...",
            hexpand=True,
        )
        self._input_entry.connect("activate", self._on_send)
        self._input_entry.connect("changed", self._on_input_changed)

        input_box.append(self._input_entry)

        # Voice button
        self._voice_button = Gtk.Button(icon_name="audio-input-microphone-symbolic")
        self._voice_button.set_tooltip_text("Voice input")
        self._voice_button.connect("clicked", self._on_voice)
        input_box.append(self._voice_button)

        # Send button
        self._send_button = Gtk.Button(
            icon_name="go-next-symbolic",
            sensitive=False,
        )
        self._send_button.set_tooltip_text("Send")
        self._send_button.connect("clicked", self._on_send)
        input_box.append(self._send_button)

        main_box.append(input_box)

        self.set_content(main_box)

        # Initialize panel manager - 面板作为独立窗口
        self._setup_panels()

        # Setup context menu for message list
        self._setup_context_menu()

        # Welcome message
        self._add_message(Message(
            "你好！我是 Ada，你的 AI 助手。有什么可以帮助你的吗？",
            is_user=False
        ))

    def _setup_panels(self):
        """Setup side panels as independent windows"""
        from .panels import SidePanelManager, SettingsPanel
        from .panels.manager import init_panel_manager

        # 面板管理器管理独立窗口
        self._panel_manager = SidePanelManager(self)
        self._panel_manager.on("panel_changed", self._on_panel_changed)

        # Initialize global panel manager for agent-triggered requests
        init_panel_manager(self._panel_manager)

        # Create settings panel content
        self._settings_panel = SettingsPanel(on_close=self._hide_panel)

        # Register panel with title and width (3x main window width)
        self._panel_manager.register_panel(
            "settings",
            self._settings_panel,
            title="设置",
            width=1200
        )

    def _on_panel_changed(self, panel_name: Optional[str]):
        """Handle panel visibility change"""
        if panel_name:
            self._settings_btn.add_css_class("accent")
        else:
            self._settings_btn.remove_css_class("accent")

    def _hide_panel(self):
        """Hide current panel"""
        self._panel_manager.hide_panel()

    def _setup_context_menu(self):
        """Setup right-click context menu for message list"""
        # Create menu actions
        copy_action = Gio.SimpleAction.new("copy-selected", None)
        copy_action.connect("activate", self._on_copy_selected)
        self.add_action(copy_action)

        # Create menu model
        menu = Gio.Menu()
        menu.append("复制所选消息", "win.copy-selected")

        # Create popover menu
        self._context_menu = Gtk.PopoverMenu(menu_model=menu)
        self._context_menu.set_parent(self._message_list)
        self._context_menu.set_has_arrow(False)

        # Right-click gesture
        gesture = Gtk.GestureClick(button=3)  # Right click
        gesture.connect("pressed", self._on_right_click)
        self._message_list.add_controller(gesture)

    def _on_right_click(self, gesture, n_press, x, y):
        """Handle right-click on message list"""
        # Position the menu at click location
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = rect.height = 1
        self._context_menu.set_pointing_to(rect)
        self._context_menu.popup()

    def _on_copy_selected(self, action, param):
        """Copy selected messages to clipboard"""
        selected_rows = self._message_list.get_selected_rows()
        if not selected_rows:
            return

        lines = []
        for row in selected_rows:
            if hasattr(row, 'message'):
                role = "用户" if row.message.is_user else "Ada"
                lines.append(f"**{role}**: {row.message.content}")

        text = "\n\n".join(lines)
        self.get_clipboard().set(text)

    def _on_input_changed(self, entry):
        """Handle input text changes"""
        self._send_button.set_sensitive(bool(entry.get_text()))

    def _on_send(self, widget):
        """Send message"""
        text = self._input_entry.get_text().strip()
        if not text:
            return

        # Add user message
        self._add_message(Message(text, is_user=True))

        # Clear input
        self._input_entry.set_text("")
        self._send_button.set_sensitive(False)

        # Reload config in case it changed
        self._config = load_config()

        # Show loading state
        self._model_icon.set_from_icon_name("content-loading-symbolic")
        self._send_button.set_sensitive(False)

        # Process in background thread
        def process_in_thread():
            try:
                # Use AdaAgent for processing (with skill execution)
                if self.agent and self.agent._initialized:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(self.agent.process(text))
                    loop.close()

                    if result.success:
                        response = result.message
                    else:
                        response = f"执行失败: {result.error or '未知错误'}"
                else:
                    # Fallback to direct LLM call
                    response = self._call_llm_sync(text)

                GLib.idle_add(self._add_message, Message(response, is_user=False))
            except Exception as e:
                logger.error(f"Processing error: {e}")
                GLib.idle_add(self._add_message, Message(f"❌ 错误: {e}", is_user=False))
            finally:
                GLib.idle_add(self._model_icon.set_from_icon_name, "user-available-symbolic")
                GLib.idle_add(self._send_button.set_sensitive, True)

        thread = threading.Thread(target=process_in_thread, daemon=True)
        thread.start()

    def _update_status(self):
        """Update model label with current model info"""
        model_info = get_model_by_id(self._current_model_id)
        if model_info:
            self._model_label.set_text(model_info["name"])
        else:
            self._model_label.set_text("未选择模型")

    def _get_current_model_config(self) -> tuple:
        """Get current model's provider, model name, and API key"""
        model_info = get_model_by_id(self._current_model_id)
        if not model_info:
            return "ollama", "qwen2.5:latest", ""

        provider = model_info["provider"]
        model = model_info["model"]
        api_keys = self._config.get("api_keys", {})
        api_key = api_keys.get(provider, "")

        return provider, model, api_key

    def _call_llm_sync(self, text: str) -> str:
        """Call LLM API synchronously"""
        provider, model, api_key = self._get_current_model_config()

        # Default URLs for each provider
        default_urls = {
            "ollama": "http://localhost:11434/v1",
            "vllm": "http://localhost:8000/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "aliyun": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "moonshot": "https://api.moonshot.cn/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
        }

        url = default_urls.get(provider, "http://localhost:11434/v1")
        api_url = f"{url}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": ADA_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')[:500]
            raise Exception(f"API 错误 ({e.code}): {error_body}")
        except Exception as e:
            raise Exception(f"请求失败: {e}")

    def _on_voice(self, button):
        """Handle voice input"""
        # Toggle voice recording
        if button.get_icon_name() == "audio-input-microphone-symbolic":
            button.set_icon_name("media-playback-stop-symbolic")
        else:
            button.set_icon_name("audio-input-microphone-symbolic")

    def _on_settings_clicked(self, button):
        """Toggle settings panel"""
        # Reload config when opening settings
        if not self._panel_manager.is_panel_visible("settings"):
            self._settings_panel._load_settings()
        self._panel_manager.toggle_panel("settings")

    def _on_model_selector_clicked(self, button):
        """Show model selector popover - only enabled models"""
        # 重新加载配置以获取最新的启用模型
        self._config = load_config()

        # Create popover
        popover = Gtk.Popover()
        popover.set_parent(button)
        popover.set_position(Gtk.PositionType.BOTTOM)

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)

        # Get enabled models
        enabled_models = get_enabled_models(self._config)

        if not enabled_models:
            # No models enabled, show message
            label = Gtk.Label(label="没有启用的模型\n请在设置中启用模型")
            label.add_css_class("dim-label")
            main_box.append(label)
        else:
            # Model list label
            list_label = Gtk.Label(label="选择模型", xalign=0)
            list_label.add_css_class("caption")
            list_label.add_css_class("dim-label")
            main_box.append(list_label)

            # Model list
            model_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
            model_list.add_css_class("rich-list")

            for model_info in enabled_models:
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_start=8, margin_end=8, margin_top=4, margin_bottom=4)
                name_label = Gtk.Label(label=model_info["name"], xalign=0, hexpand=True)
                row_box.append(name_label)

                if model_info["id"] == self._current_model_id:
                    check = Gtk.Image(icon_name="object-select-symbolic")
                    row_box.append(check)

                row.set_child(row_box)
                row.model_id = model_info["id"]
                model_list.append(row)

            model_list.connect("row-activated", self._on_model_selected, popover)
            main_box.append(model_list)

        popover.set_child(main_box)
        popover.popup()

    def _on_model_selected(self, list_box, row, popover):
        """Handle model selection"""
        model_id = row.model_id

        # Update current model
        self._current_model_id = model_id

        # Save to config
        self._config["current_model"] = model_id
        self._save_config()

        # Update UI
        self._update_status()

        popover.popdown()

    def _save_config(self):
        """Save config to file"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self._config, indent=2, ensure_ascii=False))
        logger.info(f"Config saved to {CONFIG_FILE}")

    def _add_message(self, message: Message):
        """Add message to list"""
        self._messages.append(message)
        row = MessageRow(message)
        self._message_list.append(row)

        # Scroll to bottom
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll message list to bottom"""
        # Get last row
        n_items = self._message_list.get_row_at_index(len(self._messages) - 1)
        if n_items:
            pass  # GTK4 handles this automatically

    def _load_state(self):
        """Load saved window state"""
        # TODO: Load from GSettings
        pass

    def _save_state(self):
        """Save window state"""
        # TODO: Save to GSettings
        pass

    def do_close_request(self):
        """Handle window close"""
        self._save_state()
        return False  # Allow close
