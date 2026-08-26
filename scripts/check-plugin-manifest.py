#!/usr/bin/env python3
"""Fail if the marketplace manifest has drifted from the plugin it advertises.

`.claude-plugin/marketplace.json` is what someone running `/plugin install`
reads. `claude-tooling/plugins/pulseengine-claude/.claude-plugin/plugin.json`
is what actually gets installed — verified: the plugin cache keys on
plugin.json's version (`~/.claude/plugins/cache/.../0.20.0/`), and
marketplace.json is not copied into the cache at all.

So the drift is not a resolution bug — it is worse in one specific way: it is
invisible. Measured on 2026-08-26, the manifest advertised version 0.12.0 and
"fourteen procedural skills" while the plugin was 0.25.0 with sixteen. Nothing
failed; the storefront was simply wrong for thirteen minor versions.

Three checks:
  1. marketplace version == plugin version (both the top-level and the entry)
  2. marketplace plugin description == plugin description
  3. the spelled-out skill count in the description == skills/ on disk

Check 3 is the one that actually rotted, so it is checked as a number and not
as a substring.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKET = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_DIR = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude"
PLUGIN = PLUGIN_DIR / ".claude-plugin" / "plugin.json"

WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
COUNT_RE = re.compile(r"\b(" + "|".join(WORDS) + r")\s+procedural\s+skills\b", re.I)


def main() -> int:
    market = json.loads(MARKET.read_text())
    plugin = json.loads(PLUGIN.read_text())
    skills = sorted(p.name for p in (PLUGIN_DIR / "skills").iterdir() if p.is_dir())

    entries = [p for p in market["plugins"] if p["name"] == plugin["name"]]
    if not entries:
        print(f"error: marketplace.json has no entry for {plugin['name']!r}", file=sys.stderr)
        return 1
    entry = entries[0]

    problems: list[str] = []

    if entry["version"] != plugin["version"]:
        problems.append(
            f"entry version {entry['version']!r} != plugin.json {plugin['version']!r}")
    if market["version"] != plugin["version"]:
        problems.append(
            f"marketplace version {market['version']!r} != plugin.json {plugin['version']!r}")
    if entry["description"] != plugin["description"]:
        problems.append("entry description differs from plugin.json's")

    m = COUNT_RE.search(entry["description"])
    if not m:
        problems.append(
            "description does not state a spelled-out '<n> procedural skills' count")
    elif WORDS[m.group(1).lower()] != len(skills):
        problems.append(
            f"description claims {m.group(1)} ({WORDS[m.group(1).lower()]}) "
            f"procedural skills, but skills/ holds {len(skills)}")

    if problems:
        print("marketplace.json has drifted from the plugin it advertises:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("\nThis is the storefront an outsider reads. Sync it.", file=sys.stderr)
        return 1

    print(f"marketplace.json in sync: v{plugin['version']}, {len(skills)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
