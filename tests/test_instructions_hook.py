"""The InstructionsLoaded hook script that records which instruction files Claude Code loads."""

import json
import os
import subprocess
import sys


def run_hook(project_root, hook_root, stdin: str) -> subprocess.CompletedProcess:
    script = project_root / ".claude" / "hooks" / "log_instructions_loaded.py"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(hook_root)}
    return subprocess.run(
        [sys.executable, str(script)], input=stdin, env=env, capture_output=True, text=True
    )


def test_hook_appends_one_record_per_event(project_root, tmp_path):
    rule = tmp_path / ".claude" / "rules" / "api-conventions.md"
    trigger = tmp_path / "src" / "taskboard" / "api" / "routes" / "tasks.py"
    event = {
        "hook_event_name": "InstructionsLoaded",
        "session_id": "abc",
        "file_path": str(rule),
        "memory_type": "Project",
        "load_reason": "path_glob_match",
        "globs": ["src/taskboard/api/**/*.py"],
        "trigger_file_path": str(trigger),
    }

    first = run_hook(project_root, tmp_path, json.dumps(event))
    run_hook(project_root, tmp_path, json.dumps({**event, "load_reason": "session_start"}))

    assert first.returncode == 0
    log = tmp_path / ".claude" / "logs" / "instructions-loaded.jsonl"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(records) == 2
    assert records[0]["file"] == ".claude/rules/api-conventions.md"
    assert records[0]["trigger_file"] == "src/taskboard/api/routes/tasks.py"
    assert records[0]["load_reason"] == "path_glob_match"


def test_hook_never_fails_the_session_on_bad_input(project_root, tmp_path):
    result = run_hook(project_root, tmp_path, "not json")

    assert result.returncode == 0
    assert result.stdout == ""
