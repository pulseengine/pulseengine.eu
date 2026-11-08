#!/usr/bin/env python3
"""Oracle for the loop-guard hook (REQ-LOOP-GUARD).

  python3 scripts/check-loop-guard.py

Feeds hooks/loop-guard.sh PostToolUseFailure and PostToolUse events the way
Claude Code does (JSON on stdin, Bash error text starting "Exit code N"). Checks:
the 3rd identical failure of one command says so once, with the error's first
line, and the 6th again; the 1st, 2nd, 4th and 5th are silent; a success of that
command resets it; a different error, a different command or a failure older
than the window starts again; masked digits (line numbers, timestamps) still
count as the same error; interrupts and other tools are ignored; sessions are
separate; bad input is silent; nothing ever prints a permission decision or
exits non-zero, and the output names the PostToolUseFailure event.

Python 3.9, stdlib only.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "claude-tooling", "plugins", "pulseengine-claude", "hooks")
SH = os.path.join(HOOKS, "loop-guard.sh")
FAILS = []
OUT = []


def check(ok, what):
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        FAILS.append(what)


def run(env, event, cmd="cargo test -p foo", err="Exit code 101\nerror: test failed, to rerun pass `-p foo --lib`",
        session="s1", tool="Bash", interrupt=False, raw=None):
    if raw is None:
        ev = {"hook_event_name": event, "tool_name": tool, "session_id": session,
              "tool_input": {"command": cmd}}
        if event == "PostToolUseFailure":
            ev["error"] = err
            ev["is_interrupt"] = interrupt
        else:
            ev["tool_response"] = {"stdout": "ok", "stderr": ""}
        raw = json.dumps(ev)
    p = subprocess.run(["bash", SH], input=raw, capture_output=True, text=True, env=env, timeout=30)
    OUT.append(p)
    return p


def said(p):
    if not p.stdout.strip():
        return ""
    o = json.loads(p.stdout)["hookSpecificOutput"]
    return o["additionalContext"] if o.get("hookEventName") == "PostToolUseFailure" else "<wrong event>"


def fresh(base):
    d = tempfile.mkdtemp(dir=base)
    return {"PATH": "/usr/bin:/bin", "HOME": d, "CLAUDE_PLUGIN_DATA": os.path.join(d, "data")}


def main():
    base = tempfile.mkdtemp(prefix="loop-guard-test-")
    try:
        e = fresh(base)
        r = [run(e, "PostToolUseFailure") for _ in range(6)]
        check(all(x.stdout == "" for x in (r[0], r[1], r[3], r[4])), "failures 1, 2, 4 and 5 are silent")
        c3 = said(r[2])
        check("failed the same way 3 times" in c3 and "Exit code 101" in c3, "the 3rd identical failure says so, with the error")
        check("6 times" in said(r[5]), "the 6th says it again")
        r7 = run(e, "PostToolUseFailure")
        check(r7.stdout == "", "the 7th is silent")

        e = fresh(base)
        run(e, "PostToolUseFailure"); run(e, "PostToolUseFailure")
        run(e, "PostToolUse")
        p = run(e, "PostToolUseFailure")
        check(p.stdout == "", "a success of the command resets the count")
        run(e, "PostToolUseFailure")
        check("3 times" in said(run(e, "PostToolUseFailure")), "...and counting starts again after it")

        e = fresh(base)
        run(e, "PostToolUseFailure"); run(e, "PostToolUseFailure")
        p = run(e, "PostToolUseFailure", err="Exit code 1\nerror[E0308]: mismatched types")
        check(p.stdout == "", "a different error starts a new count")

        e = fresh(base)
        run(e, "PostToolUseFailure"); run(e, "PostToolUseFailure")
        p = run(e, "PostToolUseFailure", cmd="cargo test -p bar")
        check(p.stdout == "", "a different command starts its own count")

        e = fresh(base)
        errs = ["Exit code 1\nthread 'main' panicked at src/lib.rs:%d:5" % n for n in (10, 42, 97)]
        ps = [run(e, "PostToolUseFailure", err=x) for x in errs]
        check("3 times" in said(ps[2]), "changing line numbers still count as the same error")

        e = fresh(base)
        run(e, "PostToolUseFailure", cmd="cargo  test   -p foo"); run(e, "PostToolUseFailure")
        check("3 times" in said(run(e, "PostToolUseFailure", cmd=" cargo test -p foo ")),
              "whitespace differences are the same command")

        e = fresh(base)
        run(e, "PostToolUseFailure"); run(e, "PostToolUseFailure")
        check(run(e, "PostToolUseFailure", session="s2").stdout == "", "sessions are counted separately")

        e = fresh(base)
        run(e, "PostToolUseFailure"); run(e, "PostToolUseFailure")
        sd = os.path.join(e["CLAUDE_PLUGIN_DATA"], "loop-guard")
        for n in os.listdir(sd):
            p = os.path.join(sd, n)
            st = json.load(open(p))
            for v in st.values():
                v["at"] = time.time() - 3600
            json.dump(st, open(p, "w"))
        check(run(e, "PostToolUseFailure").stdout == "", "a repeat older than the 30-minute window starts again")

        e = fresh(base)
        for _ in range(3):
            p = run(e, "PostToolUseFailure", interrupt=True)
        check(p.stdout == "", "interrupted commands are not counted")
        for _ in range(3):
            p = run(e, "PostToolUseFailure", tool="Read")
        check(p.stdout == "", "other tools are ignored")

        e = fresh(base)
        p = run(e, "PostToolUse")
        check(p.stdout == "" and not os.path.exists(os.path.join(e["CLAUDE_PLUGIN_DATA"], "loop-guard")),
              "a success with no recent failure never starts python or writes state")

        for bad in ("", "not json", "[1]", json.dumps({"hook_event_name": "PostToolUseFailure"})):
            p = run(fresh(base), None, raw=bad)
            check(p.stdout == "" and p.returncode == 0, "bad input %r: silent, exit 0" % bad[:16])

        check(all(p.returncode == 0 for p in OUT), "every run exits 0")
        check(not any(x in p.stdout for p in OUT for x in ("permissionDecision", "updatedInput", '"decision"')),
              "no run prints a permission decision")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    if FAILS:
        print("%d failed" % len(FAILS), file=sys.stderr)
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
