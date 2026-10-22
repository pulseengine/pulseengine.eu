#!/usr/bin/env python3
"""Sample commits for model classification and score the classifier against an oracle.

The classification itself is done by a small, cheap model (delegate-by-cost);
this script prepares its input and checks its output, so the model is never
trusted on its own word.

    commit-classify.py sample  <clone> --ext .rs [...] --name N [--until D] [--per-bucket 15]
        writes cls/N-input.txt (subject only) and cls/N-full.json (full message)
    commit-classify.py oracle  <clone> [<clone> ...] --ext .rs --n 160
        conventional-commit repos only: strips the prefix (blinding) and writes
        cls/oracle-input.txt plus cls/oracle-truth.json
    commit-classify.py score
        compares cls/oracle-labels.json with cls/oracle-truth.json: agreement,
        confusion matrix, fix precision and recall
    commit-classify.py mix N [N ...]
        reads cls/N-full-labels.json ({"primary", "contains_fix"}) and prints the
        feature / fix / refactor / maintenance mix, hidden fixes, and fix+refactor

Prompt used for the model (subject or full message, one label per commit):
  feature: adds new capability or behaviour
  fix: corrects a defect, wrong behaviour, a broken check, or a regression
  refactor: restructures code without changing behaviour
  maintenance: tests only, docs, CI, build, dependencies, releases, formatting
  contains_fix (full-message pass): true if the commit also corrects a defect,
  even as a side effect; always true for primary = fix.
"""
import argparse
import collections
import json
import pathlib
import random
import re
import subprocess

PRE = re.compile(r"^(\w+)(\([^)]*\))?!?:\s*")
FIX = re.compile(r"(?i)\b(fix(e[sd])?|bug(s|fix)?|regress\w*|revert\w*|workaround)\b")
TRAILER = re.compile(r"(?im)^\s*(co-authored-by|signed-off-by|generated with|🤖|claude-session|https://claude\.ai).*$")
CATS = ["feature", "fix", "refactor", "maintenance"]
OUT = pathlib.Path("cls")


def steps(repo, exts, until=None, limit=2000):
    args = ["git", "-C", repo, "log", "--no-merges", "--reverse", "--name-only",
            "--format=@@%H\t%s"]
    if until:
        args.append(f"--until={until}")
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    cs, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            h, s = line[2:].split("\t", 1)
            cur = [h, s, []]
            cs.append(cur)
        elif line.strip() and cur:
            cur[2].append(line)
    return [c for c in cs if any(f.endswith(exts) for f in c[2])][:limit]


# A conventional prefix on ANY line, optionally bulleted. Squash-merge bodies
# carry the PR's own commit list ("* feat(interop): ..."), so stripping only
# line 1 left the answer in the text: 2 of 160 oracle messages leaked it on line
# 1, and far more inside the body, which inflates a full-message oracle and makes
# squash-merging repos look easier to classify than others.
ANYPRE = re.compile(r"(?m)^(\s*(?:[*\-]\s*)?)(feat|fix|refactor|chore|docs|test|tests|ci|build|perf|"
                    r"style|deps|revert|release)(\([^)]*\))?!?:\s*", re.I)


def body(repo, h):
    text = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%B", h],
                          capture_output=True, text=True).stdout
    text = TRAILER.sub("", text).strip()
    text = ANYPRE.sub(lambda m: m.group(1), text)
    return re.sub(r"\n{2,}", "\n", text)[:700].replace("\t", " ")


def cmd_sample(a):
    random.seed(7)
    st = steps(a.clone, tuple(a.ext), a.until)
    rows, full = [], []
    for b in range(0, len(st), 250):
        chunk = list(enumerate(st[b:b + 250], start=b))
        for i, (h, s, _) in random.sample(chunk, min(a.per_bucket, len(chunk))):
            rows.append(f"{a.name}-{i}\t{PRE.sub('', s)}")
            full.append({"id": f"{a.name}-{i}", "text": body(a.clone, h)})
    OUT.mkdir(exist_ok=True)
    (OUT / f"{a.name}-input.txt").write_text("\n".join(rows))
    (OUT / f"{a.name}-full.json").write_text(json.dumps(full, indent=0))
    print(a.name, len(rows))


