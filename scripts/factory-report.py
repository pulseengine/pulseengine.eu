#!/usr/bin/env python3
# rivet: verifies REQ-FACTORY-REPORT-INSTRUMENT-GATE
"""Monthly measurement for the fix-hotspot experiment (docs/experiments/2026-10-hotspot-trigger.md).

    factory-report.py --self-test              offline decision table; no credential, no network, no CLI
    factory-report.py configured               prints whether a Claude credential is set (exit 0 either way)
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

The model calls run on the owner's Claude subscription: the Claude Code CLI
in print mode, authenticated by the CLAUDE_CODE_OAUTH_TOKEN secret (made with
`claude setup-token`). ANTHROPIC_API_KEY is accepted as a fallback credential
for a local run, and is then billed to that API account; when both are set the
OAuth token wins and the key is withheld from the CLI, which would otherwise
prefer it. The workflow passes only the OAuth token. Bare mode is never used:
it reads only an API key and ignores OAuth, so it would silently break the
subscription run.

A missing credential (unset or empty) is exit 0 with a notice and no
file. This deliberately differs from check-issue-classes.py, which exits 2 on a
missing token: that script is a gate, and a gate that cannot reach its evidence
must go red. This one produces a report, and a skipped run publishes nothing,
so nothing false can be read from it. A red schedule for the known reason "the
owner has not added the secret yet" would only train people to ignore red.

Instruments:
- Message labels: Claude Haiku through the Claude Code CLI, model id below,
  read from the models overview page on 2026-10-27; the CLI is pinned to the
  version below and accepted both full ids when tried on 2026-10-28. The 22 October calibration used Claude
  Code's "haiku" alias, which may not be the same snapshot; the instrument
  check, not the name, is what qualifies the model each month.
- Diff judgement (criterion 3): Claude Sonnet reading message plus diff
  truncated at 3,500 characters, both repositories shuffled together under
  opaque ids, as judge-batches.py did for the baseline. It has no labelled
  refactor reference, so it is reported as uncalibrated.
  No fallback model is passed to the CLI, and every answer's per-model usage
  must name exactly the requested model: a fallback would swap the instrument
  silently, so a swap is "could not run" and a refusal is a missing label;
  either way the run fails closed.
- Each call runs `claude -p` with no tools, no MCP servers, no settings
  sources and no session persistence, from a fresh empty directory, so no
  CLAUDE.md, memory or hook reaches the classifier. The prompt goes on stdin;
  the labels come back in the result's `structured_output`, validated by the
  CLI against --json-schema. The CLI has no max-tokens flag, so none is set.

Month boundaries are UTC calendar months. The 22 October baseline used a
+02:00 cut-off; the difference is at most two hours at each end.

Exit: 0 report written, or not configured · 1 instrument check failed or
labels incomplete · 2 could not run (reference moved, network, a CLI failure
after retries, auth failure, the subscription usage limit).
"""
from __future__ import annotations

import argparse
import base64
import collections
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
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
BATCH = 20                  # commits per classifier request
JUDGE_BATCH = 10            # diffs per judge request
CLAUDE_CLI = "claude"
CLI_VERSION = "2.1.312"     # the version the workflow installs and this was tried with
CLI_TIMEOUT = 600           # seconds per call
BACKOFF = (15, 60, 180, 420)  # seconds before each retry of a transient failure

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
# The month the trigger shipped ("YYYY-MM"): rivet#1133, merged 2026-10-28 as
# b4122de6. The window is the three calendar months after it, and the verdict
# is computed over the window's summed counts, never from one month.
TRIGGER_SHIPPED = "2026-10"

PREFIX = re.compile(r"^(\w+)(\([^)]*\))?!?:")


class CouldNotRun(Exception):
    pass


