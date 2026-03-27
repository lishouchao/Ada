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

# 提供商配置（按提供商组织）
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

# 生成扁平化的 ALL_MODELS 用于模型选择器
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
                "model": model["id"]
            })
    return result

ALL_MODELS = _build_all_models()


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
        """构建面板UI - 不包含标题栏，由独立窗口提供"""
        # 主容器
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

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

        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_child(sidebar_list)
        sidebar_scroll.set_size_request(180, -1)

        sidebar_page = Adw.NavigationPage(title="设置")
        sidebar_page.set_child(sidebar_scroll)

        # 内容区 - 创建在信号连接之前
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # 添加各页面
        self._content_stack.add_named(self._build_llm_page(), "llm")
        self._content_stack.add_named(self._build_general_page(), "general")
        self._content_stack.add_named(self._build_memory_page(), "memory")
        self._content_stack.add_named(self._build_skills_page(), "skills")
        self._content_stack.add_named(self._build_security_page(), "security")

        # 信号连接放在 stack 创建之后
        sidebar_list.connect("row-selected", self._on_page_selected)
        sidebar_list.select_row(sidebar_list.get_row_at_index(0))

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
        """构建 LLM 设置页面 - 按提供商组织"""
        page = Adw.PreferencesPage()
        page.set_title("语言模型")

        # 保存所有开关引用
        self._model_switches = {}
        self._api_key_rows = {}

        # 按提供商创建组
        for provider in PROVIDERS:
            group = Adw.PreferencesGroup(
                title=provider["name"],
                description=f"本地服务 (前缀: {provider['prefix']})" if provider['prefix'] else None
            )

            # 如果需要 API Key，添加输入框
            if provider["need_key"]:
                key_row = Adw.PasswordEntryRow(title="API Key")
                key_row.connect("changed", self._on_api_key_changed, provider["id"])
                group.add(key_row)
                self._api_key_rows[provider["id"]] = key_row

            # 添加该提供商的所有模型
            for model in provider["models"]:
                model_id = f"{provider['id']}:{model['id']}"
                row = Adw.ActionRow(title=model["name"])
                switch = Gtk.Switch(valign=Gtk.Align.CENTER)
                switch.connect("notify::active", self._on_model_toggle, model_id)
                row.add_suffix(switch)
                self._model_switches[model_id] = switch
                group.add(row)

            page.add(group)

        return page

    def _on_model_toggle(self, switch, param, model_id: str):
        """模型启用/停用切换"""
        if self._initializing:
            return

        enabled_models = self._config.get("enabled_models", [])

        if switch.get_active():
            if model_id not in enabled_models:
                enabled_models.append(model_id)
        else:
            if model_id in enabled_models:
                enabled_models.remove(model_id)

        self._config["enabled_models"] = enabled_models
        save_config(self._config)

    def _on_api_key_changed(self, entry, provider: str):
        """API Key 变更处理"""
        if self._initializing:
            return

        api_keys = self._config.get("api_keys", {})
        api_keys[provider] = entry.get_text()
        self._config["api_keys"] = api_keys
        save_config(self._config)

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

    def _on_dark_mode_changed(self, switch, param):
        style_manager = Adw.StyleManager.get_default()
        if switch.get_active():
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)
        save_config(self._config)

    def _load_settings(self):
        """加载保存的设置"""
        # 加载启用的模型
        enabled_models = self._config.get("enabled_models", [])

        # 更新所有模型开关
        for model_id, switch in self._model_switches.items():
            switch.set_active(model_id in enabled_models)

        # 加载 API Keys
        api_keys = self._config.get("api_keys", {})
        for provider_id, key_row in self._api_key_rows.items():
            if api_keys.get(provider_id):
                key_row.set_text(api_keys[provider_id])

    def get_enabled_models(self) -> list:
        """获取已启用的模型列表"""
        return self._config.get("enabled_models", [])

    def get_api_key(self, provider: str) -> str:
        """获取指定服务商的 API Key"""
        api_keys = self._config.get("api_keys", {})
        return api_keys.get(provider, "")
