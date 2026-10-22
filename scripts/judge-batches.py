#!/usr/bin/env python3
"""Second instrument for the refactor class: the same sampled commits, judged
from message AND diff by a different model, blind to project and first label.

    judge-batches.py build <name>=<clone>:<ext,ext>[:until] ...   # judge/q*.json + judge/key.json
    judge-batches.py merge                                         # judge/*.labels.json -> cls/judge-diff-labels.json

Each batch item is {id, message, diff}: the message with conventional prefixes
stripped on every line (commit-classify.body), the diff limited to source
files and truncated at 3,500 characters. Ids are shuffled across projects so
the judge cannot tell which project a commit belongs to. Labels per id:
{"primary": feature|fix|refactor|maintenance, "refactor": bool}."""
import importlib.util as u, json, pathlib, random, subprocess, sys

here = pathlib.Path(__file__).parent
s = u.spec_from_file_location("cc", here / "commit-classify.py"); m = u.module_from_spec(s); s.loader.exec_module(m)
J = pathlib.Path("judge")


def build(specs):
    random.seed(23)
    items = []
    for spec in specs:
        name, rest = spec.split("=", 1)
        parts = rest.split(":")
        repo, exts, until = parts[0], tuple(parts[1].split(",")), (parts[2] if len(parts) > 2 else None)
        st = m.steps(repo, exts, until)
        for k in json.loads((m.OUT / f"{name}-full-labels.json").read_text()):
            h = st[int(k.rsplit("-", 1)[1])][0]
            diff = subprocess.run(["git", "-C", repo, "show", "--format=", "--stat=120", "-p", "-U2", h, "--",
                                   *[f"*{x}" for x in exts]], capture_output=True, text=True, errors="replace").stdout
            items.append({"k": k, "h": h, "message": m.body(repo, h), "diff": diff[:3500]})
    random.shuffle(items)
    J.mkdir(exist_ok=True)
    key = {f"j{i:04d}": {"k": it["k"], "h": it["h"]} for i, it in enumerate(items)}
    pub = [{"id": f"j{i:04d}", "message": it["message"], "diff": it["diff"]} for i, it in enumerate(items)]
    for b in range(0, len(pub), 30):
        (J / f"q{b // 30:03d}.json").write_text(json.dumps(pub[b:b + 30], indent=0))
    (J / "key.json").write_text(json.dumps(key))
    print(len(pub), "items in", (len(pub) + 29) // 30, "batches")


def merge():
    key = json.loads((J / "key.json").read_text())
    lab = {}
    for f in sorted(J.glob("*.labels.json")):
        lab.update(json.loads(f.read_text()))
    missing, extra = set(key) - set(lab), set(lab) - set(key)
    bad = [i for i, v in lab.items() if v.get("primary") not in m.CATS]
    if missing or extra or bad:
        raise SystemExit(f"refusing: {len(missing)} missing, {len(extra)} extra, {len(bad)} malformed")
    out = {v["k"]: lab[i] for i, v in key.items()}
    (m.OUT / "judge-diff-labels.json").write_text(json.dumps(out, indent=0))
    print(len(out), "judged commits")


if __name__ == "__main__":
    build(sys.argv[2:]) if sys.argv[1] == "build" else merge()
