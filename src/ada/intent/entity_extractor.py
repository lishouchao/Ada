"""
Entity Extractor - Extract structured entities from text
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ada.intent.base import Entity

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extract structured entities from natural language text.

    Supports various entity types:
    - paths: File and directory paths
    - apps: Application names
    - dates: Dates and times
    - numbers: Numeric values with units
    - urls: Web URLs
    - emails: Email addresses
    """

    def __init__(self):
        self._patterns = self._build_patterns()
        self._common_apps = self._build_app_list()

    def _build_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Build regex patterns for entity extraction"""
        return {
            "path": [
                # Absolute paths
                re.compile(r'(?:^|\s)(/(?:[^/\s]+/)*[^/\s]+)'),
                # Home paths
                re.compile(r'~/(?:[^/\s]+/)*[^/\s]+'),
                # Relative paths with extension
                re.compile(r'(?:^|\s)([\w\-\.]+/[\w\-\.\/]+)'),
            ],
            "url": [
                re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
                re.compile(r'www\.[^\s<>"{}|\\^`\[\]]+\.[a-z]{2,}'),
            ],
            "email": [
                re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            ],
            "date": [
                # ISO format
                re.compile(r'\d{4}-\d{2}-\d{2}'),
                # Chinese format
                re.compile(r'\d{1,2}月\d{1,2}[日号]'),
                # Relative dates
                re.compile(r'(?:今天|明天|后天|昨天|the day after tomorrow|tomorrow|today|yesterday)'),
            ],
            "time": [
                re.compile(r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?', re.IGNORECASE),
                re.compile(r'(?:上午|下午|早上|晚上)\d{1,2}点(?:\d{1,2}分)?'),
            ],
            "number": [
                re.compile(r'\d+(?:\.\d+)?\s*(?:KB|MB|GB|TB|kb|mb|gb|tb)'),
                re.compile(r'\d+(?:\.\d+)?\s*(?:秒|分钟|小时|天|周|月|年)'),
            ],
        }

    def _build_app_list(self) -> Dict[str, str]:
        """Build list of common applications"""
        return {
            # Browsers
            "firefox": "firefox",
            "chrome": "google-chrome",
            "chromium": "chromium",
            "edge": "microsoft-edge",
            # Development
            "vscode": "code",
            "vs code": "code",
            "code": "code",
            "vim": "vim",
            "nvim": "nvim",
            "emacs": "emacs",
            "idea": "idea",
            "pycharm": "pycharm",
            # System
            "terminal": "gnome-terminal",
            "files": "nautilus",
            "nautilus": "nautilus",
            "settings": "gnome-control-center",
            # Office
            "libreoffice": "libreoffice",
            "writer": "libreoffice-writer",
            "calc": "libreoffice-calc",
            # Media
            "vlc": "vlc",
            "spotify": "spotify",
            "rhythmbox": "rhythmbox",
            # Communication
            "slack": "slack",
            "discord": "discord",
            "telegram": "telegram-desktop",
            "wechat": "wechat",
        }

    async def extract(self, text: str) -> List[Entity]:
        """
        Extract all entities from text.

        Args:
            text: Input text

        Returns:
            List of extracted entities
        """
        entities = []
        text_lower = text.lower()

        # Extract pattern-based entities
        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity = Entity(
                        type=entity_type,
                        value=match.group(0),
                        raw_text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                    )
                    entities.append(entity)

        # Extract application names
        app_entities = self._extract_apps(text, text_lower)
        entities.extend(app_entities)

        # Extract Chinese apps (common patterns)
        cn_entities = self._extract_chinese_patterns(text)
        entities.extend(cn_entities)

        # Deduplicate and sort
        entities = self._deduplicate(entities)

        return entities

    def _extract_apps(self, text: str, text_lower: str) -> List[Entity]:
        """Extract application names"""
        entities = []

        for app_name, app_id in self._common_apps.items():
            # Check for app name in text
            pattern = r'\b' + re.escape(app_name) + r'\b'
            match = re.search(pattern, text_lower)
            if match:
                entity = Entity(
                    type="app",
                    value=app_id,
                    raw_text=text[match.start():match.end()],
                    start=match.start(),
                    end=match.end(),
                    metadata={"canonical_name": app_name},
                )
                entities.append(entity)

        return entities

    def _extract_chinese_patterns(self, text: str) -> List[Entity]:
        """Extract Chinese-specific patterns"""
        entities = []

        # App launch patterns
        patterns = [
            (r'打开\s*([^\s，。！？]+)', "app"),
            (r'启动\s*([^\s，。！？]+)', "app"),
            (r'运行\s*([^\s，。！？]+)', "app"),
            (r'关闭\s*([^\s，。！？]+)', "app"),
            (r'整理\s*([^\s，。！？]+(?:文件夹|目录)?)', "path"),
        ]

        for pattern, entity_type in patterns:
            for match in re.finditer(pattern, text):
                value = match.group(1).strip()
                if value:
                    entity = Entity(
                        type=entity_type,
                        value=value,
                        raw_text=value,
                        start=match.start(1),
                        end=match.end(1),
                    )
                    entities.append(entity)

        return entities

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities"""
        seen = set()
        unique = []

        for entity in entities:
            key = (entity.type, entity.start, entity.end)
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        # Sort by start position
        unique.sort(key=lambda e: e.start)

        return unique

    def extract_paths(self, text: str) -> List[Entity]:
        """Extract only path entities"""
        import asyncio
        return asyncio.run(self.extract(text))
        # Filter for paths only
        all_entities = asyncio.get_event_loop().run_until_complete(self.extract(text))
        return [e for e in all_entities if e.type == "path"]

    def extract_apps(self, text: str) -> List[Entity]:
        """Extract only app entities"""
        import asyncio
        all_entities = asyncio.get_event_loop().run_until_complete(self.extract(text))
        return [e for e in all_entities if e.type == "app"]

    def normalize_path(self, path: str) -> str:
        """Normalize a path value"""
        # Expand home directory
        if path.startswith("~"):
            path = str(Path(path).expanduser())

        # Make absolute
        if not path.startswith("/"):
            path = str(Path.cwd() / path)

        return str(Path(path).resolve())

    def parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        match = re.match(r'(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)', size_str, re.IGNORECASE)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2).upper()

        multipliers = {
            "KB": 1024,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3,
            "TB": 1024 ** 4,
        }

        return int(value * multipliers[unit])

    def parse_duration(self, duration_str: str) -> int:
        """Parse duration string to seconds"""
        match = re.match(r'(\d+(?:\.\d+)?)\s*(秒|分钟|小时|天|周|月|年)', duration_str)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2)

        multipliers = {
            "秒": 1,
            "分钟": 60,
            "小时": 3600,
            "天": 86400,
            "周": 604800,
            "月": 2592000,
            "年": 31536000,
        }

        return int(value * multipliers[unit])
