"""The team-tracker MCP server: credential handling, tools, and a real stdio MCP session."""

import asyncio
import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters, stdio_client

from team_tracker.tracker import Tracker, TrackerConfig, TrackerError

VALID_TOKEN = "tt_test_token_1234"


def tracker(token: str | None = VALID_TOKEN, project: str = "TB") -> Tracker:
    return Tracker(TrackerConfig(token=token, project_key=project))


@pytest.mark.parametrize(
    ("token", "problem"),
    [
        (None, "not set"),
        ("${TRACKER_TOKEN}", "unexpanded"),
        ("hunter2", "malformed"),
    ],
)
def test_bad_credentials_are_explained_and_block_every_read(token, problem):
    broken = tracker(token)

    assert problem in broken.whoami()["problem"]
    with pytest.raises(TrackerError, match="UNAUTHORIZED"):
        broken.list_issues()


def test_whoami_masks_the_token():
    identity = tracker().whoami()

    assert identity["authenticated"] is True
    assert identity["token_fingerprint"] == "tt_…1234"
    assert VALID_TOKEN not in str(identity)


def test_config_reads_project_key_with_default():
    assert TrackerConfig.from_env({"TRACKER_TOKEN": VALID_TOKEN}).project_key == "TB"
    assert TrackerConfig.from_env({"TRACKER_PROJECT": "OPS"}).project_key == "OPS"


def test_issue_ids_follow_the_project_key():
    ids = {issue["id"] for issue in tracker(project="OPS").list_issues()}

    assert "OPS-101" in ids


def test_list_issues_filters_by_status_and_label():
    open_ids = {issue["id"] for issue in tracker().list_issues(status="open")}
    design = tracker().list_issues(label="needs-design")

    assert open_ids == {"TB-101", "TB-102", "TB-103"}
    assert [issue["id"] for issue in design] == ["TB-103"]


def test_get_issue_returns_detail_and_open_questions():
    issue = tracker().get_issue("tb-103")

    assert issue["kind"] == "feature"
    assert issue["acceptance_criteria"]
    assert len(issue["open_questions"]) == 4


def test_get_issue_unknown_id_lists_known_ones():
    with pytest.raises(TrackerError, match="NOT_FOUND.*TB-101"):
        tracker().get_issue("TB-999")


def test_add_comment_appends_and_rejects_empty_body():
    board = tracker()

    comment = board.add_comment("TB-101", "Fixed the slice start.")

    assert comment["id"] == "C-1"
    assert board.get_issue("TB-101")["comments"] == [comment]
    with pytest.raises(TrackerError, match="VALIDATION"):
        board.add_comment("TB-101", "   ")


# --- Over a real stdio MCP session ------------------------------------------------------------


def server_params(token: str | None) -> StdioServerParameters:
    env = {key: value for key, value in os.environ.items() if not key.startswith("TRACKER_")}
    if token is not None:
        env["TRACKER_TOKEN"] = token
    return StdioServerParameters(
        command=sys.executable, args=["-m", "team_tracker.server"], env=env
    )


async def with_session(token: str | None, action):
    async with stdio_client(server_params(token)) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await action(session)


def test_mcp_lists_tools_with_annotations():
    async def action(session):
        return (await session.list_tools()).tools

    tools = {tool.name: tool for tool in asyncio.run(with_session(VALID_TOKEN, action))}

    assert set(tools) == {"whoami", "list_issues", "get_issue", "add_comment"}
    assert tools["get_issue"].annotations.read_only_hint is True
    assert tools["add_comment"].annotations.idempotent_hint is False
    assert "get_issue" in tools["list_issues"].description


def test_mcp_get_issue_with_token_from_environment():
    async def action(session):
        return await session.call_tool("get_issue", {"issue_id": "TB-101"})

    result = asyncio.run(with_session(VALID_TOKEN, action))

    assert result.is_error is False
    assert "skips the first page" in result.content[0].text


def test_mcp_without_token_returns_unauthorized_tool_error():
    async def action(session):
        return await session.call_tool("list_issues", {})

    result = asyncio.run(with_session(None, action))

    assert result.is_error is True
    assert "UNAUTHORIZED" in result.content[0].text
