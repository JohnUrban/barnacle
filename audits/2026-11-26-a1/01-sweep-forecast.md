<!-- audits/2026-11-26-a1 supporting file for 01-full-audit-claude-fable-5-2.md -->
> **Sweep report: forecast science and internal consistency (finding IDs FC-n).** Written 2026-11-26 by a read-only
> subagent of the lead auditor's session (Claude Fable 5.2), filed unedited except
> that scratch paths were rewritten to `audits/2026-11-26-a1/01-probes/forecast/` (scripts only; large
> data dumps were not committed) and, in the records sweep, one line of personal
> context was redacted. It is evidence for report 01, not an independent review:
> the lead re-checked only the items listed in report 01's verification table.

# Forecast science and internal consistency — auditor report (slice: hourly forecast)

Read-only audit; nothing in the repo was changed (`git status` still shows only `?? del`). Scratch work is in `audits/2026-11-26-a1/01-probes/forecast/` (`dump.py`, `fc_<commit>.json`, `index_<commit>.html`, `tests.out`).

Abbreviations: repo root = `<repo>`; **FFD** = `forecast/flood_forecast_daily.py`; **REND** = `forecast/rendering.py`; **WID** = `docs/barnacle-widget.js`. "Table" = `all_tides[].forecast_peak_mllw`; "curve" = `water_series`. Clock when written: 2026-11-26 about 22:50 EST.

The answer to K3 is FC-1: a bad gauge reading, not rain and not a formula bug.

## Findings (ranked)

### FC-1 — K3 solved: garbage gauge readings at the tail of the series became a +7.22 ft "fresh" surge
**Severity: critical.** For one hour the page showed water at porch-deck level tonight; the same path feeds alerts whenever no NWS product is active.

**Evidence**
- Commit `7386bc773` (generated 2026-11-26T19:06:47Z): `water_series_input.decay.surge_obs_ft = 7.219`, reading time 19:00Z, rung `fresh`, status `ok`, `degraded_inputs = []`.
- The gauge tail published in that run, against the same stamps in the next run (`fc515b6a2`):

| Stamp (EST) | 19:06Z run | 20:07Z run |
|---|---|---|
| 13:12 | 6.22 | 4.142 |
| 13:36 | 6.318 | 3.848 |
| 13:42 | 6.006 | 3.763 |
| 14:00 | 7.302 | 3.584 |

- Astronomy at 14:00 was about 0.08 ft, hence 7.302 − 0.08 = +7.22. The neighbouring runs had surge 3.07 and 3.78.
- **Mechanism.** `fetch_current_surge` uses the single last despiked reading (FFD:731, 797). `_despike_gauge` (FFD:984–1019) compares each point with the median of ±10 raw neighbours. The newest point has only past neighbours, so a garbage run of 6 or more samples (36 min) at the tail passes.
- **Missing guards.** `surge_decay._valid` accepts −10 to 20 ft (`forecast/surge_decay.py:94–100`). Nothing compares the reading with the previous state (+3.09 at 17:54Z, a 4.1 ft jump in 66 min), with NWPS, or with the product. The gate requires only a finite surge (`forecast/check_artifacts.py:409–415`).
- **What it produced**
  - `today_peak_water_navd88 = 8.049` (the 21:00 point; porch deck is 8.08) and `today_rel_grate_sw_in = 54.3`.
  - `day_worst` for 11-27 at 7.53 NAVD88.
  - A flooding-windows table on `docs/index.html` listing "SW grate ~08:00 → 02:31, 18.5 h, +83.9″ at 08:30" and "Bottom of porch steps … +40.4″ at 21:00".
  - `data/surge_state.json` saved `surge_ft 7.219`. The stale-state rung could have served it for up to 168 h had the gauge then gone silent.
  - Append-only ledgers took the value: `data/predictions_log.csv` row 24373 (11-29 11:25 tide, 6.865, "street") and `data/outlook_log.csv` rows at 19:06:47Z (`persist_flat 11.990`, `persist_decay 10.800` for the 21:07 tide).
