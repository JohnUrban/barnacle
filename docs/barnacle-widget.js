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
// Updated 2026-07-06: v0.8 landmark set (the old v0.6 keys had broken
// highestExceeded silently), enhancement 0.00 (was hardcoded +0.40),
// "dry" now displays as "NO FLOODING", added the tide-curve chart
// fed by the new water_series field in forecast.json.

const FORECAST_URL = "https://johnurban.github.io/barnacle/forecast.json";

// Landmark elevations (NAVD88). Match flood_forecast_daily.py LANDMARKS
// (v0.8, 16 landmarks). Ascending elevation; highestExceeded scans in
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
  ["lawn_step",                         "Lawn step",      4.58],
  ["porch_step",                        "Porch step",     5.08],
];
const LOWEST_ELEV = 3.52;      // grate_SW — first water appears here
const CURB_ELEV   = 4.16;      // flood onset at the property
const LOCAL_ENHANCEMENT = 0.00;  // v0.8
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

// ---- tide-curve chart (medium widget) ----
// Draws forecast.water_series (model-predicted water NAVD88, 30-min
// steps, now-2h → now+24h) as a line chart with:
//   - dashed reference line at LOWEST_ELEV (first water at SW grate)
//   - dashed reference line at CURB_ELEV (flood onset)
//   - vertical "now" marker
//   - shaded fill where the curve exceeds LOWEST_ELEV
function drawTideChart(series, width, height, styleText) {
  const ctx = new DrawContext();
  ctx.size = new Size(width, height);
  ctx.opaque = false;
  ctx.respectScreenScale = true;

  const times = series.map(p => parseLocal(p.time)).filter(Boolean);
  const vals = series.map(p => p.water_navd88);
  if (!times.length) return null;

  // Y range: include reference lines with a little headroom
  let yMin = Math.min(...vals, LOWEST_ELEV) - 0.3;
  let yMax = Math.max(...vals, CURB_ELEV) + 0.3;
  const t0 = times[0].getTime();
  const t1 = times[times.length - 1].getTime();

  const PAD_L = 2, PAD_R = 2, PAD_T = 4, PAD_B = 12;
  const plotW = width - PAD_L - PAD_R;
  const plotH = height - PAD_T - PAD_B;
  const x = (t) => PAD_L + plotW * ((t - t0) / (t1 - t0));
  const y = (v) => PAD_T + plotH * (1 - (v - yMin) / (yMax - yMin));

  // Shaded exceedance fill above the lowest grate: draw thin vertical
  // strips where water > LOWEST_ELEV (DrawContext has no polygon fill
  // along a path, so strips approximate it).
  ctx.setFillColor(new Color("#4a90d9", 0.25));
  for (let i = 0; i < times.length; i++) {
    const v = vals[i];
    if (v <= LOWEST_ELEV) continue;
    const xi = x(times[i].getTime());
    const stripW = Math.max(2, plotW / times.length);
    const topY = y(v);
    const botY = y(LOWEST_ELEV);
    ctx.fillRect(new Rect(xi - stripW / 2, topY, stripW, botY - topY));
  }

  // Reference lines (dashed effect: short segments)
  function dashedLine(yPix, color) {
    ctx.setStrokeColor(color);
    ctx.setLineWidth(1);
    for (let xi = PAD_L; xi < width - PAD_R; xi += 8) {
      const p = new Path();
      p.move(new Point(xi, yPix));
      p.addLine(new Point(Math.min(xi + 4, width - PAD_R), yPix));
      ctx.addPath(p);
      ctx.strokePath();
    }
  }
  dashedLine(y(LOWEST_ELEV), new Color("#4a90d9", 0.8));  // first water
  dashedLine(y(CURB_ELEV), new Color("#c0392b", 0.8));    // flood onset

  // Water curve
  ctx.setStrokeColor(new Color("#1a5fa8"));
  ctx.setLineWidth(2);
  const path = new Path();
  path.move(new Point(x(times[0].getTime()), y(vals[0])));
  for (let i = 1; i < times.length; i++) {
    path.addLine(new Point(x(times[i].getTime()), y(vals[i])));
  }
  ctx.addPath(path);
  ctx.strokePath();

  // "Now" marker (vertical line)
  const nowT = Date.now();
  if (nowT >= t0 && nowT <= t1) {
    ctx.setStrokeColor(new Color("#555555", 0.9));
    ctx.setLineWidth(1);
    const np = new Path();
    np.move(new Point(x(nowT), PAD_T));
    np.addLine(new Point(x(nowT), PAD_T + plotH));
    ctx.addPath(np);
    ctx.strokePath();
  }

  // Tiny axis labels: reference-line names at right edge
  ctx.setTextColor(new Color("#c0392b"));
  ctx.setFont(Font.systemFont(7));
  ctx.drawText("curb", new Point(width - 26, y(CURB_ELEV) - 9));
  ctx.setTextColor(new Color("#1a5fa8"));
  ctx.drawText("1st water", new Point(width - 40, y(LOWEST_ELEV) + 1));

  // Time labels: start / now / end along the bottom
  ctx.setTextColor(new Color("#777777"));
  ctx.setFont(Font.systemFont(7));
  const fmtHr = (d) => {
    let h = d.getHours(); const ap = h >= 12 ? "P" : "A"; h = (h % 12) || 12;
    return `${h}${ap}`;
  };
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
  const regime = (forecast.depths_in && forecast.depths_in.regime) || "dry";
  const style = REGIME_STYLES[regime] || REGIME_STYLES.dry;
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

  if (family === "medium") {
    // Left column: key numbers. Right: tide-curve chart.
    const row = w.addStack();
    row.layoutHorizontally();
    row.spacing = 8;

    const left = row.addStack();
    left.layoutVertically();

    const regLabel = left.addText(regimeDisplay(regime));
    regLabel.font = Font.boldSystemFont(regimeDisplay(regime).length > 8 ? 16 : 22);
    regLabel.textColor = new Color(style.text);
    regLabel.lineLimit = 1;
    regLabel.minimumScaleFactor = 0.6;

    left.addSpacer(2);
    const peakLine = left.addText(
      peakFt != null ? `${peakFt.toFixed(2)} ft` : "—"
    );
    peakLine.font = Font.semiboldSystemFont(15);
    peakLine.textColor = new Color("#222");

    const timeLine = left.addText(formatTimeShort(peakTime));
    timeLine.font = Font.systemFont(10);
    timeLine.textColor = new Color("#555");

    if (hToPeak != null) {
      const htp = left.addText(formatHoursToPeak(hToPeak));
      htp.font = Font.systemFont(9);
      htp.textColor = new Color("#666");
    }

    left.addSpacer(3);
    if (exceeded) {
      const landLine = left.addText(`★ ${exceeded.label} +${exceeded.depth.toFixed(1)}″`);
      landLine.font = Font.semiboldSystemFont(11);
      landLine.textColor = new Color(style.text);
      landLine.lineLimit = 1;
      landLine.minimumScaleFactor = 0.7;
    } else if (rel != null) {
      const relLine = left.addText(
        `${rel >= 0 ? "+" : ""}${rel.toFixed(1)}″ vs SW grate`
      );
      relLine.font = Font.systemFont(10);
      relLine.textColor = new Color("#666");
    }
    if (conf) {
      const confTxt = confUnc != null
        ? `${conf.toUpperCase()} ±${confUnc.toFixed(2)}`
        : conf.toUpperCase();
      const confLine = left.addText(confTxt);
      confLine.font = Font.systemFont(9);
      confLine.textColor = new Color("#555");
    }
    if (cold) {
      const coldLine = left.addText("Cold (hyp. open)");
      coldLine.font = Font.systemFont(8);
      coldLine.textColor = new Color("#3a5b88");
    }
    if (watchStr) {
      const wLine = left.addText(watchStr);
      wLine.font = Font.systemFont(8);
      wLine.textColor = new Color("#666");
    }

    // Right: the 24-h model water-level curve
    const right = row.addStack();
    right.layoutVertically();
    const img = series.length >= 4
      ? drawTideChart(series, 190, 110, style.text)
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
    const regLabel = w.addText(regimeDisplay(regime));
    regLabel.font = Font.boldSystemFont(regimeDisplay(regime).length > 8 ? 15 : 20);
    regLabel.textColor = new Color(style.text);
    regLabel.lineLimit = 1;
    regLabel.minimumScaleFactor = 0.6;
    w.addSpacer(4);
    const peakLine = w.addText(
      peakFt != null ? `${peakFt.toFixed(2)} ft` : "—"
    );
    peakLine.font = Font.semiboldSystemFont(16);
    peakLine.textColor = new Color("#222");
    const timeLine = w.addText(formatTimeShort(peakTime));
    timeLine.font = Font.systemFont(10);
    timeLine.textColor = new Color("#555");
    if (hToPeak != null) {
      const htp = w.addText(formatHoursToPeak(hToPeak));
      htp.font = Font.systemFont(9);
      htp.textColor = new Color("#666");
    }
    w.addSpacer(4);
    if (exceeded) {
      const landLine = w.addText(`★ ${exceeded.label}`);
      landLine.font = Font.semiboldSystemFont(11);
      landLine.textColor = new Color(style.text);
      const depthLine = w.addText(`+${exceeded.depth.toFixed(1)}″`);
      depthLine.font = Font.systemFont(11);
      depthLine.textColor = new Color("#444");
    } else if (rel != null) {
      const relLine = w.addText(
        `${rel >= 0 ? "+" : ""}${rel.toFixed(1)}″ vs SW grate`
      );
      relLine.font = Font.systemFont(10);
      relLine.textColor = new Color("#666");
    }
    if (cold) {
      const coldLine = w.addText("Cold (hyp. open)");
      coldLine.font = Font.systemFont(9);
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
