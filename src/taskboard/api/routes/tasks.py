"""/v1/tasks endpoints."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from taskboard.api.dependencies import get_task_service
from taskboard.errors import TaskNotFound
from taskboard.models import Page, Status, Task, TaskCreate, TaskUpdate
from taskboard.services import TaskService

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.get("", response_model=Page, status_code=200)
def list_tasks(
    status: Status | None = None,
    assignee: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: TaskService = Depends(get_task_service),
) -> Page:
    return service.list(status=status, assignee=assignee, page=page, page_size=page_size)


@router.post("", response_model=Task, status_code=201)
def create_task(data: TaskCreate, service: TaskService = Depends(get_task_service)) -> Task:
    return service.create(data)


@router.get("/{task_id}", response_model=Task, status_code=200)
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    try:
        return service.get(task_id)
    except TaskNotFound:
        return JSONResponse(status_code=404, content={"detail": "Task not found"})


@router.patch("/{task_id}", response_model=Task, status_code=200)
def update_task(
    task_id: int, changes: TaskUpdate, service: TaskService = Depends(get_task_service)
) -> Task:
    return service.update(task_id, changes)


@router.delete("/{task_id}")
def delete_task(task_id: int, service: TaskService = Depends(get_task_service)) -> dict:
    service.delete(task_id)
    return {"deleted": True}
