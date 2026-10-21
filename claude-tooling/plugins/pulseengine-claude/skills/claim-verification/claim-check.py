#!/usr/bin/env python3
"""claim-check — gate a repo's documentation claims against live evidence.

Reference implementation for the `claim-verification` skill. A repo drops a
`claims.yaml` next to its docs; CI runs this; drift between a claim, its recorded
ledger, and the *actual source* fails the build. Truth-over-time becomes a property
of the gate, not the author.

Usage:  claim-check.py [claims.yaml]     (default: ./claims.yaml)
        claim-check.py --self-test        (decision table over fixtures)
Exit:   0 = all claims hold · 1 = one or more drifted

A repo may reimplement this in Rust (cf. tools/fetch-reports); the shape is what
matters. Evidence predicates re-derive from source — never a number typed in prose.

claims.yaml shape:
  claims:
    - id: LOOM-BADGE
      doc: README.md
      text: "Translation-Validated"          # must appear VERBATIM in `doc`
      evidence:
        - kind: file-exists
          path: proofs/Correctness.v
        - kind: count-max                      # re-count from source; fail if over
          pattern: '#\\[verifier::external_body\\]'
          glob: ['src/**/*.rs']
          max: 133
        - kind: no-new                         # no new sorry/admit since recorded
          pattern: '\\bAdmitted\\b'
          glob: ['proofs/**/*.v']
          recorded: 74

COUPLED ARTIFACTS (pulseengine.eu#198) — two things that must agree, checked as a
pair rather than each on its own. A side is a SET of names, taken either from
paths on disk or from a doc:

    {glob: 'skills/*/SKILL.md', name: 'skills/([^/]+)/'}      # group 1 of each path
    {file: 'README.md', pattern: '^- `([a-z-]+)`', after: '## Skills', before: '## '}

        - kind: set-equal          # both directions; neither side may be empty
          left:  {glob: ..., name: ...}
          right: {file: ..., pattern: ...}
          waive: [name, ...]       # existing debt, printed on EVERY run, never silent
        - kind: count-equals       # a number written in prose == a set's size
          number: {file: README.md, pattern: '# (\\d+) custom skills'}
          set:    {glob: 'skills/*/SKILL.md', name: 'skills/([^/]+)/'}

The three rules #198 found made such checks actually work, and this enforces two
of them: a side that yields nothing FAILS ("0 mismatches" and "nothing compared"
must never look alike), and a waiver is printed every run. The third, watching the
detector fail, is the --self-test below.
"""
import sys
import re
import glob
import pathlib

try:
    import yaml
except ImportError:
    sys.exit("claim-check: needs PyYAML  (pip install pyyaml)")


def _count(pattern, globs, root):
    rx = re.compile(pattern)
    globs = [globs] if isinstance(globs, str) else globs
    total = 0
    matched_any = False
    for g in globs:
        # Resolve globs relative to the claims file's directory, NOT the CWD —
        # otherwise the predicate silently matches nothing and greens a claim it
        # never checked (the "oracle that measures nothing" failure).
        for f in glob.glob(str(root / g), recursive=True):
            p = pathlib.Path(f)
            if p.is_file():
                matched_any = True
                total += len(rx.findall(p.read_text(errors="ignore")))
    return total, matched_any


def _side(spec, root):
    """A set of names, from paths on disk or from a doc. Returns (names, error)."""
    if "glob" in spec:
        rx = re.compile(spec.get("name", r"([^/]+?)(?:\.[^/.]+)?$"))
        names = set()
        for f in glob.glob(str(root / spec["glob"]), recursive=True):
            rel = pathlib.Path(f).relative_to(root).as_posix()
            m = rx.search(rel)
            if m:
                names.add(m.group(1))
        return names, None if names else f'side matched NO paths: glob {spec["glob"]!r}'
    if "file" in spec:
        p = root / spec["file"]
        if not p.exists():
            return set(), f'side file not found: {spec["file"]}'
        text = p.read_text(errors="ignore")
        if spec.get("after"):
            i = text.find(spec["after"])
            if i < 0:
                return set(), f'section start {spec["after"]!r} not found in {spec["file"]}'
            text = text[i + len(spec["after"]):]
        if spec.get("before"):
            j = text.find(spec["before"])
            if j >= 0:
                text = text[:j]
        names = set(re.findall(spec["pattern"], text, re.M))
        return names, None if names else f'side pattern matched NOTHING in {spec["file"]}'
    return set(), "side needs either glob or file"


