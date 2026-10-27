#!/usr/bin/env python3
# rivet: verifies REQ-FACTORY-REPORT-INSTRUMENT-GATE
"""Monthly measurement for the fix-hotspot experiment (docs/experiments/2026-10-hotspot-trigger.md).

    factory-report.py --self-test              offline decision table; no key, no network
    factory-report.py configured               prints whether ANTHROPIC_API_KEY is set (exit 0 either way)
    factory-report.py run --clones DIR --work DIR --out data/factory-report [--month YYYY-MM]
    factory-report.py publish --file data/factory-report/YYYY-MM.json --repo owner/name

ORDER IS THE POINT. `run` checks the instrument before it measures anything:

  1. The two frozen references are rebuilt and their sha256 compared with the
     pinned values below. Agent: 160 rivet/spar commits from
     `commit-classify.py oracle --until 2026-10-22T10:13:00+02:00`, the
     author's stripped conventional prefix as truth. Human: Levin and
     Yehudai's 400-commit sample (Zenodo 835534), downloaded and
     checksum-checked on every run. A mismatch means the reference moved
     (history rewritten, Python's shuffle changed), so the run stops.
  2. The classifier labels both references and `commit-classify.fix_scores`
     scores them. Fix precision below 0.75 or recall below 0.70 on EITHER
     reference fails the run with exit 1 and writes nothing.
  3. Only then are rivet and spar measured for the month and the report file
     written. The SAME function, prompt, model and effort label the month's
     sample as labelled the references, so the check qualifies the instrument
     the report actually uses.

A missing ANTHROPIC_API_KEY (unset or empty) is exit 0 with a notice and no
file. This deliberately differs from check-issue-classes.py, which exits 2 on a
missing token: that script is a gate, and a gate that cannot reach its evidence
must go red. This one produces a report, and a skipped run publishes nothing,
so nothing false can be read from it. A red schedule for the known reason "the
owner has not added the secret yet" would only train people to ignore red.

Instruments:
- Message labels: Claude Haiku via the API, model id below, read from the
  models overview page on 2026-10-27. The 22 October calibration used Claude
  Code's "haiku" alias, which may not be the same snapshot; the instrument
  check, not the name, is what qualifies the model each month.
- Diff judgement (criterion 3): Claude Sonnet reading message plus diff
  truncated at 3,500 characters, as judge-batches.py did for the baseline.
  It has no labelled refactor reference, so it is reported as uncalibrated.
  No server-side refusal fallback is enabled on either model: a fallback
  would swap the instrument silently, so a refusal is a missing label and the
  run fails closed.

Month boundaries are UTC calendar months. The 22 October baseline used a
+02:00 cut-off; the difference is at most two hours at each end.

Exit: 0 report written, or not configured · 1 instrument check failed or
labels incomplete · 2 could not run (reference moved, network, API error).
"""
from __future__ import annotations

