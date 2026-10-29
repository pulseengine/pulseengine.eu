#!/usr/bin/env bash
# PreToolUse(Agent) hook (pulseengine-claude): a non-blocking reminder to choose
# `model:` per delegate-by-cost. The logic is in agent-model-reminder.py; this
# wrapper only guarantees the hook can never fail the call: whatever python
# does (missing, crashing, writing to stderr), the hook is silent on stderr
# and exits 0.
python3 "$(dirname "$0")/agent-model-reminder.py" 2>/dev/null
exit 0
