//! A value with Python's semantics: the shape both YAML blocks and JSON
//! (world.json, GitHub responses) are read into, so every rule can be written
//! the way seam-check.py writes it: truthiness, `==`, `%r`, `%s`, `type().__name__`
//! and `json.dumps(indent=2, sort_keys=True)` all behave as in CPython.

use std::fmt::Write as _;

#[derive(Clone, Debug)]
pub enum V {
    None,
    Bool(bool),
    Int(i128),
    Float(f64),
    Str(String),
    List(Vec<V>),
    /// Insertion-ordered, as a Python dict.
    Dict(Vec<(V, V)>),
}

/// The run cannot go on the way Python's would: Python raises an uncaught
/// exception (a traceback on stderr, exit 1, nothing on stdout).
#[derive(Debug)]
pub struct Crash(pub String);

impl V {
    pub fn s(x: &str) -> V {
        V::Str(x.to_string())
    }

    pub fn truthy(&self) -> bool {
        match self {
            V::None => false,
            V::Bool(b) => *b,
            V::Int(i) => *i != 0,
            V::Float(f) => *f != 0.0,
            V::Str(s) => !s.is_empty(),
            V::List(l) => !l.is_empty(),
            V::Dict(d) => !d.is_empty(),
        }
    }

    pub fn type_name(&self) -> &'static str {
        match self {
            V::None => "NoneType",
            V::Bool(_) => "bool",
            V::Int(_) => "int",
            V::Float(_) => "float",
            V::Str(_) => "str",
            V::List(_) => "list",
            V::Dict(_) => "dict",
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            V::Str(s) => Some(s),
            _ => None,
        }
    }

    pub fn is_dict(&self) -> bool {
        matches!(self, V::Dict(_))
    }

    pub fn is_list(&self) -> bool {
        matches!(self, V::List(_))
    }

    /// `d.get(key)` on a dict with a string key; None for a non-dict too.
    pub fn get(&self, key: &str) -> Option<&V> {
        match self {
            V::Dict(d) => d.iter().find(|(k, _)| k.as_str() == Some(key)).map(|(_, v)| v),
            _ => None,
        }
    }

    pub fn get_mut(&mut self, key: &str) -> Option<&mut V> {
        match self {
            V::Dict(d) => d.iter_mut().find(|(k, _)| k.as_str() == Some(key)).map(|(_, v)| v),
            _ => None,
        }
    }

    pub fn has(&self, key: &str) -> bool {
        self.get(key).is_some()
    }

    /// `d[key] = value`: replace in place, or append.
    pub fn set(&mut self, key: &str, value: V) {
        if let Some(slot) = self.get_mut(key) {
            *slot = value;
        } else if let V::Dict(d) = self {
            d.push((V::s(key), value));
        }
    }

    /// `d.get(key) or default`, as the truthy value.
    pub fn get_or<'a>(&'a self, key: &str) -> Option<&'a V> {
        self.get(key).filter(|v| v.truthy())
    }

    /// `x is hashable` for the value kinds a block can carry.
    pub fn hashable(&self) -> bool {
        !matches!(self, V::List(_) | V::Dict(_))
    }
}

/// Python `==` (numbers compare across bool/int/float, containers deeply).
impl PartialEq for V {
    fn eq(&self, other: &V) -> bool {
        fn num(v: &V) -> Option<f64> {
            match v {
                V::Bool(b) => Some(if *b { 1.0 } else { 0.0 }),
                V::Int(i) => Some(*i as f64),
                V::Float(f) => Some(*f),
                _ => None,
            }
        }
        match (self, other) {
            (V::None, V::None) => true,
            (V::Str(a), V::Str(b)) => a == b,
            (V::List(a), V::List(b)) => a == b,
            (V::Dict(a), V::Dict(b)) => {
                a.len() == b.len() && a.iter().all(|(k, v)| b.iter().any(|(k2, v2)| k == k2 && v == v2))
            }
            (V::Int(a), V::Int(b)) => a == b,
            (V::Bool(a), V::Bool(b)) => a == b,
            _ => match (num(self), num(other)) {
                (Some(a), Some(b)) => a == b,
                _ => false,
            },
        }
    }
}

