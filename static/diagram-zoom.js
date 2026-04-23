// Click-to-zoom for diagrams in blog posts.
// Uses event delegation on .blog-post__content so Mermaid's async-rendered
// SVGs work without needing to re-attach handlers.
// Modal supports wheel zoom, drag pan, ESC/backdrop close.
(function () {
  'use strict';

  var postContent = document.querySelector('.blog-post__content');
  if (!postContent) return;

  var MIN_SCALE = 0.25;
  var MAX_SCALE = 10;

  var modal = null;
  var stage = null;
  var state = { scale: 1, x: 0, y: 0 };
  var drag = null;

  function apply() {
    if (!stage || !stage.firstElementChild) return;
    stage.firstElementChild.style.transform =
      'translate(' + state.x + 'px, ' + state.y + 'px) scale(' + state.scale + ')';
  }

  function makeEl(tag, cls, attrs) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) el.setAttribute(k, attrs[k]);
      }
    }
    return el;
  }

  function createModal() {
    modal = makeEl('div', 'diagram-modal', {
      role: 'dialog',
      'aria-modal': 'true',
      'aria-label': 'Zoomed diagram',
    });

    var closeBtn = makeEl('button', 'diagram-modal__close', {
      type: 'button',
      'aria-label': 'Close zoomed diagram',
    });
    closeBtn.textContent = '×';

    var hint = makeEl('div', 'diagram-modal__hint');
    hint.textContent = 'scroll to zoom · drag to pan · ESC to close';

    stage = makeEl('div', 'diagram-modal__stage', { role: 'presentation' });

    modal.appendChild(closeBtn);
    modal.appendChild(hint);
    modal.appendChild(stage);

    modal.addEventListener('click', function (e) {
      if (e.target === modal) close();
    });
    closeBtn.addEventListener('click', close);

    modal.addEventListener('wheel', function (e) {
      e.preventDefault();
      var factor = e.deltaY < 0 ? 1.18 : 1 / 1.18;
      var next = state.scale * factor;
      if (next < MIN_SCALE) next = MIN_SCALE;
      if (next > MAX_SCALE) next = MAX_SCALE;
      state.scale = next;
      apply();
    }, { passive: false });

    stage.addEventListener('pointerdown', function (e) {
      drag = { x: e.clientX, y: e.clientY, ox: state.x, oy: state.y };
      try { stage.setPointerCapture(e.pointerId); } catch (_) {}
      stage.style.cursor = 'grabbing';
    });
    stage.addEventListener('pointermove', function (e) {
      if (!drag) return;
      state.x = drag.ox + (e.clientX - drag.x);
      state.y = drag.oy + (e.clientY - drag.y);
      apply();
    });
    var endDrag = function () {
      drag = null;
      if (stage) stage.style.cursor = 'grab';
    };
    stage.addEventListener('pointerup', endDrag);
    stage.addEventListener('pointercancel', endDrag);

    document.body.appendChild(modal);
  }

  function open(svg) {
    if (!modal) createModal();
    var clone = svg.cloneNode(true);
    clone.removeAttribute('width');
    clone.removeAttribute('height');
    clone.style.transformOrigin = 'center center';
    clone.style.transition = 'none';
    clone.style.maxWidth = '100%';
    clone.style.maxHeight = '100%';
    while (stage.firstChild) stage.removeChild(stage.firstChild);
    stage.appendChild(clone);
    state = { scale: 1, x: 0, y: 0 };
    apply();
    modal.classList.add('is-open');
    document.body.classList.add('diagram-modal-open');
  }

  function close() {
    if (!modal) return;
    modal.classList.remove('is-open');
    document.body.classList.remove('diagram-modal-open');
    while (stage.firstChild) stage.removeChild(stage.firstChild);
  }

  // Event delegation: one click handler on the post content,
  // catches any SVG (including Mermaid's async renders) and any
  // .diagram-zoomable element (e.g. table wrappers).
  postContent.addEventListener('click', function (e) {
    // Respect nested anchors (bespoke SVGs like pipeline.html)
    if (e.target.closest && e.target.closest('a[href]')) return;

    var target = null;
    if (e.target.closest) {
      target = e.target.closest('svg');
      if (!target) target = e.target.closest('.diagram-zoomable');
    }
    if (!target) return;

    // If the zoomable element is a container (e.g. table wrapper), find its
    // SVG child if any; otherwise zoom the container itself.
    var inner = target.tagName === 'svg' ? target : (target.querySelector('svg') || target);
    e.preventDefault();
    open(inner);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
})();
