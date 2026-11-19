//! `json.loads` into a [`V`], with CPython's error messages for the common
//! failures ("Expecting value: line 1 column 1 (char 0)").

use crate::pyval::V;

pub fn loads(text: &str) -> Result<V, String> {
    let chars: Vec<char> = text.chars().collect();
    let mut p = P { c: &chars, i: 0 };
    if chars.first() == Some(&'\u{feff}') {
        return Err(p.err("Unexpected UTF-8 BOM (decode using utf-8-sig)", 0));
    }
    p.ws();
    let v = p.value()?;
    p.ws();
    if p.i != chars.len() {
        return Err(p.err("Extra data", p.i));
    }
    Ok(v)
}

struct P<'a> {
    c: &'a [char],
    i: usize,
}

impl P<'_> {
    fn err(&self, msg: &str, pos: usize) -> String {
        let before = &self.c[..pos.min(self.c.len())];
        let line = before.iter().filter(|c| **c == '\n').count() + 1;
        let col = match before.iter().rposition(|c| *c == '\n') {
            Some(nl) => pos - nl,
            None => pos + 1,
        };
        format!("{}: line {} column {} (char {})", msg, line, col, pos)
    }

    fn peek(&self) -> Option<char> {
        self.c.get(self.i).copied()
    }

    fn ws(&mut self) {
        while matches!(self.peek(), Some(' ' | '\t' | '\n' | '\r')) {
            self.i += 1;
        }
    }

    fn lit(&self, s: &str) -> bool {
        let n = s.chars().count();
        self.i + n <= self.c.len() && self.c[self.i..self.i + n].iter().copied().eq(s.chars())
    }

    fn value(&mut self) -> Result<V, String> {
        match self.peek() {
            Some('{') => self.object(),
            Some('[') => self.array(),
            Some('"') => {
                let s = self.string()?;
                Ok(V::Str(s))
            }
            _ if self.lit("null") => {
                self.i += 4;
                Ok(V::None)
            }
            _ if self.lit("true") => {
                self.i += 4;
                Ok(V::Bool(true))
            }
            _ if self.lit("false") => {
                self.i += 5;
                Ok(V::Bool(false))
            }
            _ if self.lit("NaN") => {
                self.i += 3;
                Ok(V::Float(f64::NAN))
            }
            _ if self.lit("Infinity") => {
                self.i += 8;
                Ok(V::Float(f64::INFINITY))
            }
            _ if self.lit("-Infinity") => {
                self.i += 9;
                Ok(V::Float(f64::NEG_INFINITY))
            }
            Some('-' | '0'..='9') => self.number(),
            _ => Err(self.err("Expecting value", self.i)),
        }
    }

    fn number(&mut self) -> Result<V, String> {
        let start = self.i;
        let digits = |p: &mut Self| {
            let s = p.i;
            while matches!(p.peek(), Some('0'..='9')) {
                p.i += 1;
            }
            p.i - s
        };
        if self.peek() == Some('-') {
            self.i += 1;
        }
        match self.peek() {
            Some('0') => self.i += 1,
            Some('1'..='9') => {
                digits(self);
            }
            _ => return Err(self.err("Expecting value", start)),
        }
        let mut float = false;
        if self.peek() == Some('.') && matches!(self.c.get(self.i + 1), Some('0'..='9')) {
            self.i += 1;
            digits(self);
            float = true;
        }
        if matches!(self.peek(), Some('e' | 'E')) {
            let save = self.i;
            self.i += 1;
            if matches!(self.peek(), Some('+' | '-')) {
                self.i += 1;
            }
            if digits(self) == 0 {
                self.i = save;
            } else {
                float = true;
            }
        }
        let text: String = self.c[start..self.i].iter().collect();
        if float {
            Ok(V::Float(text.parse().unwrap_or(f64::NAN)))
        } else {
            match text.parse::<i128>() {
                Ok(i) => Ok(V::Int(i)),
                Err(_) => Ok(V::Float(text.parse().unwrap_or(f64::NAN))),
            }
        }
    }

    fn string(&mut self) -> Result<String, String> {
        let start = self.i;
        self.i += 1;
        let mut out = String::new();
        loop {
            let Some(c) = self.peek() else {
                return Err(self.err("Unterminated string starting at", start));
            };
            match c {
                '"' => {
                    self.i += 1;
                    return Ok(out);
                }
                '\\' => {
                    let esc_at = self.i;
                    self.i += 1;
                    let Some(e) = self.peek() else {
                        return Err(self.err("Unterminated string starting at", start));
                    };
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
                            let hi = self.hex4(esc_at)?;
                            if (0xd800..0xdc00).contains(&hi) && self.lit("\\u") {
                                let save = self.i;
                                self.i += 2;
                                let lo = self.hex4(self.i - 2)?;
                                if (0xdc00..0xe000).contains(&lo) {
                                    let cp = 0x10000 + ((hi - 0xd800) << 10) + (lo - 0xdc00);
                                    out.push(char::from_u32(cp).unwrap_or('\u{fffd}'));
                                    continue;
                                }
                                self.i = save;
                            }
                            out.push(char::from_u32(hi).unwrap_or('\u{fffd}'));
                        }
                        other => {
                            let msg = format!("Invalid \\escape: {}", crate::pyval::repr_str(&other.to_string()));
                            return Err(self.err(&msg, esc_at));
                        }
                    }
                }
                c if (c as u32) < 0x20 => return Err(self.err("Invalid control character at", self.i)),
                c => {
                    out.push(c);
                    self.i += 1;
                }
            }
        }
    }

    fn hex4(&mut self, esc_at: usize) -> Result<u32, String> {
        let s: String = self.c.get(self.i..self.i + 4).map(|x| x.iter().collect()).unwrap_or_default();
        if s.len() == 4 && s.chars().all(|c| c.is_ascii_hexdigit()) {
            self.i += 4;
            Ok(u32::from_str_radix(&s, 16).unwrap_or(0xfffd))
        } else {
            Err(self.err("Invalid \\uXXXX escape", esc_at))
        }
    }

    fn object(&mut self) -> Result<V, String> {
        self.i += 1;
        let mut items: Vec<(V, V)> = vec![];
        self.ws();
        if self.peek() == Some('}') {
            self.i += 1;
            return Ok(V::Dict(items));
        }
        loop {
            if self.peek() != Some('"') {
                return Err(self.err("Expecting property name enclosed in double quotes", self.i));
            }
            let k = self.string()?;
            self.ws();
            if self.peek() != Some(':') {
                return Err(self.err("Expecting ':' delimiter", self.i));
            }
            self.i += 1;
            self.ws();
            let v = self.value()?;
            match items.iter_mut().find(|(x, _)| x.as_str() == Some(&k)) {
                Some(slot) => slot.1 = v,
                None => items.push((V::Str(k), v)),
            }
            self.ws();
            match self.peek() {
                Some('}') => {
                    self.i += 1;
                    return Ok(V::Dict(items));
                }
                Some(',') => {
                    let comma = self.i;
                    self.i += 1;
                    self.ws();
                    if self.peek() == Some('}') {
                        return Err(self.err("Illegal trailing comma before end of object", comma));
                    }
                }
                _ => return Err(self.err("Expecting ',' delimiter", self.i)),
            }
        }
    }

    fn array(&mut self) -> Result<V, String> {
        self.i += 1;
        let mut items = vec![];
        self.ws();
        if self.peek() == Some(']') {
            self.i += 1;
            return Ok(V::List(items));
        }
        loop {
            self.ws();
            items.push(self.value()?);
            self.ws();
            match self.peek() {
                Some(']') => {
                    self.i += 1;
                    return Ok(V::List(items));
                }
                Some(',') => {
                    let comma = self.i;
                    self.i += 1;
                    self.ws();
                    if self.peek() == Some(']') {
                        return Err(self.err("Illegal trailing comma before end of array", comma));
                    }
                }
                _ => return Err(self.err("Expecting ',' delimiter", self.i)),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn errors_read_as_python() {
        assert_eq!(loads("").unwrap_err(), "Expecting value: line 1 column 1 (char 0)");
        assert_eq!(loads("{\"a\": 1,}").unwrap_err(), "Illegal trailing comma before end of object: line 1 column 8 (char 7)");
        assert_eq!(loads("[1] x").unwrap_err(), "Extra data: line 1 column 5 (char 4)");
        assert_eq!(loads("{\n\"a\" 1}").unwrap_err(), "Expecting ':' delimiter: line 2 column 5 (char 6)");
    }

    #[test]
    fn values() {
        let v = loads("{\"a\": [1, 2.5, \"\\u00e9\\ud83d\\ude00\", null, true], \"a\": 3}").unwrap();
        assert_eq!(crate::pyval::repr(&v), "{'a': 3}");
    }
}
