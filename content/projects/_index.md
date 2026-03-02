+++
title = "Projects"
description = "The PulseEngine ecosystem — from core pipeline tools to build rules and developer infrastructure"
template = "section.html"
+++

## Core Pipeline

<div class="grid">

{{ project_card(name="Meld", desc="Statically fuses multiple WebAssembly components into a single core module. Import resolution, index-space merging, and canonical ABI adapter generation at build time.", url="https://github.com/pulseengine/meld", icon="🔗", badge="accent") }}

{{ project_card(name="Loom", desc="Twelve-pass WebAssembly optimization pipeline built on Cranelift's ISLE pattern-matching engine. Constant folding, strength reduction, CSE, inlining, dead code elimination.", url="https://github.com/pulseengine/loom", icon="🧵", badge="cyan") }}

{{ project_card(name="Synth", desc="Transcodes WebAssembly to native ARM for embedded Cortex-M targets through program synthesis — exploring equivalent native implementations, not just translating instructions.", url="https://github.com/pulseengine/synth", icon="⚡", badge="green") }}

{{ project_card(name="Kiln", desc="WebAssembly Component Model interpreter and runtime. Full WASI 0.2 support with no_std architecture for embedded, automotive, medical, and aerospace environments.", url="https://github.com/pulseengine/kiln", icon="🔥", badge="amber") }}

{{ project_card(name="Sigil", desc="Supply chain security — attestation, signing, and verification across every pipeline stage. Sigstore keyless signing, SLSA L4 provenance, TPM 2.0 support.", url="https://github.com/pulseengine/sigil", icon="🔏", badge="purple") }}

</div>

## Build & Verification

<div class="grid">

{{ project_card(name="rules_wasm_component", desc="Bazel rules for WebAssembly Component Model across Rust, Go, C++, and JavaScript.", url="https://github.com/pulseengine/rules_wasm_component", icon="📦", badge="accent") }}

{{ project_card(name="rules_rocq_rust", desc="Bazel rules for Rocq theorem proving and Rust formal verification with hermetic Nix toolchains.", url="https://github.com/pulseengine/rules_rocq_rust", icon="📐", badge="green") }}

{{ project_card(name="rules_verus", desc="Bazel rules for Verus Rust verification.", url="https://github.com/pulseengine/rules_verus", icon="✅", badge="green") }}

{{ project_card(name="rules_moonbit", desc="Bazel rules for MoonBit with hermetic toolchain support.", url="https://github.com/pulseengine/rules_moonbit", icon="🌙", badge="cyan") }}

</div>

## AI & MCP

<div class="grid">

{{ project_card(name="mcp", desc="Rust framework for building Model Context Protocol servers and clients, published to crates.io.", url="https://github.com/pulseengine/mcp", icon="🤖", badge="purple") }}

{{ project_card(name="wasi-mcp", desc="Proposed WASI API for Model Context Protocol, targeting WASI 0.3 standardization.", url="https://github.com/pulseengine/wasi-mcp", icon="🌐", badge="purple") }}

</div>

## Developer Tools

<div class="grid">

{{ project_card(name="thrum", desc="Gate-based pipeline orchestrator for autonomous AI-driven development.", url="https://github.com/pulseengine/thrum", icon="🎵", badge="amber") }}

{{ project_card(name="temper", desc="GitHub App that hardens repositories to organizational standards.", url="https://github.com/pulseengine/temper", icon="🛡️", badge="red") }}

{{ project_card(name="wasm-component-examples", desc="Working examples for Component Model development in C, C++, Go, and Rust.", url="https://github.com/pulseengine/wasm-component-examples", icon="📝", badge="accent") }}

{{ project_card(name="moonbit_checksum_updater", desc="Native MoonBit checksum management with GitHub API integration.", url="https://github.com/pulseengine/moonbit_checksum_updater", icon="🔢", badge="cyan") }}

</div>