/// `for x in value` over `value or []`: a list yields items, a string its
/// characters, a dict its keys; a truthy number is a TypeError in Python.
pub fn iter_or_empty(v: Option<&V>) -> Result<Vec<V>, Crash> {
    match v {
        None => Ok(vec![]),
        Some(v) if !v.truthy() => Ok(vec![]),
        Some(V::List(l)) => Ok(l.clone()),
        Some(V::Str(s)) => Ok(s.chars().map(|c| V::Str(c.to_string())).collect()),
        Some(V::Dict(d)) => Ok(d.iter().map(|(k, _)| k.clone()).collect()),
        Some(other) => Err(Crash(format!("TypeError: '{}' object is not iterable", other.type_name()))),
    }
}

/// `needle in haystack` with a str needle.
pub fn py_in(needle: &str, hay: &V) -> Result<bool, Crash> {
    match hay {
        V::List(l) => Ok(l.iter().any(|x| x.as_str() == Some(needle))),
        V::Str(s) => Ok(s.contains(needle)),
        V::Dict(d) => Ok(d.iter().any(|(k, _)| k.as_str() == Some(needle))),
        other => Err(Crash(format!("TypeError: argument of type '{}' is not iterable", other.type_name()))),
    }
}

// ── repr / str ──────────────────────────────────────────────────────────────

/// `str.isprintable()` for one character. Exact for ASCII and Latin-1 and for
/// the format, separator and private-use ranges a block plausibly carries;
/// unassigned code points (category Cn) are not tabled and count as printable.
fn printable(c: char) -> bool {
    let u = c as u32;
    if u < 0x20 || (0x7f..0xa0).contains(&u) {
        return false;
    }
    if c == ' ' {
        return true;
    }
    let not = [
        (0xa0, 0xa0), (0xad, 0xad), (0x600, 0x605), (0x61c, 0x61c), (0x6dd, 0x6dd),
        (0x70f, 0x70f), (0x890, 0x891), (0x8e2, 0x8e2), (0x1680, 0x1680), (0x180e, 0x180e),
        (0x2000, 0x200f), (0x2028, 0x202f), (0x205f, 0x2064), (0x2066, 0x206f),
        (0x3000, 0x3000), (0xd800, 0xf8ff), (0xfeff, 0xfeff), (0xfff9, 0xfffb),
        (0x110bd, 0x110bd), (0x110cd, 0x110cd), (0x13430, 0x1343f), (0x1bca0, 0x1bca3),
        (0x1d173, 0x1d17a), (0xe0001, 0xe0001), (0xe0020, 0xe007f), (0xf0000, 0x10ffff),
    ];
    !not.iter().any(|(a, b)| (*a..=*b).contains(&u))
}

pub fn repr_str(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') { '"' } else { '\'' };
    let mut out = String::new();
    out.push(quote);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if printable(c) => out.push(c),
            c => {
                let u = c as u32;
                if u <= 0xff {
                    let _ = write!(out, "\\x{:02x}", u);
                } else if u <= 0xffff {
                    let _ = write!(out, "\\u{:04x}", u);
                } else {
                    let _ = write!(out, "\\U{:08x}", u);
                }
            }
        }
    }
    out.push(quote);
    out
}

/// `float.__repr__`: the shortest round-trip digits, in Python's layout
/// (scientific below 1e-4 and from 1e16 on).
pub fn repr_float(f: f64) -> String {
    if f.is_nan() {
        return "nan".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "inf".into() } else { "-inf".into() };
    }
    if f == 0.0 {
        return if f.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    // Rust's {:e} is the shortest round-trip form: d[.ddd]e[-]x.
    let e = format!("{:e}", f.abs());
    let (mant, exp) = e.split_once('e').unwrap_or((&e, "0"));
    let exp: i32 = exp.parse().unwrap_or(0);
    let digits: String = mant.chars().filter(|c| *c != '.').collect();
    let sign = if f < 0.0 { "-" } else { "" };
    let n = digits.len() as i32;
    let body = if (-4..16).contains(&exp) {
        if exp >= 0 {
            let int_len = exp + 1;
            if n <= int_len {
                format!("{}{}.0", digits, "0".repeat((int_len - n) as usize))
            } else {
                format!("{}.{}", &digits[..int_len as usize], &digits[int_len as usize..])
            }
        } else {
            format!("0.{}{}", "0".repeat((-exp - 1) as usize), digits)
        }
    } else {
        let m = if n > 1 { format!("{}.{}", &digits[..1], &digits[1..]) } else { digits.clone() };
        format!("{}e{}{:02}", m, if exp < 0 { "-" } else { "+" }, exp.abs())
    };
    format!("{}{}", sign, body)
}

