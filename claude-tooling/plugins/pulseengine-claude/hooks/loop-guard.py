#!/usr/bin/env python3
"""PostToolUse / PostToolUseFailure(Bash) hook (pulseengine-claude): the loop guard.

An agent that re-runs the same failing command, hoping it passes this time, burns
tokens and wall-clock without learning anything. Microsoft's TokenEconomizer
measured this waste and steps in with a model-judged guard; the owner chose
(2026-11-08) to borrow the idea without a model call or third-party code.

When the same Bash command fails with the same error three times in a row, with
no success of that command in between, the agent gets one line of context:
stop repeating it, read the error, change the approach, or ask. Edits between
the runs do not reset the count, because "edit, re-run, same failure" is the
loop worth catching. A success of that command (PostToolUse) resets it. The line
is repeated at most at the 3rd and 6th identical failure.

It NEVER blocks: on PostToolUseFailure it prints only
`hookSpecificOutput.additionalContext`, otherwise nothing, and always exits 0.

A command's identity is its text with whitespace collapsed. A failure's identity
is the first two lines of the `error` text (which for Bash starts with
"Exit code N") with digits and hex runs masked, so a changing line number or
timestamp does not hide a repeat. An entry older than WINDOW_S counts as new.

State: one small JSON file per session in $CLAUDE_PLUGIN_DATA/loop-guard/, else
${TMPDIR:-/tmp}/pulseengine-claude/loop-guard/; written atomically, pruned after
7 days. Missing or corrupt state fails open (counting starts again).

Python 3.9+, stdlib only, no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time

THRESHOLDS = (3, 6)
WINDOW_S = 1800
PRUNE_AFTER_S = 7 * 24 * 3600


def state_dir():
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    if base:
        return os.path.join(base, "loop-guard")
    return os.path.join(tempfile.gettempdir(), "pulseengine-claude", "loop-guard")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, path)
    except OSError:
        pass


def prune(d, now):
    try:
        for n in os.listdir(d):
            p = os.path.join(d, n)
            if n.endswith(".json") and now - os.path.getmtime(p) > PRUNE_AFTER_S:
                os.remove(p)
    except OSError:
        pass


def key(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def command_id(cmd):
    return key(" ".join(cmd.split()))


def error_id(err):
    lines = [ln.strip() for ln in err.splitlines() if ln.strip()][:2]
    masked = re.sub(r"0x[0-9a-fA-F]+|[0-9a-f]{8,}|\d+", "#", "\n".join(lines))
    return key(masked)


def first_line(err, limit=140):
    lines = [ln.strip() for ln in err.splitlines() if ln.strip()]
    text = " / ".join(lines[:2])
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if not isinstance(event, dict) or event.get("tool_name") != "Bash":
        return
    name = event.get("hook_event_name")
    cmd = (event.get("tool_input") or {}).get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return
    now = time.time()
    d = state_dir()
    sid = str(event.get("session_id") or "nosession")
    path = os.path.join(d, "s-" + key(sid) + ".json")
    state = load(path)
    cid = command_id(cmd)

    if name == "PostToolUse":
        if cid in state:
            del state[cid]
            save(path, state)
        return
    if name != "PostToolUseFailure" or event.get("is_interrupt") is True:
        return
    err = event.get("error")
    if not isinstance(err, str):
        return
    eid = error_id(err)
    entry = state.get(cid) if isinstance(state.get(cid), dict) else {}
    if entry.get("err") == eid and now - float(entry.get("at", 0)) <= WINDOW_S:
        count = int(entry.get("n", 0)) + 1
    else:
        count = 1
    state[cid] = {"err": eid, "n": count, "at": now}
    if not os.path.exists(path):
        prune(d, now)
    save(path, state)
    if count in THRESHOLDS:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUseFailure",
            "additionalContext": (
                "loop-guard: this command has now failed the same way %d times in a row "
                "(%s). Re-running it unchanged will not help unless the failure is a flaky "
                "network step. Read the error, change the approach (a different command, a "
                "narrower test, the tool's --help), or ask the owner." % (count, first_line(err)))}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # fail open: a reminder must never break a call
        pass