- **Alerts.** None was sent because of it: `alert_state.json` at that commit still has `last_sent_ts 2026-11-26T16:09:13Z`. That was only because product rows covered every tide inside 48 h. With no product the table would have read 10.80 / 10.36 / 7.99 / 8.13 ft, all severe (computed with `surge_decay.choose_anchor`).
- This is a recurrence of the BACKLOG open loop `gauge-ingest-no-battery-check` (2026-09-27, BACKLOG.md:910), now in the hourly surge anchor.

**How verified:** REPRODUCED the filter weakness (synthetic: a clean series with the last 6 points +3 ft keeps the last point; with 5 it is rejected; a single end spike is rejected). READ the code. Published values are VERIFIED from the two commits. The exact raw values are INFERRED: the feed is not archived, and the published points alone would not have let 7.302 through, so the dropped stamps (13:00, 13:06, 13:24, 13:30, 13:48, 13:54) must have been high garbage too.

**Confidence:** high on cause and consequences; medium on the exact raw input.

**Fix direction:** make the anchor robust at the tail (median of the last few readings plus a rate-of-change check against the saved state or NWPS); mark the input degraded and fall to the stale rung when the check fails; never save an unvetted reading to `surge_state.json`.

### FC-2 — K1 map: three estimates of the same tide, wired to different consumers
**Severity: high.** One page says "SEVERE" and "street water" for the same tide; alerts follow only one of the numbers.

**Which field reads which**

| Source | Fields and consumers | Lines |
|---|---|---|
| **Table** (product row within 2 h, else decay) | built | FFD:2300–2327 |
| | headline fields `peak_forecast_observed_mllw`, `depths_in`, `surge_source`, `current_surge_ft` | FFD:2785–2795 |
| | `plain_language_summary` | FFD:3648–3712 |
| | `day_outlook` → widget "Tidal flood:" line | FFD:2689–2714; WID:734–756 |
| | alert level and alert text (ntfy/email) | FFD:4878–4886, 5557–5588 |
| | `predictions_log` and all scoring | FFD:1218–1268 |
| | day-card tide rows; email tables; per-tide pages | REND:257–274; 1368, 1491; 2717 |
| | map title / initial water level | FFD:8464–8495 |
| **Curve** (observed-surge decay, 30 h) | built | FFD:622–624, 2607 |
| | `flood_windows` | FFD:2662 |
| | `today_peak_water_navd88`, `today_regime`, `today_highest_crossed`, `today_rel_grate_sw_in` | FFD:2718–2730 |
| | widget colour and headline, window line, peak line, chart | WID:555, 239–252, 713–717, 594/803 |
| | landing chart; map slider for the first 30 h | FFD:6103; 8414–8419 |
| **Both** | `day_worst` = max rank of table tides and curve; ties go to the curve because the tide candidate's level is `None` → day-card badge, ribbon, email "WORST 72H" | FFD:4835–4857; REND:309–324, 81–93 |
| **Third** (`outlook_7d.series`: NWPS + advisory correction) | 7-day page; map slider after 30 h | `forecast/outlook.py:508–564`; FFD:8424–8431 |

**Live example** (`d03ab3191`, 02:11Z), tide 2026-11-27 09:23:
- Table 6.9 ft MLLW ("street").
- Curve 6.321 NAVD88 = 9.14 MLLW ("severe"; `flood_windows.curb` 06:31–11:55, +25.9″).
- Outlook series 4.08 NAVD88.
- Published `docs/index.html`: TOMORROW card "SEVERE | ★ Fri 9:23 AM tide — street (+6.7″)".
- Map title "Predicted water level — 4.08 ft NAVD88 (SH 6.90 ft MLLW @ Fri 9:23 AM)"; the same map's slider point `{"t":"2026-11-27 09:30","w":6.321}`.
- Email-subject logic gives "WORST 72H SEVERE: tide peak 6.90 ft at Fri 9:23 AM (NW corner +2.0″)".
- The alert level sees only "street".

**Map seam at +30 h** (curve to outlook), same hour, three runs: +1.46 ft (18:09Z), +3.28 ft (19:06Z), +2.24 ft (02:11Z).

Three "today peak" numbers also sit in one JSON: `today_peak_water_navd88` 6.337 (it includes a point up to 30 min in the past, FFD:2130), `day_worst[0]` 6.249 (strictly future), and the lookback model claim 6.453.

