#!/usr/bin/env python3
# rivet: verifies REQ-README-ROSTER
"""Fail if the plugin README's skill roster has drifted from skills/ on disk.

`check-plugin-manifest.py` keeps `marketplace.json` and `plugin.json` honest
about each other, including the spelled-out skill count. Nothing checked the
README, which is the only place a reader learns what each skill actually DOES —
the manifests carry one run-on description, not a per-skill entry.

So the README drifted, and the count check could not see it. Measured on
2026-10-14, the roster listed 14 of 18 skills: `evidence-transfer`,
`gate-potency`, `repo-hygiene` and `verify-your-own-claims` were installed,
loadable, triggering, and undocumented. Four skills a reader could not learn
existed, in a plugin whose own `claim-verification` skill exists to stop exactly
this — and the same shape as PLUGIN-MEMORY-FILES-ALL-DOCUMENTED, which was
caught by hand once and is now a gated claim.

Why a script rather than another claims.yaml entry: a claim binds a pattern to a
count, so it would need editing on every skill added. This derives both sides
from disk and needs no maintenance.

Checked in both directions:
  1. every directory under skills/ has a README bullet
  2. every README bullet names a directory that exists (catches a skill renamed
     or removed with its entry left behind, which reads as present)

Exit: 0 roster matches disk · 1 drift · 2 could not run the check.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude"
SKILLS = PLUGIN / "skills"
README = PLUGIN / "README.md"

# The roster's bullet shape: two-space indent, backticked dir name, trailing slash.
BULLET = re.compile(r"^  - `([a-z0-9-]+)/`", re.M)


def main() -> int:
    if not SKILLS.is_dir():
        print(f"error: no skills directory at {SKILLS}", file=sys.stderr)
        return 2
    if not README.is_file():
        print(f"error: no README at {README}", file=sys.stderr)
        return 2

    on_disk = {p.name for p in SKILLS.iterdir() if p.is_dir()}
    if not on_disk:
        print(f"error: {SKILLS} holds no skill directories", file=sys.stderr)
        return 2

    listed = set(BULLET.findall(README.read_text()))
    if not listed:
        print("error: found no skill bullets in the README — has the roster's "
              "format changed? Expected lines like '  - `gate-potency/` — ...'",
              file=sys.stderr)
        return 2

    undocumented = sorted(on_disk - listed)
    phantom = sorted(listed - on_disk)

    if undocumented or phantom:
        print("the plugin README's skill roster has drifted from skills/:",
              file=sys.stderr)
        for name in undocumented:
            print(f"  - {name} is installed but has no README entry — a reader "
                  f"cannot learn it exists", file=sys.stderr)
        for name in phantom:
            print(f"  - {name} has a README entry but no directory — renamed or "
                  f"removed, and the entry reads as present", file=sys.stderr)
        return 1

    print(f"README roster matches skills/ on disk: {len(on_disk)} skills, "
          f"documented both ways")
    return 0


if __name__ == "__main__":
    sys.exit(main())
