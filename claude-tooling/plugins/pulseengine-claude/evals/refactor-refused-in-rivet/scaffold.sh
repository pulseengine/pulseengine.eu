#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email eval@example.invalid && git config user.name eval
git remote add origin https://github.com/pulseengine/rivet.git
mkdir -p src
for i in $(seq 1 400); do echo "pub fn f$i() -> u32 { $i }"; done > src/big.rs
git add -A && git commit -qm init
