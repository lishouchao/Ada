"""
Memory Base - Core memory data structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MemoryType(Enum):
    """Types of memories"""
    EPISODIC = "episodic"       # Events and experiences
    SEMANTIC = "semantic"       # Facts and knowledge
    PROCEDURAL = "procedural"   # Skills and procedures
    WORKING = "working"         # Temporary working memory
    CONVERSATION = "conversation"  # Chat history


@dataclass
class Memory:
    """
    A single memory entry.

    Memories are the fundamental unit of storage in Ada's memory system.
    They can represent facts, events, skills, or conversation history.
    """
    content: str
    memory_type: MemoryType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    importance: float = 0.5  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    source: str = "user"  # user, system, learned
    tags: List[str] = field(default_factory=list)

    def access(self):
        """Mark this memory as accessed"""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "source": self.source,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            source=data.get("source", "user"),
            tags=data.get("tags", []),
        )


@dataclass
class MemoryQuery:
    """
    Query for searching memories.

    Supports text search, semantic search, and filtering.
    """
    text: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    memory_types: Optional[List[MemoryType]] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    min_importance: float = 0.0
    limit: int = 10
    offset: int = 0
    include_expired: bool = False
    semantic_threshold: float = 0.7  # Similarity threshold for semantic search

    def matches(self, memory: Memory) -> bool:
        """Check if a memory matches this query (non-semantic part)"""
        # Check type filter
        if self.memory_types and memory.memory_type not in self.memory_types:
            return False

        # Check tags
        if self.tags and not any(tag in memory.tags for tag in self.tags):
            return False

        # Check source
        if self.source and memory.source != self.source:
            return False

        # Check importance
        if memory.importance < self.min_importance:
            return False

        # Check expiration
        if not self.include_expired and memory.expires_at:
            if datetime.now() > memory.expires_at:
                return False

        # Check text (simple substring match)
        if self.text and self.text.lower() not in memory.content.lower():
            return False

        return True
