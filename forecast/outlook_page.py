#!/usr/bin/env python3
"""docs/outlook.html: the 7-day outlook page (2026-09-23).

Consumes a completed forecast dict (its `outlook_7d` field) and returns
HTML; never fetches. Visual grammar follows the site: y axis in inches
relative to the SW grate, blue for tide+surge, gray for production,
dashed landmark lines. Two layers on every element: the honest
astronomical number and the labeled guidance number with its source.
"""

import datetime as dt
import html
import json

try:
    from .station_time import parse_station_local_time
except ImportError:                      # run as a script from forecast/
    from station_time import parse_station_local_time

GRATE_SW_MLLW = 6.34
# Landmark reference lines: the SAME five, colors, dash and labels as the
# landing-page water chart (shared palette; legend datasets learned by
# color). Inches vs the SW grate.
LANDMARK_LINES = (
    ("SW grate 0″ (ground)", 0.0, "#222222", True),
    ("gutter +3.1″ (move the car)", 3.1, "#2f8f5f", False),
    ("curb +7.7″ (flood onset)", 7.7, "#c0392b", False),
    ("lawn step +13.7″", 13.7, "#7c4dbc", False),
    ("1st porch step top +22.7″", 22.7, "#6d4c2f", False),
)
# Standard frame of the landing chart: [-60, +36] inches, expanded only
# when data or a reference line would be clipped.
Y_FRAME = (-60, 36)
SOURCE_LABELS = {
    "nws_product": "NWS coastal flood product",
    "nwps": "NWS gauge forecast (shadow)",
    "petss_mid": "P-ETSS mid-band (GEFS surge)",
    "persist_decay": "persistence, decayed (assumption)",
    "astro": "astronomy only (no surge guidance)",
}
SOURCE_SHORT = {"nws_product": "NWS product", "nwps": "NWS gauge fcst",
                "petss_mid": "P-ETSS mid", "persist_decay": "persist. decayed",
                "astro": "astro only", "nws-coastal-flood-product": "NWS product",
                "surge-persistence": "persistence", "astronomical-only-degraded": "astro (degraded)"}
REGIME_LABEL = {"dry": "no flooding", "street": "street water", "light": "light flooding",
                "moderate": "moderate flooding", "severe": "severe flooding",
                "cold_lockout": "cold lockout", "unknown": "unknown (no rain forecast)"}
RAIN_SOURCE = {"nws_grid": "NWS grid", "nbm": "NBM 6-h", "wpc_24h": "WPC 24-h"}
CHART_TAGS = (
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js" '
    'integrity="sha384-FcQlsUOd0TJjROrBxhJdUhXTUgNJQxTMcxZe6nHbaEfFL1zjQ+bq/uRoBQxb0KMo" '
    'crossorigin="anonymous"></script>')


def _e(v):
    return html.escape("" if v is None else str(v))


def _ft(v):
    return "—" if v is None else f"{v:.2f} ft"


def _inch(mllw):
    return None if mllw is None else round((mllw - GRATE_SW_MLLW) * 12.0, 1)


def _short_time(stamp):
    try:
        t = parse_station_local_time(stamp)
    except (TypeError, ValueError):
        return _e(stamp)
    return t.strftime("%a %-I:%M %p").replace(":00", "")


def _day_title(day):
    d = dt.date.fromisoformat(day["date"])
    return f"{day['label']} · {d.strftime('%a %-m/%-d')}"


def _regime_word(r):
    return REGIME_LABEL.get(r or "dry", r or "dry")


