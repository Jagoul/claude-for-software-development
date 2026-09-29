"""Domain models for Taskboard.

These models still use Pydantic v1 idioms (`@validator`, `@root_validator`, class-based
`Config`, `max_items`). They work on Pydantic v2 but emit deprecation warnings. Migrating them,
and every call site that uses `.dict()`, `.copy(update=...)` or `.parse_obj()`, is tracked as
TB-102.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, root_validator, validator


class Status(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCreate(BaseModel):
    """Payload for creating a task."""

    title: str = Field(..., min_length=1, max_length=120)
    description: str = ""
    priority: Priority = Priority.MEDIUM
    assignee: str | None = None
    due_date: date | None = None
    tags: list[str] = Field(default_factory=list, max_items=10)

    class Config:
        validate_assignment = True

    @validator("title")
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @validator("tags", each_item=True)
    def normalise_tag(cls, value: str) -> str:
        return value.strip().lower()


class TaskUpdate(BaseModel):
    """Partial update. Only the fields that are sent are changed."""

    title: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    status: Status | None = None
    priority: Priority | None = None
    assignee: str | None = None
    due_date: date | None = None

    @root_validator(skip_on_failure=True)
    def at_least_one_field(cls, values: dict) -> dict:
        if all(value is None for value in values.values()):
            raise ValueError("send at least one field to update")
        return values


class Task(BaseModel):
    """A stored task."""

    id: int
    title: str
    description: str = ""
    status: Status = Status.TODO
    priority: Priority = Priority.MEDIUM
    assignee: str | None = None
    due_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    """One page of a list result. `page` is 1-based."""

    items: list[Task]
    page: int
    page_size: int
    total: int
