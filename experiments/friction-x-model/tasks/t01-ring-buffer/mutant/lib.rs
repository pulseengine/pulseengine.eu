#![no_std]

pub const CAPACITY: usize = 16;

pub struct RingBuffer {
    data: [u8; CAPACITY],
    head: usize,
    count: usize,
}

impl Default for RingBuffer {
    fn default() -> Self {
        Self::new()
    }
}

impl RingBuffer {
    #[must_use]
    pub const fn new() -> Self {
        Self { data: [0; CAPACITY], head: 0, count: 0 }
    }

    pub fn push(&mut self, value: u8) -> bool {
        // MUTANT: overwrites the oldest byte when full (violates R3)
        let tail = (self.head + self.count) % CAPACITY;
        self.data[tail] = value;
        if self.count == CAPACITY {
            self.head = (self.head + 1) % CAPACITY;
        } else {
            self.count += 1;
        }
        true
    }

    pub fn pop(&mut self) -> Option<u8> {
        if self.count == 0 {
            return None;
        }
        let value = self.data[self.head];
        self.head = (self.head + 1) % CAPACITY;
        self.count -= 1;
        Some(value)
    }

    #[must_use]
    pub fn peek(&self) -> Option<u8> {
        if self.count == 0 { None } else { Some(self.data[self.head]) }
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.count
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.count == 0
    }
}
