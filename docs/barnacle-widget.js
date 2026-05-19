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
// Medium widget (4x2):    same as small on the left; right column adds
//                         plain-language summary, confidence + ± range,
//                         and "next watch" date from the look-ahead.
//
// Source data: https://johnurban.github.io/barnacle/forecast.json
// Refreshed each hourly GitHub Actions workflow run (HANDOFF 9b.1).
//
// Refreshed 2026-05-19 to surface 9b-era fields: confidence_uncertainty_ft,
// lookahead_watch, cold_lockout flag.

const FORECAST_URL = "https://johnurban.github.io/barnacle/forecast.json";

// Landmark elevations (NAVD88). Match flood_forecast_daily.py LANDMARKS.
const LANDMARKS = [
  ["lowest_sentinel_grate", "Sentinel grate", 3.60],
  ["lowest_road_corner",    "Lowest corner",  3.64],
  ["gutter_walkway",        "Gutter",         3.78],
  ["corner_grate",          "Storm grate",    3.91],
  ["curb",                  "Curb",           4.16],
  ["road_middle",           "Road middle",    4.36],
  ["intersection",          "Intersection",   4.54],
  ["lawn_step",             "Lawn step",      4.58],
  ["porch_step",            "Porch step",     5.08],
];
const LOWEST_ELEV = 3.60;

// Background + text colors per regime, matching the email/Pages CSS.
const REGIME_STYLES = {
  dry:          { bg: "#e8f5e9", text: "#2f6f47" },
  street:       { bg: "#e3f2fd", text: "#1565c0" },
  light:        { bg: "#fff8e1", text: "#8a6d3b" },
  moderate:     { bg: "#ffe0b2", text: "#b45f00" },
  severe:       { bg: "#ffcdd2", text: "#b33c3c" },
  cold_lockout: { bg: "#eceff1", text: "#455a64" },
};

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
  // Mirror the model: water_at_342_navd88 = SH + 0.40 - 2.82
  const waterNAVD88 = forecastPeakMLLW + 0.40 - 2.82;
  return (waterNAVD88 - LOWEST_ELEV) * 12;
}

function hoursToPeak(peakTimeStr) {
  // Returns signed hours to the peak (positive = future, negative = past).
  const m = peakTimeStr && peakTimeStr.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
  if (!m) return null;
  const [, y, mo, d, h, mi] = m.map(Number);
  // Treat the tide-time as local; iOS reads its own timezone for "now".
  const peak = new Date(y, mo - 1, d, h, mi);
  const now = new Date();
  return (peak - now) / 3600000;
}

function formatHoursToPeak(hours) {
  if (hours == null || isNaN(hours)) return "";
  const abs = Math.abs(hours);
  if (abs < 1) return `${Math.round(abs * 60)} min ${hours >= 0 ? "to" : "past"} peak`;
  if (abs < 48) return `${abs.toFixed(1)} h ${hours >= 0 ? "to" : "past"} peak`;
  return `${(abs / 24).toFixed(1)} d ${hours >= 0 ? "to" : "past"} peak`;
}

function nextWatchDate(forecast) {
  // Returns short string for the first row of lookahead_watch, e.g.
  // "Next watch: Jun 13 (6.24, gutter)". Empty when none.
  const rows = forecast.lookahead_watch || [];
  if (!rows.length) return "";
  const r = rows[0];
  const t = (r.time || "").match(/(\d{4})-(\d{2})-(\d{2})/);
  if (!t) return "";
  const months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"];
  const moStr = months[Number(t[2]) - 1] + " " + Number(t[3]);
  // Trim label to fit
  const label = (r.label || "").replace(" (no surge needed)", "");
  return `Next watch ${moStr} (${r.mllw.toFixed(2)})`;
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
  const summary = forecast.plain_language_summary || "";
  const hToPeak = hoursToPeak(peakTime);
  const watchStr = nextWatchDate(forecast);
  const cold = forecast.cold_lockout === true;

  if (family === "medium") {
    // Two-column layout
    const row = w.addStack();
    row.layoutHorizontally();
    row.spacing = 10;

    // Left column
    const left = row.addStack();
    left.layoutVertically();

    const regLabel = left.addText(regime.toUpperCase());
    regLabel.font = Font.boldSystemFont(22);
    regLabel.textColor = new Color(style.text);

    left.addSpacer(2);
    const peakLine = left.addText(
      peakFt != null ? `${peakFt.toFixed(2)} ft` : "—"
    );
    peakLine.font = Font.semiboldSystemFont(16);
    peakLine.textColor = new Color("#222");

    const timeLine = left.addText(formatTimeShort(peakTime));
    timeLine.font = Font.systemFont(11);
    timeLine.textColor = new Color("#555");

    if (hToPeak != null) {
      const htp = left.addText(formatHoursToPeak(hToPeak));
      htp.font = Font.systemFont(9);
      htp.textColor = new Color("#666");
    }

    left.addSpacer(4);
    if (exceeded) {
      const landLine = left.addText(`★ ${exceeded.label}`);
      landLine.font = Font.semiboldSystemFont(12);
      landLine.textColor = new Color(style.text);
      const depthLine = left.addText(`+${exceeded.depth.toFixed(1)}″`);
      depthLine.font = Font.systemFont(11);
      depthLine.textColor = new Color("#444");
    } else if (rel != null) {
      const relLine = left.addText(
        `${rel >= 0 ? "+" : ""}${rel.toFixed(1)}″ rel`
      );
      relLine.font = Font.systemFont(11);
      relLine.textColor = new Color("#666");
    }

    // Right column
    const right = row.addStack();
    right.layoutVertically();
    if (summary) {
      const sumText = right.addText(summary);
      sumText.font = Font.systemFont(11);
      sumText.textColor = new Color("#333");
      sumText.lineLimit = 4;
    }
    right.addSpacer(4);
    if (conf) {
      const confTxt = confUnc != null
        ? `Confidence: ${conf.toUpperCase()} (±${confUnc.toFixed(2)} ft)`
        : `Confidence: ${conf.toUpperCase()}`;
      const confLine = right.addText(confTxt);
      confLine.font = Font.semiboldSystemFont(10);
      confLine.textColor = new Color("#555");
    }
    if (cold) {
      const coldLine = right.addText("Cold conditions (hypothesis open)");
      coldLine.font = Font.systemFont(9);
      coldLine.textColor = new Color("#3a5b88");
    }
    if (watchStr) {
      const wLine = right.addText(watchStr);
      wLine.font = Font.systemFont(9);
      wLine.textColor = new Color("#666");
    }
  } else {
    // Small widget — single column, key info
    const regLabel = w.addText(regime.toUpperCase());
    regLabel.font = Font.boldSystemFont(20);
    regLabel.textColor = new Color(style.text);
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
        `${rel >= 0 ? "+" : ""}${rel.toFixed(1)}″ vs lowest corner`
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

  // Footer (visible on both sizes if space allows): updated timestamp
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
  // Running in the Scriptable app itself — preview both sizes.
  await widget.presentMedium();
}

Script.complete();
