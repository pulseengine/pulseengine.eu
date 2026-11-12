#!/usr/bin/env python3
"""Oracle for the disk-pressure hook (REQ-DISK-PRESSURE).

  python3 scripts/check-disk-pressure.py

Runs hooks/disk-pressure.sh the way Claude Code does (JSON on stdin) with a
fake `warte` on PATH whose `probe pressure --format json` prints a scenario
from a file, and counts its calls. Checks: only disk-heavy commands are looked
at; the probe is called without --measure; a low or critical volume is said
with the calling session's own holdings, the three biggest other live holders
by repo and session, and ended sessions' scratchpads as "tell the owner";
holders on a volume that is fine are left out; unsized holders say so; ok is
silent; a stale answer, no volumes, a failing or garbled probe and no probe at
all are "not available" (never ok) and fall back to statvfs; the answer is
cached; the line is said once per verdict per session and again when worse or
after a recovery; no run prints a permission decision or exits non-zero. The
statvfs fallback is tested in-process with platform, mounts and statvfs faked:
macOS measures the Data volume (not the sealed /) plus the working
directory's volume, Linux measures /.

Python 3.9, stdlib only. Mount names and repos in fixtures are made up.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "claude-tooling", "plugins", "pulseengine-claude", "hooks")
SH = os.path.join(HOOKS, "disk-pressure.sh")
PY = os.path.join(HOOKS, "disk-pressure.py")
EXT = "/Volumes/ext-test"
FAILS = []


def check(ok, what):
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        FAILS.append(what)


def scenario(verdict, holders=True, age=0, volumes=True, sized_age=0, sized=True):
    now = time.time()
    vols = [{"mount": EXT, "free_gb": {"critical": 7.5, "low": 15.0, "ok": 90.0}[verdict],
             "total_gb": 1000, "verdict": verdict,
             "held_gb": {"scratchpad": 20, "target": 60, "worktree": 5}},
            {"mount": "/data-test", "free_gb": 80.0, "total_gb": 460, "verdict": "ok",
             "held_gb": {"scratchpad": 0, "target": 0, "worktree": 0}}] if volumes else []
    hs = [
        {"kind": "target", "mount": EXT, "gb": 12, "path": "/x/1", "session_id": "self-session-1", "live": True},
        {"kind": "target", "mount": EXT, "gb": 54, "path": "/x/2", "repo": "meld", "live": True,
         "agents": [{"agent": "claude", "pid": 101}], "pid": 101, "complete": False},
        {"kind": "scratchpad", "mount": EXT, "gb": 14, "path": "/x/3", "session_id": "cccc2222", "pid": 102, "repo": "witness", "live": True},
        {"kind": "scratchpad", "mount": EXT, "gb": 9, "path": "/x/4", "session_id": "dddd3333", "repo": "synth", "live": True},
        {"kind": "worktree", "mount": EXT, "gb": 5, "path": "/x/5", "session_id": "eeee4444", "repo": "rivet", "live": True},
        {"kind": "scratchpad", "mount": EXT, "gb": 30, "path": "/x/6", "session_id": "ffff5555", "live": False},
        {"kind": "target", "mount": "/data-test", "gb": 40, "path": "/x/7", "session_id": "gggg6666", "repo": "loom", "live": True},
    ] if holders else []
    return {"host": "test-host", "verdict": verdict, "volumes_at": now - age,
            "measured_at": (now - sized_age) if sized else None, "volumes": vols,
            "holders": hs if sized else []}


class Env:
    def __init__(self, base, warte=True):
        self.dir = tempfile.mkdtemp(dir=base)
        self.bin = os.path.join(self.dir, "bin")
        os.makedirs(self.bin)
        self.scen = os.path.join(self.dir, "scenario.json")
        self.calls = os.path.join(self.dir, "calls")
        if warte:
            self.fake_warte('cat "%s"' % self.scen)
        self.env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin",
                    "HOME": os.path.join(self.dir, "home"),
                    "CLAUDE_PLUGIN_DATA": os.path.join(self.dir, "data")}
        os.makedirs(self.env["HOME"])

    def fake_warte(self, body):
        exe = os.path.join(self.bin, "warte")
        with open(exe, "w") as f:
            f.write('#!/bin/sh\necho "$*" >> "%s"\n'
                    'case "$*" in *--measure*) echo measured >&2; exit 9;; esac\n'
                    '[ "$1 $2 $3 $4" = "probe pressure --format json" ] || exit 2\n%s\n'
                    % (self.calls, body))
        os.chmod(exe, 0o755)

    def set(self, obj):
        with open(self.scen, "w") as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj))

    def ncalls(self):
        return len(open(self.calls).read().splitlines()) if os.path.exists(self.calls) else 0

    def args(self):
        return open(self.calls).read() if os.path.exists(self.calls) else ""

    def run(self, command, session="self-session-1", stdin=None):
        ev = stdin if stdin is not None else json.dumps(
            {"tool_name": "Bash", "session_id": session, "cwd": self.dir,
             "tool_input": {"command": command}})
        return subprocess.run(["bash", SH], input=ev, capture_output=True, text=True,
                              env=self.env, timeout=30)

    def drop_cache(self):
        p = os.path.join(self.env["CLAUDE_PLUGIN_DATA"], "disk-pressure", "verdict.json")
        if os.path.exists(p):
            os.remove(p)


def ctx(p):
    if not p.stdout.strip():
        return ""
    try:
        return json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError):
        return "<unparseable: %r>" % p.stdout[:200]


def in_process(dp):
    check([dp.verdict_for(x) for x in (9.9, 10.0, 19.9, 20.0)] == ["critical", "low", "low", "ok"],
          "thresholds: under 10 GB critical, under 20 GB low, 20 GB ok")
    real = (dp.sys, dp.os.path.isdir, dp.os.statvfs, dp.os.path.ismount, dp.os.path.realpath)
    try:
        dp.os.path.realpath = lambda p: p
        dp.os.path.isdir = lambda p: p in ("/System/Volumes/Data", "/work-test/repo")
        dp.os.path.ismount = lambda p: p in ("/", "/System/Volumes/Data", "/work-test")
        dp.sys = type("S", (), {"platform": "darwin"})
        check(dp.data_volume() == "/System/Volumes/Data",
              "macOS fallback measures the Data volume, not the sealed /")
        seen = []
        free = {"/System/Volumes/Data": 50 * 10**9, "/work-test": 5 * 10**9}

        def statvfs(p):
            seen.append(p)
            return type("V", (), {"f_bavail": free[p] // 4096, "f_frsize": 4096,
                                  "f_blocks": hash(p) & 0xffff})
        dp.os.statvfs = statvfs
        v = dp.local_verdict("/work-test/repo")
        check(seen == ["/System/Volumes/Data", "/work-test"] and v["verdict"] == "critical",
              "fallback measures the Data volume and the cwd's volume; the worst (5 GB) wins")
        m = dp.message(v, "s")
        check("/work-test 5 GB free" in m and "/System/Volumes/Data" not in m.split("(", 2)[1]
              and "local measure" in m and "next disk-heavy command" in m,
              "the fallback line names the bad volume only, says it is local, and the next command")
        check("small batches" in m and "bench-devices.yaml disk-io" in m,
              "every low volume gets the batch caution, internal disks too")
        dp.sys = type("S", (), {"platform": "linux"})
        check(dp.data_volume() == "/", "Linux fallback measures /")
    finally:
        dp.sys, dp.os.path.isdir, dp.os.statvfs, dp.os.path.ismount, dp.os.path.realpath = real


def main():
    base = tempfile.mkdtemp(prefix="disk-pressure-test-")
    outputs = []
    try:
        spec = importlib.util.spec_from_file_location("dp", PY)
        dp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dp)
        in_process(dp)

        e = Env(base)
        e.set(scenario("critical"))
        p = e.run("ls -la")
        outputs.append(p)
        check(p.stdout == "" and e.ncalls() == 0, "a non-heavy command: silent, probe not called")

        p = e.run("cd x && cargo test --workspace")
        outputs.append(p)
        c = ctx(p)
        check("CRITICAL" in c and EXT + " 7.5 GB free" in c and "(warte probe)" in c,
              "critical on a volume is said, naming the volume")
        check("you hold target 12 GB" in c, "the calling session's own holding is 'yours'")
        check("target >=54 GB (repo meld, agent claude, pid 101)" in c and "repo witness" in c
              and "repo synth" in c and "repo rivet" not in c,
              "the three biggest other live holders, largest first, by repo and session")
        check("small batches" in c and "bench-devices.yaml disk-io" in c,
              "the warte line carries the batch caution and the with-device route")
        check("30 GB in 1 ended session(s): tell the owner" in c and "ffff5555" not in c,
              "an ended session's scratchpad goes to the owner, never to the holder list")
        check("repo loom" not in c, "holders on a volume that is fine are left out")
        check("--measure" not in e.args() and e.ncalls() == 1, "probe called once, without --measure")

        p = e.run("cargo build")
        outputs.append(p)
        check(p.stdout == "" and e.ncalls() == 1, "same session, same verdict: silent; cached")
        p = e.run("git clone https://example.invalid/r.git", session="other-session")
        outputs.append(p)
        c = ctx(p)
        check("CRITICAL" in c and e.ncalls() == 1 and "you hold" not in c
              and "target 12 GB (session self-ses" in c,
              "another session is told from the cache, and sees the first one's holding as other")

        e = Env(base)
        seq = []
        for verdict in ("low", "critical", "low", "ok", "low"):
            e.set(scenario(verdict))
            e.drop_cache()
            seq.append(e.run("cargo test"))
        outputs += seq
        check("LOW" in ctx(seq[0]) and "CRITICAL" in ctx(seq[1]), "low, then worse to critical: both said")
        check(seq[2].stdout == "", "critical easing to low: not said again")
        check(seq[3].stdout == "", "ok is silent")
        check("LOW" in ctx(seq[4]), "after a recovery to ok, low is said again")

        e = Env(base)
        e.set(scenario("critical", holders=False))
        p = e.run("docker pull alpine")
        outputs.append(p)
        check("not sized yet" in ctx(p), "critical with no holders yet says sizing is pending")

        e = Env(base)
        e.set(scenario("critical", sized=False))
        p = e.run("cargo build")
        outputs.append(p)
        check("CRITICAL" in ctx(p) and "not sized yet" in ctx(p) and "(warte probe)" in ctx(p),
              "measured_at null: volumes still count, holders 'not sized yet'")
        e = Env(base)
        e.set(scenario("critical", sized_age=7200))
        p = e.run("cargo build")
        outputs.append(p)
        check("CRITICAL" in ctx(p) and "not sized yet" in ctx(p) and "repo meld" not in ctx(p),
              "holders sized long ago are not named; fresh volumes still count")

        cases = [("a stale answer", scenario("critical", age=7200)),
                 ("an answer without volumes", scenario("critical", volumes=False)),
                 ("garbled output", "not json"),
                 ("a probe that fails", None)]
        for what, obj in cases:
            e = Env(base)
            if obj is None:
                e.fake_warte("exit 3")
            else:
                e.set(obj)
            p = e.run("npm install")
            outputs.append(p)
            check("(warte probe)" not in p.stdout and e.ncalls() == 1,
                  "%s is not available: falls back to statvfs" % what)
        e = Env(base, warte=False)
        p = e.run("cargo install foo")
        outputs.append(p)
        check("(warte probe)" not in p.stdout, "no warte on PATH: falls back to statvfs")

        # Heavy disk I/O takes turns through with-device (jess), whatever the free space.
        e = Env(base)
        e.set(scenario("ok"))
        wd = os.path.join(e.bin, "with-device")
        with open(wd, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(wd, 0o755)
        p = e.run("cargo mutants --in-place")
        outputs.append(p)
        c = ctx(p)
        check("disk-io:" in c and "with-device --registry ~/.config/pulseengine/bench-devices.yaml disk-io --wait 3600" in c and "disk-pressure:" not in c,
              "unwrapped cargo mutants: the with-device line, even with free space")
        p = e.run("cargo mutants -p foo")
        outputs.append(p)
        check(p.stdout == "", "the same session is not told again within 30 minutes")
        p = e.run("with-device --registry ~/.config/pulseengine/bench-devices.yaml disk-io --wait 3600 -- cargo mutants", session="s-wrapped")
        outputs.append(p)
        check(p.stdout == "", "a command already run through with-device is left alone")
        p = e.run("rm -rf ../wt-576/target", session="s-rm")
        outputs.append(p)
        check("disk-io:" in ctx(p), "a mass delete of a target/ is disk-heavy")
        p = e.run("rm notes.txt", session="s-small")
        outputs.append(p)
        check(p.stdout == "", "deleting one file is not")
        os.remove(wd)
        p = e.run("cargo clean", session="s-nowd")
        outputs.append(p)
        check("not installed" in ctx(p), "without with-device the line says so and asks for batching")

        e = Env(base)
        for bad in ("", "not json", json.dumps([1]), json.dumps({"tool_name": "Edit"})):
            p = e.run(None, stdin=bad)
            outputs.append(p)
            check(p.stdout == "" and p.returncode == 0, "bad input %r: silent, exit 0" % bad[:12])

        check(all(p.returncode == 0 for p in outputs), "every run exits 0")
        check(not any("permissionDecision" in p.stdout or "updatedInput" in p.stdout for p in outputs),
              "no run prints a permission decision or rewrites the call")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    if FAILS:
        print("%d failed" % len(FAILS), file=sys.stderr)
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
