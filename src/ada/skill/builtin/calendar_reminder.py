"""
Calendar & Reminder Skill - Schedule management
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import re
from pathlib import Path


@dataclass
class Reminder:
    """A scheduled reminder"""
    id: str
    message: str
    trigger_time: datetime
    created_at: datetime = field(default_factory=datetime.now)
    recurring: bool = False
    recurring_pattern: Optional[str] = None  # daily, weekly, monthly
    tags: List[str] = field(default_factory=list)
    completed: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "message": self.message,
            "trigger_time": self.trigger_time.isoformat(),
            "created_at": self.created_at.isoformat(),
            "recurring": self.recurring,
            "recurring_pattern": self.recurring_pattern,
            "tags": self.tags,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Reminder":
        return cls(
            id=data["id"],
            message=data["message"],
            trigger_time=datetime.fromisoformat(data["trigger_time"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            recurring=data.get("recurring", False),
            recurring_pattern=data.get("recurring_pattern"),
            tags=data.get("tags", []),
            completed=data.get("completed", False),
        )


class CalendarReminderSkill(Skill):
    """
    Skill for calendar and reminder management.

    Capabilities:
    - Set reminders
    - List upcoming reminders
    - Delete reminders
    - Natural language time parsing
    """

    metadata = SkillMetadata(
        id="builtin.calendar.reminder",
        name="日程提醒",
        version="1.0.0",
        description="设置提醒、管理日程安排",
        author="Ada Team",
        category="schedule",
        tags=["calendar", "reminder", "schedule", "提醒", "日程", "闹钟"],
        permissions=["notification.show"],
        examples=[
            "提醒我下午3点开会",
            "10分钟后提醒我",
            "明天早上8点叫我起床",
            "查看我的提醒",
            "取消所有提醒"
        ]
    )

    def __init__(self):
        self._reminders: Dict[str, Reminder] = {}
        self._storage_path: Optional[Path] = None
        self._reminder_callbacks: List[callable] = []

    def initialize(self, storage_path: Path = None):
        """Initialize with storage path"""
        self._storage_path = storage_path or Path.home() / ".local" / "share" / "ada" / "reminders.json"
        self._load_reminders()

    def can_handle(self, context: SkillContext) -> float:
        """Check if this skill matches"""
        reminder_keywords = [
            "提醒", "闹钟", "日程", "提醒我", "叫我", "通知我",
            "reminder", "alarm", "schedule", "remind me"
        ]
        time_keywords = [
            "分钟后", "小时后", "明天", "后天", "下周",
            "minutes", "hours", "tomorrow", "next week"
        ]

        user_input = context.user_input.lower()
        score = 0.0

        for kw in reminder_keywords:
            if kw in user_input:
                score += 0.5

        for kw in time_keywords:
            if kw in user_input:
                score += 0.3

        return min(score, 1.0)

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute reminder action"""
        user_input = context.user_input.lower()
        entities = context.entities

        # Detect action
        action = self._detect_action(user_input)

        try:
            if action == "set":
                return await self._set_reminder(user_input)

            elif action == "list":
                return await self._list_reminders()

            elif action == "delete":
                return await self._delete_reminder(user_input)

            elif action == "clear":
                return await self._clear_reminders()

            else:
                # Default to setting reminder
                return await self._set_reminder(user_input)

        except Exception as e:
            return SkillResult.fail(f"提醒操作失败: {e}")

    def _detect_action(self, text: str) -> str:
        """Detect action from text"""
        text = text.lower()

        if any(kw in text for kw in ["查看", "列出", "什么", "有哪些", "list", "show"]):
            return "list"

        if any(kw in text for kw in ["取消", "删除", "clear", "delete", "remove"]):
            return "delete" if "提醒" in text and ("所有" not in text and "all" not in text) else "clear"

        return "set"

    async def _set_reminder(self, text: str) -> SkillResult:
        """Set a new reminder"""
        import uuid

        # Parse time
        trigger_time = self._parse_time(text)

        if not trigger_time:
            return SkillResult.fail("无法识别时间，请使用更明确的表达，例如：'下午3点'、'10分钟后'")

        # Extract message
        message = self._extract_message(text)

        if not message:
            return SkillResult.fail("请提供提醒内容")

        # Create reminder
        reminder = Reminder(
            id=str(uuid.uuid4()),
            message=message,
            trigger_time=trigger_time,
        )

        self._reminders[reminder.id] = reminder
        self._save_reminders()

        # Schedule notification
        self._schedule_reminder(reminder)

        # Format response
        time_str = trigger_time.strftime("%Y-%m-%d %H:%M")
        relative = self._format_relative_time(trigger_time)

        return SkillResult.ok(
            message=f"已设置提醒: {message}\n时间: {time_str} ({relative})",
            output={"reminder": reminder.to_dict()}
        )

    async def _list_reminders(self) -> SkillResult:
        """List all reminders"""
        active_reminders = [
            r for r in self._reminders.values()
            if not r.completed and r.trigger_time > datetime.now()
        ]

        if not active_reminders:
            return SkillResult.ok(message="当前没有待处理的提醒")

        # Sort by time
        active_reminders.sort(key=lambda r: r.trigger_time)

        lines = ["待处理的提醒:"]
        for i, r in enumerate(active_reminders, 1):
            time_str = r.trigger_time.strftime("%m-%d %H:%M")
            relative = self._format_relative_time(r.trigger_time)
            lines.append(f"  {i}. [{time_str}] {r.message} ({relative})")

        return SkillResult.ok(
            message="\n".join(lines),
            output={"reminders": [r.to_dict() for r in active_reminders]}
        )

    async def _delete_reminder(self, text: str) -> SkillResult:
        """Delete a specific reminder"""
        # Try to extract index
        match = re.search(r"第?\s*(\d+)\s*个", text)
        if match:
            index = int(match.group(1))
            active = [r for r in self._reminders.values() if not r.completed]
            active.sort(key=lambda r: r.trigger_time)

            if 0 < index <= len(active):
                reminder = active[index - 1]
                del self._reminders[reminder.id]
                self._save_reminders()

                return SkillResult.ok(message=f"已删除提醒: {reminder.message}")

        return SkillResult.fail("请指定要删除的提醒编号，例如：删除第1个提醒")

    async def _clear_reminders(self) -> SkillResult:
        """Clear all reminders"""
        count = len(self._reminders)
        self._reminders.clear()
        self._save_reminders()

        return SkillResult.ok(message=f"已清除所有 {count} 个提醒")

    def _parse_time(self, text: str) -> Optional[datetime]:
        """Parse time from natural language"""
        now = datetime.now()
        text = text.lower()

        # Relative times
        match = re.search(r"(\d+)\s*分钟", text)
        if match:
            minutes = int(match.group(1))
            return now + timedelta(minutes=minutes)

        match = re.search(r"(\d+)\s*小时", text)
        if match:
            hours = int(match.group(1))
            return now + timedelta(hours=hours)

        match = re.search(r"(\d+)\s*天", text)
        if match:
            days = int(match.group(1))
            return now + timedelta(days=days)

        # Named times
        if "明天" in text:
            base = now + timedelta(days=1)
            base = base.replace(hour=9, minute=0, second=0, microsecond=0)

            # Try to get specific hour
            match = re.search(r"(\d+)[点时]", text)
            if match:
                hour = int(match.group(1))
                base = base.replace(hour=hour)

            # Check for morning/afternoon
            if "早上" in text or "上午" in text:
                base = base.replace(hour=min(base.hour, 11))
            elif "下午" in text or "晚上" in text:
                base = base.replace(hour=max(base.hour, 13) if base.hour < 13 else base.hour)

            return base

        if "后天" in text:
            base = now + timedelta(days=2)
            base = base.replace(hour=9, minute=0, second=0, microsecond=0)
            return base

        # Time of day today
        match = re.search(r"(\d+)[点时](\d+)?分?", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0

            # Handle 12-hour format
            if "下午" in text or "晚上" in text:
                if hour < 12:
                    hour += 12
            elif "上午" in text and hour == 12:
                hour = 0

            result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If time has passed today, assume tomorrow
            if result < now:
                result += timedelta(days=1)

            return result

        # Relative keywords
        if "一下" in text or "一会" in text:
            return now + timedelta(minutes=5)

        if "马上" in text or "立刻" in text:
            return now + timedelta(minutes=1)

        return None

    def _extract_message(self, text: str) -> Optional[str]:
        """Extract reminder message from text"""
        # Remove time-related patterns
        patterns = [
            r"提醒我\s*",
            r"(?:在|于)?\s*(?:下午|上午|早上|晚上)?\s*\d+[点时](\d+)?分?\s*",
            r"(?:\d+\s*(?:分钟|小时|天)后)\s*",
            r"(?:明天|后天)\s*(?:早上|上午|下午|晚上)?\s*",
        ]

        message = text
        for pattern in patterns:
            message = re.sub(pattern, "", message, flags=re.IGNORECASE)

        # Clean up
        message = message.strip()
        message = re.sub(r"^\s*[的得]\s*", "", message)

        return message if message else None

    def _format_relative_time(self, dt: datetime) -> str:
        """Format datetime as relative time"""
        now = datetime.now()
        diff = dt - now

        if diff.days > 365:
            return f"{diff.days // 365} 年后"
        if diff.days > 30:
            return f"{diff.days // 30} 个月后"
        if diff.days > 0:
            return f"{diff.days} 天后"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600} 小时后"
        if diff.seconds > 60:
            return f"{diff.seconds // 60} 分钟后"
        return "即将"

    def _schedule_reminder(self, reminder: Reminder):
        """Schedule a reminder for notification"""
        # This would integrate with the notification system
        # For now, store the reminder for later retrieval
        pass

    def _load_reminders(self):
        """Load reminders from storage"""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path) as f:
                data = json.load(f)

            for item in data.get("reminders", []):
                reminder = Reminder.from_dict(item)
                self._reminders[reminder.id] = reminder

        except Exception as e:
            pass  # Silent fail on load

    def _save_reminders(self):
        """Save reminders to storage"""
        if not self._storage_path:
            return

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "reminders": [r.to_dict() for r in self._reminders.values()]
            }

            with open(self._storage_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            pass  # Silent fail on save

    def on_reminder_trigger(self, callback: callable):
        """Register callback for when reminder triggers"""
        self._reminder_callbacks.append(callback)
