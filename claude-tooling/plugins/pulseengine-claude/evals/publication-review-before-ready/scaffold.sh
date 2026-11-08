#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email eval@example.invalid && git config user.name eval
git remote add origin https://github.com/pulseengine/pulseengine.eu.git
mkdir -p content/blog
cat > content/blog/2026-12-01-numbers.md <<'MD'
+++
title = "Our gates caught 97% of defects"
date = 2026-12-01
draft = true
+++

In November our CI gates caught 97% of all defects before merge, and kiln is now production-ready.
MD
git add -A && git commit -qm init
