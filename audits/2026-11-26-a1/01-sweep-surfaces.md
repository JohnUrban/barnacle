<!-- audits/2026-11-26-a1 supporting file for 01-full-audit-claude-fable-5-2.md -->
> **Sweep report: user-facing surfaces (finding IDs UX-n).** Written 2026-11-26 by a read-only
> subagent of the lead auditor's session (Claude Fable 5.2), filed unedited except
> that scratch paths were rewritten to `audits/2026-11-26-a1/01-probes/surfaces/` (scripts only; large
> data dumps were not committed) and, in the records sweep, one line of personal
> context was redacted. It is evidence for report 01, not an independent review:
> the lead re-checked only the items listed in report 01's verification table.

# Surfaces audit (UX slice) for audits/2026-11-26-a1

Scope note: read-only; nothing in the repo was touched (`git status` still shows only the pre-existing `?? del`). Evidence comes from committed artifacts (`git show <commit>:docs/...`), pure renderers called on those JSONs with a mocked clock and no network, and the widget script executed under a Node stub of the Scriptable API. Nothing was rendered in a real browser or in Scriptable. Leading warning/radar glyphs are omitted from quoted strings. Times are EST on 2026-11-26 unless a date is given.

Test states: (a) forecast `a881364a9` (generated 15:08:02Z = 10:08), nowcast `aaf5956f4`; (b) forecast `66893eb89` (23:07:10Z = 18:07), nowcast `3d79deadb`; (c) forecast `d03ab3191` (02:11:32Z on 11-27 = 21:11), nowcast `d7e4a97bf` (02:12:38Z). Sending runs: `c712c8365` (alert sent 16:09:13Z = 11:09) and `5857208e4` (sent 01:56:36Z = 20:56), per `data/alert_state.json` in those commits. Latest run seen: `bbbf5678b` (22:09).

## Findings (ranked)

### UX-1. One tide, two magnitudes, and each surface picks a different one
**Severity: critical.** A reader cannot tell whether the Fri 2026-11-27 09:23 tide is "street, curb clear" or higher than the evening flood just observed; it was the same split for the Thu 21:07 tide all day.

The root (table = NWS product, curve = surge decay) is already in `history/plans/2026-11-26-storm-evidence-and-queue.md` section A. New here is the surface map and the quoted contradictions.

- **Table-keyed arms:** tide table, day-card tide lines (`rendering.py:264-272`), landmarks table, "Details on highest tide", per-tide pages, outlook day cards, email table, ntfy body, og/meta tags (`rendering.py:3140, 3296-3299`), small-widget "72h" line.
- **Curve-keyed arms:** chart, "Flooding windows" table, both maps' sliders and "Worst" buttons (`flood_forecast_daily.py:8447-8460`, `docs/highlands.html:820-836`), all `today_*` fields (`flood_forecast_daily.py:2718-2730`), hence the widget headline/peak/window lines and the email "TODAY" block.
- **Mixed, unexplained:** the day-card badge (`rendering.py:309-323`, max of both) and email "WORST 72H" (label from `day_worst`, detail from the table).

Quoted contradictions on one page:
- **State (a), Thu 21:07 tide:** day card "★ Thu 9:07 PM tide — severe (+27.1″)" and table "8.60 | Porch step 1 | +5.5″ | +28.2″ | severe", against flood windows "SW distal grate across Bay | 3.52 | ~19:39 → 00:00 | 4.3 h | +8.9″ at 21:00" and "Curb TOP at walkway | 4.16 | ~20:23 → 22:37 | 2.2 h | +1.2″ at 21:00". Observed street crest was +30.7″.
- **State (c), Fri 09:23 tide:** TOMORROW card badge "SEVERE" directly over "★ Fri 9:23 AM tide — street (+6.7″)"; table "6.90 | NW corner | +2.0″ | +6.7″ | street"; flood windows "SW distal grate across Bay | 3.52 | ~06:06 → 12:21 | 6.2 h | +33.6″ at 09:30"; per-tide page "STREET ... curb still clear. Peak forecast: 6.90 ft MLLW"; outlook page "Tomorrow · Fri 11/27 STREET WATER — worst pathway: tide".
- **State (c) email subject (re-rendered):** "... | WORST 72H SEVERE: tide peak 6.90 ft at Fri 9:23 AM (NW corner +2.0")".
- **Live at `bbbf5678b`:** badge "SEVERE" over "street (+6.7″)"; windows "+29.2″ at 09:30"; `outlook_7d.tides[1].guidance` = nws_product 6.9, persist_decay 8.79.

