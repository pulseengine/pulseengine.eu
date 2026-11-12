#!/usr/bin/env python3
"""Cause classes for the incident ledger's escapes.

    incident-causes.py classify [--run docs/incidents/run.json]
                                [--causes docs/incidents/causes.json]
    incident-causes.py report   [--run ...] [--causes ...] [--md docs/incidents/report.md]
    incident-causes.py --self-test

Of the escapes scripts/incident-ledger.py finds, only the hand-curated ledger
entries carry a cause. `classify` gives every other escape unit in run.json
exactly one class, from the evidence a person would use:

  wrong-code             the change did the wrong thing
  missing-test           behaviour no test covered; nothing existed that could have caught it
  vacuous-gate           a check existed but could not fail (wrong object, skipped, always green)
  environment-or-target  behaviour only visible on real hardware, CI runners,
                         a toolchain or a deployment
  dependency-or-upstream a dependency bump or an upstream change broke it
  ci-infra               the CI or build infrastructure itself failed or was misconfigured
  unknown                the evidence does not support one of the above

Evidence per unit (GitHub REST, through incident-ledger.py's cached, throttled
client): the merge's title, conventional-commit type, PR body (truncated) and
changed file paths; the signal kinds (and the workflow of a main-red); and for
each later fix or revert PR it names (at most 3) its title and changed paths.
`fix_only_touches_tests` is a hint computed from those paths; it is evidence
the model sees, never a rule applied to its answer. The authoring class is
withheld, so the model cannot grade by who wrote it.

The model is a classifier only, through the mechanism factory-report.py uses
(Claude Code CLI print mode, CLAUDE_CODE_OAUTH_TOKEN, --json-schema, no tools,
the pinned CLASSIFIER_MODEL, the answer's per-model usage must name exactly that
model). Its answer is stored as given. An answer outside the class list, a
missing id or an unreadable answer fails the run (exit 2); nothing partial is
written. Unlike factory-report there is no frozen reference to qualify the
model: the instrument is uncalibrated, and docs/incidents/causes.json carries a
fixed sample of 20 units with an empty `spot_check` field for the owner to fill.
Classified units are kept between runs (the 90-day windows overlap), so a unit
is classified once, by the model pinned when it was first seen.

Titles are sent to the model but are never written to causes.json or the
report (the report already withholds them, and kiln's titles stay private).

Exit: 0 ok · 1 report cannot be made (an escape without a cause, bad file) ·
2 could not run (no credential, API error, model failure, invalid answer).
"""
# rivet: verifies REQ-INCIDENT-LEDGER
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = ROOT / "docs" / "incidents" / "run.json"
CAUSES = ROOT / "docs" / "incidents" / "causes.json"
REPORT = ROOT / "docs" / "incidents" / "report.md"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


il = _load("incident_ledger", "incident-ledger.py")
fr = _load("factory_report", "factory-report.py")

CLASSES = ("wrong-code", "missing-test", "vacuous-gate", "environment-or-target",
           "dependency-or-upstream", "ci-infra", "unknown")
SAMPLE_N = 20
SAMPLE_SEED = "incident-causes-sample-v1"
BATCH = 10                  # units per classifier request
MAX_FIXES = 3
MAX_FILES = 30
BODY_CHARS = 700
TITLE_CHARS = 200
SCHEMA_VERSION = 1

PROMPT = """Each item is a merge to a main branch that later turned out to be an escape (a defect that got past the checks), with the evidence a person would use: the merge's title, type, description and changed files, the signals that flagged it, and the title and changed files of the later fix or revert, when one is known.
Assign exactly one cause class:
  wrong-code: the change did the wrong thing (logic error, wrong behaviour, regression)
  missing-test: the behaviour was not covered by any test, so nothing existed that could have caught it
  vacuous-gate: a check existed but could not fail (it tested the wrong object, was skipped, or was always green)
  environment-or-target: behaviour only visible on real hardware, on CI runners, with a particular toolchain, or in a deployment
  dependency-or-upstream: a dependency bump or an upstream change caused it
  ci-infra: the CI, workflow or build infrastructure itself failed or was misconfigured
  unknown: the evidence does not support one of the classes above
Judge from the evidence only. A mention in a later fix is not proof of causation: when the evidence is thin, answer unknown. fix_only_touches_tests is a hint about the fix, not a verdict. Return one entry per input id, using the ids exactly as given."""

