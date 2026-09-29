---
description: Scaffold a new API endpoint with its service method and tests, following the team's API conventions
argument-hint: <METHOD> <path> <what it does>
allowed-tools: Bash(uv run pytest *)
---

Add this endpoint: **$ARGUMENTS**

Work through the layers in this order, and follow `.claude/rules/api-conventions.md`:

1. **Service**: add or extend a method on the service in `src/taskboard/services/`. Business
   rules go here, and failures raise errors from `taskboard.errors`.
2. **Route**: add a thin handler to the resource's router in `src/taskboard/api/routes/`, with an
   explicit `response_model` and `status_code`.
3. **Tests**: add API tests in `tests/test_<resource>_api.py` for success, validation (422), and
   not found (404) where it applies.
4. Run `uv run pytest` and report the result.

Before writing code, restate the endpoint contract in three lines (request, success response,
error codes). If the request is ambiguous, ask instead of guessing.
