#!/usr/bin/env python3
"""Fail if the plugin cites a blog post that is not in content/blog/.

The plugin's memory and skills attribute claims to posts by slug, e.g.

    From `2026-04-24-variant-pruning-rust-mcdc`.

Nothing connected those citations to the posts. Deleting a draft in #169
left four of them pointing at files that no longer existed, and the breakage
was invisible for eleven days because a citation is prose, not a link — the
site's link checker never sees it.

Matching is on the slug STEM, not the full filename. Filename dates get
corrected (three were realigned to their frontmatter in #169) and a citation
should not break because a post moved by three days.

Exit: 0 all resolve · 1 dangling citations · 2 could not run the check.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude"
POSTS = ROOT / "content" / "blog"

# A dated slug inside backticks: `2026-04-24-variant-pruning-rust-mcdc`
CITATION = re.compile(r"`(20\d{2}-\d{2}-\d{2}-[a-z0-9][a-z0-9.\-]*)`")
DATE_PREFIX = re.compile(r"^20\d{2}-\d{2}-\d{2}-")


def main() -> int:
    if not PLUGIN.is_dir() or not POSTS.is_dir():
        print(f"error: expected {PLUGIN} and {POSTS}", file=sys.stderr)
        return 2

    stems = {DATE_PREFIX.sub("", p.stem if p.suffix == ".md" else p.name)
             for p in POSTS.iterdir()}

    cites: dict[str, list[str]] = {}
    for f in PLUGIN.rglob("*.md"):
        for slug in CITATION.findall(f.read_text(encoding="utf-8", errors="replace")):
            cites.setdefault(slug, []).append(str(f.relative_to(ROOT)))

    if not cites:
        # No citations at all is more likely a broken regex than a clean plugin.
        print("error: found zero post citations — the check examined nothing",
              file=sys.stderr)
        return 2

    dangling = {s: w for s, w in cites.items() if DATE_PREFIX.sub("", s) not in stems}

    print(f"{len(cites)} post citations checked against {len(stems)} posts, "
          f"{len(dangling)} dangling")
    if not dangling:
        return 0

    print("\nCitations pointing at posts that are not in content/blog/:", file=sys.stderr)
    for slug, where in sorted(dangling.items()):
        print(f"  `{slug}`\n      cited in: {', '.join(sorted(set(where)))}", file=sys.stderr)
    print("\nEither restore the post, or reword the citation to state the claim "
          "instead of attributing it.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