**Verified:** REPRODUCED (committed HTML/JSON; email via `render_email`). **Confidence:** high.
**Fix direction:** one day-scoped headline value consumed by every arm, with both sources shown and labelled wherever either appears (plan queue items 2 and 4).

### UX-2. Widget and the alert email's "TODAY" headline said MODERATE/LIGHT hours before the highest flood in the ledger
**Severity: critical.** The glance surface and the top line of the only long-lead alert understated the evening flood by two classes.

The widget and email TODAY block read `today_regime` (curve only); `day_worst` is not referenced in `docs/barnacle-widget.js`, `forecast/outlook_page.py` or `docs/highlands.html` (grep count 0 each). The site day card at the same moments said "SEVERE". This is a rule 8 breach.

| Run | Widget headline | Widget peak line |
|---|---|---|
| 11:09 (`c712c8365`) | "MODERATE" | "peak +13.7″ vs SW grate @9P" |
| 12:07 (`e8acc1164`) | "LIGHT" | "peak +11.5″ vs SW grate @9P" |
| 13:09 (`6c2ae33ba`) | "MODERATE" | "peak +13.2″ vs SW grate @9P" |

- **Email sent 11:09 (re-rendered from that run's forecast.json):** subject "[342 Bay] TODAY MODERATE (so far: REPORTED at 09:48: “I stand corrected. There is a flood out there now.” (not measured)) | WORST 72H SEVERE: tide peak 8.60 ft at Thu 9:07 PM (Porch step 1 +5.5")".
- **Its HTML top block:** "TODAY — OUTLOOK / MODERATE / Tide peak today +13.7″ vs SW grate at 21:00", then "WORST 72 H SEVERE — worst-case tide peak 8.60 ft MLLW at Nov 26, 2026: Thu 9:07 PM". That is the same tide twice, +13.7″ and +27.1″.
- **State (a) medium widget:** the only numbers were the morning's tail, "Porch base wet ~6:33A–10:19A (3.8h)" and "peak +18.5″ vs SW grate @10A". The 8.60 ft evening figure appears nowhere on it.

**Verified:** REPRODUCED (Node harness on the committed widget; email re-render). The literal sent bytes are not in the repo; renderer code is unchanged since 2026-09-28 (`rendering.py`) and 2026-11-17 (facade). **Confidence:** high.
**Fix direction:** widget and email TODAY consume `day_worst[0]` (with a widget version bump); label the "peak" line with its source.

### UX-3. One burst of gauge noise published "+54.3″" (porch-deck level) for an hour with every input "ok"
**Severity: high.** A user checking at 14:06–15:07 saw a Sandy-class number with no warning.

Run `7386bc773` (19:06:47Z):
- `water_series_input.detail` = "surge +7.22 ft from a reading just now..."
- `live_gauge_24h` tail: 12:54 4.418, 13:12 6.22, 13:18 4.694, 13:36 6.318, 13:42 6.006, 14:00 7.302.
- The next run `fc515b6a2` shows 13:30–14:00 as 3.879–3.584.
- `degraded_inputs` was `[]`, and `surge_observation` and `live_gauge` were "ok".

Published in that hour:
- Widget: "peak +54.3″ vs SW grate @9P" and "Porch base wet ~8A–1:53P (5.9h)".
- Site windows: "SW distal grate across Bay | 3.52 | ~08:00 → 02:31 | 18.5 h | +83.9″ at 08:30".
- Site gauge note: "Latest: 7.30 ft MLLW at Nov 26, 2026: Thu 2:00 PM".
- The day card on the same page still said "severe (+27.1″)".

This explains the "8.05 unexplained" item in the e02 README.

**Verified:** REPRODUCED for what was published. The mechanism is INFERRED: `_despike_gauge` (`flood_forecast_daily.py:984-1019`) has a one-sided window at the series end with several contaminated neighbours. **Confidence:** high on the facts, medium on the mechanism.
**Fix direction:** plausibility bound on surge and on its change between runs, plus a held-back newest reading; fail to the "degraded" label rather than publish.

### UX-4. No surface says what the water is doing now in a tide flood; when "now" appears it is worded as rain
**Severity: high.** From 19:16 to 20:55 the owner watched water climb from the curb to the second-step wall while every headline was an hourly outlook.

- **Gating:** the strip, widget LIVE line and imminent ntfy all require `nc.active` (`rendering.py:3389`, widget `:526`), which is `recent_max > max(0.3, drain)` in/hr (`nowcast.py:520`). All 27 nowcast commits from 21:21Z to 01:47Z have `active false` with no `street_now_in`, while `bay_navd88` in the same files rose 1.09 → 6.29.
- **Strip wording at (c) (reconstructed from `rendering.py:3400-3413` + JSON):** "Rain on the hillside now: 0.3 in/hr (radar). Street water ≈ +33.5″ vs SW grate; projected peak +33.6″ around 02:16 UTC. Tank model on OBSERVED radar, not forecast...". It prints a UTC clock and credits radar for a level that is bay gauge plus about 0.6″.
- **Email-rail ntfy body at 20:56:** "[Barnacle] ALERT: FLOODING (radar): street +33.5″ now → +34.0″ projected (severe). Verify on the site chart.; severe tide flooding Thu 9:07 PM (8.80 ft)."
- **Imminent text (reconstructed with an empty prior state):** "[342 Bay] STREET FLOODING PORCH-STEP LEVEL: +34" now, bay over grates. 8:56PM". Observed at 20:54–20:59 was +27.5″ to +28.7″ (e02 README).
- **Trend:** the JSON said `trend: "falling"` from its first active run (01:55Z) while the street rose until 21:15.
- **Day card at 21:11:** "Thu 9:07 PM tide — severe (+29.5″) (past)", four minutes before the crest.

**Verified:** REPRODUCED for the JSON timeline and widget; READ for the strip (not run in a browser); INFERRED for the imminent text. **Confidence:** high.
**Fix direction:** a "NOW" line fed by the live bay reading on every arm, labelled as bay level and not as street or radar, in local time; "past" only after the water is observed or modelled to have left.

### UX-5. The closed tide gate is not disclosed where a decision is made, and bay-derived levels are worded as street facts
**Severity: high.** Tidal calls are expected to be off while the gate is closed (HANDOFF), and a reader is never told.

The only mentions are historical, in a collapsed "Explain this figure" (`flood_forecast_daily.py:6361`) and on the details page (`rendering.py:413`). There are zero mentions in the widget, `outlook_page.py`, `docs/highlands.html`, the email or the ntfy text.

Wording that asserts street state from the gauge:
- Chart explain: "In ordinary tides the corner has tracked it within a few inches".
- Flood windows: "Times are approximate (∼10–20 min)" (`rendering.py:1645`). On 11-26 the model had the SW grate wet from 05:45 and the porch base from 06:33; the owner reported no flood at 09:47 and a flood at 09:48.
- Recent peaks at (c): "Thu, Nov 26 | 9.21 | Thu 8:54 PM | +34.5″ | Porch step 1 +11.8"". Observed was 8 in above that step at most.
- Details page: "tide-only floors ... actual water at 342 was at least this high".
- Details page: "Flood recall: 74.6% (50/67 observed floods caught)", where "flood" means gauge ≥ 6.34 ft (`rendering.py:888`).

**Verified:** REPRODUCED by grep and committed pages. **Confidence:** high.
**Fix direction:** a standing gate notice on every arm that carries a tidal call, and relabel gauge-derived street statements as bay level.

### UX-6. A surge-tide flood is labelled "(RAIN)"
**Severity: medium-high.** It tells readers the worst case depends on rain when about 98% of the water is tide.

`compute_day_worst` sets the pathway to "rain (tank line)" whenever `wmax > tmax + 0.02` ft (`flood_forecast_daily.py:4849`). At (b) the tide was 5.641 and water 5.689, a 0.58 in difference.

- Site from 14:06 through 22:09: badge "SEVERE (RAIN)" with ribbon "▲ WORST OF 72 H · rain (tank line)".
- Email sent 20:56: "WORST 72H SEVERE (RAIN): tide peak 8.80 ft at Thu 9:07 PM (Porch step 1 +7.8")".
- Outlook page at (c): "Rain pathway: tank line peaks +30.1″ vs SW grate at 21:00 (severe flooding)".
- Arms disagree: the email TODAY at (b) says "SEVERE" (`headline_for` needs a strictly higher rank) where the site says "SEVERE (RAIN)".