# ---------------------------------------------------------------------------
def _intro(ol, forecast):
    reach = ol.get("reach") or {}
    a = ol.get("assumptions") or {}
    src = ol.get("sources") or {}

    def ok(k):
        return (src.get(k) or {}).get("status") == "ok"
    grid_qpf_end = (reach.get("grid_qpf_end_utc") or "")[:16].replace("T", " ")
    items = [
        ("Astronomical tide", "NOAA predictions for every high tide in the next 7 days. "
         "This is the honest floor: it needs no model."),
        ("NWS coastal flood product", "forecaster tide table, used when an advisory or "
         "warning is active, about 3 days."),
        ("NWS gauge forecast for Sandy Hook", "the forecasters' hourly water level, 72 h, "
         "every day. SHADOW: shown and scored, not yet the production surge source."),
        ("P-ETSS", "NOAA's GEFS-based probabilistic surge, hourly to 102 h; the shaded "
         "band is its 10th to 90th percentile and the line is the midpoint."),
        ("Beyond 102 h", f"this hour's surge decayed with a {a.get('persistence_decay_tau_h', 48):.0f}-hour "
         "e-folding time. That decay is an ASSUMPTION scored by the shadow ledger; astronomy "
         "is the only honest number there."),
        ("Rain", f"NWS grid amounts to {grid_qpf_end}Z, then the National Blend of Models (NBM) "
         "6-h amounts to 7 days, WPC daily totals as fallback. Rain chance is the NWS grid to 7 days. "
         "NBM's probabilistic file adds the 10th/50th/90th percentile amounts and the chance of "
         "0.25, 0.5 and 1 in per 6 h: the rain band's high end is the 90th percentile run through "
         "the same tank model, labeled as such."),
        ("Wind", "NWS grid gusts and direction to 7 days."),
        ("Model cross-check", "four global models and a 31-member ensemble from a non-NOAA "
         "service. Never an input; shown so a large disagreement is visible."),
    ]
    lis = "".join(f"<li><b>{_e(k)}:</b> {_e(v)}</li>" for k, v in items)
    return f"""
  <section class="outlook-intro">
    <h2>How to read this page</h2>
    <p><b>Two pathways, every day.</b> Tidal flooding is one; rain flooding is the other, and it can be
    the worse one at low tide when the input rate beats the drains. Each day card's headline is the worst
    of the two, and the chart draws both. The <b>astronomical tide</b> is the honest part:
    it is known years ahead. The <b>guidance</b> layer adds surge, rain and wind from the
    sources below, each labeled with where it comes from and how far it reaches. The
    production forecast on the <a href="index.html">landing page</a> and its alerts are
    unchanged by this page; alerts consider only the next 48 hours.</p>
    <ul class="more-info-list">{lis}</ul>
  </section>"""


def _xcheck_block(day):
    m = day.get("xcheck_models") or {}
    ens = day.get("xcheck_ensemble") or {}
    if not m and not ens:
        return ""
    cells = "".join(
        f"<li>{_e(name.upper())}: {('%.2f in' % v['precip_in']) if v.get('precip_in') is not None else '—'}"
        f", gust {('%.0f mph' % v['gust_mph']) if v.get('gust_mph') is not None else '—'}</li>"
        for name, v in m.items())
    ens_line = ""
    if ens:
        ens_line = (f"<li>GEFS ensemble ({ens.get('members')} members): "
                    f"{ens.get('p_half_inch_pct')}% chance of more than 0.5 in; median "
                    f"{ens.get('median_in')} in, 90th pct {ens.get('p90_in')} in, max {ens.get('max_in')} in; "
                    f"gust median {ens.get('gust_median_mph')} mph, max {ens.get('gust_max_mph')} mph</li>")
    return (f'<details class="xcheck"><summary>Model cross-check (non-NOAA)</summary>'
            f'<ul>{cells}{ens_line}</ul></details>')


