#!/usr/bin/env python3
"""Monthly process metrics for an agent-built repository.

Reproduces the tables in "The machine arrived before the factory".

    factory-metrics.py <path-to-clone> [--issues owner/repo]

Git metrics read the first-parent history of the checked-out branch (one entry
per merged PR when the repo squash-merges). Issue metrics use the GitHub REST
API through `gh api`, paginated by page number.

Instruments and their blind spots:
- Commit types come from conventional-commit prefixes the authors (mostly agents)
  chose. `fix:` includes dependency and CI fixes.
- "Files per change" counts source files only (docs, lockfiles, YAML, JSON
  excluded), so artifact-only changes read as 0.
- "Fix age" comes in two flavours and they do not agree. The default is days
  since the touched .rs file last changed, which is a FILE-level proxy and only a
  LOWER BOUND on the age of the lines a fix actually changed: the lines were last
  edited at or before the file's previous touch, never after it. Two things push
  it down regardless of defect age -- a wave of fixes landing in the same files in
  sequence, so each fix's "previous touch" is the previous fix, and ordinary churn
  in hot files. `--line-age` measures the real thing with `git blame` over the
  lines each fix deleted or modified. Use the file-level number for cadence and
  the line-level number for any claim about how old a defect was.
- Issue authorship is the GitHub account, and agents file under the owner's
  account, so who filed an issue cannot be recovered. The Claude Code body marker
  is reported as a lower bound only.
"""
import argparse
import collections
import datetime as dt
import json
import re
import statistics as st
import subprocess

# Source extensions counted for lines and fix age. Rust by default, because the
# first post measured Rust repositories; pass --ext for any other language.
EXTS = (".rs",)

MAINTAINERS = ()
EXCLUDE = re.compile(r"(\.md$|\.lock$|CHANGELOG|^docs/|\.ya?ml$|\.json$)")
SILENT = re.compile(
    r"(?i)silent|never (fires|checked)|no-op|masked|exits 0|cannot fail|blind|"
    r"always green|reports success"
)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, check=True).stdout


def commits(repo):
    out = git(repo, "log", "--first-parent", "--no-merges", "--reverse",
              "--numstat", "--date=short", "--format=@@%ad\t%s")
    result, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            day, subject = line[2:].split("\t", 1)
            cur = {"d": dt.date.fromisoformat(day), "s": subject, "f": []}
            result.append(cur)
        elif line.strip() and cur is not None:
            cur["f"].append(line.split("\t", 2)[2])
    return result


def area(path):
    parts = path.split("/")
    if parts[0] in ("crates", "libs", "packages") and len(parts) > 1:
        return "/".join(parts[:2])
    return parts[0]


def rust_loc_at_month_end(repo, month):
    y, m = map(int, month.split("-"))
    end = f"{y + (m == 12)}-{m % 12 + 1:02d}-01"
    rev = git(repo, "rev-list", "-1", "--first-parent", f"--before={end}",
              "HEAD").strip()
    files = [f for f in git(repo, "ls-tree", "-r", "--name-only", rev).split()
             if f.endswith(EXTS)]
    total = 0
    for f in files:
        blob = subprocess.run(["git", "-C", repo, "show", f"{rev}:{f}"],
                              capture_output=True, check=True).stdout
        total += blob.count(b"\n")
    return total


