"""
Agent Context - State and configuration management

Defines the agent's state, configuration, and runtime context.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
import os


class AgentMode(Enum):
    """Agent operating mode"""
    INTERACTIVE = "interactive"     # Interactive session with user
    AUTONOMOUS = "autonomous"       # Autonomous execution
    PLANNING = "planning"           # Planning only, no execution
    DEBUG = "debug"                 # Debug mode with verbose logging


@dataclass
class AgentConfig:
    """Agent configuration"""

    # Model settings
    llm_backend: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    llm_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"

    # Execution settings
    max_parallel_tasks: int = 3
    default_timeout: float = 30.0
    max_retries: int = 2

    # Memory settings
    memory_enabled: bool = True
    memory_db_path: str = "~/.local/share/ada/memory"
    max_working_memory: int = 100

    # Security settings
    sandbox_enabled: bool = True
    auto_approve_low_risk: bool = True
    require_confirmation_high: bool = True

    # UI settings
    show_progress: bool = True
    verbose: bool = False

    # Platform settings
    platform: str = "gnome"  # gnome, kde, nebula

    @classmethod
    def from_file(cls, path: Path) -> "AgentConfig":
        """Load configuration from YAML file"""
        import yaml

        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(
            llm_backend=data.get("llm", {}).get("backend", "ollama"),
            llm_model=data.get("llm", {}).get("model", "qwen2.5:7b"),
            llm_base_url=data.get("llm", {}).get("base_url", "http://localhost:11434"),
            embedding_model=data.get("llm", {}).get("embedding_model", "nomic-embed-text"),
            max_parallel_tasks=data.get("execution", {}).get("max_parallel_tasks", 3),
            default_timeout=data.get("execution", {}).get("default_timeout", 30.0),
            memory_enabled=data.get("memory", {}).get("enabled", True),
            memory_db_path=data.get("memory", {}).get("db_path", "~/.local/share/ada/memory"),
            sandbox_enabled=data.get("security", {}).get("sandbox_enabled", True),
            auto_approve_low_risk=data.get("security", {}).get("auto_approve_low_risk", True),
            platform=data.get("platform", "gnome"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "llm": {
                "backend": self.llm_backend,
                "model": self.llm_model,
                "base_url": self.llm_base_url,
                "embedding_model": self.embedding_model,
            },
            "execution": {
                "max_parallel_tasks": self.max_parallel_tasks,
                "default_timeout": self.default_timeout,
                "max_retries": self.max_retries,
            },
            "memory": {
                "enabled": self.memory_enabled,
                "db_path": self.memory_db_path,
                "max_working_memory": self.max_working_memory,
            },
            "security": {
                "sandbox_enabled": self.sandbox_enabled,
                "auto_approve_low_risk": self.auto_approve_low_risk,
                "require_confirmation_high": self.require_confirmation_high,
            },
            "ui": {
                "show_progress": self.show_progress,
                "verbose": self.verbose,
            },
            "platform": self.platform,
        }


@dataclass
class AgentState:
    """
    Mutable agent state passed through the execution graph.

    This is the central state object that flows through all
    nodes in the StateGraph.
    """

    # Input
    user_input: str = ""
    intent: Dict[str, Any] = field(default_factory=dict)

    # Processing state
    current_task_id: Optional[str] = None
    task_plan: Optional[Any] = None  # TaskPlan

    # Results
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Any] = field(default_factory=list)
    final_response: str = ""

    # Context
    active_window: Optional[str] = None
    focused_element: Optional[str] = None
    clipboard_content: Optional[str] = None

    # Memory
    relevant_memories: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    session_id: str = ""
    request_id: str = ""
    mode: AgentMode = AgentMode.INTERACTIVE

    # Error handling
    errors: List[Dict[str, Any]] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_message: str = ""

    def add_action(self, action_type: str, params: Dict, result: Any):
        """Record an action taken"""
        self.actions_taken.append({
            "type": action_type,
            "params": params,
            "result": result
        })

    def add_error(self, error: Exception, context: Dict = None):
        """Record an error"""
        self.errors.append({
            "error": str(error),
            "type": type(error).__name__,
            "context": context or {}
        })

    def request_confirmation(self, message: str):
        """Request user confirmation"""
        self.requires_confirmation = True
        self.confirmation_message = message


@dataclass
class AgentContext:
    """
    Runtime context for the agent.

    Contains all the services and managers the agent needs.
    """

    config: AgentConfig
    state: AgentState

    # Services (injected)
    llm_client: Any = None  # LLMClient
    memory_manager: Any = None  # MemoryManager
    skill_registry: Any = None  # SkillRegistry
    executor: Any = None  # Executor
    permission_manager: Any = None  # PermissionManager
    event_bus: Any = None  # EventBus

    # Platform adapters
    perception: Any = None  # PerceptionAdapter
    platform_adapter: Any = None  # PlatformAdapter

    @classmethod
    def create(
        cls,
        config: AgentConfig = None,
        mode: AgentMode = AgentMode.INTERACTIVE
    ) -> "AgentContext":
        """Create a new agent context"""
        import uuid

        if config is None:
            config = AgentConfig()

        state = AgentState(
            session_id=str(uuid.uuid4())[:8],
            request_id=str(uuid.uuid4())[:8],
            mode=mode
        )

        return cls(config=config, state=state)

    def new_request(self, user_input: str) -> "AgentContext":
        """Create a new request context"""
        import uuid

        self.state = AgentState(
            user_input=user_input,
            session_id=self.state.session_id,
            request_id=str(uuid.uuid4())[:8],
            mode=self.state.mode
        )
        return self


class Agent:
    """
    Main Ada agent class.

    Example:
        async with Ada(config) as agent:
            result = await agent.execute("整理下载文件夹")
            print(result)
    """

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self._context: Optional[AgentContext] = None
        self._graph: Optional[Any] = None  # CompiledGraph

    async def __aenter__(self) -> "Agent":
        """Initialize agent"""
        self._context = AgentContext.create(self.config)
        await self._initialize()
        return self

    async def __aexit__(self, *args):
        """Cleanup agent"""
        await self._cleanup()

    async def _initialize(self):
        """Initialize all services"""
        # This will be implemented to initialize:
        # - LLM client
        # - Memory manager
        # - Skill registry
        # - Executor with backends
        # - Permission manager
        # - Event bus
        # - Platform adapters
        pass

    async def _cleanup(self):
        """Cleanup services"""
        pass

    async def execute(
        self,
        command: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a natural language command.

        Args:
            command: Natural language command
            context: Optional additional context

        Returns:
            Execution result
        """
        self._context.new_request(command)

        if context:
            self._context.state.user_preferences.update(context)

        # Run through the state graph
        result = await self._graph.run(self._context.state)

        return {
            "success": not bool(result.errors),
            "response": result.final_response,
            "actions": result.actions_taken,
            "errors": [e["error"] for e in result.errors]
        }

    async def query(self, question: str) -> str:
        """
        Ask a question (no execution, just answer).

        Args:
            question: Question to answer

        Returns:
            Answer string
        """
        self._context.new_request(question)
        self._context.state.mode = AgentMode.PLANNING

        # TODO: Implement query mode
        return "Query mode not yet implemented"

    async def plan(self, command: str) -> Any:
        """
        Plan without executing.

        Args:
            command: Command to plan

        Returns:
            TaskPlan
        """
        self._context.new_request(command)
        self._context.state.mode = AgentMode.PLANNING

        # TODO: Implement plan mode
        return None
