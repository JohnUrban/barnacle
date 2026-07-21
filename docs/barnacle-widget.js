// Bay Ave Barnacle — iOS home-screen widget for Scriptable
// HANDOFF item 27, Stage 2
//
// =====================  INSTALL  =====================
// 1. Install the free "Scriptable" app from the App Store.
// 2. On your iPhone, open Safari and visit:
//      https://johnurban.github.io/barnacle/barnacle-widget.js
// 3. Tap Share → Copy. (Or: select all the text and copy.)
// 4. Open Scriptable, tap the + in the upper right, paste this code,
//    tap Save (or the back arrow), and rename the script to "Barnacle".
// 5. Long-press an empty spot on your home screen → tap + (top-left) →
//    search "Scriptable" → choose the size (small or medium).
// 6. Add to home screen. Once placed, tap the widget once to edit it,
//    set Script: Barnacle. Tap outside to confirm.
//
// Widget refreshes itself every ~15 min (or sooner if iOS feels like
// it). To force a refresh, edit the widget and tap "Done" again.
//
// =====================  WHAT IT SHOWS  =====================
// Small widget (2x2):     regime label, peak forecast + time,
//                         hours-to-peak, highest exceeded landmark
//                         (or rel-to-lowest when no landmark exceeded),
//                         cold-conditions advisory pip if applicable.
// Medium widget (4x2):    same as small on the left; right side is a
//                         24-hour model-predicted water-level curve
//                         (v0.8 tide+surge series) with reference
//                         lines at the lowest grate (first water) and
//                         the curb (flood onset), plus a "now" marker.
//
// Source data: https://johnurban.github.io/barnacle/forecast.json
// Refreshed each hourly GitHub Actions workflow run (HANDOFF 9b.1).
//
// Updated 2026-07-06 (several passes): v0.9 landmark set (18, incl.
// porch ladder), enhancement 0.00, "dry" displays as "NO FLOODING",
// tide-curve chart fed by water_series, and a pluvial (rain-driven)
// flood-risk line — rain floods this intersection independent of the
// tide, so the tide-keyed regime label alone can mislead.

// WIDGET_VERSION: bump on every edit — shows in the widget footer so
// you can verify which copy is installed (CDN caches the .js ~10 min
// after a push; if the version below doesn't match the repo, re-copy).
const WIDGET_VERSION = "v7.22a";
const NOWCAST_URL = "https://johnurban.github.io/barnacle/nowcast.json";
const FORECAST_URL = "https://johnurban.github.io/barnacle/forecast.json";

// Landmark elevations (NAVD88). Match flood_forecast_daily.py LANDMARKS
// (v0.9, 18 landmarks). Ascending elevation; highestExceeded scans in
// order so the last exceeded entry wins.
const LANDMARKS = [
  ["grate_SW",                          "SW grate",       3.52],
  ["grate_SE",                          "SE grate",       3.60],
  ["corner_SE",                         "SE corner",      3.64],
  ["corner_SW",                         "SW corner",      3.64],
  ["grate_bay_ave_upstream",            "Upstream grate", 3.64],
  ["gutter_walkway",                    "Gutter",         3.78],
  ["grate_NE",                          "NE grate",       3.80],
  ["grate_NW",                          "NW grate",       3.80],
  ["corner_NE",                         "NE corner",      3.91],
  ["corner_NW",                         "NW corner",      3.91],
  ["curb",                              "Curb",           4.16],
  ["sidewalk_under_walkway_lawn_step",  "Sidewalk",       4.33],
  ["road_middle",                       "Road middle",    4.36],
  ["intersection_highpoint",            "Intersection",   4.54],
  ["lawn_step",                         "Lawn step",      4.66],
  ["porch_step_base",                   "Porch base",     4.68],
  ["porch_step1_top",                   "Porch step 1",   5.41],
  ["porch_deck",                        "Porch deck",     8.08],
];
const LOWEST_ELEV = 3.52;      // grate_SW — first water appears here
const CURB_ELEV   = 4.16;      // flood onset at the property
const LOCAL_ENHANCEMENT = 0.00;  // v0.8+
const MLLW_TO_NAVD88 = -2.82;

// Background + text colors per regime, matching the email/Pages CSS.
// Keys are the INTERNAL regime names (frozen in the data); display
// labels come from REGIME_DISPLAY below.
const REGIME_STYLES = {
  dry:          { bg: "#e8f5e9", text: "#2f6f47" },
  street:       { bg: "#e3f2fd", text: "#1565c0" },
  light:        { bg: "#fff8e1", text: "#8a6d3b" },
  moderate:     { bg: "#ffe0b2", text: "#b45f00" },
  severe:       { bg: "#ffcdd2", text: "#b33c3c" },
  cold_lockout: { bg: "#eceff1", text: "#455a64" },
};
// "DRY" reads ridiculous on rainy no-flood days; show what we mean.
const REGIME_DISPLAY = {
  dry: "NO FLOODING",
  cold_lockout: "COLD LOCKOUT",
};
function regimeDisplay(regime) {
  return REGIME_DISPLAY[regime] || regime.toUpperCase();
}

