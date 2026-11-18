//! The five regular expressions of check-north-star.py, written out by hand
//! with Python `re` semantics on str: Unicode `\b`, ASCII `[0-9]`, `$` also
//! matching before one trailing newline, and IGNORECASE's extra matches.

use crate::py::is_word;

fn boundary(s: &[char], i: usize) -> bool {
    let before = i > 0 && is_word(s[i - 1]);
    let after = i < s.len() && is_word(s[i]);
    before != after
}

fn digit(s: &[char], i: usize) -> bool {
    i < s.len() && s[i].is_ascii_digit()
}

/// `$` without MULTILINE: at the end, or before a final "\n".
fn dollar(s: &[char], i: usize) -> bool {
    i == s.len() || (i + 1 == s.len() && s[i] == '\n')
}

/// `ID_RE.match`: `^O[1-9][0-9]*$`
pub fn id_match(s: &str) -> bool {
    let s: Vec<char> = s.chars().collect();
    if s.len() < 2 || s[0] != 'O' || !('1'..='9').contains(&s[1]) {
        return false;
    }
    let mut i = 2;
    while digit(&s, i) {
        i += 1;
    }
    dollar(&s, i)
}

/// `LAYER_RE.match`: `^20[0-9]{2}\.(0[1-9]|1[0-2])$`
pub fn layer_match(s: &str) -> bool {
    let s: Vec<char> = s.chars().collect();
    if s.len() < 7 || s[0] != '2' || s[1] != '0' || !digit(&s, 2) || !digit(&s, 3) || s[4] != '.' {
        return false;
    }
    let month = match (s[5], s[6]) {
        ('0', '1'..='9') | ('1', '0'..='2') => true,
        _ => false,
    };
    month && dollar(&s, 7)
}

/// `DATE_RE.search`: `\b(20[0-9]{2}|Q[1-4]\b)`
pub fn date_search(s: &str) -> bool {
    let s: Vec<char> = s.chars().collect();
    (0..s.len()).any(|i| {
        boundary(&s, i)
            && ((s[i] == '2' && i + 1 < s.len() && s[i + 1] == '0' && digit(&s, i + 2) && digit(&s, i + 3))
                || (s[i] == 'Q' && i + 1 < s.len() && ('1'..='4').contains(&s[i + 1]) && boundary(&s, i + 2)))
    })
}

fn octets(s: &[char], pos: usize, group: usize) -> bool {
    for len in (1..=3).rev() {
        if !(0..len).all(|k| digit(s, pos + k)) {
            continue;
        }
        let end = pos + len;
        if group < 3 {
            if end < s.len() && s[end] == '.' && octets(s, end + 1, group + 1) {
                return true;
            }
        } else if boundary(s, end) {
            return true;
        }
    }
    false
}

/// `IPV4_RE.search`: `\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b`
pub fn ipv4_search(s: &str) -> bool {
    let s: Vec<char> = s.chars().collect();
    (0..s.len()).any(|i| boundary(&s, i) && octets(&s, i, 0))
}

/// `[a-z0-9-]` under re.I: ASCII letters of either case, digits, '-', and the
/// four non-ASCII characters Python's case folding maps onto a-z (measured on
/// CPython 3.9, 3.11, 3.12 and 3.14: U+0130, U+0131, U+017F, U+212A).
fn host_class(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '-' || matches!(c, '\u{130}' | '\u{131}' | '\u{17f}' | '\u{212a}')
}

/// A literal letter under re.I. Of the letters in the suffixes, only 'i' has
/// non-ASCII matches (U+0130, U+0131).
fn lit_i(c: char, want: char) -> bool {
    c.to_ascii_lowercase() == want || (want == 'i' && matches!(c, '\u{130}' | '\u{131}'))
}

/// `HOST_RE.search`: `\b[a-z0-9-]+\.(?:local|lan|home|internal|intranet)\b`, re.I
pub fn host_search(s: &str) -> bool {
    let s: Vec<char> = s.chars().collect();
    const SUFFIXES: [&str; 5] = ["local", "lan", "home", "internal", "intranet"];
    (0..s.len()).any(|i| {
        if !boundary(&s, i) {
            return false;
        }
        let mut j = i;
        while j < s.len() && host_class(s[j]) {
            j += 1;
        }
        // '.' is outside the class, so the run must be the maximal one.
        if j == i || j >= s.len() || s[j] != '.' {
            return false;
        }
        let start = j + 1;
        SUFFIXES.iter().any(|w| {
            let n = w.len();
            start + n <= s.len()
                && w.chars().enumerate().all(|(k, wc)| lit_i(s[start + k], wc))
                && boundary(&s, start + n)
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn match_like_python() {
        assert!(id_match("O1") && id_match("O12\n") && !id_match("O0") && !id_match("O1\n\n"));
        assert!(layer_match("2026.11") && !layer_match("2026-11") && !layer_match("2026.13"));
        assert!(date_search("By 2027.") && date_search("in Q3") && !date_search("Q34") && !date_search("x2027"));
        assert!(ipv4_search("runs on 10.0.0.5") && !ipv4_search("1.2.3.4567") && ipv4_search("1.2.3.4.5"));
        assert!(host_search("measured on box.lan") && host_search("A.LOCAL") && !host_search("x.lane"));
    }
}
