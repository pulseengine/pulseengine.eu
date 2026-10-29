// Fixed Kani harnesses for t12 (F4). The agent sees this file and may not edit
// it. It is compiled as its own crate, `fxm_proofs`, which depends on the
// agent's crate and imports only the names below, so no macro the agent
// defines can reach it; every assertion uses an absolute `::core::` path.
// These check freedom from panics, bounds, the counts' shape, the accepted
// frame's stability and a round trip, not the events and values of H2..H6:
// those are left to the hidden tests. Bounded model checking within these
// bounds only.
use fxm_task::{encode, Counts, Event, Receiver, FLAG, MAX_PAYLOAD};

fn total(c: Counts) -> u32 {
    u32::from(c.frames) + u32::from(c.runts) + u32::from(c.crc_errors) + u32::from(c.filtered)
        + u32::from(c.aborts) + u32::from(c.overruns)
}

/// Any 8 bytes, for any address: no panic, the accepted frame stays within
/// MAX_PAYLOAD, and each byte adds at most one to the counts in all (H2..H8).
#[kani::proof]
#[kani::unwind(10)]
fn any_bytes_stay_in_bounds() {
    let mut rx = Receiver::new(kani::any());
    let mut before = total(rx.counts());
    let mut i = 0;
    while i < 8 {
        let ev = rx.push(kani::any());
        let now = total(rx.counts());
        ::core::assert!(now >= before && now - before <= 1);
        ::core::assert!((now == before) == (ev == Event::Nothing));
        ::core::assert!(rx.frame().len() <= MAX_PAYLOAD);
        before = now;
        i += 1;
    }
}

/// After a frame is accepted, the accepted payload does not change until the
/// next Frame event, whatever 4 bytes follow (H7).
#[kani::proof]
#[kani::unwind(14)]
fn accepted_frame_is_stable() {
    let mut wire = [0_u8; 12];
    let n = encode(5, &[0xA1, 0xA2], &mut wire);
    ::core::assert!(n > 0 && n <= 12);
    let mut rx = Receiver::new(5);
    let mut k = 0;
    while k < n {
        let _ = rx.push(wire[k]);
        k += 1;
    }
    ::core::assert!(rx.frame() == [0xA1, 0xA2]);
    let mut i = 0;
    while i < 4 {
        if rx.push(kani::any()) == Event::Frame {
            break;
        }
        ::core::assert!(rx.frame() == [0xA1, 0xA2]);
        i += 1;
    }
}

/// encode then push gives back the payload, for any address and any payload
/// of up to 2 bytes (H3, H5, H10).
#[kani::proof]
#[kani::unwind(14)]
fn encode_then_receive_round_trips() {
    let addr: u8 = kani::any();
    let payload: [u8; 2] = kani::any();
    let len: usize = kani::any();
    kani::assume(len <= 2);
    let mut wire = [0_u8; 12];
    let n = encode(addr, &payload[..len], &mut wire);
    ::core::assert!(n >= 5 && n <= 12);
    let mut rx = Receiver::new(addr);
    let mut last = Event::Nothing;
    let mut k = 0;
    while k < n {
        last = rx.push(wire[k]);
        k += 1;
    }
    ::core::assert!(last == Event::Frame);
    ::core::assert!(rx.frame() == &payload[..len]);
}

/// The 36th content byte of a frame is an overrun (H4). The bytes are fixed:
/// symbolic ones do not finish within the time limit.
#[kani::proof]
#[kani::unwind(38)]
fn thirty_six_content_bytes_overrun() {
    let mut rx = Receiver::new(0x05);
    let b: u8 = 0x11;
    let _ = rx.push(FLAG);
    let mut i = 0;
    while i < 35 {
        ::core::assert!(rx.push(b) == Event::Nothing);
        i += 1;
    }
    ::core::assert!(rx.push(b) == Event::Overrun);
    ::core::assert_eq!(rx.counts().overruns, 1);
}

/// encode returns 0 and writes nothing when the output is too short (H10).
#[kani::proof]
#[kani::unwind(14)]
fn encode_rejects_short_output() {
    let addr: u8 = kani::any();
    let payload: [u8; 2] = kani::any();
    let mut full = [0_u8; 12];
    let need = encode(addr, &payload, &mut full);
    let cap: usize = kani::any();
    kani::assume(cap < need);
    let mut out = [0xA5_u8; 12];
    ::core::assert_eq!(encode(addr, &payload, &mut out[..cap]), 0);
    ::core::assert!(out.iter().all(|&b| b == 0xA5));
}
