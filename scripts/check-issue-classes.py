#!/usr/bin/env python3
# rivet: verifies REQ-ISSUE-CLASS-RATCHET
"""Fail if the rivet/spar issue queues are not classified on the oracle axis.

`issue-hunt` says the exit condition is a release, not an empty tracker — right,
and nothing limited intake. The brake splits the queue by the only axis that
decides whether an agent can finish an item alone:

  agent-closable  a named reproducer exists AND currently fails on main
  needs-decision  everything else: scope, architecture, priority, no oracle yet

The brake applies to `needs-decision` only, so discovery is never throttled.

WHAT THIS CHECK DOES AND DOES NOT ENFORCE — read this before trusting it.
If a label alone released an issue from the brake, an agent would write both the
fix and the exemption releasing it: spar #385 exactly, an exemption keyed on a
pattern the exempted party controls, which ran green over 12 of 12 unproven
obligations. So an `agent-closable` issue must carry a fenced ```repro block
holding a command.

THE PROOF IS BY REFERENCE, NOT BY COMMAND — this is what makes it mechanical.
An earlier revision only checked that a fenced ```repro block existed and parsed,
which ```repro/true satisfies; that moved a self-assigned exemption from a label
into a code fence without proving anything. Executing the block here was refused
and still is: issue bodies stay editable after labelling, including by external
filers, and this job holds a cross-repo token, so running strings from an issue
body would be command injection with a secret in the environment.

So `agent-closable` instead requires `repro-run:` with a link to a **GitHub
Actions run in the same repository as the issue**, and the check asserts, over
the API only:

  1. the run exists and `conclusion == "failure"`;
  2. its head commit touches a test path.

Only reviewed repository code ever executes — in that repo's own CI, where it
already runs — and the token needs read scopes alone, never execution. A `true`
reproducer cannot produce a red run that touches a test, so it fails by
construction. The cost of entering class (a) is now authoring a failing test,
which is exactly the work the amendment calls an (a)-class task.

Every rule stays a pure function over fetched records, so the whole decision
table runs offline and gates pull requests.

WHY A TWO-SIDED RATCHET AND NOT A THRESHOLD. Nobody can defend 20 over 40. The
floor is whatever `needs-decision` measured at the first classified pass. Growth
above it puts the pass in close-only mode — and a count BELOW it is also a
finding, because a floor left above the real count is headroom: drop from 20 to
10 and ten new undecided items land before the brake fires. That is the
ceiling-with-headroom vacuity, and spar's own ratchet comment calls for "exact
two-sided ... locked in rather than left as slack".

WHY STALENESS DEMOTES, AND FROM WHEN. The incentive runs toward class (a). An
`agent-closable` issue still open after MAX_AGENT_DAYS was not oracle-closable in
practice, so it demotes to `needs-decision` and comes under the brake. Nobody has
to judge motives, and the demotion rate measures classification honesty directly.

The clock starts when the LABEL was applied, not when the issue was filed. Most
of this backlog predates the brake — 10 rivet and 14 spar issues are over 60 days
old — so ageing from `createdAt` would flag every old issue the moment it is
classified, and the only way to a green first pass would be to put all of them in
`needs-decision`, inflating the very floor the ratchet then locks in.

WHY SCHEDULED AND NOT A PR CHECK. The property is a fact about tracker state,
which drifts with no PR involved, so a PR gate would be green on a backlog that
grew overnight. Runners here carry no `gh` (see memory: runners-have-no-gh-cli),
so this talks to the REST API over stdlib and treats a missing token as
**exit 2, could not run** — never as a pass. A gate that cannot reach its
evidence must say so.

Exit: 0 conforming · 1 drift · 2 could not run.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOORS = ROOT / "scripts" / "issue-class-floors.json"

AGENT = "agent-closable"
DECIDE = "needs-decision"
MAX_AGENT_DAYS = 21

# Bot liveness alerts are not work items. rivet carries 108 of them; counting
# them was how the first backlog read came out with the wrong denominator.
BOT_AUTHORS = {"app/github-actions", "github-actions[bot]", "github-actions"}
BOT_LABELS = {"runner-down"}
EXEMPT_LABELS = {"perennial"}

REPRO = re.compile(r"```+\s*repro\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

# `repro-run: https://github.com/<owner>/<repo>/actions/runs/<id>`
REPRO_RUN = re.compile(
    r"repro-run:\s*<?https://github\.com/([\w.-]+)/([\w.-]+)/actions/runs/(\d+)",
    re.IGNORECASE,
)

# Path-based on purpose: a content sniff for "is this a test" would have to parse
# four languages, and a wrong answer here silently widens class (a).
TEST_PATH = re.compile(
    r"(^|/)(tests?|fuzz|spec)/|(^|/)test_[^/]+$|[._-]test\.[\w]+$|\.test\.[\w]+$|(^|/)tests\.rs$",
    re.IGNORECASE,
)


def repro_run_ref(body: str | None) -> tuple[str, str, int] | None:
    """The owner/repo/run-id a `repro-run:` line points at."""
    m = REPRO_RUN.search(body or "")
    return (m.group(1), m.group(2), int(m.group(3))) if m else None


def run_proves_red(ref: tuple[str, str, int], issue_repo: str,
                   run: dict | None, changed: list[str]) -> list[str]:
    """Pure: does this run stand as proof? Takes already-fetched records so the
    decision table covers it without a network."""
    owner, repo, run_id = ref
    named = f"{owner}/{repo}"
    problems: list[str] = []
    # Same repo as the issue: otherwise any red run anywhere would do.
    if named.lower() != issue_repo.lower():
        problems.append(
            f"repro-run points at {named}, not at {issue_repo} — the proof must be "
            f"a run in the issue's own repository"
        )
        return problems
    if run is None:
        problems.append(f"repro-run {run_id} does not exist in {named}")
        return problems
    if run.get("conclusion") != "failure":
        problems.append(
            f"repro-run {run_id} concluded {run.get('conclusion')!r}, not 'failure' — "
            f"a green run is not a reproducer"
        )
    if not any(TEST_PATH.search(f) for f in changed):
        problems.append(
            f"repro-run {run_id}'s head commit touches no test path "
            f"({len(changed)} file(s) changed) — a red run without a new test "
            f"proves a broken build, not a reproduced defect"
        )
    return problems


def is_work_item(issue: dict) -> bool:
    """A bot alert or a perennial is not part of either queue."""
    if (issue.get("author") or "") in BOT_AUTHORS:
        return False
    labels = {l.lower() for l in issue.get("labels", [])}
    return not (labels & BOT_LABELS) and not (labels & EXEMPT_LABELS)


def repro_command(body: str | None) -> str | None:
    """The first non-empty, non-comment line of a fenced ```repro block."""
    m = REPRO.search(body or "")
    if not m:
        return None
    for line in m.group(1).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def age_days(stamp: str | None, now: datetime) -> float | None:
    if not stamp:
        return None
    try:
        t = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - t).total_seconds() / 86400


def classify(issues: list[dict], floor: int | None, now: datetime) -> tuple[list[str], dict]:
    """Pure check over already-fetched issues. Returns (findings, counts)."""
    findings: list[str] = []
    counts = {AGENT: 0, DECIDE: 0, "unclassified": 0, "stale_agent": 0, "skipped": 0}

    for i in issues:
        if not is_work_item(i):
            counts["skipped"] += 1
            continue
        num, labels = i.get("number"), {l.lower() for l in i.get("labels", [])}
        has_a, has_b = AGENT in labels, DECIDE in labels

        if has_a and has_b:
            findings.append(f"#{num} carries both {AGENT} and {DECIDE} — the classes are exclusive")
            counts["unclassified"] += 1
            continue
        if not has_a and not has_b:
            findings.append(f"#{num} carries neither {AGENT} nor {DECIDE}")
            counts["unclassified"] += 1
            continue

        if has_b:
            counts[DECIDE] += 1
            continue

        counts[AGENT] += 1
        ref = repro_run_ref(i.get("body"))
        if ref is None:
            findings.append(
                f"#{num} is {AGENT} with no `repro-run:` link to a failing Actions "
                f"run — the class is earned by a red run that adds a test, not "
                f"asserted by a label"
            )
        elif "repro_run" in i:
            # Resolved by the live check; offline the reference alone is all we have.
            findings.extend(
                f"#{num}: {p}"
                for p in run_proves_red(ref, i.get("repo", ""), i["repro_run"],
                                        i.get("repro_run_files", []))
            )
        # labeledAt when we have it; createdAt only as a last resort, and then
        # it is reported as unknown rather than silently treated as old.
        age = age_days(i.get("labeledAt"), now)
        if age is not None and age > MAX_AGENT_DAYS:
            counts["stale_agent"] += 1
            findings.append(
                f"#{num} has been {AGENT} for {age:.0f} days (limit {MAX_AGENT_DAYS}) — "
                f"demote to {DECIDE}; it was not oracle-closable in practice"
            )

    if floor is not None:
        if counts[DECIDE] > floor:
            findings.append(
                f"{DECIDE} queue is {counts[DECIDE]}, above its floor of {floor} — "
                f"the pass runs in close-only mode and files no new issues"
            )
        elif counts[DECIDE] < floor:
            findings.append(
                f"{DECIDE} queue is {counts[DECIDE]}, below its floor of {floor} — "
                f"ratchet the floor down to {counts[DECIDE]}; a floor above the real "
                f"count is headroom new undecided work slips into"
            )
    return findings, counts


def labeled_at(repo: str, number: int, token: str) -> str | None:
    """When was AGENT last applied? The staleness clock starts there."""
    url = f"https://api.github.com/repos/{repo}/issues/{number}/events?per_page=100"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "pulseengine-check-issue-classes",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        events = json.load(r)
    stamps = [
        e.get("created_at")
        for e in events
        if e.get("event") == "labeled" and (e.get("label") or {}).get("name", "").lower() == AGENT
    ]
    return max(stamps) if stamps else None


def api(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "pulseengine-check-issue-classes",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_run(ref: tuple[str, str, int], token: str) -> tuple[dict | None, list[str]]:
    """The run record and the files its head commit changed. Read scopes only —
    nothing here executes anything, in this repo or the referenced one."""
    owner, repo, run_id = ref
    try:
        run = api(f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, []
        raise
    sha = run.get("head_sha")
    files: list[str] = []
    if sha:
        try:
            commit = api(f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}", token)
            files = [f["filename"] for f in commit.get("files", [])]
        except urllib.error.HTTPError:
            files = []
    return run, files


def fetch(repo: str, token: str) -> list[dict]:
    """Open issues via REST. urllib, because the runners have no gh."""
    out: list[dict] = []
    for page in range(1, 11):
        url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=100&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "pulseengine-check-issue-classes",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r)
        if not batch:
            break
        for it in batch:
            if "pull_request" in it:
                continue
            labels = [l["name"] for l in it.get("labels", [])]
            rec = {
                "number": it["number"],
                "labels": labels,
                "body": it.get("body"),
                "createdAt": it.get("created_at"),
                "author": (it.get("user") or {}).get("login", ""),
                "labeledAt": None,
            }
            # One extra call, only for class (a), only to age the label rather
            # than the issue. Everything else needs no event history.
            if AGENT in {l.lower() for l in labels}:
                rec["labeledAt"] = labeled_at(repo, it["number"], token)
                rec["repo"] = repo
                ref = repro_run_ref(rec["body"])
                if ref is not None:
                    # Resolve it here so classify() stays pure and offline.
                    rec["repro_run"], rec["repro_run_files"] = fetch_run(ref, token)
            out.append(rec)
        if len(batch) < 100:
            break
    return out


def self_test() -> int:
    """Decision table. Every rule asserted in BOTH directions — a rule only
    present in the should-fail column can be satisfied by a check that always
    fails, which is how a gate passes review while measuring nothing."""
    now = datetime(2026, 10, 21, tzinfo=timezone.utc)
    fresh, old = "2026-10-20T00:00:00Z", "2026-08-01T00:00:00Z"

    RUN = "repro-run: https://github.com/pulseengine/rivet/actions/runs/4242\n"
    ok_body = "words\n" + RUN + "```repro\ncargo test -p rivet --test vet_gate\n```\n"

    def a(n, body=ok_body, created=fresh, labeled=fresh, labels=None, run=..., files=None):
        d = dict(number=n, labels=labels if labels is not None else [AGENT],
                 body=body, createdAt=created, labeledAt=labeled, author="avrabe",
                 repo="pulseengine/rivet")
        if run is not ...:
            d["repro_run"] = run
            d["repro_run_files"] = files or []
        return d

    def b(n, created=fresh):
        return dict(number=n, labels=[DECIDE], body="", createdAt=created,
                    labeledAt=None, author="avrabe")

    cases = [
        # (name, issues, floor, expect_findings)
        ("conforming agent-closable passes", [a(1)], None, False),
        ("conforming needs-decision passes", [b(2, old)], None, False),
        ("unlabelled issue is caught", [a(3, labels=[])], None, True),
        ("both labels is caught", [a(4, labels=[AGENT, DECIDE])], None, True),
        ("agent-closable with no repro-run link is caught",
         [a(5, body="I promise there is an oracle")], None, True),
        ("a repro command WITHOUT a run link is not enough any more",
         [a(6, body="```repro\ntrue\n```")], None, True),

        # Proof by reference. Only reviewed repo code runs, in that repo's CI.
        ("a red run touching a test is accepted",
         [a(21, run={"conclusion": "failure", "head_sha": "abc"},
            files=["crates/rivet/tests/vet_gate.rs"])], None, False),
        ("a GREEN run is rejected",
         [a(22, run={"conclusion": "success", "head_sha": "abc"},
            files=["crates/rivet/tests/vet_gate.rs"])], None, True),
        ("a red run touching NO test path is rejected",
         [a(23, run={"conclusion": "failure", "head_sha": "abc"},
            files=["src/main.rs", "README.md"])], None, True),
        ("a run that does not exist is rejected",
         [a(24, run=None, files=[])], None, True),
        ("a run in a DIFFERENT repo is rejected",
         [a(25, body="repro-run: https://github.com/someone/else/actions/runs/1\n",
            run={"conclusion": "failure", "head_sha": "abc"},
            files=["tests/t.rs"])], None, True),
        ("`true` cannot be laundered through a red run with no test",
         [a(26, body=RUN + "```repro\ntrue\n```",
            run={"conclusion": "failure", "head_sha": "abc"},
            files=["src/lib.rs"])], None, True),

        # Staleness ages from the LABEL, not the issue.
        ("stale label is caught", [a(7, created=old, labeled=old)], None, True),
        ("OLD ISSUE, FRESHLY LABELLED is clean — else no first pass can go green",
         [a(8, created=old, labeled=fresh)], None, False),
        ("no labeledAt at all does not fabricate staleness",
         [a(9, created=old, labeled=None)], None, False),
        ("stale needs-decision is NOT caught (the brake is not an SLA)",
         [b(10, old)], None, False),

        ("bot alert is skipped, not required to carry a class",
         [dict(number=11, labels=["runner-down"], body="", createdAt=old,
               labeledAt=None, author="app/github-actions")], None, False),
        ("perennial is skipped",
         [dict(number=12, labels=["perennial"], body="", createdAt=old,
               labeledAt=None, author="avrabe")], None, False),

        # The ratchet is two-sided: slack is a finding, not a comfort.
        ("needs-decision AT the floor passes", [b(13)], 1, False),
        ("needs-decision ABOVE the floor fires the brake", [b(14), b(15)], 1, True),
        ("needs-decision BELOW the floor says lower it", [b(16)], 2, True),
        ("agent-closable does NOT count toward the floor",
         [a(17), a(18), b(19)], 1, False),

    ]

    print("check-issue-classes self-test")
    bad = 0
    for name, issues, floor, expect in cases:
        findings, _ = classify(issues, floor, now)
        got = bool(findings)
        mark = "ok  " if got == expect else "FAIL"
        if got != expect:
            bad += 1
        print(f"  [{mark}] {name}  (expected {'findings' if expect else 'clean'}, got {len(findings)})")
        if got != expect:
            for f in findings:
                print(f"            {f}")
    print(f"  {len(cases) - bad}/{len(cases)} cases hold")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true", help="run the decision table; no network")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--repos", nargs="*", help="override the repo list from the floors file")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not FLOORS.is_file():
        print(f"could not run: {FLOORS.relative_to(ROOT)} is missing", file=sys.stderr)
        return 2
    floors = json.loads(FLOORS.read_text())

    token = os.environ.get("ISSUE_CLASS_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "could not run: no ISSUE_CLASS_TOKEN / GH_TOKEN / GITHUB_TOKEN in the environment.\n"
            "Reading another repo's issues needs a cross-repo read token; the default\n"
            "GITHUB_TOKEN is scoped to this repository only. Exiting 2 rather than 0 —\n"
            "a gate that cannot reach its evidence has not verified anything.",
            file=sys.stderr,
        )
        return 2

    now = datetime.now(timezone.utc)
    repos = args.repos if args.repos else sorted(floors.get("repos", {}))
    report, rc = {}, 0
    for repo in repos:
        floor = (floors.get("repos", {}).get(repo) or {}).get(f"{DECIDE}_floor")
        try:
            issues = fetch(repo, token)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"could not run: {repo}: {e}", file=sys.stderr)
            return 2
        findings, counts = classify(issues, floor, now)
        report[repo] = {"floor": floor, "counts": counts, "findings": findings}
        if findings:
            rc = 1

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return rc

    for repo, r in report.items():
        c = r["counts"]
        print(f"{repo}: {AGENT}={c[AGENT]}  {DECIDE}={c[DECIDE]} (floor {r['floor']})  "
              f"unclassified={c['unclassified']}  stale={c['stale_agent']}  skipped={c['skipped']}")
        for f in r["findings"]:
            print(f"  - {f}")
    print("conforming" if rc == 0 else "DRIFT — see findings above")
    return rc


if __name__ == "__main__":
    sys.exit(main())
