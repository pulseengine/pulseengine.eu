#!/usr/bin/env python3
"""Incident ledger: escape and catch rates per 100 merges, org-wide.

    incident-ledger.py run [--days 90 | --since D --until D] [--repos a,b]
                           [--json OUT] [--md OUT] [--baseline REPO,...]
    incident-ledger.py check-ledger [--ledger docs/incidents/ledger.yaml]
    incident-ledger.py --self-test

Answers "AI raised outages 30%"-type claims at our own scale with rates, not
anecdotes. The unit is a MERGE to a repo's default branch: one first-parent
commit, or one PR when a rebase-merge put several first-parent commits on main.

Signals, recorded per unit and never mixed silently:
  escape (post-merge):
    main-red    a push/merge_group GitHub Actions suite on the unit's sha concluded
                FAILURE/TIMED_OUT/STARTUP_FAILURE and the previous run of the same
                workflow on first-parent main was not red (a red streak is charged
                to the commit that started it; path-filtered commits are skipped)
    revert      a later unit says "This reverts commit <sha>" or is titled
                Revert "<this unit's subject>"
    hotfix-ref  a later fix:/revert unit, within 14 days, references this unit's
                PR number (#N). Heuristic: a mention is not proof of causation
    merge-guard a "merge-guard: unchecked change on main (<sha12>)" issue
    ledger      a docs/incidents/ledger.yaml entry of kind escape names this merge
                (a manually found escape, e.g. a harness defect fixed later)
  catch (pre-merge):
    pr-red      a PR commit before the head had a FAILURE/ERROR status rollup and
                the PR still merged (the red was fixed before merge)
    mq-ejected  the PR was removed from the merge queue with reason failed_checks
  flags (nets, not incidents):
    merged-before-ci   a pull_request Actions suite on the head was still running
                       at mergedAt
    merged-red-head    the head's status rollup is FAILURE/ERROR yet it merged
    no-pr              pushed to main without a PR

Rates are units-with->=1-signal / units, per 100, with Wilson 95% intervals.
Escape rate = post-merge signals. Incident rate (owner definition) = escape OR
mq-ejected. Catch share = caught / (caught + escaped).

Authoring class, from the unit's commit messages and authors:
  claude-<model>   one named model in Co-Authored-By: Claude <model> trailers
  mixed            more than one named model in one unit
  claude-unnamed   agent marker (trailer without a model, Claude-Session link,
                   "Generated with Claude Code", an anthropic.com author) but no model
  bot              a [bot] author (dependabot, ...)
  human-only       none of the above. Agents commit under the human account, so
                   this class is "no marker", not "proven human".

Blind spots: a red-then-green re-run on the same sha shows only the last
attempt, so flakes are invisible on both sides; the status rollup includes
non-required checks; a revert or fix that names nothing is not linked; forks are
excluded (their history is upstream's).

API use is deliberately gentle (secondary rate limits are a known problem in
this org): one serial process, at most one request per second, every response
cached on disk (immutable results forever, recent ones per day), ETag
conditional requests on REST, backoff on 403/429. Unit lists come from treeless
bare clones (`git log --first-parent`), not the API. The cache lives outside the
repo (INCIDENT_LEDGER_CACHE, default ~/.cache/pulseengine-incident-ledger) and
its path is never written into any output.

Needs python3 >= 3.9, git, a GitHub token (GITHUB_TOKEN / GH_TOKEN or
`gh auth token`), and PyYAML for the ledger file.
"""
# rivet: verifies REQ-INCIDENT-LEDGER
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ORG = "pulseengine"
ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "incidents" / "ledger.yaml"
ACTIONS_APP_ID = 15368                     # the github-actions app
REDACT_TITLES = {"kiln"}                  # aggregate counts only, no titles
BASELINE_EXCLUDE = {
    "sigil": "pre-agent history is the imported upstream project (another author), "
             "not this org's process",
}
PRIVATE_NOTE = "private repo: number and title only"
Z95 = 1.959963984540054
RED = {"FAILURE", "TIMED_OUT", "STARTUP_FAILURE"}
NONINFO = {None, "CANCELLED", "SKIPPED", "NEUTRAL", "STALE", "ACTION_REQUIRED"}
MAIN_EVENTS = {"push", "merge_group"}
ROLLUP_RED = {"FAILURE", "ERROR"}
HOTFIX_DAYS = 14
STABLE_DAYS = 3                           # older than this: cache forever
ESCAPES = ("main-red", "revert", "hotfix-ref", "merge-guard", "ledger")
STRICT = tuple(k for k in ESCAPES if k != "hotfix-ref")   # without the heuristic
CATCHES = ("pr-red", "mq-ejected")
NET_CLASSES = (
    "no-test", "vacuous-gate", "skipped-or-non-required-check",
    "merged-without-ci", "human-override", "wrong-system", "wrong-object",
    "unclassified",
)

CONV = re.compile(r"^(\w+)(\([^)]*\))?!?:")
KNOWN_TYPES = {"feat", "fix", "docs", "ci", "chore", "refactor", "test", "build",
               "perf", "revert", "style"}
PR_SUBJ = re.compile(r"\(#(\d+)\)\s*$")
PR_MERGE = re.compile(r"^Merge pull request #(\d+)")
CO_CLAUDE = re.compile(r"(?im)^\s*co-authored-by:\s*claude\b([^<\n]*)<")
SESSION = re.compile(r"https://claude\.ai/code/session_[A-Za-z0-9]+")
GENERATED = re.compile(r"(?i)generated with \[?claude code")
REVERTS = re.compile(r"This reverts commit ([0-9a-f]{7,40})")
REVERT_SUBJ = re.compile(r'^Revert "(.+)"')
PR_REF = re.compile(r"(?<![\w/])#(\d+)\b")
GUARD = re.compile(r"merge-guard: unchecked change on main \(([0-9a-f]{7,40})\)")


# ── statistics ────────────────────────────────────────────────────────────────

def wilson(k: int, n: int, z: float = Z95):
    """Wilson score interval for k successes in n trials, or None for n == 0."""
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def rate(k: int, n: int) -> dict:
    ci = wilson(k, n)
    if ci is None:
        return {"k": k, "n": n, "per100": None, "lo": None, "hi": None}
    return {"k": k, "n": n, "per100": round(100 * k / n, 4),
            "lo": round(100 * ci[0], 4), "hi": round(100 * ci[1], 4)}


def fmt_rate(r: dict) -> str:
    if r["per100"] is None:
        return "n/a (n=0)"
    return f"{r['per100']:.1f} [{r['lo']:.1f}, {r['hi']:.1f}] ({r['k']}/{r['n']})"


# ── commit classification ─────────────────────────────────────────────────────

def ts(iso: str) -> dt.datetime:
    """Parse git or GitHub ISO-8601 (with Z or an offset) on Python 3.9."""
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def change_type(subject: str) -> str:
    if subject.startswith("Revert "):
        return "revert"
    m = CONV.match(subject)
    if not m:
        return "non-conventional"
    t = m.group(1).lower()
    return t if t in KNOWN_TYPES else "other"


def _norm_model(s: str) -> str:
    s = re.sub(r"\([^)]*\)", "", s).strip().lower()
    return re.sub(r"\s+", "-", s)


def is_bot(name: str, email: str) -> bool:
    return name.endswith("[bot]") or "[bot]@" in email or "dependabot" in email \
        or "renovate" in email


