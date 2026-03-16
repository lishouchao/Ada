"""
Intent Parser - Natural language intent parsing
"""

import logging
import re
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ada.intent.base import Intent, IntentCategory, Entity, IntentResult
from ada.intent.entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


class IntentParserBackend(ABC):
    """Abstract backend for intent parsing"""

    @abstractmethod
    async def parse(self, text: str, context: Dict[str, Any]) -> Optional[Intent]:
        """Parse text into intent"""
        pass


class RuleBasedBackend(IntentParserBackend):
    """
    Rule-based intent parsing.

    Uses pattern matching and keyword extraction for fast,
    deterministic intent recognition.
    """

    def __init__(self):
        self._patterns = self._build_patterns()
        self._entity_extractor = EntityExtractor()

    def _build_patterns(self) -> Dict[str, List[Dict]]:
        """Build intent recognition patterns"""
        return {
            "file.open": [
                {"pattern": r"打开\s*(.+?)(?:文件)?$", "action": "open", "category": IntentCategory.FILE},
                {"pattern": r"open\s+(.+?)(?:\s+file)?$", "action": "open", "category": IntentCategory.FILE},
            ],
            "file.delete": [
                {"pattern": r"删除\s*(.+?)(?:文件)?$", "action": "delete", "category": IntentCategory.FILE},
                {"pattern": r"remove\s+(.+?)(?:\s+file)?$", "action": "delete", "category": IntentCategory.FILE},
            ],
            "file.move": [
                {"pattern": r"移动\s*(.+?)\s*到\s*(.+)$", "action": "move", "category": IntentCategory.FILE},
                {"pattern": r"move\s+(.+?)\s+to\s+(.+)$", "action": "move", "category": IntentCategory.FILE},
            ],
            "file.organize": [
                {"pattern": r"整理\s*(.+?)(?:文件夹|目录)?$", "action": "organize", "category": IntentCategory.FILE},
                {"pattern": r"organize\s+(.+?)(?:\s+folder)?$", "action": "organize", "category": IntentCategory.FILE},
            ],
            "app.launch": [
                {"pattern": r"(?:打开|启动|运行)\s*(.+?)(?:应用程序)?$", "action": "launch", "category": IntentCategory.APPLICATION},
                {"pattern": r"(?:open|launch|run|start)\s+(.+?)(?:\s+app)?$", "action": "launch", "category": IntentCategory.APPLICATION},
            ],
            "app.switch": [
                {"pattern": r"切换到\s*(.+?)(?:应用)?$", "action": "switch", "category": IntentCategory.APPLICATION},
                {"pattern": r"switch\s+(?:to\s+)?(.+?)(?:\s+app)?$", "action": "switch", "category": IntentCategory.APPLICATION},
            ],
            "app.close": [
                {"pattern": r"(?:关闭|退出)\s*(.+?)(?:应用)?$", "action": "close", "category": IntentCategory.APPLICATION},
                {"pattern": r"(?:close|quit|exit)\s+(.+?)(?:\s+app)?$", "action": "close", "category": IntentCategory.APPLICATION},
            ],
            "system.shutdown": [
                {"pattern": r"关机|shutdown|power off", "action": "shutdown", "category": IntentCategory.SYSTEM},
            ],
            "system.reboot": [
                {"pattern": r"重启|reboot|restart", "action": "reboot", "category": IntentCategory.SYSTEM},
            ],
            "info.query": [
                {"pattern": r"(?:查询|搜索|查找)\s*(.+)$", "action": "query", "category": IntentCategory.INFORMATION},
                {"pattern": r"(?:search|query|find|look\s+up)\s+(.+)$", "action": "query", "category": IntentCategory.INFORMATION},
            ],
        }

    async def parse(self, text: str, context: Dict[str, Any]) -> Optional[Intent]:
        """Parse using rule-based matching"""
        text_lower = text.lower().strip()

        best_intent = None
        best_confidence = 0.0

        for intent_name, patterns in self._patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                match = re.search(pattern, text, re.IGNORECASE)

                if match:
                    # Calculate confidence based on match quality
                    confidence = len(match.group(0)) / len(text)
                    confidence = min(confidence * 1.5, 1.0)  # Scale up

                    if confidence > best_confidence:
                        # Extract entities
                        entities = self._extract_entities_from_match(match, text)

                        best_intent = Intent(
                            name=intent_name,
                            category=pattern_info["category"],
                            action=pattern_info["action"],
                            entities=entities,
                            raw_input=text,
                            confidence=confidence,
                            requires_confirmation=self._requires_confirmation(intent_name),
                        )
                        best_confidence = confidence

        return best_intent

    def _extract_entities_from_match(self, match: re.Match, text: str) -> Dict[str, Entity]:
        """Extract entities from regex match"""
        entities = {}

        for i, group in enumerate(match.groups(), 1):
            if group:
                entity_type = self._guess_entity_type(group, i)
                start = match.start(i)
                end = match.end(i)

                entities[f"arg{i}"] = Entity(
                    type=entity_type,
                    value=group.strip(),
                    raw_text=group,
                    start=start,
                    end=end,
                )

        return entities

    def _guess_entity_type(self, text: str, position: int) -> str:
        """Guess entity type from text content"""
        text = text.strip()

        # Check for path
        if text.startswith(("/","~/")) or "/" in text:
            return "path"

        # Check for app
        common_apps = ["firefox", "chrome", "code", "vscode", "terminal", "nautilus", "files"]
        if text.lower() in common_apps:
            return "app"

        # Default based on position
        return "target" if position == 1 else "destination"

    def _requires_confirmation(self, intent_name: str) -> bool:
        """Check if intent requires user confirmation"""
        destructive_intents = [
            "file.delete",
            "system.shutdown",
            "system.reboot",
        ]
        return intent_name in destructive_intents


