#!/usr/bin/env python3
"""PreToolUse(Agent) hook (pulseengine-claude): remind to choose `model:`.

The delegate-by-cost skill was invoked 0 times in 1,531 sessions (2026-10-29
transcript study): only its description steered, and Agent calls without
`model:` kept running on the parent's model. This hook puts the rule in front
of the agent at the one moment it applies.

It NEVER blocks, denies, approves or rewrites the call. On a match it prints
only `hookSpecificOutput.additionalContext` (no permissionDecision, no
updatedInput) and exits 0; on anything else, including bad input or an
exception, it prints nothing and exits 0. Claude Code adds PreToolUse
additionalContext alongside the tool result, so the reminder shapes the NEXT
Agent call, not this one.

Fires only when `model` is missing AND `subagent_type` is absent,
"general-purpose" or "claude" -- the types that inherit the parent's model.
Silent on "fork" (it ignores `model:` anyway), on Explore and other built-ins
with their own model, and on any project or plugin agent, whose own
frontmatter `model:` this hook cannot see.

Python 3.9+, stdlib only, no network, no files read or written.
"""

import json
import sys

INHERITS = {"", "general-purpose", "claude"}

# Kept to one short line: in the heaviest local session it would have fired
# 367 times, so its length is paid per Agent call.
REMINDER = (
    "delegate-by-cost: this Agent call has no `model:`, so by default it runs "
    "at the parent's price. Next call: `haiku` for mechanical work with an "
    "exact check, `sonnet` for judgment short of top-tier."
)


def reminder_for(event):
    """Return the reminder text if this event should get one, else None."""
    if not isinstance(event, dict):
        return None
    if event.get("tool_name") not in ("Agent", "Task"):
        return None
    ti = event.get("tool_input")
    if not isinstance(ti, dict):
        return None
    model = ti.get("model")
    if isinstance(model, str) and model.strip():
        return None
    st = ti.get("subagent_type")
    if st is None:
        st = ""
    if not isinstance(st, str) or st.strip() not in INHERITS:
        return None
    return REMINDER


def main():
    try:
        event = json.loads(sys.stdin.read() or "null")
        text = reminder_for(event)
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
