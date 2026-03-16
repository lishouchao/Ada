"""
Tests for core components
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from ada.core.graph import StateGraph, Node, CompiledGraph
from ada.core.executor import Executor, ExecutionResult, Action
from ada.core.planner import Planner, Task, TaskPlan
from ada.core.llm import Message, LLMResponse, MockBackend
from ada.core.context import AgentContext, AgentState, AgentMode, AgentConfig


class TestStateGraph:
    """Tests for StateGraph"""

    def test_create_node(self):
        """Test node creation"""
        async def handler(state):
            return state

        node = Node("test", handler)
        assert node.name == "test"
        assert node.handler == handler

    def test_add_node(self):
        """Test adding nodes to graph"""
        graph = StateGraph(dict)

        async def start(state):
            return state

        graph.add_node(Node("start", start))
        assert "start" in graph._nodes

    def test_add_edge(self):
        """Test adding edges"""
        graph = StateGraph(dict)
        graph.add_node(Node("a", lambda s: s))
        graph.add_node(Node("b", lambda s: s))

        graph.add_edge("a", "b")
        assert graph._edges["a"] == "b"

    def test_compile(self):
        """Test graph compilation"""
        graph = StateGraph(dict)
        graph.add_node(Node("start", lambda s: s))
        graph.add_node(Node("end", lambda s: s))
        graph.set_entry_point("start")
        graph.add_edge("start", "end")

        compiled = graph.compile()
        assert isinstance(compiled, CompiledGraph)

    @pytest.mark.asyncio
    async def test_run(self):
        """Test running a simple graph"""
        graph = StateGraph(dict)

        async def add_value(state):
            return {**state, "added": True}

        graph.add_node(Node("start", add_value))
        graph.set_entry_point("start")

        compiled = graph.compile()
        result = await compiled.invoke({})

        assert result["added"] is True


class TestExecutor:
    """Tests for Executor"""

    @pytest.mark.asyncio
    async def test_execute_action(self):
        """Test action execution"""
        executor = Executor()

        action = Action(
            type="test.action",
            params={"value": 42},
        )

        # Register mock backend
        async def mock_handler(a):
            return ExecutionResult.ok(output={"result": a.params["value"] * 2})

        executor.register_handler("test.action", mock_handler)

        result = await executor.execute(action)
        assert result.success
        assert result.output["result"] == 84

    @pytest.mark.asyncio
    async def test_execution_fallback(self):
        """Test fallback on failure"""
        executor = Executor()

        # No handler registered
        action = Action(type="unknown.action")

        result = await executor.execute(action)
        assert not result.success


class TestPlanner:
    """Tests for Planner"""

    def test_create_task(self):
        """Test task creation"""
        task = Task(
            id="task-1",
            description="Test task",
            action="test.action",
        )

        assert task.id == "task-1"
        assert task.status == "pending"

    def test_plan_tasks(self):
        """Test task planning"""
        planner = Planner()

        tasks = [
            Task(id="1", description="First", action="a"),
            Task(id="2", description="Second", action="b", dependencies=["1"]),
            Task(id="3", description="Third", action="c", dependencies=["2"]),
        ]

        plan = planner.create_plan(tasks)
        assert len(plan.tasks) == 3

        # Check order (topological sort)
        order = plan.get_execution_order()
        assert order.index("1") < order.index("2")
        assert order.index("2") < order.index("3")


class TestLLM:
    """Tests for LLM client"""

    def test_message_creation(self):
        """Test message creation"""
        msg = Message.user("Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

        msg = Message.assistant("Hi there!")
        assert msg.role == "assistant"

        msg = Message.system("System message")
        assert msg.role == "system"

    def test_response_creation(self):
        """Test response creation"""
        response = LLMResponse(
            content="Test response",
            model="test-model",
        )

        assert response.content == "Test response"
        assert not response.is_error

    @pytest.mark.asyncio
    async def test_mock_backend(self):
        """Test mock backend"""
        backend = MockBackend()
        backend.add_response("Hello", "Hi there!")

        response = await backend.chat([Message.user("Hello")])
        assert response.content == "Hi there!"


class TestAgentContext:
    """Tests for Agent context"""

    def test_create_context(self):
        """Test context creation"""
        config = AgentConfig()
        context = AgentContext(config=config)

        assert context.state == AgentState.IDLE
        assert context.mode == AgentMode.NORMAL

    def test_context_state_transitions(self):
        """Test state transitions"""
        config = AgentConfig()
        context = AgentContext(config=config)

        context.set_state(AgentState.THINKING)
        assert context.state == AgentState.THINKING

        context.set_state(AgentState.EXECUTING)
        assert context.state == AgentState.EXECUTING

    def test_context_history(self):
        """Test conversation history"""
        config = AgentConfig()
        context = AgentContext(config=config)

        context.add_message(Message.user("Hello"))
        context.add_message(Message.assistant("Hi!"))

        history = context.get_history()
        assert len(history) == 2
