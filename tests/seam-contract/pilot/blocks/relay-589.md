The interface-identity contract in this issue, as a machine-checked block (`seam-check.py`, pulseengine.eu plugin 0.48.0). Drafted from this issue and the announcement on pulseengine/jess#167, up to 2026-10-29. The version is the one this issue names.

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
    version: "0.11.0"
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
```
