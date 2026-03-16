"""
Permission Manager - Permission system for Ada
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels"""
    DENY = 0       # Explicitly denied
    ASK = 1        # Ask user each time
    ALLOW_SESSION = 2  # Allow for this session
    ALLOW_ALWAYS = 3   # Always allow


@dataclass
class Permission:
    """
    A single permission definition.

    Permissions control what actions Ada can perform.
    """
    id: str                       # Permission identifier (e.g., "file.read")
    name: str                     # Human-readable name
    description: str              # Description for user
    category: str                 # Category for grouping
    level: PermissionLevel = PermissionLevel.ASK
    constraints: Dict[str, Any] = field(default_factory=dict)
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def is_granted(self) -> bool:
        """Check if permission is currently granted"""
        if self.level == PermissionLevel.DENY:
            return False
        if self.level == PermissionLevel.ASK:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "level": self.level.value,
            "constraints": self.constraints,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Permission":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            level=PermissionLevel(data.get("level", 1)),
            constraints=data.get("constraints", {}),
            granted_at=datetime.fromisoformat(data["granted_at"]) if data.get("granted_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


# Default permissions
DEFAULT_PERMISSIONS = [
    # File permissions
    Permission(
        id="file.read",
        name="读取文件",
        description="允许读取文件内容",
        category="file",
        level=PermissionLevel.ALLOW_SESSION
    ),
    Permission(
        id="file.write",
        name="写入文件",
        description="允许修改文件内容",
        category="file",
        level=PermissionLevel.ASK
    ),
    Permission(
        id="file.delete",
        name="删除文件",
        description="允许删除文件",
        category="file",
        level=PermissionLevel.ASK
    ),
    Permission(
        id="file.execute",
        name="执行文件",
        description="允许执行可执行文件",
        category="file",
        level=PermissionLevel.ASK
    ),

    # Application permissions
    Permission(
        id="app.launch",
        name="启动应用",
        description="允许启动应用程序",
        category="app",
        level=PermissionLevel.ALLOW_SESSION
    ),
    Permission(
        id="app.close",
        name="关闭应用",
        description="允许关闭应用程序",
        category="app",
        level=PermissionLevel.ASK
    ),
    Permission(
        id="app.control",
        name="控制应用",
        description="允许控制应用程序界面",
        category="app",
        level=PermissionLevel.ASK
    ),

    # System permissions
    Permission(
        id="system.info",
        name="系统信息",
        description="允许读取系统信息",
        category="system",
        level=PermissionLevel.ALLOW_ALWAYS
    ),
    Permission(
        id="system.settings",
        name="系统设置",
        description="允许修改系统设置",
        category="system",
        level=PermissionLevel.ASK
    ),
    Permission(
        id="system.power",
        name="电源控制",
        description="允许关机、重启等操作",
        category="system",
        level=PermissionLevel.ASK
    ),

    # Network permissions
    Permission(
        id="network.request",
        name="网络请求",
        description="允许发送网络请求",
        category="network",
        level=PermissionLevel.ASK
    ),
    Permission(
        id="network.listen",
        name="网络监听",
        description="允许监听网络端口",
        category="network",
        level=PermissionLevel.DENY
    ),

    # Memory permissions
    Permission(
        id="memory.read",
        name="读取记忆",
        description="允许读取存储的记忆",
        category="memory",
        level=PermissionLevel.ALLOW_ALWAYS
    ),
    Permission(
        id="memory.write",
        name="写入记忆",
        description="允许存储新的记忆",
        category="memory",
        level=PermissionLevel.ALLOW_ALWAYS
    ),

    # Clipboard permissions
    Permission(
        id="clipboard.read",
        name="读取剪贴板",
        description="允许读取剪贴板内容",
        category="clipboard",
        level=PermissionLevel.ASK
    ),
    Permission(
        id="clipboard.write",
        name="写入剪贴板",
        description="允许写入剪贴板内容",
        category="clipboard",
        level=PermissionLevel.ALLOW_SESSION
    ),

    # Notification permissions
    Permission(
        id="notification.show",
        name="显示通知",
        description="允许显示桌面通知",
        category="notification",
        level=PermissionLevel.ALLOW_ALWAYS
    ),
]


class PermissionManager:
    """
    Manage permissions for Ada operations.

    Features:
    - Permission definitions
    - User consent handling
    - Permission persistence
    - Constraint checking
    """

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".config" / "ada" / "permissions.json"
        self._permissions: Dict[str, Permission] = {}
        self._callbacks: List[callable] = []

        # Initialize with defaults
        self._init_defaults()

        # Load saved permissions
        self._load()

    def _init_defaults(self):
        """Initialize with default permissions"""
        for perm in DEFAULT_PERMISSIONS:
            self._permissions[perm.id] = perm

    def _load(self):
        """Load saved permissions from disk"""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            for perm_id, perm_data in data.get("permissions", {}).items():
                if perm_id in self._permissions:
                    saved_perm = Permission.from_dict(perm_data)
                    # Merge saved level with default
                    self._permissions[perm_id].level = saved_perm.level
                    self._permissions[perm_id].granted_at = saved_perm.granted_at
                    self._permissions[perm_id].expires_at = saved_perm.expires_at

            logger.info(f"Loaded {len(self._permissions)} permissions")

        except Exception as e:
            logger.error(f"Error loading permissions: {e}")

    def _save(self):
        """Save permissions to disk"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = {
                "version": 1,
                "permissions": {
                    pid: p.to_dict()
                    for pid, p in self._permissions.items()
                    if p.level != PermissionLevel.ASK  # Only save non-default
                }
            }

            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving permissions: {e}")

    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get a permission by ID"""
        return self._permissions.get(permission_id)

    def check(self, permission_id: str, context: Dict[str, Any] = None) -> PermissionLevel:
        """
        Check a permission.

        Args:
            permission_id: Permission to check
            context: Optional context for constraint checking

        Returns:
            PermissionLevel indicating if allowed
        """
        perm = self._permissions.get(permission_id)
        if not perm:
            logger.warning(f"Unknown permission: {permission_id}")
            return PermissionLevel.ASK

        return perm.level

    async def request(
        self,
        permission_id: str,
        reason: str = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Request a permission from the user.

        Args:
            permission_id: Permission to request
            reason: Reason for needing the permission
            context: Optional context

        Returns:
            True if granted, False otherwise
        """
        perm = self._permissions.get(permission_id)
        if not perm:
            logger.warning(f"Unknown permission requested: {permission_id}")
            return False

        # Check if already granted
        if perm.is_granted():
            return True

        # Check if permanently denied
        if perm.level == PermissionLevel.DENY:
            return False

        # Need to ask user
        result = await self._ask_user(perm, reason, context)

        return result

    async def _ask_user(
        self,
        permission: Permission,
        reason: str,
        context: Dict[str, Any]
    ) -> bool:
        """Ask user for permission"""
        # This would integrate with the UI
        # For now, return based on callbacks

        for callback in self._callbacks:
            try:
                result = await callback(permission, reason, context)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"Error in permission callback: {e}")

        # Default: ask (which effectively denies until confirmed)
        return False

    def grant(self, permission_id: str, level: PermissionLevel = PermissionLevel.ALLOW_SESSION):
        """Grant a permission"""
        perm = self._permissions.get(permission_id)
        if perm:
            perm.level = level
            perm.granted_at = datetime.now()
            self._save()

    def deny(self, permission_id: str):
        """Deny a permission"""
        perm = self._permissions.get(permission_id)
        if perm:
            perm.level = PermissionLevel.DENY
            self._save()

    def revoke(self, permission_id: str):
        """Revoke a permission (reset to ask)"""
        perm = self._permissions.get(permission_id)
        if perm:
            perm.level = PermissionLevel.ASK
            perm.granted_at = None
            perm.expires_at = None
            self._save()

    def reset_all(self):
        """Reset all permissions to defaults"""
        self._permissions.clear()
        self._init_defaults()
        self._save()

    def list_permissions(self, category: str = None) -> List[Permission]:
        """List all permissions, optionally filtered by category"""
        perms = list(self._permissions.values())

        if category:
            perms = [p for p in perms if p.category == category]

        return perms

    def list_categories(self) -> List[str]:
        """List all permission categories"""
        return list(set(p.category for p in self._permissions.values()))

    def on_permission_request(self, callback: callable):
        """Register callback for permission requests"""
        self._callbacks.append(callback)

    def check_constraints(
        self,
        permission_id: str,
        constraints: Dict[str, Any]
    ) -> bool:
        """
        Check if constraints are satisfied for a permission.

        Args:
            permission_id: Permission to check
            constraints: Constraints to validate

        Returns:
            True if constraints are satisfied
        """
        perm = self._permissions.get(permission_id)
        if not perm:
            return False

        # Check each constraint
        for key, value in constraints.items():
            if key in perm.constraints:
                if perm.constraints[key] != value:
                    return False

        return True
