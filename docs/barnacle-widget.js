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
  const times = [], tideIn = [], pluvIn = [];
  for (const p of series) {
    const t = parseLocal(p.time);
    if (!t) continue;
    times.push(t);
    tideIn.push(toIn(p.tide_navd88 != null ? p.tide_navd88 : p.water_navd88));
    pluvIn.push(p.pluvial_navd88 != null ? toIn(p.pluvial_navd88) : null);
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

  dashedH(y(0), new Color("#4a90d9", 0.8));        // SW grate = 0″
  dashedH(y(CURB_IN), new Color("#c0392b", 0.8));  // curb
  if (potIn) dashedH(y(potIn), new Color("#d97706", 0.9));  // rain potential

  // Day boundaries: dotted vertical line at each midnight in window
  const mid = new Date(times[0]);
  mid.setHours(24, 0, 0, 0);
  while (mid.getTime() < t1) {
    dottedV(x(mid.getTime()), new Color("#999999", 0.9));
    mid.setHours(mid.getHours() + 24);
  }

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
        ctx.setFillColor(new Color("#d97706"));
        ctx.fillEllipse(new Rect(cx - r, py - r, 2 * r, 2 * r));
      }
    }
  }

  // Reference labels (with inches — SW grate is the 0 of the axis)
  ctx.setFont(Font.systemFont(7));
  ctx.setTextColor(new Color("#c0392b"));
  ctx.drawText(`curb +${CURB_IN.toFixed(0)}″`, new Point(width - 44, y(CURB_IN) - 9));
  ctx.setTextColor(new Color("#1a5fa8"));
  ctx.drawText("SW grate 0″", new Point(width - 50, y(0) + 1));
  if (potIn) {
    ctx.setTextColor(new Color("#d97706"));
    ctx.drawText(`rain pot. +${potIn.toFixed(0)}″`, new Point(2, y(potIn) - 9));
  }

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
  const req = new Request(FORECAST_URL);
  return await req.loadJSON();
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
  const pluvialLevel = (forecast.pluvial_risk && forecast.pluvial_risk.level) || null;
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
    const hdr = left.addText("TODAY");
    hdr.font = Font.mediumSystemFont(9);
    hdr.textColor = new Color("#777");

    const regLabel = left.addText(regimeDisplay(todayRegime));
    regLabel.font = Font.boldSystemFont(regimeDisplay(todayRegime).length > 8 ? 15 : 20);
    regLabel.textColor = new Color(style.text);
    regLabel.lineLimit = 1;
    regLabel.minimumScaleFactor = 0.6;
    addPluvialLine(left);

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
    const wHdr = left.addText("WORST 72H");
    wHdr.font = Font.mediumSystemFont(9);
    wHdr.textColor = new Color("#777");
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
    if (conf) {
      const confTxt = confUnc != null
        ? `${conf.toUpperCase()} ±${confUnc.toFixed(2)}`
        : conf.toUpperCase();
      const confLine = left.addText(confTxt);
      confLine.font = Font.systemFont(8);
      confLine.textColor = new Color("#555");
    }
    if (cold) {
      const coldLine = left.addText("Cold (hyp. open)");
      coldLine.font = Font.systemFont(8);
      coldLine.textColor = new Color("#3a5b88");
    }

    // Right: the 24-h model water-level curve
    const right = row.addStack();
    right.layoutVertically();
    const rainPotential = (forecast.pluvial_risk &&
                           forecast.pluvial_risk.potential_low_tide_navd88) || null;
    const img = series.length >= 4
      ? drawTideChart(series, 190, 110, style.text, rainPotential)
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
    const hdrS = w.addText("TODAY");
    hdrS.font = Font.mediumSystemFont(8);
    hdrS.textColor = new Color("#777");
    const regLabel = w.addText(regimeDisplay(todayRegime));
    regLabel.font = Font.boldSystemFont(regimeDisplay(todayRegime).length > 8 ? 14 : 18);
    regLabel.textColor = new Color(style.text);
    regLabel.lineLimit = 1;
    regLabel.minimumScaleFactor = 0.6;
    addPluvialLine(w);
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

  // Footer: updated timestamp
  w.addSpacer();
  const stamp = w.addText("Updated " + new Date().toLocaleTimeString(
    "en-US", { hour: "numeric", minute: "2-digit" }
  ));
  stamp.font = Font.systemFont(8);
  stamp.textColor = new Color("#888");

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
