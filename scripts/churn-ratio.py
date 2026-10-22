"""Deleted-per-added lines per quarter, from git numstat on HEAD's history (no merges).
all = every text file; rs = .rs only, excluding vendored/generated paths and lockfiles."""
import subprocess, sys, collections, re
SKIP = re.compile(r"(^|/)(vendor|third_party|target|node_modules)/|\.lock$|(^|/)Cargo\.lock$")
def run(repo):
    out = subprocess.run(["git", "-C", repo, "log", "--no-merges", "--numstat", "--format=@%cs"],
                         capture_output=True, text=True, errors="replace").stdout
    q = None; A = collections.defaultdict(lambda: [0, 0, 0, 0])
    for l in out.splitlines():
        if l.startswith("@"):
            y, m = int(l[1:5]), int(l[6:8]); q = f"{y}Q{(m - 1) // 3 + 1}"; continue
        p = l.split("\t")
        if len(p) != 3 or p[0] == "-": continue
        a, d, f = int(p[0]), int(p[1]), p[2]
        A[q][0] += a; A[q][1] += d
        if f.endswith(".rs") and not SKIP.search(f) and "=>" not in f:
            A[q][2] += a; A[q][3] += d
    return A
for repo in sys.argv[1:]:
    A = run(repo); name = repo.rstrip("/").split("/")[-1]
    rows = [(k, *v) for k, v in sorted(A.items()) if v[0] >= 2000]   # skip near-empty quarters
    r_all = [d / a for _, a, d, _, _ in rows if a]
    r_rs = [d2 / a2 for _, _, _, a2, d2 in rows if a2 >= 2000]
    print(f"{name:8} all {min(r_all):.2f}-{max(r_all):.2f}  rs {min(r_rs, default=0):.2f}-{max(r_rs, default=0):.2f}")
    for k, a, d, a2, d2 in rows:
        print(f"   {k}  all +{a:>8} -{d:>8} {d/a:5.2f}   rs +{a2:>7} -{d2:>7} {d2/max(1,a2):5.2f}")
