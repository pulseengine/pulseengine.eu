#!/usr/bin/env python3
# rivet: verifies REQ-SEAM-CONTRACT-CHECK
"""seam-check: mechanically check the cross-repo seam contracts written in issues.

A seam contract is the agreed interface between two repos, written as a fenced
```seam block (strict YAML) in an issue body or comment. This finds the blocks,
checks each one, and resolves its interface reference against the provider's
default branch, so a contract that has drifted from the code goes red instead of
staying true only in prose.

Usage:
  seam-check.py                          discover open issues labelled `seam` in the org
  seam-check.py --issue OWNER/REPO#N     check the blocks on these issues only (repeatable)
  seam-check.py --block FILE             check a drafted block before posting it (repeatable)
  seam-check.py --party OWNER/REPO       only the seams this repo provides or consumes
  seam-check.py --fixtures DIR           offline: issues and files come from DIR/world.json
  seam-check.py --format json            machine output (schema seam-check.v1), e.g. for warte
  seam-check.py --stale-days N           warn when a decision is older than N days and not
                                         implemented (default 30); --strict makes warnings fail
  seam-check.py --now YYYY-MM-DD         the date staleness is measured against (default: today, UTC)
  seam-check.py --self-test              run the built-in fixtures and negative controls

GitHub access is REST over curl (urllib when curl is absent), never the gh CLI,
because the self-hosted runners have none. The token is GITHUB_TOKEN or GH_TOKEN,
else `gh auth token` when gh happens to be installed, else none (60 requests an
hour). The token is sent only to the GitHub API host.

Blind spots, stated so a green run is not over-read: an issue that carries a
block but not the `seam` label is not discovered; a private repo the token cannot
read is an infra error (exit 2), not a pass; only open issues are discovered.

Exit: 0 every seam passes · 1 a violation (or, with --strict, a warning), or no
seam found at all · 2 could not check (API failure, rate limit, unreadable repo,
missing PyYAML). A failure to reach the evidence never reads as a pass.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

SCHEMA = "seam-check.v1"
BLOCK_FORMAT = 1
KINDS = ("hal", "consumption", "wire", "identity", "other")
STATUSES = ("proposed", "options", "decided", "implemented", "broken")
DECIDED = ("decided", "implemented")
IFACE_KINDS = ("wit", "file")
GITHUB_API = "https://api.github.com"

FENCE = re.compile(r"^```seam[ \t]*\r?\n(.*?)^```[ \t]*\r?$", re.M | re.S)
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SEAM_ID = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WIT_PACKAGE = re.compile(r"^\s*package\s+([a-z0-9-]+:[a-z0-9-]+(?:/[a-z0-9-]+)*)@([0-9A-Za-z.+-]+)\s*;", re.M)

# key -> (required, type). Types: str, int, map, list, "map|list".
TOP = {
    "format": (True, int), "seam": (True, str), "kind": (True, str), "status": (True, str),
    "provider": (True, dict), "consumers": (True, list), "interface": (True, "map|list"),
    "options": (False, list), "recommendation": (False, str), "decisions": (False, list),
    "implemented_by": (False, str), "open_questions": (False, list), "notes": (False, str),
}
PROVIDER = {"repo": (True, str), "promise": (True, str), "guard": (False, "str|list")}
CONSUMER = {"repo": (True, str), "binding": (True, str), "guard": (False, "str|list")}
IFACE = {
    "kind": (True, str), "path": (True, str), "repo": (False, str), "ref": (False, str),
    "package": (False, str), "version": (False, str), "interfaces": (False, list),
    "symbols": (False, list),
}
OPTION = {"id": (True, str), "summary": (True, str)}
DECISION = {
    "summary": (True, str), "option": (False, str), "decided_by": (True, str),
    "date": (True, str), "ref": (False, str),
}
QUESTION = {"q": (True, str), "owner": (True, str), "ref": (False, str)}


class InfraError(Exception):
    """The evidence could not be reached. Always exit 2, never a pass."""


# ── strict YAML ─────────────────────────────────────────────────────────────

def _loader():
    try:
        import yaml
    except ImportError:
        raise InfraError("PyYAML is required (pip install pyyaml)")

    class Strict(yaml.SafeLoader):
        pass

    # Dates stay strings: an unquoted 2026-10-21 must not become a date object
    # whose formatting differs from what the author wrote.
    Strict.yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def mapping(loader, node, deep=False):
        seen = set()
        for k, _ in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate key %r" % (key,), k.start_mark)
            seen.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml, Strict


def parse_block(text: str):
    """Return (data, error). data is None when the block is not a valid mapping."""
    yaml, strict = _loader()
    try:
        data = yaml.load(text, Loader=strict)  # noqa: S506 (Strict derives from SafeLoader)
    except yaml.YAMLError as e:
        return None, "block is not valid YAML: %s" % str(e).replace("\n", " ")
    if not isinstance(data, dict):
        return None, "block must be a YAML mapping"
    return data, None


def blocks_in(text: str) -> list[str]:
    return [m.group(1) for m in FENCE.finditer(text or "")]


# ── transports: where issues and files come from (swappable) ───────────────

class Fixtures:
    """Offline world: DIR/world.json lists issues and files. No network."""

    def __init__(self, root: str):
        self.root = root
        try:
            with open(os.path.join(root, "world.json"), encoding="utf-8") as f:
                self.world = json.load(f)
        except (OSError, ValueError) as e:
            raise InfraError("cannot read fixture world %s: %s" % (root, e))
        self.fail = set(self.world.get("fail", []))

    def name(self) -> str:
        return "fixtures:%s" % self.root

    def _issue(self, i: dict) -> dict:
        def body(d):
            if "body_file" in d:
                with open(os.path.join(self.root, d["body_file"]), encoding="utf-8") as f:
                    return f.read()
            return d.get("body", "")
        return {
            "repo": i["repo"], "number": i["number"], "title": i.get("title", ""),
            "url": i.get("url", "https://github.com/%s/issues/%s" % (i["repo"], i["number"])),
            "labels": i.get("labels", []), "body": body(i),
            "comments": [{"id": c.get("id", n), "created_at": c.get("created_at", ""),
                          "body": body(c)} for n, c in enumerate(i.get("comments", []))],
        }

    def discover(self, org: str, label: str) -> list[dict]:
        if "search" in self.fail:
            raise InfraError("fixture: search failed")
        return [self._issue(i) for i in self.world.get("issues", [])
                if label in i.get("labels", []) and i.get("state", "open") == "open"
                and i["repo"].split("/")[0] == org]

    def issue(self, repo: str, number: int) -> dict:
        for i in self.world.get("issues", []):
            if i["repo"] == repo and i["number"] == number:
                return self._issue(i)
        raise InfraError("fixture: no issue %s#%d" % (repo, number))

    def default_branch(self, repo: str) -> str:
        if "repo" in self.fail or repo not in self.world.get("files", {}):
            raise InfraError("fixture: repo %s is not readable" % repo)
        return self.world.get("default_branch", {}).get(repo, "main")

    def read_file(self, repo: str, path: str, ref: str):
        """Text of the file, '' for a presence-only entry, None when absent."""
        files = self.world.get("files", {}).get(repo)
        if files is None:
            raise InfraError("fixture: repo %s is not readable" % repo)
        if path not in files:
            return None
        if files[path] is None:
            return ""
        with open(os.path.join(self.root, files[path]), encoding="utf-8") as f:
            return f.read()


class GitHub:
    """GitHub REST over curl (or urllib). Issues are the transport today; agora
    later is another class with the same four methods."""

    def __init__(self, api: str, token: str | None, http: str = "auto"):
        self.api = api.rstrip("/")
        self.token = token
        self.http = ("curl" if shutil.which("curl") else "urllib") if http == "auto" else http
        self._branches: dict[str, str] = {}

    def name(self) -> str:
        return "github:%s" % self.api

    def _get(self, url: str, accept: str = "application/vnd.github+json"):
        headers = {"Accept": accept, "User-Agent": "seam-check",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if self.http == "curl":
            return self._curl(url, headers)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (api is http(s))
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
        except (urllib.error.URLError, OSError) as e:
            raise InfraError("GET %s failed: %s" % (url, e))

    def _curl(self, url: str, headers: dict):
        with tempfile.TemporaryDirectory() as d:
            hfile, out, dump = (os.path.join(d, n) for n in ("req", "body", "resp"))
            # Headers from a 0600 file, so the token never appears in argv.
            fd = os.open(hfile, os.O_WRONLY | os.O_CREAT, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write("".join("%s: %s\n" % kv for kv in headers.items()))
            p = subprocess.run(
                ["curl", "-sS", "--max-time", "30", "-H", "@" + hfile, "-D", dump,
                 "-o", out, "-w", "%{http_code}", url],
                capture_output=True, text=True)
            if p.returncode != 0:
                raise InfraError("GET %s failed: curl exit %d: %s" % (url, p.returncode, p.stderr.strip()))
            status = int(p.stdout.strip() or 0)
            hdrs: dict[str, str] = {}
            with open(dump, encoding="latin-1") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        hdrs[k.strip().lower()] = v.strip()
            with open(out, "rb") as f:
                return status, hdrs, f.read()

    def _json(self, url: str):
        status, hdrs, body = self._get(url)
        if status != 200:
            raise InfraError("GET %s -> HTTP %d%s" % (url, status, _rate_note(hdrs)))
        try:
            return json.loads(body.decode("utf-8")), hdrs
        except ValueError as e:
            raise InfraError("GET %s -> unparseable JSON: %s" % (url, e))

    def _pages(self, url: str):
        """Every page, by the Link header. One page of 30 silently drops the rest."""
        while url:
            data, hdrs = self._json(url)
            yield data
            m = re.search(r'<([^>]+)>;\s*rel="next"', hdrs.get("link", ""))
            url = m.group(1) if m else ""

    def _comments(self, repo: str, number: int) -> list[dict]:
        out = []
        for page in self._pages("%s/repos/%s/issues/%d/comments?per_page=100" % (self.api, repo, number)):
            out += [{"id": c["id"], "created_at": c.get("created_at", ""), "body": c.get("body") or "",
                     "url": c.get("html_url", "")} for c in page]
        return out

    def _issue_of(self, i: dict, repo: str) -> dict:
        return {"repo": repo, "number": i["number"], "title": i.get("title", ""),
                "url": i.get("html_url", ""), "labels": [lb["name"] for lb in i.get("labels", [])],
                "body": i.get("body") or "", "comments": self._comments(repo, i["number"])}

    def discover(self, org: str, label: str) -> list[dict]:
        q = urllib.parse.quote("org:%s label:%s is:issue is:open" % (org, label))
        out = []
        for page in self._pages("%s/search/issues?q=%s&per_page=100" % (self.api, q)):
            if page.get("incomplete_results"):
                raise InfraError("issue search returned incomplete_results; refusing a partial answer")
            for i in page.get("items", []):
                repo = "/".join(i["repository_url"].rstrip("/").split("/")[-2:])
                out.append(self._issue_of(i, repo))
        return out

    def issue(self, repo: str, number: int) -> dict:
        data, _ = self._json("%s/repos/%s/issues/%d" % (self.api, repo, number))
        return self._issue_of(data, repo)

    def default_branch(self, repo: str) -> str:
        if repo not in self._branches:
            data, _ = self._json("%s/repos/%s" % (self.api, repo))
            self._branches[repo] = data["default_branch"]
        return self._branches[repo]

    def read_file(self, repo: str, path: str, ref: str):
        url = "%s/repos/%s/contents/%s?ref=%s" % (
            self.api, repo, urllib.parse.quote(path), urllib.parse.quote(ref))
        status, hdrs, body = self._get(url, accept="application/vnd.github.raw")
        if status == 404:
            return None  # the repo answered (default_branch succeeded): the file is absent
        if status != 200:
            raise InfraError("GET %s -> HTTP %d%s" % (url, status, _rate_note(hdrs)))
        return body.decode("utf-8", errors="replace")


def _rate_note(hdrs: dict) -> str:
    if hdrs.get("x-ratelimit-remaining") == "0":
        return " (rate limit exhausted; resets at %s)" % hdrs.get("x-ratelimit-reset", "?")
    return ""


def resolve_token(api: str, env=None) -> str | None:
    env = os.environ if env is None else env
    if api.rstrip("/") not in (GITHUB_API, env.get("GITHUB_API_URL", GITHUB_API).rstrip("/")):
        return None  # never send a GitHub token to any other host
    tok = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if tok:
        return tok
    if shutil.which("gh"):
        p = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()
    return None


# ── rules ───────────────────────────────────────────────────────────────────

def _shape(obj, spec: dict, where: str, out: list, missing: dict | None = None):
    """Required keys, types, unknown keys. Appends (rule, message). `missing`
    names the rule a missing field reports under, when it is not `required`."""
    if not isinstance(obj, dict):
        out.append(("required", "%s must be a mapping" % where))
        return False
    for k in obj:
        if k not in spec:
            out.append(("unknown-key", "%s: unknown key %r (strict schema)" % (where, k)))
    ok = True
    for k, (req, typ) in spec.items():
        if k not in obj or obj[k] is None or obj[k] == "":
            if req:
                out.append(((missing or {}).get(k, "required"), "%s: missing required field %r" % (where, k)))
                ok = False
            continue
        v = obj[k]
        good = {str: isinstance(v, str), int: isinstance(v, int) and not isinstance(v, bool),
                dict: isinstance(v, dict), list: isinstance(v, list),
                "map|list": isinstance(v, (dict, list)),
                "str|list": isinstance(v, str) or (isinstance(v, list) and bool(v)
                                                   and all(isinstance(x, str) and x for x in v))}[typ]
        if not good:
            hint = " (quote it)" if typ is str else ""
            out.append(("required", "%s.%s must be %s, got %s%s" % (
                where, k, getattr(typ, "__name__", typ), type(v).__name__, hint)))
            ok = False
    return ok


def _date(s: str):
    if not isinstance(s, str) or not DATE.match(s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def check_block(d: dict, now: datetime.date, stale_days: int) -> tuple[list, list]:
    """Structural rules. Returns (violations, warnings), each a list of (rule, message)."""
    v: list = []
    w: list = []
    _shape(d, TOP, "seam", v)
    if d.get("format") not in (None, BLOCK_FORMAT) and isinstance(d.get("format"), int):
        v.append(("enum", "format must be %d, got %r" % (BLOCK_FORMAT, d["format"])))
    sid = d.get("seam")
    if isinstance(sid, str) and not SEAM_ID.match(sid):
        v.append(("required", "seam id %r must match %s" % (sid, SEAM_ID.pattern)))
    if isinstance(d.get("kind"), str) and d["kind"] not in KINDS:
        v.append(("enum", "kind %r is not one of %s" % (d["kind"], "/".join(KINDS))))
    status = d.get("status")
    if isinstance(status, str) and status not in STATUSES:
        v.append(("enum", "status %r is not one of %s" % (status, "/".join(STATUSES))))

    # Both sides name an owner repo.
    parties = set()
    prov = d.get("provider")
    if _shape(prov, PROVIDER, "provider", v, {"repo": "owner"}) and isinstance(prov.get("repo"), str):
        if not REPO.match(prov["repo"]):
            v.append(("owner", "provider.repo %r is not OWNER/REPO" % prov["repo"]))
        parties.add(prov["repo"])
    cons = d.get("consumers")
    if isinstance(cons, list):
        if not cons:
            v.append(("owner", "consumers is empty: a seam needs at least one consumer"))
        for n, c in enumerate(cons):
            if _shape(c, CONSUMER, "consumers[%d]" % n, v, {"repo": "owner"}) and isinstance(c.get("repo"), str):
                if not REPO.match(c["repo"]):
                    v.append(("owner", "consumers[%d].repo %r is not OWNER/REPO" % (n, c["repo"])))
                if isinstance(prov, dict) and c["repo"] == prov.get("repo"):
                    v.append(("owner", "consumers[%d].repo is the provider: a seam has two sides" % n))
                parties.add(c["repo"])

    # Interface entries: shape only here; resolution needs the transport.
    ifaces = d.get("interface")
    for n, it in enumerate(ifaces if isinstance(ifaces, list) else [ifaces] if ifaces else []):
        where = "interface[%d]" % n
        if not _shape(it, IFACE, where, v):
            continue
        k = it.get("kind")
        if k not in IFACE_KINDS:
            v.append(("enum", "%s.kind %r is not one of %s" % (where, k, "/".join(IFACE_KINDS))))
        elif k == "wit" and not (it.get("package") and it.get("version")):
            v.append(("required", "%s: a wit interface needs package and version" % where))
        elif k == "file" and not it.get("symbols"):
            v.append(("required", "%s: a file interface needs symbols (literal text that must appear)" % where))
        for key in ("interfaces", "symbols"):
            if isinstance(it.get(key), list) and not all(isinstance(s, str) and s for s in it[key]):
                v.append(("required", "%s.%s must be a list of non-empty strings" % (where, key)))

    # Every open question has an owner, and the owner is a side of this seam.
    for n, q in enumerate(d.get("open_questions") or []):
        if _shape(q, QUESTION, "open_questions[%d]" % n, v):
            if q["owner"] not in parties:
                v.append(("question-owner", "open_questions[%d].owner %r is not a party to this seam (%s)"
                          % (n, q["owner"], ", ".join(sorted(parties)) or "none")))
        elif isinstance(q, dict) and not q.get("owner"):
            v.append(("question-owner", "open_questions[%d] has no owner" % n))

    option_ids = []
    for n, o in enumerate(d.get("options") or []):
        if _shape(o, OPTION, "options[%d]" % n, v):
            option_ids.append(o["id"])
    if status == "options":
        if len(option_ids) < 2:
            v.append(("options", "status options needs at least two options, has %d" % len(option_ids)))
        rec = d.get("recommendation")
        if not rec:
            v.append(("options", "status options needs a recommendation naming one option"))
        elif rec not in option_ids:
            v.append(("options", "recommendation %r is not an option id (%s)" % (rec, ", ".join(option_ids))))

    # Decided means a decision with who and when.
    decisions = d.get("decisions") or []
    latest = None
    for n, dec in enumerate(decisions):
        if not _shape(dec, DECISION, "decisions[%d]" % n, v, {"date": "decision", "decided_by": "decision"}):
            continue
        day = _date(dec["date"])
        if day is None:
            v.append(("decision", "decisions[%d].date %r is not YYYY-MM-DD" % (n, dec["date"])))
        elif day > now:
            v.append(("decision", "decisions[%d].date %s is in the future" % (n, dec["date"])))
        elif latest is None or day > latest:
            latest = day
        if dec.get("option") and option_ids and dec["option"] not in option_ids:
            v.append(("decision", "decisions[%d].option %r is not an option id (%s)"
                      % (n, dec["option"], ", ".join(option_ids))))
    if status in DECIDED and not decisions:
        v.append(("decision", "status %s needs at least one entry in decisions" % status))
    if status == "implemented" and not d.get("implemented_by"):
        v.append(("implemented", "status implemented needs implemented_by (the PR or release that landed it)"))
    if status == "broken":
        v.append(("broken", "the seam is marked broken: the provider and consumers must settle it"))
    if status == "decided" and latest is not None and (now - latest).days > stale_days:
        w.append(("stale", "decided %s, %d days ago, and not implemented (threshold %d days)"
                  % (latest.isoformat(), (now - latest).days, stale_days)))
    return v, w


def resolve(d: dict, src) -> tuple[list, list]:
    """Interface and guard resolution against the repos. Returns (violations, resolved)."""
    v: list = []
    resolved: list = []
    prov = (d.get("provider") or {}).get("repo") if isinstance(d.get("provider"), dict) else None
    ifaces = d.get("interface")
    for n, it in enumerate(ifaces if isinstance(ifaces, list) else [ifaces] if ifaces else []):
        if not isinstance(it, dict) or it.get("kind") not in IFACE_KINDS or not isinstance(it.get("path"), str):
            continue
        repo = it.get("repo") or prov
        if not isinstance(repo, str) or not REPO.match(repo):
            continue
        ref = it.get("ref") or src.default_branch(repo)
        where = "interface[%d] %s:%s@%s" % (n, repo, it["path"], ref)
        text = src.read_file(repo, it["path"], ref)
        rec = {"repo": repo, "path": it["path"], "ref": ref, "found": text is not None}
        resolved.append(rec)
        if text is None:
            v.append(("interface-missing", "%s does not exist" % where))
            continue
        if it["kind"] == "wit" and it.get("package") and it.get("version"):
            m = WIT_PACKAGE.search(text)
            if not m:
                v.append(("interface-version", "%s has no `package name@version;` line" % where))
            else:
                rec["found_package"], rec["found_version"] = m.group(1), m.group(2)
                if m.group(1) != it["package"]:
                    v.append(("interface-version", "%s declares package %s, the block says %s"
                              % (where, m.group(1), it["package"])))
                if m.group(2) != str(it["version"]):
                    v.append(("interface-version", "%s is at @%s, the block says @%s: update the block "
                              "(or pin ref:) and tell the consumers" % (where, m.group(2), it["version"])))
            for name in it.get("interfaces") or []:
                if isinstance(name, str) and not re.search(r"^\s*interface\s+%s\s*\{" % re.escape(name), text, re.M):
                    v.append(("interface-symbol", "%s declares no `interface %s`" % (where, name)))
        for sym in it.get("symbols") or []:
            if isinstance(sym, str) and sym and sym not in text:
                v.append(("interface-symbol", "%s does not contain %r" % (where, sym)))
    sides = [("provider", d.get("provider"))] + [("consumers[%d]" % n, c)
                                                  for n, c in enumerate(d.get("consumers") or [])]
    for where, side in sides:
        if not (isinstance(side, dict) and isinstance(side.get("repo"), str) and REPO.match(side["repo"])):
            continue
        guards = side.get("guard")
        guards = [guards] if isinstance(guards, str) else guards if isinstance(guards, list) else []
        for g in guards:
            if not isinstance(g, str) or not g:
                continue
            ref = src.default_branch(side["repo"])
            if src.read_file(side["repo"], g, ref) is None:
                v.append(("guard-missing", "%s.guard %s:%s@%s does not exist" % (where, side["repo"], g, ref)))
    return v, resolved


# ── driver ──────────────────────────────────────────────────────────────────

def collect(issues: list[dict]) -> tuple[list[dict], list[dict]]:
    """Blocks per issue: the body is canonical; with no block in the body, the
    latest comment carrying one counts. Returns (blocks, issues_without_block)."""
    blocks, empty = [], []
    for i in issues:
        src = {"repo": i["repo"], "issue": i["number"], "url": i.get("url", ""), "in": "body"}
        texts = blocks_in(i.get("body", ""))
        if not texts:
            for c in sorted(i.get("comments", []), key=lambda c: (c.get("created_at", ""), str(c.get("id"))),
                            reverse=True):
                texts = blocks_in(c.get("body", ""))
                if texts:
                    src = dict(src, **{"in": "comment", "comment_id": c.get("id"),
                                       "url": c.get("url") or src["url"]})
                    break
        if not texts:
            empty.append({"repo": i["repo"], "issue": i["number"], "url": i.get("url", "")})
        for t in texts:
            blocks.append({"text": t, "source": src})
    return blocks, empty


def run(argv: list[str], out=None) -> int:
    out = out or sys.stdout
    ap = argparse.ArgumentParser(prog="seam-check.py", description="Check seam contract blocks.")
    ap.add_argument("--org", default="pulseengine")
    ap.add_argument("--label", default="seam")
    ap.add_argument("--issue", action="append", default=[], metavar="OWNER/REPO#N")
    ap.add_argument("--block", action="append", default=[], metavar="FILE")
    ap.add_argument("--party", action="append", default=[], metavar="OWNER/REPO")
    ap.add_argument("--fixtures", metavar="DIR")
    ap.add_argument("--api", default=os.environ.get("GITHUB_API_URL", GITHUB_API))
    ap.add_argument("--http", choices=("auto", "curl", "urllib"), default="auto")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--stale-days", type=int, default=30)
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    ap.add_argument("--now", help="YYYY-MM-DD (default: today, UTC)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()

    now = _date(a.now) if a.now else datetime.datetime.now(datetime.timezone.utc).date()
    if now is None:
        print("error: --now must be YYYY-MM-DD", file=sys.stderr)
        return 2
    report = {"schema": SCHEMA, "now": now.isoformat(), "seams": [], "issues_without_block": [],
              "errors": [], "exit": 2}
    try:
        _loader()
        src = Fixtures(a.fixtures) if a.fixtures else GitHub(a.api, resolve_token(a.api), a.http)
        report["source"] = src.name()
        issues = []
        for spec in a.issue:
            m = re.match(r"^([^#\s]+/[^#\s]+)#(\d+)$", spec)
            if not m:
                print("error: --issue wants OWNER/REPO#N, got %r" % spec, file=sys.stderr)
                return 2
            issues.append(src.issue(m.group(1), int(m.group(2))))
        for path in a.block:
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except OSError as e:
                raise InfraError("cannot read block file %s: %s" % (path, e))
            body = text if blocks_in(text) else "```seam\n%s```\n" % (text if text.endswith("\n") else text + "\n")
            issues.append({"repo": "local", "number": 0, "url": path, "labels": [], "body": body,
                           "comments": []})
        if not a.issue and not a.block:
            issues = src.discover(a.org, a.label)
        blocks, empty = collect(issues)
        report["issues_without_block"] = empty

        seen: dict[str, list] = {}
        for b in blocks:
            data, err = parse_block(b["text"])
            entry = {"id": None, "source": b["source"], "violations": [], "warnings": []}
            if data is None:
                entry["violations"].append({"rule": "parse", "message": err})
            else:
                entry["id"] = data.get("seam") if isinstance(data.get("seam"), str) else None
                for key in ("kind", "status", "provider", "consumers", "interface", "open_questions",
                            "decisions", "implemented_by"):
                    if key in data:
                        entry[key] = data[key]
                parties = {(data.get("provider") or {}).get("repo") if isinstance(data.get("provider"), dict) else None}
                parties |= {c.get("repo") for c in data.get("consumers") or [] if isinstance(c, dict)}
                if a.party and not (parties & set(a.party)):
                    continue
                vio, warn = check_block(data, now, a.stale_days)
                rv, resolved = resolve(data, src)
                entry["resolved"] = resolved
                entry["violations"] += [{"rule": r, "message": m} for r, m in vio + rv]
                entry["warnings"] += [{"rule": r, "message": m} for r, m in warn]
                if entry["id"]:
                    seen.setdefault(entry["id"], []).append(entry)
            if a.party and data is None and b["source"]["repo"] not in a.party:
                continue
            report["seams"].append(entry)
        for sid, entries in seen.items():
            if len(entries) > 1:
                where = ", ".join("%s#%s" % (e["source"]["repo"], e["source"]["issue"]) for e in entries)
                for e in entries:
                    e["violations"].append({"rule": "duplicate-id", "message": "seam id %r appears %d times (%s)"
                                            % (sid, len(entries), where)})
        if not a.party:
            for e in empty:
                report["seams"].append({"id": None, "source": dict(e, **{"in": "issue"}), "warnings": [],
                                        "violations": [{"rule": "no-block", "message":
                                                        "issue carries no ```seam block in its body or comments"}]})
    except InfraError as e:
        report["errors"].append(str(e))
        report["exit"] = 2
        _emit(report, a.format, out)
        return 2

    if not report["seams"]:
        report["errors"].append("no seam blocks found: nothing was checked, which is not a pass")
        report["exit"] = 1
        _emit(report, a.format, out)
        return 1
    bad = any(s["violations"] for s in report["seams"])
    warned = any(s["warnings"] for s in report["seams"])
    report["exit"] = 1 if bad or (a.strict and warned) else 0
    report["summary"] = {
        "seams": len(report["seams"]),
        "failing": sum(1 for s in report["seams"] if s["violations"]),
        "warning": sum(1 for s in report["seams"] if s["warnings"]),
    }
    _emit(report, a.format, out)
    return report["exit"]


def _emit(report: dict, fmt: str, out):
    if fmt == "json":
        out.write(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
        return
    for s in report["seams"]:
        src = s["source"]
        where = "%s#%s" % (src["repo"], src["issue"]) if src["repo"] != "local" else src["url"]
        tag = "FAIL" if s["violations"] else "WARN" if s["warnings"] else "PASS"
        out.write("%s  %s  (%s, %s)\n" % (tag, s.get("id") or "<no id>", where, src.get("in")))
        for f in s["violations"]:
            out.write("      [%s] %s\n" % (f["rule"], f["message"]))
        for f in s["warnings"]:
            out.write("      warn [%s] %s\n" % (f["rule"], f["message"]))
    for e in report["errors"]:
        out.write("error: %s\n" % e)
    out.write("seam-check: exit %d (%s)\n" % (report["exit"], report.get("source", "?")))


# ── self-test: every rule has a negative control ────────────────────────────

GOOD = """\
format: 1
seam: provider-consumer/example
kind: consumption
status: decided
provider:
  repo: acme/provider
  promise: "the WIT package and not changing it without telling the consumer"
  guard: scripts/one-exporter.sh
