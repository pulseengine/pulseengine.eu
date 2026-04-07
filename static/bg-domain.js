// Domain coloring — complex function visualization with slowly morphing parameters
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

  let time = 0;
  let animId;
  let lastFrame = 0;
  const frameInterval = 50;

  // Complex arithmetic helpers
  function cmul(ar, ai, br, bi) { return [ar * br - ai * bi, ar * bi + ai * br]; }
  function cabs(r, i) { return Math.sqrt(r * r + i * i); }
  function carg(r, i) { return Math.atan2(i, r); }

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    const scale = 4;
    const aspect = W / H;

    // Morphing parameter for the complex function
    const pr = Math.sin(time * 0.3) * 0.8;
    const pi = Math.cos(time * 0.2) * 0.8;

    for (let py = 0; py < H; py++) {
      for (let px = 0; px < W; px++) {
        // Map pixel to complex plane
        let zr = (px / W - 0.5) * scale * aspect;
        let zi = (py / H - 0.5) * scale;

        // f(z) = z^3 + p*z + 1 (morphing cubic)
        const z2 = cmul(zr, zi, zr, zi);
        const z3 = cmul(z2[0], z2[1], zr, zi);
        const pz = cmul(pr, pi, zr, zi);
        const wr = z3[0] + pz[0] + 1;
        const wi = z3[1] + pz[1];

        const mag = cabs(wr, wi);
        const arg = carg(wr, wi);

        // Map argument (angle) to hue, magnitude to brightness
        // Use site palette colors based on angle
        const t = (arg / (Math.PI * 2) + 1) % 1;
        const brightness = 1 - 1 / (1 + mag * 0.3);

        // Contour lines on magnitude
        const logMag = Math.log(mag + 1);
        const contour = Math.abs(logMag - Math.round(logMag)) < 0.08 ? 0.3 : 0;

        let r, g, b;
        if (t < 0.33) {
          const s = t / 0.33;
          r = 10 + s * 98; g = 13 + s * 127; b = 20 + s * 235;
        } else if (t < 0.66) {
          const s = (t - 0.33) / 0.33;
          r = 108 - s * 74; g = 140 + s * 71; b = 255 - s * 17;
        } else {
          const s = (t - 0.66) / 0.34;
          r = 34 + s * 158; g = 211 - s * 79; b = 238 + s * 14;
        }

        const v = brightness + contour;
        const idx = (py * W + px) * 4;
        buf[idx] = Math.min(255, (r * v) | 0);
        buf[idx + 1] = Math.min(255, (g * v) | 0);
        buf[idx + 2] = Math.min(255, (b * v) | 0);
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
