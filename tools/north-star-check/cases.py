#!/usr/bin/env python3
# rivet: verifies REQ-NORTH-STAR-COMPONENT
"""Run the North Star check's cases through every implementation; all must agree.

The implementations are scripts/check-north-star.py and the north-star-check
WebAssembly component under one or more runtimes. Each case is a directory
laid out like the repository (data/north-star.toml, data/north-star/<id>.json)
and every runner checks the same directories, so the comparison is about the
checkers, not about how each one was fed.

The cases:
  - "committed": the repository's own data, which must pass (exit 0);
  - the 15 planted violations of check-north-star.py --self-test, ported as a
    table; each must make EVERY implementation exit 1;
  - --fuzz N seeded random mutations (wrong types, odd strings, datetimes,
    malformed or edge-case measurement JSON); for these only agreement is
    required: same stdout, same exit code.

Agreement is on stdout and the exit code. stderr is only required to start
with "check-north-star:" when the exit code is 2: exception and parser texts
differ between Python and Rust.

  cases.py --runner python \\
           --runner wasmtime='wasmtime run --dir {dir}::/case {wasm} --root /case' \\
           --wasm north-star-check.wasm [--fuzz 300] [--expect-cannot-run NAME]

A runner is NAME=COMMAND; {dir} is the case directory, {wasm} the component.
"python" alone means the Python script. --expect-cannot-run NAME marks a
runtime known not to run the component yet (a recorded gap): its failure to
start is reported and tolerated, but if it starts running the component the
harness fails so the expectation is removed and the runtime is compared.

Exit: 0 all agree · 1 a disagreement, or a planted case not caught · 2 could
not run.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import pathlib
import random
import shlex
import subprocess
import sys
import tempfile

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - the macOS floor is 3.9
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        print("cases.py: needs Python 3.11+ or the tomli package", file=sys.stderr)
        sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "check-north-star.py"


# --- a TOML writer: inline values only, which keeps document order --------

def _tstr(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20 or o == 0x7F:
            out.append("\\u%04X" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _tval(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isnan(v):
            return "nan"
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        r = repr(v)
        return r if any(c in r for c in ".e") else r + ".0"
    if isinstance(v, str):
        return _tstr(v)
    if isinstance(v, dt.datetime):
        return v.isoformat()
    if isinstance(v, (dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, list):
        return "[" + ", ".join(_tval(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join("%s = %s" % (_tstr(k), _tval(x)) for k, x in v.items()) + "}"
    raise TypeError("cannot write %r as TOML" % (v,))


def to_toml(doc: dict) -> str:
    text = "".join("%s = %s\n" % (_tstr(k), _tval(v)) for k, v in doc.items())
    back = tomllib.loads(text)
    if repr(back) != repr(doc):  # repr, because nan != nan
        raise AssertionError("TOML writer does not round-trip:\n%r\n%r" % (doc, back))
    return text


# --- the cases ---------------------------------------------------------------

def committed_measurements() -> dict:
    d = ROOT / "data" / "north-star"
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.json"))}


def planted(base: dict) -> list:
    """check-north-star.py --self-test's planted violations, as data."""
    meas = committed_measurements()

    def m(fn):
        d = copy.deepcopy(base)
        fn(d)
        return d

    cases = [
        ("missing guard", m(lambda d: d["objectives"][0].pop("guard")), meas),
        ("bad id", m(lambda d: d["objectives"][0].update(id="X1")), meas),
        ("duplicate id", m(lambda d: d["objectives"][1].update(id=d["objectives"][0]["id"])), meas),
        ("made-up zero", m(lambda d: d["objectives"][0].update(state="0%")), meas),
        ("unknown commitment objective",
         m(lambda d: d["periods"][0]["commitments"][0].update(objective="O99")), meas),
        ("bad kind", m(lambda d: d["periods"][0]["commitments"][0].update(kind="maybe")), meas),
        ("bad layer", m(lambda d: d["periods"][0]["layers"].append("2026-11")), meas),
        ("unknown pull", m(lambda d: d["products"][0]["pulls"].append("O99")), meas),
        ("dated north star", m(lambda d: d.update(north_star=d["north_star"] + " By 2027.")), meas),
        ("ipv4", m(lambda d: d["objectives"][0].update(summary="runs on 10.0.0.5")), meas),
        ("local host", m(lambda d: d["objectives"][0].update(summary="measured on box.lan")), meas),
    ]
    # Rule 7: the self-test's planted measurement directories. Every other
    # objective is unmeasured and the directory holds only the planted file.
    first = base["objectives"][0]["id"]

    def r7(state):
        def fn(d):
            d["objectives"][0]["state"] = state
            for o in d["objectives"][1:]:
                o["state"] = "unmeasured"
        return m(fn)

    def f(payload):
        return {"%s.json" % first: json.dumps(payload)}

    cases += [
        ("measured without a file", r7("measured"), {}),
        ("file without measured", r7("unmeasured"), f({"objective": first, "value": 1, "of": 2})),
        ("value above denominator", r7("measured"), f({"objective": first, "value": 3, "of": 2})),
        ("file for another objective", r7("measured"), f({"objective": "O99", "value": 1, "of": 2})),
    ]
    return cases


