//! The slice of Python semantics the North Star check depends on.
//!
//! `scripts/check-north-star.py` is dynamically typed: a field can hold any
//! TOML value, and the messages print it with `%r` / `%s`. To give the same
//! output on every input, values here behave like the Python objects tomllib
//! returns: truthiness, `str()`, `repr()`, `==` and hashability.

use unicode_general_category::{GeneralCategory as G, get_general_category};

/// A TOML value as Python's tomllib returns it.
#[derive(Clone, Debug)]
pub enum Py {
    None,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    List(Vec<Py>),
    /// Insertion order, as a Python dict.
    Dict(Vec<(String, Py)>),
    Date(Date),
    Time(Time),
    DateTime(Date, Time, Option<i32>),
}

#[derive(Clone, Copy, Debug)]
pub struct Date {
    pub y: u16,
    pub m: u8,
    pub d: u8,
}

#[derive(Clone, Copy, Debug)]
pub struct Time {
    pub h: u8,
    pub mi: u8,
    pub s: u8,
    /// Microseconds: tomllib truncates fractional seconds to six digits.
    pub us: u32,
}

/// A Python exception that would end the script (it now exits 2).
pub type PyErr = String;

impl Py {
    pub fn get(&self, key: &str) -> Result<Option<&Py>, PyErr> {
        match self {
            Py::Dict(items) => Ok(items.iter().find(|(k, _)| k == key).map(|(_, v)| v)),
            other => Err(format!("AttributeError: '{}' object has no attribute 'get'", other.type_name())),
        }
    }

    pub fn type_name(&self) -> &'static str {
        match self {
            Py::None => "NoneType",
            Py::Bool(_) => "bool",
            Py::Int(_) => "int",
            Py::Float(_) => "float",
            Py::Str(_) => "str",
            Py::List(_) => "list",
            Py::Dict(_) => "dict",
            Py::Date(_) => "date",
            Py::Time(_) => "time",
            Py::DateTime(..) => "datetime",
        }
    }

    /// `bool(x)`. Dates, times and datetimes are always true (Python 3.5+).
    pub fn truthy(&self) -> bool {
        match self {
            Py::None => false,
            Py::Bool(b) => *b,
            Py::Int(i) => *i != 0,
            Py::Float(f) => *f != 0.0,
            Py::Str(s) => !s.is_empty(),
            Py::List(l) => !l.is_empty(),
            Py::Dict(d) => !d.is_empty(),
            Py::Date(_) | Py::Time(_) | Py::DateTime(..) => true,
        }
    }

    /// `for x in value`: list items, a string's characters, a dict's keys.
    pub fn iter(&self) -> Result<Vec<Py>, PyErr> {
        match self {
            Py::List(l) => Ok(l.clone()),
            Py::Str(s) => Ok(s.chars().map(|c| Py::Str(c.to_string())).collect()),
            Py::Dict(d) => Ok(d.iter().map(|(k, _)| Py::Str(k.clone())).collect()),
            other => Err(format!("TypeError: '{}' object is not iterable", other.type_name())),
        }
    }

    /// `value or []`, then iterate.
    pub fn iter_or_empty(v: Option<&Py>) -> Result<Vec<Py>, PyErr> {
        match v {
            Some(x) if x.truthy() => x.iter(),
            _ => Ok(Vec::new()),
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Py::Str(s) => Some(s),
            _ => None,
        }
    }

    /// Set membership needs a hashable value.
    pub fn check_hashable(&self) -> Result<(), PyErr> {
        match self {
            Py::List(_) | Py::Dict(_) => Err(format!("TypeError: unhashable type: '{}'", self.type_name())),
            _ => Ok(()),
        }
    }

    /// `a == b` for the hashable values a set comparison meets.
    pub fn py_eq(&self, other: &Py) -> bool {
        use Py::*;
        match (self, other) {
            (None, None) => true,
            (Str(a), Str(b)) => a == b,
            (Bool(_) | Int(_) | Float(_), Bool(_) | Int(_) | Float(_)) => num_eq(self, other),
            (Date(a), Date(b)) => (a.y, a.m, a.d) == (b.y, b.m, b.d),
            (Time(a), Time(b)) => time_key(a) == time_key(b),
            (DateTime(d1, t1, Option::None), DateTime(d2, t2, Option::None)) => {
                (d1.y, d1.m, d1.d, time_key(t1)) == (d2.y, d2.m, d2.d, time_key(t2))
            }
            (DateTime(d1, t1, Some(o1)), DateTime(d2, t2, Some(o2))) => {
                utc_micros(d1, t1, *o1) == utc_micros(d2, t2, *o2)
            }
            _ => false,
        }
    }

    /// `str(x)`.
    pub fn py_str(&self) -> String {
        match self {
            Py::Str(s) => s.clone(),
            Py::Date(d) => date_iso(d),
            Py::Time(t) => time_iso(t),
            Py::DateTime(d, t, off) => {
                let mut s = format!("{} {}", date_iso(d), time_iso(t));
                if let Some(o) = off {
                    s.push_str(&offset_iso(*o));
                }
                s
            }
            other => other.py_repr(),
        }
    }

    /// `repr(x)`.
    pub fn py_repr(&self) -> String {
        match self {
            Py::None => "None".into(),
            Py::Bool(true) => "True".into(),
            Py::Bool(false) => "False".into(),
            Py::Int(i) => i.to_string(),
            Py::Float(f) => float_repr(*f),
            Py::Str(s) => str_repr(s),
            Py::List(l) => format!("[{}]", l.iter().map(Py::py_repr).collect::<Vec<_>>().join(", ")),
            Py::Dict(d) => format!(
                "{{{}}}",
                d.iter()
                    .map(|(k, v)| format!("{}: {}", str_repr(k), v.py_repr()))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            Py::Date(d) => format!("datetime.date({}, {}, {})", d.y, d.m, d.d),
            Py::Time(t) => format!("datetime.time({})", time_fields(t)),
            Py::DateTime(d, t, off) => {
                let mut s = format!("datetime.datetime({}, {}, {}, {}", d.y, d.m, d.d, time_fields(t));
                if let Some(o) = off {
                    s.push_str(", tzinfo=");
                    s.push_str(&tz_repr(*o));
                }
                s.push(')');
                s
            }
        }
    }
}

