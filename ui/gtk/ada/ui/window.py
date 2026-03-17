"""
Main Window - Primary UI for Ada
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Pango

import asyncio
import logging
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Config file path
CONFIG_FILE = Path.home() / ".config" / "ada" / "config.json"

# Thread pool for async HTTP calls
_executor = ThreadPoolExecutor(max_workers=4)


def load_llm_config() -> Dict[str, Any]:
    """Load LLM configuration from file"""
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text())
            return config.get("llm", {})
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    return {}


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

        # Create message bubble
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_start=12,
            margin_end=12,
            margin_top=6,
            margin_bottom=6,
        )

        # Message content
        label = Gtk.Label(
            label=message.content,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
            xalign=0 if not message.is_user else 1,
        )

        # Style based on sender
        if message.is_user:
            box.add_css_class("ada-message")
            box.add_css_class("ada-user-message")
            label.set_halign(Gtk.Align.END)
        else:
            box.add_css_class("ada-message")
            box.add_css_class("ada-assistant-message")
            label.set_halign(Gtk.Align.START)

        box.append(label)

        # Thinking indicator
        if message.thinking:
            thinking_label = Gtk.Label(
                label=message.thinking,
                wrap=True,
                xalign=0,
            )
            thinking_label.add_css_class("ada-thinking")
            box.append(thinking_label)

        self.set_child(box)


class MainWindow(Adw.ApplicationWindow):
    """
    Main application window for Ada.

    Features:
    - Chat interface
    - Message history
    - Input field with voice option
    - Status indicator
    """

    def __init__(self, app, agent=None):
        super().__init__(application=app, title="Ada")

        self.agent = agent
        self._messages: List[Message] = []
        self._llm_config = load_llm_config()

        # Window setup
        self.set_default_size(600, 700)
        self.set_size_request(400, 500)

        # Build UI
        self._build_ui()

        # Load saved state
        self._load_state()

        # Update status label with current provider
        self._update_status()

    def _build_ui(self):
        """Build the user interface"""
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Ada", subtitle="AI Assistant"))

        # Settings button (LLM config)
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.set_tooltip_text("LLM 设置")
        settings_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(settings_btn)

        # Menu button
        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About", "app.about")
        menu_button = Gtk.MenuButton(menu_model=menu)
        header.pack_end(menu_button)

        # Status indicator with provider info
        self._status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._status_icon = Gtk.Image(icon_name="user-available-symbolic")
        self._status_label = Gtk.Label(label="Ollama · qwen2.5")
        self._status_label.add_css_class("caption")
        self._status_label.add_css_class("dim-label")
        self._status_box.append(self._status_icon)
        self._status_box.append(self._status_label)
        header.pack_start(self._status_box)

        main_box.append(header)

        # Content area with chat
        content = Adw.Clamp(maximum_size=800)

        # Message list
        self._message_list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            valign=Gtk.Align.END,
        )
        self._message_list.add_css_class("rich-list")

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

        # Welcome message
        self._add_message(Message(
            "你好！我是 Ada，你的 AI 助手。有什么可以帮助你的吗？",
            is_user=False
        ))

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
        self._llm_config = load_llm_config()

        # Show loading state
        self._status_icon.set_from_icon_name("content-loading-symbolic")
        self._send_button.set_sensitive(False)

        # Process in background thread
        import threading

        def process_in_thread():
            try:
                response = self._call_llm_sync(text)
                GLib.idle_add(self._add_message, Message(response, is_user=False))
            except Exception as e:
                logger.error(f"LLM error: {e}")
                GLib.idle_add(self._add_message, Message(f"❌ 错误: {e}", is_user=False))
            finally:
                GLib.idle_add(self._status_icon.set_from_icon_name, "user-available-symbolic")
                GLib.idle_add(self._send_button.set_sensitive, True)

        thread = threading.Thread(target=process_in_thread, daemon=True)
        thread.start()

    def _update_status(self):
        """Update status label with current provider info"""
        provider = self._llm_config.get("provider", "ollama")
        model = self._llm_config.get("model", "")

        provider_names = {
            "ollama": "Ollama",
            "openai": "OpenAI",
            "anthropic": "Claude",
            "google": "Gemini",
            "aliyun": "通义千问",
            "deepseek": "DeepSeek",
            "zhipu": "智谱AI",
            "moonshot": "Kimi",
            "baidu": "文心一言",
            "siliconflow": "硅基流动",
        }

        name = provider_names.get(provider, provider)
        self._status_label.set_text(f"{name} · {model}" if model else name)

    def _call_llm_sync(self, text: str) -> str:
        """Call LLM API synchronously"""
        provider = self._llm_config.get("provider", "ollama")
        model = self._llm_config.get("model", "qwen2.5:latest")
        api_key = self._llm_config.get("api_key", "")
        base_url = self._llm_config.get("base_url", "")
        params = self._llm_config.get("params", {})

        # Default URLs for each provider
        default_urls = {
            "ollama": "http://localhost:11434/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "aliyun": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "moonshot": "https://api.moonshot.cn/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
        }

        url = base_url or default_urls.get(provider, "http://localhost:11434/v1")
        api_url = f"{url}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": text}],
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 4096),
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

    async def _process_message(self, text: str):
        """Process message with agent"""
        # Show thinking indicator
        self._status_icon.set_from_icon_name("content-loading-symbolic")

        try:
            result = await self.agent.process(text)

            # Add response
            GLib.idle_add(
                self._add_message,
                Message(result.message, is_user=False)
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            GLib.idle_add(
                self._add_message,
                Message(f"抱歉，处理消息时出错：{e}", is_user=False)
            )

        finally:
            # Hide thinking indicator
            GLib.idle_add(
                self._status_icon.set_from_icon_name,
                "user-available-symbolic"
            )

    def _on_voice(self, button):
        """Handle voice input"""
        # Toggle voice recording
        if button.get_icon_name() == "audio-input-microphone-symbolic":
            button.set_icon_name("media-playback-stop-symbolic")
            # Start recording
            asyncio.create_task(self._start_voice_recording())
        else:
            button.set_icon_name("audio-input-microphone-symbolic")
            # Stop recording

    def _on_settings_clicked(self, button):
        """Open LLM settings dialog"""
        from .preferences import PreferencesWindow
        prefs = PreferencesWindow(self.get_application())
        prefs.present()

    async def _start_voice_recording(self):
        """Start voice recording"""
        # Placeholder for voice input
        pass

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
            # Scroll adjustment
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


# Required import for Gio.Menu
from gi.repository import Gio