def notice(msg):
    print(f"::notice title=factory-report::{msg}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(f"### factory report\n\n{msg}\n")


CREDENTIALS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")   # first set one wins


def credential():
    """The name of the credential the CLI will use, or "". Unset and empty are
    the same: an Actions secret that does not exist arrives as the empty
    string, not as a missing variable."""
    return next((k for k in CREDENTIALS if (os.environ.get(k) or "").strip()), "")


NOT_CONFIGURED = ("not configured: CLAUDE_CODE_OAUTH_TOKEN is not set, so no report was produced. "
                  "Create it with `claude setup-token` and add it under Settings > Secrets and "
                  "variables > Actions to enable the monthly run.")


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
class UsageLimit(CouldNotRun):
    """The subscription's usage window is exhausted. Not retried: the window
    does not reset within any backoff this job can afford."""


class Usage:
    """Per-model tokens and the CLI's own notional list-price cost. On the
    subscription nothing is billed per token; the figure says what the run
    would have cost on the API."""

    KEYS = (("inputTokens", "input_tokens"), ("cacheCreationInputTokens", "cache_creation_input_tokens"),
            ("cacheReadInputTokens", "cache_read_input_tokens"), ("outputTokens", "output_tokens"))

    def __init__(self):
        self.tokens = collections.defaultdict(lambda: collections.defaultdict(float))

    def add(self, model_usage):
        for m, u in (model_usage or {}).items():
            for src, dst in self.KEYS:
                self.tokens[m][dst] += u.get(src, 0) or 0
            self.tokens[m]["notional_cost_usd"] += u.get("costUSD", 0) or 0

    def report(self):
        return {m: {**{dst: int(t[dst]) for _, dst in self.KEYS},
                    "notional_cost_usd": round(t["notional_cost_usd"], 4)}
                for m, t in self.tokens.items()}


def _schema(fields):
    return {"type": "object", "additionalProperties": False, "required": ["labels"],
            "properties": {"labels": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", *fields],
                "properties": {"id": {"type": "string"}, **fields}}}}}


LABEL_FIELDS = {"primary": {"type": "string", "enum": cc.CATS}, "contains_fix": {"type": "boolean"}}
JUDGE_FIELDS = {"primary": {"type": "string", "enum": cc.CATS}, "refactor": {"type": "boolean"}}


def cli_argv(model, system, fields):
    """Print mode with every ambient input switched off. `--tools ""` leaves
    only the CLI's StructuredOutput tool, which is how --json-schema answers."""
    return [CLAUDE_CLI, "-p", "--model", model, "--effort", EFFORT,
            "--json-schema", json.dumps(_schema(fields)), "--output-format", "json", "--verbose",
            "--system-prompt", system, "--tools", "", "--strict-mcp-config",
            "--setting-sources", "", "--no-session-persistence"]


def cli_env():
    """With the OAuth token present, the API key is withheld from the CLI so
    the run lands on the subscription, never on an API account by accident."""
    env = dict(os.environ)
    if (env.get("CLAUDE_CODE_OAUTH_TOKEN") or "").strip():
        env.pop("ANTHROPIC_API_KEY", None)
    return env


def cli_result(stdout):
    """(result object, rate-limit infos). `--output-format json` prints one
    result object, or with --verbose (always passed, so the rate-limit events
    come too) the whole message list ending in it; both are read."""
    try:
        d = json.loads(stdout or "")
    except ValueError:
        return None, []
    msgs = d if isinstance(d, list) else [d]
    msgs = [m for m in msgs if isinstance(m, dict)]
    res = next((m for m in reversed(msgs) if m.get("type") == "result"), None)
    return res, [m.get("rate_limit_info") or {} for m in msgs if m.get("type") == "rate_limit_event"]


LIMIT_TEXT = re.compile(r"usage limit|hit your (usage )?limit|limit reached|limit will reset|resets at", re.I)
TRANSIENT_TEXT = re.compile(r"overloaded|connection|timed? ?out|network|ECONNRESET|socket|internal server", re.I)
TRANSIENT_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
_sleep = time.sleep          # the self-test replaces it


