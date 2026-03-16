"""
Ada Skill System - Modular, reusable capabilities

Skills are modular capabilities that can be discovered,
matched to intents, and executed by the agent.
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from ada.skill.registry import SkillRegistry
from ada.skill.loader import SkillLoader

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillContext",
    "SkillResult",
    "SkillRegistry",
    "SkillLoader",
]
