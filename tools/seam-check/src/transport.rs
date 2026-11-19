//! Where issues and files come from: an offline fixture world, or GitHub REST
//! over curl (or, with `--http urllib`, a plain-HTTP std client standing in for
//! Python's urllib; it serves the loopback stub, not HTTPS).

use crate::check::{os_error, Fail};
use crate::json;
use crate::pyval::{py_in, py_str, V};
use crate::text::{link_next, quote};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub const GITHUB_API: &str = "https://api.github.com";

pub trait Source {
    fn name(&self) -> String;
    fn discover(&mut self, org: &str, label: &str) -> Result<Vec<V>, Fail>;
    fn issue(&mut self, repo: &str, number: i128) -> Result<V, Fail>;
    fn default_branch(&mut self, repo: &str) -> Result<V, Fail>;
    /// Text of the file, "" for a presence-only entry, None when absent.
    fn read_file(&mut self, repo: &str, path: &str, refv: &V) -> Result<Option<String>, Fail>;
}

fn infra<T>(msg: String) -> Result<T, Fail> {
    Err(Fail::Infra(msg))
}

fn crash(msg: &str) -> Fail {
    Fail::Crash(msg.to_string())
}

// ── fixtures ────────────────────────────────────────────────────────────────

pub struct Fixtures {
    root: String,
    world: V,
    fail: Vec<V>,
}

fn read_text(path: &Path) -> Result<String, Fail> {
    let raw = std::fs::read(path).map_err(|e| crash(&format!("OSError: {}", os_error(&e, &path.to_string_lossy()))))?;
    String::from_utf8(raw).map_err(|_| crash("UnicodeDecodeError"))
}

impl Fixtures {
    pub fn new(root: &str) -> Result<Fixtures, Fail> {
        let path = Path::new(root).join("world.json");
        let shown = path.to_string_lossy().to_string();
        let world = match std::fs::read(&path) {
            Err(e) => return infra(format!("cannot read fixture world {}: {}", root, os_error(&e, &shown))),
            Ok(raw) => match String::from_utf8(raw) {
                Err(e) => {
                    let at = e.utf8_error().valid_up_to();
                    let b = e.as_bytes()[at];
                    return infra(format!(
                        "cannot read fixture world {}: 'utf-8' codec can't decode byte 0x{:02x} in position {}: invalid start byte",
                        root, b, at
                    ));
                }
                Ok(t) => json::loads(&t).map_err(|e| Fail::Infra(format!("cannot read fixture world {}: {}", root, e)))?,
            },
        };
        let fail = match world.get("fail") {
            Some(V::List(l)) => l.clone(),
            Some(V::Str(s)) => s.chars().map(|c| V::Str(c.to_string())).collect(),
            Some(V::Dict(d)) => d.iter().map(|(k, _)| k.clone()).collect(),
            None => vec![],
            Some(_) => return Err(crash("TypeError: object is not iterable")),
        };
        Ok(Fixtures { root: root.to_string(), world, fail })
    }

    fn failing(&self, what: &str) -> bool {
        self.fail.iter().any(|x| x.as_str() == Some(what))
    }

    fn body(&self, d: &V) -> Result<V, Fail> {
        if let Some(bf) = d.get("body_file") {
            return Ok(V::Str(read_text(&Path::new(&self.root).join(py_str(bf)))?));
        }
        Ok(d.get("body").cloned().unwrap_or(V::s("")))
    }

    fn issue_of(&self, i: &V) -> Result<V, Fail> {
        let repo = i.get("repo").cloned().ok_or_else(|| crash("KeyError: 'repo'"))?;
        let number = i.get("number").cloned().ok_or_else(|| crash("KeyError: 'number'"))?;
        let url = match i.get("url") {
            Some(u) => u.clone(),
            None => V::Str(format!("https://github.com/{}/issues/{}", py_str(&repo), py_str(&number))),
        };
        let mut comments = vec![];
        if let Some(cs) = i.get("comments") {
            let items = match cs {
                V::List(l) => l.clone(),
                _ => return Err(crash("TypeError: comments")),
            };
            for (n, c) in items.iter().enumerate() {
                comments.push(V::Dict(vec![
                    (V::s("id"), c.get("id").cloned().unwrap_or(V::Int(n as i128))),
                    (V::s("created_at"), c.get("created_at").cloned().unwrap_or(V::s(""))),
                    (V::s("body"), self.body(c)?),
                ]));
            }
        }
        Ok(V::Dict(vec![
            (V::s("repo"), repo),
            (V::s("number"), number),
            (V::s("title"), i.get("title").cloned().unwrap_or(V::s(""))),
            (V::s("url"), url),
            (V::s("labels"), i.get("labels").cloned().unwrap_or(V::List(vec![]))),
            (V::s("body"), self.body(i)?),
            (V::s("comments"), V::List(comments)),
        ]))
    }

