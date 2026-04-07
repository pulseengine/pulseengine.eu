// Background dispatcher — picks a random renderer on each page load
(function () {
  'use strict';

  var backgrounds = [
    'mandelbrot.js',
    'bg-julia.js',
    'bg-reaction-diffusion.js',
    'bg-flowfield.js',
    'bg-lorenz.js',
    'bg-waves.js',
    'bg-contours.js',
    'bg-life.js',
    'bg-lissajous.js',
    'bg-sierpinski.js',
    'bg-domain.js',
  ];

  var pick = backgrounds[Math.floor(Math.random() * backgrounds.length)];

  // Resolve path relative to this script's location
  var scripts = document.getElementsByTagName('script');
  var thisScript = scripts[scripts.length - 1];
  var basePath = thisScript.src.substring(0, thisScript.src.lastIndexOf('/') + 1);

  var script = document.createElement('script');
  script.src = basePath + pick;
  document.body.appendChild(script);
})();
