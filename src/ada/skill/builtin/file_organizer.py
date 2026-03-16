"""
File Organizer Skill - Organize files by rules
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from typing import List, Dict, Any


class FileOrganizerSkill(Skill):
    """
    Skill for organizing files based on rules.

    Capabilities:
    - Organize by file type/extension
    - Organize by date
    - Organize by size
    - Move/copy to target directories
    """

    metadata = SkillMetadata(
        id="builtin.file.organizer",
        name="文件整理器",
        version="1.0.0",
        description="根据规则自动整理文件，支持按类型、日期、大小等条件分类",
        author="Ada Team",
        category="file",
        tags=["file", "organize", "sort", "整理", "分类"],
        permissions=["file.read", "file.move"],
        examples=[
            "整理下载文件夹",
            "按类型整理桌面文件",
            "把大于100MB的文件移到外部硬盘",
            "按日期归档文档"
        ]
    )

    def can_handle(self, context: SkillContext) -> float:
        """Check if this skill matches the intent"""
        keywords = ["整理", "归档", "分类", "整理一下", "organize", "sort"]
        user_input = context.user_input.lower()

        score = 0.0
        for kw in keywords:
            if kw in user_input:
                score += 0.3

        # Check for file-related entities
        if context.entities:
            if "path" in context.entities or "folder" in context.entities:
                score += 0.2
            if "file" in context.entities:
                score += 0.2

        return min(score, 1.0)

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute file organization"""
        entities = context.entities
        user_input = context.user_input

        # Parse source directory
        source = entities.get("source") or entities.get("path") or "~/Downloads"

        # Parse strategy
        strategy = self._detect_strategy(user_input)

        # Parse destination if specified
        destination = entities.get("destination") or entities.get("target")

        # Progress callback
        if context.progress_callback:
            context.progress_callback(0, f"开始扫描 {source}...")

        try:
            # Scan files
            files = await self._scan_files(context, source)

            if not files:
                return SkillResult.ok(
                    message=f"目录 {source} 中没有需要整理的文件"
                )

            if context.progress_callback:
                context.progress_callback(20, f"找到 {len(files)} 个文件，开始分类...")

            # Classify files
            groups = self._classify_files(files, strategy)

            if context.progress_callback:
                context.progress_callback(40, f"已分类为 {len(groups)} 组")

            # Calculate destination for each group
            plans = self._plan_moves(groups, source, destination, strategy)

            # Confirm if high impact
            total_files = sum(len(g) for g in groups.values())
            if total_files > 10:
                return SkillResult(
                    success=True,
                    requires_confirmation=True,
                    confirmation_message=f"将移动 {total_files} 个文件到 {len(groups)} 个分类目录，确认继续？",
                    output={"plans": plans, "strategy": strategy}
                )

            # Execute moves
            moved = 0
            for i, (src, dst) in enumerate(plans):
                result = await context.executor.execute({
                    "type": "file.move",
                    "params": {"source": src, "target": dst}
                })
                if result.success:
                    moved += 1
                if context.progress_callback:
                    progress = 40 + int(50 * (i + 1) / len(plans))
                    context.progress_callback(progress, f"已移动 {moved}/{len(plans)} 个文件")

            if context.progress_callback:
                context.progress_callback(100, "整理完成")

            return SkillResult.ok(
                output={
                    "moved_count": moved,
                    "total_files": len(files),
                    "groups": {k: len(v) for k, v in groups.items()},
                    "strategy": strategy
                },
                message=f"已整理 {moved} 个文件到 {len(groups)} 个分类目录"
            )

        except Exception as e:
            return SkillResult.fail(str(e))

    def _detect_strategy(self, text: str) -> str:
        """Detect organization strategy from text"""
        text = text.lower()

        if any(kw in text for kw in ["日期", "date", "时间", "time"]):
            return "by_date"
        if any(kw in text for kw in ["大小", "size", "大于", "小于"]):
            return "by_size"
        # Default: by extension/type
        return "by_type"

    async def _scan_files(self, context: SkillContext, path: str) -> List[Dict]:
        """Scan directory for files"""
        result = await context.executor.execute({
            "type": "file.list",
            "params": {"path": path, "recursive": False}
        })

        if not result.success:
            return []

        # Filter files only
        return [f for f in result.output if not f.get("is_dir")]

    def _classify_files(
        self,
        files: List[Dict],
        strategy: str
    ) -> Dict[str, List[Dict]]:
        """Classify files by strategy"""
        groups = {}

        for file in files:
            if strategy == "by_type":
                key = self._get_file_category(file)
            elif strategy == "by_date":
                key = self._get_date_category(file)
            elif strategy == "by_size":
                key = self._get_size_category(file)
            else:
                key = "other"

            if key not in groups:
                groups[key] = []
            groups[key].append(file)

        return groups

    def _get_file_category(self, file: Dict) -> str:
        """Get file category by extension"""
        name = file.get("name", "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

        categories = {
            "documents": ["pdf", "doc", "docx", "txt", "md", "xls", "xlsx", "ppt", "pptx"],
            "images": ["jpg", "jpeg", "png", "gif", "svg", "webp", "bmp"],
            "videos": ["mp4", "mkv", "avi", "mov", "webm", "flv"],
            "music": ["mp3", "wav", "flac", "aac", "ogg"],
            "archives": ["zip", "tar", "gz", "rar", "7z"],
            "code": ["py", "js", "ts", "java", "cpp", "go", "rs"],
            "packages": ["deb", "rpm", "flatpak", "appimage", "exe", "dmg"],
        }

        for category, extensions in categories.items():
            if ext in extensions:
                return category

        return "other"

    def _get_date_category(self, file: Dict) -> str:
        """Get date category from file mtime"""
        import time
        mtime = file.get("mtime", time.time())
        dt = time.localtime(mtime)
        return f"{dt.tm_year}/{dt.tm_mon:02d}"

    def _get_size_category(self, file: Dict) -> str:
        """Get size category"""
        size = file.get("size", 0)

        if size < 1024 * 1024:  # < 1MB
            return "small"
        elif size < 100 * 1024 * 1024:  # < 100MB
            return "medium"
        else:
            return "large"

    def _plan_moves(
        self,
        groups: Dict[str, List[Dict]],
        source: str,
        destination: str,
        strategy: str
    ) -> List[tuple]:
        """Plan file moves"""
        import os

        plans = []
        dest_base = destination or source

        for category, files in groups.items():
            target_dir = os.path.join(dest_base, category)

            for file in files:
                src = file.get("path")
                dst = os.path.join(target_dir, file.get("name"))
                if src:
                    plans.append((src, dst))

        return plans