def _call(runner, argv, prompt):
    """One CLI call, retried with backoff on transient failures. Returns the
    result object; raises CouldNotRun (or UsageLimit) on anything else."""
    why = ""
    for attempt in range(len(BACKOFF) + 1):
        if attempt:
            print(f"  claude: {why}; retry {attempt}/{len(BACKOFF)} in {BACKOFF[attempt - 1]}s", file=sys.stderr)
            _sleep(BACKOFF[attempt - 1])
        with tempfile.TemporaryDirectory(prefix="factory-report-claude-") as cwd:
            try:
                p = runner(argv, input=prompt, capture_output=True, text=True, timeout=CLI_TIMEOUT,
                           cwd=cwd, env=cli_env())
            except subprocess.TimeoutExpired:
                why = f"no answer within {CLI_TIMEOUT}s"
                continue
            except FileNotFoundError:
                raise CouldNotRun(f"the Claude Code CLI ({CLAUDE_CLI}) is not installed")
        res, limits = cli_result(p.stdout)
        text = str((res or {}).get("result") or p.stderr or "")[:300]
        if any(i.get("status") == "rejected" for i in limits) or (
                (res is None or res.get("is_error")) and LIMIT_TEXT.search(text)):
            raise UsageLimit(f"subscription usage limit reached: {text}")
        if res is not None and p.returncode == 0 and not res.get("is_error"):
            return res
        status = (res or {}).get("api_error_status")
        why = f"exit {p.returncode}, status {status}: {text}"
        if res is not None and status not in TRANSIENT_STATUS and not TRANSIENT_TEXT.search(text):
            raise CouldNotRun(f"Claude Code CLI failed ({why})")
    raise CouldNotRun(f"Claude Code CLI failed after {len(BACKOFF)} retries ({why})")


def _ask(client, usage, model, system, items, fields):
    """One request. Returns {id: label}. A refusal, or an answer without
    structured output, returns {} for the batch, so the caller's schema check
    (commit-classify.load_labels) fails closed on the missing ids. `client` is
    a subprocess.run-compatible runner."""
    res = _call(client, cli_argv(model, system, fields), json.dumps(items, ensure_ascii=False))
    used = res.get("modelUsage") or {}
    usage.add(used)
    if set(used) != {model}:
        raise CouldNotRun(f"asked for {model}, the CLI answered with {sorted(used)}: instrument swapped")
    out = res.get("structured_output")
    rows = out.get("labels") if isinstance(out, dict) else None
    if not isinstance(rows, list):
        print(f"  {model}: no structured output (stop_reason={res.get('stop_reason')}, "
              f"{res.get('terminal_reason')}) for {len(items)} items; leaving them unlabelled", file=sys.stderr)
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
    """The runner every model call goes through; the self-test passes a stub."""
    return subprocess.run


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


def blind_judge(client, usage, samples, month):
    """Judge every repo's sample in one shuffled list under opaque ids, as
    judge-batches.py did for the baseline, so no request tells the judge
    which project or month a diff came from. Returns {real id: label}."""
    items = [i for name in samples for i in samples[name]]
    random.Random(f"judge-{month}").shuffle(items)
    key = {f"j{k:04d}": it["id"] for k, it in enumerate(items)}
    pub = [{"id": f"j{k:04d}", "message": it["text"], "diff": it["diff"]} for k, it in enumerate(items)]
    got = judge(client, usage, pub)
    return {key[j]: lab for j, lab in got.items() if j in key}


def measure(month, clones, client, usage, token, work):
    repos, samples = {}, {}
    for name, slug in REPOS.items():
        pool, items = month_sample(name, clones / name, month)
        samples[name] = items
        lab_path = work / "cls" / f"{name}-{month}-labels.json"
        lab_path.write_text(json.dumps(classify(client, usage, [{"id": i["id"], "text": i["text"]} for i in items])))
        msg = cc.load_labels(lab_path, [it["id"] for it in items])
        m = shares(msg)
        m["hidden_fix"] = sum(v["contains_fix"] and v["primary"] != "fix" for v in msg.values())
        repos[name] = {
            "pr_commits": pr_commit_counts(slug, month, token),
            "sample": {"pool": pool, "n": len(items), "seed": f"{name}-{month}",
                       "shas": [i["h"] for i in items], "message_labels": m}}
    jud = blind_judge(client, usage, samples, month)
    for name, items in samples.items():
        ids = [it["id"] for it in items]
        missing = [i for i in ids if i not in jud]
        if missing:
            raise SystemExit(f"judge labels: {len(missing)} missing for {name}, refusing to report")
        repos[name]["sample"]["diff_labels"] = shares({i: jud[i] for i in ids})
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
    if not credential():
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
    except UsageLimit as e:
        # A CLI failure is "could not run", not "the instrument failed": the
        # exit code is how the log tells the two apart.
        print(f"::error title=factory-report::subscription usage limit reached — re-run with "
              f"workflow_dispatch month={month}")
        print(f"could not run: subscription usage limit reached — re-run with workflow_dispatch "
              f"month={month} ({e})", file=sys.stderr)
        return 2
    except (CouldNotRun, subprocess.CalledProcessError) as e:
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


