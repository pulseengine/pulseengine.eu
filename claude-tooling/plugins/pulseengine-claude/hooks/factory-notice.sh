#!/usr/bin/env bash
# SessionStart / SessionEnd hook (pulseengine-claude): the factory notice inbox.
#   start  record the session start, then tell the agent which answers are waiting
#          and, inside the owner's decision windows only, which decisions are
#          surfaced (read-only: nothing is consumed here)
#   end    if the agent posted no session-summary and the session changed
#          something, post a minimal automatic one; then flush the outbox to warte
# The hook JSON arrives on stdin and is passed through. Never blocks, never
# fails: notice.py bounds its own network time and exits 0 on every hook path.
command -v python3 >/dev/null 2>&1 || exit 0
script="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/factory-notice/notice.py"
[ -f "$script" ] || exit 0
python3 "$script" "hook-$1" 2>/dev/null || true
exit 0