ODD_VALUES = [
    "", " ", " ", "\x1c", "O1", "O1\n", "O0", "O01", "o1", "X1", "measured", "unmeasured",
    "committed", "stretch", "2026.11", "2026.11\n", "2026.1", "2026-11", "Q3", "Q34", "by 2027",
    "x2027", "1.2.3.4", "1.2.3.4567", "999.1.1.1", "box.lan", "BOX.LOCAL", "a-b.internal",
    "x.lane", "İnternal.k", "x.ıntranet", "_a.home", "it's", 'say "hi"', "tab\tnl\n",
    " ", "\U0001f600", "été", "\x7f", "line\r", 0, 1, -7, 2 ** 40, 0.0, -0.0, 1.0,
    2026.11, 1e16, 1e-05, float("inf"), float("nan"), True, False, [], ["O1"], ["O1", 2],
    {}, {"a": 1}, {"objective": "O1"},
    dt.date(2026, 11, 17), dt.time(10, 0), dt.time(10, 0, 5, 123000),
    dt.datetime(2026, 11, 17, 10, 0), dt.datetime(2026, 11, 17, 10, 0, 7, tzinfo=dt.timezone.utc),
    dt.datetime(2026, 11, 17, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5, minutes=-30))),
]

ODD_JSON = [
    None, '{"objective": "%s", "value": 1, "of": 2}', '{"objective": "%s", "value": 0, "of": 1}',
    '{"objective": "%s", "value": true, "of": 2}', '{"objective": "%s", "value": 1.0, "of": 2}',
    '{"objective": "%s", "value": 1, "of": 0}', '{"objective": "%s", "value": -1, "of": 2}',
    '{"objective": "%s", "value": 1, "of": 99999999999999999999999}',
    '{"objective": "%s", "value": 1, "of": 2, "x": NaN}', '{"objective": "%s", "value": 1, "value": 9, "of": 2}',
    '{"objective": "%s\\ud800", "value": 1, "of": 2}', '{"objective": "%s", "value": 1, "of": 2} x',
    "null", "[]", "[1]", '"O1"', "3", "", "{", "﻿{}", '{"objective": "%s", "value": 1e0, "of": 2}',
    '{"objective": "%s", "value": -0, "of": 2}', b"\xff\xfe",
]

PATHS = [
    ("north_star",), ("updated",), ("objectives",), ("periods",), ("products",),
    ("objectives", 0, "id"), ("objectives", 1, "id"), ("objectives", 0, "state"), ("objectives", 1, "state"),
    ("objectives", 2, "title"), ("objectives", 0, "summary"), ("objectives", 3, "guard"), ("objectives", 0),
    ("periods", 0, "layers"), ("periods", 1, "layers", 0), ("periods", 0, "commitments"),
    ("periods", 0, "commitments", 0, "objective"), ("periods", 1, "commitments", 0, "kind"),
    ("periods", 0, "commitments", 0, "target"), ("periods", 1),
    ("products", 0, "pulls"), ("products", 1, "pulls", 0), ("products", 2, "name"), ("products", 0),
]


def _set(doc, path, value, delete=False):
    node = doc
    for k in path[:-1]:
        node = node[k]
    if isinstance(node, dict) != isinstance(path[-1], str) or not isinstance(node, (dict, list)):
        raise TypeError("an earlier mutation changed the parent's type")
    if delete:
        if isinstance(node, dict):
            node.pop(path[-1], None)
        else:
            del node[path[-1]]
    else:
        node[path[-1]] = value


def fuzz(base: dict, n: int, seed: int) -> list:
    rng = random.Random(seed)
    ids = [o["id"] for o in base["objectives"]]
    out = []
    for k in range(n):
        d = copy.deepcopy(base)
        for _ in range(rng.randint(1, 3)):
            path = rng.choice(PATHS)
            try:
                _set(d, path, copy.deepcopy(rng.choice(ODD_VALUES)), delete=rng.random() < 0.15)
            except (KeyError, IndexError, TypeError):
                pass  # an earlier mutation removed the parent; keep what we have
        meas = {}
        for oid in rng.sample(ids + ["X1", "O01"], rng.randint(0, 2)):
            j = rng.choice(ODD_JSON)
            if j is None:
                continue
            meas["%s.json" % oid] = j % oid if isinstance(j, str) and "%s" in j else j
        out.append(("fuzz %03d" % k, d, meas))
    return out


