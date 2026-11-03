#!/usr/bin/env python3
"""Blog auto-publish: scan content/blog/ drafts and categorize them by schedule.

Modes:

  --mode scan
      Print a JSON inventory to stdout: {today, ready, blocked, scheduled, held}.
      Safe-by-default: a draft auto-publishes ONLY when it explicitly opts
      in with `ready = true` AND its `date` has arrived. Concretely:
      A draft is "ready"     when ready = true, hold is not true, date <= today.
      A draft is "scheduled" when ready = true, hold is not true, date > today.
      A draft is "held"      otherwise — no ready flag, ready = false, an
                             explicit hold = true, or ready but missing a date.
                             The report splits this bucket: `hold = true` is a
                             decision, a missing `ready` is an omission.
      The absence of `ready` is the default, so forgetting it can never
      publish a post early; you have to opt in.
      A ready, due draft that links to another draft is "blocked" instead:
      it gets no PR this run (CI's check-draft-links would fail it) and
      publishes once its target is on main. The post is never edited.

  --mode verdict --state S --auto B --queued B
      Classify a publish PR right after `gh pr merge`: prints merged,
      pending or stuck. A CLOSED PR is stuck whatever else is reported.

  --mode flip --file PATH
      Replace the first `draft = true` line in PATH with `draft = false`.
      Nothing else in the post changes.

  --mode report --inventory PATH --published JSON [--pending JSON]
                [--stuck JSON] [--run-url URL]
      Render a markdown status report (with a `<!-- blog-cron-status -->`
      bot marker) suitable for posting on the pinned status issue. Every
      due draft not published by this run is listed as an error.

  --self-test
      Run the decision tables offline; exit 1 on any failing case.

The frontmatter parser is intentionally regex-based, not full-TOML — it
only reads the five fields that drive the cron (date, draft, ready, hold,
title) and does not need to interpret arrays or tables. This avoids a
dependency on `tomllib` and keeps the script readable.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys

BLOG_DIR = pathlib.Path("content/blog")

FRONTMATTER_RE = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+", re.S)
DATE_RE = re.compile(r"^date\s*=\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
DRAFT_RE = re.compile(r"^draft\s*=\s*(true|false)\s*$", re.M)
READY_RE = re.compile(r"^ready\s*=\s*(true|false)\s*$", re.M)
HOLD_RE = re.compile(r"^hold\s*=\s*(true|false)\s*$", re.M)
TITLE_RE = re.compile(r'^title\s*=\s*"([^"]*)"\s*$', re.M)
DRAFT_TRUE_LINE = re.compile(r"^draft\s*=\s*true\s*$", re.M)
# Same pattern and slug rule as scripts/check-draft-links.py, the CI gate a
# publish PR must pass: a link that gate would call dead blocks the post here.
LINK_RE = re.compile(r'\[[^\]]*\]\((/blog/[^)]+)\)')


def parse_post(path: pathlib.Path) -> dict | None:
    """Return a record for a post, or None if it has no parseable frontmatter."""
    text = path.read_text(encoding="utf-8")
    fm_match = FRONTMATTER_RE.match(text)
    if not fm_match:
        return None
    fm = fm_match.group(1)
    date_m = DATE_RE.search(fm)
    draft_m = DRAFT_RE.search(fm)
    ready_m = READY_RE.search(fm)
    hold_m = HOLD_RE.search(fm)
    title_m = TITLE_RE.search(fm)
    return {
        "path": str(path),
        "slug": path.stem.split("-", 3)[-1] if path.stem[:10].count("-") == 2 else path.stem,
        "title": title_m.group(1) if title_m else path.stem,
        "date": date_m.group(1) if date_m else None,
        "draft": bool(draft_m and draft_m.group(1) == "true"),
        "ready": bool(ready_m and ready_m.group(1) == "true"),
        "hold": bool(hold_m and hold_m.group(1) == "true"),
    }


def url_slug(path: pathlib.Path) -> str:
    """/blog/<slug>/ for a post file, as check-draft-links.py computes it."""
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem).replace(".", "-")
    return f"/blog/{slug}/"


def draft_links(text: str, draft_urls: dict) -> list[str]:
    """Slugs of the drafts that `text` links to, in order, without repeats."""
    found = []
    for m in LINK_RE.finditer(text):
        url = m.group(1) if m.group(1).endswith("/") else m.group(1) + "/"
        if url in draft_urls and draft_urls[url] not in found:
            found.append(draft_urls[url])
    return found


def scan(today: str, blog_dir: pathlib.Path = BLOG_DIR) -> dict:
    drafts = []
    draft_urls = {}  # /blog/<slug>/ -> slug, for every draft on disk
    for path in sorted(blog_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        record = parse_post(path)
        if record is None:
            continue
        if record["draft"]:
            drafts.append(record)
            draft_urls[url_slug(path)] = record["slug"]
    # Safe-by-default partition. A draft auto-publishes ONLY if it explicitly
    # opts in with `ready = true`, is not explicitly held, and has a date.
    # Everything else stays held — so a missing `ready` flag can never ship a
    # post early. Each draft lands in exactly one bucket.
    #
    # A due post that links to a draft is "blocked", not "ready": CI's
    # check-draft-links would fail its PR. Scan runs on an unmodified checkout
    # of main, before any flip, so "draft" here means draft on main. The old
    # flip-time link stripper read a tree this run had already flipped, and its
    # pattern never matched a markdown link, so it removed nothing (#336).
    ready, blocked, scheduled, held = [], [], [], []
    for p in drafts:
        if p["ready"] and not p["hold"] and p["date"]:
            if p["date"] > today:
                scheduled.append(p)
                continue
            text = pathlib.Path(p["path"]).read_text(encoding="utf-8")
            targets = [s for s in draft_links(text, draft_urls) if s != p["slug"]]
            if targets:
                blocked.append({**p, "blocked_on": targets})
            else:
                ready.append(p)
        else:
            held.append(p)
    return {
        "today": today,
        "ready": ready,
        "blocked": blocked,
        "scheduled": sorted(scheduled, key=lambda p: p["date"]),
        "held": sorted(held, key=lambda p: p["slug"]),
    }


def flip(path_str: str) -> None:
    path = pathlib.Path(path_str)
    text = path.read_text(encoding="utf-8")
    new_text, count = DRAFT_TRUE_LINE.subn("draft = false", text, count=1)
    if count == 0:
        sys.exit(f"flip: no `draft = true` line found in {path_str}")
    # Only the draft line changes. A link to another draft is not stripped
    # here: scan() holds such a post back as "blocked" until its target is
    # on main, so the owner's text ships as written.
    path.write_text(new_text, encoding="utf-8")


def verdict(state: str, auto: bool, queued: bool) -> str:
    """merged | pending | stuck for a publish PR, read right after `gh pr merge`.

    CLOSED comes first. A closed PR can still report auto-merge armed for a
    moment (the 2026-11-03 run read armed=true a second after #335 closed),
    and a closed PR never merges, whatever else is reported.
    """
    if state == "CLOSED":
        return "stuck"
    if state == "MERGED":
        return "merged"
    if state == "OPEN" and (auto or queued):
        return "pending"
    return "stuck"


def render_report(inventory: dict, published: list[dict], run_url: str,
                  pending: list[dict] | None = None,
                  stuck: list[dict] | None = None) -> str:
    today = inventory["today"]
    pending, stuck = pending or [], stuck or []
    lines = [
        "<!-- blog-cron-status -->",
        f"## Blog auto-publish · last run {today}",
        "",
    ]
    if published:
        lines.append(f"**This run:** published {len(published)} —")
        for entry in published:
            slug = entry["slug"]
            pr = entry.get("pr")
            pr_suffix = f" (PR #{pr})" if pr else ""
            lines.append(f"- `{slug}`{pr_suffix}")
    else:
        lines.append("**This run:** published nothing.")
    lines.append("")

    # Every draft that opted in with `ready = true`, whose date has come, and
    # that this run did not publish. Omitting these is how the report said
    # "no posts ready to publish today" while #312-#336 closed unmerged. A
    # pending PR is listed too: on a merge-queue repo that is the normal state
    # at report time, and nothing in this run can see whether it lands.
    done = {e["slug"] for e in published}
    outcome = {}
    for kind, entries in (("pending", pending), ("stuck", stuck)):
        for e in entries:
            outcome[e["slug"]] = (kind, e.get("pr"))
    due = [p for p in inventory["ready"] + inventory.get("blocked", [])
           if p["slug"] not in done]
    if due:
        lines.append(f"**❌ Error — due but not published ({len(due)}):**")
        for p in sorted(due, key=lambda p: (p["date"], p["slug"])):
            kind, pr = outcome.get(p["slug"], (None, None))
            if p.get("blocked_on"):
                why = ("blocked: links to draft "
                       + ", ".join(f"`{s}`" for s in p["blocked_on"])
                       + " — publishes once that is on main")
            elif kind == "pending":
                why = f"PR #{pr} armed for the merge queue — not on main yet"
            elif kind == "stuck":
                why = f"STUCK: PR #{pr} did not merge and is not queued"
            else:
                why = "no PR was opened"
            lines.append(f"- ❌ {p['date']} · `{p['slug']}` — {why}")
        lines.append("")

    scheduled = inventory["scheduled"]
    lines.append(f"**Scheduled ({len(scheduled)}):**")
    if scheduled:
        for p in scheduled:
            lines.append(f"- {p['date']} · `{p['slug']}` — {p['title']}")
    else:
        lines.append("- _none_")
    lines.append("")

    # Two very different states used to render identically as `∞ Held`:
    # a post parked on purpose (`hold = true`) and a finished post that
    # simply never got `ready = true`. Collapsing them is how a post rots —
    # one measured instance sat 101 days while this report was green daily.
    # An omission needs an action; a hold does not. Show them apart.
    held = inventory["held"]
    parked = [p for p in held if p.get("hold")]
    unmarked = [p for p in held if not p.get("hold")]

    lines.append(f"**Held on purpose — `hold = true` ({len(parked)}):**")
    if parked:
        for p in parked:
            lines.append(f"- ⏸ · `{p['slug']}` — {p['title']}")
    else:
        lines.append("- _none_")
    lines.append("")

    lines.append(f"**Not yet marked `ready = true` ({len(unmarked)}):**")
    if unmarked:
        lines.append(
            "_These will never publish until someone adds `ready = true`. "
            "If that is deliberate, set `hold = true` instead so it stops "
            "showing up here as an omission._"
        )
        for p in unmarked:
            age = f"{p['date']} · " if p.get("date") else "no date · "
            lines.append(f"- ⚠️ {age}`{p['slug']}` — {p['title']}")
    else:
        lines.append("- _none_")
    lines.append("")

    if run_url:
        lines.append(f"_Run: {run_url}_")
    return "\n".join(lines) + "\n"


def self_test() -> int:
    """Decision tables, offline. Returns the number of failing cases."""
    import tempfile

    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += not ok

    # verdict: (state, auto-merge armed, in merge queue) -> outcome.
    # The first row is the 2026-11-03 run's reading of #335, which the old
    # bash logic classified as pending: closed, with auto-merge still showing.
    for args, want in (
        (("CLOSED", True, False), "stuck"),
        (("CLOSED", False, True), "stuck"),
        (("CLOSED", False, False), "stuck"),
        (("MERGED", False, False), "merged"),
        (("OPEN", True, False), "pending"),
        (("OPEN", False, True), "pending"),
        (("OPEN", False, False), "stuck"),
        (("", False, False), "stuck"),
    ):
        got = verdict(*args)
        check(f"verdict{args} -> {want} (got {got})", got == want)

    def post(date: str, body: str = "", ready: bool = True, draft: bool = True) -> str:
        return (f'+++\ntitle = "t"\ndate = {date}\ndraft = {str(draft).lower()}\n'
                f'ready = {str(ready).lower()}\n+++\n\n{body}\n')

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        files = {
            # the incident pair: both due, the second links to the first over
            # a line break, as the trust post does
            "2026-10-30-attention.md": post("2026-10-30"),
            "2026-11-02-trust.md": post("2026-11-02", "[whose attention\nruns out](/blog/attention/)"),
            "2026-10-01-old.md": post("2026-10-01", draft=False),
            "2026-11-01-links-published.md": post("2026-11-01", "[x](/blog/old/) [self](/blog/links-published/)"),
            "2026-12-01-future.md": post("2026-12-01", "[a](/blog/attention/)"),
            "2026-10-02-unready.md": post("2026-10-02", ready=False),
            "2026-11-01-links-unready.md": post("2026-11-01", "[u](/blog/unready)"),
        }
        for name, text in files.items():
            (d / name).write_text(text, encoding="utf-8")
        inv = scan("2026-11-03", d)
        ready = sorted(p["slug"] for p in inv["ready"])
        blocked = {p["slug"]: p["blocked_on"] for p in inv["blocked"]}
        check("scan: a due post linking a draft is blocked, not ready",
              blocked.get("trust") == ["attention"] and "trust" not in ready)
        check("scan: its target, due and unlinked, is ready", "attention" in ready)
        check("scan: links to published posts and to itself do not block",
              "links-published" in ready)
        check("scan: a link without trailing slash to a held draft blocks",
              blocked.get("links-unready") == ["unready"])
        check("scan: a future post stays scheduled even with a draft link",
              [p["slug"] for p in inv["scheduled"]] == ["future"])

        trust = d / "2026-11-02-trust.md"
        before = trust.read_text(encoding="utf-8")
        flip(str(trust))
        after = trust.read_text(encoding="utf-8")
        check("flip: only the draft line changes; a draft link survives",
              after == before.replace("draft = true", "draft = false", 1)
              and "](/blog/attention/)" in after)

    inv = {"today": "2026-11-03",
           "ready": [{"slug": "a", "date": "2026-10-30", "title": "A"},
                     {"slug": "q", "date": "2026-11-03", "title": "Q"},
                     {"slug": "n", "date": "2026-11-03", "title": "N"}],
           "blocked": [{"slug": "b", "date": "2026-11-02", "title": "B",
                        "blocked_on": ["a"]}],
           "scheduled": [], "held": []}
    rep = render_report(inv, [], "", pending=[{"slug": "q", "pr": "7"}],
                        stuck=[{"slug": "a", "pr": "335"}])
    check("report: every due, unpublished post is an error",
          "Error — due but not published (4)" in rep)
    check("report: a closed PR is shown as stuck", "STUCK: PR #335" in rep)
    check("report: a blocked post names its draft target", "links to draft `a`" in rep)
    check("report: a pending PR is listed, not omitted", "PR #7 armed" in rep)
    check("report: a post with no PR is listed", "`n` — no PR was opened" in rep)
    check("report: never says nothing was ready while posts are due",
          "no posts ready" not in rep)
    rep = render_report({**inv, "ready": inv["ready"][:1], "blocked": []},
                        [{"slug": "a", "pr": "9"}], "")
    check("report: a published post is not an error", "Error" not in rep)

    print(f"\n{'passed' if not fails else 'FAILED'}: {fails} failing case(s)")
    return 1 if fails else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["scan", "flip", "report", "verdict"])
    parser.add_argument("--self-test", action="store_true", help="Run the decision tables offline")
    parser.add_argument("--state", help="PR state: OPEN, CLOSED or MERGED (--mode verdict)")
    parser.add_argument("--auto", default="false", help="auto-merge armed, true|false (--mode verdict)")
    parser.add_argument("--queued", default="false", help="in the merge queue, true|false (--mode verdict)")
    parser.add_argument("--pending", default="[]",
                        help="JSON array of {slug, pr} armed or queued this run (--mode report)")
    parser.add_argument("--stuck", default="[]",
                        help="JSON array of {slug, pr} that did not merge (--mode report)")
    parser.add_argument("--file", help="Path to the post (--mode flip)")
    parser.add_argument("--inventory", help="Path to inventory JSON (--mode report)")
    parser.add_argument(
        "--published",
        default="[]",
        help="JSON array of {slug, pr} for posts published this run (--mode report)",
    )
    parser.add_argument("--run-url", default="", help="GitHub Actions run URL (--mode report)")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.mode:
        parser.error("--mode or --self-test is required")
    if args.mode == "verdict":
        if args.state is None:
            sys.exit("--state is required for --mode verdict")
        print(verdict(args.state, args.auto == "true", args.queued == "true"))
    elif args.mode == "scan":
        today = datetime.date.today().isoformat()
        json.dump(scan(today), sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.mode == "flip":
        if not args.file:
            sys.exit("--file is required for --mode flip")
        flip(args.file)
    elif args.mode == "report":
        if not args.inventory:
            sys.exit("--inventory is required for --mode report")
        with open(args.inventory, encoding="utf-8") as f:
            inventory = json.load(f)
        published = json.loads(args.published)
        sys.stdout.write(render_report(inventory, published, args.run_url,
                                       json.loads(args.pending), json.loads(args.stuck)))


if __name__ == "__main__":
    main()