def model_class(messages, authors) -> str:
    """messages: commit bodies; authors: (name, email) pairs of the unit."""
    if authors and all(is_bot(n, e) for n, e in authors):
        return "bot"
    named, agent = set(), False
    for m in messages:
        for g in CO_CLAUDE.findall(m):
            agent = True
            s = _norm_model(g)
            if s:
                named.add(s)
        if SESSION.search(m) or GENERATED.search(m):
            agent = True
    if any(e.lower().endswith("anthropic.com") for _, e in authors):
        agent = True
    if len(named) > 1:
        return "mixed"
    if named:
        return "claude-" + named.pop()
    return "claude-unnamed" if agent else "human-only"


def session_links(messages) -> list:
    out = []
    for m in messages:
        for s in SESSION.findall(m):
            if s not in out:
                out.append(s)
    return out


# ── git ───────────────────────────────────────────────────────────────────────

def git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True).stdout


FMT = "%H%x1f%P%x1f%cI%x1f%an%x1f%ae%x1f%B%x1e"


def _parse_log(out: str) -> list:
    rows = []
    for rec in out.split("\x1e"):
        rec = rec.lstrip("\n")
        if not rec.strip():
            continue
        h, parents, date, an, ae, body = rec.split("\x1f", 5)
        rows.append({"sha": h, "parents": parents.split(), "date": date,
                     "an": an, "ae": ae, "msg": body.strip()})
    return rows


def first_parent_log(repo, branch: str, since=None, until=None) -> list:
    args = ["log", "--first-parent", "--reverse", f"--format={FMT}", branch]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    rows = _parse_log(git(repo, *args))
    for r in rows:
        r["extra"] = []
        if len(r["parents"]) > 1:      # a true merge: trailers live on the branch
            side = _parse_log(git(repo, "log", f"--format={FMT}",
                                  f"{r['parents'][0]}..{r['parents'][1]}"))
            r["extra"] = [(s["an"], s["ae"], s["msg"]) for s in side]
    return rows


def commit_before(repo, branch: str, since: str):
    out = git(repo, "log", "--first-parent", "-1", f"--until={since}",
              "--format=%H", branch).strip()
    return out or None


def build_units(repo_name: str, rows: list, pr_of_sha=None) -> list:
    """Group first-parent commits into merge units (one per PR, else per sha)."""
    pr_of_sha = pr_of_sha or {}
    units, by_pr = [], {}
    for r in rows:
        subject = r["msg"].splitlines()[0] if r["msg"] else ""
        m = PR_SUBJ.search(subject) or PR_MERGE.match(subject)
        pr = int(m.group(1)) if m else pr_of_sha.get(r["sha"])
        msgs = [r["msg"]] + [x[2] for x in r["extra"]]
        authors = [(r["an"], r["ae"])] + [(x[0], x[1]) for x in r["extra"]]
        if len(r["parents"]) > 1:      # GitHub is the merge's author; skip it
            authors = authors[1:] or authors
        if pr is not None and pr in by_pr:
            u = by_pr[pr]
            u["shas"].append(r["sha"])
            u["sha"] = r["sha"]
            u["date"] = r["date"]
            u["_msgs"] += msgs
            u["_authors"] += authors
            continue
        u = {"repo": repo_name, "pr": pr, "sha": r["sha"], "shas": [r["sha"]],
             "date": r["date"], "subject": subject, "type": change_type(subject),
             "_msgs": msgs, "_authors": authors, "signals": [], "flags": []}
        if pr is None:
            u["flags"].append("no-pr")
        units.append(u)
        if pr is not None:
            by_pr[pr] = u
    for u in units:
        u["month"] = u["date"][:7]
        u["model"] = model_class(u["_msgs"], u["_authors"])
        u["sessions"] = session_links(u["_msgs"])
    return units


# ── signal derivation (pure; all fixtures go through these) ───────────────────

def main_red_signals(units: list, suites_by_sha: dict, prior_sha=None) -> None:
    """Charge each red streak per workflow to the unit whose sha started it."""
    last = {}
    order = ([prior_sha] if prior_sha else []) + [s for u in units for s in u["shas"]]
    unit_of = {s: u for u in units for s in u["shas"]}
    for sha in order:
        seen = {}
        for s in suites_by_sha.get(sha, []):
            if s.get("event") not in MAIN_EVENTS:
                continue
            wf, c = s.get("workflow"), s.get("conclusion")
            if c in NONINFO:
                continue
            # one sha, several suites of one workflow: red wins
            if seen.get(wf) not in RED:
                seen[wf] = c
            if c in RED and s.get("url"):
                seen[wf + "\x00url"] = s["url"]
        for wf, c in seen.items():
            if wf.endswith("\x00url"):
                continue
            if c in RED and last.get(wf) not in RED and sha in unit_of:
                ev = {"kind": "main-red", "workflow": wf}
                if seen.get(wf + "\x00url"):
                    ev["evidence"] = seen[wf + "\x00url"]
                unit_of[sha]["signals"].append(ev)
            last[wf] = c


def revert_signals(units: list) -> None:
    for i, u in enumerate(units):
        for msg in u["_msgs"]:
            targets = REVERTS.findall(msg)
            m = REVERT_SUBJ.match(msg.splitlines()[0] if msg else "")
            for t in units[:i]:
                hit = any(s.startswith(x) for x in targets for s in t["shas"])
                if not hit and m and t["subject"] == m.group(1):
                    hit = True
                if hit and not any(e["kind"] == "revert" for e in t["signals"]):
                    t["signals"].append({"kind": "revert", "by_sha": u["sha"],
                                         "by_pr": u["pr"]})


def hotfix_signals(units: list) -> None:
    by_pr = {u["pr"]: u for u in units if u["pr"] is not None}
    for u in units:
        if u["type"] not in ("fix", "revert"):
            continue
        refs = set()
        for msg in u["_msgs"]:
            for line in msg.splitlines():
                found = {int(x) for x in PR_REF.findall(line)}
                if len(found) < 3:       # a line listing 3+ PRs is an inventory
                    refs |= found
        refs.discard(u["pr"])
        ud = ts(u["date"])
        for n in sorted(refs):
            t = by_pr.get(n)
            if t is None or t is u:
                continue
            if any(s["kind"] == "revert" and s.get("by_sha") == u["sha"]
                   for s in t["signals"]):
                continue                 # already charged as a revert by this unit
            td = ts(t["date"])
            if td < ud and (ud - td).days <= HOTFIX_DAYS:
                old = next((s for s in t["signals"] if s["kind"] == "hotfix-ref"), None)
                if old:
                    old["by_pr"] = sorted(set(old["by_pr"]) | {u["pr"]})
                else:
                    t["signals"].append({"kind": "hotfix-ref", "by_pr": [u["pr"]]})


def guard_signals(units: list, guards: list) -> None:
    """guards: [{"sha": prefix, "url": issue url}] for this repo."""
    for g in guards:
        for u in units:
            if any(s.startswith(g["sha"]) for s in u["shas"]):
                u["signals"].append({"kind": "merge-guard", "evidence": g["url"]})


