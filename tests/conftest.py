"""
Pytest configuration and fixtures for Ada tests
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from typing import Generator

# Configure asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def temp_config(temp_dir: Path) -> dict:
    """Create a temporary configuration"""
    return {
        "agent": {
            "name": "TestAda",
            "mode": "test",
        },
        "llm": {
            "backend": "mock",
            "model": "test-model",
        },
        "memory": {
            "backend": "sqlite",
            "database_path": str(temp_dir / "test_memory.db"),
        },
        "storage": {
            "base_path": str(temp_dir),
        },
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return {
        "content": "This is a test response",
        "model": "test-model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }


@pytest.fixture
def sample_user_input():
    """Sample user inputs for testing"""
    return {
        "file_organize": "整理下载文件夹",
        "app_launch": "打开 Firefox",
        "system_info": "显示系统信息",
        "reminder": "10分钟后提醒我开会",
        "volume": "把音量调到50%",
    }


@pytest.fixture
def sample_skill_context():
    """Sample skill context for testing"""
    from ada.skill.base import SkillContext

    return SkillContext(
        user_input="测试输入",
        entities={"app": "firefox", "path": "/home/user/Downloads"},
        conversation_history=[],
        user_preferences={},
        executor=None,
    )
