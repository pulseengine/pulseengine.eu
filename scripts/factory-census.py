#!/usr/bin/env python3
"""Cross-repository process census for the PulseEngine org.

    factory-census.py <dir-of-clones> [--issues-org pulseengine] [--json out.json]

`factory-metrics.py` measures one repository in depth and counts Rust. This
measures EVERY repository we author, so a pattern found in two of them can be
checked against the rest rather than assumed to generalise. It is deliberately
language-agnostic: the org ships Rust, Starlark, Python, JavaScript, Shell,
Jinja and C.

What it reports per repo, over first-parent history (one entry per merged PR in
a squash-merge repo), and then as a tally across repos:

- coupling: median and 90th-percentile source files per change, first active
  month against last
- lifecycle: feat and fix share of changes, first half against second half
- backlog: open non-bot issues, and how many are older than 60 days
- the silent-check class: issue titles using the vocabulary of a check that
  passed without checking

Instruments and their blind spots:
- Conventional-commit prefixes are a convention, not a fact about the change.
  The `conv%` column is the share of changes that parse as one at all; a feat or
  fix share means nothing where that share is low, and the tally skips those.
- "Source files" is an extension allowlist. Generated code, vendored trees and
  test fixtures are not separated out.
- Forks are excluded by the caller, because their history is upstream's.
- A repo with few changes carries no signal. `--min-changes` sets the bar for
  inclusion in the tally and defaults to 20; thin repos are still printed.
- Issue provenance is not recoverable: agents file under a human account.
"""
from __future__ import annotations

import argparse
import collections
import math
import datetime as dt
import json
import pathlib
import re
import statistics as st
import subprocess
import sys

SOURCE_EXT = {
    ".rs", ".py", ".js", ".ts", ".tsx", ".mjs", ".sh", ".bash", ".c", ".h",
    ".cpp", ".hpp", ".cc", ".bzl", ".star", ".bazel", ".lean", ".v", ".rq",
    ".jinja", ".j2", ".tera", ".html", ".scss", ".css", ".wit", ".aadl",
}
EXCLUDE_PATH = re.compile(r"(^|/)(vendor|third_party|node_modules|target|dist)/")
SILENT = re.compile(
    r"(?i)silent|never (fires|checked)|no-op|masked|exits 0|cannot fail|blind|"
    r"always green|reports success"
)
CONV = re.compile(r"^(\w+)(\([^)]*\))?!?:")


