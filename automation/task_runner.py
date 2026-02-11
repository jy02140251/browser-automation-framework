"""Task runner for executing automation workflows."""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    task_name: str
    status: TaskStatus
    duration_ms: float = 0.0
    result_data: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WorkflowResult:
    workflow_name: str
    total_tasks: int
    completed: int
    failed: int
    skipped: int
    total_duration_ms: float
    task_results: List[TaskResult]
    started_at: str
    finished_at: str


class AutomationTask:
    """Represents a single automation task."""

    def __init__(self, name: str, action: Callable[..., Awaitable], **kwargs):
        self.name = name
        self.action = action
        self.kwargs = kwargs
        self.depends_on: List[str] = []
        self.retry_count: int = kwargs.pop("retry_count", 0)
        self.timeout: int = kwargs.pop("timeout", 60)
        self.skip_on_failure: bool = kwargs.pop("skip_on_failure", False)

    def depends(self, *task_names: str) -> "AutomationTask":
        self.depends_on.extend(task_names)
        return self


class TaskRunner:
    """Execute a series of automation tasks with dependency resolution."""

    def __init__(self, name: str = "workflow"):
        self.name = name
        self._tasks: Dict[str, AutomationTask] = {}
        self._results: Dict[str, TaskResult] = {}

    def add_task(self, task: AutomationTask) -> "TaskRunner":
        self._tasks[task.name] = task
        return self

    async def execute(self, context: Dict[str, Any] = None) -> WorkflowResult:
        """Execute all tasks respecting dependencies."""
        context = context or {}
        start_time = time.perf_counter()
        started_at = datetime.utcnow().isoformat()

        execution_order = self._resolve_order()
        logger.info(f"Starting workflow '{self.name}' with {len(execution_order)} tasks")

        for task_name in execution_order:
            task = self._tasks[task_name]

            if not self._dependencies_met(task):
                self._results[task_name] = TaskResult(
                    task_name=task_name, status=TaskStatus.SKIPPED,
                    error="Dependencies not met",
                )
                continue

            result = await self._execute_task(task, context)
            self._results[task_name] = result

            if result.status == TaskStatus.COMPLETED and result.result_data:
                context[task_name] = result.result_data

        total_duration = (time.perf_counter() - start_time) * 1000
        results = list(self._results.values())

        return WorkflowResult(
            workflow_name=self.name,
            total_tasks=len(results),
            completed=sum(1 for r in results if r.status == TaskStatus.COMPLETED),
            failed=sum(1 for r in results if r.status == TaskStatus.FAILED),
            skipped=sum(1 for r in results if r.status == TaskStatus.SKIPPED),
            total_duration_ms=total_duration,
            task_results=results,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
        )

    async def _execute_task(self, task: AutomationTask, context: Dict) -> TaskResult:
        start = time.perf_counter()
        logger.info(f"Executing task: {task.name}")

        for attempt in range(task.retry_count + 1):
            try:
                result = await asyncio.wait_for(
                    task.action(context, **task.kwargs),
                    timeout=task.timeout,
                )
                duration = (time.perf_counter() - start) * 1000
                return TaskResult(
                    task_name=task.name, status=TaskStatus.COMPLETED,
                    duration_ms=duration, result_data=result,
                )
            except Exception as e:
                logger.error(f"Task '{task.name}' attempt {attempt + 1} failed: {e}")
                if attempt < task.retry_count:
                    await asyncio.sleep(1)

        duration = (time.perf_counter() - start) * 1000
        return TaskResult(
            task_name=task.name, status=TaskStatus.FAILED,
            duration_ms=duration, error=str(e),
        )

    def _dependencies_met(self, task: AutomationTask) -> bool:
        for dep in task.depends_on:
            result = self._results.get(dep)
            if not result or result.status != TaskStatus.COMPLETED:
                return False
        return True

    def _resolve_order(self) -> List[str]:
        visited = set()
        order = []

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            task = self._tasks.get(name)
            if task:
                for dep in task.depends_on:
                    visit(dep)
                order.append(name)

        for name in self._tasks:
            visit(name)
        return order