// ---- helpers ----
function formatTimeShort(s) {
  // "2026-05-18 21:58" -> "Mon 9:58 PM"
  const m = s && s.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
  if (!m) return s || "";
  const [, y, mo, d, h, mi] = m.map(Number);
  const date = new Date(y, mo - 1, d, h, mi);
  const wday = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][date.getDay()];
  const ampm = h >= 12 ? "PM" : "AM";
  const hr12 = (h % 12) || 12;
  return `${wday} ${hr12}:${String(mi).padStart(2,"0")} ${ampm}`;
}

function parseLocal(s) {
  const m = s && s.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
  if (!m) return null;
  const [, y, mo, d, h, mi] = m.map(Number);
  return new Date(y, mo - 1, d, h, mi);
}

function highestExceeded(depths) {
  let result = null;
  for (const [key, label, elev] of LANDMARKS) {
    if ((depths[key] || 0) > 0) {
      result = { key, label, elev, depth: depths[key] };
    }
  }
  return result;
}

function relativeToLowest(forecastPeakMLLW) {
  // Mirror the v0.8 model: water_navd88 = SH + 0.00 - 2.82
  const waterNAVD88 = forecastPeakMLLW + LOCAL_ENHANCEMENT + MLLW_TO_NAVD88;
  return (waterNAVD88 - LOWEST_ELEV) * 12;
}

function hoursToPeak(peakTimeStr) {
  const peak = parseLocal(peakTimeStr);
  if (!peak) return null;
  return (peak - new Date()) / 3600000;
}

function formatHoursToPeak(hours) {
  if (hours == null || isNaN(hours)) return "";
  const abs = Math.abs(hours);
  if (abs < 1) return `${Math.round(abs * 60)} min ${hours >= 0 ? "to" : "past"} peak`;
  if (abs < 48) return `${abs.toFixed(1)} h ${hours >= 0 ? "to" : "past"} peak`;
  return `${(abs / 24).toFixed(1)} d ${hours >= 0 ? "to" : "past"} peak`;
}

function nextWatchDate(forecast) {
  const rows = forecast.lookahead_watch || [];
  if (!rows.length) return "";
  const r = rows[0];
  const t = (r.time || "").match(/(\d{4})-(\d{2})-(\d{2})/);
  if (!t) return "";
  const months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"];
  const moStr = months[Number(t[2]) - 1] + " " + Number(t[3]);
  return `Next watch ${moStr} (${r.mllw.toFixed(2)})`;
}

function fmtClock(s) {
  // "2026-07-06 16:40" -> "4:40P"
  const m = s && s.match(/ (\d{2}):(\d{2})/);
  if (!m) return "";
  let h = Number(m[1]); const mi = m[2];
  const ap = h >= 12 ? "P" : "A"; h = (h % 12) || 12;
  return mi === "00" ? `${h}${ap}` : `${h}:${mi}${ap}`;
}

function todayWindowLine(forecast) {
  // One-line flood window for the highest landmark crossed today,
  // e.g. "SW grate wet ~4:40–7:10P (2.5h)". Null when nothing floods.
  const hc = forecast.today_highest_crossed;
  const fw = forecast.flood_windows || {};
  if (!hc || !fw[hc.key] || !fw[hc.key].length) return null;
  const label = (LANDMARKS.find(l => l[0] === hc.key) || [null, hc.key])[1];
  const ep = fw[hc.key][0];
  if (ep.grazing) return `${label}: may briefly touch`;
  const start = fmtClock(ep.start);
  const end = ep.end ? fmtClock(ep.end) : "…";
  const dur = ep.duration_h != null ? ` (${ep.duration_h.toFixed(1)}h)` : "";
  return `${label} wet ~${start}–${end}${dur}`;
}

