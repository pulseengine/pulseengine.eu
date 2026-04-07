// Julia set fractal background — animated parameter drift
// Same rendering approach as Mandelbrot: low-res canvas, smooth coloring
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const W = 360;
  const H = 240;
  canvas.width = W;
  canvas.height = H;

  // Palette — same scheme as Mandelbrot for visual consistency
  const palette = new Array(256);
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    let r, g, b;
    if (t < 0.25) {
      const s = t / 0.25;
      r = lerp(8, 108, s); g = lerp(12, 140, s); b = lerp(28, 255, s);
    } else if (t < 0.5) {
      const s = (t - 0.25) / 0.25;
      r = lerp(108, 34, s); g = lerp(140, 211, s); b = lerp(255, 238, s);
    } else if (t < 0.75) {
      const s = (t - 0.5) / 0.25;
      r = lerp(34, 192, s); g = lerp(211, 132, s); b = lerp(238, 252, s);
    } else {
      const s = (t - 0.75) / 0.25;
      r = lerp(192, 8, s); g = lerp(132, 12, s); b = lerp(252, 28, s);
    }
    palette[i] = [r | 0, g | 0, b | 0];
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  // Interesting Julia constant orbits — parameter c drifts along these paths
  const paths = [
    // Orbit near the main cardioid boundary — produces spirals
    function (t) {
      const a = t * Math.PI * 2;
      const r = 0.7885;
      return { cr: r * Math.cos(a), ci: r * Math.sin(a) };
    },
    // Orbit near Douady rabbit → dendrite transition
    function (t) {
      const a = t * Math.PI * 2;
      return { cr: -0.8 + 0.15 * Math.cos(a), ci: 0.156 + 0.05 * Math.sin(a) };
    },
    // Orbit near Siegel disc
    function (t) {
      const a = t * Math.PI * 2;
      return { cr: -0.4 + 0.05 * Math.cos(a), ci: 0.6 + 0.05 * Math.sin(a) };
    },
  ];

  let pathIdx = Math.floor(Math.random() * paths.length);
  let time = Math.random(); // Start at random phase

  const maxIter = 80;
  const imgData = ctx.createImageData(W, H);
  const buf = imgData.data;

  const zoom = 3.2;
  let animId;
  let lastFrame = 0;
  const frameInterval = 50; // ~20fps

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    const path = paths[pathIdx];
    const c = path(time);
    const cr = c.cr;
    const ci = c.ci;

    const aspect = W / H;
    const halfW = zoom * 0.5;
    const halfH = halfW / aspect;
    const dx = zoom / W;
    const dy = (zoom / aspect) / H;

    for (let py = 0; py < H; py++) {
      const y0 = -halfH + py * dy;
      for (let px = 0; px < W; px++) {
        const x0 = -halfW + px * dx;
        let zr = x0, zi = y0;
        let iter = 0;

        while (zr * zr + zi * zi <= 4 && iter < maxIter) {
          const tmp = zr * zr - zi * zi + cr;
          zi = 2 * zr * zi + ci;
          zr = tmp;
          iter++;
        }

        const idx = (py * W + px) * 4;
        if (iter === maxIter) {
          buf[idx] = 10; buf[idx + 1] = 13; buf[idx + 2] = 20; buf[idx + 3] = 255;
        } else {
          const log2 = Math.log(2);
          const nu = Math.log(Math.log(zr * zr + zi * zi) / log2) / log2;
          const smooth = (iter + 1 - nu) / maxIter;
          const ci2 = ((smooth * 255 * 3) | 0) % 256;
          const col = palette[ci2];
          buf[idx] = col[0]; buf[idx + 1] = col[1]; buf[idx + 2] = col[2]; buf[idx + 3] = 255;
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // Drift c parameter slowly
    time += 0.0003;
    if (time > 1.0) {
      time = 0;
      pathIdx = (pathIdx + 1) % paths.length;
    }
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