def git(repo: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def is_source(path: str) -> bool:
    if EXCLUDE_PATH.search(path):
        return False
    return pathlib.PurePosixPath(path).suffix.lower() in SOURCE_EXT


def measure_git(repo: pathlib.Path) -> dict | None:
    out = git(repo, "log", "--first-parent", "--no-merges", "--reverse",
              "--numstat", "--date=short", "--format=@@%ad\t%s")
    if not out.strip():
        return None
    changes, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            day, _, subject = line[2:].partition("\t")
            try:
                d = dt.date.fromisoformat(day)
            except ValueError:
                cur = None
                continue
            cur = {"d": d, "s": subject, "f": []}
            changes.append(cur)
        elif line.strip() and cur is not None:
            parts = line.split("\t", 2)
            if len(parts) == 3:
                cur["f"].append(parts[2])
    if not changes:
        return None

    months = collections.defaultdict(lambda: {"n": 0, "files": [], "conv": 0,
                                              "feat": 0, "fix": 0})
    for c in changes:
        m = months[c["d"].strftime("%Y-%m")]
        m["n"] += 1
        m["files"].append(sum(1 for f in c["f"] if is_source(f)))
        hit = CONV.match(c["s"])
        if hit:
            m["conv"] += 1
            kind = hit.group(1).lower()
            if kind == "feat":
                m["feat"] += 1
            elif kind == "fix":
                m["fix"] += 1

    keys = sorted(months)
    active = [k for k in keys if months[k]["n"] >= 5]
    first, last = (active[0], active[-1]) if len(active) >= 2 else (keys[0], keys[-1])

    def p90(vals):
        s = sorted(vals)
        return s[int(0.9 * (len(s) - 1))] if s else 0

    allfiles = [x for k in keys for x in months[k]["files"]]
    n = len(changes)
    conv = sum(months[k]["conv"] for k in keys)
    half = len(keys) // 2 or 1
    early = [k for k in keys[:half]]
    late = [k for k in keys[half:]]

    def share(ks, field):
        c = sum(months[k]["conv"] for k in ks)
        v = sum(months[k][field] for k in ks)
        return (100 * v / c) if c else None

    return {
        "changes": n,
        "months": len(keys),
        "first_month": keys[0], "last_month": keys[-1],
        "conv_pct": round(100 * conv / n, 1),
        "med_files": st.median(allfiles) if allfiles else 0,
        "p90_files": p90(allfiles),
        "p90_first": p90(months[first]["files"]),
        "p90_last": p90(months[last]["files"]),
        "feat_early": share(early, "feat"), "feat_late": share(late, "feat"),
        "fix_early": share(early, "fix"), "fix_late": share(late, "fix"),
    }


def measure_issues(slug: str, today: dt.date) -> dict | None:
    items, page = [], 1
    while page <= 10:
        r = subprocess.run(
            ["gh", "api", f"repos/{slug}/issues?state=all&per_page=100&page={page}"],
            capture_output=True, text=True)
        if r.returncode != 0:
            return None
        batch = json.loads(r.stdout)
        items += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            break
        page += 1
    human = [i for i in items if not i["user"]["login"].endswith("[bot]")]
    bots = len(items) - len(human)
    openi = [i for i in human if i["state"] == "open"]
    old = sum((today - dt.date.fromisoformat(i["created_at"][:10])).days > 60
              for i in openi)
    return {"total": len(items), "bots": bots, "human": len(human),
            "open": len(openi), "open_over_60d": old,
            "silent_titles": sum(bool(SILENT.search(i["title"])) for i in human)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("clones", help="directory holding one clone per repo")
    ap.add_argument("--issues-org", help="org slug; omit to skip the issue pass")
    ap.add_argument("--min-changes", type=int, default=20,
                    help="changes a repo needs before it counts in the tally")
    ap.add_argument("--json")
    a = ap.parse_args()

    root = pathlib.Path(a.clones)
    repos = sorted(p for p in root.iterdir() if (p / ".git").is_dir())
    today = dt.date.today()
    rows = {}

    hdr = (f"{'repo':26} {'chg':>5} {'mo':>3} {'conv%':>6} {'medF':>5} {'p90F':>5} "
           f"{'p90 1st>last':>13} {'feat e>l':>10} {'fix e>l':>10} "
           f"{'open':>5} {'>60d':>5} {'silent':>6}")
    print(hdr)
    print("-" * len(hdr))
    for p in repos:
        g = measure_git(p)
        if g is None:
            print(f"{p.name:26} {'no first-parent history':>40}")
            continue
        iss = measure_issues(f"{a.issues_org}/{p.name}", today) if a.issues_org else None
        rows[p.name] = {"git": g, "issues": iss}
        f = lambda v: "-" if v is None else f"{v:.0f}%"
        print(f"{p.name:26} {g['changes']:5} {g['months']:3} {g['conv_pct']:5.0f}% "
              f"{g['med_files']:5.0f} {g['p90_files']:5} "
              f"{g['p90_first']:5} > {g['p90_last']:<5} "
              f"{f(g['feat_early']):>4} > {f(g['feat_late']):<4} "
              f"{f(g['fix_early']):>4} > {f(g['fix_late']):<4} "
              f"{(iss or {}).get('open','-'):>5} {(iss or {}).get('open_over_60d','-'):>5} "
              f"{(iss or {}).get('silent_titles','-'):>6}")

    # --- the generalisation test -------------------------------------------
    big = {k: v for k, v in rows.items()
           if v["git"]["changes"] >= a.min_changes and v["git"]["conv_pct"] >= 50
           and v["git"]["months"] >= 3}
    print(f"\ntally over the {len(big)} of {len(rows)} repos with >= {a.min_changes} "
          f"changes, >= 3 active months and >= 50% conventional prefixes")
    print(f"  (excluded: {', '.join(sorted(set(rows) - set(big))) or 'none'})")

    def tally(name, pred, against=None):
        """`against` is the opposite direction; when given, print a one-sided
        sign test over the repos that moved either way (ties dropped). Each
        repo is one vote, so the three largest repos cannot outvote the rest.
        The repos share an author and tooling, so the votes are not
        independent and the p-value is a guide, not proof."""
        hits = [k for k, v in big.items() if pred(v["git"])]
        note = ""
        if against is not None:
            n = len(hits) + sum(1 for v in big.values() if against(v["git"]))
            pv = sum(math.comb(n, i) for i in range(len(hits), n + 1)) / 2 ** n
            note = f"  sign test {len(hits)}/{n} p={pv:.3f}"
        print(f"  {name:46} {len(hits):2} of {len(big)}{note}   {' '.join(sorted(hits))}")

    tally("p90 files per change fell, first to last month",
          lambda g: g["p90_last"] < g["p90_first"],
          against=lambda g: g["p90_last"] > g["p90_first"])
    tally("p90 files per change rose",
          lambda g: g["p90_last"] > g["p90_first"])
    tally("median change touches 1 or 2 source files",
          lambda g: g["med_files"] <= 2)
    tally("feature share fell, first half to second",
          lambda g: g["feat_early"] is not None and g["feat_late"] is not None
          and g["feat_late"] < g["feat_early"],
          against=lambda g: g["feat_early"] is not None and g["feat_late"] is not None
          and g["feat_late"] > g["feat_early"])
    tally("fix share rose, first half to second",
          lambda g: g["fix_early"] is not None and g["fix_late"] is not None
          and g["fix_late"] > g["fix_early"],
          against=lambda g: g["fix_early"] is not None and g["fix_late"] is not None
          and g["fix_late"] < g["fix_early"])
    withiss = {k: v for k, v in big.items() if v["issues"]}
    sil = [(k, v["issues"]["silent_titles"]) for k, v in withiss.items()
           if v["issues"]["silent_titles"] > 0]
    print(f"  {'repos with >=1 silent-check issue title':46} {len(sil):2} of {len(withiss)}"
          f"   {' '.join(k for k, _ in sorted(sil, key=lambda x: -x[1]))}")
    print(f"  {'silent-check titles, total':46} {sum(n for _, n in sil):2}")
    tot_open = sum(v["issues"]["open"] for v in withiss.values())
    tot_old = sum(v["issues"]["open_over_60d"] for v in withiss.values())
    print(f"  {'open non-bot issues across them':46} {tot_open:2}  "
          f"({tot_old} older than 60 days)")

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rows, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