class LLMBasedBackend(IntentParserBackend):
    """
    LLM-based intent parsing.

    Uses language model for more flexible, context-aware parsing.
    Falls back gracefully when LLM is unavailable.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self._fallback = RuleBasedBackend()

    async def parse(self, text: str, context: Dict[str, Any]) -> Optional[Intent]:
        """Parse using LLM"""
        if not self.llm_client:
            return await self._fallback.parse(text, context)

        try:
            prompt = self._build_prompt(text, context)
            response = await self.llm_client.chat(prompt)

            if response:
                return self._parse_llm_response(response, text)

        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")

        # Fallback to rule-based
        return await self._fallback.parse(text, context)

    def _build_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Build prompt for LLM"""
        return f"""Analyze the following user request and extract the intent.

User request: {text}

Context:
{context}

Respond in JSON format:
{{
    "intent": "category.action (e.g., file.open, app.launch)",
    "action": "the action to perform",
    "entities": {{
        "entity_name": "extracted value"
    }},
    "confidence": 0.0-1.0,
    "requires_confirmation": true/false
}}

Only respond with the JSON, no additional text."""

    def _parse_llm_response(self, response: str, original_text: str) -> Optional[Intent]:
        """Parse LLM response into Intent"""
        import json

        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Parse intent name
                intent_name = data.get("intent", "unknown.unknown")
                category_str, action = intent_name.split(".", 1) if "." in intent_name else ("unknown", "unknown")

                try:
                    category = IntentCategory(category_str)
                except ValueError:
                    category = IntentCategory.UNKNOWN

                # Convert entities
                entities = {}
                for name, value in data.get("entities", {}).items():
                    entities[name] = Entity(
                        type=name,
                        value=value,
                        raw_text=str(value),
                        start=0,
                        end=0,
                    )

                return Intent(
                    name=intent_name,
                    category=category,
                    action=action,
                    entities=entities,
                    raw_input=original_text,
                    confidence=data.get("confidence", 0.8),
                    requires_confirmation=data.get("requires_confirmation", False),
                )

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")

        return None


class IntentParser:
    """
    Main intent parser with multiple backends.

    Tries LLM first, falls back to rule-based parsing.
    """

    def __init__(self, llm_client=None):
        self._rule_backend = RuleBasedBackend()
        self._llm_backend = LLMBasedBackend(llm_client) if llm_client else None
        self._entity_extractor = EntityExtractor()

    async def parse(self, text: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """
        Parse user input into intent.

        Args:
            text: User input text
            context: Optional context (conversation history, user preferences)

        Returns:
            IntentResult with parsed intent
        """
        start_time = time.time()
        context = context or {}

        # Try LLM first
        intent = None
        if self._llm_backend:
            intent = await self._llm_backend.parse(text, context)

        # Fall back to rule-based
        if not intent:
            intent = await self._rule_backend.parse(text, context)

        # Extract additional entities
        entities = await self._entity_extractor.extract(text)

        # Create result
        result = IntentResult(
            intent=intent,
            entities=entities,
            parsing_time_ms=(time.time() - start_time) * 1000,
        )

        return result

    async def parse_batch(self, texts: List[str], context: Optional[Dict[str, Any]] = None) -> List[IntentResult]:
        """Parse multiple inputs"""
        results = []
        for text in texts:
            result = await self.parse(text, context)
            results.append(result)
        return results

    def add_custom_pattern(self, intent_name: str, pattern: str, category: IntentCategory, action: str):
        """Add custom intent pattern"""
        self._rule_backend._patterns.setdefault(intent_name, []).append({
            "pattern": pattern,
            "action": action,
            "category": category,
        })