def _rain_line(rp):
    """The rain pathway on a card: tank line peak and burst scenario, each
    with its regime; never gated by the tide."""
    if not rp:
        return "Rain pathway: —"
    if not rp.get("rain_available"):
        return "Rain pathway: NO rain forecast for this day — unknown, not dry"
    bits = []
    if rp.get("rain_coverage") is not None and rp["rain_coverage"] < 1.0:
        bits.append(f"rain known for {rp.get('rain_known_hours')} of {rp.get('rain_hours')} hours "
                    f"(the rest is unknown, not dry)")
    if rp.get("tank_peak_navd88") is not None:
        inch = (rp["tank_peak_navd88"] - 3.52) * 12.0
        bits.append(f"tank line peaks <b>{inch:+.1f}\u2033</b> vs SW grate at {_e(rp.get('tank_peak_time'))} "
                    f"({_e(_regime_word(rp.get('tank_regime')))})")
    else:
        bits.append(f"tank line stays below the grate (peak rate {rp.get('peak_rate_in_hr', 0):.2f} in/hr, "
                    f"max 6-h {rp.get('max_6h_in', 0):.2f} in)")
    if rp.get("burst_potential_navd88") is not None:
        inch = (rp["burst_potential_navd88"] - 3.52) * 12.0
        bits.append(f"burst scenario {rp.get('burst_est_in_hr'):.1f} in/hr → potential <b>{inch:+.1f}\u2033</b> "
                    f"({_e(_regime_word(rp.get('burst_regime')))})")
    elif rp.get("burst_signal"):
        bits.append("burst-capable hours flagged, magnitude below the potential threshold")
    if rp.get("burst_at_high_tide_navd88") is not None:
        inch = (rp["burst_at_high_tide_navd88"] - 3.52) * 12.0
        ht = rp.get("high_tide_navd88")
        bits.append(f"the same burst on the day's high tide ({(ht + 2.82):.1f} ft MLLW) → "
                    f"<b>{inch:+.1f}\u2033</b> ({_e(_regime_word(rp.get('burst_at_high_tide_regime')))})")
    if rp.get("nbm_p90_6h_in") is not None:
        chance = rp.get("nbm_p_ge_half_in_6h_pct")
        chance_txt = f"{chance:.0f}% chance of ≥0.5 in in 6 h" if chance is not None else "chance n/a"
        if rp.get("nbm_p90_potential_navd88") is not None:
            inch = (rp["nbm_p90_potential_navd88"] - 3.52) * 12.0
            hi = ""
            if rp.get("nbm_p90_at_high_tide_navd88") is not None:
                hi = (f", on the high tide <b>{(rp['nbm_p90_at_high_tide_navd88'] - 3.52) * 12.0:+.1f}\u2033</b> "
                      f"({_e(_regime_word(rp.get('nbm_p90_at_high_tide_regime')))})")
            bits.append(f"NBM 90th-pct rain {rp['nbm_p90_6h_in']:.2f} in/6 h → potential <b>{inch:+.1f}\u2033</b> "
                        f"({_e(_regime_word(rp.get('nbm_p90_regime')))}){hi}; {chance_txt}")
        else:
            bits.append(f"NBM 90th-pct rain {rp['nbm_p90_6h_in']:.2f} in/6 h; {chance_txt}")
    return "Rain pathway: " + "; ".join(bits)


def _worst_line(ol):
    w = ol.get("worst") or {}
    t, f = w.get("tide") or {}, w.get("flood_chance") or {}
    if not f:
        return ""
    def inch(v):
        return f"{(v - 3.52) * 12.0:+.1f}\u2033"
    return (f'<p><b>Worst flood chance in the next 7 days:</b> {inch(f["navd88"])} vs the SW grate '
            f'at {_e(_short_time(f["time"]))} via <b>{_e(f.get("pathway"))}</b>. '
            f'Worst tide: {inch(t["navd88"])} at {_e(_short_time(t["time"]))}. '
            f'The two are not the same question: rain can flood this corner at low tide.</p>')


