---
description: Fetch a tracker issue and fix it test-first, or stop and recommend plan mode if it is too big
argument-hint: <issue-id, e.g. TB-101>
allowed-tools: mcp__team-tracker__get_issue, Bash(uv run pytest *)
---

Fix tracker issue **$ARGUMENTS**.

1. Read the issue with the `team-tracker` MCP tool `get_issue`. If the tracker is unavailable,
   stop and tell me how to fix the connection (for example, `TRACKER_TOKEN` not exported).
2. Size it before touching code. If the fix will touch more than three files, migrates a library,
   or the issue has `open_questions`, **stop**. Say why, and recommend re-running this in plan
   mode (Shift+Tab). Do not edit anything in that case.
3. Reproduce it. Find the test that pins the bug (look for `xfail` with this issue ID) or write
   one that fails for the right reason. Run it and show the failure.
4. Make the smallest change that fixes the root cause. Remove the issue's `xfail` marker.
5. Run `uv run pytest` and report the result verbatim.
6. Finish with: root cause (one sentence), files changed, tests run, and a commit message in the
   form `$ARGUMENTS: imperative summary`. Do not commit.
