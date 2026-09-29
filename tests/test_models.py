"""Model validation behaviour. It must survive the Pydantic v2 migration (TB-102) unchanged."""

import pytest
from pydantic import ValidationError

from taskboard.models import Priority, TaskCreate, TaskUpdate


def test_task_create_strips_title_and_normalises_tags():
    task = TaskCreate.parse_obj({"title": "  Ship it ", "tags": ["  Backend", "URGENT "]})

    assert task.dict()["title"] == "Ship it"
    assert task.tags == ["backend", "urgent"]
    assert task.priority is Priority.MEDIUM


def test_task_create_rejects_more_than_ten_tags():
    with pytest.raises(ValidationError):
        TaskCreate(title="Too many", tags=[f"t{n}" for n in range(11)])


def test_task_update_requires_at_least_one_field():
    with pytest.raises(ValidationError, match="at least one field"):
        TaskUpdate()


def test_task_update_keeps_only_sent_fields():
    update = TaskUpdate(status="done")

    assert update.dict(exclude_unset=True) == {"status": "done"}
