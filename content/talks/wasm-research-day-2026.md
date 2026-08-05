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
  <h2>How embedded actually builds software</h2>
  <div class="split">
    <div class="split__col">
      <h3>what you do today</h3>
      <p>Take the vendor's HAL and board-support package for that part. Take an
      RTOS with a port layer per architecture and a board file per board. Take
      register headers generated from the chip's own description file. Select
      variants with <code>#ifdef</code>. Statically link one image.</p>
    </div>
    <div class="split__col">
      <h3>and it is the right answer</h3>
      <p>No MMU. Kilobytes of RAM. Hard deadlines. Cents per unit. Every
      abstraction costs bytes and cycles that are not there, and the vendor knows
      the silicon better than you do. This ships in billions of units, and it
      works.</p>
    </div>
  </div>
  <p>The consequence is the part worth arguing about: <span class="hi">the OS is
  the layer that gets rewritten per target</span>, and the application's
  portability is a convention, not a contract.</p>
</section>

<section class="slide">
  <p class="slide__act">Act I &middot; the inversion</p>
  <h2>So invert it</h2>
  <p class="slide__lead">Write the OS itself as WebAssembly components, and make the
  Component Model the integration step.</p>
  <p>Between OS components. Between the OS and its drivers. Between the OS and the
  tenants above it. Not a runtime on the device &mdash; a <em>build step</em> that
  joins typed pieces and then gets compiled away.</p>
  <p>The OS and everything above it is the car. The handful of native functions that
  actually touch the hardware are the tires. New chip, new board &mdash;
  <span class="hi">change the tires, not the car.</span></p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-one">gust:os · gust:hal</span></p>
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
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-many">the whole chain</span></p>
  <h2>Integration step, not a build step</h2>
  <p class="slide__lead">Five components in, one native object out &mdash; and every
  arrow happens on a build machine, not on the device.</p>
  <div class="flow">
    <div class="flow__row">
      <span class="flow__stage">compose<small>wac</small></span>
      <span class="flow__in">5 components</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">1 component · 20 741 B<br><span class="dim">exports 5 gust:os · imports mmio + taskdisp</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">fuse<small>meld</small></span>
      <span class="flow__in">1 component<br><span class="dim">5 linear memories</span></span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">1 core module · 9 874 B<br><span class="dim">shared memory &mdash; 52% smaller</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">optimize<small>loom</small></span>
      <span class="flow__in">core module</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">core module <span class="hi">+ wsc.facts</span><br><span class="dim">channel byte-verified; producer not yet wired</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">lower to ARM<small>synth</small></span>
      <span class="flow__in">module + facts</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">gustos.o <span class="dim">· 4 812 B text · .bss 0</span></span>
    </div>
    <div class="flow__row">
      <span class="flow__stage">link<small>ld</small></span>
      <span class="flow__in">.o + <span class="hi">3</span> native functions</span>
      <span class="flow__arrow">&rarr;</span>
      <span class="flow__out">firmware<br><span class="dim">no engine, no interpreter, no JIT</span></span>
    </div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-many">the whole chain</span></p>
  <h2>The same chain, actually run</h2>
  <p class="slide__lead">Five components in, one relocatable object out &mdash;
  and at the end, the two questions that matter: what does it still need from the
  world, and what does it cost?</p>
  <div class="cast" data-cast="/casts/dissolve.cast">
    <button type="button" class="cast__play">run it</button>
    <pre class="cast__screen" aria-label="terminal recording of the dissolve"></pre>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-one">gust on the F100</span></p>
  <h2>The part that sets the rules is a failsafe</h2>
  <p class="slide__lead">Not the smallest board we could find &mdash; the emergency
  motor controller. It sits beside the main flight computer and forwards per-motor
  commands. If that computer stops, this is what is still driving the motors.</p>
  <pre class="evidence"><span class="dim">its linker geometry, generated from the AADL model</span>
