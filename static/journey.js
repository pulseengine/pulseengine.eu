// Journey — path selection + fuse animation + scroll reveals
(function () {
  'use strict';

  var journey = document.getElementById('journey');
  if (!journey) return;

  var fuseFill = journey.querySelector('.fuse__fill');
  var steps = journey.querySelectorAll('.journey__step');
  var nodes = journey.querySelectorAll('.fuse__node');
  var pathBtns = document.querySelectorAll('.paths__btn');
  var activePath = null;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // -- Path selection --
  pathBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var path = btn.getAttribute('data-path');

      // Toggle
      if (activePath === path) {
        activePath = null;
        pathBtns.forEach(function (b) { b.classList.remove('paths__btn--active'); });
      } else {
        activePath = path;
        pathBtns.forEach(function (b) {
          b.classList.toggle('paths__btn--active', b.getAttribute('data-path') === path);
        });
      }

      updateVisibility();

      // Scroll to journey
      journey.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  });

  function updateVisibility() {
    steps.forEach(function (step) {
      var paths = step.getAttribute('data-paths');
      var isRelevant = !activePath || paths === 'all' || paths.indexOf(activePath) !== -1;

      step.classList.toggle('journey__step--dim', !isRelevant && !!activePath);

      // Show/hide expanded content
      var expands = step.querySelectorAll('.journey__expand');
      expands.forEach(function (ex) {
        var showFor = ex.getAttribute('data-show');
        ex.style.display = (activePath === showFor) ? 'block' : 'none';
      });
    });
  }

  // Initial state — hide all expands
  updateVisibility();

  // -- Fuse fill on scroll --
  function updateFuse() {
    var rect = journey.getBoundingClientRect();
    var journeyTop = rect.top;
    var journeyHeight = rect.height;
    var viewportHeight = window.innerHeight;

    // How far through the journey are we?
    var progress = Math.max(0, Math.min(1,
      (viewportHeight - journeyTop) / (journeyHeight + viewportHeight * 0.5)
    ));

    if (fuseFill) {
      fuseFill.style.transform = 'scaleY(' + progress + ')';
    }

    // Light up nodes
    nodes.forEach(function (node) {
      var nodeRect = node.getBoundingClientRect();
      var nodeCenter = nodeRect.top + nodeRect.height / 2;
      node.classList.toggle('fuse__node--lit', nodeCenter < viewportHeight * 0.6);
    });
  }

  // -- Reveal on scroll --
  var reveals = document.querySelectorAll('.reveal');

  if (reduceMotion) {
    reveals.forEach(function (el) { el.classList.add('visible'); });
  }

  var revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' });

  reveals.forEach(function (el) { revealObserver.observe(el); });

  // Scroll handler (throttled)
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (!ticking) {
      requestAnimationFrame(function () {
        updateFuse();
        ticking = false;
      });
      ticking = true;
    }
  });
  updateFuse();
})();
