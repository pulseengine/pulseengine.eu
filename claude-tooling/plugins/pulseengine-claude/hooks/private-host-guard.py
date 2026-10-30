#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit) hook (pulseengine-claude): ask before a
host-shaped value lands in a file of a git repository.

Private hostnames, LAN and tailnet addresses, mount paths and the owner's home
path have leaked into public repos and PR text (the 2026-10-30 tuition study
counted 39 edits into repo paths and 97 commit commands carrying one). This is
the client-side early warning; a server-side scan is separate work.

The check, in order, each step silent when it does not apply:
  - the file is under a temp dir (TMPDIR, /tmp, /private/tmp, /var/folders)
    or under ~/.claude (memory, transcripts): not a repo, never asked;
  - the nearest existing parent directory is not inside a git work tree, or
    the path is git-ignored there or inside .git/: never asked;
  - only text the call ADDS is scanned: Write content, Edit new_string minus
    values already in old_string, MultiEdit edits[].new_string likewise;
  - a value allowed by the repo's .private-hostname-allow or the user's
    ~/.config/pulseengine-claude/private-hostname-allow is dropped
    (see private_hosts.py for the line format).
Anything left is an "ask" with the kinds and masked values, never a deny: a
host-shaped value can be legitimate, and the owner decides.

Outputs: an ask (permissionDecision "ask" with a reason) or nothing. Always
exit 0; an exception prints nothing. Python 3.9+, stdlib only, no network.
"""

import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import private_hosts as ph  # noqa: E402

TOOLS = {"Edit", "Write", "MultiEdit"}
GIT_TIMEOUT_S = 3


def git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                           timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return r.returncode, r.stdout.strip()


def nearest_dir(path):
    d = os.path.dirname(path)
    while d and not os.path.isdir(d):
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    return d or None


def added_text(tool, ti):
    """[(new, old)] pairs whose new side is what the call writes."""
    if tool == "Write":
        return [(ti.get("content"), "")]
    if tool == "Edit":
        return [(ti.get("new_string"), ti.get("old_string") or "")]
    pairs = []
    for e in ti.get("edits") or []:
        if isinstance(e, dict):
            pairs.append((e.get("new_string"), e.get("old_string") or ""))
    return pairs


def decide(event):
    if not isinstance(event, dict) or event.get("tool_name") not in TOOLS:
        return None
    ti = event.get("tool_input")
    if not isinstance(ti, dict):
        return None
    fp = ti.get("file_path")
    if not isinstance(fp, str) or not fp:
        return None
    cwd = event.get("cwd") if isinstance(event.get("cwd"), str) and event.get("cwd") else os.getcwd()
    path = os.path.normpath(os.path.join(cwd, os.path.expanduser(fp)))
    if ph.in_temp(path) or ph.under(path, os.path.join(os.path.expanduser("~"), ".claude")):
        return None
    hits, seen = [], set()
    for new, old in added_text(event["tool_name"], ti):
        if not isinstance(new, str):
            continue
        before = {v for _, v in ph.find(old if isinstance(old, str) else "")}
        for k, v in ph.find(new):
            if v not in before and v not in seen:
                seen.add(v)
                hits.append((k, v))
    if not hits:
        return None
    d = nearest_dir(path)
    if not d:
        return None
    rc, top = git(["rev-parse", "--show-toplevel"], d)
    if rc != 0 or not top:
        return None
    rel = os.path.relpath(ph.realpath(path), ph.realpath(top))
    # a path inside .git/ never gets here: rev-parse --show-toplevel refuses
    # to run from inside the git dir, so the call above already returned
    if rel.startswith(".."):
        return None
    rc, _ = git(["check-ignore", "-q", "--no-index", "--", rel], top)
    if rc == 0:
        return None
    hits = ph.filter_hits(hits, rel, top)
    if not hits:
        return None
    reason = (
        "pulseengine-claude private-host-guard: this %s to %s (inside the git repo %s) adds "
        "host-shaped value(s): %s. Private hostnames, LAN/tailnet addresses, mount paths and "
        "home paths must not reach a repository. Replace them with a placeholder or an "
        "environment variable. If the value is meant to be there, the owner approves this call; "
        "the owner, not you, adds a line to %s or %s."
        % (event["tool_name"], rel, os.path.basename(top), ph.describe(hits),
           os.path.join(os.path.basename(top), ph.REPO_ALLOW), ph.user_allow_path()))
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "ask",
                                   "permissionDecisionReason": reason}}


def main():
    try:
        out = decide(json.loads(sys.stdin.read() or "null"))
        if out:
            sys.stdout.write(json.dumps(out))
    except Exception:  # fail open: a guard bug must never block every edit
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
