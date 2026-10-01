'use strict';
// Layer evidence view — pulseengine.eu#201 + #205.
// Data comes from static/layers.json, written by scripts/fetch-layers.py in the
// deploy. The page never computes a figure it cannot attribute to that file.
const DATA_URL = (document.getElementById('lv-root')
  && document.getElementById('lv-root').dataset.src) || '/layers.json';
const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (t, c, txt) => { const n = document.createElement(t); if (c) n.className = c;
  if (txt != null) n.textContent = txt; return n; };
const PLAT = p => p.replace('aarch64','arm64').replace('x86_64','x64')
  .replace('-apple-darwin','·mac').replace('-unknown-linux-gnu','·linux')
  .replace('-pc-windows-msvc','·win');
const DAYS = (a, b) => Math.round((new Date(b) - new Date(a)) / 864e5);
const fmtDate = s => new Date(s).toISOString().slice(0, 10);
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

let D, REALM = 'pulseengine', IDX = 0, cards = [];
const R = n => D.realms[n];
const cur = () => R(REALM).layers[R(REALM).order[IDX]];
const newestOf = n => D.realms[n].layers[D.realms[n].order[0]];

/* A transition only if the browser has one and motion is welcome. */
const swap = fn => (document.startViewTransition && !REDUCED)
  ? document.startViewTransition(fn) : fn();

/* ── #201 · the bento ────────────────────────────────────────────────────── */
function figures() {
  const c = newestOf('pulseengine'), cov = newestOf('covalent');
  const tools = Object.values(c.tools);
  const signed = tools.filter(t => t.proof && t.proof !== 'unverified').length;
  const wTools = Object.values(newestOf('pulseengine-wasm').tools);
  const unver = wTools.filter(t => t.proof === 'unverified').length;
  const left = DAYS(new Date().toISOString().slice(0, 10), c.support_until);
  return [
    { lead: 1, k: 'current layer', v: c.layer,
      u: 'counter ' + c.counter + ' · issued ' + fmtDate(c.issued) + ' · ' + c.payloads + ' payload blobs',
      cmd: 'curl -s "https://ghcr.io/v2/pulseengine/layers/tags/list" \\\n  -H "Authorization: Bearer $(anon_token layers)" | jq -r \'.tags[-1]\'',
      note: 'The tag list is the history. Tags are `YYYY.MM.P` with a monotonic per-line counter, so the newest is the last element and no separate index is needed.' },
    { k: 'payloads signed', v: signed + '/' + tools.length, u: 'cosign-sums, this realm',
      tone: signed === tools.length ? 'g' : 'a',
      cmd: 'jq -r \'.manifests[].annotations["eu.pulseengine.source.proof"]\' envelope.json \\\n  | sort | uniq -c',
      note: 'Read from the layer’s own signed envelope, so the figure is attested by the same signature that attests the bytes.' },
    { k: 'unverified upstream', v: String(unver), u: 'of ' + wTools.length + ' in pulseengine-wasm',
      tone: unver ? 'a' : 'g',
      cmd: 'jq -r \'.manifests[].annotations\n  | select(.["eu.pulseengine.source.proof"]=="unverified")\n  | .["eu.pulseengine.tool"]\' wasm-envelope.json | sort -u',
      note: 'wac, wkg and wit-bindgen-wrpc publish neither cosign-signed sums nor build provenance. Each travels with the operator’s reason signed into the layer. They reach a consumer through the `covalent` composition, which delivers ' + cov.effective.tools + ' tools in total and inherits all ' + cov.effective.unverified + ' of them — a composition cannot widen trust, and it cannot narrow it either. Showing this number is the panel earning trust: a dashboard that could only go green would not be evidence.' },
    { wide: 1, k: 'support window', v: left + ' days', u: 'this layer, until ' + c.support_until,
      tone: left > 14 ? 'g' : left > 5 ? 'a' : 'r',
      cmd: 'curl -s .../blobs/$LINE_STATUS_DIGEST \\\n  | jq -r \'.payload\' | base64 -d | jq \'.["support-until"]\'',
      note: 'From the signed `line-status` document. The rolling policy is one month as of varve v0.33.0. For a composition this figure is not the one to show — see the covalent realm below.' }
  ];
}

