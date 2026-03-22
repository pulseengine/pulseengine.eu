+++
title = "Formal Verification Guide for AI Agents"
description = "Practical reference for Verus, Rocq, Lean, and Kani verification across PulseEngine projects"
template = "page.html"
+++


Reference document for AI agents working on PulseEngine projects that use
Verus, Rocq, Lean, or Kani for formal verification. Link to this from your
project's AGENTS.md or CLAUDE.md.

> Based on findings from AutoVerus (Microsoft, ICLR 2025), AlphaVerus (CMU,
> ICML 2025), Strat2Rocq (2025), Lean Copilot, and the VeriCoding benchmark.

---

## General Principles

1. **Get the spec right before attempting proofs.** A wrong `requires`/`ensures`
   wastes all downstream effort. Write the spec, review it, then prove it.
2. **Try the simple thing first.** Most proofs are simpler than they look.
   Let the solver attempt it before adding manual proof steps.
3. **Generate multiple candidates.** If a proof attempt fails, try 3-5
   different strategies before concluding the property is hard. Success
   rate jumps from ~60% (single shot) to 91% (5 candidates + repair).
4. **Classify the error, then apply the matching fix.** Don't guess randomly.
   Each verifier error type has a known repair pattern (see tables below).
5. **Code must satisfy all verification tracks simultaneously.** In gale,
   the same source must: compile as plain Rust, pass Verus, translate through
   coq_of_rust, and be analyzable by Kani. Write to the intersection.

---

## Verus (SMT / Z3)

### Rust Subset Restrictions

Verus accepts a subset of Rust inside `verus! { }` blocks:

- **No trait objects** (`dyn Trait`) in verified code
- **No closures** in proof context
- **No async/await** in verified functions
- **Integer arithmetic** is checked for overflow by default — `a + b` will
  fail if overflow is possible. Use `checked_add`/`checked_sub` or prove
  bounds via `requires`
- **Use `as int`** in spec functions to lift to mathematical integers
  (unbounded) for reasoning
- **`Vec`** works but prefer fixed-size or ghost `Seq` for specifications
- **`HashMap`/`BTreeMap`**: use `Map<K,V>` in spec, concrete type in exec
- **Generics**: supported, but some trait bounds may not work in proof context

### Writing Specifications

```rust
// Good: precise, minimal, testable
pub fn give(&mut self) -> (result: bool)
    requires old(self).inv(),
    ensures
        self.inv(),
        result == (old(self).count < old(self).limit),
        result ==> self.count == old(self).count + 1,
        !result ==> self.count == old(self).count,
```

- Start with the **invariant** (`inv()`) — what must always be true
- `requires` states what the caller must guarantee
- `ensures` states what the function guarantees
- Use `old(self)` to refer to pre-state in ensures
- Keep specs **minimal** — don't over-specify implementation details

### Error Types and Repair Strategies

| Error | What It Means | Fix |
|-------|--------------|-----|
| `AssertFail` | An assertion can't be proven | Add intermediate `assert()` steps to guide Z3, or use `assert(...) by { lemma_call(); }` |
| `PreCondFail` | Caller doesn't satisfy `requires` | Either strengthen the caller's proof context or weaken the precondition |
| `InvFailFront` | Loop invariant doesn't hold on entry | Check that initial values before the loop satisfy the invariant |
| `InvFailEnd` | Loop invariant doesn't hold after loop body | Usually a missing update or off-by-one; check every variable the invariant mentions |
| `ArithmeticFlow` | Possible overflow/underflow | Add bounds to `requires`, use `checked_*` arithmetic, or prove bounds with `assert` |
| `MismatchedType` | Type mismatch in proof context | Add explicit type casts or restructure to match expected types |
| Solver timeout | Z3 can't decide within time limit | Break into smaller `assert` steps, add triggers, simplify quantifiers |

### Proof Strategies (ordered by simplicity)

1. **Let the solver try** — write spec, run Verus, see if it just works
2. **Add assert breadcrumbs** — intermediate assertions that guide Z3:
   ```rust
   assert(self.count <= self.limit);  // help Z3 see the bound
   assert(self.count + 1 <= self.limit);  // then the increment is safe
   ```
3. **Use `assert(...) by { ... }`** for explicit proof blocks:
   ```rust
   assert(result == expected) by {
       reveal(some_opaque_fn);  // expose definition to solver
   }
   ```
