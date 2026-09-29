"""FastAPI dependencies shared by the routers."""

from fastapi import Request

from taskboard.services import TaskService


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service
