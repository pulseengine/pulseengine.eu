//! A JSON reader that accepts and rejects what Python's `json.loads` does.
//!
//! Rule 7 reads `data/north-star/<id>.json`. Python accepts `NaN`,
//! `Infinity`, `-Infinity`, integers of any size, lone surrogate escapes and
//! duplicate keys (the last one wins); a strict JSON library rejects some of
//! these, which would turn a valid measurement into an invalid one. Only the
//! parts rule 7 reads are kept precisely: strings, integers and structure.

#[derive(Debug, Clone)]
pub enum J {
    Null,
    Bool(bool),
    /// Sign and decimal digits without leading zeros ("0" for zero).
    Int(bool, String),
    Float,
    /// `None` for a string holding a lone surrogate: equal to no TOML string.
    Str(Option<String>),
    Arr,
    /// Key, value; lookups take the last match, as a Python dict built in order.
    Obj(Vec<(Option<String>, J)>),
}

impl J {
    pub fn get(&self, key: &str) -> Option<&J> {
        match self {
            J::Obj(items) => items.iter().rev().find(|(k, _)| k.as_deref() == Some(key)).map(|(_, v)| v),
            _ => None,
        }
    }

    /// `isinstance(x, int)`: bool is a subclass of int.
    pub fn as_int(&self) -> Option<(bool, String)> {
        match self {
            J::Int(neg, d) => Some((*neg, d.clone())),
            J::Bool(b) => Some((false, if *b { "1".into() } else { "0".into() })),
            _ => None,
        }
    }
}

/// Compare two integers given as sign and digits.
pub fn int_cmp(a: &(bool, String), b: &(bool, String)) -> std::cmp::Ordering {
    use std::cmp::Ordering::*;
    let mag = |x: &String, y: &String| x.len().cmp(&y.len()).then_with(|| x.cmp(y));
    match (a.0, b.0) {
        (false, true) => Greater,
        (true, false) => Less,
        (false, false) => mag(&a.1, &b.1),
        (true, true) => mag(&b.1, &a.1),
    }
}

struct P<'a> {
    s: &'a [char],
    i: usize,
}

pub fn parse(text: &str) -> Result<J, ()> {
    let chars: Vec<char> = text.chars().collect();
    let mut p = P { s: &chars, i: 0 };
    p.ws();
    let v = p.value(0)?;
    p.ws();
    if p.i != chars.len() {
        return Err(());
    }
    Ok(v)
}