import argparse
import base64
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("commit_classify", HERE / "commit-classify.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

# ── Instrument ───────────────────────────────────────────────────────────────
MODEL_SOURCE = "https://platform.claude.com/docs/en/about-claude/models/overview (read 2026-10-27)"
CLASSIFIER_MODEL = "claude-haiku-5-5"
JUDGE_MODEL = "claude-sonnet-5-5"
EFFORT = "low"
MAX_TOKENS = 16000          # thinking counts against it; a classification batch needs ~2k
BATCH = 20                  # commits per classifier request
JUDGE_BATCH = 10            # diffs per judge request
# USD per million tokens, input/output, from the same page (Haiku: prompts <= 100K).
PRICE = {CLASSIFIER_MODEL: (0.10, 0.50), JUDGE_MODEL: (2.00, 10.00)}

PRECISION_MIN = 0.75
RECALL_MIN = 0.70

PROMPT = """Label each commit message with exactly one primary class:
  feature: adds new capability or behaviour
  fix: corrects a defect, wrong behaviour, a broken check, or a regression
  refactor: restructures code without changing behaviour
  maintenance: tests only, docs, CI, build, dependencies, releases, formatting
and contains_fix: true if the commit also corrects a defect, even as a side
effect; always true for primary = fix.
Return one entry per input id, using the ids exactly as given."""

JUDGE_PROMPT = """Each item is a commit: its message and its source diff (possibly truncated).
Judge from the diff what the change does, with exactly one primary class:
  feature: adds new capability or behaviour
  fix: corrects a defect, wrong behaviour, a broken check, or a regression
  refactor: restructures code without changing behaviour
  maintenance: tests only, docs, CI, build, dependencies, releases, formatting
and refactor: true if any substantial part of the diff restructures code
without changing behaviour. Return one entry per input id, ids exactly as given."""

# ── Frozen references ────────────────────────────────────────────────────────
ORACLE_UNTIL = "2026-10-22T10:13:00+02:00"
LEVIN_URL = ("https://zenodo.org/api/records/835534/files/"
             "1151-commits-labeled-with-maintenance-activities.csv/content")
LEVIN_SHA256 = "99760ab035193761a747fd3f2a4b579dd6503e5dfcab94b54f3fad974765816e"
PINNED = {
    "oracle-truth.json": "906b7cf61cb2bab3f46b0451a6aca46296a91e1160e9a8cb4b81e036e2149468",
    "oracle-full-input.json": "4bb5db92b9169e8a50920ef7889e7928e8f9d00a70a040c6759bdb087a124c9e",
    "levin-truth.json": "4e04221b4d4479a7701f8f92d9533f85696ce148d8f60a57ece8a9257ebdc3cd",
    "levin-full-input.json": "4f5e21a48ae33c71f4d9670811ab677ddd09532bdb7368701be8d3ac30dbb3c9",
}
REFERENCES = {"agent": "oracle", "human": "levin"}

# ── Measurement ──────────────────────────────────────────────────────────────
REPOS = {"rivet": "pulseengine/rivet", "spar": "pulseengine/spar"}
HOTSPOT = ("rivet", "rivet-cli/src/main.rs")
SAMPLE_N = 45               # per repo per month; rivet's baseline sample was 45
EXTS = (".rs",)
# The trigger has not shipped. Set this to the month it ships ("YYYY-MM"); the
# window is the three calendar months after it, and the verdict is computed
# over the window's summed counts, never from one month.
TRIGGER_SHIPPED = None

PREFIX = re.compile(r"^(\w+)(\([^)]*\))?!?:")


class CouldNotRun(Exception):
    pass


def notice(msg):
    print(f"::notice title=factory-report::{msg}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(f"### factory report\n\n{msg}\n")


def api_key():
    """Unset and empty are the same: an Actions secret that does not exist
    arrives as the empty string, not as a missing variable."""
    return (os.environ.get("ANTHROPIC_API_KEY") or "").strip()


NOT_CONFIGURED = ("not configured: ANTHROPIC_API_KEY is not set, so no report was produced. "
                  "Add it under Settings > Secrets and variables > Actions to enable the monthly run.")


# ── Gate (pure) ──────────────────────────────────────────────────────────────
def gate(scores):
    """scores: {reference name: fix_scores dict}. Returns failure strings; [] passes.
    Both references must be present and each must clear both thresholds."""
    bad = []
    for name in REFERENCES:
        s = scores.get(name)
        if s is None:
            bad.append(f"{name}: not scored")
            continue
        if s["precision"] < PRECISION_MIN:
            bad.append(f"{name}: fix precision {s['precision']:.2f} < {PRECISION_MIN}")
        if s["recall"] < RECALL_MIN:
            bad.append(f"{name}: fix recall {s['recall']:.2f} < {RECALL_MIN}")
    return bad


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# ── Model calls (the one code path for references and month samples) ─────────
class Usage:
    def __init__(self):
        self.tokens = collections.defaultdict(lambda: [0, 0])

    def add(self, model, u):
        self.tokens[model][0] += getattr(u, "input_tokens", 0) or 0
        self.tokens[model][1] += getattr(u, "output_tokens", 0) or 0

    def report(self):
        out = {}
        for m, (i, o) in self.tokens.items():
            pi, po = PRICE.get(m, (0, 0))
            out[m] = {"input_tokens": i, "output_tokens": o,
                      "cost_usd": round(i / 1e6 * pi + o / 1e6 * po, 4)}
        return out


def _schema(fields):
    return {"type": "json_schema", "schema": {
        "type": "object", "additionalProperties": False, "required": ["labels"],
        "properties": {"labels": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", *fields],
            "properties": {"id": {"type": "string"}, **fields}}}}}}