def _day_cards(ol):
    cards = []
    for i, d in enumerate(ol.get("days") or []):
        regime = d.get("regime_max") or "dry"
        pathway = d.get("worst_pathway") or "tide"
        src = SOURCE_LABELS.get(d.get("outlook_source") or "astro", d.get("outlook_source") or "")
        rp = d.get("rain_pathway") or {}
        tidal_regime = d.get("tidal_regime_max") or regime
        tides = ", ".join(
            f"{_e(t['time'])} {t['outlook_mllw']:.1f}" if t.get("outlook_mllw") is not None else _e(t["time"])
            for t in d.get("tides") or [])
        band = ""
        if d.get("band_hi_max_mllw") is not None:
            band = (f'<p class="dc-line">Guidance high end: <b>{d["band_hi_max_mllw"]:.2f} ft</b> '
                    f'({_e(_regime_word(d.get("regime_hi_max")))}) at the P-ETSS 90th percentile</p>')
        rain = "Rain: —"
        if d.get("qpf_in") is not None:
            rain = (f"Rain: <b>{d['qpf_in']:.2f} in</b> ({_e(RAIN_SOURCE.get(d.get('qpf_source'), d.get('qpf_source')))})")
        pop = f" · chance {d['pop_max_pct']:.0f}%" if d.get("pop_max_pct") is not None else ""
        wind = "Wind: —"
        if d.get("gust_max_mph") is not None:
            wind = f"Wind: gusts to <b>{d['gust_max_mph']:.0f} mph</b> {_e(d.get('gust_dir') or '')}"
        cls = "day-card day-card-today" if i == 0 else "day-card"
        cards.append(f"""
    <div class="{cls} regime-{_e(regime)}">
      <h3>{_e(_day_title(d))}</h3>
      <p class="dc-line"><b>{_e(_regime_word(regime).upper())}</b> <span class="note">— worst pathway: {_e(pathway)}</span></p>
      <p class="dc-line">Tide: astronomy <b>{_ft(d.get('astro_max_mllw'))}</b>, with guidance <b>{_ft(d.get('outlook_max_mllw'))}</b>
         → {_e(_regime_word(tidal_regime))} <span class="note">({_e(src)})</span></p>
      {band}
      <p class="dc-line">{_rain_line(rp)}</p>
      <p class="dc-line">Tides: {tides}</p>
      <p class="dc-line">{rain}{pop}</p>
      <p class="dc-line">{wind}</p>
      {_xcheck_block(d)}
    </div>""")
    return (f'<section><h2>Seven days at the corner</h2>{_worst_line(ol)}'
            f'<div class="day-cards">{"".join(cards)}</div></section>')


