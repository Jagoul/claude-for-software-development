"""TB-102 acceptance check: the app runs with Pydantic deprecation warnings turned into errors."""

import subprocess
import sys
import textwrap

import pytest

RUN_THE_APP = textwrap.dedent(
    """
    from taskboard.models import TaskCreate, TaskUpdate
    from taskboard.services import TaskService
    from taskboard.storage import TaskRepository

    service = TaskService(TaskRepository())
    task = service.create(TaskCreate(title="Migrate", tags=["Tech-Debt"]))
    service.update(task.id, TaskUpdate(status="in_progress"))
    service.list(page=1, page_size=10)
    """
)


@pytest.mark.xfail(strict=True, reason="TB-102: models and call sites still use Pydantic v1 idioms")
def test_app_runs_without_pydantic_deprecation_warnings():
    result = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", RUN_THE_APP],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
