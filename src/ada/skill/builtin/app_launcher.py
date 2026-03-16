"""
App Launcher Skill - Launch and manage applications
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from typing import Dict, Any, List


class AppLauncherSkill(Skill):
    """
    Skill for launching and managing applications.

    Capabilities:
    - Launch applications by name
    - Switch to running applications
    - Close applications
    """

    metadata = SkillMetadata(
        id="builtin.app.launcher",
        name="应用启动器",
        version="1.0.0",
        description="启动、切换和管理应用程序",
        author="Ada Team",
        category="app",
        tags=["app", "launch", "application", "启动", "打开"],
        permissions=["app.launch", "app.switch"],
        examples=[
            "打开 Firefox",
            "启动 VS Code",
            "运行终端",
            "切换到 Chrome"
        ]
    )

    def can_handle(self, context: SkillContext) -> float:
        """Check if this skill matches"""
        launch_keywords = ["打开", "启动", "运行", "open", "launch", "run", "start"]
        switch_keywords = ["切换到", "切换", "switch"]

        user_input = context.user_input.lower()
        score = 0.0

        for kw in launch_keywords:
            if kw in user_input:
                score += 0.4

        for kw in switch_keywords:
            if kw in user_input:
                score += 0.4

        # Check for app name entity
        if context.entities and context.entities.get("app"):
            score += 0.3

        return min(score, 1.0)

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute app launch/switch"""
        entities = context.entities
        user_input = context.user_input

        # Extract app name
        app_name = entities.get("app") or entities.get("application")
        if not app_name:
            app_name = self._extract_app_name(user_input)

        if not app_name:
            return SkillResult.fail("未识别到应用名称")

        # Detect action type
        action = self._detect_action(user_input)

        try:
            if action == "launch":
                result = await context.executor.execute({
                    "type": "app.launch",
                    "params": {"name": app_name}
                })
                action_desc = "启动"

            elif action == "switch":
                result = await context.executor.execute({
                    "type": "app.switch",
                    "params": {"name": app_name}
                })
                action_desc = "切换到"

            elif action == "close":
                result = await context.executor.execute({
                    "type": "app.close",
                    "params": {"name": app_name}
                })
                action_desc = "关闭"

            else:
                result = await context.executor.execute({
                    "type": "app.launch",
                    "params": {"name": app_name}
                })
                action_desc = "启动"

            if result.success:
                return SkillResult.ok(
                    message=f"已{action_desc} {app_name}",
                    output={"app": app_name, "action": action}
                )
            else:
                return SkillResult.fail(result.error or f"无法{action_desc} {app_name}")

        except Exception as e:
            return SkillResult.fail(str(e))

    def _extract_app_name(self, text: str) -> str:
        """Extract app name from user input"""
        import re

        # Common patterns
        patterns = [
            r"打开\s*(.+?)(?:\s|$)",
            r"启动\s*(.+?)(?:\s|$)",
            r"运行\s*(.+?)(?:\s|$)",
            r"launch\s+(.+?)(?:\s|$)",
            r"open\s+(.+?)(?:\s|$)",
            r"start\s+(.+?)(?:\s|$)",
            r"切换到\s*(.+?)(?:\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _detect_action(self, text: str) -> str:
        """Detect action from text"""
        text = text.lower()

        if any(kw in text for kw in ["关闭", "退出", "close", "quit", "exit"]):
            return "close"
        if any(kw in text for kw in ["切换", "switch"]):
            return "switch"
        return "launch"
