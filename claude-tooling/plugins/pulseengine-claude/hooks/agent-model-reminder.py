#!/usr/bin/env python3
"""PreToolUse(Agent) hook (pulseengine-claude): remind to choose `model:`.

The delegate-by-cost skill was invoked 0 times in 1,531 sessions (2026-10-29
transcript study): only its description steered, and Agent calls without
`model:` kept running on the parent's model. This hook puts the rule in front
of the agent at the one moment it applies.

It NEVER blocks, denies, approves or rewrites the call. On a reminder it prints
only `hookSpecificOutput.additionalContext` (no permissionDecision, no
updatedInput) and exits 0; otherwise, including bad input or an exception, it
prints nothing and exits 0. Claude Code adds PreToolUse additionalContext
alongside the tool result, so the reminder shapes the NEXT Agent call.

A call is "missing" when `model` is absent or empty AND `subagent_type` is
absent, "general-purpose" or "claude" -- the types that inherit the parent's
model. Any Agent call that sets `model` is "set". Everything else ("fork",
Explore and other built-ins with their own model, plugin and project agents,
whose frontmatter `model:` this hook cannot see) is neutral: no reminder, and
it neither counts nor resets.

Throttle (owner decision 2026-10-29): per session, remind on the first missing
call, then on every 10th consecutive missing call after the last reminder
(calls 1, 11, 21, ...). A set call resets the count, so the next reminder
comes on the 10th consecutive missing call after it. Unthrottled, the
heaviest local session would have been reminded 367 times.

State: one small JSON file per session, keyed by the hook input's
session_id, in $CLAUDE_PLUGIN_DATA/agent-model-reminder/ (the plugin's
documented persistent data dir), else ${TMPDIR:-/tmp}/pulseengine-claude/
agent-model-reminder/. Written atomically (temp file + os.replace); files
older than 7 days are pruned when a new session's file is created. Missing or
corrupt state fails open: the call is treated as a session's first, so the
worst case is a reminder too many, never a blocked call.

Python 3.9+, stdlib only, no network.
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import time

INHERITS = {"", "general-purpose", "claude"}
EVERY = 10
PRUNE_AFTER_S = 7 * 24 * 3600

# One short line: its length is paid on every reminder.
REMINDER = (
    "delegate-by-cost: this Agent call has no `model:`, so by default it runs "
    "at the parent's price. Next call: `haiku` for mechanical work with an "
    "exact check, `sonnet` for judgment short of top-tier."
)


def classify(event):
    """'missing', 'set', or None (not an Agent call, or neutral)."""
    if not isinstance(event, dict) or event.get("tool_name") not in ("Agent", "Task"):
        return None
    ti = event.get("tool_input")
    if not isinstance(ti, dict):
        return None
    model = ti.get("model")
    if isinstance(model, str) and model.strip():
        return "set"
    st = ti.get("subagent_type")
    if st is None:
        st = ""
    if not isinstance(st, str) or st.strip() not in INHERITS:
        return None
    return "missing"


def reminder_for(event):
    """Unthrottled: the reminder text if this call is missing `model:`."""
    return REMINDER if classify(event) == "missing" else None


def state_dir(env=None):
    env = os.environ if env is None else env
    base = env.get("CLAUDE_PLUGIN_DATA", "").strip()
    if base:
        return os.path.join(base, "agent-model-reminder")
    tmp = env.get("TMPDIR", "").strip() or tempfile.gettempdir()
    return os.path.join(tmp, "pulseengine-claude", "agent-model-reminder")


def state_file(directory, session_id):
    if not isinstance(session_id, str) or not session_id:
        return None
    name = session_id if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id) \
        else hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()
    return os.path.join(directory, name + ".json")


def load(path):
    """The count since the last reminder, or None (no state, or corrupt)."""
    try:
        with open(path, encoding="utf-8") as f:
            n = json.load(f).get("n")
    except (OSError, ValueError, AttributeError):
        return None
    return n if isinstance(n, int) and not isinstance(n, bool) and 0 <= n < EVERY else None


def save(path, n, new):
    try:
        d = os.path.dirname(path)
        os.makedirs(d, exist_ok=True)
        if new:
            prune(d)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"n": n}, f)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError:
        pass  # fail open: no state means the next call is treated as first


def prune(d):
    cutoff = time.time() - PRUNE_AFTER_S
    try:
        names = os.listdir(d)
    except OSError:
        return
    for name in names:
        if name.endswith(".json"):
            p = os.path.join(d, name)
            try:
                if os.path.getmtime(p) < cutoff:
                    os.unlink(p)
            except OSError:
                pass


def decide(event, directory):
    """Apply the throttle and return the reminder text or None."""
    kind = classify(event)
    if kind is None:
        return None
    path = state_file(directory, event.get("session_id"))
    if path is None:  # no session to key on: unthrottled, fail open
        return REMINDER if kind == "missing" else None
    n = load(path)
    if kind == "set":
        if n is not None and n != 0:
            save(path, 0, new=False)
        return None
    if n is None:  # first missing call of the session (or lost state)
        save(path, 0, new=not os.path.exists(path))
        return REMINDER
    n += 1
    if n >= EVERY:
        save(path, 0, new=False)
        return REMINDER
    save(path, n, new=False)
    return None


def main():
    try:
        event = json.loads(sys.stdin.read() or "null")
        text = decide(event, state_dir())
        if text:
            sys.stdout.write(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": text,
            }}))
    except Exception:  # never let a reminder become a hook error
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
