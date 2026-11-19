//! The regular expressions of seam-check.py, written out by hand so the crate
//! needs no regex engine. Each function names the pattern it implements and
//! keeps Python `re` semantics that matter here: `$` also matches before one
//! trailing newline, `^` under re.M matches after every `\n`, and `\s` is
//! Unicode whitespace.

/// Python's `\s` for str patterns: str.isspace().
pub fn py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

/// `re.match(r"...$", s)` where the pattern is anchored at both ends: `$`
/// accepts the end of the string or a final `\n`.
fn dollar(s: &str, pred: impl Fn(&str) -> bool) -> bool {
    pred(s) || s.strip_suffix('\n').is_some_and(&pred)
}

fn repo_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '-')
}

/// REPO = `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`
pub fn is_repo(s: &str) -> bool {
    dollar(s, |s| match s.split_once('/') {
        Some((a, b)) => !a.is_empty() && !b.is_empty() && a.chars().all(repo_char) && b.chars().all(repo_char),
        None => false,
    })
}

/// SEAM_ID = `^[a-z0-9][a-z0-9._/-]*$`
pub fn is_seam_id(s: &str) -> bool {
    dollar(s, |s| {
        let mut it = s.chars();
        match it.next() {
            Some(c) if c.is_ascii_lowercase() || c.is_ascii_digit() => {
                it.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '.' | '_' | '/' | '-'))
            }
            _ => false,
        }
    })
}

pub const SEAM_ID_PATTERN: &str = "^[a-z0-9][a-z0-9._/-]*$";

/// `--issue` spec: `^([^#\s]+/[^#\s]+)#(\d+)$` -> (repo, number).
pub fn issue_spec(spec: &str) -> Option<(String, i128)> {
    let one = |s: &str| -> Option<(String, i128)> {
        let (left, right) = s.split_once('#')?;
        if right.is_empty() || !right.chars().all(|c| c.is_ascii_digit()) {
            return None;
        }
        if left.chars().any(|c| c == '#' || py_space(c)) {
            return None;
        }
        let chars: Vec<char> = left.chars().collect();
        let ok = chars.iter().enumerate().any(|(i, c)| *c == '/' && i >= 1 && i + 1 < chars.len());
        if !ok {
            return None;
        }
        Some((left.to_string(), right.parse().ok()?))
    };
    one(spec).or_else(|| spec.strip_suffix('\n').and_then(one))
}

/// Byte offsets where `^` matches under re.M.
fn line_starts(t: &str) -> impl Iterator<Item = usize> + '_ {
    std::iter::once(0).chain(t.match_indices('\n').map(|(i, _)| i + 1)).filter(move |i| *i <= t.len())
}

/// FENCE = ```` ^```seam[ \t]*\r?\n(.*?)^```[ \t]*\r?$ ```` (re.M | re.S), finditer.
pub fn blocks_in(text: &str) -> Vec<String> {
    let b = text.as_bytes();
    let mut out = vec![];
    let mut from = 0usize;
    'outer: loop {
        // The next opening at a line start at or after `from`.
        let mut open = None;
        for s in line_starts(text) {
            if s < from {
                continue;
            }
            if !b[s..].starts_with(b"```seam") {
                continue;
            }
            let mut p = s + 7;
            while p < b.len() && (b[p] == b' ' || b[p] == b'\t') {
                p += 1;
            }
            if p < b.len() && b[p] == b'\r' {
                p += 1;
            }
            if p < b.len() && b[p] == b'\n' {
                open = Some(p + 1);
                break;
            }
        }
        let Some(body) = open else { break };
        // The lazy body ends at the first line start whose line is a bare fence.
        for q in line_starts(text) {
            if q < body {
                continue;
            }
            if !b[q..].starts_with(b"```") {
                continue;
            }
            let mut p = q + 3;
            while p < b.len() && (b[p] == b' ' || b[p] == b'\t') {
                p += 1;
            }
            if p < b.len() && b[p] == b'\r' && (p + 1 == b.len() || b[p + 1] == b'\n') {
                p += 1;
            }
            if p == b.len() || b[p] == b'\n' {
                out.push(text[body..q].to_string());
                from = p;
                continue 'outer;
            }
        }
        // An opening with no closing fence: the regex moves one position on.
        from = body;
        // Advance past this opening line so it is not found again.
        if from >= b.len() {
            break;
        }
    }
    out
}

