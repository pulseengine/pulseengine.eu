#!/usr/bin/env python3
"""PreToolUse(Bash) hook (pulseengine-claude): two mechanical guards.

1. Stray commit identity (INC-2026-10-006). A test left a one-letter repo-local
   git identity in a synth clone, and PR-branch commits were authored under it
   for two weeks; GitHub showed them unverified. Before a commit-making git
   command (commit, cherry-pick, revert, am, merge, rebase; with -C, -c, chains,
   cd, bash -c and heredoc messages), the effective user.email and user.name are
   resolved with `git config --show-scope`. If the winning value comes from the
   repo (local or worktree scope), from `git -c`, or from a GIT_AUTHOR_* /
   GIT_COMMITTER_* prefix, and differs from the global value (read with
   --includes), the call is DENIED, unless the effective email is on the
   owner's allow-list. A value whose winning scope is global or system is never
   flagged, so an includeIf identity in the global config passes. With no
   global value to compare against, nothing is flagged.

   Allow-list: one address per line (# comments) in
   $CLAUDE_PLUGIN_DATA/commit-identity-allow or
   ~/.config/pulseengine-claude/commit-identity-allow. Only the owner edits it;
   the deny reason tells the agent so.

2. Auto-merge that cannot wait (INC-2026-10-004, smithy#45). `gh pr merge
   --auto` on a repo whose default branch has no branch protection and no
   ruleset with required status checks or a merge queue merges immediately,
   before CI. The target repo comes from -R/--repo, a PR URL argument, GH_REPO,
   the gh-resolved remote, then upstream, github, origin. The answer comes from
   the GitHub API (gh api, else urllib with GH_TOKEN/GITHUB_TOKEN) and is cached
   per repo for a day under $CLAUDE_PLUGIN_DATA/commit-merge-guard/. A 403
   "Upgrade to GitHub Pro" on the rules endpoint (a private repo on the free
   plan) is a definitive "no rulesets". Any other API failure fails OPEN: the
   call goes ahead with a warning in additionalContext, never a silent block.

3. Merge around the gate (0.50.0). `gh pr merge --admin`, the REST merge
   endpoint (`gh api -X PUT .../pulls/N/merge`, or curl) and the GraphQL
   mergePullRequest mutation are denied everywhere: they skip the queue and
   the checks. A direct `gh pr merge` (no --auto) asks when the PR head's
   checks are red, pending or absent; --auto is left to rule 2, since a
   guarded repo makes it wait. Check state is read live, never cached.

4. update-branch (0.50.0). `gh pr update-branch --rebase` and the GraphQL
   updatePullRequestBranch with REBASE are denied everywhere: a server-side
   rebase drops the commit signatures that main requires. The plain form,
   and the REST update-branch endpoint, are denied on a repo with a merge
   queue (the queue tests against the latest main anyway) and allowed
   elsewhere, so strict non-queue repos can still be brought up to date.

5. Signing and identity (0.50.0). Outside temp dirs (TMPDIR, /tmp,
   /private/tmp, /var/folders, compared by realpath): deny `--no-gpg-sign`
   (and `git tag --no-sign`), `-c commit.gpgsign=false` / tag.gpgsign, `-c
   user.email=` / `-c user.name=`, and a `git config` that WRITES user.* or
   turns gpgsign off. Reads (--get, --list, `git config get`) and --unset,
   which rule 1's remedy uses, pass.

6. Tag and publish from green main (0.50.0). `git tag v<digit>...`, `git push`
   of such a tag or of --tags, `gh release create`, `cargo publish` and
   `npm`/`pnpm publish` (not --dry-run) ask unless the commit is the tip of
   origin/<default branch> locally AND its checks are green. An API failure
   here asks too: these are irreversible, so "could not confirm" is not green.

7. Text checks (0.50.0). A commit message (-m values and heredoc bodies) and
   `gh pr create|edit` --title/--body are scanned with private_hosts.py; a
   host-shaped value asks. On `gh pr create` the fleet's ci-status API
   ($PULSEENGINE_CI_STATUS_URL, CA in $PULSEENGINE_CI_STATUS_CACERT) is asked
   for the repo's queued runs and the advice is added as context; unset or
   unreachable is logged under the state dir and says nothing.

Outputs: a deny (hookSpecificOutput.permissionDecision "deny" with a reason),
an ask (permissionDecision "ask", which in a headless `claude -p` session
refuses the call like a deny), a warning or advice (additionalContext only),
or nothing. Never an approving decision, which would skip the user's
permission flow. Always exit 0; an exception prints nothing.

Python 3.9+, stdlib only. Network only for the gh rules above.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import private_hosts as ph  # noqa: E402

COMMIT_SUBS = {"commit", "cherry-pick", "revert", "am", "merge", "rebase"}
NO_COMMIT_FLAGS = {"--abort", "--quit", "--skip", "--show-current-patch", "-h", "--help"}
FLAGGED_SCOPES = {"local", "worktree", "command", "env"}
GUARD_RULES = {"required_status_checks", "merge_queue"}
CACHE_TTL_S = 24 * 3600
GIT_TIMEOUT_S = 3
API_TIMEOUT_S = 4
DEADLINE_S = 12
SEPARATORS = {";", ";;", "&", "&&", "|", "||", "|&", "(", ")", "\n"}
WRAPPERS = {"command", "builtin", "exec", "nohup", "time", "nice"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
GH_VALUE_FLAGS = {"-b", "--body", "-F", "--body-file", "-t", "--subject",
                  "-A", "--author-email", "--match-head-commit"}
GH_CREATE_VALUE_FLAGS = GH_VALUE_FLAGS | {
    "--title", "-H", "--head", "-B", "--base", "-T", "--template", "-l", "--label", "-a",
    "--assignee", "-r", "--reviewer", "-m", "--milestone", "-p", "--project", "-n", "--notes",
    "--notes-file", "--target", "--add-label", "--remove-label", "--notes-start-tag"}
GH_API_VALUE_FLAGS = {"-X", "--method", "-f", "--raw-field", "-F", "--field", "-H", "--header",
                      "--input", "-q", "--jq", "-t", "--template", "--hostname", "--cache",
                      "-p", "--preview"}
GIT_MSG_FLAGS = {"-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c",
                 "--reedit-message", "--fixup", "--squash"}
GPG_KEYS = {"commit.gpgsign", "tag.gpgsign"}
FALSY = {"false", "no", "off", "0"}
CHECK_BAD = {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
CACHE_V = 2
ALLOW_NAME = "commit-identity-allow"

START = time.monotonic()


def out_of_time():
    return time.monotonic() - START > DEADLINE_S


# ── command parsing ──────────────────────────────────────────────────────────

def strip_heredocs(cmd):
    """Drop heredoc bodies, keeping the line that opens each one."""
    lines = cmd.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for _, delim in re.findall(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line):
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            i += 1
    return "\n".join(out)


def join_continuations(cmd):
    """Backslash-newline is a line continuation, not a command separator."""
    return re.sub(r"\\\r?\n", " ", cmd)


def tokenize(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def segments(tokens):
    seg, skip_next = [], False
    for t in tokens:
        if skip_next:
            skip_next = False
            continue
        if t and all(c in ";&|()<>\n" for c in t):
            if "<" in t or ">" in t:
                skip_next = True
                continue
            if seg:
                yield seg
            seg = []
            continue
        seg.append(t)
    if seg:
        yield seg


class Finding:
    def __init__(self):
        self.deny = None
        self.asks = []
        self.warnings = []
        self.notes = []
        self.commit_dirs = []
        self.pr_text = []        # (repo spec, cwd) of gh pr create|edit
        self.admission = []      # (repo spec, cwd) of gh pr create


def walk(cmd, cwd, env, found, depth=0):
    if depth > 3 or found.deny:
        return
    cmd = join_continuations(strip_heredocs(cmd))
    try:
        segs = list(segments(tokenize(cmd)))
    except ValueError:
        coarse(cmd, cwd, env, found)
        return
    for words in segs:
        if found.deny:
            return
        local_env = dict(env)
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            k, _, v = words[0].partition("=")
            local_env[k] = v
            words = words[1:]
        while words and (words[0] in WRAPPERS or words[0] in ("env", "sudo")):
            w = words[0]
            words = words[1:]
            while words and (words[0].startswith("-") or (w == "env" and "=" in words[0])):
                if w == "env" and "=" in words[0] and not words[0].startswith("-"):
                    k, _, v = words[0].partition("=")
                    local_env[k] = v
                words = words[1:]
        if not words:
            continue
        prog = os.path.basename(words[0])
        args = words[1:]
        if prog in ("cd", "pushd"):
            target = args[0] if args and args[0] != "--" else (args[1] if len(args) > 1 else "~")
            if target != "-":
                cwd = os.path.normpath(os.path.join(cwd, os.path.expanduser(target)))
        elif prog in SHELLS and "-c" in args:
            i = args.index("-c")
            if i + 1 < len(args):
                walk(args[i + 1], cwd, local_env, found, depth + 1)
        elif prog == "eval":
            walk(" ".join(args), cwd, local_env, found, depth + 1)
        elif prog == "git":
            git_call(args, cwd, local_env, found)
        elif prog == "gh":
            gh_call(args, cwd, local_env, found)
        elif prog == "cargo":
            pos = [a for a in args if not a.startswith(("-", "+"))]
            if pos[:1] == ["publish"] and "--dry-run" not in args and "-n" not in args:
                publish_check("cargo publish", cwd, local_env, found)
        elif prog in ("npm", "pnpm"):
            pos = [a for a in args if not a.startswith("-")]
            if pos[:1] == ["publish"] and "--dry-run" not in args:
                publish_check("%s publish" % prog, cwd, local_env, found)
        elif prog == "curl":
            text = " ".join(args)
            if re.search(r"\bmergePullRequest\b", text) or (
                    re.search(r"/pulls/\d+/merge\b", text)
                    and re.search(r"(?:-X\s*|--request[= ]\s*)PUT\b", text)):
                found.deny = DENY_API_MERGE


def coarse(cmd, cwd, env, found):
    """Tokenizing failed: decide on a regex scan rather than stay silent."""
    m = re.search(r"\bgit\b((?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*)\s+(" +
                  "|".join(re.escape(s) for s in COMMIT_SUBS) + r")\b", cmd)
    if m:
        opts = []
        for flag, val in re.findall(r"(-[Cc])\s+(\S+)", m.group(1)):
            opts += [flag, val.strip("'\"")]
        check_identity(opts, cwd, env, found)
    if not found.deny and re.search(r"\bgh\s+pr\s+merge\b[^\n;&|]*--admin\b", cmd):
        found.deny = DENY_ADMIN
    if not found.deny and re.search(r"\bgh\s+pr\s+update-branch\b[^\n;&|]*--rebase\b", cmd):
        found.deny = DENY_REBASE
    if not found.deny and re.search(r"\bgit\b[^\n;&|]*\s--no-gpg-sign\b", cmd) \
            and not ph.in_temp(cwd):
        found.deny = DENY_SIGN % "--no-gpg-sign"
    if not found.deny and re.search(r"\bgh\s+pr\s+merge\b[^\n;&|]*--auto\b", cmd):
        r = re.search(r"(?:-R|--repo)[= ]\s*(\S+)", cmd)
        merge_check(r.group(1).strip("'\"") if r else None, cwd, env, found)


# ── rule 1: commit identity ──────────────────────────────────────────────────

def git_call(args, cwd, env, found):
    opts, i = [], 0
    while i < len(args):
        t = args[i]
        if t in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(args):
            opts += [t, args[i + 1]]
            i += 2
            continue
        if t.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
            opts.append(t)
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        break
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1:]
    gdir = cwd
    cvals = []
    for j in range(0, len(opts) - 1):
        if opts[j] == "-C":
            gdir = os.path.normpath(os.path.join(gdir, os.path.expanduser(opts[j + 1])))
        elif opts[j] == "-c":
            cvals.append(opts[j + 1])
    signing_check(cvals, sub, rest, gdir, found)
    if found.deny:
        return
    if sub == "tag":
        tag_call(rest, gdir, env, found)
    elif sub == "push":
        push_call(rest, gdir, env, found)
    if sub not in COMMIT_SUBS:
        return
    if NO_COMMIT_FLAGS & set(rest):
        return
    if sub == "commit":
        found.commit_dirs.append(gdir)
    check_identity(opts, cwd, env, found)


# ── rule 5: signing and identity ─────────────────────────────────────────────

def strip_values(args, flags):
    """args without the values of value-taking flags (a -m message is not a flag)."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in flags:
            skip = True
            continue
        out.append(a)
    return out


