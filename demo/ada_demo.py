#!/usr/bin/env python3
"""
Ada UI Demo - Complete GTK4/libadwaita demonstration with LLM settings
"""

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, Pango, Gio

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
            {"id": "siliconflow", "name": "硅基流动", "desc": "多模型代理"},
        ]
    }
}

PROVIDER_MODELS = {
    "ollama": ["qwen2.5:latest", "llama3.2:latest", "deepseek-r1:latest", "mistral:latest"],
    "vllm": ["自定义模型"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-sonnet"],
    "google": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "aliyun": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen2.5-72b-instruct"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
    "zhipu": ["glm-4-plus", "glm-4-flash", "glm-4-air"],
    "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    "baidu": ["ernie-4.0-8k", "ernie-3.5-8k", "ernie-speed-8k"],
    "siliconflow": ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"],
}


class MessageRow(Gtk.Box):
    """A chat message row"""

    def __init__(self, text: str, is_user: bool = True):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(6)
        self.set_margin_bottom(6)

        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.set_margin_top(4)
        bubble.set_margin_bottom(4)
        bubble.set_margin_start(12)
        bubble.set_margin_end(12)

        sender = Gtk.Label()
        sender.set_halign(Gtk.Align.START)
        sender.set_markup(f"<b>{'你' if is_user else 'Ada'}</b>")
        sender.add_css_class('caption-heading')

        label = Gtk.Label()
        label.set_text(text)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)

        bubble.append(sender)
        bubble.append(label)

        if is_user:
            bubble.add_css_class('card')
            self.set_halign(Gtk.Align.END)
        else:
            bubble.add_css_class('assistant-message')
            self.set_halign(Gtk.Align.START)

        self.append(bubble)


