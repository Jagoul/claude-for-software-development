"""In-memory task repository. Swappable for a database-backed one behind the same methods."""

from datetime import UTC, datetime

from taskboard.models import Task, TaskCreate


class TaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def add(self, data: TaskCreate) -> Task:
        now = datetime.now(UTC)
        task = Task(id=self._next_id, created_at=now, updated_at=now, **data.dict())
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Task | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[Task]:
        """All tasks, oldest first."""
        return [self._tasks[task_id] for task_id in sorted(self._tasks)]

    def save_changes(self, task_id: int, changes: dict) -> Task:
        current = self._tasks[task_id]
        updated = current.copy(update={**changes, "updated_at": datetime.now(UTC)})
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None