def write_case(base_dir: pathlib.Path, name: str, doc: dict, meas: dict) -> pathlib.Path:
    d = base_dir / name.replace(" ", "-")
    (d / "data" / "north-star").mkdir(parents=True)
    (d / "data" / "north-star.toml").write_text(to_toml(doc), encoding="utf-8")
    for fname, body in meas.items():
        p = d / "data" / "north-star" / fname
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")
    return d


# --- running -----------------------------------------------------------------

def run(cmd: list, timeout: int = 120):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "", str(e)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def runner_cmd(spec: str, wasm: str, case_dir: pathlib.Path) -> list:
    if spec == "python":
        return [sys.executable, "-I", str(SCRIPT), "--root", str(case_dir)]
    return [a.replace("{dir}", str(case_dir)).replace("{wasm}", wasm) for a in shlex.split(spec)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runner", action="append", required=True, help="NAME=COMMAND, or python")
    ap.add_argument("--wasm", default="", help="the component, substituted for {wasm}")
    ap.add_argument("--fuzz", type=int, default=0, help="seeded random cases to add")
    ap.add_argument("--seed", type=int, default=20261118)
    ap.add_argument("--expect-cannot-run", action="append", default=[], metavar="NAME")
    a = ap.parse_args()

    runners = []
    for r in a.runner:
        name, _, cmd = r.partition("=")
        runners.append((name, cmd or name))
    if len(runners) < 2:
        print("cases.py: give at least two runners to compare", file=sys.stderr)
        return 2

    base = tomllib.loads((ROOT / "data" / "north-star.toml").read_text(encoding="utf-8"))
    cases = [("committed", base, committed_measurements())]
    cases += planted(base)
    n_planted = len(cases) - 1
    cases += fuzz(base, a.fuzz, a.seed)

    failures = 0
    exits = []
    gap_seen = {n: [] for n in a.expect_cannot_run}
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = pathlib.Path(tmp)
        for idx, (name, doc, meas) in enumerate(cases):
            case_dir = write_case(tmpd, name, doc, meas)
            results = {}
            for rname, spec in runners:
                rc, out, err = run(runner_cmd(spec, a.wasm, case_dir))
                if rname in gap_seen:
                    # A known gap: tolerated only while the runtime cannot run it.
                    if rc not in (0, 1) or not out.startswith("north-star:"):
                        if not gap_seen[rname]:
                            gap_seen[rname].append((rc, (err or out).strip().splitlines()[-3:]))
                        continue
                    print("FAIL %s: %s now runs the component (exit %s); remove --expect-cannot-run %s"
                          % (name, rname, rc, rname))
                    failures += 1
                    continue
                results[rname] = (rc, out, err)
            if not results:
                continue
            ref_name = next(iter(results))
            ref = results[ref_name]
            exits.append(ref[0])
            for rname, res in results.items():
                if (res[0], res[1]) != (ref[0], ref[1]):
                    print("FAIL %s: %s and %s disagree" % (name, ref_name, rname))
                    for nm, r in ((ref_name, ref), (rname, res)):
                        print("  %s exit %s\n    %s" % (nm, r[0], "\n    ".join(r[1].splitlines() or ["(no stdout)"])))
                        if r[2].strip():
                            print("    stderr: %s" % r[2].strip().splitlines()[-1])
                    failures += 1
                if res[0] == 2 and not res[2].startswith("check-north-star:"):
                    print("FAIL %s: %s exit 2 without a check-north-star message: %s"
                          % (name, rname, res[2].strip()[:200]))
                    failures += 1
                if res[0] not in (0, 1, 2):
                    print("FAIL %s: %s exit %s (crash?)" % (name, rname, res[0]))
                    failures += 1
            if name == "committed" and ref[0] != 0:
                print("FAIL committed: the repository's own data must pass, got exit %s" % ref[0])
                failures += 1
            if 1 <= idx <= n_planted:
                for rname, res in results.items():
                    if res[0] != 1:
                        print("FAIL planted %r: %s exit %s, expected 1" % (name, rname, res[0]))
                        failures += 1

    for rname, seen in gap_seen.items():
        if seen:
            rc, tail = seen[0]
            print("KNOWN GAP %s: cannot run the component (exit %s): %s" % (rname, rc, " | ".join(tail)))
    names = ", ".join(n for n, _ in runners if n not in gap_seen)
    total = len(cases)
    # A comparison where every case exits 2 compares nothing about the rules.
    print("exit codes of %s: %s" % (runners[0][0], ", ".join(
        "%d x %s" % (exits.count(c), c) for c in sorted(set(exits), key=str))))
    print("cases: %d (1 committed, %d planted, %d fuzz); compared: %s; %s"
          % (total, n_planted, a.fuzz, names, "all agree" if not failures else "%d failure(s)" % failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
