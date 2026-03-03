#!/usr/bin/env python3
"""Inject git commit info into blog post frontmatter before zola build."""

import subprocess
import sys
from pathlib import Path


def git_info(path: Path) -> tuple[str, str, int]:
    """Return (short_hash, full_hash, commit_count) for a file."""
    result = subprocess.run(
        ["git", "log", "--format=%H", "--", str(path)],
        capture_output=True, text=True, check=True,
    )
    commits = result.stdout.strip().splitlines()
    if not commits:
        return ("", "", 0)
    return (commits[0][:7], commits[0], len(commits))


def inject(path: Path) -> bool:
    """Inject git info into frontmatter. Returns True if modified."""
    text = path.read_text()
    if not text.startswith("+++"):
        return False

    end = text.index("+++", 3)
    frontmatter = text[3:end]
    body = text[end:]

    short_hash, full_hash, count = git_info(path)
    if count == 0:
        return False

    # Remove existing git info lines if re-running
    lines = [
        line for line in frontmatter.splitlines()
        if not line.startswith("last_commit")
        and not line.startswith("commit_count")
    ]

    # Find or create [extra] section
    extra_idx = None
    next_section_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "[extra]":
            extra_idx = i
        elif extra_idx is not None and line.strip().startswith("["):
            next_section_idx = i
            break

    git_lines = [
        f'last_commit = "{short_hash}"',
        f'commit_count = {count}',
    ]

    if extra_idx is not None:
        insert_at = next_section_idx if next_section_idx else len(lines)
        for j, gl in enumerate(git_lines):
            lines.insert(insert_at + j, gl)
    else:
        lines.append("")
        lines.append("[extra]")
        lines.extend(git_lines)

    new_frontmatter = "\n".join(lines)
    if not new_frontmatter.endswith("\n"):
        new_frontmatter += "\n"

    path.write_text("+++" + new_frontmatter + body)
    return True


def main() -> int:
    blog_dir = Path("content/blog")
    if not blog_dir.exists():
        print("content/blog not found", file=sys.stderr)
        return 1

    count = 0
    for md in sorted(blog_dir.glob("*.md")):
        if md.name == "_index.md":
            continue
        if inject(md):
            count += 1
            info = git_info(md)
            print(f"  {md.name}: {info[0]} ({info[2]} revisions)")

    print(f"Injected git info into {count} posts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
