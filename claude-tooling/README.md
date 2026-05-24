# claude-tooling

Houses the `pulseengine-claude` Claude Code plugin (methodology reference memory + procedural skills for PulseEngine engineering work).

The marketplace manifest itself lives at the **repo root** in `pulseengine.eu/.claude-plugin/marketplace.json` (this is the convention Claude Code's marketplace loader expects — same shape as `anthropics/skills`). It points down into `claude-tooling/plugins/pulseengine-claude/` for the actual plugin contents.

See `plugins/pulseengine-claude/README.md` for plugin details.

## Install (same flow as any other Claude Code marketplace)

In Claude Code, run:

```
/plugin marketplace add pulseengine-eu github.com/pulseengine/pulseengine.eu
/plugin install pulseengine-claude@pulseengine-eu
```

Or the CLI equivalent:

```sh
claude plugin marketplace add pulseengine-eu github.com/pulseengine/pulseengine.eu
claude plugin install pulseengine-claude@pulseengine-eu
```

## Layout

```
pulseengine.eu/                          (repo root)
├── .claude-plugin/
│   └── marketplace.json                 ← marketplace manifest (must be at repo root)
└── claude-tooling/
    └── plugins/
        └── pulseengine-claude/
            ├── .claude-plugin/plugin.json
            ├── skills/
            │   ├── clean-room-verification/SKILL.md
            │   ├── release-execution/SKILL.md
            │   ├── oracle-gate-a-change/SKILL.md
            │   └── pulseengine-feature-loop/SKILL.md
            ├── memory/
            │   ├── pulseengine-philosophy.md
            │   └── pulseengine-toolchain.md
            ├── hooks/
            │   ├── hooks.json
            │   └── inject-pulseengine-memory.sh
            └── README.md
```

The marketplace manifest's `plugins[].source` is `./claude-tooling/plugins/pulseengine-claude` — a relative path from the marketplace root (= repo root, the directory containing `.claude-plugin/`).