fn time_key(t: &Time) -> (u8, u8, u8, u32) {
    (t.h, t.mi, t.s, t.us)
}

fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe
}

fn utc_micros(d: &Date, t: &Time, off_min: i32) -> i128 {
    let days = days_from_civil(d.y as i64, d.m as i64, d.d as i64) as i128;
    let secs = days * 86400 + t.h as i128 * 3600 + t.mi as i128 * 60 + t.s as i128 - off_min as i128 * 60;
    secs * 1_000_000 + t.us as i128
}

fn num_eq(a: &Py, b: &Py) -> bool {
    fn as_int(p: &Py) -> Option<i64> {
        match p {
            Py::Bool(b) => Some(*b as i64),
            Py::Int(i) => Some(*i),
            _ => None,
        }
    }
    match (as_int(a), as_int(b), a, b) {
        (Some(x), Some(y), _, _) => x == y,
        (Some(i), None, _, Py::Float(f)) | (None, Some(i), Py::Float(f), _) => int_float_eq(i, *f),
        (None, None, Py::Float(x), Py::Float(y)) => x == y,
        _ => false,
    }
}

/// Python compares an int and a float exactly, not by converting the int.
fn int_float_eq(i: i64, f: f64) -> bool {
    if !f.is_finite() || f.fract() != 0.0 || f.abs() >= 9.3e18 {
        return false;
    }
    (f as i128) == i as i128
}

fn date_iso(d: &Date) -> String {
    format!("{:04}-{:02}-{:02}", d.y, d.m, d.d)
}

fn time_iso(t: &Time) -> String {
    let mut s = format!("{:02}:{:02}:{:02}", t.h, t.mi, t.s);
    if t.us != 0 {
        s.push_str(&format!(".{:06}", t.us));
    }
    s
}

fn offset_iso(off_min: i32) -> String {
    let sign = if off_min < 0 { '-' } else { '+' };
    let a = off_min.abs();
    format!("{}{:02}:{:02}", sign, a / 60, a % 60)
}

/// The C `datetime` repr drops a zero microsecond, then a zero second.
fn time_fields(t: &Time) -> String {
    if t.us != 0 {
        format!("{}, {}, {}, {}", t.h, t.mi, t.s, t.us)
    } else if t.s != 0 {
        format!("{}, {}, {}", t.h, t.mi, t.s)
    } else {
        format!("{}, {}", t.h, t.mi)
    }
}

/// `repr(timezone(timedelta(minutes=off)))`; a zero offset is `timezone.utc`.
fn tz_repr(off_min: i32) -> String {
    if off_min == 0 {
        return "datetime.timezone.utc".into();
    }
    let total = off_min as i64 * 60;
    let days = total.div_euclid(86400);
    let secs = total.rem_euclid(86400);
    let mut parts = Vec::new();
    if days != 0 {
        parts.push(format!("days={}", days));
    }
    if secs != 0 {
        parts.push(format!("seconds={}", secs));
    }
    format!("datetime.timezone(datetime.timedelta({}))", parts.join(", "))
}

