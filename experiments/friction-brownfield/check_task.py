#!/usr/bin/env python3
"""check_task.py: the acceptance checks for one v2 brownfield task.

Pre-registration: docs/experiments/2026-11-friction-brownfield.md, section
"The success oracle, independent of friction". Each check is one command with
one exit code (0 pass, 1 fail, 2 could not run):

    check_task.py check  TASK_DIR LANG N     one check, N in 1..10, LANG c|rust
    check_task.py all    TASK_DIR [LANG...]  every check, each as its own subprocess
    check_task.py negctl TASK_DIR LANG N     break check N in place, expect exit 1,
                                             restore by the reverse edit, expect exit 0
    check_task.py derive BASE COMPLETE OUT   write the edit list BASE -> COMPLETE
    check_task.py assemble TASK_DIR LANG AUTHOR_TREE PATHS  split an authoring tree into the task layout
    check_task.py manifest TASK_DIR          sha256 of every task file (for tasks.sha256)
    check_task.py vectors-sanity VECTORS_JSON  the oracle-of-the-oracle check alone
    check_task.py self-test                  pure-function tests, no toolchain needed

The checks (doc bullet in brackets):
  1  baseline: builds without warnings, passes the visible tests and the regression suite  [b1]
  2  baseline: fails the new-behaviour suite, also with the new names supplied             [b2]
  3  reference: builds, passes visible + both hidden suites, adds no new findings at
     the top analyser level, and (Rust) passes every Kani harness                          [b3]
  4  invariant mutant: passes the new-behaviour suite, fails the regression suite          [b4]
  5  visible-pass mutant: passes the visible tests, fails a hidden suite                   [b5]
  6  probes on the reference: a new finding from each real tool, B1 and B2 (C);
     B1, B2 and B3 (Rust)                                                                  [b6]
  7  visible and hidden suites share no case (names, request sequences, a scan of
     hand-written visible tests for a whole hidden request ADU);
     every stored vector file is what the generator writes                                 [b7]
  8  every name the hidden suites and Kani harnesses use that the baseline lacks
     appears in the change request                                                         [b8]
  9  the baseline prompt stays under the 90K-token cap (a conservative byte bound)         [b9]
 10  the ablation split re-derives (strip(marked) == baseline, baseline + reference ==
     complete) and the baseline's analyser noise is inside the task's noise budget         [review]

Task layout (private, on the bench machine; only its manifest is public):
  TASK/task.json, TASK/change-request.md, TASK/vectors/{vectors.json,gen_vectors.py}
  TASK/<lang>/marked/     Vibe's tree with FC17 markers (the authoring output)
  TASK/<lang>/complete/   marked, marker lines removed (the complete system)
  TASK/<lang>/repo/       the baseline (what the model sees)
  TASK/<lang>/reference.edits.json
  TASK/<lang>/hidden/{regression,new}/  (Rust also hidden/kani/)
Mutants and probes are edit lists in task.json, applied on top of the reference.
TASK/negctl.json holds one in-place edit per check that must turn it red.

Finding fingerprint: (tool, rule, file, the flagged line's text with whitespace
collapsed), compared as multisets. The doc's fingerprint also has the
enclosing function; it is left out here, which only merges identical lines in
different functions of one file, and the multiset count keeps them apart.
"""
import collections
import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

CFLAGS = ["-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-O1"]
CC = os.environ.get("FXM_CC", "cc")
CPPCHECK = os.environ.get("FXM_CPPCHECK", "cppcheck")
CPPCHECK_ARGS = ["--std=c11", "--enable=warning,style,performance,portability", "--addon=misra",
                 "--suppress=missingIncludeSystem", "--quiet",
                 "--template={file}:{line}:{column}: {severity}: {id}: {message}"]
RUST_TOOLCHAIN = os.environ.get("FXM_RUST_TOOLCHAIN", "1.96.1")
CLIPPY_LINTS = ["-W", "clippy::all", "-W", "clippy::pedantic"]
TIMEOUT = {"build": 300, "test": 300, "cppcheck": 300, "clippy": 300, "kani": 900}
TOKEN_CAP = 90_000
BYTES_PER_TOKEN_BOUND = 2.0      # pessimistic: code tokenises at ~3.5-4 bytes per token
PROMPT_RESERVE = 8_000           # CLI, rules paragraph, answer format (the doc's 8K)
SUMMARY = re.compile(r"passed (\d+) failed (\d+)")
BUILD_DIR = os.environ.get("FXM_BUILD_DIR")
if BUILD_DIR:
    pathlib.Path(BUILD_DIR).mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = BUILD_DIR


class CouldNotRun(Exception):
    pass


