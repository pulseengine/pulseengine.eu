Seam update for v0.2.0, before the tag. The change is additive within `sieve.classify.v1`:
- `unresolved` (class to `[{code, input}]`) is always present;
- `explain` appears with `--explain`;
- `sieve --version` line 2 also names `sieve.equivalence.v1` and `sieve.observe.v1`.

No field is removed or renamed, and the two run-all reason strings plant matches are unchanged. `seam-check.py --block` against main: PASS.