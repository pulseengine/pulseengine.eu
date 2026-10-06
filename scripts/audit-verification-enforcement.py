#!/usr/bin/env python3
"""Find verification evidence that exists in a repo but that nothing runs.

This is `gate-potency` audit 4 — "Defined implies enforced" — applied across the
org, mechanically, so it can be re-run instead of remembered. The skill already
names the class: *a check that exists in the tool but appears in no workflow is
not a gate; registry entries, scripts and harnesses are inert until something
runs them.* Nobody had run it over the proof artefacts.

The failure it looks for is the half-finished state, which is worse than the
absent one because it reads as done. Measured 2026-10-06: meld carries 14,487
lines of Rocq with 350 `Qed` and 0 `Admitted`, and all seven of its
`rocq_proof_test` targets are tagged `manual` — which excludes them from Bazel
wildcards — while no meld workflow invokes bazel at all. The proofs are real and
unreachable.

================================ READ THIS =================================
THIS AUDIT IS A LEAD GENERATOR, NOT A VERDICT. It reads file inventories,
BUILD files and workflow text over the GitHub API. It cannot see:

  * a tool invoked transitively (a Makefile, a shell script, a composite
    action, or a reusable workflow in another repo),
  * a check that runs in a scheduled job defined outside .github/workflows,
  * a proof re-checked by a human before release,
  * whether a proof that IS built proves anything useful (see
    `sigil`, whose Verus theorems end in `assume(false)` and say so).

It is also wrong in the other direction. A repo with NO row is not a repo
whose proofs are enforced — it is a repo where a non-comment line in some
workflow mentioned a checker. `synth` runs `bazel test //coq:verify_proofs`
and genuinely is enforced; a repo that merely runs `cargo test` while its
Rocq sits unbuilt would also produce no row. Absence of a row means "no
cheap signal", never "verified".

So treat every row as "look here", and confirm by opening the repo before
filing or fixing anything. If you confirm a row is wrong, add the repo and
the reason to KNOWN_EXCEPTIONS below so the next run does not re-raise it.
An agent re-running this should re-derive the findings, not trust this
docstring: the counts above were true on 2026-10-06 and say nothing about
today.
============================================================================

Needs network and `gh` auth. Deliberately NOT a CI gate: it crosses repo
boundaries and depends on the GitHub API, so it is a thing you run, not a thing
that blocks a merge.

Exit: 0 nothing unenforced · 1 leads found · 2 could not run the audit.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys

# Repos that carry formal-verification or structural-coverage evidence.
REPOS = ["ordeal", "meld", "gale", "scry", "synth", "sigil", "rivet",
         "kiln", "relay", "loom", "spar", "witness", "varve"]

PROOF_EXT = {"v": "Rocq/Coq", "lean": "Lean"}

# Things a workflow can say that mean "a proof or coverage check actually runs".
INVOKES = ["bazel test", "bazel build", "lake build", "lake exe", "rocq", "coqc",
           "dune build", "verus", "cargo kani", "kani ", "regen.sh", "coq-of-rust",
           "charon", "aeneas", "mcdc", "instrument-coverage"]

# Confirmed-by-hand exceptions. Add here rather than silencing the whole repo,
# and say WHY — a bare repo name teaches the next reader nothing.
KNOWN_EXCEPTIONS: dict[str, str] = {
    # "repo": "reason this row is not a finding, with the evidence",
}


def gh(path: str):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def tree(repo: str) -> list | None:
    """Whole file list in ONE call.

    This used to call the code-search API once per repo per extension. Code
    search is limited to 30 requests a minute, the limit was hit, `search_count`
    returned -1, and `if n > 0` silently dropped every rate-limited repo — so
    the audit reported "3 repos examined" and read as though the other ten had
    no proofs. An audit that cannot tell "none" from "could not look" is the
    thing this script exists to find. The trees API is on the 5000/hour core
    limit and answers in one request.
    """
    meta = gh(f"repos/pulseengine/{repo}")
    if not meta:
        return None
    branch = meta.get("default_branch", "main")
    t = gh(f"repos/pulseengine/{repo}/git/trees/{branch}?recursive=1")
    if not t or "tree" not in t:
        return None
    return [e["path"] for e in t["tree"] if e.get("type") == "blob"]


def workflow_text(repo: str) -> str | None:
    wfs = gh(f"repos/pulseengine/{repo}/contents/.github/workflows")
    if wfs is None:
        return None
    body = []
    for w in wfs:
        c = gh(f"repos/pulseengine/{repo}/contents/.github/workflows/{w['name']}")
        if not c or "content" not in c:
            continue
        text = base64.b64decode(c["content"]).decode("utf-8", "replace")
        # Strip YAML comments. A repo whose workflows merely DISCUSS bazel or
        # Rocq in a comment is not a repo that runs them — matching raw text
        # made `gale` look enforced on the strength of a comment explaining why
        # `bazel test //...` is NOT run there.
        body.append("\n".join(l for l in text.splitlines()
                               if not l.lstrip().startswith("#")))
    return "\n".join(body)


def manual_tagged(repo: str, paths: list[str]) -> tuple[int, int]:
    """(proof test targets, of those tagged `manual`).

    Bazel's `manual` tag excludes a target from //... , so a proof test carrying
    it is invisible to a wildcard build even when one runs.
    """
    total = tagged = 0
    for p in [p for p in paths if p.endswith("BUILD.bazel") or p.endswith("BUILD")]:
        c = gh(f"repos/pulseengine/{repo}/contents/{p}")
        if not c or "content" not in c:
            continue
        body = base64.b64decode(c["content"]).decode("utf-8", "replace")
        for m in re.finditer(r"(rocq_proof_test|lean_proof_test|verus_test)\((.*?)\n\)",
                             body, re.S):
            total += 1
            if "manual" in m.group(2):
                tagged += 1
    return total, tagged


def main() -> int:
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        print("error: gh is not authenticated — the audit cannot read anything",
              file=sys.stderr)
        return 2

    rows, examined, unreadable = [], 0, []
    for repo in REPOS:
        paths = tree(repo)
        if paths is None:
            unreadable.append(repo)
            continue
        proofs = {}
        for ext, lang in PROOF_EXT.items():
            n = sum(1 for p in paths if p.endswith("." + ext))
            if n:
                proofs[lang] = n
        if not proofs:
            examined += 1
            continue

        wf = workflow_text(repo)
        if wf is None:
            unreadable.append(repo)
            continue
        examined += 1
        low = wf.lower()
        runs = sorted({k for k in INVOKES if k in low})
        total, tagged = manual_tagged(repo, paths)

        if not runs:
            verdict = "NOTHING IN ANY WORKFLOW INVOKES A PROOF CHECKER"
        elif tagged and not any("bazel" in r for r in runs):
            verdict = f"{tagged}/{total} proof targets tagged manual, and no bazel invocation"
        elif tagged:
            verdict = f"{tagged}/{total} proof targets tagged manual — excluded from //..."
        else:
            verdict = ""
        if verdict:
            rows.append((repo, proofs, verdict))

    print(f"{examined} of {len(REPOS)} repos examined, {len(rows)} with a lead")
    if unreadable:
        print(f"\nerror: could NOT read {len(unreadable)} repo(s): "
              f"{', '.join(unreadable)}", file=sys.stderr)
        print("A repo this audit could not read is NOT a repo without findings. "
              "Re-run when the API is reachable; do not report this run as a "
              "clean sweep.", file=sys.stderr)
        return 2
    if not examined:
        print("error: examined nothing — the audit cannot tell you anything",
              file=sys.stderr)
        return 2
    print()

    if not rows:
        print("No repo carries proof artefacts that nothing appears to run.")
        return 0

    print(f"{'repo':10} {'evidence present':28} what the workflows suggest")
    print("-" * 92)
    for repo, proofs, verdict in rows:
        if repo in KNOWN_EXCEPTIONS:
            continue
        have = ", ".join(f"{n} {lang}" for lang, n in proofs.items())
        print(f"{repo:10} {have:28} {verdict}")

    print("\nEvery row is a LEAD. Open the repo and confirm before filing or "
          "fixing — this cannot see Makefiles, composite actions, reusable "
          "workflows, or a human re-checking a proof. Record a confirmed "
          "false positive in KNOWN_EXCEPTIONS with its reason.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
