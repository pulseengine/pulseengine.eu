#!/usr/bin/env bash
# SessionStart hook (pulseengine-claude): one short line when this machine
# cannot make the signed, verified commits main requires: no global
# user.email, no signing key, or commit.gpgsign not true. Silent when all
# three hold. Reads git config only (no network, no key access), and exits 0
# on every path, so it can never hold up a session.
command -v git >/dev/null 2>&1 || exit 0
missing=""
[ -n "$(git config --global --includes --get user.email 2>/dev/null)" ] || missing="$missing global user.email,"
[ -n "$(git config --global --includes --get user.signingkey 2>/dev/null)" ] || missing="$missing user.signingkey,"
[ "$(git config --global --includes --type=bool --get commit.gpgsign 2>/dev/null)" = "true" ] || missing="$missing commit.gpgsign=true,"
[ -n "$missing" ] || exit 0
msg="pulseengine-claude signing probe: this machine's git config lacks${missing%,}, so commits will not be signed and verified and main will refuse them at merge. Ask the owner to fix the global git config; do not set an identity or signing config yourself."
if command -v jq >/dev/null 2>&1; then
  printf '%s' "$msg" | jq -Rs '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: .}}'
fi
exit 0
