"""
Note Taker Skill Handler

A simple skill for taking quick notes.
"""

from ada.skill.base import SkillContext, SkillResult
from pathlib import Path
from datetime import datetime
import re


async def handle(context: SkillContext) -> SkillResult:
    """
    Handle note-taking request.

    Args:
        context: Skill context

    Returns:
        SkillResult with note status
    """
    user_input = context.user_input
    entities = context.entities or {}

    # Extract note content
    note_content = extract_note_content(user_input)

    if not note_content:
        return SkillResult.fail("请提供要记录的内容")

    # Get notes file path
    notes_dir = Path.home() / "Documents" / "Notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    notes_file = notes_dir / "ada_notes.md"

    # Format note
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    formatted_note = f"\n## {timestamp}\n\n{note_content}\n"

    # Append to file
    try:
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(formatted_note)

        return SkillResult.ok(
            message=f"已记录到 {notes_file}",
            output={
                "content": note_content,
                "file": str(notes_file),
                "timestamp": timestamp
            }
        )

    except Exception as e:
        return SkillResult.fail(f"记录失败: {str(e)}")


def extract_note_content(text: str) -> str:
    """Extract note content from user input"""
    # Remove command phrases
    patterns = [
        r"^(?:记录|记下|帮我记|记住|把.*?记到笔记里)\s*",
        r"^(?:note|remember)\s+(?:that\s+)?",
    ]

    content = text.strip()

    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.IGNORECASE)

    return content.strip()