LABEL_FIELDS = {"primary": {"type": "string", "enum": cc.CATS}, "contains_fix": {"type": "boolean"}}
JUDGE_FIELDS = {"primary": {"type": "string", "enum": cc.CATS}, "refactor": {"type": "boolean"}}


def _ask(client, usage, model, system, items, fields):
    """One request. Returns {id: label}. A refusal, a truncated answer, or
    unparseable JSON returns {} for the batch, so the caller's schema check
    (commit-classify.load_labels) fails closed on the missing ids."""
    resp = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, system=system,
        output_config={"effort": EFFORT, "format": _schema(fields)},
        messages=[{"role": "user", "content": json.dumps(items, ensure_ascii=False)}])
    usage.add(model, resp.usage)
    if resp.stop_reason != "end_turn":
        print(f"  {model}: stop_reason={resp.stop_reason} for {len(items)} items; leaving them unlabelled",
              file=sys.stderr)
        return {}
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        rows = json.loads(text)["labels"]
    except (ValueError, KeyError, TypeError):
        return {}
    want = {it["id"] for it in items}
    return {r["id"]: {k: r[k] for k in fields} for r in rows
            if isinstance(r, dict) and r.get("id") in want and all(k in r for k in fields)}


def classify(client, usage, items):
    """items: [{"id", "text"}] -> {id: {"primary", "contains_fix"}}"""
    out = {}
    for b in range(0, len(items), BATCH):
        out.update(_ask(client, usage, CLASSIFIER_MODEL, PROMPT, items[b:b + BATCH], LABEL_FIELDS))
    return out


def judge(client, usage, items):
    """items: [{"id", "message", "diff"}] -> {id: {"primary", "refactor"}}"""
    out = {}
    for b in range(0, len(items), JUDGE_BATCH):
        out.update(_ask(client, usage, JUDGE_MODEL, JUDGE_PROMPT, items[b:b + JUDGE_BATCH], JUDGE_FIELDS))
    return out


def make_client():
    import anthropic  # lazy: the PR self-test runs without the SDK installed
    return anthropic.Anthropic(max_retries=4)


# ── Step 1-2: references and the instrument check ────────────────────────────
def build_references(clones, work):
    """Regenerate both references into work/cls and check them against PINNED."""
    work.mkdir(parents=True, exist_ok=True)
    script = str(HERE / "commit-classify.py")
    order = [str(clones / name) for name in REPOS]      # rivet then spar, as on 22 October
    subprocess.run([sys.executable, "-I", script, "oracle", *order, "--ext", *EXTS, "--n", "160",
                    "--until", ORACLE_UNTIL], cwd=work, check=True)
    dl = work / "levin-download"
    dl.mkdir(exist_ok=True)
    csv = dl / "levin.csv"
    try:
        urllib.request.urlretrieve(LEVIN_URL, csv)
    except urllib.error.URLError as e:
        raise CouldNotRun(f"Levin download failed: {e}")
    if sha256(csv) != LEVIN_SHA256:
        raise CouldNotRun(f"Levin CSV sha256 {sha256(csv)} != pinned {LEVIN_SHA256}")
    subprocess.run([sys.executable, "-I", script, "levin", str(csv), "--n", "400"], cwd=work, check=True)
    moved = [f"{f}: {sha256(work / 'cls' / f)[:12]} != pinned {h[:12]}"
             for f, h in PINNED.items() if sha256(work / "cls" / f) != h]
    if moved:
        raise CouldNotRun("frozen reference moved: " + "; ".join(moved))
    refs = {}
    for name, stem in REFERENCES.items():
        truth = json.loads((work / "cls" / f"{stem}-truth.json").read_text())
        items = json.loads((work / "cls" / f"{stem}-full-input.json").read_text())
        refs[name] = (stem, truth, items)
    return refs