def pr_signals(u: dict, pr: dict) -> None:
    """pr: the GraphQL pullRequest node (or a fixture of the same shape)."""
    if not pr:
        return
    commits = [c["commit"] for c in (pr.get("commits") or {}).get("nodes", [])]
    head = pr.get("headRefOid") or (commits[-1]["oid"] if commits else None)
    before = [c for c in commits if c["oid"] != head]
    if any((c.get("statusCheckRollup") or {}).get("state") in ROLLUP_RED
           for c in before):
        u["signals"].append({"kind": "pr-red", "evidence": pr.get("url")})
    head_c = next((c for c in commits if c["oid"] == head), None)
    if head_c and (head_c.get("statusCheckRollup") or {}).get("state") in ROLLUP_RED:
        u["flags"].append("merged-red-head")
    for ev in (pr.get("timelineItems") or {}).get("nodes", []):
        if ev.get("__typename") == "RemovedFromMergeQueueEvent" and \
                (ev.get("reason") or "").lower() in ("failed_checks", "failed checks"):
            u["signals"].append({"kind": "mq-ejected", "at": ev.get("createdAt"),
                                 "evidence": pr.get("url")})
            break
    merged = pr.get("mergedAt")
    hn = ((pr.get("head") or {}).get("nodes") or [])
    if merged and hn:
        late = False
        for s in (hn[0]["commit"].get("checkSuites") or {}).get("nodes", []):
            wr = s.get("workflowRun") or {}
            if wr.get("event") != "pull_request":
                continue
            if (wr.get("createdAt") or "9") > merged:
                continue                 # a re-run after the merge
            runs = (s.get("checkRuns") or {}).get("nodes", [])
            if s.get("status") != "COMPLETED" or \
                    any((r.get("completedAt") or "9") > _plus(merged, 30) for r in runs):
                late = True
        if late:
            u["flags"].append("merged-before-ci")


