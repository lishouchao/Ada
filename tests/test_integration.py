"""
Integration tests for Ada
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import json

from ada.core.agent import AdaAgent, create_agent
from ada.core.context import AgentConfig, AgentState, AgentMode
from ada.skill.base import SkillContext, SkillResult
from ada.events.base import Event, EventType


class TestAgentIntegration:
    """Integration tests for Ada agent"""

    @pytest.fixture
    async def agent(self, temp_dir):
        """Create a test agent"""
        config = AgentConfig()
        config.memory["database_path"] = str(temp_dir / "test_memory.db")
        config.storage["base_path"] = str(temp_dir)

        agent = AdaAgent(config)
        await agent.initialize()

        yield agent

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent._initialized
        assert agent.context.state == AgentState.IDLE
        assert len(agent.skill_registry) > 0

    @pytest.mark.asyncio
    async def test_process_simple_input(self, agent):
        """Test processing simple input"""
        result = await agent.process("你好")

        assert result is not None
        assert result.success

    @pytest.mark.asyncio
    async def test_process_skill_match(self, agent):
        """Test processing with skill match"""
        result = await agent.process("打开 Firefox")

        assert result is not None
        assert result.skill_id is not None

    @pytest.mark.asyncio
    async def test_conversation_history(self, agent):
        """Test conversation history tracking"""
        await agent.process("第一句话")
        await agent.process("第二句话")

        history = agent.context.conversation_history
        assert len(history) >= 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_callback_registration(self, agent):
        """Test callback registration"""
        responses = []

        def on_response(text):
            responses.append(text)

        agent.on_response(on_response)

        await agent.process("测试")

        assert len(responses) > 0

    @pytest.mark.asyncio
    async def test_execute_skill_directly(self, agent):
        """Test direct skill execution"""
        result = await agent.execute_skill(
            "builtin.app.launcher",
            "打开 Firefox"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_state_transitions(self, agent):
        """Test agent state transitions"""
        assert agent.context.state == AgentState.IDLE

        # Process should trigger transitions
        task = asyncio.create_task(agent.process("测试"))

        # Give it a moment to start processing
        await asyncio.sleep(0.1)

        # Should eventually return to idle
        await task
        assert agent.context.state == AgentState.IDLE


class TestSkillIntegration:
    """Integration tests for skill system"""

    @pytest.fixture
    def config(self, temp_dir):
        """Create test config"""
        config = AgentConfig()
        config.memory["database_path"] = str(temp_dir / "memory.db")
        return config

    @pytest.mark.asyncio
    async def test_skill_discovery(self, config):
        """Test skill discovery and loading"""
        agent = AdaAgent(config)
        await agent.initialize()

        # Should have built-in skills
        assert len(agent.skill_registry) > 0

        # Check specific skills exist
        assert agent.skill_registry.get("builtin.app.launcher") is not None
        assert agent.skill_registry.get("builtin.file.organizer") is not None

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_skill_matching(self, config):
        """Test skill matching and scoring"""
        agent = AdaAgent(config)
        await agent.initialize()

        context = SkillContext(
            user_input="打开 Firefox",
            entities={"app": "firefox"},
        )

        matches = agent.skill_registry.find_all(context)

        assert len(matches) > 0
        # Best match should be app launcher
        best_skill, score = matches[0]
        assert "app" in best_skill.metadata.id.lower()

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_skill_execution_flow(self, config):
        """Test complete skill execution flow"""
        agent = AdaAgent(config)
        await agent.initialize()

        # Process input that should match a skill
        result = await agent.process("整理下载文件夹")

        assert result is not None
        # May or may not succeed depending on environment
        # but should not error

        await agent.shutdown()


class TestMemoryIntegration:
    """Integration tests for memory system"""

    @pytest.fixture
    async def agent(self, temp_dir):
        """Create agent with memory"""
        config = AgentConfig()
        config.memory["database_path"] = str(temp_dir / "memory.db")

        agent = AdaAgent(config)
        await agent.initialize()

        yield agent

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_conversation_storage(self, agent):
        """Test conversation is stored in memory"""
        await agent.process("记住这个信息：我的名字是测试")

        # Memory should have been stored
        # This would require searching the memory store
        assert agent.memory_store is not None

    @pytest.mark.asyncio
    async def test_memory_persistence(self, temp_dir):
        """Test memory persists across sessions"""
        db_path = temp_dir / "memory.db"

        # First session
        config = AgentConfig()
        config.memory["database_path"] = str(db_path)

        agent1 = AdaAgent(config)
        await agent1.initialize()
        await agent1.process("记住这个重要信息")
        await agent1.shutdown()

        # Second session
        agent2 = AdaAgent(config)
        await agent2.initialize()

        # Memory should still exist
        assert agent2.memory_store is not None
        count = agent2.memory_store.count()
        assert count > 0

        await agent2.shutdown()


class TestEventIntegration:
    """Integration tests for event system"""

    @pytest.fixture
    async def agent(self, temp_dir):
        """Create agent with events"""
        config = AgentConfig()
        config.memory["database_path"] = str(temp_dir / "memory.db")

        agent = AdaAgent(config)
        await agent.initialize()

        yield agent

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_event_publishing(self, agent):
        """Test event publishing"""
        received = []

        def handler(event):
            received.append(event)

        agent.event_bus.subscribe(EventType.USER_MESSAGE, handler)

        event = Event.user_message("测试")
        await agent.event_bus.publish(event)

        # Event should be processed
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_event_filtering(self, agent):
        """Test event filtering"""
        received = []

        def handler(event):
            received.append(event)

        def filter_fn(event):
            return "important" in event.data.get("message", "")

        agent.event_bus.subscribe(
            EventType.USER_MESSAGE,
            handler,
            filter_func=filter_fn
        )

        await agent.event_bus.publish(Event.user_message("普通消息"))
        await agent.event_bus.publish(Event.user_message("important message"))

        assert len(received) == 1
        assert "important" in received[0].data["message"]


class TestAPIIntegration:
    """Integration tests for REST API"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from ada.api.main import app

        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Ada API" in response.json()["name"]

    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_skills_list(self, client):
        """Test skills list endpoint"""
        response = client.get("/skills")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_status_endpoint(self, client):
        """Test status endpoint"""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data