FIELDS = {"cause": {"type": "string", "enum": list(CLASSES)}}


class ClassifierError(Exception):
    """The model's answer cannot be accepted; the run fails and writes nothing."""


# ── evidence (pure given a fetch function) ───────────────────────────────────

TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs|testdata|fixtures?)(/|$)|"
                       r"(^|/)test_[^/]*$|[._-](test|tests|spec)\.[A-Za-z0-9]+$|_test\.[A-Za-z0-9]+$")


def is_test_path(path: str) -> bool:
    return bool(TEST_PATH.search(path))


def unit_id(u: dict) -> str:
    return f"{u['repo']}@{u['sha'][:12]}"


def _clip(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + " [truncated]"


def _files(items) -> list:
    return [f"{f.get('status', '?')} {f['filename']}" for f in (items or [])[:MAX_FILES]]


def _paths(files: list) -> list:
    return [f.split(" ", 1)[1] for f in files]


def fetch_change(fetch, repo: str, pr, sha: str) -> dict:
    """title, body, files of one change, by PR number or else by commit sha."""
    base = f"/repos/{il.ORG}/{repo}"
    if pr:
        p = fetch(f"{base}/pulls/{pr}")
        files = fetch(f"{base}/pulls/{pr}/files?per_page={MAX_FILES}")
        return {"title": _clip(p.get("title"), TITLE_CHARS), "body": _clip(p.get("body"), BODY_CHARS),
                "files": _files(files)}
    c = fetch(f"{base}/commits/{sha}")
    msg = ((c.get("commit") or {}).get("message") or "")
    head, _, rest = msg.partition("\n")
    return {"title": _clip(head, TITLE_CHARS), "body": _clip(rest, BODY_CHARS),
            "files": _files(c.get("files"))}


def fixes_of(u: dict) -> list:
    """[(kind, pr, sha)] of the later changes the signals name, at most MAX_FIXES."""
    out = []
    for s in u["signals"]:
        if s["kind"] == "revert":
            out.append(("revert", s.get("by_pr"), s.get("by_sha")))
        elif s["kind"] == "hotfix-ref":
            out += [("fix-ref", n, None) for n in s.get("by_pr") or []]
    return out[:MAX_FIXES]


def gather(u: dict, fetch) -> dict:
    """The evidence item sent to the classifier. The authoring class is left out."""
    merge = fetch_change(fetch, u["repo"], u.get("pr"), u["sha"])
    merge["type"] = u.get("type")
    sigs = []
    for s in u["signals"]:
        e = {"kind": s["kind"]}
        if s.get("workflow"):
            e["workflow"] = s["workflow"]
        sigs.append(e)
    fixes = []
    for kind, pr, sha in fixes_of(u):
        if not pr and not sha:
            continue
        ch = fetch_change(fetch, u["repo"], pr, sha)
        paths = _paths(ch["files"])
        fixes.append({"kind": kind, "title": ch["title"], "files": ch["files"],
                      "fix_only_touches_tests": bool(paths) and all(is_test_path(p) for p in paths)})
    return {"id": unit_id(u), "repo": u["repo"], "merge": merge, "signals": sigs, "fixes": fixes}


# ── classification ───────────────────────────────────────────────────────────

def classify_items(client, usage, items: list, model=None) -> dict:
    """{id: class}. Every id must come back with a class from CLASSES, or
    ClassifierError: the answer is stored as given, never defaulted or repaired."""
    model = model or fr.CLASSIFIER_MODEL
    out = {}
    for b in range(0, len(items), BATCH):
        chunk = items[b:b + BATCH]
        got = fr._ask(client, usage, model, PROMPT, chunk, FIELDS)
        for it in chunk:
            row = got.get(it["id"])
            if row is None:
                raise ClassifierError(f"no answer for {it['id']}")
            c = row.get("cause")
            if c not in CLASSES:
                raise ClassifierError(f"{it['id']}: {c!r} is not one of {', '.join(CLASSES)}")
            out[it["id"]] = c
    return out


def validate_causes(doc: dict) -> list:
    """Problems with a causes.json document; [] when it is well formed."""
    errs = []
    if doc.get("schema") != SCHEMA_VERSION:
        errs.append(f"schema must be {SCHEMA_VERSION}")
    if list(doc.get("classes") or []) != list(CLASSES):
        errs.append("classes differ from the class list in incident-causes.py")
    units = doc.get("units")
    if not isinstance(units, dict):
        return errs + ["units must be an object"]
    for i, e in units.items():
        if not isinstance(e, dict):
            errs.append(f"{i}: not an object")
            continue
        if e.get("cause") not in CLASSES:
            errs.append(f"{i}: cause {e.get('cause')!r} is not in the class list")
        for k in ("repo", "sha", "month", "classifier"):
            if not isinstance(e.get(k), str) or not e[k]:
                errs.append(f"{i}: {k} missing")
        if "title" in e or "body" in e:
            errs.append(f"{i}: titles and bodies must not be stored")
    sample = doc.get("spot_check_sample")
    if not isinstance(sample, list) or len(sample) > SAMPLE_N:
        errs.append(f"spot_check_sample must be a list of at most {SAMPLE_N}")
    else:
        for s in sample:
            if s.get("id") not in units:
                errs.append(f"sample id {s.get('id')!r} is not a classified unit")
            if not isinstance(s.get("spot_check"), str):
                errs.append(f"sample {s.get('id')!r}: spot_check must be a string")
    return errs


def pick_sample(ids, existing: list, n=SAMPLE_N, seed=SAMPLE_SEED) -> list:
    """A fixed pseudo-random sample: members already chosen (and what the owner
    wrote in them) stay; gaps fill in hash order, so the choice is repeatable."""
    have = set(ids)
    keep = [s for s in existing if s["id"] in have][:n]
    taken = {s["id"] for s in keep}
    rest = sorted((i for i in have if i not in taken),
                  key=lambda i: hashlib.sha256((seed + i).encode()).hexdigest())
    return keep + [{"id": i, "spot_check": ""} for i in rest[:n - len(keep)]]


def escapes_of(run: dict) -> list:
    return [u for u in run["units"] if u.get("escape")]


def empty_doc() -> dict:
    return {"schema": SCHEMA_VERSION, "classes": list(CLASSES), "units": {},
            "spot_check_sample": []}


def classify_run(run: dict, doc: dict, fetch, client, usage) -> dict:
    """The new causes document: every escape in run classified, earlier units kept."""
    pending = [u for u in escapes_of(run) if unit_id(u) not in doc["units"]]
    items = []
    for u in pending:
        items.append(gather(u, fetch))
    answers = classify_items(client, usage, items) if items else {}
    new = dict(doc)
    new["units"] = dict(doc["units"])
    for u in pending:
        new["units"][unit_id(u)] = {
            "repo": u["repo"], "pr": u.get("pr"), "sha": u["sha"][:12], "month": u["month"],
            "date": u["date"][:10], "cause": answers[unit_id(u)],
            "signals": sorted({s["kind"] for s in u["signals"]}),
            "classifier": fr.CLASSIFIER_MODEL}
    run_ids = [unit_id(u) for u in escapes_of(run)]
    new["spot_check_sample"] = pick_sample(
        run_ids, [s for s in doc.get("spot_check_sample", []) if s["id"] in new["units"]])
    new["units"] = dict(sorted(new["units"].items()))
    errs = validate_causes(new)
    if errs:
        raise ClassifierError("causes.json would be invalid: " + "; ".join(errs[:5]))
    return new


# ── report section ───────────────────────────────────────────────────────────

def causes_md(run: dict, doc: dict) -> str:
    """The "Causes" section. Raises ValueError if an escape in run has no cause."""
    errs = validate_causes(doc)
    if errs:
        raise ValueError("causes.json: " + "; ".join(errs[:5]))
    esc = escapes_of(run)
    missing = [unit_id(u) for u in esc if unit_id(u) not in doc["units"]]
    if missing:
        raise ValueError(f"{len(missing)} escape(s) have no cause (run classify): "
                         + ", ".join(missing[:5]))
    by_month = collections.defaultdict(collections.Counter)
    for u in esc:
        by_month[u["month"]][doc["units"][unit_id(u)]["cause"]] += 1
    L = ["## Causes", "",
         "Each escape unit (the 'escape' column above: a later signal says the merge let a "
         "defect through) has exactly one cause class, assigned by a language model from "
         f"the merge's title, type and changed files and the later fix's title and changed "
         f"files (`scripts/incident-causes.py`, classifier `{fr.CLASSIFIER_MODEL}`, "
         "results in `docs/incidents/causes.json`). The model is a classifier only and is "
         "not calibrated against a reference; the sample below is the check. `hotfix-ref` "
         "escapes are a heuristic (see Method), so their causes inherit that doubt. "
         "`unknown` is a legitimate answer, not a gap. Cells are units / escapes in the "
         "month.", "",
         "| month | escapes | " + " | ".join(CLASSES) + " |",
         "|---|---:|" + "---:|" * len(CLASSES)]
    total = collections.Counter()
    for m in sorted(by_month):
        n = sum(by_month[m].values())
        total.update(by_month[m])
        L.append(f"| {m} | {n} | " + " | ".join(f"{by_month[m][c]}/{n}" for c in CLASSES) + " |")
    N = sum(total.values())
    L.append(f"| all | {N} | " + " | ".join(f"{total[c]}/{N}" for c in CLASSES) + " |")
    L += ["", f"### Spot-check sample ({len(doc['spot_check_sample'])} units)", "",
          f"Fixed pseudo-random sample (SHA-256 order of the unit id, seed "
          f"`{SAMPLE_SEED}`), kept between runs. For each, read the merge and its fix and "
          "write `agree`, `disagree: <class>` or a note in the unit's `spot_check` field "
          "in `docs/incidents/causes.json`; the owner fills it, the report only copies it.",
          ""]
    for s in doc["spot_check_sample"]:
        e = doc["units"][s["id"]]
        ref = f"{e['repo']}#{e['pr']}" if e.get("pr") else e["repo"]
        L.append(f"- {ref} ({e['sha']}, {e['date']}), model says {e['cause']}; "
                 f"spot_check: {s['spot_check']}".rstrip())
    return "\n".join(L) + "\n"


# ── commands ─────────────────────────────────────────────────────────────────

def load_doc(path) -> dict:
    p = pathlib.Path(path)
    return json.loads(p.read_text()) if p.exists() else empty_doc()


def cmd_classify(a, client=None, fetch=None) -> int:
    if not fr.credential():
        print("incident-causes: neither CLAUDE_CODE_OAUTH_TOKEN nor ANTHROPIC_API_KEY is set; "
              "nothing classified", file=sys.stderr)
        return 2
    run = json.loads(pathlib.Path(a.run).read_text())
    doc = load_doc(a.causes)
    errs = validate_causes(doc) if doc["units"] else []
    if errs:
        print("incident-causes: existing causes.json is invalid: " + "; ".join(errs[:5]),
              file=sys.stderr)
        return 1
    if fetch is None:
        cache = pathlib.Path(os.environ.get("INCIDENT_LEDGER_CACHE") or
                             pathlib.Path.home() / ".cache" / "pulseengine-incident-ledger")
        fetch = il.GitHub(cache).rest
    usage = fr.Usage()
    try:
        new = classify_run(run, doc, fetch, client or fr.make_client(), usage)
    except (ClassifierError, fr.CouldNotRun) as e:
        print(f"incident-causes: could not classify: {e}", file=sys.stderr)
        return 2
    pathlib.Path(a.causes).write_text(json.dumps(new, indent=1) + "\n")
    n_new = len(new["units"]) - len(doc["units"])
    cost = sum(u.get("notional_cost_usd", 0) for u in usage.report().values())
    print(f"classified {n_new} new unit(s), {len(new['units'])} in total; notional cost "
          f"${cost:.2f}", file=sys.stderr)
    return 0


def cmd_report(a) -> int:
    run = json.loads(pathlib.Path(a.run).read_text())
    doc = load_doc(a.causes)
    try:
        section = causes_md(run, doc)
    except ValueError as e:
        print(f"incident-causes: {e}", file=sys.stderr)
        return 1
    pathlib.Path(a.md).write_text(il.render_md(run, section) + "\n")
    print(f"report written with {len(escapes_of(run))} classified escapes")
    return 0


# ── self-test ────────────────────────────────────────────────────────────────

def _cli_result(model, rows, **kw):
    r = {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
         "structured_output": {"labels": rows},
         "modelUsage": {model: {"inputTokens": 10, "outputTokens": 5, "cacheReadInputTokens": 0,
                                "cacheCreationInputTokens": 0, "costUSD": 0.0001}}}
    r.update(kw)
    return r


def stub_client(answer):
    """A subprocess.run stand-in: answer(item) -> class, for every item sent.
    Records the argv and input of each call."""
    calls = []

    def run(argv, **kw):
        items = json.loads(kw["input"])
        calls.append((argv, items))
        model = argv[argv.index("--model") + 1]
        rows = [{"id": i["id"], "cause": answer(i)} for i in items]
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(_cli_result(model, rows)),
                                           stderr="")
    run.calls = calls
    return run