def _plus(iso: str, seconds: int) -> str:
    return (ts(iso) + dt.timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def outcome(u: dict) -> dict:
    kinds = {s["kind"] for s in u["signals"]}
    esc = bool(kinds & set(ESCAPES))
    return {"escape": esc, "strict": bool(kinds & set(STRICT)),
            "caught": bool(kinds & set(CATCHES)),
            "incident": esc or "mq-ejected" in kinds}


def aggregate(units: list, key) -> dict:
    groups = collections.defaultdict(list)
    for u in units:
        groups[key(u)].append(u)
    out = {}
    for g in sorted(groups):
        us = groups[g]
        o = [outcome(u) for u in us]
        n = len(us)
        esc = sum(x["escape"] for x in o)
        cau = sum(x["caught"] for x in o)
        out[g] = {"merges": n,
                  "escape": rate(esc, n),
                  "strict": rate(sum(x["strict"] for x in o), n),
                  "incident": rate(sum(x["incident"] for x in o), n),
                  "caught": rate(cau, n),
                  "catch_share": rate(cau, cau + esc)}
    return out


# ── ledger ────────────────────────────────────────────────────────────────────

GH_PR_URL = re.compile(r"^https://github\.com/pulseengine/[\w.-]+/pull/\d+$")
URL = re.compile(r"https://\S+")


def load_ledger(path):
    try:
        import yaml
    except ImportError:
        sys.exit("incident-ledger: needs PyYAML for the ledger (pip install pyyaml)")
    return yaml.safe_load(pathlib.Path(path).read_text()) or {}


def check_entries(entries: list) -> list:
    """Shape and closure rule. Returns a list of error strings."""
    errs, ids = [], set()
    for e in entries:
        i = e.get("id", "?")
        if i in ids:
            errs.append(f"{i}: duplicate id")
        ids.add(i)
        for k in ("id", "kind", "status", "change", "net", "why", "countermeasure"):
            if k not in e:
                errs.append(f"{i}: missing {k}")
        if errs and errs[-1].startswith(f"{i}: missing"):
            continue
        if e["kind"] not in ("escape", "near-miss", "catch"):
            errs.append(f"{i}: kind must be escape|near-miss|catch")
        if e["status"] not in ("open", "closed"):
            errs.append(f"{i}: status must be open|closed")
        ch = e["change"]
        for k in ("repo", "model"):
            if not ch.get(k):
                errs.append(f"{i}: change.{k} missing")
        if not (ch.get("pr") or ch.get("merge_sha") or ch.get("commits")):
            errs.append(f"{i}: change needs pr, merge_sha or commits")
        if e["net"].get("class") not in NET_CLASSES:
            errs.append(f"{i}: net.class must be one of {', '.join(NET_CLASSES)}")
        for f in ("net", "why"):
            if e[f].get("source") not in ("manual", "mechanical"):
                errs.append(f"{i}: {f}.source must be manual|mechanical")
        if not e["why"].get("evidence"):
            errs.append(f"{i}: why.evidence needs at least one link")
        cm = e["countermeasure"]
        if e["status"] == "closed":
            if not GH_PR_URL.match(str(cm.get("pr") or "")):
                errs.append(f"{i}: closed needs countermeasure.pr (a PR URL)")
            if cm.get("merged") is not True:
                errs.append(f"{i}: closed needs countermeasure.merged: true")
            if not URL.search(str(cm.get("negative_control") or "")):
                errs.append(f"{i}: closed needs countermeasure.negative_control "
                            "with a link showing red-on-old-bug")
    return errs


def apply_ledger(units: list, entries: list) -> None:
    """A manually found escape counts: it adds a `ledger` signal to its merge."""
    for e in entries:
        if e.get("kind") != "escape":
            continue
        for u in units:
            if match_ledger(e, u) and not any(
                    s["kind"] == "ledger" and s.get("id") == e["id"] for s in u["signals"]):
                u["signals"].append({"kind": "ledger", "id": e["id"]})


def match_ledger(entry: dict, u: dict) -> bool:
    ch = entry.get("change", {})
    if ch.get("repo") != u["repo"]:
        return False
    if ch.get("pr") is not None and ch.get("pr") == u["pr"]:
        return True
    sha = str(ch.get("merge_sha") or "")
    return bool(sha) and any(s.startswith(sha) for s in u["shas"])


# ── GitHub client (gentle) ────────────────────────────────────────────────────

class GitHub:
    def __init__(self, cache: pathlib.Path, offline=False, min_gap=1.0):
        self.cache = cache
        (cache / "api").mkdir(parents=True, exist_ok=True)
        self.offline, self.min_gap, self._last = offline, min_gap, 0.0
        self.requests = self.cache_hits = 0
        self.token = None if offline else self._token()

    @staticmethod
    def _token():
        t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if t:
            return t
        try:
            return subprocess.run(["gh", "auth", "token"], capture_output=True,
                                  text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            sys.exit("incident-ledger: no token (GITHUB_TOKEN, GH_TOKEN or gh auth)")

    def _path(self, key: str) -> pathlib.Path:
        return self.cache / "api" / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def _http(self, method, url, body=None, headers=None):
        wait = self._last + self.min_gap - time.time()
        if wait > 0:
            time.sleep(wait)
        h = {"Authorization": f"bearer {self.token}", "User-Agent": "pe-incident-ledger",
             "Accept": "application/vnd.github+json"}
        h.update(headers or {})
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        self.requests += 1
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                status, hdr, data = r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            status, hdr, data = e.code, dict(e.headers), e.read()
        except (urllib.error.URLError, TimeoutError) as e:
            status, hdr, data = 599, {}, str(e).encode()
        self._last = time.time()
        return status, {k.lower(): v for k, v in hdr.items()}, data

    def _send(self, method, url, body=None, headers=None):
        for attempt in range(7):
            status, hdr, data = self._http(method, url, body, headers)
            limited = status in (403, 429) and (
                b"rate limit" in data.lower() or "retry-after" in hdr
                or hdr.get("x-ratelimit-remaining") == "0")
            if status == 200 and b'"RATE_LIMITED"' in data:
                limited = True
            if limited:
                if "retry-after" in hdr:
                    w = int(hdr["retry-after"])
                elif hdr.get("x-ratelimit-remaining") == "0":
                    w = int(hdr.get("x-ratelimit-reset", "0")) - int(time.time()) + 5
                else:
                    w = 60 * 2 ** attempt
                w = max(5, min(w, 900))
                sys.stderr.write(f"rate limited ({status}); backing off {w}s\n")
                time.sleep(w)
                continue
            if status in (502, 503, 504, 599):
                time.sleep(10 * 2 ** attempt)
                continue
            return status, hdr, data
        sys.exit(f"incident-ledger: giving up on {url} after backoff")

    def graphql(self, query: str, variables: dict, stable: bool):
        key = query + json.dumps(variables, sort_keys=True)
        if not stable:
            key += dt.date.today().isoformat()
        p = self._path("gql" + key)
        if p.exists():
            self.cache_hits += 1
            return json.loads(p.read_text())
        if self.offline:
            sys.exit("incident-ledger: --offline and a GraphQL response is not cached")
        body = json.dumps({"query": query, "variables": variables}).encode()
        status, _, data = self._send("POST", "https://api.github.com/graphql", body,
                                     {"Content-Type": "application/json"})
        if status != 200:
            sys.exit(f"incident-ledger: GraphQL HTTP {status}: {data[:300]!r}")
        out = json.loads(data)
        if out.get("data") is None:
            sys.exit(f"incident-ledger: GraphQL error: {json.dumps(out)[:400]}")
        p.write_text(json.dumps(out))
        return out

    def rest(self, path: str):
        """GET with an ETag: a 304 costs no rate limit and returns the cache."""
        p = self._path("rest" + path)
        cached = json.loads(p.read_text()) if p.exists() else None
        if self.offline:
            if cached is None:
                sys.exit("incident-ledger: --offline and a REST response is not cached")
            return cached["body"]
        hdr = {"If-None-Match": cached["etag"]} if cached and cached.get("etag") else {}
        status, h, data = self._send("GET", "https://api.github.com" + path, None, hdr)
        if status == 304 and cached:
            self.cache_hits += 1
            return cached["body"]
        if status != 200:
            sys.exit(f"incident-ledger: REST {path} HTTP {status}: {data[:200]!r}")
        body = json.loads(data)
        p.write_text(json.dumps({"etag": h.get("etag"), "body": body}))
        return body


SUITES = ("checkSuites(first:40, filterBy:{appId:%d}){nodes{conclusion status "
          "workflowRun{event url workflow{name}}}}" % ACTIONS_APP_ID)
COMMIT_Q = ("associatedPullRequests(first:1){nodes{number mergedAt}} " + SUITES)
PR_Q = (
    "number url title mergedAt headRefOid "
    "commits(last:30){nodes{commit{oid statusCheckRollup{state}}}} "
    "timelineItems(first:30, itemTypes:[REMOVED_FROM_MERGE_QUEUE_EVENT]){nodes{"
    "__typename ... on RemovedFromMergeQueueEvent{createdAt reason}}} "
    "head: commits(last:1){nodes{commit{oid checkSuites(first:15, filterBy:{appId:%d})"
    "{nodes{status conclusion workflowRun{event createdAt} "
    "checkRuns(first:8){nodes{completedAt}}}}}}}" % ACTIONS_APP_ID
)


def _stable(dates) -> bool:
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=STABLE_DAYS)
    return all(d and d != "0" and ts(d) < cut for d in dates) or \
        all(d == "0" for d in dates)


def fetch_commits(gh: GitHub, repo: str, shas_dates: list, batch=40) -> dict:
    out = {}
    for i in range(0, len(shas_dates), batch):
        chunk = shas_dates[i:i + batch]
        parts = " ".join(f'c{j}: object(oid:"{s}"){{... on Commit{{oid {COMMIT_Q}}}}}'
                         for j, (s, _) in enumerate(chunk))
        q = f'query($o:String!,$n:String!){{repository(owner:$o,name:$n){{{parts}}}}}'
        d = gh.graphql(q, {"o": ORG, "n": repo}, _stable([x[1] for x in chunk]))
        for node in (d["data"]["repository"] or {}).values():
            if node:
                out[node["oid"]] = node
    return out


def fetch_prs(gh: GitHub, repo: str, prs_dates: list, batch=15) -> dict:
    out = {}
    for i in range(0, len(prs_dates), batch):
        chunk = prs_dates[i:i + batch]
        parts = " ".join(f"p{n}: pullRequest(number:{n}){{{PR_Q}}}" for n, _ in chunk)
        q = f'query($o:String!,$n:String!){{repository(owner:$o,name:$n){{{parts}}}}}'
        d = gh.graphql(q, {"o": ORG, "n": repo}, _stable([x[1] for x in chunk]))
        for node in (d["data"]["repository"] or {}).values():
            if node:
                out[node["number"]] = node
    return out


def suites_of(node) -> list:
    out = []
    for s in ((node or {}).get("checkSuites") or {}).get("nodes", []):
        wr = s.get("workflowRun") or {}
        out.append({"event": wr.get("event"), "workflow": (wr.get("workflow") or {}).get("name"),
                    "conclusion": s.get("conclusion"), "url": wr.get("url")})
    return out


def list_repos(gh: GitHub) -> list:
    q = ("query($o:String!){organization(login:$o){repositories(first:100, isFork:false)"
         "{nodes{name isArchived isPrivate isEmpty defaultBranchRef{name}}}}}")
    d = gh.graphql(q, {"o": ORG}, False)
    return [r for r in d["data"]["organization"]["repositories"]["nodes"]
            if not r["isArchived"] and not r["isEmpty"] and r["defaultBranchRef"]]


def ensure_clone(cache: pathlib.Path, name: str, branch: str) -> pathlib.Path:
    d = cache / "clones" / f"{name}.git"
    url = f"https://github.com/{ORG}/{name}.git"
    if not d.exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                        "--single-branch", "--branch", branch, url, str(d)], check=True)
    else:
        subprocess.run(["git", "-C", str(d), "fetch", "-q", "--filter=blob:none",
                        "origin", f"+refs/heads/{branch}:refs/heads/{branch}"], check=True)
    time.sleep(1)
    return d


def merge_guards(gh: GitHub) -> dict:
    q = "/search/issues?q=" + urllib.request.quote(
        f'org:{ORG} in:title "merge-guard: unchecked change on main"') + "&per_page=100"
    out = collections.defaultdict(list)
    for it in gh.rest(q).get("items", []):
        m = GUARD.search(it["title"])
        if m:
            repo = it["repository_url"].rsplit("/", 1)[1]
            out[repo].append({"sha": m.group(1), "url": it["html_url"]})
    return out