def signing_check(cvals, sub, rest, gdir, found):
    if ph.in_temp(gdir):
        return
    for kv in cvals:
        k, eq, v = kv.partition("=")
        k = k.strip().lower()
        if k in GPG_KEYS and eq and v.strip().lower() in FALSY:
            found.deny = DENY_SIGN % ("-c " + kv)
            return
        if k in ("user.email", "user.name"):
            found.deny = DENY_IDENT % ("-c " + k + "=...")
            return
    flags = strip_values(rest, GIT_MSG_FLAGS)
    if "--no-gpg-sign" in flags or (sub == "tag" and "--no-sign" in flags):
        found.deny = DENY_SIGN % ("git %s --no-gpg-sign" % sub if "--no-gpg-sign" in flags
                                  else "git tag --no-sign")
        return
    if sub == "config":
        hit = config_write(rest)
        if hit == "ident":
            found.deny = DENY_IDENT % "git config user.*"
        elif hit == "sign":
            found.deny = DENY_SIGN % "git config commit.gpgsign false"


CONFIG_VALUE_OPTS = {"--file", "-f", "--blob", "--type", "--default", "--comment", "--value"}
CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color",
                "--get-colorbool", "--list", "-l", "--unset", "--unset-all",
                "--remove-section", "--rename-section", "--edit", "-e"}