def line_age_for_month(repo, month):
    """Median age, in days, of the LINES each fix commit changed that month.

    The file-level figure above is a lower bound; this is the measurement a
    claim about defect age needs. For every `fix:` commit, take the hunks it
    deleted or modified and blame them against the commit's parent, then take
    the median per commit and the median of those.
    """
    out = git(repo, "log", "--first-parent", "--no-merges",
              "--date=format:%Y-%m", "--format=%H|%ad|%s")
    per_commit = []
    prev_touch_was_same_month_fix = [0, 0]
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3 or parts[1] != month:
            continue
        sha, _, subject = parts
        if not re.match(r"fix(\(|!|:)", subject):
            continue
        ct = git(repo, "show", "-s", "--format=%ct", sha).strip()
        if not ct:
            continue
        ct = int(ct)
        diff = git(repo, "diff", "-U0", f"{sha}^", sha, "--", "*.rs")
        cur, ages = None, []
        for dl in diff.splitlines():
            if dl.startswith("--- a/"):
                cur = dl[6:]
            elif dl.startswith("@@") and cur:
                m = re.match(r"@@ -(\d+)(?:,(\d+))? ", dl)
                if not m:
                    continue
                start, cnt = int(m.group(1)), int(m.group(2) or 1)
                if cnt == 0:
                    continue
                bl = git(repo, "blame", "--line-porcelain",
                         f"-L{start},{start + cnt - 1}", f"{sha}^", "--", cur)
                for b in bl.splitlines():
                    if b.startswith("author-time "):
                        ages.append((ct - int(b.split()[1])) / 86400)
        if ages:
            per_commit.append(st.median(ages))
        # How much of the file-level signal is the fix wave measuring itself?
        for f in [x for x in git(repo, "show", "--name-only", "--format=",
                                 "--first-parent", sha).split() if x.endswith(EXTS)][:10]:
            pm = git(repo, "log", "-1", "--format=%ad|%s", "--date=format:%Y-%m",
                     f"{sha}^", "--", f).strip()
            if pm:
                prev_touch_was_same_month_fix[1] += 1
                mo, _, subj = pm.partition("|")
                if mo == month and re.match(r"fix(\(|!|:)", subj):
                    prev_touch_was_same_month_fix[0] += 1
    return per_commit, prev_touch_was_same_month_fix


def git_table(repo, sink=None):
    cs = commits(repo)
    last_touch = {}
    rows = collections.defaultdict(lambda: {"n": 0, "files": [], "areas": [],
                                            "types": collections.Counter(),
                                            "fix_age": [], "conv": 0})
    for c in cs:
        month = c["d"].strftime("%Y-%m")
        row = rows[month]
        src = [f for f in c["f"] if not EXCLUDE.search(f)]
        row["n"] += 1
        row["files"].append(len(src))
        row["areas"].append(len({area(f) for f in src}))
        m = re.match(r"(\w+)(\(.*?\))?!?:", c["s"])
        kind = m.group(1).lower() if m else "other"
        row["conv"] += bool(m)
        row["types"][kind] += 1
        for f in c["f"]:
            if not f.endswith(EXTS):
                continue
            if kind == "fix" and f in last_touch:
                row["fix_age"].append((c["d"] - last_touch[f]).days)
            last_touch[f] = c["d"]

    print(f"{'month':8} {'chg':>4} {'medF':>4} {'p90F':>4} {'>=4ar':>5} "
          f"{'feat':>5} {'fix':>5} {'fixAge':>6} {'>30d':>5} {'rustLOC':>8}")
    for month in sorted(rows):
        r = rows[month]
        files = sorted(r["files"])
        p90 = files[int(0.9 * (len(files) - 1))]
        wide = 100 * sum(a >= 4 for a in r["areas"]) / r["n"]
        feat = 100 * r["types"]["feat"] / r["n"]
        fix = 100 * r["types"]["fix"] / r["n"]
        ages = r["fix_age"]
        age = f"{st.median(ages):.0f}d" if ages else "-"
        old = f"{100 * sum(a > 30 for a in ages) / len(ages):.0f}%" if ages else "-"
        loc = rust_loc_at_month_end(repo, month)
        print(f"{month:8} {r['n']:4} {st.median(files):4.0f} {p90:4} {wide:4.0f}% "
              f"{feat:4.0f}% {fix:4.0f}% {age:>6} {old:>5} {loc:8}")
        if sink is not None:
            sink.setdefault("months", []).append({
                "month": month, "changes": r["n"], "p90_files": p90,
                "feat_pct": round(feat, 1), "fix_pct": round(fix, 1),
                # A feat or fix share means nothing in a month whose changes
                # mostly do not carry a conventional prefix: relay's first
                # month is 3% conventional and would otherwise read as 0% feat.
                "conv_pct": round(100 * r["conv"] / r["n"], 1),
                "fix_age_days": st.median(ages) if ages else None,
                "rust_loc": loc})


def issues(slug):
    items, page = [], 1
    while True:
        out = subprocess.run(
            ["gh", "api", f"repos/{slug}/issues?state=all&per_page=100&page={page}"],
            capture_output=True, text=True, check=True).stdout
        batch = json.loads(out)
        items += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            return items
        page += 1