// ---- tide-curve chart (medium widget) ----
// Draws forecast.water_series (model-predicted water NAVD88, 30-min
// steps, now-2h → now+24h) as a line chart with:
//   - dashed reference line at LOWEST_ELEV (first water at SW grate)
//   - dashed reference line at CURB_ELEV (flood onset)
//   - vertical "now" marker
//   - shaded fill where the curve exceeds LOWEST_ELEV
function drawTideChart(series, width, height, styleText, rainPotential) {
  const ctx = new DrawContext();
  ctx.size = new Size(width, height);
  ctx.opaque = false;
  ctx.respectScreenScale = true;

  // Y-axis: inches relative to the SW grate (the standard reference).
  const toIn = (v) => (v - LOWEST_ELEV) * 12;
  const times = [], tideIn = [], pluvIn = [], obsIn = [];
  for (const p of series) {
    const t = parseLocal(p.time);
    if (!t) continue;
    times.push(t);
    tideIn.push(toIn(p.tide_navd88 != null ? p.tide_navd88 : p.water_navd88));
    pluvIn.push(p.pluvial_navd88 != null ? toIn(p.pluvial_navd88) : null);
    obsIn.push(p.observed_navd88 != null ? toIn(p.observed_navd88) : null);
  }
  if (!times.length) return null;
  const combined = tideIn.map((v, i) => Math.max(v, pluvIn[i] != null ? pluvIn[i] : -1e9));

  const CURB_IN = toIn(CURB_ELEV);          // ≈ +7.7″
  const potIn = rainPotential ? toIn(rainPotential) : null;
  // Standard frame (user 2026-07-06): same y-limits every day so the
  // eye calibrates — normal tides swing −55″..+5″, measured floods
  // peak ~+21″. Expands only when data exceeds it (never clip a
  // Sandy-class forecast).
  let yMin = Math.min(-60, Math.min(...tideIn, 0) - 3);
  let yMax = Math.max(36, Math.max(...combined, CURB_IN, potIn || 0) + 3);
  const t0 = times[0].getTime();
  const t1 = times[times.length - 1].getTime();

  const PAD_L = 2, PAD_R = 2, PAD_T = 4, PAD_B = 12;
  const plotW = width - PAD_L - PAD_R;
  const plotH = height - PAD_T - PAD_B;
  const x = (t) => PAD_L + plotW * ((t - t0) / (t1 - t0));
  const y = (v) => PAD_T + plotH * (1 - (v - yMin) / (yMax - yMin));

  // Exceedance fill: combined water above the SW grate (0″)
  ctx.setFillColor(new Color("#4a90d9", 0.25));
  for (let i = 0; i < times.length; i++) {
    const v = combined[i];
    if (v <= 0) continue;
    const xi = x(times[i].getTime());
    const stripW = Math.max(2, plotW / times.length);
    ctx.fillRect(new Rect(xi - stripW / 2, y(v), stripW, y(0) - y(v)));
  }

  function dashedH(yPix, color) {
    ctx.setStrokeColor(color);
    ctx.setLineWidth(1);
    for (let xi = PAD_L; xi < width - PAD_R; xi += 8) {
      const p = new Path();
      p.move(new Point(xi, yPix));
      p.addLine(new Point(Math.min(xi + 4, width - PAD_R), yPix));
      ctx.addPath(p); ctx.strokePath();
    }
  }
  function dottedV(xPix, color) {
    ctx.setStrokeColor(color);
    ctx.setLineWidth(1);
    for (let yi = PAD_T; yi < PAD_T + plotH; yi += 5) {
      const p = new Path();
      p.move(new Point(xPix, yi));
      p.addLine(new Point(xPix, Math.min(yi + 2, PAD_T + plotH)));
      ctx.addPath(p); ctx.strokePath();
    }
  }

  // Rain-burst possibility ZONE: water-navy band from ground (0″) up
  // to the analog-scaled burst potential — drawn only across the
  // hours flagged burst-capable (PoP/thunderstorm wording), not the
  // whole window. A zone, not a level.
  if (potIn) {
    // Band: bottom = tide curve, top = FLAT absolute burst-potential
    // level (matches the website) — a burst could fill street water
    // to ~that level at any point in the storm window; thickness is
    // the rain's headroom over the tide. Clamps to zero where the
    // tide already exceeds the potential.
    ctx.setFillColor(new Color("#0b3d6b", 0.30));
    const flags = series.map(p => !!p.burst_risk);
    const anyFlag = flags.some(Boolean);
    const stripW = Math.max(2, plotW / times.length);
    for (let i = 0; i < times.length; i++) {
      if (anyFlag && !flags[i]) continue;
      const xi = x(times[i].getTime());
      const topV = Math.max(potIn, tideIn[i]);
      ctx.fillRect(new Rect(xi - stripW / 2, y(topV), stripW, y(tideIn[i]) - y(topV)));
    }
    ctx.setStrokeColor(new Color("#0b3d6b", 0.95));
    ctx.setLineWidth(1.5);
    let zseg = null;
    for (let i = 0; i < times.length; i++) {
      const active = !anyFlag || flags[i];
      if (active) {
        const pt = new Point(x(times[i].getTime()), y(Math.max(potIn, tideIn[i])));
        if (zseg) zseg.addLine(pt);
        else { zseg = new Path(); zseg.move(pt); }
      } else if (zseg) {
        ctx.addPath(zseg); ctx.strokePath(); zseg = null;
      }
    }
    if (zseg) { ctx.addPath(zseg); ctx.strokePath(); }
  }

  // Landmark reference lines — SHARED PALETTE with the website chart
  // (unlabeled here by design; learned by color):
  //   solid black  = SW grate 0″ (ground level / axis datum)
  //   green dashed = gutter +3.1″ (move the car)
  //   red dashed   = curb +7.7″ (flood onset)
  //   purple dashed= lawn step +13.7″
  //   brown dashed = top of 1st porch step +22.7″ (Oct-30 class)
  //   steel dashed = MSL −45″ (mean sea level, epoch 1983-2001 —
  //                  same steel family as the site's datum lines)
  const GUTTER_IN = toIn(3.78), LAWN_IN = toIn(4.66), PORCH1_IN = toIn(5.41);
  const MSL_IN = toIn(-0.24);
  ctx.setStrokeColor(new Color("#222222", 0.9));
  ctx.setLineWidth(1.5);
  {
    const gp = new Path();
    gp.move(new Point(PAD_L, y(0)));
    gp.addLine(new Point(width - PAD_R, y(0)));
    ctx.addPath(gp); ctx.strokePath();
  }
  dashedH(y(GUTTER_IN), new Color("#2f8f5f", 0.85));
  dashedH(y(CURB_IN), new Color("#c0392b", 0.85));
  dashedH(y(LAWN_IN), new Color("#7c4dbc", 0.85));
  dashedH(y(PORCH1_IN), new Color("#6d4c2f", 0.85));
  dashedH(y(MSL_IN), new Color("#4a6b8a", 0.8));

  // Day boundaries: dotted vertical line at each midnight in window
  const mid = new Date(times[0]);
  mid.setHours(24, 0, 0, 0);
  while (mid.getTime() < t1) {
    dottedV(x(mid.getTime()), new Color("#999999", 0.9));
    mid.setHours(mid.getHours() + 24);
  }

  // OBSERVED bay (despiked gauge) — gray, past portion only, drawn
  // under the forecast curve. Site parity (v7.20a): the past is
  // observation, the future is model; the now-dot is the seam.
  ctx.setStrokeColor(new Color("#555555", 0.9));
  ctx.setLineWidth(2.5);
  let oseg = null;
  for (let i = 0; i < times.length; i++) {
    if (obsIn[i] != null) {
      const pt = new Point(x(times[i].getTime()), y(obsIn[i]));
      if (!oseg) { oseg = new Path(); oseg.move(pt); }
      else oseg.addLine(pt);
    } else if (oseg) {
      ctx.addPath(oseg); ctx.strokePath(); oseg = null;
    }
  }
  if (oseg) { ctx.addPath(oseg); ctx.strokePath(); }

  // Tide curve (bay water — blue)
  ctx.setStrokeColor(new Color("#1a5fa8"));
  ctx.setLineWidth(2);
  let path = new Path();
  path.move(new Point(x(times[0].getTime()), y(tideIn[0])));
  for (let i = 1; i < times.length; i++) {
    path.addLine(new Point(x(times[i].getTime()), y(tideIn[i])));
  }
  ctx.addPath(path);
  ctx.strokePath();

  // Rain street-water segments (amber) — separate surface, drawn as
  // its own line only where the layer is active (two-line design).
  ctx.setStrokeColor(new Color("#d97706"));
  ctx.setLineWidth(2);
  let seg = null;
  for (let i = 0; i < times.length; i++) {
    if (pluvIn[i] != null) {
      const pt = new Point(x(times[i].getTime()), y(pluvIn[i]));
      if (seg) { seg.addLine(pt); }
      else { seg = new Path(); seg.move(pt); }
    } else if (seg) {
      ctx.addPath(seg); ctx.strokePath(); seg = null;
    }
  }
  if (seg) { ctx.addPath(seg); ctx.strokePath(); }

  // "Now" marker: vertical line + filled dot ON the curve at the
  // current time (user request — makes "you are here" unmissable).
  const nowT = Date.now();
  if (nowT >= t0 && nowT <= t1) {
    ctx.setStrokeColor(new Color("#555555", 0.9));
    ctx.setLineWidth(1);
    const np = new Path();
    np.move(new Point(x(nowT), PAD_T));
    np.addLine(new Point(x(nowT), PAD_T + plotH));
    ctx.addPath(np);
    ctx.strokePath();
    // Interpolate the tide value at now and dot it
    let i1 = times.findIndex(t => t.getTime() >= nowT);
    if (i1 > 0) {
      const ta = times[i1 - 1].getTime(), tb = times[i1].getTime();
      const frac = (nowT - ta) / (tb - ta);
      const vNow = tideIn[i1 - 1] + (tideIn[i1] - tideIn[i1 - 1]) * frac;
      const cx = x(nowT), cy = y(vNow), r = 3.5;
      ctx.setFillColor(new Color("#ffffff"));
      ctx.fillEllipse(new Rect(cx - r - 1.5, cy - r - 1.5, 2 * (r + 1.5), 2 * (r + 1.5)));
      ctx.setFillColor(new Color("#1a5fa8"));
      ctx.fillEllipse(new Rect(cx - r, cy - r, 2 * r, 2 * r));
      // If the rain line is active at now, dot it too (amber)
      if (pluvIn[i1 - 1] != null && pluvIn[i1] != null) {
        const pNow = pluvIn[i1 - 1] + (pluvIn[i1] - pluvIn[i1 - 1]) * frac;
        const py = y(pNow);
        ctx.setFillColor(new Color("#ffffff"));
        ctx.fillEllipse(new Rect(cx - r - 1.5, py - r - 1.5, 2 * (r + 1.5), 2 * (r + 1.5)));
        ctx.setFillColor(new Color("#0b3d6b"));
        ctx.fillEllipse(new Rect(cx - r, py - r, 2 * r, 2 * r));
      }
    }
  }

  // Unlabeled by design — the landmark palette is learned by color
  // (labels + inches live on the website chart). Only the datum gets
  // a tiny marker.
  ctx.setFont(Font.systemFont(7));
  ctx.setTextColor(new Color("#222222"));
  ctx.drawText("0″", new Point(width - 12, y(0) + 1));

  // X ticks every 6 clock hours (0/6/12/18) + start/end labels
  ctx.setTextColor(new Color("#777777"));
  ctx.setFont(Font.systemFont(7));
  const fmtHr = (d) => {
    let h = d.getHours(); const ap = h >= 12 ? "P" : "A"; h = (h % 12) || 12;
    return `${h}${ap}`;
  };
  const tick = new Date(times[0]);
  tick.setMinutes(0, 0, 0);
  tick.setHours(tick.getHours() + (6 - tick.getHours() % 6) % 6 || 6);
  while (tick.getTime() < t1 - 3600e3) {
    const xi = x(tick.getTime());
    ctx.setStrokeColor(new Color("#999999", 0.8));
    ctx.setLineWidth(1);
    const tp = new Path();
    tp.move(new Point(xi, PAD_T + plotH));
    tp.addLine(new Point(xi, PAD_T + plotH + 3));
    ctx.addPath(tp); ctx.strokePath();
    ctx.drawText(fmtHr(tick), new Point(xi - 6, height - 10));
    tick.setHours(tick.getHours() + 6);
  }
  ctx.drawText(fmtHr(times[0]), new Point(PAD_L, height - 10));
  ctx.drawText(fmtHr(times[times.length - 1]), new Point(width - 18, height - 10));

  return ctx.getImage();
}

