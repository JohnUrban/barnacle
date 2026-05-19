// Bay Ave Barnacle — client-side heat-map renderer (HANDOFF 9b.10).
//
// Renders a predicted-water-depth overlay onto a base map image. Pure
// function of (water level NAVD88 ft) + the static (x, y, elevation)
// map points + the base map image. No PNG storage in git: everything
// the page needs is text (one number + a CSV-like blob) and a static
// base image. The browser does the contouring.
//
// Algorithm:
//   1. Compute Delaunay triangulation of the surveyed map points
//      (each point: x, y in image pixel coords; elevation in ft NAVD88).
//   2. For each triangle: rasterize it pixel-by-pixel using barycentric
//      interpolation to get the elevation at each pixel.
//   3. depth(pixel) = max(0, water_level - elev). Color by depth using
//      a light→dark blue gradient with increasing opacity. Skip pixels
//      where depth <= 0 (dry).
//   4. Composite the overlay onto the base image.
//
// Dependency: d3-delaunay v6 (UMD, loaded by the host page from CDN).
//
// API:
//   window.BarnacleMap.render({
//     canvas: <HTMLCanvasElement>,
//     points: [{x: <px>, y: <px>, navd88: <ft>}, ...],
//     waterNavd88: <ft>,
//     baseMapUrl: '../icons/map_raw.png',
//     title: 'optional title',  // drawn on the canvas
//   })
//   .then(() => { /* render complete */ });

(function() {
  'use strict';

  // Cap the depth used for color saturation. A single very-low pocket
  // wouldn't otherwise let the rest of the gradient breathe.
  var MAX_DEPTH_FT = 2.0;

  // matplotlib Blues colormap, sampled. Each row [r, g, b]; alpha is
  // applied separately based on normalized depth.
  var BLUES = [
    [247, 251, 255], [222, 235, 247], [198, 219, 239],
    [158, 202, 225], [107, 174, 214], [66,  146, 198],
    [33,  113, 181], [8,   81,  156], [8,   48,  107]
  ];
  function depthToRGB(t) {
    // t in [0, 1]. Interpolate within BLUES.
    if (t <= 0) return BLUES[0];
    if (t >= 1) return BLUES[BLUES.length - 1];
    var f = t * (BLUES.length - 1);
    var lo = Math.floor(f);
    var hi = Math.min(lo + 1, BLUES.length - 1);
    var frac = f - lo;
    var a = BLUES[lo], b = BLUES[hi];
    return [
      Math.round(a[0] + (b[0] - a[0]) * frac),
      Math.round(a[1] + (b[1] - a[1]) * frac),
      Math.round(a[2] + (b[2] - a[2]) * frac)
    ];
  }

  function depthToAlpha(t) {
    // Alpha rises from 0 (dry edge) to ~0.85 (saturated deep).
    // Matches the matplotlib renderer's BluesAlpha colormap so the
    // client-side map looks like the existing pre-rendered PNGs.
    return Math.min(0.85, t * 0.85);
  }

  function loadImage(url) {
    return new Promise(function(resolve, reject) {
      var img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = function() { resolve(img); };
      img.onerror = function() { reject(new Error('Failed to load ' + url)); };
      img.src = url;
    });
  }

  function render(opts) {
    var canvas = opts.canvas;
    var points = opts.points || [];
    var waterNavd88 = opts.waterNavd88;
    var title = opts.title || '';

    if (points.length < 3) {
      return Promise.reject(new Error('Need at least 3 points for triangulation'));
    }
    if (typeof waterNavd88 !== 'number' || isNaN(waterNavd88)) {
      // No overlay — just draw the base image.
      return loadImage(opts.baseMapUrl).then(function(img) {
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        if (title) drawTitle(ctx, title, canvas.width);
      });
    }
    if (typeof d3 === 'undefined' || !d3.Delaunay) {
      return Promise.reject(new Error('d3-delaunay not loaded'));
    }

    return loadImage(opts.baseMapUrl).then(function(img) {
      var w = img.naturalWidth, h = img.naturalHeight;
      canvas.width = w;
      canvas.height = h;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);

      var imageData = ctx.getImageData(0, 0, w, h);
      var data = imageData.data;

      // Build Delaunay over (x, y) — d3-delaunay wants flat array.
      var coords = new Float64Array(points.length * 2);
      for (var i = 0; i < points.length; i++) {
        coords[i * 2]     = points[i].x;
        coords[i * 2 + 1] = points[i].y;
      }
      var delaunay = new d3.Delaunay(coords);
      var triangles = delaunay.triangles;  // Int32Array

      for (var ti = 0; ti < triangles.length; ti += 3) {
        var i0 = triangles[ti], i1 = triangles[ti + 1], i2 = triangles[ti + 2];
        var p0 = points[i0], p1 = points[i1], p2 = points[i2];

        // Triangle bounding box, clipped to canvas
        var minX = Math.max(0, Math.floor(Math.min(p0.x, p1.x, p2.x)));
        var maxX = Math.min(w - 1, Math.ceil(Math.max(p0.x, p1.x, p2.x)));
        var minY = Math.max(0, Math.floor(Math.min(p0.y, p1.y, p2.y)));
        var maxY = Math.min(h - 1, Math.ceil(Math.max(p0.y, p1.y, p2.y)));

        // Barycentric setup
        var denom = (p1.y - p2.y) * (p0.x - p2.x) +
                    (p2.x - p1.x) * (p0.y - p2.y);
        if (Math.abs(denom) < 1e-10) continue;

        for (var y = minY; y <= maxY; y++) {
          for (var x = minX; x <= maxX; x++) {
            var a = ((p1.y - p2.y) * (x - p2.x) +
                     (p2.x - p1.x) * (y - p2.y)) / denom;
            var b = ((p2.y - p0.y) * (x - p2.x) +
                     (p0.x - p2.x) * (y - p2.y)) / denom;
            var c = 1 - a - b;
            if (a < 0 || b < 0 || c < 0) continue;

            var elev = a * p0.navd88 + b * p1.navd88 + c * p2.navd88;
            var depthFt = waterNavd88 - elev;
            if (depthFt <= 0) continue;

            var t = Math.min(depthFt / MAX_DEPTH_FT, 1.0);
            var rgb = depthToRGB(t);
            var alpha = depthToAlpha(t);
            var idx = (y * w + x) * 4;
            data[idx]     = data[idx]     * (1 - alpha) + rgb[0] * alpha;
            data[idx + 1] = data[idx + 1] * (1 - alpha) + rgb[1] * alpha;
            data[idx + 2] = data[idx + 2] * (1 - alpha) + rgb[2] * alpha;
          }
        }
      }
      ctx.putImageData(imageData, 0, 0);
      if (title) drawTitle(ctx, title, w);
    });
  }

  function drawTitle(ctx, text, width) {
    ctx.save();
    ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
    ctx.fillRect(0, 0, width, 30);
    ctx.fillStyle = '#222';
    ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    ctx.fillText(text, width / 2, 15);
    ctx.restore();
  }

  // Public API
  window.BarnacleMap = { render: render };
})();
