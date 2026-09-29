"""Liveness endpoint. Unversioned on purpose: load balancers probe it directly."""

from fastapi import APIRouter
from pydantic import BaseModel

from taskboard import __version__

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    version: str


@router.get("/healthz", response_model=Health, status_code=200)
def healthz() -> Health:
    return Health(status="ok", version=__version__)
