#!/usr/bin/env python3
"""Compare repositories by development step instead of calendar time.

    bucket-metrics.py <clone> --ext .rs [...] [--path src/] [--bucket 250] [--max 2000]
                      [--label name] [--json out.json]

Every non-merge commit on HEAD that touches at least one source file is one
step. Steps are grouped into buckets of --bucket commits, so the first 250
commits of PX4 sit next to the first 250 of rivet, whatever the calendar said.

Per bucket:
- p90 / median source files per change, share of changes over >= 4 areas
- fix share (subject keyword: fix, bug, regression, revert, workaround)
- fix age in STEPS: how many source commits ago a file touched by a fix was
  last changed. Unlike days, this does not depend on how fast the project ran.
- source files in the tree at bucket end, as a size proxy that needs no blobs
- calendar days the bucket spanned, and distinct authors

Only commit metadata and trees are read, so partial clones (--filter=blob:none)
work. Blind spots: keyword fix share depends on writing habits; author counts
cannot separate humans from agents committing under a human account.
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


def area(path, prefix):
    rest = path[len(prefix):] if prefix and path.startswith(prefix) else path
    parts = rest.split("/")
    return parts[0] if len(parts) > 1 else "."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--ext", nargs="+", required=True)
    ap.add_argument("--path", default="")
    ap.add_argument("--bucket", type=int, default=250)
    ap.add_argument("--max", type=int, default=2000)
    ap.add_argument("--label")
    ap.add_argument("--json")
    ap.add_argument("--until", help="only read history up to this date (speed)")
    a = ap.parse_args()
    exts = tuple(a.ext)

    args = ["log", "--no-merges", "--reverse", "--name-only", "--date=short",
            "--format=@@%H\t%ad\t%ae\t%s"]
    if a.until:
        args.append(f"--until={a.until}")
    if a.path:
        args += ["--", a.path]
    commits, cur = [], None
    for line in git(a.repo, *args).splitlines():
        if line.startswith("@@"):
            h, day, author, subject = line[2:].split("\t", 3)
            cur = {"h": h, "d": dt.date.fromisoformat(day), "a": author, "s": subject, "f": []}
            commits.append(cur)
        elif line.strip() and cur is not None:
            cur["f"].append(line)

    steps = []
    for c in commits:
        src = [f for f in c["f"] if f.endswith(exts) and f.startswith(a.path)]
        if src:
            c["src"] = src
            steps.append(c)
        if len(steps) >= a.max:
            break

    last_step = {}
    buckets = collections.OrderedDict()
    for i, c in enumerate(steps):
        is_fix = bool(FIX.search(c["s"]))
        ages = []
        for f in c["src"]:
            if is_fix and f in last_step:
                ages.append(i - last_step[f])
            last_step[f] = i
        b = buckets.setdefault(i // a.bucket, {"steps": [], "ages": [], "fix": 0})
        b["steps"].append(c)
        b["ages"] += ages
        b["fix"] += is_fix

    label = a.label or a.repo.rstrip("/").rsplit("/", 1)[-1]
    out = []
    print(f"{label}: {len(steps)} source commits measured")
    print(f"{'steps':>11} {'days':>5} {'auth':>4} {'medF':>4} {'p90F':>4} {'>=4ar':>5} "
          f"{'fix':>5} {'ageSteps':>8} {'>100st':>6} {'files':>6}")
    for k, b in buckets.items():
        cs = b["steps"]
        files = sorted(len(c["src"]) for c in cs)
        p90 = files[int(0.9 * (len(files) - 1))]
        wide = 100 * sum(len({area(f, a.path) for f in c["src"]}) >= 4 for c in cs) / len(cs)
        fix = 100 * b["fix"] / len(cs)
        age = st.median(b["ages"]) if b["ages"] else None
        far = 100 * sum(x > 100 for x in b["ages"]) / len(b["ages"]) if b["ages"] else None
        days = (cs[-1]["d"] - cs[0]["d"]).days + 1
        tree = [f for f in git(a.repo, "ls-tree", "-r", "--name-only", cs[-1]["h"]).split("\n")
                if f.endswith(exts) and f.startswith(a.path)]
        rng = f"{k * a.bucket + 1}-{k * a.bucket + len(cs)}"
        print(f"{rng:>11} {days:5} {len({c['a'] for c in cs}):4} {st.median(files):4.0f} {p90:4} "
              f"{wide:4.0f}% {fix:4.0f}% {'-' if age is None else f'{age:.0f}':>8} "
              f"{'-' if far is None else f'{far:.0f}%':>6} {len(tree):6}")
        out.append({"bucket": k, "range": rng, "days": days, "authors": len({c['a'] for c in cs}),
                    "median_files": st.median(files), "p90_files": p90, "wide_pct": round(wide, 1),
                    "fix_pct": round(fix, 1), "fix_age_steps": age,
                    "fix_age_over100_pct": None if far is None else round(far, 1),
                    "source_files": len(tree)})
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"label": label, "buckets": out}, fh, indent=1)


if __name__ == "__main__":
    main()
