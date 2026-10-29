// Fixed Kani harnesses for t02 (F4). The agent sees this file and may not edit
// it. The harness appends `#[cfg(kani)] mod fxm_kani_proofs;` to the crate
// root, so `super::*` is the agent's crate. These check freedom from panics
// and algebraic properties, not the exact values of Q1..Q5: those are left to
// the hidden tests. Bounded model checking over all 16-bit inputs.
use super::*;

/// No operation panics or overflows, for any input.
#[kani::proof]
fn no_operation_panics() {
    let a: Q15 = kani::any();
    let b: Q15 = kani::any();
    let _ = add(a, b);
    let _ = sub(a, b);
    let _ = mul(a, b);
    let _ = neg(a);
    let _ = abs(a);
}

/// add is commutative. (mul commutativity is not a harness: proving it means
/// equating two symbolic 16x16 multipliers, which a SAT back end does not
/// finish within the time limit.)
#[kani::proof]
fn add_commutes() {
    let a: Q15 = kani::any();
    let b: Q15 = kani::any();
    assert_eq!(add(a, b), add(b, a));
}

/// Multiplying by one half never grows the magnitude.
#[kani::proof]
fn mul_by_half_never_grows() {
    let a: Q15 = kani::any();
    assert!(i32::from(mul(a, 16384)).abs() <= i32::from(a).abs());
}

/// neg is an involution away from the saturating corner; abs is never negative.
#[kani::proof]
fn neg_and_abs_shape() {
    let a: Q15 = kani::any();
    if a != Q15::MIN {
        assert_eq!(neg(neg(a)), a);
    }
    assert!(abs(a) >= 0);
}

/// Multiplying by zero gives zero.
#[kani::proof]
fn mul_by_zero_is_zero() {
    let a: Q15 = kani::any();
    assert_eq!(mul(a, 0), 0);
}
