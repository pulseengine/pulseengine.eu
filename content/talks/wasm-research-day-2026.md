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
  <p class="slide__cite">I work in automotive, so to me everything is a car &mdash;
  declaring the bias up front.<br>
  pulseengine.eu &middot; every number on these slides says where it came from</p>
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
      <pre class="evidence">mmio · gpio · spi
timer · uart · dma
irq  <span class="dim">— poll(line) -&gt; bool, deliberately</span></pre>
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
      <span class="flow__out">core module <span class="hi">+ wsc.facts</span><br><span class="dim">channel byte-verified; producer not yet wired</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">synth compile</span>
      <span class="flow__in">module + facts</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">gustos.o <span class="dim">· 4 812 B text · .bss 0</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">ld</span>
      <span class="flow__in">.o + <span class="hi">3</span> native functions</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">firmware<br><span class="dim">no engine, no interpreter, no JIT</span></span>
    </div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>The same chain, actually run</h2>
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
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car</p>
  <h2>&hellip; and the FSM proves the absence</h2>
  <pre class="evidence">fn p2_cannot_un_start() {
    let w = Iwdg { phase: Running, .. };
    if let Ok(n) = refresh(w) { assert_eq!(n.phase, <span class="ok">Running</span>); }
    <span class="dim">// no escape from Running:</span>
    assert!(unlock(w).is_err());
}</pre>
  <p><span class="hi">The contract cannot express the one transition the proof
  forbids.</span> That is the argument for putting a seam in a type system rather
  than in a comment.</p>
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
native 271   dissolved 499 milliticks/call   ratio <span class="warn">1.839&times; slower</span>
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
</section>

