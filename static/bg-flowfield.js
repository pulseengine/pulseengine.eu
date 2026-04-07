// Flow field background — particles tracing through curl noise
// Produces river-like streams that slowly shift
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const W = 360;
  const H = 240;
  canvas.width = W;
  canvas.height = H;

  // Simple value noise (no dependencies)
  const PERM = new Uint8Array(512);
  for (let i = 0; i < 256; i++) PERM[i] = i;
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = PERM[i]; PERM[i] = PERM[j]; PERM[j] = tmp;
  }
  for (let i = 0; i < 256; i++) PERM[256 + i] = PERM[i];

  function fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }

  function grad(hash, x, y) {
    const h = hash & 3;
    const u = h < 2 ? x : y;
    const v = h < 2 ? y : x;
    return ((h & 1) ? -u : u) + ((h & 2) ? -v : v);
  }

  function noise2d(x, y) {
    const xi = x | 0;
    const yi = y | 0;
    const xf = x - xi;
    const yf = y - yi;
    const u = fade(xf);
    const v = fade(yf);
    const X = xi & 255;
    const Y = yi & 255;
    const aa = PERM[PERM[X] + Y];
    const ab = PERM[PERM[X] + Y + 1];
    const ba = PERM[PERM[X + 1] + Y];
    const bb = PERM[PERM[X + 1] + Y + 1];
    const x1 = lerp(grad(aa, xf, yf), grad(ba, xf - 1, yf), u);
    const x2 = lerp(grad(ab, xf, yf - 1), grad(bb, xf - 1, yf - 1), u);
    return lerp(x1, x2, v);
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  // Particles
  const NUM = 800;
  const particles = [];
  for (let i = 0; i < NUM; i++) {
    particles.push({
      x: Math.random() * W,
      y: Math.random() * H,
      age: Math.floor(Math.random() * 200),
      maxAge: 150 + Math.floor(Math.random() * 150),
    });
  }

  // Trail canvas — accumulates fading particle paths
  const trailCanvas = document.createElement('canvas');
  trailCanvas.width = W;
  trailCanvas.height = H;
  const tCtx = trailCanvas.getContext('2d');
  tCtx.fillStyle = 'rgb(10, 13, 20)';
  tCtx.fillRect(0, 0, W, H);

  let time = Math.random() * 100;
  let animId;
  let lastFrame = 0;
  const frameInterval = 33; // ~30fps for smooth trails

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    // Fade trails slightly
    tCtx.fillStyle = 'rgba(10, 13, 20, 0.02)';
    tCtx.fillRect(0, 0, W, H);

    const scale = 0.008;

    for (let i = 0; i < NUM; i++) {
      const p = particles[i];

      // Get flow angle from noise
      const angle = noise2d(p.x * scale, p.y * scale + time * 0.1) * Math.PI * 4;

      const prevX = p.x;
      const prevY = p.y;

      p.x += Math.cos(angle) * 0.8;
      p.y += Math.sin(angle) * 0.8;
      p.age++;

      // Fade in/out based on age
      const life = p.age / p.maxAge;
      const alpha = life < 0.1 ? life / 0.1 : life > 0.9 ? (1 - life) / 0.1 : 1;

      // Draw trail segment
      tCtx.strokeStyle = 'rgba(108, 140, 255, ' + (alpha * 0.6) + ')';
      tCtx.lineWidth = 1;
      tCtx.beginPath();
      tCtx.moveTo(prevX, prevY);
      tCtx.lineTo(p.x, p.y);
      tCtx.stroke();

      // Reset if out of bounds or too old
      if (p.x < 0 || p.x >= W || p.y < 0 || p.y >= H || p.age >= p.maxAge) {
        p.x = Math.random() * W;
        p.y = Math.random() * H;
        p.age = 0;
        p.maxAge = 150 + Math.floor(Math.random() * 150);
      }
    }

    time += 0.003;

    // Copy trail canvas to main canvas
    ctx.drawImage(trailCanvas, 0, 0);
  }

  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(animId); }
    else { animId = requestAnimationFrame(render); }
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    for (let i = 0; i < 300; i++) render(i * frameInterval);
    cancelAnimationFrame(animId);
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    animId = requestAnimationFrame(render);
  }
})();
