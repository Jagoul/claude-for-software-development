# Taskboard: team instructions for Claude Code

This file is committed, so every developer's Claude Code session loads the same rules.
Personal preferences belong in `CLAUDE.local.md` (git-ignored) or `~/.claude/CLAUDE.md`.
Conventions for one area of the code live in `.claude/rules/` and load only when Claude works on
matching files.

## Project

Taskboard is a FastAPI service for team task tracking.

- `src/taskboard/api/`: HTTP layer (routers, dependencies, error envelope)
- `src/taskboard/services/`: business rules
- `src/taskboard/storage/`: repository (in memory today)
- `src/taskboard/models.py`: Pydantic models
- `src/team_tracker/`: MCP server for our issue tracker
- `src/claude_config_check/`: linter for this Claude Code setup
- `tests/`: pytest suite

## Commands

- `uv run pytest`: full test suite. It must pass before you say a change is done.
- `uv run ruff check . && uv run ruff format --check .`: lint and format check.
- `uv run taskboard-api`: run the API at http://127.0.0.1:8000 (docs at `/docs`).
- `uv run check-claude-config`: validate `CLAUDE.md`, rules, skills, commands, and `.mcp.json`.

## Coding standards

- Python 3.12. Type hints on every public function. Write `X | None`, not `Optional[X]`.
- Layering is strict: `api` → `services` → `storage`. Routes never touch the repository.
  Services raise errors from `taskboard.errors`; the API layer maps them to HTTP.
- New code uses Pydantic v2 APIs. The v1 idioms still in the code are tracked as TB-102; do
  not add more.
- No `print`. Use `logging.getLogger(__name__)`.
- Prefer small functions and early returns. Every module starts with a one-line docstring.
- Do not add a dependency without saying so explicitly in your summary.
- Never hard-code secrets and never read `.env` files.

## Testing conventions

- pytest only: plain functions and fixtures, no `unittest.TestCase`.
- A bug fix starts with a failing test that reproduces the bug. A feature ships with tests at
  the API level.
- Test names describe behaviour: `test_<behaviour>_<condition>`.
- Known bugs are pinned with `@pytest.mark.xfail(strict=True, reason="TB-###: ...")`. The fix
  removes the marker, and the strict flag makes a forgotten marker fail the suite.
- Tests must not depend on execution order, the network, or the wall clock.
- Run the full suite before you finish, and report failures verbatim.

## Workflow

- Issue IDs look like `TB-123`. Read the issue with the `team-tracker` MCP server (`get_issue`)
  before starting work on it.
- Use plan mode when a change touches more than three files, migrates a library, or the issue
  lists open design questions. Execute directly for a well-specified fix in one file.
- Commit messages: `TB-123: imperative summary`.
