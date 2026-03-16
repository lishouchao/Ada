"""
Hybrid Executor - Multi-path execution engine

The executor provides a hybrid execution model that automatically
selects the optimal path for each action:
  API > DBus > CLI > GUI

This ensures maximum efficiency while maintaining compatibility.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, TypeVar
from enum import Enum
import asyncio
import time


class ExecutionPath(Enum):
    """Available execution paths"""
    API = "api"       # Direct API call (fastest)
    DBUS = "dbus"     # D-Bus method call
    CLI = "cli"       # Command line tool
    GUI = "gui"       # GUI automation (AT-SPI)


@dataclass
class ExecutionResult:
    """Result of action execution"""
    success: bool
    path: ExecutionPath
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0
    fallback_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """Action definition for execution"""
    type: str                              # Action type (e.g., "file.read", "app.launch")
    target: Optional[str] = None           # Target element reference (role:name:nth)
    params: Dict[str, Any] = field(default_factory=dict)
    fallback_paths: List[ExecutionPath] = field(default_factory=list)
    timeout: float = 30.0
    retry_count: int = 1

    def __post_init__(self):
        if not self.fallback_paths:
            # Default fallback chain
            self.fallback_paths = [ExecutionPath.API, ExecutionPath.DBUS, ExecutionPath.CLI, ExecutionPath.GUI]


class ExecutionBackend(ABC):
    """Abstract base class for execution backends"""

    @property
    @abstractmethod
    def path(self) -> ExecutionPath:
        """Return the execution path type"""
        pass

    @abstractmethod
    async def can_execute(self, action: Action) -> bool:
        """Check if this backend can execute the action"""
        pass

    @abstractmethod
    async def execute(self, action: Action) -> ExecutionResult:
        """Execute the action"""
        pass


class Executor:
    """
    Hybrid executor that selects the optimal execution path.

    Execution priority:
    1. API - Direct function calls (fastest, most reliable)
    2. DBus - Inter-process communication
    3. CLI - Command line tools
    4. GUI - AT-SPI automation (most universal but slowest)

    Example:
        executor = Executor()
        executor.register_backend(api_backend)
        executor.register_backend(dbus_backend)

        result = await executor.execute(
            Action(type="file.read", params={"path": "/home/user/doc.txt"})
        )
    """

    def __init__(self):
        self._backends: Dict[ExecutionPath, ExecutionBackend] = {}
        self._preferred_path: Optional[ExecutionPath] = None
        self._before_hooks: List[Callable] = []
        self._after_hooks: List[Callable] = []

    def register_backend(self, backend: ExecutionBackend):
        """Register an execution backend"""
        self._backends[backend.path] = backend

    def set_preferred_path(self, path: ExecutionPath):
        """Set preferred execution path"""
        self._preferred_path = path

    def add_before_hook(self, hook: Callable[[Action], None]):
        """Add pre-execution hook"""
        self._before_hooks.append(hook)

    def add_after_hook(self, hook: Callable[[Action, ExecutionResult], None]):
        """Add post-execution hook"""
        self._after_hooks.append(hook)

    async def execute(
        self,
        action: Action,
        preferred: ExecutionPath = None
    ) -> ExecutionResult:
        """
        Execute an action using the optimal path.

        Args:
            action: The action to execute
            preferred: Optional preferred execution path

        Returns:
            ExecutionResult with success status and output
        """
        # Run before hooks
        for hook in self._before_hooks:
            hook(action)

        # Determine execution order
        paths = self._get_execution_order(preferred or self._preferred_path, action)
        errors = []

        for path in paths:
            backend = self._backends.get(path)
            if not backend:
                continue

            if not await backend.can_execute(action):
                continue

            start = time.time()
            try:
                result = await asyncio.wait_for(
                    backend.execute(action),
                    timeout=action.timeout
                )
                result.path = path
                result.duration_ms = int((time.time() - start) * 1000)
                result.fallback_used = (path != paths[0])

                # Run after hooks
                for hook in self._after_hooks:
                    hook(action, result)

                return result

            except asyncio.TimeoutError:
                errors.append(f"{path.value}: timeout")
            except Exception as e:
                errors.append(f"{path.value}: {str(e)}")

        # All paths failed
        result = ExecutionResult(
            success=False,
            path=ExecutionPath.GUI,
            output=None,
            error="All execution paths failed: " + "; ".join(errors)
        )

        # Run after hooks even on failure
        for hook in self._after_hooks:
            hook(action, result)

        return result

    def _get_execution_order(
        self,
        preferred: ExecutionPath = None,
        action: Action = None
    ) -> List[ExecutionPath]:
        """Get ordered list of execution paths to try"""
        # Use action's fallback paths if specified
        if action and action.fallback_paths:
            return action.fallback_paths

        default = [
            ExecutionPath.API,
            ExecutionPath.DBUS,
            ExecutionPath.CLI,
            ExecutionPath.GUI
        ]

        if preferred:
            return [preferred] + [p for p in default if p != preferred]

        return default

    def get_registered_paths(self) -> List[ExecutionPath]:
        """Get list of registered execution paths"""
        return list(self._backends.keys())


# Built-in action types
class ActionType:
    """Common action type constants"""

    # File operations
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    FILE_DELETE = "file.delete"
    FILE_MOVE = "file.move"
    FILE_COPY = "file.copy"
    FILE_LIST = "file.list"
    FILE_SEARCH = "file.search"

    # Application operations
    APP_LAUNCH = "app.launch"
    APP_CLOSE = "app.close"
    APP_SWITCH = "app.switch"

    # System operations
    SYSTEM_INFO = "system.info"
    SYSTEM_SETTING = "system.setting"

    # UI operations
    UI_CLICK = "ui.click"
    UI_INPUT = "ui.input"
    UI_SELECT = "ui.select"
    UI_SCROLL = "ui.scroll"
    UI_HOVER = "ui.hover"

    # Web operations
    WEB_SEARCH = "web.search"
    WEB_OPEN = "web.open"
    WEB_FILL = "web.fill"
