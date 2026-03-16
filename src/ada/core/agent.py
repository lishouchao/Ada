"""
Ada Agent - Main agent implementation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import json

from ada.core.context import AgentContext, AgentState, AgentConfig, AgentMode
from ada.core.graph import StateGraph, Node, CompiledGraph
from ada.core.executor import Executor
from ada.core.planner import Planner, Task, TaskPlan
from ada.core.llm import LLMClient, Message, LLMResponse
from ada.skill.registry import SkillRegistry
from ada.skill.base import SkillContext, SkillResult
from ada.skill.loader import SkillLoader
from ada.memory.store import MemoryStore
from ada.memory.base import Memory, MemoryType, MemoryQuery
from ada.intent.parser import IntentParser
from ada.events.bus import EventBus

logger = logging.getLogger(__name__)


class AdaAgent:
    """
    Ada AI Assistant - Main agent implementation.

    This is the core class that orchestrates all components:
    - LLM for language understanding and generation
    - Skill system for action execution
    - Memory system for context retention
    - Event system for reactive behavior
    """

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.context = AgentContext(config=self.config)

        # Core components
        self.llm: Optional[LLMClient] = None
        self.executor = Executor()
        self.planner = Planner()

        # Skill system
        self.skill_registry = SkillRegistry()
        self.skill_loader = SkillLoader(self.skill_registry)

        # Memory system
        self.memory_store: Optional[MemoryStore] = None

        # Intent parser
        self.intent_parser = IntentParser()

        # Event system
        self.event_bus = EventBus()

        # State
        self._initialized = False
        self._running = False
        self._conversation_history: List[Message] = []

        # Callbacks
        self._on_response_callbacks: List[Callable] = []
        self._on_thinking_callbacks: List[Callable] = []
        self._on_action_callbacks: List[Callable] = []

    async def initialize(self) -> bool:
        """
        Initialize all components.

        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True

        try:
            # Initialize LLM
            await self._init_llm()

            # Initialize memory
            await self._init_memory()

            # Load skills
            await self._load_skills()

            # Start event bus
            await self.event_bus.start()

            # Build state graph
            self._graph = self._build_graph()

            self._initialized = True
            self.context.set_state(AgentState.IDLE)

            logger.info("Ada agent initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            self.context.set_state(AgentState.ERROR)
            return False

    async def _init_llm(self):
        """Initialize LLM client"""
        llm_config = self.config.llm

        self.llm = LLMClient(
            backend=llm_config.get("backend", "ollama"),
            model=llm_config.get("model", "llama3.2"),
            **llm_config.get("params", {})
        )

        # Test connection
        try:
            if await self.llm.is_available():
                logger.info(f"LLM initialized: {llm_config.get('backend')}")
            else:
                logger.warning("LLM not available, using fallback mode")
        except Exception as e:
            logger.warning(f"LLM check failed: {e}")

    async def _init_memory(self):
        """Initialize memory store"""
        memory_config = self.config.memory

        db_path = Path(memory_config.get(
            "database_path",
            "~/.local/share/ada/memory.db"
        )).expanduser()

        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.memory_store = MemoryStore(db_path)
        logger.info(f"Memory store initialized: {db_path}")

    async def _load_skills(self):
        """Load all skills"""
        # Load built-in skills
        from ada.skill.builtin import BUILTIN_SKILLS

        for skill_class in BUILTIN_SKILLS:
            skill = skill_class()
            self.skill_registry.register(skill)

        # Load from skill directories
        skill_dirs = self.config.skills.get("directories", [])

        for skill_dir in skill_dirs:
            path = Path(skill_dir).expanduser()
            if path.exists():
                self.skill_loader.load_from_directory(path, "user")

        logger.info(f"Loaded {len(self.skill_registry)} skills")

    def _build_graph(self) -> CompiledGraph:
        """Build the agent state graph"""
        graph = StateGraph(AgentContext)

        # Add nodes
        graph.add_node(Node("analyze", self._analyze_node))
        graph.add_node(Node("plan", self._plan_node))
        graph.add_node(Node("execute", self._execute_node))
        graph.add_node(Node("respond", self._respond_node))

        # Set entry point
        graph.set_entry_point("analyze")

        # Add edges
        graph.add_edge("analyze", "plan")
        graph.add_edge("plan", "execute")
        graph.add_edge("execute", "respond")

        # Conditional edge from respond
        graph.add_conditional_edge(
            "respond",
            self._should_continue,
            {
                "continue": "analyze",
                "done": "__end__"
            }
        )

        return graph.compile()

    async def _analyze_node(self, context: AgentContext) -> AgentContext:
        """Analyze user input"""
        self.context.set_state(AgentState.THINKING)

        # Notify thinking
        for callback in self._on_thinking_callbacks:
            try:
                callback("分析用户输入...")
            except Exception:
                pass

        # Parse intent
        intent_result = await self.intent_parser.parse(
            context.current_input,
            {"history": context.conversation_history}
        )

        context.current_intent = intent_result.intent
        context.entities = intent_result.entities

        # Find matching skills
        skill_context = SkillContext(
            user_input=context.current_input,
            entities=context.entities or {},
            conversation_history=context.conversation_history,
            user_preferences=context.user_preferences,
            executor=self.executor,
        )

        context.matched_skills = self.skill_registry.find_all(skill_context)

        return context

    async def _plan_node(self, context: AgentContext) -> AgentContext:
        """Plan actions based on analysis"""
        # Notify thinking
        for callback in self._on_thinking_callbacks:
            try:
                callback("规划行动方案...")
            except Exception:
                pass

        # Create plan based on intent and skills
        if context.matched_skills:
            # Use best matching skill
            best_skill, score = context.matched_skills[0]
            context.selected_skill = best_skill
            context.plan = TaskPlan(
                tasks=[Task(
                    id="1",
                    description=f"Execute {best_skill.metadata.name}",
                    action="skill.execute",
                    params={"skill_id": best_skill.metadata.id}
                )]
            )
        else:
            # No skill matched, use LLM for response
            context.selected_skill = None
            context.plan = TaskPlan(
                tasks=[Task(
                    id="1",
                    description="Generate response",
                    action="llm.respond"
                )]
            )

        return context

    async def _execute_node(self, context: AgentContext) -> AgentContext:
        """Execute the plan"""
        self.context.set_state(AgentState.EXECUTING)

        results = []

        for task in context.plan.tasks:
            # Notify action
            for callback in self._on_action_callbacks:
                try:
                    callback(task.description)
                except Exception:
                    pass

            try:
                if task.action == "skill.execute":
                    result = await self._execute_skill(
                        context.selected_skill,
                        context.current_input,
                        context.entities
                    )
                    results.append(result)

                elif task.action == "llm.respond":
                    # Response will be generated in respond node
                    pass

            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                results.append(SkillResult.fail(str(e)))

        context.execution_results = results
        return context

    async def _respond_node(self, context: AgentContext) -> AgentContext:
        """Generate response to user"""
        # Build response based on execution results
        if context.execution_results:
            # Use skill result
            result = context.execution_results[0]
            if result.success:
                context.response = result.message
            else:
                context.response = f"执行失败: {result.error}"
        else:
            # Use LLM for response
            context.response = await self._generate_llm_response(context)

        # Store in conversation history
        context.conversation_history.append(
            Message.user(context.current_input)
        )
        context.conversation_history.append(
            Message.assistant(context.response)
        )

        # Store in memory
        await self._store_conversation(context.current_input, context.response)

        # Notify response
        for callback in self._on_response_callbacks:
            try:
                callback(context.response)
            except Exception:
                pass

        self.context.set_state(AgentState.IDLE)
        return context

    def _should_continue(self, context: AgentContext) -> str:
        """Determine if agent should continue"""
        # Check for follow-up actions
        if context.requires_followup:
            return "continue"
        return "done"

    async def _execute_skill(
        self,
        skill,
        user_input: str,
        entities: Dict
    ) -> SkillResult:
        """Execute a skill"""
        skill_context = SkillContext(
            user_input=user_input,
            entities=entities or {},
            conversation_history=self.context.conversation_history,
            user_preferences=self.context.user_preferences,
            executor=self.executor,
        )

        return await skill.execute(skill_context)

    async def _generate_llm_response(self, context: AgentContext) -> str:
        """Generate response using LLM"""
        if not self.llm:
            return "抱歉，语言模型不可用。"

        # Build messages
        messages = [
            Message.system(self._get_system_prompt())
        ]

        # Add conversation history
        messages.extend(context.conversation_history[-10:])

        # Add current input
        messages.append(Message.user(context.current_input))

        try:
            response = await self.llm.chat(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM response failed: {e}")
            return f"抱歉，生成响应时出错: {e}"

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        return """你是 Ada，一个友好的 AI 助手，运行在 NebulaOS 桌面系统上。

你的能力包括：
- 启动和管理应用程序
- 整理文件和文件夹
- 控制系统设置（音量、亮度等）
- 设置提醒和日程
- 搜索网络获取信息
- 管理剪贴板内容

请用简洁、友好的方式回应用户。如果需要执行操作，请确认用户意图。"""

    async def _store_conversation(self, user_input: str, response: str):
        """Store conversation in memory"""
        if not self.memory_store:
            return

        # Store user input
        user_memory = Memory(
            content=user_input,
            memory_type=MemoryType.CONVERSATION,
            metadata={"role": "user"}
        )
        await self.memory_store.save(user_memory)

        # Store assistant response
        assistant_memory = Memory(
            content=response,
            memory_type=MemoryType.CONVERSATION,
            metadata={"role": "assistant"}
        )
        await self.memory_store.save(assistant_memory)

    # Public API

    async def process(self, user_input: str) -> SkillResult:
        """
        Process user input and return response.

        Args:
            user_input: User's text input

        Returns:
            SkillResult with response
        """
        if not self._initialized:
            await self.initialize()

        # Reset context for new input
        self.context.current_input = user_input
        self.context.current_intent = None
        self.context.entities = {}
        self.context.matched_skills = []
        self.context.selected_skill = None
        self.context.plan = None
        self.context.execution_results = []
        self.context.response = None

        # Run through state graph
        try:
            result = await self._graph.invoke(self.context)

            return SkillResult.ok(
                message=result.response or "处理完成",
                output={
                    "intent": result.current_intent.to_dict() if result.current_intent else None,
                    "skill": result.selected_skill.metadata.id if result.selected_skill else None,
                }
            )

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return SkillResult.fail(str(e))

    async def execute_skill(self, skill_id: str, input_text: str) -> SkillResult:
        """Execute a specific skill by ID"""
        if not self._initialized:
            await self.initialize()

        skill = self.skill_registry.get(skill_id)
        if not skill:
            return SkillResult.fail(f"Skill not found: {skill_id}")

        context = SkillContext(
            user_input=input_text,
            entities={},
            conversation_history=self.context.conversation_history,
            user_preferences=self.context.user_preferences,
            executor=self.executor,
        )

        return await skill.execute(context)

    def on_response(self, callback: Callable):
        """Register callback for responses"""
        self._on_response_callbacks.append(callback)

    def on_thinking(self, callback: Callable):
        """Register callback for thinking updates"""
        self._on_thinking_callbacks.append(callback)

    def on_action(self, callback: Callable):
        """Register callback for action updates"""
        self._on_action_callbacks.append(callback)

    async def shutdown(self):
        """Shutdown the agent"""
        self._running = False
        await self.event_bus.stop()
        logger.info("Agent shutdown complete")


# Convenience function
async def create_agent(config: AgentConfig = None) -> AdaAgent:
    """Create and initialize an Ada agent"""
    agent = AdaAgent(config)
    await agent.initialize()
    return agent
