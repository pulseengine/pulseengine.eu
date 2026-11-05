---
name: outside-in-recheck
description: This skill should be used when the user shares outside material (a conference talk or transcript, a paper, an upstream spec change, a peer project's release notes or design doc) or says "recheck us against this". Turn the source into checkable questions about our own repos instead of summarizing it.
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Outside-in recheck: use what others know to test what we believe

An agent that audits its own repo uses its own earlier framing: the checks it thinks of are the ones the repo already has. Outside material carries a different framing, and a different framing finds different defects. When the user shares a talk, a paper, an upstream spec change or a peer project's design doc, the useful output is a list of things in our repos that the source says should be true, with the state of each. A summary of the source is not the output.

> **The one principle.** Every load-bearing idea in the source becomes a question about us, answered with a tool result. "The speaker recommends X" is not a finding. "We do not run X on loom's nightly (`nightly.yml:40`)" is.

## Procedure

### 1. Extract the ideas as questions

Read the source and write a short numbered list of its load-bearing ideas or claims, usually 5 to 15. Phrase each as a checkable question for us: **do we do X, and is it enforced?** Drop ideas that are background or marketing. Keep the ones where a repo of ours could be doing the opposite without anyone noticing.

### 2. Map each question to repos and check it

Name the PulseEngine repos each question touches. Answer each with tool evidence: a `file:line`, the required-check list from the branch-protection API, the conclusion of a CI run step. Do not answer from memory or from the repo's own docs; the docs are the framing you are trying to escape.

For a broad sweep, delegate read-only audits per repo cluster (see [`delegate-by-cost`] for the model tier). Then verify the sharpest claims in each audit yourself before reporting, per [`clean-room-verification`]: re-run the grep, re-read the line, re-fetch the run. An audit result you did not re-check is a lead, not a finding.

### 3. Classify

Give every item exactly one state:

- **already-enforced**: a required check or a hook fails when it is violated, shown by the check list or a failing run.
- **present-but-not-enforced**: the practice exists on paper or in a script but nothing makes it bite. Typical forms are an optional check, `continue-on-error`, `|| true` or `|| echo`, a skipped step, a result that nothing consumes.
- **absent**: nothing does it.
- **not-applicable**: the idea does not fit our engine or our stage; say why in one clause.

Present-but-not-enforced is the class that matters most. It is also where [`gate-potency`] applies: run the negative control before calling a check enforced.

### 4. Report and ask

Report one compact table: idea, our state, evidence.

| # | idea (as a question) | our state | evidence |
|---|---|---|---|
| 1 | does the nightly fuzz run a fuzzer? | present-but-not-enforced | `nightly.yml:40` |

Below the table, rank the items to adopt by value per effort, and ask the owner which to act on as an option dialogue: each option with its pros, cons and your recommendation. In an unattended run post it through [`factory-notice`] and keep working on something else. Do not file issues before the owner answers.

### 5. File one issue per approved item

On approval, file one issue per item in the repo that owns the fix. Each issue states the finding with its evidence, and acceptance criteria that include a **negative control**: the change is accepted only when injecting the violation makes the check go red and removing it makes it green. Route each issue to the session or agent that owns that repo. For a pass over a tracker, hand the filed issues to [`issue-hunt`].

### 6. Keep confidential findings out of public issues

Some areas are confidential; the owner's private memories name them, and this file never does. A finding there does not go into a public issue, a public PR or a post. Record it where the memory says, tell the owner in the report, and file nothing public. When unsure whether an area is confidential, treat it as confidential and ask.

### 7. Offer to report upstream

Where a finding is a divergence from an upstream spec, or the source itself has a defect, offer to report it upstream as well and let the owner decide. A solo maintainer borrows community review this way: the upstream group checks the reading of its own spec for free. Quote the spec section and attach the minimal reproduction, with no private paths or hostnames.

## Worked example

On 2026-11-05, talks at the Bytecode Alliance Plumbers Summit led to a two-agent oracle audit across the repos. One agent audited and a second agent re-verified the claims cold. It produced 12 issues and 3 real defects:

- loom's nightly fuzz ran no fuzzer (loom#474);
- sigil's release step `cosign verify || echo` could never fail (sigil#350);
- witness's MC/DC claim went further than its evidence, found by a new truth-table oracle (witness#352).

All three were present-but-not-enforced. None was visible from inside the repo's own framing: the nightly job was green, the release step printed output, and the MC/DC report existed.

## Anti-patterns

- **Summarizing the source.** The user can read it. The value is the comparison with our state.
- **Answering from the repo's own docs.** That is the framing you are trying to leave.
- **Reporting an audit agent's claims unchecked.** Re-verify the sharpest ones.
- **Filing before the owner chooses.** Twelve unrequested issues cost a solo maintainer more than they save.
- **Calling a check enforced because it is in the workflow.** Look at the required-check list and the step conclusion.
- **A public issue for a confidential finding.**

## Where this composes

- [`clean-room-verification`]: verify the sharpest audit claims before reporting.
- [`gate-potency`]: negative-control any check you are about to classify as enforced.
- [`claim-verification`]: a claim our docs make that the source contradicts becomes a gated claim.
- [`issue-hunt`]: the filed issues enter the tracker pass.
- [`factory-notice`]: carries the option dialogue when the owner is not present.
