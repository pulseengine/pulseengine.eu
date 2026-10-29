#!/usr/bin/env python3
# rivet: verifies REQ-AGENT-MODEL-REMINDER
"""Check the PreToolUse(Agent) hook that reminds the agent to choose `model:`.

Runs the real wrapper, hooks/agent-model-reminder.sh, under bash with each
case's JSON on stdin, the way Claude Code runs it, and checks:

  never blocks  every case exits 0 with empty stderr, and no output ever
                carries permissionDecision, updatedInput, decision, continue
                or any key other than hookSpecificOutput.{hookEventName,
                additionalContext} -- the hook may add context and nothing else;
  fires         no `model` and subagent_type absent, "general-purpose" or
                "claude" (also under the old tool name Task, and with
                model "" or null) print exactly that context, naming haiku;
  silent        `model` set, subagent_type "fork", "Explore", "Plan", a plugin
                or project agent, a non-Agent tool, malformed or empty stdin,
                and a non-object tool_input print nothing;
  no python3    with python3 off PATH, or a python3 that crashes with a
                traceback, the wrapper exits 0 with empty stdout and stderr;
  python alone  the .py exits 0 silently on malformed input without the
                wrapper's masking, so each layer holds on its own;
  fast          the slowest single run stays under 2 s;
  wired         hooks.json registers the wrapper exactly once, under
                PreToolUse, with a matcher that names Agent.

Exit: 0 all hold · 1 a check failed · 2 cannot check (no bash, no hook).
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude" / "hooks"
WRAPPER = HOOKS / "agent-model-reminder.sh"
HOOKS_JSON = HOOKS / "hooks.json"
CMD = "bash ${CLAUDE_PLUGIN_ROOT}/hooks/agent-model-reminder.sh"


def ev(tool_input, tool_name="Agent"):
    return json.dumps({"session_id": "t", "hook_event_name": "PreToolUse",
                       "tool_name": tool_name, "tool_input": tool_input,
                       "tool_use_id": "toolu_test"})


P = {"prompt": "count the files", "description": "count files"}
FIRE = {
    "no subagent_type, no model": ev(dict(P)),
    "general-purpose, no model": ev(dict(P, subagent_type="general-purpose")),
    "claude, no model": ev(dict(P, subagent_type="claude")),
    "general-purpose, model empty": ev(dict(P, subagent_type="general-purpose", model="")),
    "no subagent_type, model null": ev(dict(P, model=None)),
    "old tool name Task, no model": ev(dict(P, subagent_type="general-purpose"), "Task"),
}
SILENT = {
    "model haiku": ev(dict(P, model="haiku")),
    "general-purpose, model sonnet": ev(dict(P, subagent_type="general-purpose", model="sonnet")),
    "fork": ev(dict(P, subagent_type="fork")),
    "Explore": ev(dict(P, subagent_type="Explore")),
    "Plan": ev(dict(P, subagent_type="Plan")),
    "claude-code-guide": ev(dict(P, subagent_type="claude-code-guide")),
    "plugin agent": ev(dict(P, subagent_type="someplugin:reviewer")),
    "project agent": ev(dict(P, subagent_type="my-reviewer")),
    "Bash tool": ev({"command": "ls"}, "Bash"),
    "tool_input not an object": ev("oops"),
    "malformed JSON": "{not json",
    "empty stdin": "",
    "JSON array": "[1, 2]",
}

failures: list[str] = []


def check(ok: bool, what: str) -> None:
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        failures.append(what)


def run(stdin: str, path: str | None = None) -> tuple[subprocess.CompletedProcess, float]:
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    t0 = time.monotonic()
    r = subprocess.run(["bash", str(WRAPPER)], input=stdin, env=env,
                       capture_output=True, text=True, timeout=10)
    return r, time.monotonic() - t0


def only_context(out: str) -> str | None:
    """The additionalContext if `out` is exactly the allowed shape, else None."""
    try:
        d = json.loads(out)
    except ValueError:
        return None
    if not isinstance(d, dict) or set(d) != {"hookSpecificOutput"}:
        return None
    h = d["hookSpecificOutput"]
    if not isinstance(h, dict) or set(h) != {"hookEventName", "additionalContext"}:
        return None
    if h["hookEventName"] != "PreToolUse" or not isinstance(h["additionalContext"], str):
        return None
    return h["additionalContext"]


def main() -> int:
    bash = shutil.which("bash")
    if not bash or not WRAPPER.is_file() or not HOOKS_JSON.is_file():
        print(f"error: need bash and {WRAPPER.relative_to(ROOT)}", file=sys.stderr)
        return 2
    slowest = 0.0

    for name, stdin in FIRE.items():
        r, dt = run(stdin)
        slowest = max(slowest, dt)
        ctx = only_context(r.stdout)
        check(r.returncode == 0 and r.stderr == "" and ctx is not None
              and "`model:`" in ctx and "haiku" in ctx and "delegate-by-cost" in ctx,
              f"fires: {name} -> exit 0, context only (rc={r.returncode}, out={r.stdout[:80]!r})")

    for name, stdin in SILENT.items():
        r, dt = run(stdin)
        slowest = max(slowest, dt)
        check(r.returncode == 0 and r.stderr == "" and r.stdout == "",
              f"silent: {name} -> exit 0, no output (rc={r.returncode}, out={r.stdout[:80]!r})")

    # no python3: a PATH holding only bash and dirname
    with tempfile.TemporaryDirectory() as tmp:
        for tool in ("bash", "dirname"):
            src = shutil.which(tool)
            if src:
                os.symlink(src, os.path.join(tmp, tool))
        r, _ = run(FIRE["general-purpose, no model"], path=tmp)
        check(r.returncode == 0 and r.stdout == "" and r.stderr == "",
              f"no python3: wrapper exits 0 silently (rc={r.returncode}, err={r.stderr[:80]!r})")

    # a python3 that crashes loudly: the wrapper still exits 0, stderr silent
    with tempfile.TemporaryDirectory() as tmp:
        stub = os.path.join(tmp, "python3")
        pathlib.Path(stub).write_text("#!/bin/sh\necho Traceback >&2\nexit 3\n")
        os.chmod(stub, 0o755)
        r, _ = run(FIRE["general-purpose, no model"], path=tmp + os.pathsep + os.environ.get("PATH", ""))
        check(r.returncode == 0 and r.stdout == "" and r.stderr == "",
              f"crashing python3: wrapper exits 0 silently (rc={r.returncode}, err={r.stderr[:80]!r})")

    # the python layer on its own, without the wrapper's masking
    for name in ("malformed JSON", "JSON array", "tool_input not an object", "empty stdin"):
        r = subprocess.run([sys.executable, str(HOOKS / "agent-model-reminder.py")],
                           input=SILENT[name], capture_output=True, text=True, timeout=10)
        check(r.returncode == 0 and r.stdout == "" and r.stderr == "",
              f"python alone: {name} -> exit 0, no output (rc={r.returncode}, err={r.stderr[-80:]!r})")

    check(slowest < 2.0, f"fast: slowest run {slowest:.3f}s < 2s")

    cfg = json.loads(HOOKS_JSON.read_text())
    where = [(event, group.get("matcher", ""))
             for event, groups in cfg.get("hooks", {}).items()
             for group in groups for h in group.get("hooks", [])
             if h.get("command") == CMD]
    check(len(where) == 1 and where[0][0] == "PreToolUse"
          and "Agent" in where[0][1].split("|"),
          f"wired: once, under PreToolUse, matcher names Agent (found {where})")

    if failures:
        print(f"\n{len(failures)} check(s) failed", file=sys.stderr)
        return 1
    print("\nall checks hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