def wilson(k, n, z=1.96):
    """95% Wilson interval for k of n, as (low, high) percentages."""
    if n == 0:
        return (0.0, 0.0)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def cmd_oracle(a):
    """Agent-prose oracle: the author's own conventional prefix is the truth,
    stripped from what the model sees (blinding). The SAME commits are written
    twice, subject only and full message, so both instruments are calibrated on
    one population. The truth is a convention the author chose, not a fact."""
    random.seed(7)
    truth = []
    for clone in a.clones:
        for i, (h, s, _) in enumerate(steps(clone, tuple(a.ext))):
            m = PRE.match(s)
            if m:
                kind = {"feat": "feature", "fix": "fix", "refactor": "refactor"}.get(
                    m.group(1).lower(), "maintenance")
                truth.append({"id": f"{pathlib.Path(clone).name}-{i}", "repo": clone, "h": h,
                              "subject": PRE.sub("", s), "truth": kind})
    random.shuffle(truth)
    truth = truth[:a.n]
    OUT.mkdir(exist_ok=True)
    (OUT / "oracle-truth.json").write_text(json.dumps(
        [{k: t[k] for k in ("id", "h", "subject", "truth")} for t in truth], indent=0))
    (OUT / "oracle-subj-input.txt").write_text("\n".join(f"{t['id']}\t{t['subject']}" for t in truth))
    (OUT / "oracle-full-input.json").write_text(json.dumps(
        [{"id": t["id"], "text": body(t["repo"], t["h"])} for t in truth], indent=0))
    print("oracle", len(truth), dict(collections.Counter(t["truth"] for t in truth)))


def cmd_levin(a):
    """Human-prose oracle: Levin and Yehudai's 1151 commits from 11 Java projects,
    hand-labelled in 2017 using the issue tracker (Zenodo 835534, CC BY-SA 4.0).
    corrective -> fix; adaptive and perfective -> not fix. Only the fix boundary
    is scored, because Swanson's classes do not map onto feature/refactor."""
    import csv
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8", errors="replace"), delimiter="#"))
    random.seed(11)
    random.shuffle(rows)
    rows = rows[:a.n]
    OUT.mkdir(exist_ok=True)
    clean = lambda t: re.sub(r"\s+", " ", t.replace("--", " ")).strip()[:700]
    (OUT / "levin-truth.json").write_text(json.dumps(
        [{"id": f"levin-{k}", "truth": "fix" if r["label"] == "c" else "other"}
         for k, r in enumerate(rows)], indent=0))
    (OUT / "levin-full-input.json").write_text(json.dumps(
        [{"id": f"levin-{k}", "text": clean(r["comment"])} for k, r in enumerate(rows)], indent=0))
    print("levin", len(rows), dict(collections.Counter(r["label"] for r in rows)))


def load_labels(path, ids):
    """Mechanical schema check: the model is an instrument, so its output is
    validated before any number is computed from it."""
    lab = json.loads(pathlib.Path(path).read_text())
    missing = [i for i in ids if i not in lab]
    extra = [i for i in lab if i not in ids]
    bad = [i for i, v in lab.items() if not isinstance(v, dict) or v.get("primary") not in CATS
           or not isinstance(v.get("contains_fix"), bool)]
    if missing or extra or bad:
        raise SystemExit(f"labels {path}: {len(missing)} missing, {len(extra)} unexpected, "
                         f"{len(bad)} malformed — refusing to score")
    return lab


