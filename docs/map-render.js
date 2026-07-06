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

  // Post-render Gaussian blur applied to the overlay layer only (NOT
  // the base map). A light touch — just enough to soften the
  // triangle-edge "spoke" creases and the angular flood boundary so
  // the overlay reads more like water and less like a faceted mesh.
  // User-evaluated 2026-05-19: radius 7 (at the base image's native
  // ~1966 px width) was the sweet spot — 12+ started looking mushy.
  // Set to 0 to disable.
  var OVERLAY_BLUR_PX = 7;

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
    // Alpha floor (2026-07-06, user: "I always wish the water was
    // more obvious sooner — it might start out too transparent"):
    // any wet pixel is immediately ~0.38 opaque, ramping to 0.85.
    if (t <= 0) return 0;
    return Math.min(0.85, 0.38 + t * 0.47);
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

      // Render the depth overlay into its OWN transparent buffer
      // (not composited onto the base yet). This lets us blur the
      // overlay layer in isolation before compositing — the base map
      // stays crisp. `data` is RGBA, all-zero (fully transparent) to
      // start.
      var imageData = ctx.createImageData(w, h);
      var data = imageData.data;

      // EE — perf. Pre-compute a 256-entry (r, g, b, alpha) lookup
      // table for depth fractions in [0, 1]. The hot inner loop now
      // does one table lookup per pixel instead of two function calls.
      var LUT_SIZE = 256;
      var lutR = new Uint8Array(LUT_SIZE);
      var lutG = new Uint8Array(LUT_SIZE);
      var lutB = new Uint8Array(LUT_SIZE);
      var lutA = new Float32Array(LUT_SIZE);
      for (var ii = 0; ii < LUT_SIZE; ii++) {
        var tt = ii / (LUT_SIZE - 1);
        // Color ramp starts 25% into the Blues map (matching
        // render_map.py's linspace(0.25, 1.0)) so shallow water is
        // clearly BLUE, not near-white (same 2026-07-06 request).
        var rgb_i = depthToRGB(0.25 + 0.75 * tt);
        lutR[ii] = rgb_i[0];
        lutG[ii] = rgb_i[1];
        lutB[ii] = rgb_i[2];
        lutA[ii] = depthToAlpha(tt);
      }

      // EE — boundary smoothing. Add 8 "phantom" high-elevation points
      // around the bbox of the real points so the Delaunay extends past
      // the input set. The phantom elevation (6.0 NAVD88) is above any
      // realistic forecast water level, so these points contribute no
      // depth and never make the overlay where they alone are involved —
      // BUT the triangles they form with real points soften the chunky
      // straight-line convex hull that was previously the visible
      // boundary of the overlay. The zero-depth contour smooths out.
      var minX0 = Infinity, maxX0 = -Infinity, minY0 = Infinity, maxY0 = -Infinity;
      for (var i = 0; i < points.length; i++) {
        if (points[i].x < minX0) minX0 = points[i].x;
        if (points[i].x > maxX0) maxX0 = points[i].x;
        if (points[i].y < minY0) minY0 = points[i].y;
        if (points[i].y > maxY0) maxY0 = points[i].y;
      }
      var bboxW = maxX0 - minX0;
      var bboxH = maxY0 - minY0;
      var pad = 0.15;  // 15% of bbox dimension
      var px0 = minX0 - bboxW * pad;
      var px1 = maxX0 + bboxW * pad;
      var py0 = minY0 - bboxH * pad;
      var py1 = maxY0 + bboxH * pad;
      var phantomElev = 6.0;  // well above any realistic water level
      var allPoints = points.slice();
      [
        [px0, py0], [(px0 + px1) / 2, py0], [px1, py0],
        [px1, (py0 + py1) / 2],
        [px1, py1], [(px0 + px1) / 2, py1], [px0, py1],
        [px0, (py0 + py1) / 2]
      ].forEach(function(pt) {
        allPoints.push({ x: pt[0], y: pt[1], navd88: phantomElev });
      });

      // Build Delaunay over (x, y) — d3-delaunay wants flat array.
      var coords = new Float64Array(allPoints.length * 2);
      for (var i = 0; i < allPoints.length; i++) {
        coords[i * 2]     = allPoints[i].x;
        coords[i * 2 + 1] = allPoints[i].y;
      }
      var delaunay = new d3.Delaunay(coords);
      var triangles = delaunay.triangles;  // Int32Array
      // Use the augmented point set for the rest of the algorithm
      points = allPoints;

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

            var t = depthFt / MAX_DEPTH_FT;
            if (t > 1) t = 1;
            var li = (t * (LUT_SIZE - 1)) | 0;  // bitwise OR for fast trunc
            var idx = (y * w + x) * 4;
            // Write the RAW overlay color + alpha into the separate
            // buffer (no compositing here — that happens after blur).
            data[idx]     = lutR[li];
            data[idx + 1] = lutG[li];
            data[idx + 2] = lutB[li];
            data[idx + 3] = (lutA[li] * 255) | 0;
          }
        }
      }

      // Composite the overlay onto the base map. When OVERLAY_BLUR_PX
      // > 0, route the overlay through an offscreen canvas and draw it
      // back with a Gaussian blur filter so the triangle-edge creases
      // and angular flood boundary soften into something water-like.
      // The base map (already drawn above) is untouched by the blur.
      if (OVERLAY_BLUR_PX > 0) {
        var off = document.createElement('canvas');
        off.width = w;
        off.height = h;
        off.getContext('2d').putImageData(imageData, 0, 0);
        ctx.save();
        ctx.filter = 'blur(' + OVERLAY_BLUR_PX + 'px)';
        ctx.drawImage(off, 0, 0);
        ctx.restore();
      } else {
        // No blur — composite the overlay directly. putImageData
        // would overwrite the base, so go through drawImage too.
        var off0 = document.createElement('canvas');
        off0.width = w;
        off0.height = h;
        off0.getContext('2d').putImageData(imageData, 0, 0);
        ctx.drawImage(off0, 0, 0);
      }
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
