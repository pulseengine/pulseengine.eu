#!/usr/bin/env python3
"""PreToolUse(Bash) hook (pulseengine-claude): disk pressure before heavy work.

On 2026-11-08 one workstation's data volume fell to 14 GB free while every
agent on it kept building; the holders were found by hand and freed 68 GB.
This hook puts that check in front of the agent on a command that eats disk
(a cargo build or test, a clone, a worktree, an image pull, a package install,
a model download). Claude Code delivers PreToolUse context with the call's
result, so the line shapes the NEXT heavy command, not the one that
triggered it.

It NEVER blocks, denies, approves or rewrites the call. When a volume is low
or critical it prints only `hookSpecificOutput.additionalContext` and exits 0;
otherwise, including bad input, an exception or no answer, it prints nothing
and exits 0.

Where the verdict comes from, in order:

1. The local warte probe: `warte probe pressure --format json`. It reads what
   the probe stored (no network, no live sizing; `--measure` is never used
   here) and answers per volume, with the holders it has sized: kind, mount,
   GB, path, the Claude Code session_id (scratchpads), the repo and the live
   agents working there. Volumes are read live (`volumes_at`); holders are
   sized only while a volume is low (`measured_at`, null until then). A
   holder of the calling session is "yours"; a holder whose session ended
   (`live` false) is reported to the owner, never deleted by an agent; a size
   with `complete` false is a floor. Volumes older than STALE_S, no volumes,
   or a probe that fails count as not available, never as ok. Holders sized
   longer ago than STALE_S, or not at all, are "not sized yet".
2. statvfs on the volumes this session writes to: the volume holding the
   session's working directory, and the data volume (on macOS the Data
   volume, not the sealed system volume at `/`; `/` elsewhere). Names nobody.

Low is under 20 GB free, critical under 10 GB, as in warte's defaults; the
worst volume wins. The verdict is cached for RECHECK_S, so the probe is asked
at most once per window however many commands run. Per session the line is
said once per verdict, and again only when it gets worse or after a recovery.

State: $CLAUDE_PLUGIN_DATA/disk-pressure/, else
${TMPDIR:-/tmp}/pulseengine-claude/disk-pressure/. Missing or corrupt state
fails open (asked again, said again).

Python 3.9+, stdlib only, no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

LOW_GB = 20.0
CRITICAL_GB = 10.0
RANK = {"ok": 0, "low": 1, "critical": 2}
RECHECK_S = 300
STALE_S = 1800
PROBE_TIMEOUT_S = 5
MAX_HOLDERS = 3

# Commands that can write gigabytes. Matched as words anywhere in the command,
# so chains (`cd x && cargo test`) count.
HEAVY = re.compile(
    r"\b(?:"
    r"cargo\s+(?:\+\S+\s+)?(?:build|b|test|t|install|bench|clippy|run|r|doc|check|c|"
    r"kani|mutants|miri|fuzz|llvm-cov|nextest|component)\b"
    r"|bazel(?:isk)?\s+(?:build|test|run)\b"
    r"|git\s+(?:\S+\s+)*?(?:clone|worktree\s+add)\b"
    r"|docker\s+(?:pull|build|buildx|compose\s+up)\b"
    r"|podman\s+(?:pull|build)\b"
    r"|nix\s+(?:build|develop|shell)\b|nix-build\b"
    r"|(?:npm|pnpm|yarn)\s+(?:ci|install|i|add)\b"
    r"|pip3?\s+install\b|uv\s+(?:sync|pip\s+install)\b"
    r"|huggingface-cli\s+download\b|hf\s+download\b"
    r"|ollama\s+pull\b|rustup\s+(?:toolchain\s+install|install|target\s+add)\b"
    r")"
)


# Disk-heavy work that should take turns on one machine (owner, 2026-11-08: ten
# sessions cleaning up or running mutation tests at once saturate a SATA disk).
HEAVY_IO = re.compile(
    r"\bcargo\s+(?:\+\S+\s+)?(?:mutants|clean)\b"
    r"|\bgit\s+(?:\S+\s+)*?worktree\s+remove\b"
    r"|\brm\s+-[A-Za-z]*r[A-Za-z]*\s+\S*(?:target|worktree|wt-)\S*"
)
IO_DEVICE = "disk-io"
IO_REPEAT_S = 1800


def other_heavy_jobs():
    """Count other disk-heavy processes on this machine (cargo-mutants, rm -r)."""
    try:
        out = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True, timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    names = [os.path.basename(x.strip()) for x in out.splitlines()]
    return sum(1 for n in names if n in ("cargo-mutants", "rm"))


def io_advice(cmd, sdir, sid, now):
    if not HEAVY_IO.search(cmd) or "with-device" in cmd:
        return None
    spath = os.path.join(sdir, "io-" + hashlib.sha256((sid or "none").encode()).hexdigest()[:16] + ".json")
    if now - load(spath).get("at", 0) < IO_REPEAT_S:
        return None
    save(spath, {"at": now})
    n = other_heavy_jobs()
    busy = ("%d other disk-heavy job(s) running on this machine. " % n) if n else ""
    tool = shutil.which("with-device")
    how = ("Run it as `with-device --registry ~/.config/pulseengine/bench-devices.yaml %s --wait 3600 --purpose '<what>' -- <command>` so sessions "
           "on this machine take turns." % IO_DEVICE) if tool else \
          ("`with-device` is not installed here, so batch it and coordinate with the other "
           "sessions before starting.")
    return ("disk-io: this command is disk-heavy (mass delete, cargo clean or mutation "
            "testing). " + busy + how)


def state_dir():
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    if base:
        return os.path.join(base, "disk-pressure")
    return os.path.join(tempfile.gettempdir(), "pulseengine-claude", "disk-pressure")


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


def verdict_for(free_gb):
    return "critical" if free_gb < CRITICAL_GB else "low" if free_gb < LOW_GB else "ok"


def worst(verdicts):
    return max(verdicts, key=lambda v: RANK.get(v, -1)) if verdicts else None


def data_volume():
    if sys.platform == "darwin" and os.path.isdir("/System/Volumes/Data"):
        return "/System/Volumes/Data"
    return "/"


def mount_of(path):
    path = os.path.realpath(path)
    while not os.path.ismount(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path


def local_verdict(cwd):
    vols = []
    seen = set()
    data = data_volume()
    for vol in [data] + ([mount_of(cwd)] if cwd and os.path.isdir(cwd) else []):
        try:
            st = os.statvfs(vol)
        except OSError:
            continue
        key = (st.f_blocks, st.f_frsize, st.f_bavail)
        if vol != data and key in seen:
            continue  # the cwd sits on the data volume already measured
        seen.add(key)
        free = st.f_bavail * st.f_frsize / 1e9
        vols.append({"mount": vol, "free_gb": round(free, 1), "verdict": verdict_for(free)})
    if not vols:
        return None
    return {"verdict": worst([v["verdict"] for v in vols]), "volumes": vols,
            "holders": [], "source": "local"}


def warte_bin():
    found = shutil.which("warte")
    if found:
        return found
    cand = os.path.expanduser("~/.local/bin/warte")
    return cand if os.access(cand, os.X_OK) else None


def probe_verdict(now):
    exe = warte_bin()
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "probe", "pressure", "--format", "json"],
                             capture_output=True, text=True, timeout=PROBE_TIMEOUT_S)
        if out.returncode != 0:
            return None
        body = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if not isinstance(body, dict):
        return None
    try:
        if now - float(body.get("volumes_at")) > STALE_S:
            return None  # stale volumes are not a measurement
    except (TypeError, ValueError):
        return None
    vols = [v for v in body.get("volumes") or [] if isinstance(v, dict) and v.get("verdict") in RANK]
    if not vols:
        return None
    holders = []
    m = body.get("measured_at")
    if isinstance(m, (int, float)) and not isinstance(m, bool) and now - m <= STALE_S:
        holders = [h for h in body.get("holders") or [] if isinstance(h, dict)]
    return {"verdict": worst([v["verdict"] for v in vols]), "volumes": vols,
            "holders": holders, "source": "warte"}


def current(sdir, now, cwd):
    cache = os.path.join(sdir, "verdict.json")
    c = load(cache)
    cwd_mount = mount_of(cwd) if cwd and os.path.isdir(cwd) else None
    if c.get("verdict") in RANK and now - c.get("at", 0) < RECHECK_S:
        if c.get("source") == "warte" or c.get("cwd_mount") == cwd_mount:
            return c
    v = probe_verdict(now) or local_verdict(cwd)
    if v:
        v["at"] = now
        v["cwd_mount"] = cwd_mount
        save(cache, v)
    return v


def gb(x, floor=False):
    if not isinstance(x, (int, float)):
        return "? GB"
    return (">=" if floor else "") + f"{x:g} GB"


def hgb(h):
    return gb(h.get("gb"), floor=h.get("complete") is False)


def describe(h):
    agents = [a for a in h.get("agents") or [] if isinstance(a, dict)]
    names = [str(a["agent"]) for a in agents if a.get("agent")]
    who = ("agent " + "/".join(names)) if names else None
    repo = ("repo " + str(h["repo"])) if h.get("repo") else None
    sid = str(h.get("session_id") or "")[:8]
    pid = h.get("pid") or (agents[0].get("pid") if len(agents) == 1 else None)
    tag = ", ".join(x for x in (repo, who, ("session " + sid) if sid else None,
                                ("pid %s" % pid) if pid else None) if x)
    return f"{h.get('kind', '?')} {hgb(h)} ({tag or 'owner unknown'})"


BATCH_NOTE = ("Delete in small batches (one target/ or worktree at a time) and coordinate "
              "before several sessions clean the same disk: ten sessions deleting or running "
              "mutation tests at once can saturate a SATA disk, internal or external, and an "
              "external one can disconnect; run the heavy part through "
              "`with-device --registry ~/.config/pulseengine/bench-devices.yaml disk-io --wait 3600 -- <command>` so they take turns.")


def message(v, session_id):
    bad = [x for x in v["volumes"] if x.get("verdict") in ("low", "critical")]
    vols = "; ".join(f"{x.get('mount', '?')} {gb(x.get('free_gb'))} free" for x in bad)
    head = f"disk-pressure: {v['verdict'].upper()} ({vols})"
    if v["source"] == "local":
        return (head + " (local measure; warte probe not available, so holders are unknown). "
                "Before your next disk-heavy command: free your own residue first "
                "(scratchpad, target/ of worktrees you are not building in, merged worktrees; "
                "only what you own). " + BATCH_NOTE + " " +
                "See the ci-status skill.")
    bad_mounts = {x.get("mount") for x in bad}
    hs = [h for h in v["holders"] if h.get("mount") in bad_mounts]
    mine = [h for h in hs if session_id and h.get("session_id") == session_id]
    live = [h for h in hs if h not in mine and h.get("live") is not False]
    dead = [h for h in hs if h not in mine and h.get("live") is False]
    parts = [head + " (warte probe)"]
    if mine:
        parts.append("you hold " + ", ".join(f"{h.get('kind', '?')} {hgb(h)}" for h in mine))
    if live:
        top = sorted(live, key=lambda h: -(h.get("gb") or 0))[:MAX_HOLDERS]
        parts.append("biggest other holders: " + "; ".join(describe(h) for h in top))
    if dead:
        parts.append("%s in %d ended session(s): tell the owner, do not delete"
                     % (gb(round(sum(h.get("gb") or 0 for h in dead), 1)), len(dead)))
    if not hs:
        parts.append("holders not sized yet (the probe sizes them within 10 min)")
    return (". ".join(parts) + ". Before your next disk-heavy command: free your own residue "
            "first (`warte probe pressure` lists paths; delete only what you own), then "
            "SendMessage the other holders, matched to ListAgents by repo. " +
            BATCH_NOTE + " " + "See the ci-status skill.")


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if not isinstance(event, dict) or event.get("tool_name") != "Bash":
        return
    cmd = (event.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str):
        return
    now = time.time()
    sdir = state_dir()
    sid = str(event.get("session_id") or "")
    lines = []
    adv = io_advice(cmd, sdir, sid, now)
    if adv:
        lines.append(adv)
    if not HEAVY.search(cmd):
        emit(lines)
        return
    cwd = event.get("cwd") if isinstance(event.get("cwd"), str) else None
    v = current(sdir, now, cwd)
    if not v:
        emit(lines)
        return
    spath = os.path.join(sdir, "session-" + hashlib.sha256((sid or "none").encode()).hexdigest()[:16] + ".json")
    s = load(spath)
    if v["verdict"] == "ok":
        if s.get("said"):
            save(spath, {"said": None, "at": now})  # recovered: say it again next time
        emit(lines)
        return
    said = s.get("said")
    if not (said in RANK and RANK[v["verdict"]] <= RANK[said]):
        save(spath, {"said": v["verdict"], "at": now})
        lines.append(message(v, sid))
    emit(lines)


def emit(lines):
    if lines:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": " ".join(lines)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # fail open: a reminder must never break a call
        pass