4. **Call lemmas** — factor reusable proof steps into separate `proof fn`:
   ```rust
   proof fn lemma_count_bounded(s: &Semaphore)
       requires s.inv(),
       ensures s.count <= s.limit,
   { /* Z3 handles this */ }
   ```
5. **Add triggers** for quantified statements:
   ```rust
   forall|i: int| 0 <= i < self.len() ==> #[trigger] self.buf[i] != 0
   ```
6. **Use `decreases`** for recursive functions — must strictly decrease on a
   well-founded measure

### Common Patterns

**Invariant preservation** (most common proof obligation):
```rust
pub fn operation(&mut self)
    requires old(self).inv(),
    ensures self.inv(),
{
    // ... modify state ...
    // Z3 must see that inv() still holds
}
```

**Bounded arithmetic** (gale kernel primitives):
```rust
requires
    self.count < self.limit,  // explicitly bound before arithmetic
ensures
    self.count == old(self).count + 1,  // safe: bounded by requires
```

**Option/Result reasoning**:
```rust
ensures
    match result {
        Ok(v) => v.inv() && v.count == initial,
        Err(e) => e == EINVAL && (limit == 0 || initial > limit),
    }
```

---

## Rocq (Coq Theorem Prover)

### coq_of_rust Compatibility

When writing Rust that must translate through `coq_of_rust`:

- **No async/await**
- **No complex trait bounds** with associated types
- **Keep match arms simple** — deeply nested patterns may not translate
- **Prefer explicit types** over inference where possible
- **Avoid complex closures** — use named functions
- The generated `.v` file uses a **monadic DSL** — proofs reason about
  `M.run`, `M.bind`, `M.return`

### Proof Tactics (ordered by reach-for-first)

| Tactic | When To Use |
|--------|------------|
| `lia` | Linear integer arithmetic — handles most numeric proofs |
| `auto` | Simple logical reasoning, constructor matching |
| `unfold X; auto` | When the goal mentions a defined function — expand it first |
| `unfold X; lia` | Numeric goals behind a definition |
| `intros; destruct` | Case analysis on sum types, booleans |
| `induction n; simpl; lia` | Inductive proofs on naturals/lists |
| `omega` | Integer arithmetic (alternative to lia) |
| `trivial` | Obvious goals (reflexivity, assumption) |

### Proof Structure (from gale's existing proofs)

```coq
(* 1. Define the invariant *)
Definition sem_inv (count limit : Z) : Prop :=
  limit > 0 /\ 0 <= count /\ count <= limit.

(* 2. Prove initialization establishes invariant *)
Theorem init_establishes_invariant :
  forall initial_count limit : Z,
    limit > 0 -> 0 <= initial_count -> initial_count <= limit ->
    sem_inv initial_count limit.
Proof. intros. unfold sem_inv. auto. Qed.

(* 3. Prove operations preserve invariant *)
Theorem give_preserves_invariant :
  forall count limit : Z,
    sem_inv count limit -> count < limit ->
    sem_inv (count + 1) limit.
Proof. intros count limit [Hlim [Hge Hle]] Hlt. unfold sem_inv. lia. Qed.
```

### Strategies from Strat2Rocq Research

- **Avoid induction when possible** — 42.5% of proof improvements come from
  lemmas that let CoqHammer skip induction entirely. If you can state a
  closed-form lemma, do it.
- **Don't restate definitions as lemmas** — `Lemma foo : X = X.` is useless.
  Good lemmas reformulate facts in ways the solver can exploit.
- **Extract ~2 reusable lemmas per theorem** — look for intermediate facts
  that appear in multiple proofs.
- **Reformulate implications** — sometimes `A -> B` is hard but the
  contrapositive `~B -> ~A` is easy. CoqHammer benefits from both forms.

---

## Lean 4

### Proof Approach

Lean proofs in PulseEngine are a third independent verification track.

