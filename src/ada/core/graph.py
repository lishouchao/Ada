"""
StateGraph - State Machine Engine for Agent Orchestration

A lightweight, type-safe state machine framework for building
complex agent workflows with support for:
- Conditional branching
- Parallel execution
- Streaming updates
- Cycle detection
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional,
    TypeVar, Union, Awaitable, Set, AsyncIterator
)
from enum import Enum
import asyncio
import time

StateT = TypeVar("StateT")
OutputT = TypeVar("OutputT")


class NodeStatus(Enum):
    """Node execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeResult(Generic[OutputT]):
    """Result of node execution"""
    status: NodeStatus
    output: Optional[OutputT] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


class Node(ABC, Generic[StateT, OutputT]):
    """Abstract base class for graph nodes"""

    def __init__(self, name: str):
        self.name = name
        self.status = NodeStatus.PENDING
        self._dependencies: Set[str] = set()

    @abstractmethod
    async def execute(self, state: StateT) -> NodeResult[OutputT]:
        """Execute node logic"""
        pass

    def depends_on(self, *node_names: str) -> "Node[StateT, OutputT]":
        """Add dependency nodes"""
        self._dependencies.update(node_names)
        return self

    @property
    def dependencies(self) -> Set[str]:
        return self._dependencies.copy()


class FunctionNode(Node[StateT, OutputT]):
    """Node that wraps a function"""

    def __init__(
        self,
        name: str,
        func: Callable[[StateT], Awaitable[OutputT]]
    ):
        super().__init__(name)
        self.func = func

    async def execute(self, state: StateT) -> NodeResult[OutputT]:
        start = time.time()
        try:
            self.status = NodeStatus.RUNNING
            result = await self.func(state)
            self.status = NodeStatus.SUCCESS
            return NodeResult(
                status=NodeStatus.SUCCESS,
                output=result,
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            self.status = NodeStatus.FAILED
            return NodeResult(
                status=NodeStatus.FAILED,
                error=e,
                duration_ms=int((time.time() - start) * 1000)
            )


@dataclass
class Edge:
    """Edge connecting nodes"""
    source: str
    target: str
    condition: Optional[Callable[[Any], bool]] = None


class StateGraph(Generic[StateT]):
    """
    State machine graph for agent orchestration.

    Example:
        graph = StateGraph[AgentState]()
        graph.add_node("perceive", perceive_node)
        graph.add_node("plan", plan_node)
        graph.add_node("execute", execute_node)
        graph.add_edge("perceive", "plan")
        graph.add_edge("plan", "execute")
        graph.set_entry_point("perceive")
        graph.set_finish_point("complete")

        compiled = graph.compile()
        result = await compiled.run(initial_state)
    """

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, List[Edge]] = {}
        self._entry_point: Optional[str] = None
        self._finish_points: Set[str] = set()

    def add_node(
        self,
        name: str,
        node: Union[Node, Callable[[StateT], Awaitable[Any]]]
    ) -> "StateGraph[StateT]":
        """Add a node to the graph"""
        if callable(node) and not isinstance(node, Node):
            node = FunctionNode(name, node)
        self._nodes[name] = node
        self._edges[name] = []
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        condition: Callable[[StateT], bool] = None
    ) -> "StateGraph[StateT]":
        """Add an edge between nodes"""
        if source not in self._edges:
            self._edges[source] = []
        self._edges[source].append(Edge(source, target, condition))
        return self

    def add_conditional_edges(
        self,
        source: str,
        condition: Callable[[StateT], str],
        targets: Dict[str, str]
    ) -> "StateGraph[StateT]":
        """Add conditional edges based on state"""
        for condition_value, target in targets.items():
            def make_cond(val):
                return lambda state: condition(state) == val
            self.add_edge(source, target, make_cond(condition_value))
        return self

    def set_entry_point(self, node_name: str) -> "StateGraph[StateT]":
        """Set the entry point node"""
        self._entry_point = node_name
        return self

    def set_finish_point(self, node_name: str) -> "StateGraph[StateT]":
        """Add a finish point node"""
        self._finish_points.add(node_name)
        return self

    def compile(self) -> "CompiledGraph[StateT]":
        """Compile the graph for execution"""
        if not self._entry_point:
            raise ValueError("Entry point not set")

        return CompiledGraph(
            nodes=self._nodes.copy(),
            edges={k: v.copy() for k, v in self._edges.items()},
            entry_point=self._entry_point,
            finish_points=self._finish_points.copy()
        )

    def to_mermaid(self) -> str:
        """Export graph as Mermaid diagram"""
        lines = ["graph TD"]
        for name, node in self._nodes.items():
            lines.append(f"    {name}[{name}]")
        for source, edges in self._edges.items():
            for edge in edges:
                label = "condition" if edge.condition else ""
                lines.append(f"    {source} -->|{label}| {edge.target}")
        return "\n".join(lines)


class CompiledGraph(Generic[StateT]):
    """Compiled graph ready for execution"""

    def __init__(
        self,
        nodes: Dict[str, Node],
        edges: Dict[str, List[Edge]],
        entry_point: str,
        finish_points: Set[str]
    ):
        self._nodes = nodes
        self._edges = edges
        self._entry_point = entry_point
        self._finish_points = finish_points

    async def run(
        self,
        initial_state: StateT,
        max_steps: int = 50
    ) -> StateT:
        """Execute the graph"""
        state = initial_state
        current_node = self._entry_point
        visited = set()
        step = 0

        while current_node and current_node not in self._finish_points:
            if step >= max_steps:
                raise RuntimeError(f"Max steps ({max_steps}) exceeded")
            if current_node in visited:
                raise RuntimeError(f"Cycle detected at node: {current_node}")

            visited.add(current_node)
            node = self._nodes[current_node]

            # Execute node
            result = await node.execute(state)

            if result.status == NodeStatus.FAILED:
                raise result.error

            # Find next node
            current_node = self._find_next_node(current_node, state)
            step += 1

        return state

    async def stream(
        self,
        initial_state: StateT
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute graph with streaming updates"""
        state = initial_state
        current_node = self._entry_point

        while current_node and current_node not in self._finish_points:
            node = self._nodes[current_node]
            result = await node.execute(state)

            yield {
                "node": current_node,
                "status": result.status,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms
            }

            if result.status == NodeStatus.FAILED:
                break

            current_node = self._find_next_node(current_node, state)

    def _find_next_node(self, current: str, state: StateT) -> Optional[str]:
        """Find the next node to execute"""
        edges = self._edges.get(current, [])
        for edge in edges:
            if edge.condition is None or edge.condition(state):
                return edge.target
        return None
