// Lissajous curves — slowly drifting frequency ratios produce evolving knots
(function () {
  'use strict';

  const canvas = document.getElementById('fractal-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const W = 360;
  const H = 240;
  canvas.width = W;
  canvas.height = H;

  const trail = document.createElement('canvas');
  trail.width = W;
  trail.height = H;
  const tCtx = trail.getContext('2d');
  tCtx.fillStyle = 'rgb(10, 13, 20)';
  tCtx.fillRect(0, 0, W, H);

  // Multiple curves with slightly different parameters
  const curves = [
    { a: 3, b: 2, delta: 0, color: 'rgba(108, 140, 255, 0.4)', drift: 0.0007 },
    { a: 5, b: 4, delta: Math.PI / 4, color: 'rgba(34, 211, 238, 0.3)', drift: 0.0005 },
    { a: 7, b: 6, delta: Math.PI / 3, color: 'rgba(192, 132, 252, 0.3)', drift: 0.0009 },
  ];

  let time = 0;
  let animId;
  let lastFrame = 0;
  const frameInterval = 33;

  function render(timestamp) {
    animId = requestAnimationFrame(render);
    if (timestamp - lastFrame < frameInterval) return;
    lastFrame = timestamp;

    tCtx.fillStyle = 'rgba(10, 13, 20, 0.008)';
    tCtx.fillRect(0, 0, W, H);

    for (let c = 0; c < curves.length; c++) {
      const curve = curves[c];
      const a = curve.a + Math.sin(time * curve.drift * 10) * 0.5;
      const b = curve.b + Math.cos(time * curve.drift * 8) * 0.3;
      const delta = curve.delta + time * 0.02;

      tCtx.strokeStyle = curve.color;
      tCtx.lineWidth = 1;
      tCtx.beginPath();

      for (let t = 0; t < Math.PI * 2; t += 0.01) {
        const x = W / 2 + Math.sin(a * t + delta) * (W * 0.4);
        const y = H / 2 + Math.sin(b * t) * (H * 0.4);
        if (t === 0) tCtx.moveTo(x, y);
        else tCtx.lineTo(x, y);
      }
      tCtx.stroke();
    }

    time += 0.015;
    ctx.drawImage(trail, 0, 0);
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