**Verified:** REPRODUCED. **Confidence:** high.
**Fix direction:** attribute by share of the water above the tide, or label "tide + rain".

### UX-7. "Worst" points at a different tide on each arm in the same state
**Severity: medium.** The word that should settle the question does not.

At state (c):
- Day-card ribbon: "WORST OF 72 H · rain (tank line)" on the Thu card, whose tide is "(past)".
- The ★ marker: "Fri 9:23 AM tide — street (+6.7″)".
- Landing map "Worst tide" and "Worst flood chance" buttons: both select `2026-11-27 09:30`, w = 6.321 (+33.6″).
- Outlook page: "Worst tide: +24.7″ at Thu 10 PM".
- Link preview: `og:title` "Bay Ave Barnacle — STREET", with description "Worst-case tide peak 6.90 ft MLLW at Nov 27, 2026: Fri 9:23 AM". This was served at the crest and is still live at `bbbf5678b`.

At state (a) the map's "Worst tide" selects Fri 09:30 at 4.716 (+14.4″) while the ribbon says the Thu 9:07 PM tide (+27.1″). At `bbbf5678b` the outlook says "Worst tide: +6.7″ at Fri 9 AM" while the landing windows say "+29.2″ at 09:30".

The ntfy text also names a tide already past: the state (a) would-be body is "severe tide flooding Thu 8:28 AM (8.30 ft)" at 10:08, and at 22:09 it is "severe tide flooding Thu 9:07 PM (8.80 ft)". This is plan item C.2.