pub fn repr(v: &V) -> String {
    match v {
        V::None => "None".into(),
        V::Bool(true) => "True".into(),
        V::Bool(false) => "False".into(),
        V::Int(i) => i.to_string(),
        V::Float(f) => repr_float(*f),
        V::Str(s) => repr_str(s),
        V::List(l) => format!("[{}]", l.iter().map(repr).collect::<Vec<_>>().join(", ")),
        V::Dict(d) => format!(
            "{{{}}}",
            d.iter().map(|(k, v)| format!("{}: {}", repr(k), repr(v))).collect::<Vec<_>>().join(", ")
        ),
    }
}

/// `"%s" % v`
pub fn py_str(v: &V) -> String {
    match v {
        V::Str(s) => s.clone(),
        other => repr(other),
    }
}

// ── json.dumps(obj, indent=2, sort_keys=True) ───────────────────────────────

fn json_str(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            ' '..='~' => out.push(c),
            c => {
                let mut buf = [0u16; 2];
                for unit in c.encode_utf16(&mut buf) {
                    let _ = write!(out, "\\u{:04x}", unit);
                }
            }
        }
    }
    out.push('"');
}

fn json_key(k: &V) -> String {
    match k {
        V::Str(s) => s.clone(),
        V::Bool(true) => "true".into(),
        V::Bool(false) => "false".into(),
        V::None => "null".into(),
        V::Float(f) => json_float(*f),
        other => repr(other),
    }
}

fn json_float(f: f64) -> String {
    if f.is_nan() {
        "NaN".into()
    } else if f.is_infinite() {
        if f > 0.0 { "Infinity".into() } else { "-Infinity".into() }
    } else {
        repr_float(f)
    }
}

fn json_into(v: &V, level: usize, out: &mut String) {
    let pad = |n: usize| "  ".repeat(n);
    match v {
        V::None => out.push_str("null"),
        V::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        V::Int(i) => out.push_str(&i.to_string()),
        V::Float(f) => out.push_str(&json_float(*f)),
        V::Str(s) => json_str(s, out),
        V::List(l) => {
            if l.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (n, x) in l.iter().enumerate() {
                out.push_str(&pad(level + 1));
                json_into(x, level + 1, out);
                if n + 1 < l.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&pad(level));
            out.push(']');
        }
        V::Dict(d) => {
            if d.is_empty() {
                out.push_str("{}");
                return;
            }
            let mut items: Vec<(String, &V)> = d.iter().map(|(k, v)| (json_key(k), v)).collect();
            items.sort_by(|a, b| a.0.cmp(&b.0));
            out.push_str("{\n");
            for (n, (k, x)) in items.iter().enumerate() {
                out.push_str(&pad(level + 1));
                json_str(k, out);
                out.push_str(": ");
                json_into(x, level + 1, out);
                if n + 1 < items.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str(&pad(level));
            out.push('}');
        }
    }
}

pub fn json_dumps(v: &V) -> String {
    let mut out = String::new();
    json_into(v, 0, &mut out);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn float_repr_matches_python() {
        for (f, want) in [
            (0.2, "0.2"), (1.0, "1.0"), (1e16, "1e+16"), (1.5e16, "1.5e+16"), (123456789012345.6, "123456789012345.6"),
            (0.0001, "0.0001"), (0.00001, "1e-05"), (1.25e-7, "1.25e-07"), (-2.5, "-2.5"), (1e22, "1e+22"),
            (100.0, "100.0"), (9999999999999998.0, "9999999999999998.0"),
        ] {
            assert_eq!(repr_float(f), want, "{}", f);
        }
    }

    #[test]
    fn str_repr_matches_python() {
        assert_eq!(repr_str("a"), "'a'");
        assert_eq!(repr_str("it's"), "\"it's\"");
        assert_eq!(repr_str("'\""), "'\\'\"'");
        assert_eq!(repr_str("a\nb\x01\u{a0}é\u{2028}"), "'a\\nb\\x01\\xa0é\\u2028'");
    }
}
