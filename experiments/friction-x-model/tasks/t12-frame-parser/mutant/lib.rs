#![no_std]

pub const FLAG: u8 = 0x7E;
pub const ESC: u8 = 0x7D;
pub const BROADCAST: u8 = 0xFF;
pub const MAX_PAYLOAD: usize = 32;

const MAX_CONTENT: usize = MAX_PAYLOAD + 3;
const UNESCAPE: u8 = 0x20;

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

#[derive(Clone, Copy, PartialEq, Eq)]
enum State {
    Hunting,
    InFrame,
    AfterEsc,
}

pub struct Receiver {
    addr: u8,
    state: State,
    buf: [u8; MAX_CONTENT],
    n: usize,
    frame: [u8; MAX_PAYLOAD],
    frame_len: usize,
    counts: Counts,
}

#[must_use]
pub fn crc16(data: &[u8]) -> u16 {
    let mut crc: u16 = 0xFFFF;
    for &byte in data {
        crc ^= u16::from(byte) << 8;
        for _ in 0..8 {
            crc = if crc & 0x8000 == 0 { crc << 1 } else { (crc << 1) ^ 0x1021 };
        }
    }
    crc
}

fn bump(count: &mut u16) {
    *count = count.saturating_add(1);
}

impl Receiver {
    #[must_use]
    pub const fn new(addr: u8) -> Self {
        Self {
            addr,
            state: State::Hunting,
            buf: [0; MAX_CONTENT],
            n: 0,
            frame: [0; MAX_PAYLOAD],
            frame_len: 0,
            counts: Counts { frames: 0, runts: 0, crc_errors: 0, filtered: 0, aborts: 0, overruns: 0 },
        }
    }

    pub fn push(&mut self, byte: u8) -> Event {
        match (self.state, byte) {
            (State::Hunting, FLAG) => {
                self.open();
                Event::Nothing
            }
            (State::Hunting, _) => Event::Nothing,
            (State::AfterEsc, FLAG) => {
                // MUTANT: an abort makes the receiver hunt instead of opening a new frame (violates H6)
                self.state = State::Hunting;
                self.n = 0;
                bump(&mut self.counts.aborts);
                Event::Abort
            }
            (State::InFrame, FLAG) => {
                let event = self.close();
                self.open();
                event
            }
            (State::InFrame, ESC) => {
                self.state = State::AfterEsc;
                Event::Nothing
            }
            (State::AfterEsc, _) => {
                self.state = State::InFrame;
                self.content(byte ^ UNESCAPE)
            }
            (State::InFrame, _) => self.content(byte),
        }
    }

    fn open(&mut self) {
        self.state = State::InFrame;
        self.n = 0;
    }

    fn content(&mut self, byte: u8) -> Event {
        if let Some(slot) = self.buf.get_mut(self.n) {
            *slot = byte;
            self.n += 1;
            Event::Nothing
        } else {
            self.state = State::Hunting;
            self.n = 0;
            bump(&mut self.counts.overruns);
            Event::Overrun
        }
    }

    fn close(&mut self) -> Event {
        let content = &self.buf[..self.n];
        let Some((&[hi, lo], body)) = content.split_last_chunk::<2>().map(|(b, c)| (c, b)) else {
            if content.is_empty() {
                return Event::Nothing;
            }
            bump(&mut self.counts.runts);
            return Event::Runt;
        };
        let Some((&addr, payload)) = body.split_first() else {
            bump(&mut self.counts.runts);
            return Event::Runt;
        };
        if crc16(body) != u16::from_be_bytes([hi, lo]) {
            bump(&mut self.counts.crc_errors);
            return Event::BadCrc;
        }
        if addr != self.addr && addr != BROADCAST {
            bump(&mut self.counts.filtered);
            return Event::Filtered;
        }
        self.frame[..payload.len()].copy_from_slice(payload);
        self.frame_len = payload.len();
        bump(&mut self.counts.frames);
        Event::Frame
    }

    #[must_use]
    pub fn frame(&self) -> &[u8] {
        &self.frame[..self.frame_len]
    }

    #[must_use]
    pub fn counts(&self) -> Counts {
        self.counts
    }
}

#[must_use]
pub fn encode(addr: u8, payload: &[u8], out: &mut [u8]) -> usize {
    if payload.len() > MAX_PAYLOAD {
        return 0;
    }
    let crc = {
        let mut whole = [0_u8; MAX_PAYLOAD + 1];
        whole[0] = addr;
        whole[1..=payload.len()].copy_from_slice(payload);
        crc16(&whole[..=payload.len()]).to_be_bytes()
    };
    let content = [addr].into_iter().chain(payload.iter().copied()).chain(crc);
    let need = 2 + content.clone().map(|b| if b == FLAG || b == ESC { 2 } else { 1 }).sum::<usize>();
    let Some(frame) = out.get_mut(..need) else {
        return 0;
    };
    let mut k = 0;
    frame[k] = FLAG;
    k += 1;
    for b in content {
        if b == FLAG || b == ESC {
            frame[k] = ESC;
            frame[k + 1] = b ^ UNESCAPE;
            k += 2;
        } else {
            frame[k] = b;
            k += 1;
        }
    }
    frame[k] = FLAG;
    need
}
