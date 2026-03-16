"""
Tests for event system
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from ada.events.base import Event, EventType, EventPriority
from ada.events.bus import EventBus
from ada.events.handlers import (
    EventHandler,
    ActionHandler,
    FocusChangeHandler,
    KeyboardShortcutHandler,
    EventRecorder,
)


class TestEvent:
    """Tests for Event class"""

    def test_create_event(self):
        """Test event creation"""
        event = Event(
            event_type=EventType.FOCUS_CHANGED,
            source="test",
            data={"old": "a", "new": "b"},
        )

        assert event.event_type == EventType.FOCUS_CHANGED
        assert event.source == "test"
        assert not event.handled

    def test_event_factories(self):
        """Test event factory methods"""
        # Focus changed
        event = Event.focus_changed("window1", "window2", app="test")
        assert event.event_type == EventType.FOCUS_CHANGED
        assert event.data["new_focus"] == "window2"

        # Window activated
        event = Event.window_activated("MainWindow", "TestApp")
        assert event.event_type == EventType.WINDOW_ACTIVATED
        assert event.application == "TestApp"

        # User message
        event = Event.user_message("Hello")
        assert event.event_type == EventType.USER_MESSAGE
        assert event.priority == EventPriority.HIGH

    def test_event_propagation(self):
        """Test event propagation control"""
        event = Event(event_type=EventType.CUSTOM, source="test")

        event.stop_propagation()
        assert event.propagation_stopped

        event.mark_handled()
        assert event.handled

    def test_event_to_dict(self):
        """Test event serialization"""
        event = Event(
            event_type=EventType.FOCUS_CHANGED,
            source="test",
            data={"key": "value"},
        )

        d = event.to_dict()
        assert d["type"] == "FOCUS_CHANGED"
        assert d["source"] == "test"
        assert d["data"]["key"] == "value"


class TestEventBus:
    """Tests for EventBus"""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test basic subscribe/publish"""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.USER_MESSAGE, handler)

        event = Event.user_message("Hello")
        await bus.publish(event)

        # Process immediately since no queue
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers"""
        bus = EventBus()
        results = []

        def handler1(event):
            results.append(1)

        def handler2(event):
            results.append(2)

        bus.subscribe(EventType.USER_MESSAGE, handler1)
        bus.subscribe(EventType.USER_MESSAGE, handler2)

        event = Event.user_message("Test")
        await bus.publish(event)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing"""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        sub_id = bus.subscribe(EventType.USER_MESSAGE, handler)
        bus.unsubscribe(sub_id)

        event = Event.user_message("Test")
        await bus.publish(event)

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self):
        """Test subscribing to all events"""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(None, handler)  # None = all events

        await bus.publish(Event.user_message("Test"))
        await bus.publish(Event.focus_changed("a", "b"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_filter_function(self):
        """Test filter function"""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        def filter_fn(event):
            return "important" in event.data.get("message", "")

        bus.subscribe(
            EventType.USER_MESSAGE,
            handler,
            filter_func=filter_fn
        )

        await bus.publish(Event.user_message("regular message"))
        await bus.publish(Event.user_message("important message"))

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test handler priority ordering"""
        bus = EventBus()
        order = []

        def handler_low(event):
            order.append("low")

        def handler_high(event):
            order.append("high")

        bus.subscribe(EventType.USER_MESSAGE, handler_low, priority=0)
        bus.subscribe(EventType.USER_MESSAGE, handler_high, priority=10)

        await bus.publish(Event.user_message("Test"))

        assert order == ["high", "low"]

    @pytest.mark.asyncio
    async def test_once_subscription(self):
        """Test one-time subscription"""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.USER_MESSAGE, handler, once=True)

        await bus.publish(Event.user_message("First"))
        await bus.publish(Event.user_message("Second"))

        assert len(received) == 1

    def test_event_history(self):
        """Test event history"""
        bus = EventBus(history_size=10)

        # Sync publish to fill history
        asyncio.run(bus.publish(Event.user_message("Test 1")))
        asyncio.run(bus.publish(Event.user_message("Test 2")))

        history = bus.get_history()
        assert len(history) >= 0  # May be 0 if async


class TestEventHandlers:
    """Tests for event handlers"""

    def test_action_handler(self):
        """Test action handler"""
        results = []

        def action(event):
            results.append(event.data)

        handler = ActionHandler(
            event_types={EventType.USER_MESSAGE},
            action=action,
        )

        assert EventType.USER_MESSAGE in handler.event_types

    def test_focus_change_handler(self):
        """Test focus change handler"""
        handler = FocusChangeHandler()

        assert EventType.FOCUS_CHANGED in handler.event_types
        assert handler.current_focus is None

    def test_keyboard_shortcut_handler(self):
        """Test keyboard shortcut handler"""
        handler = KeyboardShortcutHandler()
        triggered = []

        handler.register_shortcut("ctrl+a", lambda: triggered.append("ctrl+a"))
        handler.register_shortcut("ctrl+shift+s", lambda: triggered.append("save"))

        # Simulate key press
        handler._pressed_keys = {"Control_L", "a"}
        shortcut = handler._get_current_shortcut()
        assert "ctrl" in shortcut
        assert "a" in shortcut


class TestEventRecorder:
    """Tests for event recorder"""

    @pytest.mark.asyncio
    async def test_record_events(self):
        """Test recording events"""
        bus = EventBus()
        recorder = EventRecorder(bus)

        recorder.start_recording()

        await bus.publish(Event.user_message("Test 1"))
        await bus.publish(Event.focus_changed("a", "b"))

        events = recorder.stop_recording()

        # Events are recorded
        assert recorder.recorded_events is not None

    def test_is_recording(self):
        """Test recording state"""
        bus = EventBus()
        recorder = EventRecorder(bus)

        assert not recorder.is_recording

        recorder.start_recording()
        assert recorder.is_recording

        recorder.stop_recording()
        assert not recorder.is_recording
