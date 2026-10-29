#![no_std]

pub type Q15 = i16;

fn clamp(x: i32) -> Q15 {
    // In range after the clamp, so the conversion cannot fail.
    Q15::try_from(x.clamp(i32::from(Q15::MIN), i32::from(Q15::MAX))).unwrap_or(Q15::MAX)
}

#[must_use]
pub fn add(a: Q15, b: Q15) -> Q15 {
    a.saturating_add(b)
}

#[must_use]
pub fn sub(a: Q15, b: Q15) -> Q15 {
    a.saturating_sub(b)
}

#[must_use]
pub fn mul(a: Q15, b: Q15) -> Q15 {
    let p = i32::from(a) * i32::from(b) + 16384;
    clamp(p.div_euclid(32768))
}

#[must_use]
pub fn neg(a: Q15) -> Q15 {
    a.saturating_neg()
}

#[must_use]
pub fn abs(a: Q15) -> Q15 {
    a.saturating_abs()
}
