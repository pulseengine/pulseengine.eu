#!/usr/bin/env python3
"""Drop report versions whose entry file was not actually deployed.

`fetch-reports` records every release that carried a report asset. It does not
check that the extracted bundle contains the file the website links to, and the
bundles are not uniform:

  * witness ships an HTML suite at mcdc/verdict-evidence/suite-index.html, but
    only from 0.10 onwards. Six older versions in the index have no HTML at all.
  * scry's mcdc bundle contains no HTML in any version — coverage-report.json,
    coverage-report.txt, README.txt and two directories. Every scry link on the
    reports page was a 404, including "latest", because the page assumed
    witness's layout for every project of kind "mcdc".

The page offers "all N versions". This makes that claim true by construction:
after this runs, every version left in index.json has its entry file on disk, so
the template can link all of them without probing anything.

Entry paths come from reports.toml, which is also where fetch-reports reads its
project list, so the two cannot drift apart.

Run after fetch-reports and before `zola build`.

Exit: 0 index rewritten (or nothing to do) · 2 inputs missing.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "reports.toml"
INDEX = ROOT / "static" / "reports" / "index.json"
REPORTS = ROOT / "static" / "reports"

DEFAULT_ENTRY = {
    "compliance": "compliance/index.html",
    "mcdc": "mcdc/verdict-evidence/suite-index.html",
}


def entry_for(name: str, cfg: dict) -> str:
    project = cfg.get("projects", {}).get(name, {})
    if project.get("entry"):
        return project["entry"]
    return DEFAULT_ENTRY.get(project.get("kind", "compliance"), DEFAULT_ENTRY["compliance"])


def main() -> int:
    if not CONFIG.is_file() or not INDEX.is_file():
        print(f"error: expected {CONFIG.name} and {INDEX.relative_to(ROOT)}", file=sys.stderr)
        return 2

    cfg = tomllib.loads(CONFIG.read_text())
    index = json.loads(INDEX.read_text())
    projects = index.get("projects") or {}
    if not projects:
        print("reports index is empty — nothing to prune")
        return 0

    total_before = total_after = 0
    for name, project in projects.items():
        entry = entry_for(name, cfg)
        versions = project.get("versions", [])
        total_before += len(versions)
        kept = [v for v in versions if (REPORTS / name / v / entry).is_file()]
        dropped = [v for v in versions if v not in kept]
        total_after += len(kept)

        if dropped:
            print(f"  {name}: dropped {len(dropped)} of {len(versions)} "
                  f"(no {entry}): {', '.join(dropped[:6])}"
                  f"{' …' if len(dropped) > 6 else ''}")

        project["versions"] = kept
        project["entry"] = entry
        if kept:
            project["latest"] = kept[0]
            seen, display = set(), []
            for v in kept:                      # already sorted descending
                key = tuple(v.split(".")[:2])
                if key not in seen:
                    seen.add(key)
                    display.append(v)
            project["display_versions"] = display
        else:
            project["display_versions"] = []
            print(f"  {name}: NO version has {entry} — the card will be empty",
                  file=sys.stderr)

    INDEX.write_text(json.dumps(index, indent=2) + "\n")
    print(f"{total_after} of {total_before} report versions have their entry file "
          f"on disk; index.json rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
