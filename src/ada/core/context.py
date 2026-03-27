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


class AgentStatus(Enum):
    """Agent status"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    ERROR = "error"


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    provider: str = "ollama"
    model: str = "qwen2.5:latest"
    api_key: str = ""
    base_url: str = ""
    embedding_model: str = "nomic-embed-text:latest"
    embedding_provider: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 4096

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "embedding_model": self.embedding_model,
            "embedding_provider": self.embedding_provider,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        return cls(
            provider=data.get("provider", "ollama"),
            model=data.get("model", "qwen2.5:latest"),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            embedding_model=data.get("embedding_model", "nomic-embed-text:latest"),
            embedding_provider=data.get("embedding_provider", ""),
            temperature=data.get("temperature", 0.7),
            top_p=data.get("top_p", 0.9),
            max_tokens=data.get("max_tokens", 4096),
        )


@dataclass
class AgentConfig:
    """Agent configuration"""

    # LLM settings
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Legacy fields (for backward compatibility)
    llm_backend: str = "ollama"
    llm_model: str = "qwen2.5:latest"
    llm_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text:latest"

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

    # Skills settings
    skills: Dict[str, Any] = field(default_factory=lambda: {"directories": []})

    @classmethod
    def from_file(cls, path: Path) -> "AgentConfig":
        """Load configuration from YAML file"""
        import yaml

        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Parse LLM config
        llm_data = data.get("llm", {})
        llm_config = LLMConfig(
            provider=llm_data.get("provider", "ollama"),
            model=llm_data.get("model", "qwen2.5:latest"),
            embedding_model=llm_data.get("embedding", {}).get("model", "nomic-embed-text:latest"),
            temperature=llm_data.get("params", {}).get("temperature", 0.7),
            top_p=llm_data.get("params", {}).get("top_p", 0.9),
            max_tokens=llm_data.get("params", {}).get("max_tokens", 4096),
        )

        # Get provider-specific settings
        provider_id = llm_data.get("provider", "ollama")
        provider_data = llm_data.get(provider_id, {})
        if provider_data:
            llm_config.base_url = provider_data.get("base_url", "")
            llm_config.api_key = provider_data.get("api_key", "")
            if "model" in provider_data:
                llm_config.model = provider_data["model"]
            if "embedding_model" in provider_data:
                llm_config.embedding_model = provider_data["embedding_model"]

        return cls(
            llm=llm_config,
            llm_backend=llm_data.get("provider", "ollama"),
            llm_model=llm_config.model,
            llm_base_url=llm_config.base_url or "http://localhost:11434",
            embedding_model=llm_config.embedding_model,
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
            "llm": self.llm.to_dict(),
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

    # Conversation history
    conversation_history: List[Any] = field(default_factory=list)  # List[Message]

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
    status: AgentStatus = AgentStatus.IDLE

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

    # Conversation
    conversation_history: List[Any] = field(default_factory=list)  # List[Message]

    # User preferences
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    # Processing state (used by agent.py)
    current_input: str = ""
    current_intent: Any = None  # Intent
    entities: Dict[str, Any] = field(default_factory=dict)
    matched_skills: List[Any] = field(default_factory=list)  # List[Tuple[Skill, float]]
    selected_skill: Any = None  # Skill
    plan: Any = None  # TaskPlan
    execution_results: List[Any] = field(default_factory=list)  # List[SkillResult]
    response: str = ""
    requires_followup: bool = False

    def set_state(self, status: AgentStatus):
        """Set agent status"""
        self.status = status

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
