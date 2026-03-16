"""
Skill Registry - Skill discovery and management
"""

from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

from ada.skill.base import Skill, SkillContext

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registry for discovering and managing skills.

    Features:
    - Register/unregister skills
    - Find skills by intent match
    - List skills by category
    - Load skills from directories

    Example:
        registry = SkillRegistry()

        # Register a skill
        registry.register(FileOrganizerSkill())

        # Find best matching skill
        skill, score = registry.find_best(context)
        if skill:
            result = await skill.execute(context)
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, skill: Skill):
        """
        Register a skill.

        Args:
            skill: Skill instance to register
        """
        skill_id = skill.metadata.id
        self._skills[skill_id] = skill

        # Index by category
        category = skill.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(skill_id)

        logger.info(f"Registered skill: {skill_id}")

    def unregister(self, skill_id: str):
        """Unregister a skill"""
        if skill_id in self._skills:
            skill = self._skills[skill_id]
            category = skill.metadata.category
            if category in self._categories:
                self._categories[category].remove(skill_id)
            del self._skills[skill_id]
            logger.info(f"Unregistered skill: {skill_id}")

    def get(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID"""
        return self._skills.get(skill_id)

    def find_best(self, context: SkillContext) -> Optional[Tuple[Skill, float]]:
        """
        Find the best matching skill for a context.

        Args:
            context: Skill context with intent and user input

        Returns:
            Tuple of (skill, score) or None if no match
        """
        candidates = []

        for skill in self._skills.values():
            try:
                score = skill.can_handle(context)
                if score > 0.0:
                    candidates.append((skill, score))
            except Exception as e:
                logger.error(f"Error checking skill {skill.metadata.id}: {e}")

        if not candidates:
            return None

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]

    def find_all(self, context: SkillContext, min_score: float = 0.3) -> List[Tuple[Skill, float]]:
        """
        Find all matching skills above threshold.

        Args:
            context: Skill context
            min_score: Minimum confidence score

        Returns:
            List of (skill, score) tuples
        """
        candidates = []

        for skill in self._skills.values():
            try:
                score = skill.can_handle(context)
                if score >= min_score:
                    candidates.append((skill, score))
            except Exception as e:
                logger.error(f"Error checking skill {skill.metadata.id}: {e}")

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def list_skills(self, category: str = None) -> List[Skill]:
        """
        List all skills, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of skills
        """
        if category:
            skill_ids = self._categories.get(category, [])
            return [self._skills[sid] for sid in skill_ids if sid in self._skills]
        return list(self._skills.values())

    def list_categories(self) -> List[str]:
        """List all categories"""
        return list(self._categories.keys())

    def get_skill_metadata(self, skill_id: str) -> Optional[Dict]:
        """Get skill metadata as dict"""
        skill = self.get(skill_id)
        if skill:
            return {
                "id": skill.metadata.id,
                "name": skill.metadata.name,
                "version": skill.metadata.version,
                "description": skill.metadata.description,
                "category": skill.metadata.category,
                "tags": skill.metadata.tags,
                "permissions": skill.metadata.permissions,
                "examples": skill.metadata.examples,
            }
        return None

    def search(self, query: str) -> List[Skill]:
        """
        Search skills by query string.

        Matches against name, description, and tags.

        Args:
            query: Search query

        Returns:
            List of matching skills
        """
        query = query.lower()
        results = []

        for skill in self._skills.values():
            # Check name
            if query in skill.metadata.name.lower():
                results.append(skill)
                continue

            # Check description
            if query in skill.metadata.description.lower():
                results.append(skill)
                continue

            # Check tags
            if any(query in tag.lower() for tag in skill.metadata.tags):
                results.append(skill)
                continue

        return results

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._skills
