#!/usr/bin/env bash
# SessionStart hook shipped with the pulseengine-claude plugin.
# Injects the bundled philosophy + toolchain reference memory as additional context.
set -euo pipefail

# CLAUDE_PLUGIN_ROOT is set by the harness to the plugin install root.
MEM_DIR="${CLAUDE_PLUGIN_ROOT}/memory"

if [ ! -d "$MEM_DIR" ]; then
  exit 0
fi

{
  echo "## PulseEngine methodology (injected by pulseengine-claude plugin)"
  echo
  echo "Reference memory that travels with the PulseEngine plugin install."
  echo "These describe always-on framing: vocabulary, methodology stances,"
  echo "and the tool directory. The procedural skills that operate on this"
  echo "framing (clean-room-verification, release-execution, oracle-gate-a-change,"
  echo "pulseengine-feature-loop) load on trigger — they are not in this file."
  echo
  for f in "$MEM_DIR"/*.md; do
    [ -e "$f" ] || continue
    name=$(basename "$f")
    echo "### $name"
    echo
    cat "$f"
    echo
  done
} | jq -Rs '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: .
  }
}'
