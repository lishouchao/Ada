"""
Ada Core - Self-built Agent Runtime

This module provides the core components for Ada's agent runtime:
- StateGraph: State machine engine for task orchestration
- Executor: Hybrid execution engine (API > DBus > CLI > GUI)
- Planner: Task decomposition and planning
- LLMClient: Unified LLM interface
"""

from ada.core.graph import StateGraph, Node, CompiledGraph
from ada.core.executor import Executor, ExecutionPath, ExecutionResult, Action
from ada.core.planner import Planner, Task, TaskPlan, TaskStatus
from ada.core.llm import LLMClient, LLMBackend, Message, LLMResponse
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
    # Context
    "AgentContext",
    "AgentState",
    "AgentConfig",
]
