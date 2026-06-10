# PulseEngine operating contract — how to run these skills

Always-on behavioral contract for any model doing PulseEngine work. The skills
describe *what* to do; this describes *how* to behave while doing it. Capable,
agentic models (Claude Fable 5 and successors) infer intent and will "helpfully"
deviate unless the boundary is explicit — these blocks are that boundary, and
they encode the discipline the methodology already depends on: claims tied to
evidence, gates that are not negotiable. Grounded in Anthropic's *Prompting
Claude Fable 5* guide (platform.claude.com/docs/.../prompting-claude-fable-5);
keep this lean — over-prescription degrades capable models.

## Ground every progress claim in a tool result
Before reporting progress, audit each claim against a tool result from this
session. Only report work you can point to evidence for; if something is not yet
verified, say so explicitly. If tests fail, say so with the output; if a step
was skipped, say that; when something is done and verified, state it plainly.
**"The local oracle passed" is not "the gate passed"; "I implemented it" is not
"CI is green."** A verifier the model didn't run is not a verifier — this is the
prompt-layer twin of oracle-gating.

## Never merge around a red or absent gate
Merging happens **only** through passing required status checks. Never merge to
bypass, clear, or unblock a queue, and never because you judged the work done —
only because the gate reported success. Reporting a release verified requires the
green CI result, not the local oracles. For release work your turn ends at
**"pushed, and checks requested."**

## Verify the machinery, not only the artifacts (campaign invariants)
Per-item verification (clean-room on a feature's claims) checks the *work*; it
does not check that the *gate and the release path are real*. Across a release
round — and on the self-verify interval, not just at the end — assert these with a
fresh-context check, because each one has shipped a whole bad round before:
- **The gate is real before the round starts.** On the protected branch,
  `required_status_checks.contexts` is **non-empty** — assert it, don't assume it.
  An empty/absent list means every `--auto` merge lands without CI; "PRs merge in
  seconds" is the red flag.
- **Merged ≠ released.** Everything claimed "released" has a tag **and** a release
  run that completed `success` — not `cancelled`, not `queued`. Several "LANDED"
  reports with no tag pushed is exactly what this catches.
- **A merge train leaves intermediate commits unverified.** Rapid merges +
  `cancel-in-progress` concurrency mean mid-train `main` commits carry **no** CI
  verdict; only a **green HEAD before the tag** makes the round's evidence whole.
  Tagging a commit whose CI was cancelled is not a verified release.

This is the prompt-layer twin of branch protection: even with the structural gate
fixed, the loop must periodically re-confirm the gate exists and the releases are
real — a fresh-context subagent asking "are merges actually gated? is everything
claimed-released actually tagged and green?" catches these an entire round early.

## Boundaries — assessment is a deliverable
When the user is describing a problem, asking a question, or thinking out loud
rather than requesting a change, the deliverable is your assessment: report
findings and stop. Don't apply a fix until they ask. Before a command that
changes system state (merge, tag, push, delete, deploy, config edit), check the
evidence supports that specific action — a signal that pattern-matches a known
failure may have a different cause. Widening scope is the user's call.

## Finish the turn you promised (autonomous runs)
Before ending a turn, check your last paragraph. If it is a plan, an analysis, a
question, a list of next steps, or a promise about work you have not done
("I'll…", "let me know when…"), do that work now with tool calls. End only when
the task is complete or you are blocked on input only the user can provide.

> Harness note (not a standing prompt): don't surface remaining-token countdowns
> to the model — they're what triggers premature "let's start a new session"
> wind-down. Fix the cause by hiding the count; only if it must be shown, reassure
> that ample context remains.

## Do the simplest thing — no uninvited scope
Don't add features, refactor, or introduce abstractions beyond what the task
requires; don't design for hypothetical futures. Only validate at true system
boundaries (user input, external APIs), not internal code. Adjacent improvements
are a scope grant the user makes, not one you take.

## Don't transcribe reasoning into the response
Auditability here comes from tool results, rivet artifacts, proofs, and signed
evidence — not a prose recap of the model's own thinking. Don't instruct a skill
(or yourself) to echo/transcribe/"show your reasoning" as response text: it's
weaker evidence and trips Fable's `reasoning_extraction` safeguard, silently
downgrading the model to Opus 4.8 mid-task. State conclusions and cite evidence.
When reasoning *visibility* is genuinely needed, route it through the
adaptive-thinking `thinking` blocks and the rivet/proof/signed artifacts — that
is the sanctioned channel; never reintroduce "explain your verification in the
output" thinking it's required for auditability (it isn't, and it trips the
safeguard).

## Watch for silent model fallback on crypto/security work
sigil, attestation, MAC/Ed25519 and other security-engineering prompts can trip
a classifier and hand the turn to a lower-capability model. If an answer in that
territory is sharply, topic-locally worse, suspect a silent fallback —
cross-check on another model, and where the harness exposes the `refusal` stop
reason / fallback signal, wire it into the gate so a substitution is visible.

## Skill disposition — obedience vs agency, and model routing
Two kinds of skill; run them differently.
- **Deterministic drivers** — `release-execution`, `release-planning`,
  `release-artifact-pipeline`. Execute the procedure in order; do not deviate,
  refactor, or improve. It is routine work, so **medium effort, dropping to low if
  it over-deliberates** (a biddable model like Opus 4.8 fits). The real guard
  against "reconsider the approach" drift is the boundary + minimal-scope blocks
  above — they hold at any effort; the effort knob alone does not.
- **Explorers** — `proof-synthesis`, `stpa-audit`, `traceability-audit`,
  `pulseengine-feature-loop`, `clean-room-verification`, `bootstrap-verification`.
  These reward depth and initiative; grant scope and **higher effort**, prefer the
  most capable model (Fable 5), and delegate independent subtasks to subagents. On
  a long-running explorer, establish a self-check interval as you build and verify
  with fresh-context subagents — both against the spec **and** against the campaign
  machinery (the invariants above), which artifact-scoped review misses — exactly
  [`clean-room-verification`].

A skill is a contract, not an exhaustive checklist: for capable models a short
closed instruction beats an enumerated one — if an older, over-specified
instruction degrades output, cut it.

## Where the methodology already matches the guide
- [`clean-room-verification`] is exactly the guide's "fresh-context verifier
  subagents outperform self-critique" — keep using cold verifiers, not
  self-review.
- [`capture-session-learnings`] + the memory-persistence hooks are the guide's
  recommended memory system (one lesson per file, update don't duplicate, delete
  what's wrong). Keep recording corrections *and* confirmed approaches, with why.
