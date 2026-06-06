#!/usr/bin/env bash
# SessionEnd + PreCompact hook (pulseengine-claude): persist a working-context
# checkpoint to .claude/pulseengine/working-context.md so the next session (or
# the post-compaction window) can resume instead of starting cold.
#
# The file has two parts:
#   - "## State (auto)"          — regenerated mechanically on every save.
#   - "## Session notes"         — agent-maintained narrative; PRESERVED across
#                                  saves (the capture-session-learnings skill
#                                  writes this; the hook never clobbers it).
#
# The checkpoint is session state, not source: the hook keeps it out of git via
# .git/info/exclude (local, never committed). Fails open.

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

dir=".claude/pulseengine"
file="${dir}/working-context.md"
mkdir -p "$dir" 2>/dev/null || exit 0

# Keep the checkpoint local-only — append to the repo's private exclude once.
exclude=".git/info/exclude"
if [ -f "$exclude" ] && ! grep -qxF "$dir/" "$exclude" 2>/dev/null; then
  printf '%s/\n' "$dir" >> "$exclude" 2>/dev/null || true
fi

# Preserve any existing agent-authored notes section.
notes=""
if [ -f "$file" ]; then
  notes="$(awk '/^## Session notes/{f=1} f{print}' "$file")"
fi

repo="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo unknown)")"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
stamp="$(date -u '+%Y-%m-%d %H:%M UTC' 2>/dev/null || echo unknown)"

{
  echo "# Working context — ${repo}"
  echo
  echo "## State (auto — regenerated each save)"
  echo "- Saved: ${stamp}"
  echo "- Branch: \`${branch}\`"
  echo "- Uncommitted files: $(git status --porcelain 2>/dev/null | grep -vc '^$' || echo 0)"
  echo "- Recent commits:"
  git log --oneline -5 2>/dev/null | sed 's/^/    /' || true
  echo
  if [ -n "$notes" ]; then
    printf '%s\n' "$notes"
  else
    echo "## Session notes (agent-maintained — survives auto-saves)"
    echo
    echo "_Not yet captured. Run the capture-session-learnings skill to record what"
    echo "this session is doing, key decisions, and what's next._"
  fi
} > "$file" 2>/dev/null || true

exit 0
