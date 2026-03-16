"""
Intent Base - Core intent and entity structures
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class IntentCategory(Enum):
    """Categories of intents"""
    SYSTEM = "system"           # System control (shutdown, settings)
    FILE = "file"               # File operations
    APPLICATION = "application" # App launch/switch
    INFORMATION = "information" # Queries and search
    COMMUNICATION = "communication"  # Messages, email
    AUTOMATION = "automation"   # Workflows, scripts
    SCHEDULE = "schedule"       # Reminders, calendar
    UNKNOWN = "unknown"         # Unrecognized intent


@dataclass
class Entity:
    """
    Extracted entity from user input.

    Entities represent specific pieces of information like
    file paths, app names, dates, etc.
    """
    type: str                   # Entity type (app, path, date, etc.)
    value: Any                  # Extracted value
    raw_text: str               # Original text from input
    start: int                  # Start position in input
    end: int                    # End position in input
    confidence: float = 1.0     # Extraction confidence
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "value": self.value,
            "raw_text": self.raw_text,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Intent:
    """
    Parsed user intent.

    Represents what the user wants to do, including
    the action, entities, and confidence scores.
    """
    name: str                           # Intent name (e.g., "file.open")
    category: IntentCategory            # Intent category
    action: str                         # Action type (open, delete, move, etc.)
    entities: Dict[str, Entity]         # Extracted entities
    raw_input: str                      # Original user input
    confidence: float = 1.0             # Overall confidence
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requires_confirmation: bool = False  # Destructive action flag
    skill_hints: List[str] = field(default_factory=list)  # Suggested skills

    def get_entity(self, name: str) -> Optional[Entity]:
        """Get entity by name"""
        return self.entities.get(name)

    def get_entity_value(self, name: str, default: Any = None) -> Any:
        """Get entity value by name"""
        entity = self.entities.get(name)
        return entity.value if entity else default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "action": self.action,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "raw_input": self.raw_input,
            "confidence": self.confidence,
            "requires_confirmation": self.requires_confirmation,
            "skill_hints": self.skill_hints,
        }


@dataclass
class IntentResult:
    """
    Result of intent parsing.

    Contains the parsed intent(s) and any parsing metadata.
    """
    intent: Optional[Intent]             # Primary intent
    alternatives: List[Intent] = field(default_factory=list)  # Alternative interpretations
    entities: List[Entity] = field(default_factory=list)      # All extracted entities
    parsing_time_ms: float = 0.0         # Time taken to parse
    parser_version: str = "1.0.0"        # Parser version used

    @property
    def has_intent(self) -> bool:
        """Check if an intent was successfully parsed"""
        return self.intent is not None

    @property
    def best_confidence(self) -> float:
        """Get the highest confidence score"""
        if self.intent:
            return self.intent.confidence
        if self.alternatives:
            return max(i.confidence for i in self.alternatives)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.to_dict() if self.intent else None,
            "alternatives": [i.to_dict() for i in self.alternatives],
            "entities": [e.to_dict() for e in self.entities],
            "parsing_time_ms": self.parsing_time_ms,
            "parser_version": self.parser_version,
        }
