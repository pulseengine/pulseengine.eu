// Conway's Game of Life — new random seed every 10 seconds
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const CELL = 3; // Pixel size per cell
  const W = Math.ceil(360 / CELL);
  const H = Math.ceil(240 / CELL);
  canvas.width = W * CELL;
  canvas.height = H * CELL;

  let grid = new Uint8Array(W * H);
  let next = new Uint8Array(W * H);

  // Seed patterns
  function seedRandom(density) {
    for (let i = 0; i < W * H; i++) {
      grid[i] = Math.random() < density ? 1 : 0;
    }
  }

  function seedSymmetric() {
    // Generate left half randomly, mirror to right
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < Math.ceil(W / 2); x++) {
        const alive = Math.random() < 0.3 ? 1 : 0;
        grid[y * W + x] = alive;
        grid[y * W + (W - 1 - x)] = alive;
      }
    }
  }

  function seedClusters() {
    grid.fill(0);
    const numClusters = 8 + Math.floor(Math.random() * 8);
    for (let c = 0; c < numClusters; c++) {
      const cx = Math.floor(Math.random() * W);
      const cy = Math.floor(Math.random() * H);
      const r = 5 + Math.floor(Math.random() * 10);
      for (let dy = -r; dy <= r; dy++) {
        for (let dx = -r; dx <= r; dx++) {
          if (dx * dx + dy * dy <= r * r && Math.random() < 0.45) {
            const x = (cx + dx + W) % W;
            const y = (cy + dy + H) % H;
            grid[y * W + x] = 1;
          }
        }
      }
    }
  }

  function seedSoup() {
    grid.fill(0);
    // Dense central soup
    const sx = Math.floor(W * 0.3);
    const sy = Math.floor(H * 0.3);
    const sw = Math.floor(W * 0.4);
    const sh = Math.floor(H * 0.4);
    for (let y = sy; y < sy + sh; y++) {
      for (let x = sx; x < sx + sw; x++) {
        grid[y * W + x] = Math.random() < 0.4 ? 1 : 0;
      }
    }
  }

  const seedFns = [
    function () { seedRandom(0.25); },
    function () { seedRandom(0.35); },
    seedSymmetric,
    seedClusters,
    seedSoup,
  ];

  let seedIdx = Math.floor(Math.random() * seedFns.length);
  seedFns[seedIdx]();

  // Track generation for reseed timing
  let generation = 0;
  let lastSeed = 0;
  const reseedInterval = 10000; // 10 seconds

  // Fade buffer for glow effect
  const imgData = ctx.createImageData(W * CELL, H * CELL);
  const buf = imgData.data;
  // Age tracking for cell brightness
  const age = new Float32Array(W * H);

  function step() {
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        // Count neighbors (wrapping)
        let count = 0;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            const nx = (x + dx + W) % W;
            const ny = (y + dy + H) % H;
            count += grid[ny * W + nx];
          }
        }

        const idx = y * W + x;
        const alive = grid[idx];

        if (alive) {
          next[idx] = (count === 2 || count === 3) ? 1 : 0;
        } else {
          next[idx] = (count === 3) ? 1 : 0;
        }
      }
    }

    // Swap
    const tmp = grid; grid = next; next = tmp;
    generation++;
  }

  function draw() {
    // Update age: alive cells brighten, dead cells fade
    for (let i = 0; i < W * H; i++) {
      if (grid[i]) {
        age[i] = Math.min(1, age[i] + 0.3);
      } else {
        age[i] = Math.max(0, age[i] - 0.02);
      }
    }

    // Render cells
    const cw = W * CELL;
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const v = age[y * W + x];

        // Color: dark background → accent blue when alive
        const r = (10 + v * 98) | 0;
        const g = (13 + v * 127) | 0;
        const b = (20 + v * 235) | 0;

        // Fill cell pixels
        for (let cy = 0; cy < CELL; cy++) {
          for (let cx = 0; cx < CELL; cx++) {
            const idx = ((y * CELL + cy) * cw + (x * CELL + cx)) * 4;
            buf[idx] = r;
            buf[idx + 1] = g;
            buf[idx + 2] = b;
            buf[idx + 3] = 255;
          }
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);
  }

  let animId;
  let lastFrame = 0;
  const frameInterval = 80; // ~12fps — deliberate, cellular automata look better slow

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    step();
    draw();

    // Reseed every 10 seconds
    if (timestamp - lastSeed > reseedInterval) {
      lastSeed = timestamp;
      seedIdx = (seedIdx + 1) % seedFns.length;
      seedFns[seedIdx]();
      age.fill(0);
    }
  }

  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(animId); }
    else { animId = requestAnimationFrame(render); }
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    for (let i = 0; i < 50; i++) step();
    draw();
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    lastSeed = performance.now();
    animId = requestAnimationFrame(render);
  }
})();
