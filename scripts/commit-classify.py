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
TRAILER = re.compile(r"(?im)^(co-authored-by|signed-off-by|generated with|🤖|claude-session|https://claude).*$")
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


def body(repo, h):
    text = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%B", h],
                          capture_output=True, text=True).stdout
    text = PRE.sub("", TRAILER.sub("", text).strip(), count=1)
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


def cmd_oracle(a):
    random.seed(7)
    truth = []
    for clone in a.clones:
        for i, (h, s, _) in enumerate(steps(clone, tuple(a.ext))):
            m = PRE.match(s)
            if m:
                kind = {"feat": "feature", "fix": "fix", "refactor": "refactor"}.get(
                    m.group(1).lower(), "maintenance")
                truth.append({"id": f"{pathlib.Path(clone).name}-{i}",
                              "subject": PRE.sub("", s), "truth": kind})
    random.shuffle(truth)
    truth = truth[:a.n]
    OUT.mkdir(exist_ok=True)
    (OUT / "oracle-truth.json").write_text(json.dumps(truth, indent=0))
    (OUT / "oracle-input.txt").write_text("\n".join(f"{t['id']}\t{t['subject']}" for t in truth))
    print("oracle", len(truth), collections.Counter(t["truth"] for t in truth))


def cmd_score(_):
    truth = json.loads((OUT / "oracle-truth.json").read_text())
    lab = json.loads((OUT / "oracle-labels.json").read_text())
    cm = collections.Counter((t["truth"], lab.get(t["id"])) for t in truth)
    agree = sum(v for (x, y), v in cm.items() if x == y)
    print(f"agreement {agree}/{len(truth)} = {100 * agree / len(truth):.0f}%")
    print("truth\\pred  " + " ".join(f"{c[:6]:>6}" for c in CATS))
    for x in CATS:
        print(f"{x[:11]:11} " + " ".join(f"{cm[(x, y)]:6}" for y in CATS))
    tp = cm[("fix", "fix")]
    fp = sum(cm[(x, "fix")] for x in CATS if x != "fix")
    fn = sum(cm[("fix", y)] for y in CATS if y != "fix")
    print(f"model fix precision {tp / max(1, tp + fp):.2f}  recall {tp / max(1, tp + fn):.2f}")
    kw = collections.Counter((t["truth"] == "fix", bool(FIX.search(t["subject"]))) for t in truth)
    kp = kw[(True, True)] / max(1, kw[(True, True)] + kw[(False, True)])
    kr = kw[(True, True)] / max(1, kw[(True, True)] + kw[(True, False)])
    print(f"keyword fix precision {kp:.2f}  recall {kr:.2f}")


def cmd_mix(a):
    print(f"{'project':20}{'n':>4} {'feat':>5} {'fix':>5} {'hidden':>6} {'refac':>6} {'fix+ref':>7}")
    for name in a.names:
        v = list(json.loads((OUT / f"{name}-full-labels.json").read_text()).values())
        n = len(v)
        pct = lambda k: f"{100 * k / n:4.0f}%"
        fix = sum(x["primary"] == "fix" for x in v)
        hid = sum(bool(x["contains_fix"]) and x["primary"] != "fix" for x in v)
        ref = sum(x["primary"] == "refactor" for x in v)
        corr = sum(bool(x["contains_fix"]) or x["primary"] == "refactor" for x in v)
        feat = sum(x["primary"] == "feature" for x in v)
        print(f"{name:20}{n:4} {pct(feat)} {pct(fix)} {pct(hid):>6} {pct(ref):>6} {pct(corr):>7}")


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
    sub.add_parser("score")
    m = sub.add_parser("mix")
    m.add_argument("names", nargs="+")
    a = ap.parse_args()
    {"sample": cmd_sample, "oracle": cmd_oracle, "score": cmd_score, "mix": cmd_mix}[a.cmd](a)


if __name__ == "__main__":
    main()