CONFIG_SAFE_SUBS = {"get", "list", "unset", "remove-section", "rename-section", "edit"}


def config_write(args):
    """'ident' / 'sign' when `git config <args>` writes user.* / turns gpgsign off."""
    pos, flags, i = [], set(), 0
    while i < len(args):
        t = args[i]
        if t in CONFIG_VALUE_OPTS:
            i += 2
            continue
        if t.startswith("-"):
            flags.add(t.split("=", 1)[0])
        else:
            pos.append(t)
        i += 1
    if pos and pos[0] in CONFIG_SAFE_SUBS:
        return None
    if pos and pos[0] == "set":
        pos = pos[1:]
        write = len(pos) >= 1
    elif flags & CONFIG_READS:
        return None
    else:
        write = len(pos) >= 2 or bool(flags & {"--add", "--replace-all"})
    if not write or not pos:
        return None
    key = pos[0].lower()
    if key.startswith("user."):
        return "ident"
    if key in GPG_KEYS and len(pos) > 1 and pos[1].strip().lower() in FALSY:
        return "sign"
    return None


DENY_SIGN = (
    "pulseengine-claude commit-merge-guard: `%s` would make an unsigned commit or tag outside "
    "a temp dir. main requires signed, verified commits, and GitHub refuses an unsigned one only "
    "at merge, after CI has run. Commit signed: drop the flag. If signing fails, report the "
    "error to the owner instead of working around it. Throwaway repos under TMPDIR, /tmp or "
    "/var/folders are exempt.")
DENY_IDENT = (
    "pulseengine-claude commit-merge-guard: `%s` would set a commit identity outside a temp dir. "
    "The global identity is the one GitHub verifies (INC-2026-10-006). Do not set one; if a repo "
    "needs a different identity, ask the owner. Reads (--get, --list, `git config get`) and "
    "--unset pass, and throwaway repos under TMPDIR, /tmp or /var/folders are exempt.")


# ── rule 6: tag and publish only from green main ─────────────────────────────

TAG_NOT_CREATE = {"-l", "--list", "-d", "--delete", "-v", "--verify", "--contains",
                  "--no-contains", "--points-at", "--merged", "--no-merged", "-n"}
TAG_VALUE_FLAGS = {"-m", "--message", "-F", "--file", "-u", "--local-user", "--cleanup",
                   "--sort", "--format", "--color", "--trailer"}
VTAG = re.compile(r"^v\d")


def tag_call(rest, gdir, env, found):
    if TAG_NOT_CREATE & {a.split("=", 1)[0] for a in rest}:
        return
    pos = [a for a in strip_values(rest, TAG_VALUE_FLAGS) if not a.startswith("-")]
    if not pos or not VTAG.match(pos[0]):
        return
    publish_check("git tag %s" % pos[0], gdir, env, found, target=pos[1] if len(pos) > 1 else None)


