"""
API Backend - Direct function calls within Ada
"""

import logging
from typing import Any, Dict, Optional

from ada.platform.execution.backends import ExecutionBackend, BackendResult

logger = logging.getLogger(__name__)


class APIBackend(ExecutionBackend):
    """
    Execute actions via direct API calls.

    This is the highest priority backend for internal actions
    that don't need external tools.
    """

    def __init__(self):
        self._handlers: Dict[str, callable] = {}
        self._register_default_handlers()

    @property
    def name(self) -> str:
        return "api"

    @property
    def priority(self) -> int:
        return 10  # Highest priority

    async def is_available(self) -> bool:
        """API backend is always available"""
        return True

    def _register_default_handlers(self):
        """Register default API handlers"""
        self._handlers = {
            "memory.store": self._handle_memory_store,
            "memory.retrieve": self._handle_memory_retrieve,
            "memory.search": self._handle_memory_search,
            "skill.list": self._handle_skill_list,
            "skill.execute": self._handle_skill_execute,
            "intent.parse": self._handle_intent_parse,
            "llm.chat": self._handle_llm_chat,
            "llm.embed": self._handle_llm_embed,
        }

    def register_handler(self, action_type: str, handler: callable):
        """Register a custom API handler"""
        self._handlers[action_type] = handler

    async def can_execute(self, action: Dict[str, Any]) -> bool:
        """Check if action can be executed via API"""
        action_type = action.get("type", "")
        return action_type in self._handlers

    async def execute(self, action: Dict[str, Any]) -> BackendResult:
        """Execute action via API call"""
        action_type = action.get("type")
        params = action.get("params", {})

        if action_type not in self._handlers:
            return BackendResult.fail(f"Unknown API action: {action_type}", self.name)

        handler = self._handlers[action_type]

        try:
            result = await handler(params)
            return result

        except Exception as e:
            logger.error(f"API execution failed: {e}")
            return BackendResult.fail(str(e), self.name)

    # Default handlers (stubs - to be connected to actual components)

    async def _handle_memory_store(self, params: Dict[str, Any]) -> BackendResult:
        """Store memory"""
        # This will be connected to MemoryManager
        return BackendResult.fail("Memory manager not connected", self.name)

    async def _handle_memory_retrieve(self, params: Dict[str, Any]) -> BackendResult:
        """Retrieve memory"""
        return BackendResult.fail("Memory manager not connected", self.name)

    async def _handle_memory_search(self, params: Dict[str, Any]) -> BackendResult:
        """Search memories"""
        return BackendResult.fail("Memory manager not connected", self.name)

    async def _handle_skill_list(self, params: Dict[str, Any]) -> BackendResult:
        """List available skills"""
        return BackendResult.fail("Skill registry not connected", self.name)

    async def _handle_skill_execute(self, params: Dict[str, Any]) -> BackendResult:
        """Execute a skill"""
        return BackendResult.fail("Skill executor not connected", self.name)

    async def _handle_intent_parse(self, params: Dict[str, Any]) -> BackendResult:
        """Parse user intent"""
        return BackendResult.fail("Intent parser not connected", self.name)

    async def _handle_llm_chat(self, params: Dict[str, Any]) -> BackendResult:
        """Chat with LLM"""
        return BackendResult.fail("LLM client not connected", self.name)

    async def _handle_llm_embed(self, params: Dict[str, Any]) -> BackendResult:
        """Generate embeddings"""
        return BackendResult.fail("LLM client not connected", self.name)

    def connect_memory_manager(self, memory_manager):
        """Connect memory manager to handlers"""
        async def store(params):
            from ada.memory.base import Memory, MemoryType
            memory = Memory(
                content=params.get("content"),
                memory_type=MemoryType(params.get("type", "semantic")),
                metadata=params.get("metadata", {}),
            )
            result = await memory_manager.store(memory)
            return BackendResult.ok({"id": result}, self.name)

        async def retrieve(params):
            memory = await memory_manager.retrieve(params.get("id"))
            if memory:
                return BackendResult.ok(memory.to_dict(), self.name)
            return BackendResult.fail("Memory not found", self.name)

        async def search(params):
            from ada.memory.base import MemoryQuery
            query = MemoryQuery(
                text=params.get("text"),
                limit=params.get("limit", 10),
            )
            memories = await memory_manager.search(query)
            return BackendResult.ok(
                [m.to_dict() for m in memories],
                self.name
            )

        self._handlers["memory.store"] = store
        self._handlers["memory.retrieve"] = retrieve
        self._handlers["memory.search"] = search

    def connect_skill_registry(self, registry):
        """Connect skill registry to handlers"""
        async def list_skills(params):
            category = params.get("category")
            skills = registry.list_skills(category)
            return BackendResult.ok(
                [{"id": s.metadata.id, "name": s.metadata.name} for s in skills],
                self.name
            )

        self._handlers["skill.list"] = list_skills

    def connect_intent_parser(self, parser):
        """Connect intent parser to handlers"""
        async def parse_intent(params):
            text = params.get("text")
            context = params.get("context", {})
            result = await parser.parse(text, context)
            return BackendResult.ok(result.to_dict(), self.name)

        self._handlers["intent.parse"] = parse_intent

    def connect_llm_client(self, client):
        """Connect LLM client to handlers"""
        async def chat(params):
            messages = params.get("messages", [])
            response = await client.chat(messages)
            return BackendResult.ok(
                {"content": response.content},
                self.name
            )

        async def embed(params):
            text = params.get("text")
            embedding = await client.embed(text)
            return BackendResult.ok(
                {"embedding": embedding},
                self.name
            )

        self._handlers["llm.chat"] = chat
        self._handlers["llm.embed"] = embed
