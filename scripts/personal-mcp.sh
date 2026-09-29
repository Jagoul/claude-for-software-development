#!/usr/bin/env bash
# Add, inspect, or remove a personal, experimental MCP server in user scope (~/.claude.json).
#
# User scope means the server follows you into every project on this machine and never reaches
# the repo. The team's servers stay in .mcp.json. Run from the project folder:
#
#   scripts/personal-mcp.sh add      # register sandbox-time for your user
#   scripts/personal-mcp.sh status   # list every server Claude Code sees here, from all scopes
#   scripts/personal-mcp.sh remove   # undo
set -euo pipefail

NAME="sandbox-time"

case "${1:-status}" in
  add)
    if claude mcp get "$NAME" >/dev/null 2>&1; then
      echo "$NAME is already registered."
    else
      claude mcp add --scope user "$NAME" -- uvx mcp-server-time
    fi
    ;;
  remove)
    claude mcp remove --scope user "$NAME"
    ;;
  status)
    claude mcp list
    ;;
  *)
    echo "usage: $0 [add|status|remove]" >&2
    exit 2
    ;;
esac
