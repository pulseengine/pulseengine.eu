#!/usr/bin/env python3
# rivet: verifies REQ-PLUGIN-VERSION-CURRENT
"""Fail if the plugin changed since the commit that last set its version.

`pulseengine-claude` is installed by version. The plugin cache keys on
plugin.json's version, so two different trees carrying the same version are
indistinguishable to anyone who installed them — the second one silently never
arrives for a user who already has the first.

Nothing enforced the bump. check-plugin-manifest.py checks that the marketplace
and the plugin agree with each other, which they can do while both being stale.
Measured 2026-10-02: v0.32.0 was set in 6a5ab57, and the plugin's own content
changed afterwards in 9221908 (repo-hygiene 0.2.0 -> 0.3.0) with no bump.

The rule: any change under the plugin directory must be accompanied by, or
followed by, a change to plugin.json's version.

Exit: 0 version is current · 1 the plugin moved without a bump · 2 cannot check.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude"
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"


def git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(ROOT), *args],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return out.stdout.strip()


def main() -> int:
    if not MANIFEST.is_file():
        print(f"error: expected {MANIFEST.relative_to(ROOT)}", file=sys.stderr)
        return 2
    try:
        version = json.loads(MANIFEST.read_text())["version"]
        # the newest commit that changed the version LINE, not the file
        blame = git("log", "-1", "--format=%H", "-S", f'"version": "{version}"',
                    "--", str(MANIFEST.relative_to(ROOT)))
        if not blame:
            # The bump may be in flight: the new version is in the tree but not
            # yet committed, so `log -S` cannot see it. That is the normal state
            # of the commit that does the bumping, and must not read as an error.
            pending = git("status", "--porcelain", "--",
                          str(MANIFEST.relative_to(ROOT)))
            if pending:
                print(f"plugin v{version} is staged or unstaged in the working "
                      f"tree — the bump is in flight, nothing to check yet")
                return 0
            print(f"error: no commit introduces version {version} and the "
                  f"manifest is clean — shallow clone? the check cannot tell "
                  f"you anything", file=sys.stderr)
            return 2
        changed = git("diff", "--name-only", f"{blame}..HEAD", "--",
                      str(PLUGIN.relative_to(ROOT)))
    except RuntimeError as e:
        print(f"error: git failed: {e}", file=sys.stderr)
        return 2

    moved = [f for f in changed.splitlines() if f.strip()
             and not f.endswith(".claude-plugin/plugin.json")]
    print(f"plugin v{version} set in {blame[:7]}; "
          f"{len(moved)} plugin file(s) changed since")
    if not moved:
        return 0

    print(f"\nThe plugin changed after v{version} was set, so two different "
          f"trees now carry that version:", file=sys.stderr)
    for f in moved[:12]:
        print(f"  {f}", file=sys.stderr)
    if len(moved) > 12:
        print(f"  … and {len(moved) - 12} more", file=sys.stderr)
    print(f"\nBump the version in {MANIFEST.relative_to(ROOT)} and in "
          f".claude-plugin/marketplace.json (check-plugin-manifest keeps them "
          f"in step).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
