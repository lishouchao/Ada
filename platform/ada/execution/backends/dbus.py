"""
D-Bus Backend - Execute actions via D-Bus
"""

import logging
from typing import Any, Dict, Optional

from ada.platform.execution.backends import ExecutionBackend, BackendResult

logger = logging.getLogger(__name__)

# Try to import D-Bus
try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logger.warning("dbus-python not available, D-Bus backend disabled")


class DBusBackend(ExecutionBackend):
    """
    Execute actions via D-Bus system and session bus.

    Supports:
    - System service calls
    - Session service calls
    - Application control via freedesktop interfaces
    """

    def __init__(self):
        self._system_bus = None
        self._session_bus = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "dbus"

    @property
    def priority(self) -> int:
        return 20  # Second priority after API

    async def is_available(self) -> bool:
        """Check if D-Bus is available"""
        return DBUS_AVAILABLE

    async def initialize(self) -> bool:
        """Initialize D-Bus connections"""
        if not DBUS_AVAILABLE:
            return False

        try:
            self._system_bus = dbus.SystemBus()
            self._session_bus = dbus.SessionBus()
            self._initialized = True
            logger.info("D-Bus backend initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize D-Bus: {e}")
            return False

    async def can_execute(self, action: Dict[str, Any]) -> bool:
        """Check if action can be executed via D-Bus"""
        if not self._initialized:
            return False

        action_type = action.get("type", "")

        # Supported D-Bus actions
        dbus_actions = [
            "app.launch",
            "app.switch",
            "app.close",
            "system.shutdown",
            "system.reboot",
            "system.suspend",
            "media.play",
            "media.pause",
            "media.next",
            "media.previous",
            "notification.show",
            "clipboard.set",
            "clipboard.get",
        ]

        return action_type in dbus_actions

    async def execute(self, action: Dict[str, Any]) -> BackendResult:
        """Execute action via D-Bus"""
        if not self._initialized:
            return BackendResult.fail("D-Bus not initialized", self.name)

        action_type = action.get("type")
        params = action.get("params", {})

        try:
            if action_type == "app.launch":
                return await self._launch_app(params)

            elif action_type == "app.switch":
                return await self._switch_app(params)

            elif action_type == "app.close":
                return await self._close_app(params)

            elif action_type == "system.shutdown":
                return await self._system_power("Shutdown")

            elif action_type == "system.reboot":
                return await self._system_power("Reboot")

            elif action_type == "system.suspend":
                return await self._system_power("Suspend")

            elif action_type == "notification.show":
                return await self._show_notification(params)

            elif action_type == "clipboard.set":
                return await self._set_clipboard(params)

            elif action_type == "clipboard.get":
                return await self._get_clipboard()

            elif action_type.startswith("media."):
                return await self._media_control(action_type, params)

            else:
                return BackendResult.fail(f"Unknown D-Bus action: {action_type}", self.name)

        except Exception as e:
            logger.error(f"D-Bus execution failed: {e}")
            return BackendResult.fail(str(e), self.name)

    async def _launch_app(self, params: Dict[str, Any]) -> BackendResult:
        """Launch application via .desktop file"""
        app_name = params.get("name")
        if not app_name:
            return BackendResult.fail("No app name specified", self.name)

        try:
            # Try to launch via Gio (GNOME)
            import subprocess
            result = subprocess.run(
                ["gtk-launch", app_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return BackendResult.ok({"launched": app_name}, self.name)
            else:
                # Fallback to exec
                result = subprocess.run(
                    ["nohup", app_name, "&"],
                    shell=True,
                    capture_output=True
                )
                if result.returncode == 0:
                    return BackendResult.ok({"launched": app_name}, self.name)

            return BackendResult.fail(f"Failed to launch {app_name}", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _switch_app(self, params: Dict[str, Any]) -> BackendResult:
        """Switch to application window"""
        app_name = params.get("name")
        if not app_name:
            return BackendResult.fail("No app name specified", self.name)

        try:
            # Use wmctrl to switch windows
            import subprocess
            result = subprocess.run(
                ["wmctrl", "-a", app_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return BackendResult.ok({"switched": app_name}, self.name)

            return BackendResult.fail(f"Failed to switch to {app_name}", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _close_app(self, params: Dict[str, Any]) -> BackendResult:
        """Close application"""
        app_name = params.get("name")
        if not app_name:
            return BackendResult.fail("No app name specified", self.name)

        try:
            import subprocess
            result = subprocess.run(
                ["wmctrl", "-c", app_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return BackendResult.ok({"closed": app_name}, self.name)

            return BackendResult.fail(f"Failed to close {app_name}", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _system_power(self, action: str) -> BackendResult:
        """Execute system power action"""
        try:
            # Use logind via D-Bus
            proxy = self._system_bus.get_object(
                'org.freedesktop.login1',
                '/org/freedesktop/login1'
            )
            interface = dbus.Interface(proxy, 'org.freedesktop.login1.Manager')

            if action == "Shutdown":
                interface.PowerOff(False)
            elif action == "Reboot":
                interface.Reboot(False)
            elif action == "Suspend":
                interface.Suspend(False)

            return BackendResult.ok({"action": action}, self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _show_notification(self, params: Dict[str, Any]) -> BackendResult:
        """Show desktop notification"""
        title = params.get("title", "Ada")
        message = params.get("message", "")
        timeout = params.get("timeout", 5000)

        try:
            proxy = self._session_bus.get_object(
                'org.freedesktop.Notifications',
                '/org/freedesktop/Notifications'
            )
            interface = dbus.Interface(proxy, 'org.freedesktop.Notifications')

            interface.Notify(
                "Ada",
                0,
                params.get("icon", "dialog-information"),
                title,
                message,
                [],
                {},
                timeout
            )

            return BackendResult.ok({"notified": True}, self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _set_clipboard(self, params: Dict[str, Any]) -> BackendResult:
        """Set clipboard content"""
        content = params.get("content", "")
        selection = params.get("selection", "clipboard")

        try:
            # Use xclip or wl-copy
            import subprocess

            # Try Wayland first
            result = subprocess.run(
                ["wl-copy"],
                input=content.encode(),
                capture_output=True
            )

            if result.returncode != 0:
                # Fall back to X11
                result = subprocess.run(
                    ["xclip", "-selection", selection],
                    input=content.encode(),
                    capture_output=True
                )

            if result.returncode == 0:
                return BackendResult.ok({"clipboard": "set"}, self.name)

            return BackendResult.fail("Failed to set clipboard", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _get_clipboard(self) -> BackendResult:
        """Get clipboard content"""
        try:
            import subprocess

            # Try Wayland first
            result = subprocess.run(
                ["wl-paste"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Fall back to X11
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True
                )

            if result.returncode == 0:
                return BackendResult.ok({"content": result.stdout}, self.name)

            return BackendResult.fail("Failed to get clipboard", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _media_control(self, action: str, params: Dict[str, Any]) -> BackendResult:
        """Control media playback"""
        try:
            # Try MPRIS D-Bus interface
            proxy = self._session_bus.get_object(
                'org.mpris.MediaPlayer2.*',
                '/org/mpris/MediaPlayer2'
            )
            interface = dbus.Interface(proxy, 'org.mpris.MediaPlayer2.Player')

            if action == "media.play":
                interface.Play()
            elif action == "media.pause":
                interface.Pause()
            elif action == "media.next":
                interface.Next()
            elif action == "media.previous":
                interface.Previous()

            return BackendResult.ok({"action": action}, self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)
