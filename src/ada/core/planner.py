"""
Task Planner - Decomposition and orchestration

The planner decomposes user intents into executable tasks,
builds dependency graphs, and optimizes execution order.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import uuid
import time


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Individual task node"""
    id: str
    name: str
    description: str
    action: Optional[str] = None           # Action type to execute
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        action: str = None,
        params: Dict = None,
        dependencies: List[str] = None
    ) -> "Task":
        """Create a new task with auto-generated ID"""
        return cls(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            action=action,
            params=params or {},
            dependencies=dependencies or []
        )


@dataclass
class TaskPlan:
    """Complete execution plan"""
    id: str
    intent_id: str
    tasks: List[Task]
    created_at: float
    current_task: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (all dependencies completed)"""
        completed_ids = {
            t.id for t in self.tasks
            if t.status == TaskStatus.COMPLETED
        }
        return [
            t for t in self.tasks
            if t.status == TaskStatus.PENDING
            and all(dep in completed_ids for dep in t.dependencies)
        ]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_progress(self) -> Dict[str, int]:
        """Get execution progress statistics"""
        stats = {status.value: 0 for status in TaskStatus}
        for task in self.tasks:
            stats[task.status.value] += 1
        return stats

    def is_complete(self) -> bool:
        """Check if all tasks are completed or skipped"""
        return all(
            t.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED, TaskStatus.CANCELLED]
            for t in self.tasks
        )

    def has_failed(self) -> bool:
        """Check if any task has failed"""
        return any(t.status == TaskStatus.FAILED for t in self.tasks)


class Planner:
    """
    Task planner that decomposes intents into executable tasks.

    Responsibilities:
    1. Decompose complex intents into tasks
    2. Build task dependency graph
    3. Topologically sort for optimal execution
    4. Handle dynamic task generation

    Example:
        planner = Planner(llm_client)
        plan = await planner.plan(intent, context)

        while not plan.is_complete():
            ready = plan.get_ready_tasks()
            for task in ready:
                result = await executor.execute(task)
                task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._task_templates: Dict[str, Callable] = {}

    def register_template(self, action_type: str, template: Callable):
        """Register a task template function"""
        self._task_templates[action_type] = template

    async def plan(
        self,
        intent: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> TaskPlan:
        """
        Create an execution plan from an intent.

        Args:
            intent: Structured intent with type, entities, params
            context: Additional context for planning

        Returns:
            TaskPlan ready for execution
        """
        intent_id = intent.get("id", str(uuid.uuid4())[:8])

        # Check for registered skill/template
        intent_type = intent.get("type", "")
        if intent_type in self._task_templates:
            tasks = await self._task_templates[intent_type](intent, context)
        else:
            # Use LLM for decomposition
            tasks = await self._decompose_with_llm(intent, context)

        # Build dependencies and sort
        self._resolve_dependencies(tasks)
        tasks = self._topological_sort(tasks)

        return TaskPlan(
            id=str(uuid.uuid4())[:8],
            intent_id=intent_id,
            tasks=tasks,
            created_at=time.time()
        )

    async def _decompose_with_llm(
        self,
        intent: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """Use LLM to decompose complex intent into tasks"""
        if not self.llm:
            # Fallback: single task
            return [
                Task.create(
                    name=f"Execute {intent.get('type', 'unknown')}",
                    description=intent.get("raw_input", ""),
                    action=intent.get("type"),
                    params=intent.get("entities", {})
                )
            ]

        prompt = self._build_planning_prompt(intent, context)
        response = await self.llm.generate(prompt)
        return self._parse_llm_response(response)

    def _build_planning_prompt(self, intent: Dict, context: Dict) -> str:
        """Build the prompt for LLM task decomposition"""
        return f"""
分析以下用户意图，将其分解为具体的执行任务。

意图类型: {intent.get('type')}
实体信息: {intent.get('entities')}
原始输入: {intent.get('raw_input')}
上下文: {context}

请输出 JSON 格式的任务列表，每个任务包含:
- name: 任务名称 (简短)
- description: 任务描述 (详细)
- action: 对应的动作类型 (如 file.read, app.launch 等)
- params: 参数字典
- dependencies: 依赖的任务名称列表 (如果有的话)

示例输出:
{{
  "tasks": [
    {{
      "name": "扫描文件",
      "description": "扫描下载文件夹中的所有文件",
      "action": "file.list",
      "params": {{"path": "~/Downloads"}},
      "dependencies": []
    }},
    {{
      "name": "分类文件",
      "description": "根据文件类型进行分类",
      "action": "file.classify",
      "params": {{"strategy": "by_type"}},
      "dependencies": ["扫描文件"]
    }}
  ]
}}
"""

    def _parse_llm_response(self, response: str) -> List[Task]:
        """Parse LLM response into Task objects"""
        import json

        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
            else:
                data = json.loads(response)

            tasks = []
            name_to_id = {}

            # First pass: create tasks and record name->id mapping
            for t in data.get("tasks", []):
                task = Task.create(
                    name=t.get("name", "unnamed"),
                    description=t.get("description", ""),
                    action=t.get("action"),
                    params=t.get("params", {})
                )
                tasks.append(task)
                name_to_id[task.name] = task.id

            # Second pass: resolve dependencies
            for i, t in enumerate(data.get("tasks", [])):
                deps = t.get("dependencies", [])
                resolved = [name_to_id[d] for d in deps if d in name_to_id]
                tasks[i].dependencies = resolved

            return tasks

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: create single task
            return [
                Task.create(
                    name="Execute intent",
                    description="Execute the user's intent",
                    action="generic.execute"
                )
            ]

    def _resolve_dependencies(self, tasks: List[Task]):
        """Resolve task dependencies from names to IDs"""
        name_to_id = {t.name: t.id for t in tasks}
        for task in tasks:
            resolved = []
            for dep in task.dependencies:
                if dep in name_to_id:
                    resolved.append(name_to_id[dep])
                # If dep is already an ID, keep it
                elif any(t.id == dep for t in tasks):
                    resolved.append(dep)
            task.dependencies = resolved

    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by dependencies using Kahn's algorithm"""
        if not tasks:
            return tasks

        # Build in-degree map and adjacency list
        in_degree = {t.id: 0 for t in tasks}
        graph = {t.id: [] for t in tasks}
        task_map = {t.id: t for t in tasks}

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in graph:
                    graph[dep_id].append(task.id)
                    in_degree[task.id] += 1

        # Find all tasks with no dependencies
        queue = [t for t in tasks if in_degree[t.id] == 0]
        result = []

        while queue:
            task = queue.pop(0)
            result.append(task)

            for next_id in graph[task.id]:
                in_degree[next_id] -= 1
                if in_degree[next_id] == 0:
                    queue.append(task_map[next_id])

        # If not all tasks included, there's a cycle
        if len(result) != len(tasks):
            # Add remaining tasks anyway (will fail at runtime)
            remaining = [t for t in tasks if t not in result]
            result.extend(remaining)

        return result
