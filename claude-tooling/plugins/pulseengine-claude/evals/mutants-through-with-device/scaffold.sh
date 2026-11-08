#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email eval@example.invalid && git config user.name eval
git remote add origin https://github.com/pulseengine/example.git
cat > Cargo.toml <<'T'
[package]
name = "ex"
version = "0.1.0"
edition = "2021"
T
mkdir -p src && echo 'pub fn add(a: u32, b: u32) -> u32 { a + b }' > src/lib.rs
git add -A && git commit -qm init