def check_claim(c, root):
    fails = []
    doc_path = root / c["doc"]
    doc = doc_path.read_text(errors="ignore") if doc_path.exists() else ""
    if not doc_path.exists():
        return [f'doc not found: {c["doc"]}']

    text = c.get("text")
    if text and text not in doc:
        fails.append(f'claim text not found verbatim in {c["doc"]}: "{text}"')

    for ev in c.get("evidence", []):
        kind = ev.get("kind")
        if kind == "verbatim":
            s = ev.get("text", text)
            if s and s not in doc:
                fails.append(f'verbatim string absent from {c["doc"]}: "{s}"')
        elif kind == "file-exists":
            if not (root / ev["path"]).exists():
                fails.append(f'evidence file missing: {ev["path"]}')
        elif kind == "count-max":
            n, matched = _count(ev["pattern"], ev["glob"], root)
            if not matched:
                fails.append(f'predicate matched NO files (measures nothing): glob {ev["glob"]}')
            elif n > ev["max"]:
                fails.append(
                    f'trusted base grew: {n} > recorded max {ev["max"]}  '
                    f'[/{ev["pattern"]}/]  — update the claim, not the number'
                )
        elif kind == "count-min":
            # PRESENCE claim: the pattern MUST appear >= min times. The dual of
            # count-max (which greens a 0-match, since 0 > max is false). Catches
            # DRIFT-TO-ABSENT — a string the doc asserts that the source no longer
            # carries (e.g. a version bumped in Cargo.toml the README still names).
            n, matched = _count(ev["pattern"], ev["glob"], root)
            if not matched:
                fails.append(f'predicate matched NO files (measures nothing): glob {ev["glob"]}')
            elif n < ev["min"]:
                fails.append(
                    f'claim evidence absent: {n} < required min {ev["min"]}  '
                    f'[/{ev["pattern"]}/]  — the doc asserts it; the source no longer carries it'
                )
        elif kind == "no-new":
            n, matched = _count(ev["pattern"], ev["glob"], root)
            if not matched:
                fails.append(f'predicate matched NO files (measures nothing): glob {ev["glob"]}')
            elif n > ev.get("recorded", 0):
                fails.append(
                    f'new unproven obligations: {n} > recorded {ev.get("recorded", 0)}  '
                    f'[/{ev["pattern"]}/]'
                )
        elif kind == "set-equal":
            left, el = _side(ev["left"], root)
            right, er = _side(ev["right"], root)
            for e in (el, er):
                if e:
                    fails.append(f"{e}  — an empty side compares nothing")
            if not (el or er):
                waived = set(ev.get("waive", []))
                for w in sorted(waived):
                    print(f"    waived (debt, printed every run): {w}")
                only_l = sorted(left - right - waived)
                only_r = sorted(right - left - waived)
                if only_l:
                    fails.append(f"in left but not right: {', '.join(only_l)}")
                if only_r:
                    fails.append(f"in right but not left: {', '.join(only_r)}")
        elif kind == "count-equals":
            names, es = _side(ev["set"], root)
            p = root / ev["number"]["file"]
            m = re.search(ev["number"]["pattern"], p.read_text(errors="ignore")) if p.exists() else None
            if es:
                fails.append(f"{es}  — an empty side compares nothing")
            elif not m:
                fails.append(f'stated number not found: /{ev["number"]["pattern"]}/ in {ev["number"]["file"]}')
            elif int(m.group(1)) != len(names):
                fails.append(f'{ev["number"]["file"]} states {m.group(1)}, the source holds {len(names)}')
        else:
            fails.append(f'unknown evidence kind: {kind!r}')
    return fails


