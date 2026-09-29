"""Run one tracker issue through Claude Code, in plan mode or direct execution, and measure it.

    uv run python scripts/plan_vs_direct.py TB-101 direct
    uv run python scripts/plan_vs_direct.py TB-102 plan --model sonnet

Each trial works on a disposable copy of this repo (in a temp folder, with its own git baseline),
so the seeded issues stay unfixed here. Direct mode sends the request with edits auto-accepted.
Plan mode sends the same request in plan mode, saves the plan, then resumes the same session
with "approved, implement it". The trial ends by running the tests and printing a JSON summary.

The copy is an untrusted folder, so the project's permission rules don't apply there. The
runner grants the same tools on the command line instead, and loads the MCP server with
--mcp-config. Needs TRACKER_TOKEN in the environment. Uses your Claude account.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLANS_DIR = Path.home() / ".claude" / "plans"
COPY_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "logs", "CLAUDE.local.md"
)
ALLOWED_TOOLS = [
    "mcp__team-tracker__get_issue",
    "mcp__team-tracker__list_issues",
    "Bash(uv run *)",
    "Bash(git status *)",
    "Bash(git diff *)",
    "Bash(grep *)",
    "Bash(ls *)",
]
PROMPT = "Resolve tracker issue {issue}. Read it first with the team-tracker get_issue tool."
NO_BRAKES = (
    " Implement it end to end now. Do not stop to ask questions or to recommend plan mode:"
    " make reasonable decisions yourself and state them at the end."
)
APPROVAL = "The plan is approved. Implement it now, then run the tests."


def sh(args: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kwargs)


def make_copy(issue: str, mode: str) -> Path:
    dest = Path(tempfile.mkdtemp(prefix=f"taskboard-{issue}-{mode}-"))
    shutil.copytree(PROJECT_ROOT, dest, dirs_exist_ok=True, ignore=COPY_IGNORE)
    for command in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-qm", "base"]):
        sh(command, dest, check=True)
    sh(["uv", "sync", "-q"], dest, check=True)
    return dest


def claude(workdir: Path, prompt: str, model: str, permission_mode: str, resume: str | None):
    args = ["claude", "-p", prompt, "--model", model, "--permission-mode", permission_mode]
    args += ["--mcp-config", ".mcp.json", "--output-format", "json", "--max-turns", "60"]
    args += ["--allowedTools", *ALLOWED_TOOLS]
    if resume:
        args += ["--resume", resume]
    started = time.monotonic()
    result = sh(args, workdir, timeout=1800)
    elapsed = time.monotonic() - started
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        sys.exit(f"claude returned no JSON:\n{result.stdout}\n{result.stderr}")
    data["wall_seconds"] = round(elapsed)
    return data


def evaluate(workdir: Path, issue: str) -> dict:
    tests = sh(["uv", "run", "pytest", "-q", "-p", "no:warnings"], workdir)
    strict = sh(["uv", "run", "pytest", "-q", "-W", "error::DeprecationWarning"], workdir)
    changed = sh(["git", "status", "--porcelain"], workdir).stdout.splitlines()
    xfail_left = sh(["grep", "-rn", f"{issue}:", "tests"], workdir).stdout.strip()
    return {
        "tests": tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else tests.stderr,
        "passes_with_deprecations_as_errors": strict.returncode == 0,
        "files_changed": sorted(line[3:] for line in changed),
        "xfail_marker_left": bool(xfail_left),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("issue", help="tracker issue, e.g. TB-101")
    parser.add_argument("mode", choices=["direct", "direct-forced", "plan"])
    parser.add_argument("--model", default="sonnet")
    args = parser.parse_args()
    if not os.environ.get("TRACKER_TOKEN"):
        sys.exit("Export TRACKER_TOKEN first (see .env.example).")

    workdir = make_copy(args.issue, args.mode)
    prompt = PROMPT.format(issue=args.issue)
    runs = []
    plan_file = None
    if args.mode == "direct":
        runs.append(claude(workdir, prompt, args.model, "acceptEdits", None))
    elif args.mode == "direct-forced":
        runs.append(claude(workdir, prompt + NO_BRAKES, args.model, "acceptEdits", None))
    else:
        started = time.time()
        plan = claude(workdir, prompt, args.model, "plan", None)
        # Headless plan mode can't show the approval dialog; the plan lands in ~/.claude/plans/.
        written = [p for p in PLANS_DIR.glob("*.md") if p.stat().st_mtime >= started]
        plan_text = max(written, key=lambda p: p.stat().st_mtime).read_text() if written else ""
        plan_file = workdir.with_name(workdir.name + ".plan.md")  # outside the repo copy
        plan_file.write_text(plan_text or plan.get("result") or "")
        runs.append(plan)
        runs.append(claude(workdir, APPROVAL, args.model, "acceptEdits", plan["session_id"]))

    summary = {
        "issue": args.issue,
        "mode": args.mode,
        "model": args.model,
        "workdir": str(workdir),
        "turns": sum(run.get("num_turns", 0) for run in runs),
        "cost_usd": round(sum(run.get("total_cost_usd", 0) for run in runs), 4),
        "wall_seconds": sum(run["wall_seconds"] for run in runs),
        "plan_turns": runs[0].get("num_turns") if args.mode == "plan" else None,
        "plan_file": str(plan_file) if plan_file else None,
        "permission_denials": [
            denial.get("tool_name") for run in runs for denial in run.get("permission_denials", [])
        ],
        "final_reply": (runs[-1].get("result") or "")[-1500:],
        **evaluate(workdir, args.issue),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
