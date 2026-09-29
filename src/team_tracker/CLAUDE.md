# team-tracker MCP server

Loaded only when Claude works in `src/team_tracker/` (a subdirectory CLAUDE.md).

- Tool docstrings are the tool descriptions Claude sees. Keep the "use it when / returns" shape,
  and when two tools overlap, name the other one.
- Raise `TrackerError` for anything the caller can act on. It becomes an `isError` tool result.
  Prefix the message with a code: `UNAUTHORIZED:`, `NOT_FOUND:`, `VALIDATION:`.
- Never return or log `TRACKER_TOKEN`. `whoami` reports a masked fingerprint only.
- Mark read-only tools with `READ_ONLY` annotations. Anything that writes gets
  `idempotentHint=False` and must be listed under `ask` in `.claude/settings.json`.
- Changing a tool name breaks the `mcp__team-tracker__<tool>` permission entries and the
  `/fix-issue` command. Update both.
