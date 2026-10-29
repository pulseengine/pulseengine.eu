#![no_std]

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
    // your fields
}

impl Biquad {
    pub const fn new(c: Coeffs, m: u8) -> Option<Self> {
        todo!()
    }

    pub fn step(&mut self, x: i16) -> Option<i16> {
        todo!()
    }

    pub fn process(&mut self, input: &[i16], output: &mut [i16]) -> (usize, usize) {
        todo!()
    }

    pub fn reset(&mut self) {
        todo!()
    }

    pub fn sat_count(&self) -> u16 {
        todo!()
    }
}