def pr_body(rep):
    refs = ", ".join(f"{n} precision {s['precision']} recall {s['recall']}"
                     for n, s in rep["instrument"]["references"].items())
    lines = [f"Monthly measurement for the fix-hotspot experiment, {rep['month']} (UTC). "
             f"Instrument check passed: {refs} (classifier `{rep['instrument']['classifier_model']}`, "
             f"judge `{rep['instrument']['judge_model']}`).", "",
             "| criterion | this month |", "|---|---|"]
    for k, v in rep["criteria"].items():
        lines.append(f"| {k} | `{json.dumps({x: y for x, y in v.items() if x != 'window_threshold'})}` |")
    cost = sum(u.get("notional_cost_usd", 0) for u in rep.get("usage", {}).values())
    lines += ["", f"Window: {rep['window']['status']}. The verdict is computed over the window's summed "
              f"counts, never from one month. Run on the Claude subscription; notional "
              f"list-price cost as reported by Claude Code: ${cost:.2f}. "
              "Opened by `.github/workflows/factory-report.yml`."]
    return "\n".join(lines)


def publish(path, repo, token, call=None):
    """Branch, file and PR through the REST API, never a push to main. A commit
    made through the contents API with an App token is expected to be signed by
    GitHub, which main's signed-commit rule needs; a `git push` from the runner
    would not be. Unverified until the first report PR: check that its commit
    shows Verified."""
    call = call or gh
    rep = json.loads(pathlib.Path(path).read_text())
    month, api = rep["month"], f"https://api.github.com/repos/{repo}"
    branch = f"factory-report/{month}"
    base = call("GET", f"{api}/git/ref/heads/main", token)["object"]["sha"]
    call("POST", f"{api}/git/refs", token, {"ref": f"refs/heads/{branch}", "sha": base})
    call("PUT", f"{api}/contents/data/factory-report/{month}.json", token, {
        "message": f"data: factory report for {month}", "branch": branch,
        "content": base64.b64encode(pathlib.Path(path).read_bytes()).decode()})
    return call("POST", f"{api}/pulls", token, {"title": f"data: factory report for {month}",
                                                 "head": branch, "base": "main", "body": pr_body(rep)})


