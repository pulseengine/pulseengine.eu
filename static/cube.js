// Rubik's cube — drag to rotate, auto-spin, snap + zoom + open
(function () {
  'use strict';

  var cube = document.querySelector('.cube');
  if (!cube) return;

  var scene = document.querySelector('.cube-scene');
  var detailPanel = document.querySelector('.cube-detail');
  var snaps = document.querySelectorAll('[data-face]');
  var closeBtn = document.querySelector('.cube-detail__close');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var rotX = -30, rotY = 35;
  var dragging = false;
  var lastX, lastY;
  var autoSpin = true;
  var idleTimer;
  var activeFace = null;
  var introPhase = true;
  var introStart = performance.now();

  var angles = {
    architect: [0, 0],
    build:     [0, -90],
    verify:    [0, 90],
    trace:     [0, 180],
    run:       [-90, 0],
    agent:     [90, 0]
  };

  function apply() {
    cube.style.transform = 'rotateX(' + rotX + 'deg) rotateY(' + rotY + 'deg)';
  }

  function stopAuto() {
    introPhase = false;
    scene.style.transform = 'scale(1)';
    autoSpin = false;
    clearTimeout(idleTimer);
    idleTimer = setTimeout(function () {
      if (!activeFace) autoSpin = true;
    }, 4000);
  }

  // ── Auto-rotation with intro animation ───────
  function spin() {
    if (dragging || reduceMotion) {
      requestAnimationFrame(spin);
      return;
    }

    if (introPhase) {
      var elapsed = (performance.now() - introStart) / 1000;
      var dur = 1.8;

      if (elapsed < dur) {
        var t = elapsed / dur;
        var scale, spinSpeed;

        if (t < 0.15) {
          // Phase 1: 1.0 → 0.3 (snap contract)
          var p = t / 0.15;
          scale = 1.0 - 0.7 * p * p;
          spinSpeed = 0.2;
        } else if (t < 0.4) {
          // Phase 2: 0.3 → 10.0 (explode)
          var p = (t - 0.15) / 0.25;
          var ease = 1 - Math.pow(1 - p, 2);
          scale = 0.3 + 9.7 * ease;
          spinSpeed = 1.2 * ease + 0.2;
        } else {
          // Phase 3: 10.0 → 1.0 (settle)
          var p = (t - 0.4) / 0.6;
          var ease = 1 - Math.pow(1 - p, 4);
          scale = 10.0 - 9.0 * ease;
          spinSpeed = 1.2 * (1 - ease) + 0.08;
        }

        scene.style.transform = 'scale(' + scale + ')';
        rotY += spinSpeed;
        apply();
        requestAnimationFrame(spin);
        return;
      } else {
        introPhase = false;
        scene.style.transform = 'scale(1)';
      }
    }

    if (!autoSpin) {
      requestAnimationFrame(spin);
      return;
    }

    rotY += 0.08;
    apply();
    requestAnimationFrame(spin);
  }

  // ── Drag (mouse) ─────────────────────────────
  scene.addEventListener('mousedown', function (e) {
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    scene.style.cursor = 'grabbing';
    stopAuto();
  });
  window.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    rotY += (e.clientX - lastX) * 0.4;
    rotX -= (e.clientY - lastY) * 0.4;
    lastX = e.clientX;
    lastY = e.clientY;
    apply();
  });
  window.addEventListener('mouseup', function () {
    dragging = false;
    scene.style.cursor = 'grab';
  });

  // ── Drag (touch) ─────────────────────────────
  scene.addEventListener('touchstart', function (e) {
    if (e.touches.length === 1) {
      dragging = true;
      lastX = e.touches[0].clientX;
      lastY = e.touches[0].clientY;
      stopAuto();
    }
  }, { passive: true });
  window.addEventListener('touchmove', function (e) {
    if (!dragging || e.touches.length !== 1) return;
    rotY += (e.touches[0].clientX - lastX) * 0.4;
    rotX -= (e.touches[0].clientY - lastY) * 0.4;
    lastX = e.touches[0].clientX;
    lastY = e.touches[0].clientY;
    apply();
  }, { passive: true });
  window.addEventListener('touchend', function () { dragging = false; });

  // ── Open a face ──────────────────────────────
  function openFace(face) {
    activeFace = face;
    autoSpin = false;

    // Set target rotation
    var a = angles[face];
    rotX = a[0];
    rotY = a[1];

    // Prep detail content
    if (detailPanel) {
      detailPanel.querySelectorAll('.cube-detail__panel').forEach(function (p) {
        p.style.display = (p.getAttribute('data-detail') === face) ? 'block' : 'none';
      });
    }

    if (reduceMotion) {
      // Honor prefers-reduced-motion: snap to target rotation, no zoom/rotate animations.
      cube.style.transition = 'none';
      scene.style.transition = 'none';
      apply();
      if (detailPanel) detailPanel.classList.add('cube-detail--open');
      return;
    }

    // Animate: rotate the cube
    cube.style.transition = 'transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
    apply();

    // After rotate: zoom out
    setTimeout(function () {
      scene.style.transform = 'scale(0.55)';
    }, 300);

    // After zoom: show detail
    setTimeout(function () {
      cube.style.transition = 'none';
      if (detailPanel) detailPanel.classList.add('cube-detail--open');
    }, 700);
  }

  function closeFace() {
    activeFace = null;

    // Hide detail
    if (detailPanel) detailPanel.classList.remove('cube-detail--open');

    // Return to isometric
    rotX = -30;
    rotY = 35;

    if (reduceMotion) {
      cube.style.transition = 'none';
      scene.style.transition = 'none';
      scene.style.transform = 'scale(1)';
      apply();
      autoSpin = true;
      snaps.forEach(function (b) { b.classList.remove('face-btn--active'); });
      return;
    }

    // Zoom back in
    scene.style.transform = 'scale(1)';

    cube.style.transition = 'transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
    apply();

    setTimeout(function () {
      cube.style.transition = 'none';
      autoSpin = true;
    }, 600);

    snaps.forEach(function (b) { b.classList.remove('face-btn--active'); });
  }

  // ── Button clicks ────────────────────────────
  snaps.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var face = btn.getAttribute('data-face');
      if (!angles[face]) return;

      if (activeFace === face) {
        closeFace();
        return;
      }

      // If switching from another face, close first then open
      if (activeFace) {
        if (detailPanel) detailPanel.classList.remove('cube-detail--open');
      }

      snaps.forEach(function (b) { b.classList.remove('face-btn--active'); });
      btn.classList.add('face-btn--active');
      openFace(face);
    });
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', closeFace);
  }

  // ── Click on cube faces ───────────────────────
  var faceMap = {
    'cube__face--front':  'architect',
    'cube__face--right':  'build',
    'cube__face--left':   'verify',
    'cube__face--back':   'trace',
    'cube__face--top':    'run',
    'cube__face--bottom': 'agent'
  };

  var faces = cube.querySelectorAll('.cube__face');
  faces.forEach(function (face) {
    face.addEventListener('click', function (e) {
      // Don't trigger on drag
      if (dragging) return;

      // Find which face this is
      var faceName = null;
      for (var cls in faceMap) {
        if (face.classList.contains(cls)) {
          faceName = faceMap[cls];
          break;
        }
      }
      if (!faceName || !angles[faceName]) return;

      // Prevent the GitHub link from firing
      e.preventDefault();
      e.stopPropagation();

      if (activeFace === faceName) {
        closeFace();
        return;
      }

      if (activeFace) {
        if (detailPanel) detailPanel.classList.remove('cube-detail--open');
      }

      snaps.forEach(function (b) { b.classList.remove('face-btn--active'); });
      // Also highlight the matching top button
      snaps.forEach(function (b) {
        if (b.getAttribute('data-face') === faceName) b.classList.add('face-btn--active');
      });

      openFace(faceName);
    });

    // Prevent links inside cube faces from navigating
    face.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function (e) {
        if (!activeFace) {
          e.preventDefault();
        }
        // If detail is already open, allow links (they're decoration anyway)
      });
    });
  });

  // ── Init ─────────────────────────────────────
  scene.style.transform = 'scale(1)';
  scene.style.transition = 'transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
  apply();
  if (!reduceMotion) requestAnimationFrame(spin);
})();
