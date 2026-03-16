"""
Vector Store - Semantic search with embeddings
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import numpy as np

from ada.memory.base import Memory, MemoryQuery

logger = logging.getLogger(__name__)


class VectorBackend(ABC):
    """Abstract base for vector storage backends"""

    @abstractmethod
    async def store(self, id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Store an embedding with metadata"""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar embeddings"""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an embedding by ID"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total embeddings"""
        pass


class SQLiteVecBackend(VectorBackend):
    """
    SQLite-vec based vector storage.

    Uses sqlite-vec extension for efficient vector similarity search.
    Falls back to numpy-based in-memory search if sqlite-vec unavailable.
    """

    def __init__(self, db_path: Path, dimension: int = 768):
        self.db_path = db_path
        self.dimension = dimension
        self._use_fallback = False
        self._fallback_store: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}

        self._init_db()

    def _init_db(self):
        """Initialize the vector database"""
        try:
            import sqlite3

            # Try to load sqlite-vec extension
            conn = sqlite3.connect(self.db_path)

            try:
                conn.enable_load_extension(True)
                # Try common locations for sqlite-vec
                import ctypes
                ctypes.CDLL("sqlite_vec")  # Try system library
                conn.load_extension("sqlite_vec")
                logger.info("Using sqlite-vec extension")
            except Exception:
                # Fall back to numpy-based search
                self._use_fallback = True
                logger.warning("sqlite-vec not available, using numpy fallback")
            finally:
                conn.close()

            if not self._use_fallback:
                self._create_tables()

        except Exception as e:
            logger.error(f"Error initializing vector DB: {e}")
            self._use_fallback = True

    def _create_tables(self):
        """Create vector tables"""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            # Create virtual table for vectors
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(
                    id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.dimension}],
                    metadata TEXT
                )
            """)
            conn.commit()

    async def store(self, id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Store an embedding"""
        import json

        if self._use_fallback:
            self._fallback_store[id] = (embedding, metadata)
            return True

        try:
            import sqlite3

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO vec_memories (id, embedding, metadata)
                    VALUES (?, ?, ?)
                """, (id, json.dumps(embedding), json.dumps(metadata)))
                conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar embeddings"""
        import json

        if self._use_fallback:
            return self._fallback_search(query_embedding, limit, threshold)

        try:
            import sqlite3

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, metadata, vec_distance_cosine(embedding, ?) as distance
                    FROM vec_memories
                    WHERE distance >= ?
                    ORDER BY distance DESC
                    LIMIT ?
                """, (json.dumps(query_embedding), threshold, limit))

                results = []
                for row in cursor.fetchall():
                    results.append((row[0], row[2], json.loads(row[1])))
                return results

        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return []

    def _fallback_search(
        self,
        query_embedding: List[float],
        limit: int,
        threshold: float
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Numpy-based fallback search"""
        if not self._fallback_store:
            return []

        query = np.array(query_embedding)
        results = []

        for id, (embedding, metadata) in self._fallback_store.items():
            vec = np.array(embedding)
            # Cosine similarity
            similarity = np.dot(query, vec) / (np.linalg.norm(query) * np.linalg.norm(vec))

            if similarity >= threshold:
                results.append((id, float(similarity), metadata))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def delete(self, id: str) -> bool:
        """Delete an embedding"""
        if self._use_fallback:
            if id in self._fallback_store:
                del self._fallback_store[id]
            return True

        try:
            import sqlite3

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM vec_memories WHERE id = ?", (id,))
                conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error deleting embedding: {e}")
            return False

    async def count(self) -> int:
        """Count embeddings"""
        if self._use_fallback:
            return len(self._fallback_store)

        try:
            import sqlite3

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM vec_memories")
                return cursor.fetchone()[0]
        except Exception:
            return 0


class ChromaBackend(VectorBackend):
    """
    ChromaDB-based vector storage.

    Provides more advanced features like metadata filtering and hybrid search.
    """

    def __init__(self, persist_directory: Path, collection_name: str = "ada_memories"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._client = None
        self._collection = None

        self._init_chroma()

    def _init_chroma(self):
        """Initialize ChromaDB client"""
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=str(self.persist_directory))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB initialized with collection '{self.collection_name}'")

        except ImportError:
            logger.warning("ChromaDB not installed, vector search unavailable")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")

    async def store(self, id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Store an embedding in ChromaDB"""
        if not self._collection:
            return False

        try:
            self._collection.upsert(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            return True

        except Exception as e:
            logger.error(f"Error storing in ChromaDB: {e}")
            return False

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search ChromaDB for similar embeddings"""
        if not self._collection:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["distances", "metadatas"]
            )

            # Convert to standard format
            matches = []
            for i, id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # Convert distance to similarity (1 - distance for cosine)
                similarity = 1 - distance

                if similarity >= threshold:
                    matches.append((id, similarity, results["metadatas"][0][i]))

            return matches

        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            return []

    async def delete(self, id: str) -> bool:
        """Delete from ChromaDB"""
        if not self._collection:
            return False

        try:
            self._collection.delete(ids=[id])
            return True

        except Exception as e:
            logger.error(f"Error deleting from ChromaDB: {e}")
            return False

    async def count(self) -> int:
        """Count embeddings in ChromaDB"""
        if not self._collection:
            return 0

        return self._collection.count()


class VectorStore:
    """
    High-level vector store with embedding generation.

    Combines vector storage with embedding generation for semantic search.
    """

    def __init__(
        self,
        store_path: Path,
        embedding_func: Optional[callable] = None,
        use_chroma: bool = False,
        dimension: int = 768
    ):
        self.store_path = store_path
        self.embedding_func = embedding_func
        self.dimension = dimension

        # Initialize backend
        if use_chroma:
            self._backend = ChromaBackend(store_path / "chroma")
        else:
            self._backend = SQLiteVecBackend(store_path / "vectors.db", dimension)

    async def add_memory(self, memory: Memory) -> bool:
        """Add a memory with its embedding to the vector store"""
        if not memory.embedding:
            if self.embedding_func:
                memory.embedding = await self.embedding_func(memory.content)
            else:
                logger.warning("No embedding function available")
                return False

        metadata = {
            "memory_type": memory.memory_type.value,
            "source": memory.source,
            "importance": memory.importance,
            "tags": memory.tags,
        }

        return await self._backend.store(memory.id, memory.embedding, metadata)

    async def search_similar(
        self,
        query: str or List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar memories.

        Args:
            query: Query text or embedding
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of (memory_id, similarity, metadata) tuples
        """
        # Get query embedding
        if isinstance(query, str):
            if self.embedding_func:
                query_embedding = await self.embedding_func(query)
            else:
                logger.warning("No embedding function for text query")
                return []
        else:
            query_embedding = query

        return await self._backend.search(query_embedding, limit, threshold)

    async def remove_memory(self, memory_id: str) -> bool:
        """Remove a memory from vector store"""
        return await self._backend.delete(memory_id)

    async def count(self) -> int:
        """Count vectors in store"""
        return await self._backend.count()
