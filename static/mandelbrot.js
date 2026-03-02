// Mandelbrot fractal background — slow infinite zoom
// Renders at reduced resolution, stretched to fill viewport
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Render at low res for performance
  const W = 360;
  const H = 240;
  canvas.width = W;
  canvas.height = H;

  // Color palette — site accent colors at low intensity
  // Pre-compute a 256-entry palette
  const palette = new Array(256);
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    // Cycle through: deep blue → accent blue → cyan → purple → back
    let r, g, b;
    if (t < 0.25) {
      const s = t / 0.25;
      r = lerp(8, 108, s);
      g = lerp(12, 140, s);
      b = lerp(28, 255, s);
    } else if (t < 0.5) {
      const s = (t - 0.25) / 0.25;
      r = lerp(108, 34, s);
      g = lerp(140, 211, s);
      b = lerp(255, 238, s);
    } else if (t < 0.75) {
      const s = (t - 0.5) / 0.25;
      r = lerp(34, 192, s);
      g = lerp(211, 132, s);
      b = lerp(238, 252, s);
    } else {
      const s = (t - 0.75) / 0.25;
      r = lerp(192, 8, s);
      g = lerp(132, 12, s);
      b = lerp(252, 28, s);
    }
    palette[i] = [r | 0, g | 0, b | 0];
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  // Interesting Mandelbrot locations to zoom into
  const targets = [
    { x: -0.7435669, y: 0.1314023, name: 'Seahorse valley' },
    { x: -0.1011, y: 0.9563, name: 'Spiral arm' },
    { x: -1.25066, y: 0.02012, name: 'Elephant valley' },
    { x: -0.235125, y: 0.827215, name: 'Double spiral' },
    { x: 0.360240443437614, y: -0.641313061064803, name: 'Mini Mandelbrot' },
  ];

  let targetIdx = Math.floor(Math.random() * targets.length);
  let target = targets[targetIdx];

  // Zoom state
  let zoom = 3.0;           // Start zoomed out (full set visible)
  const zoomSpeed = 0.9985; // Slow zoom per frame
  const maxZoom = 0.00001;  // How deep before we reset
  let cx = target.x;
  let cy = target.y;

  const maxIter = 80;
  const imgData = ctx.createImageData(W, H);
  const buf = imgData.data;

  let animId;
  let lastFrame = 0;
  const frameInterval = 50; // ~20fps to keep it chill

  function render(timestamp) {
    animId = requestAnimationFrame(render);

    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    const aspect = W / H;
    const halfW = zoom * 0.5;
    const halfH = halfW / aspect;
    const xMin = cx - halfW;
    const yMin = cy - halfH;
    const dx = zoom / W;
    const dy = (zoom / aspect) / H;

    for (let py = 0; py < H; py++) {
      const ci = yMin + py * dy;
      for (let px = 0; px < W; px++) {
        const cr = xMin + px * dx;
        let zr = 0, zi = 0;
        let iter = 0;

        while (zr * zr + zi * zi <= 4 && iter < maxIter) {
          const tmp = zr * zr - zi * zi + cr;
          zi = 2 * zr * zi + ci;
          zr = tmp;
          iter++;
        }

        const idx = (py * W + px) * 4;
        if (iter === maxIter) {
          // Inside the set — near-black
          buf[idx] = 10;
          buf[idx + 1] = 13;
          buf[idx + 2] = 20;
          buf[idx + 3] = 255;
        } else {
          // Smooth coloring
          const log2 = Math.log(2);
          const nu = Math.log(Math.log(zr * zr + zi * zi) / log2) / log2;
          const smooth = (iter + 1 - nu) / maxIter;
          const ci2 = ((smooth * 255 * 3) | 0) % 256;
          const c = palette[ci2];
          buf[idx] = c[0];
          buf[idx + 1] = c[1];
          buf[idx + 2] = c[2];
          buf[idx + 3] = 255;
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // Zoom in
    zoom *= zoomSpeed;

    // When zoomed in deep enough, pick a new target and zoom back out
    if (zoom < maxZoom) {
      targetIdx = (targetIdx + 1) % targets.length;
      target = targets[targetIdx];
      cx = target.x;
      cy = target.y;
      zoom = 3.0;
    }
  }

  // Only run when tab is visible
  function onVisibility() {
    if (document.hidden) {
      cancelAnimationFrame(animId);
    } else {
      animId = requestAnimationFrame(render);
    }
  }

  // Respect prefers-reduced-motion
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // Render a single frame and stop
    zoom = 2.5;
    render(0);
    cancelAnimationFrame(animId);
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    animId = requestAnimationFrame(render);
  }
})();
