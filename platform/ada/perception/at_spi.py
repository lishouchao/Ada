"""
AT-SPI Monitor - Accessibility-based UI perception
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import AT-SPI
try:
    import pyatspi
    ATSPI_AVAILABLE = True
except ImportError:
    ATSPI_AVAILABLE = False
    logger.warning("pyatspi not available, UI perception disabled")


@dataclass
class UIElement:
    """
    Represents a UI element from AT-SPI.

    Captures all accessibility properties of a widget.
    """
    role: str                          # ATK role name
    name: str                          # Accessible name
    description: str                   # Accessible description
    path: str                          # D-Bus object path
    bounds: Optional[Dict[str, int]]   # x, y, width, height
    state: List[str]                   # State set
    children: List["UIElement"] = field(default_factory=list)
    parent_path: Optional[str] = None
    application: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    text_content: Optional[str] = None
    is_focusable: bool = False
    is_focused: bool = False
    is_visible: bool = True
    is_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "role": self.role,
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "bounds": self.bounds,
            "state": self.state,
            "children": [c.to_dict() for c in self.children],
            "parent_path": self.parent_path,
            "application": self.application,
            "attributes": self.attributes,
            "text_content": self.text_content,
            "is_focusable": self.is_focusable,
            "is_focused": self.is_focused,
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
        }

    def find_by_role(self, role: str) -> List["UIElement"]:
        """Find all descendants with given role"""
        results = []
        for child in self.children:
            if child.role == role:
                results.append(child)
            results.extend(child.find_by_role(role))
        return results

    def find_by_name(self, name: str) -> List["UIElement"]:
        """Find all descendants with given name"""
        results = []
        for child in self.children:
            if name.lower() in child.name.lower():
                results.append(child)
            results.extend(child.find_by_name(name))
        return results

    def find_clickable(self) -> List["UIElement"]:
        """Find all clickable elements"""
        clickable_roles = [
            "push button", "toggle button", "check box",
            "radio button", "menu item", "link"
        ]
        results = []
        for child in self.children:
            if child.role in clickable_roles and child.is_enabled:
                results.append(child)
            results.extend(child.find_clickable())
        return results


@dataclass
class UITree:
    """
    Complete UI tree snapshot.

    Represents the entire accessible UI hierarchy.
    """
    root: UIElement
    timestamp: float
    focused_element: Optional[str] = None
    active_window: Optional[str] = None

    def find_element(self, path: str) -> Optional[UIElement]:
        """Find element by path"""
        def search(element: UIElement) -> Optional[UIElement]:
            if element.path == path:
                return element
            for child in element.children:
                result = search(child)
                if result:
                    return result
            return None
        return search(self.root)

    def get_focused(self) -> Optional[UIElement]:
        """Get currently focused element"""
        if not self.focused_element:
            return None
        return self.find_element(self.focused_element)

    def find_all(self, role: str = None, name: str = None) -> List[UIElement]:
        """Find all elements matching criteria"""
        results = []
        def search(element: UIElement):
            match = True
            if role and element.role != role:
                match = False
            if name and name.lower() not in element.name.lower():
                match = False
            if match:
                results.append(element)
            for child in element.children:
                search(child)
        search(self.root)
        return results


class ATSPIMonitor:
    """
    Monitor UI changes via AT-SPI.

    Provides real-time perception of the desktop UI through
    accessibility infrastructure.
    """

    def __init__(self):
        self._registry = None
        self._event_handlers: List[Callable] = []
        self._running = False

    @property
    def is_available(self) -> bool:
        """Check if AT-SPI is available"""
        return ATSPI_AVAILABLE

    async def initialize(self) -> bool:
        """Initialize AT-SPI connection"""
        if not ATSPI_AVAILABLE:
            logger.error("AT-SPI not available")
            return False

        try:
            self._registry = pyatspi.Registry.getDesktop(0)
            logger.info("AT-SPI initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AT-SPI: {e}")
            return False

    async def get_tree(self, app_name: str = None) -> Optional[UITree]:
        """
        Get the current UI tree.

        Args:
            app_name: Optional filter to specific application

        Returns:
            UITree snapshot or None if unavailable
        """
        if not self._registry:
            return None

        import time

        try:
            # Get focused element
            focused_path = await self._get_focused_element_path()

            # Get active window
            active_window = await self._get_active_window_path()

            # Build tree from desktop
            root = await self._build_element_tree(
                self._registry,
                parent_path=None,
                filter_app=app_name
            )

            if root:
                return UITree(
                    root=root,
                    timestamp=time.time(),
                    focused_element=focused_path,
                    active_window=active_window,
                )

        except Exception as e:
            logger.error(f"Error getting UI tree: {e}")

        return None

    async def _build_element_tree(
        self,
        accessible,
        parent_path: Optional[str],
        filter_app: str = None,
        depth: int = 0
    ) -> Optional[UIElement]:
        """Recursively build UI element tree"""
        if depth > 50:  # Prevent infinite recursion
            return None

        try:
            # Get basic properties
            role = accessible.getRoleName()
            name = accessible.name or ""
            description = accessible.description or ""

            # Get path
            try:
                path = accessible.path
            except:
                path = f"/unknown/{id(accessible)}"

            # Check app filter
            app_name = ""
            try:
                app = accessible.getApplication()
                if app:
                    app_name = app.name or ""
                    if filter_app and filter_app.lower() not in app_name.lower():
                        return None
            except:
                pass

            # Get bounds
            bounds = None
            try:
                component = accessible.queryComponent()
                if component:
                    rect = component.getExtents(0)  # SCREEN_COORDS
                    bounds = {
                        "x": rect.x,
                        "y": rect.y,
                        "width": rect.width,
                        "height": rect.height,
                    }
            except:
                pass

            # Get state
            state = []
            try:
                state_set = accessible.getState()
                state = [s.name for s in state_set.states]
            except:
                pass

            # Get text content
            text_content = None
            try:
                text = accessible.queryText()
                if text:
                    text_content = text.getText(0, text.characterCount)
            except:
                pass

            # Get attributes
            attributes = {}
            try:
                attrs = accessible.getAttributes()
                for attr in attrs:
                    if ":" in attr:
                        key, value = attr.split(":", 1)
                        attributes[key] = value
            except:
                pass

            # Create element
            element = UIElement(
                role=role,
                name=name,
                description=description,
                path=path,
                bounds=bounds,
                state=state,
                parent_path=parent_path,
                application=app_name,
                attributes=attributes,
                text_content=text_content,
                is_focusable="focusable" in state,
                is_focused="focused" in state,
                is_visible="visible" in state,
                is_enabled="enabled" in state,
            )

            # Process children
            try:
                for i in range(accessible.childCount):
                    child = accessible.getChildAtIndex(i)
                    child_element = await self._build_element_tree(
                        child, path, filter_app, depth + 1
                    )
                    if child_element:
                        element.children.append(child_element)
            except:
                pass

            return element

        except Exception as e:
            logger.debug(f"Error building element: {e}")
            return None

    async def _get_focused_element_path(self) -> Optional[str]:
        """Get path of currently focused element"""
        if not self._registry:
            return None

        try:
            # Search for focused element
            for app in self._registry:
                focused = self._find_focused(app)
                if focused:
                    try:
                        return focused.path
                    except:
                        return None
        except:
            pass

        return None

    def _find_focused(self, accessible):
        """Recursively find focused element"""
        try:
            state = accessible.getState()
            if state.contains(pyatspi.STATE_FOCUSED):
                return accessible

            for i in range(accessible.childCount):
                child = accessible.getChildAtIndex(i)
                result = self._find_focused(child)
                if result:
                    return result
        except:
            pass

        return None

    async def _get_active_window_path(self) -> Optional[str]:
        """Get path of active window"""
        if not self._registry:
            return None

        try:
            for app in self._registry:
                for i in range(app.childCount):
                    window = app.getChildAtIndex(i)
                    try:
                        state = window.getState()
                        if state.contains(pyatspi.STATE_ACTIVE):
                            return window.path
                    except:
                        pass
        except:
            pass

        return None

    def on_event(self, callback: Callable):
        """Register for UI events"""
        self._event_handlers.append(callback)

    async def start_monitoring(self):
        """Start monitoring UI events"""
        if not ATSPI_AVAILABLE or not self._registry:
            return

        self._running = True

        # Register for relevant events
        events = [
            "focus:",
            "window:activate",
            "window:deactivate",
            "object:state-changed",
        ]

        for event in events:
            try:
                pyatspi.Registry.registerListener(self._handle_event, event)
            except Exception as e:
                logger.error(f"Failed to register event {event}: {e}")

        logger.info("Started AT-SPI monitoring")

    async def stop_monitoring(self):
        """Stop monitoring UI events"""
        self._running = False

        if ATSPI_AVAILABLE:
            try:
                pyatspi.Registry.deregisterListener(self._handle_event, "focus:")
                pyatspi.Registry.deregisterListener(self._handle_event, "window:")
                pyatspi.Registry.deregisterListener(self._handle_event, "object:")
            except:
                pass

        logger.info("Stopped AT-SPI monitoring")

    def _handle_event(self, event):
        """Handle AT-SPI event"""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
