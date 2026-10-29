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
  throttle      per session_id: reminds on missing call 1, 11, 21; a call
                with `model:` resets the count; Explore neither counts nor
                resets; sessions are independent; corrupt state, an
                unwritable state dir and a missing session_id fail open
                (remind, exit 0); a hostile session_id stays inside the
                state dir; TMPDIR is the fallback; 7-day-old state is
                pruned; no temp files are left behind. Every run writes its
                state into a temp dir, never the real plugin data dir;
  wired         hooks.json registers the wrapper exactly once, under
                PreToolUse, with a matcher that names Agent.

Exit: 0 all hold · 1 a check failed · 2 cannot check (no bash, no hook).
"""

from __future__ import annotations

import itertools
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


_sid = itertools.count()


def ev(tool_input, tool_name="Agent", sid=None):
    # A fresh session per fixture by default, so the throttle never hides a
    # single-call case; the throttle checks pass their own sid.
    sid = f"fixture-{next(_sid)}" if sid is None else sid
    return json.dumps({"session_id": sid, "hook_event_name": "PreToolUse",
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


STATE = {"dir": ""}  # set in main(): every run writes state into a temp dir


def run(stdin: str, path: str | None = None, env_over: dict | None = None
        ) -> tuple[subprocess.CompletedProcess, float]:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PLUGIN_DATA", "TMPDIR")}
    env["CLAUDE_PLUGIN_DATA"] = STATE["dir"]
    if path is not None:
        env["PATH"] = path
    for k, v in (env_over or {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
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


MISS = dict(P, subagent_type="general-purpose")
SET = dict(P, subagent_type="general-purpose", model="haiku")
NEUTRAL = dict(P, subagent_type="Explore")


def fired_seq(sid: str, inputs: list, env_over: dict | None = None) -> list[int]:
    """Run one call per input in session `sid`; return the 1-based calls that reminded."""
    out = []
    for i, ti in enumerate(inputs, 1):
        r, _ = run(ev(ti, sid=sid), env_over=env_over)
        if r.returncode != 0 or r.stderr:
            out.append(-i)  # a non-zero exit or stderr is never acceptable
        elif r.stdout:
            out.append(i if only_context(r.stdout) else -i)
    return out


def throttle_checks() -> None:
    d = pathlib.Path(STATE["dir"]) / "agent-model-reminder"
    got = fired_seq("thr-plain", [MISS] * 25)
    check(got == [1, 11, 21], f"throttle: 25 missing calls remind on 1, 11, 21 (got {got})")
    got = fired_seq("thr-reset", [MISS] * 5 + [SET] + [MISS] * 10)
    check(got == [1, 16], f"throttle: a call with `model:` resets the count (got {got})")
    got = fired_seq("thr-neutral", [MISS] + [NEUTRAL] * 5 + [MISS] * 10)
    check(got == [1, 16], f"throttle: Explore neither counts nor resets (got {got})")
    got = fired_seq("thr-set-first", [SET, SET, MISS, MISS])
    check(got == [3], f"throttle: the first missing call reminds even after set calls (got {got})")
    a, b = fired_seq("thr-a", [MISS] * 3), fired_seq("thr-b", [MISS] * 3)
    check(a == [1] and b == [1], f"throttle: sessions are independent (got {a}, {b})")

    # corrupt state fails open: reminds, exits 0, and the file is valid again
    fired_seq("thr-corrupt", [MISS, MISS])
    for junk in ("{not json", '{"n": "x"}', '{"n": 99}', "[]", ""):
        (d / "thr-corrupt.json").write_text(junk)
        got = fired_seq("thr-corrupt", [MISS])
        ok_file = json.loads((d / "thr-corrupt.json").read_text()) == {"n": 0}
        check(got == [1] and ok_file, f"corrupt state {junk!r}: reminds, rewrites valid state (got {got})")

    # an unwritable state dir: never an error, unthrottled (reminds every call)
    with tempfile.TemporaryDirectory() as tmp:
        blocker = os.path.join(tmp, "not-a-dir")
        pathlib.Path(blocker).write_text("x")
        got = fired_seq("thr-ro", [MISS] * 3, env_over={"CLAUDE_PLUGIN_DATA": blocker})
        check(got == [1, 2, 3], f"unwritable state dir: fails open, exit 0 (got {got})")

    # no session_id: unthrottled
    got = []
    for i in range(3):
        r, _ = run(json.dumps({"tool_name": "Agent", "tool_input": MISS}))
        got.append(bool(r.returncode == 0 and only_context(r.stdout)))
    check(got == [True] * 3, f"no session_id: reminds every call, exit 0 (got {got})")

    # a hostile session_id stays inside the state dir
    with tempfile.TemporaryDirectory() as tmp:
        data = os.path.join(tmp, "data")
        got = fired_seq("../../escape", [MISS, MISS], env_over={"CLAUDE_PLUGIN_DATA": data})
        inside = [p for p in pathlib.Path(tmp).rglob("*.json")]
        check(got == [1] and len(inside) == 1
              and inside[0].parent == pathlib.Path(data) / "agent-model-reminder",
              f"hostile session_id: one state file, inside the state dir (got {got}, {inside})")

    # TMPDIR fallback when CLAUDE_PLUGIN_DATA is unset
    with tempfile.TemporaryDirectory() as tmp:
        got = fired_seq("thr-tmp", [MISS] * 2, env_over={"CLAUDE_PLUGIN_DATA": None, "TMPDIR": tmp})
        f = pathlib.Path(tmp) / "pulseengine-claude" / "agent-model-reminder" / "thr-tmp.json"
        check(got == [1] and f.is_file(), f"TMPDIR fallback: state under pulseengine-claude/ (got {got})")

    # pruning: a new session's file removes state older than 7 days, keeps newer
    old, young = d / "old-session.json", d / "young-session.json"
    for p, age in ((old, 8 * 86400), (young, 86400)):
        p.write_text('{"n": 0}')
        t = time.time() - age
        os.utime(p, (t, t))
    fired_seq("thr-prune-trigger", [MISS])
    check(not old.exists() and young.exists(), "prune: 8-day-old state removed, 1-day-old kept")

    # atomic write: no temp files left behind
    leftovers = [p.name for p in d.iterdir() if p.name.startswith(".tmp-")]
    check(not leftovers, f"atomic: no temp files left in the state dir ({leftovers})")


def main() -> int:
    bash = shutil.which("bash")
    if not bash or not WRAPPER.is_file() or not HOOKS_JSON.is_file():
        print(f"error: need bash and {WRAPPER.relative_to(ROOT)}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as state:
        STATE["dir"] = state
        return checks()


def checks() -> int:
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
                           input=SILENT[name], capture_output=True, text=True, timeout=10,
                           env=dict(os.environ, CLAUDE_PLUGIN_DATA=STATE["dir"]))
        check(r.returncode == 0 and r.stdout == "" and r.stderr == "",
              f"python alone: {name} -> exit 0, no output (rc={r.returncode}, err={r.stderr[-80:]!r})")

    check(slowest < 2.0, f"fast: slowest run {slowest:.3f}s < 2s")

    throttle_checks()

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
