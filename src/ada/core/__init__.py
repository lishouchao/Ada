"""
Ada Core - Self-built Agent Runtime

This module provides the core components for Ada's agent runtime:
- StateGraph: State machine engine for task orchestration
- Executor: Hybrid execution engine (API > DBus > CLI > GUI)
- Planner: Task decomposition and planning
- LLMClient: Unified LLM interface supporting multiple providers
- Providers: Predefined configurations for mainstream LLM services
"""

from ada.core.graph import StateGraph, Node, CompiledGraph
from ada.core.executor import Executor, ExecutionPath, ExecutionResult, Action
from ada.core.planner import Planner, Task, TaskPlan, TaskStatus
from ada.core.llm import (
    LLMClient, LLMBackend, Message, LLMResponse,
    ToolDefinition, ToolCall,
    OllamaBackend, OpenAICompatibleBackend, AnthropicBackend, GoogleBackend
)
from ada.core.llm_providers import (
    ProviderInfo, ProviderType, ProviderRegion,
    get_provider, list_providers, get_chinese_providers, get_international_providers,
    PROVIDERS
)
from ada.core.context import AgentContext, AgentState, AgentConfig

__all__ = [
    # Graph
    "StateGraph",
    "Node",
    "CompiledGraph",
    # Executor
    "Executor",
    "ExecutionPath",
    "ExecutionResult",
    "Action",
    # Planner
    "Planner",
    "Task",
    "TaskPlan",
    "TaskStatus",
    # LLM
    "LLMClient",
    "LLMBackend",
    "Message",
    "LLMResponse",
    "ToolDefinition",
    "ToolCall",
    "OllamaBackend",
    "OpenAICompatibleBackend",
    "AnthropicBackend",
    "GoogleBackend",
    # LLM Providers
    "ProviderInfo",
    "ProviderType",
    "ProviderRegion",
    "get_provider",
    "list_providers",
    "get_chinese_providers",
    "get_international_providers",
    "PROVIDERS",
    # Context
    "AgentContext",
    "AgentState",
    "AgentConfig",
]
