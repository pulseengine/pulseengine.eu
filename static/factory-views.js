// Stacked views of one factory (#194).
//
// Deliberately NOT cube.js: that is 308 lines of 3D transform, pointer drag and
// touch handling for the Projects cube. This is the same [data-view] / panel
// idiom with none of the geometry — switching a layer, not rotating a solid.
//
// The chosen view lives in the URL hash so a view is linkable: someone arguing
// about the supply chain can send #view=use directly.
(function () {
  var root = document.getElementById('fviews');
  if (!root) return;

  var btns = root.querySelectorAll('[data-view]');
  var panels = root.querySelectorAll('[data-panel]');

  function show(name) {
    var found = false;
    panels.forEach(function (p) {
      var on = p.getAttribute('data-panel') === name;
      // setAttribute, NOT `p.hidden = ...`: `hidden` is an IDL property of
      // HTMLElement, and these panels are SVGElement. Assigning the property
      // on an SVG element sets an inert JS field and never reflects to the
      // attribute, so the CSS never sees it — the nav updated and the picture
      // did not.
      if (on) { p.removeAttribute('hidden'); found = true; }
      else { p.setAttribute('hidden', ''); }
    });
    if (!found) return false;
    btns.forEach(function (b) {
      var on = b.getAttribute('data-view') === name;
      b.classList.toggle('fviews__btn--on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    return true;
  }

  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      var name = b.getAttribute('data-view');
      if (show(name)) history.replaceState(null, '', '#view=' + name);
    });
  });

  // Deep link, and keep working if the hash names a view that no longer exists.
  var m = /(?:^|#|&)view=([a-z]+)/.exec(location.hash);
  if (m) show(m[1]);
})();
