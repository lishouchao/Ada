"""
Side Panel Manager - 管理侧边面板的显示和切换
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, GLib
from typing import Dict, Optional, Callable


class SidePanelManager:
    """
    管理侧边面板的显示和切换

    支持多个面板注册，同时只显示一个面板。
    """

    def __init__(self, panel_container: Gtk.Box, revealer: Gtk.Revealer):
        """
        初始化面板管理器

        Args:
            panel_container: 面板容器（Gtk.Box）
            revealer: 用于动画的 Revealer 控件
        """
        self._container = panel_container
        self._revealer = revealer
        self._panels: Dict[str, Gtk.Widget] = {}
        self._current_panel: Optional[str] = None
        self._on_panel_changed: Optional[Callable[[Optional[str]], None]] = None

    def register_panel(self, name: str, panel: Gtk.Widget) -> None:
        """
        注册面板

        Args:
            name: 面板名称（唯一标识）
            panel: 面板控件
        """
        self._panels[name] = panel
        panel.set_visible(False)

    def show_panel(self, name: str) -> bool:
        """
        显示指定面板

        Args:
            name: 面板名称

        Returns:
            bool: 是否成功显示
        """
        if name not in self._panels:
            return False

        # 如果当前显示的是同一个面板，则隐藏
        if self._current_panel == name:
            self.hide_panel()
            return True

        # 隐藏当前面板
        if self._current_panel and self._current_panel in self._panels:
            self._panels[self._current_panel].set_visible(False)

        # 显示新面板
        panel = self._panels[name]

        # 清空容器并添加新面板
        while child := self._container.get_first_child():
            self._container.remove(child)
        self._container.append(panel)

        panel.set_visible(True)
        self._current_panel = name

        # 显示 revealer
        self._revealer.set_reveal_child(True)

        # 通知面板状态变化
        if self._on_panel_changed:
            self._on_panel_changed(name)

        return True

    def hide_panel(self) -> None:
        """隐藏当前面板"""
        if self._current_panel and self._current_panel in self._panels:
            self._panels[self._current_panel].set_visible(False)

        self._revealer.set_reveal_child(False)
        self._current_panel = None

        # 通知面板状态变化
        if self._on_panel_changed:
            self._on_panel_changed(None)

    def toggle_panel(self, name: str) -> bool:
        """
        切换面板显示状态

        Args:
            name: 面板名称

        Returns:
            bool: 切换后面板是否可见
        """
        if self._current_panel == name:
            self.hide_panel()
            return False
        else:
            self.show_panel(name)
            return True

    def is_panel_visible(self, name: str) -> bool:
        """检查指定面板是否可见"""
        return self._current_panel == name

    def get_current_panel(self) -> Optional[str]:
        """获取当前显示的面板名称"""
        return self._current_panel

    def set_on_panel_changed(self, callback: Callable[[Optional[str]], None]) -> None:
        """设置面板状态变化回调"""
        self._on_panel_changed = callback