    fn issues(&self) -> Vec<V> {
        match self.world.get("issues") {
            Some(V::List(l)) => l.clone(),
            _ => vec![],
        }
    }

    fn files(&self, repo: &str) -> Option<V> {
        self.world.get("files").and_then(|f| f.get(repo)).cloned()
    }
}

impl Source for Fixtures {
    fn name(&self) -> String {
        format!("fixtures:{}", self.root)
    }

    fn discover(&mut self, org: &str, label: &str) -> Result<Vec<V>, Fail> {
        if self.failing("search") {
            return infra("fixture: search failed".into());
        }
        let mut out = vec![];
        for i in self.issues() {
            let labels = i.get("labels").cloned().unwrap_or(V::List(vec![]));
            if !py_in(label, &labels)? {
                continue;
            }
            if i.get("state").map(|s| s.as_str() == Some("open")).unwrap_or(true) {
                let repo = i.get("repo").map(py_str).unwrap_or_default();
                if repo.split('/').next() == Some(org) {
                    out.push(self.issue_of(&i)?);
                }
            }
        }
        Ok(out)
    }

    fn issue(&mut self, repo: &str, number: i128) -> Result<V, Fail> {
        for i in self.issues() {
            if i.get("repo").and_then(|r| r.as_str()) == Some(repo) && i.get("number") == Some(&V::Int(number)) {
                return self.issue_of(&i);
            }
        }
        infra(format!("fixture: no issue {}#{}", repo, number))
    }

    fn default_branch(&mut self, repo: &str) -> Result<V, Fail> {
        if self.failing("repo") || self.files(repo).is_none() {
            return infra(format!("fixture: repo {} is not readable", repo));
        }
        Ok(self.world.get("default_branch").and_then(|d| d.get(repo)).cloned().unwrap_or(V::s("main")))
    }

    fn read_file(&mut self, repo: &str, path: &str, _refv: &V) -> Result<Option<String>, Fail> {
        let Some(files) = self.files(repo) else {
            return infra(format!("fixture: repo {} is not readable", repo));
        };
        match files.get(path) {
            None => Ok(None),
            Some(V::None) => Ok(Some(String::new())),
            Some(f) => Ok(Some(read_text(&Path::new(&self.root).join(py_str(f)))?)),
        }
    }
}

// ── GitHub ──────────────────────────────────────────────────────────────────

pub fn which(cmd: &str) -> Option<PathBuf> {
    let path = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path) {
        let p = dir.join(cmd);
        if let Ok(m) = std::fs::metadata(&p) {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                if m.is_file() && m.permissions().mode() & 0o111 != 0 {
                    return Some(p);
                }
            }
            #[cfg(not(unix))]
            if m.is_file() {
                return Some(p);
            }
        }
    }
    None
}

type Resp = (u16, HashMap<String, String>, Vec<u8>);

pub struct GitHub {
    api: String,
    token: Option<String>,
    http: String,
    branches: HashMap<String, V>,
}

impl GitHub {
    pub fn new(api: &str, token: Option<String>, http: &str) -> GitHub {
        let http = if http == "auto" {
            if which("curl").is_some() { "curl" } else { "urllib" }
        } else {
            http
        };
        GitHub { api: api.trim_end_matches('/').to_string(), token, http: http.to_string(), branches: HashMap::new() }
    }

    fn get(&self, url: &str, accept: &str) -> Result<Resp, Fail> {
        let mut headers = vec![
            ("Accept", accept.to_string()),
            ("User-Agent", "seam-check".to_string()),
            ("X-GitHub-Api-Version", "2022-11-28".to_string()),
        ];
        if let Some(t) = &self.token {
            headers.push(("Authorization", format!("Bearer {}", t)));
        }
        if self.http == "curl" {
            curl(url, &headers)
        } else {
            plain_http(url, &headers)
        }
    }

    fn json(&self, url: &str) -> Result<(V, HashMap<String, String>), Fail> {
        let (status, hdrs, body) = self.get(url, "application/vnd.github+json")?;
        if status != 200 {
            return infra(format!("GET {} -> HTTP {}{}", url, status, rate_note(&hdrs)));
        }
        let text = match String::from_utf8(body) {
            Ok(t) => t,
            Err(e) => {
                let at = e.utf8_error().valid_up_to();
                return infra(format!(
                    "GET {} -> unparseable JSON: 'utf-8' codec can't decode byte 0x{:02x} in position {}: invalid start byte",
                    url,
                    e.as_bytes()[at],
                    at
                ));
            }
        };
        match json::loads(&text) {
            Ok(v) => Ok((v, hdrs)),
            Err(e) => infra(format!("GET {} -> unparseable JSON: {}", url, e)),
        }
    }

