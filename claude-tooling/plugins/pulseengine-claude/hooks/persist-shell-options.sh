#!/usr/bin/env bash
# SessionStart hook (pulseengine-claude): make the agent's zsh behave like bash
# on the two options that fail the most agent Bash calls.
#
# Claude Code runs the contents of $CLAUDE_ENV_FILE before every Bash command,
# in the same shell process as the command. On macOS that shell is zsh, and two
# zsh defaults turn ordinary commands into errors:
#
#   NOMATCH  an unmatched glob aborts the whole command — `--include=*.py`,
#            `ls target/*/bin`, an unquoted `?` in a URL ("no matches found").
#   EQUALS   a word starting with `=` is looked up as a command — `echo ===`,
#            `[ "$a" == "$b" ]` ("== not found").
#
# Measured over 263k archived agent Bash calls (2026-10-29): about 2,200 calls
# failed on a pattern that was never meant as a glob or as `=cmd` (`--include=`
# 1,353, `==` 714, URL `?` 145, `--format=%G?` 22), many with the status hidden
# by a pipe, so the agent read "no hits" instead of an error. A further 1,198
# were real globs with no match; those still fail, but as the command's own
# "No such file" rather than zsh aborting the whole command line.
# `setopt no_nomatch no_equals` gives the bash behaviour: an unmatched glob is
# passed through literally and `=word` is an ordinary word.
#
# The line is guarded by $ZSH_VERSION, so a bash shell running the same file
# does nothing. It is an `if`, not `[ ... ] && setopt`: under bash the `&&` form
# leaves exit status 1 behind, which would fail anything chained after the file
# with `&&` or run under `set -e`.
#
# It is appended at most once: SessionStart fires again on resume, clear and
# compact, and other hooks may write the same file, so the file is never
# truncated and an existing copy of the line is not repeated.
#
# Fails open: no $CLAUDE_ENV_FILE, an unwritable file, or any error → exit 0.

line='if [ -n "$ZSH_VERSION" ]; then setopt no_nomatch no_equals; fi'

f="${CLAUDE_ENV_FILE:-}"
[ -n "$f" ] || exit 0

if [ -f "$f" ] && grep -qxF -- "$line" "$f" 2>/dev/null; then
  exit 0
fi

{
  # Another hook may have left its last line without a newline; appending
  # straight after it would glue this line onto that one.
  if [ -s "$f" ] && [ -n "$(tail -c 1 "$f" 2>/dev/null)" ]; then
    printf '\n'
  fi
  printf '%s\n' "$line"
} >>"$f" 2>/dev/null

exit 0
