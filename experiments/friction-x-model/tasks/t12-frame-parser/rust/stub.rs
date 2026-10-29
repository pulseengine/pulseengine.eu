#![no_std]

pub const FLAG: u8 = 0x7E;
pub const ESC: u8 = 0x7D;
pub const BROADCAST: u8 = 0xFF;
pub const MAX_PAYLOAD: usize = 32;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Event {
    Nothing,
    Frame,
    Runt,
    BadCrc,
    Filtered,
    Abort,
    Overrun,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Counts {
    pub frames: u16,
    pub runts: u16,
    pub crc_errors: u16,
    pub filtered: u16,
    pub aborts: u16,
    pub overruns: u16,
}

pub struct Receiver {
    // your fields
}

impl Receiver {
    pub const fn new(addr: u8) -> Self {
        todo!()
    }

    pub fn push(&mut self, byte: u8) -> Event {
        todo!()
    }

    pub fn frame(&self) -> &[u8] {
        todo!()
    }

    pub fn counts(&self) -> Counts {
        todo!()
    }
}

pub fn crc16(data: &[u8]) -> u16 {
    todo!()
}

pub fn encode(addr: u8, payload: &[u8], out: &mut [u8]) -> usize {
    todo!()
}
