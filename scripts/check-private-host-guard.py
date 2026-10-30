#!/usr/bin/env python3
# rivet: verifies REQ-GUARDS-050
"""Check the PreToolUse(Edit|Write|MultiEdit) private-host-guard hook.

Runs the real wrapper, hooks/private-host-guard.sh, under bash with each case's
JSON on stdin, against real git repos placed OUTSIDE every temp root (a
`.hookfix-*` dir under the repo checkout, removed afterwards), because files
under TMPDIR, /tmp and /var/folders are exempt by design. HOME points at a
fixture home inside that dir and GIT_CONFIG_GLOBAL at an empty file.

  ask       Write of a new file (also in a not-yet-existing subdir) with a .local
            host; Edit adding an RFC 1918 address; MultiEdit adding a /Volumes
            path; a ULA address; the owner's home path. The reason names the
            kind, masks the value, and says the owner edits the allow-lists;
  silent    the value was already in old_string; a temp-dir file; a file under
            ~/.claude; a dir that is not a git repo; a git-ignored file; a file
            inside .git/; a repo .private-hostname-allow glob and a file: rule;
            the user allow-list; settings.local.json, `*.local`, a version
            number and /Users/<other> (path boundary); a non-edit tool;
            malformed or empty stdin;
  shape     every run exits 0 with empty stderr; output is an ask (+ reason) or
            nothing, never deny, an approving decision or updatedInput; no
            python3 or a crashing python3 is silent;
  wired     hooks.json registers the wrapper once, under PreToolUse with
            matcher "Edit|Write|MultiEdit".

Exit: 0 all hold · 1 a check failed · 2 cannot check (no bash or git, no hook,
or the checkout itself sits under a temp root).
"""

from __future__ import annotations

import contextlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude" / "hooks"
WRAPPER = HOOKS / "private-host-guard.sh"
HOOKS_JSON = HOOKS / "hooks.json"
CMD = "bash ${CLAUDE_PLUGIN_ROOT}/hooks/private-host-guard.sh"
TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
CRASH_PY = "#!/bin/sh\necho 'Traceback (most recent call last):' >&2\nexit 1\n"

FAILS = []


def fail(msg):
    FAILS.append(msg)
    print("FAIL " + msg)


def under_temp(p):
    rp = os.path.realpath(p)
    roots = list(TEMP_ROOTS) + [tempfile.gettempdir()]
    return any(rp == os.path.realpath(r) or rp.startswith(os.path.realpath(r) + "/") for r in roots)


class Env:
    def __init__(self, base, tmp):
        self.base_dir = base
        self.home = base / "home"
        self.home.mkdir()
        (self.home / "empty.gitconfig").write_text("")
        self.tmp = tmp
        tools = {t: shutil.which(t) for t in ("git", "bash", "cat", "dirname")}
        tools["python3"] = sys.executable
        if not all(tools.values()):
            print("cannot check: missing %s" % [k for k, v in tools.items() if not v])
            sys.exit(2)
        self.links, self.nopy, self.crash = base / "bin", base / "bin-nopy", base / "bin-crash"
        for d in (self.links, self.nopy, self.crash):
            d.mkdir()
            for name, path in tools.items():
                if d == self.nopy and name == "python3":
                    continue
                if d == self.crash and name == "python3":
                    (d / "python3").write_text(CRASH_PY)
                    (d / "python3").chmod(0o755)
                    continue
                (d / name).symlink_to(path)

    def env(self, path_dir=None):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("GIT_", "GH_", "GITHUB_", "CLAUDE_", "PULSEENGINE_"))
               and k not in ("HOME", "PATH", "XDG_CONFIG_HOME", "TMPDIR")}
        env.update({"HOME": str(self.home), "PATH": str(path_dir or self.links),
                    "GIT_CONFIG_GLOBAL": str(self.home / "empty.gitconfig"),
                    "GIT_CONFIG_NOSYSTEM": "1", "TMPDIR": str(self.tmp),
                    # the fixture dir sits inside this checkout: stop repo discovery there
                    "GIT_CEILING_DIRECTORIES": str(self.base_dir)})
        return env

    def repo(self, name, parent=None):
        d = (parent or self.base_dir) / name
        d.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=d, env=self.env(), check=True, capture_output=True)
        return d


