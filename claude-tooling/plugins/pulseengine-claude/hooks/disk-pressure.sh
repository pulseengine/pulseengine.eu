#!/usr/bin/env bash
# PreToolUse(Bash) hook (pulseengine-claude): disk-pressure advice before a
# command that eats disk. The logic is in disk-pressure.py.
#
# The prefilter keeps every other Bash call cheap: no python unless the command
# names one of the words below. The wrapper fails OPEN: whatever python does,
# the hook exits 0 with stderr silenced, and its only output is
# additionalContext, so a crash can never turn into a block.
input=$(cat)
case $input in
  *cargo*|*bazel*|*clone*|*worktree*|*docker*|*podman*|*nix*|*npm*|*yarn*) ;;
  *pip*|*'uv '*|*huggingface*|*'hf '*|*ollama*|*rustup*) ;;
  *'rm '*) ;;
  *) exit 0 ;;
esac
printf '%s' "$input" | python3 -B "$(dirname "$0")/disk-pressure.py" 2>/dev/null
exit 0
