#![no_std]

pub const CAPACITY: usize = 16;

pub struct RingBuffer {
    // your fields
}

impl RingBuffer {
    pub const fn new() -> Self {
        todo!()
    }

    pub fn push(&mut self, value: u8) -> bool {
        todo!()
    }

    pub fn pop(&mut self) -> Option<u8> {
        todo!()
    }

    pub fn peek(&self) -> Option<u8> {
        todo!()
    }

    pub fn len(&self) -> usize {
        todo!()
    }

    pub fn is_empty(&self) -> bool {
        todo!()
    }
}
