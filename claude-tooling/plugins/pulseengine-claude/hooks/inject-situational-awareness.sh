#!/usr/bin/env bash
# SessionStart hook (pulseengine-claude): inject cheap, mechanical situational
# awareness so a session starts oriented instead of spending its first turns
# re-deriving git state — branch, working-tree status, recent commits, a
# best-effort repo-category guess (see pulseengine-repo-taxonomy memory), and
# the working-context snapshot saved by the previous session, if any.
#
# Deliberately git-only (no network / no gh) so it stays fast and never blocks
# session start. Fails open: any error yields no injected context.

emit() {
  # Wrap stdin as SessionStart additionalContext; no-op if jq is unavailable.
  if command -v jq >/dev/null 2>&1; then
    jq -Rs '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: .}}'
  fi
}

# Not a git repo → nothing useful to say.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

repo="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo unknown)")"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"

# Best-effort category hint. The taxonomy memory is the source of truth; this
# is only a nudge. Keep the tool list roughly in sync with the toolchain memory.
# Category heuristic only — the authoritative roster is the pulseengine-toolchain memory.
tools=" rivet spar witness sigil meld loom synth kiln gale scry smithy thrum mcp temper rules_lean rules_rocq_rust rules_verus rules_wasm_component rules_moonbit "
consumers=" wohl relay example-kvs "
if printf '%s' "$tools" | grep -q " $repo "; then
  category="toolchain development (tool builds itself — inward lens; oracle-gate the tool, dogfood the chain)"
elif printf '%s' "$consumers" | grep -q " $repo "; then
  category="toolchain consumer / application (outward lens — compose the full feature loop)"
else
  category="unclassified — infer role from the repo (see pulseengine-repo-taxonomy)"
fi

dirty="$(git status --porcelain 2>/dev/null | grep -vc '^$' || echo 0)"
upstream="$(git rev-list --left-right --count '@{upstream}...HEAD' 2>/dev/null || true)"

{
  echo "## PulseEngine situational awareness (injected at session start)"
  echo
  echo "- **Repo:** \`${repo}\` — ${category}"
  echo "- **Branch:** \`${branch}\`$( [ -n "$upstream" ] && echo " (behind/ahead vs upstream: ${upstream})" )"
  echo "- **Uncommitted files:** ${dirty}"
  echo
  echo "Recent commits:"
  git log --oneline -5 2>/dev/null | sed 's/^/    /' || true
  echo

  wc_file=".claude/pulseengine/working-context.md"
  if [ -f "$wc_file" ]; then
    echo "### Resumed working context (from the previous session)"
    echo
    cat "$wc_file"
    echo
    echo "_(Update this as work progresses; the capture-session-learnings skill maintains it.)_"
  fi
} | emit