class LLMConfigDialog(Adw.PreferencesWindow):
    """LLM Configuration Dialog"""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="LLM 设置",
            default_width=500,
            default_height=600,
        )
        self.parent_window = parent
        self._current_provider_ids = []
        self._on_save_callback = None

        self.add(self._build_llm_page())

    def set_save_callback(self, callback):
        """Set callback for when settings are saved"""
        self._on_save_callback = callback

    def _build_llm_page(self) -> Adw.PreferencesPage:
        """Build LLM settings page"""
        page = Adw.PreferencesPage(title="语言模型", icon_name="dialog-information-symbolic")

        # Provider selection group
        provider_group = Adw.PreferencesGroup(title="服务商选择")

        # Category
        self.category_row = Adw.ComboRow(
            title="服务商类型",
            subtitle="选择服务商类别",
            model=Gtk.StringList.new([
                "本地模型 (Local)",
                "国际服务 (International)",
                "国内服务 (China)"
            ]),
        )
        self.category_row.connect("notify::selected", self._on_category_changed)
        provider_group.add(self.category_row)

        # Provider
        self.provider_row = Adw.ComboRow(
            title="服务商",
            subtitle="选择 LLM 服务商",
        )
        self._update_provider_list("local")
        self.provider_row.connect("notify::selected", self._on_provider_changed)
        provider_group.add(self.provider_row)

        # Model
        self.model_row = Adw.ComboRow(
            title="模型",
            subtitle="选择使用的模型",
        )
        self._update_model_list()
        provider_group.add(self.model_row)

        page.add(provider_group)

        # Connection settings group
        self.settings_group = Adw.PreferencesGroup(title="连接设置")

        # API Key
        self.api_key_row = Adw.PasswordEntryRow(title="API Key")
        self.settings_group.add(self.api_key_row)

        # Base URL
        self.base_url_row = Adw.EntryRow(title="服务器地址")
        self.settings_group.add(self.base_url_row)

        page.add(self.settings_group)

        # Test connection
        test_group = Adw.PreferencesGroup()
        test_row = Adw.ButtonRow(
            title="测试连接",
            subtitle="验证配置是否正确",
        )
        test_row.connect("activated", self._on_test_connection)
        test_group.add(test_row)
        page.add(test_group)

        # Save button
        save_group = Adw.PreferencesGroup()
        save_row = Adw.ButtonRow(
            title="💾 保存设置",
            subtitle="应用当前 LLM 配置",
        )
        save_row.connect("activated", self._on_save)
        save_row.add_css_class("suggested-action")
        save_group.add(save_row)
        page.add(save_group)

        # Generation parameters
        params_group = Adw.PreferencesGroup(title="生成参数")

        self.temperature_row = Adw.SpinRow(title="Temperature", subtitle="响应随机性 (0.0 - 2.0)")
        self.temperature_row.set_range(0.0, 2.0)
        self.temperature_row.set_value(0.7)
        self.temperature_row.set_digits(1)
        params_group.add(self.temperature_row)

        self.max_tokens_row = Adw.SpinRow(title="最大长度", subtitle="最大响应长度")
        self.max_tokens_row.set_range(100, 128000)
        self.max_tokens_row.set_value(4096)
        params_group.add(self.max_tokens_row)

        page.add(params_group)

        # Update initial state
        self._update_provider_settings()

        return page

    def _get_category_key(self, index: int) -> str:
        keys = ["local", "international", "china"]
        return keys[index] if 0 <= index < len(keys) else "local"

    def _update_provider_list(self, category: str):
        category_info = PROVIDER_CATEGORIES.get(category, PROVIDER_CATEGORIES["local"])
        providers = category_info["providers"]
        model = Gtk.StringList.new([f"{p['name']} - {p['desc']}" for p in providers])
        self.provider_row.set_model(model)
        self._current_provider_ids = [p["id"] for p in providers]
        self._update_model_list()

    def _update_model_list(self):
        provider_id = self._get_current_provider_id()
        models = PROVIDER_MODELS.get(provider_id, ["默认模型"])
        model = Gtk.StringList.new(models)
        self.model_row.set_model(model)

    def _get_current_provider_id(self) -> str:
        if not self._current_provider_ids:
            return "ollama"
        selected = self.provider_row.get_selected()
        if 0 <= selected < len(self._current_provider_ids):
            return self._current_provider_ids[selected]
        return "ollama"

    def _update_provider_settings(self):
        provider_id = self._get_current_provider_id()

        # Local providers don't need API key
        is_local = provider_id in ["ollama", "vllm"]
        self.api_key_row.set_visible(not is_local)

        # Default URLs
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
            "siliconflow": "https://api.siliconflow.cn/v1",
        }

        self.base_url_row.set_text(default_urls.get(provider_id, ""))
        self.base_url_row.set_visible(provider_id in ["ollama", "vllm"])

        # Update group title
        names = {
            "ollama": "Ollama 设置",
            "vllm": "vLLM 设置",
            "openai": "OpenAI 设置",
            "anthropic": "Anthropic 设置",
            "google": "Google AI 设置",
            "aliyun": "通义千问 设置",
            "deepseek": "DeepSeek 设置",
            "zhipu": "智谱AI 设置",
            "moonshot": "Kimi 设置",
            "baidu": "文心一言 设置",
            "siliconflow": "硅基流动 设置",
        }
        self.settings_group.set_title(names.get(provider_id, "连接设置"))

    def _on_category_changed(self, row, param):
        category = self._get_category_key(row.get_selected())
        self._update_provider_list(category)
        self._update_provider_settings()

    def _on_provider_changed(self, row, param):
        self._update_model_list()
        self._update_provider_settings()

    def _on_test_connection(self, row):
        provider_id = self._get_current_provider_id()
        toast = Adw.Toast.new(f"正在测试 {provider_id} 连接...")
        toast.set_timeout(2)
        self.add_toast(toast)

        GLib.timeout_add(1500, lambda: self._show_test_result())

    def _show_test_result(self) -> bool:
        toast = Adw.Toast.new("✓ 连接成功！")
        toast.set_timeout(3)
        self.add_toast(toast)
        return False

    def _on_save(self, row):
        """Save settings and close"""
        if self._on_save_callback:
            self._on_save_callback(self.get_config())

        toast = Adw.Toast.new("✓ 设置已保存")
        toast.set_timeout(2)
        self.add_toast(toast)

        GLib.timeout_add(500, lambda: (self.destroy(), False)[1])

    def get_config(self):
        return {
            "provider": self._get_current_provider_id(),
            "model": PROVIDER_MODELS.get(self._get_current_provider_id(), [""])[
                self.model_row.get_selected() if self.model_row.get_selected() >= 0 else 0
            ],
            "api_key": self.api_key_row.get_text(),
            "base_url": self.base_url_row.get_text(),
            "temperature": self.temperature_row.get_value(),
            "max_tokens": int(self.max_tokens_row.get_value()),
        }


