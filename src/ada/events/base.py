"""
Event Base - Core event definitions and types
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional, Callable
import uuid


class EventType(Enum):
    """Types of events Ada can respond to"""
    # AT-SPI events
    FOCUS_CHANGED = auto()          # Window/widget focus changed
    WINDOW_ACTIVATED = auto()       # Window activated
    WINDOW_DEACTIVATED = auto()     # Window deactivated
    WINDOW_OPENED = auto()          # New window opened
    WINDOW_CLOSED = auto()          # Window closed
    WINDOW_MOVED = auto()           # Window moved/resized

    # State changes
    STATE_CHANGED = auto()          # Widget state changed
    VISIBLE_DATA_CHANGED = auto()   # Visible content changed
    TEXT_CHANGED = auto()           # Text content changed
    SELECTION_CHANGED = auto()      # Selection changed

    # User actions
    KEY_PRESSED = auto()            # Key pressed
    KEY_RELEASED = auto()           # Key released
    MOUSE_CLICKED = auto()          # Mouse click
    MOUSE_MOVED = auto()            # Mouse movement

    # System events
    SCREENSHOT_TAKEN = auto()       # Screenshot captured
    CLIPBOARD_CHANGED = auto()      # Clipboard content changed
    NOTIFICATION_RECEIVED = auto()  # Desktop notification

    # Application events
    APP_LAUNCHED = auto()           # Application launched
    APP_TERMINATED = auto()         # Application terminated
    APP_RESPONSE = auto()           # Application responded

    # Ada internal events
    AGENT_STARTED = auto()          # Agent started
    AGENT_STOPPED = auto()          # Agent stopped
    SKILL_EXECUTED = auto()         # Skill executed
    MEMORY_UPDATED = auto()         # Memory updated
    USER_MESSAGE = auto()           # User sent message
    AGENT_RESPONSE = auto()         # Agent responded

    # Custom
    CUSTOM = auto()                 # Custom event type


class EventPriority(Enum):
    """Event processing priority"""
    CRITICAL = 0    # Process immediately, block others
    HIGH = 1        # Process before normal
    NORMAL = 2      # Standard priority
    LOW = 3         # Process after normal
    BACKGROUND = 4  # Process when idle


@dataclass
class Event:
    """
    A single event in the system.

    Events represent state changes or actions that Ada can respond to.
    """
    event_type: EventType
    source: str                     # Event source identifier
    data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    handled: bool = False
    propagation_stopped: bool = False

    # Source details
    application: Optional[str] = None
    window: Optional[str] = None
    widget: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def stop_propagation(self):
        """Stop event from being processed by more handlers"""
        self.propagation_stopped = True

    def mark_handled(self):
        """Mark event as handled"""
        self.handled = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.event_type.name,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.name,
            "handled": self.handled,
            "application": self.application,
            "window": self.window,
            "widget": self.widget,
            "metadata": self.metadata,
        }

    @classmethod
    def focus_changed(cls, old_focus: str, new_focus: str, app: str = None) -> "Event":
        """Create focus changed event"""
        return cls(
            event_type=EventType.FOCUS_CHANGED,
            source="at-spi",
            data={"old_focus": old_focus, "new_focus": new_focus},
            application=app,
        )

    @classmethod
    def window_activated(cls, window: str, app: str) -> "Event":
        """Create window activated event"""
        return cls(
            event_type=EventType.WINDOW_ACTIVATED,
            source="at-spi",
            data={},
            window=window,
            application=app,
        )

    @classmethod
    def text_changed(cls, text: str, widget: str, app: str = None) -> "Event":
        """Create text changed event"""
        return cls(
            event_type=EventType.TEXT_CHANGED,
            source="at-spi",
            data={"text": text},
            widget=widget,
            application=app,
        )

    @classmethod
    def clipboard_changed(cls, content: str, content_type: str = "text") -> "Event":
        """Create clipboard changed event"""
        return cls(
            event_type=EventType.CLIPBOARD_CHANGED,
            source="system",
            data={"content": content[:1000], "type": content_type},  # Limit size
        )

    @classmethod
    def user_message(cls, message: str) -> "Event":
        """Create user message event"""
        return cls(
            event_type=EventType.USER_MESSAGE,
            source="user",
            data={"message": message},
            priority=EventPriority.HIGH,
        )

    @classmethod
    def agent_response(cls, response: str, skill_used: str = None) -> "Event":
        """Create agent response event"""
        return cls(
            event_type=EventType.AGENT_RESPONSE,
            source="agent",
            data={"response": response, "skill": skill_used},
        )

    @classmethod
    def custom(cls, name: str, data: Dict[str, Any], source: str = "custom") -> "Event":
        """Create custom event"""
        return cls(
            event_type=EventType.CUSTOM,
            source=source,
            data={"name": name, **data},
        )