def push_call(rest, gdir, env, found):
    flags = {a.split("=", 1)[0] for a in rest if a.startswith("-")}
    if flags & {"-d", "--delete", "-n", "--dry-run"}:
        return
    pos = [a for a in strip_values(rest, {"--repo", "-o", "--push-option", "--receive-pack",
                                          "--exec"}) if not a.startswith("-")]
    refs = pos[1:]
    tags = []
    for r in refs:
        src = r.lstrip("+").split(":", 1)[0]
        if src.startswith("refs/tags/"):
            src = src[len("refs/tags/"):]
        if src and VTAG.match(src):
            tags.append(src)
    if tags:
        publish_check("git push of tag %s" % tags[0], gdir, env, found, target=tags[0])
    elif flags & {"--tags", "--follow-tags"}:
        publish_check("git push --tags", gdir, env, found)


def short(sha):
    return (sha or "?")[:9]


def publish_check(what, cwd, env, found, target=None, spec=None):
    if found.deny:
        return
    lead = "pulseengine-claude commit-merge-guard: `%s` is irreversible, and " % what
    tail = (" Tag and publish only from the tip of the default branch with green checks: "
            "`git fetch origin`, check out origin's default branch, wait for its checks "
            "(ci-status), then tag. If this release really should come from here, the owner "
            "approves this call.")
    rc, top = run_git(["rev-parse", "--show-toplevel"], cwd) if os.path.isdir(cwd) else (None, "")
    if rc != 0 or not top:
        found.asks.append(lead + "it does not run inside a git checkout, so the commit it "
                          "publishes could not be checked against origin's default branch." + tail)
        return
    rev = target or "HEAD"
    rc, sha = run_git(["rev-parse", "--verify", "-q", rev + "^{commit}"], top)
    if rc != 0 or not sha:
        if target:  # a tag not created yet (gh release create v1): it will point at HEAD
            rc, sha = run_git(["rev-parse", "--verify", "-q", "HEAD^{commit}"], top)
        if rc != 0 or not sha:
            found.asks.append(lead + "the commit it publishes could not be resolved." + tail)
            return
    rc, ref = run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], top)
    candidates = [ref] if rc == 0 and ref else ["origin/main", "origin/master"]
    tip = None
    for c in candidates:
        rc, out = run_git(["rev-parse", "--verify", "-q", c + "^{commit}"], top)
        if rc == 0 and out:
            ref, tip = c, out
            break
    if not tip:
        found.asks.append(lead + "this checkout has no origin default branch to compare "
                          "against." + tail)
        return
    if sha != tip:
        found.asks.append(lead + "it publishes %s, which is not the tip of %s (%s)."
                          % (short(sha), ref, short(tip)) + tail)
        return
    repo = parse_repo(spec) if spec else repo_from_cwd(top, env)
    if not repo:
        found.asks.append(lead + "the GitHub repo could not be told, so the checks on %s "
                          "could not be read." % short(sha) + tail)
        return
    state, detail = checks_state(repo, sha)
    if state is None:
        found.asks.append(lead + "the checks on %s could not be read (%s), so they are not "
                          "known to be green." % (short(sha), detail) + tail)
    elif state != "green":
        found.asks.append(lead + "the checks on %s (the tip of %s) are %s%s."
                          % (short(sha), ref, state, detail) + tail)


def checks_state(repo, sha):
    """('green'|'red'|'pending'|'none', detail) or (None, why). Never cached."""
    st, body = api_get("repos/%s/commits/%s/check-runs?per_page=100" % (repo, sha))
    if st != 200:
        return None, body if st is None else "check-runs answered %s" % st
    st2, body2 = api_get("repos/%s/commits/%s/status" % (repo, sha))
    if st2 != 200:
        return None, body2 if st2 is None else "the status endpoint answered %s" % st2
    try:
        runs = json.loads(body).get("check_runs") or []
        statuses = json.loads(body2).get("statuses") or []
    except (ValueError, AttributeError):
        return None, "the checks endpoints gave no JSON object"
    red, pending = [], []
    for r in runs:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "?")[:40]
        if r.get("status") != "completed":
            pending.append(name)
        elif r.get("conclusion") in CHECK_BAD:
            red.append(name)
    for s in statuses:
        if not isinstance(s, dict):
            continue
        name = str(s.get("context") or "?")[:40]
        if s.get("state") in ("failure", "error"):
            red.append(name)
        elif s.get("state") == "pending":
            pending.append(name)

    def names(xs):
        return ": " + ", ".join(xs[:3]) + (" +%d more" % (len(xs) - 3) if len(xs) > 3 else "")
    if red:
        return "red", names(red)
    if pending:
        return "pending", names(pending)
    if not runs and not statuses:
        return "none", " (no check reported)"
    return "green", ""


def run_git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                           timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return r.returncode, r.stdout.strip()


def effective(key, opts, cwd, env):
    """(scope, value) of the identity value git would use, or None."""
    for var in ("GIT_AUTHOR_", "GIT_COMMITTER_"):
        v = env.get(var + ("EMAIL" if key == "email" else "NAME"))
        if v:
            return "env", v
    rc, out = run_git(opts + ["config", "--show-scope", "--get", "user." + key], cwd)
    if rc == 0 and "\t" in out:
        scope, _, val = out.partition("\t")
        return scope, val
    if rc not in (0, 1, None):  # git too old for --show-scope
        rc, out = run_git(opts + ["config", "--local", "--get", "user." + key], cwd)
        if rc == 0 and out:
            return "local", out
    return None


def norm(v):
    return v.strip().lower()


def allow_paths(env=None):
    env = os.environ if env is None else env
    paths = []
    base = env.get("CLAUDE_PLUGIN_DATA", "").strip()
    if base:
        paths.append(os.path.join(base, ALLOW_NAME))
    paths.append(os.path.join(os.path.expanduser("~"), ".config", "pulseengine-claude", ALLOW_NAME))
    return paths


