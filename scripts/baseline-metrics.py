#!/usr/bin/env python3
"""Process metrics with one definition for every repository, AI-era or not.

    baseline-metrics.py <clone> --ext .rs [.c ...] [--path kernel/]
                        [--period month|year] [--since YYYY-MM-DD] [--until YYYY-MM-DD]
                        [--loc] [--json out.json]

Differences from factory-metrics.py, chosen so pre-AI histories compare fairly:
- All non-merge commits on HEAD (not first-parent): older projects merge
  topic branches or rebase; squash-merging projects give the same set either way.
- "Fix" is a keyword match on the subject (fix, bug, regression, revert,
  workaround), because older projects do not use conventional-commit prefixes.
  The same rule is applied to rivet and spar for the comparison.
- Source files are selected by extension (and optionally a path prefix).
- Authors per period are counted, so output per author can be compared.

Instruments and blind spots: subjects are written by people or agents with
different habits, so keyword fix share is noisy across projects; fix age is per
file, not per line; imported histories (seL4 and l4v from 2014, Zephyr from 2015)
start mature, so their first months are not early life.
"""
import argparse
import collections
import datetime as dt
import json
import re
import statistics as st
import subprocess

FIX = re.compile(r"(?i)\b(fix(e[sd])?|bug(s|fix)?|regress\w*|revert\w*|workaround)\b")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, check=True).stdout


def load(repo, since, until, path=""):
    args = ["log", "--no-merges", "--reverse", "--name-only", "--date=short",
            "--format=@@%ad\t%ae\t%s"]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if path:
        args += ["--", path]
    commits, cur = [], None
    for line in git(repo, *args).splitlines():
        if line.startswith("@@"):
            day, author, subject = line[2:].split("\t", 2)
            cur = {"d": dt.date.fromisoformat(day), "a": author, "s": subject, "f": []}
            commits.append(cur)
        elif line.strip() and cur is not None:
            cur["f"].append(line)
    return commits


def area(path, prefix):
    rest = path[len(prefix):] if prefix and path.startswith(prefix) else path
    parts = rest.split("/")
    return parts[0] if len(parts) > 1 else "."


def loc_at(repo, date, exts, prefix):
    rev = git(repo, "rev-list", "-1", f"--before={date}", "HEAD").strip()
    if not rev:
        return 0
    total = 0
    for f in git(repo, "ls-tree", "-r", "--name-only", rev).split("\n"):
        if f.endswith(exts) and f.startswith(prefix):
            blob = subprocess.run(["git", "-C", repo, "show", f"{rev}:{f}"],
                                  capture_output=True).stdout
            total += blob.count(b"\n")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--ext", nargs="+", required=True)
    ap.add_argument("--path", default="")
    ap.add_argument("--period", choices=("month", "year"), default="month")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--loc", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    exts = tuple(a.ext)

    last_touch = {}
    rows = collections.OrderedDict()
    for c in load(a.repo, None, a.until, a.path):
        src = [f for f in c["f"] if f.endswith(exts) and f.startswith(a.path)]
        is_fix = bool(FIX.search(c["s"]))
        ages = []
        for f in src:
            if is_fix and f in last_touch:
                ages.append((c["d"] - last_touch[f]).days)
            last_touch[f] = c["d"]
        if not src or (a.since and c["d"] < dt.date.fromisoformat(a.since)):
            continue
        key = c["d"].strftime("%Y-%m" if a.period == "month" else "%Y")
        r = rows.setdefault(key, {"n": 0, "files": [], "areas": [], "fix": 0,
                                  "age": [], "authors": set()})
        r["n"] += 1
        r["files"].append(len(src))
        r["areas"].append(len({area(f, a.path) for f in src}))
        r["fix"] += is_fix
        r["age"] += ages
        r["authors"].add(c["a"])

    out = []
    print(f"{'period':8} {'chg':>5} {'auth':>4} {'chg/au':>6} {'medF':>4} {'p90F':>4} "
          f"{'>=4ar':>5} {'fix':>5} {'fixAge':>6} {'>30d':>5}" + (" {:>8}".format("LOC") if a.loc else ""))
    for key, r in rows.items():
        files = sorted(r["files"])
        p90 = files[int(0.9 * (len(files) - 1))]
        wide = 100 * sum(x >= 4 for x in r["areas"]) / r["n"]
        fix = 100 * r["fix"] / r["n"]
        age = st.median(r["age"]) if r["age"] else None
        old = 100 * sum(x > 30 for x in r["age"]) / len(r["age"]) if r["age"] else None
        row = {"period": key, "changes": r["n"], "authors": len(r["authors"]),
               "median_files": st.median(files), "p90_files": p90, "wide_pct": round(wide, 1),
               "fix_pct": round(fix, 1), "fix_age_days": age,
               "fix_age_over30_pct": None if old is None else round(old, 1)}
        line = (f"{key:8} {r['n']:5} {len(r['authors']):4} {r['n'] / len(r['authors']):6.1f} "
                f"{st.median(files):4.0f} {p90:4} {wide:4.0f}% {fix:4.0f}% "
                f"{'-' if age is None else f'{age:.0f}d':>6} {'-' if old is None else f'{old:.0f}%':>5}")
        if a.loc:
            if a.period == "year":
                end = f"{int(key) + 1}-01-01"
            else:
                y, m = map(int, key.split("-"))
                end = f"{y + (m == 12)}-{m % 12 + 1:02d}-01"
            row["loc"] = loc_at(a.repo, end, exts, a.path)
            line += f" {row['loc']:8}"
        print(line)
        out.append(row)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