impl P<'_> {
    fn peek(&self) -> Option<char> {
        self.s.get(self.i).copied()
    }

    fn ws(&mut self) {
        while matches!(self.peek(), Some(' ' | '\t' | '\n' | '\r')) {
            self.i += 1;
        }
    }

    fn lit(&mut self, w: &str) -> bool {
        let n = w.chars().count();
        if self.i + n <= self.s.len() && self.s[self.i..self.i + n].iter().copied().eq(w.chars()) {
            self.i += n;
            true
        } else {
            false
        }
    }

    fn value(&mut self, depth: usize) -> Result<J, ()> {
        if depth > 900 {
            return Err(()); // Python raises RecursionError near here
        }
        match self.peek() {
            Some('"') => {
                self.i += 1;
                self.string().map(J::Str)
            }
            Some('{') => {
                self.i += 1;
                self.object(depth)
            }
            Some('[') => {
                self.i += 1;
                self.ws();
                if self.peek() == Some(']') {
                    self.i += 1;
                    return Ok(J::Arr);
                }
                loop {
                    self.ws();
                    self.value(depth + 1)?;
                    self.ws();
                    match self.peek() {
                        Some(',') => self.i += 1,
                        Some(']') => {
                            self.i += 1;
                            return Ok(J::Arr);
                        }
                        _ => return Err(()),
                    }
                }
            }
            Some('n') if self.lit("null") => Ok(J::Null),
            Some('t') if self.lit("true") => Ok(J::Bool(true)),
            Some('f') if self.lit("false") => Ok(J::Bool(false)),
            Some('N') if self.lit("NaN") => Ok(J::Float),
            Some('I') if self.lit("Infinity") => Ok(J::Float),
            Some('-') if self.lit("-Infinity") => Ok(J::Float),
            Some('-' | '0'..='9') => self.number(),
            _ => Err(()),
        }
    }

    fn digits(&mut self) -> usize {
        let st = self.i;
        while matches!(self.peek(), Some('0'..='9')) {
            self.i += 1;
        }
        self.i - st
    }

    fn number(&mut self) -> Result<J, ()> {
        let neg = self.peek() == Some('-');
        if neg {
            self.i += 1;
        }
        let st = self.i;
        match self.peek() {
            Some('0') => self.i += 1,
            Some('1'..='9') => {
                self.digits();
            }
            _ => return Err(()),
        }
        let int: String = self.s[st..self.i].iter().collect();
        let mut float = false;
        // Python's scanner takes the fraction / exponent only when complete;
        // otherwise the number ends there and the rest is "extra data".
        if self.peek() == Some('.') && matches!(self.s.get(self.i + 1), Some('0'..='9')) {
            self.i += 1;
            self.digits();
            float = true;
        }
        if matches!(self.peek(), Some('e' | 'E')) {
            let save = self.i;
            self.i += 1;
            if matches!(self.peek(), Some('+' | '-')) {
                self.i += 1;
            }
            if self.digits() == 0 {
                self.i = save;
            } else {
                float = true;
            }
        }
        if float {
            return Ok(J::Float);
        }
        let neg = neg && int != "0";
        Ok(J::Int(neg, int))
    }

    fn hex4(&mut self) -> Result<u32, ()> {
        if self.i + 4 > self.s.len() {
            return Err(());
        }
        let mut v = 0u32;
        for k in 0..4 {
            v = v * 16 + self.s[self.i + k].to_digit(16).ok_or(())?;
        }
        self.i += 4;
        Ok(v)
    }

    /// After the opening quote. `None` when a lone surrogate is in it.
    fn string(&mut self) -> Result<Option<String>, ()> {
        let mut out = String::new();
        let mut lone = false;
        loop {
            let c = self.peek().ok_or(())?;
            self.i += 1;
            match c {
                '"' => return Ok(if lone { None } else { Some(out) }),
                '\\' => {
                    let e = self.peek().ok_or(())?;
                    self.i += 1;
                    match e {
                        '"' => out.push('"'),
                        '\\' => out.push('\\'),
                        '/' => out.push('/'),
                        'b' => out.push('\u{8}'),
                        'f' => out.push('\u{c}'),
                        'n' => out.push('\n'),
                        'r' => out.push('\r'),
                        't' => out.push('\t'),
                        'u' => {
                            let u = self.hex4()?;
                            if (0xd800..0xdc00).contains(&u)
                                && self.s.get(self.i) == Some(&'\\')
                                && self.s.get(self.i + 1) == Some(&'u')
                            {
                                let save = self.i;
                                self.i += 2;
                                let lo = self.hex4()?;
                                if (0xdc00..0xe000).contains(&lo) {
                                    let cp = 0x10000 + ((u - 0xd800) << 10) + (lo - 0xdc00);
                                    out.push(char::from_u32(cp).unwrap());
                                    continue;
                                }
                                self.i = save;
                            }
                            match char::from_u32(u) {
                                Some(ch) => out.push(ch),
                                None => lone = true,
                            }
                        }
                        _ => return Err(()),
                    }
                }
                c if (c as u32) < 0x20 => return Err(()),
                c => out.push(c),
            }
        }
    }

    fn object(&mut self, depth: usize) -> Result<J, ()> {
        let mut items = Vec::new();
        self.ws();
        if self.peek() == Some('}') {
            self.i += 1;
            return Ok(J::Obj(items));
        }
        loop {
            self.ws();
            if self.peek() != Some('"') {
                return Err(());
            }
            self.i += 1;
            let k = self.string()?;
            self.ws();
            if self.peek() != Some(':') {
                return Err(());
            }
            self.i += 1;
            self.ws();
            let v = self.value(depth + 1)?;
            items.push((k, v));
            self.ws();
            match self.peek() {
                Some(',') => self.i += 1,
                Some('}') => {
                    self.i += 1;
                    return Ok(J::Obj(items));
                }
                _ => return Err(()),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_what_python_accepts() {
        assert!(parse(r#"{"a": NaN, "b": -Infinity, "c": 1e400}"#).is_ok());
        assert!(parse(r#"{"objective": "O1", "value": 1, "value": 2}"#).unwrap().get("value").is_some());
        assert!(parse(r#""\ud800""#).is_ok());
        assert!(parse("123456789012345678901234567890").is_ok());
    }

    #[test]
    fn rejects_what_python_rejects() {
        for bad in ["", "{", "[1,]", "01", "1.", "\u{feff}{}", "{'a': 1}", "\"\t\"", "{} x", "nan"] {
            assert!(parse(bad).is_err(), "{bad:?}");
        }
    }
}
