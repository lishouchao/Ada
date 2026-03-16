"""
Tests for skill system
"""

import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from ada.skill.registry import SkillRegistry
from ada.skill.loader import SkillLoader
from ada.skill.builtin.file_organizer import FileOrganizerSkill
from ada.skill.builtin.app_launcher import AppLauncherSkill


class TestSkillBase:
    """Tests for skill base classes"""

    def test_skill_metadata(self):
        """Test skill metadata creation"""
        metadata = SkillMetadata(
            id="test.skill",
            name="Test Skill",
            version="1.0.0",
            description="A test skill",
            author="Test Author",
            category="test",
            tags=["test", "example"],
            permissions=["test.read"],
            examples=["test example"],
        )

        assert metadata.id == "test.skill"
        assert metadata.name == "Test Skill"
        assert "test" in metadata.tags

    def test_skill_context(self):
        """Test skill context creation"""
        context = SkillContext(
            user_input="测试输入",
            entities={"app": "firefox"},
            conversation_history=[],
            user_preferences={"language": "zh-CN"},
            executor=None,
        )

        assert context.user_input == "测试输入"
        assert context.entities["app"] == "firefox"

    def test_skill_result(self):
        """Test skill result creation"""
        # OK result
        result = SkillResult.ok(message="Success", output={"key": "value"})
        assert result.success
        assert result.message == "Success"
        assert result.output["key"] == "value"

        # Fail result
        result = SkillResult.fail("Error message")
        assert not result.success
        assert result.error == "Error message"

        # Result requiring confirmation
        result = SkillResult(
            success=True,
            requires_confirmation=True,
            confirmation_message="Confirm?",
        )
        assert result.requires_confirmation


class TestFileOrganizerSkill:
    """Tests for file organizer skill"""

    def test_skill_metadata(self):
        """Test file organizer metadata"""
        skill = FileOrganizerSkill()

        assert skill.metadata.id == "builtin.file.organizer"
        assert skill.metadata.category == "file"
        assert "整理" in skill.metadata.tags

    def test_can_handle(self):
        """Test intent matching"""
        skill = FileOrganizerSkill()

        context = SkillContext(
            user_input="整理下载文件夹",
            entities={},
        )

        score = skill.can_handle(context)
        assert score > 0.3

    def test_strategy_detection(self):
        """Test organization strategy detection"""
        skill = FileOrganizerSkill()

        assert skill._detect_strategy("按类型整理") == "by_type"
        assert skill._detect_strategy("按日期归档") == "by_date"
        assert skill._detect_strategy("按大小分类") == "by_size"

    def test_file_categorization(self):
        """Test file categorization"""
        skill = FileOrganizerSkill()

        # Test different file types
        assert skill._get_file_category({"name": "doc.pdf"}) == "documents"
        assert skill._get_file_category({"name": "image.jpg"}) == "images"
        assert skill._get_file_category({"name": "video.mp4"}) == "videos"
        assert skill._get_file_category({"name": "code.py"}) == "code"


class TestAppLauncherSkill:
    """Tests for app launcher skill"""

    def test_skill_metadata(self):
        """Test app launcher metadata"""
        skill = AppLauncherSkill()

        assert skill.metadata.id == "builtin.app.launcher"
        assert skill.metadata.category == "app"
        assert "启动" in skill.metadata.tags

    def test_can_handle(self):
        """Test intent matching"""
        skill = AppLauncherSkill()

        # Launch intent
        context = SkillContext(
            user_input="打开 Firefox",
            entities={"app": "firefox"},
        )
        score = skill.can_handle(context)
        assert score > 0.3

        # Switch intent
        context = SkillContext(
            user_input="切换到 Chrome",
            entities={},
        )
        score = skill.can_handle(context)
        assert score > 0.3

    def test_action_detection(self):
        """Test action detection"""
        skill = AppLauncherSkill()

        assert skill._detect_action("打开 Firefox") == "launch"
        assert skill._detect_action("关闭终端") == "close"
        assert skill._detect_action("切换到 VS Code") == "switch"

    def test_app_name_extraction(self):
        """Test app name extraction"""
        skill = AppLauncherSkill()

        assert skill._extract_app_name("打开 Firefox") == "Firefox"
        assert skill._extract_app_name("启动 VS Code") == "VS Code"
        assert skill._extract_app_name("运行终端") == "终端"


class TestSkillRegistry:
    """Tests for skill registry"""

    def test_register_skill(self):
        """Test skill registration"""
        registry = SkillRegistry()
        skill = FileOrganizerSkill()

        registry.register(skill)

        assert "builtin.file.organizer" in registry

    def test_unregister_skill(self):
        """Test skill unregistration"""
        registry = SkillRegistry()
        skill = FileOrganizerSkill()

        registry.register(skill)
        registry.unregister("builtin.file.organizer")

        assert "builtin.file.organizer" not in registry

    def test_find_best_skill(self):
        """Test finding best matching skill"""
        registry = SkillRegistry()
        registry.register(FileOrganizerSkill())
        registry.register(AppLauncherSkill())

        context = SkillContext(
            user_input="整理下载文件夹",
            entities={},
        )

        result = registry.find_best(context)
        assert result is not None
        skill, score = result
        assert skill.metadata.id == "builtin.file.organizer"

    def test_list_skills(self):
        """Test listing skills"""
        registry = SkillRegistry()
        registry.register(FileOrganizerSkill())
        registry.register(AppLauncherSkill())

        skills = registry.list_skills()
        assert len(skills) == 2

        # Filter by category
        file_skills = registry.list_skills(category="file")
        assert len(file_skills) == 1

    def test_search_skills(self):
        """Test searching skills"""
        registry = SkillRegistry()
        registry.register(FileOrganizerSkill())
        registry.register(AppLauncherSkill())

        results = registry.search("整理")
        assert len(results) == 1
        assert results[0].metadata.id == "builtin.file.organizer"