**How verified:** READ in code; values VERIFIED in committed `forecast.json` and `index.html`; subject REPRODUCED with `headline_for`, `worst_72h_headline` and `landmark_summary` on the saved JSON.

**Confidence:** high.

**Fix direction:** owner decision on one reconciled per-tide value. Until then every surface should label which estimate it shows, and alerts and headlines should read the same one.

### FC-3 — Product rows are never checked against the live gauge
**Severity: high.** The per-tide number and alert text stayed 0.4–1.0 ft below water that had already been observed.

**Evidence**
- Product rows override unconditionally (FFD:2300–2310).
- Runs 23:07Z and 00:20Z published 8.2 ft for the 21:07 tide. The gauge reached 8.25 by 19:30 EST (series `observed_navd88` 5.433) and the page kept 8.2 until the 01:08Z run.
- Runs 01:08Z to 02:11Z published 8.8. The gauge read 8.975 at 20:30 and 9.211 at 20:54. The 02:11Z page row "Thu 9:07 PM tide — severe (+29.5″) (past)" is 4.3 in below the same file's curve peak (+33.8″).
- Final 6 h before the evening tide, as issued, mean error: product −0.81, NWPS −0.54, constant surge −0.28, decay −0.52 ft (`data/outlook_log.csv`, observed 9.211 preliminary).

**How verified:** VERIFIED from commits `66893eb89`, `6d4c6440c`, `2ff6da084`, `d03ab3191` and `outlook_log.csv`; READ in code.

**Confidence:** high.

**Fix direction:** floor a tide's value at the water already observed in its window, and flag a product row the gauge has overtaken.

### FC-4 — K2 quantified as issued; the decay rule also holds a departing surge up
**Severity: high.** The chart, widget colour and flood windows under-called both floods at half-day lead by 1.5–3.3 ft and may over-call the morning after.

**Evidence** — mean error by lead for the two 2026-11-26 tides (`data/outlook_log.csv`: `nws_product_mllw`, `persist_flat_mllw`, `persist_decay_mllw`):

| Tide (observed) | Lead | Product | Constant | Decay |
|---|---|---|---|---|
| 08:28 (8.267) | 0–6 h | +0.03 | −0.78 | −0.83 |
| | 6–12 h | +0.03 | −0.87 | −1.02 |
| | 12–24 h | +0.03 | −1.41 | −1.47 |
| 21:07 (9.211, preliminary) | 0–6 h | −0.81 | −0.28 | −0.52 |
| | 6–12 h | −0.68 | −0.61 | −1.27 |
| | 12–24 h | −0.98 | −3.04 | −3.34 |

- The 6–12 h evening row includes the FC-1 spike run.
- The decay costs 0.05–0.5 ft beyond constant persistence; surge growth costs the rest.
- Mirror image: from the 21:06 reading (+4.34) the curve holds +3.26 ft at 09:23 tomorrow, where the product and NWPS say +1.0.

**How verified:** REPRODUCED from the ledger (script output in the scratch directory).

**Confidence:** high on the numbers. The over-call tomorrow is an open prediction, not yet a measured error.

**Fix direction:** the as-issued comparison of decay, constant and guidance already queued (plan item 3). The ledger columns exist to run it now.

### FC-5 — Product boundary and product loss flip the table by feet
**Severity: medium to high.** Phantom street calls at the edge of the product; a false "severe" in the table and alert level if the advisory lapses or the alerts API fails for one run.

**Evidence**
- Beyond the product's last row the table jumps from the product's departure to the decayed observed surge. At 18:09Z the last product row (11-28 23:10) had +0.3 ft and the next tide (11-29 11:25) had +0.95 ft. At 20:07Z that tide was 6.38 "street" ("brief water at the sw grate" in the summary) while the outlook said 5.5 (NWPS, dry). Once the product reached it, it read 5.8, dry.
- If the product had been absent at 02:11Z (alert expired, or `get_surge_forecast` raising, FFD:2225–2230): 6.9 street → 9.15 severe; 5.0 dry → 7.14 light; 5.5 dry → 7.53 moderate. The alert signature would change, which is a "new event" send (FFD:5022–5024).

**How verified:** values VERIFIED in commits; the flip COMPUTED with `surge_decay.choose_anchor` on the published reading (the same code reproduces the logged 6.865); the alert consequence READ, not run end to end.