async function fetchForecast() {
  // Cache-buster: iOS URLCache happily serves widgets a stale JSON
  // for far longer than Pages' max-age (found 2026-07-09: site showed
  // the new so-far line while the widget rendered a cached JSON
  // without the field). A per-5-min query param defeats it while
  // still coalescing rapid refreshes.
  const bust = Math.floor(Date.now() / 300000);
  const req = new Request(FORECAST_URL + "?t=" + bust);
  const fc = await req.loadJSON();
  // LIVE nowcast overlay (2026-07-17): tiny separate file kept fresh
  // by a best-effort 10-min radar Action; attach only when active and
  // <20 min old. Stale radar must never override the forecast headline.
  try {
    const nreq = new Request(NOWCAST_URL + "?t=" + bust);
    const nc = await nreq.loadJSON();
    if (nc && nc.active && nc.generated_utc &&
        (Date.now() - Date.parse(nc.generated_utc)) / 60000 <= 20) {
      fc._nowcast = nc;
    }
  } catch (e) {}
  return fc;
}

function makeErrorWidget(err) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#fdecec");
  const t = w.addText("Barnacle");
  t.font = Font.boldSystemFont(16);
  t.textColor = new Color("#8a3232");
  w.addSpacer(4);
  const e = w.addText(String(err).substring(0, 80));
  e.font = Font.systemFont(10);
  e.textColor = new Color("#8a3232");
  return w;
}

