// Sierpinski triangle — chaos game with slowly rotating vertices
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
  // Accumulation buffer — counts how many times each pixel is hit
  const accum = new Float32Array(W * H);

  // Fill background
  for (let i = 0; i < W * H * 4; i += 4) {
    buf[i] = 10; buf[i + 1] = 13; buf[i + 2] = 20; buf[i + 3] = 255;
  }

  let angle = 0;
  let px = W / 2;
  let py = H / 2;

  let animId;
  let lastFrame = 0;
  const frameInterval = 50;
  let generation = 0;

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    // Three vertices of the triangle, slowly rotating
    const cx = W / 2;
    const cy = H / 2;
    const r = Math.min(W, H) * 0.45;
    const vertices = [];
    for (let i = 0; i < 3; i++) {
      const a = angle + (i * Math.PI * 2) / 3 - Math.PI / 2;
      vertices.push({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r });
    }

    // Run chaos game iterations
    for (let i = 0; i < 500; i++) {
      const v = vertices[Math.floor(Math.random() * 3)];
      px = (px + v.x) / 2;
      py = (py + v.y) / 2;

      const ix = Math.floor(px);
      const iy = Math.floor(py);
      if (ix >= 0 && ix < W && iy >= 0 && iy < H) {
        accum[iy * W + ix] += 0.15;
      }
    }

    // Fade accumulation slowly
    for (let i = 0; i < W * H; i++) {
      accum[i] *= 0.998;
      const v = Math.min(1, accum[i]);
      const idx = i * 4;
      buf[idx] = (10 + v * 98) | 0;
      buf[idx + 1] = (13 + v * 127) | 0;
      buf[idx + 2] = (20 + v * 235) | 0;
    }

    ctx.putImageData(imgData, 0, 0);

    angle += 0.001;
    generation++;

    // Periodically clear for fresh pattern
    if (generation % 3000 === 0) {
      accum.fill(0);
    }
  }

  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(animId); }
    else { animId = requestAnimationFrame(render); }
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    for (let i = 0; i < 100; i++) render(i * frameInterval);
    cancelAnimationFrame(animId);
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    animId = requestAnimationFrame(render);
  }
})();