**Verified:** REPRODUCED (embedded `var MS` in published HTML; committed pages). **Confidence:** high.
**Fix direction:** define "worst" once (pathway-scoped, future-only) and have every arm read it.

### UX-8. Unavailable is shown as "none" or as nothing on the widget and for the live nowcast
**Severity: medium.** This is rule 7 on the glance surface.

- **Rain inputs down:** with QPF, hourly and alert fetches failed, `pluvial_risk.level` is None and `day_outlook.rain_risk` is False (`flood_forecast_daily.py:2471-2494, 2707-2714`). The widget then prints "NO FLOODING" (green, large) and "Rain flood: none", with the only caveat an 8 pt line "degraded inputs: rain QPF, NWS hourly, alerts". The site day card for the same inputs says "Rain: forecast inputs unavailable — not assumed dry".
- **Stale forecast:** a 9-hour-old forecast keeps the big headline and adds only "STALE — forecast from 9:11 PM (9h old)" at 8 pt.
- **Nowcast health:** `input_health` has no radar/nowcast key. A stale, degraded or errored nowcast simply hides the strip and LIVE line.
- **Fallback bay level:** `bay_source` ("astronomical-fallback", `nowcast.py:456-463`) is read by no renderer, widget or alert gate (grep count 0). 2 of 31 sampled nowcast commits since 2026-09-20 used the fallback (both inactive).
- **Latent crash:** an active nowcast without `street_now_in` replaces the whole widget with "Cannot read properties of undefined (reading 'toFixed')".

**Verified:** REPRODUCED on synthetic field values for the widget cases (not a real outage); READ for the server paths; sampled for the fallback. **Confidence:** medium-high.
**Fix direction:** "rain: unknown" on the widget, a greyed headline when stale, and nowcast health plus bay source as visible inputs.

### UX-9. "Flooding windows (coming 30 h)" and the widget's "wet" line show past or model-retro windows, with no dates
**Severity: medium.** Readers get a wrong time for when water arrives or leaves.

- `flood_windows` is built on a series that starts 6 h back; the table prints clock times only (`rendering.py:1617-1638`) and the widget takes element `[0]` (widget `:246`).
- **Widget through the afternoon:** 15:07 "Porch base wet ~9A–11:12A (2.2h)"; 16:07 "~10A–11:22A (1.4h)"; 17:07 "~11A–11:25A (0.4h)". The start is the series' left edge, and the past is recomputed with the current surge.
- **The evening window** first appears at 18:07: "Porch base wet ~7:04P–10:44P (3.7h)".
- **State (a) table** lists "+28.6″ at 08:30" under "coming 30 h", against "Recent observed peaks" on the same page, "8.27 | Thu 8:54 AM | +23.1″".
- **Three same-landmark rows** for Thu morning, Thu evening and Fri morning carry no day label.

**Verified:** REPRODUCED. **Confidence:** high.
**Fix direction:** future windows only (or mark past ones), add weekday labels, and select the next window on the widget.

### UX-10. The widget's live flood classes use different thresholds from the server
**Severity: medium.** The same live number gets two class words.

