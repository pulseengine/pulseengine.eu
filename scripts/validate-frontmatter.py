#!/usr/bin/env python3
"""Validate blog post frontmatter for required fields and consistency."""

import sys
import tomllib
from pathlib import Path

REQUIRED_FIELDS = ["title", "description", "date"]
REQUIRED_TAXONOMIES = ["tags", "authors"]


def extract_frontmatter(path: Path) -> str | None:
    """Extract TOML frontmatter between +++ markers."""
    text = path.read_text()
    if not text.startswith("+++"):
        return None
    end = text.index("+++", 3)
    return text[3:end]


def validate(path: Path) -> list[str]:
    """Return list of validation errors for a blog post."""
    errors = []

    # Skip section index files
    if path.name == "_index.md":
        return errors

    toml_str = extract_frontmatter(path)
    if toml_str is None:
        return [f"{path}: missing TOML frontmatter (+++ markers)"]

    try:
        fm = tomllib.loads(toml_str)
    except tomllib.TOMLDecodeError as e:
        return [f"{path}: invalid TOML frontmatter: {e}"]

    for field in REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"{path}: missing required field '{field}'")

    taxonomies = fm.get("taxonomies", {})
    for tax in REQUIRED_TAXONOMIES:
        if tax not in taxonomies:
            errors.append(f"{path}: missing taxonomy '{tax}'")
        elif not taxonomies[tax]:
            errors.append(f"{path}: taxonomy '{tax}' is empty")

    return errors


def main() -> int:
    files = [Path(f) for f in sys.argv[1:]]
    all_errors = []

    for f in files:
        all_errors.extend(validate(f))

    for error in all_errors:
        print(error, file=sys.stderr)

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