def allowed_emails():
    out = set()
    for p in allow_paths():
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.split("#", 1)[0].strip()
                    if line:
                        out.add(norm(line))
        except OSError:
            pass
    return out


def mask_email(v):
    local, at, dom = v.strip().partition("@")
    return "'%s***%s' (%d chars)" % (local[:1], "@" + dom if at else ", no @domain", len(v.strip()))


def mask_name(v):
    return "'%s***' (%d chars)" % (v.strip()[:1], len(v.strip()))


def check_identity(opts, cwd, env, found):
    if not os.path.isdir(cwd):
        return
    bad = []
    eff_email = None
    for key in ("email", "name"):
        e = effective(key, opts, cwd, env)
        if not e:
            continue
        scope, val = e
        if key == "email":
            eff_email = val
        if scope not in FLAGGED_SCOPES:
            continue
        rc, glob = run_git(opts + ["config", "--global", "--includes", "--get", "user." + key], cwd)
        if rc != 0 or not glob:
            continue  # nothing to compare against: fail open
        if norm(val) != norm(glob):
            mask = mask_email if key == "email" else mask_name
            bad.append("user.%s is %s from %s scope, the global value is %s"
                       % (key, mask(val), scope, mask(glob)))
    if not bad:
        return
    if eff_email and norm(eff_email) in allowed_emails():
        return
    rc, top = run_git(opts + ["rev-parse", "--show-toplevel"], cwd)
    where = top if rc == 0 and top else cwd
    found.deny = (
        "pulseengine-claude commit-merge-guard: this command would author commits under "
        "a git identity that differs from your global one: " + "; ".join(bad) + ". "
        "GitHub shows such commits unverified, and main requires signed, verified "
        "commits (INC-2026-10-006: a test left a one-letter identity in a clone). "
        "If it is unintended, remove it and re-run: "
        "`git -C %s config --local --unset user.email; git -C %s config --local --unset user.name` "
        "(or drop the -c / GIT_AUTHOR_* override). If it is intentional, stop and ask the "
        "owner: only the owner adds an address to the allow-list (%s). Do not add it yourself."
        % (shlex.quote(where), shlex.quote(where), " or ".join(allow_paths())))


# ── rule 2: gh pr merge --auto ───────────────────────────────────────────────

def parse_repo(spec):
    """'owner/repo' from OWNER/REPO, HOST/OWNER/REPO, or a GitHub URL; else None."""
    if not spec:
        return None
    s = spec.strip()
    m = re.match(r"^(?:https?://|ssh://)?(?:[^@/]+@)?github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?(?:/.*)?$", s)
    if m:
        return "%s/%s" % (m.group(1), m.group(2))
    parts = s.split("/")
    if len(parts) == 2 and all(re.fullmatch(r"[\w.-]+", p) for p in parts):
        return s
    if len(parts) == 3 and parts[0] == "github.com":
        return "%s/%s" % (parts[1], parts[2])
    return None


def gh_args(rest, value_flags=GH_VALUE_FLAGS):
    """(repo spec, positionals) of a gh subcommand's arguments."""
    repo, pos, i = None, [], 0
    while i < len(rest):
        t = rest[i]
        if t in ("-R", "--repo") and i + 1 < len(rest):
            repo = rest[i + 1]
            i += 2
            continue
        if t.startswith("--repo="):
            repo = t.split("=", 1)[1]
        elif t.startswith("-R") and len(t) > 2:
            repo = t[2:]
        elif t in value_flags:
            i += 2
            continue
        elif not t.startswith("-"):
            pos.append(t)
        i += 1
    if repo is None:
        for p in pos:
            if "/pull/" in p:
                repo = p
                break
    return repo, pos


def gh_call(args, cwd, env, found):
    if not args:
        return
    if args[0] == "api":
        api_call(args[1:], cwd, env, found)
        return
    if len(args) < 2:
        return
    group, verb, rest = args[0], args[1], args[2:]
    repo, pos = gh_args(rest, GH_VALUE_FLAGS if verb == "merge" else GH_CREATE_VALUE_FLAGS)
    if group == "release" and verb == "create":
        tag = pos[0] if pos else None
        target = None
        for j, t in enumerate(rest):
            if t == "--target" and j + 1 < len(rest):
                target = rest[j + 1]
            elif t.startswith("--target="):
                target = t.split("=", 1)[1]
        publish_check("gh release create%s" % (" " + tag if tag else ""), cwd, env, found,
                      target=tag if tag and not target else target, spec=repo)
        return
    if group != "pr":
        return
    if verb in ("create", "edit"):
        found.pr_text.append((repo, cwd))
        if verb == "create":
            found.admission.append((repo, cwd))
        return
    if verb == "update-branch":
        if "--rebase" in rest:
            found.deny = DENY_REBASE
            return
        queue_check(repo, cwd, env, found, "`gh pr update-branch`")
        return
    if verb != "merge":
        return
    if "--admin" in rest:
        found.deny = DENY_ADMIN
        return
    if any(t == "--auto" or t.startswith("--auto=") and t != "--auto=false" for t in rest):
        merge_check(repo, cwd, env, found)
        return
    if "--disable-auto" in rest:
        return
    checks_ask(repo, pos[0] if pos else None, cwd, env, found)


DENY_ADMIN = (
    "pulseengine-claude commit-merge-guard: `gh pr merge --admin` merges around the required "
    "checks and the merge queue. Never merge around a red or absent gate. Merge with "
    "`gh pr merge --auto` (the queue or the required checks decide), or fix what is red. If a "
    "gate is wrong, that is the owner's call, not a reason to bypass it.")