    fn pages(&self, first: String) -> Result<Vec<V>, Fail> {
        let mut out = vec![];
        let mut url = first;
        while !url.is_empty() {
            let (data, hdrs) = self.json(&url)?;
            out.push(data);
            url = link_next(hdrs.get("link").map(String::as_str).unwrap_or("")).unwrap_or_default();
        }
        Ok(out)
    }

    fn comments(&self, repo: &str, number: &V) -> Result<Vec<V>, Fail> {
        let mut out = vec![];
        let url = format!("{}/repos/{}/issues/{}/comments?per_page=100", self.api, repo, py_str(number));
        for page in self.pages(url)? {
            let V::List(items) = page else { return Err(crash("TypeError: comments page")) };
            for c in items {
                out.push(V::Dict(vec![
                    (V::s("id"), c.get("id").cloned().ok_or_else(|| crash("KeyError: 'id'"))?),
                    (V::s("created_at"), c.get("created_at").cloned().unwrap_or(V::s(""))),
                    (V::s("body"), c.get_or("body").cloned().unwrap_or(V::s(""))),
                    (V::s("url"), c.get("html_url").cloned().unwrap_or(V::s(""))),
                ]));
            }
        }
        Ok(out)
    }

    fn issue_of(&self, i: &V, repo: &str) -> Result<V, Fail> {
        let number = i.get("number").cloned().ok_or_else(|| crash("KeyError: 'number'"))?;
        let mut labels = vec![];
        if let Some(V::List(l)) = i.get("labels") {
            for lb in l {
                labels.push(lb.get("name").cloned().ok_or_else(|| crash("KeyError: 'name'"))?);
            }
        }
        Ok(V::Dict(vec![
            (V::s("repo"), V::s(repo)),
            (V::s("number"), number.clone()),
            (V::s("title"), i.get("title").cloned().unwrap_or(V::s(""))),
            (V::s("url"), i.get("html_url").cloned().unwrap_or(V::s(""))),
            (V::s("labels"), V::List(labels)),
            (V::s("body"), i.get_or("body").cloned().unwrap_or(V::s(""))),
            (V::s("comments"), V::List(self.comments(repo, &number)?)),
        ]))
    }
}

fn rate_note(h: &HashMap<String, String>) -> String {
    if h.get("x-ratelimit-remaining").map(String::as_str) == Some("0") {
        format!(
            " (rate limit exhausted; resets at {})",
            h.get("x-ratelimit-reset").map(String::as_str).unwrap_or("?")
        )
    } else {
        String::new()
    }
}

impl Source for GitHub {
    fn name(&self) -> String {
        format!("github:{}", self.api)
    }

    fn discover(&mut self, org: &str, label: &str) -> Result<Vec<V>, Fail> {
        let q = quote(&format!("org:{} label:{} is:issue is:open", org, label));
        let mut out = vec![];
        for page in self.pages(format!("{}/search/issues?q={}&per_page=100", self.api, q))? {
            if page.get_or("incomplete_results").is_some() {
                return infra("issue search returned incomplete_results; refusing a partial answer".into());
            }
            let items = match page.get("items") {
                Some(V::List(l)) => l.clone(),
                _ => vec![],
            };
            for i in items {
                let ru = i.get("repository_url").map(py_str).ok_or_else(|| crash("KeyError: 'repository_url'"))?;
                let parts: Vec<&str> = ru.trim_end_matches('/').split('/').collect();
                let repo = parts[parts.len().saturating_sub(2)..].join("/");
                out.push(self.issue_of(&i, &repo)?);
            }
        }
        Ok(out)
    }

    fn issue(&mut self, repo: &str, number: i128) -> Result<V, Fail> {
        let (data, _) = self.json(&format!("{}/repos/{}/issues/{}", self.api, repo, number))?;
        self.issue_of(&data, repo)
    }

    fn default_branch(&mut self, repo: &str) -> Result<V, Fail> {
        if !self.branches.contains_key(repo) {
            let (data, _) = self.json(&format!("{}/repos/{}", self.api, repo))?;
            let b = data.get("default_branch").cloned().ok_or_else(|| crash("KeyError: 'default_branch'"))?;
            self.branches.insert(repo.to_string(), b);
        }
        Ok(self.branches[repo].clone())
    }

