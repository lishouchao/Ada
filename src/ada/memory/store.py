"""
Memory Store - Persistent storage for memories
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from ada.memory.base import Memory, MemoryType, MemoryQuery

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    SQLite-based persistent storage for memories.

    Features:
    - CRUD operations for memories
    - Full-text search
    - Metadata filtering
    - Automatic expiration cleanup
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """Create database tables if they don't exist"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    source TEXT DEFAULT 'user',
                    tags TEXT DEFAULT '[]'
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON memories(source)")

            # Enable full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id,
                    content,
                    content='memories',
                    content_rowid='rowid'
                )
            """)

            conn.commit()

    def save(self, memory: Memory) -> bool:
        """Save a memory to the store"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memories
                    (id, content, memory_type, metadata, created_at, updated_at,
                     expires_at, importance, access_count, last_accessed, source, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.id,
                    memory.content,
                    memory.memory_type.value,
                    json.dumps(memory.metadata),
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                    memory.expires_at.isoformat() if memory.expires_at else None,
                    memory.importance,
                    memory.access_count,
                    memory.last_accessed.isoformat() if memory.last_accessed else None,
                    memory.source,
                    json.dumps(memory.tags),
                ))

                # Update FTS index
                conn.execute("""
                    INSERT OR REPLACE INTO memories_fts (id, content)
                    VALUES (?, ?)
                """, (memory.id, memory.content))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving memory {memory.id}: {e}")
            return False

    def get(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()

            if row:
                memory = self._row_to_memory(row)
                memory.access()
                # Update access count
                conn.execute(
                    "UPDATE memories SET access_count = ?, last_accessed = ? WHERE id = ?",
                    (memory.access_count, memory.last_accessed.isoformat(), memory.id)
                )
                conn.commit()
                return memory

        return None

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.execute("DELETE FROM memories_fts WHERE id = ?", (memory_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    def search(self, query: MemoryQuery) -> List[Memory]:
        """Search memories based on query criteria"""
        memories = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM memories WHERE 1=1"
            params = []

            # Filter by memory type
            if query.memory_types:
                placeholders = ",".join("?" * len(query.memory_types))
                sql += f" AND memory_type IN ({placeholders})"
                params.extend([mt.value for mt in query.memory_types])

            # Filter by source
            if query.source:
                sql += " AND source = ?"
                params.append(query.source)

            # Filter by importance
            if query.min_importance > 0:
                sql += " AND importance >= ?"
                params.append(query.min_importance)

            # Filter by expiration
            if not query.include_expired:
                sql += " AND (expires_at IS NULL OR expires_at > ?)"
                params.append(datetime.now().isoformat())

            # Full-text search
            if query.text:
                sql += " AND id IN (SELECT id FROM memories_fts WHERE memories_fts MATCH ?)"
                params.append(query.text)

            # Order and limit
            sql += " ORDER BY importance DESC, created_at DESC LIMIT ? OFFSET ?"
            params.extend([query.limit, query.offset])

            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                memory = self._row_to_memory(row)
                # Additional tag filtering in Python
                if query.tags:
                    if not any(tag in memory.tags for tag in query.tags):
                        continue
                memories.append(memory)

        return memories

    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        """Count memories, optionally filtered by type"""
        with sqlite3.connect(self.db_path) as conn:
            if memory_type:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE memory_type = ?",
                    (memory_type.value,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM memories")
            return cursor.fetchone()[0]

    def cleanup_expired(self) -> int:
        """Remove expired memories"""
        with sqlite3.connect(self.db_path) as conn:
            # Get expired IDs
            cursor = conn.execute(
                "SELECT id FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now().isoformat(),)
            )
            expired_ids = [row[0] for row in cursor.fetchall()]

            # Delete expired
            if expired_ids:
                placeholders = ",".join("?" * len(expired_ids))
                conn.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", expired_ids)
                conn.execute(f"DELETE FROM memories_fts WHERE id IN ({placeholders})", expired_ids)
                conn.commit()

            return len(expired_ids)

    def get_recent(self, limit: int = 10, memory_type: Optional[MemoryType] = None) -> List[Memory]:
        """Get most recent memories"""
        query = MemoryQuery(
            memory_types=[memory_type] if memory_type else None,
            limit=limit
        )
        return self.search(query)

    def get_important(self, limit: int = 10, min_importance: float = 0.7) -> List[Memory]:
        """Get most important memories"""
        query = MemoryQuery(
            min_importance=min_importance,
            limit=limit
        )
        return self.search(query)

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert database row to Memory object"""
        return Memory(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            importance=row["importance"],
            access_count=row["access_count"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            source=row["source"],
            tags=json.loads(row["tags"]),
        )
