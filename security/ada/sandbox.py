"""
Sandbox Manager - Bubblewrap-based execution sandboxing
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check for bubblewrap
BWRAP_AVAILABLE = bool(subprocess.run(["which", "bwrap"], capture_output=True).returncode == 0)


@dataclass
class SandboxConfig:
    """
    Configuration for execution sandbox.

    Defines what resources the sandboxed process can access.
    """
    # Network access
    network: bool = False

    # Filesystem access
    read_only_paths: List[str] = field(default_factory=list)
    read_write_paths: List[str] = field(default_factory=list)
    tmpfs_paths: List[str] = field(default_factory=lambda: ["/tmp"])

    # Device access
    allow_gpu: bool = False
    allow_audio: bool = False
    allow_video: bool = False
    allow_usb: bool = False

    # System access
    allow_dbus_system: bool = False
    allow_dbus_session: bool = False
    dbus_talk: List[str] = field(default_factory=list)

    # Environment
    env_vars: Dict[str, str] = field(default_factory=dict)
    clear_env: bool = False

    # Resource limits
    memory_mb: Optional[int] = None
    cpu_percent: Optional[int] = None

    # Security
    no_new_privileges: bool = True
    die_with_parent: bool = True

    # User namespace
    uid: Optional[int] = None
    gid: Optional[int] = None

    def to_bwrap_args(self) -> List[str]:
        """Convert config to bwrap command arguments"""
        args = []

        # Filesystem
        for path in self.read_only_paths:
            args.extend(["--ro-bind", path, path])

        for path in self.read_write_paths:
            args.extend(["--bind", path, path])

        for path in self.tmpfs_paths:
            args.extend(["--tmpfs", path])

        # Network
        if not self.network:
            args.append("--unshare-net")

        # Devices
        if self.allow_gpu:
            args.extend(["--dev-bind", "/dev/dri", "/dev/dri"])

        if self.allow_audio:
            args.extend(["--dev-bind", "/dev/snd", "/dev/snd"])
            # PulseAudio socket
            pulse_socket = os.path.expanduser("~/.config/pulse")
            if os.path.exists(pulse_socket):
                args.extend(["--ro-bind", pulse_socket, pulse_socket])

        if self.allow_video:
            args.extend(["--dev-bind", "/dev/video0", "/dev/video0"])

        # D-Bus
        if self.allow_dbus_system or self.dbus_talk:
            args.extend(["--ro-bind", "/var/run/dbus", "/var/run/dbus"])

        if self.allow_dbus_session:
            dbus_socket = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
            if dbus_socket.startswith("unix:path="):
                socket_path = dbus_socket[10:]
                args.extend(["--ro-bind", socket_path, socket_path])

        # Proxy D-Bus calls through xdg-dbus-proxy if specific talks
        if self.dbus_talk:
            # This would need xdg-dbus-proxy setup
            pass

        # Environment
        if self.clear_env:
            args.append("--clearenv")

        for key, value in self.env_vars.items():
            args.extend(["--setenv", key, value])

        # Security
        if self.no_new_privileges:
            args.append("--new-session")

        if self.die_with_parent:
            args.append("--die-with-parent")

        # User namespace
        if self.uid is not None:
            args.extend(["--uid", str(self.uid)])

        if self.gid is not None:
            args.extend(["--gid", str(self.gid)])

        return args

    @classmethod
    def minimal(cls) -> "SandboxConfig":
        """Create minimal sandbox config"""
        return cls(
            network=False,
            tmpfs_paths=["/tmp", "/var/tmp"],
            no_new_privileges=True,
        )

    @classmethod
    def standard(cls) -> "SandboxConfig":
        """Create standard sandbox config with basic filesystem access"""
        home = str(Path.home())
        return cls(
            network=False,
            read_only_paths=[
                "/usr", "/lib", "/lib64", "/bin", "/sbin",
                "/etc/resolv.conf", "/etc/ssl",
            ],
            read_write_paths=[home],
            tmpfs_paths=["/tmp", "/var/tmp"],
            allow_dbus_session=True,
            dbus_talk=["org.freedesktop.Notifications"],
        )

    @classmethod
    def permissive(cls) -> "SandboxConfig":
        """Create permissive sandbox for trusted operations"""
        return cls(
            network=True,
            read_only_paths=["/usr", "/lib", "/lib64", "/bin", "/sbin"],
            read_write_paths=[str(Path.home())],
            allow_dbus_session=True,
            allow_dbus_system=True,
        )


@dataclass
class SandboxResult:
    """Result from sandboxed execution"""
    success: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SandboxManager:
    """
    Manage sandboxed execution using bubblewrap.

    Provides secure execution environment for untrusted code
    and external commands.
    """

    def __init__(self, default_config: SandboxConfig = None):
        self.default_config = default_config or SandboxConfig.standard()
        self._active_sandboxes: Dict[str, subprocess.Popen] = {}

    @property
    def is_available(self) -> bool:
        """Check if bubblewrap is available"""
        return BWRAP_AVAILABLE

    async def execute(
        self,
        command: List[str],
        config: SandboxConfig = None,
        timeout: int = 30,
        input_data: bytes = None
    ) -> SandboxResult:
        """
        Execute a command in sandbox.

        Args:
            command: Command and arguments to execute
            config: Sandbox configuration (uses default if not provided)
            timeout: Execution timeout in seconds
            input_data: Optional stdin data

        Returns:
            SandboxResult with execution outcome
        """
        config = config or self.default_config

        if not self.is_available:
            logger.warning("Bubblewrap not available, running without sandbox")
            return await self._execute_unsandboxed(command, timeout, input_data)

        # Build bwrap command
        bwrap_cmd = ["bwrap"]
        bwrap_cmd.extend(config.to_bwrap_args())
        bwrap_cmd.extend(command)

        logger.debug(f"Sandbox command: {' '.join(bwrap_cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *bwrap_cmd,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input_data),
                    timeout=timeout
                )

                return SandboxResult(
                    success=process.returncode == 0,
                    returncode=process.returncode,
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    timed_out=False
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                return SandboxResult(
                    success=False,
                    returncode=-1,
                    stdout="",
                    stderr="Command timed out",
                    timed_out=True
                )

        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return SandboxResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(e)
            )

    async def _execute_unsandboxed(
        self,
        command: List[str],
        timeout: int,
        input_data: bytes
    ) -> SandboxResult:
        """Fallback execution without sandbox"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_data),
                timeout=timeout
            )

            return SandboxResult(
                success=process.returncode == 0,
                returncode=process.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace")
            )

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

            return SandboxResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="Command timed out",
                timed_out=True
            )

        except Exception as e:
            return SandboxResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(e)
            )

    async def execute_script(
        self,
        script: str,
        language: str = "python",
        config: SandboxConfig = None,
        timeout: int = 30
    ) -> SandboxResult:
        """
        Execute a script in sandbox.

        Args:
            script: Script content
            language: Script language (python, bash, etc.)
            config: Sandbox configuration
            timeout: Execution timeout

        Returns:
            SandboxResult with script output
        """
        # Create minimal config for scripts
        config = config or SandboxConfig.minimal()

        # Map languages to interpreters
        interpreters = {
            "python": ["python3", "-c"],
            "python3": ["python3", "-c"],
            "bash": ["bash", "-c"],
            "sh": ["sh", "-c"],
        }

        if language not in interpreters:
            return SandboxResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Unsupported language: {language}"
            )

        command = interpreters[language] + [script]

        return await self.execute(command, config, timeout)

    def create_isolated_environment(self, name: str, config: SandboxConfig = None) -> "IsolatedEnvironment":
        """Create an isolated environment for persistent operations"""
        return IsolatedEnvironment(name, config or self.default_config, self)


class IsolatedEnvironment:
    """An isolated environment for running multiple commands"""

    def __init__(self, name: str, config: SandboxConfig, manager: SandboxManager):
        self.name = name
        self.config = config
        self.manager = manager
        self._workdir: Optional[Path] = None

    async def setup(self):
        """Setup the isolated environment"""
        import tempfile
        self._workdir = Path(tempfile.mkdtemp(prefix=f"ada_sandbox_{self.name}_"))
        self.config.read_write_paths.append(str(self._workdir))

    async def execute(self, command: List[str], **kwargs) -> SandboxResult:
        """Execute command in this environment"""
        return await self.manager.execute(command, self.config, **kwargs)

    async def cleanup(self):
        """Cleanup the environment"""
        if self._workdir and self._workdir.exists():
            import shutil
            shutil.rmtree(self._workdir)