FLASH : 128K
RAM   : <span class="hi">8K</span></pre>
  <p>Its one safety property is <span class="hi">byte-exact pass-through</span>:
  when a rotor fails and the controller asymmetrically zeros motors, re-mixing
  would reintroduce the parasitic moment that caused a real failure. So the
  failsafe must <em>not</em> be clever.</p>
  <p class="slide__cite">And that is not a sentence on a slide. It is a typed
  requirement, its WIT is generated from the architecture model, and an oracle
  gates it &mdash; 46 rows &times; 4 motors, byte-exact, with a negative control
  that must fail. <span class="warn">Status: draft.</span></p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-one">gust on the F100</span></p>
  <h2>What it costs on that part</h2>
  <p class="evidence__label">a whole flashed image — the watchdog silicon test</p>
  <pre class="evidence">   text    data    bss
   6028       0       8
flash  <span class="ok">6 028 B of 131 072</span>   4.6%
SRAM   <span class="ok">    8 B of   8 192</span>   0.1%   &mdash; 8 184 free</pre>
  <p>No MMU. No engine. <span class="hi">Eight bytes of RAM.</span> That is why the
  drivers are 0 SRAM, the interfaces are scalar, and the allocator traps instead of
  growing &mdash; none of those are taste.</p>
  <p class="slide__cite">Scope: one dissolved driver plus the minimum to boot and
  report. A floor, not a system footprint &mdash; no scheduler, no tenants.</p>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-many">the whole chain</span></p>
  <h2>The seam, as it is actually written</h2>
  <div class="split">
    <div class="split__col">
      <h3>wit/gust-hal.wit</h3>
      <pre class="evidence" data-lang="wit">interface mmio {
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
      <pre class="evidence" data-lang="sh">wac compose fused-gustos.wac
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
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-one">one driver</span></p>
  <h2>A contract that cannot express the bug</h2>
  <p>A watchdog you can accidentally switch off is worthless. So the interface
  offers no way to switch it off:</p>
  <pre class="evidence" data-lang="wit">interface wdg {
  unlock:     func(base: u32, state: u32) -&gt; u32;
  configure:  func(base: u32, state: u32, psc: u32, rld: u32) -&gt; u32;
  lock:       func(state: u32) -&gt; u32;
  start:      func(base: u32, state: u32) -&gt; u32;
  refresh:    func(base: u32, state: u32) -&gt; u32;
  is-running: func(state: u32) -&gt; u32;
}   <span class="dim">— six functions. no stop. no disable.</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-one">one driver</span></p>
  <h2>&hellip; and the FSM proves the absence</h2>
  <pre class="evidence" data-lang="rust">fn p2_cannot_un_start() {
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
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-one">gust:hal · dma</span></p>
  <h2>The seam is not only scalars</h2>
  <p>Everything so far has been <code>u32</code> in, <code>u32</code> out. DMA is
  where that stops &mdash; and the Component Model already has the vocabulary:</p>
  <pre class="evidence" data-lang="wit">resource dma-buffer { len: func() -&gt; u32; }

read: func(channel: u32, buf: dma-buffer)
        -&gt; future&lt;dma-buffer&gt;</pre>
  <p>It consumes <code>own&lt;dma-buffer&gt;</code>. While the engine has it, the
  buffer is <span class="hi">statically inaccessible to wasm</span> until the
  future resolves with the re-owned handle. Circular DMA is a stream of per-chunk
  ownership &mdash; each chunk owned by exactly one side at a time.</p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>the ownership state machine, dissolved</span><span class="ledger__val">220 B · 0 SRAM · 6 Kani proofs</span></div>
  </div>
</section>

<section class="slide">
  <p class="slide__act">Act II &middot; the car<span class="slide__scope is-many">gust, three parts</span></p>
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
  <p class="slide__act">Act III &middot; the tires<span class="slide__scope is-many">gust, three hosts</span></p>
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
  <p class="slide__act">Act III &middot; the tires<span class="slide__scope is-one">one driver</span></p>
  <h2>The whole of a tire</h2>
  <p>A component that imports <code>gust:hal/mmio</code> does not care who answers
  it. In a browser tab, this is the answer &mdash; the whole of it:</p>
  <p class="evidence__label">web/shim-mmio.js</p>
  <pre class="evidence" data-lang="js">const REGS = new Uint32Array(64);
<span class="dim">// the one clock register the OS reads</span>
const TIM2_CNT = 0x40000024;
export function read32(addr) {
  const a = addr &gt;&gt;&gt; 0;
  return a === TIM2_CNT ? clock : REGS[(a &gt;&gt;&gt; 2) &amp; 63];
}</pre>
</section>

<section class="slide">
  <p class="slide__act">Act III &middot; the tires<span class="slide__scope is-one">one driver</span></p>
  <h2>&hellip; and on silicon</h2>
  <p class="evidence__label">same import, answered by the bus</p>
  <pre class="evidence" data-lang="rust">#[no_mangle] extern "C" fn read32(addr: u32) -&gt; u32 {
    unsafe { core::ptr::read_volatile(addr as *const u32) }
}</pre>
  <p>Nothing else about the component changes.
  <span class="hi">That substitution is the entire thesis.</span></p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">seam</span><span>a whole STM32 USART driver, dissolved</span><span class="ledger__val">254 B · 0 SRAM · 3 relocs</span></div>
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
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-one">meld</span></p>
  <h2>Is this the Component Model, or our dialect?</h2>
  <p>The fuser does essentially what <span class="hi">RFC 46</span> proposes &mdash;
  for the sync subset. Same architecture: parse the components, flatten the
  composition DAG, merge the index spaces, generate FACT-style adapter
  trampolines, re-wrap as a component for host compatibility.</p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag ok">runtime</span><span>canonical-ABI fixtures &mdash; strings, lists, records, variants, options, results, resources, flags, enums, both directions</span><span class="ledger__val">43 / 45</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">declined</span><span>async / fibers &mdash; no stack switching on these parts, and compiling the runtime in is a TCB problem</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">rejected</span><span>multiply-instantiated modules &mdash; we refuse them rather than ship an unproved transform</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p class="slide__cite">The two failures are three-component resource chains where
  an intermediate re-exports a resource it does not define.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-many">everything below the seam</span></p>
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
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-many">four tools</span></p>
  <h2>Four tools, one spine</h2>
  <div class="archtabs">
    <button type="button" class="archtab is-on" data-arch="meld">meld</button>
    <button type="button" class="archtab" data-arch="loom">loom</button>
    <button type="button" class="archtab" data-arch="synth">synth</button>
    <button type="button" class="archtab" data-arch="scry">scry</button>
  </div>
  <p class="archwhat is-on" data-arch="meld"><b>meld</b> welds many components, joined at their interfaces, into a single module &mdash; so the boundaries stop existing at run time.</p>
  <p class="archwhat" data-arch="loom"><b>loom</b> rewrites the code to be smaller and faster, and reverts any rewrite it cannot prove keeps the same behaviour.</p>
  <p class="archwhat" data-arch="synth"><b>synth</b> turns the wasm into real machine instructions for a real chip, and re-proves the translation on every compilation.</p>
  <p class="archwhat" data-arch="scry"><b>scry</b> is <span class="hi">sound abstract interpretation</span> &mdash; it reads the code without running it and over-approximates, so what it proves holds on every run. It records every place it had to give up as data.</p>
  <div class="archset">
    <div class="archr is-on" data-arch="meld">
      <div class="archr__row"><span class="archr__st">in</span><div class="archr__bs">
        <span class="ab">Component decoder<small>core + CM, nested</small></span>
        <span class="ab">Core-instance topology<small>shared memories · tables</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">model</span><div class="archr__bs">
        <span class="ab ev">Import resolution<small>proved sound + complete</small></span>
        <span class="ab ev">Topological order<small>cycle detection terminates</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">work</span><div class="archr__bs">
        <span class="ab ev">Index-space remap<small>injective · 6 spaces</small></span>
        <span class="ab ev">Layout disjointness<small>sequential, non-overlapping</small></span>
        <span class="ab">Per-boundary seams<small>address · call-lowering</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">check</span><div class="archr__bs">
        <span class="ab ev">Fused trampolines<small>lift/lower roundtrip</small></span>
        <span class="ab ev">Differential oracles<small>compose&rarr;fuse&rarr;run vs compose&rarr;run</small></span>
        <span class="ab hz">Validates &ne; correct<small>tool lenient · engine strict</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">One core module<small>no runtime linking</small></span>
        <span class="ab">DWARF + provenance<small>remapped · attestation</small></span>
      </div></div>
    </div>
    <div class="archr" data-arch="loom">
      <div class="archr__row"><span class="archr__st">in</span><div class="archr__bs">
        <span class="ab">Core module<small>wasmparser · no execution</small></span>
        <span class="ab ev">wsc.* strip<small>input facts never re-emitted</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">model</span><div class="archr__bs">
        <span class="ab">ISLE terms<small>typed term rewriting</small></span>
        <span class="ab">E-graph<small>equality saturation</small></span>
        <span class="ab">Value-attached facts<small>keyed by value, not index</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">work</span><div class="archr__bs">
        <span class="ab">inline · const-fold<small>algebraic mid-end</small></span>
        <span class="ab">dce · dead-stores<small>the risky class</small></span>
        <span class="ab">forward-carrier · SROA<small>seam dissolution</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">check</span><div class="archr__bs">
        <span class="ab ev">Translation validation<small>value equivalence · QF_BV</small></span>
        <span class="ab ev">Behavioral differential<small>executed vs baseline</small></span>
        <span class="ab hz">Total-operation model<small>the verifier does not see traps</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">Optimized Wasm<small>byte-identical if nothing proven</small></span>
        <span class="ab ev">wsc.facts<small>value-range invariants</small></span>
      </div></div>
    </div>
    <div class="archr" data-arch="synth">
      <div class="archr__row"><span class="archr__st">in</span><div class="archr__bs">
        <span class="ab ev">wsc.facts ingest<small>bad section &rArr; no facts</small></span>
        <span class="ab">WIT / ABI<small>lift · lower</small></span>
        <span class="ab">cabi arena bind<small>dangling realloc &rarr; defined fn</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">model</span><div class="archr__bs">
        <span class="ab">CFG + SSA<small>liveness · reaching defs</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">work</span><div class="archr__bs">
        <span class="ab ev">Verified selector DSL<small>50 rules · 50 Rocq Qed</small></span>
        <span class="ab ev">Fact specialization<small>per-site SMT + LRAT</small></span>
        <span class="ab">Register allocation<small>Belady spill</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">check</span><div class="archr__bs">
        <span class="ab ev">Translation validation<small>QF_BV · pure Rust</small></span>
        <span class="ab ev">Trap-preservation VC<small>div · OOB · trunc</small></span>
        <span class="ab hz">Trap re-introduction<small>hardware is more total</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">Freestanding ELF<small>vectors · linker · MPU</small></span>
        <span class="ab ev">WCET sidecar<small>leaf functions only</small></span>
        <span class="ab">DWARF<small>relocatable</small></span>
      </div></div>
    </div>
    <div class="archr" data-arch="scry">
      <div class="archr__row"><span class="archr__st">in</span><div class="archr__bs">
        <span class="ab">Wasm core module<small>no engine, no execution</small></span>
        <span class="ab ev">Verified premises<small>bounded memory · closed world</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">model</span><div class="archr__bs">
        <span class="ab ev">Interval · known-bits<small>&gamma; over &#8484;</small></span>
        <span class="ab ev">Octagon · pentagon<small>&plusmn;x&plusmn;y &le; c · x &lt; y</small></span>
        <span class="ab ev">Region memory<small>in-bounds</small></span>
        <span class="ab hz">Wrapping arithmetic<small>&#8484; &ne; i32</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">work</span><div class="archr__bs">
        <span class="ab ev">Structured-CFG interp<small>domains ride in lockstep</small></span>
        <span class="ab ev">Widening + narrowing<small>threshold · guard refine</small></span>
        <span class="ab">Write-set havoc<small>unmodelled &rArr; gap record</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">check</span><div class="archr__bs">
        <span class="ab ev">Rocq suite<small>19 files · 0 admits</small></span>
        <span class="ab">&gamma;-sweeps<small>concrete-oracle falsification</small></span>
      </div></div>
      <div class="archr__row"><span class="archr__st">out</span><div class="archr__bs">
        <span class="ab">Trap verdicts<small>PROVEN-SAFE | POTENTIAL-TRAP</small></span>
        <span class="ab ev">Shadow-stack bound<small>consumed by synth</small></span>
        <span class="ab ev">Gap report<small>every &top;, as data</small></span>
      </div></div>
    </div>
  </div>
  <p class="slide__cite">Same five rows every time &mdash; and every tool's hazard is
  the same defect: its model is more total than Wasm.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-many">loom &rarr; synth</span></p>
  <h2>No stage trusts the one above it</h2>
  <p>It is not running a separate pass to hunt for facts. <span class="hi">To
  delete a bounds check it must already have established the index is in
  range</span> &mdash; every optimizer does that. What is unusual is what happens
  next: normally the code is emitted and the reasoning that justified it
  evaporates.</p>
  <p>Here it is written into a custom section instead &mdash; and the whole
  channel is nine bytes:</p>
  <pre class="evidence"><span class="dim">custom section "wsc.facts"</span>
01              <span class="dim">schema v1</span>
01              <span class="dim">one fact</span>
  01            <span class="dim">kind = value-range</span>
  03            <span class="dim">func_index  3</span>
  07            <span class="dim">value_id    7  &larr; a VALUE, not a position</span>
  03 00 ff 0f   <span class="dim">body: 0 &le; v &le; 2047   (sleb128)</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-many">loom &rarr; synth</span></p>
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
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-many">loom &rarr; synth</span></p>
  <h2>What the channel is worth</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">measured</span><span>one guarded memory access, lowered with and without the fact</span><span class="ledger__val">232 &rarr; 104 B</span></div>
  </div>
  <p class="slide__cite">Honest scope: emitter, schema and wire format are done and
  byte-verified against the consumer. The <em>source</em> that would populate this
  at volume is not wired &mdash; so that is what the channel does when it carries a
  fact, not evidence that we produce many yet.</p>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-one">synth</span></p>
  <h2>Faster <em>because</em> it is proven</h2>
  <pre class="evidence">gust_mix(ch) = clamp(1500 + (ch - 1024), 1000, 2000)</pre>
  <p>The OS primitives above carry a proven bound &mdash;
  <code>ch &isin; [524, 1524]</code> &mdash; so <code>ch + 476</code> is
  <em>provably</em> inside [1000, 2000] and
  <span class="hi">both clamp branches are dead code</span>:</p>
  <pre class="evidence">push {r7, lr}
add.w r0, r0, #476
uxth  r0, r0
pop  {r7, pc}   <span class="dim">— the whole function, 12 B</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-one">synth</span></p>
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
  <p class="slide__act">Act IV &middot; the factory<span class="slide__scope is-many">synth vs LLVM</span></p>
  <h2>&hellip; and no, LLVM is not the problem</h2>
  <p class="evidence__label">tell it the same thing and it folds it too</p>
  <pre class="evidence" data-lang="rust">assert_<span class="bad">unchecked</span>(524 &lt;= ch &amp;&amp; ch &lt;= 1524);
  &rarr; add.w r0, r0, #476     <span class="dim">stock LLVM, 30 B &rarr; 12 B</span></pre>
  <p>So the codegen is not the result. <span class="hi">Both emit the same
  instruction &mdash; only one of them checked.</span></p>
  <p class="slide__cite">You can tell a compiler anything and it will believe you.
  Get that range wrong and it is undefined behaviour, silently, with no
  diagnostic. The question was never <em>can the compiler fold it</em> &mdash; it
  is <em>how would you know the premise is true</em>.</p>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing<span class="slide__scope is-one">gust drivers</span></p>
  <h2>What componentizing actually costs</h2>
  <p class="evidence__label">driver object .text, core module &rarr; component</p>
  <pre class="evidence">gpio   502 &rarr; 1196 B     spi  454 &rarr; 1450 B
timer  204 &rarr;  828 B     wdg  638 &rarr; 1718 B
.data / .bss, all of them   <span class="ok">0 &rarr; 0</span>
<span class="dim">flash is cheap here; SRAM is the binding constraint</span></pre>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing<span class="slide__scope is-one">wit-bindgen</span></p>
  <h2>So we patched the generator</h2>
  <p class="evidence__label">measured for this talk</p>
  <pre class="evidence"><span class="dim">wdg, rebuilt both ways — feature off is the control
(not the 1718 B shipped object; this is a newer bindgen)</span>
canonical glue on a growing allocator   1746 B
backed by a bounded arena instead       <span class="ok">1428 B</span>   <span class="hi">&minus;318</span></pre>
  <p><code>cabi_realloc</code> now delegates to an embedder arena that traps rather
  than growing. <span class="hi">29% of the overhead back</span> &mdash; and the
  drivers do not use it yet.</p>
</section>

<section class="slide">
  <p class="slide__act">Act V &middot; what is missing<span class="slide__scope is-many">all of it</span></p>
  <h2>Before the rest of the vision holds</h2>
  <ul>
    <li><span class="hi">A proven stack bound.</span> An OS node reserves 2 048 of
    those 8 192 bytes for its shadow stack &mdash; and the compiler's own contract
    says that budget is <em>asserted</em>, not proven. scry computes the depth;
    wiring it to the reservation is the named next step, and until it lands the
    number is our word.</li>
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
  <p class="slide__act">Act V &middot; what is missing<span class="slide__scope is-many">the takeaway</span></p>
  <h2>Three things to take with you</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">one</span><span>The Component Model can be a <em>build step</em>. It does not have to be present at run time &mdash; 43 of 45 canonical-ABI fixtures survive complete erasure.</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">two</span><span>A proof can cross a tool boundary in <em>nine bytes</em> &mdash; keyed to a value, dropped rather than re-pointed when the value dies.</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag hi">three</span><span>On a part with 8 KB of RAM the seam costs nothing at run time, because by then it is <em>not there</em>.</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p class="slide__cite">The schema is open, and the erasure ledger is a claim, not
  a result &mdash; if it is wrong I would rather hear it than not.</p>
</section>

<section class="slide">
  <h1>Change the tires,<br>not the car</h1>
  <p class="slide__lead">The OS as components is the demonstration. The factory
  that lowers it — and can say why each stage is believed — is the part that
  generalizes.</p>
  <p class="slide__cite">pulseengine.eu &middot; every tool named here is open source</p>
</section>

<section class="slide is-backup">
  <p class="slide__act">backup <span class="slide__scope is-backup-tag">not in the talk</span></p>
  <h2>Qualify the checker, not the prover</h2>
  <p>Certification asks why you believe the solver. "Qualify Z3" is not a
  tractable answer.</p>
  <p>So the solver stays <em>untrusted</em> and emits a certificate. Only a small
  checker is trusted — and its soundness is machine-checked in Lean 4, with no
  <code>sorry</code> in its kernel.</p>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag hi">shipped</span><span>bit-vector obligations re-discharged with re-checkable certificates</span><span class="ledger__val">62 / 62</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">scope</span><span>62 of the <em>bit-vector</em> obligations. The rest of each proof still rests on the solver.</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p class="slide__cite">Don't trust the tool — check its output.</p>
</section>

<section class="slide is-backup">
  <p class="slide__act">backup <span class="slide__scope is-backup-tag">not in the talk</span></p>
  <h2>Exactly how far this goes — and no further</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag ok">shipping</span><span>theorem proving · SMT · bounded MC · translation validation</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag warn">partial</span><span>refinement to Lean · mutation · abstract interpretation</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">not yet</span><span>An authority audit. We have not been audited.</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p>Bounded model checking is bounded. Verus, Rocq and Kani <em>are</em> gated on
  pull requests &mdash; but path-filtered, so a commit outside those paths triggers
  nothing. <span class="hi">Lean runs in no workflow at all.</span></p>
</section>

<section class="slide is-backup">
  <p class="slide__act">backup <span class="slide__scope is-backup-tag">not in the talk</span></p>
  <h2>Every one of these gates was green for the wrong reason</h2>
  <div class="ledger">
    <div class="ledger__row"><span class="ledger__tag bad">scry</span><span>a proof that never ran</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">synth</span><span>two validators, one blind spot</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">loom</span><span>a gate with zero callers</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">meld</span><span>a test on a path the shipped code skipped</span><span class="ledger__val">&nbsp;</span></div>
    <div class="ledger__row"><span class="ledger__tag bad">gale</span><span>a count that cannot see instances</span><span class="ledger__val">&nbsp;</span></div>
  </div>
  <p class="slide__cite">One of them, concretely: a requirement said the fuser
  rejects a component that instantiates a module twice. The test called the reject
  function directly and passed. The shipped path accepted those modules and
  duplicated them.</p>
  <blockquote class="slide__quote">The failure produced the same observable as
  success.</blockquote>
</section>

<section class="slide is-backup">
  <p class="slide__act">backup <span class="slide__scope is-backup-tag">not in the talk</span></p>
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