<section class="slide">
  <p class="slide__act">Act III &middot; the tires</p>
  <h2>&hellip; and on silicon</h2>
  <p class="evidence__label">same import, answered by the bus</p>
  <pre class="evidence">#[no_mangle] extern "C" fn read32(addr: u32) -&gt; u32 {
    unsafe { core::ptr::read_volatile(addr as *const u32) }
}</pre>
  <p>Nothing else about the component changes.
  <span class="hi">That substitution is the entire thesis.</span></p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>a whole STM32 USART driver, dissolved</span><span class="ledger__val">326 B · 0 SRAM · 3 relocs</span></div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Why any of this machinery exists</h2>
  <p class="slide__lead">Most of this code was written by AI, under review. That is
  the premise, not a footnote.</p>
  <p>An assistant will write a plausible driver, a plausible proof, and a plausible
  green test, faster than anyone can read them. So the question stopped being
  <em>can it write the code</em> and became <span class="hi">what would have to be
  true for me to believe it</span>.</p>
  <p>Qualify the pipeline once and the <em>argument</em> amortizes across every
  product built on it. That is why the factory matters more than the car.</p>
  <p class="slide__cite">It is also why the failures later in this act are the
  interesting part &mdash; they are what a plausible green check costs when nobody
  can read everything.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>What you still have to trust</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag warn">before</span><span>rustc + the LLVM wasm backend &mdash; every component starts here</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">compose</span><span>wac · the WIT generator · wit-bindgen's canonical glue</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">models</span><span>our encodings of Wasm and of four ISAs</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">checkers</span><span>the LRAT checker's Lean proof, its kernel, the model&harr;code gap</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">below</span><span>ld · the linker script · the native functions · hand-written unsafe</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p><span class="hi">"Three native functions" is the seam, not the trusted base.</span>
  The base is this list, and none of the gates in this talk cover the first row.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Where the evidence enters</h2>
  <div class="archtabs">
    <button type="button" class="archtab is-on" data-arch="meld">meld</button>
    <button type="button" class="archtab" data-arch="loom">loom</button>
    <button type="button" class="archtab" data-arch="synth">synth</button>
  </div>
  <div class="archset">
    <div class="archr is-on" data-arch="meld">
      <div class="archr__row"><span class="archr__st">parse</span><div class="archr__bs">
        <span class="ab">Component decoder<small>core + CM, nested</small></span>
        <span class="ab">Core-instance topology<small>shared memories · tables</small></span>
        <span class="ab">Canonical options<small>encoding · realloc</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">resolve</span><div class="archr__bs">
        <span class="ab ev">Import resolution<small>proved sound + complete</small></span>
        <span class="ab ev">Topological order<small>cycle detection terminates</small></span>
        <span class="ab ev">Adapter-site ID<small>sites found at every crossing</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">merge</span><div class="archr__bs">
        <span class="ab ev">Index-space remap<small>injective · complete · 6 spaces</small></span>
        <span class="ab ev">Layout disjointness<small>sequential, non-overlapping</small></span>
        <span class="ab">Per-boundary seams<small>address · call-lowering · PIC</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">adapt</span><div class="archr__bs">
        <span class="ab ev">Fused trampolines<small>lift/lower roundtrip</small></span>
        <span class="ab">Transcode · copy · realloc<small>UTF-8/16 · memory.copy</small></span>
        <span class="ab hz">Validates &ne; correct<small>tool lenient · engine strict · run exact</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">One core module<small>no runtime linking, no host</small></span>
        <span class="ab">DWARF + provenance<small>remapped · fusion attestation</small></span>
      </div></div>
    </div>
    <div class="archr" data-arch="loom">
      <div class="archr__row"><span class="archr__st">in</span><div class="archr__bs">
        <span class="ab">Core module / component<small>wasmparser · no execution</small></span>
        <span class="ab ev">wsc.* namespace strip<small>input facts never re-emitted</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">ir</span><div class="archr__bs">
        <span class="ab">Instructions &rarr; ISLE terms<small>typed term rewriting</small></span>
        <span class="ab">E-graph<small>equality saturation</small></span>
        <span class="ab">Value-attached facts<small>keyed by value, not index</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">passes</span><div class="archr__bs">
        <span class="ab">inline · const-fold<small>algebraic mid-end</small></span>
        <span class="ab">dce · dead-stores<small>code removal — the risky class</small></span>
        <span class="ab">forward-carrier · SROA<small>seam dissolution</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">per&nbsp;compilation</span><div class="archr__bs">
        <span class="ab ev">Translation validation<small>value equivalence · QF_BV</small></span>
        <span class="ab ev">Trap-equivalence gate<small>certificate re-checked</small></span>
        <span class="ab hz">Total-operation model<small>the verifier does not see traps</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">gate</span><div class="archr__bs">
        <span class="ab ev">Behavioral differential<small>executed vs baseline</small></span>
        <span class="ab">Revert-on-doubt<small>skip the function, keep the original</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">Optimized Wasm<small>byte-identical when nothing proven</small></span>
        <span class="ab ev">wsc.facts<small>value-range invariants, schema v1</small></span>
      </div></div>
    </div>
    <div class="archr" data-arch="synth">
      <div class="archr__row"><span class="archr__st">upstream</span><div class="archr__bs">
        <span class="ab ev">loom<small>Z3 validator &rarr; wsc.facts</small></span>
        <span class="ab ev">scry<small>intervals · stack-depth</small></span>
        <span class="ab ev">meld<small>component &rarr; core wasm</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">front</span><div class="archr__bs">
        <span class="ab ev">wsc.facts ingest<small>bad section &rArr; no facts, never error</small></span>
        <span class="ab">WIT / ABI<small>lift · lower</small></span>
        <span class="ab">cabi arena bind<small>dangling realloc &rarr; defined fn</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">middle</span><div class="archr__bs">
        <span class="ab ev">Verified selector DSL<small>50 rules · 50 Rocq Qed</small></span>
        <span class="ab ev">Fact specialization<small>per-site SMT + LRAT</small></span>
        <span class="ab">Register allocation<small>Belady spill</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">back</span><div class="archr__bs">
        <span class="ab">Thumb-2 · A32 · A64 · RV32IMAC<small>M3/M4/M7 · R5 · a53 · ESP32-C3</small></span>
        <span class="ab hz">Trap re-introduction<small>hardware is more total than Wasm</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">per&nbsp;compilation</span><div class="archr__bs">
        <span class="ab ev">Translation validation<small>QF_BV · pure Rust</small></span>
        <span class="ab ev">Trap-preservation VC<small>div · OOB · trunc</small></span>
        <span class="ab ev">Allocation validators<small>whole-function · CFG</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">Freestanding ELF<small>vectors · linker · MPU</small></span>
        <span class="ab ev">WCET sidecar<small>leaf functions only · declines on call</small></span>
        <span class="ab">DWARF<small>relocatable</small></span>
      </div></div>
    </div>
  </div>
  <p class="slide__cite">Tinted = produces or checks evidence · amber = this stage's hazard</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>No stage trusts the one above it</h2>
  <p>When <code>loom</code> proves a value range it does not discard it. It writes
  it into a custom section — and the whole channel is nine bytes:</p>
  <pre class="evidence"><span class="dim">custom section "wsc.facts"</span>
