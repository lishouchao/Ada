"""
Execution Backends - Various execution backends for Ada
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BackendResult:
    """Result from a backend execution"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    backend: str = "unknown"

    @classmethod
    def ok(cls, output: Any = None, backend: str = "unknown") -> "BackendResult":
        return cls(success=True, output=output, backend=backend)

    @classmethod
    def fail(cls, error: str, backend: str = "unknown") -> "BackendResult":
        return cls(success=False, error=error, backend=backend)


class ExecutionBackend(ABC):
    """
    Abstract base for execution backends.

    Each backend handles a specific method of executing actions:
    - API: Direct function calls within Ada
    - DBus: System D-Bus calls
    - CLI: Command-line tools
    - GUI: UI automation via AT-SPI
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name"""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Backend priority (lower = higher priority)"""
        pass

    @abstractmethod
    async def can_execute(self, action: Dict[str, Any]) -> bool:
        """Check if this backend can execute the action"""
        pass

    @abstractmethod
    async def execute(self, action: Dict[str, Any]) -> BackendResult:
        """Execute the action"""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if backend is available"""
        pass
