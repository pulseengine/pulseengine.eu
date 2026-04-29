// Theme toggle — clicking the button cycles light ↔ dark and persists
// the choice in localStorage. The bootstrapper in <head> already
// applied the saved preference before render, so this script only
// needs to handle the click and the post-load attribute update.
//
// Resolution order on each click:
//   1. If data-theme is currently "dark" → switch to "light"
//   2. Else (data-theme="light", or unset and OS-prefers-light, or unset
//      and OS-prefers-dark) → switch to "dark"
// In other words: click always inverts the *currently rendered* theme,
// then pins that choice in localStorage so the OS preference no longer
// auto-applies.

(function () {
  'use strict';

  var STORAGE_KEY = 'pulseengine-theme';
  var btn = document.querySelector('.theme-toggle');
  if (!btn) return;

  function currentTheme() {
    var explicit = document.documentElement.getAttribute('data-theme');
    if (explicit === 'light' || explicit === 'dark') return explicit;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  }

  // Sync ARIA state to the rendered theme. aria-pressed="true" when light
  // is active (the non-default state); aria-label describes what the click
  // would *do*, which is what screen readers announce.
  function syncAria() {
    var theme = currentTheme();
    btn.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
    btn.setAttribute(
      'aria-label',
      theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'
    );
  }

  syncAria();

  btn.addEventListener('click', function () {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* private mode */ }
    syncAria();
  });
})();
