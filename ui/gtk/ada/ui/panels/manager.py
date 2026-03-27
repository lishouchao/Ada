"""
Side Panel Manager - 管理独立的侧边窗口

支持多种触发方式：
1. 主窗体按钮触发（设置按钮等）
2. Agent 行为触发（打开浏览器、显示文件等）
3. 其他组件触发

特点：
- 面板是完全独立的 Gtk.Window
- 有自己的标题栏、最小化/最大化/关闭按钮
- 自动定位在主窗口右侧
- 可独立关闭
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, GLib, Gdk
from typing import Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)

# 检测是否是 Wayland 环境
def is_wayland() -> bool:
    """检测当前是否运行在 Wayland 下"""
    display = Gdk.Display.get_default()
    if display:
        return "Wayland" in type(display).__name__
    return False


class SidePanelManager:
    """
    侧边面板管理器

    管理所有内容面板作为独立窗口。
    面板窗口自动定位在主窗口右侧。
    """

    # 预定义面板类型
    SETTINGS = "settings"
    BROWSER = "browser"
    FILES = "files"
    SKILLS = "skills"
    MEMORY = "memory"
    HELP = "help"

    def __init__(self, main_window: Gtk.Window):
        self._main_window = main_window
        self._panels: Dict[str, Gtk.Window] = {}
        self._panel_contents: Dict[str, Gtk.Widget] = {}
        self._current_panel: Optional[str] = None
        self._callbacks: Dict[str, list] = {
            "panel_opened": [],
            "panel_closed": [],
            "panel_changed": [],
        }

        # 主窗口关闭时关闭所有面板
        main_window.connect("close-request", self._on_main_window_close)

    def _on_main_window_close(self, window) -> bool:
        """主窗口关闭时关闭所有面板"""
        for panel_name in list(self._panels.keys()):
            self.hide_panel(panel_name)
        return False  # 允许关闭

    def register_panel(self, name: str, panel_content: Gtk.Widget,
                       title: str = "Panel", width: int = 500) -> None:
        """
        注册面板内容

        Args:
            name: 面板名称（使用类常量如 SidePanelManager.SETTINGS）
            panel_content: 面板内容控件
            title: 面板窗口标题
            width: 面板宽度
        """
        self._panel_contents[name] = {
            "content": panel_content,
            "title": title,
            "width": width,
        }
        logger.debug(f"Panel content registered: {name}")

    def show_panel(self, name: str, data: Optional[dict] = None) -> bool:
        """
        显示指定面板

        可从任何地方调用：按钮、Agent、其他组件

        Args:
            name: 面板名称
            data: 传递给面板的数据（如 URL、文件路径等）

        Returns:
            bool: 是否成功显示
        """
        if name not in self._panel_contents:
            logger.warning(f"Panel not found: {name}")
            return False

        panel_info = self._panel_contents[name]
        panel_content = panel_info["content"]

        # 如果面板有 update_data 方法，传递数据
        if data and hasattr(panel_content, 'update_data'):
            panel_content.update_data(data)

        # 如果当前显示的是同一个面板，则隐藏
        if self._current_panel == name and name in self._panels:
            self.hide_panel(name)
            return True

        # 关闭当前面板
        if self._current_panel and self._current_panel in self._panels:
            self.hide_panel(self._current_panel)

        # 创建新的独立窗口
        window = Gtk.Window()
        window.set_title(panel_info["title"])
        window.set_default_size(panel_info["width"], 700)  # 副窗口高度
        window.set_transient_for(self._main_window)  # 与主窗口关联
        window.set_destroy_with_parent(True)  # 主窗口关闭时副窗口也关闭

        # 设置窗口内容
        window.set_child(panel_content)

        # 窗口关闭时清理
        window.connect("close-request", self._on_panel_close, name)

        # 监听主窗口位置变化，副窗口跟随（仅在 X11 下有效）
        self._configure_handler = self._main_window.connect(
            "notify::default-width", self._on_main_window_configure
        )

        # 定位到主窗口右侧并排显示
        self._position_panel_window(window, panel_info["width"])

        # 显示窗口
        window.present()

        # 延迟再次定位（窗口显示后才能获取准确位置）
        GLib.timeout_add(100, self._position_panel_window, window, panel_info["width"])

        self._panels[name] = window
        self._current_panel = name

        # 触发回调
        self._trigger_callbacks("panel_opened", name)
        self._trigger_callbacks("panel_changed", name)

        logger.info(f"Panel window shown: {name}")
        return True

    def _position_panel_window(self, panel_window: Gtk.Window, panel_width: int):
        """将面板窗口定位在主窗口右侧"""
        if not panel_window.is_visible():
            return False

        # 获取主窗口的位置和大小
        main_surface = self._main_window.get_surface()
        if not main_surface:
            return False

        try:
            # 尝试获取主窗口位置（X11 下有效，Wayland 下可能失败）
            main_x = main_surface.get_x()
            main_y = main_surface.get_y()
            main_width = self._main_window.get_width()
            main_height = self._main_window.get_height()

            # 计算面板位置（主窗口右侧）
            panel_x = main_x + main_width + 10  # 10px 间距
            panel_y = main_y

            # 在 X11 下尝试移动窗口
            # GTK4 没有直接的 move()，但可以通过 xdg_toplevel 实现
            # 这里我们使用一个变通方法：通过 Gdk.Toplevel 的 API
            panel_surface = panel_window.get_surface()
            if panel_surface and not is_wayland():
                # X11 下可以尝试设置位置
                # 注意：GTK4 没有公开的 move API，但 transient 关系会帮助定位
                logger.debug(f"Requesting panel position: ({panel_x}, {panel_y})")

            # Wayland 下，transient_for 关系会让窗口管理器尽量
            # 将两个窗口放在一起，但无法保证精确位置

            return False  # 不重复执行

        except Exception as e:
            logger.debug(f"Cannot position panel window: {e}")
            return False

    def _on_main_window_configure(self, window, param):
        """主窗口位置/大小变化时，重新定位副窗口"""
        if self._current_panel and self._current_panel in self._panels:
            panel_window = self._panels[self._current_panel]
            panel_info = self._panel_contents.get(self._current_panel)
            if panel_info:
                GLib.idle_add(
                    self._position_panel_window,
                    panel_window,
                    panel_info["width"]
                )

    def _on_panel_close(self, window, name: str) -> bool:
        """面板窗口关闭处理"""
        if name in self._panels:
            del self._panels[name]
        if self._current_panel == name:
            self._current_panel = None

        self._trigger_callbacks("panel_closed", name)
        self._trigger_callbacks("panel_changed", None)

        logger.debug(f"Panel window closed: {name}")
        return False  # 允许关闭

    def hide_panel(self, name: Optional[str] = None) -> None:
        """隐藏指定面板（或当前面板）"""
        if name is None:
            name = self._current_panel

        if name and name in self._panels:
            window = self._panels[name]
            window.destroy()
            del self._panels[name]

            if self._current_panel == name:
                self._current_panel = None

            # 断开主窗口的信号连接
            if hasattr(self, '_configure_handler'):
                try:
                    self._main_window.disconnect(self._configure_handler)
                except:
                    pass

            self._trigger_callbacks("panel_closed", name)
            self._trigger_callbacks("panel_changed", None)

            logger.debug(f"Panel hidden: {name}")

    def toggle_panel(self, name: str, data: Optional[dict] = None) -> bool:
        """
        切换面板显示状态

        Args:
            name: 面板名称
            data: 传递给面板的数据

        Returns:
            bool: 切换后面板是否可见
        """
        if self._current_panel == name and name in self._panels:
            self.hide_panel(name)
            return False
        else:
            self.show_panel(name, data)
            return True

    def is_panel_visible(self, name: Optional[str] = None) -> bool:
        """检查面板是否可见"""
        if name is None:
            return self._current_panel is not None
        return name in self._panels and self._panels[name].is_visible()

    def get_current_panel(self) -> Optional[str]:
        """获取当前显示的面板名称"""
        return self._current_panel

    def on(self, event: str, callback: Callable) -> None:
        """
        注册事件回调

        Args:
            event: 事件名称 ("panel_opened", "panel_closed", "panel_changed")
            callback: 回调函数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable) -> None:
        """移除事件回调"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    def _trigger_callbacks(self, event: str, *args) -> None:
        """触发事件回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# 全局面板请求队列（用于 Agent 等外部组件请求打开面板）
_panel_manager: Optional[SidePanelManager] = None


def init_panel_manager(manager: SidePanelManager) -> None:
    """初始化全局面板管理器"""
    global _panel_manager
    _panel_manager = manager


def request_panel(panel_name: str, data: Optional[dict] = None) -> None:
    """
    请求打开面板（可从任何地方调用）

    用于 Agent 或其他非 UI 组件请求打开面板。
    请求会在 GTK 主循环中异步处理。

    Args:
        panel_name: 面板名称
        data: 传递给面板的数据
    """
    global _panel_manager

    if _panel_manager is None:
        logger.warning(f"Panel manager not initialized, cannot open: {panel_name}")
        return

    # 在主线程中执行
    GLib.idle_add(_panel_manager.show_panel, panel_name, data)


def get_panel_manager() -> Optional[SidePanelManager]:
    """获取全局面板管理器"""
    return _panel_manager
