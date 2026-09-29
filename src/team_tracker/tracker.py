"""Issue data, credential handling, and the operations the MCP tools expose.

Credentials arrive through environment variables that Claude Code fills in from `.mcp.json`
(`"TRACKER_TOKEN": "${TRACKER_TOKEN}"`). The token itself is never committed and never echoed
back: `whoami` only reports a masked fingerprint.
"""

import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

TOKEN_PATTERN = re.compile(r"^tt_[A-Za-z0-9_]{8,}$")
UNEXPANDED = re.compile(r"^\$\{[^}]+\}$")


class TrackerError(Exception):
    """An error the MCP layer returns to the client as an `isError` tool result."""


@dataclass(frozen=True)
class TrackerConfig:
    token: str | None
    project_key: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "TrackerConfig":
        env = os.environ if env is None else env
        token = env.get("TRACKER_TOKEN") or None
        return cls(token=token, project_key=env.get("TRACKER_PROJECT") or "TB")

    def auth_problem(self) -> str | None:
        """Why the token can't be used, or None when it is valid."""
        if self.token is None:
            return (
                "TRACKER_TOKEN is not set. Export it in the shell that starts Claude Code "
                "(see .env.example); .mcp.json passes it through as ${TRACKER_TOKEN}."
            )
        if UNEXPANDED.match(self.token):
            return (
                f"TRACKER_TOKEN arrived unexpanded as {self.token!r}. The variable was not set "
                "when Claude Code started. Export it and restart the session."
            )
        if not TOKEN_PATTERN.match(self.token):
            return (
                "TRACKER_TOKEN is malformed. Tracker tokens look like tt_<at least 8 characters>."
            )
        return None

    def fingerprint(self) -> str:
        if not self.token:
            return "(none)"
        return f"tt_…{self.token[-4:]}"


@dataclass
class Issue:
    id: str
    title: str
    kind: str
    status: str
    labels: list[str]
    description: str
    acceptance_criteria: list[str]
    open_questions: list[str] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "status": self.status,
            "labels": self.labels,
        }

    def detail(self) -> dict:
        return {
            **self.summary(),
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "open_questions": self.open_questions,
            "comments": self.comments,
        }


def seed_issues(project_key: str) -> dict[str, Issue]:
    issues = [
        Issue(
            id=f"{project_key}-101",
            title="Task list skips the first page of results",
            kind="bug",
            status="open",
            labels=["bug", "api", "customer-reported"],
            description=(
                "GET /v1/tasks returns an empty `items` list when a team has fewer than 20 "
                "tasks, and page 2 shows the tasks that should be on page 1. `total` is correct. "
                "QA pinned it with "
                "tests/test_tasks_api.py::test_first_page_returns_first_tasks, currently marked "
                "xfail(strict=True)."
            ),
            acceptance_criteria=[
                "GET /v1/tasks?page=1 returns the first page_size tasks, oldest first.",
                "The xfail marker on test_first_page_returns_first_tasks is removed and it passes.",
                "uv run pytest passes.",
            ],
        ),
        Issue(
            id=f"{project_key}-102",
            title="Migrate models and call sites from Pydantic v1 idioms to Pydantic v2",
            kind="migration",
            status="open",
            labels=["tech-debt", "dependencies"],
            description=(
                "We run Pydantic 2 but still write Pydantic 1: @validator, @root_validator, "
                "class-based Config, Field(max_items=...), and call sites using .dict(), "
                ".copy(update=...) and .parse_obj(). Each emits PydanticDeprecatedSince20 and the "
                "v1 shims are scheduled for removal. The usages are spread across models, storage, "
                "services, and tests."
            ),
            acceptance_criteria=[
                "No Pydantic v1 API remains anywhere in src/ or tests/.",
                "Behaviour is unchanged: validation errors, stripping, tag normalisation, partial "
                "updates.",
                "tests/test_migration_readiness.py passes with its xfail marker removed.",
                "uv run pytest -W error::DeprecationWarning passes.",
            ],
        ),
        Issue(
            id=f"{project_key}-103",
            title="Rate-limit write endpoints",
            kind="feature",
            status="open",
            labels=["feature", "api", "needs-design"],
            description=(
                "A misbehaving integration created 40k tasks in an hour. Limit how fast a client "
                "can call POST, PATCH and DELETE on /v1/tasks. Reads stay unlimited. Clients send "
                "an X-Client-Id header; some older scripts don't."
            ),
            acceptance_criteria=[
                "Writes over the limit get 429 in the standard error envelope with a Retry-After "
                "header.",
                "The limit is configurable without a code change.",
                "Tests cover allowed, limited, and window-reset behaviour without sleeping.",
            ],
            open_questions=[
                "Algorithm: fixed window, sliding window, or token bucket?",
                "Placement: ASGI middleware, a FastAPI dependency on the write routes, or the "
                "service layer?",
                "Key: X-Client-Id, client IP, or both? What happens when the header is missing?",
                "State: in-process memory now; do we need an interface ready for Redis later?",
            ],
        ),
        Issue(
            id=f"{project_key}-099",
            title="Add a liveness endpoint",
            kind="feature",
            status="closed",
            labels=["ops"],
            description="Load balancers need GET /healthz returning 200 and the version.",
            acceptance_criteria=["GET /healthz returns {status: ok, version}."],
        ),
    ]
    return {issue.id: issue for issue in issues}


class Tracker:
    def __init__(self, config: TrackerConfig) -> None:
        self.config = config
        self._issues = seed_issues(config.project_key)

    def _require_auth(self) -> None:
        problem = self.config.auth_problem()
        if problem:
            raise TrackerError(f"UNAUTHORIZED: {problem}")

    def whoami(self) -> dict:
        problem = self.config.auth_problem()
        return {
            "authenticated": problem is None,
            "project_key": self.config.project_key,
            "token_fingerprint": self.config.fingerprint(),
            "problem": problem,
        }

    def list_issues(self, status: str | None = None, label: str | None = None) -> list[dict]:
        self._require_auth()
        issues = self._issues.values()
        if status:
            issues = [issue for issue in issues if issue.status == status]
        if label:
            issues = [issue for issue in issues if label in issue.labels]
        return [issue.summary() for issue in issues]

    def get_issue(self, issue_id: str) -> dict:
        self._require_auth()
        issue = self._issues.get(issue_id.strip().upper())
        if issue is None:
            known = ", ".join(sorted(self._issues))
            raise TrackerError(f"NOT_FOUND: no issue {issue_id!r}. Known issues: {known}.")
        return issue.detail()

    def add_comment(self, issue_id: str, body: str) -> dict:
        self._require_auth()
        issue = self._issues.get(issue_id.strip().upper())
        if issue is None:
            raise TrackerError(f"NOT_FOUND: no issue {issue_id!r}.")
        if not body.strip():
            raise TrackerError("VALIDATION: comment body must not be empty.")
        comment = {
            "id": f"C-{len(issue.comments) + 1}",
            "author": "claude-code",
            "body": body.strip(),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        issue.comments.append(comment)
        return comment
