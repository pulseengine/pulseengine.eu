+++
title = "Trust at machine speed"
description = "Teams that are slow and safe get overtaken, and teams that are fast without evidence stall at their first audit or incident. The team that pulls away is fast and produces its evidence automatically. Europe's regulation has started asking for evidence in machine-readable form, and Germany's evidence culture is still mostly paper. What PulseEngine has today: claims checked in CI, traceability in rivet, and signed release evidence a buyer can check without the vendor's key."
date = 2026-11-02
draft = true
[taxonomies]
tags = ["process", "verification", "regulation", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Trust is an advantage at machine speed only when a machine can check it.**

- Slow and safe gets overtaken. Fast without evidence stalls at its first
  audit or incident. Fast with evidence produced in CI pulls away.
- The EU moved the AI Act's high-risk rules to December 2027 and August 2028.
  The Cyber Resilience Act already asks for a software bill of materials in a
  machine-readable format.
- Germany has the evidence culture (TÜV, ISO 26262, ASPICE), mostly in manual
  form. We put PulseEngine's evidence in CI and in signed release files. On
  28 October we checked one release's signature with cosign, without any key
  from us, and a one-byte change made the check fail.
{% </insight> %}

The posts before this one were about the inside of an agent factory:
[where the bottleneck is](/blog/safe-was-built-for-slow-humans/), [what an
ASPICE trace still lacks](/blog/aspice-is-not-a-queue/) and [whose attention
runs out first](/blog/the-scarce-resource-is-attention/). This one looks
outward, at the buyer, the assessor and the regulator, and at what they will
accept as a reason to trust software that was written in hours.

## Three kinds of team

The usual argument has two teams: one moves fast and breaks things, the other
is careful and slow. Agents add a third.

| Team | How it builds trust | What happens |
|---|---|---|
| **Slow and safe** | Reviews, documents and sign-offs by people | Overtaken. Its evidence costs the same per change whether an agent or a person wrote the change |
| **Fast without evidence** | None, or claims in a README | Stalls at the first audit, customer questionnaire or incident, when the evidence has to be produced after the fact |
| **Fast with automated evidence** | Checks that run on every change, results that are stored and signed | Pulls away. Evidence is a by-product of the pipeline, so its cost does not grow with the number of changes |

The third team is not careless about trust. It has moved trust from people
reading documents to machines checking results, and it reaches the same
audit with the evidence already on file.

## What Europe changed this year

On 7 May 2026 the European Parliament and the Council reached political
agreement on the Digital Omnibus on AI, which the Commission had proposed in
November 2025 "as part of the EU's simplification agenda to boost Europe's
competitiveness"[^ec-omnibus]. Under it, the rules for high-risk AI systems in
areas such as biometrics, education and employment apply from 2 December
2027, and those for systems built into products such as lifts or toys from
2 August 2028. Per the Commission's AI Act page, the amendments entered into
force on 27 July 2026[^ec-ai-framework].

The push behind it is older. Mario Draghi's report on European
competitiveness, September 2024, counted "around 100 tech-focused laws" and
over 270 regulators active in digital networks across the member states, and
named the AI Act as an example of the precautionary, ex-ante
approach[^draghi]. It also noted that only four of the world's top 50 tech
companies are European. We do not claim the report caused the omnibus; the
Commission frames the omnibus as simplification for competitiveness, and the
report argued for that.

The obligations that remain still need evidence, and some of it is now
specified as machine-readable. The Cyber Resilience Act, Regulation (EU)
2024/2847, has applied its reporting obligations since 11 September 2026,
and its main obligations apply from 11 December 2027[^ec-cra]. Annex I asks
manufacturers to identify and document the components of a product,
including "a software bill of materials in a commonly used and
machine-readable format" covering at least the top-level
dependencies[^cra-annex].

The regulation was simplified and delayed, but it did not stop asking for
evidence. What changed is the form. An SBOM that a tool can read is
something a pipeline can produce and a buyer's tool can check, without a
meeting.

## Germany: the culture is there, the form is manual

Germany's engineering trust is real and institutional: TÜV certification,
ISO 26262 for functional safety in road vehicles, Automotive SPICE for
process capability. What these share in practice is that the evidence is
assembled and read by people: documents, review records and assessment
interviews. That suits a team that ships a few times a year. It does not
suit a line where agents produce reviewed changes in hours, because each
change waits for a person to read its evidence.

Our own repositories show the gap from the other side. Measured on 26
October, gale has 302 of its 329 software requirements linked to a
verification measure in rivet, and none of them has a recorded result, because
gale's CI imports no test results into rivet ([ASPICE is not a
queue](/blog/aspice-is-not-a-queue/)). The links are machine-checked. The
evidence that the checks passed is not yet in the trace. Automating evidence
is work, and we are partway through it.

