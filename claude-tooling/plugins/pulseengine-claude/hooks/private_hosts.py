"""Host-shaped values that must not reach a repository (pulseengine-claude).

Shared by private-host-guard.py (Edit, Write, MultiEdit) and
commit-merge-guard.py (commit messages and PR text). Python 3.9+, stdlib only.

What counts as host-shaped:
  mdns/lan   a dotted name ending in .local, .lan, .home.arpa or .ts.net
             (`buildbox.local`, not `settings.local.json`, `.env.local`, `*.local`)
  ipv4       RFC 1918 (10/8, 172.16/12, 192.168/16) and CGNAT 100.64/10
  ula        IPv6 unique-local fc00::/7 (`fd12:3456::1`)
  volumes    a macOS mount path, /Volumes/<name>
  home       the owner's own home directory ($HOME at run time, never a
             literal here), matched on a path boundary

A hit is allowed by a line in the repo's `.private-hostname-allow` or the
user's ~/.config/pulseengine-claude/private-hostname-allow. A line is an
fnmatch glob on the value (`*.local`, `10.0.0.1`), or `file:<glob>` on the
repo-relative path (`file:tests/fixtures/*`). `#` starts a comment.
"""

import fnmatch
import os
import re

ALLOW_NAME = "private-hostname-allow"
REPO_ALLOW = ".private-hostname-allow"
TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")

_PATTERNS = [
    ("mdns/lan", re.compile(
        r"(?<![\w.*-])(?:[a-z0-9][a-z0-9-]*\.)+(?:local|lan|home\.arpa|ts\.net)"
        r"(?![\w-])(?!\.[a-z0-9])", re.I)),
    ("ipv4", re.compile(
        r"(?<![\w.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168|"
        r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))\.\d{1,3}\.\d{1,3}(?![\w.]*\d)")),
    ("ula", re.compile(
        r"(?<![\w:])f[cd][0-9a-f]{2}:(?:[0-9a-f]{0,4}:){1,6}[0-9a-f]{0,4}(?![\w:])", re.I)),
    ("volumes", re.compile(r"/Volumes/[A-Za-z0-9][^\s'\"`)\]}>,;]*")),
]


def _home_pattern(home):
    home = (home or "").rstrip("/")
    # "/" or "/root"-short homes would match far too much; a real owner home
    # has at least two path components.
    if home.count("/") < 2:
        return None
    return re.compile(re.escape(home) + r"(?![\w.-])")


def find(text, home=None):
    """[(kind, value)] for every host-shaped value in text, in order, unique."""
    if not isinstance(text, str) or not text:
        return []
    pats = list(_PATTERNS)
    hp = _home_pattern(os.path.expanduser("~") if home is None else home)
    if hp:
        pats.append(("home", hp))
    seen, out = set(), []
    for kind, rx in pats:
        for m in rx.finditer(text):
            v = m.group(0).rstrip(".")
            if kind == "ula" and v.count(":") < 2:
                continue
            if v not in seen:
                seen.add(v)
                out.append((kind, v))
    return out


def mask(value):
    v = value.strip()
    return "%s***%s" % (v[:2], v[-3:]) if len(v) > 6 else "***"


def realpath(p):
    try:
        return os.path.realpath(os.path.expanduser(p))
    except (OSError, ValueError):
        return p


def under(path, root):
    path, root = realpath(path), realpath(root)
    return path == root or path.startswith(root.rstrip("/") + "/")


def temp_roots(env=None):
    env = os.environ if env is None else env
    roots = list(TEMP_ROOTS)
    t = (env.get("TMPDIR") or "").strip()
    if t:
        roots.append(t)
    return roots


def in_temp(path, env=None):
    return any(under(path, r) for r in temp_roots(env))


def _read_allow(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if line:
                    out.append(line)
    except OSError:
        pass
    return out


def user_allow_path():
    return os.path.join(os.path.expanduser("~"), ".config", "pulseengine-claude", ALLOW_NAME)


def allow_rules(repo_top):
    rules = _read_allow(user_allow_path())
    if repo_top:
        rules += _read_allow(os.path.join(repo_top, REPO_ALLOW))
    return rules


def allowed(value, rel_path, rules):
    for r in rules:
        if r.startswith("file:"):
            if rel_path and fnmatch.fnmatch(rel_path, r[5:].strip()):
                return True
        elif fnmatch.fnmatch(value.lower(), r.lower()):
            return True
    return False


def filter_hits(hits, rel_path, repo_top):
    rules = allow_rules(repo_top)
    return [(k, v) for k, v in hits if not allowed(v, rel_path, rules)]


_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_MSG_LINE = re.compile(r"\bcommit\b|\s-[A-Za-z]*[mF]\b|--(?:message|body|title|notes|file|body-file)\b")


def message_text(cmd, flags=("-m", "--message")):
    """The message a command carries: values of `flags` and heredoc bodies
    opened on a line that names a commit or a message flag. Not the rest of
    the command, whose `cd /home/...` paths are not published anywhere."""
    if not isinstance(cmd, str):
        return ""
    parts = []
    lines = cmd.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        for _, delim in _HEREDOC.findall(line):
            body = []
            while i < len(lines) and lines[i].strip() != delim:
                body.append(lines[i])
                i += 1
            i += 1
            if _MSG_LINE.search(line):
                parts.append("\n".join(body))
    shorts = "".join(f[1] for f in flags if re.fullmatch(r"-[A-Za-z]", f))
    longs = "|".join(re.escape(f[2:]) for f in flags if f.startswith("--"))
    alts = []
    if shorts:
        alts.append(r"-[A-Za-z]*[%s]" % re.escape(shorts))
    if longs:
        alts.append(r"--(?:%s)" % longs)
    if alts:
        rx = re.compile(r"(?:^|[\s;&|(])(?:%s)(?:=|\s+)(?:\"((?:[^\"\\]|\\.)*)\"|'([^']*)'|(\S+))"
                        % "|".join(alts), re.S)
        for m in rx.finditer(cmd):
            parts.append(next(g for g in m.groups() if g is not None))
    return "\n".join(parts)


def describe(hits, limit=4):
    parts = ["%s %s" % (k, mask(v)) for k, v in hits[:limit]]
    if len(hits) > limit:
        parts.append("+%d more" % (len(hits) - limit))
    return ", ".join(parts)