def _chart(ol):
    series = ol.get("series") or []
    tides = ol.get("tides") or []
    if not series:
        return _peaks_chart(ol)
    pot_by_day = ((ol.get("worst") or {}).get("burst_potential_by_day")) or {}

    def inch_navd(v):
        return None if v is None else round((v - 3.52) * 12.0, 1)
    labels = [_short_time(p["time"]) for p in series]
    tide = [inch_navd(p.get("tide_navd88")) for p in series]
    astro = [_inch(p.get("astro_mllw")) for p in series]
    pluv = [inch_navd(p.get("pluvial_navd88")) for p in series]
    burst = []
    for p in series:
        pot = pot_by_day.get(p["time"][:10])
        burst.append(inch_navd(max(pot, p["tide_navd88"])) if (p.get("burst_risk") and pot is not None) else None)
    src = [p.get("surge_source") for p in series]
    now_i = next((i for i, p in enumerate(series) if (p.get("lead_h") or 0) >= 0), 0)
    data = {"labels": labels, "tide": tide, "astro": astro, "pluv": pluv, "burst": burst,
            "src": src, "now_i": now_i,
            "landmarks": [{"label": n, "y": y, "color": c, "solid": solid}
                          for n, y, c, solid in LANDMARK_LINES]}
    all_vals = [v for k in ("tide", "astro", "pluv", "burst") for v in data[k] if v is not None] + \
               [y for _n, y, _c, _s in LANDMARK_LINES]
    data["y_min"] = min(Y_FRAME[0], (min(all_vals) - 3) if all_vals else Y_FRAME[0])
    data["y_max"] = max(Y_FRAME[1], (max(all_vals) + 3) if all_vals else Y_FRAME[1])
    aria = ("Seven-day water level at the corner in inches relative to the SW grate: tide plus "
            "guidance surge (blue), rain street-water from the tank model (amber), burst "
            "scenario band (navy) on burst-capable hours.")
    payload = json.dumps(data)
    script = """
<script>
(function () {
  var D = __DATA__;
  var el = document.getElementById('outlook-series-chart');
  if (!el || typeof Chart === 'undefined') { return; }
  var datasets = [
    { label: 'Burst scenario (rain, no clock)', data: D.burst, borderWidth: 0,
      backgroundColor: 'rgba(11,61,107,0.30)', pointRadius: 0, fill: { target: 2 }, spanGaps: false },
    { label: 'Rain street-water (tank line)', data: D.pluv, borderColor: '#d97706',
      backgroundColor: '#d97706', borderWidth: 2, pointRadius: 0, tension: 0.2, spanGaps: false },
    { label: 'Tide + guidance surge (bay water)', data: D.tide, borderColor: '#1a5fa8',
      borderWidth: 2, pointRadius: 0, tension: 0.3 },
    { label: 'Astronomical tide only', data: D.astro, borderColor: '#7aa6d8', borderDash: [6, 4],
      borderWidth: 1.2, pointRadius: 0, tension: 0.3 }
  ];
  D.landmarks.forEach(function (lm) {
    datasets.push({ label: lm.label, data: D.labels.map(function () { return lm.y; }),
      borderColor: lm.color, borderWidth: lm.solid ? 1.5 : 1.2,
      borderDash: lm.solid ? [] : [6, 5], fill: false, pointRadius: 0 });
  });
  var nowLine = { id: 'nowLine', afterDraw: function (chart) {
    var x = chart.scales.x.getPixelForValue(D.now_i), c = chart.ctx, a = chart.chartArea;
    c.save(); c.strokeStyle = '#222'; c.lineWidth = 1.2; c.beginPath();
    c.moveTo(x, a.top); c.lineTo(x, a.bottom); c.stroke(); c.restore(); } };
  new Chart(el, { type: 'line', data: { labels: D.labels, datasets: datasets }, plugins: [nowLine],
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      scales: { y: { title: { display: true, text: 'inches vs SW grate (\u00b1 = above/below)' },
                     min: D.y_min, max: D.y_max },
                x: { ticks: { maxTicksLimit: 14, maxRotation: 50, font: { size: 10 } } } },
      plugins: { legend: { display: true, labels: { boxWidth: 22, boxHeight: 2, font: { size: 10 } } } } } });
})();
</script>"""
    return (f'<section><h2>Water at the corner, next 7 days</h2>'
            f'<p class="note">Same grammar as the landing chart: blue is bay water (astronomical tide plus '
            f'guidance surge: NWS gauge forecast inside 72 h, then P-ETSS, then decayed persistence); '
            f'amber is rain street-water from the production tank model driven by the forecast rain '
            f'(NWS grid, then NBM); the navy band is the burst scenario on burst-capable hours, drawn as a '
            f'level because a burst has no knowable clock. Dashed light blue is astronomy alone. The frame '
            f'is the landing chart\'s standard \u221260 to +36 inches; the vertical line is now.</p>'
            f'<div style="position:relative;height:380px"><canvas id="outlook-series-chart" role="img" '
            f'aria-label="{_e(aria)}"></canvas></div>{CHART_TAGS}'
            + script.replace("__DATA__", payload) + "</section>")