def run(E, event, path_dir=None):
    stdin = event if isinstance(event, str) else json.dumps(event)
    return subprocess.run(["bash", str(WRAPPER)], input=stdin, capture_output=True, text=True,
                          env=E.env(path_dir), timeout=30)


def ev(tool, file_path, cwd, **ti):
    ti["file_path"] = str(file_path)
    return {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": ti, "cwd": str(cwd), "tool_use_id": "toolu_test"}


def classify(name, r):
    if r.returncode != 0:
        fail("%s: exit %d" % (name, r.returncode))
    if r.stderr:
        fail("%s: stderr %r" % (name, r.stderr[:200]))
    if not r.stdout:
        return "silent", ""
    try:
        out = json.loads(r.stdout)
    except ValueError:
        fail("%s: stdout is not JSON: %r" % (name, r.stdout[:200]))
        return "bad", ""
    hso = out.get("hookSpecificOutput") if isinstance(out, dict) else None
    if set(out) != {"hookSpecificOutput"} or not isinstance(hso, dict) \
            or hso.get("hookEventName") != "PreToolUse":
        fail("%s: unexpected output shape %r" % (name, out))
        return "bad", ""
    if set(hso) == {"hookEventName", "permissionDecision", "permissionDecisionReason"} \
            and hso["permissionDecision"] == "ask":
        return "ask", hso["permissionDecisionReason"]
    fail("%s: output carries %r (only an ask + reason allowed)" % (name, sorted(hso)))
    return "bad", ""


def expect(name, r, want, contains=(), absent=()):
    got, text = classify(name, r)
    if got != want:
        fail("%s: expected %s, got %s %r" % (name, want, got, text[:300]))
        return
    bad = len(FAILS)
    for c in contains:
        if c not in text:
            fail("%s: reason lacks %r: %r" % (name, c, text[:400]))
    for a in absent:
        if a in text:
            fail("%s: reason contains %r" % (name, a))
    if len(FAILS) == bad:
        print("ok   %-60s %s" % (name, got))


def cases(E):
    repo = E.repo("repo")
    (repo / ".gitignore").write_text("secret.env\n")
    plain = E.base_dir / "plain"
    plain.mkdir()
    E.repo(".claude", parent=E.home)  # a ~/.claude that is itself a git repo is still exempt
    # Inside the hook's own TMPDIR: a sibling temp dir is a temp dir only where
    # the platform's temp root is one of the fixed roots (macOS /var/folders),
    # not on a runner whose TMPDIR points elsewhere (CI, 2026-10-30).
    with contextlib.nullcontext(E.tmp) as td:
        trepo = pathlib.Path(os.path.realpath(td)) / "trepo"
        trepo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=trepo, env=E.env(), check=True, capture_output=True)
        own = ("owner", "private-hostname-allow")

        expect("Write a new file with a .local host",
               run(E, ev("Write", repo / "deploy.sh", repo, content="ssh buildbox.local true\n")),
               "ask", ("mdns/lan", "bu***cal", "deploy.sh") + own, ("buildbox.local",))
        expect("Write into a not-yet-existing subdir",
               run(E, ev("Write", repo / "new" / "dir" / "a.md", repo, content="at 10.1.2.3\n")),
               "ask", ("ipv4",))
        expect("Edit adds an RFC 1918 address",
               run(E, ev("Edit", repo / "README.md", repo, old_string="host: x", new_string="host: 192.168.1.50")),
               "ask", ("ipv4", "19***.50"), ("192.168.1.50",))
        expect("MultiEdit adds a /Volumes path",
               run(E, ev("MultiEdit", repo / "a.sh", repo,
                         edits=[{"old_string": "a", "new_string": "b"},
                                {"old_string": "c", "new_string": "cd /Volumes/Data/work"}])),
               "ask", ("volumes",))
        expect("ULA address", run(E, ev("Write", repo / "net.yml", repo, content="addr: fd12:3456:789a::1\n")),
               "ask", ("ula",))
        expect("owner's home path",
               run(E, ev("Write", repo / "notes.md", repo, content="see %s/git/x\n" % E.home)),
               "ask", ("home",))
        expect("relative file_path resolves against cwd",
               run(E, ev("Write", "rel.md", repo, content="buildbox.lan\n")), "ask", ("mdns/lan",))

        for name, event in [
            ("value already in old_string",
             ev("Edit", repo / "README.md", repo, old_string="ssh 10.0.0.5", new_string="ssh -4 10.0.0.5")),
            ("file in a temp dir repo", ev("Write", trepo / "x.sh", trepo, content="ssh buildbox.local\n")),
            ("file under ~/.claude", ev("Write", E.home / ".claude" / "memory" / "m.md", E.home,
                                        content="host buildbox.local\n")),
            ("dir that is not a git repo", ev("Write", plain / "x.md", plain, content="buildbox.local\n")),
            ("git-ignored file", ev("Write", repo / "secret.env", repo, content="HOST=10.0.0.9\n")),
            ("inside .git/", ev("Write", repo / ".git" / "description", repo, content="10.0.0.9\n")),
            ("settings.local.json, *.local, a version, another user's home",
             ev("Write", repo / "doc.md", repo,
                content="edit settings.local.json; glob *.local; v10.2.3.4; bump 10.2.3; %s-other/x\n" % E.home)),
            ("clean content", ev("Write", repo / "ok.md", repo, content="nothing private\n")),
            ("non-edit tool", ev("Read", repo / "deploy.sh", repo, content="buildbox.local")),
            ("malformed JSON", '{"tool_name": "Write", "tool_input": {"file_path": "x'),
            ("empty stdin", ""),
            ("non-object tool_input", json.dumps({"tool_name": "Write", "tool_input": ["x"]})),
        ]:
            expect("silent: " + name, run(E, event), "silent")

        (repo / ".private-hostname-allow").write_text("# fixture names\n*.local\nfile:fixtures/*\n")
        expect("repo allow-list glob", run(E, ev("Write", repo / "d.sh", repo, content="buildbox.local\n")),
               "silent")
        expect("repo allow-list file: rule",
               run(E, ev("Write", repo / "fixtures" / "net.txt", repo, content="10.9.8.7\n")), "silent")
        expect("allow-list does not cover other kinds",
               run(E, ev("Write", repo / "d.sh", repo, content="10.9.8.7\n")), "ask", ("ipv4",))
        (repo / ".private-hostname-allow").unlink()
        cfg = E.home / ".config" / "pulseengine-claude"
        cfg.mkdir(parents=True)
        (cfg / "private-hostname-allow").write_text("10.9.8.7\n")
        expect("user allow-list", run(E, ev("Write", repo / "d.sh", repo, content="10.9.8.7\n")), "silent")
        (cfg / "private-hostname-allow").unlink()

        for name, d in (("no python3", E.nopy), ("crashing python3", E.crash)):
            expect("fails open: " + name,
                   run(E, ev("Write", repo / "deploy.sh", repo, content="buildbox.local\n"), path_dir=d), "silent")


def main():
    if not WRAPPER.is_file() or not shutil.which("bash") or not shutil.which("git"):
        print("cannot check: no hook, bash or git")
        return 2
    base = pathlib.Path(tempfile.mkdtemp(prefix=".hookfix-", dir=str(ROOT)))
    try:
        if under_temp(str(base)):
            print("cannot check: the checkout %s is under a temp root, where the hook is exempt" % ROOT)
            return 2
        with tempfile.TemporaryDirectory() as tmp:
            cases(Env(base, os.path.realpath(tmp)))
    finally:
        shutil.rmtree(str(base), ignore_errors=True)

    try:
        pre = json.loads(HOOKS_JSON.read_text())["hooks"]["PreToolUse"]
    except (OSError, ValueError, KeyError):
        fail("hooks.json has no PreToolUse list")
        pre = []
    hits = [e.get("matcher") for e in pre for h in e.get("hooks", []) if h.get("command") == CMD]
    if hits != ["Edit|Write|MultiEdit"]:
        fail("hooks.json: wrapper registered as %r, want once under 'Edit|Write|MultiEdit'" % hits)
    else:
        print("ok   wired once under PreToolUse matcher Edit|Write|MultiEdit")

    print("%d failure(s)" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
