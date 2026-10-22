#!/usr/bin/env python3
"""B-SZZ: find the commits that introduced the lines a fix had to change.

    szz.py <clone> --ext .rs [...] --fixes ids.json --steps-label NAME [--max 2000]

For each fix commit, the source lines it deletes or modifies are blamed in the
fix's parent (whitespace ignored, blank and comment-only lines skipped). The
commits those lines come from are the candidate bug-introducing commits.

Output per fix: the introducing commits with their subject and how many source
commits (steps) and days lie between introduction and fix. Steps are counted on
the same sequence bucket-metrics.py uses, so latencies compare across projects.

Blind spots, as in the literature: a fix that only adds lines (a missing check)
has nothing to blame and is reported as "add-only"; refactorings and moves
between introduction and fix misattribute blame; a squash commit is one step.
"""
import argparse
import datetime as dt
import json
import re
import subprocess

COMMENT = re.compile(r"^\s*(//|#|/\*|\*|--|;)")


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, check=check).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--ext", nargs="+", required=True)
    ap.add_argument("--fixes", required=True,
                    help='JSON list of {"i": step index, "h": commit sha} for the fixes')
    ap.add_argument("--until")
    ap.add_argument("--max", type=int, default=2000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    exts = tuple(a.ext)

    args = ["log", "--no-merges", "--reverse", "--name-only", "--date=short",
            "--format=@@%H\t%ad\t%s"]
    if a.until:
        args.append(f"--until={a.until}")
    steps, cur = [], None
    for line in git(a.repo, *args).splitlines():
        if line.startswith("@@"):
            h, d, s = line[2:].split("\t", 2)
            cur = {"h": h, "d": dt.date.fromisoformat(d), "s": s, "f": []}
            steps.append(cur)
        elif line.strip() and cur is not None:
            cur["f"].append(line)
    steps = [c for c in steps if any(f.endswith(exts) for f in c["f"])][:a.max]
    index = {c["h"]: i for i, c in enumerate(steps)}

    results = []
    for want in json.load(open(a.fixes)):
        # The index alone silently points at a different commit when the step
        # sequence differs (other clone, other --until); the sha makes it fail.
        i = want["i"]
        fix = steps[i]
        if not fix["h"].startswith(want["h"]):
            raise SystemExit(f"step {i} is {fix['h'][:12]}, fixes file says {want['h'][:12]}")
        parent = git(a.repo, "rev-parse", f"{fix['h']}^", check=False).strip()
        if not parent:
            continue
        intro = {}
        for f in [f for f in fix["f"] if f.endswith(exts)]:
            diff = git(a.repo, "diff", "-U0", "-w", parent, fix["h"], "--", f, check=False)
            ranges = []
            for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+", diff, re.M):
                start, count = int(m.group(1)), int(m.group(2) or 1)
                if count:
                    ranges.append((start, start + count - 1))
            for lo, hi in ranges:
                blame = git(a.repo, "blame", "-w", "--porcelain", "-L", f"{lo},{hi}",
                            parent, "--", f, check=False)
                sha = None
                for bl in blame.splitlines():
                    if re.match(r"^[0-9a-f]{40} ", bl):
                        sha = bl.split()[0]
                    elif bl.startswith("\t") and sha:
                        text = bl[1:]
                        if text.strip() and not COMMENT.match(text):
                            intro[sha] = intro.get(sha, 0) + 1
        rec = {"fix_step": i, "fix": fix["s"][:120], "add_only": not intro, "introducers": []}
        for sha, lines in sorted(intro.items(), key=lambda kv: -kv[1]):
            j = index.get(sha)
            subj = git(a.repo, "log", "-1", "--format=%s", sha, check=False).strip()
            day = git(a.repo, "log", "-1", "--format=%ad", "--date=short", sha, check=False).strip()
            rec["introducers"].append({
                "sha": sha[:12], "lines": lines, "subject": subj[:120],
                "step": j, "lag_steps": None if j is None else i - j,
                "lag_days": (fix["d"] - dt.date.fromisoformat(day)).days if day else None})
        results.append(rec)
    json.dump(results, open(a.out, "w"), indent=1)
    blamed = [r for r in results if not r["add_only"]]
    print(f"{len(results)} fixes, {len(blamed)} with blamable lines, "
          f"{len(results) - len(blamed)} add-only")


if __name__ == "__main__":
    main()
