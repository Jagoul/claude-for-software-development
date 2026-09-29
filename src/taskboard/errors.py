"""Domain errors raised by the service layer. The API layer maps them to HTTP responses."""


class TaskboardError(Exception):
    """Base class for domain errors."""

    code = "TASKBOARD_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TaskNotFound(TaskboardError):
    code = "TASK_NOT_FOUND"

    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} does not exist.")
        self.task_id = task_id


class InvalidTransition(TaskboardError):
    code = "INVALID_STATUS_TRANSITION"
