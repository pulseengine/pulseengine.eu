+++
title = "The OS as components — and the factory that lowers it"
description = "Wasm Research Day 2026. The Component Model as the integration step for an operating system, the same components lowered ahead of time onto three architectures, and an honest account of what is still missing."
date = 2026-08-06
template = "talk.html"

[extra]
event = "Wasm Research Day 2026"
slot = "30 minutes, remote"
+++

<section class="slide">
  <p class="slide__act">Wasm Research Day 2026 &middot; 30 minutes</p>
  <h1>The OS as components<span class="dim">,</span><br>and the factory that lowers it</h1>
  <p class="slide__lead">Most embedded stacks make the operating system platform-specific
  and hope the application is portable. We are inverting that.</p>
  <p class="slide__cite">pulseengine.eu &middot; every number on these slides says where it came from</p>
</section>

<section class="slide">
  <p class="slide__act">Act I &middot; the inversion</p>
  <h2>Portability is usually asked of the wrong layer</h2>
  <div class="split">
    <div class="split__col">
      <h3>the usual arrangement</h3>
      <p>The OS is written for the chip. The application is written against the OS
      and <em>hoped</em> to be portable. Every new board re-opens the OS.</p>
    </div>
    <div class="split__col">
      <h3>what we are trying</h3>
      <p>The OS itself is WebAssembly components. The Component Model is the
      integration step — between OS components, between the OS and its drivers,
      and between the OS and the tenants above it.</p>
    </div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act I &middot; the inversion</p>
  <h2>The car and the tires</h2>
  <p class="slide__lead">Think of the OS and everything above it as the car, and the
  handful of native functions that actually touch the hardware as the tires.</p>
  <p>For new terrain — another chip, another board — <span class="hi">you change the
  tires, not the car.</span></p>
  <p class="slide__cite">This talk spends most of its time on the factory that
  builds the car, because that is the part that has to be qualified once.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>Two seams, and everything hangs off them</h2>
  <div class="split">
    <div class="split__col">
      <h3>gust:os &mdash; what tenants see</h3>
      <pre class="evidence">time · log · spawn
exec · timer · taskdisp
channel · io</pre>
    </div>
    <div class="split__col">
      <h3>gust:hal &mdash; what touches metal</h3>
      <pre class="evidence">mmio · irq · gpio
spi · timer · uart · dma</pre>
    </div>
  </div>
  <p>A driver sits <em>below</em> the OS: it may import <code>gust:hal</code> and
  must not depend upward on <code>gust:os</code>. That is not a convention — it is
  a gate that fails the build.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>Integration step, not a build step</h2>
  <div class="chain">
    <div class="chain__stage"><span class="chain__name">wac</span><span class="chain__what">compose the components into one</span></div>
    <div class="chain__stage"><span class="chain__name">meld</span><span class="chain__what">fuse — one shared memory</span></div>
    <div class="chain__stage"><span class="chain__name">loom</span><span class="chain__what">optimize, and emit what it proved</span></div>
    <div class="chain__stage"><span class="chain__name">synth</span><span class="chain__what">lower to ARM / RISC-V</span></div>
    <div class="chain__stage"><span class="chain__name">.o</span><span class="chain__what">one relocatable object · no runtime on the device</span></div>
  </div>
  <p>Wasm is where the pieces are joined and checked. It is not present at run
  time — there is no interpreter, no JIT, and no engine resident on the chip.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>Three dies, one session</h2>
  <p class="evidence__label">captured 2026-08-04, all three probes attached at once</p>
  <div class="stack">
    <pre class="evidence"><span class="dim">Cortex-M4 · NUCLEO-G474RE</span>
gust-wdg-silicon OK: IWDG watchdog reset CONFIRMED on real STM32G474
silicon (RCC_CSR=0x34000000, IWDGRSTF=<span class="ok">1</span>)</pre>
    <pre class="evidence"><span class="dim">Cortex-M3 · STM32F100 VLDISCOVERY — the same .o, a second die</span>
gust-wdg-silicon OK: IWDG watchdog reset CONFIRMED on real STM32F100
silicon (RCC_CSR=0x34000000, IWDGRSTF=<span class="ok">1</span>)</pre>
    <pre class="evidence"><span class="dim">RISC-V · ESP32-C3 rev v0.4</span>
correctness: <span class="ok">IDENTICAL</span> ok over [0,2047]
gust_mix_native     271 milliticks/call
gust_mix_dissolved  499 milliticks/call
ratio_x1000        1839   (mismatch=<span class="ok">0</span>)</pre>
  </div>
  <p class="slide__cite">The watchdog legs are one happy path on two dies. They do
  not evidence the cannot-un-start property — the firmware never attempts an
  un-start. That stays a source-level proof.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>The tires are smaller than you would guess</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>A whole STM32 USART driver, dissolved</span><span class="ledger__val">326 B flash · 0 SRAM</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>Its entire trusted surface</span><span class="ledger__val">3 relocations</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>DMA modelled as an ownership round-trip</span><span class="ledger__val">218 B · 6 Kani proofs</span></div>
  </div>
  <p>The three relocations are <code>mmio_read32</code>, <code>mmio_write32</code>,
  <code>irq_poll</code>. Everything above them — the protocol, the state machine,
  the error handling — is wasm that got lowered.</p>
</section>

<section class="slide">
  <p class="slide__act">Act III &middot; the tires</p>
  <h2>Same bytes. Three different answerers.</h2>
  <div class="split">
    <div class="split__col">
      <h3>in a browser tab</h3>
      <p><code>gust:hal/mmio</code> answered by a JS array. Pulled from the
      registry, signature verified, transpiled — <span class="ok">10 / 10</span>
      behavioural checks pass.</p>
    </div>
    <div class="split__col">
      <h3>on a host</h3>
      <p>Answered by a Rust array under a component runtime. Same script, same
      assertions.</p>
    </div>
    <div class="split__col">
      <h3>on silicon</h3>
      <p>Answered by real registers. The composite is lowered first; nothing
      interprets it.</p>
    </div>
  </div>
  <p class="slide__cite">The published artifact is the same one in all three:
  <code>ghcr.io/pulseengine/gale-nano:0.6.0</code>, signed, pulled — not rebuilt
  per target.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <blockquote class="slide__quote">The pipeline is qualified once; every product
  that uses it inherits that qualification.</blockquote>
  <p class="slide__cite">— our own words, from a post two years before this talk</p>
  <p>This is why the factory matters more than the car. A car you qualify once is
  one car. A <em>factory</em> you qualify once is every car it will ever build.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Six faces, not four tools</h2>
  <div class="split">
    <div class="split__col">
      <h3>architect</h3><p><code>spar</code> — AADL / SysML. The WIT is generated from the model, not hand-written.</p>
    </div>
    <div class="split__col">
      <h3>build</h3><p><code>meld</code> fuse · <code>loom</code> optimize · <code>synth</code> lower · <code>sigil</code> attesting across all of it.</p>
    </div>
    <div class="split__col">
      <h3>verify</h3><p><code>witness</code> MC/DC on the shipped wasm · <code>scry</code> abstract interpretation · Verus, Rocq, Lean, Kani as build rules.</p>
    </div>
    <div class="split__col">
      <h3>trace</h3><p><code>rivet</code> — typed requirements, decisions and tests. Broken links fail the build.</p>
    </div>
    <div class="split__col">
      <h3>run</h3><p><code>kiln</code> runtime · <code>gale</code> verified kernel primitives · the applications above them.</p>
    </div>
    <div class="split__col">
      <h3>agent</h3><p>The loop that files findings between repos — and the governance that keeps 30+ repos to the same rules.</p>
    </div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>No stage trusts the one above it</h2>
  <p>When <code>loom</code> proves a value range, it does not just use it and
  discard it. It writes it into a custom section — <code>wsc.facts</code> — keyed
  to <em>values</em>, not positions, so renumbering cannot silently re-point a fact.</p>
  <p><code>synth</code> never re-derives that fact and never takes it on faith. It
  proves its own specialization correct <em>given</em> the fact, per site, and
  emits a certificate.</p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">measured</span><span>A bounds-guard sequence, with the fact forwarded</span><span class="ledger__val">232 &rarr; 104 B</span></div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Faster <em>because</em> it is proven</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag dim">baseline</span><span>native LLVM, full clamp</span><span class="ledger__val">0.50 cyc/call · 1.00&times;</span></div>
    <div class="ledger__row"><span class="ledger__tag dim">today</span><span>dissolved, as shipped</span><span class="ledger__val">0.83 cyc/call · 1.65&times;</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">measured floor</span><span>clamp elided because a proof allows it</span><span class="ledger__val">0.23 cyc/call · <span class="ok">0.45&times;</span></span></div>
  </div>
  <p>Not a model — a measured floor, soundness-gated. The elision is only legal
  because something upstream proved the bound. <span class="hi">A compiler with no
  verifier in its pipeline structurally cannot reach it.</span></p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Qualify the checker, not the prover</h2>
  <p>Certification asks: why do you believe the solver? "Qualify Z3" is not a
  tractable answer.</p>
  <p>So the solver stays <em>untrusted</em> and emits a certificate. Only a small,
  dependency-free checker is trusted — and that checker's soundness is
  machine-checked in Lean 4, with no <code>sorry</code> anywhere in its kernel.</p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">shipped</span><span>bit-vector obligations re-discharged with re-checkable certificates</span><span class="ledger__val">62 / 62</span></div>
  </div>
  <p class="slide__cite">This turns unchecked-solver evidence into the argument
  a verified compiler makes: don't trust the tool, check its output.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Every one of these gates was green for the wrong reason</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag bad">scry</span><span>a proof that never ran — the theorem was false when it did</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">synth</span><span>two validators, same direction, same blind spot</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">loom</span><span>a gate with passing tests and zero callers</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">meld</span><span>verified by a test on a path the shipped code didn't take</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">gale</span><span>a count over modules that cannot see instances</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <blockquote class="slide__quote">The failure produced the same observable as
  success.</blockquote>
  <p>The remedy is not more gates. It is that every check must be able to go red
  <em>for a reason you can state in advance</em>.</p>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>What componentizing actually costs</h2>
  <p class="evidence__label">driver object .text, core module &rarr; component</p>
  <pre class="evidence">gpio    502 &rarr; 1196 B      spi    454 &rarr; 1244 B
timer   204 &rarr;  828 B      wdg    638 &rarr; 1718 B
.data / .bss, every one of them       <span class="ok">0 &rarr; 0</span></pre>
  <p>Roughly <span class="hi">+700 B fixed per driver</span> for canonical-ABI glue
  — a constant, not a proportion. On a chip with 8 KB of SRAM that is a real
  number, and it is filed upstream rather than absorbed quietly.</p>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>Where the verification story actually stands</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag ok">shipping</span><span>Theorem proving · SMT contracts · bounded model checking · translation validation</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">partial</span><span>Refinement to Lean · mutation testing · abstract interpretation</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">not yet</span><span>An authority audit. We have not been audited.</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p>Proofs run on a verification schedule, not on every commit. Our own docs say
  this out loud: closer to <em>"well-specified and comprehensively tested with
  local formal verification"</em> than <em>"continuously formally verified."</em></p>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>Two things building this talk taught us</h2>
  <div class="split">
    <div class="split__col">
      <h3>the runner broke on success</h3>
      <p>Plugging in the third board made the first one unreachable — two probes,
      an interactive prompt, and a harness with no terminal. The all-three-at-once
      case was exactly the case nothing had run.</p>
    </div>
    <div class="split__col">
      <h3>a reproducible number that isn't</h3>
      <p>The RISC-V figure is recorded with a byte-reproducible command. The wasm
      input to that command is not in the repository — it lived in a scratch
      directory that no longer exists.</p>
    </div>
  </div>
  <blockquote class="slide__quote">A bench whose input is not committed is not
  reproducible, however precisely its output is recorded.</blockquote>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>Before the rest of the vision holds</h2>
  <ul>
    <li>Multi-tenant isolation on real MPU regions — modelled, not yet enforced on silicon.</li>
    <li>Drivers beyond the ones that port cleanly. Register maps differ; a verified
    state machine for one bus does not transfer to the next revision of that bus —
    it needs a fresh proof, not a port.</li>
    <li>The canonical-ABI overhead above, reduced rather than accepted.</li>
    <li>Certificates on every obligation, not the subset that has them today.</li>
    <li>Someone outside this project auditing the dossier.</li>
  </ul>
</section>

<section class="slide">
  <h1>Change the tires,<br>not the car</h1>
  <p class="slide__lead">The OS as components is the demonstration. The factory
  that lowers it — and can say why each stage is believed — is the part that
  generalizes.</p>
  <p class="slide__cite">pulseengine.eu &middot; every tool named here is open source</p>
</section>