def cmd_publish(a):
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("could not run: GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    try:
        pr = publish(a.file, a.repo, token)
    except CouldNotRun as e:
        print(f"could not publish: {e}", file=sys.stderr)
        return 2
    print(f"opened {pr.get('html_url')}")
    return 0


def cmd_configured(_a):
    ok = bool(credential())
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
        reqs = []

        def fake_gh(method, url, token, body=None):
            reqs.append((method, url.split("/repos/o/r")[1], body))
            return {"object": {"sha": "abc"}, "html_url": "https://example.invalid/pr/1"}

        pr = publish(td / "out" / "2026-11.json", "o/r", "t", call=fake_gh)
        steps = [(m, u) for m, u, _ in reqs]
        check("publish: branch, file and PR via REST, never a ref update on main",
              steps == [("GET", "/git/ref/heads/main"), ("POST", "/git/refs"),
                        ("PUT", "/contents/data/factory-report/2026-11.json"), ("POST", "/pulls")]
              and reqs[1][2]["ref"] == "refs/heads/factory-report/2026-11"
              and reqs[2][2]["branch"] == "factory-report/2026-11"
              and reqs[3][2]["head"] == "factory-report/2026-11"
              and reqs[3][2]["base"] == "main" and pr["html_url"].endswith("/pr/1"))
        check("publish: the PR body names the instrument and every criterion",
              "claude-haiku-5-5" in reqs[3][2]["body"]
              and all(k in reqs[3][2]["body"] for k in criteria(fake_repos())))
        code, files = pipeline(lambda items: {i["id"]: never[i["id"]] for i in items})
        check("a failing instrument exits 1, never measures, writes nothing",
              code == 1 and files == [] and calls == [])
        code, files = pipeline(lambda items: {i["id"]: {"primary": "fixed", "contains_fix": True} for i in items})
        check("malformed labels are refused, nothing written", code == 1 and files == [] and calls == [])
        code, files = pipeline(lambda items: {i["id"]: perfect[i["id"]] for i in items[:-1]})
        check("one missing label (a refusal) is refused, nothing written", code == 1 and files == [])

        saved = {k: os.environ.pop(k) for k in CREDENTIALS if k in os.environ}
        try:
            for val, label in ((None, "unset"), ("", "empty"), ("  ", "blank")):
                for k in CREDENTIALS:
                    os.environ.pop(k, None)
                    if val is not None:
                        os.environ[k] = val
                out = td / f"skip-{label}"
                code = cmd_run(argparse.Namespace(month="2026-11", work=str(td / "w2"), clones=str(td),
                                                  out=str(out)))
                check(f"{label} CLAUDE_CODE_OAUTH_TOKEN and ANTHROPIC_API_KEY exit 0 and write nothing",
                      code == 0 and not out.exists())
            for k in CREDENTIALS:
                os.environ.pop(k, None)
            os.environ["ANTHROPIC_API_KEY"] = "k"
            check("ANTHROPIC_API_KEY alone counts as configured (local fallback)",
                  credential() == "ANTHROPIC_API_KEY" and "ANTHROPIC_API_KEY" in cli_env())
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "t"
            check("with both set the OAuth token wins and the key is withheld from the CLI",
                  credential() == "CLAUDE_CODE_OAUTH_TOKEN" and "ANTHROPIC_API_KEY" not in cli_env())

            # The subscription limit mid-run: exit 2, nothing written, the
            # re-run instruction in the log.
            real = globals()["build_references"]

            def limited(*_a):
                raise UsageLimit("subscription usage limit reached: You've hit your limit")

            globals()["build_references"] = limited
            out, err = td / "limited", io.StringIO()
            try:
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    code = cmd_run(argparse.Namespace(month="2026-11", work=str(td / "w3"), clones=str(td),
                                                      out=str(out)))
            finally:
                globals()["build_references"] = real
            check("a usage limit exits 2, writes nothing, and says how to re-run",
                  code == 2 and not out.exists() and "subscription usage limit reached — re-run with "
                  "workflow_dispatch month=2026-11" in err.getvalue())
        finally:
            for k in CREDENTIALS:
                os.environ.pop(k, None)
            os.environ.update(saved)

    check("previous month of 2026-11-01 is 2026-10", previous_month(dt.date(2026, 11, 1)) == "2026-10")
    check("previous month of 2027-01-15 is 2026-12", previous_month(dt.date(2027, 1, 15)) == "2026-12")
    check("pre-window while the trigger has not shipped", TRIGGER_SHIPPED is not None
          or window_status("2026-11")["status"] == "pre-window")

    cli_shape_test(check)
    print(f"  {'all cases hold' if not bad else f'{bad} case(s) FAILED'}")
    return 1 if bad else 0


def fake_repos():
    lab = {"n": 1, "counts": {k: 0 for k in cc.CATS}, "share": {k: 0.0 for k in cc.CATS}}
    pr = {"prs": 1, "commits": 1, "by_prefix": {}, "refactor": 0, "refactor_share": 0.0}
    smp = {"pool": 1, "n": 1, "seed": "", "shas": [], "message_labels": lab, "diff_labels": lab}
    return {"rivet": {"pr_commits": pr, "sample": smp,
                      "hotspot": {"path": HOTSPOT[1], "commits": 0, "fix": 0, "exists_at_month_end": True}},
            "spar": {"pr_commits": pr, "sample": smp}}


# Recorded from Claude Code 2.1.312 on 2026-10-28 (`claude -p --output-format json`
# with verbose on, so a message list), trimmed to the fields read here. The
# first is cli_argv(CLASSIFIER_MODEL, ...) on two commits; the second is the
# same call with a model id that does not exist (exit 1).
RECORDED = [
    {"type": "system", "subtype": "init", "tools": ["StructuredOutput"], "mcp_servers": [],
     "model": "claude-haiku-5-5", "apiKeySource": "none", "claude_code_version": "2.1.312"},
    {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", "rateLimitType": "seven_day",
                                                      "utilization": 0.32}},
    {"type": "result", "subtype": "success", "is_error": False, "api_error_status": None,
     "stop_reason": "tool_use", "terminal_reason": "completed", "num_turns": 2,
     "result": "{\"labels\":[{\"id\":\"a\",\"primary\":\"fix\",\"contains_fix\":true},"
               "{\"id\":\"b\",\"primary\":\"feature\",\"contains_fix\":false}]}",
     "structured_output": {"labels": [{"id": "a", "primary": "fix", "contains_fix": True},
                                      {"id": "b", "primary": "feature", "contains_fix": False}]},
     "total_cost_usd": 0.0003017,
     "modelUsage": {"claude-haiku-5-5": {"inputTokens": 2, "outputTokens": 97, "cacheReadInputTokens": 0,
                                         "cacheCreationInputTokens": 1265, "costUSD": 0.0003017}}}]
