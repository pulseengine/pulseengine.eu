The consumption contract in this thread, as a machine-checked block (`seam-check.py`, pulseengine.eu plugin 0.48.0). Drafted from this issue's body and comments up to 2026-10-29.

```seam
format: 1
seam: relay-jess/consumption
kind: consumption
status: decided
provider:
  repo: pulseengine/relay
  promise: "the published flight components and their WIT, pulseengine:falcon-cascade; a seam change is announced in this issue before a tag carries it"
consumers:
  - repo: pulseengine/jess
    binding: "fusing, lowering and signing per core; supplying the calibration; reading the seam's units as documented"
    guard:
      - tools/abi/check-observer-layout.py
      - tools/publish-gate/check-consumable.sh
interface:
  - kind: wit
    path: wit/falcon-cascade/cascade.wit
    package: "pulseengine:falcon-cascade"
    version: "0.12.0"
    interfaces: [controller, observer, pilot]
options:
  - id: step
    summary: "synchronous per-cycle step(sensor-sample) -> actuator-cmd, mirroring FlightCore::step"
  - id: stream
    summary: "P3 stream<sensor-sample> -> stream<actuator-cmd>"
decisions:
  - summary: "both, layered: one synchronous step per partition window at the core boundary, stream<T> composition inside each bundle; fine-grained components, jess fuses, lowers and signs per core"
    decided_by: "jess proposed, relay accepted"
    date: "2026-07-23"
    ref: "jess#167 comments of 2026-07-23 19:50 and 20:24 UTC"
  - summary: "command channel: pilot.command(...) as a third interface (option c)"
    decided_by: "jess"
    date: "2026-10-15"
    ref: "jess#167 comment of 2026-10-15 09:42 UTC"
  - summary: "calibration entry point: configure-calibration on the pilot interface (option i)"
    decided_by: "relay maintainer"
    date: "2026-10-21"
    ref: "relay#586; jess#167 comment of 2026-10-21 18:17 UTC"
  - summary: "calibration fields: the full 3x3 mag matrix (mag-offdiag), and pilot's sensor-calibration carries residual, board-level terms only"
    decided_by: "relay proposed in relay#611, jess accepted"
    date: "2026-10-28"
    ref: "jess#167 comment of 2026-10-28 15:00 UTC"
open_questions:
  - q: "battery-v: stays in sensor-frame, or moves to pilot as a setter (asked 2026-10-21)"
    owner: pulseengine/jess
  - q: "confirm jess's decoder reads cruise-alt as metres AGL, positive-up, not NED (asked 2026-10-21)"
    owner: pulseengine/jess
  - q: "relay#575 split: does the supervisor run in the M7 orchestrator, or as its own component for the F100 (asked 2026-10-21)"
    owner: pulseengine/jess
  - q: "a per-instance calibration entry point on relay's decode/voting stage, keyed by IMU instance (follow-up, not in relay#611)"
    owner: pulseengine/relay
notes: "@0.12.0 is on relay main and in no tag yet (latest falcon-v1.140.0). The issue body's five questions were answered on 2026-07-23; the options above are its question 2."
```
