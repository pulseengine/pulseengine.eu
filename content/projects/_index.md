+++
title = "Projects"
description = "The PulseEngine ecosystem — from core pipeline tools to build rules and developer infrastructure"
template = "section.html"
+++

## Core Pipeline

<div class="grid">

{{ project_card(name="meld", desc="Statically fuses multiple WebAssembly components into a single core module. Import resolution, index-space merging, and canonical ABI adapter generation at build time.", url="https://github.com/pulseengine/meld", icon="🔗", badge="accent", label="Fusion") }}

{{ project_card(name="loom", desc="Twelve-pass WebAssembly optimization pipeline built on Cranelift's ISLE pattern-matching engine. Constant folding, strength reduction, CSE, inlining, dead code elimination.", url="https://github.com/pulseengine/loom", icon="🧵", badge="cyan", label="Optimizer") }}

{{ project_card(name="synth", desc="Transcodes WebAssembly to native ARM for embedded Cortex-M targets through program synthesis — exploring equivalent native implementations, not just translating instructions.", url="https://github.com/pulseengine/synth", icon="⚡", badge="green", label="Transcoder") }}

{{ project_card(name="kiln", desc="WebAssembly Component Model interpreter and runtime. Full WASI 0.2 support with no_std architecture for embedded, automotive, medical, and aerospace environments.", url="https://github.com/pulseengine/kiln", icon="🔥", badge="amber", label="Runtime") }}

{{ project_card(name="sigil", desc="Supply chain security — attestation, signing, and verification across every pipeline stage. Sigstore keyless signing, SLSA L4 provenance, TPM 2.0 support.", url="https://github.com/pulseengine/sigil", icon="🔏", badge="purple", label="Security") }}

</div>

## Safety-Critical Systems

<div class="grid">

{{ project_card(name="gale", desc="Formally verified Rust port of Zephyr RTOS kernel primitives for ASIL-D. Dual-track verification with Verus and Rocq, 9 verified synchronization primitives.", url="https://github.com/pulseengine/gale", icon="🌬️", badge="green", label="RTOS") }}

{{ project_card(name="spar", desc="AADL v2.2 architecture analysis toolchain — parser, semantic model, 30+ pluggable analyses, and LSP server for safety-critical system design.", url="https://github.com/pulseengine/spar", icon="🏗️", badge="accent", label="Architecture") }}

{{ project_card(name="rivet", desc="Schema-driven SDLC artifact manager for requirements traceability and safety compliance. STPA, ASPICE, and cybersecurity schemas.", url="https://github.com/pulseengine/rivet", icon="📋", badge="amber", label="Traceability") }}

</div>

## Build & Verification

<div class="grid">

{{ project_card(name="rules_wasm_component", desc="Bazel rules for WebAssembly Component Model across Rust, Go, C++, and JavaScript.", url="https://github.com/pulseengine/rules_wasm_component", icon="📦", badge="accent", label="Bazel") }}

{{ project_card(name="rules_rocq_rust", desc="Bazel rules for Rocq theorem proving and Rust formal verification with hermetic Nix toolchains.", url="https://github.com/pulseengine/rules_rocq_rust", icon="📐", badge="green", label="Verification") }}

{{ project_card(name="rules_verus", desc="Bazel rules for Verus Rust verification.", url="https://github.com/pulseengine/rules_verus", icon="✅", badge="green", label="Verification") }}

{{ project_card(name="rules_moonbit", desc="Bazel rules for MoonBit with hermetic toolchain support.", url="https://github.com/pulseengine/rules_moonbit", icon="🌙", badge="cyan", label="Bazel") }}

{{ project_card(name="rules_lean", desc="Bazel rules for Lean 4 with Mathlib and Aeneas integration for formal verification.", url="https://github.com/pulseengine/rules_lean", icon="📏", badge="green", label="Verification") }}

</div>

## AI & MCP

<div class="grid">

{{ project_card(name="mcp", desc="Rust framework for building Model Context Protocol servers and clients, published to crates.io.", url="https://github.com/pulseengine/mcp", icon="🤖", badge="purple", label="Framework") }}

{{ project_card(name="template-mcp-server", desc="Scaffolding template for creating MCP servers in Rust with cross-platform npm distribution.", url="https://github.com/pulseengine/template-mcp-server", icon="🧩", badge="purple", label="Template") }}

{{ project_card(name="timedate-mcp", desc="MCP server for time, date, and timezone operations with full IANA timezone support.", url="https://github.com/pulseengine/timedate-mcp", icon="🕐", badge="purple", label="Server") }}

</div>

## Developer Tools

<div class="grid">

{{ project_card(name="temper", desc="GitHub App that hardens repositories to organizational standards.", url="https://github.com/pulseengine/temper", icon="🛡️", badge="red", label="Governance") }}

{{ project_card(name="wasm-component-examples", desc="Working examples for Component Model development in C, C++, Go, and Rust.", url="https://github.com/pulseengine/wasm-component-examples", icon="📝", badge="accent", label="Examples") }}

{{ project_card(name="bazel-file-ops-component", desc="WebAssembly-based cross-platform file operations for Bazel builds. Dual TinyGo and Rust implementations.", url="https://github.com/pulseengine/bazel-file-ops-component", icon="📂", badge="cyan", label="Build") }}

{{ project_card(name="moonbit_checksum_updater", desc="Native MoonBit checksum management with GitHub API integration.", url="https://github.com/pulseengine/moonbit_checksum_updater", icon="🔢", badge="cyan", label="Build") }}

</div>
