---
description: Check the working tree against the team's standards before opening a pull request
allowed-tools: Bash(git status *), Bash(git diff *), Bash(uv run pytest *), Bash(uv run ruff *)
---

## Current changes

- Status: !`git status --short`
- Diff summary: !`git diff --stat HEAD`

## Your task

Review these changes as the team's pre-PR check. Run `uv run pytest -q` and
`uv run ruff check .`, then report one line per item, marked PASS or FAIL:

1. Tests pass.
2. Lint is clean.
3. Every behaviour change has a test, and every fixed bug removed its `xfail` marker.
4. No new Pydantic v1 idioms (`.dict()`, `@validator`, `class Config`, ...).
5. Routes stay thin and use the error envelope (see `.claude/rules/api-conventions.md`).
6. No secrets, `.env` contents, or debug `print` calls in the diff.

End with a suggested PR title in the form `TB-###: summary`, if an issue ID appears in the
changes or the branch name. Do not fix anything unless I ask.
