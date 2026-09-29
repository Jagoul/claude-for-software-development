#!/usr/bin/env python3
"""InstructionsLoaded hook: record every CLAUDE.md and rules file Claude Code loads, and why.

Claude Code pipes the event as JSON on stdin. Each event becomes one line in
`.claude/logs/instructions-loaded.jsonl` (git-ignored), which shows whether a path-scoped rule
loaded at session start or only when a matching file was touched. It runs on whatever `python3`
each developer has (macOS still ships 3.9), so it sticks to the standard library and Python 3.8
syntax, and it never fails the session: any error is swallowed.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def relative(path: str | None, root: Path) -> str | None:
    if not path:
        return None
    try:
        return str(Path(path).resolve().relative_to(root))
    except ValueError:
        return path.replace(str(Path.home()), "~")


def build_record(event: dict, root: Path) -> dict:
    return {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": event.get("session_id"),
        "file": relative(event.get("file_path"), root),
        "memory_type": event.get("memory_type"),
        "load_reason": event.get("load_reason"),
        "globs": event.get("globs"),
        "trigger_file": relative(event.get("trigger_file_path"), root),
        "parent_file": relative(event.get("parent_file_path"), root),
    }


def main() -> int:
    try:
        event = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()
        log_path = root / ".claude" / "logs" / "instructions-loaded.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(build_record(event, root)) + "\n")
    except Exception:  # noqa: BLE001 - observability must never break a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
