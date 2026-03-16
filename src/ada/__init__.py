"""
Ada - NebulaOS Intelligent Assistant

Named after Ada Lovelace, the first programmer.

Ada is an OS-integrated AI assistant that provides:
- UI tree perception via AT-SPI
- Hybrid execution (API > DBus > CLI > GUI)
- Skill-based task automation
- Local memory and context awareness

Example:
    >>> from ada import Ada
    >>> async with Ada() as agent:
    ...     result = await agent.execute("整理下载文件夹")
    ...     print(result)
"""

__version__ = "0.1.0"
__author__ = "NebulaOS Team"
__license__ = "GPL-3.0-or-later"

from ada.core import Agent, AgentState, AgentConfig
from ada.skill import Skill, SkillRegistry, SkillContext, SkillResult

__all__ = [
    "Agent",
    "AgentState",
    "AgentConfig",
    "Skill",
    "SkillRegistry",
    "SkillContext",
    "SkillResult",
]
