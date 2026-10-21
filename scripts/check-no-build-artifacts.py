#!/usr/bin/env python3
# rivet: verifies REQ-NO-BUILD-ARTIFACTS
"""Fail if git tracks a build artifact.

Found by external review of #232: `scripts/__pycache__/check-issue-classes.cpython-314.pyc`
rode along in that PR, and `scripts/__pycache__/fetch-layers.cpython-314.pyc`
had been tracked for longer. Ten gates ran green over both, because every one of
them asks whether a *claim* matches the tree and none asks what is IN the tree.
`.gitignore` had no Python entry at all.

A compiled `.pyc` is the worst case of the class: it is a stale copy of a script
a reviewer is reading, it is opaque in a diff, it changes with the interpreter
version rather than with intent, and on an import it can shadow the source it
was built from. Nothing here should ever ship one.

The list is deliberately extension- and directory-based rather than a
content-sniff for "binary": the site legitimately tracks fonts and images, so a
generic binary test would either flag those or need an allowlist long enough to
hide a real artifact in.

Exit: 0 clean · 1 tracked artifacts found · 2 could not run.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

BAD_DIRS = {"__pycache__", "node_modules", "target", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
BAD_SUFFIXES = {".pyc", ".pyo", ".pyd", ".o", ".a", ".so", ".dylib", ".dll", ".rlib", ".rmeta", ".class"}


def main() -> int:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"could not run: {e}", file=sys.stderr)
        return 2

    files = [f for f in out.split("\0") if f]
    if not files:
        print("could not run: git ls-files returned nothing", file=sys.stderr)
        return 2

    findings = []
    for f in files:
        parts = pathlib.PurePosixPath(f).parts
        hit = BAD_DIRS.intersection(parts)
        if hit:
            findings.append(f"{f} — inside {'/'.join(sorted(hit))}/")
            continue
        if pathlib.PurePosixPath(f).suffix.lower() in BAD_SUFFIXES:
            findings.append(f"{f} — compiled artifact")

    if findings:
        print(f"git tracks {len(findings)} build artifact(s):", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nRemove them (`git rm --cached <path>`) and cover them in .gitignore.\n"
            "A compiled copy of a script a reviewer is reading is worse than useless:\n"
            "it is opaque in a diff and can shadow the source on import.",
            file=sys.stderr,
        )
        return 1

    print(f"{len(files)} tracked files, no build artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