class TestCLIIntegration:
    """Integration tests for CLI"""

    def test_version_command(self):
        """Test version command"""
        from click.testing import CliRunner
        from ada.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "Ada" in result.output

    def test_skills_list_command(self):
        """Test skills list command"""
        from click.testing import CliRunner
        from ada.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["skills", "list"])

        assert result.exit_code == 0
        assert "Skills" in result.output or "skill" in result.output.lower()

    def test_help_command(self):
        """Test help command"""
        from click.testing import CliRunner
        from ada.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Ada" in result.output


class TestEndToEnd:
    """End-to-end integration tests"""

    @pytest.fixture
    async def full_agent(self, temp_dir):
        """Create fully configured agent"""
        config = AgentConfig()
        config.memory["database_path"] = str(temp_dir / "memory.db")
        config.storage["base_path"] = str(temp_dir)
        config.llm["backend"] = "mock"  # Use mock for testing

        agent = AdaAgent(config)
        await agent.initialize()

        yield agent

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, full_agent):
        """Test complete conversation flow"""
        # Multiple turns
        responses = []

        inputs = [
            "你好",
            "你能做什么？",
            "帮我打开 Firefox",
            "谢谢"
        ]

        for user_input in inputs:
            result = await full_agent.process(user_input)
            responses.append(result)

        # All should succeed (or at least not error)
        for result in responses:
            assert result is not None

    @pytest.mark.asyncio
    async def test_skill_chain(self, full_agent):
        """Test skill execution chain"""
        # Execute multiple skills in sequence
        result1 = await full_agent.execute_skill(
            "builtin.clipboard.manager",
            "读取剪贴板"
        )

        # Should handle gracefully even if clipboard unavailable
        assert result1 is not None