**Confidence:** high for the table; medium for the alert outcome (quiet hours and the stuck `last_sent_rank` interact).

**Fix direction:** carry the last product or NWPS departure across the boundary with a labelled fade; treat a fetch failure differently from "not active".

### FC-6 — Scoring loop: the published sentences score the table, and half of it is the NWS product
**Severity: medium.** Published accuracy overstates the skill of what drives the chart and headline in storms.

**Evidence**
- `accuracy_by_lead` reproduces exactly from `predictions_log.csv` + `observed_peaks_cache.csv`: MAE 0.110 / 0.138 / 0.156 / 0.239 / 0.320 / 0.373, 27 tides (FFD:3302–3403).
- 13 of those 27 tides have product-sourced rows.
- On those rows: table MAE 0.13 / 0.12 / 0.13 / 0.15 / 0.14 ft; the curve's rule (`persist_decay_mllw`) MAE 0.22 / 0.29 / 0.33 / 0.46 / 0.65 ft, bias −0.19 to −0.40.
- The curve is never scored.
- `accuracy_summary` ("last 30 as-run forecasts", REND:739–772) also reproduces (+0.018, 0.220, 0.939). It scores the 72-h worst tide from one archive a day, so the 30 rows hold 24 distinct tides (5 double-counted) and mix leads of 0–72 h (FFD:1117–1163).
- Observed peaks are cached on first fetch and never refreshed (FFD:3248–3250). NOAA revised preliminary values by up to 3.7 ft the same day (FC-1).
- The scorer guard of 2026-11-10 works: the 11-26 08:28 rows were scored at 8.267 @ 08:54.

**How verified:** REPRODUCED.

**Confidence:** high.

**Fix direction:** report by source, score the curve at tide times, and refresh cached peaks once verified data exist.

### FC-7 — The past six hours of the curve are a back-cast with the current surge
**Severity: medium.** The page lists past flood windows that did not happen at those depths; the widget's window line can show the past episode.

**Evidence**
- `SurgeAnchor.at` returns the current reading for all earlier hours (`forecast/surge_decay.py:63–64`).
- `compute_flood_windows` runs on the whole series (FFD:2662, 4555–4639).
- The table "Flooding windows (coming 30 h)" prints every episode, with no dates (REND:1617–1639).
- 18:09Z page: "SW grate ~07:00 → 13:00, +34.3″ at 08:30". The observed bay peak was 8.267 ft = +23.1″. "07:00" is only the series start.
- The widget takes `fw[hc.key][0]` (WID:246). For the five runs 16:09Z to 20:07Z that episode was the morning one (for example 20:07Z: porch base 09:00–11:12) under a headline about 21:00.
- The observed overlay showed the garbage 14:00 reading as `observed_navd88` 4.482 in the 19:06Z run.

**How verified:** VERIFIED in the published index.html and JSON; the widget rendering is INFERRED from code plus JSON (no screenshot).

**Confidence:** high on the data; medium on what the widget drew.

**Fix direction:** compute windows from now forward (the past belongs to the gauge or lookback), and pick the first episode that ends after now.

### FC-8 — Rain tank with the bay at or above 3.52 ft: zero drain, so drizzle makes street water
**Severity: medium.** Light rain over a modestly high tide can turn the widget to STREET or LIGHT.

**Evidence**
- Drain is zero at bay ≥ 3.52 (FFD:4411–4416, 4511–4513).
- Steady state at bay 3.52: 0.01 in/hr → +3.9″ over the SW grate; 0.02 → +4.9″; 0.10 → 4.15 NAVD88; 0.123 → 4.18 (over the 4.16 curb).
- Cliff: at 0.123 in/hr, bay 3.26 gives +0.0″ and bay 3.50 gives +7.7″.
- `PLUVIAL_SERIES_RATE_MIN = 0.25` (FFD:4235) is never referenced. Its comment quotes the owner: "When it is lightly raining, the drains work fine".
- 12 of 184 daily archives show a lift over 0.2 ft above a bay of at least 3.3 ft. Examples: `docs/archive/2026-07-11.json` (bay 3.576 → 3.953, 24-h peak QPF 0.013 in/hr); `2026-08-10.json` (3.562 → 3.96, 0.025 in/hr).
- The nowcast will not run its tank below 0.3 in/hr (FC-9), so the two arms disagree on the same physics.

