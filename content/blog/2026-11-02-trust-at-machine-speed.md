+++
title = "Trust at machine speed"
description = "At machine speed, the team that pulls away is the one whose evidence is produced automatically. Europe's regulation has started asking for some evidence in machine-readable form, while German assessment practice, in the author's observation, still has people assemble and read most of it. What PulseEngine has today: claims checked in CI, traceability in rivet, and a release signature a buyer can check without the vendor's key."
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
  The Cyber Resilience Act will require a software bill of materials in a
  machine-readable format from December 2027.
- German practice around ISO 26262 and ASPICE, often with TÜV assessment, has
  the evidence culture. In the author's observation, people still assemble and
  read most of that evidence.
- We put PulseEngine's evidence in CI and in signed release files. On
  28 October we checked one release archive's signature with cosign, without
  any key from us, and a one-byte change made the check fail.
{% </insight> %}

The posts before this one were about the inside of an agent factory:
[where the bottleneck is](/blog/safe-was-built-for-slow-humans/), [what an
ASPICE trace still lacks](/blog/aspice-is-not-a-queue/) and [whose attention
runs out first](/blog/the-scarce-resource-is-attention/). This one looks
outward, at the buyer, the assessor and the regulator, and at what they will
accept as a reason to trust software that was written in hours.

## Three kinds of team

Agents add a third kind of team to the usual two:

| Team | How it builds trust | What happens |
|---|---|---|
| **Slow and safe** | Reviews, documents and sign-offs by people | Overtaken. Its evidence costs the same per change whether an agent or a person wrote the change |
| **Fast without evidence** | None, or claims in a README | Stalls at the first audit, customer questionnaire or incident, when the evidence has to be produced after the fact |
| **Fast with automated evidence** | Checks that run on every change, results that are stored and signed | Pulls away. Evidence is a by-product of the pipeline, so its cost does not grow with the number of changes |

The third team moves trust from people reading documents to machines checking
results, so it reaches the same audit with the evidence already on file.

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
over 270 regulators active in digital networks across the member states. As
an example of the precautionary, ex-ante approach it named the AI Act's extra
requirements for general-purpose AI models above a computational-power
threshold[^draghi]. We do not claim the report caused the omnibus.

The obligations that remain still need evidence, and some of it is now
specified as machine-readable. The Cyber Resilience Act, Regulation (EU)
2024/2847, has applied its reporting obligations since 11 September 2026,
and its main obligations apply from 11 December 2027[^ec-cra]. Annex I asks
manufacturers to identify and document vulnerabilities and components of a
product, including "a software bill of materials in a commonly used and
machine-readable format" covering at least the top-level
dependencies[^cra-annex]. Manufacturers must draw up the SBOM, but Annex II
point 9 makes giving it to users optional, and Recital 77 says they should not
be obliged to make it public. An SBOM a tool can read is one a pipeline can
produce and, where the manufacturer shares it, a buyer's tool can parse.

## Germany: the evidence culture and its form

Germany's engineering trust rests on institutions: German practice around
ISO 26262 for functional safety in road vehicles and Automotive SPICE for
process capability, often with TÜV assessment. In the author's observation,
the evidence in that practice is mostly assembled and read by people:
documents, review records and assessment interviews. That suits a team that
ships a few times a year. It does not suit a line where agents produce
reviewed changes in hours, because each change waits for a person to read its
evidence.

gale has 302 of its 329 software requirements linked to a verification
measure in rivet, measured on 26 October, and none of them has a recorded
result, because gale's CI imports no test results into rivet ([ASPICE is not
a queue](/blog/aspice-is-not-a-queue/)). The links are machine-checked. The
evidence that the checks passed is not yet in the trace.

## What PulseEngine has, and what it shows

PulseEngine is a WebAssembly Component Model engine for safety-critical
systems, with machine-checked proofs for parts of it, and all of it is work
in progress. Three parts of it are relevant to trust.

**Claims checked in CI.** This site's repository keeps its load-bearing
claims in `claims.yaml`, each bound to evidence a script can re-derive. CI
runs `claim-check.py` on every pull request to main; on 28 October it
reported every claim holding. A claim that drifts from its evidence fails the
build instead of waiting for a reader to notice.

