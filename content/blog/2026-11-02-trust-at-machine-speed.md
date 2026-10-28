+++
title = "Trust at machine speed"
description = "Trust is an advantage at machine speed only when a machine can check it. Europe's regulation has started asking for some evidence in machine-readable form, while German assessment practice still has people assemble and read most of it. What PulseEngine has today: claims checked in CI, traceability in rivet, and a release signature a buyer can check without the vendor's key."
date = 2026-11-02
draft = true
[taxonomies]
tags = ["process", "verification", "regulation", "ai-agents"]
authors = ["Ralf Anton Beier"]
+++

{% <insight> %}
**Trust is an advantage at machine speed only when a machine can check it.**

- Of three kinds of team, we argue, slow and safe gets overtaken, fast without
  evidence stalls at its first audit or incident, and fast with evidence
  produced in CI pulls away.
- The EU moved the AI Act's high-risk rules to December 2027 and August 2028.
  The Cyber Resilience Act will require a software bill of materials in a
  machine-readable format from December 2027.
- Germany has the evidence culture: ISO 26262 functional-safety assessment,
  often by TÜV, and ASPICE assessments by intacs-certified assessors. In our
  experience, people still assemble and read most of that evidence.
- We put some of PulseEngine's evidence in CI and in signed release files. On
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
| **Fast with automated evidence** | Checks that run on every change, results that are stored and signed | Pulls away. Machines check results instead of people reading documents, and evidence is a by-product of the pipeline, so its cost does not grow with the number of changes and it is already on file at the audit |

## What Europe changed this year

On 7 May 2026 the European Parliament and the Council reached political
agreement on the Digital Omnibus on AI, which the Commission had proposed in
November 2025 "as part of the EU's simplification agenda to boost Europe's
competitiveness"[^ec-omnibus]. Under it, the rules for high-risk AI systems in
areas such as biometrics, education and employment apply from 2 December
2027, and those for systems built into products such as lifts or toys from
2 August 2028. Per the Commission's AI Act page, the amendments entered into
force on 27 July 2026[^ec-ai-framework].

The argument for simplification is older. Mario Draghi's report on European
competitiveness, September 2024, counted "around 100 tech-focused laws" and
over 270 regulators active in digital networks across the member states. As
an example of the precautionary, ex-ante approach it named the AI Act's extra
requirements for general-purpose AI models above a computational-power
threshold[^draghi]. We do not claim the report caused the omnibus. The
evidence on cost is mixed: an LSE discussion paper of July 2026, using patent
data for the GDPR, the Green Deal and the AI Act, found that "no regulatory
package was followed by an absolute decline in EU innovation"[^lse-dp93].

The remaining obligations still need evidence, and some of it is now
specified as machine-readable. The Cyber Resilience Act, Regulation (EU)
2024/2847, has applied its reporting obligations since 11 September 2026,
and its main obligations apply from 11 December 2027[^ec-cra]. Annex I asks
manufacturers to identify and document vulnerabilities and components of a
product, including "a software bill of materials in a commonly used and
machine-readable format" covering at least the top-level
dependencies[^cra-annex]. Manufacturers must draw up the SBOM, but Annex II
point 9 makes giving it to users optional, and Recital 77 says they should not
be obliged to make it public. Annex VII point 8 lists the SBOM, if
applicable, in the technical documentation, which a market surveillance
authority can ask for on reasoned request when it needs it to check
compliance. An SBOM a tool can read is one a pipeline can produce, and one a
buyer's tool can parse if the manufacturer shares it.

## Germany: the evidence culture and its form

In Germany, trust in safety-related software rests on ISO 26262
functional-safety assessment, often by TÜV, and on ASPICE assessments by
intacs-certified assessors. In the author's observation, the evidence in
that practice is mostly assembled and read by people:
documents, review records and assessment interviews. Assessments happen at
milestones and sample that record. Between them, the project's own
change-impact analysis and work-product reviews are done by people for each
change. That suits a team that ships a few times a year. It does not suit a
line where agents produce reviewed changes in hours, because those per-change
steps then have to keep pace with the agents.

## What PulseEngine has, and what it shows

PulseEngine is a WebAssembly Component Model engine for safety-critical
systems, with machine-checked proofs for parts of it; everything is work in
progress. Three of its pieces bear on trust.

**Claims checked in CI.** This site's repository keeps its load-bearing
claims in `claims.yaml`, each bound to evidence a script can re-derive. CI
runs `claim-check.py` on every pull request to main; on 28 October it
reported every claim holding. A claim that drifts from its evidence fails the
build instead of waiting for a reader to notice.

**Traceability in rivet.** [rivet](https://github.com/pulseengine/rivet)
links requirements to design, code and verification measures, and this
site's CI runs `rivet validate` on every pull request.

gale, one of the PulseEngine repositories, has 302 of its 329 software
requirements linked to a verification measure in rivet, measured on 26
October, and none of them has a recorded result, because gale's CI imports no
test results into rivet ([ASPICE is not a queue](/blog/aspice-is-not-a-queue/)).
`rivet validate` checks that each link resolves, not that the check passed.

**Signed release evidence.** [witness](https://github.com/pulseengine/witness)
measures MC/DC-style branch coverage for WebAssembly components. Each release
since v0.6.4 ships a compliance-evidence archive with per-verdict coverage
reports and in-toto statements. Each in-toto statement is DSSE-signed with a
per-release ephemeral Ed25519 key, whose public half ships in the archive. In
v0.45.0, each statement also ships with its own Sigstore keyless certificate
and signature, which we did not check. A signature checked against a key
shipped with the data does not show where the data came from; a keyless
signature can.

Since v0.10.0 the archive itself also carries a Sigstore keyless signature.
Its README positions witness as supplementary evidence in a qualification
dossier until v1.0. On 28 October we downloaded
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
at `refs/tags/v0.45.0`; it pins the tag name, not the commit. With one byte
appended to the archive, the same command exited 1. The check relies on
GitHub's OIDC token issuance and Sigstore's certificate authority and
transparency log, which we do not control. It needs network access to
Sigstore's log because the archive ships without a Sigstore bundle. The
release's SHA256SUMS.txt, which lists the archive's hash, has one. The check
shows that a workflow run in our repository at that tag signed these bytes.
It does not show what that workflow did, or that the coverage numbers are
right.

## What a buyer can ask for

**A check that does not need the vendor.** A signature tied to a public build
identity shows where the bytes came from without the vendor's key or word;
the buyer trusts GitHub and Sigstore instead. Re-running a claims file lets a reader re-derive the claims
against the repository's evidence instead of reading them. A PDF signed off by
the vendor offers neither.

**A statement of what each check covers.** A signature shows origin, a
coverage report shows which compiled, Wasm-level conditions the tests
distinguish, and a trace link shows that a check exists. None of them alone
shows that the software is safe.

## What a critic would say

**"PulseEngine certifies nothing. Glass house."** Correct: nothing here is
certified or qualified. What we claim is that the evidence can be checked, and
for tools the route to more is qualification under RTCA DO-330, the tool
qualification standard used with DO-178C in aerospace[^do330]; automotive has
its own tool-confidence process in ISO 26262. Qualification happens inside an
applicant's certification project, so a vendor can only prepare qualification
data. witness plans a small checker audited under DO-330 for v1.0, and we have
prepared no qualification data for any of our tools.

**"Verification gives false confidence."** It can: a proof is only as good as
its statement. A survey of AI-assisted formal mathematics (arXiv v2, October
2026) notes that compilation shows a candidate elaborates, "not that it
faithfully represents the source"[^solvers], and on the VERINA benchmark,
based on one trial per task, the best model, OpenAI o3, reached 52.3% on
specification soundness and completeness and 4.9% proof success[^verina]. Our
own checks get the same treatment: we broke the claim pinning the previous
post on purpose and claim-check exited 1, though `claims.yaml` pins text and
patterns, not behaviour.

**"Agents reviewing agents is not independence."** The posts on this site are
reviewed by fresh-context agents in split roles, and their findings and fixes
are recorded in the pull request description and its commits. Those
reviewers share a model family with the author, so the review is advisory and nothing like an independent
assessment; the human step is the owner deciding to publish.

**"Your agents are the attack surface."** In the Clinejection case, an issue
title was placed in the prompt of a triage agent with shell access, and the
chain ended in a tampered release[^clinejection]. At Black Hat USA 2026,
Novee Security reported that an issue from an account with no repository
rights reached CI secrets in the vendors' own repositories for Claude Code,
Gemini CLI and OpenAI Codex[^csa-blackhat], and Google's advisory for Gemini
CLI rates its headless-mode flaw critical[^gemini-ghsa]. Our issue-class check
refuses to execute issue bodies, and an agent accepts only an answer that
names an option it offered; that option check limits what a forged answer can
pick but does not authenticate the answerer, and our issue-hunt sessions do
read issue text into an agent's prompt. We audited our agent workflows on 28 October 2026
and fixed one finding the same day (plugin 0.45.1 and 0.45.2); further fixes
are in progress. The audit itself is not published.

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

[^draghi]: Mario Draghi, *The future of European competitiveness. Part A: A competitiveness strategy for Europe*, published on the European Commission's site (Publications Office of the European Union edition, 2025), September 2024; the landing page gives 9 September 2024. [commission.europa.eu](https://commission.europa.eu/topics/eu-competitiveness/draghi-report_en). Primary (report). The report states that it does not represent the Commission's official position; the views are Draghi's. The 100 laws, 270 regulators and the AI Act compute-threshold example are from Part A.

[^ec-cra]: European Commission, *Cyber Resilience Act*, Shaping Europe's digital future. [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act). Primary (official policy page). Source of the regulation number and the 11 September 2026 and 11 December 2027 dates.

[^cra-annex]: Regulation (EU) 2024/2847, Annex I, Part II, point (1); also Annex II, point (9); Annex VII, point (8); and Recital 77. Official text at [eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng); read from the mirror at springlex.eu ([Annex I](https://www.springlex.eu/en/packages/cra/cra-regulation/annex-1/), [Annex II](https://www.springlex.eu/en/packages/cra/cra-regulation/annex-2/), [Annex VII](https://www.springlex.eu/en/packages/cra/cra-regulation/annex-7/), [Recital 77](https://www.springlex.eu/en/packages/cra/cra-regulation/recital-77/)) because EUR-Lex did not serve the page to our client. Secondary copy of the primary text.

[^lse-dp93]: Slobodan Tomić and Ognjen Dragičević, *Does EU Regulation Stifle Innovation? In search for a 'Brussels Innovation Effect'*, LSE CARR Discussion Paper 93, July 2026. [lse.ac.uk](https://www.lse.ac.uk/government/research/research-groups/carr/assets/documents/D-P/DP-93.pdf). Primary (discussion paper, not peer-reviewed). Based on OECD REGPAT patent data and R&D intensity.

[^do330]: RTCA, *DO-330: Software Tool Qualification Considerations*. [my.rtca.org](https://my.rtca.org/productdetails?id=a1B36000001IcfkEAC). Primary (standard, product page). witness's plan is from its README, [github.com/pulseengine/witness](https://github.com/pulseengine/witness).

[^solvers]: Eric Jiang et al., *From Solvers to Research: Large Language Model-Driven Formal Mathematics at the Research Frontier*, arXiv:2607.07779, v2, 19 October 2026. [arxiv.org](https://arxiv.org/abs/2607.07779). Primary (survey and position paper).

[^verina]: Zhe Ye, Zhengxu Yan, Jingxuan He, Timothe Kasriel, Kaiyu Yang and Dawn Song, *VERINA: Benchmarking Verifiable Code Generation*, arXiv:2505.23135, v3, 16 March 2026. [arxiv.org](https://arxiv.org/abs/2505.23135). Primary (benchmark paper). Figures from the v3 abstract; earlier versions report different numbers.

[^clinejection]: Cloud Security Alliance AI Safety Initiative, *Clinejection: Prompt Injection in GitHub Issue Titles Enables CI/CD Cache Poisoning and Supply Chain Compromise*, research note, 10 March 2026. [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/research/csa-research-note-clinejection-prompt-injection-cicd-cache-p/). Secondary (research note on Adnan Khan's disclosure).

[^csa-blackhat]: Cloud Security Alliance, *Three AI Coding Agents, One GitHub Issue: CI/CD Secrets Exposed*, research note, 8 August 2026. [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/08/CSA_research_note_ai_coding_agent_cicd_secrets_20260808-csa-styled.pdf). Secondary (AI-assisted research note, which says it has not undergone official CSA review, reporting Novee Security's Black Hat talk of 5 August 2026).

[^gemini-ghsa]: Google, *Gemini CLI: Remote Code Execution via workspace trust and tool allowlisting bypasses*, GitHub security advisory GHSA-wpqr-6v78-jr5g, 24 April 2026. [github.com/advisories](https://github.com/advisories/GHSA-wpqr-6v78-jr5g). Primary (vendor advisory).

---

*This post is part of [PulseEngine](/) — a WebAssembly Component Model engine
for safety-critical systems, with machine-checked proofs for parts of it
(work in progress).*