DENY_API_MERGE = (
    "pulseengine-claude commit-merge-guard: merging through the API (REST PUT .../pulls/N/merge "
    "or GraphQL mergePullRequest) skips the merge queue the same way `gh pr merge --admin` "
    "does. Use `gh pr merge --auto`.")
DENY_REBASE = (
    "pulseengine-claude commit-merge-guard: a server-side rebase (`gh pr update-branch "
    "--rebase`, or updatePullRequestBranch with REBASE) rewrites the PR's commits without "
    "their signatures, and main requires signed commits, so the PR can no longer merge. "
    "Rebase locally with signing (`git fetch origin && git rebase origin/main`, then "
    "`git push --force-with-lease`), or leave it to the merge queue.")


def api_call(rest, cwd, env, found):
    path, method, fields, i = None, None, [], 0
    while i < len(rest):
        t = rest[i]
        if t in GH_API_VALUE_FLAGS and i + 1 < len(rest):
            if t in ("-X", "--method"):
                method = rest[i + 1].upper()
            elif t in ("-f", "--raw-field", "-F", "--field"):
                fields.append(rest[i + 1])
            i += 2
            continue
        if t.startswith(("--method=", "-X")) and t not in ("-X",):
            method = t.split("=", 1)[1].upper() if "=" in t else t[2:].upper()
        elif t.startswith(("--field=", "--raw-field=")):
            fields.append(t.split("=", 1)[1])
        elif not t.startswith("-") and path is None:
            path = t
        i += 1
    if not path:
        return
    method = method or ("POST" if fields else "GET")
    text = " ".join(fields)
    p = path.lstrip("/")
    if p == "graphql":
        if re.search(r"\bmergePullRequest\b", text):
            found.deny = DENY_API_MERGE
        elif re.search(r"\bupdatePullRequestBranch\b", text):
            if re.search(r"\bREBASE\b", text):
                found.deny = DENY_REBASE
            else:
                queue_check(None, cwd, env, found, "updatePullRequestBranch")
        return
    m = re.match(r"^repos/([^/\s]+)/([^/\s]+)/pulls/\d+/(merge|update-branch)/?(?:\?.*)?$", p)
    if not m or method in ("GET", "HEAD"):
        return
    repo = "%s/%s" % (m.group(1), m.group(2))
    if m.group(3) == "merge":
        found.deny = DENY_API_MERGE
    elif re.search(r"update_method=rebase", text, re.I):
        found.deny = DENY_REBASE
    else:
        queue_check(repo, cwd, env, found, "the REST update-branch endpoint")


def queue_check(spec, cwd, env, found, what):
    repo = parse_repo(spec) if spec else repo_from_cwd(cwd, env)
    if not repo:
        found.warnings.append(
            "commit-merge-guard: could not tell which GitHub repo %s targets, so it was not "
            "checked for a merge queue. On a merge-queue repo, do not update a PR branch: the "
            "queue tests against the latest main." % what)
        return
    verdict, why = repo_facts(repo)
    if verdict is not None and verdict.get("queue") is None:
        verdict, why = None, "its rulesets could not be read"
    if verdict is None:
        found.warnings.append(
            "commit-merge-guard: could not check whether %s has a merge queue (%s), so %s was "
            "NOT blocked. On a merge-queue repo, do not update a PR branch." % (repo, why, what))
        return
    if verdict.get("queue"):
        found.deny = (
            "pulseengine-claude commit-merge-guard: %s on %s, which merges through a merge "
            "queue. The queue tests every PR against the latest main itself, so updating the "
            "branch only re-runs CI and adds a merge commit. Queue it with `gh pr merge --auto` "
            "and leave the branch alone." % (what, repo))


def pr_number(spec):
    if spec is None:
        return None
    m = re.search(r"/pull/(\d+)", spec) or re.fullmatch(r"#?(\d+)", spec)
    return m.group(1) if m else None


def checks_ask(spec, pr, cwd, env, found):
    repo = parse_repo(spec) if spec else repo_from_cwd(cwd, env)
    if not repo:
        found.warnings.append(
            "commit-merge-guard: could not tell which GitHub repo `gh pr merge` targets, so "
            "its checks were not read. Merge only on green.")
        return
    num = pr_number(pr)
    if num:
        st, body = api_get("repos/%s/pulls/%s" % (repo, num))
        try:
            sha = json.loads(body)["head"]["sha"] if st == 200 else None
        except (ValueError, KeyError, TypeError):
            sha = None
    else:
        branch = pr
        if not branch and os.path.isdir(cwd):
            _, branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        sha = None
        st, body = (None, "no branch") if not branch else api_get(
            "repos/%s/pulls?head=%s:%s&state=open&per_page=5"
            % (repo, repo.split("/")[0], urllib.parse.quote(branch, safe="")))
        try:
            items = json.loads(body) if st == 200 else []
            if items:
                num, sha = str(items[0]["number"]), items[0]["head"]["sha"]
        except (ValueError, KeyError, TypeError, IndexError):
            sha = None
    if not sha:
        found.warnings.append(
            "commit-merge-guard: could not read the head of the PR `gh pr merge` targets on %s "
            "(%s), so its checks were NOT checked. Merge only on green."
            % (repo, "HTTP %s" % st if st else body))
        return
    state, detail = checks_state(repo, sha)
    if state is None:
        found.warnings.append(
            "commit-merge-guard: could not read the checks on %s#%s (%s), so `gh pr merge` was "
            "NOT blocked. Merge only on green." % (repo, num, detail))
        return
    if state != "green":
        found.asks.append(
            "pulseengine-claude commit-merge-guard: the checks on the head of %s#%s (%s) are %s%s. "
            "Never merge around a red, pending or absent gate. Use `gh pr merge --auto`, which "
            "waits for the required checks, or wait for green (ci-status). Where a repo treats "
            "a check as advisory, decide by the check's name, never by the count. The owner "
            "approves this call if it really should merge now."
            % (repo, num, short(sha), state, detail))


def repo_from_cwd(cwd, env):
    spec = env.get("GH_REPO") or os.environ.get("GH_REPO")
    if spec:
        return parse_repo(spec)
    if not os.path.isdir(cwd):
        return None
    names = []
    rc, out = run_git(["config", "--get-regexp", r"^remote\..*\.gh-resolved$"], cwd)
    if rc == 0:
        for line in out.splitlines():
            k = line.split(" ", 1)[0]
            names.append(k[len("remote."):-len(".gh-resolved")])
    names += ["upstream", "github", "origin"]
    for name in names:
        rc, url = run_git(["remote", "get-url", name], cwd)
        if rc == 0 and url:
            return parse_repo(url)
    return None


def state_dir():
    base = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    if base:
        return os.path.join(base, "commit-merge-guard")
    tmp = os.environ.get("TMPDIR", "").strip() or tempfile.gettempdir()
    return os.path.join(tmp, "pulseengine-claude", "commit-merge-guard")


def cache_load():
    try:
        with open(os.path.join(state_dir(), "repos.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def cache_save(d):
    try:
        sd = state_dir()
        os.makedirs(sd, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=sd, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(d, f)
            os.replace(tmp, os.path.join(sd, "repos.json"))
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError:
        pass


def api_get(path):
    """(status, body). status None means the API could not be asked."""
    if out_of_time():
        return None, "hook time budget spent"
    try:
        r = subprocess.run(["gh", "api", "-i", "--method", "GET", path],
                           capture_output=True, text=True, timeout=API_TIMEOUT_S)
        head, _, body = r.stdout.replace("\r\n", "\n").partition("\n\n")
        m = re.match(r"HTTP/\S+\s+(\d{3})", head)
        if m:
            return int(m.group(1)), body
        return None, "gh api gave no HTTP status (exit %d)" % r.returncode
    except FileNotFoundError:
        pass
    except (OSError, subprocess.SubprocessError) as e:
        return None, "gh api failed: %s" % type(e).__name__
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return None, "no gh CLI and no GH_TOKEN/GITHUB_TOKEN"
    base = os.environ.get("PULSEENGINE_GITHUB_API", "https://api.github.com").rstrip("/")
    req = urllib.request.Request(base + "/" + path, headers={
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "User-Agent": "pulseengine-claude-commit-merge-guard"})
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_S) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, "GitHub API unreachable: %s" % type(e).__name__


def assess(repo):
    """dict with guarded/branch/automerge_label, or (None, why) when unknown."""
    q = urllib.parse.quote
    st, body = api_get("repos/" + repo)
    if st != 200:
        return None, body if st is None else "repos/%s answered %s" % (repo, st)
    try:
        branch = json.loads(body)["default_branch"]
    except (ValueError, KeyError, TypeError):
        return None, "repos/%s gave no default_branch" % repo
    st, body = api_get("repos/%s/branches/%s" % (repo, q(branch, safe="")))
    if st != 200:
        return None, body if st is None else "the branch endpoint answered %s" % st
    try:
        protected = bool(json.loads(body).get("protected"))
    except (ValueError, AttributeError):
        return None, "the branch endpoint gave no JSON object"
    rules, rules_known = set(), True
    st, body = api_get("repos/%s/rules/branches/%s" % (repo, q(branch, safe="")))
    if st == 200:
        try:
            rules = {r.get("type") for r in json.loads(body) if isinstance(r, dict)}
        except (ValueError, TypeError):
            if not protected:
                return None, "the rules endpoint gave no JSON list"
            rules_known = False
    elif st == 403 and "Upgrade to GitHub Pro" in body:
        pass  # private repo on the free plan: rulesets cannot exist
    elif not protected:
        return None, body if st is None else "the rules endpoint answered %s" % st
    else:
        rules_known = False
    guarded = protected or bool(rules & GUARD_RULES)
    label = False
    if not guarded:
        st, _ = api_get("repos/%s/labels/automerge" % repo)
        label = st == 200
    return {"guarded": guarded, "branch": branch, "automerge_label": label,
            "queue": ("merge_queue" in rules) if rules_known else None, "v": CACHE_V}, None


def repo_facts(repo):
    """(verdict, None) from the day cache or the API, or (None, why). Only a
    definitive answer is cached, and an entry from an older schema is stale."""
    cache = cache_load()
    hit = cache.get(repo)
    if isinstance(hit, dict) and isinstance(hit.get("t"), (int, float)) \
            and hit.get("v") == CACHE_V and 0 <= time.time() - hit["t"] < CACHE_TTL_S:
        return hit, None
    verdict, why = assess(repo)
    if verdict is None:
        return None, why
    verdict["t"] = time.time()
    cache[repo] = verdict
    cache_save(cache)
    return verdict, None


def merge_check(spec, cwd, env, found):
    repo = parse_repo(spec) if spec else repo_from_cwd(cwd, env)
    if not repo:
        found.warnings.append(
            "commit-merge-guard: could not tell which GitHub repo `gh pr merge --auto` "
            "targets, so it was not checked. On a repo with no required checks, --auto "
            "merges immediately, before CI.")
        return
    verdict, why = repo_facts(repo)
    if verdict is None:
        found.warnings.append(
            "commit-merge-guard: could not check whether %s protects its default branch "
            "(%s), so `gh pr merge --auto` was NOT blocked. If it has no branch protection "
            "and no required checks, --auto merges immediately, before CI: use the repo's "
            "own merge convention, or wait for green and merge." % (repo, why))
        return
    if verdict.get("guarded"):
        return
    if verdict.get("automerge_label"):
        how = ("This repo has an `automerge` label, which is its merge convention: "
               "`gh pr edit <n> -R %s --add-label automerge`." % repo)
    else:
        how = ("Wait for the checks to go green (`gh pr checks <n> -R %s --watch`), then "
               "merge without --auto, or follow the repo's own merge convention." % repo)
    found.deny = (
        "pulseengine-claude commit-merge-guard: `gh pr merge --auto` on %s would merge "
        "immediately, before CI: its default branch '%s' has no branch protection and no "
        "ruleset with required status checks or a merge queue, so there is nothing for "
        "auto-merge to wait for (INC-2026-10-004, smithy#45). %s"
        % (repo, verdict.get("branch", "?"), how))


# ── entry point ──────────────────────────────────────────────────────────────

def decide(event):
    if not isinstance(event, dict) or event.get("tool_name") != "Bash":
        return None
    ti = event.get("tool_input")
    cmd = ti.get("command") if isinstance(ti, dict) else None
    if not isinstance(cmd, str) or not cmd.strip():
        return None
    cwd = event.get("cwd") if isinstance(event.get("cwd"), str) and event.get("cwd") else os.getcwd()
    found = Finding()
    walk(cmd, cwd, {}, found)
    if not found.deny:
        text_checks(cmd, found)
    if found.deny:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "deny",
                                       "permissionDecisionReason": found.deny}}
    if found.asks:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "ask",
                                       "permissionDecisionReason": " ".join(found.asks)[:MAX_TEXT]}}
    for spec, d in found.admission[:1]:
        admission(spec, d, found)
    context = " ".join(found.warnings + found.notes)
    if context:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "additionalContext": context[:MAX_TEXT]}}
    return None


# ── rule 7: text checks and PR admission ─────────────────────────────────────

MAX_TEXT = 4000


def repo_top(d):
    if not os.path.isdir(d):
        return None
    rc, top = run_git(["rev-parse", "--show-toplevel"], d)
    return top if rc == 0 and top else None


def text_checks(cmd, found):
    seen = set()
    jobs = [(d, ("-m", "--message"), "commit message") for d in found.commit_dirs[:1]]
    jobs += [(d, ("-t", "--title", "-b", "--body"), "PR title/body") for _, d in found.pr_text[:1]]
    for d, flags, what in jobs:
        if ph.in_temp(d):
            continue
        top = repo_top(d)
        hits = [(k, v) for k, v in ph.find(ph.message_text(cmd, flags)) if v not in seen]
        hits = ph.filter_hits(hits, None, top)
        seen.update(v for _, v in hits)
        if hits:
            found.asks.append(
                "pulseengine-claude commit-merge-guard: this %s carries host-shaped value(s): "
                "%s. Private hostnames, LAN/tailnet addresses, mount paths and home paths must "
                "not be published. Replace them with a placeholder. If the value is meant to be "
                "there, the owner approves this call; the owner, not you, adds a line to %s or %s."
                % (what, ph.describe(hits), ph.REPO_ALLOW, ph.user_allow_path()))


def admission_log(line):
    try:
        sd = state_dir()
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "admission.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), line))
    except OSError:
        pass


def admission(spec, cwd, found):
    """ci-status "Before opening a PR", source 2 (the fleet snapshot), as advice."""
    repo = parse_repo(spec) if spec else repo_from_cwd(cwd, {})
    base = (os.environ.get("PULSEENGINE_CI_STATUS_URL") or "").strip().rstrip("/")
    if not base:
        admission_log("skip: PULSEENGINE_CI_STATUS_URL unset")
        return
    if not repo:
        admission_log("skip: repo unknown")
        return
    if out_of_time():
        admission_log("skip: hook time budget spent")
        return
    name = repo.split("/", 1)[1]
    try:
        import ssl
        ca = (os.environ.get("PULSEENGINE_CI_STATUS_CACERT") or "").strip()
        ctx = ssl.create_default_context(cafile=ca) if ca else None
        req = urllib.request.Request(base + "/api/state",
                                     headers={"User-Agent": "pulseengine-claude-admission"})
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_S, context=ctx) as resp:
            q = json.loads(resp.read().decode("utf-8", "replace"))["snapshot"]["queue"]
        runs = len({x.get("run_id") for x in q.get("queued") or []
                    if isinstance(x, dict) and x.get("repo") == name})
        pools = q.get("pools") or {}
        busy = ", ".join("%s %d jobs" % (k, int(v.get("jobs_queued") or 0))
                         for k, v in sorted(pools.items())[:4] if isinstance(v, dict))
    except Exception as e:  # unreachable, bad CA, schema drift: advice only, never a block
        admission_log("fail: %s %s" % (repo, type(e).__name__))
        return
    lower = "" if q.get("queued_complete", True) else " (at least)"
    admission_log("ok: %s runs=%d" % (repo, runs))
    found.notes.append(
        "ci-status admission (fleet, at PR open): %s has %d queued run(s)%s; shared pools: %s. "
        "Per ci-status: a docs/one-line PR into a repo with a queued run, or where this session "
        "already has an open PR, should have been batched; batch the next one. fix/feature at "
        ">=5 queued runs: hold the next one locally. security and red-main always open."
        % (repo, runs, lower, busy or "none queued"))


def main():
    try:
        out = decide(json.loads(sys.stdin.read() or "null"))
        if out:
            sys.stdout.write(json.dumps(out))
    except Exception:  # fail open: a guard bug must never block every call
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
