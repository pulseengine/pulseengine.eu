#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email eval@example.invalid && git config user.name eval
git remote add origin https://github.com/pulseengine/example.git
mkdir -p artifacts
cat > rivet.yaml <<'Y'
project: example
sources: [artifacts]
Y
cat > artifacts/reqs.yaml <<'Y'
artifacts:
  - id: REQ-001
    type: requirement
    title: Parse the header
    status: verified
  - id: REQ-002
    type: requirement
    title: Reject a truncated frame
    status: implemented
Y
git add -A && git commit -qm init
