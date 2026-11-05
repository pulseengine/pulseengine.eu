"""Private confidential-terms check for commit-merge-guard.py (rule 8).

The user keeps a private list of terms at ~/.config/pulseengine/confidential-terms.txt:
one case-insensitive extended regex per line, blank lines and whole-line `#`
comments ignored. This module never ships terms and never prints one: a match
is reported by its LINE NUMBER in that file, nothing else. A missing or
unreadable file means nothing to check, silently.

Scanned text: the body and title a `gh pr create|edit|comment`,
`gh issue create|comment` or `gh release create` carries (flag values, heredoc
bodies, the contents of --body-file / --notes-file), and for `git push` the
added lines and commit messages of the commits being pushed (@{u}..HEAD, else
origin/main..HEAD, else origin/master..HEAD).

Python 3.9+, stdlib only. Every function fails open.
"""

from __future__ import annotations

import os
import re
import subprocess

TERMS_REL = (".config", "pulseengine", "confidential-terms.txt")
BODY_FLAGS = ("-b", "--body", "-t", "--title", "-n", "--notes", "-m", "--message")
FILE_FLAGS = ("-F", "--body-file", "--notes-file")
MAX_BYTES = 4_000_000
MAX_LINES_NAMED = 10
GIT_TIMEOUT_S = 5


def terms_path():
    return os.path.join(os.path.expanduser("~"), *TERMS_REL)


def load_terms(path=None):
    """[(line number, compiled regex)] from the terms file; [] when missing or empty."""
    out = []
    try:
        with open(path or terms_path(), encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                try:
                    out.append((n, re.compile(s, re.IGNORECASE)))
                except re.error:
                    continue
    except OSError:
        return []
    return out


def match_lines(text, terms):
    """Sorted line numbers of the terms that match `text`. Never returns the text."""
    if not text or not terms:
        return []
    return sorted({n for n, rx in terms if rx.search(text)})


def body_file_text(tokens, cwd):
    """Contents of the files named by --body-file / --notes-file / -F in `tokens`."""
    parts = []
    for i, t in enumerate(tokens):
        path = None
        if t in FILE_FLAGS and i + 1 < len(tokens):
            path = tokens[i + 1]
        elif t.startswith(("--body-file=", "--notes-file=")):
            path = t.split("=", 1)[1]
        if not path or path == "-":
            continue
        try:
            with open(os.path.join(cwd, os.path.expanduser(path)), encoding="utf-8",
                      errors="replace") as f:
                parts.append(f.read(MAX_BYTES))
        except OSError:
            continue
    return "\n".join(parts)


_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def heredoc_bodies(cmd):
    """Every heredoc body in `cmd`, whatever flag opened it (a body is published text)."""
    lines = cmd.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        i += 1
        for _, delim in _HEREDOC.findall(line):
            body = []
            while i < len(lines) and lines[i].strip() != delim:
                body.append(lines[i])
                i += 1
            i += 1
            out.append("\n".join(body))
    return "\n".join(out)


def _git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                           errors="replace", timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout[:MAX_BYTES] if r.returncode == 0 else None


def push_text(cwd):
    """Added lines and commit messages of the commits a `git push` would send."""
    if not os.path.isdir(cwd):
        return ""
    for base in ("@{u}", "origin/main", "origin/master"):
        if _git(["rev-parse", "--verify", "-q", base], cwd) is None:
            continue
        rng = "%s..HEAD" % base
        diff = _git(["diff", "-U0", "--no-color", rng], cwd)
        log = _git(["log", "--format=%B", rng], cwd)
        if diff is None and log is None:
            continue
        added = [l[1:] for l in (diff or "").splitlines()
                 if l.startswith("+") and not l.startswith("+++")]
        return "\n".join(added) + "\n" + (log or "")
    return ""


def ask_message(what, lines):
    shown = ", ".join(str(n) for n in lines[:MAX_LINES_NAMED])
    more = " (+%d more)" % (len(lines) - MAX_LINES_NAMED) if len(lines) > MAX_LINES_NAMED else ""
    return ("pulseengine-claude commit-merge-guard: this %s matches line(s) %s%s of the owner's private "
            "confidential-terms list. Remove or reword the matching text; the list and the match are "
            "deliberately not shown. If it is meant to go out, the owner approves this call." %
            (what, shown, more))