    fn read_file(&mut self, repo: &str, path: &str, refv: &V) -> Result<Option<String>, Fail> {
        let V::Str(r) = refv else {
            return Err(crash(&format!("TypeError: quote() doesn't support '{}' objects", refv.type_name())));
        };
        let url = format!("{}/repos/{}/contents/{}?ref={}", self.api, repo, quote(path), quote(r));
        let (status, hdrs, body) = self.get(&url, "application/vnd.github.raw")?;
        if status == 404 {
            return Ok(None);
        }
        if status != 200 {
            return infra(format!("GET {} -> HTTP {}{}", url, status, rate_note(&hdrs)));
        }
        Ok(Some(String::from_utf8_lossy(&body).into_owned()))
    }
}

/// A private temp directory (0700), removed on drop.
struct TempDir(PathBuf);

impl TempDir {
    fn new() -> std::io::Result<TempDir> {
        use std::sync::atomic::{AtomicU64, Ordering};
        static N: AtomicU64 = AtomicU64::new(0);
        let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        let p = std::env::temp_dir().join(format!(
            "seam-check-{}-{}-{}",
            std::process::id(),
            N.fetch_add(1, Ordering::Relaxed),
            nanos
        ));
        let mut b = std::fs::DirBuilder::new();
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            b.mode(0o700);
        }
        b.create(&p)?;
        Ok(TempDir(p))
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn curl(url: &str, headers: &[(&str, String)]) -> Result<Resp, Fail> {
    let d = TempDir::new().map_err(|e| crash(&format!("OSError: {}", e)))?;
    let (hfile, out, dump) = (d.0.join("req"), d.0.join("body"), d.0.join("resp"));
    // Headers from a 0600 file, so the token never appears in argv.
    {
        let mut o = std::fs::OpenOptions::new();
        o.write(true).create(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            o.mode(0o600);
        }
        let mut fh = o.open(&hfile).map_err(|e| crash(&format!("OSError: {}", e)))?;
        let text: String = headers.iter().map(|(k, v)| format!("{}: {}\n", k, v)).collect();
        fh.write_all(text.as_bytes()).map_err(|e| crash(&format!("OSError: {}", e)))?;
    }
    let p = std::process::Command::new("curl")
        .args(["-sS", "--max-time", "30", "-H"])
        .arg(format!("@{}", hfile.display()))
        .arg("-D")
        .arg(&dump)
        .arg("-o")
        .arg(&out)
        .args(["-w", "%{http_code}", url])
        .stdin(std::process::Stdio::null())
        .output()
        .map_err(|e| crash(&format!("FileNotFoundError: {}", e)))?;
    if !p.status.success() {
        let code = p.status.code().unwrap_or(-1);
        return infra(format!(
            "GET {} failed: curl exit {}: {}",
            url,
            code,
            String::from_utf8_lossy(&p.stderr).trim()
        ));
    }
    let so = String::from_utf8_lossy(&p.stdout);
    let so = so.trim();
    let status: u16 = if so.is_empty() { 0 } else { so.parse().map_err(|_| crash("ValueError: http_code"))? };
    let mut hdrs = HashMap::new();
    let raw = std::fs::read(&dump).map_err(|e| crash(&format!("OSError: {}", e)))?;
    let latin1: String = raw.iter().map(|b| *b as char).collect();
    for line in latin1.split_inclusive('\n') {
        if let Some((k, v)) = line.split_once(':') {
            hdrs.insert(k.trim().to_lowercase(), v.trim().to_string());
        }
    }
    let body = std::fs::read(&out).map_err(|e| crash(&format!("OSError: {}", e)))?;
    Ok((status, hdrs, body))
}

/// The `--http urllib` path: HTTP/1.1 over a std TcpStream, plain http:// only.
fn plain_http(url: &str, headers: &[(&str, String)]) -> Result<Resp, Fail> {
    let Some(rest) = url.strip_prefix("http://") else {
        return infra(format!("GET {} failed: <urlopen error only http:// is supported without curl>", url));
    };
    let (hostport, path) = match rest.find('/') {
        Some(i) => (&rest[..i], &rest[i..]),
        None => (rest, "/"),
    };
    let addr = if hostport.contains(':') { hostport.to_string() } else { format!("{}:80", hostport) };
    let timeout = std::time::Duration::from_secs(30);
    let conn = std::net::ToSocketAddrs::to_socket_addrs(&addr)
        .ok()
        .and_then(|mut a| a.next())
        .ok_or_else(|| Fail::Infra(format!("GET {} failed: <urlopen error [Errno 8] nodename nor servname provided, or not known>", url)))
        .and_then(|sa| {
            std::net::TcpStream::connect_timeout(&sa, timeout)
                .map_err(|e| Fail::Infra(format!("GET {} failed: <urlopen error {}>", url, os_error_short(&e))))
        })?;
    let mut s = conn;
    let _ = s.set_read_timeout(Some(timeout));
    let mut req = format!("GET {} HTTP/1.1\r\nHost: {}\r\nAccept-Encoding: identity\r\nConnection: close\r\n", path, hostport);
    for (k, v) in headers {
        req.push_str(&format!("{}: {}\r\n", k, v));
    }
    req.push_str("\r\n");
    s.write_all(req.as_bytes())
        .map_err(|e| Fail::Infra(format!("GET {} failed: <urlopen error {}>", url, os_error_short(&e))))?;
    let mut raw = vec![];
    s.read_to_end(&mut raw).map_err(|e| Fail::Infra(format!("GET {} failed: {}", url, os_error_short(&e))))?;
    let split = raw.windows(4).position(|w| w == b"\r\n\r\n").ok_or_else(|| {
        Fail::Infra(format!("GET {} failed: Remote end closed connection without response", url))
    })?;
    let head: String = raw[..split].iter().map(|b| *b as char).collect();
    let mut body = raw[split + 4..].to_vec();
    let mut lines = head.split("\r\n");
    let status: u16 = lines
        .next()
        .and_then(|l| l.split_whitespace().nth(1))
        .and_then(|c| c.parse().ok())
        .ok_or_else(|| Fail::Infra(format!("GET {} failed: bad status line", url)))?;
    let mut hdrs = HashMap::new();
    for l in lines {
        if let Some((k, v)) = l.split_once(':') {
            hdrs.insert(k.trim().to_lowercase(), v.trim().to_string());
        }
    }
    if hdrs.get("transfer-encoding").is_some_and(|t| t.eq_ignore_ascii_case("chunked")) {
        body = dechunk(&body);
    } else if let Some(n) = hdrs.get("content-length").and_then(|n| n.parse::<usize>().ok()) {
        body.truncate(n);
    }
    Ok((status, hdrs, body))
}

fn dechunk(mut b: &[u8]) -> Vec<u8> {
    let mut out = vec![];
    loop {
        let Some(nl) = b.windows(2).position(|w| w == b"\r\n") else { break };
        let size = std::str::from_utf8(&b[..nl])
            .ok()
            .and_then(|s| usize::from_str_radix(s.split(';').next().unwrap_or("").trim(), 16).ok())
            .unwrap_or(0);
        if size == 0 || nl + 2 + size > b.len() {
            break;
        }
        out.extend_from_slice(&b[nl + 2..nl + 2 + size]);
        b = &b[(nl + 4 + size).min(b.len())..];
    }
    out
}

/// `[Errno 61] Connection refused`, as Python prints an OSError without a path.
fn os_error_short(e: &std::io::Error) -> String {
    match e.raw_os_error() {
        Some(code) => {
            let t = e.to_string();
            let t = t.rfind(" (os error ").map(|i| t[..i].to_string()).unwrap_or(t);
            format!("[Errno {}] {}", code, t)
        }
        None if e.kind() == std::io::ErrorKind::TimedOut || e.kind() == std::io::ErrorKind::WouldBlock => {
            "timed out".into()
        }
        None => e.to_string(),
    }
}

/// `resolve_token`: GITHUB_TOKEN, GH_TOKEN, `gh auth token`; only for the GitHub API host.
pub fn resolve_token(api: &str, env: &dyn Fn(&str) -> Option<String>) -> Option<String> {
    let mine = env("GITHUB_API_URL").unwrap_or_else(|| GITHUB_API.to_string());
    let api = api.trim_end_matches('/');
    if api != GITHUB_API && api != mine.trim_end_matches('/') {
        return None; // never send a GitHub token to any other host
    }
    for k in ["GITHUB_TOKEN", "GH_TOKEN"] {
        if let Some(t) = env(k).filter(|t| !t.is_empty()) {
            return Some(t);
        }
    }
    if which("gh").is_some() {
        if let Ok(p) = std::process::Command::new("gh").args(["auth", "token"]).stdin(std::process::Stdio::null()).output() {
            let t = String::from_utf8_lossy(&p.stdout).trim().to_string();
            if p.status.success() && !t.is_empty() {
                return Some(t);
            }
        }
    }
    None
}