def repo_units(gh, cache, r, since, until, guards) -> list:
    name, branch = r["name"], r["defaultBranchRef"]["name"]
    clone = ensure_clone(cache, name, branch)
    rows = first_parent_log(clone, branch, since, until)
    if not rows:
        return []
    prior = commit_before(clone, branch, since) if since else None
    want = [(x["sha"], x["date"]) for x in rows] + ([(prior, "0")] if prior else [])
    nodes = fetch_commits(gh, name, want)
    pr_of = {}
    for s, n in nodes.items():
        prs = (n.get("associatedPullRequests") or {}).get("nodes") or []
        if prs and prs[0].get("mergedAt"):
            pr_of[s] = prs[0]["number"]
    units = build_units(name, rows, pr_of)
    main_red_signals(units, {s: suites_of(n) for s, n in nodes.items()}, prior)
    prs = fetch_prs(gh, name, [(u["pr"], u["date"]) for u in units if u["pr"]])
    for u in units:
        if u["pr"]:
            pr_signals(u, prs.get(u["pr"]))
            if u["pr"] not in prs:
                u["flags"].append("pr-not-found")
    revert_signals(units)
    hotfix_signals(units)
    guard_signals(units, guards.get(name, []))
    for u in units:
        u["private"] = r["isPrivate"]
    return units


def first_agent_date(clone, branch: str):
    for r in first_parent_log(clone, branch):
        msgs = [r["msg"]] + [x[2] for x in r["extra"]]
        authors = [(r["an"], r["ae"])] + [(x[0], x[1]) for x in r["extra"]]
        if model_class(msgs, authors) not in ("human-only", "bot"):
            return r["date"]
    return None


# ── output ────────────────────────────────────────────────────────────────────

def public_unit(u: dict) -> dict:
    o = {k: u[k] for k in ("repo", "pr", "sha", "date", "month", "type", "model",
                           "signals", "flags")}
    o.update(outcome(u))
    return o


def incident_rows(units: list, entries: list, titles=False) -> list:
    rows = []
    for u in units:
        if not u["signals"]:
            continue
        led = [e["id"] for e in entries if match_ledger(e, u)]
        o = outcome(u)
        row = {"repo": u["repo"], "pr": u["pr"], "sha": u["sha"][:12],
               "date": u["date"][:10], "model": u["model"], "type": u["type"],
               "sessions": u["sessions"], "signals": u["signals"],
               "escape": o["escape"], "caught": o["caught"], "ledger": led}
        if titles:                     # local triage only; never in committed output
            row["title"] = "(title withheld)" if u["repo"] in REDACT_TITLES \
                else u["subject"]
        rows.append(row)
    return rows


def _md_table(title: str, agg: dict, col: str) -> list:
    lines = [f"### {title}", "",
             f"| {col} | merges | escape /100 [95% CI] | strict escape /100 "
             "| incident /100 (owner def.) | caught /100 | catch share % |",
             "|---|---:|---|---|---|---|---|"]
    for g, a in agg.items():
        lines.append(f"| {g} | {a['merges']} | {fmt_rate(a['escape'])} | "
                     f"{fmt_rate(a['strict'])} | "
                     f"{fmt_rate(a['incident'])} | {fmt_rate(a['caught'])} | "
                     f"{fmt_rate(a['catch_share'])} |")
    return lines + [""]


def render_md(res: dict) -> str:
    h = res["headline"]
    L = ["# Incident ledger: run report", "",
         f"Generated {res['generated']} by `scripts/incident-ledger.py run`. Window "
         f"{res['window']['since']} to {res['window']['until']}, {len(res['repos'])} "
         "non-fork, non-archived repos. Snapshot: these numbers are from this run "
         "and drift on the next one.", "",
         "Unit: a merge to the default branch. Rates are merges with at least one "
         "signal per 100 merges, Wilson 95% interval, (k/n). Never read a bare count "
         "as a trend.", "",
         "## Headline", "",
         f"- Escape rate (post-merge: main-red, revert, hotfix-ref, merge-guard, "
         f"or a ledger entry of kind escape): "
         f"**{fmt_rate(h['escape'])}** per 100 merges",
         f"- Strict escape rate, the same without hotfix-ref (a heuristic; see "
         f"Method): **{fmt_rate(h['strict'])}**",
         f"- Incident rate, owner definition (escape or merge-queue ejection): "
         f"**{fmt_rate(h['incident'])}**",
         f"- Caught before merge (red PR commit later fixed, or queue ejection on "
         f"failed checks): **{fmt_rate(h['caught'])}**",
         f"- Catch share, caught / (caught + escaped): **{fmt_rate(h['catch_share'])}** "
         "percent", "",
         "Signal counts (a unit can carry several): " +
         ", ".join(f"{k} {v}" for k, v in res["signal_counts"].items()) + ".",
         "Net flags: " + ", ".join(f"{k} {v}" for k, v in res["flag_counts"].items()) + ".",
         ""]
    L += _md_table("By authoring class", res["by_model"], "class")
    L += ["`human-only` means no agent marker, not proven human: agents commit under "
          "the owner's account.", ""]
    L += _md_table("By change type", res["by_type"], "type")
    L += _md_table("By month", res["by_month"], "month")
    L += _md_table("By repo", res["by_repo"], "repo")
    if res.get("baseline"):
        b = res["baseline"]
        L += ["## Baseline (weak)", "", b["note"], ""]
        L += _md_table("Pre-agent window vs agent era, same repos, same signals",
                       b["table"], "era")
        L += ["Excluded from the baseline: " + "; ".join(b["excluded"]), ""]
    L += ["## Seeded and triaged entries", "",
          "| id | kind | status | change | net | why | countermeasure |",
          "|---|---|---|---|---|---|---|"]
    for e in res["ledger"]:
        ch = e["change"]
        ref = f"{ch['repo']}#{ch['pr']}" if ch.get("pr") else ch["repo"]
        cm = e["countermeasure"]
        found = e.get("_found")
        mech = "" if found is None else (" (sweep found it)" if found else
                                         " (sweep missed it)")
        L.append(f"| {e['id']} | {e['kind']} | {e['status']} | {ref}, {ch['model']}"
                 f"{mech} | {e['net']['class']} ({e['net']['source']}) | "
                 f"{e['why']['classifier']} ({e['why']['source']}) | "
                 f"{cm.get('gate') or 'none yet'} |")
    L += ["", f"Seed recall (mechanically detectable seeds found by the sweep): "
          f"{res['seed_recall']}", ""]
    L += ["## Net-failure classes", "",
          "Ledger entries of every kind (escape, near-miss, catch) by `net.class`, "
          "plus every untriaged mechanical escape as `unclassified (manual)` until "
          "someone fills fields 2 to 4. With this few triaged entries, the order "
          "among the triaged classes says nothing yet.", ""]
    for k, v in res["net_classes"]:
        L.append(f"- {k}: {v}")
    L += ["", "## Mechanical incidents", "",
          "Fields 2 to 4 (net, why, countermeasure) are manual for every row without "
          "a ledger id. PR titles are not published here; follow the repo and PR "
          "number.", "",
          "| repo | PR | sha | date | class | type | signals | ledger |" +
          (" title |" if res.get("titles") else ""),
          "|---|---|---|---|---|---|---|---|" + ("---|" if res.get("titles") else "")]
    for r in res["incidents"]:
        sig = ", ".join(s["kind"] for s in r["signals"])
        pr = f"#{r['pr']}" if r["pr"] else "-"
        title = f" {r['title'].replace('|', '/')[:90]} |" if "title" in r else ""
        L.append(f"| {r['repo']} | {pr} | {r['sha']} | {r['date']} | {r['model']} | "
                 f"{r['type']} | {sig} | {', '.join(r['ledger']) or 'untriaged'} |"
                 f"{title}")
    L += ["", "## Method and blind spots", "", res["method"], "", CALIBRATION, ""]
    return "\n".join(L)


