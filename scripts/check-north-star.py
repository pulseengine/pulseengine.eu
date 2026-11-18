#!/usr/bin/env python3
"""Fail if data/north-star.toml breaks the rules the North Star page depends on.

The file is read by the /north-star page, by each repository's `serves:`
allowed-values list and by the indicator scripts, so a malformed entry breaks
three readers at once, and some of the rules are about honesty rather than
syntax:

  1. every objective has an id (O<n>, unique), a title, a summary, an
     indicator and a guard metric; a guard is required because agents work on
     whatever number a gate checks;
  2. an objective's state is "unmeasured" or "measured", so nothing can show
     a made-up zero;
  3. every commitment and every product names an objective that exists, and a
     commitment is "committed" or "stretch";
  4. a period's layers are varve layer names (YYYY.MM);
  5. the North Star sentence carries no date: the goal moves, only steps are
     dated;
  6. no private infrastructure detail: no IPv4 address and no host name under
     a local-network suffix;
  7. "measured" and a script-written measurement go together: an objective is
     "measured" exactly when data/north-star/<id>.json exists, names that
     objective and carries an integer value out of a positive denominator, so
     no number can be typed into the TOML.

Exit: 0 consistent · 1 a rule is broken · 2 could not run the check
(including a value of a type the rules cannot handle, e.g. objectives = 5).
`--self-test` runs each rule against a planted violation (negative controls).
`--root DIR` checks DIR/data instead of this repository's (the component
equivalence harness, tools/north-star-check/cases.py, uses it).
"""

from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import re
import sys

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - the macOS floor is 3.9
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        print("check-north-star: needs Python 3.11+ or the tomli package", file=sys.stderr)
        sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "north-star.toml"
MEASURE_DIR = ROOT / "data" / "north-star"

ID_RE = re.compile(r"^O[1-9][0-9]*$")
LAYER_RE = re.compile(r"^20[0-9]{2}\.(0[1-9]|1[0-2])$")
DATE_RE = re.compile(r"\b(20[0-9]{2}|Q[1-4]\b)")
IPV4_RE = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
HOST_RE = re.compile(r"\b[a-z0-9-]+\.(?:local|lan|home|internal|intranet)\b", re.I)
STATES = {"unmeasured", "measured"}
KINDS = {"committed", "stretch"}
OBJECTIVE_FIELDS = ("id", "title", "summary", "indicator", "guard", "state")


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _measurement(oid: str, measure_dir: pathlib.Path):
    p = measure_dir / ("%s.json" % oid)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def check(doc: dict, measure_dir: pathlib.Path = MEASURE_DIR) -> list:
    errors = []
    star = doc.get("north_star")
    if not isinstance(star, str) or not star.strip():
        errors.append("north_star is missing or empty")
    elif DATE_RE.search(star):
        errors.append("north_star carries a date; only commitments are dated")

    objectives = doc.get("objectives") or []
    if not objectives:
        errors.append("no objectives")
    ids = set()
    for i, o in enumerate(objectives):
        where = "objectives[%d]" % i
        for f in OBJECTIVE_FIELDS:
            v = o.get(f)
            if not isinstance(v, str) or not v.strip():
                errors.append("%s: field %r is missing or empty" % (where, f))
        oid = o.get("id", "")
        if oid and not ID_RE.match(oid):
            errors.append("%s: id %r is not O<n>" % (where, oid))
        if oid in ids:
            errors.append("%s: duplicate id %r" % (where, oid))
        ids.add(oid)
        state = o.get("state")
        if state and state not in STATES:
            errors.append("%s: state %r is not one of %s" % (where, state, sorted(STATES)))
        m = _measurement(oid, measure_dir) if oid else None
        if state == "measured":
            if m is None:
                errors.append("%s: state is measured but data/north-star/%s.json is missing" % (where, oid))
            elif not (m.get("objective") == oid and isinstance(m.get("value"), int)
                      and isinstance(m.get("of"), int) and m["of"] > 0 and 0 <= m["value"] <= m["of"]):
                errors.append("%s: data/north-star/%s.json is not a valid measurement" % (where, oid))
        elif m is not None:
            errors.append("%s: data/north-star/%s.json exists but state is %r" % (where, oid, state))

    for i, p in enumerate(doc.get("periods") or []):
        where = "periods[%d]" % i
        layers = p.get("layers") or []
        if not layers:
            errors.append("%s: no varve layers" % where)
        for layer in layers:
            if not LAYER_RE.match(str(layer)):
                errors.append("%s: layer %r is not YYYY.MM" % (where, layer))
        for j, c in enumerate(p.get("commitments") or []):
            cw = "%s.commitments[%d]" % (where, j)
            if c.get("objective") not in ids:
                errors.append("%s: objective %r does not exist" % (cw, c.get("objective")))
            if c.get("kind") not in KINDS:
                errors.append("%s: kind %r is not one of %s" % (cw, c.get("kind"), sorted(KINDS)))
            if not str(c.get("target", "")).strip():
                errors.append("%s: target is empty" % cw)

    for i, pr in enumerate(doc.get("products") or []):
        for pid in pr.get("pulls") or []:
            if pid not in ids:
                errors.append("products[%d] (%s): pulls unknown objective %r" % (i, pr.get("name"), pid))

    for s in _strings(doc):
        if IPV4_RE.search(s) or HOST_RE.search(s):
            errors.append("private infrastructure detail in text: %r" % s[:60])
    return errors


