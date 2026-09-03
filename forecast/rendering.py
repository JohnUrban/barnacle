"""Bay Ave Barnacle — rendering (SEAM 2 of the Phase-3 module split,
extracted 2026-09-02; see forecast/README.md "Forecast code boundaries",
seam `rendering`).

Email, site, details, and per-tide page renderers plus their text/HTML
section builders, moved VERBATIM from flood_forecast_daily.py. Every
function here consumes a completed forecast object (and already-fetched
series/context passed in by the caller) and returns strings/fragments;
nothing here fetches live data, writes files, sends email, computes
model physics, or touches ledgers. flood_forecast_daily.py remains the
compatibility facade and re-exports every name below at its tail.

Deliberately left in the facade: _render_water_series_section and
_render_historical_floods_html (open ledger/CSV files directly),
_render_heatmap (writes the map PNG via subprocess),
_render_equation_widget_html (reads PLUVIAL_VOLUME_K/POW_K/POW_GAMMA,
which _load_stage_curve() rebinds via `global` at runtime — a
from-import here would freeze them at None), and build_sms_text
(calls compute_alert_level, which reads live docs/nowcast.json).
"""

# Shared constants and helpers stay in the facade; import them
# explicitly (same try/except relative-import pattern as station_time
# in flood_forecast_daily.py). One addition for script mode: when the
# facade runs as `python3 flood_forecast_daily.py`, it exists in
# sys.modules only as "__main__" — alias it first so the plain import
# below binds to that SAME module object instead of re-executing the
# whole facade (which would fork its lazily-calibrated globals).
import sys as _sys

try:
    from .flood_forecast_daily import (  # noqa: F401
        CURRENT_MODEL_VERSION, FLOOD_WINDOW_KEYS, GRATE_SW, LANDMARKS,
        LOCAL_ENHANCEMENT_FT, LOOKAHEAD_DAYS, MLLW_TO_NAVD88_OFFSET,
        PAST_TIDE_VISIBILITY_HOURS, REGIME_GLOSSARY, SEVERITY_RANK,
        SH_FIRST_WATER, _client_map_section_html,
        _compute_classifier_metrics, _compute_leadtime_accuracy,
        _confidence_qualifier_sentences, _degraded_health_rows,
        _flood_peaks_chart_data, _fmt_metric,
        _high_value_calibration_callouts, _html_escape,
        _landmarks_footer_html, _landmarks_footer_text, _load_accuracy_rows,
        _load_outcome_depth_rows, _lookahead_label, _nowcast_cadence_stats,
        _oscillation_chart_data, _per_tide_log_stats, _rain_is_notable,
        _render_equation_widget_html, _render_historical_floods_html,
        _render_water_series_section, _station_local_now,
        _station_local_today, _tide_confidence, _tide_slug,
        _unified_landmark_table_html, _unified_landmark_table_text,
        _unusual_forecast_text, _upcoming_tides_only, dt,
        estimate_pluvial_water_models, format_date_short, format_time_full,
        format_time_short, headline_for, json, landmark_summary,
        regime_display)
except ImportError:                      # run as a script from forecast/
    _ffmain = _sys.modules.get("__main__")
    if ("flood_forecast_daily" not in _sys.modules
            and getattr(_ffmain, "build_forecast", None) is not None):
        _sys.modules["flood_forecast_daily"] = _ffmain
    from flood_forecast_daily import (   # noqa: F401
        CURRENT_MODEL_VERSION, FLOOD_WINDOW_KEYS, GRATE_SW, LANDMARKS,
        LOCAL_ENHANCEMENT_FT, LOOKAHEAD_DAYS, MLLW_TO_NAVD88_OFFSET,
        PAST_TIDE_VISIBILITY_HOURS, REGIME_GLOSSARY, SEVERITY_RANK,
        SH_FIRST_WATER, _client_map_section_html,
        _compute_classifier_metrics, _compute_leadtime_accuracy,
        _confidence_qualifier_sentences, _degraded_health_rows,
        _flood_peaks_chart_data, _fmt_metric,
        _high_value_calibration_callouts, _html_escape,
        _landmarks_footer_html, _landmarks_footer_text, _load_accuracy_rows,
        _load_outcome_depth_rows, _lookahead_label, _nowcast_cadence_stats,
        _oscillation_chart_data, _per_tide_log_stats, _rain_is_notable,
        _render_equation_widget_html, _render_historical_floods_html,
        _render_water_series_section, _station_local_now,
        _station_local_today, _tide_confidence, _tide_slug,
        _unified_landmark_table_html, _unified_landmark_table_text,
        _unusual_forecast_text, _upcoming_tides_only, dt,
        estimate_pluvial_water_models, format_date_short, format_time_full,
        format_time_short, headline_for, json, landmark_summary,
        regime_display)


def _render_summary_text(forecast):
    """One-line plain-language summary, plus confidence + unusual-forecast
    note (when applicable) on their own lines."""
    out = []
    # day cards (2026-07-20) replaced the per-tide sentence list;
    # this block now carries the outage notice + confidence + unusual
    summary = ""
    if summary:
        out.append(summary)
    level = forecast.get("confidence_level")
    reason = forecast.get("confidence_reason") or ""
    if level:
        # Primary line: badge + reason
        out.append(f"Confidence: {level.upper()} — {reason}")
        # Augment lines for non-high confidence (HANDOFF 9b.6)
        for extra in _confidence_qualifier_sentences(forecast):
            out.append(f"  {extra}")
    unusual = _unusual_forecast_text(forecast)
    if unusual:
        out.append(unusual)
    return out


