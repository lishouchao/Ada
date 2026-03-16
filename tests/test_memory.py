"""
Tests for memory system
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from ada.memory.base import Memory, MemoryType, MemoryQuery
from ada.memory.store import MemoryStore
from ada.memory.vector import VectorStore, SQLiteVecBackend


class TestMemory:
    """Tests for Memory class"""

    def test_create_memory(self):
        """Test memory creation"""
        memory = Memory(
            content="Test memory content",
            memory_type=MemoryType.SEMANTIC,
        )

        assert memory.content == "Test memory content"
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.importance == 0.5
        assert not memory.embedding

    def test_memory_access(self):
        """Test memory access tracking"""
        memory = Memory(
            content="Test",
            memory_type=MemoryType.EPISODIC,
        )

        initial_count = memory.access_count
        memory.access()

        assert memory.access_count == initial_count + 1
        assert memory.last_accessed is not None

    def test_memory_types(self):
        """Test different memory types"""
        semantic = Memory(content="Fact", memory_type=MemoryType.SEMANTIC)
        episodic = Memory(content="Event", memory_type=MemoryType.EPISODIC)
        procedural = Memory(content="Skill", memory_type=MemoryType.PROCEDURAL)
        working = Memory(content="Temp", memory_type=MemoryType.WORKING)

        assert semantic.memory_type == MemoryType.SEMANTIC
        assert episodic.memory_type == MemoryType.EPISODIC
        assert procedural.memory_type == MemoryType.PROCEDURAL
        assert working.memory_type == MemoryType.WORKING

    def test_memory_expiration(self):
        """Test memory expiration"""
        # Expired memory
        memory = Memory(
            content="Old",
            memory_type=MemoryType.WORKING,
            expires_at=datetime.now() - timedelta(hours=1),
        )

        # Not expired
        future_memory = Memory(
            content="New",
            memory_type=MemoryType.WORKING,
            expires_at=datetime.now() + timedelta(hours=1),
        )

    def test_memory_serialization(self):
        """Test memory serialization"""
        memory = Memory(
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            metadata={"key": "value"},
            tags=["test", "example"],
        )

        d = memory.to_dict()

        assert d["content"] == "Test"
        assert d["memory_type"] == "semantic"
        assert d["metadata"]["key"] == "value"
        assert "test" in d["tags"]

        # Deserialize
        restored = Memory.from_dict(d)
        assert restored.content == memory.content
        assert restored.memory_type == memory.memory_type


class TestMemoryQuery:
    """Tests for MemoryQuery"""

    def test_create_query(self):
        """Test query creation"""
        query = MemoryQuery(
            text="search term",
            limit=20,
            min_importance=0.5,
        )

        assert query.text == "search term"
        assert query.limit == 20
        assert query.min_importance == 0.5

    def test_query_filtering(self):
        """Test query filtering logic"""
        query = MemoryQuery(
            text="test",
            memory_types=[MemoryType.SEMANTIC],
            min_importance=0.7,
        )

        # Matching memory
        good_memory = Memory(
            content="test content",
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
        )

        # Non-matching (wrong type)
        bad_memory1 = Memory(
            content="test",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
        )

        # Non-matching (low importance)
        bad_memory2 = Memory(
            content="test",
            memory_type=MemoryType.SEMANTIC,
            importance=0.3,
        )

        assert query.matches(good_memory)
        assert not query.matches(bad_memory1)
        assert not query.matches(bad_memory2)


class TestMemoryStore:
    """Tests for MemoryStore"""

    @pytest.fixture
    def store(self, temp_dir):
        """Create a memory store"""
        db_path = temp_dir / "test_memory.db"
        return MemoryStore(db_path)

    def test_save_and_get(self, store):
        """Test save and retrieve"""
        memory = Memory(
            content="Test memory",
            memory_type=MemoryType.SEMANTIC,
        )

        # Save
        assert store.save(memory)

        # Get
        retrieved = store.get(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Test memory"

    def test_delete(self, store):
        """Test delete"""
        memory = Memory(
            content="To delete",
            memory_type=MemoryType.EPISODIC,
        )

        store.save(memory)
        assert store.delete(memory.id)

        # Should not exist
        assert store.get(memory.id) is None

    def test_search(self, store):
        """Test search"""
        # Add some memories
        store.save(Memory(content="Python is great", memory_type=MemoryType.SEMANTIC))
        store.save(Memory(content="JavaScript is cool", memory_type=MemoryType.SEMANTIC))
        store.save(Memory(content="Meeting notes", memory_type=MemoryType.EPISODIC))

        # Search
        query = MemoryQuery(text="Python")
        results = store.search(query)

        assert len(results) > 0
        assert "Python" in results[0].content

    def test_search_by_type(self, store):
        """Test search by type"""
        store.save(Memory(content="Fact 1", memory_type=MemoryType.SEMANTIC))
        store.save(Memory(content="Event 1", memory_type=MemoryType.EPISODIC))

        query = MemoryQuery(memory_types=[MemoryType.SEMANTIC])
        results = store.search(query)

        for r in results:
            assert r.memory_type == MemoryType.SEMANTIC

    def test_count(self, store):
        """Test count"""
        initial_count = store.count()

        store.save(Memory(content="New", memory_type=MemoryType.SEMANTIC))

        assert store.count() == initial_count + 1

    def test_get_recent(self, store):
        """Test get recent"""
        store.save(Memory(content="Recent 1", memory_type=MemoryType.EPISODIC))
        store.save(Memory(content="Recent 2", memory_type=MemoryType.EPISODIC))

        recent = store.get_recent(limit=5)

        assert len(recent) > 0

    def test_cleanup_expired(self, store):
        """Test cleanup of expired memories"""
        # Create expired memory
        expired = Memory(
            content="Expired",
            memory_type=MemoryType.WORKING,
            expires_at=datetime.now() - timedelta(hours=1),
        )
        store.save(expired)

        # Cleanup
        cleaned = store.cleanup_expired()

        assert cleaned > 0
        assert store.get(expired.id) is None


class TestVectorStore:
    """Tests for VectorStore"""

    @pytest.fixture
    def vector_store(self, temp_dir):
        """Create a vector store"""
        store_path = temp_dir / "vectors"
        return VectorStore(store_path, dimension=128)

    def test_store_creation(self, vector_store):
        """Test store creation"""
        assert vector_store.dimension == 128

    @pytest.mark.asyncio
    async def test_add_and_search(self, vector_store):
        """Test adding and searching"""
        # Create mock embedding function
        async def embed(text):
            # Simple hash-based embedding for testing
            import hashlib
            h = hashlib.md5(text.encode()).hexdigest()
            return [float(int(h[i:i+2], 16)) / 255 for i in range(0, 128*2, 2)]

        vector_store.embedding_func = embed

        # Add memories
        memory1 = Memory(
            id="mem1",
            content="Python programming",
            memory_type=MemoryType.SEMANTIC,
            embedding=await embed("Python programming"),
        )

        memory2 = Memory(
            id="mem2",
            content="JavaScript development",
            memory_type=MemoryType.SEMANTIC,
            embedding=await embed("JavaScript development"),
        )

        await vector_store.add_memory(memory1)
        await vector_store.add_memory(memory2)

        # Search
        results = await vector_store.search_similar("Python coding", limit=5)
        assert len(results) > 0