RECORDED_ERROR = {
    "type": "result", "subtype": "success", "is_error": True, "api_error_status": 404,
    "stop_reason": "stop_sequence", "terminal_reason": "api_error", "num_turns": 1,
    "result": "There's an issue with the selected model (claude-nonexistent-9). It may not exist or you "
              "may not have access to it. Run --model to pick a different model.",
    "structured_output": None, "total_cost_usd": 0, "modelUsage": {}}


def cli_shape_test(check):
    """A stub in place of subprocess.run: the exact command a subscription run
    sends, and the parsing of what the CLI answers, caught before the owner's
    first run instead of during it."""
    global _sleep
    calls, slept = [], []
    real_sleep, _sleep = _sleep, slept.append
    repo = HERE.parent.resolve()

    def done(obj, code=0, stderr=""):
        return subprocess.CompletedProcess([], code, stdout=json.dumps(obj), stderr=stderr)

    def result(model, rows, **kw):
        r = {**RECORDED[-1], "structured_output": {"labels": rows},
             "modelUsage": {model: {"inputTokens": 100, "outputTokens": 20, "cacheReadInputTokens": 5,
                                    "cacheCreationInputTokens": 7, "costUSD": 0.001}}}
        r.update(kw)
        return r

    def stub(argv, **kw):
        cwd = pathlib.Path(kw.get("cwd") or ".").resolve()
        calls.append({"argv": list(argv), "input": kw.get("input"), "cwd": cwd,
                      "cwd_empty": cwd.is_dir() and not any(cwd.iterdir()), "kw": kw})
        model = argv[argv.index("--model") + 1]
        sent = json.loads(kw["input"])
        ids = [i["id"] for i in sent]
        if "refuse-me" in ids:
            return done(result(model, [], structured_output=None, stop_reason="refusal"))
        if model == JUDGE_MODEL:   # label each diff by what its message says, to check the mapping
            return done(result(model, [{"id": i["id"], "primary": i["message"], "refactor": False} for i in sent]))
        return done(result(model, [{"id": i, "primary": "fix", "contains_fix": True} for i in ids]))

    try:
        usage = Usage()
        got = classify(stub, usage, [{"id": f"c{i}", "text": "msg"} for i in range(25)])
        a = calls[0]["argv"] if calls else []

        def val(flag):
            return a[a.index(flag) + 1] if flag in a and a.index(flag) + 1 < len(a) else None

        check("CLI: print mode, the pinned Haiku id, effort low, verbose JSON output",
              a[:2] == [CLAUDE_CLI, "-p"] and val("--model") == CLASSIFIER_MODEL
              and val("--effort") == EFFORT == "low" and val("--output-format") == "json"
              and "--verbose" in a)
        check("CLI: --json-schema is the labels schema itself, not an API format wrapper",
              json.loads(val("--json-schema") or "null") == _schema(LABEL_FIELDS)
              and json.loads(val("--json-schema"))["required"] == ["labels"])
        check("CLI: no tools, no MCP, no settings sources, no session persistence",
              val("--tools") == "" and val("--setting-sources") == ""
              and "--strict-mcp-config" in a and "--no-session-persistence" in a)
        check("CLI: never bare mode (it ignores OAuth), never a fallback model",
              not any("bare" in x for x in a) and not any("fallback" in x for x in a))
        check("CLI: the system prompt is the classifier prompt",
              val("--system-prompt") == PROMPT)
        check("CLI: the commits go on stdin, never in argv",
              json.loads(calls[0]["input"])[0] == {"id": "c0", "text": "msg"}
              and not any("c0" in x for x in a))
        check("CLI: each call runs in a fresh empty directory outside the repo",
              all(c["cwd_empty"] and repo not in c["cwd"].parents and c["cwd"] != repo for c in calls)
              and len({c["cwd"] for c in calls}) == len(calls))
        check("CLI: a timeout is set on every call", all(c["kw"].get("timeout") for c in calls))
        check("CLI: 25 commits go in 2 batches and all come back labelled", len(calls) == 2 and len(got) == 25)
        check("CLI: labels are read from structured_output", got.get("c0", {}).get("primary") == "fix")
        rep_ = usage.report()[CLASSIFIER_MODEL]
        check("CLI: usage is accumulated per model, cache tokens and notional cost included",
              rep_["input_tokens"] == 200 and rep_["cache_read_input_tokens"] == 10
              and rep_["cache_creation_input_tokens"] == 14 and rep_["output_tokens"] == 40
              and rep_["notional_cost_usd"] == 0.002)
        check("CLI: a refusal (no structured output) leaves the batch unlabelled",
              classify(stub, usage, [{"id": "refuse-me", "text": "msg"}]) == {})

        # The recorded responses, exactly as the CLI printed them.
        u = Usage()
        rec = _ask(lambda *a_, **k: done(RECORDED), u, CLASSIFIER_MODEL, PROMPT,
                   [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}], LABEL_FIELDS)
        check("recorded: the message-list shape parses to both labels",
              rec == {"a": {"primary": "fix", "contains_fix": True},
                      "b": {"primary": "feature", "contains_fix": False}})
        check("recorded: usage and notional cost read from modelUsage",
              u.report() == {CLASSIFIER_MODEL: {"input_tokens": 2, "cache_creation_input_tokens": 1265,
                                                "cache_read_input_tokens": 0, "output_tokens": 97,
                                                "notional_cost_usd": 0.0003}})
        rec1 = _ask(lambda *a_, **k: done(RECORDED[-1]), Usage(), CLASSIFIER_MODEL, PROMPT,
                    [{"id": "a", "text": "x"}], LABEL_FIELDS)
        check("recorded: the single-object shape parses too", rec1 == {"a": {"primary": "fix", "contains_fix": True}})

        def raises(responses, exc=CouldNotRun):
            seq, n = list(responses), [0]

            def r(*_a, **_k):
                n[0] += 1
                x = seq.pop(0) if len(seq) > 1 else seq[0]
                if isinstance(x, BaseException):
                    raise x
                return x
            slept.clear()
            try:
                with contextlib.redirect_stderr(io.StringIO()):   # simulated retries, not real ones
                    out = _ask(r, Usage(), CLASSIFIER_MODEL, PROMPT, [{"id": "a", "text": "x"}], LABEL_FIELDS)
                return "returned", n[0], out
            except exc as e:
                return type(e).__name__, n[0], str(e)
            except Exception as e:     # the wrong exception is a failure, not a pass
                return f"wrong:{type(e).__name__}", n[0], str(e)

        k, n, _ = raises([done(RECORDED_ERROR, 1)])
        check("recorded: is_error (404, unknown model) is could-not-run, not retried",
              k == "CouldNotRun" and n == 1)
        k, n, _ = raises([done({**RECORDED_ERROR, "api_error_status": 401, "result": "Invalid API key"}, 1)])
        check("an auth failure is could-not-run, not retried", k == "CouldNotRun" and n == 1)
        k, n, out = raises([done({**RECORDED_ERROR, "api_error_status": 529, "result": "Overloaded"}, 1),
                            subprocess.TimeoutExpired("claude", CLI_TIMEOUT),
                            done({}, 1, "socket hang up"), done(RECORDED)])
        check("transient failures (529, timeout, no JSON) are retried with backoff, then succeed",
              k == "returned" and n == 4 and out.get("a", {}).get("primary") == "fix" and slept == list(BACKOFF[:3]))
        k, n, _ = raises([done({**RECORDED_ERROR, "api_error_status": 503, "result": "Overloaded"}, 1)])
        check("a transient failure that persists is could-not-run after every retry",
              k == "CouldNotRun" and n == len(BACKOFF) + 1)
        k, n, msg = raises([done([{"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}},
                                  {**RECORDED_ERROR, "api_error_status": 429,
                                   "result": "You've hit your limit · resets 3pm"}], 1)], UsageLimit)
        check("a rejected rate-limit event is a usage limit, reported as such, not retried",
              k == "UsageLimit" and n == 1 and "usage limit" in msg)
        k, n, _ = raises([done({**RECORDED_ERROR, "api_error_status": 429,
                                "result": "Claude usage limit reached. Your limit will reset at 3pm"}, 1)],
                         UsageLimit)
        check("usage-limit wording without the event is a usage limit too", k == "UsageLimit" and n == 1)
        k, n, _ = raises([done({**RECORDED[-1], "is_error": False, "modelUsage": {
            JUDGE_MODEL: RECORDED[-1]["modelUsage"][CLASSIFIER_MODEL]}})])
        check("an answer from another model is could-not-run (instrument swap)", k == "CouldNotRun" and n == 1)
        k, n, _ = raises([FileNotFoundError("claude")])
        check("a missing CLI is could-not-run", k == "CouldNotRun" and n == 1)
        k, n, _ = raises([done({"type": "result", "is_error": False, "modelUsage": {}}, 0)])
        check("a result with no model usage is could-not-run", k == "CouldNotRun")

        calls.clear()
        samples = {name: [{"id": f"{name}-2026-11-{k}", "h": "x", "diff": f"d{p}",
                           "text": ["feature", "fix", "refactor", "maintenance"][k % 4]} for k in range(12)]
                   for p, name in enumerate(REPOS)}
        jud = blind_judge(stub, usage, samples, "2026-11")
        ja = calls[0]["argv"] if calls else []
        sent = [json.loads(c["input"]) for c in calls]
        seen_ids = [i["id"] for b in sent for i in b]
        check("CLI judge: the pinned Sonnet id, the judge prompt and schema, no tools, never bare mode",
              ja[ja.index("--model") + 1] == JUDGE_MODEL and ja[ja.index("--system-prompt") + 1] == JUDGE_PROMPT
              and json.loads(ja[ja.index("--json-schema") + 1]) == _schema(JUDGE_FIELDS)
              and ja[ja.index("--tools") + 1] == "" and not any("bare" in x for x in ja))
        check("CLI judge: ids are opaque, so no request names a project or month",
              seen_ids and all(re.fullmatch(r"j\d{4}", i) for i in seen_ids)
              and not any(n in json.dumps([c["input"] for c in calls]) + json.dumps([c["argv"] for c in calls])
                          for n in REPOS))
        check("CLI judge: 24 diffs in 3 batches, projects mixed within the first",
              len(calls) == 3 and {i["diff"] for i in sent[0]} == {"d0", "d1"})
        check("CLI judge: every label maps back to its own commit",
              len(jud) == 24 and all(jud[i["id"]]["primary"] == i["text"] for n in samples for i in samples[n]))
    finally:
        _sleep = real_sleep


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
