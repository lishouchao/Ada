"""
Built-in Skills - Pre-packaged with Ada
"""

from ada.skill.builtin.file_organizer import FileOrganizerSkill
from ada.skill.builtin.app_launcher import AppLauncherSkill
from ada.skill.builtin.system_control import SystemControlSkill
from ada.skill.builtin.web_search import WebSearchSkill
from ada.skill.builtin.calendar_reminder import CalendarReminderSkill
from ada.skill.builtin.clipboard_manager import ClipboardManagerSkill

__all__ = [
    "FileOrganizerSkill",
    "AppLauncherSkill",
    "SystemControlSkill",
    "WebSearchSkill",
    "CalendarReminderSkill",
    "ClipboardManagerSkill",
]

# Skill list for easy registration
BUILTIN_SKILLS = [
    FileOrganizerSkill,
    AppLauncherSkill,
    SystemControlSkill,
    WebSearchSkill,
    CalendarReminderSkill,
    ClipboardManagerSkill,
]
