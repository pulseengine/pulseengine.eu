#![no_std]

/// The accumulator type: wide enough for five 16x16-bit products (B2).
type Acc = i64;

const ONE: Acc = 16384;
const HALF: Acc = 8192;

pub const MAX_DECIMATION: u8 = 8;

#[derive(Clone, Copy)]
pub struct Coeffs {
    pub b0: i16,
    pub b1: i16,
    pub b2: i16,
    pub a1: i16,
    pub a2: i16,
}

pub struct Biquad {
    c: Coeffs,
    m: u8,
    phase: u8,
    x1: i16,
    x2: i16,
    y1: i16,
    y2: i16,
    sat: u16,
}

impl Biquad {
    #[must_use]
    pub const fn new(c: Coeffs, m: u8) -> Option<Self> {
        if m == 0 || m > MAX_DECIMATION {
            return None;
        }
        Some(Self { c, m, phase: 0, x1: 0, x2: 0, y1: 0, y2: 0, sat: 0 })
    }

    fn filter(&mut self, x: i16) -> i16 {
        let c = self.c;
        let acc = Acc::from(c.b0) * Acc::from(x) + Acc::from(c.b1) * Acc::from(self.x1)
            + Acc::from(c.b2) * Acc::from(self.x2)
            - Acc::from(c.a1) * Acc::from(self.y1)
            - Acc::from(c.a2) * Acc::from(self.y2);
        let floor = acc.div_euclid(ONE);
        let rem = acc.rem_euclid(ONE);
        let rounded = if rem >= HALF { floor + 1 } else { floor }; // MUTANT: ties round up, not to even (violates B3)
        let clamped = rounded.clamp(Acc::from(i16::MIN), Acc::from(i16::MAX));
        if clamped != rounded {
            self.sat = self.sat.saturating_add(1);
        }
        // In range after the clamp, so the conversion cannot fail.
        let out = i16::try_from(clamped).unwrap_or(i16::MAX);
        self.x2 = self.x1;
        self.x1 = x;
        self.y2 = self.y1;
        self.y1 = out;
        out
    }

    const fn emits_next(&self) -> bool {
        self.phase + 1 == self.m
    }

    pub fn step(&mut self, x: i16) -> Option<i16> {
        let y = self.filter(x);
        if self.emits_next() {
            self.phase = 0;
            Some(y)
        } else {
            self.phase += 1;
            None
        }
    }

    pub fn process(&mut self, input: &[i16], output: &mut [i16]) -> (usize, usize) {
        let mut taken = 0;
        let mut written = 0;
        for &x in input {
            if self.emits_next() && written == output.len() {
                break;
            }
            taken += 1;
            if let Some(y) = self.step(x) {
                if let Some(slot) = output.get_mut(written) {
                    *slot = y;
                }
                written += 1;
            }
        }
        (taken, written)
    }

    pub fn reset(&mut self) {
        self.x1 = 0;
        self.x2 = 0;
        self.y1 = 0;
        self.y2 = 0;
        self.phase = 0;
    }

    #[must_use]
    pub fn sat_count(&self) -> u16 {
        self.sat
    }
}
