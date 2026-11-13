#!/usr/bin/env python3
"""Check every PulseEngine repo's Lean pin against data/lean-pins.toml.

Policy, not lockstep (owner decision 2026-11-13). The rules are written in the
data file's header: stable releases only, at most `max_minor_behind` minors
behind the org target, a target reviewed every `review_days` days, and
exceptions that expire.

Pins are read from each repo's default branch over raw.githubusercontent.com,
which needs no token for public repos. The runners carry no `gh` CLI.

Blind spot: only the repos listed in the data file are checked. A repo that
adds a Lean pin is not discovered until someone lists it.

Exit: 0 every pin is within policy · 1 a rule is broken · 2 could not run
(a pin could not be fetched or parsed: a gate that cannot reach its evidence
has verified nothing).
`--self-test` runs each rule against a planted violation (negative controls).
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys
import urllib.request

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - the macOS floor is 3.9
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        print("check-lean-pins: needs Python 3.11+ or the tomli package", file=sys.stderr)
        sys.exit(2)

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "lean-pins.toml"
RAW = "https://raw.githubusercontent.com/pulseengine/{repo}/HEAD/{path}"

VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.]+)?$")
ELAN = re.compile(r"^leanprover/lean4:v?(\S+)$")
BAZEL = re.compile(r'lean\.toolchain\(\s*version\s*=\s*"([^"]+)"')


class FetchError(Exception):
    pass


def parse_version(v: str):
    m = VERSION.match(v)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or ""


def extract_pin(kind: str, text: str):
    if kind == "elan":
        m = ELAN.match(text.strip())
    elif kind == "bazel":
        m = BAZEL.search(text)
    else:
        return None
    return m.group(1) if m else None


def fetch(repo: str, path: str) -> str:
    url = RAW.format(repo=repo, path=path)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 - fixed host
            return r.read().decode("utf-8")
    except Exception as e:  # pragma: no cover - network
        raise FetchError(f"{repo}/{path}: {e}") from e


def check(doc: dict, pins: dict, today: dt.date) -> list:
    """Return a list of rule violations. `pins` maps repo name to version string."""
    errs = []
    pol = doc.get("policy", {})
    target = parse_version(str(pol.get("target", "")))
    if target is None or target[3]:
        errs.append(f"policy: target {pol.get('target')!r} is not a stable release")
        return errs
    try:
        reviewed = dt.date.fromisoformat(str(pol["target_reviewed"]))
        days = int(pol["review_days"])
        behind = int(pol["max_minor_behind"])
    except (KeyError, ValueError) as e:
        errs.append(f"policy: missing or malformed field ({e})")
        return errs
    if (today - reviewed).days > days:
        errs.append(f"policy: target {pol['target']} last reviewed {reviewed}, more than {days} days ago; "
                    "review the target (bump it or re-date target_reviewed)")

    exceptions = {}
    for ex in doc.get("exception", []):
        try:
            exp = dt.date.fromisoformat(str(ex["expires"]))
        except (KeyError, ValueError):
            errs.append(f"exception for {ex.get('repo')!r}: missing or malformed expires")
            continue
        if not str(ex.get("reason", "")).strip():
            errs.append(f"exception for {ex.get('repo')!r}: no reason")
        if exp < today:
            errs.append(f"exception for {ex.get('repo')}: expired {exp}")
            continue
        exceptions[ex.get("repo")] = exp

    for repo in doc.get("repo", []):
        name = repo["name"]
        raw = pins.get(name)
        v = parse_version(raw or "")
        if v is None:
            errs.append(f"{name}: pin {raw!r} is not a Lean version")
            continue
        problems = []
        if v[3]:
            problems.append(f"{raw} is a release candidate")
        if v[0] != target[0] or v[1] < target[1] - behind:
            problems.append(f"{raw} is more than {behind} minors behind the target {pol['target']}")
        if problems and name not in exceptions:
            errs.extend(f"{name}: {p}" for p in problems)
    return errs


def self_test() -> int:
    today = dt.date(2026, 11, 13)
    base = {
        "policy": {"target": "4.29.1", "target_reviewed": "2026-11-13", "review_days": 100,
                   "max_minor_behind": 3},
        "repo": [{"name": "a", "path": "lean-toolchain", "kind": "elan"}],
        "exception": [],
    }

    def doc(**kw):
        d = {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in base.items()}
        for k, v in kw.items():
            if k in d["policy"]:
                d["policy"][k] = v
            else:
                d[k] = v
        return d

    cases = [
        # (label, doc, pins, today, expect_fail)
        ("pin at target passes", doc(), {"a": "4.29.1"}, today, False),
        ("pin ahead of target passes", doc(), {"a": "4.35.0"}, today, False),
        ("pin 3 behind passes", doc(), {"a": "4.26.0"}, today, False),
        ("pin 4 behind fails", doc(), {"a": "4.25.0"}, today, True),
        ("release candidate fails", doc(), {"a": "4.30.0-rc2"}, today, True),
        ("unparsable pin fails", doc(), {"a": "nightly"}, today, True),
        ("missing pin fails", doc(), {}, today, True),
        ("rc target fails", doc(target="4.30.0-rc1"), {"a": "4.29.1"}, today, True),
        ("stale target review fails", doc(), {"a": "4.29.1"}, dt.date(2027, 3, 1), True),
        ("live exception covers rc", doc(exception=[{"repo": "a", "reason": "r", "expires": "2027-01-01"}]),
         {"a": "4.30.0-rc2"}, today, False),
        ("expired exception fails", doc(exception=[{"repo": "a", "reason": "r", "expires": "2026-11-01"}]),
         {"a": "4.30.0-rc2"}, today, True),
        ("exception without reason fails", doc(exception=[{"repo": "a", "reason": "", "expires": "2027-01-01"}]),
         {"a": "4.29.1"}, today, True),
        ("major mismatch fails", doc(), {"a": "5.0.0"}, today, True),
    ]
    extract = [
        ("elan", "leanprover/lean4:v4.30.0-rc2\n", "4.30.0-rc2"),
        ("bazel", 'lean.toolchain(version = "4.27.0")', "4.27.0"),
        ("elan", "leanprover/lean4:stable\n", "stable"),
        ("bazel", "no toolchain here", None),
    ]
    bad = 0
    for label, d, pins, day, expect in cases:
        got = bool(check(d, pins, day))
        ok = got == expect
        bad += not ok
        print(f"  {'ok ' if ok else 'BAD'} {label}: {'fail' if got else 'pass'}")
    for kind, text, want in extract:
        got = extract_pin(kind, text)
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'BAD'} extract {kind} {text.strip()!r} -> {got!r}")
    print(f"self-test: {len(cases) + len(extract) - bad}/{len(cases) + len(extract)} as expected")
    return 1 if bad else 0


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    if sys.argv[1:]:
        print("usage: check-lean-pins.py [--self-test]", file=sys.stderr)
        return 2
    doc = tomllib.loads(DATA.read_text())
    pins = {}
    try:
        for repo in doc.get("repo", []):
            text = fetch(repo["name"], repo["path"])
            pin = extract_pin(repo.get("kind", ""), text)
            if pin is None:
                print(f"check-lean-pins: no Lean pin found in {repo['name']}/{repo['path']}", file=sys.stderr)
                return 2
            pins[repo["name"]] = pin
    except FetchError as e:
        print(f"check-lean-pins: could not fetch {e}", file=sys.stderr)
        return 2
    for name, pin in sorted(pins.items()):
        print(f"  {name}: {pin}")
    errs = check(doc, pins, dt.date.today())
    for e in errs:
        print(f"FAIL {e}")
    print(f"lean pins: {len(pins)} repos, {len(errs)} violation(s), target {doc['policy']['target']}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
