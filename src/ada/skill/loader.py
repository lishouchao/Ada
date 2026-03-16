"""
Skill Loader - Dynamic skill loading from directories
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml

from ada.skill.base import Skill, SkillMetadata
from ada.skill.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Load skills from directories.

    Supports two skill formats:
    1. Python package with Skill class
    2. SKILL.md with YAML frontmatter

    Directory structure:
        skills/
        ├── builtin/
        │   └── file-organizer/
        │       ├── __init__.py    # Contains Skill class
        │       └── SKILL.md       # Optional metadata
        ├── user/
        └── community/
    """

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._loaded_paths: Dict[str, float] = {}  # path -> mtime

    def load_from_directory(
        self,
        directory: Path,
        skill_type: str = "user"
    ) -> List[Skill]:
        """
        Load all skills from a directory.

        Args:
            directory: Root directory containing skill folders
            skill_type: Type prefix (builtin, user, community)

        Returns:
            List of loaded skills
        """
        loaded = []

        if not directory.exists():
            logger.warning(f"Skill directory not found: {directory}")
            return loaded

        for skill_dir in directory.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith((".", "_")):
                continue

            skill = self.load_skill(skill_dir, skill_type)
            if skill:
                loaded.append(skill)

        return loaded

    def load_skill(self, skill_dir: Path, skill_type: str = "user") -> Optional[Skill]:
        """
        Load a single skill from directory.

        Args:
            skill_dir: Directory containing the skill
            skill_type: Type prefix for skill ID

        Returns:
            Loaded skill or None on failure
        """
        skill_id = f"{skill_type}.{skill_dir.name.replace('-', '_')}"

        # Try Python module first
        skill = self._load_python_skill(skill_dir, skill_id)
        if skill:
            self.registry.register(skill)
            return skill

        # Try SKILL.md with script
        skill = self._load_md_skill(skill_dir, skill_id)
        if skill:
            self.registry.register(skill)
            return skill

        logger.warning(f"Could not load skill from {skill_dir}")
        return None

    def _load_python_skill(
        self,
        skill_dir: Path,
        skill_id: str
    ) -> Optional[Skill]:
        """Load skill from Python module"""
        init_file = skill_dir / "__init__.py"

        if not init_file.exists():
            return None

        try:
            # Load module from path
            spec = importlib.util.spec_from_file_location(
                f"skills.{skill_id}",
                init_file
            )
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find Skill subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Skill)
                    and attr is not Skill
                ):
                    skill = attr()
                    # Ensure metadata ID matches
                    if not skill.metadata.id:
                        skill.metadata.id = skill_id
                    return skill

        except Exception as e:
            logger.error(f"Error loading Python skill {skill_dir}: {e}")

        return None

    def _load_md_skill(
        self,
        skill_dir: Path,
        skill_id: str
    ) -> Optional[Skill]:
        """Load skill from SKILL.md file"""
        md_file = skill_dir / "SKILL.md"
        script_file = skill_dir / "handler.py"

        if not md_file.exists():
            return None

        try:
            # Parse SKILL.md
            metadata = self._parse_skill_md(md_file)
            if not metadata:
                return None

            # Ensure ID matches
            metadata.id = metadata.id or skill_id

            # Load script if exists
            handler = None
            if script_file.exists():
                handler = self._load_handler_script(script_file)

            # Create skill from metadata
            if handler:
                skill = self._create_skill_from_handler(metadata, handler)
            else:
                # Create declarative skill
                skill = self._create_declarative_skill(metadata)

            return skill

        except Exception as e:
            logger.error(f"Error loading MD skill {skill_dir}: {e}")

        return None

    def _parse_skill_md(self, md_file: Path) -> Optional[SkillMetadata]:
        """Parse SKILL.md with YAML frontmatter"""
        with open(md_file) as f:
            content = f.read()

        # Extract YAML frontmatter
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        yaml_content = parts[1].strip()
        try:
            data = yaml.safe_load(yaml_content)
            return SkillMetadata.from_dict(data)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing SKILL.md YAML: {e}")
            return None

    def _load_handler_script(self, script_file: Path) -> Optional[callable]:
        """Load handler function from script"""
        try:
            spec = importlib.util.spec_from_file_location(
                script_file.stem,
                script_file
            )
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return getattr(module, "handle", None)

        except Exception as e:
            logger.error(f"Error loading handler script: {e}")
            return None

    def _create_skill_from_handler(
        self,
        metadata: SkillMetadata,
        handler: callable
    ) -> Skill:
        """Create skill from metadata and handler function"""

        class HandlerSkill(Skill):
            def __init__(self, meta, func):
                self.metadata = meta
                self._handler = func

            def can_handle(self, context):
                return 0.5  # Default score

            async def execute(self, context):
                try:
                    result = await self._handler(context)
                    return result
                except Exception as e:
                    from ada.skill.base import SkillResult
                    return SkillResult.fail(str(e))

        return HandlerSkill(metadata, handler)

    def _create_declarative_skill(self, metadata: SkillMetadata) -> Skill:
        """Create skill from declarative metadata only"""

        class DeclarativeSkill(Skill):
            def __init__(self, meta):
                self.metadata = meta

            def can_handle(self, context):
                # Match based on tags and examples
                score = 0.0
                user_input = context.user_input.lower()

                for tag in self.metadata.tags:
                    if tag.lower() in user_input:
                        score += 0.2

                return min(score, 1.0)

            async def execute(self, context):
                from ada.skill.base import SkillResult
                return SkillResult.fail(
                    f"Skill {self.metadata.name} requires implementation"
                )

        return DeclarativeSkill(metadata)

    def reload_modified(self, directory: Path) -> List[Skill]:
        """Reload skills that have been modified"""
        reloaded = []

        if not directory.exists():
            return reloaded

        for skill_dir in directory.iterdir():
            if not skill_dir.is_dir():
                continue

            # Check modification time
            init_file = skill_dir / "__init__.py"
            md_file = skill_dir / "SKILL.md"

            current_mtime = 0.0
            if init_file.exists():
                current_mtime = max(current_mtime, init_file.stat().st_mtime)
            if md_file.exists():
                current_mtime = max(current_mtime, md_file.stat().st_mtime)

            # Check if modified
            cached_mtime = self._loaded_paths.get(str(skill_dir), 0)
            if current_mtime > cached_mtime:
                skill = self.load_skill(skill_dir)
                if skill:
                    reloaded.append(skill)
                    self._loaded_paths[str(skill_dir)] = current_mtime

        return reloaded
