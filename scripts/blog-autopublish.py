#!/usr/bin/env python3
"""Blog auto-publish: scan content/blog/ drafts and categorize them by schedule.

Three modes:

  --mode scan
      Print a JSON inventory to stdout: {today, ready, scheduled, held}.
      A draft is "ready" when date <= today and hold is not true.
      A draft is "scheduled" when date > today (and hold is not true).
      A draft is "held" when hold = true (regardless of date).

  --mode flip --file PATH
      Atomically replace the first `draft = true` line in PATH with
      `draft = false`. Used by the workflow once a post moves to ready.

  --mode report --inventory PATH --published JSON [--run-url URL]
      Render a markdown status report (with a `<!-- blog-cron-status -->`
      bot marker) suitable for posting on the pinned status issue.

The frontmatter parser is intentionally regex-based, not full-TOML — it
only reads the four fields that drive the cron (date, draft, hold, title)
and does not need to interpret arrays or tables. This avoids a dependency
on `tomllib` and keeps the script readable.
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
    hold_m = HOLD_RE.search(fm)
    title_m = TITLE_RE.search(fm)
    return {
        "path": str(path),
        "slug": path.stem.split("-", 3)[-1] if path.stem[:10].count("-") == 2 else path.stem,
        "title": title_m.group(1) if title_m else path.stem,
        "date": date_m.group(1) if date_m else None,
        "draft": bool(draft_m and draft_m.group(1) == "true"),
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
    held = [p for p in drafts if p["hold"]]
    active = [p for p in drafts if not p["hold"]]
    ready = [p for p in active if p["date"] and p["date"] <= today]
    scheduled = [p for p in active if p["date"] and p["date"] > today]
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

    held = inventory["held"]
    lines.append(f"**Held ({len(held)}):**")
    if held:
        for p in held:
            lines.append(f"- ∞ · `{p['slug']}` — {p['title']}")
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
