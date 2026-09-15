# Generated media — what we may publish, and what it may not stand for

Applies to anything we publish that an audience sees rather than reads: YouTube
videos, animations, diagrams rendered from a model, synthesised narration,
generated screenshots. relay produces the most of it today; other repos will.

Two separate constraints. The legal one is narrow and we currently sit outside
it. The evidence one is ours, is stricter, and is the one that can actually
damage the project.

## 1. The legal line — EU AI Act Article 50(4)

Binding since **2026-08-02**. Elaborated by the *Code of Practice on
Transparency of AI-Generated Content* (voluntary, final 2026-06-10). Two limbs,
and only two.

**Deep fakes.** Article 3(60) defines one as

> AI-generated or manipulated image, audio or video content that resembles
> existing persons, objects, places, entities or events and would falsely appear
> to a person to be authentic or truthful.

Both conditions must hold. **There is no editorial-review exemption on this
limb** — a human approving a deep fake does not remove the disclosure duty.

**Published text on matters of public interest.** The duty attaches only to text

> published with the purpose of informing the public on matters of public
> interest, without human review or editorial control and where no natural or
> legal person holds editorial responsibility for the publication

Five cumulative conditions, so human editorial responsibility removes it.

**We are not a provider** under Article 50(2). That limb covers "providers of AI
systems generating synthetic audio, image, video or text content". We ship
verification, build and attestation tooling; synth generates machine code by
program synthesis, not synthetic media. The machine-readable marking
commitments do not apply to us.

### Where that leaves us today

| what we publish | in scope | why |
|---|---|---|
| Fully generated explainers and animations | no | evident illustrations; they do not pass as authentic footage |
| Conference recordings | no | real recording of a real event |
| Synthetic narration over real capture | no, normally | a generic synthetic voice resembles no *existing* person |
| Blog posts written by agents | no | every post carries a named author and `ready = true` is a per-post human act |
| **Generated footage depicting real hardware or a real run** | **yes** | resembles existing objects and events, and would read as authentic |

The blog exemption is carried entirely by the author byline and the
`ready = true` gate in `blog-autopublish.yml`. Treat both as controls, not as
ergonomics: removing the opt-in to reduce friction would flip the position
silently, with nothing going red.

*This is a reading of the published text, not legal advice.*

## 2. The line that matters more: a rendering is not a result

The regulation asks whether an audience could be deceived about how a video was
made. Our own standard is harder, because our product is evidence.

**A generated depiction must never stand in for a measured result.** An
animation of the pipeline is a diagram and is fine. An animation showing gust
booting on a board, or a drone flying under verified control, is a *claim* — and
if the footage is generated then the claim's evidence is synthetic, whatever the
label says.

This is [[pulseengine-toolchain]]'s evidence discipline applied to media, and it
is the same error the `evidence-transfer` skill names: a result that is true
about the wrong substrate. That skill was written for an emulator run filed as
on-target evidence. A rendered board is the same mistake with better production
values, and it is worse, because a viewer cannot re-run it.

The claims most at risk are the ones we are proudest of, because they are the
ones worth filming: bit-identical boot across three chips, 3.5 KB on real
silicon, a component running on a real drone.

## 3. Before publishing generated media

1. **Does it depict something real?** If yes, it is either genuine capture or it
   is labelled. There is no third option.
2. **Does it carry a claim?** If a viewer could take it as showing a result,
   the result must exist and be reproducible, and the footage must be real.
   Cite the same evidence the written claim cites.
3. **Is a named person responsible for publishing it?** For text that is what
   keeps us outside Article 50(4); for media it is simply how we work.
4. **Label when in doubt.** Disclosure costs a line of description. A synthetic
   depiction taken as evidence costs the thing the whole project sells.

See [[pulseengine-philosophy]] for why claims are bound to evidence at all, and
[[pulseengine-prose-conventions]] for the written counterpart.
