"""
Clipboard Manager Skill - Clipboard operations
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from typing import Dict, Any, List, Optional
import subprocess
import asyncio


class ClipboardManagerSkill(Skill):
    """
    Skill for clipboard management.

    Capabilities:
    - Copy text to clipboard
    - Read clipboard content
    - Clipboard history (basic)
    """

    metadata = SkillMetadata(
        id="builtin.clipboard.manager",
        name="剪贴板管理",
        version="1.0.0",
        description="管理剪贴板内容，支持复制、读取和历史记录",
        author="Ada Team",
        category="utility",
        tags=["clipboard", "copy", "paste", "剪贴板", "复制", "粘贴"],
        permissions=["clipboard.read", "clipboard.write"],
        examples=[
            "复制这段文字到剪贴板",
            "读取剪贴板内容",
            "把剪贴板的内容保存到文件"
        ]
    )

    def __init__(self):
        self._history: List[str] = []
        self._max_history = 100

    def can_handle(self, context: SkillContext) -> float:
        """Check if this skill matches"""
        keywords = [
            "剪贴板", "复制", "粘贴", "clipboard", "copy", "paste"
        ]

        user_input = context.user_input.lower()
        score = 0.0

        for kw in keywords:
            if kw in user_input:
                score += 0.4

        return min(score, 1.0)

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute clipboard action"""
        user_input = context.user_input.lower()
        entities = context.entities

        # Detect action
        action = self._detect_action(user_input)

        try:
            if action == "copy":
                return await self._copy_to_clipboard(user_input, entities)

            elif action == "read":
                return await self._read_clipboard()

            elif action == "save":
                return await self._save_to_file(user_input, entities)

            elif action == "history":
                return await self._show_history()

            else:
                return SkillResult.fail("无法识别的剪贴板操作")

        except Exception as e:
            return SkillResult.fail(f"剪贴板操作失败: {e}")

    def _detect_action(self, text: str) -> str:
        """Detect action from text"""
        text = text.lower()

        if any(kw in text for kw in ["读取", "获取", "显示", "read", "get", "show"]):
            return "read"

        if any(kw in text for kw in ["保存", "写入", "save", "write"]):
            return "save"

        if any(kw in text for kw in ["历史", "记录", "history"]):
            return "history"

        return "copy"

    async def _copy_to_clipboard(self, text: str, entities: Dict) -> SkillResult:
        """Copy text to clipboard"""
        import re

        # Extract text to copy
        patterns = [
            r"复制\s*[\"'](.+?)[\"']",
            r"复制\s*['\"](.+?)['\"]",
            r"复制\s*(.+?)(?:到剪贴板)?$",
            r"copy\s+[\"'](.+?)[\"']",
        ]

        content = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                break

        if not content:
            return SkillResult.fail("请提供要复制的内容")

        # Copy to clipboard
        try:
            # Try wl-copy (Wayland)
            process = await asyncio.create_subprocess_exec(
                "wl-copy",
                stdin=asyncio.subprocess.PIPE
            )
            await process.communicate(content.encode())

            if process.returncode != 0:
                # Fall back to xclip (X11)
                process = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard",
                    stdin=asyncio.subprocess.PIPE
                )
                await process.communicate(content.encode())

            # Add to history
            self._add_to_history(content)

            preview = content[:50] + "..." if len(content) > 50 else content
            return SkillResult.ok(
                message=f"已复制到剪贴板: {preview}",
                output={"content": content}
            )

        except Exception as e:
            return SkillResult.fail(f"复制失败: {e}")

    async def _read_clipboard(self) -> SkillResult:
        """Read clipboard content"""
        try:
            # Try wl-paste (Wayland)
            process = await asyncio.create_subprocess_exec(
                "wl-paste",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                # Fall back to xclip (X11)
                process = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard", "-o",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

            if process.returncode == 0:
                content = stdout.decode("utf-8", errors="replace")

                # Add to history
                self._add_to_history(content)

                preview = content[:200] + "..." if len(content) > 200 else content
                return SkillResult.ok(
                    message=f"剪贴板内容:\n{preview}",
                    output={"content": content}
                )

            return SkillResult.fail("无法读取剪贴板")

        except Exception as e:
            return SkillResult.fail(f"读取失败: {e}")

    async def _save_to_file(self, text: str, entities: Dict) -> SkillResult:
        """Save clipboard content to file"""
        # Get clipboard content first
        read_result = await self._read_clipboard()

        if not read_result.success:
            return read_result

        content = read_result.output.get("content", "")

        # Get file path
        import re
        match = re.search(r"保存(?:到)?\s*(.+?)(?:文件)?$", text)
        file_path = match.group(1).strip() if match else None

        if not file_path:
            file_path = entities.get("path")

        if not file_path:
            return SkillResult.fail("请指定保存路径")

        # Expand path
        from pathlib import Path
        file_path = Path(file_path).expanduser()

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                f.write(content)

            return SkillResult.ok(
                message=f"已保存到 {file_path}",
                output={"path": str(file_path), "size": len(content)}
            )

        except Exception as e:
            return SkillResult.fail(f"保存失败: {e}")

    async def _show_history(self) -> SkillResult:
        """Show clipboard history"""
        if not self._history:
            return SkillResult.ok(message="剪贴板历史为空")

        lines = ["剪贴板历史:"]
        for i, item in enumerate(self._history[-10:], 1):
            preview = item[:30] + "..." if len(item) > 30 else item
            preview = preview.replace("\n", " ")
            lines.append(f"  {i}. {preview}")

        return SkillResult.ok(
            message="\n".join(lines),
            output={"history": self._history[-10:]}
        )

    def _add_to_history(self, content: str):
        """Add content to history"""
        if content and content not in self._history:
            self._history.append(content)
            if len(self._history) > self._max_history:
                self._history.pop(0)
