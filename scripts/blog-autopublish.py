#!/usr/bin/env python3
"""Blog auto-publish: scan content/blog/ drafts and categorize them by schedule.

Three modes:

  --mode scan
      Print a JSON inventory to stdout: {today, ready, scheduled, held}.
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

  --mode flip --file PATH
      Atomically replace the first `draft = true` line in PATH with
      `draft = false`. Used by the workflow once a post moves to ready.

  --mode report --inventory PATH --published JSON [--run-url URL]
      Render a markdown status report (with a `<!-- blog-cron-status -->`
      bot marker) suitable for posting on the pinned status issue.

The frontmatter parser is intentionally regex-based, not full-TOML — it
only reads the five fields that drive the cron (date, draft, ready, hold,
title) and does not need to interpret arrays or tables. This avoids a
dependency on `tomllib` and keeps the script readable.
"""

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


def scan(today: str) -> dict:
    drafts = []
    for path in sorted(BLOG_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        record = parse_post(path)
        if record is None:
            continue
        if record["draft"]:
            drafts.append(record)
    # Safe-by-default partition. A draft auto-publishes ONLY if it explicitly
    # opts in with `ready = true`, is not explicitly held, and has a date.
    # Everything else stays held — so a missing `ready` flag can never ship a
    # post early. Each draft lands in exactly one bucket.
    ready, scheduled, held = [], [], []
    for p in drafts:
        if p["ready"] and not p["hold"] and p["date"]:
            (ready if p["date"] <= today else scheduled).append(p)
        else:
            held.append(p)
    return {
        "today": today,
        "ready": ready,
        "scheduled": sorted(scheduled, key=lambda p: p["date"]),
        "held": sorted(held, key=lambda p: p["slug"]),
    }


def flip(path_str: str) -> None:
    path = pathlib.Path(path_str)
    text = path.read_text(encoding="utf-8")
    new_text, count = DRAFT_TRUE_LINE.subn("draft = false", text, count=1)
    if count == 0:
        sys.exit(f"flip: no `draft = true` line found in {path_str}")
    path.write_text(new_text, encoding="utf-8")


def render_report(inventory: dict, published: list[dict], run_url: str) -> str:
    today = inventory["today"]
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
        lines.append("**This run:** no posts ready to publish today.")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["scan", "flip", "report"], required=True)
    parser.add_argument("--file", help="Path to the post (--mode flip)")
    parser.add_argument("--inventory", help="Path to inventory JSON (--mode report)")
    parser.add_argument(
        "--published",
        default="[]",
        help="JSON array of {slug, pr} for posts published this run (--mode report)",
    )
    parser.add_argument("--run-url", default="", help="GitHub Actions run URL (--mode report)")
    args = parser.parse_args()

    if args.mode == "scan":
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
        sys.stdout.write(render_report(inventory, published, args.run_url))


if __name__ == "__main__":
    main()