def self_test():
    """Each rule in BOTH directions, over throwaway fixtures. A rule seen only to
    pass is indistinguishable from one that cannot fail (pulseengine.eu#198)."""
    import tempfile
    def run(files, ev):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            for rel, body in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(body)
            (root / "doc.md").write_text((root / "doc.md").read_text() if (root / "doc.md").exists() else "x")
            return check_claim({"id": "T", "doc": "doc.md", "evidence": [ev]}, root)
    two = {"s/a/SKILL.md": "", "s/b/SKILL.md": ""}
    disk = {"glob": "s/*/SKILL.md", "name": r"s/([^/]+)/"}
    doc = lambda body: {**two, "doc.md": body}
    table = {"file": "doc.md", "pattern": r"^- `([a-z]+)`", "after": "## S", "before": "## E"}
    cases = [
        ("set-equal: sets match -> holds", doc("## S\n- `a`\n- `b`\n## E\n"),
         {"kind": "set-equal", "left": disk, "right": table}, False),
        ("set-equal: doc lacks one -> fails", doc("## S\n- `a`\n## E\n"),
         {"kind": "set-equal", "left": disk, "right": table}, True),
        ("set-equal: doc lists a phantom -> fails", doc("## S\n- `a`\n- `b`\n- `c`\n## E\n"),
         {"kind": "set-equal", "left": disk, "right": table}, True),
        ("set-equal: empty doc side -> FAILS, not 0 mismatches", doc("## S\n## E\n"),
         {"kind": "set-equal", "left": disk, "right": table}, True),
        ("set-equal: empty disk side -> FAILS", {"doc.md": "## S\n- `a`\n## E\n"},
         {"kind": "set-equal", "left": disk, "right": table}, True),
        # The two guards in isolation: with every difference waived, ONLY the
        # empty-side guard can fail the claim. Without these cases a mutant that
        # disables a guard survives, because the set difference fails it anyway.
        ("set-equal: empty doc side, differences waived -> still FAILS", doc("## S\n## E\n"),
         {"kind": "set-equal", "left": disk, "right": table, "waive": ["a", "b"]}, True),
        ("set-equal: empty disk side, differences waived -> still FAILS", {"doc.md": "## S\n- `a`\n## E\n"},
         {"kind": "set-equal", "left": disk, "right": table, "waive": ["a"]}, True),
        ("set-equal: waived name excluded", doc("## S\n- `a`\n## E\n"),
         {"kind": "set-equal", "left": disk, "right": table, "waive": ["b"]}, False),
        ("set-equal: section bounds respected", doc("- `z`\n## S\n- `a`\n- `b`\n## E\n- `y`\n"),
         {"kind": "set-equal", "left": disk, "right": table}, False),
        ("count-equals: stated == actual -> holds", doc("# 2 custom skills"),
         {"kind": "count-equals", "number": {"file": "doc.md", "pattern": r"# (\d+) custom"}, "set": disk}, False),
        ("count-equals: stated != actual -> fails", doc("# 18 custom skills"),
         {"kind": "count-equals", "number": {"file": "doc.md", "pattern": r"# (\d+) custom"}, "set": disk}, True),
        ("count-equals: number missing -> fails", doc("no number here"),
         {"kind": "count-equals", "number": {"file": "doc.md", "pattern": r"# (\d+) custom"}, "set": disk}, True),
        ("count-equals: empty set -> fails", {"doc.md": "# 0 custom skills"},
         {"kind": "count-equals", "number": {"file": "doc.md", "pattern": r"# (\d+) custom"}, "set": disk}, True),
    ]
    bad = 0
    print("claim-check self-test")
    for name, files, ev, expect_fail in cases:
        got = bool(run(files, ev))
        ok = got == expect_fail
        bad += not ok
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"  {len(cases) - bad}/{len(cases)} cases hold")
    return 1 if bad else 0


def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "claims.yaml")
    if not path.exists():
        sys.exit(f"claim-check: {path} not found")
    root = path.parent
    data = yaml.safe_load(path.read_text()) or {}
    claims = data.get("claims", [])
    if not claims:
        print("claim-check: no claims declared — nothing to gate.")
        return

    bad = 0
    for c in claims:
        fails = check_claim(c, root)
        if fails:
            bad += 1
            print(f"✗ {c['id']}")
            for f in fails:
                print(f"    {f}")
        else:
            print(f"✓ {c['id']}")

    print(f"\n{len(claims) - bad}/{len(claims)} claims hold.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
