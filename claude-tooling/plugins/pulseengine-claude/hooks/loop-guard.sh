#!/usr/bin/env bash
# PostToolUse / PostToolUseFailure(Bash) hook (pulseengine-claude): the loop
# guard. The logic is in loop-guard.py.
#
# PostToolUse fires on every successful Bash call, so the wrapper only starts
# python there when this machine has loop-guard state written in the last 30
# minutes (a recent failure to reset); everything else exits at once. Fails
# OPEN: whatever python does, the hook exits 0 with stderr silenced.
input=$(cat)
case $input in
  *'"PostToolUseFailure"'*) ;;
  *)
    dir="${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}/pulseengine-claude}/loop-guard"
    [ -n "$CLAUDE_PLUGIN_DATA" ] && dir="$CLAUDE_PLUGIN_DATA/loop-guard"
    [ -d "$dir" ] || exit 0
    [ -n "$(find "$dir" -name '*.json' -mmin -30 2>/dev/null | head -n 1)" ] || exit 0
    ;;
esac
printf '%s' "$input" | python3 -B "$(dirname "$0")/loop-guard.py" 2>/dev/null
exit 0
