"""Shared fixtures: a fresh app per test, its service, and a task factory."""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from taskboard.main import create_app
from taskboard.models import Task, TaskCreate
from taskboard.services import TaskService
from taskboard.storage import TaskRepository

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repository() -> TaskRepository:
    return TaskRepository()


@pytest.fixture
def service(repository: TaskRepository) -> TaskService:
    return TaskService(repository)


@pytest.fixture
def client(repository: TaskRepository) -> TestClient:
    return TestClient(create_app(repository))


@pytest.fixture
def make_tasks(service: TaskService) -> Callable[[int], list[Task]]:
    def make(count: int, **fields) -> list[Task]:
        return [
            service.create(TaskCreate.parse_obj({"title": f"Task {n}", **fields}))
            for n in range(1, count + 1)
        ]

    return make


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT
