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

Outputs: a deny (hookSpecificOutput.permissionDecision "deny" with a reason), a
warning (additionalContext only), or nothing. Never an allow decision, which would skip
the user's permission flow. Always exit 0; an exception prints nothing.

Python 3.9+, stdlib only. No network except for `gh pr merge --auto`.
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
        self.warnings = []


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


def coarse(cmd, cwd, env, found):
    """Tokenizing failed: decide on a regex scan rather than stay silent."""
    m = re.search(r"\bgit\b((?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*)\s+(" +
                  "|".join(re.escape(s) for s in COMMIT_SUBS) + r")\b", cmd)
    if m:
        opts = []
        for flag, val in re.findall(r"(-[Cc])\s+(\S+)", m.group(1)):
            opts += [flag, val.strip("'\"")]
        check_identity(opts, cwd, env, found)
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
    if i >= len(args) or args[i] not in COMMIT_SUBS:
        return
    if NO_COMMIT_FLAGS & set(args[i + 1:]):
        return
    check_identity(opts, cwd, env, found)


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


def gh_call(args, cwd, env, found):
    if len(args) < 2 or args[0] != "pr" or args[1] != "merge":
        return
    rest = args[2:]
    if not any(t == "--auto" or t.startswith("--auto=") and t != "--auto=false" for t in rest):
        return
    repo, i = None, 0
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
        elif t in GH_VALUE_FLAGS:
            i += 2
            continue
        elif not t.startswith("-") and repo is None and "/pull/" in t:
            repo = t
        i += 1
    merge_check(repo, cwd, env, found)


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
    rules = set()
    st, body = api_get("repos/%s/rules/branches/%s" % (repo, q(branch, safe="")))
    if st == 200:
        try:
            rules = {r.get("type") for r in json.loads(body) if isinstance(r, dict)}
        except (ValueError, TypeError):
            if not protected:
                return None, "the rules endpoint gave no JSON list"
    elif st == 403 and "Upgrade to GitHub Pro" in body:
        pass  # private repo on the free plan: rulesets cannot exist
    elif not protected:
        return None, body if st is None else "the rules endpoint answered %s" % st
    guarded = protected or bool(rules & GUARD_RULES)
    label = False
    if not guarded:
        st, _ = api_get("repos/%s/labels/automerge" % repo)
        label = st == 200
    return {"guarded": guarded, "branch": branch, "automerge_label": label}, None


def merge_check(spec, cwd, env, found):
    repo = parse_repo(spec) if spec else repo_from_cwd(cwd, env)
    if not repo:
        found.warnings.append(
            "commit-merge-guard: could not tell which GitHub repo `gh pr merge --auto` "
            "targets, so it was not checked. On a repo with no required checks, --auto "
            "merges immediately, before CI.")
        return
    cache = cache_load()
    hit = cache.get(repo)
    if isinstance(hit, dict) and isinstance(hit.get("t"), (int, float)) \
            and 0 <= time.time() - hit["t"] < CACHE_TTL_S:
        verdict = hit
    else:
        verdict, why = assess(repo)
        if verdict is None:
            found.warnings.append(
                "commit-merge-guard: could not check whether %s protects its default branch "
                "(%s), so `gh pr merge --auto` was NOT blocked. If it has no branch protection "
                "and no required checks, --auto merges immediately, before CI: use the repo's "
                "own merge convention, or wait for green and merge." % (repo, why))
            return
        verdict["t"] = time.time()
        cache[repo] = verdict
        cache_save(cache)
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
    if found.deny:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "deny",
                                       "permissionDecisionReason": found.deny}}
    if found.warnings:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "additionalContext": " ".join(found.warnings)}}
    return None


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
