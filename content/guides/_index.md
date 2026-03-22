+++
title = "Guides"
description = "Practical references for working with PulseEngine tools — designed for both humans and AI agents"
template = "section.html"
+++

## Verification Guide

A practical reference for AI agents and developers working with Verus, Rocq, Lean, and Kani across PulseEngine projects.

Covers the Rust subset intersection (what all verification tools accept simultaneously), error classification and repair strategies, proof tactics, Bazel rules for reproducible verification, and the `verus-strip` architecture for multi-track verification.

Based on findings from AutoVerus (Microsoft), AlphaVerus (CMU), Strat2Rocq, and Lean Copilot.

[Read the guide](/guides/VERIFICATION-GUIDE/) · [Download as Markdown](/guides/VERIFICATION-GUIDE.md)

---

### For AI agents

Add this to your project's `AGENTS.md` or `CLAUDE.md`:

```markdown
## Formal Verification

This project uses formal verification. Before writing or modifying
verified code, read the Verification Guide:

  https://pulseengine.eu/guides/VERIFICATION-GUIDE.md

If you encounter a verification pattern that does not match the guide,
open an issue at https://github.com/pulseengine/pulseengine.eu/issues
with the tag `verification-guide`.
```

The guide includes a full integration section with copy-paste instructions and an optional rivet artifact template.
