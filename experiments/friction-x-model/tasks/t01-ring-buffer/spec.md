# t01: bounded byte ring buffer

A first-in, first-out queue of bytes with a fixed capacity of 16. It never
allocates and never overwrites stored data.

Every behaviour below is numbered. The hidden tests check these sentences and
nothing else.

- **R1.** A new (C: freshly initialised) buffer is empty: its length is 0.
- **R2.** `push` stores one byte at the back and returns true, if fewer than
  16 bytes are stored.
- **R3.** `push` on a buffer holding 16 bytes returns false and changes
  nothing. The stored bytes are not overwritten.
- **R4.** `pop` removes and returns the byte at the front (the oldest stored
  byte). On an empty buffer it returns nothing and changes nothing.
- **R5.** `peek` returns the byte at the front without removing it. On an
  empty buffer it returns nothing.
- **R6.** Bytes come out in the order they went in, across any number of
  wrap-arounds of the internal storage.
- **R7.** The length is the number of stored bytes, from 0 to 16.
- **R8 (C only).** Any null pointer argument makes `rb_push`, `rb_pop` and
  `rb_peek` return false without writing anything; `rb_init(NULL)` does
  nothing; `rb_len(NULL)` returns 0. On a false return, `*out` is not written.

## C

Implement the functions declared in `rb.h` (given, fixed: you may not change
it) in one file, `rb.c`, in C11. No dynamic memory, no standard library calls
beyond `<stdbool.h>` and `<stdint.h>`.

## Rust

Implement the crate root `lib.rs` of a `no_std` library with this public API:

```rust
pub const CAPACITY: usize = 16;
pub struct RingBuffer { /* your fields */ }
impl RingBuffer {
    pub const fn new() -> Self;               // R1
    pub fn push(&mut self, value: u8) -> bool; // R2, R3
    pub fn pop(&mut self) -> Option<u8>;      // R4
    pub fn peek(&self) -> Option<u8>;         // R5
    pub fn len(&self) -> usize;               // R7
    pub fn is_empty(&self) -> bool;           // R7: len() == 0
}
```

No dependencies, no heap.
