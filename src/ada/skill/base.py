"""
Skill Base - Abstract base classes for skills
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path


@dataclass
class SkillMetadata:
    """Skill metadata and description"""
    id: str                              # Unique identifier (e.g., "builtin.file.organizer")
    name: str                            # Display name
    version: str = "1.0.0"               # Version string
    description: str = ""                # Detailed description
    author: str = ""                     # Author name
    category: str = "general"            # Category: file, app, system, web, etc.
    tags: List[str] = field(default_factory=list)  # Search tags
    permissions: List[str] = field(default_factory=list)  # Required permissions
    examples: List[str] = field(default_factory=list)  # Usage examples
    min_agent_version: str = "0.1.0"     # Minimum Ada version required
    homepage: str = ""                   # Project homepage
    license: str = "MIT"                 # License

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        """Create from dictionary"""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            permissions=data.get("permissions", []),
            examples=data.get("examples", []),
        )


@dataclass
class SkillContext:
    """
    Context provided to skill during execution.

    Contains everything a skill needs to execute.
    """
    # Input
    user_input: str                      # Original user input
    intent: Dict[str, Any]               # Parsed intent
    entities: Dict[str, Any]             # Extracted entities

    # Services
    executor: Any = None                 # HybridExecutor
    memory: Any = None                   # MemoryManager
    llm: Any = None                      # LLMClient
    event_bus: Any = None                # EventBus

    # Platform
    ui_tree: Any = None                  # Current UI tree
    active_window: Optional[str] = None  # Active window name

    # Runtime
    working_dir: Path = field(default_factory=lambda: Path.cwd())
    session_id: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)

    # Progress
    progress_callback: Any = None        # Callable[[int, str], None]


@dataclass
class SkillResult:
    """Result of skill execution"""
    success: bool
    output: Any = None                   # Output data
    message: str = ""                    # Human-readable message
    actions: List[Dict[str, Any]] = field(default_factory=list)  # Actions taken
    follow_up: Optional[str] = None      # Suggested follow-up
    error: Optional[str] = None          # Error message if failed
    requires_confirmation: bool = False  # Needs user confirmation
    confirmation_message: str = ""       # What to ask user

    @classmethod
    def ok(cls, output: Any = None, message: str = "", **kwargs) -> "SkillResult":
        """Create a successful result"""
        return cls(success=True, output=output, message=message, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs) -> "SkillResult":
        """Create a failed result"""
        return cls(success=False, error=error, **kwargs)


class Skill(ABC):
    """
    Abstract base class for skills.

    To implement a skill:
    1. Set the metadata class variable
    2. Implement can_handle() to check intent match
    3. Implement execute() to perform the action

    Example:
        class FileOrganizerSkill(Skill):
            metadata = SkillMetadata(
                id="builtin.file.organizer",
                name="文件整理器",
                description="根据规则自动整理文件",
                category="file",
                tags=["file", "organize", "sort"],
                permissions=["file.read", "file.move"]
            )

            def can_handle(self, context: SkillContext) -> float:
                keywords = ["整理", "归档", "分类"]
                score = sum(1 for k in keywords if k in context.user_input)
                return min(score * 0.3, 1.0)

            async def execute(self, context: SkillContext) -> SkillResult:
                # Implementation here
                pass
    """

    metadata: SkillMetadata

    @abstractmethod
    def can_handle(self, context: SkillContext) -> float:
        """
        Check if this skill can handle the given context.

        Returns:
            Confidence score from 0.0 (cannot handle) to 1.0 (perfect match)
        """
        pass

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute the skill.

        Args:
            context: Execution context with all necessary services

        Returns:
            SkillResult with success status and output
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters (optional override)"""
        return True

    def get_required_permissions(self) -> List[str]:
        """Get required permissions"""
        return self.metadata.permissions

    def describe(self) -> str:
        """Get skill description"""
        return f"{self.metadata.name} ({self.metadata.id}): {self.metadata.description}"
