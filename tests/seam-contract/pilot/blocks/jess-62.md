The HAL contract in this thread, as a machine-checked block (`seam-check.py`, pulseengine.eu plugin 0.48.0). Drafted from this issue's body and comments up to 2026-10-29.

```seam
format: 1
seam: relay-jess/hal
kind: hal
status: implemented
provider:
  repo: pulseengine/relay
  promise: "the peripheral seam traits in relay-hal (on embedded-hal-async and embedded-io-async, plus PwmOut, AdcIn, CanBus and Presence), not changed without telling jess"
consumers:
  - repo: pulseengine/jess
    binding: "the binding of those traits to i.MX RT1176 silicon: BSP, the embedded-hal-async HAL component, on-silicon validation"
interface:
  - kind: file
    path: crates/relay-hal/src/lib.rs
    symbols:
      - "pub trait PwmOut"
      - "pub trait AdcIn"
      - "pub trait CanBus"
      - "pub struct Presence<const N: usize>"
decisions:
  - summary: "anchor relay-hal on embedded-hal-async and embedded-io-async, transaction-level and async-first; custom traits only where no standard exists (frame-based PwmOut, AdcIn, Presence/health)"
    decided_by: "relay and jess, both acked in this thread"
    date: "2026-06-20"
    ref: "jess#62 comments of 2026-06-20 05:40 and 05:51 UTC"
implemented_by: "relay falcon-v1.81.0 to falcon-v1.85.0; jess acked the complete surface on 2026-06-21"
notes: "The body's seam inventory (RegBus, SerialBus) is superseded by the 2026-06-20 decision. relay-hal carries no version this thread names, so the block pins trait names, not a version. No consumer-side guard is named."
```
