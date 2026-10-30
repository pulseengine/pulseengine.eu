#!/usr/bin/env bash
# Sourced by the pulseengine-claude SessionStart hooks. emit_context NAME
# wraps stdin as SessionStart additionalContext, and keeps it whole.
#
# Claude Code turns any additionalContext string over ~10k characters into a
# ~2.3 KB preview plus a file path, and the model reads the preview only
# (2026-10-30 tuition study: the 48 KB methodology block arrived as its first
# 2.3 KB on every session from June to October). So nothing over
# PULSEENGINE_CONTEXT_MAX (9,500) characters is ever handed over. A longer text
# is written in full to a spill file, and what is injected is its head plus one
# line naming that file, so the cut is ours, visible, and points at the rest.
# Measured in bytes, which is never fewer than characters.
#
# No-op without jq, like the hooks were before. Never fails the hook.

PULSEENGINE_CONTEXT_MAX=9500

emit_context() {
  command -v jq >/dev/null 2>&1 || { cat >/dev/null; return 0; }
  local name="$1" text dir spill
  text=$(LC_ALL=C cat)
  if [ "$(printf '%s' "$text" | LC_ALL=C wc -c)" -gt "$PULSEENGINE_CONTEXT_MAX" ]; then
    dir="${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}/pulseengine-claude}/context"
    spill="$dir/$name.md"
    mkdir -p "$dir" 2>/dev/null && printf '%s\n' "$text" > "$spill" 2>/dev/null || spill="(could not be written)"
    text="$(printf '%s' "$text" | LC_ALL=C head -c 8800 | sed '$d')

[pulseengine-claude: this block was cut at ${PULSEENGINE_CONTEXT_MAX} characters so it arrives whole; the full text is in $spill]"
  fi
  printf '%s' "$text" | jq -Rs '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: .}}'
}
