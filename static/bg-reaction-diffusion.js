// Reaction-diffusion (Gray-Scott model) background
// Slowly evolving Turing patterns — spots, stripes, coral
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const W = 200;
  const H = 133;
  canvas.width = W;
  canvas.height = H;

  // Gray-Scott parameters — different presets give different patterns
  const presets = [
    { f: 0.0545, k: 0.062, name: 'spots' },
    { f: 0.042, k: 0.063, name: 'stripes' },
    { f: 0.035, k: 0.065, name: 'coral' },
    { f: 0.025, k: 0.06, name: 'worms' },
  ];

  const preset = presets[Math.floor(Math.random() * presets.length)];
  const f = preset.f;
  const k = preset.k;
  const Da = 1.0;
  const Db = 0.5;

  // Two chemical concentrations
  const size = W * H;
  let a = new Float32Array(size);
  let b = new Float32Array(size);
  let nextA = new Float32Array(size);
  let nextB = new Float32Array(size);

  // Initialize: all A=1, B=0, with a seeded region of B
  for (let i = 0; i < size; i++) { a[i] = 1.0; b[i] = 0.0; }

  // Seed several random spots of chemical B
  for (let s = 0; s < 12; s++) {
    const sx = 20 + Math.floor(Math.random() * (W - 40));
    const sy = 20 + Math.floor(Math.random() * (H - 40));
    const r = 3 + Math.floor(Math.random() * 4);
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        if (dx * dx + dy * dy <= r * r) {
          const idx = ((sy + dy + H) % H) * W + ((sx + dx + W) % W);
          b[idx] = 1.0;
        }
      }
    }
  }

  const imgData = ctx.createImageData(W, H);
  const buf = imgData.data;

  let animId;
  let lastFrame = 0;
  const frameInterval = 50;

  function step() {
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const idx = y * W + x;

        // Laplacian with wrapping
        const up = ((y - 1 + H) % H) * W + x;
        const dn = ((y + 1) % H) * W + x;
        const lt = y * W + ((x - 1 + W) % W);
        const rt = y * W + ((x + 1) % W);

        const lapA = a[up] + a[dn] + a[lt] + a[rt] - 4 * a[idx];
        const lapB = b[up] + b[dn] + b[lt] + b[rt] - 4 * b[idx];

        const aVal = a[idx];
        const bVal = b[idx];
        const abb = aVal * bVal * bVal;

        nextA[idx] = aVal + Da * lapA - abb + f * (1.0 - aVal);
        nextB[idx] = bVal + Db * lapB + abb - (k + f) * bVal;
      }
    }

    // Swap buffers
    const tmpA = a; a = nextA; nextA = tmpA;
    const tmpB = b; b = nextB; nextB = tmpB;
  }

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    // Run multiple simulation steps per frame for visible evolution
    for (let s = 0; s < 8; s++) step();

    // Render: map chemical B concentration to color
    for (let i = 0; i < size; i++) {
      const v = Math.min(1, Math.max(0, b[i]));
      const idx = i * 4;

      // Dark blue/cyan palette matching site colors
      buf[idx] = (10 + v * 98) | 0;        // R: 10 → 108
      buf[idx + 1] = (13 + v * 127) | 0;   // G: 13 → 140
      buf[idx + 2] = (20 + v * 235) | 0;   // B: 20 → 255
      buf[idx + 3] = 255;
    }

    ctx.putImageData(imgData, 0, 0);
  }

  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(animId); }
    else { animId = requestAnimationFrame(render); }
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    for (let i = 0; i < 2000; i++) step();
    render(0);
    cancelAnimationFrame(animId);
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    animId = requestAnimationFrame(render);
  }
})();