/// WIT_PACKAGE = `^\s*package\s+([a-z0-9-]+:[a-z0-9-]+(?:/[a-z0-9-]+)*)@([0-9A-Za-z.+-]+)\s*;` (re.M), search.
pub fn wit_package(text: &str) -> Option<(String, String)> {
    let ident = |c: u8| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-';
    let run = |b: &[u8], from: usize, pred: &dyn Fn(u8) -> bool| -> usize {
        let mut p = from;
        while p < b.len() && pred(b[p]) {
            p += 1;
        }
        p
    };
    for s in line_starts(text) {
        let rest = &text[s..];
        let rest = rest.trim_start_matches(py_space);
        let Some(rest) = rest.strip_prefix("package") else { continue };
        let after = rest.trim_start_matches(py_space);
        if after.len() == rest.len() {
            continue;
        }
        let b = after.as_bytes();
        let p1 = run(b, 0, &ident);
        if p1 == 0 || b.get(p1) != Some(&b':') {
            continue;
        }
        let p2 = run(b, p1 + 1, &ident);
        if p2 == p1 + 1 {
            continue;
        }
        let mut end = p2;
        let mut ok = true;
        while b.get(end) == Some(&b'/') {
            let e = run(b, end + 1, &ident);
            if e == end + 1 {
                ok = false;
                break;
            }
            end = e;
        }
        if !ok || b.get(end) != Some(&b'@') {
            continue;
        }
        let vend = run(b, end + 1, &|c: u8| c.is_ascii_alphanumeric() || matches!(c, b'.' | b'+' | b'-'));
        if vend == end + 1 {
            continue;
        }
        if after[vend..].trim_start_matches(py_space).starts_with(';') {
            return Some((after[..end].to_string(), after[end + 1..vend].to_string()));
        }
    }
    None
}

/// `re.search(r"^\s*interface\s+%s\s*\{" % re.escape(name), text, re.M)`
pub fn declares_interface(text: &str, name: &str) -> bool {
    for s in line_starts(text) {
        let rest = text[s..].trim_start_matches(py_space);
        let Some(rest) = rest.strip_prefix("interface") else { continue };
        // \s+ then the literal name: try every split of the whitespace run.
        let ws: Vec<usize> = rest
            .char_indices()
            .take_while(|(_, c)| py_space(*c))
            .map(|(i, c)| i + c.len_utf8())
            .collect();
        for end in ws {
            if let Some(after) = rest[end..].strip_prefix(name) {
                if after.trim_start_matches(py_space).starts_with('{') {
                    return true;
                }
            }
        }
    }
    false
}

/// The `<...>; rel="next"` URL of a Link header: `<([^>]+)>;\s*rel="next"`, search.
pub fn link_next(link: &str) -> Option<String> {
    for (i, _) in link.match_indices('<') {
        let rest = &link[i + 1..];
        let Some(close) = rest.find('>') else { continue };
        if close == 0 {
            continue;
        }
        let after = &rest[close + 1..];
        if let Some(a) = after.strip_prefix(';') {
            if a.trim_start_matches(py_space).starts_with("rel=\"next\"") {
                return Some(rest[..close].to_string());
            }
        }
    }
    None
}

/// `urllib.parse.quote(s)` with the default safe='/'.
pub fn quote(s: &str) -> String {
    let mut out = String::new();
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'_' | b'.' | b'-' | b'~' | b'/') {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{:02X}", b));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fence() {
        let t = "x\n```seam\na: 1\n```\nmid\n```seam  \r\nb: 2\n```  \r\n";
        assert_eq!(blocks_in(t), vec!["a: 1\n".to_string(), "b: 2\n".to_string()]);
        assert_eq!(blocks_in("```seam\n```"), vec!["".to_string()]);
        assert!(blocks_in("```seam\nno close\n").is_empty());
        assert_eq!(blocks_in(" ```seam\na\n```\n"), Vec::<String>::new());
    }

    #[test]
    fn wit() {
        assert_eq!(
            wit_package("/// x\npackage acme:api@0.2.0;\n"),
            Some(("acme:api".into(), "0.2.0".into()))
        );
        assert_eq!(wit_package("  package a:b/c/d@1.0.0-rc.1 ;"), Some(("a:b/c/d".into(), "1.0.0-rc.1".into())));
        assert_eq!(wit_package("package a:b;\n"), None);
        assert!(declares_interface("x\n  interface controller {\n", "controller"));
        assert!(!declares_interface("interface controllers {\n", "controller"));
    }

    #[test]
    fn misc() {
        assert!(is_repo("a/b") && is_repo("a/b\n") && !is_repo("a/b/c") && !is_repo("a/"));
        assert_eq!(issue_spec("a/b/c#12"), Some(("a/b/c".into(), 12)));
        assert_eq!(issue_spec("ab#1"), None);
        assert_eq!(quote("org:a b/c"), "org%3Aa%20b/c");
        assert_eq!(link_next("<a>; rel=\"prev\", <b?x=1>; rel=\"next\""), Some("b?x=1".into()));
    }
}
