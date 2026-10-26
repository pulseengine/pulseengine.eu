#!/usr/bin/env python3
"""Check that no published blog post links to a draft post.

CI builds without --drafts, so links to draft posts are dead. This gate
catches them before they reach production.

Rules:
- A published post (draft = false) must not link to a draft post (draft = true).
- A post must not link to a post with a later date (forward reference).
- Draft posts may link to other drafts (they're not built in production).

Usage:
    check-draft-links.py [--drafts]   # --drafts: also check drafts (for local dev)
"""

import argparse
import re
import sys
from pathlib import Path

BLOG_DIR = Path("content/blog")
LINK_RE = re.compile(r'\[[^\]]*\]\((/blog/[^)]+)\)')


def parse_frontmatter(path: Path) -> dict:
    """Parse TOML frontmatter (+++ delimited)."""
    text = path.read_text()
    if not text.startswith("+++"):
        return {}
    end = text.find("+++", 3)
    if end == -1:
        return {}
    fm = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key == "draft":
                fm[key] = val.lower() == "true"
            elif key == "date":
                fm[key] = val
            elif key == "title":
                fm[key] = val
    return fm


def get_slug(path: Path) -> str:
    """Get the URL slug from a blog post path."""
    # content/blog/2026-10-25-safe-was-built-for-slow-humans.md
    # → /blog/safe-was-built-for-slow-humans/
    name = path.stem  # 2026-10-25-safe-was-built-for-slow-humans
    # Strip date prefix
    slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', name)
    # Replace dots with dashes (Zola does this)
    slug = slug.replace('.', '-')
    return f"/blog/{slug}/"


def main():
    parser = argparse.ArgumentParser(description="Check for links to draft posts")
    parser.add_argument("--drafts", action="store_true",
                        help="Also check draft posts (for local dev)")
    args = parser.parse_args()

    # Build index of all posts
    posts = {}  # slug → {path, draft, date, title}
    for path in sorted(BLOG_DIR.glob("*.md")):
        fm = parse_frontmatter(path)
        slug = get_slug(path)
        posts[slug] = {
            "path": path,
            "draft": fm.get("draft", False),
            "date": fm.get("date", ""),
            "title": fm.get("title", path.stem),
        }

    errors = []
    warnings = []

    for path in sorted(BLOG_DIR.glob("*.md")):
        fm = parse_frontmatter(path)
        is_draft = fm.get("draft", False)
        post_date = fm.get("date", "")
        post_slug = get_slug(path)
        post_title = fm.get("title", path.stem)

        # Skip drafts unless --drafts flag
        if is_draft and not args.drafts:
            continue

        text = path.read_text()
        for match in LINK_RE.finditer(text):
            target_slug = match.group(1)
            # Normalize: ensure trailing slash
            if not target_slug.endswith('/'):
                target_slug += '/'

            target = posts.get(target_slug)
            if target is None:
                continue  # Not a blog post link (might be external or typo — other checker handles that)

            # Rule 1: Published post linking to draft
            if not is_draft and target["draft"]:
                errors.append(
                    f"{path.name}: links to draft '{target['title']}' ({target_slug}). "
                    f"Remove the link or publish the target first."
                )

            # Rule 2: Forward reference (linking to a post with a later date)
            if post_date and target["date"] and target["date"] > post_date:
                if not is_draft and not target["draft"]:
                    warnings.append(
                        f"{path.name} (date {post_date}): links to '{target['title']}' "
                        f"(date {target['date']}) — forward reference."
                    )

    for w in warnings:
        print(f"  warning: {w}")

    if errors:
        print(f"\n{len(errors)} dead link(s) to drafts:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    print(f"  {len(posts)} posts checked, 0 links to drafts")
    sys.exit(0)


if __name__ == "__main__":
    main()
