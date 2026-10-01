'use strict';
// Collapsing main navigation.
//
// Twelve nav items do not fit one row below 1062px (measured); the breakpoint
// is 1150px to leave room for a client that falls back to a wider font. The header is a fixed
// height, so wrapping pushed a row outside it; below the breakpoint the links
// live in a panel behind a button instead.
//
// The panel is closed by CSS (`display:none`) and opened by a class, so with
// JavaScript unavailable the button is simply never shown and the links render
// as the normal row — which is the pre-existing behaviour, not a regression.
(function () {
  const toggle = document.getElementById('nav-toggle');
  const panel = document.getElementById('site-nav-links');
  if (!toggle || !panel) return;

  const open = () => {
    panel.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
  };
  const close = () => {
    panel.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  };
  const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';

  toggle.addEventListener('click', e => {
    e.stopPropagation();
    isOpen() ? close() : open();
  });

  // Following a link should not leave the panel covering the page it lands on.
  panel.addEventListener('click', e => { if (e.target.closest('a')) close(); });

  document.addEventListener('click', e => {
    if (isOpen() && !panel.contains(e.target) && e.target !== toggle) close();
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && isOpen()) { close(); toggle.focus(); }
  });

  // Returning to a width where the links fit must not leave the panel latched
  // open, or the class would show it as a dropdown over a nav that is already
  // visible.
  matchMedia('(max-width: 1150px)').addEventListener('change', e => {
    if (!e.matches) close();
  });
})();
