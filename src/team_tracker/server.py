"""team-tracker MCP server (stdio).

Registered for the whole team in `.mcp.json`, so every developer who clones the repo gets it.
Run it by hand with `uv run team-tracker-mcp`.
"""

from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from team_tracker.tracker import Tracker, TrackerConfig, TrackerError

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def build_server(tracker: Tracker | None = None) -> MCPServer:
    tracker = tracker or Tracker(TrackerConfig.from_env())
    server = MCPServer(
        "team-tracker",
        version="1.0.0",
        instructions=(
            "The team's issue tracker. Issue IDs look like TB-101. Use get_issue to read the "
            "description, acceptance criteria, and open design questions before changing code."
        ),
    )

    def call(operation):
        try:
            return operation()
        except TrackerError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(annotations=READ_ONLY)
    def whoami() -> dict:
        """Report whether the tracker credentials are valid, and for which project.

        Use this to diagnose connection problems. Returns `authenticated`, `project_key`, a masked
        `token_fingerprint` (never the token), and `problem` when authentication fails.
        """
        return tracker.whoami()

    @server.tool(annotations=READ_ONLY)
    def list_issues(
        status: Literal["open", "closed"] | None = None, label: str | None = None
    ) -> list[dict]:
        """List issues as summaries (id, title, kind, status, labels).

        Use it to find work. It does not return descriptions or acceptance criteria: call
        get_issue for one issue's full detail.
        """
        return call(lambda: tracker.list_issues(status=status, label=label))

    @server.tool(annotations=READ_ONLY)
    def get_issue(issue_id: str) -> dict:
        """Get one issue in full: description, acceptance criteria, open design questions, comments.

        `issue_id` looks like TB-101. Read this before starting any change linked to an issue.
        A non-empty `open_questions` list means the design is not settled yet.
        """
        return call(lambda: tracker.get_issue(issue_id))

    @server.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
        )
    )
    def add_comment(issue_id: str, body: str) -> dict:
        """Post a comment on an issue, for example a fix summary or a proposed plan.

        Not idempotent: calling it twice posts two comments. Returns the new comment.
        """
        return call(lambda: tracker.add_comment(issue_id, body))

    return server


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