def _peaks_chart(ol):
    tides = ol.get("tides") or []
    labels = [_short_time(t["time"]) for t in tides]
    def series(key):
        return [_inch(t.get(key)) for t in tides]
    data = {
        "labels": labels,
        "astro": series("astro_mllw"),
        "outlook": series("outlook_mllw"),
        "lo": series("band_lo_mllw"),
        "hi": series("band_hi_mllw"),
        "production": series("production_mllw"),
        "sources": [t.get("outlook_source") for t in tides],
        "landmarks": [{"label": n, "y": y, "color": c, "solid": solid}
                      for n, y, c, solid in LANDMARK_LINES],
    }
    all_vals = [v for k in ("astro", "outlook", "lo", "hi", "production")
                for v in data[k] if v is not None] + [y for _n, y, _c, _s in LANDMARK_LINES]
    data["y_min"] = min(Y_FRAME[0], (min(all_vals) - 3) if all_vals else Y_FRAME[0])
    data["y_max"] = max(Y_FRAME[1], (max(all_vals) + 3) if all_vals else Y_FRAME[1])
    aria = ("Seven-day high-tide outlook at Sandy Hook in inches relative to the SW grate: "
            + "; ".join(f"{l} {o:+.0f} in" for l, o in zip(labels, data["outlook"]) if o is not None))
    payload = json.dumps(data)
    script = """
<script>
(function () {
  var D = __DATA__;
  var el = document.getElementById('outlook-peaks-chart');
  if (!el || typeof Chart === 'undefined') { return; }
  var datasets = [
    { label: 'Guidance band (P-ETSS 10-90%)', data: D.hi, borderWidth: 0,
      backgroundColor: 'rgba(26,95,168,0.15)', pointRadius: 0, fill: '+1', spanGaps: false },
    { label: 'band low', data: D.lo, borderWidth: 0, pointRadius: 0, fill: false, spanGaps: false },
    { label: 'Outlook (tide + guidance)', data: D.outlook, borderColor: '#1a5fa8',
      backgroundColor: '#1a5fa8', borderWidth: 2.5, pointRadius: 4, tension: 0.2,
      pointStyle: D.sources.map(function (s) { return s === 'astro' ? 'crossRot' : (s === 'persist_decay' ? 'triangle' : 'circle'); }) },
    { label: 'Astronomical tide only', data: D.astro, borderColor: '#7aa6d8', borderDash: [6, 4],
      borderWidth: 1.5, pointRadius: 2, tension: 0.2 },
    { label: 'Production forecast (landing page, 72 h)', data: D.production, borderColor: '#555555',
      backgroundColor: '#555555', borderWidth: 0, pointRadius: 5, pointStyle: 'rectRot', showLine: false }
  ];
  D.landmarks.forEach(function (lm) {
    datasets.push({ label: lm.label, data: D.labels.map(function () { return lm.y; }),
      borderColor: lm.color, borderWidth: lm.solid ? 1.5 : 1.2,
      borderDash: lm.solid ? [] : [6, 5], fill: false, pointRadius: 0 });
  });
  new Chart(el, { type: 'line', data: { labels: D.labels, datasets: datasets },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      scales: { y: { title: { display: true, text: 'inches vs SW grate (\u00b1 = above/below)' },
                     min: D.y_min, max: D.y_max },
                x: { ticks: { maxRotation: 60, autoSkip: true, font: { size: 10 } } } },
      plugins: { legend: { display: true, labels: { boxWidth: 22, boxHeight: 2, font: { size: 10 },
                 filter: function (i) { return i.text !== 'band low'; } } } } } });
})();
</script>"""
    return (f'<section><h2>High tides with the surge band, next 7 days</h2>'
            f'<p class="note">Restored at John\'s request (2026-09-23): the per-tide view with the P-ETSS 10th to 90th percentile band, which is where a tide\'s reasonable high end shows (Saturday\'s band reaches the first porch step). Blue line: outlook with guidance (circle = NWS/P-ETSS guidance, triangle = '
            f'decayed persistence, cross = astronomy only). Dashed light blue: astronomy alone. Shaded: '
            f'P-ETSS 10th to 90th percentile surge band. Gray diamonds: the production forecast for the '
            f'same tides. Landmark lines are the same five as the landing chart, in the same colors. '
            f'The frame is the landing chart\'s standard \u221260 to +36 inches and only widens if a line would be clipped.</p>'
            f'<div style="position:relative;height:360px"><canvas id="outlook-peaks-chart" role="img" '
            f'aria-label="{_e(aria)}"></canvas></div>{CHART_TAGS}'
            + script.replace("__DATA__", payload) + "</section>")


