#!/usr/bin/env python3
# rivet: verifies REQ-COMMIT-MERGE-GUARD
# rivet: verifies REQ-GUARDS-050
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

0.50.0 (REQ-GUARDS-050), in new_rules():
  gate      --admin, REST PUT .../merge (gh api, curl) and GraphQL
            mergePullRequest deny with no API call; a direct merge asks on a
            red, pending or check-less head (by number, URL or current
            branch), is silent on green, warns when checks are unreadable;
  branch    update-branch --rebase, GraphQL REBASE and REST update_method=rebase
            deny; plain and REST update-branch deny on a merge-queue repo, pass
            on a non-queue repo, warn when rulesets are unreadable; a 0.49.0
            cache entry without the queue field is re-fetched;
  publish   v-tags, tag pushes, --tags, gh release create, cargo/npm publish
            ask off the origin tip, on a red tip and on unreadable checks, pass
            on a green tip; -l/-d/non-v tags/--dry-run/branch pushes are silent
            with no API call;
  signing   outside temp roots (a .hookfix-* dir in this checkout):
            --no-gpg-sign, -c gpgsign=false, tag --no-sign, config gpgsign
            false, config user.* writes (old and 2.46 syntax) and -c user.*
            deny; reads, --unset (also with a value pattern) and other keys
            pass; the same commands in a temp repo pass;
  text      a host-shaped value in -m, a heredoc message or gh pr create
            --body asks with masked values; a host in the cd/ssh part of the
            command, settings.local.json and a version do not; both allow-lists
            and temp repos are silent;
  admission a local stub of the fleet API: queued runs and pools arrive as one
            short context line; unset and unreachable are silent and logged;
  probe     signing-probe.sh is silent when email, key and gpgsign are set and
            prints one line under 400 chars naming what is missing otherwise.