**How verified:** REPRODUCED (`estimate_pluvial_water`, `simulate_pluvial_series`); archive scan.

**Confidence:** high that the model does this. Whether the street really ponds then is undetermined; it overlaps the open science item "high-base tank".

**Fix direction:** an owner and science decision on a low-rate floor or disconnected-puddle threshold at high base (a model change, class a); delete or wire the dead constant.

### FC-9 — Cause traced: the nowcast publishes no street level for a tidal flood unless radar exceeds 0.3 in/hr
**Severity: medium.** The live rail is blind to tide-only street water. This is plan addendum item 1, whose cause was untraced.

**Evidence**
- `active = recent_max > max(0.3, drain)` (`forecast/nowcast.py:519–520`); `street_now_in` is set only inside `if active:` (532–593).
- Published runs 19:33–20:47 EST: `active False`, bay 5.27–6.29 NAVD88, `recent_max` 0.15–0.27, `street_now None`.
- 20:55 EST: `recent_max 0.32` → `street_now 33.5`.
- Consumers read a missing value as zero: `nc.get(NOWCAST_STREET_NOW_KEY) or 0` (FFD:4899) and `nc.street_now_in || 0` (WID:647). That is charter rule 7 ("unavailable ≠ zero").

**How verified:** VERIFIED from 11 committed `docs/nowcast.json` versions; READ.

**Confidence:** high.

**Fix direction:** publish the bay-driven base stage with a label whenever the bay is above the grate, and carry "no estimate" as null to consumers. Owner decision; the gate caveat applies.

### FC-10 — A surge flood was headlined "SEVERE (RAIN)"
**Severity: medium.** The pathway label misattributes the flood.

**Evidence**
- `path = "rain (tank line)"` when `wmax > tmax + 0.02` (FFD:4849); rank ties go to the curve (FFD:4857).
- Published `docs/index.html` at `7386bc773` and `d03ab3191`: "TODAY · THU NOV 26 | ▲ WORST OF 72 H · rain (tank line) | SEVERE (RAIN)".
- At 02:11Z the day maximum was 6.249 NAVD88 against a tide of 6.200; rain added 0.049 ft (0.6 in of about 33).
- `worst_72h_headline` adds "(RAIN)" on the same test (REND:89–90).

**How verified:** VERIFIED in published pages; READ.

**Confidence:** high.