- **Use `simp` aggressively** — Lean's simplifier handles many goals
- **`omega`** for integer arithmetic (like Rocq's `lia`)
- **`decide`** for decidable propositions
- **`cases`/`match`** for case analysis
- **`induction`** when structural recursion is needed

### Mathlib

Lean's power comes partly from [Mathlib](https://github.com/leanprover-community/mathlib4) —
over 1 million lines of formalized mathematics. For kernel verification,
relevant Mathlib modules include:

- `Mathlib.Data.Nat.Basic` — natural number arithmetic
- `Mathlib.Data.Int.Basic` — integer arithmetic and order
- `Mathlib.Data.Fin` — bounded naturals (useful for array indices)
- `Mathlib.Order.BoundedOrder` — bounded lattice structures
- `Mathlib.Tactic` — automation tactics

PulseEngine's [rules_lean](https://github.com/pulseengine/rules_lean)
provides Bazel rules with Mathlib integration via `lean_prebuilt_library`.

### Lean Copilot Integration

If using [Lean Copilot](https://github.com/lean-dojo/LeanCopilot):

- `suggest_tactics` — shows candidate next steps
- `search_proof` — finds complete multi-tactic proofs (74.2% success)
- `select_premises` — retrieves useful lemmas from Mathlib and project libraries
- Automates most mechanical proof steps; focus human/agent effort on the
  remaining 25% that need domain knowledge

---

## Kani (Bounded Model Checking)

### Harness Patterns

```rust
#[kani::proof]
fn verify_sem_give_no_overflow() {
    let count: u32 = kani::any();
    let limit: u32 = kani::any();
    kani::assume(limit > 0);
    kani::assume(count <= limit);
    kani::assume(count < limit);

    let new_count = count + 1;  // Kani checks: can this overflow?
    assert!(new_count <= limit);
}
```

- **`kani::any()`** — symbolic value, Kani explores all possibilities
- **`kani::assume()`** — constrain the search space (like requires)
- **`assert!()`** — what must hold (like ensures)
- Kani exhaustively checks within the bounded state space
- Use for: absence of panics, arithmetic safety, FFI equivalence

### FFI Equivalence Checking

```rust
#[kani::proof]
fn verify_ffi_sem_give_matches() {
    let count: u32 = kani::any();
    let limit: u32 = kani::any();
    kani::assume(limit > 0 && count <= limit);

    let rust_result = Semaphore::give_logic(count, limit);
    let ffi_result = gale_sem_count_give(count, limit);
    assert_eq!(rust_result, ffi_result);
}
```

---

## Writing Code for All Tracks Simultaneously

### The Intersection

Code in gale must work across: plain Rust, Verus, coq_of_rust, and Kani.
The safe intersection:

| Feature | Plain Rust | Verus | coq_of_rust | Kani |
|---------|-----------|-------|-------------|------|
| Basic types (u32, bool, etc.) | ✓ | ✓ | ✓ | ✓ |
| Structs with named fields | ✓ | ✓ | ✓ | ✓ |
| Enums (simple) | ✓ | ✓ | ✓ | ✓ |
| `match` (simple arms) | ✓ | ✓ | ✓ | ✓ |
| `if/else` | ✓ | ✓ | ✓ | ✓ |
| `Result<T, E>` | ✓ | ✓ | ✓ | ✓ |
| `Option<T>` | ✓ | ✓ | ✓ | ✓ |
| Checked arithmetic | ✓ | ✓ | ✓ | ✓ |
| `impl` blocks | ✓ | ✓ | ✓ | ✓ |
| Trait objects (`dyn`) | ✓ | ✗ | ✗ | ✓ |
| Closures | ✓ | ✗ | ✗ | ✓ |
| async/await | ✓ | ✗ | ✗ | ✗ |
| Complex generics | ✓ | partial | partial | ✓ |
| `unsafe` blocks | ✓ | ✗ | ✗ | ✓ |

### Architecture Pattern

```
src/sem.rs          ← Verus-annotated source (single source of truth)
  │
  ├── verus! { }    ← Verus verifies this
  │
  └── verus-strip ──→ plain/src/sem.rs  ← plain Rust (auto-generated)
                        │
                        ├── cargo test   ← unit tests, proptest
                        ├── cargo kani   ← bounded model checking
                        ├── cargo miri   ← UB detection
                        └── coq_of_rust  ← generates .v for Rocq proofs
```

The `verus-strip` tool removes all verification annotations, producing
standard Rust that all other tools can consume.

---

## Bazel Rules

PulseEngine provides Bazel rules for each verification tool, enabling
hermetic, reproducible verification builds:

- **[rules_verus](https://github.com/pulseengine/rules_verus)** — `verus_library` and `verus_test` rules. Downloads pre-built Verus binaries with SHA-256 verification. Cross-platform (macOS, Linux, Windows).
- **[rules_rocq_rust](https://github.com/pulseengine/rules_rocq_rust)** — `rocq_library`, `rocq_proof_test`, and `rocq_rust_verified_library` rules. Hermetic Rocq 9.0 toolchain via Nix. Includes `coq_of_rust` integration for Rust → Rocq translation.
- **[rules_lean](https://github.com/pulseengine/rules_lean)** — `lean_library`, `lean_proof_test`, and `lean_prebuilt_library` rules. Mathlib integration. Aeneas support for LLBC → Lean translation.

### Example BUILD.bazel

```starlark
load("@rules_verus//verus:defs.bzl", "verus_test")
load("@rules_rocq_rust//rocq:defs.bzl", "rocq_library", "rocq_proof_test")
load("@rules_rocq_rust//coq_of_rust:defs.bzl", "rocq_rust_verified_library")

# Track 1: Verus verification (SMT/Z3)
verus_test(name = "verus_test", srcs = glob(["src/*.rs"]))

# Track 2: Rocq — translate Rust to Rocq, then prove properties
rocq_rust_verified_library(
    name = "kernel_translated",
    rust_sources = glob(["plain/src/*.rs"]),
)

rocq_library(
    name = "kernel_proofs",
    srcs = glob(["proofs/*.v"]),
    deps = [":kernel_translated"],
)

rocq_proof_test(
    name = "rocq_proof_test",
    deps = [":kernel_proofs"],
)
```

---

## References

- [AutoVerus](https://github.com/microsoft/verus-proof-synthesis) (Microsoft) — automated Verus proof generation, 91.3% success rate
- [AlphaVerus](https://github.com/cmu-l3/alphaverus) (CMU) — self-improving Dafny → Verus translation
- [Strat2Rocq](https://arxiv.org/abs/2510.10131) — lemma extraction from LLMs for CoqHammer, +13.4% improvement
- [Lean Copilot](https://github.com/lean-dojo/LeanCopilot) — 74.2% proof step automation in Lean
- [VeriCoding Benchmark](https://github.com/Beneficial-AI-Foundation/vericoding-benchmark) — 2,334 Verus tasks for testing proof generation
- [Verus documentation](https://verus-lang.github.io/verus/)
- [Rocq/Coq reference](https://rocq-prover.org/)
- [Blog post: Formal verification just became practical](/blog/formal-verification-ai-agents/)

---

## Integrating Into Your Project

### Step 1: Add to AGENTS.md (or CLAUDE.md)

Add this section to your project's `AGENTS.md` or `CLAUDE.md` so that any AI agent working on the project knows about the verification guide:

```markdown
## Formal Verification

This project uses formal verification. Before writing or modifying
verified code, read the Verification Guide:

  https://pulseengine.eu/guides/VERIFICATION-GUIDE.md

Key rules:
- Code must compile in the intersection of Verus, coq_of_rust, and Kani
  (see the compatibility table in the guide)
- Follow the error classification table when a proof fails — don't guess
- Use `verus-strip` to produce plain Rust for non-Verus tools
- Run `bazel test //...` or the equivalent cargo commands to verify all tracks

If you encounter a verification pattern that does not match the guide —
a proof strategy that fails, an error type not listed, or a Rust feature
that should work but doesn't — open an issue:

  https://github.com/pulseengine/pulseengine.eu/issues

Tag it `verification-guide` and describe what you tried, what failed,
and what you expected. This helps us improve the guide for everyone.
```

### Step 2: Reference from rivet artifacts (optional)

If your project uses rivet for traceability, you can link verification
artifacts to the guide:

```yaml
- id: FV-GUIDE-001
  type: design-decision
  title: Verification guide reference
  description: >
    Formal verification follows the PulseEngine Verification Guide.
    Proof strategies, error handling, and Rust subset rules are
    documented at pulseengine.eu/guides/verification-guide/
  status: approved
```

### Step 3: Keep it current

When you find something that works better than what the guide says,
or something that no longer works, update the guide. It lives at:

- Website (rendered): [pulseengine.eu/guides/verification-guide/](/guides/verification-guide/)
- Source: `content/guides/verification-guide/index.md` in the pulseengine.eu repo
- Downloadable: [/guides/VERIFICATION-GUIDE.md](/guides/VERIFICATION-GUIDE.md)

---

## Feedback and Updates

This guide evolves as we learn what works. If you encounter:

- Proof strategies that fail or produce false confidence
- Verus/Rocq/Lean error patterns not documented here
- Rust subset restrictions we missed
- Better approaches than what we describe

Open an issue at [github.com/pulseengine/pulseengine.eu](https://github.com/pulseengine/pulseengine.eu/issues) with the tag `verification-guide`. Whether you are a human or an AI agent, the feedback is valuable.

*Last updated: March 22, 2026*