# ── Edits: the {path, old, new} answer format ────────────────────────────────
def apply_edits(root, edits):
    """Apply edits in order; raise ValueError on any edit that does not apply."""
    root = pathlib.Path(root)
    for i, e in enumerate(edits):
        rel = pathlib.PurePosixPath(e["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"edit {i}: path outside the tree: {e['path']}")
        p = root / rel
        if e["old"] == "":
            if p.exists():
                raise ValueError(f"edit {i}: {e['path']} exists; empty old creates a new file")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(e["new"], encoding="utf-8")
            continue
        if not p.is_file():
            raise ValueError(f"edit {i}: no such file {e['path']}")
        text = p.read_text(encoding="utf-8")
        n = text.count(e["old"])
        if n != 1:
            raise ValueError(f"edit {i}: old occurs {n} times in {e['path']}")
        p.write_text(text.replace(e["old"], e["new"], 1), encoding="utf-8")


def derive_file_edits(path, a, b):
    """Edits turning text a into text b, bottom-up, each old unique when applied."""
    al, bl = a.splitlines(keepends=True), b.splitlines(keepends=True)
    ops = [o for o in difflib.SequenceMatcher(a=al, b=bl, autojunk=False).get_opcodes() if o[0] != "equal"]
    edits, cur = [], list(al)
    for _, i1, i2, j1, j2 in reversed(ops):
        ctx = 0 if i2 > i1 else 1
        while True:
            lo, hi = max(0, i1 - ctx), min(len(cur), i2 + ctx)
            old = "".join(cur[lo:hi])
            if old and "".join(cur).count(old) == 1:
                break
            if lo == 0 and hi == len(cur):
                break
            ctx += 1
        new = "".join(cur[lo:i1]) + "".join(bl[j1:j2]) + "".join(cur[i2:hi])
        if not old:                       # empty file gaining content
            raise ValueError(f"{path}: cannot anchor an edit in an empty file")
        edits.append({"path": path, "old": old, "new": new})
        cur[lo:hi] = new.splitlines(keepends=True)
    return edits


def tree_files(root):
    root = pathlib.Path(root)
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def derive_edits(base, complete):
    base, complete = pathlib.Path(base), pathlib.Path(complete)
    bf, cf = set(tree_files(base)), set(tree_files(complete))
    if bf - cf:
        raise ValueError(f"the reference would delete files: {sorted(bf - cf)}")
    edits = []
    for f in sorted(cf):
        new = (complete / f).read_text(encoding="utf-8")
        if f not in bf:
            edits.append({"path": f, "old": "", "new": new})
            continue
        old = (base / f).read_text(encoding="utf-8")
        if old != new:
            edits += derive_file_edits(f, old, new)
    return edits


def trees_equal(a, b):
    fa, fb = tree_files(a), tree_files(b)
    if fa != fb:
        return False, f"file sets differ: only-left {sorted(set(fa) - set(fb))} only-right {sorted(set(fb) - set(fa))}"
    for f in fa:
        if (pathlib.Path(a) / f).read_bytes() != (pathlib.Path(b) / f).read_bytes():
            return False, f"{f} differs"
    return True, ""


# ── Markers (same rule as the strip_fc17.py given to the author) ─────────────
BEGIN = re.compile(r"^\s*(/\*\s*FC17-BEGIN\s*\*/|//\s*FC17-BEGIN)\s*$")
END = re.compile(r"^\s*(/\*\s*FC17-END\s*\*/|//\s*FC17-END)\s*$")


def strip_regions(text, keep_body):
    out, inside = [], False
    for line in text.splitlines(keepends=True):
        if BEGIN.match(line):
            if inside:
                raise ValueError("nested FC17-BEGIN")
            inside = True
        elif END.match(line):
            if not inside:
                raise ValueError("FC17-END without BEGIN")
            inside = False
        elif keep_body or not inside:
            out.append(line)
    if inside:
        raise ValueError("FC17-BEGIN without END")
    return "".join(out)


def feature_only(marked_text):
    """True when a file has markers and nothing but includes, imports, comments
    and blank lines outside them: such a file is new in the reference, so the
    baseline leaves it out rather than keep an empty shell named after the feature."""
    if not any(BEGIN.match(ln) for ln in marked_text.splitlines()):
        return False
    rest = strip_regions(marked_text, keep_body=False)
    rest = re.sub(r"/\*.*?\*/", "", rest, flags=re.S)
    for ln in rest.splitlines():
        t = ln.strip()
        if t and not t.startswith(("#include", "//", "use ")):
            return False
    return True


# ── Running things ───────────────────────────────────────────────────────────
def run(cmd, cwd, timeout, env=None):
    e = dict(os.environ, RUSTUP_AUTO_INSTALL="0")
    e.update(env or {})
    try:
        p = subprocess.run(cmd, cwd=str(cwd), env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"timeout after {timeout}s: {' '.join(map(str, cmd))}"
    except FileNotFoundError as x:
        raise CouldNotRun(str(x))
    return p.returncode, p.stdout.decode("utf-8", "replace")


class Work:
    """A scratch directory under FXM_BUILD_DIR, removed afterwards."""

    def __enter__(self):
        self.d = pathlib.Path(tempfile.mkdtemp(prefix="fb-"))
        return self.d

    def __exit__(self, *a):
        shutil.rmtree(self.d, ignore_errors=True)


def materialize(task, lang, dst, variant=None):
    """Copy the baseline to dst and apply the reference and a variant's extra edits.
    variant: None (baseline), 'reference', or a key of task.json mutants/probes."""
    shutil.copytree(task / lang / "repo", dst)
    if variant is None:
        return dst
    apply_edits(dst, json.loads((task / lang / "reference.edits.json").read_text()))
    if variant != "reference":
        spec = json.loads((task / "task.json").read_text())[lang]
        extra = {**spec.get("mutants", {}), **spec.get("probes", {})}[variant]
        apply_edits(dst, extra["edits"])
    return dst


def suite_result(rc, out):
    m = SUMMARY.findall(out)
    if rc is None:
        return {"ran": False, "ok": False, "why": out[-400:]}
    if not m:
        return {"ran": False, "ok": False, "why": out[-1200:]}
    passed, failed = map(int, m[-1])
    return {"ran": True, "ok": rc == 0 and failed == 0 and passed > 0, "passed": passed, "failed": failed}


# C ---------------------------------------------------------------------------
def c_build(root, w):
    rc, out = run(["make", f"BUILD_DIR={w / 'mk'}", "all"], root, TIMEOUT["build"])
    return rc, [ln for ln in out.splitlines() if ": warning:" in ln or ": error:" in ln], out


def c_visible(root, w):
    rc, out = run(["make", f"BUILD_DIR={w / 'mk'}", "test"], root, TIMEOUT["test"])
    return suite_result(rc, out)


def c_hidden(root, suite_dir, w, defines=()):
    """Compile a hidden suite where the author kept it (ROOT/hidden/<name>/), so its
    relative includes resolve as they did at authoring time."""
    exe = w / ("h-" + suite_dir.name)
    placed = root / "hidden" / suite_dir.name
    if placed.exists():
        shutil.rmtree(placed)
    shutil.copytree(suite_dir, placed)
    suite_dir = placed
    srcs = sorted(str(p) for p in (root / "src").glob("*.c")) + sorted(str(p) for p in suite_dir.glob("*.c"))
    rc, out = run([CC, *CFLAGS, *[f"-D{d}" for d in defines], "-I", str(root / "include"), "-I", str(suite_dir),
                   *srcs, "-o", str(exe)], root, TIMEOUT["build"])
    if rc != 0:
        return {"ran": False, "ok": False, "compile_errors": out, "why": "did not compile"}
    rc, out = run([str(exe)], w, TIMEOUT["test"])
    return suite_result(rc, out)


C_MISSING = [re.compile(r"use of undeclared identifier '(\w+)'"), re.compile(r"call to undeclared function '(\w+)'"),
             re.compile(r"unknown type name '(\w+)'"), re.compile(r"no member named '(\w+)'"),
             re.compile(r"'([\w./]+)' file not found")]


def c_missing_names(out):
    names = set()
    for rx in C_MISSING:
        names |= set(rx.findall(out))
    return names


def norm(s):
    return " ".join(s.split())


def c_findings(root):
    """Fingerprints from the compiler (B1) and cppcheck with MISRA (B2)."""
    found = collections.Counter()
    with Work() as w:
        rc, warns, out = c_build(root, w)
        if rc != 0:
            found[("cc", "build-failed", "", "")] += 1
        for ln in warns:
            m = re.match(r"(.+?):(\d+):\d+: (?:warning|error): .*?(?:\[(-W[\w-]+)\])?$", ln)
            if m:
                found[("cc", m[3] or "error", m[1], line_text(root, m[1], int(m[2])))] += 1
    srcs = sorted(str(p.relative_to(root)) for p in (root / "src").glob("*.c"))
    rc, out = run([CPPCHECK, *CPPCHECK_ARGS, "-I", "include", *srcs], root, TIMEOUT["cppcheck"])
    if rc is None:
        raise CouldNotRun(out)
    for m in re.finditer(r"^(.+?):(\d+):\d+: \w+: ([\w.-]+): ", out, re.M):
        found[("cppcheck", m[3], m[1], line_text(root, m[1], int(m[2])))] += 1
    return found


def line_text(root, f, n):
    p = pathlib.Path(f) if os.path.isabs(f) else pathlib.Path(root) / f
    try:
        return norm(p.read_text(encoding="utf-8").splitlines()[n - 1])
    except (OSError, IndexError):
        return ""


# Rust ------------------------------------------------------------------------
def cargo(*a):
    return ["cargo", f"+{RUST_TOOLCHAIN}", *a]


def r_env(w):
    return {"CARGO_TARGET_DIR": str(w / "target")}


def r_build(root, w):
    rc, out = run(cargo("build", "--lib", "--message-format", "short"), root, TIMEOUT["build"], r_env(w))
    return rc, [ln for ln in out.splitlines() if ": warning:" in ln or ": error" in ln], out


def r_visible(root, w):
    rc, out = run(cargo("test", "--tests", "--", "--nocapture", "--test-threads=1"), root, TIMEOUT["test"], r_env(w))
    m = SUMMARY.findall(out)
    tr = re.findall(r"test result: (\w+)\. (\d+) passed; (\d+) failed", out)
    if rc is None or not tr:
        return {"ran": False, "ok": False, "why": out[-1200:]}
    failed = sum(int(t[2]) for t in tr)
    passed = sum(int(t[1]) for t in tr)
    warn = len(re.findall(r"^warning:", out, re.M))
    return {"ran": True, "ok": rc == 0 and failed == 0 and passed > 0, "passed": passed, "failed": failed,
            "vector_summaries": m, "warnings": warn}


def r_hidden(root, suite_dir, w, drop_lines=None):
    """Copy the runner and its vector module into tests/ of a copy and run it."""
    cp = w / ("t-" + suite_dir.name)
    if cp.exists():
        shutil.rmtree(cp)
    shutil.copytree(root, cp)
    runner = [p for p in suite_dir.glob("*.rs")]
    if len(runner) != 1:
        raise CouldNotRun(f"{suite_dir}: expected one runner .rs, found {runner}")
    text = runner[0].read_text(encoding="utf-8")
    if drop_lines:
        text = "".join(ln for ln in text.splitlines(keepends=True) if not re.search(drop_lines, ln))
    (cp / "tests" / runner[0].name).write_text(text, encoding="utf-8")
    for d in suite_dir.iterdir():
        if d.is_dir():
            shutil.copytree(d, cp / "tests" / d.name)
    name = runner[0].stem
    rc, out = run(cargo("test", "--test", name, "--message-format", "json", "--", "--nocapture"), cp,
                  TIMEOUT["test"], r_env(w))
    if rc is None:
        return {"ran": False, "ok": False, "why": out[-400:]}
    if "could not compile" in out or "error[" in out or '"level":"error"' in out:
        return {"ran": False, "ok": False, "compile_errors": out, "why": "did not compile"}
    tr = re.findall(r"test result: (\w+)\. (\d+) passed; (\d+) failed", out)
    res = suite_result(rc, out)
    if tr and res.get("ran"):
        res["ok"] = res["ok"] and all(int(t[2]) == 0 for t in tr)
    return res


R_MISSING = re.compile(r"(?:cannot find (?:value|type|function|struct|macro|trait|crate)|no variant[\w ,]*? named|"
                       r"no function or associated item named|no field|unresolved import|failed to "
                       r"resolve: could not find|no method named) `([\w:]+)`")


def r_missing_names(out):
    names = set()
    for ln in out.splitlines():
        try:
            msg = json.loads(ln).get("message", {}) or {}
        except (ValueError, AttributeError):
            msg = {"message": ln}
        text = msg.get("message", "") if isinstance(msg, dict) else ""
        for n in R_MISSING.findall(text):
            names.add(n.split("::")[-1])
    return names


def r_findings(root):
    """Fingerprints from rustc (B1) and Clippy all+pedantic (B2)."""
    found = collections.Counter()
    with Work() as w:
        rc, out = run(cargo("clippy", "--lib", "--message-format", "json", "--", *CLIPPY_LINTS), root,
                      TIMEOUT["clippy"], r_env(w))
    if rc is None:
        raise CouldNotRun(out)
    for ln in out.splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("reason") != "compiler-message":
            continue
        m = d["message"]
        if m["level"] not in ("warning", "error") or not m.get("spans"):
            continue
        sp = next((s for s in m["spans"] if s.get("is_primary")), m["spans"][0])
        code = (m.get("code") or {}).get("code") or m["level"]
        tool = "clippy" if code.startswith("clippy::") else "rustc"
        text = norm(sp["text"][0]["text"]) if sp.get("text") else ""
        found[(tool, code, sp["file_name"], text)] += 1
    if rc != 0 and not any(k[1] == "error" or k[0] == "rustc" for k in found):
        found[("rustc", "build-failed", "", "")] += 1
    return found


def r_kani(root, kani_dir, w):
    cp = w / "k"
    shutil.copytree(root, cp)
    shutil.copytree(kani_dir, cp / "hidden" / "kani")
    rc, out = run(["cargo", "kani"], cp / "hidden" / "kani", TIMEOUT["kani"], {"CARGO_TARGET_DIR": str(w / "tk")})
    if rc is None:
        return {"ok": False, "why": out}
    res = {}
    for chunk in out.split("Checking harness ")[1:]:
        name = chunk.split("...")[0].strip()
        res[name] = "VERIFICATION:- SUCCESSFUL" in chunk
    return {"ok": rc == 0 and bool(res) and all(res.values()), "harnesses": res,
            "out": "" if rc == 0 else out[-2000:]}


# ── The checks ───────────────────────────────────────────────────────────────
def tools_for(lang):
    if lang == "c":
        return {"build": c_build, "visible": c_visible, "hidden": c_hidden, "findings": c_findings}
    return {"build": r_build, "visible": r_visible, "hidden": r_hidden, "findings": r_findings}


def say(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    return ok


def check1(task, lang, T):
    with Work() as w:
        root = materialize(task, lang, w / "base")
        rc, warns, out = T["build"](root, w)
        ok = say(rc == 0 and not warns, f"baseline builds (exit {rc}), {len(warns)} warnings/errors")
        v = T["visible"](root, w)
        ok &= say(v["ok"], f"baseline visible tests: {v}")
        r = T["hidden"](root, task / lang / "hidden" / "regression", w)
        ok &= say(r["ok"], f"baseline regression suite: { {k: x for k, x in r.items() if k != 'compile_errors'} }")
    return ok


def check2(task, lang, T):
    spec = json.loads((task / "task.json").read_text())[lang]
    with Work() as w:
        root = materialize(task, lang, w / "base")
        plain = T["hidden"](root, task / lang / "hidden" / "new", w)
        ok = say(not plain["ok"], f"new-behaviour suite on the baseline does not pass (ran={plain['ran']})")
        if lang == "c":
            shim = c_hidden(root, task / lang / "hidden" / "new", w, defines=spec["new_name_shim"]["defines"])
        else:
            shim = r_hidden(root, task / lang / "hidden" / "new", w, drop_lines=spec["new_name_shim"]["drop_lines"])
        ok &= say(shim.get("ran", False) and shim.get("failed", 0) > 0,
                  f"with the new names shimmed it runs and cases fail: "
                  f"passed {shim.get('passed')} failed {shim.get('failed')}")
    return ok


def check_variant_suites(task, lang, T, variant, w):
    root = materialize(task, lang, w / variant, variant)
    res = {"visible": T["visible"](root, w)}
    for s in ("regression", "new"):
        res[s] = T["hidden"](root, task / lang / "hidden" / s, w)
    return root, res


def brief(r):
    return {k: v for k, v in r.items() if k in ("ok", "ran", "passed", "failed", "why", "warnings")}


def check3(task, lang, T):
    with Work() as w:
        root, res = check_variant_suites(task, lang, T, "reference", w)
        rc, warns, _ = T["build"](root, w)
        ok = say(rc == 0 and not warns, f"reference builds (exit {rc}), {len(warns)} warnings/errors")
        for s, r in res.items():
            ok &= say(r["ok"], f"reference {s}: {brief(r)}")
        base = T["findings"](materialize(task, lang, w / "b2"))
        ref = T["findings"](root)
        new = ref - base
        ok &= say(not new, f"reference adds no new findings ({sum(base.values())} baseline, "
                           f"{sum(ref.values())} reference, new: {sorted(new)[:6]})")
        if lang == "rust":
            k = r_kani(root, task / lang / "hidden" / "kani", w)
            ok &= say(k["ok"], f"reference Kani: {k.get('harnesses')} {k.get('why', '')}{k.get('out', '')[-600:]}")
    return ok


def check4(task, lang, T):
    with Work() as w:
        _, res = check_variant_suites(task, lang, T, "invariant", w)
        ok = say(res["new"]["ok"], f"invariant mutant passes new-behaviour: {brief(res['new'])}")
        ok &= say(res["regression"].get("ran") and not res["regression"]["ok"],
                  f"invariant mutant fails regression: {brief(res['regression'])}")
    return ok


def check5(task, lang, T):
    with Work() as w:
        _, res = check_variant_suites(task, lang, T, "visible_pass", w)
        ok = say(res["visible"]["ok"], f"visible-pass mutant passes visible: {brief(res['visible'])}")
        hidden_fail = [s for s in ("regression", "new") if res[s].get("ran") and not res[s]["ok"]]
        ok &= say(bool(hidden_fail), f"visible-pass mutant fails a hidden suite: {hidden_fail} "
                                     f"(regression {brief(res['regression'])}, new {brief(res['new'])})")
    return ok


def check6(task, lang, T):
    spec = json.loads((task / "task.json").read_text())[lang]
    ok = True
    with Work() as w:
        ref = T["findings"](materialize(task, lang, w / "ref", "reference"))
        for level in (["B1", "B2"] if lang == "c" else ["B1", "B2", "B3"]):
            name = f"probe_{level}"
            root = materialize(task, lang, w / name, name)
            if level == "B1":
                rc, warns, _ = T["build"](root, w)
                v = T["visible"](root, w) if rc == 0 else {"ok": False}
                tool_hits = len(warns) + (0 if v["ok"] else 1)
                ok &= say(tool_hits > 0, f"{level} probe: build exit {rc}, {len(warns)} diagnostics, "
                                         f"visible ok={v['ok']}")
            elif level == "B2":
                new = T["findings"](root) - ref
                analyser = [k for k in new if k[0] in ("cppcheck", "clippy")]
                ok &= say(bool(analyser), f"{level} probe: {len(analyser)} new analyser findings {analyser[:3]}")
            else:
                k = r_kani(root, task / lang / "hidden" / "kani", w)
                failed = [h for h, good in (k.get("harnesses") or {}).items() if not good]
                ok &= say(bool(failed), f"{level} probe: Kani harnesses failing {failed}")
    return ok


def vector_requests(vec):
    return {g: [tuple(s["req"] for s in c["steps"]) for c in cases] for g, cases in vec.items()}


HEXRUN = re.compile(r"(?:0x[0-9A-Fa-f]{2}u?\s*,\s*){5,}0x[0-9A-Fa-f]{2}")
DECRUN = re.compile(r"(?<![\w.])(?:\d{1,3}(?:u8)?\s*,\s*){5,}\d{1,3}(?![\w.])")


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def vector_sanity(vec):
    """An independent look at the generator's output (the oracle of the oracle).
    Holding registers start at (i*7 + 0x100) & 0xFFFF (the authoring spec). Returns
    a list of problems; empty means the vectors can tell the reference from its
    obvious wrong twins."""
    problems = []
    for g, cases in vec.items():
        for c in cases:
            for k, st in enumerate(c["steps"]):
                req = bytes.fromhex(st["req"])
                if len(req) >= 4 and crc16(req[:-2]) == int.from_bytes(req[-2:], "little") and st["resp"]:
                    resp = bytes.fromhex(st["resp"])
                    if len(resp) < 4 or crc16(resp[:-2]) != int.from_bytes(resp[-2:], "little"):
                        problems.append(f"{c['name']} step {k}: response has a wrong CRC")
                    if "expect" not in st:
                        problems.append(f"{c['name']} step {k}: no expect field")
    normal17, distinguishing = 0, 0
    for c in vec.get("fc17", []):
        hold = [(i * 7 + 0x100) & 0xFFFF for i in range(200)]
        for k, st in enumerate(c["steps"]):
            req, resp = bytes.fromhex(st["req"]), bytes.fromhex(st["resp"])
            if len(req) < 4 or req[0] not in (0x00, 0x11):
                continue
            fc, d = req[1], req[2:-2]
            ok = (len(resp) > 2 and resp[1] == fc) or (req[0] == 0 and not resp)
            if fc == 0x06 and ok and len(d) == 4:
                hold[int.from_bytes(d[0:2], "big")] = int.from_bytes(d[2:4], "big")
            elif fc == 0x10 and ok and len(d) >= 5:
                a, q = int.from_bytes(d[0:2], "big"), int.from_bytes(d[2:4], "big")
                for i in range(q):
                    hold[a + i] = int.from_bytes(d[5 + 2 * i:7 + 2 * i], "big")
            elif fc == 0x17 and len(resp) > 2 and resp[1] == 0x17:
                rs, rq, ws, wq, bc = (int.from_bytes(d[0:2], "big"), int.from_bytes(d[2:4], "big"),
                                      int.from_bytes(d[4:6], "big"), int.from_bytes(d[6:8], "big"), d[8])
                if bc != 2 * wq or len(d) != 9 + bc:
                    problems.append(f"{c['name']} step {k}: normal 0x17 response to a malformed request")
                    continue
                before = list(hold)
                for i in range(wq):
                    hold[ws + i] = int.from_bytes(d[9 + 2 * i:11 + 2 * i], "big")
                want = bytes([0x11, 0x17, 2 * rq]) + b"".join(hold[rs + i].to_bytes(2, "big") for i in range(rq))
                if resp[:-2] != want:
                    problems.append(f"{c['name']} step {k}: 0x17 response is not write-then-read of the holding registers")
                normal17 += 1
                if any(before[rs + i] != hold[rs + i] for i in range(rq)):
                    distinguishing += 1
    if normal17 < 8:
        problems.append(f"fc17: {normal17} normal 0x17 responses (need 8)")
    if distinguishing < 3:
        problems.append(f"fc17: {distinguishing} normal 0x17 responses that read-before-write would change (need 3)")
    fc16 = {}
    for c in vec.get("regression", []):
        for st in c["steps"]:
            req, resp = bytes.fromhex(st["req"]), bytes.fromhex(st["resp"])
            if len(req) > 6 and req[0] == 0x11 and req[1] == 0x10 and resp:
                fc16.setdefault(int.from_bytes(req[4:6], "big"), set()).add(resp[1])
    for q, want in ((122, 0x10), (123, 0x10), (124, 0x90)):
        if want not in fc16.get(q, set()):
            problems.append(f"regression: no 0x10 request at quantity {q} answered with 0x{want:02x}")
    if len(vec.get("regression", [])) < 40:   # authoring asked for 45; the split removes whole-case duplicates
        problems.append(f"regression: {len(vec.get('regression', []))} cases (need 40)")
    return problems


def check7(task, lang, T):
    vec = json.loads((task / "vectors" / "vectors.json").read_text())
    names = {g: [c["name"] for c in cs] for g, cs in vec.items()}
    ok = say(set(vec) == {"visible", "regression", "fc17"}, f"vector groups {sorted(vec)}")
    probs = vector_sanity(vec)
    ok &= say(not probs, f"the vectors pass the independent sanity check: {probs[:8]}")
    allnames = [n for v in names.values() for n in v]
    ok &= say(len(allnames) == len(set(allnames)), f"{len(allnames)} case names, unique")
    reqs = vector_requests(vec)
    single = {g: {r for c in rs for r in c} for g, rs in reqs.items()}
    for a, b in (("visible", "regression"), ("visible", "fc17"), ("regression", "fc17")):
        inter = set(reqs[a]) & set(reqs[b])
        ok &= say(not inter, f"no case (request sequence) in both {a} and {b} ({len(inter)} shared; "
                             f"{len(single[a] & single[b])} single steps shared, e.g. follow-up reads, allowed)")
    ok &= say(not any(r[2:4] == "17" for c in reqs["visible"] + reqs["regression"] for r in c),
              "no 0x17 request outside the fc17 group")
    hidden_hex = {r.lower() for g in ("regression", "fc17") for r in single[g]}
    repo = task / lang / "repo"
    hits = []
    for f in tree_files(repo):
        if "vectors_visible" in f or not f.startswith("tests"):
            continue
        txt = (repo / f).read_text(encoding="utf-8", errors="replace")
        runs = ["".join(x[2:] for x in re.findall(r"0x[0-9A-Fa-f]{2}", m[0])).lower() for m in HEXRUN.finditer(txt)]
        runs += ["".join(f"{int(x):02x}" for x in re.findall(r"\d+", m[0]) if int(x) < 256)
                 for m in DECRUN.finditer(txt)]
        for h in runs:
            hits += [f for r in hidden_hex if len(r) >= 12 and r in h]
    ok &= say(not hits, f"no hidden request bytes in hand-written visible tests ({sorted(set(hits))[:5]})")
    with Work() as w:
        g = w / "gen"
        shutil.copytree(task / "vectors", g / "vectors")
        (g / "tools").mkdir()
        shutil.copy(task / "vectors" / "gen_vectors.py", g / "tools" / "gen_vectors.py")
        rc, out = run([sys.executable, "-I", "tools/gen_vectors.py"], g, 120)
        ok &= say(rc == 0, f"generator runs (exit {rc})")
        stored = json.loads((task / "task.json").read_text())[lang]["vector_files"]
        for gen_rel, task_rel in stored.items():
            a, b = g / gen_rel, task / lang / task_rel
            same = a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()
            ok &= say(same, f"{lang}/{task_rel} is byte-identical to the generator's {gen_rel}")
        same = (g / "vectors" / "vectors.json").read_bytes() == (task / "vectors" / "vectors.json").read_bytes()
        ok &= say(same, "vectors.json regenerates byte-identically")
    return ok


def check8(task, lang, T):
    cr = (task / "change-request.md").read_text(encoding="utf-8")
    missing = set()
    with Work() as w:
        root = materialize(task, lang, w / "base")
        for s in ("new", "regression"):
            r = T["hidden"](root, task / lang / "hidden" / s, w)
            if "compile_errors" in r:
                names = (c_missing_names if lang == "c" else r_missing_names)(r["compile_errors"])
                if not names:
                    return say(False, f"{s} suite fails to compile on the baseline for a reason other than "
                                      f"a missing name:\n{r['compile_errors'][-1500:]}")
                missing |= names
        if lang == "rust":
            cp = w / "kb"
            shutil.copytree(root, cp)
            shutil.copytree(task / lang / "hidden" / "kani", cp / "hidden" / "kani")
            rc, out = run(["cargo", "kani", "--only-codegen"], cp / "hidden" / "kani", TIMEOUT["kani"],
                          {"CARGO_TARGET_DIR": str(w / "tk")})
            if rc != 0:
                names = r_missing_names(out)
                if not names:
                    return say(False, f"Kani harnesses fail to build on the baseline:\n{(out or '')[-1500:]}")
                missing |= names
    ok = say(bool(missing), f"names the hidden material uses that the baseline lacks: {sorted(missing)}")
    for n in sorted(missing):
        ok &= say(re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", cr) is not None,
                  f"'{n}' appears in the change request")
    return ok


def prompt_files(repo):
    return [f for f in tree_files(repo) if not f.endswith(("Cargo.lock",))] + \
           [f for f in tree_files(repo) if f.endswith("Cargo.lock")]


def check9(task, lang, T):
    repo = task / lang / "repo"
    parts = [f"=== {f} ===\n" + (repo / f).read_text(encoding="utf-8") for f in prompt_files(repo)]
    parts.append((task / "change-request.md").read_text(encoding="utf-8"))
    base = T["findings"](repo)
    parts.append("\n".join(f"[pre-existing] {k[0]} {k[1]} {k[2]}: {k[3]} x{n}" for k, n in sorted(base.items())))
    nbytes = len("\n".join(parts).encode("utf-8"))
    bound = int(nbytes / BYTES_PER_TOKEN_BOUND) + PROMPT_RESERVE
    typical = int(nbytes / 4) + PROMPT_RESERVE
    return say(bound < TOKEN_CAP, f"prompt {nbytes} bytes; token bound {bound} (2.0 bytes/token + {PROMPT_RESERVE}), "
                                  f"typical {typical} (4 bytes/token); cap {TOKEN_CAP}")


def check10(task, lang, T):
    spec = json.loads((task / "task.json").read_text())[lang]
    with Work() as w:
        s, c = w / "strip", w / "complete"
        marked = task / lang / "marked"
        for f in tree_files(marked):
            if f.startswith("hidden/new/") or not any(f == p or f.startswith(p + "/") for p in spec["repo_paths"]):
                continue
            text = (marked / f).read_text(encoding="utf-8")
            for dst, keep in ((s, False), (c, True)):
                if dst == s and feature_only(text):
                    continue
                (dst / f).parent.mkdir(parents=True, exist_ok=True)
                (dst / f).write_text(strip_regions(text, keep), encoding="utf-8")
        eq, why = trees_equal(s, task / lang / "repo")
        ok = say(eq, f"strip(marked) == baseline {why}")
        eq, why = trees_equal(c, task / lang / "complete")
        ok &= say(eq, f"marked minus marker lines == complete {why}")
        r = w / "rebuilt"
        shutil.copytree(task / lang / "repo", r)
        try:
            apply_edits(r, json.loads((task / lang / "reference.edits.json").read_text()))
            eq, why = trees_equal(r, task / lang / "complete")
        except ValueError as x:
            eq, why = False, str(x)
        ok &= say(eq, f"baseline + reference edits == complete {why}")
        touched = {e["path"] for e in json.loads((task / lang / "reference.edits.json").read_text())}
        lib = [p for p in touched if p.startswith(("src/", "include/"))]
        ok &= say(len(lib) >= 3, f"the reference touches {len(lib)} library files {sorted(lib)}")
    base = T["findings"](task / lang / "repo")
    b = spec["noise_budget"]
    an = {k: n for k, n in base.items() if k[0] == b["tool"] and k[1].startswith(b["rule_prefix"])}
    total = sum(an.values())
    rules = {k[1] for k in an}
    files = {k[2] for k in an}
    other = {k: n for k, n in base.items() if k[0] in ("cc", "rustc")}
    ok &= say(b["min"] <= total <= b["max"], f"noise: {total} {b['tool']} findings (budget {b['min']}..{b['max']})")
    ok &= say(len(rules) >= b["min_rules"], f"noise: {len(rules)} distinct rules (min {b['min_rules']})")
    ok &= say(len(files) >= b["min_files"], f"noise: {len(files)} files (min {b['min_files']})")
    ok &= say(not other, f"noise: no compiler findings on the baseline ({sum(other.values())})")
    marks = 0
    for f in tree_files(task / lang / "repo"):
        marks += len(re.findall(b["marker_regex"], (task / lang / "repo" / f).read_text(encoding="utf-8")))
    ok &= say(marks >= b["min_marked"], f"noise: {marks} documented deviations/allows (min {b['min_marked']})")
    return ok


CHECKS = {1: check1, 2: check2, 3: check3, 4: check4, 5: check5, 6: check6, 7: check7, 8: check8, 9: check9,
          10: check10}


def cmd_check(task, lang, n):
    task = pathlib.Path(task).resolve()
    try:
        ok = CHECKS[n](task, lang, tools_for(lang))
    except CouldNotRun as x:
        print(f"COULD-NOT-RUN {x}")
        return 2
    except ValueError as x:
        print(f"FAIL {x}")
        return 1
    return 0 if ok else 1


def cmd_all(task, langs):
    worst = 0
    rows = []
    for lang in langs:
        for n in CHECKS:
            p = subprocess.run([sys.executable, __file__, "check", str(task), lang, str(n)], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
            out = p.stdout.decode("utf-8", "replace")
            print(f"--- check {n} {lang}: exit {p.returncode}\n{out}", flush=True)
            rows.append((n, lang, p.returncode))
            worst = max(worst, p.returncode)
    print("\nSUMMARY")
    for n, lang, rc in rows:
        print(f"check {n:2d} {lang:4s} exit {rc}")
    return worst


# ── Negative controls: break the input, expect 1, restore by re-editing ─────
def negctl_edit(task, lang, n):
    """(file, old, new): one in-place edit that must make check n fail."""
    nc = json.loads((task / "negctl.json").read_text())[lang][str(n)]
    new = nc["new"] if "new" in nc else nc["old"] + "\n" + ("negative control padding " * (nc["append_bytes"] // 25))
    return task / nc["file"], nc["old"], new


def cmd_negctl(task, lang, n):
    task = pathlib.Path(task).resolve()
    f, old, new = negctl_edit(task, lang, n)
    before = hashlib.sha256(f.read_bytes()).hexdigest()
    text = f.read_text(encoding="utf-8")
    if text.count(old) != 1:
        print(f"negctl {n}: anchor occurs {text.count(old)} times in {f.name}")
        return 2
    f.write_text(text.replace(old, new, 1), encoding="utf-8")
    if f.read_text(encoding="utf-8").count(new) != 1:
        f.write_text(text, encoding="utf-8")
        print(f"negctl {n}: the broken text is not unique, so the reverse edit would be ambiguous")
        return 2
    broken = cmd_check_sub(task, lang, n)
    text = f.read_text(encoding="utf-8")
    f.write_text(text.replace(new, old, 1), encoding="utf-8")       # restore by the reverse edit
    after = hashlib.sha256(f.read_bytes()).hexdigest()
    restored = cmd_check_sub(task, lang, n)
    ok = broken == 1 and restored == 0 and before == after
    print(f"negctl check {n} {lang}: broken exit {broken} (want 1), restored exit {restored} (want 0), "
          f"file restored byte-identical {before == after}")
    return 0 if ok else 1


def cmd_check_sub(task, lang, n):
    p = subprocess.run([sys.executable, __file__, "check", str(task), lang, str(n)], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    sys.stdout.write("    | " + p.stdout.decode("utf-8", "replace").replace("\n", "\n    | ") + "\n")
    return p.returncode


def cmd_assemble(task, lang, marked_src, repo_paths):
    """Build TASK/LANG/{marked,complete,repo,hidden,reference.edits.json} from an authoring tree."""
    task = pathlib.Path(task).resolve()
    d = task / lang
    if d.exists():
        raise SystemExit(f"{d} exists; assemble writes a fresh directory only")
    src = pathlib.Path(marked_src).resolve()
    skip = ("build/", "target/", "__pycache__/")
    for f in tree_files(src):
        if f.startswith(skip) or "/__pycache__/" in f or "/target/" in f or f.endswith(".dump"):
            continue
        (d / "marked" / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, d / "marked" / f)
    for f in tree_files(d / "marked"):
        if any(f == p or f.startswith(p + "/") for p in repo_paths):
            text = (d / "marked" / f).read_text(encoding="utf-8")
            for sub, keep in (("repo", False), ("complete", True)):
                if sub == "repo" and feature_only(text):
                    continue
                (d / sub / f).parent.mkdir(parents=True, exist_ok=True)
                (d / sub / f).write_text(strip_regions(text, keep), encoding="utf-8")
        elif f.startswith(("hidden/regression/", "hidden/new/", "hidden/kani/")):
            (d / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d / "marked" / f, d / f)
    edits = derive_edits(d / "repo", d / "complete")
    (d / "reference.edits.json").write_text(json.dumps(edits, indent=1) + "\n", encoding="utf-8")
    print(f"{lang}: {len(tree_files(d / 'repo'))} baseline files, {len(edits)} reference edits")
    return 0


def cmd_manifest(task):
    task = pathlib.Path(task).resolve()
    for f in tree_files(task):
        if "/target/" in f or "__pycache__" in f:
            continue
        print(f"{hashlib.sha256((task / f).read_bytes()).hexdigest()}  {task.name}/{f}")
    return 0


# ── Self-test: the pure parts, no toolchain ─────────────────────────────────
def self_test():
    fails = []

    def t(cond, name):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond:
            fails.append(name)

    with Work() as w:
        a, b = w / "a", w / "b"
        (a / "src").mkdir(parents=True)
        (b / "src").mkdir(parents=True)
        base = "int f(void) {\n    return 1;\n}\n\nint g(void) {\n    return 1;\n}\n"
        comp = "int f(void) {\n    return 2;\n}\n\nint g(void) {\n    return 1;\n}\n\nint h(void) { return 3; }\n"
        (a / "src" / "x.c").write_text(base)
        (b / "src" / "x.c").write_text(comp)
        (b / "src" / "y.c").write_text("int y;\n")
        edits = derive_edits(a, b)
        r = w / "r"
        shutil.copytree(a, r)
        apply_edits(r, edits)
        t(trees_equal(r, b)[0], "derive + apply round-trips, with repeated lines and a new file")
        try:
            apply_edits(r, [{"path": "src/x.c", "old": "int ", "new": "long "}])
            t(False, "ambiguous old is refused")
        except ValueError:
            t(True, "ambiguous old is refused")
        for bad in ("../x", "/etc/passwd"):
            try:
                apply_edits(r, [{"path": bad, "old": "", "new": "x"}])
                t(False, f"path {bad} is refused")
            except ValueError:
                t(True, f"path {bad} is refused")
        try:
            apply_edits(r, [{"path": "src/y.c", "old": "", "new": "x"}])
            t(False, "create over an existing file is refused")
        except ValueError:
            t(True, "create over an existing file is refused")
    src = "a\n/* FC17-BEGIN */\nb\n/* FC17-END */\nc\n    // FC17-BEGIN\nd\n    // FC17-END\n"
    t(strip_regions(src, False) == "a\nc\n", "strip removes marked regions")
    t(strip_regions(src, True) == "a\nb\nc\nd\n", "keep_body removes only marker lines")
    t(feature_only('#include "x.h"\n/* c */\n/* FC17-BEGIN */\nint f(void);\n/* FC17-END */\n'),
      "a file with only includes outside its markers is feature-only")
    t(not feature_only('#include "x.h"\nint g;\n/* FC17-BEGIN */\nint f(void);\n/* FC17-END */\n'),
      "a file with other code is not feature-only")
    t(not feature_only("int g;\n"), "a file without markers is not feature-only")
    for bad in ("/* FC17-BEGIN */\n", "/* FC17-END */\n", "/* FC17-BEGIN */\n/* FC17-BEGIN */\n/* FC17-END */\n"):
        try:
            strip_regions(bad, False)
            t(False, f"unbalanced markers refused: {bad!r}")
        except ValueError:
            t(True, f"unbalanced markers refused: {bad!r}")
    t(c_missing_names("t.c:3:15: error: use of undeclared identifier 'MB_FC_X'\n") == {"MB_FC_X"},
      "C missing-name parse")
    rj = json.dumps({"reason": "compiler-message", "message": {"message": "no variant or associated item named "
                                                                          "`ReadWriteMultipleRegisters` found for enum `FunctionCode`"}})
    t(r_missing_names(rj) == {"ReadWriteMultipleRegisters"}, "Rust missing-name parse")
    rj2 = json.dumps({"reason": "compiler-message", "message": {"message": "no variant, associated function, or constant "
                      "named `ReadWriteMultipleRegisters` found for enum `FunctionCode` in the current scope"}})
    t(r_missing_names(rj2) == {"ReadWriteMultipleRegisters"}, "Rust missing-name parse, rustc 1.96 wording")
    t(bool(HEXRUN.search("{0x11u, 0x03u, 0x00u, 0x00u, 0x00u, 0x02u}")), "literal scan reads u-suffixed C bytes")
    t(bool(DECRUN.search("&[17, 3, 0, 0, 0, 2, 198, 155]")), "literal scan reads decimal Rust bytes")
    t(suite_result(0, "passed 3 failed 0\n")["ok"] and not suite_result(0, "passed 3 failed 1\n")["ok"]
      and not suite_result(1, "passed 3 failed 0\n")["ok"] and not suite_result(0, "no summary")["ok"],
      "suite summary needs exit 0, failed 0 and a summary line")
    t(not suite_result(0, "passed 0 failed 0\n")["ok"], "an empty suite does not pass")
    print(f"self-test: {len(fails)} failed")
    return 1 if fails else 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "self-test":
        return self_test()
    if len(argv) == 5 and argv[1] == "check":
        return cmd_check(argv[2], argv[3], int(argv[4]))
    if len(argv) >= 3 and argv[1] == "all":
        return cmd_all(pathlib.Path(argv[2]).resolve(), argv[3:] or ["c", "rust"])
    if len(argv) == 5 and argv[1] == "negctl":
        return cmd_negctl(argv[2], argv[3], int(argv[4]))
    if len(argv) == 5 and argv[1] == "derive":
        edits = derive_edits(argv[2], argv[3])
        pathlib.Path(argv[4]).write_text(json.dumps(edits, indent=1) + "\n", encoding="utf-8")
        print(f"{len(edits)} edits")
        return 0
    if len(argv) == 3 and argv[1] == "vectors-sanity":
        probs = vector_sanity(json.loads(pathlib.Path(argv[2]).read_text()))
        for x in probs:
            print("FAIL " + x)
        print(f"vectors-sanity: {len(probs)} problems")
        return 1 if probs else 0
    if len(argv) == 6 and argv[1] == "assemble":
        return cmd_assemble(argv[2], argv[3], argv[4], argv[5].split(","))
    if len(argv) == 3 and argv[1] == "manifest":
        return cmd_manifest(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