**Fix direction:** name the pathway by which line sets the regime (or by rain's share), not by a 0.02 ft margin.

### FC-11 — The retired cold-lockout rule still removes the map and blanks the ledger's water level
**Severity: medium; dormant until the first 72-h mean below 32°F.** The landing and per-tide maps would vanish on almost every cold day.

**Evidence**
- `_compute_map_water_level` returns `None` when `cold and peak_mllw < 8.0` (FFD:8484–8488).
- `_client_map_section_html` then returns `""` (FFD:6872–6874); it is used at REND:3219 and 2768.
- `append_predictions_log` writes an empty `water_navd88_predicted` under the same condition (FFD:1239).
- Memory and code comments say the rule is advisory only, with predictions not zeroed.

**How verified:** REPRODUCED in memory (saved 02:11Z forecast, peak 6.9: map section 9,200 chars; with `cold_lockout=True` it is 0 chars).

**Confidence:** high.

**Fix direction:** drop the two `cold and < 8.0` branches.

### FC-12 — The per-tide table adds rain with a v0.6 formula the v0.10.6 spec does not contain
**Severity: medium to low.** Table depths and regimes, and so alert ranks, include a rain term that no current document states, and it has a step in it.

**Evidence**
- `predict_landmark_depths` adds `8·tanh(rate)/12` ft when rate > 0.1 in/hr (FFD:1843–1845): 0.10 → +0″, 0.11 → +0.88″.
- The spec's "Tide-keyed pathway" (`model/v0.10.6.md:413–424`) has no rain term.
- 11 ledger rows (2026-11-24T23:06Z onward; 21:07 tide, 7.600 ft, rain 0.12) carry `regime_predicted = severe` while their `water_navd88_predicted` (4.780) classifies as moderate. The ledger README says the regime can be rebuilt from that column.
- The 11-26 summary "past porch step 1 (~5.5″)" is 4.44″ + 1.09″ from this term.
- This is a third rain model beside the dynamic tank and the steady-state scenarios.

**How verified:** REPRODUCED (function calls; ledger scan).

**Confidence:** high.

**Fix direction:** state it in the spec or replace it with the tank at the tide's level; log the rain-inclusive water level.

### FC-13 — Two threshold schemes for the same class words
**Severity: low to medium.** The widget's LIVE class can be one step lower than `nowcast.json` and the alert for the same inches.

**Evidence**
- Python: light above the curb, moderate at curb + 4″, severe at curb + 8″ — that is +7.7 / +11.7 / +15.7″ over the SW grate (FFD:191–193, 1853–1865, 6002–6016).
- Widget live headline: 7.7 / 13.7 / 22.7 (WID:649–652).
- "Severe" begins at 7.65 ft MLLW, so the morning (8.27) and evening (9.2) floods are the same rank.

**How verified:** READ; thresholds REPRODUCED by calling the functions.

**Confidence:** high.

**Fix direction:** one shared table of class thresholds.

### FC-14 — The tank holds the bay level from the previous sample
**Severity: low.** Modelled street water stays at curb level 30–60 min after the drains should reopen on a falling tide.

**Evidence**
- `bay_at` returns `tide_waters[i-1]` (FFD:4496–4500).
- Synthetic falling tide with 0.123 in/hr: at bay 2.90 (full drain 0.25 in/hr, more than the rain) the model still reports 4.174.
- Published: `outlook_7d.series` at 2026-11-27 00:00 (19:06Z run) has `pluvial_navd88 4.194` with `tide_navd88 2.533` and rain 0.137. The hourly series makes the lag up to 1 h.
- In the 02:11Z run the curb window ends 00:31 because of this plateau.

**How verified:** REPRODUCED; VERIFIED in published JSON.

**Confidence:** high.

**Fix direction:** interpolate the bay within the step.

### FC-15 — Unknown rain is read as zero in the production path
**Severity: low.** This is charter rule 7.

**Evidence**
- An explicit null QPF interval becomes 0.0 (FFD:1701).
- Hours with no QPF bucket, including series hours before the grid's first interval, become 0.0 in the tank (FFD:630).
- A tide beyond QPF reach reports `peak_rain_in_hr 0.0`, not null (FFD:2338, 2387).
- A null PoP becomes 0 (FFD:2448, 2644).
- The outlook path flags the same cases `rain_unknown` (`forecast/outlook.py:617–625`); production does not.

**How verified:** READ.

**Confidence:** high.

**Fix direction:** carry None through and flag it as the outlook does.

### FC-16 — Product values rounded to 0.1 ft sit on the class thresholds
**Severity: low.** Category, widget day rank and alert rank flip on rounding.

**Evidence**
- Curb threshold 6.98 ft: 6.9 is "street", 7.0 is "light" (+0.24″).
- The 11-27 09:23 tide read 7.0 light (18:09Z), 6.8 street (20:07Z), 6.9 street (02:11Z).
- First-water threshold 6.34: 6.3 dry, 6.4 street.

**How verified:** REPRODUCED (function calls); VERIFIED in commits.

**Confidence:** high.

**Fix direction:** show a product value within its rounding of a threshold as "at the curb", without a class change.

### FC-17 — The 7-day table pairs an NWS-product central value with a P-ETSS band that may not contain it
**Severity: low.**

**Evidence**
- The band is always P-ETSS p10–p90 (`forecast/outlook.py:204`).
- 02:11Z run: 11-27 09:23 central 6.9, band 6.4–6.8; 11-29 11:25 central 5.8, band 5.41–5.71.
- The day card prints "Guidance high end: 6.80 ft … at the P-ETSS 90th percentile" under a central of 6.9 (`forecast/outlook_page.py:232–234`).

**How verified:** VERIFIED in JSON; READ.

**Confidence:** high.

**Fix direction:** label the band as a different model's range, or widen it to include the central value.

### FC-18 — Small slips
**Severity: low.**
- **Legend elevation.** Legends say the lowest landmark is "3.64 NAVD88" (REND:1386–1387 calls it the SW grate; REND:3478–3479, live in `docs/index.html`). The numbers use 3.52 (REND:1566 is correct).
- **Mean window.** Labels say "trailing 365-d mean", the spec says 364-d, and the record covers 338 days (`data/surge_mean.json`: 8,112 hours, 2025-11-28 to 2026-10-31).
- **Surge reading.** It is interpolated linearly between hourly predictions (FFD:775–797), which biases it by up to about 0.075 ft at a crest (synthetic M2 curve; about +0.03 at 21:06 tonight).
- **Product rows at month start.** A product issued in the first days of a month that lists a row from the previous month would be dated a month late (`forecast/nws_surge_parser.py:306–312`); the row then matches no tide.
- **Field name.** `current_surge_ft` is the worst tide's product departure (1.1 at 02:11Z), not the current surge (4.33).

**How verified:** READ; the interpolation bias COMPUTED.

**Confidence:** high, except the month-start case, which is a code reading with no observed instance.

## K4 — where "street = bay (plus rain)" lives (no gate model proposed)
- Curve: FFD:624 and 658–659.
- Table: FFD:1837 and 1847.
- Tank base: FFD:4517–4523.
- Nowcast: `forecast/nowcast.py:534` and 554–555.
- 7-day series: `forecast/outlook.py:613` and 630.
- Class functions: FFD:6002–6016.
- The `compute_flood_windows` docstring already admits symmetric level crossings (FFD:4570–4573).

## Is the decay applied consistently?
- **Table rows without a product row:** yes, the decayed surge at the tide's time (FFD:2317–2321).
- **Curve:** yes per point; earlier hours hold the reading.
- **7-day outlook:** decay is only a fallback (`guidance_decay`, `observed_decay`). Inside 102 h it uses NWPS or P-ETSS, so on ordinary days the 72-h table (decay) and the 7-day table (NWPS) already list different numbers for one tide. This is by design and is logged as `production_mllw` beside `outlook_mllw`.
- **Alerts:** whatever the table holds.

## Checked and found sound
- **Landmarks.** Code (FFD:94–116), `model/elevations.md` (lines 115–129), the spec ladder and the widget (WID:115–134) agree. One datum offset (−2.82) is used throughout; no inch/foot slip found in the depth or tank arithmetic.
- **Constants.** tau 36 h, fresh limit 60 min, snap 0.05 ft / 168 h, fallback mean 0.54, mean age gates, tank K / gamma / k_out / lag, drain law, 48-h alert window, burst analog, NWPS 72 h and P-ETSS 102 h reach, anchor hold 1 h and fade 6 h all match `model/v0.10.6.md`.
- **Decay arithmetic.** It reproduces the published values (6.865 for 11-29 11:25; 10.80 in `outlook_log`).
- **Station time.** GMT transport, offset-bearing keys, product matching in naive local on both sides, and window crossings in UTC are sound. Minor: same-zone aware arithmetic is wall-clock in the two transition hours a year.
- **Published accuracy numbers.** Both sentences reproduce exactly from the ledgers; the window-complete guard works.
- **`regime_hi_max`.** It is ranked by `REGIME_RANK`, not alphabetically.
- **Tests.** 511 ran OK (1 skipped) under `BARNACLE_REQUIRE_GRIB=1`. No test mentions the despike filter (grep of `tests/` for "despike" is empty).

## Could not determine
- The raw NOAA values for 13:00–14:00 EST on 2026-11-26; the feed is not archived, so the exact filter path in FC-1 is inferred.
- Which estimate is right for 2026-11-27 09:23: table 6.9 against curve 9.14 ft MLLW as of 02:11Z. Checkable after about 11:30 EST.
- Whether the street really holds water in the drizzle-over-high-bay cases of FC-8; no observation was found for those dates.
- What the Scriptable widget actually drew; inferred from code and JSON.
- The exact lines in `main()` that save `surge_state.json`; I verified the effect from the commit, not the code.
- Why the nowcast was "gated-quiet" at 13:15, 14:10 and 15:12 EST during the storm (trigger gate; another slice).
- How quiet hours, the daily cap and the stuck `last_sent_rank` would combine if the product were lost. I computed the table flip only.