consumers:
  - repo: acme/consumer
    binding: "the host that calls it"
    guard: tools/check-pin.sh
interface:
  - kind: wit
    path: wit/api.wit
    package: "acme:api"
    version: "0.2.0"
    interfaces: [controller]
  - kind: file
    path: src/wire.rs
    symbols: ["pub const VERSION: u8 = 2;"]
options:
  - id: step
    summary: "synchronous step per tick"
  - id: stream
    summary: "a stream of samples"
recommendation: step
decisions:
  - summary: "step at the core boundary"
    option: step
    decided_by: "acme/consumer maintainer"
    date: "2026-10-20"
open_questions:
  - q: "where does battery-v live?"
    owner: acme/consumer
"""

WIT = "/// api\npackage acme:api@0.2.0;\n\ninterface controller {\n  step: func();\n}\n"
WIRE = "pub const VERSION: u8 = 2;\npub const LEN: usize = 81;\n"


def _world(d: str, body: str, *, comments=None, labels=("seam",), files=None, fail=(), extra_issues=()):
    os.makedirs(d, exist_ok=True)
    for name, text in (("api.wit", WIT), ("wire.rs", WIRE)):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(text)
    world = {
        "issues": [{"repo": "acme/consumer", "number": 1, "labels": list(labels), "body": body,
                    "comments": comments or []}] + list(extra_issues),
        "files": files if files is not None else {
            "acme/provider": {"wit/api.wit": "api.wit", "src/wire.rs": "wire.rs",
                              "scripts/one-exporter.sh": None},
            "acme/consumer": {"tools/check-pin.sh": None},
        },
        "fail": list(fail),
    }
    with open(os.path.join(d, "world.json"), "w", encoding="utf-8") as f:
        json.dump(world, f)
    return d


def _sub(old: str, new: str, text: str = GOOD) -> str:
    assert old in text, old
    return text.replace(old, new, 1)


def _block(text: str) -> str:
    return "Contract below.\n\n```seam\n%s```\n" % text


def _stub_github(routes: dict):
    """A loopback GitHub stand-in, so the real HTTP path runs in CI offline."""
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            path = self.path
            for prefix, (code, headers, body) in routes.items():
                if path.startswith(prefix):
                    break
            else:
                code, headers, body = 404, {}, b'{"message":"Not Found"}'
            if callable(body):
                body = body(self.server.server_address[1])
            self.send_response(code)
            for k, val in headers.items():
                if callable(val):
                    val = val(self.server.server_address[1])
                self.send_header(k, val)
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else body.encode())

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def self_test() -> int:
    import io
    now = ["--now", "2026-10-29", "--org", "acme"]
    cases = []  # (name, world-builder kwargs or None, extra argv, expected)
    mut = [
        ("parse: not YAML", _sub("kind: consumption", "kind: [consumption")),
        ("parse: not a mapping", "- just\n- a list\n"),
        ("parse: duplicate key", _sub("kind: consumption", "kind: consumption\nkind: wire")),
        ("required: unquoted float version", _sub('version: "0.2.0"', "version: 0.2")),
        ("required: missing interface", _sub("interface:\n  - kind: wit", "interfacex:\n  - kind: wit")),
        ("enum: bad kind", _sub("kind: consumption", "kind: api")),
        ("enum: bad status", _sub("status: decided", "status: agreed")),
        ("unknown-key", _sub("kind: consumption", "kind: consumption\nowner: someone")),
        ("owner: consumer without repo", _sub("  - repo: acme/consumer\n    binding", "  - binding")),
        ("owner: provider repo not OWNER/REPO", _sub("repo: acme/provider", "repo: provider")),
        ("owner: consumer is the provider", _sub("  - repo: acme/consumer\n", "  - repo: acme/provider\n")),
        ("owner: no consumers", _sub(
            "consumers:\n  - repo: acme/consumer\n    binding: \"the host that calls it\"\n"
            "    guard: tools/check-pin.sh\n", "consumers: []\n")),
        ("question-owner: missing", _sub("    owner: acme/consumer\n", "")),
        ("question-owner: not a party", _sub("    owner: acme/consumer\n", "    owner: acme/elsewhere\n")),
        ("decision: decided without decisions", _sub("decisions:", "decisionz:")),
        ("decision: no date", _sub('    date: "2026-10-20"\n', "")),
        ("decision: date not ISO", _sub('date: "2026-10-20"', 'date: "20 Oct 2026"')),
        ("decision: date in the future", _sub('date: "2026-10-20"', 'date: "2027-01-01"')),
        ("decision: option not offered", _sub("    option: step", "    option: batch")),
        ("decision: no decided_by", _sub('    decided_by: "acme/consumer maintainer"\n', "")),
        ("options: one option only", _sub("status: decided", "status: options").replace(
            "  - id: stream\n    summary: \"a stream of samples\"\n", "")),
        ("options: no recommendation", _sub("status: decided", "status: options").replace(
            "recommendation: step\n", "")),
        ("options: recommendation not an option", _sub("status: decided", "status: options").replace(
            "recommendation: step", "recommendation: batch")),
        ("implemented: no implemented_by", _sub("status: decided", "status: implemented")),
        ("broken", _sub("status: decided", "status: broken")),
        ("interface-missing", _sub("path: wit/api.wit", "path: wit/gone.wit")),
        ("interface-version: version drift", _sub('version: "0.2.0"', 'version: "0.1.0"')),
        ("interface-version: package drift", _sub('package: "acme:api"', 'package: "acme:other"')),
        ("interface-symbol: WIT interface gone", _sub("interfaces: [controller]", "interfaces: [pilot]")),
        ("interface-symbol: file symbol gone", _sub("VERSION: u8 = 2;", "VERSION: u8 = 3;")),
        ("required: wit without version", _sub('    version: "0.2.0"\n', "")),
        ("required: file without symbols", _sub('    symbols: ["pub const VERSION: u8 = 2;"]\n', "")),
        ("guard-missing", _sub("guard: tools/check-pin.sh", "guard: tools/gone.sh")),
        ("guard-missing: provider guard gone", _sub("guard: scripts/one-exporter.sh", "guard: scripts/gone.sh")),
        ("guard-missing: second guard in a list", _sub("guard: tools/check-pin.sh",
                                                       "guard: [tools/check-pin.sh, tools/gone.sh]")),
        ("required: guard list with a non-string", _sub("guard: tools/check-pin.sh", "guard: [tools/check-pin.sh, 3]")),
    ]
    for name, text in mut:
        cases.append((name, {"body": _block(text)}, now, 1))
    # Each case names the rule that must fire (the text before ':'), so a mutant
    # cannot pass for the wrong reason, e.g. by finding no seam at all.
    cases += [
        ("positive: good block", {"body": _block(GOOD)}, now, 0),
        ("positive: a guard list", {"body": _block(_sub("guard: tools/check-pin.sh", "guard: [tools/check-pin.sh]"))},
         now, 0),
        ("positive: --party keeps it", {"body": _block(GOOD)}, now + ["--party", "acme/provider"], 0),
        ("no-seams: --party filters everything out", {"body": _block(GOOD)}, now + ["--party", "acme/x"], 1),
        ("no-block: labelled, no block", {"body": "prose only"}, now, 1),
        ("no-seams: nothing labelled", {"body": _block(GOOD), "labels": ()}, now, 1),
        ("duplicate-id: across issues", {"body": _block(GOOD), "extra_issues": [
            {"repo": "acme/provider", "number": 7, "labels": ["seam"], "body": _block(GOOD)}]}, now, 1),
        ("positive: body is canonical over a later broken comment",
         {"body": _block(GOOD), "comments": [{"created_at": "2026-10-28T00:00:00Z",
                                              "body": _block(_sub("kind: consumption", "kind: api"))}]}, now, 0),
        ("positive: no body block, the latest comment counts",
         {"body": "prose", "comments": [
             {"created_at": "2026-10-01T00:00:00Z", "body": _block(_sub("kind: consumption", "kind: api"))},
             {"created_at": "2026-10-28T00:00:00Z", "body": _block(GOOD)}]}, now, 0),
        ("enum: no body block, the latest comment is broken", {"body": "prose", "comments": [
            {"created_at": "2026-10-01T00:00:00Z", "body": _block(GOOD)},
            {"created_at": "2026-10-28T00:00:00Z", "body": _block(_sub("kind: consumption", "kind: api"))}]},
         now, 1),
        ("positive: stale is a warning only", {"body": _block(GOOD)}, ["--now", "2027-03-01", "--org", "acme"], 0),
        ("stale: --strict makes it fail", {"body": _block(GOOD)},
         ["--now", "2027-03-01", "--org", "acme", "--strict"], 1),
        ("positive: implemented is never stale", {"body": _block(_sub("status: decided", "status: implemented")
                                                             + "implemented_by: \"acme/provider#9\"\n")},
         ["--now", "2027-03-01", "--org", "acme", "--strict"], 0),
        ("infra: search fails", {"body": _block(GOOD), "fail": ["search"]}, now, 2),
        ("infra: provider repo unreadable", {"body": _block(GOOD), "files": {
            "acme/consumer": {"tools/check-pin.sh": None}}}, now, 2),
    ]

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for n, (name, kw, extra, want) in enumerate(cases):
            d = _world(os.path.join(tmp, "w%d" % n), **kw)
            buf = io.StringIO()
            got = run(["--fixtures", d, "--format", "json"] + extra, out=buf)
            ok = got == want
            fired = sorted({f["rule"] for s in json.loads(buf.getvalue())["seams"]
                            for f in s["violations"] + s["warnings"]})
            rule = name.split(":")[0]
            if want == 1 and not name.startswith("no-seams"):
                ok = ok and rule in fired  # the named rule fired, not some other one
            if name.startswith("no-seams"):
                ok = ok and "no seam blocks found" in buf.getvalue()
            failures += not ok
            print("%s  %-62s exit %d (want %d) %s" % ("ok  " if ok else "FAIL", name, got, want,
                                                      ",".join(fired)))
            if not ok:
                print(buf.getvalue())

        # --block mode, offline: the drafted-block path.
        d = _world(os.path.join(tmp, "blk"), "prose", labels=())
        bf = os.path.join(tmp, "draft.seam")
        for name, text, want in (("positive: --block draft", GOOD, 0),
                                 ("--block draft with version drift", _sub('"0.2.0"', '"0.3.0"'), 1)):
            with open(bf, "w", encoding="utf-8") as f:
                f.write(text)
            got = run(["--fixtures", d, "--block", bf] + now, out=io.StringIO())
            failures += got != want
            print("%s  %-62s exit %d (want %d)" % ("ok  " if got == want else "FAIL", name, got, want))

        # JSON output carries the schema and the exit code (warte reads it).
        buf = io.StringIO()
        run(["--fixtures", _world(os.path.join(tmp, "js"), _block(GOOD)), "--format", "json"] + now, out=buf)
        j = json.loads(buf.getvalue())
        ok = j.get("schema") == SCHEMA and j.get("exit") == 0 and j["seams"][0]["id"] == "provider-consumer/example"
        failures += not ok
        print("%s  %-62s" % ("ok  " if ok else "FAIL", "json: schema, exit and id present"))

    # The real HTTP path against a loopback stub: pagination, raw files, errors.
    def search(port):
        return json.dumps({"incomplete_results": False, "items": [{
            "number": 1, "title": "t", "html_url": "x", "labels": [{"name": "seam"}], "body": "prose",
            "repository_url": "http://127.0.0.1:%d/repos/acme/consumer" % port}]})

    def page1(port):
        return json.dumps([{"id": 1, "created_at": "2026-10-01T00:00:00Z", "body": "no block here"}])

    page2 = json.dumps([{"id": 2, "created_at": "2026-10-28T00:00:00Z", "body": _block(GOOD)}])
    ok_routes = {
        "/search/issues": (200, {}, search),
        "/repos/acme/consumer/issues/1/comments?per_page=100&page=2": (200, {}, page2),
        "/repos/acme/consumer/issues/1/comments": (200, {"Link": lambda p: (
            '<http://127.0.0.1:%d/repos/acme/consumer/issues/1/comments?per_page=100&page=2>; rel="next"' % p)},
            page1),
        "/repos/acme/provider/contents/wit/api.wit": (200, {}, WIT),
        "/repos/acme/provider/contents/src/wire.rs": (200, {}, WIRE),
        "/repos/acme/consumer/contents/tools/check-pin.sh": (200, {}, "#!/bin/sh\n"),
        "/repos/acme/provider/contents/scripts/one-exporter.sh": (200, {}, "#!/bin/sh\n"),
        "/repos/acme/provider": (200, {}, '{"default_branch": "main"}'),
        "/repos/acme/consumer": (200, {}, '{"default_branch": "main"}'),
    }
    http_cases = [
        ("http: block on comment page 2 (pagination)", ok_routes, 0),
        ("http: search 500", dict(ok_routes, **{"/search/issues": (500, {}, "{}")}), 2),
        ("http: rate limited", dict(ok_routes, **{"/search/issues": (
            403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1"}, "{}")}), 2),
        ("http: incomplete search results", dict(ok_routes, **{"/search/issues": (
            200, {}, lambda p: search(p).replace('"incomplete_results": false', '"incomplete_results": true'))}), 2),
        ("http: provider repo 404", {k: r for k, r in ok_routes.items() if k != "/repos/acme/provider"}, 2),
        ("http: interface file 404", {k: r for k, r in ok_routes.items()
                                      if k != "/repos/acme/provider/contents/wit/api.wit"}, 1),
        ("http: interface file 500", dict(ok_routes, **{"/repos/acme/provider/contents/wit/api.wit": (
            500, {}, "{}")}), 2),
    ]
    modes = ["urllib"] + (["curl"] if shutil.which("curl") else [])
    for mode in modes:
        for name, routes, want in http_cases:
            srv = _stub_github(routes)
            api = "http://127.0.0.1:%d" % srv.server_address[1]
            got = run(["--api", api, "--http", mode] + now, out=io.StringIO())
            srv.shutdown()
            failures += got != want
            print("%s  %-62s exit %d (want %d)" % ("ok  " if got == want else "FAIL", "%s [%s]" % (name, mode),
                                                   got, want))

    # The token never leaves for a non-GitHub host.
    tok = resolve_token("http://127.0.0.1:1", {"GITHUB_TOKEN": "secret"})
    failures += tok is not None
    print("%s  %-62s" % ("ok  " if tok is None else "FAIL", "token withheld from a non-GitHub API host"))

    print("seam-check self-test: %s" % ("PASS" if not failures else "%d FAILED" % failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
