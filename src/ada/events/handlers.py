"""
Event Handlers - Pre-built event handlers for common use cases
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from ada.events.base import Event, EventType, EventPriority
from ada.events.bus import EventBus

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Abstract base for event handlers.

    Handlers provide a structured way to respond to events.
    """

    @property
    @abstractmethod
    def event_types(self) -> Set[EventType]:
        """Event types this handler processes"""
        pass

    @property
    def priority(self) -> int:
        """Handler priority (higher = first)"""
        return 0

    @property
    def filter_func(self) -> Optional[Callable[[Event], bool]]:
        """Optional event filter"""
        return None

    @abstractmethod
    async def handle(self, event: Event) -> bool:
        """
        Handle the event.

        Args:
            event: Event to handle

        Returns:
            True if event was handled, False to continue propagation
        """
        pass

    def register(self, bus: EventBus) -> str:
        """Register this handler with an event bus"""
        return bus.subscribe(
            list(self.event_types),
            self.handle,
            filter_func=self.filter_func,
            priority=self.priority
        )


class ActionHandler(EventHandler):
    """
    Handler that triggers actions based on events.

    Useful for simple event-to-action mappings.
    """

    def __init__(
        self,
        event_types: Set[EventType],
        action: Callable[[Event], Any],
        condition: Callable[[Event], bool] = None,
        priority: int = 0
    ):
        self._event_types = event_types
        self._action = action
        self._condition = condition
        self._priority = priority

    @property
    def event_types(self) -> Set[EventType]:
        return self._event_types

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def filter_func(self) -> Optional[Callable[[Event], bool]]:
        return self._condition

    async def handle(self, event: Event) -> bool:
        try:
            result = self._action(event)
            if asyncio.iscoroutine(result):
                await result
            return True
        except Exception as e:
            logger.error(f"Action handler error: {e}")
            return False


class WindowChangeHandler(EventHandler):
    """
    Handler for window activation changes.

    Triggers when the active window changes.
    """

    @property
    def event_types(self) -> Set[EventType]:
        return {EventType.WINDOW_ACTIVATED, EventType.WINDOW_DEACTIVATED}

    @property
    def priority(self) -> int:
        return 5

    async def handle(self, event: Event) -> bool:
        window = event.window
        app = event.application

        if event.event_type == EventType.WINDOW_ACTIVATED:
            logger.info(f"Window activated: {window} ({app})")
            # Could trigger context update, UI perception, etc.

        elif event.event_type == EventType.WINDOW_DEACTIVATED:
            logger.debug(f"Window deactivated: {window}")

        return False  # Allow other handlers


class FocusChangeHandler(EventHandler):
    """
    Handler for focus changes.

    Tracks which widget has focus.
    """

    def __init__(self):
        self._current_focus: Optional[str] = None
        self._focus_history: List[str] = []

    @property
    def event_types(self) -> Set[EventType]:
        return {EventType.FOCUS_CHANGED}

    @property
    def priority(self) -> int:
        return 10

    @property
    def current_focus(self) -> Optional[str]:
        return self._current_focus

    async def handle(self, event: Event) -> bool:
        old_focus = event.data.get("old_focus")
        new_focus = event.data.get("new_focus")

        self._current_focus = new_focus
        self._focus_history.append(new_focus)

        # Keep history limited
        if len(self._focus_history) > 100:
            self._focus_history.pop(0)

        logger.debug(f"Focus: {old_focus} -> {new_focus}")
        return False


class ClipboardHandler(EventHandler):
    """
    Handler for clipboard changes.

    Can monitor and optionally process clipboard content.
    """

    def __init__(self, process_func: Callable[[str], Any] = None):
        self._process_func = process_func
        self._last_content: Optional[str] = None

    @property
    def event_types(self) -> Set[EventType]:
        return {EventType.CLIPBOARD_CHANGED}

    @property
    def last_content(self) -> Optional[str]:
        return self._last_content

    async def handle(self, event: Event) -> bool:
        content = event.data.get("content", "")
        content_type = event.data.get("type", "text")

        self._last_content = content

        if self._process_func and content_type == "text":
            try:
                result = self._process_func(content)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Clipboard processing error: {e}")

        return False


class KeyboardShortcutHandler(EventHandler):
    """
    Handler for keyboard shortcuts.

    Triggers actions when specific key combinations are pressed.
    """

    def __init__(self):
        self._shortcuts: Dict[str, Callable] = {}
        self._pressed_keys: Set[str] = set()

    @property
    def event_types(self) -> Set[EventType]:
        return {EventType.KEY_PRESSED, EventType.KEY_RELEASED}

    @property
    def priority(self) -> int:
        return 100  # High priority for shortcuts

    def register_shortcut(
        self,
        keys: str,  # e.g., "Ctrl+Shift+A"
        action: Callable[[], Any]
    ):
        """Register a keyboard shortcut"""
        self._shortcuts[keys.lower()] = action

    def unregister_shortcut(self, keys: str):
        """Unregister a keyboard shortcut"""
        self._shortcuts.pop(keys.lower(), None)

    async def handle(self, event: Event) -> bool:
        key = event.data.get("key", "")

        if event.event_type == EventType.KEY_PRESSED:
            self._pressed_keys.add(key)

            # Check for shortcut match
            shortcut = self._get_current_shortcut()
            if shortcut in self._shortcuts:
                action = self._shortcuts[shortcut]
                try:
                    result = action()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Shortcut action error: {e}")

                event.stop_propagation()
                return True

        elif event.event_type == EventType.KEY_RELEASED:
            self._pressed_keys.discard(key)

        return False

    def _get_current_shortcut(self) -> str:
        """Get current key combination as shortcut string"""
        modifiers = []
        keys = []

        for key in self._pressed_keys:
            if key in ("Control_L", "Control_R"):
                modifiers.append("Ctrl")
            elif key in ("Shift_L", "Shift_R"):
                modifiers.append("Shift")
            elif key in ("Alt_L", "Alt_R"):
                modifiers.append("Alt")
            elif key in ("Super_L", "Super_R"):
                modifiers.append("Super")
            else:
                keys.append(key)

        parts = modifiers + keys
        return "+".join(parts).lower()


class EventRecorder:
    """
    Records events for later playback or analysis.

    Useful for automation and testing.
    """

    def __init__(self, bus: EventBus):
        self.bus = bus
        self._recording: List[Event] = []
        self._is_recording = False
        self._subscription_id = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def recorded_events(self) -> List[Event]:
        return list(self._recording)

    def start_recording(self, event_types: List[EventType] = None):
        """Start recording events"""
        if self._is_recording:
            return

        self._recording.clear()
        self._is_recording = True

        def record_event(event: Event):
            self._recording.append(event)

        self._subscription_id = self.bus.subscribe(
            event_types,
            record_event,
            priority=-100  # Low priority to capture everything
        )

        logger.info(f"Started recording events: {event_types}")

    def stop_recording(self) -> List[Event]:
        """Stop recording and return recorded events"""
        if not self._is_recording:
            return []

        self._is_recording = False

        if self._subscription_id:
            self.bus.unsubscribe(self._subscription_id)
            self._subscription_id = None

        logger.info(f"Stopped recording. Captured {len(self._recording)} events")
        return list(self._recording)

    async def replay(self, events: List[Event] = None, delay: float = 0.1):
        """Replay recorded events"""
        events = events or self._recording

        for event in events:
            await self.bus.publish(event)
            await asyncio.sleep(delay)