function renderBento() {
  const host = $('#lv-figs'); host.textContent = '';
  figures().forEach(f => {
    const b = el('button', 'lv__tile' + (f.lead ? ' tile--lead' : '') + (f.wide ? ' tile--wide' : '')
      + (f.tone ? ' tone-' + f.tone : ''));
    b.type = 'button'; b.setAttribute('aria-expanded', 'false');
    b.append(el('span', 'lv__k', f.k), el('span', 'lv__val', f.v), el('span', 'lv__u', f.u));
    const more = el('span', 'lv__more'); more.append(el('i', null, '+'),
      document.createTextNode('how this is derived')); b.append(more);
    const p = el('div', 'lv__prov');
    p.innerHTML = f.note.replace(/`([^`]+)`/g, '<code>$1</code>');
    p.append(Object.assign(el('code', 'lv__cmd'), { textContent: f.cmd }));
    b.addEventListener('click', () => {
      const on = p.classList.toggle('is-open');
      b.setAttribute('aria-expanded', String(on));
    });
    host.append(b, p);
  });
}

/* ── freshness, derived from the age of the fetch ────────────────────────── */
const AGE = () => Math.max(0, Math.round((Date.now() - new Date(D.generated_utc)) / 6e4));
const stateFor = m => m < 1440 ? 'live' : m < 10080 ? 'aging' : 'stale';
const human = m => m < 90 ? m + ' min' : m < 2880 ? Math.round(m / 60) + ' h' : Math.round(m / 1440) + ' d';

function renderFresh(state, preview) {
  const band = $('#lv-fresh'); band.dataset.state = state;
  const a = human(AGE());
  const real = {
    live:  'measured ' + a + ' ago — <span class="lv__txt">registry reachable, all three realms answered</span>',
    aging: 'measured ' + a + ' ago — <span class="lv__txt">older than a deploy cycle. Figures still shown, the timestamp moves to the front.</span>',
    stale: 'last good fetch ' + a + ' ago — <span class="lv__txt">figures withheld. The panel states the age and links the registry rather than showing numbers it cannot date.</span>' };
  const demo = {
    live:  'measured 4 min ago — <span class="lv__txt">registry reachable, all three realms answered</span>',
    aging: 'measured 31 h ago — <span class="lv__txt">older than a deploy cycle. Figures still shown, the timestamp moves to the front.</span>',
    stale: 'fetch failed, last good 9 d ago — <span class="lv__txt">figures withheld. The panel states the age and links the registry rather than showing numbers it cannot date.</span>' };
  $('#lv-fresh-txt').innerHTML = (preview ? demo : real)[state]
    + (preview ? ' <span class="lv__txt" style="opacity:.7">[preview]</span>' : '');
  $$('.lv__seg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.st === state)));
  $$('.lv__tile .lv__val').forEach(v => { v.style.opacity = state === 'stale' ? '.26' : '1'; });
}

/* ── #205 · realms ───────────────────────────────────────────────────────── */
const LABEL = { 'pulseengine': 'the methodology toolchain',
                'pulseengine-wasm': 'component-model tools, vouched for',
                'covalent': 'a composition — carries nothing itself' };

function renderRealms() {
  const host = $('#lv-realms'); host.textContent = '';
  Object.keys(D.realms).forEach(name => {
    const b = el('button', 'lv__realm'); b.type = 'button';
    b.setAttribute('aria-pressed', String(name === REALM));
    const n = R(name).order.length;
    b.append(el('b', null, name),
             el('span', null, n + (n === 1 ? ' layer · ' : ' layers · ') + LABEL[name]));
    b.addEventListener('click', () => {
      if (name === REALM) return;
      swap(() => { REALM = name; IDX = 0; renderRealms(); buildDeck(); select(); });
    });
    host.append(b);
  });
}

/* marks shown on a card face — the reasons a layer is worth a second look */
function marks(L) {
  const m = [];
  const lost = L.diff.platforms.filter(p => p.lost.length);
  if (lost.length) m.push(['bad', '−' + lost.reduce((s, p) => s + p.lost.length, 0) + ' payloads']);
  if (L.effective && L.effective.overstated_days > 0)
    m.push(['bad', 'window +' + L.effective.overstated_days + 'd']);
  if (L.includes.length) {
    const b = L.includes.filter(i => i.behind > 0);
    if (b.length) m.push(['warn', b[0].behind + ' behind']);
    m.push(['info', L.includes.length + ' includes']);
  }
  if (L.diff.versions.length) m.push(['info', L.diff.versions.length +
      (L.diff.versions.length === 1 ? ' bump' : ' bumps')]);
  if (L.diff.added.length) m.push(['ok', '+' + L.diff.added.length + ' new']);
  if (!m.length) m.push(['info', Object.keys(L.tools).length + ' tools']);
  return m.slice(0, 3);
}

function buildDeck() {
  const deck = $('#lv-deck'), scale = $('#lv-scale');
  deck.textContent = ''; scale.textContent = ''; cards = [];
  let lastLine = null;
  R(REALM).order.forEach((tag, i) => {
    const L = R(REALM).layers[tag];
    const line = L.line || tag.replace(/\.\d+$/, '');

    const c = el('button', 'lv__card'); c.type = 'button'; c.dataset.i = i;
    const t = el('div', 'lv__tag'); t.append(document.createTextNode(L.layer));
    t.append(el('em', null, 'counter ' + L.counter)); c.append(t);
    c.append(el('div', 'lv__when', fmtDate(L.issued) + ' \u00b7 ' +
      (L.includes.length ? L.includes.length + ' includes' : L.payloads + ' blobs')));
    const mk = el('div', 'lv__marks');
    if (!L.prev && L.branched_from) mk.append(el('span', 'lv__mk is-info', 'line ' + line));
    marks(L).forEach(([cls, txt]) => mk.append(el('span', 'lv__mk is-' + cls, txt)));
    c.append(mk);
    c.addEventListener('click', () => go(i));
    deck.append(c); cards.push(c);

    // The ruler is the one place the boundary between lines can be stated
    // without competing with the stack, so each line gets a heading there.
    if (line !== lastLine) {
      const h = el('div', 'lv__line-mark', line);
      scale.append(h);
      lastLine = line;
    }
    const tk = el('button', 'lv__tick'); tk.type = 'button'; tk.dataset.i = i;
    tk.textContent = L.layer.replace(/^\d{4}\./, '');
    if (marks(L).some(([cls]) => cls === 'bad')) tk.classList.add('is-flagged');
    tk.addEventListener('click', () => go(i));
    scale.append(tk);
  });
  layout();
}

/* Depth: older layers recede up and back; newer ones fly past the viewer. */
const MAXD = 8;
/* Only the cards within the visible depth exist as boxes. Everything deeper is
   display:none, not merely transparent: in a preserve-3d context each card is a
   composited layer, and nineteen of them with soft shadows froze the renderer. */
function layout() {
  cards.forEach((c, i) => {
    const d = i - IDX;
    if (d < 0 || d > MAXD) { c.style.display = 'none'; return; }
    c.style.display = '';
    c.style.transform = 'translate3d(0,' + (-d * 21) + 'px,' + (-d * 88) + 'px)';
    c.style.opacity = String(1 - d * 0.062);
    c.style.zIndex = String(120 - d);
    c.dataset.front = String(d === 0);
  });
  $$('.lv__tick').forEach((t, i) => t.setAttribute('aria-current', String(i === IDX)));
  const t = $$('.lv__tick')[IDX];
  if (t) t.scrollIntoView({ block: 'nearest', behavior: 'auto' });
  $('#lv-newer').disabled = IDX === 0;
  $('#lv-older').disabled = IDX === cards.length - 1;
}

function go(i) {
  const n = Math.max(0, Math.min(cards.length - 1, i));
  if (n === IDX) return;
  IDX = n; layout(); select();
}

/* ── detail ──────────────────────────────────────────────────────────────── */
function chip(cls, a, arrow, b) {
  const c = el('span', 'lv__c is-' + cls); c.append(el('b', null, a));
  if (arrow) { c.append(el('span', 'lv__ar', ' ' + arrow + ' ')); c.append(document.createTextNode(b)); }
  return c;
}

function select() {
  const L = cur(), det = $('#lv-det'); det.textContent = '';
  const today = new Date().toISOString().slice(0, 10);
  const h = el('div', 'lv__det-h');
  h.append(el('h3', null, L.layer));
  h.append(el('span', 'lv__meta', REALM + ' · counter ' + L.counter + ' · issued ' +
    L.issued.replace('T', ' ').replace('Z', ' UTC')));
  det.append(h);

  const stated = L.support_until;
  const eff = L.effective ? L.effective.support_until : stated;
  const left = DAYS(today, eff);
  const tools = Object.values(L.tools);
  const pills = el('div', 'lv__pills');
  pills.append(el('span', 'lv__pill is-c', L.includes.length
    ? L.effective.tools + ' tools, via ' + L.includes.length + ' layers'
    : tools.length + ' tools'));
  pills.append(el('span', 'lv__pill', L.includes.length ? 'no payloads of its own' : L.payloads + ' payload blobs'));
  pills.append(el('span', 'lv__pill is-g', 'root verifies'));
  const unv = L.includes.length ? L.effective.unverified
                                : tools.filter(t => t.proof === 'unverified').length;
  pills.append(el('span', 'lv__pill is-' + (unv ? 'a' : 'g'),
    unv ? unv + ' unverified upstream' : 'all payloads signed'));
  pills.append(el('span', 'lv__pill is-' + (left > 14 ? 'g' : left > 5 ? 'a' : 'r'),
    (L.effective && L.effective.overstated_days ? 'effective: ' : '') +
    (left >= 0 ? left + ' more days' : 'ended ' + (-left) + ' d ago')));
  det.append(pills);

  if (L.includes.length) return composition(L, det, stated, eff);

  // A layer is diffed against its predecessor IN ITS OWN LINE. The first layer
  // of a new line has none, but it continued from whatever was newest in the
  // realm when it was issued, so that comparison is shown and labelled a branch.
  const bf = L.branched_from;
  const src = L.prev ? L.diff : (bf || L.diff);
  det.append(el('div', 'lv__dl',
    L.prev ? 'tool versions changed vs ' + L.prev
           : bf ? 'line ' + (L.line || '') + ' starts here \u2014 changes vs ' + bf.layer
                : 'oldest layer in this realm'));
  const vd = el('div', 'lv__chg');
  (src.versions || []).forEach(v => vd.append(chip('up', v.tool + ' ' + v.from, '\u2192', v.to)));
  (src.added || []).forEach(a => vd.append(chip('add',
    '+ ' + (a.tool || a) + (a.version ? ' ' + a.version : ''))));
  (src.removed || []).forEach(r => vd.append(chip('loss', '\u2212 ' + r)));
  if (!vd.children.length) vd.append(el('span', 'lv__none',
    (L.prev || bf) ? 'no tool version changed' : 'nothing behind it to compare against'));
  det.append(vd);

  if (!L.prev && bf) {
    const n = el('div', 'lv__alert is-amber');
    n.append(el('b', null, '\u25c9 a new line starts here'));
    n.insertAdjacentHTML('beforeend',
      'This is counter 1 of line <b>' + (L.line || '') + '</b>. It continued from <b>' +
      bf.layer + '</b> in line <b>' + bf.line + '</b>, the layer that was newest when this ' +
      'one was issued.<br><br>Lines run in parallel. <code>varve deposit</code> takes the layer ' +
      'tag, the counter and the issue date as explicit inputs, so line ' + bf.line + ' does not ' +
      'close when this one opens: it can still receive a patch, and its layers keep their own ' +
      'support windows. The branch point is resolved by issue time, so a layer added to ' +
      bf.line + ' later cannot change what this layer is recorded as having changed.');
    det.append(n);
  }

  const lost = L.diff.platforms.filter(p => p.lost.length);
  const gained = L.diff.platforms.filter(p => p.gained.length);
  if (lost.length || gained.length) {
    det.append(el('div', 'lv__dl', 'per-platform payloads changed'));
    const pd = el('div', 'lv__chg');
    lost.forEach(p => pd.append(chip('loss', p.tool, '−', p.lost.map(PLAT).join(' '))));
    gained.forEach(p => pd.append(chip('add', p.tool, '+', p.gained.map(PLAT).join(' '))));
    det.append(pd);
  }
  if (lost.length) {
    const n = lost.reduce((s, p) => s + p.lost.length, 0);
    const a = el('div', 'lv__alert');
    a.append(el('b', null, '◉ this is the case for the view'));
    a.insertAdjacentHTML('beforeend',
      'This layer shipped <b>' + n + ' fewer platform payloads</b> than ' + L.prev + ', across ' +
      lost.length + ' tools — no Linux build of ' + lost.map(p => p.tool).join(', ') + '. ' +
      'The version diff above shows only <code>ordeal 0.22.0 → 0.22.1</code>, so a history that ' +
      'compared versions alone would call this layer routine. The cause was an assembler that read ' +
      '<code>asset-for</code> values literally instead of as templates (varve#199); omissions are ' +
      'reported per payload and the deposit still exits 0, which is correct for a genuinely unbuilt ' +
      'platform and exactly why it was quiet. Restored in 2026.09.19.');
    det.append(a);
  }
  contents(tools, det);
  // Only the genuinely oldest layer explains where the history stops. The
  // first layer of a NEW line also has no predecessor, but it has a branch
  // point, and that case is covered above.
  if (!L.prev && !L.branched_from) det.append(originNote());
}

function originNote() {
  const d = el('div', 'lv__alert is-amber');
  d.append(el('b', null, '◉ why the history stops here'));
  if (REALM === 'pulseengine') {
    d.insertAdjacentHTML('beforeend',
      '<b>Measured here:</b> the oldest layer in this registry is 2026.09.2, counter 3, created ' +
      '2026-09-09. The counter is per line, so counters 1–2 — 2026.09.0 and 2026.09.1 — are ' +
      'absent from this line.<br><br><b>Not measured here, cited:</b> the 2026.08 line and everything ' +
      'up to 2026.09.1 were signed by a root retired 2026-09-07 (varve#110, pulseengine.eu#204). This ' +
      'registry cannot show that; it shows only that they are gone. The oldest surviving layer ' +
      'postdates the rotation by two days, which is consistent with it.<br><br>The gap is stated ' +
      'rather than hidden. A card that rendered those layers as if they still verified would be ' +
      'worse than no view.');
  } else {
    d.insertAdjacentHTML('beforeend',
      'Counter ' + cur().counter + '. This is the realm’s first published layer, so there is ' +
      'nothing behind it to diff against. An empty history here is a fact about the realm’s age, ' +
      'not a gap in the data — which is why it reads differently from the note on <b>pulseengine</b>.');
  }
  return d;
}

function composition(L, det, stated, eff) {
  const c = el('div', 'lv__comp');
  c.append(el('b', null, 'a composition — it holds no tools'));
  c.insertAdjacentHTML('beforeend',
    '<p>Every payload a consumer gets from this layer belongs to another realm and is signed by ' +
    'another root. This layer asserts one thing: <b style="color:var(--ink)">these two, together, ' +
    'are a toolchain</b>. varve verifies each included layer against its own realm’s root, never ' +
    'this one, so a composing realm cannot widen trust. An include therefore names a realm and a ' +
    '<em>digest</em>, because a tag could be moved after this layer was signed.</p>');
  det.append(c);

  det.append(el('div', 'lv__dl', 'what it composes'));
  L.includes.forEach(inc => {
    const box = el('div', 'lv__inc');
    const top = el('div', 'lv__inc-top');
    top.append(el('span', 'lv__rn', inc.realm), el('span', 'lv__lt', inc.layer));
    box.append(top, el('div', 'lv__dg', inc.digest));
    const f = el('div', 'lv__facts');
    if (inc.resolved) {
      f.append(el('span', 'lv__pill', inc.tools + ' tools'));
      f.append(el('span', 'lv__pill is-' + (inc.unverified ? 'a' : 'g'),
        inc.unverified ? inc.unverified + ' unverified' : 'all signed'));
      f.append(el('span', 'lv__pill', 'supported to ' + inc.support_until));
      f.append(el('span', 'lv__pill is-' + (inc.behind ? 'a' : 'g'),
        inc.behind ? inc.behind + ' layers behind ' + inc.newest_in_realm : 'newest in its realm'));
    } else f.append(el('span', 'lv__pill is-r', 'not resolvable from the registry'));
    box.append(f); det.append(box);
  });

  if (L.effective.overstated_days > 0) {
    const a = el('div', 'lv__alert');
    a.append(el('b', null, '◉ the window outlives what is inside it'));
    a.insertAdjacentHTML('beforeend',
      'This layer states <b>' + stated + '</b>. Every layer it composes ends <b>' + eff + '</b>, ' +
      L.effective.overstated_days + ' days earlier. Nothing is computed wrongly: ' +
      '<code>support-horizon</code> derives a window from the channel policy and the issue date, and ' +
      'a composition is cut after the layers it pairs, so its window routinely closes last. The ' +
      'documented rule is written for a layer that carries payloads.<br><br>So this view reports the ' +
      '<b>effective</b> horizon — the minimum over the closure — and names what constrains it: ' +
      L.effective.constrained_by.join(', ') + '. Filed as ' +
      '<a href="https://github.com/pulseengine/varve/issues/226">varve#226</a>.');
    det.append(a);
  }
  const drift = L.includes.filter(i => i.behind > 0);
  if (drift.length) {
    const a = el('div', 'lv__alert is-amber');
    a.append(el('b', null, '◉ the pairing has drifted'));
    a.insertAdjacentHTML('beforeend', drift.map(i =>
      'It pins <b>' + i.realm + ' ' + i.layer + '</b> while that realm has published <b>' +
      i.newest_in_realm + '</b>, ' + i.behind + ' layers on.').join(' ') +
      ' That is not a fault — a composition is a deliberate pin, and re-cutting it is a decision. ' +
      'But it is invisible unless something walks both and says so, which is the second reason this ' +
      'view exists.');
    det.append(a);
  }

  const all = [];
  L.includes.forEach(inc => {
    const src = inc.resolved && R(inc.realm).layers[inc.layer];
    if (src) Object.values(src.tools).forEach(t => all.push({ ...t, from: inc.realm }));
  });
  det.append(el('div', 'lv__dl', 'what a consumer effectively gets'));
  contents(all, det, true);
}

function contents(tools, det, origin) {
  if (!origin) det.append(el('div', 'lv__dl', 'contents'));
  const tb = el('table', 'lv__tools');
  tb.innerHTML = '<thead><tr><th>tool</th><th>version</th><th>platforms</th>' +
    (origin ? '<th>from</th>' : '') + '<th>provenance</th></tr></thead>';
  const body = el('tbody');
  tools.sort((a, b) => a.name.localeCompare(b.name)).forEach(t => {
    const tr = el('tr');
    const n = el('td', 'lv__n'); n.append(document.createTextNode(t.name));
    if (t.kind && t.kind !== 'tool') n.append(el('span', 'lv__kind', t.kind));
    tr.append(n, el('td', 'lv__v', t.version),
      el('td', 'lv__p is-dim', t.platforms.length ? t.platforms.length + '×' : 'any'));
    if (origin) tr.append(el('td', 'lv__p is-dim', t.from));
    const td = el('td', 'lv__p');
    const good = t.proof && t.proof !== 'unverified';
    td.append(el('span', good ? 'is-ok' : 'is-warn', (good ? '✓ ' : '⚠ ') + t.proof));
    if (t.asserts) {
      const d = el('details', 'lv__why');
      d.append(el('summary', null, good ? 'what it asserts' : 'why it was ingested anyway'));
      d.append(el('p', null, t.asserts));
      td.append(d);
    }
    tr.append(td); body.append(tr);
  });
  tb.append(body); det.append(tb);
}

/* ── input: keys, swipe, wheel ───────────────────────────────────────────── */
function wireInput() {
  $('#lv-older').addEventListener('click', () => go(IDX + 1));
  $('#lv-newer').addEventListener('click', () => go(IDX - 1));
  addEventListener('keydown', e => {
    if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowLeft')  { go(IDX + 1); e.preventDefault(); }
    if (e.key === 'ArrowUp'   || e.key === 'ArrowRight') { go(IDX - 1); e.preventDefault(); }
  });
  let y0 = null;
  const stage = $('#lv-stage');
  stage.addEventListener('touchstart', e => { y0 = e.touches[0].clientY; }, { passive: true });
  stage.addEventListener('touchend', e => {
    if (y0 == null) return;
    const dy = e.changedTouches[0].clientY - y0;
    if (Math.abs(dy) > 42) go(IDX + (dy > 0 ? -1 : 1));
    y0 = null;
  }, { passive: true });
}

/* ── boot ────────────────────────────────────────────────────────────────── */
fetch(DATA_URL).then(r => r.json()).then(d => {
  D = d;
  const total = Object.values(d.realms).reduce((n, r) => n + r.order.length, 0);
  const gen = $('#lv-gen');
  if (gen) gen.textContent = 'Fetched ' + d.generated_utc + ' · ' + total +
    ' layers across ' + Object.keys(d.realms).length + ' realms.';
  renderBento(); renderFresh(stateFor(AGE()), false);
  $$('.lv__seg button').forEach(b => b.addEventListener('click', () =>
    renderFresh(b.dataset.st, b.dataset.st !== stateFor(AGE()))));

  const hr = location.hash.match(/realm=([\w-]+)/);
  if (hr && d.realms[hr[1]]) REALM = hr[1];
  renderRealms(); buildDeck();
  const hl = location.hash.match(/layer=([\d.]+)/);
  const i = hl ? R(REALM).order.indexOf(hl[1]) : -1;
  IDX = i < 0 ? 0 : i;
  layout(); select(); wireInput();

});
