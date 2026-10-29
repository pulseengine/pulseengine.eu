// Fixed Kani harnesses for t11 (F4). The agent sees this file and may not edit
// it. It is compiled as its own crate, `fxm_proofs`, which depends on the
// agent's crate and imports only the names below, so no macro the agent
// defines can reach it; every assertion uses an absolute `::core::` path.
// These check freedom from panics and overflow, and structural properties,
// not the exact values of B2..B5: those are left to the hidden tests. The
// coefficients are fixed per harness and the inputs are symbolic. Bounded
// model checking within these bounds only.
use fxm_task::{Biquad, Coeffs, MAX_DECIMATION};

const EXTREME: Coeffs = Coeffs { b0: 32767, b1: 32767, b2: 32767, a1: -32768, a2: -32768 };
const EXTREME_NEG: Coeffs = Coeffs { b0: -32768, b1: -32768, b2: -32768, a1: 32767, a2: 32767 };
const IDENTITY: Coeffs = Coeffs { b0: 16384, b1: 0, b2: 0, a1: 0, a2: 0 };

/// Three samples with the largest coefficients and any inputs never panic or
/// overflow (B2: the accumulator is exact), and the saturation count only
/// grows, by at most one per sample (B4).
#[kani::proof]
#[kani::unwind(4)]
fn extreme_coefficients_never_overflow() {
    let Some(mut f) = Biquad::new(EXTREME, 1) else { ::core::panic!("M = 1 is valid") };
    let mut before = f.sat_count();
    let mut i = 0;
    while i < 3 {
        let _ = f.step(kani::any());
        let now = f.sat_count();
        ::core::assert!(now >= before && now - before <= 1);
        before = now;
        i += 1;
    }
}

/// The same with the opposite signs.
#[kani::proof]
#[kani::unwind(4)]
fn extreme_negative_coefficients_never_overflow() {
    let Some(mut f) = Biquad::new(EXTREME_NEG, 1) else { ::core::panic!("M = 1 is valid") };
    let mut i = 0;
    while i < 3 {
        let _ = f.step(kani::any());
        i += 1;
    }
}

/// Initialisation accepts exactly M = 1 to 8 (B1).
#[kani::proof]
fn new_accepts_only_valid_factors() {
    let m: u8 = kani::any();
    ::core::assert_eq!(Biquad::new(IDENTITY, m).is_some(), m >= 1 && m <= MAX_DECIMATION);
}

/// b0 = 1.0 and nothing else, without decimation, passes every input through
/// and never saturates (B2, B3, B4, B7).
#[kani::proof]
fn identity_passes_through() {
    let Some(mut f) = Biquad::new(IDENTITY, 1) else { ::core::panic!("M = 1 is valid") };
    let x: i16 = kani::any();
    let z: i16 = kani::any();
    ::core::assert_eq!(f.step(x), Some(x));
    ::core::assert_eq!(f.step(z), Some(z));
    ::core::assert_eq!(f.sat_count(), 0);
}

/// Eight samples emit exactly 8 / M outputs, for every valid M (B6).
#[kani::proof]
#[kani::unwind(9)]
fn decimation_emits_one_in_m() {
    let m: u8 = kani::any();
    kani::assume(m >= 1 && m <= MAX_DECIMATION);
    let Some(mut f) = Biquad::new(IDENTITY, m) else { ::core::panic!("M is valid") };
    let mut emitted: u8 = 0;
    let mut i = 0;
    while i < 8 {
        if f.step(kani::any()).is_some() {
            emitted += 1;
        }
        i += 1;
    }
    ::core::assert_eq!(emitted, 8 / m);
}

/// process takes at most the input, writes at most the output and at most one
/// output per input taken, and leaves the rest of the output alone (B8).
#[kani::proof]
#[kani::unwind(6)]
fn process_stays_in_bounds() {
    let input: [i16; 4] = kani::any();
    let mut output = [7_i16; 3];
    let n_in: usize = kani::any();
    let cap: usize = kani::any();
    let m: u8 = kani::any();
    kani::assume(n_in <= 4 && cap <= 3 && m >= 1 && m <= 3);
    let Some(mut f) = Biquad::new(IDENTITY, m) else { ::core::panic!("M is valid") };
    let (taken, written) = f.process(&input[..n_in], &mut output[..cap]);
    ::core::assert!(taken <= n_in && written <= cap && written <= taken);
    let mut k = written;
    while k < 3 {
        ::core::assert_eq!(output[k], 7);
        k += 1;
    }
}

/// Reset keeps the saturation count (B9).
#[kani::proof]
fn reset_keeps_sat_count() {
    let Some(mut f) = Biquad::new(EXTREME, 2) else { ::core::panic!("M = 2 is valid") };
    let _ = f.step(kani::any());
    let _ = f.step(kani::any());
    let n = f.sat_count();
    f.reset();
    ::core::assert_eq!(f.sat_count(), n);
}
