#!/usr/bin/env python3
"""Collect the PulseEngine development timeline, month by month.

Delta-first: reads the existing data/timeline.json and only collects months
that are *complete* (strictly before the current calendar month) and not yet
present. A month, once collected, is frozen — including its AI-written `trend`
narrative, which this script never overwrites (it only ever writes `trend: null`
for a brand-new month, to be filled in by the trend step).

Signals per month, across every PUBLIC repo in the org (forks + archived
included — the forks show which upstreams were absorbed, the archived repos show
which directions were retired):

  - born     : repos created that month (fork / archived flagged)
  - released : releases/tags published that month
  - retired  : archived repos, placed by last-push month (approximate)
  - activity : commits, PRs opened, issues opened, and the busiest repos

Usage:
  scripts/collect-timeline.py            # collect any missing complete months
  scripts/collect-timeline.py --force    # recollect all months (drops frozen data)
  scripts/collect-timeline.py --check    # exit non-zero if a complete month is missing

Requires: gh (authenticated), python3.
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ORG = "pulseengine"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "timeline.json"


def gh_json(args: list[str], default=None, retries: int = 4):
    """Run `gh <args>` and parse JSON. Handles the 202 'computing' responses
    the stats endpoints return by retrying with backoff."""
    for attempt in range(retries):
        proc = subprocess.run(["gh", *args], capture_output=True, text=True)
        out = proc.stdout.strip()
        if proc.returncode == 0 and out:
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                return default
        # 202 Accepted (stats not yet computed) → empty body, retry
        if "HTTP 202" in proc.stderr or (proc.returncode == 0 and not out):
            time.sleep(1.5 * (attempt + 1))
            continue
        if attempt == retries - 1:
            sys.stderr.write(f"warn: gh {' '.join(args)} → {proc.stderr.strip()[:200]}\n")
    return default


def month_of(iso: str) -> str:
    return iso[:7]  # "2026-04-13T..." → "2026-04"


def complete_months(start: str, end_exclusive: str) -> list[str]:
    """All 'YYYY-MM' from start up to but excluding end_exclusive (current month)."""
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end_exclusive[:4]), int(end_exclusive[5:7])
    out = []
    while (y, m) < (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def list_repos() -> list[dict]:
    repos = gh_json([
        "repo", "list", ORG, "--limit", "300", "--visibility", "public",
        "--json", "name,createdAt,pushedAt,isFork,isArchived,description,primaryLanguage",
    ], default=[])
    return sorted(repos, key=lambda r: r["createdAt"])


def month_bounds(m: str) -> tuple[str, str]:
    """'2025-03' -> ('2025-03-01T00:00:00Z', '2025-04-01T00:00:00Z')."""
    y, mo = int(m[:4]), int(m[5:7])
    ny, nm = (y + 1, 1) if mo == 12 else (y, mo + 1)
    return f"{y:04d}-{mo:02d}-01T00:00:00Z", f"{ny:04d}-{nm:02d}-01T00:00:00Z"


def commits_by_month(repo: str, months: set[str]) -> dict[str, int]:
    """Exact default-branch commit counts per month via one aliased GraphQL query
    (history(since,until){totalCount}) — no 202 'computing' race like the stats API."""
    keys = {}
    aliases = []
    for i, m in enumerate(sorted(months)):
        since, until = month_bounds(m)
        keys[f"m{i}"] = m
        aliases.append(f'm{i}: history(since:"{since}", until:"{until}"){{ totalCount }}')
    query = ("query($owner:String!,$name:String!){ repository(owner:$owner,name:$name){"
             " defaultBranchRef{ target{ ... on Commit { " + " ".join(aliases) + " } } } } }")
    res = gh_json(["api", "graphql", "-f", f"query={query}",
                   "-F", f"owner={ORG}", "-F", f"name={repo}"], default=None)
    out: dict[str, int] = {}
    if not res:
        return out
    repo_node = (res.get("data") or {}).get("repository") or {}
    ref = repo_node.get("defaultBranchRef") or {}
    target = ref.get("target") or {}
    for key, m in keys.items():
        node = target.get(key)
        if node and node.get("totalCount"):
            out[m] = node["totalCount"]
    return out


def releases_by_month(repo: str) -> list[tuple[str, str]]:
    rels = gh_json(["api", f"repos/{ORG}/{repo}/releases", "--paginate"], default=[])
    out = []
    for r in rels or []:
        published = r.get("published_at") or r.get("created_at")
        if published:
            out.append((month_of(published), r.get("tag_name", "")))
    return out


ISSUES_QUERY = """
query($owner:String!, $name:String!, $cursor:String) {
  repository(owner:$owner, name:$name) {
    issues(first:100, after:$cursor, orderBy:{field:CREATED_AT, direction:ASC}) {
      nodes { createdAt } pageInfo { hasNextPage endCursor }
    }
  }
}"""
PRS_QUERY = ISSUES_QUERY.replace("issues(", "pullRequests(")


def created_by_month(repo: str, query: str, field: str) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    cursor = None
    for _ in range(50):  # cap pagination
        args = ["api", "graphql", "-f", f"query={query}",
                "-F", f"owner={ORG}", "-F", f"name={repo}"]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        res = gh_json(args, default=None)
        if not res:
            break
        conn = res.get("data", {}).get("repository", {}).get(field, {})
        for node in conn.get("nodes", []):
            out[month_of(node["createdAt"])] += 1
        page = conn.get("pageInfo", {})
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
    return dict(out)


def build_months(target_months: set[str]) -> dict[str, dict]:
    repos = list_repos()
    sys.stderr.write(f"collecting {len(target_months)} month(s) across {len(repos)} repos…\n")

    months: dict[str, dict] = {
        m: {"month": m, "born": [], "released": {"count": 0, "repos": []}, "retired": [],
            "activity": {"commits": 0, "prs_opened": 0, "issues_opened": 0, "busiest": []},
            "trend": None}
        for m in target_months
    }
    # per-month per-repo tallies for "busiest" (commits) and grouped releases
    repo_commits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    repo_releases: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for i, r in enumerate(repos, 1):
        name = r["name"]
        sys.stderr.write(f"  [{i}/{len(repos)}] {name}\n")
        bm = month_of(r["createdAt"])
        if bm in months:
            months[bm]["born"].append({
                "name": name, "fork": r["isFork"], "archived": r["isArchived"],
                "lang": (r.get("primaryLanguage") or {}).get("name"),
                "desc": r.get("description") or "",
            })
        if r["isArchived"]:
            rm = month_of(r["pushedAt"])
            if rm in months:
                months[rm]["retired"].append({"name": name})
        for mm, tag in releases_by_month(name):
            if mm in months:
                repo_releases[mm][name] += 1
        # Forks are absorption events, not our development: their default branch
        # carries the entire upstream history (often predating the fork), which
        # would swamp every activity signal. Count activity for our own repos only.
        if r["isFork"]:
            continue
        for mm, c in commits_by_month(name, target_months).items():
            if mm in months:
                months[mm]["activity"]["commits"] += c
                repo_commits[mm][name] += c
        for mm, c in created_by_month(name, PRS_QUERY, "pullRequests").items():
            if mm in months:
                months[mm]["activity"]["prs_opened"] += c
        for mm, c in created_by_month(name, ISSUES_QUERY, "issues").items():
            if mm in months:
                months[mm]["activity"]["issues_opened"] += c

    for m, block in months.items():
        top = sorted(repo_commits.get(m, {}).items(), key=lambda kv: -kv[1])[:4]
        block["activity"]["busiest"] = [{"repo": r, "commits": c} for r, c in top if c]
        rel = sorted(repo_releases.get(m, {}).items(), key=lambda kv: -kv[1])
        block["released"] = {"count": sum(n for _, n in rel),
                             "repos": [{"repo": r, "n": n} for r, n in rel]}
    return months


def main() -> int:
    force = "--force" in sys.argv
    check = "--check" in sys.argv

    existing = {}
    if DATA.exists():
        existing = {b["month"]: b for b in json.loads(DATA.read_text())}

    repos = list_repos()
    if not repos:
        sys.stderr.write("error: no repos returned from gh\n")
        return 2
    start = month_of(min(r["createdAt"] for r in repos))
    now = datetime.now(timezone.utc)
    current = f"{now.year:04d}-{now.month:02d}"
    wanted = complete_months(start, current)

    missing = [m for m in wanted if m not in existing]
    if check:
        stale = [m for m in wanted if m not in existing
                 or existing.get(m, {}).get("trend") in (None, "")]
        if stale:
            sys.stderr.write(
                "timeline is behind — collect + write the development trend for: "
                + ", ".join(stale) + "\n")
            return 1
        print("timeline up to date")
        return 0

    to_collect = set(wanted) if force else set(missing)
    if not to_collect:
        print(f"timeline up to date ({len(wanted)} months, through {wanted[-1]})")
        return 0

    fresh = build_months(to_collect)
    merged = dict(existing)
    for m, block in fresh.items():
        # preserve an existing hand/AI-written trend on --force
        if m in existing and existing[m].get("trend"):
            block["trend"] = existing[m]["trend"]
        merged[m] = block

    ordered = [merged[m] for m in sorted(merged)]
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(ordered, indent=2) + "\n")
    print(f"wrote {len(ordered)} months ({ordered[0]['month']}..{ordered[-1]['month']}); "
          f"collected {len(to_collect)} new")
    empty = [m['month'] for m in ordered if not m.get('trend')]
    if empty:
        print(f"trend still to write for: {', '.join(empty)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
