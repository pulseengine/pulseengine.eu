+++
title = "spar"
description = "Validate your system architecture before you write code"
template = "docs-section.html"
sort_by = "weight"
weight = 20
+++

## What it does

spar parses AADL v2.3 and SysML v2 system architecture models, runs pluggable analyses (scheduling, latency, resource budgets, connectivity, safety), and generates code artifacts (WIT interfaces, Rust skeletons, rivet docs, test harnesses). It also includes a deployment solver and SVG architecture rendering.

**Input:** `.aadl` or SysML v2 model files.
**Output:** analysis results (SARIF/JSON/text), SVG diagrams, generated WIT/Rust code, rivet artifacts.

## When to use it

Use spar when you need to validate that your system architecture is feasible before writing implementation code. Does the scheduling work? Do the resource budgets fit? Are all ports connected? Are latency bounds met?

Also use it to generate the code skeletons and WIT interfaces that feed into the build pipeline — architecture drives implementation, not the other way around.

## Getting started

```sh
# Install
cargo install spar

# Parse and analyze
spar parse system.aadl --tree
spar analyze --root Pkg::System.Impl system.aadl

# Generate architecture diagram
spar render --root Pkg::System.Impl -o arch.svg system.aadl

# Generate code from the model
spar codegen --root Pkg::System.Impl --wit --rust system.aadl
```

VS Code: install the [spar-aadl extension](https://marketplace.visualstudio.com/items?itemName=pulseengine.spar-aadl) for live diagnostics and architecture diagrams.

## How it connects

- **Upstream:** validates architecture BEFORE the build pipeline runs
- **rules_wasm_component:** spar-generated WIT/Rust feeds into Bazel component builds
- **meld:** fuses the components spar's architecture defined
- **rivet:** generates rivet artifacts for architecture traceability
- **Browser:** compiles to a WebAssembly component for in-browser analysis

## Limitations

- AADL v2.3 compliance ~95% for parsing, ~85% instance model, ~75% properties/modes
- SysML v2 support is newer and less complete than AADL
- Deployment solver uses heuristic bin-packing; MILP optimization in development

## Reference

- [Introduction](/docs/spar/introduction/)
- [Getting Started (full)](/docs/spar/getting-started/)
- [AADL Compliance](/docs/spar/compliance/)