**Traceability in rivet.** [rivet](https://github.com/pulseengine/rivet)
links requirements to design, code and verification measures, and this
site's CI runs `rivet validate` on every pull request.

**Signed release evidence.** [witness](https://github.com/pulseengine/witness)
measures MC/DC-style branch coverage for WebAssembly components. Each release
since v0.6.4 ships a compliance-evidence archive with per-verdict coverage
reports and in-toto statements. The in-toto statements are signed with an
ephemeral key shipped in the archive, and the archive itself carries a
Sigstore keyless signature. Its README positions witness as supplementary
evidence in a qualification dossier until v1.0. On 28 October we downloaded
the v0.45.0 archive and checked its keyless signature with cosign 3.1.2
against the Sigstore certificate published with it (two flag-deprecation
warnings removed from the output):

```text
$ cosign verify-blob \
    --certificate witness-v0.45.0-compliance-evidence.tar.gz.cert \
    --signature   witness-v0.45.0-compliance-evidence.tar.gz.sig \
    --certificate-identity 'https://github.com/pulseengine/witness/.github/workflows/release.yml@refs/tags/v0.45.0' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    witness-v0.45.0-compliance-evidence.tar.gz
Verified OK
```

The command pins the exact signer identity, witness's `release.yml` workflow
at `refs/tags/v0.45.0`. With one byte appended to the archive, the same
command exited 1. Neither step used a key we hold. The check relies on
GitHub's OIDC token issuance and Sigstore's certificate authority and
transparency log, which we do not control, and it needs network access to
Sigstore's log because no bundle is shipped. It shows that a workflow run in
our repository at that tag signed these bytes. It does not show what that
workflow did, or that the coverage numbers are right.

## What to take from this

**Let the buyer check without you.** A signature tied to a public build
identity and a claims file a script can re-run can be checked without the
vendor's key and without taking the vendor's word for where it came from. A
PDF signed off by the vendor cannot.

**Be exact about what each check covers.** A signature shows origin, a
coverage report shows which compiled, Wasm-level conditions the tests
distinguish, and a trace link shows that a check exists. None of them alone
shows that the software is safe.

## Limits and sources

The three kinds of team are an argument; nobody measured them. The
description of German assessment practice is the author's observation. The
regulatory dates are from the European Commission's pages, read on 28
October 2026; the CRA text was read from a third-party mirror of the
Official Journal because EUR-Lex did not serve the page. The PulseEngine
statements come from this repository, the witness and sigil repositories,
and one cosign run on 28 October 2026. sigil (embedded signatures, Sigstore
keyless signing, SLSA provenance) was not used for this check. Nothing here
is a certification or an assessment result.

[^ec-omnibus]: European Commission, *EU agrees to simplify AI rules to boost innovation and ban 'nudification' apps to protect citizens*, press release IP/26/1024, 7 May 2026. [ec.europa.eu](https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1024). Primary (official press release). Source of the agreement date, the proposal date and the two application dates.

[^ec-ai-framework]: European Commission, *AI Act*, Shaping Europe's digital future. [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai). Primary (official policy page). Source of the entry into force on 27 July 2026.

[^draghi]: Mario Draghi, *The future of European competitiveness. Part A: A competitiveness strategy for Europe*, published by the European Commission, September 2024; the landing page gives 9 September 2024. [commission.europa.eu](https://commission.europa.eu/topics/eu-competitiveness/draghi-report_en). Primary (report). The report states that it "should not be considered as representative of the European Commission's official position"; the views are Draghi's. The 100 laws, 270 regulators and the AI Act compute-threshold example are from Part A.

[^ec-cra]: European Commission, *Cyber Resilience Act*, Shaping Europe's digital future. [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act). Primary (official policy page). Source of the regulation number and the 11 September 2026 and 11 December 2027 dates.

[^cra-annex]: Regulation (EU) 2024/2847, Annex I, Part II, point (1); also Annex II, point (9), and Recital 77. Official text at [eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng); read from the mirror at springlex.eu ([Annex I](https://www.springlex.eu/en/packages/cra/cra-regulation/annex-1/), [Annex II](https://www.springlex.eu/en/packages/cra/cra-regulation/annex-2/), [Recital 77](https://www.springlex.eu/en/packages/cra/cra-regulation/recital-77/)) because EUR-Lex did not serve the page to our client. Secondary copy of the primary text.

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
