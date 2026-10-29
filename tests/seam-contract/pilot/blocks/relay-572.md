The HITL wire binding in this issue, as a machine-checked block (`seam-check.py`, pulseengine.eu plugin 0.48.0). Drafted from this issue and the binding v2 announcement on pulseengine/jess#167, up to 2026-10-29.

```seam
format: 1
seam: relay-jess/hitl-wire
kind: wire
status: implemented
provider:
  repo: pulseengine/relay
  promise: "the falcon-hitl binding's frame layout; a payload change bumps VERSION and is announced on jess#167 before a tag carries it"
consumers:
  - repo: pulseengine/jess
    binding: "a decoder for the sensor frame, whose offsets change with the battery element"
interface:
  - kind: file
    path: crates/falcon-hitl/src/wire.rs
    symbols:
      - "pub const VERSION: u8 = 2;"
      - "pub const SENSOR_PAYLOAD_LEN: usize = 81;"
  - kind: file
    path: docs/TRANSPORT-BINDING.md
    symbols:
      - "**Seam:** `pulseengine:falcon-cascade@0.12.0`"
decisions:
  - summary: "a battery element on the HITL wire with an explicit ABSENT validity bit, not a 0.0 sentinel; Kani harnesses updated and mutation-tested"
    decided_by: "relay maintainer"
    date: "2026-10-21"
    ref: "relay#572 comment of 2026-10-21 18:16 UTC"
implemented_by: "relay#614 (binding v2), merged to main 2026-10-28; no tag carries it yet"
open_questions:
  - q: "BindingHost accepts replies whose seq it never sent: the echo rule in the binding doc is not enforced in on_reply (jess probe, jess#167 2026-10-28 23:48 UTC)"
    owner: pulseengine/relay
notes: "This issue's body pins 76 B and @0.11.0; VERSION 2, 81 B and @0.12.0 come from the jess#167 announcement of 2026-10-28 and relay main. jess has no decoder for this wire yet (jess#167, 2026-10-28), so no consumer-side guard can be named."
```
