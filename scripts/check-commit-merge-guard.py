#!/usr/bin/env python3
# rivet: verifies REQ-COMMIT-MERGE-GUARD
"""Check the PreToolUse(Bash) commit-merge-guard hook.

Runs the real wrapper, hooks/commit-merge-guard.sh, under bash with each case's
JSON on stdin, against real throwaway git repos and a stub `gh` that answers
from fixture files. Nothing reaches the network, the caller's git identity or
the real plugin data dir: HOME, GIT_CONFIG_GLOBAL and CLAUDE_PLUGIN_DATA point
into a temp dir, GIT_CONFIG_NOSYSTEM is set, tokens are stripped, and PATH is a
directory of symlinks (git, python3, bash, cat, dirname) plus the stub.

  identity  a repo-local one-letter identity (t@t, and a bare `t`) denies a
            commit: plain, -S, `git -C`, after `cd &&`, in `bash -c`, with the
            heredoc message agents use, with an unbalanced quote (coarse
            fallback), and in worktree scope; `git -c user.email=` and a
            GIT_AUTHOR_EMAIL prefix deny too; a name-only difference denies;
            the reason masks both addresses and tells the agent not to edit
            the allow-list. No local identity, a local value equal to the global
            one (case-insensitive), an allow-listed address (either allow-list
            file), no global identity, `rebase --abort`, `git log`, `echo "git
            commit"` and a non-repo dir are silent;
  merge     `gh pr merge --auto` on a smithy-shaped repo (no protection, rules
            403 "Upgrade to GitHub Pro") denies and names its automerge label;
            without the label it says wait for green; protection, a merge-queue
            ruleset and a required-status-checks ruleset are silent; repo from
            -R, --repo=, a PR URL, GH_REPO, gh-resolved, upstream before origin;
            a 500 on the repo or on rules (unprotected) warns and does not deny;
            no gh and no token warns; `gh pr merge` without --auto is silent and
            never calls the API;
  cache     a definitive answer is cached (second run: zero API calls), a
            day-old entry is re-fetched, a failure is not cached;
  quiet     unrelated commands and non-Bash tools print nothing, never call gh;
  shape     every run exits 0 with empty stderr; output is a deny
            (permissionDecision "deny" + reason) or additionalContext, never
            "allow" or updatedInput; no python3 or a crashing python3 is silent;
            the slowest run stays under 2 s;
  wired     hooks.json registers the wrapper once, under PreToolUse with
            matcher "Bash", after the Agent|Task entry.

Exit: 0 all hold · 1 a check failed · 2 cannot check (no bash or git, no hook).
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
WRAPPER = HOOKS / "commit-merge-guard.sh"
HOOKS_JSON = HOOKS / "hooks.json"
CMD = "bash ${CLAUDE_PLUGIN_ROOT}/hooks/commit-merge-guard.sh"

GLOBAL_NAME = "Owner Example"
GLOBAL_EMAIL = "owner@example.com"

STUB_GH = r'''#!/usr/bin/env python3
import os, sys
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
p = os.path.join(os.environ["STUB_DIR"], sys.argv[-1].replace("/", "__") + ".http")
try:
    data = open(p).read()
except OSError:
    data = "HTTP/2.0 404 Not Found\n\n{\"message\":\"Not Found\"}"
sys.stdout.write(data)
sys.exit(0 if data.startswith("HTTP/2.0 200") else 1)
'''

CRASH_PY = "#!/bin/sh\necho 'Traceback (most recent call last):' >&2\nexit 1\n"

FAILS = []


def fail(msg):
    FAILS.append(msg)
    print("FAIL " + msg)


def http(status, body):
    reason = {200: "OK", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}[status]
    return "HTTP/2.0 %d %s\nContent-Type: application/json\n\n%s" % (status, reason, json.dumps(body))


UPGRADE = {"message": "Upgrade to GitHub Pro or make this repository public to enable this feature.",
           "status": "403"}
UNPROT = {"name": "main", "protected": False,
          "protection": {"enabled": False, "required_status_checks": {"contexts": [], "checks": []}}}
PROT = {"name": "main", "protected": True,
        "protection": {"enabled": True, "required_status_checks": {"contexts": ["build"]}}}


def fixtures():
    f = {}

    def repo(name, branch, rules, label=False, repo_status=200):
        f["repos/acme/" + name] = http(repo_status, {"default_branch": "main", "private": True}
                                       if repo_status == 200 else {"message": "boom"})
        f["repos/acme/%s/branches/main" % name] = http(200, branch)
        f["repos/acme/%s/rules/branches/main" % name] = rules
        if label:
            f["repos/acme/%s/labels/automerge" % name] = http(200, {"name": "automerge"})

    repo("unprotected", UNPROT, http(403, UPGRADE), label=True)   # smithy#45 shape
    repo("nolabel", UNPROT, http(403, UPGRADE))
    repo("protected", PROT, http(200, []))
    repo("queue", UNPROT, http(200, [{"type": "merge_queue"}]))
    repo("ruleset", UNPROT, http(200, [{"type": "required_status_checks"}]))
    repo("deletiononly", UNPROT, http(200, [{"type": "deletion"}]))
    repo("rules500", UNPROT, http(500, {"message": "boom"}))
    repo("broken", UNPROT, http(200, []), repo_status=500)
    return f


class Env:
    def __init__(self, tmp):
        self.tmp = tmp
        self.home = tmp / "home"
        self.data = tmp / "data"
        self.stub = tmp / "stub"
        self.log = tmp / "gh.log"
        self.links = tmp / "bin"
        self.nogh = tmp / "bin-nogh"
        self.nopy = tmp / "bin-nopy"
        self.crash = tmp / "bin-crash"
        for d in (self.home, self.data, self.stub, self.links, self.nogh, self.nopy, self.crash):
            d.mkdir(parents=True)
        self.gitconfig = self.home / ".gitconfig"
        self.gitconfig.write_text("[user]\n\tname = %s\n\temail = %s\n" % (GLOBAL_NAME, GLOBAL_EMAIL))
        (self.home / "empty.gitconfig").write_text("")
        tools = {t: shutil.which(t) for t in ("git", "bash", "cat", "dirname")}
        tools["python3"] = sys.executable
        if not all(tools.values()):
            print("cannot check: missing %s" % [k for k, v in tools.items() if not v])
            sys.exit(2)
        for d in (self.links, self.nogh, self.nopy, self.crash):
            for name, path in tools.items():
                if d == self.nopy and name == "python3":
                    continue
                if d == self.crash and name == "python3":
                    (d / "python3").write_text(CRASH_PY)
                    (d / "python3").chmod(0o755)
                    continue
                (d / name).symlink_to(path)
        for d in (self.links, self.nopy, self.crash):
            (d / "gh").write_text(STUB_GH)
            (d / "gh").chmod(0o755)
        for path, text in fixtures().items():
            (self.stub / (path.replace("/", "__") + ".http")).write_text(text)

    def base(self, path_dir=None, **over):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("GIT_", "GH_", "GITHUB_", "CLAUDE_"))
               and k not in ("HOME", "PATH", "XDG_CONFIG_HOME", "TMPDIR")}
        env.update({
            "HOME": str(self.home), "PATH": str(path_dir or self.links),
            "GIT_CONFIG_GLOBAL": str(self.gitconfig), "GIT_CONFIG_NOSYSTEM": "1",
            "CLAUDE_PLUGIN_DATA": str(self.data), "TMPDIR": str(self.tmp),
            "STUB_DIR": str(self.stub), "STUB_LOG": str(self.log),
            "PULSEENGINE_GITHUB_API": "http://127.0.0.1:9",
        })
        env.update(over)
        return env

    def git(self, cwd, *args):
        subprocess.run(["git"] + list(args), cwd=cwd, env=self.base(), check=True,
                       capture_output=True)

    def repo(self, name, origin=None, **cfg):
        d = self.tmp / "repos" / name
        d.mkdir(parents=True)
        self.git(d, "init", "-q")
        for k, v in cfg.items():
            self.git(d, "config", "--local", k.replace("_", "."), v)
        if origin:
            self.git(d, "remote", "add", "origin", origin)
        return d

    def calls(self):
        try:
            return len(self.log.read_text().splitlines())
        except OSError:
            return 0

    def reset_cache(self):
        shutil.rmtree(self.data / "commit-merge-guard", ignore_errors=True)


SLOWEST = [0.0, ""]


def run(env, event, path_dir=None, **over):
    stdin = event if isinstance(event, str) else json.dumps(event)
    t = time.monotonic()
    r = subprocess.run(["bash", str(WRAPPER)], input=stdin, capture_output=True, text=True,
                       env=env.base(path_dir, **over), timeout=30)
    dt = time.monotonic() - t
    if dt > SLOWEST[0]:
        SLOWEST[:] = [dt, stdin[:60]]
    return r


def ev(command, cwd, tool="Bash"):
    return {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"command": command, "description": "x"}, "cwd": str(cwd),
            "tool_use_id": "toolu_test"}


def classify(name, r):
    """'deny', 'warn' or 'silent'; records a failure on any shape violation."""
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
    keys = set(hso) - {"hookEventName"}
    if keys == {"permissionDecision", "permissionDecisionReason"} and hso["permissionDecision"] == "deny":
        return "deny", hso["permissionDecisionReason"]
    if keys == {"additionalContext"}:
        return "warn", hso["additionalContext"]
    fail("%s: output carries %r (only deny+reason or additionalContext allowed)" % (name, sorted(keys)))
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
        print("ok   %-58s %s" % (name, got))


def main():
    if not WRAPPER.is_file() or not shutil.which("bash") or not shutil.which("git"):
        print("cannot check: no hook, bash or git")
        return 2
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(os.path.realpath(td))
        E = Env(tmp)
        nonrepo = tmp / "nonrepo"
        nonrepo.mkdir()
        t_repo = E.repo("t", "git@github.com:acme/unprotected.git", user_name="t", user_email="t@t")
        bare_t = E.repo("baret", user_name="t", user_email="t")
        ok = E.repo("ok", "https://github.com/acme/protected.git")
        same = E.repo("same", user_name=GLOBAL_NAME, user_email=GLOBAL_EMAIL.upper())
        allowed = E.repo("allowed", user_email="second@example.com", user_name=GLOBAL_NAME)
        allowed2 = E.repo("allowed2", user_email="third@example.com", user_name=GLOBAL_NAME)
        name_only = E.repo("nameonly", user_name="t")
        wt = E.repo("wt")
        E.git(wt, "config", "extensions.worktreeConfig", "true")
        E.git(wt, "config", "--worktree", "user.email", "t@t")
        (E.data / "commit-identity-allow").write_text("# owner's second address\nSECOND@example.com\n")
        cfgdir = E.home / ".config" / "pulseengine-claude"
        cfgdir.mkdir(parents=True)
        (cfgdir / "commit-identity-allow").write_text("third@example.com\n")

        no_leak = (GLOBAL_EMAIL, "t@t,", "'t@t'")
        deny_id = ("t***", "o***@example.com", "Do not add it yourself", "INC-2026-10-006")

        # ── identity ─────────────────────────────────────────────────────────
        before = E.calls()
        heredoc = ("cd %s && git add -A && git commit -S -m \"$(cat <<'EOF'\n"
                   "fix: don't lose the trailer\n\nCo-Authored-By: A <a@example.com>\n"
                   "Claude-Session: https://example.com/s\nEOF\n)\"" % t_repo)
        for name, cmd, cwd in [
            ("synth INC-006: local t@t, git commit", "git commit -m x", t_repo),
            ("local t@t, git commit -S", "git commit -S -m x", t_repo),
            ("local t@t, git -C from elsewhere", "git -C %s commit -m x" % t_repo, nonrepo),
            ("local t@t, cd && chained heredoc commit", heredoc, nonrepo),
            ("local t@t, bash -c", "bash -c 'cd %s && git commit -m z'" % t_repo, nonrepo),
            ("local t@t, unbalanced quote (coarse path)", 'git commit -m "oops', t_repo),
            ("local t@t, git cherry-pick", "git cherry-pick abc123", t_repo),
            ("local t@t, git rebase main", "git rebase main", t_repo),
            ("local t@t, backslash-newline continuation",
             "git -C %s \\\n  commit -m x" % t_repo, nonrepo),
        ]:
            expect(name, run(E, ev(cmd, cwd)), "deny", deny_id, no_leak)
        expect("bare `t` email (no @)", run(E, ev("git commit -m x", bare_t)), "deny",
               ("no @domain",), no_leak)
        expect("worktree-scope t@t", run(E, ev("git commit -m x", wt)), "deny", ("worktree scope",))
        expect("git -c user.email=t@t in a clean repo",
               run(E, ev("git -c user.email=t@t commit -m x", ok)), "deny", ("command scope",))
        expect("GIT_AUTHOR_EMAIL=t@t prefix",
               run(E, ev("GIT_AUTHOR_EMAIL=t@t git commit -m x", ok)), "deny", ("env scope",))
        expect("local name differs only", run(E, ev("git commit -m x", name_only)), "deny",
               ("user.name",))
        for name, cmd, cwd in [
            ("no local identity", "git commit -m x", ok),
            ("local equals global (case differs)", "git commit -m x", same),
            ("allow-listed in $CLAUDE_PLUGIN_DATA", "git commit -m x", allowed),
            ("allow-listed in ~/.config", "git commit -m x", allowed2),
            ("local t@t, rebase --abort", "git rebase --abort", t_repo),
            ("local t@t, git log", "git log --oneline", t_repo),
            ("local t@t, git commit only inside echo", 'echo "git commit"', t_repo),
            ("local t@t, git commit only in a heredoc body",
             "cat > run.sh <<'EOF'\ngit commit -m x\nEOF\nchmod +x run.sh", t_repo),
            ("non-repo dir", "git commit -m x", nonrepo),
        ]:
            expect(name, run(E, ev(cmd, cwd)), "silent")
        expect("no global identity to compare", run(
            E, ev("git commit -m x", t_repo), GIT_CONFIG_GLOBAL=str(E.home / "empty.gitconfig")), "silent")
        if E.calls() != before:
            fail("identity cases called gh %d times" % (E.calls() - before))

        # ── merge ────────────────────────────────────────────────────────────
        E.reset_cache()
        expect("smithy#45 shape: -R, no protection, automerge label",
               run(E, ev("gh pr merge 45 --auto --squash -R acme/unprotected", nonrepo)), "deny",
               ("acme/unprotected", "--add-label automerge", "INC-2026-10-004"))
        expect("smithy#45 shape, flags on a continuation line",
               run(E, ev("gh pr merge 45 \\\n  --auto --squash -R acme/unprotected", nonrepo)), "deny",
               ("acme/unprotected",))
        expect("unprotected, no label",run(E, ev("gh pr merge 3 --auto -R acme/nolabel", nonrepo)),
               "deny", ("gh pr checks", "without --auto"), ("--add-label",))
        expect("unprotected, deletion-only ruleset",
               run(E, ev("gh pr merge 3 --auto --repo=acme/deletiononly", nonrepo)), "deny")
        expect("repo from origin (t repo -> acme/unprotected)",
               run(E, ev("gh pr merge --auto", t_repo)), "deny", ("acme/unprotected",))
        expect("repo from PR URL",
               run(E, ev("gh pr merge https://github.com/acme/nolabel/pull/7 --auto", ok)), "deny",
               ("acme/nolabel",))
        expect("repo from GH_REPO prefix",
               run(E, ev("GH_REPO=acme/nolabel gh pr merge 7 --auto", ok)), "deny", ("acme/nolabel",))
        for name, cmd in [
            ("protected", "gh pr merge 1 --auto -R acme/protected"),
            ("merge-queue ruleset", "gh pr merge 1 --auto -R acme/queue"),
            ("required-status-checks ruleset", "gh pr merge 1 --auto -R acme/ruleset"),
        ]:
            expect(name, run(E, ev(cmd, nonrepo)), "silent")
        expect("repo from origin (protected)", run(E, ev("gh pr merge --auto --squash", ok)), "silent")
        ups = E.repo("ups", "https://github.com/acme/protected.git")
        E.git(ups, "remote", "add", "upstream", "https://github.com/acme/nolabel.git")
        expect("upstream before origin", run(E, ev("gh pr merge --auto", ups)), "deny", ("acme/nolabel",))
        E.git(ups, "config", "remote.origin.gh-resolved", "base")
        expect("gh-resolved remote wins", run(E, ev("gh pr merge --auto", ups)), "silent")
        expect("repo 500: warn, not deny", run(E, ev("gh pr merge 1 --auto -R acme/broken", nonrepo)),
               "warn", ("NOT blocked",))
        expect("rules 500 on unprotected: warn",
               run(E, ev("gh pr merge 1 --auto -R acme/rules500", nonrepo)), "warn", ("NOT blocked",))
        expect("no gh, no token: warn",
               run(E, ev("gh pr merge 1 --auto -R acme/other", nonrepo), path_dir=E.nogh), "warn",
               ("no gh CLI",))
        expect("non-GitHub remote: warn", run(E, ev("gh pr merge --auto", bare_t)), "warn",
               ("could not tell",))
        before = E.calls()
        for name, cmd in [
            ("gh pr merge without --auto", "gh pr merge 45 --squash -R acme/unprotected"),
            ("--disable-auto", "gh pr merge 45 --disable-auto -R acme/unprotected"),
            ("gh pr view", "gh pr view 45 -R acme/unprotected"),
        ]:
            expect(name, run(E, ev(cmd, nonrepo)), "silent")
        if E.calls() != before:
            fail("non --auto gh commands called the API %d times" % (E.calls() - before))

        # ── cache ────────────────────────────────────────────────────────────
        E.reset_cache()
        b0 = E.calls()
        run(E, ev("gh pr merge 1 --auto -R acme/protected", nonrepo))
        b1 = E.calls()
        expect("cached repeat", run(E, ev("gh pr merge 1 --auto -R acme/protected", nonrepo)), "silent")
        b2 = E.calls()
        cf = E.data / "commit-merge-guard" / "repos.json"
        c = json.loads(cf.read_text())
        c["acme/protected"]["t"] -= 25 * 3600
        cf.write_text(json.dumps(c))
        run(E, ev("gh pr merge 1 --auto -R acme/protected", nonrepo))
        b3 = E.calls()
        run(E, ev("gh pr merge 1 --auto -R acme/broken", nonrepo))
        b4 = E.calls()
        run(E, ev("gh pr merge 1 --auto -R acme/broken", nonrepo))
        b5 = E.calls()
        if not (b1 - b0 == 3 and b2 == b1 and b3 - b2 == 3 and b4 > b3 and b5 > b4):
            fail("cache: calls first=%d repeat=%d stale=%d broken=%d,%d (want 3,0,3,>0,>0)"
                 % (b1 - b0, b2 - b1, b3 - b2, b4 - b3, b5 - b4))
        else:
            print("ok   cache: first 3 calls, repeat 0, day-old 3, failure not cached")

        # ── quiet ────────────────────────────────────────────────────────────
        before = E.calls()
        for name, event in [
            ("ls", ev("ls -la", t_repo)),
            ("git status", ev("git status", t_repo)),
            ("grep for commit text", ev("grep -rn 'merge commit' docs", t_repo)),
            ("Read tool", ev("git commit", t_repo, tool="Read")),
            ("malformed JSON", '{"tool_name": "Bash", "tool_input": {"command": "git commit'),
            ("empty stdin", ""),
            ("non-object tool_input", json.dumps({"tool_name": "Bash", "tool_input": ["git commit"]})),
        ]:
            expect("quiet: " + name, run(E, event), "silent")
        if E.calls() != before:
            fail("quiet cases called gh")

        # ── wrapper fails open ───────────────────────────────────────────────
        for name, d in (("no python3", E.nopy), ("crashing python3", E.crash)):
            expect("fails open: " + name, run(E, ev("git commit -m x", t_repo), path_dir=d), "silent")

    if SLOWEST[0] > 2.0:
        fail("slowest run %.2fs > 2s: %r" % tuple(SLOWEST))
    else:
        print("ok   slowest run %.2fs" % SLOWEST[0])

    # ── wiring ───────────────────────────────────────────────────────────────
    try:
        pre = json.loads(HOOKS_JSON.read_text())["hooks"]["PreToolUse"]
    except (OSError, ValueError, KeyError):
        fail("hooks.json has no PreToolUse list")
        pre = []
    entries = [(e.get("matcher"), h.get("command")) for e in pre for h in e.get("hooks", [])]
    hits = [m for m, c in entries if c == CMD]
    if hits != ["Bash"]:
        fail("hooks.json: wrapper registered as %r, want exactly once under matcher 'Bash'" % hits)
    elif not pre or pre[0].get("matcher") != "Agent|Task":
        fail("hooks.json: the Agent|Task entry must stay first")
    else:
        print("ok   wired once under PreToolUse matcher Bash")

    print("%d failure(s)" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
