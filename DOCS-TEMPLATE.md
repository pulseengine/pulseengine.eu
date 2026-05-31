# Documentation Template — per tool

Every tool in PulseEngine follows this structure. Sections 1-5 are the front
door (user-facing). Section 6 is reference. Section 7 is internals.

## 1. What it does
One paragraph. What goes in, what comes out. No jargon.

## 2. When to use it
Which problem does this solve? Who is this for?
"Use this when you need to..."

## 3. Getting started
- Prerequisites
- Install (every method: cargo, binary, bazel)
- Minimal config
- First useful command (copy-paste)
- Expected output
- "What just happened" (one paragraph)

## 4. How it connects
- What feeds into this tool (upstream)
- What this tool produces for others (downstream)
- Concrete example from the ecosystem

## 5. Limitations
- What doesn't work yet
- Known gaps
- What's planned

## 6. Reference
- CLI commands (every subcommand, every flag)
- Configuration format
- Schemas / analysis passes / supported standards (tool-specific)

## 7. Internals
- Architecture
- Proof status
- Safety analysis (STPA)
- Design decisions
(This is for contributors and evaluators, not users)