def _tide_table(ol):
    rows = []
    for t in ol.get("tides") or []:
        band = ("—" if t.get("band_lo_mllw") is None
                else f"{t['band_lo_mllw']:.2f}–{t['band_hi_mllw']:.2f}")
        rain = t.get("rain") or {}
        rain_txt = ("—" if rain.get("qpf_in") is None
                    else f"{rain['qpf_in']:.2f} in ({_e(RAIN_SOURCE.get(rain.get('source'), rain.get('source')))})")
        wind = t.get("wind") or {}
        wind_txt = ("—" if wind.get("gust_mph") is None
                    else f"{wind['gust_mph']:.0f} mph {_e(_compass(wind.get('dir_deg')))}")
        prod = ("—" if t.get("production_mllw") is None
                else f"{t['production_mllw']:.2f} ({_e(SOURCE_SHORT.get(t.get('production_source'), t.get('production_source')))})")
        xc = "—" if t.get("xcheck_p_half_inch_pct") is None else f"{t['xcheck_p_half_inch_pct']}%"
        rows.append(
            f'<tr class="regime-{_e(t.get("regime") or "dry")}">'
            f'<td>{_e(_short_time(t["time"]))}</td><td>{t["lead_h"]:+.0f} h</td>'
            f'<td>{t["astro_mllw"]:.2f}</td>'
            f'<td><b>{t["outlook_mllw"]:.2f}</b> <span class="note">{_e(SOURCE_SHORT.get(t.get("outlook_source"), t.get("outlook_source")))}</span></td>'
            f'<td>{band}</td><td>{_e(_regime_word(t.get("regime")))}'
            + (f' <span class="note">(up to {_e(_regime_word(t.get("regime_hi")))})</span>' if t.get("regime_hi") and t.get("regime_hi") != t.get("regime") else "")
            + f'</td><td>{t["grate_sw_in"] if t.get("grate_sw_in") is not None else "—"}</td>'
            f'<td>{t["curb_in"] if t.get("curb_in") is not None else "—"}</td>'
            f'<td>{prod}</td><td>{rain_txt}</td>'
            f'<td>{("%.0f%%" % t["pop_pct"]) if t.get("pop_pct") is not None else "—"}</td>'
            f'<td>{wind_txt}</td>'
            f'<td>{("%.0f%%" % t["nbm_p_ge_half_in_6h_pct"]) if t.get("nbm_p_ge_half_in_6h_pct") is not None else "—"}</td>'
            f'<td>{xc}</td></tr>')
    return f"""
  <section>
    <h2>Every high tide</h2>
    <p class="note">ft MLLW at Sandy Hook. Depths are inches of water over the SW grate and the curb top
    at the outlook value. "Production" is what the landing page and alerts use for the same tide.
    "NBM P(≥0.5 in/6 h)" is NOAA's blend probability that the 6-hour bucket holding this tide gets
    half an inch or more; the last column is the non-NOAA ensemble's chance for the whole day (cross-check).</p>
    <div class="table-wrap"><table class="tide-table">
      <thead><tr><th>High tide</th><th>Lead</th><th>Astro</th><th>Outlook (source)</th><th>Band</th>
      <th>Regime</th><th>SW grate in</th><th>Curb in</th><th>Production</th><th>Rain 6 h</th>
      <th>Chance</th><th>Gust</th><th>NBM P(&ge;0.5 in/6 h)</th><th>Ens &gt;0.5 in</th></tr></thead>
      <tbody>{"".join(rows)}</tbody></table></div>
  </section>"""


