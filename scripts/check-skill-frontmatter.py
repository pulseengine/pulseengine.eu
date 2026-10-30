#!/usr/bin/env python3
# rivet: verifies REQ-SKILL-LOADS
# rivet: verifies REQ-SKILL-DESC-CAP
"""Fail if a SKILL.md's frontmatter breaks the limits agent runtimes enforce.

Why this exists: `claude plugin validate` checks the plugin and marketplace
MANIFESTS, not skill frontmatter, so nothing in this repo's tooling looked at
skill descriptions. Two of eighteen skills sat 11 and 35 characters over the
limit until GitHub Copilot CLI refused them:

    ✖ The following skills failed to load:
      • release-artifact-pipeline/SKILL.md: Skill description must be at most 1024 characters
      • traceability-audit/SKILL.md: Skill description must be at most 1024 characters

Note the verb: **failed to load**. An over-length description does not degrade
the skill, it removes it — the runtime lists the other sixteen and says nothing
where those two should be. That is the same silent-capability-loss shape as
pulseengine.eu#145, and it is why this is a gate rather than a style note.

Limits are the ones Copilot CLI enforces (verified against v1.0.83, which is
the strictest reader these skills are loaded by today):

    name         <= 64 chars, and must match the directory name
    description  <= 1024 chars, and must be present

Exit: 0 all skills load-able · 1 violations · 2 could not run the check.
"""

from __future__ import annotations

import pathlib
import re
import sys

try:
    import yaml
except ImportError:  # a gate that cannot parse must not pass
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "claude-tooling" / "plugins" / "pulseengine-claude" / "skills"

NAME_MAX = 64
DESC_MAX = 1024
DESC_CAP = 350   # ours, stricter than any runtime: see the description check below

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
FIELD = re.compile(r"^(name|description):\s*(.+?)(?=\n[a-z_]+:|\Z)", re.S | re.M)


def main() -> int:
    if not SKILLS.is_dir():
        print(f"error: {SKILLS} not found", file=sys.stderr)
        return 2

    problems: list[str] = []
    checked = 0

    for d in sorted(SKILLS.iterdir()):
        f = d / "SKILL.md"
        if not f.is_file():
            continue
        checked += 1
        text = f.read_text(encoding="utf-8", errors="replace")

        m = FRONTMATTER.match(text)
        if not m:
            problems.append(f"{d.name}: no YAML frontmatter block")
            continue

        # A strict YAML parser must accept the block. Claude Code reads it
        # leniently, but Copilot CLI uses a strict parser and refuses the whole
        # skill on e.g. an unquoted ": " inside a plain-scalar description
        # ("mapping values are not allowed"). A lenient regex read cannot see that.
        try:
            parsed = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            first = str(e).splitlines()[0]
            problems.append(
                f"{d.name}: frontmatter is not valid YAML ({first}) — "
                f"strict readers such as Copilot CLI REFUSE TO LOAD the skill; "
                f"quote the value or use a block scalar"
            )
            continue
        if not isinstance(parsed, dict):
            problems.append(f"{d.name}: frontmatter is not a YAML mapping")
            continue
        fields = {k: str(v).strip() for k, v in parsed.items()
                  if k in ("name", "description") and v is not None}

        name = fields.get("name")
        if not name:
            problems.append(f"{d.name}: frontmatter has no `name`")
        else:
            if len(name) > NAME_MAX:
                problems.append(f"{d.name}: name is {len(name)} chars (max {NAME_MAX})")
            if name != d.name:
                problems.append(f"{d.name}: name is {name!r}, must match the directory")

        desc = fields.get("description")
        if not desc:
            problems.append(f"{d.name}: frontmatter has no `description`")
        elif len(desc) > DESC_MAX:
            over = len(desc) - DESC_MAX
            problems.append(
                f"{d.name}: description is {len(desc)} chars, {over} over the "
                f"{DESC_MAX} limit — Copilot CLI REFUSES TO LOAD the skill"
            )
        else:
            # Our own cap (0.51.0, REQ-SKILL-DESC-CAP): every session AND every
            # subagent pays for every description; 24 of them came to ~20k
            # chars. Measured on the parsed YAML value, as the runtime sees it.
            value = parsed.get("description") if isinstance(parsed, dict) else desc
            n = len(value) if isinstance(value, str) else len(desc)
            if n > DESC_CAP:
                problems.append(
                    f"{d.name}: description is {n} chars, over the {DESC_CAP} cap — "
                    f"keep the trigger words, move the detail into the body"
                )

    if not checked:
        # A checker that examined nothing must not report success.
        print("error: found no SKILL.md files — the check examined nothing",
              file=sys.stderr)
        return 2

    print(f"{checked} skills checked, {len(problems)} violating "
          f"(name <= {NAME_MAX}, description <= {DESC_CAP}, runtime limit {DESC_MAX})")
    if not problems:
        return 0

    print("\nFrontmatter that will not load:", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