function makeWidget(forecast, family) {
  const w = new ListWidget();
  // TODAY drives the widget color (2026-07-06 redesign): the regime
  // from the next-26h water series (which includes rain), upgraded
  // one step visually when pluvial risk is elevated. The 72h worst
  // tide is a labeled secondary line, no longer the headline.
  const worstRegime = (forecast.depths_in && forecast.depths_in.regime) || "dry";
  let todayRegime = forecast.today_regime || worstRegime;
  const _pr = forecast.pluvial_risk || {};
  // 2026-07-20 scope fix: risk whose window opens TOMORROW must not
  // relabel TODAY (risk_today === false gates it; missing field =
  // old JSON = old behavior).
  const pluvialLevel = (_pr.level && _pr.risk_today !== false)
    ? _pr.level : null;
  const pluvialTomorrow = (_pr.level && _pr.risk_today === false)
    ? _pr.level : null;
  // Resolve the "NO FLOODING" + "RAIN FLOOD RISK" contradiction
  // (2026-07-07): when the tide-derived regime is dry but rain risk
  // is live, the rain message IS the headline; "no tidal flooding"
  // becomes the detail line and the separate warning line is
  // suppressed as redundant.
  let todayLabel = regimeDisplay(todayRegime);
  let todaySub = null;
  let showPluvialLine = !!pluvialLevel;
  if (pluvialLevel && todayRegime === "dry") {
    todayLabel = pluvialLevel === "elevated" ? "RAIN FLOOD RISK" : "RAIN POSSIBLE";
    todaySub = "no tidal flooding expected";
    showPluvialLine = false;
  }
  let styleKey = todayRegime;
  if (pluvialLevel === "elevated" && (styleKey === "dry" || styleKey === "street")) {
    styleKey = "light";  // amber-ish background when rain risk dominates
  }
  const style = REGIME_STYLES[styleKey] || REGIME_STYLES.dry;
  w.backgroundColor = new Color(style.bg);

  const peakFt = forecast.peak_forecast_observed_mllw;
  const peakTime = forecast.peak_time_local || "";
  const depths = forecast.depths_in || {};
  const exceeded = highestExceeded(depths);
  const rel = peakFt != null ? relativeToLowest(peakFt) : null;
  const conf = forecast.confidence_level || "";
  const confUnc = forecast.confidence_uncertainty_ft;   // ± ft on peak
  const hToPeak = hoursToPeak(peakTime);
  const watchStr = nextWatchDate(forecast);
  const cold = forecast.cold_lockout === true;
  const series = forecast.water_series || [];
  // Pluvial (rain-driven) flood risk is INDEPENDENT of the tide-keyed
  // regime that colors this widget — heavy rain floods the
  // intersection with no tidal contribution at all (2026-07-06 event).
  // Without this line, a pluvial-risk day with benign tides would
  // show "NO FLOODING", which is exactly backwards.
  const pluvial = (forecast.pluvial_risk && forecast.pluvial_risk.level) || null;

  function addPluvialLine(stack) {
    if (!pluvial) return;
    const t = stack.addText(
      pluvial === "elevated" ? "⚠ RAIN FLOOD RISK" : "⚠ rain flood possible");
    t.font = Font.boldSystemFont(pluvial === "elevated" ? 12 : 10);
    t.textColor = new Color("#9a4c00");
    t.lineLimit = 1;
    t.minimumScaleFactor = 0.7;
  }

  if (family === "medium") {
    // Left column: key numbers. Right: tide-curve chart.
    const row = w.addStack();
    row.layoutHorizontally();
    row.spacing = 8;

    const left = row.addStack();
    left.layoutVertically();

    // ---- TODAY block (the headline) ----
    const hdr = left.addText("TODAY · OUTLOOK");
    if (forecast._nowcast) {
      const nc = forecast._nowcast;
      const line = left.addText(
        "📡 LIVE: " + (nc.street_now_in >= 0 ? "+" : "") +
        nc.street_now_in.toFixed(1) + "″ now → " +
        (nc.peak_proj_in >= 0 ? "+" : "") +
        nc.peak_proj_in.toFixed(1) + "″ peak");
      line.font = Font.boldSystemFont(10);
      line.textColor = new Color("#b91c1c");
      line.lineLimit = 1;
      line.minimumScaleFactor = 0.7;
    }
    hdr.font = Font.mediumSystemFont(9);
    hdr.textColor = new Color("#777");

    const regLabel = left.addText(todayLabel);
    regLabel.font = Font.boldSystemFont(todayLabel.length > 8 ? 15 : 20);
    regLabel.textColor = new Color(style.text);
    regLabel.lineLimit = 1;
    regLabel.minimumScaleFactor = 0.6;
    if (todaySub) {
      const s = left.addText(todaySub);
      s.font = Font.systemFont(9);
      s.textColor = new Color("#555");
    }
    if (showPluvialLine) addPluvialLine(left);
    if (pluvialTomorrow) {
      const tm = left.addText(
        pluvialTomorrow === "elevated"
          ? "\u26A0 rain flood risk TOMORROW"
          : "rain possible tomorrow");
      tm.font = Font.semiboldSystemFont(9);
      tm.textColor = new Color("#8a6d3b");
      tm.lineLimit = 1;
    }

    // SO-FAR line (2026-07-09, post-event-#4): the outlook is
    // forward-looking by design, but an hour after a top-3 flood the
    // widget read as amnesia. today_lookback = today's measured/
    // observed peak (spot-check tape sees rain floods; despiked
    // gauge sees tide floods).
    const lb = forecast.today_lookback;
    if (lb && lb.rel_grate_in > 0) {
      const reg = (lb.regime === "dry" ? "street water"
                   : lb.regime).toUpperCase();
      const lbLine = left.addText(
        `so far: ${reg} +${lb.rel_grate_in.toFixed(1)}″ @${lb.time_local}`);
      lbLine.font = Font.semiboldSystemFont(9);
      lbLine.textColor = new Color(
        lb.regime === "severe" ? "#b91c1c" :
        lb.regime === "moderate" ? "#c2410c" : "#555");
      lbLine.lineLimit = 1;
      lbLine.minimumScaleFactor = 0.7;
    }

    // Flood window for the highest landmark crossed today, or the
    // rel-to-SW-grate peak (the standard mental unit).
    const winLine = todayWindowLine(forecast);
    if (winLine) {
      const t = left.addText(winLine);
      t.font = Font.semiboldSystemFont(10);
      t.textColor = new Color(style.text);
      t.lineLimit = 2;
      t.minimumScaleFactor = 0.7;
    }
    const relToday = forecast.today_rel_grate_sw_in;
    if (relToday != null) {
      const t = left.addText(
        `peak ${relToday >= 0 ? "+" : ""}${relToday.toFixed(1)}″ vs SW grate` +
        (forecast.today_peak_time ? ` @${fmtClock(forecast.today_peak_time)}` : ""));
      t.font = Font.systemFont(9);
      t.textColor = new Color("#555");
      t.lineLimit = 1;
      t.minimumScaleFactor = 0.7;
    }

    left.addSpacer(4);
    // ---- 72h worst (secondary, clearly labeled) ----
    const worstStyle = REGIME_STYLES[worstRegime] || REGIME_STYLES.dry;
    // 72 H — OUTLOOK (user redesign 2026-07-21): risk-first lines
    // (tidal days / rain days) instead of worst-tide-first; the
    // confidence "LOW ±0.50" line is dropped — glanceability wins,
    // details live one tap away on the site.
    const wHdr = left.addText("72H — OUTLOOK");
    wHdr.font = Font.mediumSystemFont(9);
    wHdr.textColor = new Color("#777");
    const dayOut = forecast.day_outlook;
    function dayNames(flagKey) {
      if (!dayOut || !dayOut.length) return null;
      const names = [];
      const today = new Date();
      for (const d of dayOut) {
        if (!d[flagKey]) continue;
        const m = d.day.match(/(\d{4})-(\d{2})-(\d{2})/);
        if (!m) continue;
        const dd = new Date(+m[1], m[2] - 1, +m[3]);
        const diff = Math.round((dd - new Date(today.getFullYear(),
          today.getMonth(), today.getDate())) / 86400000);
        names.push(diff === 0 ? "today" : diff === 1 ? "tomorrow"
          : ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][dd.getDay()]);
      }
      return names;
    }
    if (dayOut && dayOut.length) {
      const tDays = dayNames("tide_flood");
      const rDays = dayNames("rain_risk");
      const tLine = left.addText(
        "Tidal flood: " + (tDays.length ? tDays.join(", ") : "none"));
      tLine.font = Font.semiboldSystemFont(10);
      tLine.textColor = new Color(tDays.length ? "#1565c0" : "#777");
      tLine.lineLimit = 1; tLine.minimumScaleFactor = 0.7;
      const rLine = left.addText(
        "Rain flood: " + (rDays.length ? rDays.join(", ") : "none"));
      rLine.font = Font.semiboldSystemFont(10);
      rLine.textColor = new Color(rDays.length ? "#b45f00" : "#777");
      rLine.lineLimit = 1; rLine.minimumScaleFactor = 0.7;
      const hLine = left.addText(
        "High tide: " + formatTimeShort(peakTime)
        + (hToPeak != null ? ` · ${formatHoursToPeak(hToPeak)}` : ""));
      hLine.font = Font.systemFont(8);
      hLine.textColor = new Color("#666");
      hLine.lineLimit = 1; hLine.minimumScaleFactor = 0.7;
    } else {
      // old-JSON fallback: previous worst-tide lines
      const wLine1 = left.addText(
        `● ${peakFt != null ? peakFt.toFixed(2) : "—"} · ${regimeDisplay(worstRegime).toLowerCase()}`);
      wLine1.font = Font.semiboldSystemFont(11);
      wLine1.textColor = new Color(worstStyle.text);
      wLine1.lineLimit = 1;
      const wLine2 = left.addText(
        formatTimeShort(peakTime) + (hToPeak != null ? ` · ${formatHoursToPeak(hToPeak)}` : ""));
      wLine2.font = Font.systemFont(8);
      wLine2.textColor = new Color("#666");
      wLine2.lineLimit = 1;
      wLine2.minimumScaleFactor = 0.7;
    }
    if (cold) {
      const coldLine = left.addText("Cold (hyp. open)");
      coldLine.font = Font.systemFont(8);
      coldLine.textColor = new Color("#3a5b88");
    }

    // Right: the 24-h model water-level curve
    const right = row.addStack();
    right.layoutVertically();
    // v0.9-gamma dual models: band top = the higher of the power-law
    // (primary) and tanh (saturating) potential estimates. Old JSONs
    // lack the _tanh field; Math.max with 0 handles both.
    const prisk = forecast.pluvial_risk || {};
    const rainPotential = Math.max(
      prisk.potential_low_tide_navd88 || 0,
      prisk.potential_low_tide_navd88_tanh || 0) || null;
    // Widget chart window: 6 h back (user 2026-07-18: context +
    // "the app knows what happened"), full forecast horizon forward.
    const cutoff = Date.now() - 6 * 3600e3;
    const chartSeries = series.filter(p => {
      const d = parseLocal(p.time);
      return !d || d.getTime() >= cutoff;
    });
    const img = chartSeries.length >= 4
      ? drawTideChart(chartSeries, 190, 110, style.text, rainPotential)
      : null;
    if (img) {
      const wi = right.addImage(img);
      wi.resizable = true;
    } else {
      // Fallback when water_series is missing (old forecast.json)
      const sumText = right.addText(forecast.plain_language_summary || "");
      sumText.font = Font.systemFont(11);
      sumText.textColor = new Color("#333");
      sumText.lineLimit = 5;
    }
  } else {
    // Small widget — single column, key info (no chart; too small)
    const hdrS = w.addText("TODAY · OUTLOOK");
    hdrS.font = Font.mediumSystemFont(8);
    hdrS.textColor = new Color("#777");
    const regLabel = w.addText(todayLabel);
    regLabel.font = Font.boldSystemFont(todayLabel.length > 8 ? 14 : 18);
    regLabel.textColor = new Color(style.text);
    regLabel.lineLimit = 1;
    regLabel.minimumScaleFactor = 0.6;
    if (todaySub) {
      const s = w.addText(todaySub);
      s.font = Font.systemFont(8);
      s.textColor = new Color("#555");
    }
    if (showPluvialLine) addPluvialLine(w);
    const winLineS = todayWindowLine(forecast);
    if (winLineS) {
      const t = w.addText(winLineS);
      t.font = Font.semiboldSystemFont(9);
      t.textColor = new Color(style.text);
      t.lineLimit = 2;
      t.minimumScaleFactor = 0.7;
    }
    const relTodayS = forecast.today_rel_grate_sw_in;
    if (relTodayS != null) {
      const t = w.addText(
        `pk ${relTodayS >= 0 ? "+" : ""}${relTodayS.toFixed(1)}″ vs SW grate`);
      t.font = Font.systemFont(9);
      t.textColor = new Color("#555");
    }
    w.addSpacer(3);
    const worstStyleS = REGIME_STYLES[worstRegime] || REGIME_STYLES.dry;
    const wl = w.addText(
      `72h: ● ${peakFt != null ? peakFt.toFixed(2) : "—"} ${formatTimeShort(peakTime)}`);
    wl.font = Font.systemFont(8);
    wl.textColor = new Color(worstStyleS.text);
    wl.lineLimit = 1;
    wl.minimumScaleFactor = 0.6;
    if (cold) {
      const coldLine = w.addText("Cold (hyp. open)");
      coldLine.font = Font.systemFont(8);
      coldLine.textColor = new Color("#3a5b88");
    }
  }

  // Footer: updated timestamp (left) + brand (right, was empty space)
  w.addSpacer();
  const footer = w.addStack();
  footer.layoutHorizontally();
  footer.centerAlignContent();
  const stamp = footer.addText("Updated " + new Date().toLocaleTimeString(
    "en-US", { hour: "numeric", minute: "2-digit" }
  ));
  stamp.font = Font.systemFont(8);
  stamp.textColor = new Color("#888");
  footer.addSpacer();
  const brand = footer.addText("Bay Ave Barnacle " + WIDGET_VERSION);
  brand.font = Font.mediumSystemFont(8);
  brand.textColor = new Color("#888");

  // Tapping the widget opens the live Pages site
  w.url = "https://johnurban.github.io/barnacle/";
  return w;
}

// ---- main ----
let widget;
try {
  const forecast = await fetchForecast();
  widget = makeWidget(forecast, config.widgetFamily || "small");
} catch (err) {
  widget = makeErrorWidget(err.message || err);
}

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  // Running in the Scriptable app itself — preview medium size.
  await widget.presentMedium();
}

Script.complete();
