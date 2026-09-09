# claude-tooling

Houses the `pulseengine-claude` Claude Code plugin (methodology reference memory + procedural skills for PulseEngine engineering work).

The marketplace manifest itself lives at the **repo root** in `pulseengine.eu/.claude-plugin/marketplace.json` (this is the convention Claude Code's marketplace loader expects — same shape as `anthropics/skills`). It points down into `claude-tooling/plugins/pulseengine-claude/` for the actual plugin contents.

See `plugins/pulseengine-claude/README.md` for plugin details.

## Install

See **[`plugins/pulseengine-claude/README.md`](plugins/pulseengine-claude/README.md)**
— it carries the install commands for Claude Code, GitHub Copilot CLI and
opencode, each verified against the tool.

Kept there rather than duplicated here: this file previously documented a
two-argument `marketplace add <name> <source>` form that current Claude Code
rejects with `✘ Invalid marketplace source format`, while the plugin README
already had the correct one-argument form. One of the two was fixed and the
other was not, which is the whole argument for a single source.

## Layout

```
pulseengine.eu/                          (repo root)
├── .claude-plugin/
│   └── marketplace.json                 ← marketplace manifest (must be at repo root)
└── claude-tooling/
    └── plugins/
        └── pulseengine-claude/
            ├── .claude-plugin/plugin.json
            ├── skills/                   ← one directory per skill, each a SKILL.md
            ├── memory/
            │   ├── pulseengine-philosophy.md
            │   └── pulseengine-toolchain.md
            ├── hooks/
            │   ├── hooks.json
            │   └── inject-pulseengine-memory.sh
            └── README.md
```

The marketplace manifest's `plugins[].source` is `./claude-tooling/plugins/pulseengine-claude` — a relative path from the marketplace root (= repo root, the directory containing `.claude-plugin/`).
