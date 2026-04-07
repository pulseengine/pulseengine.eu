// Perlin noise contour lines — slowly morphing topographic map
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const W = 360;
  const H = 240;
  canvas.width = W;
  canvas.height = H;

  const imgData = ctx.createImageData(W, H);
  const buf = imgData.data;

  // Permutation table
  const PERM = new Uint8Array(512);
  for (let i = 0; i < 256; i++) PERM[i] = i;
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = PERM[i]; PERM[i] = PERM[j]; PERM[j] = tmp;
  }
  for (let i = 0; i < 256; i++) PERM[256 + i] = PERM[i];

  function fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }
  function lerp(a, b, t) { return a + (b - a) * t; }

  function grad(hash, x, y) {
    const h = hash & 3;
    const u = h < 2 ? x : y;
    const v = h < 2 ? y : x;
    return ((h & 1) ? -u : u) + ((h & 2) ? -v : v);
  }

  function noise2d(x, y) {
    const xi = Math.floor(x) & 255;
    const yi = Math.floor(y) & 255;
    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);
    const u = fade(xf);
    const v = fade(yf);
    const aa = PERM[PERM[xi] + yi];
    const ab = PERM[PERM[xi] + yi + 1];
    const ba = PERM[PERM[xi + 1] + yi];
    const bb = PERM[PERM[xi + 1] + yi + 1];
    return lerp(
      lerp(grad(aa, xf, yf), grad(ba, xf - 1, yf), u),
      lerp(grad(ab, xf, yf - 1), grad(bb, xf - 1, yf - 1), u),
      v
    );
  }

  function fbm(x, y, octaves) {
    let val = 0, amp = 1, freq = 1, total = 0;
    for (let i = 0; i < octaves; i++) {
      val += noise2d(x * freq, y * freq) * amp;
      total += amp;
      amp *= 0.5;
      freq *= 2;
    }
    return val / total;
  }

  let time = 0;
  let animId;
  let lastFrame = 0;
  const frameInterval = 80; // Slower — contours don't need fast updates
  const numContours = 12;

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    const scale = 0.012;

    for (let py = 0; py < H; py++) {
      for (let px = 0; px < W; px++) {
        const n = fbm(px * scale + time, py * scale, 4);
        // Normalize to 0-1
        const v = (n + 1) * 0.5;

        // Create contour lines: sharp brightness at specific iso-values
        const contourVal = v * numContours;
        const frac = contourVal - Math.floor(contourVal);
        // Thin contour line when frac is near 0 or 1
        const edge = Math.min(frac, 1 - frac);
        const line = edge < 0.06 ? 1.0 - edge / 0.06 : 0;

        // Base fill between contours
        const fill = v * 0.15;
        const brightness = fill + line * 0.7;

        const idx = (py * W + px) * 4;
        buf[idx] = (10 + brightness * 98) | 0;
        buf[idx + 1] = (13 + brightness * 127) | 0;
        buf[idx + 2] = (20 + brightness * 235) | 0;
        buf[idx + 3] = 255;
      }
    }

    ctx.putImageData(imgData, 0, 0);
    time += 0.008;
  }

  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(animId); }
    else { animId = requestAnimationFrame(render); }
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    render(0);
    cancelAnimationFrame(animId);
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    animId = requestAnimationFrame(render);
  }
})();
