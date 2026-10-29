// Fixed Kani harnesses for t01 (F4). The agent sees this file and may not edit
// it. The harness appends `#[cfg(kani)] mod fxm_kani_proofs;` to the crate
// root, so `super::*` is the agent's crate. Bounded model checking within
// these bounds only.
use super::*;

/// No operation sequence of up to 20 steps panics, and the length stays
/// within 0..=CAPACITY (R7).
#[kani::proof]
#[kani::unwind(21)]
fn any_sequence_keeps_len_bounded() {
    let mut rb = RingBuffer::new();
    let mut i = 0;
    while i < 20 {
        let op: u8 = kani::any();
        match op % 3 {
            0 => {
                let _ = rb.push(kani::any());
            }
            1 => {
                let _ = rb.pop();
            }
            _ => {
                let _ = rb.peek();
            }
        }
        assert!(rb.len() <= CAPACITY);
        assert_eq!(rb.is_empty(), rb.len() == 0);
        i += 1;
    }
}

/// A full buffer rejects a push and keeps its length (R3).
#[kani::proof]
#[kani::unwind(18)]
fn full_buffer_rejects_push() {
    let mut rb = RingBuffer::new();
    let mut i = 0;
    while i < CAPACITY {
        assert!(rb.push(kani::any()));
        i += 1;
    }
    assert!(!rb.push(kani::any()));
    assert_eq!(rb.len(), CAPACITY);
}

/// An empty buffer yields nothing (R1, R4, R5).
#[kani::proof]
fn empty_buffer_yields_nothing() {
    let mut rb = RingBuffer::new();
    assert_eq!(rb.len(), 0);
    assert!(rb.peek().is_none());
    assert!(rb.pop().is_none());
}
