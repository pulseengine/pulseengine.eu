// Wave interference — overlapping concentric sine waves creating moiré patterns
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

  // Wave sources — slowly drifting positions
  const sources = [
    { x: W * 0.3, y: H * 0.4, freq: 0.15, phase: 0, dx: 0.12, dy: 0.08 },
    { x: W * 0.7, y: H * 0.6, freq: 0.18, phase: 1.5, dx: -0.09, dy: 0.11 },
    { x: W * 0.5, y: H * 0.2, freq: 0.12, phase: 3.0, dx: 0.07, dy: -0.06 },
    { x: W * 0.2, y: H * 0.8, freq: 0.20, phase: 4.5, dx: -0.05, dy: -0.10 },
  ];

  let time = 0;
  let animId;
  let lastFrame = 0;
  const frameInterval = 50;

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    for (let py = 0; py < H; py++) {
      for (let px = 0; px < W; px++) {
        let sum = 0;

        for (let s = 0; s < sources.length; s++) {
          const src = sources[s];
          const dx = px - src.x;
          const dy = py - src.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          sum += Math.sin(dist * src.freq - time * 2 + src.phase);
        }

        // Normalize to 0-1
        const v = (sum / sources.length + 1) * 0.5;
        const idx = (py * W + px) * 4;

        // Map to site palette
        buf[idx] = (10 + v * 98) | 0;
        buf[idx + 1] = (13 + v * 127) | 0;
        buf[idx + 2] = (20 + v * 235) | 0;
        buf[idx + 3] = 255;
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // Drift sources slowly
    for (let s = 0; s < sources.length; s++) {
      const src = sources[s];
      src.x += src.dx;
      src.y += src.dy;
      // Bounce off edges
      if (src.x < 0 || src.x >= W) src.dx *= -1;
      if (src.y < 0 || src.y >= H) src.dy *= -1;
      src.x = Math.max(0, Math.min(W - 1, src.x));
      src.y = Math.max(0, Math.min(H - 1, src.y));
    }

    time += 0.03;
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