The widget uses 22.7 / 13.7 / 7.7 in (widget `:649-652`). The server uses curb +8 / +4 in, i.e. 15.7 / 11.7 / 7.7 in over the SW grate (`flood_forecast_daily.py:191-193, 6002-6016`).

On 2026-11-12:
- Nowcast `dc838b68e`: `regime_display` "DRY → SEVERE (rising)"; widget "MODERATE · LIVE".
- Nowcast `e89453361`: "MODERATE"; widget "LIGHT · LIVE".

**Verified:** REPRODUCED (harness). **Confidence:** high.
**Fix direction:** the widget displays `nc.regime_display` instead of re-deriving it.

### UX-11. Accuracy displays claim more than they measure
**Severity: medium.** Skill numbers sit beside a storm call they do not describe.

- **Tide-table column:** "Peak MAE at this lead" showed "0.16 ft (156 predictions)" at (a) and "0.11 ft (81 predictions)" at (b) for the Thu 21:07 tide. Its error was −0.4 to −0.6 ft at 11 h and −0.8 to −1.0 ft at 3 h (8.6 and 8.2 against 9.0–9.2 preliminary). The count is hourly issuances on 26–27 tides.
- **Depths to 0.1 in** at 11 h lead ("+27.1″").
- **"Outcome-depth accuracy":** "N = 21 labeled observations", last row 2026-07-09, under "Compares each user-logged observation" (`rendering.py:812`). The ledger has 232 numeric-depth rows; none of the 78 since 2026-09-01 carries a model prediction, so the September and November floods are unscored.
- **The note** "an append-only record; rows are never recomputed under newer models" (`rendering.py:924`) does not mention the 109 rows corrected in place on 2026-11-10.

**Verified:** REPRODUCED and READ. **Confidence:** high.
**Fix direction:** condition the MAE on storm tides or show the storm figure, count tides, and state the rescore and the outcome table's coverage.

### UX-12. "So far today" edge cases
**Severity: medium-low.** A derived or misdated value can carry a "MEASURED" or exact-time label.

- **Derived shown as measured:** live now, "SO FAR: MEASURED +30.7″ at 21:15 (measured, severe)". Ledger row 293 reads "just barely breaching over the second step ; basically level with it" with depth 8.0 entered from the taped riser. The e02 README calls 6.08 "derived, not read", and the second step is not a landmark.
- **Surrogate times** live only in the `notes` column. With rows 279–282 + 296 alone, the line reads 'REPORTED at 09:48: “As for episode 1, I think it made it to about the level of the lawn step and reversed. It was nowhere near as extreme as tonights (episode 2). (user)” (not measured; time as logged)'. That is a 21:57 recollection shown at 09:48, and it wins the tie with row 280 by file order (`:5839, 5854`).
- **Approximate time read as exact:** `_lookback_time_uncertain` returns False for row 281's "starting around 9:37'", because the closing quote matches the feet unit in `_UNIT` (`:5604-5615`).
- **No guard against times later than now** (`:5806`).
- **Midnight reset:** the result is `null` at 00:10 on 11-27, so the flood vanishes from every arm.
- **Any qualitative report outranks the bay peak**, so from 09:48 until 22:09 every arm, including at the crest, showed the morning quote.

**Verified:** REPRODUCED (mocked clock, temp copies of the real rows, no network). **Confidence:** high.
**Fix direction:** a machine-readable time kind and evidence kind on ledger rows; fix the unit lookahead; carry the last flood across midnight.

### UX-13. Time display
**Severity: low.** Each item costs seconds for a reader in a hurry.

- The strip prints "around 02:16 UTC" (`nowcast.py:584`, `rendering.py:3410`).
- The outlook page is stamped "generated 2026-11-27T02:11:32Z" while the details page says "generated Thu Nov 26, 09:11 PM ET".
- "Note: today's forecast peak (6.90 ft)" at (c) refers to Friday's tide.
- "Recent observed peaks" truncates its oldest day: "Thu, Nov 19" reads 4.63 @ 2:42 PM at (a), 2.86 @ 6:12 PM at (b) and 2.76 @ 11:54 PM at (c).
- Chart tooltips and the now-line use the device time zone (`rendering.py:1896, 2040`; `flood_forecast_daily.py:6441`).

**Verified:** REPRODUCED and READ. **Confidence:** high.
**Fix direction:** station-local everywhere, with full days in the recap.

