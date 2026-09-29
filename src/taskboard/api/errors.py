"""The API error envelope: every error response is {"error": {"code": ..., "message": ...}}."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from taskboard.errors import InvalidTransition, TaskboardError, TaskNotFound

STATUS_BY_ERROR: dict[type[TaskboardError], int] = {
    TaskNotFound: 404,
    InvalidTransition: 409,
}


class ApiError(Exception):
    """Raise from a route to return an enveloped error with an explicit status and code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def envelope(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return envelope(exc.status_code, exc.code, exc.message)

    @app.exception_handler(TaskboardError)
    async def handle_domain_error(_request: Request, exc: TaskboardError) -> JSONResponse:
        return envelope(STATUS_BY_ERROR.get(type(exc), 400), exc.code, exc.message)
