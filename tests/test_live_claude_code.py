"""Live checks: run the real Claude Code CLI headlessly and observe what it loads and calls.

Run with `uv run pytest -m live`. Needs the `claude` CLI, signed in, and this folder trusted
(run `claude` here once and accept the trust dialog): in an untrusted folder Claude Code ignores
the project's hooks, permissions, and MCP approvals. Each test makes a small real request,
using Haiku unless CLAUDE_LIVE_MODEL says otherwise.
"""

import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG = PROJECT_ROOT / ".claude" / "logs" / "instructions-loaded.jsonl"
MODEL = os.environ.get("CLAUDE_LIVE_MODEL", "haiku")
READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed"),
]


def claude(prompt: str, *, token: str = "tt_live_default_0000", stream: bool = False):
    fmt = ["--output-format", "stream-json", "--verbose"] if stream else ["--output-format", "json"]
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", MODEL, "--max-turns", "12", *fmt],
        cwd=PROJECT_ROOT,
        env={**os.environ, "TRACKER_TOKEN": token},
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    if not stream:
        return json.loads(result.stdout)
    return [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]


def loaded(session_id: str) -> list[dict]:
    """InstructionsLoaded events recorded by the project hook for one session."""
    if not LOG.exists():
        return []
    records = [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]
    return [record for record in records if record["session_id"] == session_id]


def read_file(path: str) -> dict:
    return claude(
        f"Use the Read tool to read `{path}`, then reply with only its number of lines. "
        "Do not read, search, or list any other file."
    )


def test_project_instructions_load_at_start_and_rules_do_not():
    run = claude("Reply with exactly: ok. Do not use any tools.")

    events = loaded(run["session_id"])
    at_start = {e["file"]: e["memory_type"] for e in events if e["load_reason"] == "session_start"}
    assert at_start.get("CLAUDE.md") == "Project"
    assert not [e for e in events if e["file"].startswith(".claude/rules/")]


@pytest.mark.parametrize(
    ("path", "expected_rule"),
    [
        ("src/taskboard/api/routes/tasks.py", ".claude/rules/api-conventions.md"),
        ("tests/test_models.py", ".claude/rules/testing-conventions.md"),
        ("src/taskboard/models.py", ".claude/rules/domain-models.md"),
        ("README.md", None),
    ],
)
def test_path_scoped_rule_loads_only_for_matching_file(path, expected_rule):
    run = read_file(path)

    matched = [e for e in loaded(run["session_id"]) if e["load_reason"] == "path_glob_match"]
    assert [e["file"] for e in matched] == ([expected_rule] if expected_rule else [])
    assert all(e["trigger_file"] == path for e in matched)


def test_subdirectory_claude_md_loads_when_its_folder_is_touched():
    run = read_file("src/team_tracker/server.py")

    files = {e["file"] for e in loaded(run["session_id"]) if e["load_reason"] != "session_start"}
    assert "src/team_tracker/CLAUDE.md" in files


def test_project_mcp_server_receives_token_from_environment():
    token = f"tt_live_{secrets.token_hex(6)}"

    run = claude(
        "Call the team-tracker whoami tool and reply with only its token_fingerprint value.",
        token=token,
    )

    assert token[-4:] in run["result"]
    assert token not in run["result"]


def test_forked_skill_runs_in_isolation_with_read_only_tools():
    events = claude("/api-audit", stream=True)

    started = next(e for e in events if e.get("subtype") == "task_started")
    finished = next(e for e in events if e.get("subtype") == "task_notification")
    main_tool_calls = [
        block
        for e in events
        if e.get("type") == "assistant"
        for block in e["message"]["content"]
        if block["type"] == "tool_use"
    ]
    fork_tool_calls = [
        block["name"]
        for line in Path(finished["output_file"]).read_text().splitlines()
        for block in (json.loads(line).get("message") or {}).get("content") or []
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]
    report = next(e for e in events if e.get("type") == "result")["result"]

    assert started["subagent_type"] == "read-only-auditor"
    assert main_tool_calls == []
    assert fork_tool_calls and set(fork_tool_calls) <= READ_ONLY_TOOLS
    assert "API audit:" in report
    assert "tasks.py" in report


def test_project_and_personal_mcp_servers_are_both_available():
    listing = subprocess.run(
        ["claude", "mcp", "list"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "TRACKER_TOKEN": "tt_live_default_0000"},
        capture_output=True,
        text=True,
        timeout=300,
    ).stdout
    if "sandbox-time" not in listing:
        pytest.skip("personal server not registered: run scripts/personal-mcp.sh add")

    connected = {line.split(":")[0] for line in listing.splitlines() if "Connected" in line}
    assert {"team-tracker", "sandbox-time"} <= connected