def _render_day_cards_html(forecast):
    """DAY CARDS (user redesign 2026-07-20): the 72-h window organized
    by calendar day - TODAY / TOMORROW / day-3 - each card holding its
    own tides, rain outlook, and regime badge, with a WORST ribbon on
    the window's worst day. Replaces the TODAY box, WORST-72H strip,
    per-tide summary sentences, and the rain-outlook box (four objects
    slicing the same 72 h differently - "mish-mashed"). Overnight
    tides sit in their calendar day labeled "Tue 2:35 AM" (user:
    everyone can interpret that). TODAY is deliberately the heaviest
    card. The FLOODING-NOW nowcast override keeps targeting
    id=today-block = the TODAY card."""
    try:
        now_l = _station_local_now()
    except Exception:
        now_l = _station_local_now()
    days = [(now_l + dt.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(3)]

    def _dk(base, i):
        d = now_l + dt.timedelta(days=i)
        return base + d.strftime("%a %b ").upper() + str(d.day)

    kickers = {days[0]: _dk("TODAY &middot; ", 0),
               days[1]: _dk("TOMORROW &middot; ", 1),
               days[2]: _dk("", 2)}
    rain_by_day = {d.get("day"): d
                   for d in (forecast.get("rain_outlook_72h") or [])}
    pr = forecast.get("pluvial_risk") or {}
    alerts = pr.get("nws_flood_alerts") or []
    peak_t = forecast.get("peak_time_local")

    def alert_covers(day):
        for a in alerts:
            on = (a.get("onset") or "")[:10]
            en = (a.get("ends") or "")[:10]
            if (not on or on <= day) and (not en or en >= day):
                yield a

    cards = []
    for day in days:
        tides = [t for t in (forecast.get("all_tides") or [])
                 if (t.get("time") or "").startswith(day)]
        tide_rank = 0
        tide_rows = []
        for t in tides:
            reg = ((t.get("depths_in") or {}).get("regime")) or "dry"
            tide_rank = max(tide_rank, SEVERITY_RANK.get(reg, 0))
            rel = ((t.get("forecast_peak_mllw") or 0)
                   + MLLW_TO_NAVD88_OFFSET - GRATE_SW) * 12
            star = "&#9733; " if t.get("time") == peak_t else ""
            past = ((t.get("hours_from_now") is not None)
                    and t["hours_from_now"] < 0)
            tide_rows.append(
                '<div class="dc-line">' + star
                + format_time_short(t["time"]) + " tide &mdash; "
                + regime_display(reg) + f" ({rel:+.1f}&Prime;)"
                + (' <span class="dc-past">(past)</span>' if past else "")
                + "</div>")
        rain = rain_by_day.get(day) or {}
        day_alerts = list(alert_covers(day))
        rain_bits = []
        if day_alerts:
            names = ", ".join(
                _html_escape(str(a.get("event", ""))) for a in day_alerts
            )
            a0 = day_alerts[0]
            on = (a0.get("onset") or "")
            span = ""
            if on[:10] == day and on[11:16]:
                hh, mm = int(on[11:13]), on[14:16]
                span = (" from " + str((hh % 12) or 12)
                        + (":" + mm if mm != "00" else "")
                        + ("AM" if hh < 12 else "PM"))
            rain_bits.append("<b>" + names + "</b>" + span)
        rain_cum = rain.get("cum_in")
        rain_pop = rain.get("max_pop_pct")
        if ((rain_cum or 0) >= 0.02 or (rain_pop or 0) >= 20):
            rain_bits.append(
                (f"~{rain_cum:.2f}&Prime; rain" if rain_cum is not None
                 else "QPF unavailable")
                + (f", PoP {rain_pop}%" if rain_pop is not None
                   else ", PoP unavailable")
                + (", thunderstorms" if rain.get("thunder") else ""))
        if rain_bits:
            rain_line = "Rain: " + "; ".join(rain_bits)
        elif rain_cum is None or rain_pop is None:
            rain_line = "Rain: forecast inputs unavailable — not assumed dry"
        else:
            rain_line = "Rain: nothing significant expected"
        rain_risky = bool(day_alerts) or bool(
            pr.get("level") and (rain.get("thunder")
                                 or (rain.get("peak_in_hr") or 0) >= 0.15))
        if tide_rank >= 2 or (tide_rank >= 1 and not rain_risky):
            badge_cls = next(k for k, v in SEVERITY_RANK.items()
                             if v == tide_rank)
            badge = regime_display(badge_cls).upper()
        elif rain_risky:
            badge = ("RAIN FLOOD RISK" if pr.get("level") == "elevated"
                     else "POSSIBLE RAIN FLOODING")
            badge_cls = "light"
        else:
            badge_cls = "dry" if tide_rank == 0 else "street"
            badge = regime_display(badge_cls).upper()
        cards.append({"day": day, "kicker": kickers[day], "badge": badge,
                      "badge_cls": badge_cls, "tide_rows": tide_rows,
                      "rain_line": rain_line,
                      "rank": (tide_rank, 1 if rain_risky else 0)})
    worst = max(cards, key=lambda c: c["rank"])
    html_cards = []
    for c in cards:
        is_today = c["day"] == days[0]
        ribbon = (' <span class="dc-worst">&#9650; WORST OF 72 H</span>'
                  if c is worst and c["rank"] > (0, 0) else "")
        extra = ""
        if is_today:
            _lb = forecast.get("today_lookback")
            if _lb and (_lb.get("rel_grate_in") or 0) > 0:
                extra = (
                    '<div class="regime-summary dc-sofar"><b>SO FAR:</b> '
                    + regime_display(_lb.get("regime") or "").upper()
                    + f' &mdash; peak {_lb["rel_grate_in"]:+.1f}&Prime; at '
                    + _lb["time_local"] + ", " + _lb["source"] + ".</div>")
        html_cards.append(
            '<section class="regime regime-' + c["badge_cls"] + ' day-card'
            + (" day-card-today" if is_today else "")
            + ('" id="today-block">' if is_today else '">')
            + '<div class="regime-kicker">' + c["kicker"] + ribbon + '</div>'
            + '<div class="regime-label">' + c["badge"] + '</div>'
            + '<div class="regime-summary">'
            + "".join(c["tide_rows"])
            + '<div class="dc-line">' + c["rain_line"] + '</div>'
            + '</div>' + extra + '</section>')
    return '<div class="day-cards">' + "".join(html_cards) + '</div>'


def _render_how_flooding_html(forecast):
    return f"""
  <section class="reference">
    <h2>How flooding works here (plain English)</h2>
    <p><b>Tide floods.</b> When the bay at Sandy Hook climbs above the
       storm-grate elevations (roughly 6.3&ndash;6.6 ft on the gauge),
       bay water pushes backwards up the storm drains and surfaces in
       the street — the SE and SW grates across Bay Ave go first, and
       those areas stay wettest. No rain required.</p>
    <p><b>Rain floods — the tide does not matter.</b> This corner
       sits at the bottom of the Highlands hillside — the bluffs
       climb ~200 feet directly above it, and everything that falls
       on them surges downhill onto this low shelf within minutes.
       So the rainfall <i>rate</i> alone understates the input
       enormously: the intersection receives the hillside's water,
       not just its own. When a burst is intense enough (roughly 1+
       inch/hour), that amplified inflow fills the drain system
       beyond its discharge capacity, the water backs up, and it
       behaves exactly as if a high tide were in — <b>even at dead
       low tide</b>. Proven July 6, 2026: about 7&Prime; of water at
       the curb while the bay sat more than a foot below the lowest
       grate. In rain floods the backup concentrates around the
       NE/NW grates (the drain trunk line) — the opposite corner
       from tide floods. <b>Take-home: never judge flood risk here
       by the tide chart alone.</b> Once the rain is hard enough,
       the tide level is irrelevant to whether it floods. The
       timing is now measured and modeled (v0.10): street water
       lags the rain peak by ~15 min, can rise 8&Prime; in 12
       minutes, and drains back within ~20&ndash;30 min of the rain
       stopping. All four floods measured to date &mdash; including
       the two worst &mdash; were rain-driven.</p>
    <p><b>Compound (the worst case).</b> The tide can't prevent a rain
       flood, but it can raise its floor: heavy rain landing on a high
       tide has nowhere to go at all. The biggest flood in this
       project's records — October 30, 2025, water past the bottom
       porch step — was exactly this combination. The two add
       <i>sub-linearly</i>, though: the deeper the water, the larger
       the area it covers, so each additional inch takes more water
       than the last. The same rain that raises a low-tide street
       pool by a foot might add only a few inches on top of a high
       tide — but those inches start from a much higher floor.</p>
  </section>

"""


def _render_reference_scale_html(forecast):
    return f"""
  <section class="reference">
    <h2>Reference scale</h2>
    <p>Sandy Hook observed water level (MLLW; {CURRENT_MODEL_VERSION} thresholds = landmark elevation + 2.82):</p>
    <ul>
      <li>&lt; 6.34 ft — no flooding, nothing visible</li>
      <li>6.34 ft — water emerges from SW grate across Bay (lowest grate)</li>
      <li>6.42 ft — SE grate across Bay emerges</li>
      <li>6.46 ft — SE/SW pavement corners wet; Bay Ave upstream grate emerges</li>
      <li>6.60 ft — water at gutter / curb edge at walkway (don't park there)</li>
      <li>6.62 ft — NE (user's corner) + NW grates emerge (Pathway B)</li>
      <li>6.98 ft — water tops curb at walkway (flood onset at property)</li>
      <li>7.15 ft — water on sidewalk under the walkway lawn step</li>
      <li>7.18 ft — Bay Ave road middle covered</li>
      <li>7.36 ft — intersection high point submerged</li>
      <li>7.48 ft — water at lawn / walkway step</li>
      <li>7.50 ft — water at bottom of porch steps</li>
      <li>8.23 ft — water over the first porch step</li>
      <li>10.90 ft — water at the porch deck (Sandy-class)</li>
    </ul>
    <h3>Tidal datums — the ladder below the grates</h3>
    <p class="note">Official NOAA datums for Sandy Hook (epoch
       1983&ndash;2001). "Sea level" is an average, not a line in the
       water: MSL averages ALL heights over 19 years; MLLW (the
       gauge's zero) averages only each day's LOWER low; NAVD88 (the
       survey datum every landmark uses) is a fixed geodetic plane
       that happens to sit 0.24 ft above epoch-MSL here. The epoch
       centers on ~1992 &mdash; with ~4.3 mm/yr of sea-level rise
       (this project's own fit), TODAY's actual mean sea level runs
       ~0.4&ndash;0.5 ft above these values.</p>
    <table>
      <thead><tr><th>Datum</th><th>ft MLLW</th><th>ft NAVD88</th>
        <th>vs SW grate</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td>MLLW (gauge zero)</td><td>0.00</td><td>&minus;2.82</td><td>&minus;76&Prime;</td><td>average daily LOWER low</td></tr>
        <tr><td>MLW</td><td>0.20</td><td>&minus;2.62</td><td>&minus;74&Prime;</td><td>average daily low tide</td></tr>
        <tr><td>MSL ("sea level")</td><td>2.58</td><td>&minus;0.24</td><td>&minus;45&Prime;</td><td>average of all levels</td></tr>
        <tr><td>NAVD88 zero</td><td>2.82</td><td>0.00</td><td>&minus;42&Prime;</td><td>survey datum plane</td></tr>
        <tr><td>MHW</td><td>4.90</td><td>2.08</td><td>&minus;17&Prime;</td><td>average daily high tide</td></tr>
        <tr><td>MHHW</td><td>5.23</td><td>2.41</td><td>&minus;13&Prime;</td><td>average HIGHER daily high</td></tr>
      </tbody>
    </table>

  </section>

"""


def _render_glossary_html(forecast):
    return f"""
  <section class="reference">
    <h2>Regime glossary</h2>
    <p>The label in the subject line (NO FLOODING / STREET / LIGHT / MODERATE / SEVERE) summarises severity based on water depth at the curb.</p>
    <ul>
      <li><b>no flooding</b> — {REGIME_GLOSSARY['dry']}</li>
      <li><b>street</b> — {REGIME_GLOSSARY['street']}</li>
      <li><b>light</b> — {REGIME_GLOSSARY['light']}</li>
      <li><b>moderate</b> — {REGIME_GLOSSARY['moderate']}</li>
      <li><b>severe</b> — {REGIME_GLOSSARY['severe']}</li>
      <li><b>cold lockout</b> — {REGIME_GLOSSARY['cold_lockout']}</li>
    </ul>
  </section>

"""


def _render_cadence_ops_html():
    c = _nowcast_cadence_stats()
    if not c:
        return ('<p class="note">Radar cadence (ops): collecting — '
                'stats appear once the heartbeat log has enough '
                'active-period runs.</p>')
    return (f'<p class="note">Radar cadence (ops, last {c["days"]} d, '
            f'active periods): median {c["median_min"]:.0f} min '
            f'between runs, p90 {c["p90_min"]:.0f}, worst '
            f'{c["max_min"]:.0f} ({c["n_gaps"]} gaps / '
            f'{c["n_runs"]} runs). Requested cadence is 10 min; '
            f'GitHub scheduling is BEST EFFORT — this line is the '
            f'measured truth of it.</p>')


def render_details_page(forecast):
    """The "For more information" page (docs/details.html, 2026-07-20
    multi-page split): deep reference material off the landing scroll —
    how-flooding, reference scale, historical floods, the model term
    by term (incl. the rain-pathway calculator), spot-check protocol,
    accuracy, glossary. Anchors match _render_more_info_links_html."""
    gen = ""
    try:
        gen = _station_local_now().strftime("%a %b %d, %I:%M %p ET")
    except Exception:
        pass
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<title>Bay Ave Barnacle — details &amp; reference</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
  <header>
    <h1><a href="index.html" style="text-decoration:none;color:inherit">Bay Ave Barnacle</a> — details</h1>
    <p class="subtitle"><a href="index.html">&larr; back to the forecast</a> &middot; reference &amp; model internals &middot; generated {gen}</p>
  </header>

  <div id="how"></div>
{_render_how_flooding_html(forecast)}
  <div id="reference"></div>
{_render_reference_scale_html(forecast)}
  <div id="history"></div>
{_render_historical_floods_html()}
  <div id="model"></div>
{_render_equation_widget_html(forecast)}
  <div id="spotcheck"></div>
  {_spot_check_block_html(forecast,
                           table_ref='<a href="index.html#landmarks">on '
                                     'the home page</a>')}
  <div id="accuracy"></div>
  {_render_accuracy_html(forecast)}
  {_render_cadence_ops_html()}
  <div id="glossary"></div>
{_render_glossary_html(forecast)}

  <footer>
    <p><a href="index.html">&larr; back to the live forecast</a></p>
  </footer>
</main>
</body></html>"""


def _render_more_info_links_html():
    """Landing-page links to details.html (2026-07-20 multi-page
    split — user: landing ends at the heat-map; deep reference
    material moves off the scroll)."""
    items = [
        ("how", "How flooding works here (plain English)"),
        ("reference", "Reference scale"),
        ("history", "How bad can it get? The 10 worst floods"),
        ("model", "The model, term by term"),
        ("spotcheck", "Spot-check (help calibrate the model)"),
        ("accuracy", "Forecast performance — as-run evidence"),
        ("glossary", "Regime glossary"),
    ]
    links = "".join(
        f'<li><a href="details.html#{a}">{t}</a></li>'
        for a, t in items)
    links += ('<li><a href="highlands.html">Highlands street flood '
              'map (beta) — every street\'s elevation and flood '
              'onset</a></li>')
    return ('<section class="more-info"><h2>For more information</h2>'
            f'<ul class="more-info-list">{links}</ul></section>')


def _render_more_details_html(forecast):
    """Collapsible "More details" strip under the day cards (user
    2026-07-21) for context lines that are true but not glanceable —
    currently the monthly-percentile note; future one-liners join
    here rather than floating loose on the page."""
    bits = []
    unusual = _unusual_forecast_text(forecast)
    if unusual:
        bits.append(unusual)
    if not bits:
        return ""
    body = "".join(f'<p class="note">{b}</p>' for b in bits)
    return ('<details class="chart-explain more-details">'
            f'<summary>More details</summary>{body}</details>')


def _render_summary_html(forecast, include_confidence=True,
                         include_unusual=True):
    """HTML version: summary + confidence + optional unusual-forecast note
    inside a styled banner. The landing page passes both flags False
    (2026-07-21): per-tide confidence lives in the tides table and the
    percentile note in the More-details strip; email keeps the banner
    complete."""
    # Day cards absorbed the per-tide sentence list (user 2026-07-20,
    # reapplied 2026-07-21 after the edit was lost in a reset cycle);
    # this banner keeps only outage / confidence / unusual notes.
    summary = ""
    level = (forecast.get("confidence_level") or "") \
        if include_confidence else ""
    reason = forecast.get("confidence_reason") or ""
    unusual = _unusual_forecast_text(forecast) if include_unusual else None
    if not summary and not level and not unusual:
        return ""
    parts = ['<section class="tldr">']
    if forecast.get("tide_predictions_stale"):
        parts.append(
            '<p class="tldr-confidence confidence-low"><b>NOAA tide-'
            'prediction service outage</b> &mdash; tide times/heights '
            'below are served from cached astronomy (identical maths, '
            'just not refreshed). Rain-risk inputs (QPF, alerts) are '
            'unaffected and live.</p>')
    if level:
        # Primary confidence line: badge + reason
        confidence_html = (
            f'<p class="tldr-confidence confidence-{level}">'
            f'<b>Confidence: {level.upper()}</b> &mdash; '
            f'<span>{reason}</span>'
        )
        # Augment with qualifier sentences for non-high confidence (9b.6)
        for extra in _confidence_qualifier_sentences(forecast):
            confidence_html += f'<br><span class="confidence-qualifier">{extra}</span>'
        confidence_html += "</p>"
        parts.append(confidence_html)
    if unusual:
        parts.append(f'<p class="tldr-unusual">{unusual}</p>')
    parts.append('</section>')
    return "".join(parts)


def _render_input_health_text(forecast):
    rows = _degraded_health_rows(forecast)
    if not rows:
        return []
    lines = ["⚠ DEGRADED INPUTS — unavailable is not being treated as zero:"]
    for row in rows:
        detail = f" — {row['detail']}" if row["detail"] else ""
        lines.append(f"  {row['label']}: {row['status']}{detail}")
    return lines


def _render_input_health_html(forecast):
    rows = _degraded_health_rows(forecast)
    if not rows:
        return ""
    items = "".join(
        f"<li><b>{_html_escape(row['label'])}:</b> "
        f"{_html_escape(row['status'])}"
        + (f" — {_html_escape(row['detail'])}" if row["detail"] else "")
        + "</li>"
        for row in rows
    )
    return (
        '<section class="input-health" style="border:2px solid #b45309;'
        'background:#fff7ed;padding:10px 14px;margin:12px 0">'
        '<h2 style="margin:0 0 6px 0">⚠ Degraded forecast inputs</h2>'
        '<p>Unavailable data is shown as unavailable and is not being '
        f'treated as a measured or forecast zero.</p><ul>{items}</ul></section>'
    )


def _render_rain_timing_text(forecast):
    """Plain-text rain timing block. Empty list when no rain is expected."""
    if not _rain_is_notable(forecast):
        return []
    cum = forecast.get("cumulative_rain_24h_in") or 0
    lines = ["Rain & tide timing:"]
    lines.append(f"  Cumulative next 24 h: {cum:.2f}\"")
    peak_t = forecast.get("peak_time_local")
    for t in _upcoming_tides_only(forecast):
        peak_rain = t.get("peak_rain_in_hr") or 0
        offset = t.get("peak_rain_offset_h")
        label = "★ peak tide" if t["time"] == peak_t else "lower high"
        # weekday-annotated (user 2026-07-20): bare clock times here
        # spanned three calendar days with no day indication
        when = format_time_short(t["time"])
        if peak_rain <= 0.005:
            lines.append(f"  {when} ({label}): no rain in ±90 min window")
            continue
        if offset is None:
            timing = "during the window"
        elif abs(offset) < 0.25:
            timing = "at the high tide"
        elif offset < 0:
            timing = f"{abs(offset):.0f} h before high tide"
        else:
            timing = f"{offset:.0f} h after high tide"
        lines.append(f"  {when} ({label}): peak {peak_rain:.2f} in/hr {timing}")
    return lines


def _render_rain_timing_html(forecast):
    """HTML version of the rain-timing block."""
    if not _rain_is_notable(forecast):
        return ""
    cum = forecast.get("cumulative_rain_24h_in") or 0
    peak_t = forecast.get("peak_time_local")
    rows = ""
    for t in _upcoming_tides_only(forecast):
        peak_rain = t.get("peak_rain_in_hr") or 0
        offset = t.get("peak_rain_offset_h")
        label = "★ peak tide" if t["time"] == peak_t else "lower high"
        # weekday-annotated (user 2026-07-20): bare clock times here
        # spanned three calendar days with no day indication
        when = format_time_short(t["time"])
        if peak_rain <= 0.005:
            timing_desc = "no rain in ±90 min window"
        else:
            if offset is None:
                timing_desc = "during the window"
            elif abs(offset) < 0.25:
                timing_desc = "at high tide"
            elif offset < 0:
                timing_desc = f"{abs(offset):.0f} h before high tide"
            else:
                timing_desc = f"{offset:.0f} h after high tide"
            timing_desc = f"peak {peak_rain:.2f} in/hr, {timing_desc}"
        rows += (
            f'<tr><td>{when} ({label})</td>'
            f'<td>{timing_desc}</td></tr>'
        )
    return (
        '<section class="rain-timing">'
        '<h2>Rain &amp; tide timing</h2>'
        f'<p>Cumulative rain next 24 h: <b>{cum:.2f}&Prime;</b></p>'
        '<table class="rain-table">'
        '<thead><tr><th>High tide</th><th>Rain near it</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '</section>'
    )


def _render_accuracy_text(forecast):
    """Plain-text one-line peak-error summary. Empty list when no
    forecasts have been scored yet (first few days after archive starts)."""
    a = forecast.get("accuracy_summary") or {}
    n = a.get("n_scored_recent") or 0
    if n == 0:
        return []
    return [(
        f"Peak forecast error (last {n} as-run forecasts): "
        f"mean error {a['mean_error_ft']:+.2f} ft, "
        f"mean |error| {a['mean_abs_error_ft']:.2f} ft, "
        f"worst |error| {a['max_abs_error_ft']:.2f} ft. "
        f"Total scored: {a['n_scored_total']}."
    )]


def _render_accuracy_html(forecast):
    """HTML accuracy section: text summary + scatter chart of
    predicted vs observed SH peaks (HANDOFF 9b.8 mode 1 — peak-magnitude
    accuracy). Empty string when no scored forecasts yet."""
    a = forecast.get("accuracy_summary") or {}
    n = a.get("n_scored_recent") or 0
    if n == 0:
        return ""

    magnitude_html = (
        f'<div class="magnitude-block">'
        f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
        f'Peak-height error</h3>'
        f'<p>Last {n} as-run forecasts: mean error '
        f'<b>{a["mean_error_ft"]:+.2f} ft</b>, '
        f'mean |error| <b>{a["mean_abs_error_ft"]:.2f} ft</b>, '
        f'worst |error| {a["max_abs_error_ft"]:.2f} ft. '
        f'Total scored: {a["n_scored_total"]}.</p></div>'
    )

    # Mode 2: outcome-depth accuracy from data/labeled_observations.csv
    # (HANDOFF 9b.8 mode 2). Each row is one in-the-field observation
    # that already has both `observed_depth_in` and
    # `model_predicted_depth_in` columns — no joining needed.
    outcome_rows = _load_outcome_depth_rows()
    outcome_html = ""
    if outcome_rows:
        n = len(outcome_rows)
        mean_err = sum(r["error_in"] for r in outcome_rows) / n
        mean_abs = sum(abs(r["error_in"]) for r in outcome_rows) / n
        max_abs = max(abs(r["error_in"]) for r in outcome_rows)
        rows_html = ""
        for r in outcome_rows:
            err = r["error_in"]
            sign_cls = "err-over" if err > 0 else ("err-under" if err < 0 else "")
            rows_html += (
                f'<tr>'
                f'<td>{r["time"]}</td>'
                f'<td>{r["landmark"]}</td>'
                f'<td>{r["observed_in"]:+.1f}&Prime;</td>'
                f'<td>{r["predicted_in"]:+.1f}&Prime;</td>'
                f'<td class="{sign_cls}">{err:+.1f}&Prime;</td>'
                f'</tr>'
            )
        outcome_html = (
            f'<div class="outcome-block">'
            f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
            f'Outcome-depth accuracy (per-observation)</h3>'
            f'<p style="font-size:13px;margin:4px 0">'
            f'N = {n} labeled observations. Mean error '
            f'<b>{mean_err:+.1f}&Prime;</b> (positive = model over-predicts), '
            f'mean |error| <b>{mean_abs:.1f}&Prime;</b>, '
            f'worst |error| {max_abs:.1f}&Prime;.</p>'
            f'<table class="outcome-table">'
            f'<thead><tr><th>Time</th><th>Landmark</th>'
            f'<th>Observed</th><th>Predicted</th><th>Error</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table>'
            f'<p class="note">Compares each user-logged observation in '
            f'<code>data/labeled_observations.csv</code> to the model\'s '
            f'predicted depth at the same landmark at the same time, '
            f'<b>as logged at observation time</b> — an append-only '
            f'record of the model version that was live that day, kept '
            f'unrevised on purpose. The large early over-predictions '
            f'(2026-05-18, offshore-wind event) are v0.7-era rows that '
            f'motivated the v0.8 wind adjustment; they are history, not '
            f'current-model skill. Sparse but each row is a real '
            f'observation with real depth.</p>'
            f'</div>'
        )

    # Lead-time accuracy (HANDOFF 9b.8 lead-time axis): does the model
    # converge as the tide approaches? Built from predictions_log.csv
    # (HANDOFF 9b.3) joined to NOAA observed peaks (cached on disk).
    leadtime = _compute_leadtime_accuracy()
    leadtime_html = ""
    if leadtime and leadtime["buckets"]:
        rows_html = ""
        for b in leadtime["buckets"]:
            err = b["mean_err_ft"]
            sign_cls = "err-over" if err > 0 else ("err-under" if err < 0 else "")
            rows_html += (
                f'<tr>'
                f'<td>{b["label"]}</td>'
                f'<td>{b["n"]}</td>'
                f'<td class="{sign_cls}">{err:+.2f} ft</td>'
                f'<td>{b["mean_abs_err_ft"]:.2f} ft</td>'
                f'</tr>'
            )
        leadtime_html = (
            f'<div class="leadtime-block">'
            f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
            f'Accuracy by lead time (predictions log)</h3>'
            f'<p style="font-size:13px;margin:4px 0">'
            f'{leadtime["n_total"]} predictions across '
            f'{leadtime["n_tides"]} past tides. Each row groups '
            f'predictions by how many hours BEFORE the tide they were '
            f'made — closer to peak should mean smaller error.</p>'
            f'<table class="outcome-table">'
            f'<thead><tr><th>Lead time</th><th>N predictions</th>'
            f'<th>Mean error (signed)</th><th>Mean |error|</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table>'
            f'<p class="note">From '
            f'<code>data/predictions_log.csv</code> joined to NOAA '
            f'observed peaks (cached at '
            f'<code>data/observed_peaks_cache.csv</code>). Populated '
            f'over time as hourly predictions accumulate. '
            f'<b>Near-peak rows begin 2026-07-21:</b> a lead-time bug '
            f'made every earlier run stop logging ~4&nbsp;h before '
            f'each peak, so 0&ndash;4&nbsp;h buckets and the final '
            f'approach on per-tide convergence charts only exist from '
            f'that date onward. Earlier rows are honest as-run history '
            f'at their stated leads; nothing was backfilled.</p>'
            f'</div>'
        )

    # Binary classifier metrics (HANDOFF 9b.8 mode 3)
    cm = _compute_classifier_metrics()
    classifier_html = ""
    if cm and cm["total"] > 0:
        def pct(x):
            return f"{x * 100:.1f}%" if x is not None else "—"
        false_alert_text = (
            f'{cm["false_alerts_per_30_days"]:.1f} per 30 days over this '
            f'{cm["sample_days"]}-day sample'
            if cm["false_alerts_per_30_days"] is not None
            else "unavailable (valid sample dates required)"
        )
        classifier_html = (
            f'<div class="classifier-block">'
            f'<h3 style="margin:12px 0 4px 0;font-size:15px">'
            f'Flood-alert skill (SH ≥ {cm["threshold_sh_mllw"]:.2f} ft = lowest grate)</h3>'
            f'<p style="font-size:13px;margin:6px 0">'
            f'Flood recall: <b>{pct(cm["recall"])}</b> '
            f'({cm["tp"]}/{cm["tp"] + cm["fn"]} observed floods caught) '
            f'&middot; Alert precision: <b>{pct(cm["precision"])}</b> '
            f'({cm["tp"]}/{cm["tp"] + cm["fp"]} flood predictions verified) '
            f'&middot; False alerts: <b>{false_alert_text}</b>.</p>'
            f'<p class="note">Dry days dominate: an always-predict-dry '
            f'baseline is {pct(cm["always_dry_accuracy"])} accurate but '
            f'catches 0% of floods. The model\'s raw accuracy is '
            f'{pct(cm["accuracy"])}; balanced accuracy is '
            f'{pct(cm["balanced_accuracy"])}. Recall and precision are '
            f'the decision-relevant headline metrics.</p>'
            f'<table class="confusion-table"><tbody>'
            f'<tr><th></th><th>Actual flood</th><th>Actual dry</th></tr>'
            f'<tr><th>Predicted flood</th>'
            f'<td class="tp">{cm["tp"]} TP</td>'
            f'<td class="fp">{cm["fp"]} FP</td></tr>'
            f'<tr><th>Predicted dry</th>'
            f'<td class="fn">{cm["fn"]} FN</td>'
            f'<td class="tn">{cm["tn"]} TN</td></tr>'
            f'</tbody></table>'
            f'<p style="font-size:13px;margin:6px 0">'
            f'False-positive rate: {pct(cm["fpr"])} &middot; '
            f'N = {cm["total"]} daily as-run forecasts. Mixed historical '
            f'model versions are intentionally not recomputed.</p>'
            f'</div>'
        )
    note_html = (
        '<p class="note">Positive mean error = model over-predicts on '
        'average. Each point is one archived daily forecast (since the '
        'JSON archive started). x = predicted Sandy Hook peak, y = '
        'actual NOAA observed peak. The dashed diagonal is perfect '
        'prediction (y=x); points above the line = model under-predicted, '
        'below = over-predicted. Raw data: '
        '<code>data/forecast_accuracy.csv</code>.</p>'
        '<p class="note">Scope: this scores the <b>tide-keyed input</b> '
        '— each day\'s predicted vs observed peak at the Sandy Hook '
        'gauge, as the forecast actually ran that day (an append-only '
        'record; rows are never recomputed under newer models). It '
        'cannot see rain-driven street floods (the gauge is 4 miles '
        'away and tide-only): pluvial skill is tracked separately '
        'against the spot-check log in '
        '<code>data/labeled_observations.csv</code>. The evidence registry '
        'currently has six measured flood-peak anchors; the v0.10.1 fit set '
        'is two full tape-measured hydrographs, with the other events used '
        'as independent peak, recession, or out-of-sample checks.</p>'
    )

    rows = _load_accuracy_rows()
    if len(rows) < 2:
        # Not enough data for a scatter chart yet — text summary +
        # (optional) outcome-depth + lead-time + binary classifier blocks
        return (
            '<section class="accuracy">'
            '<h2>Forecast performance — as-run evidence</h2>'
            f'{classifier_html}'
            f'{leadtime_html}'
            f'{magnitude_html}'
            f'{outcome_html}'
            f'{note_html}'
            '</section>'
        )

    # Bounds for the chart axes — include the y=x line range
    all_vals = []
    for r in rows:
        all_vals.append(r["predicted"])
        all_vals.append(r["observed"])
    lo = min(all_vals) - 0.1
    hi = max(all_vals) + 0.1

    rows_json = json.dumps(rows)
    return f"""
<section class="accuracy">
  <h2>Forecast performance — as-run evidence</h2>
  {classifier_html}
  {leadtime_html}
  {magnitude_html}
  {outcome_html}
  <canvas id="accuracy-chart" width="800" height="380"
          style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js" integrity="sha384-FcQlsUOd0TJjROrBxhJdUhXTUgNJQxTMcxZe6nHbaEfFL1zjQ+bq/uRoBQxb0KMo" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js" integrity="sha384-oNtu+d18330MVFpltUTve1DatxCkkctlpA2AC3GulbVFOSqhHdDat3qHse/Lbuek" crossorigin="anonymous"></script>
  <script>
    (function() {{
      var rows = {rows_json};
      var lo = {lo:.2f};
      var hi = {hi:.2f};
      var data = rows.map(function(r) {{
        return {{ x: r.predicted, y: r.observed, date: r.date,
                  error: r.error, regime: r.regime }};
      }});
      var ctx = document.getElementById('accuracy-chart').getContext('2d');
      new Chart(ctx, {{
        type: 'scatter',
        data: {{
          datasets: [{{
            label: 'Daily forecast vs actual',
            data: data,
            backgroundColor: 'rgba(31, 111, 235, 0.55)',
            borderColor: 'rgba(31, 111, 235, 0.85)',
            pointRadius: 5,
            pointHoverRadius: 7,
          }}]
        }},
        options: {{
          responsive: true,
          plugins: {{
            annotation: {{
              annotations: {{
                yEqualsX: {{
                  type: 'line',
                  xMin: lo, xMax: hi, yMin: lo, yMax: hi,
                  borderColor: 'rgba(150,150,150,0.7)',
                  borderWidth: 1, borderDash: [6, 4],
                  label: {{ display: true, content: 'y = x (perfect)',
                            position: 'end',
                            backgroundColor: 'rgba(255,255,255,0.85)',
                            color: '#666',
                            font: {{ size: 11 }} }}
                }}
              }}
            }},
            tooltip: {{
              callbacks: {{
                label: function(ctx) {{
                  var r = ctx.raw;
                  return [
                    r.date,
                    'Predicted: ' + r.x.toFixed(2) + ' ft MLLW',
                    'Observed:  ' + r.y.toFixed(2) + ' ft MLLW',
                    'Error:     ' + r.error.toFixed(2) + ' ft '
                      + (r.error > 0 ? '(over-pred)' : '(under-pred)'),
                  ];
                }}
              }}
            }},
            legend: {{ display: false }}
          }},
          scales: {{
            x: {{ title: {{ display: true,
                            text: 'Predicted SH peak (ft MLLW)' }},
                  suggestedMin: lo, suggestedMax: hi,
                  grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
            y: {{ title: {{ display: true,
                            text: 'Observed SH peak (ft MLLW)' }},
                  suggestedMin: lo, suggestedMax: hi,
                  grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
          }}
        }}
      }});
    }})();
  </script>
  {note_html}
</section>
"""


def _render_low_tides_text(forecast):
    """Plain-text block listing low tides in the next 24h. Useful for
    knowing when sub-curb water might drain back out, parking returns,
    etc. (See also: future Atlantic Highlands Marina Barnacle spin-off,
    where this block is the headline rather than a footnote.)"""
    lows = forecast.get("low_tides") or []
    if not lows:
        return []
    lines = ["Low tides in next 24h:"]
    for lt in lows:
        when = format_time_full(lt["time"])
        lines.append(f"  {when}  —  {lt['value_mllw']:.2f} ft MLLW")
    return lines


def _render_low_tides_html(forecast):
    """HTML version of the low-tides block."""
    lows = forecast.get("low_tides") or []
    if not lows:
        return ""
    rows = ""
    for lt in lows:
        rows += (
            f'<tr>'
            f'<td>{format_time_full(lt["time"])}</td>'
            f'<td>{lt["value_mllw"]:.2f}</td>'
            f'</tr>'
        )
    return (
        '<section class="low-tides">'
        '<h2>Low tides in next 24h</h2>'
        '<table class="history-table">'
        '<thead><tr><th>Time</th><th>Level (ft MLLW)</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="note">Astronomical low-tide predictions for situational '
        'awareness — useful for parking returns, sub-curb drainage, and '
        '(eventually) boat-ramp viability at Atlantic Highlands Marina.</p>'
        '</section>'
    )


def _render_lookahead_text(forecast):
    """Plain-text "dates to watch" block — 1-2 month astronomical look-ahead.
    HANDOFF 9b.7. Empty when no upcoming tides cross the lowest threshold."""
    rows = forecast.get("lookahead_watch") or []
    if not rows:
        return []
    lines = [
        f"Dates to watch (next {LOOKAHEAD_DAYS} days, astronomical only):",
    ]
    for r in rows:
        when_full = format_time_full(r["time"])
        lines.append(
            f"  {when_full}  —  {r['mllw']:.2f} ft MLLW  ({_lookahead_label(r)})"
        )
    lines.append(
        "  These are baseline astronomical tides — surge isn't forecast "
        "this far out. An event of significance also needs surge or rain. "
        "Spring tides (new/full moon ±2 d) are when astronomical highs "
        "stack highest; expect tighter margins on those days."
    )
    return lines


def _render_lookahead_html(forecast):
    """HTML version of the look-ahead block. HANDOFF 9b.7."""
    rows = forecast.get("lookahead_watch") or []
    if not rows:
        return ""
    body = ""
    for r in rows:
        spring_cls = f" spring-{r['spring_tide'].replace(' ', '-')}" if r.get("spring_tide") else ""
        body += (
            f'<tr class="{r["severity_class"]}{spring_cls}">'
            f'<td>{format_time_full(r["time"])}</td>'
            f'<td>{r["mllw"]:.2f}</td>'
            f'<td>{_lookahead_label(r)}</td>'
            f'</tr>'
        )
    return (
        '<section class="lookahead">'
        f'<h2>Dates to watch — next {LOOKAHEAD_DAYS} days</h2>'
        '<table class="history-table">'
        '<thead><tr><th>Date / time</th><th>Peak (ft MLLW)</th>'
        '<th>Significance</th></tr></thead>'
        f'<tbody>{body}</tbody></table>'
        '<p class="note">Astronomical-only predictions — surge isn\'t '
        'forecast this far out. An event of real significance also needs '
        'surge or rain, neither of which is in this table. Use as a '
        'planning aid (which dates have elevated baseline tides) rather '
        'than as a flood forecast. Spring-tide rows (new / full moon '
        '±2 d) are marked — those are when astronomical highs stack '
        'highest and a small surge can do extra damage.</p>'
        '</section>'
    )


def _render_recent_history_text(forecast):
    """Recent-history recap block (last 7 days). Empty when no data."""
    history = forecast.get("recent_history_7d") or []
    if not history:
        return []
    lines = ["Recent observed peaks (last 7 days):"]
    lines.append(
        f"  {'Date':<14}{'Peak (MLLW)':>13}  "
        f"{'Peak time':<14}{'Rel':>8}  Highest landmark reached"
    )
    for h in history:
        date_label = format_date_short(h["date"])
        peak_t = format_time_short(h.get("peak_time") or "")
        rel_str = f"{h['rel_in']:+.1f}\""
        lines.append(
            f"  {date_label:<14}"
            f"{h['peak_mllw']:>12.2f}   "
            f"{peak_t:<14}"
            f"{rel_str:>8}  "
            f"{h['highest_landmark']}"
        )
    return lines


def _render_recent_history_html(forecast):
    """HTML recap block."""
    history = forecast.get("recent_history_7d") or []
    if not history:
        return ""
    rows = ""
    for h in history:
        date_label = format_date_short(h["date"])
        peak_t = format_time_short(h.get("peak_time") or "")
        rel_str = f"{h['rel_in']:+.1f}&Prime;"
        rows += (
            f'<tr>'
            f'<td>{date_label}</td>'
            f'<td>{h["peak_mllw"]:.2f}</td>'
            f'<td>{peak_t}</td>'
            f'<td>{rel_str}</td>'
            f'<td>{h["highest_landmark"]}</td>'
            f'</tr>'
        )
    return (
        '<section class="recent-history">'
        '<h2>Recent observed peaks (last 7 days)</h2>'
        '<table class="history-table">'
        '<thead><tr><th>Date</th><th>Peak (ft MLLW)</th><th>Peak time</th>'
        '<th>Rel</th><th>Highest landmark</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p class="note">From NOAA Sandy Hook water_level (6-min product, '
        'preliminary). <b>Rel</b> = inches above the lowest landmark '
        '(SW grate, 3.52 NAVD88), always positive or negative. '
        '"Highest landmark" applies the 0.00 ft local enhancement (v0.8, carried in v0.9) '
        'to the observed peak.</p>'
        '</section>'
    )


def _spot_check_block_text(forecast, today=None):
    """Plain-text spot-check prompt with suggested observation times.
    Always emitted (every email, including DRY); the user requested this
    to build the calibration habit. References the landmark table above
    rather than duplicating the ladder. Includes high-value calibration
    callouts when today's conditions are unusual (rain at low tide;
    cold lockout above curb)."""
    today = today or _station_local_today()
    all_tides = forecast.get("all_tides") or []
    if not all_tides:
        return []
    peak_t = forecast.get("peak_time_local")
    items = []
    for t in all_tides:
        when = format_time_short(t["time"])
        role = "peak" if t["time"] == peak_t else "lower high"
        items.append(f"{when} ({role})")
    times_str = ", ".join(items)
    lines = [
        "Spot-check (help calibrate the model):",
        f"  Suggested observation times today: {times_str}",
    ]
    lines.extend(_high_value_calibration_callouts(forecast))
    lines.extend([
        "  Take a peek around one of those times — even 'no water at all'",
        "  is useful. Use the landmark table above (lowest to highest) to",
        "  describe what you saw. Report back with: time you looked,",
        "  highest landmark with water (or 'no water'), and rough depth",
        "  above it. Goes into data/labeled_observations.csv.",
    ])
    return lines


def _spot_check_block_html(forecast, today=None, table_ref="above"):
    """HTML version of the spot-check prompt. table_ref: where the
    landmark ladder lives relative to this block — "above" (email,
    where the table renders directly before it) or an <a> fragment
    (details.html, where the table stayed on the landing page)."""
    today = today or _station_local_today()
    all_tides = forecast.get("all_tides") or []
    if not all_tides:
        return ""
    peak_t = forecast.get("peak_time_local")
    items = []
    for t in all_tides:
        when = format_time_short(t["time"])
        role = "peak" if t["time"] == peak_t else "lower high"
        items.append(f"{when} ({role})")
    times_str = ", ".join(items)
    callouts = _high_value_calibration_callouts(forecast)
    callouts_html = ""
    for c in callouts:
        # Strip the leading "  ★ " marker from the text version
        text = c.strip().lstrip("★").strip()
        callouts_html += f'<p class="spot-check-callout">★ {text}</p>'
    return (
        '<section class="spot-check">'
        '<h2>Spot-check (help calibrate the model)</h2>'
        f'<p>Suggested observation times today: <b>{times_str}</b>.</p>'
        f'{callouts_html}'
        '<p>Take a peek around one of those times — even '
        '&ldquo;no water at all&rdquo; is useful. Use the landmark table '
        f'{table_ref} (lowest to highest) to describe what you saw. Report back '
        'with: time you looked, highest landmark with water (or '
        '&ldquo;no water&rdquo;), and rough depth above it. '
        'Goes into <code>data/labeled_observations.csv</code>.</p>'
        '</section>'
    )


def _landmarks_section_text(forecast, today=None):
    """Combined Landmarks section: unified table + footer + spot-check."""
    parts = []
    table_lines = _unified_landmark_table_text(forecast, today)
    if table_lines:
        parts.extend(table_lines)
    footer = _landmarks_footer_text(forecast, today)
    if footer:
        if parts:
            parts.append("")  # blank line
        parts.extend(footer)
    spot = _spot_check_block_text(forecast, today)
    if spot:
        if parts:
            parts.append("")
        parts.extend(spot)
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def _landmarks_section_html(forecast, today=None, wrapper="section",
                            include_spot_check=True):
    """Combined Landmarks section (HTML)."""
    table_html = _unified_landmark_table_html(forecast, today)
    footer_html = "".join(_landmarks_footer_html(forecast, today))
    if not table_html and not footer_html:
        body = ""
    else:
        body = table_html + footer_html
    if not body:
        landmarks_section = ""
    elif wrapper == "section":
        landmarks_section = (
            '<section class="landmarks" id="landmarks">'
            '<h2>Landmarks today</h2>' + body + '</section>'
        )
    else:
        landmarks_section = (
            '<h3>Landmarks today</h3>'
            '<div style="background:white;padding:8px;border-radius:4px">'
            + body + '</div>'
        )
    if include_spot_check:
        return landmarks_section + _spot_check_block_html(forecast, today)
    return landmarks_section


def render_email(forecast):
    d = forecast["depths_in"]
    regime = d["regime"]
    try:
        _now_k = _station_local_now()
    except Exception:
        _now_k = _station_local_now()
    _kick_today = _now_k.strftime("%a %b ") + str(_now_k.day)
    _kick_end = (_now_k + dt.timedelta(hours=72)).strftime("%a")
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    all_tides = forecast.get("all_tides", [])

    subject_short, subject_above, _ = landmark_summary(d, peak_ft)
    headline, _ = headline_for(forecast, regime)
    # Email parity with the site's TODAY/WORST split (2026-07-17):
    # subject leads with TODAY (incl. the so-far lookback when water
    # already happened); the worst-72h peak becomes the tail.
    # today_regime is None once the local day's series is exhausted
    # (post-Phase-1 day scoping). Remaining-today truth is then "no
    # further flooding today" — NOT the worst-72h regime, which would
    # resurrect the tomorrow-bleed. Keep the worst-72h fallback only
    # when the series itself is missing (degraded inputs own that).
    _tr = forecast.get("today_regime")
    if _tr is None:
        _tr = "dry" if forecast.get("water_series") else regime
    _today_head, _ = headline_for(forecast, _tr)
    _lb = forecast.get("today_lookback")
    if _lb and (_lb.get("rel_grate_in") or 0) > 0:
        _today_head += (f" (so far: {regime_display(_lb.get('regime') or '').upper()}"
                        f" {_lb['rel_grate_in']:+.1f}\")")
    subject = (f"[342 Bay] TODAY {_today_head} | WORST 72H {headline}: "
               f"{peak_ft:.2f} ft at {format_time_short(peak_t)} "
               f"({subject_short} {subject_above:+.1f}\")")

    # Format the list of all high tides in next 24h.
    # Columns: time, pred, surge, peak, highest-exceeded landmark, inches
    # above that landmark, inches relative to the lowest landmark, regime.
    tide_lines = []
    tide_lines.append(
        f"   {'Time':<16}{'Pred':>6}{'Surge':>8}{'Peak':>7}  "
        f"{'Landmark':<14}{'Above':>8}{'Rel':>8}  Regime"
    )
    for t in all_tides:
        td = t["depths_in"]
        short, above_in, rel_in = landmark_summary(td, t["forecast_peak_mllw"])
        marker = "★" if t["time"] == peak_t else " "
        tide_lines.append(
            f" {marker} {format_time_short(t['time']):<16}"
            f"{t['predicted_mllw']:>6.2f}"
            f"{t['surge_ft']:>+8.2f}"
            f"{t['forecast_peak_mllw']:>7.2f}  "
            f"{short:<14}"
            f"{above_in:>+7.1f}\""
            f"{rel_in:>+7.1f}\""
            f"  {td['regime']}"
        )
    tide_block = "\n".join(tide_lines)
    tide_block += (
        "\n  Above = inches above the highest exceeded landmark (negative "
        "= water below the lowest landmark).\n"
        "  Rel = inches above the lowest landmark (SW grate across Bay, "
        "3.64 NAVD88) — always."
    )

    summary_lines = _render_summary_text(forecast)
    summary_block = ("\n".join(summary_lines) + "\n\n") if summary_lines else ""
    health_lines = _render_input_health_text(forecast)
    health_block = ("\n".join(health_lines) + "\n\n") if health_lines else ""
    rain_lines = _render_rain_timing_text(forecast)
    rain_block = ("\n".join(rain_lines) + "\n\n") if rain_lines else ""
    pr = forecast.get("pluvial_risk") or {}
    if pr.get("level"):
        rain_block = (
            f"*** PLUVIAL FLOOD RISK ({pr['level'].upper()}) — independent of tide ***\n"
            + "".join(
                f"  NWS ALERT: {a.get('event', '')} — {a.get('headline', '')}\n"
                for a in (pr.get("nws_flood_alerts") or []))
            + "  Peak QPF "
            + _fmt_metric(pr.get("peak_rain_rate_24h_in_hr")) + " in/hr, "
            + "cumulative "
            + _fmt_metric(pr.get("cumulative_rain_24h_in")) + '\", '
            + "max PoP " + _fmt_metric(
                pr.get("max_pop_24h_pct"), ".0f"
            ) + "%"
            + (", thunderstorm wording" if pr.get("convective_wording") else "")
            + ".\n  Heavy rain alone floods the intersection (see 2026-07-06"
            " event); tide-keyed predictions below do not capture this.\n\n"
        ) + rain_block
    recap_lines = _render_recent_history_text(forecast)
    recap_block = ("\n".join(recap_lines) + "\n\n") if recap_lines else ""
    low_lines = _render_low_tides_text(forecast)
    low_block = ("\n".join(low_lines) + "\n\n") if low_lines else ""
    accuracy_lines = _render_accuracy_text(forecast)
    accuracy_block = ("\n".join(accuracy_lines) + "\n\n") if accuracy_lines else ""
    lookahead_lines = _render_lookahead_text(forecast)
    lookahead_block = ("\n".join(lookahead_lines) + "\n\n") if lookahead_lines else ""
    cold_lines = _render_cold_advisory_text(forecast)
    cold_block = ("\n".join(cold_lines) + "\n\n") if cold_lines else ""

    _today_head_text, _ = headline_for(
        forecast, forecast.get("today_regime") or regime)
    _lbt = forecast.get("today_lookback")
    _lb_text = ""
    if _lbt and (_lbt.get("rel_grate_in") or 0) > 0:
        _lb_text = (f" | so far: "
                    f"{regime_display(_lbt.get('regime') or '').upper()} "
                    f"{_lbt['rel_grate_in']:+.1f}\" at {_lbt['time_local']}")
    text = f"""\
TODAY: {_today_head_text}{_lb_text}
WORST 72H: {headline}: {peak_ft:.2f} ft at {format_time_short(peak_t)}

Bay Ave Barnacle flood forecast for 342 Bay Ave - {_station_local_today().isoformat()}

{health_block}{summary_block}{cold_block}High tides in next 24h ( * = worst case, headlined below):
{tide_block}

Worst case detail:
  High tide time:  {format_time_full(peak_t)}
  Predicted tide:  {forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)
  Surge:           {forecast['current_surge_ft']:+.2f} ft
  Forecast peak:   {peak_ft:.2f} ft MLLW
  Surge source:    {forecast['surge_source']}
                   ({forecast['nws_status']})
  Rain in window:  {_fmt_metric(forecast.get('peak_rain_rate_in_hr'))} in/hr peak
  72h mean temp:   {_fmt_metric(forecast.get('temp_avg_72h_f'), '.1f')} F
  Cold conditions: {'YES — ice-lock hypothesis met but no longer applied (see retrospective)' if forecast['cold_lockout'] else 'no'}

{rain_block}{_landmarks_section_text(forecast)}
Regime: {regime_display(regime)} — {REGIME_GLOSSARY.get(regime, '')}
Today ({_station_local_now().strftime("%A")}): {regime_display(forecast.get('today_regime') or regime)}; peak water {forecast.get('today_rel_grate_sw_in', 0) or 0:+.1f}" vs SW grate{f" at {forecast['today_peak_time'][-5:]}" if forecast.get('today_peak_time') else ""}

{recap_block}{accuracy_block}{low_block}{lookahead_block}Reference scale (Sandy Hook obs MLLW; {CURRENT_MODEL_VERSION} thresholds = landmark + 2.82):
  < 6.34  : no flooding (nothing visible)
  6.34    : water emerges from SW grate across Bay (lowest grate)
  6.42    : SE grate across Bay emerges
  6.46    : SE/SW pavement corners wet; Bay Ave upstream grate emerges
  6.60    : water at gutter / curb edge at walkway — don't park there
  6.62    : NE (user's corner) + NW grates emerge (Pathway B)
  6.98    : water at curb top — flood onset at property
  7.15    : water on sidewalk under the walkway lawn step
  7.18    : Bay Ave road middle covered
  7.36    : intersection high point submerged
  7.48    : water at lawn / walkway step
  7.50    : water at bottom of porch steps
  8.23    : water over the first porch step
  10.90   : water at the porch deck (Sandy-class)

Regime glossary (subject-line label, based on water depth at the curb):
  no flooding  : {REGIME_GLOSSARY['dry']}
  street       : {REGIME_GLOSSARY['street']}
  light        : {REGIME_GLOSSARY['light']}
  moderate     : {REGIME_GLOSSARY['moderate']}
  severe       : {REGIME_GLOSSARY['severe']}
  cold lockout : {REGIME_GLOSSARY['cold_lockout']}

Model: {CURRENT_MODEL_VERSION} (pluvial: dynamic tank hydrograph; scenarios = tank steady-state / tanh bracket). Local enhancement {LOCAL_ENHANCEMENT_FT:+.2f} ft (4-event calibration, conservative).
"""

    bg = {"dry": "#e8f5e9", "street": "#e3f2fd", "light": "#fff8e1",
          "moderate": "#ffe0b2", "severe": "#ffcdd2",
          "cold_lockout": "#eceff1"}.get(regime, "#fff")

    # Build the all-tides rows for the HTML email (new column layout)
    tide_rows_html = ""
    for t in all_tides:
        td = t["depths_in"]
        is_worst = (t["time"] == peak_t)
        row_style = "background:#ffffcc" if is_worst else ""
        short, above_in, rel_in = landmark_summary(td, t["forecast_peak_mllw"])
        tide_rows_html += (
            f'<tr style="{row_style}">'
            f'<td>{format_time_full(t["time"])}</td>'
            f'<td align="right">{t["predicted_mllw"]:.2f}</td>'
            f'<td align="right">{t["surge_ft"]:+.2f}</td>'
            f'<td align="right"><b>{t["forecast_peak_mllw"]:.2f}</b></td>'
            f'<td>{short}</td>'
            f'<td align="right">{above_in:+.1f}&Prime;</td>'
            f'<td align="right">{rel_in:+.1f}&Prime;</td>'
            f'<td>{regime_display(td["regime"])}</td>'
            f'</tr>'
        )

    summary_html = _render_summary_html(forecast)
    rain_html = _render_rain_timing_html(forecast)
    recap_html = _render_recent_history_html(forecast)
    low_html = _render_low_tides_html(forecast)
    accuracy_html = _render_accuracy_html(forecast)
    lookahead_html = _render_lookahead_html(forecast)

    # Email parity with the site (2026-07-17): TODAY — OUTLOOK (+ so-far
    # line when water already happened) then WORST 72H, before the
    # summary/confidence blocks — same order as the home page.
    _tr = forecast.get("today_regime")
    if _tr is None:
        _tr = "dry" if forecast.get("water_series") else regime
    _today_head, _today_cls = headline_for(forecast, _tr)
    _tbg = {"dry": "#e8f5e9", "street": "#e3f2fd", "light": "#fff8e1",
            "moderate": "#ffe0b2", "severe": "#ffcdd2",
            "cold_lockout": "#eceff1"}.get(_today_cls, "#fff8e1")
    _lb = forecast.get("today_lookback")
    _lb_html = ""
    if _lb and (_lb.get("rel_grate_in") or 0) > 0:
        _lb_html = (
            f'<div style="border-top:1px solid rgba(0,0,0,0.15);'
            f'margin-top:6px;padding-top:6px;font-size:14px">'
            f'<b>SO FAR TODAY:</b> '
            f'{regime_display(_lb.get("regime") or "").upper()} — peak '
            f'water {_lb["rel_grate_in"]:+.1f}&Prime; vs SW grate at '
            f'{_lb["time_local"]}, {_lb["source"]}.</div>')
    _today_sub = (f'Tide peak today {forecast.get("today_rel_grate_sw_in", 0) or 0:+.1f}&Prime; '
                  f'vs SW grate'
                  + (f' at {forecast["today_peak_time"][-5:]}'
                     if forecast.get("today_peak_time") else ""))
    today_block_html = (
        f'<div style="background:{_tbg};padding:14px 18px;border-radius:8px;'
        f'margin:12px 0;border:1px solid rgba(0,0,0,0.08)">'
        f'<div style="font-size:11px;color:#777;letter-spacing:1px">TODAY — OUTLOOK</div>'
        f'<div style="font-size:26px;font-weight:bold">{_today_head}</div>'
        f'<div style="font-size:14px">{_today_sub}</div>{_lb_html}</div>'
        f'<div style="background:#f4f6f8;padding:8px 18px;border-radius:8px;'
        f'margin:-4px 0 14px 0;border:1px solid rgba(0,0,0,0.08)">'
        f'<div style="font-size:11px;color:#777;letter-spacing:1px">WORST 72 H</div>'
        f'<div style="font-size:14px"><b>{headline_for(forecast, regime)[0]}</b> — '
        f'worst-case tide peak {peak_ft:.2f} ft MLLW at '
        f'{format_time_full(peak_t)}.</div></div>')

    health_html = _render_input_health_html(forecast)
    html = f"""\
<html><body style="font-family:sans-serif;background:{bg};padding:20px">
<h2>Bay Ave Flood Forecast</h2>
<p><b>{_station_local_today().isoformat()}</b></p>

{today_block_html}
{health_html}
{summary_html}
<h3>High tides in next 24h</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;background:white">
<tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Highest landmark</th><th>Above</th><th>Rel</th><th>Regime</th></tr>
{tide_rows_html}
</table>
<p style="font-size:small;color:#666">Highlighted row = worst-case tide, headlined below.
<b>Above</b> = inches above the highest exceeded landmark (negative when water is below the lowest landmark).
<b>Rel</b> = inches above the lowest landmark (SW grate across Bay, 3.52 NAVD88).</p>

<p><b>Worst case:</b> {format_time_full(peak_t)}<br>
<b>Forecast peak (obs):</b> {peak_ft:.2f} ft MLLW Sandy Hook
({forecast['peak_predicted_mllw']:.2f} predicted {forecast['current_surge_ft']:+.2f} surge)<br>
<b>Surge source:</b> {forecast['surge_source']} ({forecast['nws_status']})<br>
<b>Rainfall in window:</b> {_fmt_metric(forecast.get('peak_rain_rate_in_hr'))} in/hr peak<br>
<b>72h mean temp:</b> {_fmt_metric(forecast.get('temp_avg_72h_f'), '.1f')}&deg;F
{'(cold conditions met — ice-lock hypothesis no longer applied; see retrospective)' if forecast['cold_lockout'] else ''}</p>

{rain_html}
{_landmarks_section_html(forecast, wrapper='inline')}

<p><b>Regime: {regime_display(regime)}</b> &mdash; <span style="color:#666;font-size:13px">{REGIME_GLOSSARY.get(regime, '')}</span></p>

<h3>Regime glossary</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;background:white;font-size:13px">
<tr><td><b>no flooding</b></td><td>{REGIME_GLOSSARY['dry']}</td></tr>
<tr><td><b>street</b></td><td>{REGIME_GLOSSARY['street']}</td></tr>
<tr><td><b>light</b></td><td>{REGIME_GLOSSARY['light']}</td></tr>
<tr><td><b>moderate</b></td><td>{REGIME_GLOSSARY['moderate']}</td></tr>
<tr><td><b>severe</b></td><td>{REGIME_GLOSSARY['severe']}</td></tr>
<tr><td><b>cold lockout</b></td><td>{REGIME_GLOSSARY['cold_lockout']}</td></tr>
</table>

{recap_html}
{accuracy_html}
{low_html}
{lookahead_html}
<p style="font-size:small;color:#666">
Model {CURRENT_MODEL_VERSION} (pluvial: dynamic tank hydrograph on the chart; scenario brackets = tank steady-state / tanh).
Local enhancement {LOCAL_ENHANCEMENT_FT:+.2f} ft (measured-event calibration).
Surge persistence is a rough proxy; for active coastal storms, check NWS
Coastal Flood Statement directly.
</p>
</body></html>"""
    return subject, text, html


def _render_flood_windows_html(forecast):
    """Flood start/end/duration table (2026-07-06 — "not just what
    will happen at the very top of the peak"). Only landmarks with
    episodes in the series window appear; grazing episodes render as
    "may briefly touch"."""
    fw = forecast.get("flood_windows") or {}
    if not fw:
        return ""
    label_by_key = {k: l for k, l, _e, _s in LANDMARKS}
    elev_by_key = {k: e for k, _l, e, _s in LANDMARKS}
    rows = ""
    for key in FLOOD_WINDOW_KEYS:      # ascending elevation order
        for ep in fw.get(key, []):
            label = label_by_key.get(key, key)
            if ep.get("grazing"):
                when = f"~{ep['peak_time'][-5:]} — may briefly touch"
                dur = "—"
                peak = f"&lt;1.2&Prime;"
            else:
                end = ep["end"][-5:] if ep.get("end") else "beyond window"
                when = f"~{ep['start'][-5:]} &rarr; {end}"
                dur = (f"{ep['duration_h']:.1f} h"
                       if ep.get("duration_h") is not None else "ongoing")
                peak = f"+{ep['peak_depth_in']:.1f}&Prime; at {ep['peak_time'][-5:]}"
            rows += (f"<tr><td>{label}</td><td>{elev_by_key.get(key, '')}</td>"
                     f"<td>{when}</td><td>{dur}</td><td>{peak}</td></tr>")
    if not rows:
        return ""
    return f"""
  <section class="flood-windows">
    <h2>Flooding windows (coming 30 h)</h2>
    <table class="tide-table">
      <thead><tr><th>Landmark</th><th>NAVD88</th><th>Wet window</th>
      <th>Duration</th><th>Peak</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="note">Derived from the predicted water curve above
       (tide + surge + rain layer). Times are approximate (&sim;10–20
       min); end times are the optimistic edge — water drains slightly
       slower than the gauge falls, and the retention pockets hold
       water for hours after. Convective bursts can flood outside
       these windows entirely (see the rain-risk banner).</p>
  </section>
"""


def _render_pluvial_advisory_html(forecast):
    """Pluvial flood-risk banner (v0.9 first step, 2026-07-06).

    Rain alone floods the intersection — proven by the 7/6 flash
    flood (7.3" at curb, 1.5 h before high tide, bay below all
    grates). The tide-keyed model cannot predict that event class,
    so this banner surfaces the risk CATEGORICALLY whenever forecast
    rain conditions resemble it. Empty string when no risk."""
    pr = forecast.get("pluvial_risk") or {}
    level = pr.get("level")
    if not level:
        return ""
    heading = ("ELEVATED pluvial flood risk" if level == "elevated"
               else "Possible pluvial flooding")
    alerts_html = ""
    alerts = pr.get("nws_flood_alerts") or []
    if alerts:
        rows = "".join(
            f'<li><b>{_html_escape(str(a.get("event", "")))}</b> '
            f'({_html_escape(str(a.get("severity", "")))}) '
            f'— {_html_escape(str(a.get("headline", "")))}</li>'
            for a in alerts)
        alerts_html = (
            f'<p style="margin:6px 0 2px 0"><b>Active NWS alerts for '
            f'this location:</b></p><ul style="margin:2px 0 8px 18px">'
            f'{rows}</ul>')
    details = (
        "Next 24 h: peak QPF rate "
        + _fmt_metric(pr.get("peak_rain_rate_24h_in_hr")) + " in/hr, "
        + "cumulative "
        + _fmt_metric(pr.get("cumulative_rain_24h_in")) + '\", '
        + "max precip probability "
        + _fmt_metric(pr.get("max_pop_24h_pct"), ".0f") + "%"
        + (", thunderstorm/heavy-rain wording in the NWS forecast"
           if pr.get("convective_wording") else "")
        + "."
    )
    # v0.9-alpha scenario depths. Two scenarios:
    #  (a) burst at LOW tide (drains functional) — 7/6-class
    #  (b) burst at the worst HIGH tide (compound) — Oct 30-class
    #
    # Burst estimate — ANALOG SCALING (user proposal 2026-07-06: "use
    # this and the October 2025 event as examples of what to expect").
    # We can't know true convective rates, but we don't need to: the
    # 7/6 event pins the mapping from QPF-as-forecast to observed
    # flood. 7/6's max 6-h QPF bucket was ~0.55" and the flood fit a
    # 1.7 in/hr effective burst. Scale linearly off that single
    # anchor: burst ≈ 1.7 × (max_6h_accum / 0.55), clamped to
    # [QPF peak rate, 3.0 in/hr]. The ratio absorbs both QPF's
    # convective smearing AND the Highlands-hillside catchment
    # amplification (rain on the ~200-ft hill drains to this low
    # corner — local water input outruns local rainfall), because
    # both were baked into the 7/6 anchor. One-anchor calibration —
    # every future rain event tightens or breaks it; the bot archives
    # pluvial_risk + QPF daily so the training set builds itself.
    burst = pr.get("burst_est_in_hr", 0) or 0
    worst_peak = forecast.get("peak_forecast_observed_mllw")
    scenario_html = ""
    if burst > 0.1:
        # v0.9-gamma dual models: each scenario reports the bracket
        # [min, max] of the power-law (primary) and tanh (saturating)
        # estimates. They agree within ~1" in the calibrated range
        # (0.4-1.7 in/hr) and diverge for violent bursts — the spread
        # IS the model uncertainty, so show it instead of hiding it.
        def _bracket(bay):
            pw, th = estimate_pluvial_water_models(burst, bay)
            lo, hi = min(pw, th), max(pw, th)
            lo_c, hi_c = (lo - 4.16) * 12, (hi - 4.16) * 12
            if (hi - lo) < 0.04:
                return f'{pw:.2f} NAVD88 ({"%+.1f" % ((pw-4.16)*12)}&Prime; at curb)', hi
            return (f'{lo:.2f}&ndash;{hi:.2f} NAVD88 '
                    f'({"%+.1f" % lo_c} to {"%+.1f" % hi_c}&Prime; at curb, '
                    f'power-law/tanh spread)', hi)
        lt_txt, _ = _bracket(2.5)
        scenario_html = (
            f'<p><b>Scenario estimates (v0.10 tank steady-state / tanh bracket, burst '
            f'{burst:.1f} in/hr):</b><br>'
            f'&bull; Burst at LOW tide (drains working): water ≈ '
            f'{lt_txt} — 7/6-class flash flood.<br>'
        )
        if worst_peak is not None:
            bay_at_high = worst_peak + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88_OFFSET
            cp_txt, cp_hi = _bracket(bay_at_high)
            oct30_tag = (" — Oct 30 2025 class"
                         if cp_hi >= 5.0 else "")
            scenario_html += (
                f'&bull; Burst at the worst HIGH tide '
                f'({forecast.get("peak_time_local", "")}): water ≈ '
                f'{cp_txt} — compound rain+tide{oct30_tag}.</p>'
            )
        else:
            scenario_html += '</p>'
    return (
        '<section class="pluvial-advisory">'
        f'<h3>&#9888; {heading} — independent of the tide</h3>'
        f'{alerts_html}'
        f'<p>{details}</p>'
        f'{scenario_html}'
        '<p class="note">Heavy rain can flood the Bay+Central '
        'intersection with no tidal contribution at all — the '
        '2026-07-06 flash flood put ~7&Prime; of water at the curb '
        '1.5 hours <i>before</i> high tide with the bay a foot below '
        'the lowest grate. The tide-keyed predictions below do not '
        'capture this event class. NWS rain amounts (QPF) smear '
        'short convective bursts, so the scenario estimates assume a '
        '7/6-class burst whenever thunderstorms are in the forecast. '
        'The pluvial model is fit on two full measured hydrographs '
        '(7/6 + 7/9/2026 flash floods) and held to six frozen measured '
        'peak anchors (Oct 2025–Aug 2026), checked against every '
        'measured flood since (eight to date) '
        'with rain forcing measured by MRMS radar. Scenario depths '
        'bracket the v0.10 tank steady-state (primary) against the '
        'saturating tanh (conservative floor — event #4 showed real '
        'peaks exceed it in violent bursts). Treat depths as '
        '&plusmn;3&Prime;-class estimates, not measurements.</p>'
        '</section>'
    )


def _render_wind_adjustment_html(forecast):
    """v0.8 wind-direction adjustment block — rendered as a separate
    "expected actual" line in the worst-case detail section. Only
    shown when forecast wind at peak is in the offshore sector
    (currently the only sector that yields a non-zero adjustment).

    Empty string when no adjustment applies (onshore or unknown
    winds → main prediction stands).
    """
    wind_adj = forecast.get("wind_adjustment") or {}
    adjusted_depths = forecast.get("depths_in_wind_adjusted")
    if not wind_adj or wind_adj.get("adjustment_ft", 0) == 0 or not adjusted_depths:
        return ""
    main_depths = forecast.get("depths_in") or {}
    main_curb = main_depths.get("curb", 0)
    adj_curb = adjusted_depths.get("curb", 0)
    adj_regime = adjusted_depths.get("regime", "?")
    main_regime = main_depths.get("regime", "?")
    return (
        '<section class="wind-adjustment-advisory">'
        '<h3>Wind adjustment — expected actual</h3>'
        f'<p class="note">{wind_adj.get("note", "")}</p>'
        f'<p><b>Wind-adjusted curb depth:</b> {adj_curb:+.1f}&Prime; '
        f'(regime: <b>{adj_regime}</b>) &mdash; vs. main prediction of '
        f'{main_curb:+.1f}&Prime; ({main_regime}). The main prediction '
        f'errs on the safer / over-predict side; the wind-adjusted '
        f'value is the v0.8 calibrated estimate for the forecast wind '
        f'sector. <i>v0.8 calibration anchor: 2026-06-14 (offshore peak '
        f'wind, enh -0.13) vs 2026-06-15 (onshore peak wind, enh 0).</i></p>'
        '</section>'
    )


def _render_cold_advisory_html(forecast):
    """When 72-h mean temp is below 32°F (cold-lockout conditions met),
    surface an advisory note instead of zeroing predictions.

    Pre-2026-05-19: predict_landmark_depths returned all-zero depths
    in cold conditions and the regime banner said COLD_LOCKOUT.
    Post-2026-05-19 (per history/reports/cold_weather_retrospective.md):
    the web-evidence retrospective showed the rule was likely too
    generous, so predictions go through unchanged and this advisory
    notes that conditions are met but the hypothesis is unresolved.

    Empty string when cold-lockout conditions are NOT met."""
    if not forecast.get("cold_lockout"):
        return ""
    temp = forecast.get("temp_avg_72h_f")
    temp_str = f"{temp:.1f}°F" if temp is not None else "below freezing"
    return (
        '\n  <section class="cold-advisory">\n'
        '    <h2>Cold-conditions advisory</h2>\n'
        f'    <p>72-h mean temperature at Sandy Hook is <b>{temp_str}</b> '
        '(below the 32°F cold-lockout threshold). Through v0.6 the model '
        'forced predicted flooding to zero in this regime, on the theory '
        'that storm-drain outfalls become ice-locked and block bay → street '
        'backflow (Pathway B); since 2026-05-19 the rule is advisory-only '
        '(hypothesis open, evidence: one event).</p>\n'
        '    <p>The 19-event historical retrospective '
        '(<a href="https://github.com/JohnUrban/barnacle/blob/main/history/reports/cold_weather_retrospective.md">'
        'cold_weather_retrospective.md</a>) found web evidence that ~3 of '
        '5 named-storm candidates likely flooded Monmouth County despite '
        'the override conditions being met — so the rule appears too '
        'generous. The single Feb 22-23 2026 observation that originally '
        'calibrated it may be an outlier.</p>\n'
        '    <p><b>Current status: hypothesis open, not applied.</b> The '
        'predictions below assume <i>no</i> suppression. Cold-lockout '
        'may still apply at 342 Bay specifically — every cold-conditions-'
        'met event going forward adds to the validation dataset.</p>\n'
        '  </section>\n'
    )


def _render_cold_advisory_text(forecast):
    """Plain-text equivalent of _render_cold_advisory_html. Returns
    list of lines (possibly empty)."""
    if not forecast.get("cold_lockout"):
        return []
    temp = forecast.get("temp_avg_72h_f")
    temp_str = f"{temp:.1f} F" if temp is not None else "below freezing"
    return [
        "Cold-conditions advisory:",
        f"  72-h mean temp at Sandy Hook is {temp_str} (below 32 F).",
        "  Pre-v0.7 cold-lockout rule would have suppressed predicted",
        "  flooding here, but the 19-event historical retrospective",
        "  (history/reports/cold_weather_retrospective.md) found",
        "  evidence the rule is too generous. Hypothesis remains open;",
        "  predictions below assume NO suppression.",
    ]


def _render_live_gauge_section(forecast):
    """Render a 24h sparkline of observed Sandy Hook water level.
    HANDOFF 16f / Y in the 2026-05-19 solo-work backlog.

    Empty string when no observed data available."""
    obs = forecast.get("live_gauge_24h") or []
    if len(obs) < 2:
        return ""
    latest = obs[-1]
    latest_val = latest.get("value_mllw")
    latest_time = latest.get("time", "")
    series = [
        {"time": p["time"], "v": p["value_mllw"]}
        for p in obs if p.get("value_mllw") is not None
    ]
    series_json = json.dumps(series)

    return f"""
  <section class="live-gauge">
    <h2>Live observed water level — past 24 h</h2>
    <p class="note">Sandy Hook gauge (station 8531680). Latest:
       <b>{latest_val:.2f} ft MLLW</b> at {format_time_full(latest_time)}.
       Refreshed each workflow run (hourly).</p>
    <canvas id="live-gauge-chart" width="800" height="240"
            style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js" integrity="sha384-FcQlsUOd0TJjROrBxhJdUhXTUgNJQxTMcxZe6nHbaEfFL1zjQ+bq/uRoBQxb0KMo" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js" integrity="sha384-oNtu+d18330MVFpltUTve1DatxCkkctlpA2AC3GulbVFOSqhHdDat3qHse/Lbuek" crossorigin="anonymous"></script>
    <script>
      (function() {{
        var series = {series_json};
        var labels = series.map(function(p) {{
          var d = new Date(p.time.replace(' ', 'T'));
          if (isNaN(d.getTime())) return p.time;
          return d.toLocaleString(undefined, {{
            hour: 'numeric', minute: '2-digit'
          }});
        }});
        var values = series.map(function(p) {{ return p.v; }});
        var ctx = document.getElementById('live-gauge-chart').getContext('2d');
        new Chart(ctx, {{
          type: 'line',
          data: {{
            labels: labels,
            datasets: [{{
              label: 'Observed (ft MLLW)',
              data: values,
              borderColor: 'rgba(31, 111, 235, 0.95)',
              backgroundColor: 'rgba(31, 111, 235, 0.10)',
              fill: true,
              pointRadius: 0,
              tension: 0.25,
            }}].concat([
              // Tidal datums (2026-07-21): the ladder BELOW the
              // grates — muted steel family, legend-toggleable
              ['MLW 0.20', 0.20], ['MSL 2.58', 2.58],
              ['MHW 4.90', 4.90], ['MHHW 5.23', 5.23]
            ].map(function(d) {{
              return {{
                label: d[0],
                data: labels.map(function() {{ return d[1]; }}),
                borderColor: 'rgba(74, 107, 138, 0.65)',
                borderWidth: 1.1, borderDash: [4, 4],
                fill: false, pointRadius: 0,
              }};
            }}))
          }},
          options: {{
            responsive: true,
            plugins: {{
              annotation: {{ annotations: {{
                curb: {{
                  type: 'line', yMin: 6.58, yMax: 6.58,
                  borderColor: 'rgba(217, 119, 6, 0.7)',
                  borderWidth: 1, borderDash: [6, 4],
                  label: {{ display: true, content: 'curb (6.58)',
                            position: 'end',
                            backgroundColor: 'rgba(255,255,255,0.85)',
                            color: '#b35a00',
                            font: {{ size: 10 }} }}
                }},
                grate: {{
                  type: 'line', yMin: {SH_FIRST_WATER}, yMax: {SH_FIRST_WATER},
                  borderColor: 'rgba(31, 111, 235, 0.5)',
                  borderWidth: 1, borderDash: [3, 3],
                  label: {{ display: true, content: 'lowest grate ({SH_FIRST_WATER})',
                            position: 'end',
                            backgroundColor: 'rgba(255,255,255,0.85)',
                            color: '#1f6feb',
                            font: {{ size: 10 }} }}
                }}
              }} }},
              legend: {{ display: false }},
              tooltip: {{
                callbacks: {{
                  label: function(c) {{ return c.parsed.y.toFixed(2) + ' ft MLLW'; }}
                }}
              }}
            }},
            scales: {{
              x: {{ grid: {{ display: false }},
                    ticks: {{ maxTicksLimit: 8, autoSkip: true }} }},
              y: {{ title: {{ display: true, text: 'ft MLLW' }},
                    grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
            }}
          }}
        }});
      }})();
    </script>
    <p class="note">For NOAA's official gauge page (more products,
       longer windows):
       <a href="https://tidesandcurrents.noaa.gov/stationhome.html?id=8531680">
       Sandy Hook 8531680</a>.</p>
  </section>
"""


def _render_oscillation_section(forecast):
    """Render the home-page water-level oscillation chart section
    (HANDOFF 9b.4(b)). Empty string when there's no plottable data."""
    data = _oscillation_chart_data(forecast)
    if len(data["points"]) < 2:
        return ""
    # Inline as JSON; Chart.js reads from the global on load.
    data_json = json.dumps(data, default=str)
    return f"""
  <section class="oscillation">
    <h2>Sandy Hook peak over time</h2>
    <p class="note">Observed (■) past peaks and predicted (●) upcoming peaks,
       plotted by default in <b>inches vs the SW grate</b> (the
       project's standard reference; 0&Prime; = water first emerges) —
       toggle to the raw gauge reading (ft MLLW).
       Both series are PER-TIDE (both daily highs — the zig-zag is the
       real day/night inequality, often ~1 ft here). Under each past
       square, a faded circle shows what the model predicted
       <b>~24 hours ahead</b> — a decision-relevant alert horizon
       — so the square-to-circle gap is the forecast error you would
       actually have lived with (nearest logged run within 16–36 h;
       missing where the throttled hourly bot had no qualifying run).
       When burst-capable rain is in the forecast, navy triangles mark
       the rain-burst COMPOUND potential over the affected upcoming
       tides (same meaning as the burst band on the 24-h chart;
       plotted in SH-equivalent units — the gauge itself never records
       rain floods). Horizontal lines are the SH-MLLW thresholds at
       which the
       {CURRENT_MODEL_VERSION} model (enhancement 0.00, calibrated on
       4 tape-measured events, SH 6.17&ndash;7.29) predicts water
       reaches each landmark. <b>Caveats</b>: offshore peak winds run
       ~0.13 ft lower (see the wind adjustment); the 0.00 enhancement
       is untested by tape above SH ~7.3 (storm-surge extrapolation);
       and these are TIDE thresholds — rain floods ignore them
       entirely (see the rain pathway / burst band above).</p>
    <div class="heatmap-toggle unit-toggle">
      <span class="note">Units:</span>
      <label><input type="radio" name="osc-unit" value="in" checked>
        &Prime; vs SW grate</label>
      <label><input type="radio" name="osc-unit" value="mllw">
        ft MLLW</label>
    </div>
    <!-- Fixed-height wrapper + maintainAspectRatio:false — on phones a
         width-locked aspect ratio squashed the plot to ~50px once the
         legend took its rows (user screenshot 2026-07-07 PM). -->
    <div style="position:relative;height:360px;margin:8px auto">
      <canvas id="oscillation-chart"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js" integrity="sha384-FcQlsUOd0TJjROrBxhJdUhXTUgNJQxTMcxZe6nHbaEfFL1zjQ+bq/uRoBQxb0KMo" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js" integrity="sha384-oNtu+d18330MVFpltUTve1DatxCkkctlpA2AC3GulbVFOSqhHdDat3qHse/Lbuek" crossorigin="anonymous"></script>
    <script>
      (function() {{
        var data = {data_json};
        var points = data.points.slice().sort(function(a, b) {{
          return (a.time < b.time) ? -1 : (a.time > b.time ? 1 : 0);
        }});
        var labels = points.map(function(p) {{
          // Compact tide-time label (e.g., "Tue 5/19 11 PM")
          var d = new Date(p.time.replace(' ', 'T'));
          if (isNaN(d.getTime())) return p.time;
          return d.toLocaleString(undefined, {{
            weekday: 'short', month: 'numeric', day: 'numeric',
            hour: 'numeric'
          }});
        }});
        var observedData = points.map(function(p) {{
          return p.kind === 'observed' ? p.sh_peak_mllw : null;
        }});
        var predictedData = points.map(function(p) {{
          return p.kind === 'predicted' ? p.sh_peak_mllw : null;
        }});
        // What the model said ~24h before each PAST tide (null where
        // the throttled hourly log has no 16-36h-lead run). Drawn as
        // a faded halo under the observed square: the vertical gap IS
        // the forecast error at a decision-relevant alert horizon.
        var pred24Data = points.map(function(p) {{
          return p.predicted_24h_mllw != null ? p.predicted_24h_mllw : null;
        }});
        // Rain-burst compound potential for near-term future tides
        // (only present when pluvial risk is live) — navy triangles,
        // same meaning as the 24h chart's burst-band top.
        var burstData = points.map(function(p) {{
          return p.burst_potential_mllw != null ? p.burst_potential_mllw : null;
        }});
        var hasBurst = burstData.some(function(v) {{ return v != null; }});
        // Landmark threshold lines as constant DATASETS with legend
        // entries — the 2026-07-06 chart grammar (labels live in the
        // LEGEND, never boxes on the plot; boxes collided into soup on
        // phones). Shared palette with the water-level chart, so the
        // reader learns ONE color language.
        var landmarks = data.landmarks;
        var thresholds = landmarks.map(function(l) {{ return l.mllw_threshold; }});
        var minE = Math.min.apply(null, thresholds);
        var maxE = Math.max.apply(null, thresholds);
        // Short names: the legend is 7 entries on a ~360px phone —
        // every character costs a wrap row, and rows cost plot height.
        var LM_STYLE = {{
          grate_SW:        {{ color: '#222222', name: 'SW grate', solid: true }},
          gutter_walkway:  {{ color: '#2f8f5f', name: 'gutter' }},
          curb:            {{ color: '#c0392b', name: 'curb' }},
          lawn_step:       {{ color: '#7c4dbc', name: 'lawn step' }},
          porch_step1_top: {{ color: '#6d4c2f', name: 'porch step' }}
        }};
        var landmarkDatasets = landmarks.map(function(l) {{
          var st = LM_STYLE[l.key] || {{ color: '#888', name: l.label }};
          return {{
            label: st.name + ' ' + l.mllw_threshold.toFixed(2),
            data: labels.map(function() {{ return l.mllw_threshold; }}),
            borderColor: st.color,
            borderWidth: st.solid ? 1.5 : 1.2,
            borderDash: st.solid ? [] : [6, 5],
            fill: false, pointRadius: 0, spanGaps: true,
          }};
        }});
        // Unit toggle (user 2026-07-07): default inches-vs-SW-grate,
        // option ft MLLW. Shared preference + event with the flood-
        // peaks chart below so both flip together.
        var UNIT_KEY = 'barnacle-peaks-unit';
        var unit = 'in';
        try {{ unit = localStorage.getItem(UNIT_KEY) || 'in'; }} catch (e) {{}}
        var GRATE_SH = 6.34;   // the SW grate expressed at the gauge
        function conv(v) {{ return unit === 'in' ? (v - GRATE_SH) * 12 : v; }}
        function fmtShort(v) {{
          var c = conv(v);
          return unit === 'in'
            ? (c >= 0 ? '+' : '') + c.toFixed(1) + '\u2033' : c.toFixed(2);
        }}
        function fmtVal(v) {{
          return fmtShort(v) + (unit === 'in' ? ' vs SW grate' : ' ft MLLW');
        }}
        function cmap(arr) {{
          return arr.map(function(v) {{ return v == null ? null : conv(v); }});
        }}
        var ctx = document.getElementById('oscillation-chart').getContext('2d');
        var chart = null;
        function build() {{
          if (chart) chart.destroy();
          var lmDatasets = landmarks.map(function(l) {{
            var st = LM_STYLE[l.key] || {{ color: '#888', name: l.label }};
            return {{
              label: st.name + ' ' + fmtShort(l.mllw_threshold),
              data: labels.map(function() {{ return conv(l.mllw_threshold); }}),
              borderColor: st.color,
              borderWidth: st.solid ? 1.5 : 1.2,
              borderDash: st.solid ? [] : [6, 5],
              fill: false, pointRadius: 0, spanGaps: true,
            }};
          }});
          chart = new Chart(ctx, {{
            type: 'line',
            data: {{
              labels: labels,
              datasets: [
                {{
                  label: 'Observed SH peak',
                  data: cmap(observedData),
                  borderColor: 'rgba(60,60,60,0.85)',
                  backgroundColor: 'rgba(60,60,60,0.85)',
                  pointStyle: 'rect', pointRadius: 4,
                  spanGaps: true, showLine: false,
                }},
                {{
                  label: 'Predicted SH peak',
                  data: cmap(predictedData),
                  borderColor: 'rgba(31, 111, 235, 0.9)',
                  backgroundColor: 'rgba(31, 111, 235, 0.9)',
                  pointStyle: 'circle', pointRadius: 4,
                  spanGaps: true, showLine: false,
                }},
                {{
                  label: 'as predicted ~24 h ahead',
                  data: cmap(pred24Data),
                  borderColor: 'rgba(31, 111, 235, 0.45)',
                  backgroundColor: 'rgba(31, 111, 235, 0.25)',
                  pointStyle: 'circle', pointRadius: 7,
                  pointBorderWidth: 1.5,
                  spanGaps: true, showLine: false,
                }}
              ].concat(hasBurst ? [{{
                  label: 'rain-burst compound potential',
                  data: cmap(burstData),
                  borderColor: 'rgba(11, 61, 107, 0.95)',
                  backgroundColor: 'rgba(11, 61, 107, 0.35)',
                  pointStyle: 'triangle', pointRadius: 6,
                  spanGaps: true, showLine: false,
                }}] : []).concat(lmDatasets)
            }},
            options: {{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {{
                tooltip: {{
                  filter: function(item) {{
                    return item.datasetIndex < (hasBurst ? 4 : 3);
                  }},
                  callbacks: {{
                    label: function(c) {{
                      var p = points[c.dataIndex];
                      if (!p) return c.formattedValue;
                      if (hasBurst && c.datasetIndex === 3) {{
                        return [
                          'If a forecast-class burst lands on this tide:',
                          'street water \u2248 ' +
                            fmtVal(p.burst_potential_mllw) +
                            (unit === 'in' ? '' :
                             ' (SH-equivalent \u2014 the gauge never' +
                             ' reads rain floods)'),
                        ];
                      }}
                      if (c.datasetIndex === 2) {{
                        var err = conv(p.predicted_24h_mllw) -
                                  conv(p.sh_peak_mllw);
                        var eu = unit === 'in' ? '\u2033' : ' ft';
                        return [
                          '~24 h ahead we said: ' +
                            fmtVal(p.predicted_24h_mllw),
                          'It came in: ' + fmtShort(p.sh_peak_mllw) +
                            ' (' + (err >= 0 ? '+' : '') +
                            err.toFixed(unit === 'in' ? 1 : 2) +
                            eu + ' error)',
                        ];
                      }}
                      return [
                        (p.kind === 'observed' ? 'Observed' : 'Predicted'),
                        fmtVal(p.sh_peak_mllw),
                      ];
                    }}
                  }}
                }},
                legend: {{ position: 'top',
                           labels: {{ boxWidth: 22, boxHeight: 2,
                                      font: {{ size: 10 }} }} }}
              }},
              scales: {{
                x: {{
                  title: {{ display: true, text: 'Tide peak (local time)',
                            font: {{ size: 11 }} }},
                  ticks: {{ maxTicksLimit: 8, font: {{ size: 10 }},
                            maxRotation: 50 }},
                  grid: {{ color: 'rgba(0,0,0,0.05)' }}
                }},
                y: {{
                  title: {{ display: true,
                            text: unit === 'in'
                              ? 'inches vs SW grate'
                              : 'Sandy Hook peak (ft MLLW)',
                            font: {{ size: 11 }} }},
                  ticks: {{ font: {{ size: 10 }} }},
                  grid: {{ color: 'rgba(0,0,0,0.06)' }},
                  suggestedMin: conv(Math.min(minE - 0.2,
                    Math.min.apply(null,
                      points.map(function(p) {{ return p.sh_peak_mllw; }})))),
                  suggestedMax: conv(Math.max(maxE + 0.2,
                    Math.max.apply(null,
                      points.map(function(p) {{
                        return Math.max(p.sh_peak_mllw,
                                        p.burst_potential_mllw || 0);
                      }})))),
                }}
              }}
            }}
          }});
        }}
        build();
        var radios = document.querySelectorAll('input[name="osc-unit"]');
        function syncRadios() {{
          radios.forEach(function(r) {{ r.checked = (r.value === unit); }});
        }}
        syncRadios();
        radios.forEach(function(r) {{
          r.addEventListener('change', function() {{
            try {{ localStorage.setItem(UNIT_KEY, r.value); }} catch (e) {{}}
            document.dispatchEvent(new CustomEvent('barnacle-peaks-unit'));
          }});
        }});
        document.addEventListener('barnacle-peaks-unit', function() {{
          try {{ unit = localStorage.getItem(UNIT_KEY) || 'in'; }} catch (e) {{}}
          syncRadios();
          build();
        }});
      }})();
    </script>
  </section>
"""


def _render_flood_peaks_section(forecast):
    """The all-pathways companion to the per-tide peaks chart above it
    (2026-07-07, user: "we care about flooding any time" — rain-only
    floods happen between tides and at low tide; the per-tide axis
    cannot show them). Continuous TIME x-axis, local-water y-axis.
    Kept alongside the original per-tide chart for now (single-user
    A/B; a keep/retire decision can come later)."""
    data = _flood_peaks_chart_data(forecast)
    if len(data["tides"]) < 2:
        return ""
    data_json = json.dumps(data, default=str)
    js = r"""
      (function() {
        var FULL = __DATA__;
        // Default window = the original view: last 7 days + forecast.
        // The payload now carries the FULL record (back to 2026-05-18);
        // the From/To pickers re-slice it client-side.
        var data = FULL;
        function sliceData(fromMs, toMs) {
          function inWin(t) {
            var ms = new Date(String(t).replace(' ', 'T')).getTime();
            return !isNaN(ms) && ms >= fromMs && ms <= toMs;
          }
          return {
            tides: FULL.tides.filter(function(p) { return inWin(p.time); }),
            measured: FULL.measured.filter(function(p) {
              return inWin(p.time); }),
            lows: (FULL.lows || []).filter(function(p) {
              return inWin(p.time); }),
            risk_days: FULL.risk_days.filter(function(p) {
              return inWin(p.day + ' 12:00'); }),
            landmarks: FULL.landmarks
          };
        }
        function defaultWindow() {
          var now = Date.now();
          return [now - 7 * 864e5, now + 3.5 * 864e5];
        }
        var GRATE = 3.52, MLLW_OFF = 2.82;
        var UNIT_KEY = 'barnacle-peaks-unit';
        var unit = 'in';
        try { unit = localStorage.getItem(UNIT_KEY) || 'in'; } catch (e) {}
        function conv(v) {
          return unit === 'in' ? (v - GRATE) * 12 : v + MLLW_OFF;
        }
        function fmtShort(v) {
          var c = conv(v);
          return unit === 'in'
            ? (c >= 0 ? '+' : '') + c.toFixed(1) + '″' : c.toFixed(2);
        }
        function fmtVal(v) {
          return fmtShort(v) + (unit === 'in' ? ' vs SW grate' : ' ft MLLW');
        }
        function T(str) {
          var d = new Date(str.replace(' ', 'T'));
          return isNaN(d.getTime()) ? null : d.getTime();
        }
        function fmtTick(ms) {
          return new Date(ms).toLocaleDateString(undefined,
            { weekday: 'short', month: 'numeric', day: 'numeric' });
        }
        var LM_STYLE = {
          grate_SW:        { color: '#222222', name: 'SW grate', solid: true },
          gutter_walkway:  { color: '#2f8f5f', name: 'gutter' },
          curb:            { color: '#c0392b', name: 'curb' },
          lawn_step:       { color: '#7c4dbc', name: 'lawn step' },
          porch_step1_top: { color: '#6d4c2f', name: 'porch step' }
        };
        var nowMs = Date.now();
        var LOWS_KEY = 'barnacle-peaks-lows';
        // Marker scaling (2026-08-20): auto-shrink as the window
        // widens (sqrt law: ~1.0 at <=10 days, floor 0.35) unless the
        // user drags the size slider (manual until auto re-checked).
        var sizeAuto = true, sizeManual = 1.0;
        function sizeFactor() {
          if (!sizeAuto) return sizeManual;
          var spanD = (xMax - xMin) / 864e5;
          return Math.max(0.35, Math.min(1.0,
            Math.sqrt(10 / Math.max(spanD, 1))));
        }
        var showLows = false;
        try { showLows = localStorage.getItem(LOWS_KEY) === '1'; }
        catch (e) {}
        // All point arrays + axis bounds derive from the CURRENT
        // window (2026-08-20 fix: these were computed once from the
        // full payload, so the first render ignored the default
        // 7-day slice and pinned the axis at the earliest measured
        // flood — Oct 30 2025).
        var allX, obsP, futP, astroP, p24P, burstP, measP, lowP,
            riskSeg, xMin, xMax, allY;
        function derive() {
          allX = [];
          function pts(rows, field, kindFilter) {
            var out = [];
            (rows || []).forEach(function(r) {
              if (kindFilter && r.kind !== kindFilter) return;
              var v = field ? r[field] : r.navd88;
              var x = T(r.time);
              if (v == null || x == null) return;
              allX.push(x);
              out.push({ x: x, y: v, src: r });
            });
            return out;
          }
          obsP    = pts(data.tides, null, 'observed');
          futP    = pts(data.tides, null, 'predicted');
          astroP  = pts(data.tides, null, 'astro');
          p24P    = pts(data.tides, 'pred24_navd88', null);
          burstP  = pts(data.tides, 'burst_navd88', null);
          measP   = pts(data.measured, null, null);
          lowP    = showLows ? pts(data.lows, null, null) : [];
          // Day-wide archived-risk segments: pairs separated by a
          // null gap so each day is its own dash.
          riskSeg = [];
          data.risk_days.forEach(function(r) {
            var d0 = T(r.day + ' 00:00'), d1 = T(r.day + ' 23:59');
            if (d0 == null) return;
            allX.push(d0, d1);
            riskSeg.push({ x: d0, y: r.navd88, src: r });
            riskSeg.push({ x: d1, y: r.navd88, src: r });
            riskSeg.push({ x: (d0 + d1) / 2, y: null });
          });
          xMin = Math.min.apply(null, allX.concat([nowMs])) - 6*3600e3;
          xMax = Math.max.apply(null, allX.concat([nowMs])) + 6*3600e3;
          allY = [];
          [obsP, futP, astroP, p24P, burstP, measP, lowP].forEach(
            function(a) {
            a.forEach(function(q) { allY.push(q.y); });
          });
          riskSeg.forEach(function(q) { if (q.y != null) allY.push(q.y); });
          data.landmarks.forEach(function(l) { allY.push(l.navd88); });
        }
        derive();
        var ctx = document.getElementById('flood-peaks-chart')
                    .getContext('2d');
        var chart = null;
        function cpts(a) {
          return a.map(function(q) {
            return { x: q.x, y: q.y == null ? null : conv(q.y), src: q.src };
          });
        }
        function build() {
          derive();
          var sf = sizeFactor();
          function r(base) { return Math.max(0.6, base * sf); }
          var sizeSlider = document.getElementById('fpk-size');
          if (sizeSlider && sizeAuto) sizeSlider.value = sf.toFixed(2);
          if (chart) chart.destroy();
          var lmDatasets = data.landmarks.map(function(l) {
            var st = LM_STYLE[l.key] || { color: '#888', name: l.key };
            return {
              label: st.name + ' ' + fmtShort(l.navd88),
              data: [{ x: xMin, y: conv(l.navd88) },
                     { x: xMax, y: conv(l.navd88) }],
              borderColor: st.color,
              borderWidth: st.solid ? 1.5 : 1.2,
              borderDash: st.solid ? [] : [6, 5],
              fill: false, pointRadius: 0, showLine: true,
            };
          });
          var core = [
            { label: 'Predicted LOW tide (astronomy)',
              data: cpts(lowP),
              pointStyle: 'triangle', rotation: 180, pointRadius: r(2.5),
              pointBackgroundColor: 'rgba(112,128,144,0.7)',
              pointBorderColor: 'rgba(112,128,144,0.9)',
              borderColor: 'rgba(112,128,144,0.9)',
              backgroundColor: 'rgba(112,128,144,0.7)',
              showLine: false },
            { label: 'Observed tide peak', data: cpts(obsP),
              borderColor: 'rgba(60,60,60,0.85)',
              backgroundColor: 'rgba(60,60,60,0.85)',
              pointStyle: 'rect', pointRadius: r(4), showLine: false },
            { label: 'Astronomical peak (no surge)', data: cpts(astroP),
              pointStyle: 'circle', pointRadius: r(3),
              pointBackgroundColor: 'rgba(26,95,168,0.30)',
              pointBorderColor: 'rgba(26,95,168,0.45)',
              borderColor: 'rgba(26,95,168,0.45)',
              backgroundColor: 'rgba(26,95,168,0.30)',
              showLine: false },
            { label: 'Predicted tide peak', data: cpts(futP),
              borderColor: 'rgba(31,111,235,0.9)',
              backgroundColor: 'rgba(31,111,235,0.9)',
              pointStyle: 'circle', pointRadius: r(4), showLine: false },
            { label: 'as predicted ~24 h ahead', data: cpts(p24P),
              borderColor: 'rgba(31,111,235,0.45)',
              backgroundColor: 'rgba(31,111,235,0.25)',
              pointStyle: 'circle', pointRadius: r(7),
              pointBorderWidth: 1.5, showLine: false },
          ];
          if (measP.length) core.push(
            { label: 'MEASURED flood (spot-check, any cause)',
              data: cpts(measP),
              borderColor: 'rgba(11,61,107,1)',
              backgroundColor: 'rgba(217,119,6,0.9)',
              pointStyle: 'rectRot', pointRadius: r(7),
              pointBorderWidth: 2, showLine: false });
          if (burstP.length) core.push(
            { label: 'rain-burst compound potential', data: cpts(burstP),
              borderColor: 'rgba(11,61,107,0.95)',
              backgroundColor: 'rgba(11,61,107,0.35)',
              pointStyle: 'triangle', pointRadius: r(6), showLine: false });
          if (riskSeg.length) core.push(
            { label: 'burst potential archived that day', data: cpts(riskSeg),
              borderColor: 'rgba(11,61,107,0.45)',
              borderWidth: 3, borderDash: [2, 3],
              pointRadius: 0, showLine: true, spanGaps: false });
          var nCore = core.length;
          chart = new Chart(ctx, {
            type: 'scatter',
            data: { datasets: core.concat(lmDatasets) },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                annotation: { annotations: {
                  nowline: {
                    type: 'line', xMin: nowMs, xMax: nowMs,
                    borderColor: '#888', borderWidth: 1,
                    borderDash: [3, 3],
                    label: { display: true, content: 'now',
                             position: 'start',
                             backgroundColor: 'rgba(255,255,255,0.75)',
                             color: '#666', font: { size: 9 } }
                  }
                } },
                tooltip: {
                  filter: function(item) {
                    return item.datasetIndex < nCore;
                  },
                  callbacks: {
                    title: function(items) {
                      if (!items.length) return '';
                      return new Date(items[0].parsed.x).toLocaleString(
                        undefined, { weekday: 'short', month: 'numeric',
                                     day: 'numeric', hour: 'numeric',
                                     minute: '2-digit' });
                    },
                    label: function(c) {
                      var raw = c.raw || {};
                      var lbl = c.dataset.label + ': ';
                      var y = raw.src && raw.src.navd88 != null
                        ? raw.src.navd88
                        : (raw.src && raw.src.burst_navd88) || null;
                      return lbl + (c.parsed.y >= 0 && unit === 'in'
                        ? '+' : '') +
                        c.parsed.y.toFixed(unit === 'in' ? 1 : 2) +
                        (unit === 'in' ? '″ vs SW grate'
                                       : ' ft MLLW-equivalent');
                    }
                  }
                },
                legend: { position: 'top',
                          labels: { boxWidth: 22, boxHeight: 2,
                                    font: { size: 10 } } }
              },
              scales: {
                x: {
                  type: 'linear', min: xMin, max: xMax,
                  ticks: {
                    maxTicksLimit: 8, font: { size: 10 },
                    maxRotation: 50,
                    callback: function(v) { return fmtTick(v); }
                  },
                  grid: { color: 'rgba(0,0,0,0.05)' }
                },
                y: {
                  title: { display: true,
                           text: unit === 'in'
                             ? 'inches vs SW grate'
                             : 'ft MLLW (gauge-equivalent)',
                           font: { size: 11 } },
                  ticks: { font: { size: 10 } },
                  grid: { color: 'rgba(0,0,0,0.06)' },
                  suggestedMin: conv(Math.min.apply(null, allY)) -
                                (unit === 'in' ? 3 : 0.25),
                  suggestedMax: conv(Math.max.apply(null, allY)) +
                                (unit === 'in' ? 3 : 0.25),
                }
              }
            }
          });
        }
        var radios = document.querySelectorAll('input[name="fpk-unit"]');
        function syncRadios() {
          radios.forEach(function(r) { r.checked = (r.value === unit); });
        }
        syncRadios();
        radios.forEach(function(r) {
          r.addEventListener('change', function() {
            try { localStorage.setItem(UNIT_KEY, r.value); } catch (e) {}
            document.dispatchEvent(new CustomEvent('barnacle-peaks-unit'));
          });
        });
        document.addEventListener('barnacle-peaks-unit', function() {
          try { unit = localStorage.getItem(UNIT_KEY) || 'in'; } catch (e) {}
          syncRadios();
          build();
        });
        (function wireRange() {
          var fromI = document.getElementById('fpk-from');
          var toI = document.getElementById('fpk-to');
          var applyB = document.getElementById('fpk-apply');
          var resetB = document.getElementById('fpk-reset');
          if (!fromI) return;
          var dw = defaultWindow();
          function iso(ms) {
            var d = new Date(ms);   // LOCAL date, not a UTC slice
            return d.getFullYear() + '-' +
              String(d.getMonth() + 1).padStart(2, '0') + '-' +
              String(d.getDate()).padStart(2, '0');
          }
          var sizeS = document.getElementById('fpk-size');
          var sizeA = document.getElementById('fpk-size-auto');
          sizeS.addEventListener('input', function() {
            sizeManual = parseFloat(sizeS.value) || 1.0;
            sizeAuto = false; sizeA.checked = false;
            build();
          });
          sizeA.addEventListener('change', function() {
            sizeAuto = sizeA.checked;
            build();
          });
          var lowsBox = document.getElementById('fpk-lows');
          lowsBox.checked = showLows;
          lowsBox.addEventListener('change', function() {
            showLows = lowsBox.checked;
            try {
              localStorage.setItem(LOWS_KEY, showLows ? '1' : '0');
            } catch (e) {}
            build();
          });
          fromI.value = iso(dw[0]); toI.value = iso(dw[1]);
          // picker bounds from the payload itself: earliest record
          // (Oct 30 2025 measured flood) → last forecast point,
          // applied to BOTH pickers so neither scrolls into empty
          // decades (2026-08-20 fix: min was on From only, and too
          // late by seven months)
          var dataMs = [];
          [FULL.tides, FULL.measured, FULL.lows || []].forEach(
            function(a) {
              a.forEach(function(q) {
                var t = new Date(String(q.time).replace(' ', 'T'))
                  .getTime();
                if (!isNaN(t)) dataMs.push(t);
              });
            });
          var lo = iso(Math.min.apply(null, dataMs));
          var hi = iso(Math.max.apply(null, dataMs) + 3 * 864e5);
          fromI.min = lo; toI.min = lo;
          fromI.max = hi; toI.max = hi;
          function apply() {
            var f = new Date(fromI.value + 'T00:00').getTime();
            var t = new Date(toI.value + 'T23:59').getTime();
            if (isNaN(f) || isNaN(t) || f >= t) return;
            data = sliceData(f, t);
            build();
          }
          applyB.addEventListener('click', apply);
          resetB.addEventListener('click', function() {
            var d = defaultWindow();
            fromI.value = iso(d[0]); toI.value = iso(d[1]);
            data = sliceData(d[0], d[1]);
            build();
          });
        })();
        data = sliceData(defaultWindow()[0], defaultWindow()[1]);
        build();
      })();
""".replace("__DATA__", data_json)
    return """
  <section class="oscillation">
    <h2>Flood peaks at 342 Bay — past &amp; forecast (all pathways)</h2>
    <details class="chart-explain">
    <summary>Explain this figure</summary>
    <p class="note">The tide-only view (toggle above) is organized
       BY TIDE — but this corner floods on rain alone, between tides,
       even at dead low tide (7/6/2026). This default view puts
       everything on a real TIME axis in local units: tide peaks (observed ■ / predicted ●
       / faded halo = what we said ~24&nbsp;h ahead), <b>measured
       flood peaks from the spot-check log</b> (orange diamonds — any
       cause, placed when they actually happened), navy triangles =
       rain-burst compound potential on upcoming tides, and faint
       navy day-dashes = days whose archived forecast carried live
       burst risk (day-wide, because a burst has magnitude but no
       forecastable clock time; the dash height is the day's MAXIMUM
       archived assessment from 2026-07-08 onward — dashes before
       that show only the day's last run, which can postdate the
       event: the 7/6 dash is the post-storm evening residue, not a
       hindcast; nothing predicted that flood — the QPF input was
       broken and the pluvial model didn't exist until that
       evening). A rain flood with no halo under it =
       a miss the tide model could never have seen; that is the point
       of this chart.</p>
    </details>
    <div class="heatmap-toggle unit-toggle">
      <span class="note">Units:</span>
      <label><input type="radio" name="fpk-unit" value="in" checked>
        &Prime; vs SW grate</label>
      <label><input type="radio" name="fpk-unit" value="mllw">
        ft MLLW</label>
      <span class="note" style="margin-left:12px">Window:</span>
      <input type="date" id="fpk-from" style="font-size:12px">
      <span class="note">to</span>
      <input type="date" id="fpk-to" style="font-size:12px">
      <button type="button" id="fpk-apply" style="font-size:12px">Apply</button>
      <button type="button" id="fpk-reset" style="font-size:12px">Default view</button>
      <label style="margin-left:10px"><input type="checkbox" id="fpk-lows">
        <span class="note">low tides</span></label>
      <span class="note" style="margin-left:10px">marker size:</span>
      <input type="range" id="fpk-size" min="0.1" max="2.0" step="0.05"
             value="1.0" style="width:90px;vertical-align:middle">
      <label><input type="checkbox" id="fpk-size-auto" checked>
        <span class="note">auto</span></label>
    </div>
    <div style="position:relative;height:380px;margin:8px auto">
      <canvas id="flood-peaks-chart"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js" integrity="sha384-FcQlsUOd0TJjROrBxhJdUhXTUgNJQxTMcxZe6nHbaEfFL1zjQ+bq/uRoBQxb0KMo" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js" integrity="sha384-oNtu+d18330MVFpltUTve1DatxCkkctlpA2AC3GulbVFOSqhHdDat3qHse/Lbuek" crossorigin="anonymous"></script>
    <script>""" + js + """    </script>
  </section>
"""


def render_per_tide_page(tide, forecast,
                          prev_slug=None, prev_time=None,
                          next_slug=None, next_time=None):
    """Render a single per-tide deep-link HTML page. Focuses on ONE tide:
    its predicted peak, surge breakdown, depths at landmarks, link to
    evolution.csv (the per-tide slice of the master predictions log).

    `prev_slug` / `next_slug` (with `prev_time` / `next_time` for the
    link labels) wire up "← prev tide / next tide →" navigation in the
    page header so users can walk through upcoming tides without going
    back to the home page (HANDOFF 9b.2 — "T" in the solo-work backlog).

    The page is at docs/tides/<slug>/index.html so it's two levels deep
    from the repo root — all asset paths get a "../../" prefix.

    HANDOFF 9b.2."""
    td = tide["depths_in"]
    regime = td["regime"]
    time_str = tide["time"]
    short, above_in, rel_in = landmark_summary(td, tide["forecast_peak_mllw"])

    # Prev / next tide navigation (HANDOFF 9b.2 — "T" in solo backlog).
    prev_link = (
        f'<a href="../{prev_slug}/">&larr; {format_time_full(prev_time)}</a>'
        if prev_slug and prev_time else '<span class="nav-disabled">&larr; —</span>'
    )
    next_link = (
        f'<a href="../{next_slug}/">{format_time_full(next_time)} &rarr;</a>'
        if next_slug and next_time else '<span class="nav-disabled">— &rarr;</span>'
    )

    # Prediction-log status (CC — observability). Tells the reader how
    # much data this tide has accumulated and at what cadence.
    log_stats = _per_tide_log_stats(time_str)
    if log_stats:
        n = log_stats["n"]
        span = log_stats["span_hours"]
        cadence = log_stats["avg_cadence_min"]
        bits = [f"<b>{n}</b> prediction{'s' if n != 1 else ''} logged"]
        if span is not None:
            bits.append(f"over {span:.1f} h")
        if cadence is not None:
            bits.append(f"({cadence:.0f} min cadence avg)")
        log_status_html = (
            '<section class="log-status">'
            '<p class="note">' + " ".join(bits) +
            ' for this tide so far. Updates as the hourly workflow ticks.</p>'
            '</section>'
        )
    else:
        log_status_html = (
            '<section class="log-status">'
            '<p class="note">No predictions logged yet for this tide. '
            'Rows accumulate as the hourly workflow runs leading up to '
            'the peak.</p>'
            '</section>'
        )

    # Per-tide heat-map: build a fake "forecast" with this tide as the
    # worst-case so _client_map_section_html renders for THIS tide's
    # water level (not the home page's worst-case). HANDOFF 9b.10.
    tide_as_forecast = {
        "peak_forecast_observed_mllw": tide["forecast_peak_mllw"],
        "cold_lockout": forecast.get("cold_lockout", False),
        "peak_rain_rate_in_hr": tide.get("peak_rain_in_hr") or 0.0,
        "peak_time_local": tide["time"],
    }
    tide_heatmap_section = _client_map_section_html(
        tide_as_forecast,
        container_class="heatmap",
        level=2,
        base_map_url="../../icons/map_raw.png",
    )

    # Landmark rows
    rows = ""
    for key, label, elev, sh in LANDMARKS:
        depth = td.get(key, 0.0) or 0.0
        wet = depth > 0
        row_cls = ' class="wet"' if wet else ""
        rows += (
            f'<tr{row_cls}>'
            f'<td>{label}</td>'
            f'<td>{elev:.2f}</td>'
            f'<td>{sh:.2f}</td>'
            f'<td>{depth:+.1f}&Prime;</td>'
            f'</tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tide {time_str} — Bay Ave Barnacle</title>
<link rel="stylesheet" href="../../style.css">
<meta name="description" content="Bay Ave Barnacle — high tide at {format_time_full(time_str)}: {regime_display(regime).upper()} regime, peak {tide['forecast_peak_mllw']:.2f} ft MLLW Sandy Hook.">
<!-- Open Graph — W -->
<meta property="og:title" content="High tide {format_time_full(time_str)} — Bay Ave Barnacle">
<meta property="og:description" content="{regime_display(regime).upper()} regime. Forecast peak {tide['forecast_peak_mllw']:.2f} ft MLLW Sandy Hook.">
<meta property="og:image" content="https://johnurban.github.io/barnacle/icons/icon-512.png">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
</head>
<body>
<main>
  <header>
    <h1>High tide @ {format_time_full(time_str)}</h1>
    <p class="subtitle"><a href="../../">&larr; Back to today's forecast</a></p>
    <nav class="tide-nav">
      <span class="tide-nav-prev">{prev_link}</span>
      <span class="tide-nav-next">{next_link}</span>
    </nav>
  </header>

  <section class="regime regime-{regime}">
    <div class="regime-label">{regime_display(regime).upper()}</div>
    <div class="regime-summary">{REGIME_GLOSSARY.get(regime, '')}.
       Peak forecast: <b>{tide['forecast_peak_mllw']:.2f} ft MLLW</b> Sandy Hook.</div>
  </section>

  <section class="forecast">
    <h2>This tide</h2>
    <dl>
      <dt>High tide time</dt><dd>{format_time_full(time_str)}</dd>
      <dt>Predicted tide (astronomical)</dt><dd>{tide['predicted_mllw']:.2f} ft MLLW</dd>
      <dt>Surge</dt><dd>{tide['surge_ft']:+.2f} ft</dd>
      <dt>Forecast peak (tide + surge)</dt><dd>{tide['forecast_peak_mllw']:.2f} ft MLLW</dd>
      <dt>Surge source</dt><dd>{tide.get('source', '')}</dd>
      <dt>Peak rainfall in ±90 min window</dt><dd>{(tide.get('peak_rain_in_hr') or 0):.2f} in/hr</dd>
      <dt>Highest landmark reached</dt><dd>{short} ({above_in:+.1f}&Prime; above; {rel_in:+.1f}&Prime; rel to lowest landmark)</dd>
    </dl>
  </section>

{log_status_html}
{tide_heatmap_section}
  <section class="scrubber-section">
    <h2>Replay forecast evolution</h2>
    <p class="note">Scrub through past predictions for this tide and see
       how the heat-map (above) would have looked at each point. Loads
       <a href="evolution.csv">evolution.csv</a> — HANDOFF 9b.4(c).</p>
    <div class="scrubber-controls">
      <button type="button" id="scrubber-play" aria-label="Play / pause">▶︎ Play</button>
      <input type="range" id="scrubber-range" min="0" max="0" value="0" step="1" disabled>
      <span id="scrubber-label" class="scrubber-label">Loading…</span>
    </div>
    <script>
      (function() {{
        var btn = document.getElementById('scrubber-play');
        var range = document.getElementById('scrubber-range');
        var label = document.getElementById('scrubber-label');
        var canvas = document.getElementById('heatmap-canvas');
        if (!canvas) {{
          label.textContent = '(no heat-map to scrub)';
          return;
        }}
        var rows = [];
        var playing = false;
        var playTimer = null;
        function fmtTime(iso) {{
          // iso like "2026-05-19T16:26:29Z"
          var d = new Date(iso);
          if (isNaN(d.getTime())) return iso;
          return d.toLocaleString(undefined, {{
            month: 'numeric', day: 'numeric',
            hour: 'numeric', minute: '2-digit'
          }});
        }}
        function showStep(i) {{
          var r = rows[i];
          if (!r) return;
          var hu = parseFloat(r.hours_until_peak);
          var huTxt = isNaN(hu) ? '' : (
            ' (' + Math.abs(hu).toFixed(1) + ' h '
            + (hu >= 0 ? 'before' : 'after') + ' peak)'
          );
          label.textContent = 'Predicted at ' + fmtTime(r.prediction_made_at) +
            huTxt + ' — water ' +
            parseFloat(r.water_navd88_predicted).toFixed(2) + ' ft NAVD88';
          if (typeof BarnacleMap !== 'undefined') {{
            BarnacleMap.render({{
              canvas: canvas,
              points: window.barnaclePoints,
              waterNavd88: parseFloat(r.water_navd88_predicted),
              style: window.barnacleMapStyle || 'bands',
              baseMapUrl: '../../icons/map_raw.png',
              title: 'As predicted at ' + fmtTime(r.prediction_made_at),
            }});
          }}
          // FF — link the views: highlight the matching point on the
          // convergence chart. Match by hours_until_peak (same source
          // field both use). Guarded for the case where the chart's
          // script hasn't run yet (initial page load order).
          if (window.convergenceChart && window.convergencePoints) {{
            var hu = parseFloat(r.hours_until_peak);
            var matchIdx = -1;
            for (var j = 0; j < window.convergencePoints.length; j++) {{
              if (Math.abs(window.convergencePoints[j].hours_until_peak - hu)
                  < 0.01) {{
                matchIdx = j;
                break;
              }}
            }}
            if (matchIdx >= 0) {{
              window.convergenceChart.setActiveElements([
                {{datasetIndex: 0, index: matchIdx}}
              ]);
              window.convergenceChart.update('none');
            }} else {{
              window.convergenceChart.setActiveElements([]);
              window.convergenceChart.update('none');
            }}
          }}
        }}
        function setPlaying(p) {{
          playing = p;
          btn.textContent = playing ? '⏸ Pause' : '▶︎ Play';
          if (playing) {{
            playTimer = setInterval(function() {{
              var next = parseInt(range.value, 10) + 1;
              if (next > parseInt(range.max, 10)) next = 0;
              range.value = next;
              showStep(next);
            }}, 800);
          }} else if (playTimer) {{
            clearInterval(playTimer);
            playTimer = null;
          }}
        }}
        btn.addEventListener('click', function() {{
          if (rows.length < 2) return;
          setPlaying(!playing);
        }});
        range.addEventListener('input', function() {{
          if (playing) setPlaying(false);
          showStep(parseInt(range.value, 10));
        }});
        fetch('evolution.csv').then(function(r) {{
          if (!r.ok) throw new Error('no evolution.csv yet');
          return r.text();
        }}).then(function(text) {{
          var lines = text.trim().split('\\n');
          if (lines.length < 2) {{
            label.textContent = 'No prediction history yet. Fills in '
              + 'as the hourly workflow logs predictions.';
            return;
          }}
          var headers = lines[0].split(',');
          var idx = {{}};
          headers.forEach(function(h, i) {{ idx[h] = i; }});
          for (var i = 1; i < lines.length; i++) {{
            var cols = lines[i].split(',');
            rows.push({{
              prediction_made_at: cols[idx['prediction_made_at']],
              target_tide_time:   cols[idx['target_tide_time']],
              hours_until_peak:   cols[idx['hours_until_peak']],
              sh_peak_mllw_predicted:
                cols[idx['sh_peak_mllw_predicted']],
              water_navd88_predicted:
                cols[idx['water_navd88_predicted']],
            }});
          }}
          if (rows.length < 2) {{
            label.textContent = 'Only one prediction logged so far. '
              + 'Slider unlocks at ≥2 predictions.';
            return;
          }}
          range.disabled = false;
          range.min = '0';
          range.max = String(rows.length - 1);
          range.value = String(rows.length - 1);  // start at the latest
          showStep(rows.length - 1);
        }}).catch(function(e) {{
          label.textContent = 'No evolution data yet (' + e.message + ').';
        }});
      }})();
    </script>
  </section>

  <section class="landmarks">
    <h2>Predicted depths at landmarks</h2>
    <table class="landmark-table">
      <thead><tr><th>Landmark</th><th>NAVD88</th><th>SH threshold (MLLW)</th><th>Predicted depth</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="note">Depth is the height of water above each landmark
       elevation, in inches. Negative = water below this landmark.</p>
  </section>

  <section class="evolution">
    <h2>Prediction convergence</h2>
    <p>How the forecast for this tide has evolved as the tide approaches.
       Each point is one prediction event from
       <a href="evolution.csv">evolution.csv</a> (slice of the
       <a href="https://github.com/JohnUrban/barnacle/blob/main/data/predictions_log.csv">master
       predictions log</a>). x = hours from peak (negative = before),
       y = predicted Sandy Hook peak in ft MLLW. HANDOFF 9b.4(a).</p>
    <canvas id="convergence-chart" width="800" height="380"
            style="max-width:100%;height:auto;display:block;margin:8px auto"></canvas>
    <p id="convergence-note" class="note" style="text-align:center"></p>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js" integrity="sha384-FcQlsUOd0TJjROrBxhJdUhXTUgNJQxTMcxZe6nHbaEfFL1zjQ+bq/uRoBQxb0KMo" crossorigin="anonymous"></script>
    <script>
      (function() {{
        var note = document.getElementById('convergence-note');
        fetch('evolution.csv').then(function(r) {{
          if (!r.ok) throw new Error('evolution.csv not found');
          return r.text();
        }}).then(function(text) {{
          var lines = text.trim().split('\\n');
          if (lines.length < 2) {{
            note.textContent = 'No prediction history yet for this tide. '
              + 'The chart fills in as the hourly workflow logs predictions.';
            return;
          }}
          var headers = lines[0].split(',');
          var idx = {{}};
          headers.forEach(function(h, i) {{ idx[h] = i; }});
          var points = [];
          for (var i = 1; i < lines.length; i++) {{
            var cols = lines[i].split(',');
            var hu = parseFloat(cols[idx['hours_until_peak']]);
            var sh = parseFloat(cols[idx['sh_peak_mllw_predicted']]);
            var wat = parseFloat(cols[idx['water_navd88_predicted']]);
            var conf = cols[idx['confidence_level']] || '';
            if (isNaN(hu) || isNaN(sh)) continue;
            // x = "hours from peak" (negative = before; convergence reads left→right)
            points.push({{ x: -hu, y: sh, water: wat, conf: conf, hours_until_peak: hu }});
          }}
          points.sort(function(a, b) {{ return a.x - b.x; }});
          if (points.length < 2) {{
            note.textContent = 'Only one prediction logged so far for this tide. '
              + 'The convergence curve will appear after the next workflow run.';
          }} else {{
            note.textContent = points.length + ' predictions logged. '
              + 'Convergence pattern reveals how the forecast settles as the tide approaches.';
          }}
          // Expose the parsed points so the scrubber can find the
          // index matching a given prediction_made_at (FF).
          window.convergencePoints = points;
          var ctx = document.getElementById('convergence-chart').getContext('2d');
          // Expose for the scrubber to highlight the active point (FF —
          // link the three interactive views on per-tide pages)
          window.convergenceChart = new Chart(ctx, {{
            type: 'line',
            data: {{
              datasets: [{{
                label: 'Predicted SH peak (ft MLLW)',
                data: points,
                borderColor: 'rgba(31, 111, 235, 0.9)',
                backgroundColor: 'rgba(31, 111, 235, 0.15)',
                pointRadius: 4,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: 'rgba(217, 119, 6, 1)',
                tension: 0.2,
              }}]
            }},
            options: {{
              responsive: true,
              plugins: {{
                tooltip: {{
                  callbacks: {{
                    label: function(ctx) {{
                      var p = ctx.raw;
                      var lines = [
                        'Predicted SH peak: ' + p.y.toFixed(2) + ' ft MLLW',
                      ];
                      if (!isNaN(p.water)) {{
                        lines.push('Water at 342: ' + p.water.toFixed(2) + ' ft NAVD88');
                      }}
                      lines.push('Made ' + Math.abs(p.x).toFixed(1) + ' h '
                        + (p.x < 0 ? 'before' : 'after') + ' peak');
                      if (p.conf) lines.push('Confidence: ' + p.conf.toUpperCase());
                      return lines;
                    }}
                  }}
                }},
                legend: {{ display: false }}
              }},
              scales: {{
                x: {{
                  type: 'linear',
                  title: {{ display: true,
                           text: 'Hours from peak (negative = before)' }},
                  grid: {{ color: function(c) {{
                    return c.tick.value === 0 ? 'rgba(217, 119, 6, 0.5)' : 'rgba(0,0,0,0.06)';
                  }} }}
                }},
                y: {{
                  title: {{ display: true, text: 'Predicted SH peak (ft MLLW)' }},
                  grid: {{ color: 'rgba(0,0,0,0.06)' }}
                }}
              }}
            }}
          }});
        }}).catch(function(e) {{
          note.textContent = 'No convergence data available yet ('
            + e.message + '). Will populate after a few workflow runs.';
        }});
      }})();
    </script>
  </section>

  <footer>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a></p>
    <p style="font-size:11px;color:#888">Per-tide page generated by the
       daily/hourly workflow. Snapshot of one forecast event; the full
       picture lives on the <a href="../../">home page</a>.</p>
  </footer>
</main>
</body>
</html>
"""


def render_html_page(forecast):
    """
    Standalone HTML page for GitHub Pages publication.
    Like the email HTML but with proper <head>, mobile meta, and footer
    links to source repo + archive.

    The heat-map is rendered CLIENT-SIDE (HANDOFF 9b.10) from the
    static map_points.csv data and the current water level — no
    pre-rendered PNG needed.
    """
    d = forecast["depths_in"]
    regime = d["regime"]
    # Headline resolves the "NO FLOODING" vs "RAIN FLOOD RISK"
    # contradiction (2026-07-07): rain risk takes the banner when the
    # tide-derived regime is dry.
    # 72-h strip + subject legitimately own tomorrow's risk — the
    # today-gate applies only to the TODAY box (2026-07-20: the strip
    # read "NO FLOODING ... rain risk begins tomorrow", contradicting
    # itself; window scope resolves it to "POSSIBLE RAIN FLOODING —
    # no tidal flooding expected, but ... begins TOMORROW").
    headline_text, headline_class = headline_for(forecast, regime,
                                                 scope="window")
    # TODAY-first banner (user 2026-07-09, matching the widget's
    # 2026-07-06 redesign): today's regime + rain risk is the top
    # banner; the worst-72h tide becomes a labeled secondary strip.
    _today_regime = forecast.get("today_regime") or regime
    today_headline, today_class = headline_for(forecast, _today_regime)
    _t_rel = forecast.get("today_rel_grate_sw_in")
    _t_time = forecast.get("today_peak_time") or ""
    today_summary = ""
    if _t_rel is not None:
        today_summary = (f"Tide peak today {_t_rel:+.1f}&Prime; vs SW grate"
                         + (f" at {_t_time[-5:]}" if _t_time else "") + ".")
    _lb = forecast.get("today_lookback")
    lookback_html = ""
    if _lb and (_lb.get("rel_grate_in") or 0) > 0:
        _lb_reg = regime_display(_lb.get("regime") or "").upper()
        lookback_html = (
            f'\n    <div class="regime-summary" style="margin-top:6px;'
            f'border-top:1px solid rgba(0,0,0,0.12);padding-top:6px">'
            f'<b>SO FAR TODAY:</b> {_lb_reg} — peak water '
            f'{_lb["rel_grate_in"]:+.1f}&Prime; vs SW grate at '
            f'{_lb["time_local"]}, {_lb["source"]}.</div>')
    _pr_b = forecast.get("pluvial_risk") or {}
    rain_later_note = ""
    if _pr_b.get("level"):
        _alerts_b = _pr_b.get("nws_flood_alerts") or []
        _alert_names = ", ".join(
            _html_escape(str(a.get("event", ""))) for a in _alerts_b
        )
        _pot_txt = ""
        if _pr_b.get("potential_low_tide_navd88"):
            _pot_txt = (f"; a burst could bring street water to "
                        f"~{(_pr_b['potential_low_tide_navd88'] - 3.52) * 12:+.0f}&Prime; "
                        f"vs SW grate regardless of tide")
        if _pr_b.get("risk_today") is False:
            # risk belongs to TOMORROW — say so in the 72-h strip,
            # keep the TODAY box about today (2026-07-20 scope fix)
            _on = ""
            for _a in _alerts_b:
                if _a.get("onset"):
                    _on = _a["onset"][11:16]
                    break
            try:
                _tmrw_wd = (_station_local_now()
                            + dt.timedelta(days=1)).strftime("%a")
            except Exception:
                _tmrw_wd = ""
            rain_later_note = (
                f" <b>Rain risk begins TOMORROW"
                + (f" ({_tmrw_wd})" if _tmrw_wd else "") + "</b>"
                + (f" ({_alert_names}" + (f" from {_on}" if _on else "")
                   + ")" if _alert_names else "")
                + _pot_txt + ".")
        else:
            today_summary += (
                " Rain risk is live today"
                + (" — " + _alert_names + " in effect" if _alert_names else "")
                + _pot_txt + ".")
    if headline_class == regime:
        headline_summary = f"{REGIME_GLOSSARY.get(regime, '')}."
    else:
        headline_summary = ("No tidal flooding expected, but heavy "
                            "rain could flood the intersection "
                            "independently of the tide — see the "
                            "rain-risk banner below.")
    headline_summary += rain_later_note
    try:
        _now_k = _station_local_now()
    except Exception:
        _now_k = _station_local_now()
    _kick_today = _now_k.strftime("%a %b ") + str(_now_k.day)
    _kick_end = (_now_k + dt.timedelta(hours=72)).strftime("%a")
    peak_t = forecast["peak_time_local"]
    peak_ft = forecast["peak_forecast_observed_mllw"]
    today = _station_local_today().isoformat()
    cold = forecast["cold_lockout"]
    all_tides = forecast.get("all_tides", [])

    # Heat-map section: client-side render (HANDOFF 9b.10) + interactive
    # depth slider (Batch 2 idea #1 follow-up, 2026-05-19).
    map_section = _client_map_section_html(
        forecast,
        container_class="heatmap",
        level=2,
        base_map_url="icons/map_raw.png",
        show_depth_slider=True,
    )

    # Build the all-tides table rows (new column layout). Each row carries:
    #  - regime class for severity-colored backgrounds (HANDOFF 9b.2)
    #  - worst-tide class on the headlined row
    #  - link to per-tide deep page (docs/tides/<slug>/) — HANDOFF 9b.2
    #  - data-hours-from-now attribute for the JS duration toggle
    #    (HANDOFF 9b.2 part 2)
    tide_rows = ""
    for t in all_tides:
        td = t["depths_in"]
        is_worst = (t["time"] == peak_t)
        hfn_row = t.get("hours_from_now")
        is_past = hfn_row is not None and hfn_row < 0
        regime_class = f"regime-{td['regime']}"
        classes = ["tide-row", regime_class]
        if is_worst:
            classes.append("worst-tide")
        if is_past:
            classes.append("past-tide")
        row_class = f' class="{" ".join(classes)}"'
        hours = t.get("hours_from_now")
        data_attr = f' data-hours-from-now="{hours:.2f}"' if hours is not None else ""
        short, above_in, rel_in = landmark_summary(td, t["forecast_peak_mllw"])
        slug = _tide_slug(t["time"])
        time_cell = (
            f'<a href="tides/{slug}/">{format_time_full(t["time"])}</a>'
            if slug else format_time_full(t["time"])
        )
        if is_past:
            conf_cell = '<td class="note">—</td>'
        else:
            _cl, _ct = _tide_confidence(forecast, t)
            _ct_attr = _ct.replace('&', '&amp;').replace('"', '&quot;') \
                          .replace('<', '&lt;')
            conf_cell = (
                f'<td><button type="button" class="conf-badge '
                f'conf-{_cl}" data-conf="{_ct_attr}">'
                f'{_cl.upper()}</button></td>')
        tide_rows += (
            f'<tr{row_class}{data_attr}>'
            f'<td>{time_cell}</td>'
            f'<td>{t["predicted_mllw"]:.2f}</td>'
            f'<td>{t["surge_ft"]:+.2f}</td>'
            f'<td><b>{t["forecast_peak_mllw"]:.2f}</b></td>'
            f'<td>{short}</td>'
            f'<td>{above_in:+.1f}&Prime;</td>'
            f'<td>{rel_in:+.1f}&Prime;</td>'
            f'<td>{regime_display(td["regime"])}</td>'
            f'{conf_cell}'
            f'</tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Bay Ave Barnacle — {today}</title>
<link rel="stylesheet" href="style.css">
<!-- PWA / iOS home-screen install (HANDOFF item 27, Stage 1) -->
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="icons/icon-512.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Barnacle">
<meta name="theme-color" content="#0f4064">
<meta name="description" content="Bay Ave Barnacle — {headline_text}. Worst-case tide peak {peak_ft:.2f} ft MLLW at {format_time_full(peak_t)}. Hyperlocal flood forecast for the Bay Ave &amp; Central Ave intersection, Highlands NJ (referenced to 342 Bay Ave).">
<!-- Open Graph (link previews) — W -->
<meta property="og:title" content="Bay Ave Barnacle — {headline_text}">
<meta property="og:description" content="Worst-case peak {peak_ft:.2f} ft MLLW at {format_time_full(peak_t)}. Hyperlocal flood forecast for the Bay Ave &amp; Central Ave intersection, Highlands NJ (referenced to 342 Bay Ave).">
<meta property="og:image" content="https://johnurban.github.io/barnacle/icons/icon-512.png">
<meta property="og:url" content="https://johnurban.github.io/barnacle/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
</head>
<body>
<main>
  <header>
    <h1>Bay Ave Barnacle</h1>
    <p class="subtitle">Hyperlocal flood forecast for the intersection of Bay Ave &amp; Central Ave in Highlands NJ &mdash; water levels referenced to 342 Bay Ave</p>
    <p class="subtitle">For general street predictions across Highlands, Atlantic Highlands, Leonardo, and Sea Bright, see our <a href="highlands.html">new barnacle street map</a>.</p>
    <p class="last-updated"
       data-generated-at="{forecast.get('generated_utc', '')}">
      <span id="last-updated-display">Last updated …</span>
    </p>
  </header>
  {_render_input_health_html(forecast)}
  <!-- DD: workflow-health banner. Hidden by default; revealed by the
       script below when last-update age exceeds the stale threshold.
       Three tiers: <90 min fresh (no banner), 90 min - 3 h amber on
       the inline last-updated indicator only (V), >3 h red banner (DD),
       >24 h bright-red banner with a "Run workflow manually" note. -->
  <div class="health-alert" id="health-alert" style="display:none">
    <span class="health-alert-title">⚠ System update is delayed</span>
    <span class="health-alert-detail" id="health-alert-detail"></span>
  </div>
  <script>
    (function() {{
      var el = document.querySelector('.last-updated');
      var disp = document.getElementById('last-updated-display');
      var banner = document.getElementById('health-alert');
      var bDetail = document.getElementById('health-alert-detail');
      if (!el || !disp) return;
      var iso = el.getAttribute('data-generated-at');
      var gen = new Date(iso);
      if (isNaN(gen.getTime())) return;
      function update() {{
        var now = new Date();
        var diffSec = Math.max(0, Math.round((now - gen) / 1000));
        var ago;
        if (diffSec < 90) ago = diffSec + ' s ago';
        else if (diffSec < 3600) ago = Math.round(diffSec / 60) + ' min ago';
        else if (diffSec < 86400) ago = Math.round(diffSec / 3600) + ' h ago';
        else ago = Math.round(diffSec / 86400) + ' d ago';
        var local = gen.toLocaleString(undefined, {{
          month: 'numeric', day: 'numeric',
          hour: 'numeric', minute: '2-digit'
        }});
        disp.textContent = 'Last updated ' + local + ' (' + ago + ')';
        // V: amber inline indicator at >2h
        if (diffSec > 7200) disp.classList.add('stale');
        else disp.classList.remove('stale');
        // DD: prominent banner at >3h, severe variant at >24h
        if (banner && bDetail) {{
          if (diffSec > 86400) {{
            banner.style.display = 'block';
            banner.classList.add('severe');
            bDetail.innerHTML = 'Last workflow run was <b>' + ago +
              '</b> (' + local + '). The hourly cron may have stalled. ' +
              '<a href="https://github.com/JohnUrban/barnacle/actions" target="_blank">' +
              'Run the workflow manually</a> to refresh.';
          }} else if (diffSec > 10800) {{
            banner.style.display = 'block';
            banner.classList.remove('severe');
            bDetail.innerHTML = 'Last workflow run was <b>' + ago +
              '</b> (' + local + '). Expected hourly; if this persists, ' +
              'the cron may have stalled.';
          }} else {{
            banner.style.display = 'none';
          }}
        }}
      }}
      update();
      setInterval(update, 30000);  // refresh "X ago" every 30s while open
    }})();
  </script>

  <div id="nowcast-strip" style="display:none"></div>
  <script>
    // LIVE RADAR NOWCAST strip (2026-07-17): renders docs/nowcast.json
    // client-side; a best-effort Action requests 10-min refreshes during
    // rain-capable weather. Hidden when inactive or >20 min stale;
    // freshness is keyed to the MRMS SOURCE frame, not workflow write time.
    (function() {{
      var bust = Math.floor(Date.now() / 120000);
      fetch('nowcast.json?t=' + bust).then(function(r) {{
        return r.json();
      }}).then(function(nc) {{
        if (!nc || !nc.active || !nc.source_latest_utc ||
            nc.radar_quality !== 'ok') return;
        var age = (Date.now() - Date.parse(nc.source_latest_utc)) / 60000;
        if (age > 20) return;
        var el = document.getElementById('nowcast-strip');
        // WORST TRUTH WINS (event #7): headline = server-computed
        // regime_display (projected class while rising, drain-clock
        // class while falling), never the lagging instant alone.
        var reg = nc.regime_display ||
                  ((nc.regime_now === 'dry') ? 'street water'
                   : nc.regime_now).toUpperCase();
        el.innerHTML =
          '<section class="regime regime-severe" style="border:2px solid #b91c1c">' +
          '<div class="regime-kicker">&#128225; LIVE RADAR NOWCAST &middot; BEST EFFORT ' +
          '(as of ' + Math.round(age) + ' min ago)</div>' +
          '<div class="regime-label">' + reg + '</div>' +
          '<div class="regime-summary">Rain on the hillside now: ' +
          nc.recent_max_in_hr.toFixed(1) + ' in/hr (radar). Street ' +
          'water ≈ ' + (nc.street_now_in >= 0 ? '+' : '') +
          nc.street_now_in.toFixed(1) + '″ vs SW grate; ' +
          'projected peak ' + (nc.peak_proj_in >= 0 ? '+' : '') +
          nc.peak_proj_in.toFixed(1) + '″ around ' +
          nc.peak_proj_utc + ' UTC. Tank model on OBSERVED radar, ' +
          'not forecast; 45-min projection holds the latest observed ' +
          'rain rate.</div></section>';
        el.style.display = 'block';
        // HEADLINE OVERRIDE (2026-07-18, user during a live flood:
        // "the app should be actively saying FLOODING at the top").
        // When observed-radar street water is real, the TODAY label
        // becomes the live truth, not the QPF outlook.
        var live_eff = Math.max(nc.street_now_in || 0,
          (nc.trend === 'rising' ? (nc.peak_proj_in || 0) : 0));
        if (live_eff >= 1) {{
          // Target the TODAY block explicitly — the first '.regime'
          // in the DOM is this strip itself (bug caught by the user
          // MID-FLOOD: strip said FLOODING NOW while TODAY still
          // said the QPF outlook, "light", under crazy flooding).
          var tb = document.getElementById('today-block');
          if (tb) {{
            var lbl = tb.querySelector('.regime-label');
            var kick = tb.querySelector('.regime-kicker');
            var summ = tb.querySelector('.regime-summary');
            if (lbl) lbl.textContent = '\u26A0 FLOODING NOW \u2014 ' +
              reg.toUpperCase() + ' (+' +
              nc.street_now_in.toFixed(1) + '\u2033 and live)';
            if (kick) kick.textContent =
              'TODAY \u2014 HAPPENING NOW (live radar; QPF outlook superseded)';
            // keep the day-card layout classes — this block is a
            // grid cell now, not the old standalone TODAY box
            tb.className = 'regime regime-severe day-card day-card-today';
          }}
        }}
      }}).catch(function() {{}});
    }})();
  </script>

{_render_water_series_section(forecast)}

{_render_day_cards_html(forecast)}

  {_render_more_details_html(forecast)}

{map_section}

  {_render_summary_html(forecast, include_confidence=False,
                        include_unusual=False)}

{_render_flood_windows_html(forecast)}

  <section class="tides">
    <h2>Upcoming high tides</h2>
    <div class="duration-toggle">
      Show:
      <label><input type="radio" name="duration" value="24"> 24h</label>
      <label><input type="radio" name="duration" value="48"> 48h</label>
      <label><input type="radio" name="duration" value="72" checked> 72h</label>
    </div>
    <table class="tide-table">
      <thead><tr><th>Time</th><th>Pred (ft)</th><th>Surge</th><th>Peak (ft)</th><th>Highest landmark</th><th>Above</th><th>Rel</th><th>Regime</th><th>Conf</th></tr></thead>
      <tbody>{tide_rows}</tbody>
    </table>
    <div id="conf-pop"></div>
    <details class="chart-explain">
    <summary>Explain this table</summary>
    <p class="note">Highlighted row is the worst tide of the 72 h (the
       one flagged &#9650; WORST OF 72 H in the day cards).
       <b>Click any time in the first column</b> to open that tide's detail
       page (per-tide heat-map, prediction-evolution replay, convergence
       chart, full landmark table). <b>Above</b> = inches above the highest
       exceeded landmark (negative if water below the lowest landmark).
       <b>Rel</b> = inches above the lowest landmark (lowest road corner,
       3.64 NAVD88) — always. <b>Conf</b> = per-tide confidence — click a
       value to see what drives it and the &plusmn; band it implies.
       Surge persistence is increasingly unreliable
       for tides beyond ~24h out — use the longer windows for planning,
       not for trust. The most recent high tide stays visible (greyed
       out, marked "past") for {PAST_TIDE_VISIBILITY_HOURS} h after its
       peak so you can check whether it flooded before you head home.
       Detail pages live under <code>tides/&lt;date&gt;T&lt;HH-MM&gt;/</code>
       — each has a tide-specific heat-map, a slider that replays the
       prediction history (drag through past predictions, watch the
       heat-map redraw), and a convergence chart showing how that
       tide's peak forecast evolved.</p>
    </details>
    <script>
      (function() {{
        var radios = document.querySelectorAll('input[name="duration"]');
        function applyFilter(hours) {{
          var rows = document.querySelectorAll('.tide-table tbody tr.tide-row');
          rows.forEach(function(tr) {{
            var h = parseFloat(tr.getAttribute('data-hours-from-now'));
            tr.style.display = (isNaN(h) || h <= hours) ? '' : 'none';
          }});
        }}
        radios.forEach(function(r) {{
          r.addEventListener('change', function() {{
            applyFilter(parseFloat(r.value));
          }});
        }});
        // Apply the default (72) on load
        applyFilter(72);
        // Confidence popup (2026-07-21): click a badge -> bubble with
        // the per-tide reasoning, positioned under that row; any
        // further click (bubble included) dismisses it.
        var pop = document.getElementById('conf-pop');
        document.querySelectorAll('.conf-badge').forEach(function(b) {{
          b.addEventListener('click', function(ev) {{
            ev.stopPropagation();
            pop.textContent = b.getAttribute('data-conf');
            pop.style.display = 'block';
            var sec = pop.offsetParent || pop.parentElement;
            var br = b.getBoundingClientRect();
            var sr = sec.getBoundingClientRect();
            pop.style.top = (br.bottom - sr.top + 6) + 'px';
          }});
        }});
        document.addEventListener('click', function() {{
          pop.style.display = 'none';
        }});
      }})();
    </script>
  </section>

  <section class="forecast">
    <h2>Details on highest tide in the next 72 hours
      <a class="detail-link" href="tides/{_tide_slug(peak_t)}/">View this tide's full detail page →</a>
    </h2>
    <dl>
      <dt>High tide time</dt><dd>{peak_t}</dd>
      <dt>Predicted tide</dt><dd>{forecast['peak_predicted_mllw']:.2f} ft MLLW (Sandy Hook)</dd>
      <dt>Surge</dt><dd>{forecast['current_surge_ft']:+.2f} ft</dd>
      <dt>Forecast peak</dt><dd>{peak_ft:.2f} ft MLLW</dd>
      <dt>Surge source</dt><dd>{forecast['surge_source']} <span class="note">({forecast['nws_status']})</span></dd>
      <dt>Peak rainfall</dt><dd>{_fmt_metric(forecast.get('peak_rain_rate_in_hr'))} in/hr</dd>
      <dt>72h mean temp</dt><dd>{_fmt_metric(forecast.get('temp_avg_72h_f'), '.1f')}&deg;F</dd>
      <dt>Cold conditions</dt><dd>{'<b>YES</b> — ice-lock hypothesis met; <i>no longer actively applied</i> (see <a href="https://github.com/JohnUrban/barnacle/blob/main/history/reports/cold_weather_retrospective.md">retrospective</a>)' if cold else 'no'}</dd>
    </dl>
{_render_wind_adjustment_html(forecast)}
  </section>
{_render_pluvial_advisory_html(forecast)}
{_render_cold_advisory_html(forecast)}

<section class="peaks-toggle-wrap">
    <div class="heatmap-toggle" id="peaks-view-toggle">
      <span class="note">Peaks view:</span>
      <label><input type="radio" name="peaks-view" value="all" checked>
        rain + tide (all pathways)</label>
      <label><input type="radio" name="peaks-view" value="tide">
        tide-only (per-tide, gauge)</label>
    </div>
    <div id="peaks-all">
{_render_flood_peaks_section(forecast)}
    </div>
    <div id="peaks-tide" style="display:none">
{_render_oscillation_section(forecast)}
    </div>
    <script>
      (function() {{
        var radios = document.querySelectorAll('input[name="peaks-view"]');
        var v = 'all';
        try {{ v = localStorage.getItem('barnacle-peaks-view') || 'all'; }} catch (e) {{}}
        function apply() {{
          document.getElementById('peaks-all').style.display =
            (v === 'all') ? 'block' : 'none';
          document.getElementById('peaks-tide').style.display =
            (v === 'tide') ? 'block' : 'none';
          // hidden Chart.js canvases render zero-size; nudge on reveal
          window.dispatchEvent(new Event('resize'));
        }}
        radios.forEach(function(r) {{
          r.checked = (r.value === v);
          r.addEventListener('change', function() {{
            v = r.value;
            try {{ localStorage.setItem('barnacle-peaks-view', v); }} catch (e) {{}}
            apply();
          }});
        }});
        apply();
      }})();
    </script>
  </section>
  {_render_rain_timing_html(forecast)}

  {_landmarks_section_html(forecast, wrapper='section', include_spot_check=False)}

{_render_live_gauge_section(forecast)}

  {_render_recent_history_html(forecast)}


  {_render_low_tides_html(forecast)}

  {_render_lookahead_html(forecast)}

{_render_more_info_links_html()}


  <footer>
    <p>Model {CURRENT_MODEL_VERSION} (pluvial: dynamic tank hydrograph —
       timing calibrated on two full measured hydrographs; scenarios = tank
       steady-state / tanh bracket; stage-storage fill,
       head-dependent drainage). Local enhancement
       {LOCAL_ENHANCEMENT_FT:+.2f} ft.
       Updated hourly (best-effort) via GitHub Actions.</p>
    <p><a href="https://github.com/JohnUrban/barnacle">Source code &amp; model</a> &middot;
       <a href="archive/">Past daily archives</a> &middot;
       <a href="tides/">Per-tide archive</a> &middot;
       <a href="barnacle-widget.js">iOS widget script (Scriptable)</a></p>
  </footer>
</main>
</body>
</html>
"""