def self_test() -> int:
    base = tomllib.loads(DATA.read_text(encoding="utf-8"))
    if check(base):
        print("self-test: the committed file must pass first:", check(base), file=sys.stderr)
        return 1

    def mutate(fn):
        d = copy.deepcopy(base)
        fn(d)
        return d

    cases = {
        "missing guard": lambda d: d["objectives"][0].pop("guard"),
        "bad id": lambda d: d["objectives"][0].update(id="X1"),
        "duplicate id": lambda d: d["objectives"][1].update(id=d["objectives"][0]["id"]),
        "made-up zero": lambda d: d["objectives"][0].update(state="0%"),
        "unknown commitment objective": lambda d: d["periods"][0]["commitments"][0].update(objective="O99"),
        "bad kind": lambda d: d["periods"][0]["commitments"][0].update(kind="maybe"),
        "bad layer": lambda d: d["periods"][0]["layers"].append("2026-11"),
        "unknown pull": lambda d: d["products"][0]["pulls"].append("O99"),
        "dated north star": lambda d: d.update(north_star=d["north_star"] + " By 2027."),
        "ipv4": lambda d: d["objectives"][0].update(summary="runs on 10.0.0.5"),
        "local host": lambda d: d["objectives"][0].update(summary="measured on box.lan"),
    }
    failed = 0
    for name, fn in cases.items():
        if not check(mutate(fn)):
            print("self-test: planted %r was NOT caught" % name, file=sys.stderr)
            failed += 1

    # Rule 7 against planted measurement directories.
    first = base["objectives"][0]["id"]
    good = {"objective": first, "value": 1, "of": 2}
    dir_cases = {
        "measured without a file": (lambda d: d["objectives"][0].update(state="measured"), None),
        "file without measured": (lambda d: d["objectives"][0].update(state="unmeasured"), good),
        "value above denominator": (lambda d: d["objectives"][0].update(state="measured"),
                                    {"objective": first, "value": 3, "of": 2}),
        "file for another objective": (lambda d: d["objectives"][0].update(state="measured"),
                                       {"objective": "O99", "value": 1, "of": 2}),
    }
    for name, (fn, payload) in dir_cases.items():
        with tempfile.TemporaryDirectory() as tmp:
            md = pathlib.Path(tmp)
            d = mutate(fn)
            for o in d["objectives"][1:]:
                o["state"] = "unmeasured"
            if payload is not None:
                (md / ("%s.json" % first)).write_text(json.dumps(payload))
            if not check(d, md):
                print("self-test: planted %r was NOT caught" % name, file=sys.stderr)
                failed += 1
    total = len(cases) + len(dir_cases)
    print("self-test: %d of %d planted violations caught" % (total - failed, total))
    return 1 if failed else 0


def main() -> int:
    global DATA, MEASURE_DIR
    argv = sys.argv[1:]
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 >= len(argv):
            print("check-north-star: --root needs a directory", file=sys.stderr)
            return 2
        root = pathlib.Path(argv[i + 1])
        DATA = root / "data" / "north-star.toml"
        MEASURE_DIR = root / "data" / "north-star"
    if not DATA.is_file():
        print("check-north-star: %s not found" % DATA, file=sys.stderr)
        return 2
    if "--self-test" in sys.argv[1:]:
        return self_test()
    try:
        doc = tomllib.loads(DATA.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - report any parse failure
        print("check-north-star: cannot parse: %s" % e, file=sys.stderr)
        return 2
    try:
        errors = check(doc, MEASURE_DIR)
    except Exception as e:  # noqa: BLE001 - a wrongly typed value, not a broken rule
        print("check-north-star: cannot check: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 2
    for e in errors:
        print("north-star: " + e)
    if not errors:
        print("north-star: %d objectives, %d periods, %d products: consistent"
              % (len(doc.get("objectives") or []), len(doc.get("periods") or []), len(doc.get("products") or [])))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