CANNED = {
    "/repos/pulseengine/rivet/pulls/10": {"title": "feat: add widget parser", "body": "x" * 2000},
    "/repos/pulseengine/rivet/pulls/10/files?per_page=30": [
        {"filename": "src/widget.rs", "status": "added"}],
    "/repos/pulseengine/rivet/pulls/11": {"title": "fix: widget parser drops last byte", "body": ""},
    "/repos/pulseengine/rivet/pulls/11/files?per_page=30": [
        {"filename": "tests/widget_test.rs", "status": "added"}],
    "/repos/pulseengine/rivet/pulls/12": {"title": "fix: also this", "body": ""},
    "/repos/pulseengine/rivet/pulls/12/files?per_page=30": [
        {"filename": "src/widget.rs", "status": "modified"},
        {"filename": "tests/widget_test.rs", "status": "modified"}],
    "/repos/pulseengine/loom/commits/" + "a" * 40: {
        "commit": {"message": "chore: bump x\n\nlong body"},
        "files": [{"filename": "Cargo.lock", "status": "modified"}]},
}


def canned_fetch(path):
    if path not in CANNED:
        raise AssertionError(f"unexpected API path {path}")
    return CANNED[path]


def _unit(repo, pr, sha, signals, month="2026-09", model="claude-opus-5.5", type_="feat"):
    return {"repo": repo, "pr": pr, "sha": sha, "date": f"{month}-05T10:00:00+02:00",
            "month": month, "type": type_, "model": model, "signals": signals, "flags": [],
            "escape": True, "strict": True, "caught": False, "incident": True}