### UX-14. Stale or wrong copy
**Severity: low.**

- "Rel = inches above the lowest landmark (lowest road corner, 3.64 NAVD88)" (`rendering.py:3478`) and the text email's "(SW grate across Bay, 3.64 NAVD88)" (`:1386`). The value is relative to the SW grate at 3.52 (`landmark_summary`); the HTML email says 3.52.
- The table Rel "+28.2″" (rain bonus included) against the card's "+27.1″" for the same tide.
- "High tides in next 24h" heads a 72-h table (`:1440, 1559`).
- Per-tide pages describe "the time slider below (it opens on NOW)" and "Worst tide" buttons that are not on the page (0 matching ids).
- "water ≈ 3.52 NAVD88 (-7.7″ at curb) — 7/6-class flash flood" at (a) (`:1732`).
- `README.md:17` still says "optional email-to-SMS alerts"; the comment at `.github/workflows/daily_forecast.yml:75` says "ntfy/email/SMS".
- Details page: "largest local floods this project has recorded — Sep 26 2026 (5.70 NAVD88...)" is now superseded.
- Outlook card: "Guidance high end: 6.80 ft" sits below "with guidance 6.90 ft".

**Verified:** REPRODUCED and READ. **Confidence:** high.
**Fix direction:** one copy pass.

### UX-15. Phone-at-night basics
**Severity: low.**

- **Widget safety lines below 4.5:1 at 8 pt:** STALE flag `#c0392b` on the severe background `#ffcdd2` is 3.86; degraded-inputs `#b45f00` is 3.26 on severe and 4.08 on green; the data-time footer `#888` is 2.52.
- **Site:** `.note` `#888` on white is 3.54; "(past)" `#999` is 2.02 on the severe card.
- **No dark scheme** in `docs/style.css`.
- **The TODAY card renders after the chart** (`rendering.py:3445-3447`).
- **The alert email subject** puts the warned tide's number after a roughly 150-character "so far" quote.

**Verified:** computed and READ. **Confidence:** high on the ratios; layout was not viewed on a device.
**Fix direction:** darker small-text colours, TODAY first, warning first in the subject.

## Checked and found sound

- **Widget version:** footer "v7.35a" matches the last widget edit in git (`62b947da7`, 2026-09-28, which changed v7.34a → v7.35a).
- **Links:** 634 relative href/src/fetch references on 15 pages (landing, details, outlook, town map, both indexes, 8 per-tide pages) and all 378 tides-index links resolve to committed files.
- **SMS on the site:** no published page mentions SMS or texts.
- **Peak-error summary:** details-page "Last 30 as-run forecasts: mean error +0.02 ft, mean |error| 0.22 ft" matches `data/forecast_accuracy.csv` (0.018 / 0.220, runs 2026-10-28 to 11-25; sign is predicted − observed).
- **Offset-bearing times:** parsed correctly by the widget and renderers in all three states (EST labels and hours-to-peak are right).
- **"So far" consistency:** the phrase carried the same evidence on site, email and widget in every state; the measured maximum is chosen correctly despite the out-of-order row 296.
- **Live override:** at (c) it fired on site and widget together.
- **Degraded production inputs on the site and email** have a prominent block and "not assumed dry" wording (READ; not triggered on 11-26, where `degraded_inputs` was `[]`).
- **Unit tests:** 511 ran, OK, 1 skipped (`BARNACLE_REQUIRE_GRIB=1`).

## Could not determine

- Real pixels: charts, maps, reflow, and the strip in a browser or Scriptable.
- The literal bytes of the two alerts sent (11:09, 20:56); they were re-rendered from the sending runs' forecast.json.
- Which number is right for the Fri 09:23 tide (not yet occurred).
- Whether the installed widget copy is v7.35a (HANDOFF says so).
- What the CDN served between commits.
- The HANDOFF's "−0.09 ft" as of 2026-11-10: I get −0.064 for the last 30 rows dated on or before 11-10, and did not resolve the difference.
- Display of the September (EDT) data in the charts.

## Reproduction files

Scratch only, in `audits/2026-11-26-a1/01-probes/surfaces/`:
- `widget_harness.js` — usage: `node widget_harness.js <widget.js> <forecast.json> <nowcast.json> <ISO now> medium|small`
- `render_states.py` — email and ntfy text for a state directory
- `lookback.py`, `lookback2.py` — the "so far" probes
- `h2t.py` — HTML to text
