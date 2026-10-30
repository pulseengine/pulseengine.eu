#!/usr/bin/env bash
# PreToolUse(Edit|Write|MultiEdit) hook (pulseengine-claude): ask before a
# host-shaped value (a .local/.lan name, an RFC 1918 or ULA address, a
# /Volumes path, the owner's home path) lands in a file of a git repo. The
# logic is in private-host-guard.py; the patterns in private_hosts.py.
#
# The wrapper fails OPEN: whatever python does (missing, crashing, writing to
# stderr), the hook exits 0 with stderr silenced. An ask is python's JSON on
# stdout (permissionDecision "ask"), never an exit code.
python3 -B "$(dirname "$0")/private-host-guard.py" 2>/dev/null
exit 0