def _compass(deg):
    if deg is None:
        return ""
    pts = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return pts[int((float(deg) + 11.25) // 22.5) % 16]


def _shadow(ol):
    sh = ol.get("shadow") or {}
    rd = sh.get("readiness") or {}
    names = {
        "nwps_vs_persistence_le72h": "NWS gauge forecast vs production persistence (≤72 h)",
        "product_vs_persistence_le72h": "NWS coastal product vs persistence (≤72 h)",
        "decay_vs_flat_persistence_le168h": "Decayed vs flat persistence (all leads)",
        "outlook_vs_production_le72h": "Outlook line vs production forecast (≤72 h)",
    }
    lis = []
    for key, label in names.items():
        r = rd.get(key) or {}
        mae = ("" if r.get("mae_candidate") is None
               else f" — MAE {r['mae_candidate']:.2f} vs {r['mae_baseline']:.2f} ft on {r.get('n')} tides "
                    f"({r.get('n_forecasts')} forecasts)")
        lis.append(f"<li><b>{_e(label)}:</b> {_e(r.get('verdict', 'NO DATA YET'))}{_e(mae)}</li>")
    buckets = sh.get("buckets") or []
    cols = ["astro", "nws_product", "nwps", "petss_p10", "petss_p90", "persist_flat",
            "persist_decay", "production", "outlook"]
    head = "".join(f"<th>{_e(c)}</th>" for c in cols)
    body = ""
    for b in buckets:
        cells = ""
        for c in cols:
            s = (b.get("sources") or {}).get(c)
            cells += ("<td>—</td>" if not s else
                      f"<td>{s['mae']:.2f}<br><span class=\"note\">{s['bias']:+.2f}, {s['n']} tides / {s.get('n_forecasts', '?')} fc</span></td>")
        body += f"<tr><td>{_e(b['label'])}</td>{cells}</tr>"
    return f"""
  <section>
    <h2>Shadow scoreboard: should guidance be promoted?</h2>
    <p class="note">Every run logs each source's value for each tide (data/outlook_log.csv, append-only).
    Once a tide's observed peak is known, every source is scored against it. Sampling rule: within each
    lead bucket every observed TIDE counts once (its issuances are averaged first), then error is taken
    across tides; candidate and baseline are paired on the same tides, and READY needs 28 distinct scored
    tides. Scored so far: {sh.get('scored_tides', 0)} tides from {sh.get('scored_rows', 0)} forecast rows.</p>
    <ul class="more-info-list">{"".join(lis)}</ul>
    <div class="table-wrap"><table class="tide-table">
      <thead><tr><th>Lead</th>{head}</tr></thead><tbody>{body}</tbody></table></div>
    <p class="note">Cells: mean absolute error in ft of the Sandy Hook tide PEAK (gauge skill, not street depth), then bias, distinct tides and forecast rows.</p>
  </section>"""


def _sources(ol):
    rows = ""
    for k, h in (ol.get("sources") or {}).items():
        rows += (f"<tr><td>{_e(k)}</td><td>{_e((h or {}).get('status'))}</td>"
                 f"<td>{_e((h or {}).get('detail'))}</td></tr>")
    reach = ol.get("reach") or {}
    return f"""
  <section>
    <h2>Sources this run</h2>
    <div class="table-wrap"><table class="tide-table">
      <thead><tr><th>Source</th><th>Status</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table></div>
    <p class="note">NBM cycle {_e(reach.get('nbm_cycle'))} · P-ETSS cycle {_e(reach.get('petss_cycle'))} ·
    gauge forecast issued {_e(reach.get('nwps_issued'))}. Unavailable data is shown as unavailable and is
    never treated as a forecast of zero.</p>
  </section>"""


def render_outlook_page(forecast):
    ol = forecast.get("outlook_7d") or {}
    gen = forecast.get("generated_utc", "")
    body = ""
    if ol.get("tides"):
        body = (_intro(ol, forecast) + _day_cards(ol) + _chart(ol) + _tide_table(ol)
                + _shadow(ol) + _sources(ol)
                + (_peaks_chart(ol) if ol.get("series") else ""))   # bottom: the per-tide band view
    else:
        h = (forecast.get("input_health") or {}).get("outlook_7d") or {}
        body = (f'<section><h2>Outlook unavailable this run</h2><p>{_e(h.get("detail") or "no outlook data")}'
                f'. The <a href="index.html">72-hour forecast</a> is unaffected.</p></section>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="barnacle-generated-utc" content="{_e(gen)}">
<meta name="barnacle-schema-version" content="{_e(forecast.get('forecast_schema_version', ''))}">
<meta name="barnacle-model-version" content="{_e(forecast.get('model_version', ''))}">
<title>Bay Ave Barnacle — 7-day outlook</title>
<link rel="stylesheet" href="style.css">
<style>
  .outlook-intro li {{ margin: 4px 0; }}
  details.xcheck {{ margin-top: 6px; font-size: 13px; }}
  details.xcheck summary {{ cursor: pointer; color: #1a5fa8; }}
  .table-wrap {{ overflow-x: auto; }}
</style>
</head>
<body>
<main>
  <header>
    <h1><a href="index.html" style="text-decoration:none;color:inherit">Bay Ave Barnacle</a> — 7-day outlook</h1>
    <p class="subtitle"><a href="index.html">&larr; back to the 72-hour forecast</a> &middot; astronomy plus labeled guidance &middot; generated {_e(gen)}</p>
  </header>
{body}
  <footer>
    <p><a href="index.html">&larr; back to the live forecast</a> &middot;
       <a href="details.html">details &amp; reference</a> &middot;
       <a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a></p>
  </footer>
</main>
</body>
</html>
"""
