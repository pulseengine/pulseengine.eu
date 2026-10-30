#!/usr/bin/env bash
# PreToolUse(Bash) hook (pulseengine-claude): the commit, merge, signing and
# publish guards (stray identity, --auto that cannot wait, --admin and API
# merges, red merges, update-branch, unsigned commits, identity writes, tags
# and publishes off green main, host-shaped values in commit and PR text, PR
# admission advice). The logic is in commit-merge-guard.py.
#
# The prefilter keeps every other Bash call cheap: no python, no git, no
# network unless the command names one of the words below.
# The wrapper fails OPEN: whatever python does (missing, crashing, writing to
# stderr), the hook exits 0 with stderr silenced. A deny or an ask is python's
# JSON on stdout (permissionDecision), never an exit code, so a crash can never
# turn into a block.
input=$(cat)
case $input in
  *commit*|*merge*|*cherry-pick*|*revert*|*rebase*|*' am'*) ;;
  *update-branch*|*gpg*|*config*|*tag*|*push*|*release*|*publish*|*'pr '*|*'gh api'*|*graphql*|*user.*) ;;
  *) exit 0 ;;
esac
printf '%s' "$input" | python3 -B "$(dirname "$0")/commit-merge-guard.py" 2>/dev/null
exit 0
