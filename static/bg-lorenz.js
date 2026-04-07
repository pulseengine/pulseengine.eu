// Lorenz strange attractor — glowing chaotic orbit traces
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const W = 360;
  const H = 240;
  canvas.width = W;
  canvas.height = H;

  // Trail canvas
  const trail = document.createElement('canvas');
  trail.width = W;
  trail.height = H;
  const tCtx = trail.getContext('2d');
  tCtx.fillStyle = 'rgb(10, 13, 20)';
  tCtx.fillRect(0, 0, W, H);

  // Lorenz parameters
  const sigma = 10;
  const rho = 28;
  const beta = 8 / 3;
  const dt = 0.005;

  // Multiple traces for richer visual
  const traces = [];
  for (let i = 0; i < 3; i++) {
    traces.push({
      x: 1 + Math.random() * 0.1,
      y: 1 + Math.random() * 0.1,
      z: 1 + Math.random() * 0.1,
      color: [
        [108, 140, 255],
        [34, 211, 238],
        [192, 132, 252],
      ][i],
    });
  }

  // Project 3D → 2D (simple orthographic, rotated slowly)
  let angle = 0;

  function project(x, y, z) {
    const ca = Math.cos(angle);
    const sa = Math.sin(angle);
    const rx = x * ca - y * sa;
    const ry = x * sa + y * ca;
    // Scale and center
    return {
      px: W / 2 + rx * 5.5,
      py: H / 2 - z * 3.5 + 70,
    };
  }

  let animId;
  let lastFrame = 0;
  const frameInterval = 33;

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    // Fade trails
    tCtx.fillStyle = 'rgba(10, 13, 20, 0.015)';
    tCtx.fillRect(0, 0, W, H);

    for (let t = 0; t < traces.length; t++) {
      const tr = traces[t];
      const p1 = project(tr.x, tr.y, tr.z);

      // Integrate 4 steps per frame
      for (let s = 0; s < 4; s++) {
        const dx = sigma * (tr.y - tr.x) * dt;
        const dy = (tr.x * (rho - tr.z) - tr.y) * dt;
        const dz = (tr.x * tr.y - beta * tr.z) * dt;
        tr.x += dx;
        tr.y += dy;
        tr.z += dz;
      }

      const p2 = project(tr.x, tr.y, tr.z);

      tCtx.strokeStyle = 'rgba(' + tr.color[0] + ',' + tr.color[1] + ',' + tr.color[2] + ', 0.5)';
      tCtx.lineWidth = 1;
      tCtx.beginPath();
      tCtx.moveTo(p1.px, p1.py);
      tCtx.lineTo(p2.px, p2.py);
      tCtx.stroke();
    }

    angle += 0.0003;
    ctx.drawImage(trail, 0, 0);
  }

  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(animId); }
    else { animId = requestAnimationFrame(render); }
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    for (let i = 0; i < 500; i++) render(i * frameInterval);
    cancelAnimationFrame(animId);
  } else {
    document.addEventListener('visibilitychange', onVisibility);
    animId = requestAnimationFrame(render);
  }
})();