def self_test() -> int:
    fails = []

    def check(cond, what):
        if not cond:
            fails.append(what)

    # 1. evidence from canned API data
    u = _unit("rivet", 10, "1" * 40, [{"kind": "hotfix-ref", "by_pr": [11, 12]},
                                       {"kind": "main-red", "workflow": "ci"}])
    ev = gather(u, canned_fetch)
    check(ev["id"] == "rivet@" + "1" * 12 and ev["merge"]["title"] == "feat: add widget parser"
          and ev["merge"]["type"] == "feat" and ev["merge"]["files"] == ["added src/widget.rs"],
          f"merge evidence wrong: {ev['merge']}")
    check(ev["merge"]["body"].endswith("[truncated]") and len(ev["merge"]["body"]) < BODY_CHARS + 20,
          "a long PR body must be truncated")
    check([s["kind"] for s in ev["signals"]] == ["hotfix-ref", "main-red"]
          and ev["signals"][1]["workflow"] == "ci", f"signals wrong: {ev['signals']}")
    check([f["title"] for f in ev["fixes"]] == ["fix: widget parser drops last byte", "fix: also this"]
          and [f["fix_only_touches_tests"] for f in ev["fixes"]] == [True, False],
          f"fixes wrong: {ev['fixes']}")
    check("claude" not in json.dumps(ev) and "model" not in ev, "authoring class must not reach the model")
    nopr = gather(_unit("loom", None, "a" * 40, [{"kind": "main-red", "workflow": "check"}]), canned_fetch)
    check(nopr["merge"]["title"] == "chore: bump x" and nopr["merge"]["body"] == "long body"
          and nopr["merge"]["files"] == ["modified Cargo.lock"] and nopr["fixes"] == [],
          f"commit-based evidence wrong: {nopr}")
    many = _unit("rivet", 10, "2" * 40, [{"kind": "hotfix-ref", "by_pr": [11, 12, 11, 12, 11]}])
    check(len(fixes_of(many)) == MAX_FIXES, "fixes must be capped")
    check(is_test_path("tests/a.rs") and is_test_path("src/foo_test.go") and is_test_path("a/test_x.py")
          and is_test_path("web/a.spec.ts") and not is_test_path("src/latest.rs")
          and not is_test_path("src/contest/mod.rs"), "is_test_path cases")

    # 2. the command sent to the model: pinned model, schema enum is the class list
    argv = fr.cli_argv(fr.CLASSIFIER_MODEL, PROMPT, FIELDS)
    sch = json.loads(argv[argv.index("--json-schema") + 1])
    enum = sch["properties"]["labels"]["items"]["properties"]["cause"]["enum"]
    check(enum == list(CLASSES) and "haiku" in fr.CLASSIFIER_MODEL
          and argv[argv.index("--model") + 1] == fr.CLASSIFIER_MODEL and "--tools" in argv,
          "CLI argv must pin the Haiku model and the class enum")
    check(len(set(CLASSES)) == 7 and "unknown" in CLASSES, "the class list is the seven classes")

    # 3. classification: the answer is stored exactly as the model gave it
    items = [ev, nopr]
    cl = stub_client(lambda i: "vacuous-gate" if i["repo"] == "rivet" else "ci-infra")
    got = classify_items(cl, fr.Usage(), items)
    check(got == {ev["id"]: "vacuous-gate", nopr["id"]: "ci-infra"}, f"answers not kept: {got}")
    check(cl.calls and cl.calls[0][0][cl.calls[0][0].index("--model") + 1] == fr.CLASSIFIER_MODEL,
          "the pinned model must be the one asked")

    # 4. refusing an answer outside the class list
    for bad in ("flaky", "", "Wrong-Code", None):
        try:
            classify_items(stub_client(lambda i, b=bad: b), fr.Usage(), items)
            check(False, f"answer {bad!r} must be refused")
        except ClassifierError:
            pass
    try:
        classify_items(stub_client(lambda i: "unknown"), fr.Usage(), [])
    except ClassifierError:
        check(False, "no items is not an error")

    def drops(argv, **kw):
        m = argv[argv.index("--model") + 1]
        first = json.loads(kw["input"])[0]
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(_cli_result(
            m, [{"id": first["id"], "cause": "unknown"}])), stderr="")

    try:
        classify_items(drops, fr.Usage(), items)
        check(False, "a missing id must fail the run")
    except ClassifierError:
        pass

    def swapped(argv, **kw):
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(_cli_result(
            "claude-sonnet-5-5", [{"id": i["id"], "cause": "unknown"} for i in json.loads(kw["input"])])),
            stderr="")

    try:
        classify_items(swapped, fr.Usage(), items)
        check(False, "a swapped model must fail the run")
    except fr.CouldNotRun:
        pass

    # 5. negative control: the fix only adds a test, and the model answer rules
    only_test = _unit("rivet", 10, "3" * 40, [{"kind": "hotfix-ref", "by_pr": [11]}])
    ev_t = gather(only_test, canned_fetch)
    check(ev_t["fixes"][0]["fix_only_touches_tests"] is True, "control: fix must be test-only")
    run = {"units": [only_test]}
    for said in ("wrong-code", "missing-test", "unknown"):
        doc = classify_run(run, empty_doc(), canned_fetch, stub_client(lambda i, s=said: s), fr.Usage())
        check(doc["units"][unit_id(only_test)]["cause"] == said,
              f"control: stored cause must equal the model's answer {said!r}, got "
              f"{doc['units'][unit_id(only_test)]['cause']!r}")
    try:
        classify_run(run, empty_doc(), canned_fetch, stub_client(lambda i: "flaky"), fr.Usage())
        check(False, "control: an invalid class must make the run fail")
    except ClassifierError:
        pass
    with tempfile.TemporaryDirectory() as td:
        rp, cp = pathlib.Path(td) / "run.json", pathlib.Path(td) / "causes.json"
        rp.write_text(json.dumps(run))
        ns = argparse.Namespace(run=str(rp), causes=str(cp))
        saved = {k: os.environ.pop(k, None) for k in fr.CREDENTIALS}
        try:
            check(cmd_classify(ns, stub_client(lambda i: "unknown"), canned_fetch) == 2,
                  "classify without a credential must exit 2")
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "x"
            check(cmd_classify(ns, stub_client(lambda i: "flaky"), canned_fetch) == 2
                  and not cp.exists(), "an invalid class must exit 2 and write nothing")
            check(cmd_classify(ns, stub_client(lambda i: "missing-test"), canned_fetch) == 0
                  and json.loads(cp.read_text())["units"][unit_id(only_test)]["cause"] == "missing-test",
                  "a valid run must write the answer as given")
        finally:
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    # 6. schema validation of causes.json
    good = classify_run(run, empty_doc(), canned_fetch, stub_client(lambda i: "unknown"), fr.Usage())
    check(validate_causes(good) == [], f"a good document must validate: {validate_causes(good)}")
    for what, mut in (
            ("a class outside the list", lambda d: d["units"][unit_id(only_test)].update(cause="flaky")),
            ("a stored title", lambda d: d["units"][unit_id(only_test)].update(title="secret")),
            ("a wrong schema version", lambda d: d.update(schema=9)),
            ("a changed class list", lambda d: d.update(classes=["a"])),
            ("a sample id that is no unit", lambda d: d["spot_check_sample"].append(
                {"id": "ghost@1", "spot_check": ""}))):
        d = json.loads(json.dumps(good))
        mut(d)
        check(validate_causes(d) != [], f"{what} must fail validation")

    # 7. incremental: a classified unit is kept and not asked again
    cl2 = stub_client(lambda i: "wrong-code")
    again = classify_run(run, good, canned_fetch, cl2, fr.Usage())
    check(again["units"] == good["units"] and not cl2.calls, "a classified unit must not be re-asked")

    # 8. the sample: fixed, 20, stable, keeps what the owner wrote
    ids = [f"r@{i:012d}" for i in range(100)]
    s1 = pick_sample(ids, [])
    check(len(s1) == SAMPLE_N and s1 == pick_sample(ids, []) and all(s["spot_check"] == "" for s in s1),
          "sample must be 20 units, repeatable, with an empty spot_check")
    s1[0]["spot_check"] = "agree"
    s2 = pick_sample(ids + ["r@new"], s1)
    check(s2[0] == {"id": s1[0]["id"], "spot_check": "agree"} and [s["id"] for s in s2] == [s["id"] for s in s1],
          "an existing sample (and the owner's note) must survive new units")
    s3 = pick_sample(ids[:3], s1)
    check(len(s3) <= 3, "a sample cannot list units outside the run")

    # 9. the report section
    u2 = _unit("loom", None, "a" * 40, [{"kind": "main-red", "workflow": "check"}], month="2026-10")
    r2 = {"units": [only_test, u2, dict(u2, sha="b" * 40, escape=False)]}
    d2 = classify_run(r2, empty_doc(), canned_fetch,
                      stub_client(lambda i: "ci-infra" if i["repo"] == "loom" else "missing-test"), fr.Usage())
    d2["spot_check_sample"][0]["spot_check"] = "agree"
    md = causes_md(r2, d2)
    check("| 2026-09 | 1 | 0/1 | 1/1 |" in md and "| 2026-10 | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 |" in md
          and "| all | 2 |" in md, f"table counts wrong:\n{md}")
    check(md.count("spot_check:") == 2 and "spot_check: agree" in md and "spot_check:\n" in md + "\n",
          "sample must list every unit with its spot_check field")
    check("secret" not in md and "feat: add widget" not in md, "no titles in the report")
    try:
        causes_md({"units": [only_test, u2]}, classify_run({"units": [only_test]}, empty_doc(), canned_fetch,
                                                           stub_client(lambda i: "unknown"), fr.Usage()))
        check(False, "an escape without a cause must make the report fail")
    except ValueError:
        pass
    full = {"generated": "g", "window": {"since": "a", "until": "b"}, "repos": ["x"],
            "headline": {k: il.rate(0, 0) for k in ("escape", "strict", "incident", "caught", "catch_share")},
            "signal_counts": {}, "flag_counts": {}, "by_model": {}, "by_type": {}, "by_month": {},
            "by_repo": {}, "incidents": [], "ledger": [], "seed_recall": "n/a", "net_classes": [],
            "method": "m", "units": r2["units"]}
    check("## Causes" in il.render_md(full, md) and "## Causes" not in il.render_md(full),
          "render_md must include the section only when given")

    for f in fails:
        print(f"self-test FAIL: {f}", file=sys.stderr)
    print(f"incident-causes self-test: {'FAIL' if fails else 'ok'} ({len(fails)} failure(s))")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("classify", "report"):
        p = sub.add_parser(name)
        p.add_argument("--run", default=str(RUN))
        p.add_argument("--causes", default=str(CAUSES))
        if name == "report":
            p.add_argument("--md", default=str(REPORT))
    a = ap.parse_args()
    return cmd_classify(a) if a.cmd == "classify" else cmd_report(a)


if __name__ == "__main__":
    sys.exit(main())
