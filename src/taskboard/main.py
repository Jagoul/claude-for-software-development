"""Application factory and the `taskboard-api` entry point."""

import os

from fastapi import FastAPI

from taskboard import __version__
from taskboard.api.errors import install_error_handlers
from taskboard.api.routes import health, tasks
from taskboard.services import TaskService
from taskboard.storage import TaskRepository


def create_app(repository: TaskRepository | None = None) -> FastAPI:
    app = FastAPI(title="Taskboard", version=__version__)
    app.state.task_service = TaskService(repository or TaskRepository())
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(tasks.router)
    return app


def run() -> None:
    import uvicorn

    port = int(os.environ.get("TASKBOARD_PORT", "8000"))
    uvicorn.run(create_app(), host="127.0.0.1", port=port)
