#!/usr/bin/env python3
"""Report which projects have stopped publishing verification evidence.

The site publishes whatever reports exist. When a project stops attaching its
report asset to releases, the page keeps showing the last one it has, with no
indication the evidence has gone quiet. Measured 2026-10-01, four of ten
projects had stopped and nothing had noticed:

    loom    last report v1.1.13  112 days ago,  9 releases since with none
    synth   last report v0.43.0   78 days ago, 42 releases since with none
    wohl    last report v0.3.0   119 days ago,  3 releases since with none
    sigil   last report v0.10.0   55 days ago,  1 release  since with none

synth was shipping in the layer at 0.78.0 against a 0.43.0 report. A page whose
argument is that claims are checkable should not quietly show evidence that
stopped two months ago.

This does NOT gate CI. Whether an upstream release carries a report is not
something this repository controls, and a site that cannot deploy because
another repo changed its release workflow would be worse than a stale figure.
It runs in the deploy and annotates, so the gap is visible on every publish.

Needs the network and a GitHub token (GITHUB_TOKEN in Actions, or gh auth).

Exit: 0 always unless --strict, which fails when anything is behind · 2 cannot run.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "reports.toml"
# A project that releases rarely is not stale; this many releases with no
# report is the signal that the pipeline stopped rather than paused.
RELEASES_BEHIND = 1


def gh_api(path: str) -> list | dict | None:
    env = dict(os.environ)
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    cmd = ["gh", "api", "--paginate", path]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                             env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    merged: list = []
    for chunk in out.stdout.replace("][", ",").splitlines():
        if not chunk.strip():
            continue
        try:
            parsed = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        merged.extend(parsed if isinstance(parsed, list) else [parsed])
    return merged


def main() -> int:
    strict = "--strict" in sys.argv
    if not CONFIG.is_file():
        print(f"error: expected {CONFIG}", file=sys.stderr)
        return 2
    cfg = tomllib.loads(CONFIG.read_text()).get("projects", {})
    if not cfg:
        print("error: reports.toml lists no projects — the check examined nothing",
              file=sys.stderr)
        return 2

    today = datetime.date.today()
    behind, checked, unreachable = [], 0, []

    for name, project in sorted(cfg.items()):
        releases = gh_api(f"repos/{project['repo']}/releases?per_page=100")
        if releases is None:
            unreachable.append(name)
            continue
        releases = [r for r in releases if not r.get("prerelease")]
        releases.sort(key=lambda r: r.get("published_at") or "", reverse=True)
        if not releases:
            continue
        checked += 1

        since = 0
        last_ok = None
        for release in releases:
            version = release["tag_name"].lstrip("vV")
            want = (project["asset_pattern"]
                    .replace("{name}", name)
                    .replace("{version}", version))
            if want in [a["name"] for a in release.get("assets", [])]:
                last_ok = release
                break
            since += 1

        if since > RELEASES_BEHIND or (since and last_ok is None):
            newest = releases[0]["tag_name"]
            if last_ok:
                when = datetime.date.fromisoformat(last_ok["published_at"][:10])
                behind.append((name, last_ok["tag_name"], (today - when).days,
                               since, newest))
            else:
                behind.append((name, "none in last 100", -1, since, newest))

    print(f"{checked} projects checked, {len(behind)} no longer publishing reports")
    if unreachable:
        print(f"  could not reach: {', '.join(unreachable)}", file=sys.stderr)

    for name, last, days, since, newest in behind:
        age = f"{days} days ago" if days >= 0 else "never"
        line = (f"{name}: last report {last} ({age}); {since} release"
                f"{'s' if since != 1 else ''} since with none; newest is {newest}")
        print(f"  {line}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning title=Report evidence stopped::{line}")

    if behind and strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
