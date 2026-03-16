"""
System Control Skill - System power and settings management
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from typing import Dict, Any, List
import subprocess
import asyncio


class SystemControlSkill(Skill):
    """
    Skill for system control operations.

    Capabilities:
    - Shutdown/Reboot/Suspend
    - Volume control
    - Brightness control
    - System information
    """

    metadata = SkillMetadata(
        id="builtin.system.control",
        name="系统控制",
        version="1.0.0",
        description="控制系统电源、音量、亮度等设置",
        author="Ada Team",
        category="system",
        tags=["system", "power", "volume", "brightness", "系统", "电源", "音量"],
        permissions=["system.power", "system.settings"],
        examples=[
            "关机",
            "重启电脑",
            "把音量调到50%",
            "调暗屏幕",
            "系统信息"
        ]
    )

    # Destructive actions that require confirmation
    DESTRUCTIVE_ACTIONS = ["shutdown", "reboot"]

    def can_handle(self, context: SkillContext) -> float:
        """Check if this skill matches"""
        power_keywords = ["关机", "重启", "睡眠", "休眠", "shutdown", "reboot", "suspend", "hibernate"]
        volume_keywords = ["音量", "volume", "静音", "mute", "大声", "小声"]
        brightness_keywords = ["亮度", "brightness", "调亮", "调暗", "屏幕"]
        info_keywords = ["系统信息", "system info", "系统状态"]

        user_input = context.user_input.lower()
        score = 0.0

        for kw in power_keywords:
            if kw in user_input:
                score += 0.5

        for kw in volume_keywords:
            if kw in user_input:
                score += 0.5

        for kw in brightness_keywords:
            if kw in user_input:
                score += 0.5

        for kw in info_keywords:
            if kw in user_input:
                score += 0.5

        return min(score, 1.0)

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute system control"""
        user_input = context.user_input.lower()
        entities = context.entities

        # Detect action
        action = self._detect_action(user_input)

        try:
            if action == "shutdown":
                return await self._handle_shutdown(context)

            elif action == "reboot":
                return await self._handle_reboot(context)

            elif action == "suspend":
                return await self._suspend()

            elif action == "volume":
                return await self._handle_volume(user_input, entities)

            elif action == "brightness":
                return await self._handle_brightness(user_input, entities)

            elif action == "info":
                return await self._get_system_info()

            else:
                return SkillResult.fail("无法识别的系统操作")

        except Exception as e:
            return SkillResult.fail(f"系统操作失败: {e}")

    def _detect_action(self, text: str) -> str:
        """Detect action from text"""
        text = text.lower()

        if any(kw in text for kw in ["关机", "shutdown", "power off"]):
            return "shutdown"

        if any(kw in text for kw in ["重启", "reboot", "restart"]):
            return "reboot"

        if any(kw in text for kw in ["睡眠", "休眠", "suspend", "sleep"]):
            return "suspend"

        if any(kw in text for kw in ["音量", "volume", "静音", "mute"]):
            return "volume"

        if any(kw in text for kw in ["亮度", "brightness", "屏幕"]):
            return "brightness"

        if any(kw in text for kw in ["系统信息", "system info"]):
            return "info"

        return "unknown"

    async def _handle_shutdown(self, context: SkillContext) -> SkillResult:
        """Handle shutdown (requires confirmation)"""
        return SkillResult(
            success=True,
            requires_confirmation=True,
            confirmation_message="确定要关机吗？",
            output={"action": "shutdown"}
        )

    async def _handle_reboot(self, context: SkillContext) -> SkillResult:
        """Handle reboot (requires confirmation)"""
        return SkillResult(
            success=True,
            requires_confirmation=True,
            confirmation_message="确定要重启吗？",
            output={"action": "reboot"}
        )

    async def _suspend(self) -> SkillResult:
        """Suspend the system"""
        try:
            result = await self._run_command(["systemctl", "suspend"])
            if result["success"]:
                return SkillResult.ok(message="系统正在进入睡眠模式")
            return SkillResult.fail("无法进入睡眠模式")
        except Exception as e:
            return SkillResult.fail(str(e))

    async def _handle_volume(self, text: str, entities: Dict) -> SkillResult:
        """Handle volume control"""
        import re

        # Extract volume level
        match = re.search(r"(\d+)\s*%?", text)
        level = int(match.group(1)) if match else None

        # Check for mute
        if "静音" in text or "mute" in text:
            result = await self._run_command(
                ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]
            )
            if result["success"]:
                return SkillResult.ok(message="已切换静音状态")
            return SkillResult.fail("无法切换静音")

        # Get current volume
        if "音量" in text and ("多少" in text or "current" in text or "get" in text):
            result = await self._run_command(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"]
            )
            if result["success"]:
                volume = result["output"].strip()
                return SkillResult.ok(message=f"当前音量: {volume}")
            return SkillResult.fail("无法获取音量")

        # Set volume
        if level is not None:
            level = max(0, min(100, level))  # Clamp to 0-100

            # Check for increase/decrease
            if "增加" in text or "提高" in text or "increase" in text or "大声" in text:
                # Increase by percentage
                result = await self._run_command(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{level}%"]
                )
            elif "减少" in text or "降低" in text or "decrease" in text or "小声" in text:
                result = await self._run_command(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{level}%"]
                )
            else:
                # Set absolute value
                result = await self._run_command(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"]
                )

            if result["success"]:
                return SkillResult.ok(message=f"音量已调整到 {level}%")
            return SkillResult.fail("无法调整音量")

        return SkillResult.fail("请指定音量值，例如：把音量调到50%")

    async def _handle_brightness(self, text: str, entities: Dict) -> SkillResult:
        """Handle brightness control"""
        import re

        # Extract brightness level
        match = re.search(r"(\d+)\s*%?", text)
        level = int(match.group(1)) if match else None

        # Get current brightness
        if "亮度" in text and ("多少" in text or "current" in text):
            result = await self._run_command(["brightnessctl", "get"])
            if result["success"]:
                return SkillResult.ok(message=f"当前亮度: {result['output'].strip()}")
            return SkillResult.fail("无法获取亮度")

        # Set brightness
        if level is not None:
            level = max(0, min(100, level))

            if "增加" in text or "提高" in text or "调亮" in text:
                result = await self._run_command(
                    ["brightnessctl", "set", f"+{level}%"]
                )
            elif "减少" in text or "降低" in text or "调暗" in text:
                result = await self._run_command(
                    ["brightnessctl", "set", f"{level}%"]
                )
            else:
                result = await self._run_command(
                    ["brightnessctl", "set", f"{level}%"]
                )

            if result["success"]:
                return SkillResult.ok(message=f"亮度已调整到 {level}%")
            return SkillResult.fail("无法调整亮度")

        # Simple increase/decrease without number
        if "调亮" in text or "增加亮度" in text:
            result = await self._run_command(["brightnessctl", "set", "+10%"])
            if result["success"]:
                return SkillResult.ok(message="亮度已增加")

        if "调暗" in text or "减少亮度" in text:
            result = await self._run_command(["brightnessctl", "set", "10%-"])
            if result["success"]:
                return SkillResult.ok(message="亮度已降低")

        return SkillResult.fail("请指定亮度值，例如：把亮度调到80%")

    async def _get_system_info(self) -> SkillResult:
        """Get system information"""
        info = {}

        # Get hostname
        result = await self._run_command(["hostname"])
        if result["success"]:
            info["hostname"] = result["output"].strip()

        # Get OS info
        result = await self._run_command(["uname", "-a"])
        if result["success"]:
            info["kernel"] = result["output"].strip()

        # Get CPU info
        result = await self._run_command(["cat", "/proc/cpuinfo"])
        if result["success"]:
            lines = result["output"].split("\n")
            for line in lines:
                if "model name" in line.lower():
                    info["cpu"] = line.split(":")[1].strip()
                    break

        # Get memory info
        result = await self._run_command(["free", "-h"])
        if result["success"]:
            lines = result["output"].split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    info["memory"] = f"总计: {parts[1]}, 已用: {parts[2]}"

        # Get disk info
        result = await self._run_command(["df", "-h", "/"])
        if result["success"]:
            lines = result["output"].split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    info["disk"] = f"总计: {parts[1]}, 已用: {parts[2]}, 可用: {parts[3]}"

        # Get uptime
        result = await self._run_command(["uptime", "-p"])
        if result["success"]:
            info["uptime"] = result["output"].strip().replace("up ", "")

        # Format message
        message_parts = ["系统信息:"]
        for key, value in info.items():
            key_names = {
                "hostname": "主机名",
                "kernel": "内核",
                "cpu": "处理器",
                "memory": "内存",
                "disk": "磁盘",
                "uptime": "运行时间"
            }
            message_parts.append(f"  {key_names.get(key, key)}: {value}")

        return SkillResult.ok(
            message="\n".join(message_parts),
            output=info
        )

    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run a command asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8", errors="replace"),
                "error": stderr.decode("utf-8", errors="replace"),
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }
