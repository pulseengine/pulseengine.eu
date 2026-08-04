+++
title = "Change the Tires, Not the Car"
description = "Wasm Research Day 2026. The Component Model as the integration step for an operating system, the same components lowered ahead of time onto three architectures, and an honest account of what is still missing."
date = 2026-08-06
template = "talk.html"

[extra]
event = "Wasm Research Day 2026"
slot = "25 + 5, remote"
+++

<section class="slide">
  <p class="slide__act">Wasm Research Day 2026 &middot; 25 + 5</p>
  <h1>Change the Tires,<br>Not the Car</h1>
  <p class="slide__lead">The Component Model as the integration step for an OS
  written in WebAssembly.</p>
  <p class="slide__cite">pulseengine.eu &middot; every number on these slides says where it came from</p>
</section>

<section class="slide">
  <p class="slide__act">Act I &middot; the inversion</p>
  <h2>What this room has already established</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag dim">2022</span><span>lowered ahead of time, no engine</span><span class="ledger__val">x86-64</span></div>
    <div class="ledger__row"><span class="ledger__tag dim">2023</span><span>pluggable HALs via the Component Model</span><span class="ledger__val">preliminary</span></div>
    <div class="ledger__row"><span class="ledger__tag dim">2025</span><span>a runtime's overhead on a small device</span><span class="ledger__val">runtime present</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">today</span><span>eliding bounds checks, soundly</span><span class="ledger__val">two hours ago</span></div>
  </div>
  <p>Four ingredients. <span class="hi">This talk needs all four at once</span> —
  where the runtime does not fit.</p>
</section>

<section class="slide">
  <p class="slide__act">Act I &middot; the inversion</p>
  <h2>Portability is usually asked of the wrong layer</h2>
  <div class="split">
    <div class="split__col">
      <h3>the usual arrangement</h3>
      <p>OS written for the chip. Application <em>hoped</em> to be portable.
      Every new board re-opens the OS.</p>
    </div>
    <div class="split__col">
      <h3>what we are trying</h3>
      <p>The OS <em>is</em> components. The Component Model is the integration
      step — OS to OS, OS to drivers, OS to tenants.</p>
    </div>
  </div>
  <p class="slide__cite">The bias, declared: I work in automotive, so to me
  everything is a car.</p>
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
  <div class="flow">
    <div class="flow__row">
      <span class="flow__stage">wac compose</span>
      <span class="flow__in">5 components</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">1 component · 20 741 B<br><span class="dim">exports 5 gust:os · imports mmio + taskdisp</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">meld fuse</span>
      <span class="flow__in">1 component<br><span class="dim">11 linear memories</span></span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">1 core module · 9 874 B<br><span class="dim">shared memory &mdash; 52% smaller</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">loom optimize</span>
      <span class="flow__in">core module</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">core module <span class="hi">+ wsc.facts</span><br><span class="dim">what it proved, forwarded</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">synth compile</span>
      <span class="flow__in">module + facts</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">gustos.o <span class="dim">· 4 812 B text · 0 SRAM</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">ld</span>
      <span class="flow__in">.o + <span class="hi">3</span> native functions</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">firmware<br><span class="dim">no engine, no interpreter, no JIT</span></span>
    </div>
  </div>
  <div class="cast" data-cast="/casts/dissolve.cast">
    <button type="button" class="cast__play">run it</button>
    <pre class="cast__screen" aria-label="terminal recording of the dissolve"></pre>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>The seam, as it is actually written</h2>
  <div class="split">
    <div class="split__col">
      <h3>wit/gust-hal.wit</h3>
      <pre class="evidence">interface mmio {
  read32:  func(addr: u32) -&gt; u32;
  write32: func(addr: u32, val: u32);
  <span class="dim">read8 / write8 likewise</span>
}
<span class="hi">world wdg-driver {
  import mmio; export wdg;
}</span></pre>
    </div>
    <div class="split__col">
      <h3>and the composition</h3>
      <pre class="evidence">wac compose fused-gustos.wac
meld fuse --memory shared
loom optimize --passes inline
synth compile --target cortex-m3 \
  --all-exports --relocatable</pre>
    </div>
  </div>
  <p>A driver's capability is checked against a typed contract at composition
  time. Before this it was an untyped <code>env</code> extern that only had to
  match <em>by name</em> at native link.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>A contract that cannot express the bug</h2>
  <p>A watchdog you can accidentally switch off is worthless. So the interface
  offers no way to switch it off:</p>
  <pre class="evidence">interface wdg {
  unlock · configure · lock
  start · refresh · is-running
  <span class="dim">— no stop. no disable.</span>
}</pre>
  <p class="evidence__label">and the FSM proves the absence, rather than relying on it</p>
  <pre class="evidence">fn p2_cannot_un_start() {
    let w = Iwdg { phase: Running, .. };
    if let Ok(n) = refresh(w) { assert_eq!(n.phase, <span class="ok">Running</span>); }
    <span class="dim">// no escape from Running:</span>
    assert!(unlock(w).is_err());
}</pre>
  <p><span class="hi">The contract itself cannot express the one transition the
  proof forbids.</span> That is the argument for putting the seam in a type
  system rather than in a comment.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>Three dies, one session</h2>
  <div class="stack">
    <pre class="evidence"><span class="dim">Cortex-M4 · NUCLEO-G474RE</span>
IWDG reset CONFIRMED   IWDGRSTF=<span class="ok">1</span></pre>
    <pre class="evidence"><span class="dim">Cortex-M3 · STM32F100 — the same .o</span>
IWDG reset CONFIRMED   IWDGRSTF=<span class="ok">1</span></pre>
    <pre class="evidence"><span class="dim">RISC-V · ESP32-C3 rev v0.4</span>
native 271   dissolved 499 milliticks/call   ratio <span class="ok">1.839&times;</span>
correctness <span class="ok">IDENTICAL</span> over [0,2047]   mismatch=<span class="ok">0</span></pre>
  </div>
  <p class="slide__cite">Captured 2026-08-04, all three probes attached at once.
  The watchdog legs are one happy path on two dies — they do not evidence
  cannot-un-start; the firmware never attempts one.</p>
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
  <p class="slide__act">Act III &middot; the tires</p>
  <h2>The whole of a tire</h2>
  <p class="evidence__label">web/shim-mmio.js — what a browser tab supplies</p>
  <pre class="evidence">const REGS = new Uint32Array(64);
<span class="dim">// the one clock register the OS reads</span>
const TIM2_CNT = 0x40000024;
export function read32(addr) {
  const a = addr &gt;&gt;&gt; 0;
  return a === TIM2_CNT ? clock : REGS[(a &gt;&gt;&gt; 2) &amp; 63];
}</pre>
  <p class="evidence__label">on silicon — same import, answered by the bus</p>
  <pre class="evidence">#[no_mangle] extern "C" fn read32(addr: u32) -&gt; u32 {
    unsafe { core::ptr::read_volatile(addr as *const u32) }
}</pre>
  <p><span class="hi">That substitution is the entire thesis.</span></p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>A whole STM32 USART driver, dissolved</span><span class="ledger__val">326 B · 0 SRAM · 3 relocs</span></div>
  </div>
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
      <h3>architect</h3><p><code>spar</code> — the WIT is generated from the model</p>
    </div>
    <div class="split__col">
      <h3>build</h3><p><code>meld</code> · <code>loom</code> · <code>synth</code>, with <code>sigil</code> attesting across all of it</p>
    </div>
    <div class="split__col">
      <h3>verify</h3><p><code>witness</code> MC/DC on the shipped wasm · Verus, Rocq, Lean, Kani</p>
    </div>
    <div class="split__col">
      <h3>trace</h3><p><code>rivet</code> — typed artifacts; broken links fail the build</p>
    </div>
    <div class="split__col">
      <h3>run</h3><p><code>kiln</code> · <code>gale</code> verified primitives</p>
    </div>
    <div class="split__col">
      <h3>agent</h3><p>the loop that files findings between repos</p>
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
    <div class="ledger__row"><span class="ledger__tag dim">native LLVM</span><span>full clamp</span><span class="ledger__val">0.50 cyc · 1.00&times;</span></div>
    <div class="ledger__row"><span class="ledger__tag dim">dissolved</span><span>as shipped today</span><span class="ledger__val">0.83 cyc · 1.65&times;</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">proof-carrying</span><span>clamp elided because a proof allows it</span><span class="ledger__val">0.23 cyc · <span class="ok">0.45&times;</span></span></div>
  </div>
  <p>Legal only because something upstream proved the bound.
  <span class="hi">A compiler with no verifier cannot reach it.</span></p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Qualify the checker, not the prover</h2>
  <p>Certification asks why you believe the solver. "Qualify Z3" is not a
  tractable answer.</p>
  <p>So the solver stays <em>untrusted</em> and emits a certificate. Only a small
  checker is trusted — and its soundness is machine-checked in Lean 4, with no
  <code>sorry</code> in its kernel.</p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">shipped</span><span>bit-vector obligations re-discharged with re-checkable certificates</span><span class="ledger__val">62 / 62</span></div>
  </div>
  <p class="slide__cite">Don't trust the tool — check its output.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Exactly how far this goes — and no further</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag ok">shipping</span><span>theorem proving · SMT · bounded MC · translation validation</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">partial</span><span>refinement to Lean · mutation · abstract interpretation</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">not yet</span><span>An authority audit. We have not been audited.</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p>Bounded model checking is bounded. Proofs run on a schedule, not every
  commit. Our own docs say <em>"comprehensively tested"</em>, not
  <em>"continuously formally verified."</em></p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Every one of these gates was green for the wrong reason</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag bad">scry</span><span>a proof that never ran</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">synth</span><span>two validators, one blind spot</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">loom</span><span>a gate with zero callers</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">meld</span><span>a test on a path the shipped code skipped</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">gale</span><span>a count that cannot see instances</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <blockquote class="slide__quote">The failure produced the same observable as
  success.</blockquote>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>What componentizing actually costs</h2>
  <p class="evidence__label">driver object .text, core module &rarr; component</p>
  <pre class="evidence">gpio   502 &rarr; 1196 B     spi  454 &rarr; 1244 B
timer  204 &rarr;  828 B     wdg  638 &rarr; 1726 B
.data / .bss, all of them   <span class="ok">0 &rarr; 0</span></pre>
  <p class="evidence__label">and the response, measured for this talk</p>
  <pre class="evidence">wdg, canonical glue on a growing allocator   1746 B
     backed by a bounded arena instead        <span class="ok">1428 B</span>   <span class="hi">&minus;318</span></pre>
  <p>So we patched the bindings generator rather than absorbing the cost:
  <code>cabi_realloc</code> delegates to an embedder arena that traps instead of
  growing. <span class="hi">29% of the overhead back</span> — and the drivers do
  not use it yet.</p>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>Two things building this talk taught us</h2>
  <div class="split">
    <div class="split__col">
      <h3>the runner broke on success</h3>
      <p>Plugging in the third board made the first unreachable. The
      all-three-at-once case was the one nothing had run.</p>
    </div>
    <div class="split__col">
      <h3>a reproducible number that isn't</h3>
      <p>A byte-reproducible command whose wasm input is not in the repo — it
      lived in a scratch directory that no longer exists.</p>
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
