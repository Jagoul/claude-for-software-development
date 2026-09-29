---
paths:
  - "src/taskboard/api/**/*.py"
---

# API conventions

These apply to everything under `src/taskboard/api/`.

- One `APIRouter` per resource in `src/taskboard/api/routes/<resource>.py`, with
  `prefix="/v1/<plural>"` and `tags=["<plural>"]`. Only `/healthz` is unversioned.
- Every endpoint declares `response_model` and `status_code` explicitly. `POST` returns 201.
  `DELETE` returns 204 with no body (`response_class=Response`).
- Errors use the envelope `{"error": {"code": "UPPER_SNAKE", "message": "..."}}`. Raise
  `ApiError(status, code, message)` or let a domain error from `taskboard.errors` propagate.
  Never build an error `JSONResponse` in a route, and never return `{"detail": ...}`.
- Routes stay thin: accept input, call one service method, return the result. No business
  rules, no `try/except` around service calls, no repository access.
- Get services through `Depends(get_task_service)`.
- Lists paginate with `page` (1-based, `ge=1`) and `page_size` (`ge=1, le=100`, default 20) and
  return `Page`.
- Query parameters and JSON fields are `snake_case`.
- A new endpoint comes with tests in `tests/test_<resource>_api.py`: success, validation (422),
  and not found (404) where it applies.
