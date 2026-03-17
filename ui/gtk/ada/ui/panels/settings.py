"""
Settings Panel - 设置侧边面板
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from typing import Dict, Any, Optional
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Config file path
CONFIG_DIR = Path.home() / ".config" / "ada"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    return {}


def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    logger.info(f"Config saved to {CONFIG_FILE}")


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


class SettingsPanel(Adw.Bin):
    """
    设置侧边面板

    使用侧边栏导航的方式显示各设置页面：
    - LLM 设置
    - 通用设置
    - 内存设置
    - 技能设置
    - 安全设置
    """

    def __init__(self, on_close: Optional[callable] = None):
        super().__init__()
        self._on_close_callback = on_close
        self._initializing = True
        self._config = load_config()

        self._build_ui()
        self._load_settings()
        self._initializing = False

    def _build_ui(self):
        """构建面板UI"""
        # 主容器
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # 顶部栏
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="设置"))

        # 关闭按钮
        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.connect("clicked", self._on_close)
        header.pack_end(close_btn)

        main_box.append(header)

        # 使用 NavigationSplitView 实现侧边栏导航
        self._split_view = Adw.NavigationSplitView()

        # 侧边栏 - 页面列表
        sidebar_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        sidebar_list.add_css_class("navigation-sidebar")

        pages = [
            ("llm", "语言模型", "dialog-information-symbolic"),
            ("general", "通用", "preferences-system-symbolic"),
            ("memory", "内存", "folder-documents-symbolic"),
            ("skills", "技能", "system-run-symbolic"),
            ("security", "安全", "security-high-symbolic"),
        ]

        for page_id, title, icon in pages:
            row = Adw.ActionRow(title=title)
            row.set_icon_name(icon)
            row.page_id = page_id
            sidebar_list.append(row)

        sidebar_list.connect("row-selected", self._on_page_selected)
        sidebar_list.select_row(sidebar_list.get_row_at_index(0))

        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_child(sidebar_list)
        sidebar_scroll.set_size_request(180, -1)

        sidebar_page = Adw.NavigationPage(title="设置")
        sidebar_page.set_child(sidebar_scroll)

        # 内容区
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # 添加各页面
        self._content_stack.add_named(self._build_llm_page(), "llm")
        self._content_stack.add_named(self._build_general_page(), "general")
        self._content_stack.add_named(self._build_memory_page(), "memory")
        self._content_stack.add_named(self._build_skills_page(), "skills")
        self._content_stack.add_named(self._build_security_page(), "security")

        content_scroll = Gtk.ScrolledWindow()
        content_scroll.set_child(self._content_stack)
        content_scroll.set_hexpand(True)
        content_scroll.set_vexpand(True)

        content_page = Adw.NavigationPage(title="内容")
        content_page.set_child(content_scroll)

        # 设置 SplitView
        self._split_view.set_sidebar(sidebar_page)
        self._split_view.set_content(content_page)
        self._split_view.set_vexpand(True)

        main_box.append(self._split_view)
        self.set_child(main_box)

    def _on_page_selected(self, listbox, row):
        """页面选择处理"""
        if row and hasattr(row, 'page_id'):
            self._content_stack.set_visible_child_name(row.page_id)

    def _on_close(self, btn):
        """关闭面板"""
        if self._on_close_callback:
            self._on_close_callback()

    def _build_llm_page(self) -> Gtk.Widget:
        """构建 LLM 设置页面"""
        page = Adw.PreferencesPage()
        page.set_title("语言模型")

        # 服务商选择组
        provider_group = Adw.PreferencesGroup(title="服务商选择")

        # 服务商类型
        self.category_row = Adw.ComboRow(
            title="服务商类型",
            model=Gtk.StringList.new([
                "本地模型",
                "国际服务",
                "国内服务"
            ]),
        )
        self.category_row.connect("notify::selected", self._on_category_changed)
        provider_group.add(self.category_row)

        # 服务商
        self.provider_row = Adw.ComboRow(title="服务商")
        self.provider_row.connect("notify::selected", self._on_provider_changed)
        provider_group.add(self.provider_row)

        # 模型
        self.model_row = Adw.ComboRow(title="模型")
        provider_group.add(self.model_row)

        page.add(provider_group)

        # 连接设置组
        self.provider_settings_group = Adw.PreferencesGroup(title="连接设置")

        # API Key
        self.api_key_row = Adw.PasswordEntryRow(title="API Key")
        self.api_key_row.connect("changed", self._on_setting_changed)
        self.provider_settings_group.add(self.api_key_row)

        # Base URL
        self.base_url_row = Adw.EntryRow(title="服务器地址")
        self.base_url_row.connect("changed", self._on_setting_changed)
        self.provider_settings_group.add(self.base_url_row)

        page.add(self.provider_settings_group)

        # 生成参数组
        params_group = Adw.PreferencesGroup(title="生成参数")

        self.temperature_row = Adw.SpinRow(title="Temperature", subtitle="响应随机性")
        self.temperature_row.set_range(0.0, 2.0)
        self.temperature_row.set_value(0.7)
        self.temperature_row.set_digits(2)
        self.temperature_row.connect("notify::value", self._on_setting_changed)
        params_group.add(self.temperature_row)

        self.max_tokens_row = Adw.SpinRow(title="最大长度", subtitle="最大响应长度")
        self.max_tokens_row.set_range(100, 128000)
        self.max_tokens_row.set_value(4096)
        self.max_tokens_row.connect("notify::value", self._on_setting_changed)
        params_group.add(self.max_tokens_row)

        page.add(params_group)

        # 初始化服务商列表
        self._update_provider_list("local")

        return page

    def _build_general_page(self) -> Gtk.Widget:
        """构建通用设置页面"""
        page = Adw.PreferencesPage()
        page.set_title("通用")

        # 外观组
        appearance_group = Adw.PreferencesGroup(title="外观")

        dark_mode = Adw.SwitchRow(title="深色模式", subtitle="使用深色主题")
        dark_mode.connect("notify::active", self._on_dark_mode_changed)
        appearance_group.add(dark_mode)

        page.add(appearance_group)

        # 行为组
        behavior_group = Adw.PreferencesGroup(title="行为")

        autostart = Adw.SwitchRow(title="自动启动", subtitle="登录时自动启动")
        behavior_group.add(autostart)

        notifications = Adw.SwitchRow(title="显示通知", subtitle="显示桌面通知", active=True)
        behavior_group.add(notifications)

        page.add(behavior_group)

        return page

    def _build_memory_page(self) -> Gtk.Widget:
        """构建内存设置页面"""
        page = Adw.PreferencesPage()
        page.set_title("内存")

        storage_group = Adw.PreferencesGroup(title="存储")

        memory_enabled = Adw.SwitchRow(title="启用内存", subtitle="记住对话和上下文", active=True)
        storage_group.add(memory_enabled)

        page.add(storage_group)

        retention_group = Adw.PreferencesGroup(title="保留")

        conv_retention = Adw.SpinRow(title="对话保留 (天)", subtitle="对话历史保留时间")
        conv_retention.set_range(1, 365)
        conv_retention.set_value(30)
        retention_group.add(conv_retention)

        page.add(retention_group)

        return page

    def _build_skills_page(self) -> Gtk.Widget:
        """构建技能设置页面"""
        page = Adw.PreferencesPage()
        page.set_title("技能")

        general_group = Adw.PreferencesGroup(title="通用")

        auto_discover = Adw.SwitchRow(title="自动发现", subtitle="自动发现并加载技能", active=True)
        general_group.add(auto_discover)

        page.add(general_group)

        skills_group = Adw.PreferencesGroup(title="已安装技能")

        skill_row = Adw.ActionRow(title="文件整理", subtitle="按类型、日期整理文件")
        skill_row.add_suffix(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
        skills_group.add(skill_row)

        skill_row2 = Adw.ActionRow(title="应用启动器", subtitle="启动和管理应用程序")
        skill_row2.add_suffix(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
        skills_group.add(skill_row2)

        page.add(skills_group)

        return page

    def _build_security_page(self) -> Gtk.Widget:
        """构建安全设置页面"""
        page = Adw.PreferencesPage()
        page.set_title("安全")

        mode_group = Adw.PreferencesGroup(title="安全模式")

        mode = Adw.ComboRow(
            title="安全级别",
            model=Gtk.StringList.new(["宽松", "平衡", "严格"]),
        )
        mode.set_selected(1)
        mode_group.add(mode)

        page.add(mode_group)

        confirm_group = Adw.PreferencesGroup(title="确认")

        destructive = Adw.SwitchRow(title="破坏性操作", subtitle="破坏性操作需要确认", active=True)
        confirm_group.add(destructive)

        system = Adw.SwitchRow(title="系统操作", subtitle="系统操作需要确认", active=True)
        confirm_group.add(system)

        page.add(confirm_group)

        sandbox_group = Adw.PreferencesGroup(title="沙箱")

        sandbox_enabled = Adw.SwitchRow(title="启用沙箱", subtitle="在隔离环境中运行外部命令", active=True)
        sandbox_group.add(sandbox_enabled)

        page.add(sandbox_group)

        return page

    def _get_category_key(self, index: int) -> str:
        keys = ["local", "international", "china"]
        return keys[index] if 0 <= index < len(keys) else "local"

    def _update_provider_list(self, category: str):
        """更新服务商列表"""
        category_info = PROVIDER_CATEGORIES.get(category, PROVIDER_CATEGORIES["local"])
        providers = category_info["providers"]

        model = Gtk.StringList.new([f"{p['name']} - {p['desc']}" for p in providers])
        self.provider_row.set_model(model)

        self._current_provider_ids = [p["id"] for p in providers]
        self._update_model_list()
        self._update_provider_settings()

    def _update_model_list(self):
        """更新模型列表"""
        provider_id = self._get_current_provider_id()
        models = PROVIDER_MODELS.get(provider_id, ["默认模型"])

        model = Gtk.StringList.new(models)
        self.model_row.set_model(model)

    def _get_current_provider_id(self) -> str:
        if not hasattr(self, '_current_provider_ids') or not self._current_provider_ids:
            return "ollama"
        selected = self.provider_row.get_selected()
        if 0 <= selected < len(self._current_provider_ids):
            return self._current_provider_ids[selected]
        return "ollama"

    def _update_provider_settings(self):
        """更新服务商设置"""
        provider_id = self._get_current_provider_id()

        # 本地服务商不需要 API Key
        is_local = provider_id in ["ollama", "vllm"]
        self.api_key_row.set_visible(not is_local)

        # 默认 URL
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

        # 更新组标题
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
        self.provider_settings_group.set_title(names.get(provider_id, "连接设置"))

    def _on_category_changed(self, row, param):
        if self._initializing:
            return
        category = self._get_category_key(row.get_selected())
        self._update_provider_list(category)
        self._save_settings()

    def _on_provider_changed(self, row, param):
        if self._initializing:
            return
        self._update_model_list()
        self._update_provider_settings()
        self._save_settings()

    def _on_setting_changed(self, *args):
        if self._initializing:
            return
        self._save_settings()

    def _on_dark_mode_changed(self, switch, param):
        style_manager = Adw.StyleManager.get_default()
        if switch.get_active():
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)
        self._save_settings()

    def _get_selected_model(self) -> str:
        provider_id = self._get_current_provider_id()
        models = PROVIDER_MODELS.get(provider_id, [])
        if models:
            selected = self.model_row.get_selected()
            if 0 <= selected < len(models):
                return models[selected]
        return ""

    def _load_settings(self):
        """加载保存的设置"""
        llm_config = self._config.get("llm", {})

        # 恢复服务商类型
        provider = llm_config.get("provider", "ollama")
        category_map = {
            "ollama": 0, "vllm": 0,
            "openai": 1, "anthropic": 1, "google": 1,
            "aliyun": 2, "deepseek": 2, "zhipu": 2, "moonshot": 2,
            "baidu": 2, "siliconflow": 2
        }
        cat_idx = category_map.get(provider, 0)
        self.category_row.set_selected(cat_idx)

        # 恢复 API Key
        if llm_config.get("api_key"):
            self.api_key_row.set_text(llm_config["api_key"])

        # 恢复参数
        params = llm_config.get("params", {})
        if params.get("temperature"):
            self.temperature_row.set_value(params["temperature"])
        if params.get("max_tokens"):
            self.max_tokens_row.set_value(params["max_tokens"])

    def _save_settings(self):
        """保存设置"""
        if self._initializing:
            return

        config = {
            "llm": {
                "provider": self._get_current_provider_id(),
                "model": self._get_selected_model(),
                "api_key": self.api_key_row.get_text() if self.api_key_row.get_visible() else "",
                "base_url": self.base_url_row.get_text() if self.base_url_row.get_visible() else "",
                "params": {
                    "temperature": self.temperature_row.get_value(),
                    "max_tokens": int(self.max_tokens_row.get_value()),
                }
            },
            "general": {}
        }

        try:
            save_config(config)
            logger.debug("Settings saved")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get_llm_config(self) -> Dict[str, Any]:
        """获取当前 LLM 配置"""
        return {
            "provider": self._get_current_provider_id(),
            "model": self._get_selected_model(),
            "api_key": self.api_key_row.get_text() if self.api_key_row.get_visible() else "",
            "base_url": self.base_url_row.get_text() if self.base_url_row.get_visible() else "",
            "params": {
                "temperature": self.temperature_row.get_value(),
                "max_tokens": int(self.max_tokens_row.get_value()),
            }
        }
