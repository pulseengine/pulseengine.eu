# t11: decimating fixed-point biquad (Q15 samples, Q14 coefficients)

A second-order IIR filter section in direct form I, followed by a decimator
that keeps every `M`-th filter output. Samples are Q15: a signed 16-bit
integer `x` stands for `x / 32768`. Coefficients are Q14: a signed 16-bit
integer `c` stands for `c / 16384`.

The filter holds five coefficients `b0, b1, b2, a1, a2`, the decimation
factor `M`, four state values (the previous two inputs `x1, x2` and the
previous two filter outputs `y1, y2`), a phase, and a saturation count.

Every behaviour below is numbered. The hidden tests check these sentences and
nothing else.

- **B1. Initialisation** (C: `bq_init`; Rust: `Biquad::new`) takes the five
  coefficients and `M`. `M` must be from 1 to 8; otherwise initialisation
  fails (C: returns false and changes nothing; Rust: returns `None`). On
  success it stores the coefficients and `M`, and sets `x1`, `x2`, `y1`,
  `y2`, the phase and the saturation count to 0.
- **B2. The accumulator.** Filtering one input sample `x` first computes
  `acc = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2`
  exactly, as a mathematical integer.
- **B3. Rounding.** It then divides `acc` by 16384 and rounds to the nearest
  integer. An exact tie (the remainder is exactly one half) rounds to the
  even integer.
- **B4. Saturation.** The rounded value is clamped to [-32768, 32767]. That
  clamped value is the filter output `y`. If clamping changed the value, the
  saturation count goes up by one. The count stops at 65535.
- **B5. State update.** After each sample, `x2` takes the old `x1`, `x1`
  takes `x`, `y2` takes the old `y1`, and `y1` takes `y`.
- **B6. Decimation.** After a sample is filtered: if the phase is `M - 1`,
  its output `y` is emitted and the phase becomes 0; otherwise nothing is
  emitted and the phase goes up by one.
- **B7. One sample** (C: `bq_step`; Rust: `step`) filters one sample. It
  returns the emitted output, if any (C: returns true and writes `*y`;
  returns false and does not write `*y` when nothing is emitted. Rust:
  `Some(y)` or `None`).
- **B8. Block processing** (`process`) takes the input samples in order and
  writes the emitted outputs to the start of the output, in order. Before
  taking each input sample it checks: if this sample would emit an output
  (the phase is `M - 1`) and the output is already full, it stops, and that
  sample and all later ones are not taken. It returns how many input
  samples it took and how many outputs it wrote. Output positions after the
  ones written are not changed. The phase and the state carry over to the
  next call. C: `out` may be the same array as `in`.
- **B9. Reset** sets `x1`, `x2`, `y1`, `y2` and the phase to 0. It keeps the
  coefficients and `M`, and it does not change the saturation count.
- **B10. The saturation count** query returns the count without changing
  anything.
- **B11 (C only).** A null pointer argument makes the function do nothing:
  `bq_init` with a null `f` or `c` returns false; `bq_step` with a null `f`
  or `y` returns false; `bq_process` with any null pointer returns 0 and sets
  nothing; `bq_reset(NULL)` does nothing; `bq_sat_count(NULL)` returns 0.

## C

Implement the functions declared in `bq.h` (given, fixed: you may not change
it) in one file, `bq.c`, in C11. No dynamic memory, no standard library calls
beyond `<stdbool.h>`, `<stddef.h>` and `<stdint.h>`. `bq.h` includes all
three. `bq_process` returns the number of input samples taken and writes the
number of outputs to `*produced`.

## Rust

Implement the crate root `lib.rs` of a `no_std` library with this public API:

```rust
pub const MAX_DECIMATION: u8 = 8;

#[derive(Clone, Copy)]
pub struct Coeffs {
    pub b0: i16,
    pub b1: i16,
    pub b2: i16,
    pub a1: i16,
    pub a2: i16,
}
pub struct Biquad { /* your fields */ }
impl Biquad {
    pub const fn new(c: Coeffs, m: u8) -> Option<Self>;                        // B1
    pub fn step(&mut self, x: i16) -> Option<i16>;                             // B2..B7
    pub fn process(&mut self, input: &[i16], output: &mut [i16]) -> (usize, usize); // B8: (taken, written)
    pub fn reset(&mut self);                                                   // B9
    pub fn sat_count(&self) -> u16;                                            // B10
}
```

No dependencies, no heap.