/// `repr(float)`: shortest round-trip digits, scientific when the decimal
/// point falls outside (-4, 16].
pub fn float_repr(f: f64) -> String {
    if f.is_nan() {
        return "nan".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "inf".into() } else { "-inf".into() };
    }
    if f == 0.0 {
        return if f.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    let e = format!("{:e}", f.abs()); // e.g. "1.2345e-5", shortest round-trip
    let (mant, exp) = e.split_once('e').unwrap();
    let exp: i32 = exp.parse().unwrap();
    let digits: String = mant.chars().filter(|c| *c != '.').collect();
    let decpt = exp + 1;
    let sign = if f < 0.0 { "-" } else { "" };
    let n = digits.len() as i32;
    let body = if decpt <= -4 || decpt > 16 {
        let m = if n == 1 { digits.clone() } else { format!("{}.{}", &digits[..1], &digits[1..]) };
        let es = if exp < 0 { '-' } else { '+' };
        format!("{}e{}{:02}", m, es, exp.abs())
    } else if decpt <= 0 {
        format!("0.{}{}", "0".repeat((-decpt) as usize), digits)
    } else if decpt >= n {
        format!("{}{}.0", digits, "0".repeat((decpt - n) as usize))
    } else {
        format!("{}.{}", &digits[..decpt as usize], &digits[decpt as usize..])
    };
    format!("{}{}", sign, body)
}

fn printable(c: char) -> bool {
    if c == ' ' {
        return true;
    }
    !matches!(
        get_general_category(c),
        G::Control
            | G::Format
            | G::Surrogate
            | G::PrivateUse
            | G::Unassigned
            | G::LineSeparator
            | G::ParagraphSeparator
            | G::SpaceSeparator
    )
}

/// `repr(str)`.
pub fn str_repr(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') { '"' } else { '\'' };
    let mut out = String::new();
    out.push(quote);
    for c in s.chars() {
        let u = c as u32;
        if c == quote || c == '\\' {
            out.push('\\');
            out.push(c);
        } else if c == '\t' {
            out.push_str("\\t");
        } else if c == '\n' {
            out.push_str("\\n");
        } else if c == '\r' {
            out.push_str("\\r");
        } else if u < 0x20 || u == 0x7f {
            out.push_str(&format!("\\x{:02x}", u));
        } else if u < 0x7f || printable(c) {
            out.push(c);
        } else if u <= 0xff {
            out.push_str(&format!("\\x{:02x}", u));
        } else if u <= 0xffff {
            out.push_str(&format!("\\u{:04x}", u));
        } else {
            out.push_str(&format!("\\U{:08x}", u));
        }
    }
    out.push(quote);
    out
}

/// `str.isspace()`: Rust's White_Space plus the four ASCII separators.
pub fn is_py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

/// `bool(s.strip())`.
pub fn strip_nonempty(s: &str) -> bool {
    s.chars().any(|c| !is_py_space(c))
}

/// `\w` in Python's `re` on str: `str.isalnum()` or `_`, i.e. categories L* and N*.
pub fn is_word(c: char) -> bool {
    if c == '_' {
        return true;
    }
    matches!(
        get_general_category(c),
        G::UppercaseLetter
            | G::LowercaseLetter
            | G::TitlecaseLetter
            | G::ModifierLetter
            | G::OtherLetter
            | G::DecimalNumber
            | G::LetterNumber
            | G::OtherNumber
    )
}

/// Convert a parsed TOML value into the value tomllib returns.
pub fn from_toml(v: &toml::Value) -> Py {
    match v {
        toml::Value::String(s) => Py::Str(s.clone()),
        toml::Value::Integer(i) => Py::Int(*i),
        toml::Value::Float(f) => Py::Float(*f),
        toml::Value::Boolean(b) => Py::Bool(*b),
        toml::Value::Array(a) => Py::List(a.iter().map(from_toml).collect()),
        toml::Value::Table(t) => Py::Dict(t.iter().map(|(k, v)| (k.clone(), from_toml(v))).collect()),
        toml::Value::Datetime(dt) => {
            let date = dt.date.map(|d| Date { y: d.year, m: d.month, d: d.day });
            let time = dt.time.map(|t| Time { h: t.hour, mi: t.minute, s: t.second, us: t.nanosecond / 1000 });
            let off = dt.offset.map(|o| match o {
                toml::value::Offset::Z => 0,
                toml::value::Offset::Custom { minutes } => minutes as i32,
            });
            match (date, time) {
                (Some(d), Some(t)) => Py::DateTime(d, t, off),
                (Some(d), None) => Py::Date(d),
                (None, Some(t)) => Py::Time(t),
                (None, None) => Py::None,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn floats_print_like_python() {
        assert_eq!(float_repr(1.0), "1.0");
        assert_eq!(float_repr(2026.11), "2026.11");
        assert_eq!(float_repr(1e16), "1e+16");
        assert_eq!(float_repr(1e15), "1000000000000000.0");
        assert_eq!(float_repr(0.0001), "0.0001");
        assert_eq!(float_repr(0.00001), "1e-05");
        assert_eq!(float_repr(-1.5e-7), "-1.5e-07");
        assert_eq!(float_repr(0.1), "0.1");
    }

    #[test]
    fn strings_print_like_python() {
        assert_eq!(str_repr("a'b"), "\"a'b\"");
        assert_eq!(str_repr("a'b\""), "'a\\'b\"'");
        assert_eq!(str_repr("\u{a0}\u{2028}é"), "'\\xa0\\u2028é'");
    }
}
