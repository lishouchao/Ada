"""
GUI Backend - UI automation via AT-SPI
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ada.platform.execution.backends import ExecutionBackend, BackendResult
from ada.platform.perception.at_spi import ATSPIMonitor, ATSPI_AVAILABLE

logger = logging.getLogger(__name__)


class GUIBackend(ExecutionBackend):
    """
    Execute actions via UI automation.

    Uses AT-SPI to interact with GUI elements when no
    other method is available.
    """

    def __init__(self):
        self._monitor: Optional[ATSPIMonitor] = None

    @property
    def name(self) -> str:
        return "gui"

    @property
    def priority(self) -> int:
        return 40  # Lowest priority, used as last resort

    async def is_available(self) -> bool:
        """Check if AT-SPI is available"""
        return ATSPI_AVAILABLE

    async def initialize(self, monitor: ATSPIMonitor = None) -> bool:
        """Initialize GUI backend with AT-SPI monitor"""
        if not ATSPI_AVAILABLE:
            return False

        self._monitor = monitor or ATSPIMonitor()
        return await self._monitor.initialize()

    async def can_execute(self, action: Dict[str, Any]) -> bool:
        """Check if action can be executed via GUI"""
        if not self._monitor or not ATSPI_AVAILABLE:
            return False

        action_type = action.get("type", "")

        # Supported GUI actions
        gui_actions = [
            "gui.click",
            "gui.type",
            "gui.scroll",
            "gui.focus",
            "gui.activate",
            "gui.select",
            "gui.drag",
        ]

        return action_type in gui_actions

    async def execute(self, action: Dict[str, Any]) -> BackendResult:
        """Execute action via GUI automation"""
        if not self._monitor:
            return BackendResult.fail("GUI backend not initialized", self.name)

        action_type = action.get("type")
        params = action.get("params", {})

        try:
            if action_type == "gui.click":
                return await self._click(params)

            elif action_type == "gui.type":
                return await self._type_text(params)

            elif action_type == "gui.scroll":
                return await self._scroll(params)

            elif action_type == "gui.focus":
                return await self._focus(params)

            elif action_type == "gui.activate":
                return await self._activate(params)

            elif action_type == "gui.select":
                return await self._select(params)

            elif action_type == "gui.drag":
                return await self._drag(params)

            else:
                return BackendResult.fail(f"Unknown GUI action: {action_type}", self.name)

        except Exception as e:
            logger.error(f"GUI execution failed: {e}")
            return BackendResult.fail(str(e), self.name)

    async def _click(self, params: Dict[str, Any]) -> BackendResult:
        """Click on a UI element"""
        element_path = params.get("path")
        element_role = params.get("role")
        element_name = params.get("name")
        coordinates = params.get("coordinates")  # [x, y]

        try:
            if coordinates:
                # Click at specific coordinates
                return await self._click_at_position(*coordinates)

            elif element_path:
                # Click element by path
                return await self._click_element_by_path(element_path)

            elif element_role or element_name:
                # Find and click element
                return await self._find_and_click(element_role, element_name)

            else:
                return BackendResult.fail("No click target specified", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _click_at_position(self, x: int, y: int) -> BackendResult:
        """Click at screen coordinates"""
        # Use ydotool or xdotool
        try:
            import subprocess

            # Try ydotool (Wayland)
            result = subprocess.run(
                ["ydotool", "mousemove", "--absolute", str(x), str(y)],
                capture_output=True
            )
            if result.returncode == 0:
                subprocess.run(["ydotool", "click", "0"], capture_output=True)
                return BackendResult.ok({"clicked": [x, y]}, self.name)

            # Fall back to xdotool (X11)
            result = subprocess.run(
                ["xdotool", "mousemove", str(x), str(y), "click", "1"],
                capture_output=True
            )

            if result.returncode == 0:
                return BackendResult.ok({"clicked": [x, y]}, self.name)

            return BackendResult.fail("Failed to click", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _click_element_by_path(self, path: str) -> BackendResult:
        """Click element by D-Bus path"""
        if not ATSPI_AVAILABLE:
            return BackendResult.fail("AT-SPI not available", self.name)

        try:
            import pyatspi

            # Find element by path
            element = self._find_element_by_path(path)
            if not element:
                return BackendResult.fail(f"Element not found: {path}", self.name)

            # Try Action interface
            try:
                action = element.queryAction()
                if action:
                    # Find click action
                    for i in range(action.nActions):
                        if "click" in action.getName(i).lower():
                            action.doAction(i)
                            return BackendResult.ok({"clicked": path}, self.name)

                    # Try default action
                    if action.nActions > 0:
                        action.doAction(0)
                        return BackendResult.ok({"activated": path}, self.name)

            except:
                pass

            # Fall back to coordinates
            try:
                component = element.queryComponent()
                if component:
                    rect = component.getExtents(0)
                    x = rect.x + rect.width // 2
                    y = rect.y + rect.height // 2
                    return await self._click_at_position(x, y)
            except:
                pass

            return BackendResult.fail(f"Cannot click element: {path}", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _find_and_click(self, role: str, name: str) -> BackendResult:
        """Find element by role/name and click it"""
        tree = await self._monitor.get_tree()
        if not tree:
            return BackendResult.fail("Could not get UI tree", self.name)

        # Find matching elements
        matches = tree.find_all(role=role, name=name)
        if not matches:
            return BackendResult.fail(f"Element not found: role={role}, name={name}", self.name)

        # Click first match
        element = matches[0]
        return await self._click_element_by_path(element.path)

    async def _type_text(self, params: Dict[str, Any]) -> BackendResult:
        """Type text into focused element or specific element"""
        text = params.get("text", "")
        element_path = params.get("path")

        try:
            import subprocess

            # Focus element if specified
            if element_path:
                await self._focus({"path": element_path})
                await asyncio.sleep(0.1)

            # Use ydotool or xdotool
            result = subprocess.run(
                ["ydotool", "type", text],
                capture_output=True
            )

            if result.returncode != 0:
                result = subprocess.run(
                    ["xdotool", "type", text],
                    capture_output=True
                )

            if result.returncode == 0:
                return BackendResult.ok({"typed": text}, self.name)

            return BackendResult.fail("Failed to type text", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _scroll(self, params: Dict[str, Any]) -> BackendResult:
        """Scroll in a direction"""
        direction = params.get("direction", "down")  # up, down, left, right
        amount = params.get("amount", 3)  # Number of scroll steps

        try:
            import subprocess

            button_map = {
                "up": 4,
                "down": 5,
                "left": 6,
                "right": 7,
            }

            button = button_map.get(direction, 5)

            for _ in range(amount):
                subprocess.run(["ydotool", "click", str(button)], capture_output=True)

            return BackendResult.ok({"scrolled": direction}, self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _focus(self, params: Dict[str, Any]) -> BackendResult:
        """Focus a UI element"""
        element_path = params.get("path")

        if not element_path:
            return BackendResult.fail("No element path specified", self.name)

        try:
            element = self._find_element_by_path(element_path)
            if not element:
                return BackendResult.fail(f"Element not found: {element_path}", self.name)

            # Try Component interface
            try:
                component = element.queryComponent()
                if component:
                    component.grabFocus()
                    return BackendResult.ok({"focused": element_path}, self.name)
            except:
                pass

            return BackendResult.fail("Cannot focus element", self.name)

        except Exception as e:
            return BackendResult.fail(str(e), self.name)

    async def _activate(self, params: Dict[str, Any]) -> BackendResult:
        """Activate a UI element (double-click or default action)"""
        element_path = params.get("path")

        if not element_path:
            return BackendResult.fail("No element path specified", self.name)

        # Double-click
        result = await self._click({"path": element_path})
        if not result.success:
            return result

        await asyncio.sleep(0.1)
        return await self._click({"path": element_path})

    async def _select(self, params: Dict[str, Any]) -> BackendResult:
        """Select an item in a list/combobox"""
        element_path = params.get("path")
        item_index = params.get("index")
        item_text = params.get("text")

        # This is complex and depends on the widget type
        # Simplified implementation
        return BackendResult.fail("GUI select not implemented", self.name)

    async def _drag(self, params: Dict[str, Any]) -> BackendResult:
        """Drag from one element/position to another"""
        source = params.get("source")
        target = params.get("target")

        # This requires more complex implementation
        return BackendResult.fail("GUI drag not implemented", self.name)

    def _find_element_by_path(self, path: str):
        """Find AT-SPI element by D-Bus path"""
        if not ATSPI_AVAILABLE:
            return None

        try:
            import pyatspi

            registry = pyatspi.Registry.getDesktop(0)

            def search(accessible, target_path):
                try:
                    if hasattr(accessible, 'path') and accessible.path == target_path:
                        return accessible

                    for i in range(accessible.childCount):
                        result = search(accessible.getChildAtIndex(i), target_path)
                        if result:
                            return result
                except:
                    pass

                return None

            return search(registry, path)

        except Exception as e:
            logger.error(f"Error finding element: {e}")
            return None
