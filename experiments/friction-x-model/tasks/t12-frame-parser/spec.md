# t12: byte-at-a-time receiver for an untrusted framed link

A receiver for frames from an untrusted serial link. It is fed one byte at a
time, as from a UART interrupt, and keeps its state between calls.

## The link format

- `FLAG` (0x7E) separates frames. `ESC` (0x7D) escapes the byte after it.
- The bytes between two flags, after unescaping, are the frame's **content**:
  one address byte, then the payload (0 to 32 bytes, `MAX_PAYLOAD`), then two
  CRC bytes, most significant byte first.
- The CRC is CRC-16/CCITT-FALSE over the address and the payload:
  polynomial 0x1021, initial value 0xFFFF, most significant bit first, no
  reflection of input or output, no final XOR. Its check value is 0x29B1
  for the nine ASCII bytes `123456789`. Over zero bytes it is 0xFFFF.
- The receiver has its own address. It accepts frames sent to its own
  address or to `BROADCAST` (0xFF).

## The receiver

Each byte pushed returns one event: `NOTHING`, `FRAME`, `RUNT`, `BAD_CRC`,
`FILTERED`, `ABORT` or `OVERRUN` (C: `FR_EV_NOTHING` and so on; Rust:
`Event::Nothing`, `Event::Frame` and so on). A byte returns `NOTHING` unless
a sentence below says otherwise. The receiver also keeps six counts:
`frames`, `runts`, `crc_errors`, `filtered`, `aborts` and `overruns`.

Every behaviour below is numbered. The hidden tests check these sentences and
nothing else.

- **H1. A new receiver** (C: `fr_rx_init`; Rust: `Receiver::new`) stores its
  address, sets every count to 0, has no accepted frame (its payload is
  empty), and is **hunting**.
- **H2. Hunting.** While hunting, every byte except `FLAG` is ignored. A
  `FLAG` ends hunting and opens a frame with no content.
- **H3. Content.** In an open frame, a byte that is neither `FLAG` nor `ESC`
  is a content byte. `ESC` is not a content byte: the byte after it, XOR
  0x20, is a content byte, whatever that byte is, except `FLAG` (see H6).
- **H4. Overrun.** A frame holds at most 35 content bytes. The content byte
  that would be the 36th instead discards the frame, returns `OVERRUN`, adds
  one to `overruns`, and makes the receiver hunt (H2).
- **H5. Closing flag.** A `FLAG` in an open frame, not right after `ESC`,
  ends that frame and at once opens a new one with no content. The ended
  frame decides what this `FLAG` returns, by the first rule that applies:
  1. no content bytes: `NOTHING`;
  2. 1 or 2 content bytes: `RUNT`, and `runts` goes up by one;
  3. the CRC over all content bytes except the last two differs from the
     last two (most significant first): `BAD_CRC`, and `crc_errors` goes up
     by one;
  4. the address (the first content byte) is neither the receiver's address
     nor `BROADCAST`: `FILTERED`, and `filtered` goes up by one;
  5. otherwise `FRAME`: `frames` goes up by one, and the payload (the
     content without the address and the two CRC bytes) becomes the
     accepted frame.
- **H6. Abort.** In an open frame, `ESC` followed by `FLAG` discards the
  frame. That `FLAG` returns `ABORT`, adds one to `aborts`, and opens a new
  frame with no content.
- **H7. The accepted frame** (C: `fr_rx_frame`; Rust: `frame`) is the
  payload of the last frame that returned `FRAME`. It stays the same until
  the next `FRAME`.
- **H8. Counts** (C: `fr_rx_counts`; Rust: `counts`) returns the six counts.
  Each count stops at 65535.
- **H9. crc16** returns the CRC above over the given bytes.
- **H10. encode** writes one frame for the given address and payload to the
  start of the output: `FLAG`, then the content (address, payload, CRC most
  significant byte first), then `FLAG`. Every content byte that is `FLAG` or
  `ESC` is sent as `ESC` followed by the byte XOR 0x20; every other byte is
  sent as it is. It returns the number of bytes written. It returns 0 and
  writes nothing if the payload is longer than 32 bytes or the output is
  too short for the whole frame.
- **H11 (C only).** A null pointer argument makes the function do nothing:
  `fr_rx_init(NULL, a)` does nothing; `fr_rx_push(NULL, b)` returns
  `FR_EV_NOTHING`; `fr_rx_frame` with a null `rx` returns NULL and, if `len`
  is not null, sets `*len` to 0; `fr_rx_frame` with a null `len` returns
  NULL; `fr_rx_counts(NULL)` returns all counts 0; `fr_crc16(NULL, n)`
  returns 0xFFFF; `fr_encode` returns 0 and writes nothing if `out` is null,
  or if `payload` is null and `len` is not 0.

## C

Implement the functions declared in `fr.h` (given, fixed: you may not change
it) in one file, `fr.c`, in C11. No dynamic memory, no standard library calls
beyond `<stddef.h>` and `<stdint.h>`. `fr.h` includes both. `fr_rx_frame`
returns a pointer to the accepted payload inside the receiver and writes its
length to `*len`.

## Rust

Implement the crate root `lib.rs` of a `no_std` library with this public API:

```rust
pub const FLAG: u8 = 0x7E;
pub const ESC: u8 = 0x7D;
pub const BROADCAST: u8 = 0xFF;
pub const MAX_PAYLOAD: usize = 32;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Event { Nothing, Frame, Runt, BadCrc, Filtered, Abort, Overrun }

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Counts {
    pub frames: u16,
    pub runts: u16,
    pub crc_errors: u16,
    pub filtered: u16,
    pub aborts: u16,
    pub overruns: u16,
}

pub struct Receiver { /* your fields */ }
impl Receiver {
    pub const fn new(addr: u8) -> Self;          // H1
    pub fn push(&mut self, byte: u8) -> Event;   // H2..H6
    pub fn frame(&self) -> &[u8];                // H7
    pub fn counts(&self) -> Counts;              // H8
}

pub fn crc16(data: &[u8]) -> u16;                             // H9
pub fn encode(addr: u8, payload: &[u8], out: &mut [u8]) -> usize; // H10
```

No dependencies, no heap.
