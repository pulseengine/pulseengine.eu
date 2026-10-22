#!/usr/bin/env python3
"""Collect each fix's dominant introducer (most blamed lines) for labelling, and
the null: line-weighted share of added source lines written by fix commits in
the labelled sample (if fixes broke things at the rate they write code, the
fix-on-fix share would be about this)."""
import json, subprocess, sys, importlib.util as u
D = sys.argv[1]   # holds full/<repo> clones; run from the directory with cls/ and szz/
s = u.spec_from_file_location("cc", __file__.rsplit("/", 1)[0] + "/commit-classify.py"); m = u.module_from_spec(s); s.loader.exec_module(m)
P = {"hubris": ("hubris", (".rs",)), "cranelift": ("wasmtime", (".rs",)), "ccc": ("claudes-c-compiler", (".rs", ".c", ".h")),
     "beads": ("beads", (".go",)), "gastown": ("gastown", (".go",)), "rivet": ("rivet", (".rs",)), "spar": ("spar", (".rs",))}
todo = []
for n, (r, ext) in P.items():
    repo = f"{D}/full/{r}"
    for rec in json.load(open(f"szz/{n}.json")):
        if rec["introducers"]:
            top = rec["introducers"][0]
            todo.append({"id": f"{n}:{top['sha']}", "text": m.body(repo, top["sha"])})
    st = m.steps(repo, ext)
    lab = json.load(open(f"cls/{n}-full-labels.json"))
    add = {"fix": 0, "all": 0}
    for k, v in lab.items():
        h = st[int(k.rsplit("-", 1)[1])][0]
        out = subprocess.run(["git", "-C", repo, "show", "--numstat", "--format=", h], capture_output=True, text=True).stdout
        a = sum(int(l.split("\t")[0]) for l in out.splitlines() if l.split("\t")[0].isdigit() and l.split("\t")[-1].endswith(ext))
        add["all"] += a; add["fix"] += a if v["primary"] == "fix" else 0
    null = 100 * add["fix"] / max(1, add["all"])
    json.dump({"fix_share_of_added_lines": null, "added": add}, open(f"szz/{n}-null.json", "w"))
    print(f"{n:10} null (fix share of added lines) {null:.1f}%")
uniq = {t["id"]: t for t in todo}
json.dump(list(uniq.values()), open("szz/introducers-input.json", "w"), indent=0)
print("introducers to label:", len(uniq))