METHOD = (__doc__.split("Rates are")[0].split("Signals,")[1]).strip()
# Instrument checks made by hand on the first run (2026-10-29). Re-measure and
# re-date these when the rules change; they are not re-derived on each run.
CALIBRATION = (
    "Calibration, first run, 2026-10-29, by hand. hotfix-ref: of 15 randomly "
    "sampled links, 9 named a real defect in the referenced merge and 6 were "
    "mentions (a reference point, a fix credited to that PR, a list), so "
    "precision is about 60% and the strict escape rate leaves it out. "
    "merged-red-head: 4 sampled heads were red on an advisory check (2), a "
    "failing audit on a dependabot bump (1) and failing clippy and tests on a "
    "dependabot bump (1), so the flag mixes real overrides with advisory reds. "
    "merged-before-ci: 4 of 4 sampled had pull_request checks still running at "
    "mergedAt (required or not), all of which later passed or were cancelled."
)


def summarise(units: list, entries: list, window: dict, repos: list,
              titles=False) -> dict:
    sc = collections.Counter(s["kind"] for u in units for s in u["signals"])
    fc = collections.Counter(f for u in units for f in u["flags"])
    allagg = aggregate(units, lambda u: "all")["all"] if units else \
        {k: rate(0, 0) for k in ("escape", "strict", "incident", "caught",
                                 "catch_share")}
    inc = incident_rows(units, entries, titles)
    led = []
    for e in entries:
        e2 = dict(e)
        if e.get("expect_mechanical"):
            e2["_found"] = any(match_ledger(e, u) and
                               set(e["expect_mechanical"]) <=
                               {s["kind"] for s in u["signals"]} for u in units)
        led.append(e2)
    detectable = [e for e in led if "_found" in e]
    recall = (f"{sum(e['_found'] for e in detectable)}/{len(detectable)}"
              if detectable else "n/a")
    nets = collections.Counter(e["net"]["class"] for e in entries)
    untriaged = sum(1 for r in inc if r["escape"] and not r["ledger"])
    nets["unclassified (manual)"] += untriaged
    return {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "window": window, "repos": repos,
        "headline": allagg,
        "signal_counts": dict(sorted(sc.items())),
        "flag_counts": dict(sorted(fc.items())),
        "by_model": aggregate(units, lambda u: u["model"]),
        "by_type": aggregate(units, lambda u: u["type"]),
        "by_month": aggregate(units, lambda u: u["month"]),
        "by_repo": aggregate(units, lambda u: u["repo"]),
        "incidents": inc,
        "titles": titles,
        "ledger": led,
        "seed_recall": recall,
        "net_classes": nets.most_common(),
        "open_entries": [e["id"] for e in entries if e["status"] == "open"],
        "method": METHOD,
    }


def cmd_run(a) -> int:
    cache = pathlib.Path(os.environ.get("INCIDENT_LEDGER_CACHE") or
                         pathlib.Path.home() / ".cache" / "pulseengine-incident-ledger")
    gh = GitHub(cache, offline=a.offline)
    until = a.until or dt.date.today().isoformat()
    since = a.since or (dt.date.fromisoformat(until) - dt.timedelta(days=a.days)).isoformat()
    repos = list_repos(gh)
    if a.repos:
        keep = set(a.repos.split(","))
        repos = [r for r in repos if r["name"] in keep]
    guards = merge_guards(gh)
    entries = load_ledger(a.ledger).get("entries", [])
    errs = check_entries(entries)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1
    units = []
    for r in sorted(repos, key=lambda r: r["name"]):
        us = repo_units(gh, cache, r, since, until + "T23:59:59Z", guards)
        print(f"{r['name']}: {len(us)} merges", file=sys.stderr)
        units += us
    apply_ledger(units, entries)
    res = summarise(units, entries, {"since": since, "until": until},
                    sorted(r["name"] for r in repos), a.titles)
    if a.baseline:
        res["baseline"] = baseline(gh, cache, repos, a.baseline.split(","), since, until)
    # countermeasure PRs of closed entries must really be merged
    for e in entries:
        pr = e["countermeasure"].get("pr")
        if e["status"] == "closed" and pr:
            _, _, repo, _, n = pr.rstrip("/").split("/")[-5:]
            q = "query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n)" \
                "{pullRequest(number:$p){merged}}}"
            d = gh.graphql(q, {"o": ORG, "n": repo, "p": int(n)}, False)
            if not ((d["data"]["repository"] or {}).get("pullRequest") or {}).get("merged"):
                print(f"{e['id']}: closed but {pr} is not merged", file=sys.stderr)
                return 1
    res["units"] = [public_unit(u) for u in units]
    res["api"] = {"requests": gh.requests, "cache_hits": gh.cache_hits}
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, separators=(",", ":")) + "\n")
    md = render_md(res)
    if a.md:
        pathlib.Path(a.md).write_text(md + "\n")
    print(f"escape {fmt_rate(res['headline']['escape'])}; caught "
          f"{fmt_rate(res['headline']['caught'])}; API requests {gh.requests}, "
          f"cache hits {gh.cache_hits}", file=sys.stderr)
    return 0


def baseline(gh, cache, repos, names, since, until) -> dict:
    """Same repos, same git+Actions signals; merge-guard and mq did not exist."""
    comparable = ("main-red", "revert", "hotfix-ref")
    pre, era, excluded, spans = [], [], [], []
    by = {r["name"]: r for r in repos}
    for n in names:
        r = by.get(n)
        if n in BASELINE_EXCLUDE:
            excluded.append(f"{n}: {BASELINE_EXCLUDE[n]}")
            continue
        if not r:
            excluded.append(f"{n}: not an active non-fork repo")
            continue
        clone = ensure_clone(cache, n, r["defaultBranchRef"]["name"])
        fa = first_agent_date(clone, r["defaultBranchRef"]["name"])
        if not fa:
            excluded.append(f"{n}: no agent marker at all")
            continue
        us = repo_units(gh, cache, r, None, fa, {})
        us = [u for u in us if ts(u["date"]) < ts(fa)]
        if len(us) < 30:
            excluded.append(f"{n}: only {len(us)} pre-agent merges")
            continue
        spans.append(f"{n} {us[0]['date'][:10]} to {fa[:10]} ({len(us)} merges)")
        pre += us
        era += [u for u in repo_units(gh, cache, r, since, until + "T23:59:59Z", {})]

    def restrict(us):
        out = []
        for u in us:
            v = dict(u)
            v["signals"] = [s for s in u["signals"] if s["kind"] in comparable + CATCHES
                            and s["kind"] != "mq-ejected"]
            out.append(v)
        return out
    tagged = [dict(u, era="pre-agent") for u in restrict(pre)] + \
             [dict(u, era="agent era (window)") for u in restrict(era)]
    note = ("Weak baseline. Pre-agent = first-parent merges before the repo's first "
            "agent marker. Spans: " + "; ".join(spans) + ". Confounders: a different "
            "project phase (early, small changes), fewer repos, often no PRs and no "
            "merge queue, CI that may not have existed yet (no CI means no main-red "
            "signal, so the pre-agent escape rate is biased low), and no marker does "
            "not mean no AI. Signals limited to main-red, revert, hotfix-ref, pr-red "
            "in both eras.")
    return {"note": note, "spans": spans, "excluded": excluded,
            "table": aggregate(tagged, lambda u: u["era"])}


