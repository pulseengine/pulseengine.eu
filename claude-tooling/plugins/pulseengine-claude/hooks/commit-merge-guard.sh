#!/usr/bin/env bash
# PreToolUse(Bash) hook (pulseengine-claude): deny a commit under a stray
# repo-local git identity, and `gh pr merge --auto` on a repo where --auto
# would merge before CI. The logic is in commit-merge-guard.py.
#
# The prefilter keeps every other Bash call cheap: no python, no git, no
# network unless the command names a commit-making git subcommand or merge.
# The wrapper fails OPEN: whatever python does (missing, crashing, writing to
# stderr), the hook exits 0 with stderr silenced. A deny is python's JSON on
# stdout (permissionDecision "deny"), never an exit code, so a crash can never
# turn into a block.
input=$(cat)
case $input in
  *commit*|*merge*|*cherry-pick*|*revert*|*rebase*|*' am'*) ;;
  *) exit 0 ;;
esac
printf '%s' "$input" | python3 "$(dirname "$0")/commit-merge-guard.py" 2>/dev/null
exit 0
