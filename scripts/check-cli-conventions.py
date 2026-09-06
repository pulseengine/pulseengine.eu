#!/usr/bin/env python3
"""Check the tools in a pinned varve layer against pulseengine-cli-conventions.

Rule 1  `--version` exits 0 and prints `<binary-name> <semver>`.
Rule 1b the semver equals the version the SIGNED LAYER records for that tool.
Rule 2  an unknown flag exits 2.

Why the layer is the oracle rather than a hardcoded list: `varve inspect`
reports, per tool, the version the signed layer vouches for. So rule 1 can be
checked as *"the binary agrees with its own signed provenance"* rather than the
weaker *"the binary prints something semver-shaped"*. A tool that prints a
different version than the layer it shipped in is a provenance defect, not a
formatting one.

Usage:
    scripts/check-cli-conventions.py [--project DIR]

DIR must contain (or sit under) a varve.toml. Without a pin every shim refuses
with "no varve.toml found", which produces nine identical failures that look
like data and are not — this script detects that case and says so instead of
reporting nine violations.

Exit: 0 all conform · 1 violations found · 2 could not run the check at all.
"""

from __future__ import annotations

import argparse
import platform
import re
import shutil
import subprocess
import sys

SEMVER = re.compile(r"^(\S+)\s+v?(\d+\.\d+\.\d+)")
NO_PIN = "no varve.toml found"


def host_platform() -> str:
    m = {"arm64": "aarch64", "x86_64": "x86_64"}.get(platform.machine(), platform.machine())
    o = {"Darwin": "apple-darwin", "Linux": "unknown-linux-gnu"}.get(platform.system(), "")
    return f"{m}-{o}"


def layer_tools(cwd: str) -> list[tuple[str, str]]:
    """(binary, version) the signed layer records for this host platform."""
    p = subprocess.run(["varve", "inspect"], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        print(f"error: `varve inspect` failed in {cwd}:\n{p.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    host, out = host_platform(), []
    for line in p.stdout.splitlines():
        f = line.split()
        # DISPATCHED/HELD  tool  <name>  <version>  <platform>  <layer>
        if len(f) >= 6 and f[1] == "tool" and f[4] == host:
            out.append((f[2], f[3]))
    return sorted(set(out))


def run(cwd: str, args: list[str]) -> tuple[int, str]:
    p = subprocess.run(["varve", "run", "--", *args], cwd=cwd, capture_output=True, text=True)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=".", help="directory with a varve.toml pin")
    a = ap.parse_args()

    if not shutil.which("varve"):
        print("error: varve not on PATH", file=sys.stderr)
        return 2

    tools = layer_tools(a.project)
    if not tools:
        # A checker that examined nothing must not report success.
        print(f"error: no tools found for platform {host_platform()} — "
              "the check examined nothing", file=sys.stderr)
        return 2

    rows, violations = [], 0
    for binary, want in tools:
        vexit, vout = run(a.project, [binary, "--version"])
        first = vout.splitlines()[0] if vout else ""

        if NO_PIN in vout:
            print(f"error: {a.project} has no varve.toml pin — every shim refuses, "
                  "which is varve working correctly, not a conventions failure.",
                  file=sys.stderr)
            return 2

        problems = []
        if vexit != 0:
            problems.append(f"--version exit {vexit}")
        m = SEMVER.match(first)
        if not m:
            problems.append("no `<name> <semver>` line")
        else:
            if m.group(1) != binary:
                problems.append(f"reports {m.group(1)!r}, binary is {binary!r}")
            if m.group(2) != want:
                problems.append(f"reports {m.group(2)}, layer records {want}")

        fexit, _ = run(a.project, [binary, "--definitely-not-a-real-flag"])
        if fexit != 2:
            problems.append(f"unknown flag exit {fexit} (want 2)")

        violations += bool(problems)
        rows.append((binary, want, first[:38], problems))

    w = max(len(r[0]) for r in rows)
    print(f"{'tool':<{w}}  {'layer':<8}  {'--version says':<38}  verdict")
    print("-" * (w + 62))
    for binary, want, first, problems in rows:
        verdict = "ok" if not problems else "; ".join(problems)
        print(f"{binary:<{w}}  {want:<8}  {first:<38}  {verdict}")

    print(f"\n{len(rows)} tools checked, {violations} violating "
          f"(platform {host_platform()})")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
