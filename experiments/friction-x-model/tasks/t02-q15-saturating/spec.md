# t02: saturating Q15 fixed-point arithmetic

A Q15 value is a signed 16-bit integer `x` that stands for the real number
`x / 32768`, so the range is -1.0 to 32767/32768. All five operations below
saturate: a result outside the 16-bit range is clamped to -32768 or 32767.
None of them may overflow, trap or panic for any input.

Every behaviour below is numbered. The hidden tests check these sentences and
nothing else.

- **Q1. add(a, b)** is the exact integer sum `a + b`, clamped to
  [-32768, 32767].
- **Q2. sub(a, b)** is the exact integer difference `a - b`, clamped to
  [-32768, 32767].
- **Q3. mul(a, b)** takes the exact integer product `p = a * b`, rounds
  `p / 32768` to the nearest integer with ties going up (towards positive
  infinity), that is `floor((p + 16384) / 32768)`, and clamps the result to
  [-32768, 32767]. Example: `mul(-32768, -32768)` is 32767.
- **Q4. neg(a)** is `-a`, clamped: `neg(-32768)` is 32767.
- **Q5. abs(a)** is `|a|`, clamped: `abs(-32768)` is 32767.

## C

Implement the functions declared in `q15.h` (given, fixed: you may not change
it) in one file, `q15.c`, in C11. No standard library calls beyond
`<stdint.h>`.

## Rust

Implement the crate root `lib.rs` of a `no_std` library with this public API:

```rust
pub type Q15 = i16;
pub fn add(a: Q15, b: Q15) -> Q15; // Q1
pub fn sub(a: Q15, b: Q15) -> Q15; // Q2
pub fn mul(a: Q15, b: Q15) -> Q15; // Q3
pub fn neg(a: Q15) -> Q15;         // Q4
pub fn abs(a: Q15) -> Q15;         // Q5
```

No dependencies.