def cmd_check_ledger(a) -> int:
    entries = load_ledger(a.ledger).get("entries", [])
    errs = check_entries(entries)
    for e in errs:
        print(f"ledger: {e}", file=sys.stderr)
    if not errs:
        closed = sum(e["status"] == "closed" for e in entries)
        print(f"ledger: {len(entries)} entries, {closed} closed, all well-formed")
    return 1 if errs else 0


# ── self-test ─────────────────────────────────────────────────────────────────

def _fixture_repo(tmp: pathlib.Path) -> pathlib.Path:
    r = tmp / "repo"
    r.mkdir()

    def g(*args, env=None):
        e = dict(os.environ, GIT_AUTHOR_NAME="Ann", GIT_AUTHOR_EMAIL="ann@example.org",
                 GIT_COMMITTER_NAME="Ann", GIT_COMMITTER_EMAIL="ann@example.org",
                 GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        e.update(env or {})
        return subprocess.run(["git", "-C", str(r), *args], check=True, env=e,
                              capture_output=True, text=True).stdout.strip()

    def commit(msg, date, env=None):
        (r / "f").write_text(msg + date)
        g("add", "f")
        g("commit", "-q", "--no-gpg-sign", "-m", msg,
          env=dict({"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}, **(env or {})))
        return g("rev-parse", "HEAD")

    g("init", "-q", "-b", "main")
    c1 = commit("feat: add a (#1)\n\nCo-Authored-By: Claude Opus 5.5 "
                "<noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/"
                "session_abc", "2026-10-01T10:00:00Z")
    c2 = commit("fix: repair b (#2)\n\nRegression from #1.\n\nCo-Authored-By: Claude "
                "Opus 4.8 (1M context) <noreply@anthropic.com>", "2026-10-02T10:00:00Z")
    commit(f'Revert "feat: add a (#1)" (#3)\n\nThis reverts commit {c1}.',
           "2026-10-03T10:00:00Z")
    g("checkout", "-q", "-b", "topic")
    commit("work on topic\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>",
           "2026-10-04T10:00:00Z")
    g("checkout", "-q", "main")
    g("merge", "-q", "--no-ff", "--no-gpg-sign", "-m",
      "Merge pull request #4 from x/topic", "topic",
      env={"GIT_AUTHOR_DATE": "2026-10-05T10:00:00Z",
           "GIT_COMMITTER_DATE": "2026-10-05T10:00:00Z",
           "GIT_AUTHOR_NAME": "GitHub", "GIT_AUTHOR_EMAIL": "noreply@github.com"})
    commit("fix: tidy (#5)\n\nDry run: #1 #2 #3 still green.", "2026-10-06T09:00:00Z")
    commit("docs: typo", "2026-10-06T10:00:00Z")
    commit("chore(deps): bump x (#6)", "2026-10-07T10:00:00Z",
           env={"GIT_AUTHOR_NAME": "dependabot[bot]",
                "GIT_AUTHOR_EMAIL": "49699333+dependabot[bot]@users.noreply.github.com"})
    commit(f"chore: back out b (#7)\n\nThis reverts commit {c2[:10]}.",
           "2026-10-08T10:00:00Z")
    return r


def self_test() -> int:
    fails = []

    def check(cond, what):
        if not cond:
            fails.append(what)

    # 1. Wilson against hand-computed values
    lo, hi = wilson(0, 20)
    check(lo == 0.0 and abs(hi - 0.16113) < 1e-4, f"wilson 0/20 upper {hi:.5f} != 0.16113")
    lo, hi = wilson(3, 100)
    check(abs(lo - 0.010256) < 1e-4 and abs(hi - 0.084502) < 1e-4,
          f"wilson 3/100 = [{lo:.5f}, {hi:.5f}], want [0.01026, 0.08450]")
    check(wilson(0, 0) is None and rate(0, 0)["per100"] is None, "n=0 must be n/a")
    check(fmt_rate(rate(3, 100)) == "3.0 [1.0, 8.5] (3/100)",
          f"fmt_rate 3/100 gave {fmt_rate(rate(3, 100))}")

    # 2. authoring class
    co = "x\n\nCo-Authored-By: Claude {} <noreply@anthropic.com>"
    hu = [("Ann", "ann@example.org")]
    check(model_class([co.format("Opus 5.5")], hu) == "claude-opus-5.5", "named model")
    check(model_class([co.format("Opus 4.8 (1M context)")], hu) == "claude-opus-4.8",
          "model with parenthetical")
    check(model_class([co.format("Opus 5.5"), co.format("Sonnet 4.5")], hu) == "mixed",
          "two models must be mixed")
    check(model_class(["x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"], hu)
          == "claude-unnamed", "unnamed trailer")
    check(model_class(["x\n\nhttps://claude.ai/code/session_X1"], hu) == "claude-unnamed",
          "session link only")
    check(model_class(["x"], [("Claude", "noreply@anthropic.com")]) == "claude-unnamed",
          "anthropic author")
    check(model_class(["x"], hu) == "human-only", "no marker is human-only")
    check(model_class(["x"], [("dependabot[bot]", "1+dependabot[bot]@users.noreply."
                               "github.com")]) == "bot", "bot author")
    check(change_type("feat(x)!: y") == "feat" and change_type("Revert \"a\"") == "revert"
          and change_type("Update readme") == "non-conventional", "change type")

    # 3. git parsing, unit grouping, revert and hotfix linkage on a real repo
    with tempfile.TemporaryDirectory() as td:
        repo = _fixture_repo(pathlib.Path(td))
        rows = first_parent_log(repo, "main")
        units = build_units("fx", rows)
        revert_signals(units)
        hotfix_signals(units)
    check(len(units) == 8, f"want 8 units on first-parent main, got {len(units)}")
    if len(units) == 8:
        check([u["pr"] for u in units] == [1, 2, 3, 4, 5, None, 6, 7],
              f"PR numbers {[u['pr'] for u in units]}")
        check([u["model"] for u in units] ==
              ["claude-opus-5.5", "claude-opus-4.8", "human-only", "claude-opus-4.8",
               "human-only", "human-only", "bot", "human-only"], f"models {[u['model'] for u in units]}")
        k1 = sorted(s["kind"] for s in units[0]["signals"])
        check(k1 == ["hotfix-ref", "revert"], f"#1 signals {k1}")
        k2 = [s["kind"] for s in units[1]["signals"]]
        check(k2 == ["revert"], f"#2 reverted by sha only (no Revert subject): {k2}")
        check(all(not u["signals"] for u in units[2:]), "only #1 and #2 may carry signals")
        check(units[5]["flags"] == ["no-pr"], "direct push flagged no-pr")
        k1h = [s for s in units[0]["signals"] if s["kind"] == "hotfix-ref"]
        check(k1h and k1h[0]["by_pr"] == [2],
              f"hotfix-ref on #1 must come from #2 only (not a revert, not an "
              f"inventory line): {k1h}")
        check(units[0]["sessions"] == ["https://claude.ai/code/session_abc"], "session")

    # 4. main-red: a streak is charged once, to its first commit; other events ignored
    us = [{"repo": "fx", "pr": i, "sha": f"s{i}", "shas": [f"s{i}"], "signals": [],
           "flags": [], "date": f"2026-10-0{i}T00:00:00Z"} for i in range(1, 7)]
    ci = lambda c, ev="push", wf="CI": {"event": ev, "workflow": wf, "conclusion": c}
    suites = {"s0": [ci("FAILURE")], "s1": [ci("FAILURE")],
              "s2": [ci("SUCCESS"), ci("FAILURE", "schedule", "Nightly")],
              "s3": [ci("FAILURE")], "s4": [ci("FAILURE")],
              "s5": [ci("CANCELLED"), ci("FAILURE", "schedule"), ci("SUCCESS", wf="D")],
              "s6": [ci("FAILURE"), ci("FAILURE", "merge_group", "D")]}
    main_red_signals(us, suites, "s0")
    got = [(u["pr"], s.get("workflow")) for u in us for s in u["signals"]]
    check(got == [(3, "CI"), (6, "D")],
          f"main-red attribution {got}, want [(3, 'CI'), (6, 'D')]")

    # 5. PR-side: pr-red and ejection are catches, not escapes; late merge flagged
    pr = {"url": "u", "mergedAt": "2026-10-01T12:00:00Z", "headRefOid": "h",
          "commits": {"nodes": [{"commit": {"oid": "a", "statusCheckRollup":
                                            {"state": "FAILURE"}}},
                                {"commit": {"oid": "h", "statusCheckRollup":
                                            {"state": "SUCCESS"}}}]},
          "timelineItems": {"nodes": [{"__typename": "RemovedFromMergeQueueEvent",
                                       "reason": "FAILED_CHECKS", "createdAt": "t"}]},
          "head": {"nodes": [{"commit": {"oid": "h", "checkSuites": {"nodes": [
              {"status": "COMPLETED", "workflowRun": {"event": "pull_request",
                                                      "createdAt": "2026-10-01T11:00:00Z"},
               "checkRuns": {"nodes": [{"completedAt": "2026-10-01T12:05:00Z"}]}}]}}}]}}
    u = {"signals": [], "flags": []}
    pr_signals(u, pr)
    kinds = sorted(s["kind"] for s in u["signals"])
    check(kinds == ["mq-ejected", "pr-red"], f"PR signals {kinds}")
    check(u["flags"] == ["merged-before-ci"], f"PR flags {u['flags']}")
    u2 = {"signals": [], "flags": []}
    pr2 = json.loads(json.dumps(pr))
    pr2["commits"]["nodes"] = [{"commit": {"oid": "h", "statusCheckRollup":
                                           {"state": "FAILURE"}}}]
    pr2["timelineItems"]["nodes"] = []
    pr_signals(u2, pr2)
    check(u2["signals"] == [] and "merged-red-head" in u2["flags"],
          f"a red head is merged-red-head, not a catch: {u2}")
    o = outcome(u)
    check(o == {"escape": False, "strict": False, "caught": True, "incident": True},
          f"ejection must be a catch and an owner-def incident, not an escape: {o}")
    agg = aggregate([dict(signals=[], flags=[], g="x") for _ in range(20)],
                    lambda v: v["g"])["x"]
    check(agg["escape"]["per100"] == 0 and abs(agg["escape"]["hi"] - 16.11) < 0.01 and
          agg["catch_share"]["per100"] is None, f"aggregate 0/20 {agg['escape']}")
    mix = [{"signals": [{"kind": "main-red"}, {"kind": "revert"}], "flags": [], "g": 1}] + \
        [{"signals": [], "flags": [], "g": 1} for _ in range(99)]
    a1 = aggregate(mix, lambda v: v["g"])[1]
    check(a1["escape"]["k"] == 1, "a unit with two signals counts once")
    hx = [{"signals": [{"kind": "hotfix-ref"}], "flags": [], "g": 1}]
    a2 = aggregate(hx, lambda v: v["g"])[1]
    check(a2["escape"]["k"] == 1 and a2["strict"]["k"] == 0,
          "strict escape must exclude hotfix-ref")

    # 6. ledger closure rule
    good = {"id": "I1", "kind": "escape", "status": "closed",
            "change": {"repo": "r", "pr": 1, "model": "human-only"},
            "net": {"class": "vacuous-gate", "source": "manual"},
            "why": {"classifier": "gate could not fail", "source": "manual",
                    "evidence": ["https://github.com/pulseengine/r/pull/1"]},
            "countermeasure": {"gate": "g", "merged": True,
                               "pr": "https://github.com/pulseengine/r/pull/2",
                               "negative_control": "red on old bug: https://x/run/1"}}
    check(check_entries([good]) == [], f"valid closed entry rejected: {check_entries([good])}")
    for broken, what in (({"negative_control": ""}, "no negative control"),
                         ({"negative_control": "seen red, trust me"}, "control w/o link"),
                         ({"merged": False}, "unmerged countermeasure"),
                         ({"pr": "fix later"}, "countermeasure not a PR URL")):
        e = json.loads(json.dumps(good))
        e["countermeasure"].update(broken)
        check(check_entries([e]) != [], f"closed entry with {what} accepted")
    e = json.loads(json.dumps(good))
    e["net"]["class"] = "bad luck"
    check(check_entries([e]) != [], "unknown net class accepted")
    check(check_entries([good, good]) != [], "duplicate id accepted")

    lu = [{"repo": "r", "pr": 1, "shas": ["abc1"], "signals": []},
          {"repo": "r", "pr": 2, "shas": ["def2"], "signals": []}]
    apply_ledger(lu, [dict(good, id="E", change={"repo": "r", "pr": 1}),
                      dict(good, id="N", kind="near-miss", change={"repo": "r", "pr": 2})])
    check([len(x["signals"]) for x in lu] == [1, 0] and outcome(lu[0])["escape"],
          "a ledger escape must count as an escape; a near-miss must not")

    # 7. rendering: kiln titles withheld, no local paths
    ku = {"repo": "kiln", "pr": 9, "sha": "k" * 40, "shas": ["k" * 40], "date":
          "2026-10-01T00:00:00Z", "month": "2026-10", "type": "fix", "model": "human-only",
          "subject": "fix: secret detail", "sessions": [], "flags": [],
          "signals": [{"kind": "main-red"}]}
    md = render_md(summarise([ku], [], {"since": "a", "until": "b"}, ["kiln"], True))
    check("secret detail" not in md and "(title withheld)" in md,
          "a withheld repo's title must stay withheld even with --titles")
    ku2 = dict(ku, repo="other", subject="fix: plain detail")
    md = render_md(summarise([ku2], [], {"since": "a", "until": "b"}, ["other"]))
    check("plain detail" not in md and "| title |" not in md,
          "no titles in the default (committed) output")
    check("/Users/" not in md and ".cache" not in md, "no local path in report")

    for f in fails:
        print(f"self-test FAIL: {f}", file=sys.stderr)
    print(f"incident-ledger self-test: {'FAIL' if fails else 'ok'} "
          f"({len(fails)} failure(s))")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--days", type=int, default=90)
    r.add_argument("--since")
    r.add_argument("--until")
    r.add_argument("--repos")
    r.add_argument("--baseline", help="comma-separated repos to compute a pre-agent "
                   "baseline for")
    r.add_argument("--ledger", default=str(LEDGER))
    r.add_argument("--json")
    r.add_argument("--md")
    r.add_argument("--offline", action="store_true", help="cache only, no network")
    r.add_argument("--titles", action="store_true", help="add PR titles to the "
                   "incident table, for local triage; never commit that output")
    c = sub.add_parser("check-ledger")
    c.add_argument("--ledger", default=str(LEDGER))
    a = ap.parse_args()
    return cmd_run(a) if a.cmd == "run" else cmd_check_ledger(a)


if __name__ == "__main__":
    sys.exit(main())