## What PulseEngine has, and what it shows

PulseEngine is a WebAssembly Component Model engine for safety-critical
systems, with machine-checked proofs for parts of it, and all of it is work
in progress. The parts relevant to trust are these, each stated at the
strength the repository supports.

**Claims checked in CI.** This site's repository keeps its load-bearing
claims in `claims.yaml`, each bound to evidence a script can re-derive. CI
runs `claim-check.py` on every pull request; on 28 October it reported 39 of
39 claims holding. A claim that drifts from its evidence fails the build
instead of waiting for a reader to notice.

**Traceability in rivet.** [rivet](https://github.com/pulseengine/rivet)
links requirements to design, code and verification measures, and this
site's CI runs `rivet validate` on every pull request. As the gale numbers above show, a link to a check is not yet
a recorded result.

**Signed release evidence.** [witness](https://github.com/pulseengine/witness)
measures MC/DC-style branch coverage for WebAssembly components. Each release
ships a compliance-evidence archive with per-verdict coverage reports and
signed in-toto statements. Its README positions witness as supplementary
evidence in a qualification dossier, not primary, until v1.0. On 28 October
we downloaded the v0.45.0 archive and checked it with cosign 3.1.2 against
the Sigstore certificate published with it (two flag-deprecation warnings
removed from the output):

```text
$ cosign verify-blob \
    --certificate witness-v0.45.0-compliance-evidence.tar.gz.cert \
    --signature   witness-v0.45.0-compliance-evidence.tar.gz.sig \
    --certificate-identity-regexp '^https://github.com/pulseengine/witness/' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    witness-v0.45.0-compliance-evidence.tar.gz
Verified OK
```

The certificate's identity is witness's `release.yml` workflow at
`refs/tags/v0.45.0`. With one byte appended to the archive, the same command
exited 1. Neither step used a key we hold. The trust moves to GitHub's
workflow identity and the Sigstore transparency log, both outside our
control, and the check shows where the archive came from, not that its
coverage numbers are right. Re-running the verdicts is a separate step.

**sigil** is our supply-chain tool for WebAssembly: embedded signatures,
Sigstore keyless signing and SLSA provenance, per its repository. The witness
archive above was checked with cosign, not with sigil.

## What to take from this

**Make the evidence a by-product.** If producing it needs a person, it will
lag behind agent-written changes. If CI produces and signs it, it keeps pace.

**Let the buyer check without you.** A signature tied to a public build
identity, a machine-readable SBOM and a claims file a script can re-run can
be checked by someone who does not trust the vendor. A PDF signed off by the
vendor cannot.

**Be exact about what each check covers.** A signature shows origin, a
coverage report shows which conditions the tests distinguish, and a trace
link shows that a check exists. None of them alone shows that the software is
safe.

## Limits and sources

The three kinds of team are an argument, not a measured classification. The
regulatory dates are from the European Commission's pages, read on 28
October 2026; the CRA annex text was read from a third-party mirror of the
Official Journal because EUR-Lex did not serve the page. The PulseEngine
statements come from this repository, the witness and sigil repositories,
and one cosign run on 28 October 2026. Nothing here is a certification or an
assessment result.

[^ec-omnibus]: European Commission, *EU agrees to simplify AI rules to boost innovation and ban 'nudification' apps to protect citizens*, press release IP/26/1024, 7 May 2026. [ec.europa.eu](https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1024). Primary (official press release). Source of the agreement date, the proposal date and the two application dates.

[^ec-ai-framework]: European Commission, *AI Act*, Shaping Europe's digital future. [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai). Primary (official policy page). Source of the entry into force on 27 July 2026.

[^draghi]: Mario Draghi, *The future of European competitiveness. Part A: A competitiveness strategy for Europe*, European Commission, 9 September 2024. [commission.europa.eu](https://commission.europa.eu/topics/eu-competitiveness/draghi-report_en). Primary (report). The 100 laws, 270 regulators, the AI Act example and the top-50 figure are from Part A.

[^ec-cra]: European Commission, *Cyber Resilience Act*, Shaping Europe's digital future. [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act). Primary (official policy page). Source of the regulation number and the 11 September 2026 and 11 December 2027 dates.

[^cra-annex]: Regulation (EU) 2024/2847, Annex I, Part II, point (1). Official text at [eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng); quoted from the mirror at [springlex.eu](https://www.springlex.eu/en/packages/cra/cra-regulation/annex-1/) because EUR-Lex did not serve the page to our client. Secondary copy of the primary text.

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