class MainWindow(Adw.ApplicationWindow):
    """Main Ada window"""

    def __init__(self, app):
        super().__init__(application=app, title="Ada - AI Assistant")
        self.set_default_size(550, 650)
        self.set_size_request(400, 450)
        self.llm_config = {"provider": "ollama", "model": "qwen2.5:latest"}

        # Build UI
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar with settings button
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle.new("Ada", "NebulaOS AI 助手"))

        # Settings button
        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.set_tooltip_text("LLM 设置")
        settings_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(settings_btn)

        # Menu
        menu = Gio.Menu()
        menu.append("关于", "app.about")
        menu_btn = Gtk.MenuButton(menu_model=menu, icon_name="open-menu-symbolic")
        header.pack_end(menu_btn)

        main_box.append(header)

        # Chat area
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)

        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.messages_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.messages_list.set_vexpand(True)
        self.messages_list.set_margin_top(12)
        self.messages_list.set_margin_bottom(12)

        viewport = Gtk.Viewport()
        viewport.set_child(self.messages_list)
        scroll.set_child(viewport)

        self.chat_box.append(scroll)
        clamp.set_child(self.chat_box)
        main_box.append(clamp)

        # Current provider indicator
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_box.set_margin_start(12)
        self.status_box.set_margin_bottom(6)

        self.status_icon = Gtk.Image(icon_name="user-available-symbolic")
        self.status_label = Gtk.Label(label="Ollama · qwen2.5:latest")
        self.status_label.add_css_class("caption")
        self.status_label.add_css_class("dim-label")

        self.status_box.append(self.status_icon)
        self.status_box.append(self.status_label)
        main_box.append(self.status_box)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        input_box.set_margin_start(12)
        input_box.set_margin_end(12)
        input_box.set_margin_top(8)
        input_box.set_margin_bottom(12)
        input_box.set_spacing(8)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("输入消息...")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.on_send)

        self.send_btn = Gtk.Button()
        self.send_btn.set_icon_name("paper-plane-symbolic")
        self.send_btn.set_tooltip_text("发送")
        self.send_btn.connect("clicked", self.on_send)
        self.send_btn.add_css_class('suggested-action')
        self.send_btn.add_css_class('circular')

        input_box.append(self.entry)
        input_box.append(self.send_btn)
        main_box.append(input_box)

        self.set_content(main_box)

        # Add demo messages
        self.add_message("你好！我是 Ada，你的 AI 助手。点击右上角 ⚙️ 按钮配置 LLM 服务商。", is_user=False)
        self.add_message("你好", is_user=True)
        self.add_message("有什么我可以帮助你的吗？我可以协助你完成各种任务，比如回答问题、整理文件、控制系统设置等。", is_user=False)

        # Apply CSS
        self._apply_css()

    def add_message(self, text: str, is_user: bool = True):
        row = MessageRow(text, is_user)
        self.messages_list.append(row)
        GLib.timeout_add(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        return False

    def on_send(self, widget):
        text = self.entry.get_text().strip()
        if not text:
            return

        self.add_message(text, is_user=True)
        self.entry.set_text("")

        # Simulate response based on current provider
        provider_name = {
            "ollama": "Ollama (本地)",
            "openai": "OpenAI",
            "anthropic": "Claude",
            "google": "Gemini",
            "aliyun": "通义千问",
            "deepseek": "DeepSeek",
            "zhipu": "智谱GLM",
            "moonshot": "Kimi",
        }.get(self.llm_config.get("provider", "ollama"), "LLM")

        responses = {
            "设置": f"当前使用 {provider_name} 服务，模型: {self.llm_config.get('model', 'unknown')}",
            "帮助": "我可以帮你：\n• 回答问题和对话\n• 整理文件\n• 启动应用程序\n• 搜索网络\n• 设置提醒\n\n请点击右上角⚙️按钮配置 LLM。",
        }

        response = f"收到你的消息：「{text}」\n\n当前使用 {provider_name} 进行回复。"
        for key, resp in responses.items():
            if key in text:
                response = resp
                break

        GLib.timeout_add(500, lambda: (self.add_message(response, is_user=False), False)[1])

    def _on_settings_clicked(self, btn):
        dialog = LLMConfigDialog(self)

        def on_save(config):
            self.llm_config = config
            provider_name = {
                "ollama": "Ollama",
                "openai": "OpenAI",
                "anthropic": "Claude",
                "google": "Gemini",
                "aliyun": "通义千问",
                "deepseek": "DeepSeek",
                "zhipu": "智谱GLM",
                "moonshot": "Kimi",
                "baidu": "文心一言",
                "siliconflow": "硅基流动",
            }.get(config.get("provider", "ollama"), "LLM")
            self.status_label.set_text(f"{provider_name} · {config.get('model', '')}")
            self.add_message(f"✓ 已切换到 {provider_name} ({config.get('model', '')})", is_user=False)

        dialog.set_save_callback(on_save)
        dialog.present()

    def _apply_css(self):
        css = b'''
        .assistant-message {
            background-color: @card_bg_color;
            border-radius: 12px;
        }
        .card {
            background-color: @accent_bg_color;
            color: @accent_fg_color;
            border-radius: 12px;
        }
        entry {
            border-radius: 24px;
            padding: 8px 16px;
        }
        .circular {
            border-radius: 50%;
            padding: 8px;
        }
        .dim-label {
            opacity: 0.6;
        }
        '''

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


class AdaDemo(Adw.Application):
    """Ada Demo Application"""

    def __init__(self):
        super().__init__(application_id='org.nebula.Ada')
        self.window = None

    def do_startup(self):
        Adw.Application.do_startup(self)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self)
        self.window.present()

    def _on_about(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name="Ada",
            application_icon="dialog-information",
            version="0.1.0",
            comments="NebulaOS AI 助手\n支持多种 LLM 服务商",
            website="https://github.com/lishouchao/Ada",
            developers=["Nebula Team"],
            copyright="© 2024",
            license_type=Gtk.License.MIT_X11,
        )
        about.present()


def main():
    app = AdaDemo()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