def cmd_score(a):
    truth = json.loads((OUT / f"{a.oracle}-truth.json").read_text())
    ids = [t["id"] for t in truth]
    lab = load_labels(a.labels, ids)
    is_fix = lambda v: v["primary"] == "fix"
    tp = sum(t["truth"] == "fix" and is_fix(lab[t["id"]]) for t in truth)
    fp = sum(t["truth"] != "fix" and is_fix(lab[t["id"]]) for t in truth)
    fn = sum(t["truth"] == "fix" and not is_fix(lab[t["id"]]) for t in truth)
    pl, ph = wilson(tp, tp + fp)
    rl, rh = wilson(tp, tp + fn)
    print(f"{a.oracle} vs {pathlib.Path(a.labels).name}: n={len(truth)}  fixes in truth={tp + fn}")
    print(f"  fix precision {tp / max(1, tp + fp):.2f} [{pl:.0f}-{ph:.0f}%]  "
          f"recall {tp / max(1, tp + fn):.2f} [{rl:.0f}-{rh:.0f}%]")
    if any(t["truth"] in CATS and t["truth"] != "fix" for t in truth):
        agree = sum(lab[t["id"]]["primary"] == t["truth"] for t in truth)
        print(f"  four-class agreement {agree}/{len(truth)} = {100 * agree / len(truth):.0f}%")
    kw_tp = sum(t["truth"] == "fix" and bool(FIX.search(t.get("subject", ""))) for t in truth)
    if any("subject" in t for t in truth):
        kw_fp = sum(t["truth"] != "fix" and bool(FIX.search(t["subject"])) for t in truth)
        print(f"  keyword rule: precision {kw_tp / max(1, kw_tp + kw_fp):.2f}  "
              f"recall {kw_tp / max(1, tp + fn):.2f}")
    if a.retest:
        lab2 = load_labels(a.retest, ids)
        same = sum(lab[i]["primary"] == lab2[i]["primary"] for i in ids)
        print(f"  test-retest: {same}/{len(ids)} = {100 * same / len(ids):.0f}% same primary label")


def cmd_mix(a):
    print(f"{'project':18}{'n':>4} {'feat':>14} {'fix':>14} {'refac':>14} {'hidden':>7}")
    for name in a.names:
        full = json.loads((OUT / f"{name}-full.json").read_text())
        lab = load_labels(OUT / f"{name}-full-labels.json", [r["id"] for r in full])
        v = list(lab.values())
        n = len(v)
        def cell(k):
            lo, hi = wilson(k, n)
            return f"{100 * k / n:3.0f}% [{lo:2.0f}-{hi:2.0f}]"
        feat = sum(x["primary"] == "feature" for x in v)
        fix = sum(x["primary"] == "fix" for x in v)
        ref = sum(x["primary"] == "refactor" for x in v)
        hid = sum(x["contains_fix"] and x["primary"] != "fix" for x in v)
        print(f"{name:18}{n:4} {cell(feat):>14} {cell(fix):>14} {cell(ref):>14} {100 * hid / n:6.0f}%")
        if a.by_bucket:
            buckets = collections.defaultdict(lambda: [0, 0])
            for i, x in lab.items():
                b = int(i.rsplit("-", 1)[1]) // 250
                buckets[b][0] += x["primary"] == "fix"
                buckets[b][1] += 1
            print("   fix share by 250-step bucket: " + "  ".join(
                f"{b}:{100 * k / m:.0f}%[{wilson(k, m)[0]:.0f}-{wilson(k, m)[1]:.0f}](n={m})"
                for b, (k, m) in sorted(buckets.items())))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("clone")
    s.add_argument("--ext", nargs="+", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--until")
    s.add_argument("--per-bucket", type=int, default=15)
    o = sub.add_parser("oracle")
    o.add_argument("clones", nargs="+")
    o.add_argument("--ext", nargs="+", required=True)
    o.add_argument("--n", type=int, default=160)
    lv = sub.add_parser("levin")
    lv.add_argument("csv")
    lv.add_argument("--n", type=int, default=400)
    sc = sub.add_parser("score")
    sc.add_argument("oracle", help="oracle | levin")
    sc.add_argument("labels")
    sc.add_argument("--retest", help="a second label file from an independent run")
    m = sub.add_parser("mix")
    m.add_argument("names", nargs="+")
    m.add_argument("--by-bucket", action="store_true")
    a = ap.parse_args()
    {"sample": cmd_sample, "oracle": cmd_oracle, "levin": cmd_levin, "score": cmd_score,
     "mix": cmd_mix}[a.cmd](a)


if __name__ == "__main__":
    main()
