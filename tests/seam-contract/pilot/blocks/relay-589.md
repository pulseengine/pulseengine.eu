This is the machine-checked form of the contract in this issue, checked by `seam-check` (pulseengine-claude plugin, `seam-contract` skill); to change the contract, edit the block below.

```seam
format: 1
seam: relay-jess/estimator-identity
kind: identity
status: implemented
provider:
  repo: pulseengine/relay
  promise: "one published exporter per falcon-cascade interface; falcon-ekf is no longer published"
  guard: scripts/build-components.sh
consumers:
  - repo: pulseengine/jess
    binding: "the ekf-stage pin names falcon-iekf, never the legacy Mahony falcon-ekf"
    guard: tools/deps/check-estimator-identity.sh
interface:
  - kind: wit
    path: wit/falcon-cascade/cascade.wit
    package: "pulseengine:falcon-cascade"
    version: "0.12.0"
    interfaces: [ekf]
  - kind: file
    path: scripts/build-components.sh
    symbols:
      - "BUNDLE_DIRS=\"flight iekf attitude rate position falcon-mixer cascade\""
      - "GUARD (#589): no two PUBLISHED components may target the same world"
options:
  - id: stop-publishing
    summary: "stop publishing falcon-ekf"
  - id: distinct-identity
    summary: "give it a distinct interface and world, e.g. legacy-ekf"
  - id: annotate
    summary: "keep it, annotate the OCI artifact and WIT doc"
decisions:
  - summary: "stop publishing falcon-ekf: it is not the estimator falcon-core flies, and removing it removes the confusable pair"
    option: stop-publishing
    decided_by: "relay maintainer"
    date: "2026-10-21"
    ref: "relay#589 comment of 2026-10-21 17:12 UTC"
implemented_by: "relay#590, merged 2026-10-22; announced on jess#167 2026-10-21"
open_questions:
  - q: "confirm jess's ekf-stage pin binds to pulseengine:falcon-cascade/ekf@0.12.0 (relay main; this issue and the guard's header name @0.11.0)"
    owner: pulseengine/jess
```