def instrument_check(refs, label_fn, work):
    """Label each reference, validate the labels, score them. Returns
    (scores, failures). Malformed or missing labels raise SystemExit from
    commit-classify.load_labels, which is a failure, never a pass."""
    scores = {}
    for name, (stem, truth, items) in refs.items():
        labels = label_fn(items)
        path = work / "cls" / f"{stem}-labels.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(labels, indent=0))
        lab = cc.load_labels(path, [t["id"] for t in truth])
        scores[name] = cc.fix_scores(truth, lab)
        if (work / "cls" / f"{stem}-truth.json").exists():
            # The printed table from the CLI itself, for the run log.
            subprocess.run([sys.executable, "-I", str(HERE / "commit-classify.py"), "score", stem,
                            str(path)], cwd=work, check=False)
    return scores, gate(scores)


# ── Step 3: measure the month ────────────────────────────────────────────────
def month_bounds(month):
    y, m = map(int, month.split("-"))
    start = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=dt.timezone.utc)
    return start, end


def previous_month(today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    first = today.replace(day=1)
    last = first - dt.timedelta(days=1)
    return f"{last.year}-{last.month:02d}"


def gh_get(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise CouldNotRun(f"GET {url}: HTTP {e.code}")


def kind_of(subject):
    m = PREFIX.match(subject)
    return m.group(1).lower() if m else None


def pr_commit_counts(slug, month, token):
    """PRs merged into main during the month; every commit on them, by prefix."""
    start, end = month_bounds(month)
    prs, page = [], 1
    while True:
        batch = gh_get(f"https://api.github.com/repos/{slug}/pulls?state=closed&base=main"
                       f"&sort=updated&direction=desc&per_page=100&page={page}", token)
        for p in batch:
            if p.get("merged_at") and start <= dt.datetime.fromisoformat(
                    p["merged_at"].replace("Z", "+00:00")) < end:
                prs.append(p["number"])
        oldest = batch[-1]["updated_at"] if batch else None
        if len(batch) < 100 or (oldest and dt.datetime.fromisoformat(oldest.replace("Z", "+00:00")) < start):
            break
        page += 1
    kinds = collections.Counter()
    for n in prs:
        commits, cpage = [], 1
        while True:
            c = gh_get(f"https://api.github.com/repos/{slug}/pulls/{n}/commits?per_page=100&page={cpage}", token)
            commits += c
            if len(c) < 100:
                break
            cpage += 1
        for c in commits:
            kinds[kind_of(c["commit"]["message"].splitlines()[0]) or "unprefixed"] += 1
    total = sum(kinds.values())
    return {"prs": len(prs), "commits": total, "by_prefix": dict(kinds),
            "refactor": kinds["refactor"],
            "refactor_share": round(kinds["refactor"] / total, 4) if total else None}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True, errors="replace").stdout


def hotspot_fixes(clone, path, month):
    start, end = month_bounds(month)
    subjects = git(clone, "log", "--no-merges", f"--since={start.isoformat()}",
                   f"--until={end.isoformat()}", "--format=%s", "--", path).splitlines()
    rev = git(clone, "rev-list", "-1", f"--before={end.isoformat()}", "HEAD").strip()
    exists = bool(rev) and bool(git(clone, "ls-tree", rev, "--", path).strip())
    return {"path": path, "commits": len(subjects),
            "fix": sum(kind_of(s) == "fix" for s in subjects), "exists_at_month_end": exists}


def month_sample(name, clone, month, n=SAMPLE_N):
    """Non-merge commits in the month touching source, sampled with a seed
    derived from repo and month, so a rerun picks the same commits."""
    start, end = month_bounds(month)
    out = git(clone, "log", "--no-merges", "--name-only", f"--since={start.isoformat()}",
              f"--until={end.isoformat()}", "--format=@@%H")
    commits, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            cur = [line[2:], []]
            commits.append(cur)
        elif line.strip() and cur:
            cur[1].append(line)
    pool = sorted(h for h, files in commits if any(f.endswith(EXTS) for f in files))
    picked = random.Random(f"{name}-{month}").sample(pool, min(n, len(pool)))
    items = []
    for k, h in enumerate(picked):
        diff = subprocess.run(["git", "-C", str(clone), "show", "--format=", "--stat=120", "-p", "-U2", h,
                               "--", *[f"*{x}" for x in EXTS]], capture_output=True, text=True,
                              errors="replace").stdout
        items.append({"id": f"{name}-{month}-{k}", "h": h, "text": cc.body(str(clone), h),
                      "diff": diff[:3500]})
    return len(pool), items


def shares(labels, key="primary"):
    n = len(labels)
    c = collections.Counter(v[key] for v in labels.values())
    return {"n": n, "counts": {k: c[k] for k in cc.CATS},
            "share": {k: round(c[k] / n, 4) if n else None for k in cc.CATS}}


def measure(month, clones, client, usage, token, work):
    repos = {}
    for name, slug in REPOS.items():
        clone = clones / name
        pool, items = month_sample(name, clone, month)
        ids = [it["id"] for it in items]
        lab_path = work / "cls" / f"{name}-{month}-labels.json"
        lab_path.write_text(json.dumps(classify(client, usage, [{"id": i["id"], "text": i["text"]} for i in items])))
        msg = cc.load_labels(lab_path, ids)
        jud = judge(client, usage, [{"id": i["id"], "message": i["text"], "diff": i["diff"]} for i in items])
        missing = set(ids) - set(jud)
        if missing:
            raise SystemExit(f"judge labels: {len(missing)} missing for {name} — refusing to report")
        m = shares(msg)
        m["hidden_fix"] = sum(v["contains_fix"] and v["primary"] != "fix" for v in msg.values())
        repos[name] = {
            "pr_commits": pr_commit_counts(slug, month, token),
            "sample": {"pool": pool, "n": len(items), "seed": f"{name}-{month}",
                       "shas": [i["h"] for i in items],
                       "message_labels": m, "diff_labels": shares(jud)}}
    hn, hp = HOTSPOT
    repos[hn]["hotspot"] = hotspot_fixes(clones / hn, hp, month)
    return repos


def criteria(repos):
    """This month's values for each criterion, with counts so the window can be
    summed later. No verdict here: the criterion is over the whole window."""
    r, s = repos["rivet"], repos["spar"]
    d = r["sample"]["diff_labels"]
    return {
        "1_rivet_refactor_share_of_pr_commits": {
            "refactor": r["pr_commits"]["refactor"], "commits": r["pr_commits"]["commits"],
            "value": r["pr_commits"]["refactor_share"], "window_threshold": ">= 0.10 over >= 100 commits"},
        "2_rivet_main_rs_fix_commits": {
            "value": r["hotspot"]["fix"], "file_exists": r["hotspot"]["exists_at_month_end"],
            "window_threshold": "mean <= 6.4 per month, or the file was split"},
        "3_rivet_diff_judged_shares": {
            "refactor": d["counts"]["refactor"], "feature": d["counts"]["feature"], "n": d["n"],
            "refactor_share": d["share"]["refactor"], "feature_share": d["share"]["feature"],
            "window_threshold": "refactor >= 0.15 and feature >= 0.25",
            "instrument": f"{JUDGE_MODEL}, message + diff, uncalibrated"},
        "4_spar_refactor_share_of_pr_commits": {
            "refactor": s["pr_commits"]["refactor"], "commits": s["pr_commits"]["commits"],
            "value": s["pr_commits"]["refactor_share"], "window_threshold": "<= 0.05"},
    }


def window_status(month):
    if TRIGGER_SHIPPED is None:
        return {"trigger_shipped": None, "status": "pre-window",
                "note": "the trigger has not shipped; this month is baseline drift, not evidence"}
    ship = dt.date.fromisoformat(TRIGGER_SHIPPED + "-01")
    months = []
    y, m = ship.year, ship.month
    for _ in range(3):
        y, m = y + (m == 12), m % 12 + 1
        months.append(f"{y}-{m:02d}")
    return {"trigger_shipped": TRIGGER_SHIPPED, "window": months,
            "status": "in-window" if month in months else "outside-window"}


def run(month, out_dir, work, *, refs_fn, label_fn, measure_fn):
    """The pipeline with its parts injectable, so the self-test can drive the
    ordering (instrument first, nothing written on failure) offline."""
    refs = refs_fn()
    scores, failures = instrument_check(refs, label_fn, work)
    for name, s in scores.items():
        print(f"instrument {name}: precision {s['precision']:.2f} recall {s['recall']:.2f} (n={s['n']})")
    if failures:
        print("INSTRUMENT CHECK FAILED, nothing published: " + "; ".join(failures), file=sys.stderr)
        return 1, None
    repos = measure_fn()
    report = {
        "month": month, "boundaries": "UTC calendar month",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "instrument": {
            "classifier_model": CLASSIFIER_MODEL, "judge_model": JUDGE_MODEL,
            "model_source": MODEL_SOURCE, "effort": EFFORT,
            "calibrated_on_2026_10_22_with": "Claude Code 'haiku' alias",
            "thresholds": {"fix_precision_min": PRECISION_MIN, "fix_recall_min": RECALL_MIN},
            "references": {n: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}
                           for n, s in scores.items()},
            "reference_sha256": PINNED, "levin_csv_sha256": LEVIN_SHA256, "passed": True},
        "repos": repos,
        "criteria": criteria(repos),
        "window": window_status(month),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{month}.json"
    path.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {path}")
    return 0, path


def cmd_run(a):
    if not api_key():
        notice(NOT_CONFIGURED)
        return 0
    month = a.month or previous_month()
    work = pathlib.Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    clones = pathlib.Path(a.clones)
    client, usage = make_client(), Usage()
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        code, path = run(month, pathlib.Path(a.out), work,
                         refs_fn=lambda: build_references(clones, work),
                         label_fn=lambda items: classify(client, usage, items),
                         measure_fn=lambda: measure(month, clones, client, usage, token, work))
    except CouldNotRun as e:
        print(f"could not run: {e}", file=sys.stderr)
        return 2
    finally:
        print("usage:", json.dumps(usage.report()))
    if path:
        rep = json.loads(path.read_text())
        rep["usage"] = usage.report()
        path.write_text(json.dumps(rep, indent=1) + "\n")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                fh.write(f"file={path}\n")
    return code


# ── Publish: a PR, never a push to main ──────────────────────────────────────
def gh(method, url, token, body=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28",
                                          "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise CouldNotRun(f"{method} {url}: HTTP {e.code} {e.read()[:300]!r}")


def cmd_publish(a):
    """Branch, file and PR through the REST API. A commit made through the
    contents API is signed by GitHub, which main's signed-commit rule needs;
    a `git push` from the runner would not be."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("could not run: GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    path = pathlib.Path(a.file)
    rep = json.loads(path.read_text())
    month, api = rep["month"], f"https://api.github.com/repos/{a.repo}"
    branch = f"factory-report/{month}"
    try:
        base = gh("GET", f"{api}/git/ref/heads/main", token)["object"]["sha"]
        gh("POST", f"{api}/git/refs", token, {"ref": f"refs/heads/{branch}", "sha": base})
        rel = f"data/factory-report/{month}.json"
        gh("PUT", f"{api}/contents/{rel}", token, {
            "message": f"data: factory report for {month}", "branch": branch,
            "content": base64.b64encode(path.read_bytes()).decode()})
        c = rep["criteria"]
        lines = [f"Monthly measurement for the fix-hotspot experiment, {month} (UTC).", "",
                 f"Instrument check passed: " + ", ".join(
                     f"{n} precision {s['precision']} recall {s['recall']}"
                     for n, s in rep["instrument"]["references"].items()) +
                 f" (classifier `{rep['instrument']['classifier_model']}`).", "",
                 "| criterion | this month |", "|---|---|"]
        for k, v in c.items():
            lines.append(f"| {k} | `{json.dumps({x: y for x, y in v.items() if x != 'window_threshold'})}` |")
        lines += ["", f"Window: {rep['window']['status']}. The verdict is over the window's summed counts, "
                  "not one month.", "", "Opened by `.github/workflows/factory-report.yml`."]
        pr = gh("POST", f"{api}/pulls", token, {"title": f"data: factory report for {month}",
                                                "head": branch, "base": "main", "body": "\n".join(lines)})
    except CouldNotRun as e:
        print(f"could not publish: {e}", file=sys.stderr)
        return 2
    print(f"opened {pr.get('html_url')}")
    return 0


def cmd_configured(_a):
    ok = bool(api_key())
    if not ok:
        notice(NOT_CONFIGURED)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"configured={'true' if ok else 'false'}\n")
    print(f"configured={'true' if ok else 'false'}")
    return 0


# ── Self-test ────────────────────────────────────────────────────────────────
def self_test():
    """Decision table, offline. Every rule in both directions: a gate seen only
    to pass is indistinguishable from one that cannot fail."""
    # The skip cases' notice must not land in a real run's summary or outputs.
    hidden = {k: os.environ.pop(k) for k in ("GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT") if k in os.environ}
    try:
        return _table()
    finally:
        os.environ.update(hidden)


def _table():
    bad = 0

    def check(name, ok):
        nonlocal bad
        bad += not ok
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")

    def s(p, r):
        return {"n": 10, "tp": 0, "fp": 0, "fn": 0, "precision": p, "recall": r}

    print("factory-report self-test")
    check("both references at the 22 October values pass", gate({"agent": s(.84, .89), "human": s(.92, .89)}) == [])
    check("exactly at the thresholds passes", gate({"agent": s(.75, .70), "human": s(.75, .70)}) == [])
    check("agent precision 0.74 fails", gate({"agent": s(.74, .89), "human": s(.92, .89)}) != [])
    check("human recall 0.69 fails", gate({"agent": s(.84, .89), "human": s(.92, .69)}) != [])
    check("a missing reference fails", gate({"agent": s(.84, .89)}) != [])

    truth = [{"id": f"t{i}", "truth": "fix" if i < 5 else "feature"} for i in range(10)]
    never = {t["id"]: {"primary": "feature", "contains_fix": False} for t in truth}
    check("an instrument that never says fix scores precision 0 and fails",
          cc.fix_scores(truth, never)["precision"] == 0.0 and gate({"agent": cc.fix_scores(truth, never),
                                                                    "human": s(.9, .9)}) != [])
    perfect = {t["id"]: {"primary": t["truth"], "contains_fix": t["truth"] == "fix"} for t in truth}
    check("a perfect instrument scores 1.0 / 1.0", cc.fix_scores(truth, perfect)["precision"] == 1.0
          and cc.fix_scores(truth, perfect)["recall"] == 1.0)

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        refs = {name: (stem, truth, [{"id": t["id"], "text": "x"} for t in truth])
                for name, stem in REFERENCES.items()}
        calls = []

        def pipeline(label_fn):
            calls.clear()
            out = td / "out"
            shutil.rmtree(out, ignore_errors=True)
            try:
                code, _ = run("2026-11", out, td / "work", refs_fn=lambda: refs, label_fn=label_fn,
                              measure_fn=lambda: calls.append("measured") or fake_repos())
            except SystemExit:
                code = 1
            return code, sorted(p.name for p in out.glob("*")) if out.exists() else []

        code, files = pipeline(lambda items: {i["id"]: perfect[i["id"]] for i in items})
        check("a passing instrument measures and writes YYYY-MM.json", code == 0 and files == ["2026-11.json"]
              and calls == ["measured"])
        code, files = pipeline(lambda items: {i["id"]: never[i["id"]] for i in items})
        check("a failing instrument exits 1, never measures, writes nothing",
              code == 1 and files == [] and calls == [])
        code, files = pipeline(lambda items: {i["id"]: {"primary": "fixed", "contains_fix": True} for i in items})
        check("malformed labels are refused, nothing written", code == 1 and files == [] and calls == [])
        code, files = pipeline(lambda items: {i["id"]: perfect[i["id"]] for i in items[:-1]})
        check("one missing label (a refusal) is refused, nothing written", code == 1 and files == [])

        for val, label in ((None, "unset"), ("", "empty"), ("  ", "blank")):
            saved = os.environ.pop("ANTHROPIC_API_KEY", None)
            if val is not None:
                os.environ["ANTHROPIC_API_KEY"] = val
            out = td / f"skip-{label}"
            code = cmd_run(argparse.Namespace(month="2026-11", work=str(td / "w2"), clones=str(td),
                                              out=str(out)))
            os.environ.pop("ANTHROPIC_API_KEY", None)
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved
            check(f"{label} ANTHROPIC_API_KEY exits 0 and writes nothing", code == 0 and not out.exists())

    check("previous month of 2026-11-01 is 2026-10", previous_month(dt.date(2026, 11, 1)) == "2026-10")
    check("previous month of 2027-01-15 is 2026-12", previous_month(dt.date(2027, 1, 15)) == "2026-12")
    check("pre-window while the trigger has not shipped", TRIGGER_SHIPPED is not None
          or window_status("2026-11")["status"] == "pre-window")

    sdk_shape_test(check)
    print(f"  {'all cases hold' if not bad else f'{bad} case(s) FAILED'}")
    return 1 if bad else 0


def fake_repos():
    lab = {"n": 1, "counts": {k: 0 for k in cc.CATS}, "share": {k: 0.0 for k in cc.CATS}}
    pr = {"prs": 1, "commits": 1, "by_prefix": {}, "refactor": 0, "refactor_share": 0.0}
    smp = {"pool": 1, "n": 1, "seed": "", "shas": [], "message_labels": lab, "diff_labels": lab}
    return {"rivet": {"pr_commits": pr, "sample": smp,
                      "hotspot": {"path": HOTSPOT[1], "commits": 0, "fix": 0, "exists_at_month_end": True}},
            "spar": {"pr_commits": pr, "sample": smp}}


def sdk_shape_test(check):
    """The real SDK against a mock transport: the request a paid run will send,
    caught before the owner's first run instead of as a 400 during it."""
    try:
        import anthropic
        import httpx2 as httpx
    except ImportError:
        try:
            import anthropic
            import httpx
        except ImportError:
            print("  [skip] SDK request shape: anthropic not installed (the monthly workflow runs it)")
            return
    sent = []

    def handler(request):
        body = json.loads(request.content)
        sent.append(body)
        ids = [i["id"] for i in json.loads(body["messages"][0]["content"])]
        stop = "refusal" if "refuse-me" in ids else "end_turn"
        text = json.dumps({"labels": [{"id": i, "primary": "fix", "contains_fix": True} for i in ids]})
        return httpx.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": body["model"],
            "content": [{"type": "thinking", "thinking": "", "signature": "x"}, {"type": "text", "text": text}],
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 100, "output_tokens": 20}})

    client = anthropic.Anthropic(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    usage = Usage()
    got = classify(client, usage, [{"id": f"c{i}", "text": "msg"} for i in range(25)])
    b = sent[0] if sent else {}
    check("SDK: model is the pinned Haiku id", b.get("model") == CLASSIFIER_MODEL)
    check("SDK: no sampling parameters are sent",
          not any(k in b for k in ("temperature", "top_p", "top_k")))
    check("SDK: effort and json_schema format are in output_config",
          b.get("output_config", {}).get("effort") == EFFORT
          and b.get("output_config", {}).get("format", {}).get("type") == "json_schema")
    check("SDK: no thinking config is sent (adaptive is the default)", "thinking" not in b)
    check("SDK: 25 commits go in 2 batches and all come back labelled", len(sent) == 2 and len(got) == 25)
    check("SDK: labels are read past a leading thinking block", got.get("c0", {}).get("primary") == "fix")
    check("SDK: usage is accumulated", usage.report()[CLASSIFIER_MODEL]["input_tokens"] == 200)
    got = classify(client, usage, [{"id": "refuse-me", "text": "msg"}])
    check("SDK: a refusal leaves the batch unlabelled", got == {})


def month_arg(v):
    if not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", v):
        raise argparse.ArgumentTypeError(f"month must be YYYY-MM, got {v!r}")
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("configured")
    r = sub.add_parser("run")
    r.add_argument("--month", type=month_arg, help="YYYY-MM; default the previous calendar month (UTC)")
    r.add_argument("--clones", required=True, help="directory holding rivet/ and spar/ clones")
    r.add_argument("--work", required=True, help="scratch directory, outside the checkout")
    r.add_argument("--out", required=True)
    p = sub.add_parser("publish")
    p.add_argument("--file", required=True)
    p.add_argument("--repo", required=True)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.cmd:
        ap.error("a subcommand or --self-test is required")
    return {"configured": cmd_configured, "run": cmd_run, "publish": cmd_publish}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
