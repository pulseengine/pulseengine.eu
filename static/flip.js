// Flip cards — click to toggle
(function () {
  'use strict';
  document.querySelectorAll('.flip-card').forEach(function (card) {
    card.addEventListener('click', function (e) {
      // Don't flip if clicking a link on the back
      if (e.target.tagName === 'A') return;
      card.classList.toggle('flipped');
    });
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        card.classList.toggle('flipped');
      }
    });
  });
})();