01              <span class="dim">schema v1</span>
01              <span class="dim">one fact</span>
  01            <span class="dim">kind = value-range</span>
  03            <span class="dim">func_index  3</span>
  07            <span class="dim">value_id    7  &larr; a VALUE, not a position</span>
  03 00 ff 0f   <span class="dim">body: 0 &le; v &le; 2047   (sleb128)</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Why a <em>value</em>, not a position</h2>
  <p>An optimizer <em>renumbers everything</em>. Key a fact to an instruction index,
  and the next pass deletes three instructions above it.</p>
  <p>The fact is still true of something &mdash; and is now asserted about something
  else. A downstream consumer then reasons about the wrong operand, with a valid
  module and a machine-checked implication.</p>
  <p>So a fact whose value did not survive the pipeline is
  <span class="hi">dropped, never re-pointed</span>. An absent fact costs
  performance; a mis-keyed one costs correctness.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>What the channel is worth</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">measured</span><span>a bounds-guard sequence, with the fact forwarded</span><span class="ledger__val">232 &rarr; 104 B</span></div>
  </div>
  <p class="slide__cite">Honest scope: emitter, schema and wire format are done and
  byte-verified against the consumer. The <em>source</em> that would populate this
  at volume is not wired &mdash; so that is what the channel does when it carries a
  fact, not evidence that we produce many yet.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>Faster <em>because</em> it is proven</h2>
  <pre class="evidence">gust_mix(ch) = clamp(1500 + (ch - 1024), 1000, 2000)</pre>
  <p>The OS primitives above carry a proven bound &mdash;
  <code>ch &isin; [524, 1524]</code> &mdash; so <code>ch + 476</code> is
  <em>provably</em> inside [1000, 2000] and
  <span class="hi">both clamp branches are dead code</span>:</p>
  <pre class="evidence">add r0, #476
bx  lr          <span class="dim">— the whole function</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory</p>
  <h2>What that is worth, measured</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag dim">native LLVM</span><span>full clamp — what LLVM ships</span><span class="ledger__val">0.50 ticks/call</span></div>
    <div class="ledger__row"><span class="ledger__tag dim">dissolved today</span><span>clamp still emitted</span><span class="ledger__val">0.70 &mdash; <span class="warn">1.4&times; slower</span></span></div>
    <div class="ledger__row"><span class="ledger__tag hi">with the proof</span><span>clamp elided</span><span class="ledger__val">0.23 &mdash; <span class="ok">2.2&times; faster</span></span></div>
  </div>
  <p class="slide__cite">The output clamp stays; this is the intermediate range
  check. The bound comes from a verified primitive, not off the wire.</p>
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
.data / .bss, all of them   <span class="ok">0 &rarr; 0</span>
<span class="dim">flash is cheap here; SRAM is the binding constraint</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>So we patched the generator</h2>
  <p class="evidence__label">measured for this talk</p>
  <pre class="evidence"><span class="dim">wdg, one wit-bindgen build, feature off vs on
(1746 not 1726 — a newer bindgen; the bump alone costs +20 B)</span>
canonical glue on a growing allocator   1746 B
backed by a bounded arena instead       <span class="ok">1428 B</span>   <span class="hi">&minus;318</span></pre>
  <p><code>cabi_realloc</code> now delegates to an embedder arena that traps rather
  than growing. <span class="hi">29% of the overhead back</span> &mdash; and the
  drivers do not use it yet.</p>
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
  <p class="slide__act">Act V &middot; what is missing</p>
  <h2>When <em>not</em> to dissolve</h2>
  <div class="split">
    <div class="split__col">
      <h3>dissolve</h3>
      <p>One closed tenant graph · no MMU · a narrow, hardware-shaped interface ·
      footprint and determinism dominate · re-qualification is per product anyway.</p>
    </div>
    <div class="split__col">
      <h3>link a shared system-interface binary</h3>
      <p>Several runtimes on one OS and ISA · a wide, dynamic, POSIX-shaped
      interface · third parties ship binaries · the fleet needs a driver updated
      without re-qualifying the image.</p>
    </div>
  </div>
  <p>Both positions want the interface specified as WIT and typed. We differ only
  in <span class="hi">when it binds</span> &mdash; and my side of that line is the
  narrow one.</p>
</section>

<section class="slide">
  <h1>Change the tires,<br>not the car</h1>
  <p class="slide__lead">The OS as components is the demonstration. The factory
  that lowers it — and can say why each stage is believed — is the part that
  generalizes.</p>
  <p class="slide__cite">pulseengine.eu &middot; every tool named here is open source</p>
</section>
