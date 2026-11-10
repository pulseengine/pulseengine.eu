#!/usr/bin/env python3
# rivet: verifies REQ-PLUGIN-NO-HOME-PATH
"""Fail if a file the plugin ships names an absolute home-directory path.

`claude-tooling/plugins/pulseengine-claude/` is installed on other people's
machines. A path such as the author's own home directory or an external-volume
mount, written into a memory file or a skill, ships with it: it discloses the
author's account name and layout, and it tells every reader's agent to look for
a directory that does not exist on their machine. pulseengine-toolchain.md
carried one through 0.51.0 (found 2026-11-04), in a sentence that also spelled
the same path again in Claude Code's dash-encoded project-directory form.

The client-side private-host-guard hook asks before such a path is written, but
asks, can be answered yes, and never sees a file that was already there. This
is the check that fails the build.

Matched (a name character must follow, so documentation that writes the
placeholder `/Volumes/<name>` or a regex whose text begins `/Volumes/[` passes):
  /Users/<name>   /Volumes/<name>   /home/<name>   -Users-<name>
The last is the same home directory with `/` turned into `-`, as Claude Code
names its per-project directories. `/System/Volumes/...` is macOS's own mount
point for the Data volume, not a home directory, and is not matched.

Scope: every tracked or untracked-not-ignored file under the plugin directory
that decodes as UTF-8. Use a repo-relative description instead ("the sibling
checkout of <repo>").

Exit: 0 clean - 1 a home path found - 2 could not run.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = "claude-tooling/plugins"

# `(?<!/System)`: macOS mounts its writable Data volume at /System/Volumes/Data,
# a fixed system path that names no user (the disk-pressure hook measures it).
PATTERN = re.compile(r"(?:/Users/|(?<!/System)/Volumes/|/home/|-Users-)[A-Za-z0-9_]")


def main() -> int:
    try:
        out = ""
        for extra in ([], ["--others", "--exclude-standard"]):
            out += subprocess.run(
                ["git", "-C", str(ROOT), "ls-files", "-z", *extra, "--", PLUGINS],
                capture_output=True, text=True, check=True,
            ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"could not run: {e}", file=sys.stderr)
        return 2

    files = sorted({f for f in out.split("\0") if f})
    if not files:
        print(f"could not run: no files under {PLUGINS}", file=sys.stderr)
        return 2

    findings = []
    scanned = 0
    for f in files:
        try:
            text = (ROOT / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or vanished; the plugin ships text
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            m = PATTERN.search(line)
            if m:
                findings.append(f"{f}:{n}: {m.group(0)[:-1]}...")

    if findings:
        print("absolute home-directory path in a shipped plugin file:", file=sys.stderr)
        for x in findings[:30]:
            print(f"  {x}", file=sys.stderr)
        if len(findings) > 30:
            print(f"  ... and {len(findings) - 30} more", file=sys.stderr)
        print("Describe the location relative to the workspace instead.",
              file=sys.stderr)
        return 1

    print(f"{scanned} plugin file(s) scanned, no home-directory path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
