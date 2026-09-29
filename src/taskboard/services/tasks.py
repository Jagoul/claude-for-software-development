"""Task business rules: filtering, pagination, and status transitions."""

from taskboard.errors import InvalidTransition, TaskNotFound
from taskboard.models import Page, Status, Task, TaskCreate, TaskUpdate
from taskboard.storage import TaskRepository

# A finished task can only be reopened into progress, never straight back to the backlog.
ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.TODO: {Status.IN_PROGRESS, Status.DONE},
    Status.IN_PROGRESS: {Status.TODO, Status.DONE},
    Status.DONE: {Status.IN_PROGRESS},
}


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create(self, data: TaskCreate) -> Task:
        return self._repository.add(data)

    def get(self, task_id: int) -> Task:
        task = self._repository.get(task_id)
        if task is None:
            raise TaskNotFound(task_id)
        return task

    def list(
        self,
        *,
        status: Status | None = None,
        assignee: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page:
        tasks = self._repository.list_all()
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        if assignee is not None:
            tasks = [task for task in tasks if task.assignee == assignee]

        start = page * page_size
        return Page(
            items=tasks[start : start + page_size],
            page=page,
            page_size=page_size,
            total=len(tasks),
        )

    def update(self, task_id: int, changes: TaskUpdate) -> Task:
        task = self.get(task_id)
        data = changes.dict(exclude_unset=True)
        new_status = data.get("status")
        if new_status is not None and new_status != task.status:
            if new_status not in ALLOWED_TRANSITIONS[task.status]:
                raise InvalidTransition(
                    f"Cannot move task {task_id} from {task.status} to {new_status}."
                )
        return self._repository.save_changes(task_id, data)

    def delete(self, task_id: int) -> None:
        if not self._repository.delete(task_id):
            raise TaskNotFound(task_id)