Exit: 0 all hold · 1 a check failed · 2 cannot check (no bash or git, no hook).
"""

from __future__ import annotations

import json
import os
import pathlib
import http.server as http_server
import shutil
import subprocess
import sys
import tempfile
import threading
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
    repo("protrules500", PROT, http(500, {"message": "boom"}))
    # PR heads on acme/protected: 7 green, 8 red, 9 pending, 10 no checks, 12 checks 500
    for num, sha in ((7, "a" * 40), (8, "b" * 40), (9, "c" * 40), (10, "d" * 40), (12, "e" * 40)):
        f["repos/acme/protected/pulls/%d" % num] = http(200, {"number": num, "head": {"sha": sha}})
    f["repos/acme/protected/pulls?head=acme:feat-x&state=open&per_page=5"] = http(
        200, [{"number": 7, "head": {"sha": "a" * 40}}])
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
               if not k.startswith(("GIT_", "GH_", "GITHUB_", "CLAUDE_", "PULSEENGINE_"))
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

    def fixture(self, path, text):
        (self.stub / (path.replace("/", "__") + ".http")).write_text(text)

    def commit(self, d, msg="c"):
        self.git(d, "commit", "-q", "--allow-empty", "--no-gpg-sign", "-m", msg)
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, env=self.base(),
                           capture_output=True, text=True, check=True)
        return r.stdout.strip()


def checks_fixture(E, repo, sha, runs, statuses=(), runs_status=200):
    E.fixture("repos/%s/commits/%s/check-runs?per_page=100" % (repo, sha),
              http(runs_status, {"total_count": len(runs), "check_runs": list(runs)}
                   if runs_status == 200 else {"message": "boom"}))
    E.fixture("repos/%s/commits/%s/status" % (repo, sha),
              http(200, {"state": "success", "statuses": list(statuses)}))


GREEN = [{"name": "build", "status": "completed", "conclusion": "success"}]
RED = [{"name": "build", "status": "completed", "conclusion": "success"},
       {"name": "Clippy", "status": "completed", "conclusion": "failure"}]
PENDING = [{"name": "build", "status": "in_progress", "conclusion": None}]


class State(http_server.BaseHTTPRequestHandler):
    BODY = b""

    def do_GET(self):  # noqa: N802
        body = State.BODY if self.path == "/ci/api/state" else b"{}"
        self.send_response(200 if self.path == "/ci/api/state" else 404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")


def under_temp(p):
    rp = os.path.realpath(p)
    roots = list(TEMP_ROOTS) + [tempfile.gettempdir()]
    return any(rp == os.path.realpath(r) or rp.startswith(os.path.realpath(r) + "/") for r in roots)


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
    if keys == {"permissionDecision", "permissionDecisionReason"} \
            and hso["permissionDecision"] in ("deny", "ask"):
        return hso["permissionDecision"], hso["permissionDecisionReason"]
    if keys == {"additionalContext"}:
        return "warn", hso["additionalContext"]
    fail("%s: output carries %r (only deny/ask+reason or additionalContext allowed)"
         % (name, sorted(keys)))
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


def new_rules(E, nonrepo, ok, t_repo):
    """0.50.0: merge around the gate, update-branch, signing, tag/publish, text, admission."""
    for sha, runs in (("a" * 40, GREEN), ("b" * 40, RED), ("c" * 40, PENDING), ("d" * 40, [])):
        checks_fixture(E, "acme/protected", sha, runs)
    checks_fixture(E, "acme/protected", "e" * 40, GREEN, runs_status=500)

    # ── merge around the gate ────────────────────────────────────────────────
    E.reset_cache()
    before = E.calls()
    for name, cmd in [
        ("--admin", "gh pr merge 5 --admin --squash -R acme/protected"),
        ("--admin with --auto", "gh pr merge 5 --auto --admin -R acme/protected"),
        ("--admin, unbalanced quote (coarse path)", 'gh pr merge 5 --admin -t "oops'),
        ("REST merge via gh api -X PUT", "gh api -X PUT repos/acme/protected/pulls/5/merge"),
        ("REST merge via gh api --method=PUT", "gh api --method=PUT /repos/acme/protected/pulls/5/merge -f merge_method=squash"),
        ("GraphQL mergePullRequest",
         "gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: \"x\"}) { clientMutationId } }'"),
        ("curl -X PUT merge", "curl -s -X PUT -H 'Authorization: x' https://api.github.com/repos/acme/protected/pulls/5/merge"),
    ]:
        expect(name, run(E, ev(cmd, ok)), "deny", ("merge",), ("Do not add it yourself",))
    if E.calls() != before:
        fail("admin/API merge denies called the API %d times" % (E.calls() - before))
    expect("GET of the merge endpoint is a read", run(E, ev("gh api repos/acme/protected/pulls/5/merge", ok)),
           "silent")
    expect("direct merge, head green", run(E, ev("gh pr merge 7 --squash -R acme/protected", nonrepo)), "silent")
    expect("direct merge, head red", run(E, ev("gh pr merge 8 --squash -R acme/protected", nonrepo)), "ask",
           ("red", "Clippy", "name"))
    expect("direct merge, head pending", run(E, ev("gh pr merge 9 -R acme/protected", nonrepo)), "ask",
           ("pending", "build"))
    expect("direct merge, no checks", run(E, ev("gh pr merge 10 -R acme/protected", nonrepo)), "ask",
           ("none",))
    expect("direct merge by URL, head red",
           run(E, ev("gh pr merge https://github.com/acme/protected/pull/8 --merge", nonrepo)), "ask", ("red",))
    expect("direct merge, checks 500: warn", run(E, ev("gh pr merge 12 -R acme/protected", nonrepo)), "warn",
           ("NOT blocked",))
    feat = E.repo("feat", "https://github.com/acme/protected.git")
    E.commit(feat)
    E.git(feat, "checkout", "-q", "-b", "feat-x")
    expect("direct merge of the current branch's PR, green", run(E, ev("gh pr merge --squash", feat)), "silent")
    before = E.calls()
    expect("--auto on a guarded repo reads no checks", run(E, ev("gh pr merge 8 --auto -R acme/protected", nonrepo)),
           "silent")
    if E.calls() - before > 3:
        fail("--auto read checks: %d calls" % (E.calls() - before))

    # ── update-branch ────────────────────────────────────────────────────────
    E.reset_cache()
    before = E.calls()
    for name, cmd in [
        ("update-branch --rebase", "gh pr update-branch 5 --rebase -R acme/protected"),
        ("update-branch --rebase, coarse path", 'gh pr update-branch 5 --rebase "oops'),
        ("GraphQL updatePullRequestBranch REBASE",
         "gh api graphql -f query='mutation { updatePullRequestBranch(input: {pullRequestId: \"x\", updateMethod: REBASE}) { clientMutationId } }'"),
        ("REST update-branch update_method=rebase",
         "gh api -X PUT repos/acme/protected/pulls/5/update-branch -f update_method=rebase"),
    ]:
        expect(name, run(E, ev(cmd, ok)), "deny", ("signatures",))
    if E.calls() != before:
        fail("rebase denies called the API %d times" % (E.calls() - before))
    expect("plain update-branch on a merge-queue repo", run(E, ev("gh pr update-branch 5 -R acme/queue", nonrepo)),
           "deny", ("merge queue", "acme/queue"))
    expect("REST update-branch on a merge-queue repo",
           run(E, ev("gh api -X PUT repos/acme/queue/pulls/5/update-branch", nonrepo)), "deny", ("merge queue",))
    expect("plain update-branch on a strict non-queue repo",
           run(E, ev("gh pr update-branch 5 -R acme/protected", nonrepo)), "silent")
    expect("GraphQL updatePullRequestBranch MERGE, repo from origin (no queue)",
           run(E, ev("gh api graphql -f query='mutation { updatePullRequestBranch(input: {pullRequestId: \"x\"}) { clientMutationId } }'", ok)),
           "silent")
    expect("plain update-branch, rulesets unreadable: warn",
           run(E, ev("gh pr update-branch 5 -R acme/protrules500", nonrepo)), "warn", ("NOT blocked",))
    cf = E.data / "commit-merge-guard" / "repos.json"
    cf.write_text(json.dumps({"acme/queue": {"guarded": True, "branch": "main", "automerge_label": False,
                                             "t": time.time()}}))
    expect("0.49.0 cache entry (no queue field) is re-fetched",
           run(E, ev("gh pr update-branch 5 -R acme/queue", nonrepo)), "deny", ("merge queue",))

    # ── tag and publish only from green main ─────────────────────────────────
    rel = E.repo("rel", "https://github.com/acme/green.git")
    tip = E.commit(rel)
    E.git(rel, "update-ref", "refs/remotes/origin/main", tip)
    checks_fixture(E, "acme/green", tip, GREEN)
    ahead = E.repo("ahead", "https://github.com/acme/green.git")
    base_sha = E.commit(ahead)
    E.git(ahead, "update-ref", "refs/remotes/origin/main", base_sha)
    E.commit(ahead, "local only")
    red = E.repo("relred", "https://github.com/acme/redrel.git")
    rtip = E.commit(red)
    E.git(red, "update-ref", "refs/remotes/origin/main", rtip)
    checks_fixture(E, "acme/redrel", rtip, RED)
    broken = E.repo("relbroken", "https://github.com/acme/brokenrel.git")
    btip = E.commit(broken)
    E.git(broken, "update-ref", "refs/remotes/origin/main", btip)
    checks_fixture(E, "acme/brokenrel", btip, GREEN, runs_status=500)
    for name, cmd in [
        ("git tag v1.2.3 on green origin tip", "git tag v1.2.3"),
        ("git tag -a v1.2.3 -m on green origin tip", "git tag -a v1.2.3 -m 'release v1.2.3'"),
        ("git push origin v1.2.3 on green tip", "git push origin v1.2.3"),
        ("gh release create on green tip", "gh release create v1.2.3 --notes x"),
        ("cargo publish on green tip", "cargo publish -p foo"),
    ]:
        expect(name, run(E, ev(cmd, rel)), "silent")
    before = E.calls()
    for name, cmd in [
        ("git tag -l", "git tag -l 'v*'"), ("git tag -d", "git tag -d v1.2.3"),
        ("non-v tag", "git tag build-5"), ("cargo publish --dry-run", "cargo publish --dry-run"),
        ("npm publish --dry-run", "npm publish --dry-run"), ("git push of a branch", "git push origin feat-x"),
        ("git push --delete of a tag", "git push --delete origin v1.2.3"),
    ]:
        expect(name, run(E, ev(cmd, ahead)), "silent")
    if E.calls() != before:
        fail("non-publishing commands called the API %d times" % (E.calls() - before))
    for name, cmd in [
        ("git tag v1.2.3 ahead of origin", "git tag v1.2.3"),
        ("git push origin --tags ahead of origin", "git push origin --tags"),
        ("cargo publish ahead of origin", "cargo publish"),
        ("npm publish ahead of origin", "npm publish --access public"),
        ("gh release create ahead of origin", "gh release create v1.2.3 --generate-notes"),
    ]:
        expect(name, run(E, ev(cmd, ahead)), "ask", ("not the tip of origin/main",))
    expect("git tag v1.2.3 on a red origin tip", run(E, ev("git tag v1.2.3", red)), "ask", ("red", "Clippy"))
    expect("git push of refs/tags/v2 on a red tip", run(E, ev("git push origin refs/tags/v2.0.0", red)), "ask",
           ("red",))
    expect("checks unreadable: ask, not green", run(E, ev("git tag v1.2.3", broken)), "ask",
           ("could not be read",))
    expect("gh release create -R outside a checkout", run(E, ev("gh release create v1 -R acme/green", nonrepo)),
           "ask", ("not run inside a git checkout",))

    # ── signing and identity (outside temp dirs) ─────────────────────────────
    nt_root = pathlib.Path(tempfile.mkdtemp(prefix=".hookfix-", dir=str(ROOT)))
    try:
        nt = nt_root / "nt"
        nt.mkdir()
        E.git(nt, "init", "-q")
        if under_temp(str(nt)):
            fail("cannot place a non-temp fixture: %s is under a temp root" % ROOT)
            return
        no_leak_sign = ("Do not add it yourself",)
        for name, cmd, cwd in [
            ("git commit --no-gpg-sign", "git commit --no-gpg-sign -m x", nt),
            ("git -c commit.gpgsign=false commit", "git -c commit.gpgsign=false commit -m x", nt),
            ("git -c commit.gpgSign=no (case)", "git -c commit.gpgSign=no commit -m x", nt),
            ("git rebase --no-gpg-sign", "git rebase --no-gpg-sign main", nt),
            ("git tag --no-sign", "git tag --no-sign -a v9 -m x", nt),
            ("git -C non-temp from a temp cwd", "git -C %s commit --no-gpg-sign -m x" % nt, nonrepo),
            ("cd non-temp && commit --no-gpg-sign", "cd %s && git commit --no-gpg-sign -m x" % nt, nonrepo),
            ("git config commit.gpgsign false", "git config commit.gpgsign false", nt),
            ("--no-gpg-sign, unbalanced quote (coarse)", 'git commit --no-gpg-sign -m "oops', nt),
        ]:
            expect("signing: " + name, run(E, ev(cmd, cwd)), "deny", ("unsigned", "temp dir"), no_leak_sign)
        for name, cmd in [
            ("git config user.email", "git config user.email t@t"),
            ("git config --global user.name", "git config --global user.name 'X Y'"),
            ("git config --local user.email", "git config --local user.email t@t"),
            ("git config set user.email (2.46 syntax)", "git config set user.email t@t"),
            ("git -c user.email= on any subcommand", "git -c user.email=a@b log -1"),
            ("git -c user.name= on commit", "git -c user.name=t commit -m x"),
        ]:
            expect("identity: " + name, run(E, ev(cmd, nt)), "deny", ("identity", "ask the owner"))
        for name, cmd in [
            ("git config --get user.email", "git config --get user.email"),
            ("git config user.email (read)", "git config user.email"),
            ("git config --local --unset user.email (0.49.0's remedy)", "git config --local --unset user.email"),
            ("git config --unset-all user.name", "git config --unset-all user.name"),
            ("git config --unset with a value pattern", "git config --unset user.email t@t"),
            ("git config --get-regexp with a value pattern", "git config --get-regexp user. t@t"),
            ("git config get user.email", "git config get user.email"),
            ("git config unset user.email", "git config unset user.email"),
            ("git config --list", "git config --list --show-origin"),
            ("git config --show-scope --get", "git config --show-scope --get user.email"),
            ("git config of another key", "git config core.editor vim"),
            ("git -c commit.gpgsign=true commit", "git -c commit.gpgsign=true commit -m x"),
            ("--no-gpg-sign as the -m message", "git commit -m --no-gpg-sign"),
        ]:
            expect("signing/identity allowed: " + name, run(E, ev(cmd, nt)), "silent")
        for name, cmd in [
            ("temp: git commit --no-gpg-sign", "git commit --no-gpg-sign -m x"),
            ("temp: git config user.email", "git config user.email t@t"),
            ("temp: -c commit.gpgsign=false", "git -c commit.gpgsign=false commit -m x"),
        ]:
            expect(name, run(E, ev(cmd, ok)), "silent")

        # ── host-shaped values in commit and PR text ─────────────────────────
        heredoc = ("git commit -m \"$(cat <<'EOF'\nfix: deploy\n\nRuns on 192.168.10.20 now.\nEOF\n)\"")
        for name, cmd, want in [
            ("-m with a .local host", "git commit -m 'deploy to buildbox.local'", ("mdns/lan", "bu***cal")),
            ("heredoc message with an RFC 1918 address", heredoc, ("ipv4",)),
            ("-m with a ULA address", "git commit -m 'bind fd12:3456:789a::1'", ("ula",)),
            ("-m with a /Volumes path", "git commit -m 'data in /Volumes/Data/x'", ("volumes",)),
            ("-m with the owner's home path", "git commit -m 'see %s/notes'" % E.home, ("home",)),
            ("gh pr create --body with a host", "gh pr create --title t --body 'runs on ci.lan'", ("PR title/body",)),
        ]:
            expect("text: " + name, run(E, ev(cmd, nt)), "ask", want + ("owner",), ("buildbox.local",))
        for name, cmd in [
            ("clean message", "git commit -m 'fix: nothing private here'"),
            ("host only in the cd path, not the message",
             "cd %s && ssh buildbox.local true && git commit -m clean" % nt),
            ("settings.local.json and *.local are not hosts", "git commit -m 'edit settings.local.json, glob *.local'"),
            ("a version number is not an address", "git commit -m 'bump to 10.2.3'"),
        ]:
            expect("text silent: " + name, run(E, ev(cmd, nt)), "silent")
        (nt / ".private-hostname-allow").write_text("# fixture hosts\n*.local\n")
        expect("text: repo allow-list drops *.local", run(E, ev("git commit -m 'deploy to buildbox.local'", nt)),
               "silent")
        (nt / ".private-hostname-allow").unlink()
        cfg = E.home / ".config" / "pulseengine-claude"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "private-hostname-allow").write_text("buildbox.local\n")
        expect("text: user allow-list drops a value", run(E, ev("git commit -m 'deploy to buildbox.local'", nt)),
               "silent")
        (cfg / "private-hostname-allow").unlink()
        expect("text: temp repo is exempt", run(E, ev("git commit -m 'deploy to buildbox.local'", ok)), "silent")
    finally:
        shutil.rmtree(str(nt_root), ignore_errors=True)

    # ── PR admission advice ──────────────────────────────────────────────────
    State.BODY = json.dumps({"snapshot": {"queue": {
        "queued": [{"repo": "protected", "run_id": 1}, {"repo": "protected", "run_id": 1},
                   {"repo": "protected", "run_id": 2}, {"repo": "other", "run_id": 3}],
        "queued_complete": True,
        "pools": {"light": {"jobs_queued": 6}, "rust-cpu": {"jobs_queued": 25}}}}}).encode()
    srv = http_server.HTTPServer(("127.0.0.1", 0), State)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    log = E.data / "commit-merge-guard" / "admission.log"
    try:
        url = "http://127.0.0.1:%d/ci" % srv.server_address[1]
        expect("admission: queued runs and pools as context",
               run(E, ev("gh pr create --title t --body b", ok), PULSEENGINE_CI_STATUS_URL=url), "warn",
               ("acme/protected has 2 queued run(s)", "light 6 jobs", "rust-cpu 25 jobs", "batch"))
        r = run(E, ev("gh pr create --fill", ok), PULSEENGINE_CI_STATUS_URL=url)
        got, text = classify("admission: advice is short", r)
        if got == "warn" and len(text) > 600:
            fail("admission advice is %d chars (> 600)" % len(text))
        expect("admission: URL unset is silent", run(E, ev("gh pr create --fill", ok)), "silent")
        expect("admission: unreachable is silent",
               run(E, ev("gh pr create --fill", ok), PULSEENGINE_CI_STATUS_URL="http://127.0.0.1:9/ci"), "silent")
        lines = log.read_text().splitlines() if log.is_file() else []
        if not any("unset" in x for x in lines) or not any(x.split(" ", 1)[1].startswith("fail:") for x in lines):
            fail("admission.log does not record the unset and unreachable cases: %r" % lines[-4:])
        else:
            print("ok   admission: unset and unreachable are logged")
    finally:
        srv.shutdown()

    # ── SessionStart signing probe ───────────────────────────────────────────
    probe = HOOKS / "signing-probe.sh"
    full = "[user]\n\tname = N\n\temail = n@example.com\n\tsigningkey = ~/.ssh/k.pub\n[commit]\n\tgpgsign = true\n"
    for name, cfg, want in [
        ("all set", full, None),
        ("no email", full.replace("\temail = n@example.com\n", ""), "user.email"),
        ("no signing key", full.replace("\tsigningkey = ~/.ssh/k.pub\n", ""), "user.signingkey"),
        ("gpgsign false", full.replace("gpgsign = true", "gpgsign = false"), "commit.gpgsign=true"),
        ("nothing set", "", "user.email"),
    ]:
        gc = E.home / ("probe-%s.gitconfig" % name.replace(" ", "-"))
        gc.write_text(cfg)
        jq = shutil.which("jq")
        pdir = E.links
        if jq and not (pdir / "jq").exists():
            (pdir / "jq").symlink_to(jq)
        r = subprocess.run(["bash", str(probe)], capture_output=True, text=True, timeout=30,
                           env=E.base(GIT_CONFIG_GLOBAL=str(gc)))
        if r.returncode != 0 or r.stderr:
            fail("signing probe %s: exit %d stderr %r" % (name, r.returncode, r.stderr[:200]))
            continue
        if want is None:
            if r.stdout:
                fail("signing probe %s: expected silence, got %r" % (name, r.stdout[:200]))
            else:
                print("ok   signing probe: %s is silent" % name)
            continue
        if not jq:  # the probe is silent without jq; a skipped case is not a pass
            fail("signing probe %s: cannot check, no jq on PATH" % name)
            continue
        try:
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        except (ValueError, KeyError, TypeError):
            fail("signing probe %s: not SessionStart JSON: %r" % (name, r.stdout[:200]))
            continue
        if want not in ctx or "\n" in ctx or len(ctx) > 400:
            fail("signing probe %s: want one line under 400 chars naming %s, got %r" % (name, want, ctx))
        else:
            print("ok   signing probe: %s -> one line (%d chars)" % (name, len(ctx)))
    try:
        ss = json.loads(HOOKS_JSON.read_text())["hooks"]["SessionStart"]
        cmds = [h.get("command") for e in ss for h in e.get("hooks", [])]
    except (OSError, ValueError, KeyError):
        cmds = []
    if cmds.count("bash ${CLAUDE_PLUGIN_ROOT}/hooks/signing-probe.sh") != 1:
        fail("hooks.json: signing-probe.sh not wired once under SessionStart")
    else:
        print("ok   signing probe wired once under SessionStart")


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
            ("--disable-auto", "gh pr merge 45 --disable-auto -R acme/unprotected"),
            ("gh pr view", "gh pr view 45 -R acme/unprotected"),
        ]:
            expect(name, run(E, ev(cmd, nonrepo)), "silent")
        if E.calls() != before:
            fail("non --auto gh commands called the API %d times" % (E.calls() - before))
        expect("direct merge, PR head unreadable: warn",
               run(E, ev("gh pr merge 45 --squash -R acme/unprotected", nonrepo)), "warn",
               ("NOT checked",))

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

        new_rules(E, nonrepo, ok, t_repo)

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
