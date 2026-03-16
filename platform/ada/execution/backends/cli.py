"""
CLI Backend - Execute actions via command-line tools
"""

import asyncio
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from ada.platform.execution.backends import ExecutionBackend, BackendResult

logger = logging.getLogger(__name__)


class CLIBackend(ExecutionBackend):
    """
    Execute actions via command-line tools.

    Provides fallback execution for actions that don't have
    API or D-Bus interfaces available.
    """

    def __init__(self):
        self._commands = self._build_command_map()

    @property
    def name(self) -> str:
        return "cli"

    @property
    def priority(self) -> int:
        return 30  # Third priority after D-Bus

    async def is_available(self) -> bool:
        """CLI is always available"""
        return True

    def _build_command_map(self) -> Dict[str, Dict[str, Any]]:
        """Build mapping of action types to CLI commands"""
        return {
            "app.launch": {
                "cmd": ["gtk-launch", "{name}"],
                "fallback": ["{name}"],
            },
            "file.open": {
                "cmd": ["xdg-open", "{path}"],
            },
            "file.copy": {
                "cmd": ["cp", "-r", "{source}", "{target}"],
            },
            "file.move": {
                "cmd": ["mv", "{source}", "{target}"],
            },
            "file.delete": {
                "cmd": ["rm", "-rf", "{path}"],
                "requires_confirmation": True,
            },
            "file.list": {
                "cmd": ["ls", "-la", "{path}"],
                "parse_output": True,
            },
            "file.mkdir": {
                "cmd": ["mkdir", "-p", "{path}"],
            },
            "directory.open": {
                "cmd": ["xdg-open", "{path}"],
            },
            "web.open": {
                "cmd": ["xdg-open", "{url}"],
            },
            "system.shutdown": {
                "cmd": ["systemctl", "poweroff"],
                "requires_confirmation": True,
                "requires_sudo": True,
            },
            "system.reboot": {
                "cmd": ["systemctl", "reboot"],
                "requires_confirmation": True,
                "requires_sudo": True,
            },
            "volume.set": {
                "cmd": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "{volume}%"],
            },
            "volume.mute": {
                "cmd": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            },
            "brightness.set": {
                "cmd": ["brightnessctl", "set", "{level}%"],
            },
            "screenshot.take": {
                "cmd": ["gnome-screenshot", "-f", "{output}"],
            },
            "process.kill": {
                "cmd": ["kill", "{pid}"],
                "requires_confirmation": True,
            },
            "package.install": {
                "cmd": ["flatpak", "install", "-y", "{package}"],
            },
        }

    async def can_execute(self, action: Dict[str, Any]) -> bool:
        """Check if action can be executed via CLI"""
        action_type = action.get("type", "")
        return action_type in self._commands

    async def execute(self, action: Dict[str, Any]) -> BackendResult:
        """Execute action via CLI"""
        action_type = action.get("type")
        params = action.get("params", {})

        if action_type not in self._commands:
            return BackendResult.fail(f"Unknown CLI action: {action_type}", self.name)

        command_info = self._commands[action_type]

        # Check for required confirmation
        if command_info.get("requires_confirmation"):
            # This should be handled at higher level
            pass

        # Build command
        cmd_template = command_info["cmd"]
        cmd = self._build_command(cmd_template, params)

        # Check if command exists
        if not shutil.which(cmd[0]):
            # Try fallback
            fallback = command_info.get("fallback")
            if fallback:
                cmd = self._build_command(fallback, params)
                if not shutil.which(cmd[0]):
                    return BackendResult.fail(f"Command not found: {cmd[0]}", self.name)
            else:
                return BackendResult.fail(f"Command not found: {cmd[0]}", self.name)

        try:
            # Execute command
            result = await self._run_command(
                cmd,
                needs_sudo=command_info.get("requires_sudo", False)
            )

            if result["success"]:
                output = result.get("output", "")

                # Parse output if needed
                if command_info.get("parse_output"):
                    output = self._parse_output(action_type, output)

                return BackendResult.ok(output, self.name)
            else:
                return BackendResult.fail(result.get("error", "Command failed"), self.name)

        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return BackendResult.fail(str(e), self.name)

    def _build_command(self, template: List[str], params: Dict[str, Any]) -> List[str]:
        """Build command from template and parameters"""
        cmd = []
        for part in template:
            # Replace placeholders
            for key, value in params.items():
                placeholder = "{" + key + "}"
                if placeholder in part:
                    part = part.replace(placeholder, str(value))
            cmd.append(part)
        return cmd

    async def _run_command(
        self,
        cmd: List[str],
        needs_sudo: bool = False,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Run a command asynchronously"""
        if needs_sudo:
            cmd = ["pkexec"] + cmd

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8", errors="replace"),
                "error": stderr.decode("utf-8", errors="replace"),
                "returncode": process.returncode,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Command timed out",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _parse_output(self, action_type: str, output: str) -> Any:
        """Parse command output based on action type"""
        if action_type == "file.list":
            return self._parse_ls_output(output)
        return output

    def _parse_ls_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse ls -la output into structured data"""
        files = []
        lines = output.strip().split("\n")

        # Skip total line
        for line in lines[1:]:
            if not line.strip():
                continue

            parts = line.split(None, 8)
            if len(parts) >= 9:
                perms = parts[0]
                size = parts[4]
                name = parts[8]

                files.append({
                    "name": name,
                    "is_dir": perms.startswith("d"),
                    "size": self._parse_size(size),
                    "permissions": perms,
                })

        return files

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        try:
            return int(size_str)
        except ValueError:
            return 0