def issue_table(slug, today, sink=None):
    allitems = issues(slug)
    bots = [i for i in allitems if i["user"]["login"].endswith("[bot]")]
    human = [i for i in allitems if not i["user"]["login"].endswith("[bot]")]
    opened = collections.Counter(i["created_at"][:7] for i in human)
    closed = collections.Counter(i["closed_at"][:7] for i in human if i["closed_at"])
    print(f"\nissues: {len(allitems)} total, {len(bots)} from bots (excluded below)")
    print(f"{'month':8} {'opened':>6} {'closed':>6} {'open':>5}")
    backlog = 0
    for month in sorted(set(opened) | set(closed)):
        backlog += opened[month] - closed[month]
        print(f"{month:8} {opened[month]:6} {closed[month]:6} {backlog:5}")
        if sink is not None:
            sink.setdefault("issues", []).append({
                "month": month, "opened": opened[month],
                "closed": closed[month], "open": backlog})
    still_open = [i for i in human if i["state"] == "open"]
    old = sum((today - dt.date.fromisoformat(i["created_at"][:10])).days > 60
              for i in still_open)
    owner = slug.split("/")[0]
    team = {owner, *MAINTAINERS}
    external = sum(i["user"]["login"] not in team for i in human)
    print(f"open > 60 days: {old}; external authors: {external}")
    marked = [i for i in human if "Generated with [Claude Code]" in (i.get("body") or "")]
    print(f"issues carrying the Claude Code body marker: {len(marked)} of {len(human)} "
          "(a lower bound on agent-filed issues; provenance is not otherwise recorded)")
    print(f"silently-wrong titles: {sum(bool(SILENT.search(i['title'])) for i in human)}")
    # Three kinds of author. Bots (CI alerts) are excluded above. Agents and the
    # owner both file under the owner's account, so the tracker cannot separate
    # them; the owner files only short issues, so body size is the one signal.
    own = [i for i in human if i["user"]["login"] in team]
    mk = [i for i in own if "Generated with [Claude Code]" in (i.get("body") or "")]
    rest = [i for i in own if i not in mk]
    blen = lambda i: len(i.get("body") or "")
    print(f"owner-account issues: {len(own)}; with the agent marker: {len(mk)} "
          f"(shortest body {min(map(blen, mk)) if mk else '-'} chars); without it: {len(rest)}, "
          f"of which {sum(blen(i) < 300 for i in rest)} have a body under 300 chars")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--issues", help="owner/repo for the issue tables")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--json", help="also write the monthly series to this file")
    ap.add_argument("--ext", nargs="+", default=[".rs"],
                    help="source extensions for lines of code and fix age (default .rs)")
    ap.add_argument("--maintainers", nargs="*", default=[],
                    help="logins that count as the project's own, besides the repo owner; "
                         "everyone else is an external author")
    ap.add_argument("--line-age", metavar="YYYY-MM", action="append",
                    help="also measure LINE-level fix age for this month "
                         "(repeatable; slow, one git blame per hunk)")
    a = ap.parse_args()
    global EXTS, MAINTAINERS
    EXTS, MAINTAINERS = tuple(a.ext), tuple(a.maintainers)
    sink = {} if a.json else None
    git_table(a.repo, sink)
    for month in a.line_age or []:
        ages, (same, total) = line_age_for_month(a.repo, month)
        if ages:
            srt = sorted(ages)
            print(f"\nline-level fix age, {month}: n={len(ages)} commits, "
                  f"median {st.median(ages):.0f}d "
                  f"(p25 {srt[len(srt)//4]:.0f}d, p75 {srt[3*len(srt)//4]:.0f}d)")
            print(f"  file-level previous touches that were themselves {month} fixes: "
                  f"{same}/{total} — the share of the file-level signal that is the "
                  f"fix wave measuring its own cadence")
            if sink is not None:
                sink.setdefault("line_age", {})[month] = {
                    "commits": len(ages), "median_days": round(st.median(ages), 1),
                    "self_referential_touches": [same, total]}
        else:
            print(f"\nline-level fix age, {month}: no fix commit touched Rust")
    if a.issues:
        issue_table(a.issues, dt.date.fromisoformat(a.today), sink)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(sink, fh, indent=1)


if __name__ == "__main__":
    main()
