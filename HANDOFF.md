# Bay Ave Barnacle — Project Handoff

**A hyperlocal flood prediction system for 342 Bay Avenue, Highlands NJ.**

This document is the authoritative state-of-the-project. It captures
the model, the architecture, what works, what didn't and why, what's
next, and all design context worth carrying into future work.

If anything anywhere disagrees with this document, **assume the file
with the higher version number wins** (currently model spec v0.10.1 —
`model/v0.10.1.md`; older specs live in `model/archive/`).

**Status: PRODUCTION.** The system is deployed, scheduled, and
self-publishing. The site refreshes on the forecast workflow and
event-driven alerts use ntfy/email/SMS when risk appears or escalates;
routine daily-morning email is retired. As of the handoff date the loop
runs without intervention; the work ahead is refinement, not bootstrap.

---

## 1. The project in one paragraph

A homeowner at 342 Bay Avenue, a low-lying property in Highlands NJ on
Sandy Hook Bay, has experienced repeated flooding from tidal + rainfall
events. Public sources (NOAA Sandy Hook gauge, the Sandy Hook Tidal
Flooding Dashboard, tide-prediction apps) give regional-scale signal
that misses the user's specific property in two directions: false
positives (predicted flooding that doesn't materialize at this house)
and false negatives (actual flooding without sufficient warning).

The project produces an **hourly-updated interactive site** plus
**event-driven flood alerts** at
[johnurban.github.io/barnacle](https://johnurban.github.io/barnacle/)
(water-level chart, flood windows, heat-map, per-tide deep-link
pages, forecast.json for the iOS widget), predicting water depth at
**18 surveyed landmarks** at 342 Bay Ave — from the SW grate (first
water) up the porch ladder to the deck — via two pathways: a
tide-keyed level model and a volume-based pluvial (rain) model.

The model is small but earned: every parameter is grounded in either
surveyed engineering elevations from a Borough PDF, or in empirical fit
across labeled flood events the user observed and tape-measured
firsthand.

**RAIN-DNA DOCTRINE (user directive 2026-07-06 — binding on all
future work):** rain modeling is Barnacle's core value-add over the
numerous tide apps (the user runs three of them). Rain effects are
NEVER deferred to a future version: ship crude, honest,
directionally-right rain models now and recalibrate with each event.
If a plan says "rain term deferred to vNext," the plan is wrong —
implement the simplest version instead. Context: heavy rain floods
this intersection with zero tidal contribution (7/6/2026), and
rain+tide compound events are the worst on record (Oct 30 2025); a
previous assistant repeatedly pushed rain modeling into the future
across v0.6–v0.8 and the user explicitly rejects that pattern.

---

## 2. Status at handoff

| Component | State |
|---|---|
| Model v0.10.1 specification (18 landmarks; tide-keyed + measured/refit dynamic pluvial tank) | ✅ Current — `model/v0.10.1.md`; v0.1–v0.10 in `model/archive/` |
| Forecast script (`forecast/flood_forecast_daily.py`) | ✅ In production, scheduled via GitHub Actions |
| Multi-tide forecast (both high tides per day) | ✅ Live since 2026-05-18 |
| NWS surge parser (`forecast/nws_surge_parser.py`) | ✅ Self-test passes; awaits first live event |
| GitHub Actions workflow | ✅ Hourly forecast plus rain-gated nowcast; schedules are best-effort under GHA throttling |
| Alert delivery (ntfy + Gmail SMTP + optional SMS gateway) | ✅ Event-driven; channels isolated and acknowledged only after confirmed delivery |
| GitHub Pages site | ✅ Live at johnurban.github.io/barnacle/ |
| Forecast archive (every day kept forever) | ✅ docs/archive/YYYY-MM-DD.html + .json |
| Machine-readable JSON archive (HANDOFF 16c) | ✅ Live since 2026-05-18 |
| Bcc privacy for multi-recipient | ✅ Built into send_email |
| Repo reorganization | ✅ Clean structure, old work archived in `attic/` |
| Historical statistics project (Claude Code) | ✅ Complete (2026-05-18). Report + CSVs in `history/` |
| Dashboard threshold correction | ✅ Corrected to 6.70 ft (was wrongly documented as 7.20 ft) |
| Stratified landmark table (8 strata, depth + history + MTD) | ✅ Live (2026-05-18) |
| Plain-language summary + confidence indicator | ✅ Live (2026-05-18, HANDOFF 8a + 16a) |
| Rain timing detail, recent-history recap | ✅ Live (2026-05-18, HANDOFF 8c + 16b) |
| Low-tide times in email | ✅ Live (2026-05-18, HANDOFF 11) |
| Day-name / AM-PM time labels everywhere | ✅ Live (2026-05-18, HANDOFF 5) |
| Unusual-forecast highlight (top-N% framing) | ✅ Live (2026-05-18, HANDOFF 16e) |
| Forecast accuracy log (`data/forecast_accuracy.csv`) | ✅ Live (2026-05-18, HANDOFF 8b). Populates from day 2. |
| Spot-check calibration callouts (pluvial-only, cold-lockout) | ✅ Live (2026-05-18, HANDOFF 10/14) |
| First real spot-check session (2026-05-18 22:12 peak) | ✅ Recorded. Forecast 6.19 / actual 6.58. **Key finding: with corrected grate elevation (3.80 not 3.91 per survey), local enhancement at SH 6.58 was ~0 or slightly negative, not +0.40. Refined hypothesis: +0.40 is a storm-surge propagation effect, not a constant.** See `assets/observations/2026-05-18/README.md` |
| v0.6 grate elevation bug | ✅ **Fixed in v0.7 (2026-06-15).** `corner_grate` renamed to `grate_NE`, elevation corrected 3.91 → 3.80; 3.91 lives separately as `corner_NE` landmark. Pathway B threshold under v0.7 enhancement (-0.13): SH 6.59 (= grate_bay_ave_upstream 3.64 + 2.95). |
| Photos from 2026-05-18 event distributed to 7 subdirectories | ✅ Done 2026-05-19. Medium-size exports (~13 MB total) under `assets/observations/2026-05-18/<grate-or-landmark>/`. 13 calibration rows in `data/labeled_observations.csv`. Plus 3 morning-after pocket photos (cba8338) confirming ≥11.4h pocket retention. |
| Second + third real spot-check events (2026-05-30, 2026-05-31) | ✅ Logged 2026-05-31. 2026-05-30 PM tide qualitative (SE/SW overtopped at SH 6.538). 2026-05-31 PM tide cleanly measured at 4 grates (water 7.25/7/5/4 in below NE/upstream/SE/SW respectively at SH 6.17 peak) — water at 342 Bay = 3.20 ± 0.05 NAVD88, implied local enhancement = -0.13 ft, **consistent with 5/18 finding**. Two events now contradict the +0.40 constant. 9 new rows in `data/labeled_observations.csv`. See `assets/observations/2026-05-30/README.md` and `assets/observations/2026-05-31/README.md`. |
| High-res measuring-tape reference photos | ✅ Added 2026-05-31. Two straight-on photos + README in `assets/observations/0-measuring-tape/` covering the digit-after-line convention, subdivision marks, color cues, and common photo-reading failure modes. Use when independently verifying tape readings from spot-check photos. |
| Hourly bot cadence — actually ~62%, not 100% | ⚠️ Documented 2026-05-31 (see `assets/observations/2026-05-30/README.md` cadence section). GitHub Actions throttles the `'0 * * * *'` schedule. Last 7 days: 120/192 hour-slots filled. UTC hours 02/04/06 never run; 08/10/11/12/14/16 partial. No fix — this is GHA free-tier load shedding behavior. Convergence charts have ~1.5-2 h effective resolution, not 1 h. |
| Web platform pivot — sub-daily updates, interactive site | ✅ Foundation shipped 2026-05-19. See section 9b. Workflow hourly; per-tide deep-link pages; client-side heat-map renderer; convergence + oscillation + scrubber charts; severity-colored rollup with 24/48/72h toggle; rain-toggle map; refined confidence with regime band; 1-2 month astronomical look-ahead; accuracy scatter + binary classifier matrix. Master predictions log at `data/predictions_log.csv` accumulating since 2026-05-19. |
| v0.7 model spec promotion | ✅ **Shipped 2026-06-15.** Bundles: corrected grate elevations + 5-grate set (NE/NW=3.80; SE=3.60; SW=3.52; upstream=3.64 low-point); new corner landmarks (corner_NE/NW=3.91; corner_SE/SW=3.64); renames (`corner_grate`→`grate_NE`, `lowest_sentinel_grate`→`grate_SE`, `lowest_road_corner`→`corner_SE`, `intersection`→`intersection_highpoint`); **enhancement = constant −0.13 ft** (3-event mean — 6/14 disproved the original piecewise heuristic at high SH); single-water-level math (drops per-landmark rain shedding); negative-surge clip removed; rain window before-biased [−90 min, +15 min]. **Re-evaluated 2026-06-15**: v0.7 actually fits Oct 30 2025 within 0.7″ at curb without retuning — the v0.6 rain term (`8·tanh(rate)`) applied as water-is-level rise is correctly calibrated. The earlier "rain-flood under-predicts" caveat I wrote was based on a flawed mental calculation. The remaining open question is whether the pre-spot-check Apr/Dec events (which give implied enhancement ~+0.4) reflect memory imprecision or a real storm-condition amplification. See `model/v0.7.md` for the full calibration table. |
| v0.8 model spec promotion | ✅ **Shipped 2026-06-16.** Same-night reaction to 2026-06-15 PM storm-condition event (SH 7.289, peak winds N/NNE, v0.7 under by 1.3″ structural / 3.5″ operational at curb). Changes: enhancement constant −0.13 → 0.00 (conservative; matches storm condition, errs +1.5″ on regular tides — within tape precision); **NEW wind-direction adjustment** (`compute_wind_adjustment()`) reports a −0.13 ft "expected actual" line when forecast wind at peak is in offshore sector (S/SSW/SW/WSW/SSE) — calibrated against 6/14 (offshore peak, enh −0.13) vs 6/15 (onshore peak, enh 0); NEW landmark `sidewalk_under_walkway_lawn_step` at 4.33 NAVD88 (cross-fit from 3 measurements). SH thresholds all shift −0.13 ft uniformly. See `model/v0.8.md` and `assets/observations/2026-06-15/README.md` for the full anchor. |
| v0.9 model spec promotion | ✅ **Shipped 2026-07-06** (the pluvial flash-flood day; three same-day commits). Bundles: (a) **QPF input fix** — rain had been silently 0.0 in every production run ever (NWS moved QPF to the gridpoint endpoint); (b) **pluvial advisory banner** with v0.9-alpha scenario depths (`estimate_pluvial_water`, two-regime, calibrated on 7/6 + Oct 30); (c) **porch ladder re-anchored**: `lawn_step` 4.58→4.66, fictitious `porch_step` 5.08 removed, NEW `porch_step_base` 4.68 / `porch_step1_top` 5.41 / `porch_deck` 8.08 (18 landmarks total); (d) lookahead thresholds recomputed (were v0.6-era); (e) seasonality display join aliased (CSV keys/thresholds stale — annual refresh). See `model/v0.9.md`. |
| Series-first architecture + flood windows + TODAY-first widget | ✅ **Shipped 2026-07-06 (evening).** Rain-DNA build: (a) QPF rain layer IN `water_series` (deterministic layer; sustained rain renders as curve bumps); (b) rain-burst *potential level* on charts (amber dashed — analog-scaled burst magnitude without fake timing); (c) `compute_flood_windows()` — start/end/duration/peak per landmark from series crossings (grazing episodes phrased "may briefly touch"); (d) `today_*` forecast fields (regime/peak/rel-to-SW-grate — the standard mental unit); (e) widget redesigned TODAY-first (today colors the widget; 72h-worst is a labeled secondary line); (f) home-page water-level chart + flooding-windows table; (g) email "Today" line. |
| Water-level chart design (FINAL, user-approved 2026-07-06) | ✅ Converged after a long design loop; do not regress. Grammar: **solid blue** = tide+surge (will happen); **navy band** = rain-burst potential, bottom = tide curve, top = FLAT absolute potential level, drawn only across burst-capable hours (thickness = rain's headroom over the tide); **amber solid** = sustained-rain street-water line (two-line design, never spliced with tide); **dashed colored lines** = landmark ladder (labels live in the LEGEND, never as boxes on the plot; shared palette with the widget: black solid=SW grate ground, green=gutter, red=curb, purple=lawn step, brown=porch step 1); y-axis = inches vs SW grate, standard frame [−60,+36] with auto-expand; 6-h ticks, dotted midnight lines, now-line + dot on curve (browser-time on the website). EXTENDED 2026-07-07 (evening, iOS session): the grammar now governs ALL charts — the peaks charts too (landmark lines as legend datasets, same palette). Both peaks charts default to inches-vs-SW-grate with an ft-MLLW toggle (shared localStorage key `barnacle-peaks-unit` + custom event). Charts sit in fixed-height wrappers with `maintainAspectRatio:false` (width-locked aspect + legend rows crushed plots to ~50px on phones). |
| Move to `bayavebarnacle@gmail.com` SMTP account | ⏸ Awaiting account-aging for Gmail app passwords |
| First real-event validation of NWS parser | ⏸ Awaiting next coastal flood event |
| v0.6 model-spec promotion + 9th landmark added | ✅ Live (2026-05-18). model/v0.6.md canonical; v0.5 archived. New lowest sentinel at 3.60 NAVD88 (SH 6.02). |
| SMS/push alerts for moderate/severe (Twilio/Pushover) | ⏸ Next-turn item |
| iOS Stage-1 Web Clip (Add to Home Screen) | ✅ Live (2026-05-18). manifest.json + apple-touch-icon + meta tags |
| iOS Stage-2 Scriptable widget | ✅ Live (2026-05-18). Script at docs/barnacle-widget.js. **Rebuilt 2026-07-06**: v0.8 landmark set (old v0.6 keys had silently broken highestExceeded since the v0.7 promotion), enhancement 0.00 (was hardcoded +0.40), "dry"→"NO FLOODING" display, and a NEW 24-h model water-level tide-curve chart (medium widget) fed by the `water_series` field now emitted into forecast.json (30-min steps, now−2h→now+24h, tide+surge backbone; pluvial line + burst band added later that evening — see the series-first row). |
| "DRY" → "no flooding" display language | ✅ Done 2026-07-06. Internal regime key `dry` frozen (predictions_log continuity); display-only mapping via `REGIME_DISPLAY` + `regime_display()`. Applied: subject line, regime banners, tide tables, meta tags, glossaries, equation widget, Scriptable widget. Also refreshed the stale v0.6-era reference scales (email text + home page) to v0.8 thresholds, and fixed a footer still claiming v0.7. |
| iOS Stage-3 PWA push notifications | ⏸ Next-turn item |
| iOS Stage-4 native iOS app | ⏸ Multi-session, requires Apple Developer Program |
| Live NOAA gauge link/embed on Pages site | ⏸ Next-turn item |
| Stevens NYHOPS surge fallback | ⏸ Not investigated further |
| ETSS direct fetch | ❌ Abandoned — network blocked from user's ISP |
| Node.js 20 deprecation in workflow | ✅ Done 2026-07-06 — checkout@v7 / setup-python@v6, verified green |

✅ done · ⏳ in progress · ⏸ backlog · ❌ ruled out

---

## 3. The model in one screen (v0.10.1 — see model/v0.10.1.md for the canonical spec)

> **This section was stale from v0.5 through v0.8 (caught in the
> 2026-07-06 audit).** To prevent recurrence it now holds only the
> one-screen summary + a pointer; `model/v0.10.1.md` is authoritative.

**Formula (tide-keyed path, applied per high tide in next 24 h):**

```
water_at_342_NAVD88 = SH_peak_MLLW + 0.00 − 2.82
if peak_rain ≥ 0.1 in/hr (in [−90 min, +15 min] of the peak):
    water += 8·tanh(rate) / 12          # ft, uniform water-level rise
depth(landmark) = max(0, water − landmark_NAVD88) × 12   # inches
```

Plus, reported separately (not in the main number):
- **Wind adjustment** (v0.8): offshore peak winds → "expected actual"
  −0.13 ft line.
- **Pluvial pathway (v0.10.1 DYNAMIC TANK, refit 2026-07-18)**:
  dV/dt = 1.296e6·(R−D(bay))^0.78 − 3.50·V through the stage curve,
  with a 15-minute hillside lag —
  the series rain line is a true HYDROGRAPH (timing solved). One
  fit matches all four measured events incl. both full hydrographs
  (`model/v0.10.1.md`). Static v0.9-gamma dual models remain for
  banner scenarios + the site calculator (tanh refuted as a peak
  model by event #4; kept as labeled conservative alternative).
- **Cold-lockout**: demoted to advisory 2026-05-19; never applied.

**18 landmarks** (ft NAVD88 → SH threshold = +2.82): grate_SW 3.52 →
6.34 (first water) · grate_SE 3.60 · corner_SE/SW 3.64 · upstream
grate 3.64 (low-point; uneven to 3.78) · gutter_walkway 3.78 ·
grate_NE/NW 3.80 · corner_NE/NW 3.91 · **curb 4.16 → 6.98 (flood
onset)** · sidewalk_under_walkway_lawn_step 4.33 · road_middle 4.36 ·
intersection_highpoint 4.54 · lawn_step 4.66 · porch_step_base 4.68 ·
porch_step1_top 5.41 · porch_deck 8.08 → 10.90 (Sandy-class).

**Hurricane Sandy reference:** 13.31 ft MLLW on the 6-min product,
12.03 on hourly_height. A 12.0 on hourly IS Sandy-class.

**Calibration events**: see `data/labeled_observations.csv` (149 records
through 2026-07-18) and the per-event READMEs under `assets/observations/`.
Tape-measured anchors: 5/18, 5/31, 6/14, 6/15 (tide events, ±0.2–1.8″
at curb); Oct 30 2025 + 7/6/2026 (rain events, the pluvial-model
anchors).

---

## 4. Production architecture

**Runtime: GitHub Actions, scheduled.** No local infrastructure to maintain.

```
                       ┌──────────────────────────────────┐
                       │  GitHub Actions runner           │
                       │  (daily 09:00 UTC, ubuntu-latest) │
                       └──────────────────────────────────┘
                                       │
                                       ▼
              ┌───────────────────────────────────────────┐
              │ python3 flood_forecast_daily.py            │
              │   --write-html ../docs/index.html          │
              └───────────────────────────────────────────┘
                  │                │              │
                  ▼                ▼              ▼
            ┌──────────┐    ┌──────────┐   ┌────────────┐
            │ NOAA API │    │ NWS API  │   │ Gmail SMTP │
            │ (tides,  │    │ (rain,   │   │ (deliver   │
            │  surge,  │    │  surge   │   │  email)    │
            │  temp)   │    │  product)│   │            │
            └──────────┘    └──────────┘   └────────────┘
                  │                │              │
                  └────────┬───────┴───────┬──────┘
                           │               │
                           ▼               ▼
                    docs/index.html   inbox(es)
                           │
                           ▼
                    archive snapshot to
                    docs/archive/YYYY-MM-DD.html
                           │
                           ▼
                    git commit + push (bot)
                           │
                           ▼
                    GitHub Pages serves at
                    johnurban.github.io/barnacle/
```

**Email format:** plain text + HTML alternative. Subject line carries the
regime label (DRY / LIGHT / MODERATE / SEVERE) for fast triage in inbox.
Body lists both high tides in next 24h with the worst-case starred (text)
or highlighted yellow (HTML); landmark depths shown for the worst case.

**Site format:** mobile-friendly, color-coded regime banner, table of
both high tides with worst highlighted, landmark depth table, reference
scale, link to source and archive. Archive grows ~3 KB/day (~1 MB/year).

**Schedule:** `cron: '0 9 * * *'` in UTC. This is 5 AM EDT in summer
(the user's preferred wake time), 4 AM EST in winter. GitHub Actions
cron doesn't adjust for DST; the seasonal drift is harmless (winter
emails arrive 1h earlier than ideal, still before wake-up).

**Credentials in GitHub Secrets:**

| Secret | Purpose |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` |
| `SMTP_USER` | Sending Gmail account (currently user's personal account) |
| `SMTP_PASS` | 16-char Gmail app password from that account |
| `SMTP_FROM` | Must match `SMTP_USER` for Gmail SMTP |
| `SMTP_TO` | Recipient(s), comma-separated for multi-recipient |

When `SMTP_TO` has multiple addresses, script auto-switches to Bcc mode
("Undisclosed recipients:;" in To header, real addresses hidden in Bcc).
No code change needed to add recipients later — just update the secret.

---

## 5. Repo layout (canonical, as of handoff)

```
barnacle/
├── README.md, HANDOFF.md, LICENSE, .gitignore
├── .github/
│   └── workflows/
│       └── daily_forecast.yml    # GitHub Actions schedule + publish
├── forecast/                     # production daily forecast code
│   ├── flood_forecast_daily.py
│   ├── nws_surge_parser.py
│   └── smoke_test.sh
├── model/
│   ├── v0.10.1.md                # ★ CURRENT spec (tide + dynamic tank)
│   ├── elevations.md             # surveyed landmark elevations
│   ├── elevations.pdf
│   ├── h2m_pdf_extracts.md       # extracted key text from Borough PDF
│   ├── HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf
│   └── archive/                  # v0.1 - v0.10 specs
├── data/
│   ├── labeled_events.csv        # 6 flood events used for calibration
│   ├── labeled_observations.csv  # ongoing log of user-observed depths at landmarks (see README)
│   ├── labeled_observations_README.md  # what to record, when to act on it
│   ├── forecast_accuracy.csv     # auto-appended: predicted vs actual peak (HANDOFF 8b)
│   ├── merged_hourly.csv         # tide + met + rain joined, Sep 2025–May 2026 snapshot
│   ├── floods_by_month{,_minor,_moderate,_major,_total}.tsv
│   ├── top10_highest_tides.tsv
│   └── raw/                      # source pulls before merging
├── analysis/
│   ├── cross_ref.py              # calibration cross-reference
│   ├── rain_analysis.py
│   └── how-rain-adds.md          # rain mechanism notes
├── assets/                       # editable sources for committed binaries
│   ├── README.md                 # ★ map-annotation workflow
│   ├── map_points.csv            # 9 landmarks + extras: label/value/category/x/y
│   ├── pick_coords.py            # interactive coordinate picker (matplotlib)
│   └── render_map.py             # CSV + map_raw.png → docs/icons/map_annotated.png
├── docs/                         # GitHub Pages site
│   ├── index.html                # today's forecast (auto-replaced)
│   ├── forecast.json             # machine-readable today's forecast (auto-replaced)
│   ├── barnacle-widget.js        # ★ iOS Scriptable widget (fetches forecast.json)
│   ├── map-render.js             # client-side heat-map renderer
│   ├── tides/                    # per-tide deep-link pages (+ index)
│   ├── style.css
│   └── archive/
│       ├── index.html            # auto-regenerated list
│       ├── YYYY-MM-DD.html       # one per day, forever
│       └── YYYY-MM-DD.json       # JSON twin per day, for accuracy log + downstream
├── history/                      # historical-stats project (Claude Code)
│   ├── HANDOFF.md                # original task spec (with dashboard correction)
│   ├── RESULTS_HANDOFF.md        # ★ peer summary of what was done & found
│   ├── reports/
│   │   └── flood_history_report.md  # ★ primary report
│   ├── scripts/
│   │   ├── pull_sandy_hook_history.py   # NOAA puller (resumable)
│   │   ├── build_dataset.py             # raw chunks → hourly parquet
│   │   ├── analyze.py                   # all derived analytics
│   │   ├── mrms_point_rain.py           # ★ MRMS radar rain at the catchment (cached)
│   │   └── fit_crdt.py                  # V=C·(R−D)·T fit across rain anchors
│   ├── data/
│   │   ├── stage_storage_curve.csv      # ★ stage-storage curve (pluvial fill model)
│   │   ├── mrms/mrms_extracted.csv      # ★ MRMS extractions (committed cache; raw/ gitignored)
│   │   ├── summary_stats.json           # ★ headline numbers
│   │   ├── calibration_check.csv        # ★ 4-event validation
│   │   ├── seasonality_recent.csv       # ★ 1996-2025 8-stratum table, used in forecast reports
│   │   ├── seasonality_by_threshold.csv # full-record version (1910-2025)
│   │   ├── monthly_peak_percentiles.csv # ★ p25/50/75/90/95/99/max per month for #16e
│   │   ├── slr_trend_by_window.csv      # SLR by 4 windows
│   │   ├── return_periods.csv           # GEV return levels
│   │   ├── flood_days_per_year.csv
│   │   ├── decadal_threshold_crossings.csv
│   │   ├── annual_means.csv
│   │   ├── 342_bay_flood_events.csv
│   │   ├── (and others)
│   │   ├── raw_chunks/                  # gitignored — 1,400 monthly pulls
│   │   └── sandy_hook_hourly_history.parquet  # gitignored — 15 MB, regenerable
│   ├── figures/                  # PNG plots (return periods, decadal, etc.)
│   └── pull.log
└── attic/                        # archived dead-ends + old structure
    ├── etss_fetcher.py
    ├── dev_pre_v0.5_reorg_20260518/   # original dev/ tree
    └── superseded_handoffs/      # SEASONAL_CONTEXT_TASK.md, deploy_HANDOFF.md
```

**On `history/data/`:** the top-level CSVs and JSON are small, referenced
by the report, and tracked in git. The raw chunks (~1,400 monthly parquet
files) and the 15 MB combined hourly parquet are gitignored — they can
be regenerated by re-running `history/scripts/pull_sandy_hook_history.py`
(resumable, ~30 min wall-clock).

---

## 6. How we got here — key insights and reversals

These are the model corrections that actually moved the needle:

1. **The user's tide app shows only astronomical tide, not surge.** Every
   flood event in the dataset had +0.8 to +2.9 ft of surge on top of the
   predicted tide. *Observed* total water level is the right input,
   not forecast astronomical alone.

2. **The "antecedent saturation" theory for April 18 was wrong.** Earlier
   versions claimed April 18 flooded worse despite a lower tide due to
   ground saturation. Actually, April 18's observed tide was higher
   (7.32 vs 6.76 ft) once surge was included. No saturation needed.

3. **Oct 30 wasn't a "rain event with modest tide."** Predicted astronomical
   was 4.67 ft (modest). But surge added +2.90 ft for observed peak 7.57 ft,
   with 1.45"/hr rain landing during high tide. Three reinforcing factors.

4. **The "5.30 ft NAVD88 curb elevation" Gemini cited was a legend sample**
   in the engineering PDF, not the actual curb at 342 Bay. Real curb is
   4.16 NAVD88. This corrected the model substantially — local enhancement
   dropped from +1.5 ft (with wrong curb) to +0.4 ft (with correct curb).

5. **The intersection at Bay+Central is a local high point (4.54 NAVD88)**
   that often stays dry while surrounding road floods. Explicit landmark
   in the model now; predictions like "road covered but intersection
   still dry" match observed reality on Dec 19.

6. **Cold weather suppresses the Pathway B drain backflow mechanism.**
   Feb 22–23 had observed Sandy Hook 7.19 ft + strong onshore winds —
   should have flooded — but user (awake checking) confirmed nothing.
   Hypothesis: ice at storm drain outfalls blocks bay→street pathway.
   In the model as an override.

7. **Three independent sources converge on "minor flooding starts at
   ~6.6 ft Sandy Hook MLLW":**
   - User's empirical curb onset (4 events): **6.58 ft**
   - NWS Mt Holly Minor Coastal Flooding: **6.70 ft**
   - Sandy Hook Tidal Dashboard "Minor" (UI + count reproduction): **6.70 ft**
   All within 0.12 ft (~1.4 inches). Hyperlocal empirical agrees with
   regional NWS standards. Earlier versions of this HANDOFF documented
   the dashboard's threshold as 7.20 ft — that was wrong (likely from
   misreading static HTML fallback values rather than live JS-rendered
   values). Correcting it makes the cross-validation story *stronger*,
   not weaker.

8. **v0.4 had arithmetic errors in three threshold values** that v0.5
   corrected (road middle, intersection, lawn step). Python code was
   always correct — only the spec tables had been miscomputed. Caught
   when Claude Code's historical-statistics project flagged a
   disagreement between handoff and v0.4 spec.

9. **Single-tide reporting hid useful information.** Original script
   reported only the higher of the two daily high tides. Multi-tide
   layout (added 2026-05-18) reveals significant per-tide variation
   that affects daily planning. First real-world example: 6.19 ft
   evening vs 4.91 ft morning = 1.28 ft spread, completely hidden in
   v1 reporting.

10. **Historical-stats project confirms model self-consistency and
    reveals trend context.** Independent NOAA pull 1910–2026 (1.02M
    hourly rows) reproduced all 4 labeled events exactly, found SLR
    rate of 4.29 mm/yr (NOAA published: 4.05 — agreement within 6%),
    and confirmed Aug 21 2025 was a real elevated event (6.93 ft +
    1.4 ft surge) above the user's curb threshold. See section 7
    below for the headline findings.

11. **The +0.40 ft local enhancement is probably a storm-surge
    propagation effect, not a constant** (2026-05-18 spot-check
    event). All 4 original calibration events involved meaningful
    surge (+1.30 to +2.90 ft); the 2026-05-18 event had essentially
    no surge at peak and showed ~0 enhancement (water at 342 Bay
    tracked Sandy Hook directly, not amplified). Cleaner framing
    than earlier "magnitude-dependent" or "time-dependent"
    hypotheses: wind/pressure pushing surge into the bay drives the
    amplification at 342 Bay (near the head of the bay) relative
    to Sandy Hook (at the bay-ocean transition). Testable at next
    storm event with surge. Queue for v0.7 model spec.

12. **v0.6 has a grate elevation bug** (2026-05-18 / survey reconciliation).
    `corner_grate` is listed at 3.91 NAVD88 — but per the H2M
    Road Reconstruction Supplement survey, the NE/NW grates are
    3.80 NAVD88. The 3.91 is the NE pavement corner, a separate
    landmark. Pathway B activation threshold shifts from SH 6.33 to
    SH 6.22. This was discovered when reconciling 2026-05-18
    observations against the surveyed elevations: the observed
    water level at the NE grate matched 3.80 well, not 3.91. Fix
    queued for v0.7 (don't patch v0.6 inline; this changes a
    landmark elevation, which per the versioning rule warrants a
    bump).

---

## 6b. Historical-stats project — key findings (2026-05-18)

Claude Code's analysis of NOAA Sandy Hook hourly data 1910–2026.
Full report in `history/reports/flood_history_report.md`; peer summary
in `history/RESULTS_HANDOFF.md`.

**Headlines:**

- **Calibration**: All 4 labeled v0.5 events match historical pull values
  exactly (Apr 17: 6.76, Apr 18: 7.32, Oct 30: 7.57 + surge 2.90,
  Dec 19: 6.83). No recalibration implied.
- **SLR validation**: 4.29 mm/yr (1932–2024) vs NOAA's published 4.05
  mm/yr — agreement within 6%, validates the gauge data and processing
  chain.
- **Recent SLR acceleration**: 5.45 mm/yr post-1980 (1.35× long-term
  rate). Forward-projecting: ~0.5 ft more rise by 2055 — at that point
  today's routine 6.6 ft high tides will wet the lawn step, not just
  the curb.
- **Flood-day frequency at curb (6.58 ft) recent decades**: 38 (2010s),
  44 (2020s). Up ~15× from the 1950s baseline. (The 1910s baseline is
  too thin to use — only 7 years of usable data.)
- **100-year return level**: 10.57 ft MLLW (95% CI 9.5–11.8). At the
  curb that's ~48 inches of water from tide alone, before rain.
- **Hurricane Sandy**: 13.31 ft on 6-min product (instantaneous, the
  famous number) / 12.03 ft on hourly_height (centered average). GEV
  fit classifies as ~5000-year event — that's the fit's verdict, not a
  probability statement; treat as "black swan even by EVT standards."
- **Aug 21 2025**: Confirmed real elevated event — Sandy Hook 6.93 ft
  + 1.4 ft surge at 19:00. Above user's curb (6.58) but below lawn-step
  (7.00). User almost certainly had road water that evening if home.

**Is the flood-rate increase real or methodological?** Audited; the
trend is mostly real, with caveats:
- Gauge methodology / sampling-rate changes can't explain the trend
  (modern averaging biases peaks *lower*, not higher).
- Datum reference shifts (NTDE updates) are handled correctly by NOAA
  and produce no artifact.
- The SLR cross-validation (matching NOAA's published 4.05 mm/yr)
  confirms data and processing are sound.
- Physics works out: ~1.3 ft mean rise since 1910 makes ~10× more
  high tides cross the curb threshold.
- One genuine uncertainty: the 1980s→1990s step (6/yr → 14/yr) is
  sharper than smooth trend predicts. Could be early-acceleration,
  storm clustering (the 1993 "Storm of the Century" era), or unknown
  factor. Worth a follow-up check of `annual_means.csv` for a smooth
  vs stepped MSL trajectory.
- **Recommended framing**: cite "15× since the 1950s" (firm) rather
  than "9× since the 1910s" (thin baseline).

---

## 7. Surge investigation — what was tried, what worked, what didn't

The user is correct that surge is the single biggest information gap.
Astronomical tide is static and known years in advance; surge varies
with weather and needs forecasting. Here's everything we explored:

### What worked
- **NWS Coastal Flood product via api.weather.gov.** When NWS issues a
  Coastal Flood Warning, Advisory, or Statement for the area, the text
  includes Sandy Hook tide projections (DD/HH AM|PM + total tide MLLW
  + departure ft + flood category). We have a self-tested parser
  (`nws_surge_parser.py`) that extracts these and uses them as the
  forecast.
- **NOAA tidesandcurrents.noaa.gov API.** Works reliably. Used for
  predicted tide (now using `hilo` product for exact tide times rather
  than hourly samples), current observed surge (persistence), air temp.
- **NWS api.weather.gov gridded hourly forecast.** Works reliably.
  Used for rainfall forecast.

### What didn't work, and why
- **NOAA ETSS direct fetch from `ftp.ncep.noaa.gov`.** TCP timeout from
  Comcast-issued IP. DNS resolves fine; the route is blocked. Could work
  from a non-residential network (e.g., cloud-hosted runner) — worth
  retrying from GitHub Actions runner if always-on numeric surge becomes
  needed.
- **NOAA ETSS via `nomads.ncep.noaa.gov` (Akamai mirror).** HTTP 403 for
  both directory listings and specific files, even with browser
  User-Agent. Reachable but gated. Probably geo/auth filtering.
- **Iowa Environmental Mesonet API.** Initial URL guess was wrong.
  Their archive does exist; we didn't pin down the right endpoint.
  Retry candidate — would let us pull historical Mt Holly CFW from
  known storm dates for parser hardening without waiting for live events.
- **NWS alerts archive at api.weather.gov.** Only retains
  active + recently-expired (24–48 h). Cannot pull historical events.
- **Stevens Institute NYHOPS forecast.** Didn't investigate the AJAX
  layer behind their UI. They run an excellent operational surge model
  for Sandy Hook specifically. Retry candidate.

### Plan-B architecture (what we shipped)
Main script tries NWS Coastal Flood product first; if no active event,
falls back to "current surge persists" (today's observed surge applied
forward). This means:
- **Routine days**: surge persistence (rough but adequate when nothing
  is brewing)
- **Active coastal storm days**: NWS forecaster-vetted tide projections

Same surge information the Borough's emergency management is looking at.

---

## 8. Production deployment story

### What was built
- `.github/workflows/daily_forecast.yml` — GitHub Actions, scheduled
  daily 09:00 UTC + manual `workflow_dispatch` for testing
- `--write-html PATH` and `--no-send` flags on the forecast script
- `render_html_page()` function producing standalone HTML with proper
  `<head>`, mobile viewport, link to source repo and archive
- `docs/style.css`, mobile-friendly, color-coded regime banner
- Auto-regenerated `docs/archive/index.html` chronological list
- Bcc support in `send_email` for multi-recipient privacy

### Snags hit and resolved
- **PAT lacking `workflow` scope** blocked initial workflow push.
  User updated existing PAT to add the scope. (Token value unchanged,
  no credential re-entry needed.) Note: this scope is required any time
  a commit modifies `.github/workflows/*`.
- **`bayavebarnacle@gmail.com` couldn't generate app passwords** even
  with 2FA enabled. Likely too-new account; Google sometimes gates
  app passwords until accounts age 24-48 hours. User worked around by
  using personal Gmail for now. To switch later: just update three
  GitHub secrets (`SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`).
- **Repo restructure had stale forecast scripts** in `forecast/` after
  the setup script's `safe_mv` lookups missed deeper subdirectories.
  Caught by smoke test (`nws_surge_parser.py` not found, email body
  still showed "Highlands NJ" instead of "Bay Ave Barnacle"). Fixed by
  manual `cp` from chat outputs into forecast/.
- **Non-fast-forward push** after the bot's auto-commit. Resolved by
  `git pull --rebase origin main` before pushing local changes. User
  set `git config pull.rebase true` to make this automatic going forward.
- **GitHub Pages CDN caching** made the main URL look stale after the
  workflow ran. Hard refresh (Cmd+Shift+R) resolved. The archive URL
  worked first try because it was a never-before-visited path.

### Operational hygiene observations
- **Cron schedule won't fire for ~24h after first being on default
  branch.** Workflows merged to main don't automatically run the next
  day; they take effect day-after-tomorrow. Manual trigger
  (workflow_dispatch) bypasses this for testing.
- **The Bot commits daily.** Each scheduled run produces a "daily
  forecast YYYY-MM-DD" commit by `github-actions[bot]` touching
  `docs/index.html`, `docs/archive/YYYY-MM-DD.html`, and
  `docs/archive/index.html`. Pull-rebase before any local commit.

---

## 9. Future work (prioritized)

### High value, near-term
−1. **CRITICAL — 2026-05-18 spot-check session findings (DO NOT LOSE).**
    First real observation event after spot-check feature went live.
    Forecast: 6.19 ft at 21:58. Actual: 6.58 ft MLLW at 22:12 (NOAA
    Sandy Hook 6-min). LOW confidence flag was correct (0.87 ft
    surge swing in prior 6 h).
    **Striking finding: effective local enhancement at SH 6.58 was
    ~0 (or slightly negative), not the +0.40 the model assumes.**
    Back-solving from observations (with corrected 3.80 grate elev,
    see "v0.6 elevation bug" below): water at 342 Bay at peak was
    ~3.68-3.72 NAVD88; SH-implied baseline 3.76; implied local
    enhancement ~-0.04 to -0.08 ft.
    **Refined hypothesis (cleaner than earlier "magnitude-dependent"
    framing): +0.40 is a storm-surge propagation effect, not a
    constant.** Storm events with wind/pressure pushing surge *into*
    the bay (Apr 18: +1.30 ft; Oct 30: +2.90 ft) amplify water at
    342 Bay relative to Sandy Hook. Normal tides without meaningful
    surge — like 2026-05-18 — track Sandy Hook directly or slightly
    lag. Testable next storm event with surge: if enhancement
    re-emerges at ~+0.40, hypothesis confirmed.
    One event — do NOT recalibrate. Watch for the pattern.
    Full write-up: `assets/observations/2026-05-18/README.md`.
    Photos: distributed to 7 grate/landmark subdirectories under
    `assets/observations/2026-05-18/` (Medium-size export, ~13 MB
    total). EXIF timestamps walked; 13 observation rows appended to
    `data/labeled_observations.csv`.
    **v0.6 elevation bug surfaced (per survey PDF):**
    - `corner_grate` listed at 3.91 NAVD88 — actually 3.80. 3.91 is
      the NE pavement corner, a separate landmark.
    - Pathway B activation threshold should be SH 6.22, not 6.33.
    - Corrected map_points.csv (16 entries) has compass-named
      grates + corners + intersection_highpoint.
    Other key findings:
    - 5 grates need modeling (currently 2): grate_NE / NW (both
      3.80) / SE (3.60) / SW (~3.55-3.58, ~0.5" lower than SE) +
      grate_bay_ave_upstream (~3.76).
    - The upstream Bay Ave grate (~3.76 NAVD88, NOT in v0.6) is the
      actual primary feeder to the user's gutter at walkway, not
      the Bay+Central corner grate as v0.6 implies.
    - The "pocket" near SE grate (~3.48-3.52 NAVD88) is *post-
      overflow retention*, not a *pre-arrival* sentinel. Water can
      only reach the pocket after bay water exceeds the grate top.
      **Pocket retention is ≥11 hours** (confirmed 2026-05-19 09:33,
      water still present from prior 22:12 peak; no rain, minimal
      morning sun). **Spot-check disambiguation rule:** when arriving
      for a subsequent tide, the pocket may hold leftover water from
      a prior tide and mislead — read the **grate-slot** water level
      to determine the current bay state. Pocket residual matters
      only when the grate itself reads sub-flush; if the grate is
      also flush/over, the current tide is breaching anyway.
    - Peak time can slip 10-30 min later than the astronomical
      prediction when surge persistence is unreliable.
0. **Accumulate landmark observations in `data/labeled_observations.csv`.**
   Append-only log started 2026-05-18 for empirical "what did the user
   actually see" data at named landmarks. Used to validate the +0.40 ft
   local enhancement at the sentinel landmarks (lowest road corner across
   Bay, gutter at walkway) and the porch step — none of which are
   calibrated by the original 4 flood events. See
   `data/labeled_observations_README.md` for column layout, when to act
   on it, and how to fill in the NOAA-side fields. Don't make this a
   chore; sparse honest observations beat dense fabricated ones.
1. **Validate NWS parser against next real event.** Will happen on its
   own. When a Coastal Flood Warning/Advisory fires for Eastern Monmouth,
   run `python3 nws_surge_parser.py` and confirm it parses cleanly.
   Tighten regex if needed.
2. ~~**Add seasonal context line to email and HTML page.**~~ ✅ DONE
   (2026-05-18, multiple commits culminating in the unified landmark
   table). Stratified by 8 landmarks; recent-window (1996-2025) typical
   counts; MTD column from live NOAA pull; near-miss line; SLR-
   conditional line. See current `forecast/flood_forecast_daily.py`.
3. **Switch SMTP_USER to `bayavebarnacle@gmail.com`** once the account
   ages enough to support app passwords. Update three GitHub secrets;
   no code change. Keeps forecast emails out of personal Sent folder.
4. ~~**Refine the `lawn_step` and `porch_step` elevations via cross-fit
   from grate measurements**~~ ✅ RESOLVED (2026-07-21). The current
   surveyed/observed values are lawn 4.66 ft NAVD88, porch base 4.68 ft,
   and first porch-step top 5.41 ft. The prior values (`lawn_step` 4.58,
   `porch_step` 5.08) were originally tape-measured, and the user was
   uncertain whether
   the 4.54–4.63 range reflects survey uncertainty vs. tape uncertainty
   at the time. Either way, direct tape alone is unreliable here
   because the sidewalk and walkway slope toward the road — a tape
   reading of step height won't translate cleanly to a single NAVD88
   elevation.

   **Better method (the SW elevation refinement on 5/31 used this
   exact approach):** at any event where water visibly reaches the
   lawn step or porch step, simultaneously measure depths at the
   grates whose NAVD88 elevations are now survey-grade (NE=3.80,
   SE=3.60, SW=3.52). Cross-fit: water_NAVD88 = grate_elev + depth,
   then step_elev = water_NAVD88 − step_visible_offset. Multiple events
   converge the estimate. 6/13 + 6/14 events may already provide this
   data (6/14 hit SH 7.16 → potentially above lawn step; awaiting user
   measurement organization).

   **Backlog of related items surfaced 2026-06-14** (see
   `assets/observations/2026-06-14/README.md` "Open todos" section for
   full context):
   - Add 3 new landmarks to `assets/map_points.csv`:
     `fire_hydrant_central`, `driveway_central`,
     `cross_central_driveway` (elevations from cross-fit, not tape).
   - Add `flood_edge` category to `pick_coords.py` /
     `render_map.py` and mark the 5 edge-photo locations from 6/14
     (each edge point's location + concurrent water level → implied
     ground elevation, free topographic data).
   - Establish a permanent reference point on `grate_bay_ave_upstream`
     for future tape (low-point convention agreed 6/14; grate top is
     uneven 3.64–3.78 NAVD88 over ~1.7″).
   - Log 19 measurements from 6/14 to `data/labeled_observations.csv`
     (deferred until v0.7 spec revision discussion is settled).
5. ~~**Day-name labeling in tide times.**~~ ✅ DONE (2026-05-18).
   Format helpers `format_time_full` ("May 18, 2026: Mon 9:58 PM") and
   `format_time_short` ("Mon 9:58 PM") applied across email + HTML
   page. Full form used in worst-case detail, recent-history rows,
   GitHub Pages tide table, near-miss line; short form used in subject
   line, email tide table, spot-check times. Plain-language summary
   uses 12-hour AM/PM with relative-day phrasing ("9:58 PM tonight").
6. **Update GitHub Actions versions before June 2 2026.** Node.js 20
   deprecation in `actions/checkout@v4` and `actions/setup-python@v5`.
   One-line PR each when new majors land.
7. **Confirm or refute the 1990s discontinuity in flood-frequency data.**
   Quick check: open `history/data/annual_means.csv`, look for an MSL
   step around 1995-1996. Smooth trajectory = real SLR / storm
   clustering. Step = methodology break (worth investigating).
8. **Check if Aug 21 2025 really did flood at 342 Bay.** Historical
   data shows Sandy Hook 6.93 ft + 1.4 ft surge at 19:00 — above curb,
   below lawn step. **Tentative yes (2026-05-18):** user inspected the
   rental in August and observed swirly mud stains on the sidewalks
   around 342 Bay, consistent with a recent flood. Worth confirming
   precise depth or whether multiple events left the staining; could
   then upgrade `data/labeled_events.csv` from tentative to confirmed.
8a. ~~**Plain-language one-sentence summary at the top of the email/page.**~~
    ✅ DONE (2026-05-18, commit ffb112c). Day-aware time phrasing
    ("tonight" / "tomorrow morning"), per-regime descriptors.
8b. ~~**Forecast accuracy log.**~~ ✅ DONE (2026-05-18). Each daily run
    walks `docs/archive/*.json`, pulls actual NOAA observed peak around
    each archived forecast's predicted peak time (±2 h window), appends
    a scored row to `data/forecast_accuracy.csv`, and renders a
    one-line "Model accuracy (last N forecasts): mean error +X ft,
    mean |error| Y ft, worst |error| Z ft" in the email/page. The
    workflow's commit step now adds both `docs/` and `data/`. The
    block will be empty for the first ~1 day after the JSON archive
    starts populating; appears from day 2 onward.
8c. ~~**Rain timing detail in the daily forecast.**~~ ✅ DONE
    (2026-05-18, commit ffb112c). Cumulative 24h rain + per-tide peak
    rate + offset relative to high tide. Block is conditional — only
    shown when ≥ 0.05" of rain is expected.

### Medium value
9. **Decompose the +0.40 local enhancement.** Currently a constant; with
   8–10 more events, may correlate with wind direction / speed / pressure /
   lunar phase. Becomes a function instead of a constant.
10. **Calibrate cold-weather override threshold.** Only Feb 22–23 in the
    dataset. Several more cold-weather high-tide events would refine
    the 72-h, 32°F trigger. **Spot-check prompt now calls this out
    when conditions match** (cold-lockout active AND predicted peak
    would cross curb without it) — ✅ wired 2026-05-18. See also
    item 16 for retrospective calibration from historical data.
11. ~~**Low tide times in email.**~~ ✅ DONE (2026-05-18). New
    `fetch_tides_24h()` returns both highs and lows; a small "Low
    tides in next 24h" block in the email and on the Pages site shows
    time + level (ft MLLW). For boat-launch context see item 23a
    (Atlantic Highlands Marina Barnacle spin-off).
12. **Severity-based notifications.** Currently emails daily regardless.
    Could suppress emails for DRY days and use a separate channel (SMS,
    push) for SEVERE days. Reduces noise.
13. **Verify Phase 1 reconstruction status.** If the road has been
    rebuilt to design (4.20 NAVD88), all thresholds shift up ~0.04 ft
    (sub-inch).
14. ~~**Pluvial-only flooding test.**~~ ✅ **ANSWERED 2026-07-06 —
    emphatically yes.** Convective flash flood put ~7.3″ at the curb
    (~4.77 NAVD88) at 11:34 AM, ~1.5 h before high tide, with the bay
    more than a foot below the lowest grate throughout (rain excess
    +10 to +25″ at every one of 20 measurements). Water reached the
    bottom porch step +1–2″. NWS QPF forecast for the day was 0.0″ —
    total input miss on the convective cell — and the model
    architecture can't represent off-peak flooding anyway. See
    `assets/observations/2026-07-06/README.md` and the v0.9 agenda
    (section 9e).
15. **Borough drainage map.** Email Stephen Winters (Floodplain Admin,
    swinters@highlandsnj.gov) for the storm sewer map. Would clarify
    Pathway B outfall locations.
16. **Cold-weather override calibration from historical data.** Two
    related ideas:
    (a) ✅ **Script written + run 2026-05-19** (commits ceb518d +
        pending). `history/scripts/cold_weather_retrospective.py`
        pulled NOAA `air_temperature` for Sandy Hook, joined to the
        existing hourly_height parquet, computed 72-h rolling mean
        temp, identified **19 candidate events 2010-2026** where
        the v0.6 cold-lockout override would have applied (SH 6.58-
        8.0 ft MLLW AND 72-h mean temp < 32°F). Outputs:
        `history/data/cold_weather_candidates.csv` (19 rows) +
        `history/reports/cold_weather_retrospective.md` (table +
        year grouping + named-storm matches + suggested validation
        path). **Validation queued**: the 3 candidates from 2026
        (Jan 4, Feb 1, Feb 2) the user was there for — direct memory
        beats archive lookup. Plus the bigger pre-2026 named storms
        (Hercules 2014, Jonas 2016, Stella 2017, Grayson 2018,
        Orlena 2021) all have NWS Mt Holly storm summaries to
        cross-check. Resolution gates v0.7: if most candidates
        didn't flood → cold-lockout stays; if many did →
        threshold/ceiling needs revision.
    (b) Filter cold-snap events out of the historical seasonality CSVs.
        Counts are slight over-estimates in winter. Not currently
        advocated for filtering — but the (a) calibration would
        require building this temperature-joined dataset, which
        would also support filtering if desired.
16a. ~~**Confidence indicator in the daily email.**~~ ✅ DONE
    (2026-05-18, commit ffb112c). Color-coded banner with high/medium/
    low + reason line; auto-detects NWS active, cold lockout, peak >
    8 ft, surge swing > 0.5 ft in 6 h.
16b. ~~**Recent-history recap (last 3-7 days) in the email.**~~ ✅ DONE
    (2026-05-18, commit ffb112c). 7-day table of observed daily peaks
    with highest landmark reached.
16c. ~~**JSON/CSV archive alongside the HTML.**~~ ✅ DONE (2026-05-18).
    `flood_forecast_daily.py --write-json PATH` dumps the forecast
    dict; workflow now writes `docs/forecast.json` and archives a
    daily snapshot at `docs/archive/YYYY-MM-DD.json`. Prereq for the
    forecast accuracy log (8b).
16d. **Threshold-crossing instant alerts as a separate channel.**
    Adjacent to item 12 (severity-based notifications). Specifically:
    a one-shot SMS or push when the day's predicted peak first
    crosses LIGHT / MODERATE / SEVERE — not the daily morning email
    you'd skim, but a separate "wake up and check on the house"
    signal. Could go to a phone via Twilio, Pushover, etc.
16e. ~~**Highlight unusually-high forecasts.**~~ ✅ DONE (2026-05-18).
    analyze.py now emits `history/data/monthly_peak_percentiles.csv`
    with p25/50/75/90/95/99/max of daily peak SH MLLW per calendar
    month (1996-2025). The forecast script labels today's peak as
    top 1% / top 5% / top 10% / top 25% / above median / below median.
    A note line ("Note: today's forecast peak (X ft) is in the top
    Y% ...") appears in the email/page only when the peak is in the
    top 25% or worse — suppresses noise on routine days.
16f. **Real-time gauge link or embedded image in the page.** The
    daily forecast is a static morning snapshot. Adding a "live gauge
    at Sandy Hook" link (or embedded NOAA image) on
    `johnurban.github.io/barnacle/` would let the user verify current
    conditions against the morning prediction without leaving the
    page.

### Worth retrying later
17. **NOAA ETSS direct fetch from GitHub Actions runner.** Different IP,
    different routing. If successful, gives always-on numeric surge
    forecast — complementary to NWS products (event-only).
18. **Stevens NYHOPS API inspection.** Focused attempt to find the
    JSON endpoint behind their SFAS visualization.
19. **Iowa Mesonet historical NWS products.** Right URL pattern would
    let us pull e.g. the Oct 30 2025 Mt Holly CFW text for parser
    hardening before relying on a live event.

### Speculative / nice-to-have
20. **Probabilistic ETSS (P-ETSS) ensemble.** 21 GEFS members → spread.
    Once ETSS works, gives probability of flooding directly.
21. **Bayesian seasonality update.** Use monthly priors to flag unusual
    forecasts.
22. **USGS Total Water Level Forecast API.** Mentioned but not
    explored. Serves coastal forecasts including Sandy Hook.
23. **Multi-location expansion.** Same model architecture, different
    anchors, for neighbors. "Atlantic Highlands Barnacle." Repo named
    generically for this.
23a. **Atlantic Highlands Marina Barnacle (spin-off project).** Adjacent
    use case at the same gauge: low-tide conditions at Atlantic
    Highlands Marina determine whether boats can launch or return to
    land. If the tide drops below some threshold (TBD by boat-ramp
    geometry), launches/retrievals are blocked. Same NOAA hilo
    product, different threshold logic, different audience. Could be:
    (a) a section appended to the existing Bay Ave email,
    (b) a separate email per subscriber group, or
    (c) a separate site/repo entirely ("ah-marina-barnacle"). Option
    (b) or (c) likely cleanest as the audiences diverge. The mailing-
    list infrastructure (item 26) supports both — Google Group lets
    subscribers self-select.
24. **NJ LiDAR DEM extraction.** Currently use surveyed plan elevations.
    LiDAR would let us see full neighborhood microtopography and produce
    flood-extent maps for any Sandy Hook level.
25. **Re-pull historical data periodically (e.g., yearly).** The
    chunked puller is resumable, so refreshing the dataset to include
    new years is cheap. Could be a GitHub Actions cron job.
25a. **Lunar phase / spring-tide annotation.** Mark spring-tide days
    (full/new moon ± 2 days) in the email and on the Pages site.
    Useful framing — "this is a spring tide, expect higher than usual
    tidal range." Pure annotation, no model change. Lunar phase is
    available from `astral` or computed analytically.
26. **Self-serve subscribe flow for neighbors.** Right now `SMTP_TO`
    is a comma-separated list in GitHub Secrets, so adding a subscriber
    means editing the secret by hand. At a small scale (≤10 subscribers
    expected) that's tolerable, but a self-serve sign-up would be nicer
    for sharing. Options in rough order of effort:
    - **Mailto link on the Pages site** — zero infra, "Email me to
      subscribe" + manual add to the secret.
    - **Google Group** (e.g., `bay-ave-barnacle@googlegroups.com`) —
      create once, set `SMTP_TO` to the single group address, link a
      "Subscribe" button on the Pages site to the group's join URL.
      Google handles subscribe / unsubscribe automatically; you're out
      of the loop. Free. Probably the best fit for this scale.
    - **Managed newsletter (Buttondown etc.)** — free under 100
      subscribers, swap SMTP send for POST to their API. Embeds a
      subscribe form on the Pages site, auto-unsubscribe links,
      analytics. ~30 lines of code change. Overkill at this scale but
      cleanest user experience.

    Bcc privacy and CAN-SPAM consideration: Bcc is already handled
    (subscribers don't see each other's emails); CAN-SPAM is fine while
    the system stays free + informational with a clear way to
    unsubscribe (already automatic on Google Group / Buttondown; needs
    a "reply to remove" note in the mailto-only flow).
27. **iOS app (multi-stage plan).** Long-term goal: a proper iPhone
    app, ideally App Store distributed. Stage by stage:

    **Stage 1 — Web Clip "Add to Home Screen" (done 2026-05-18 in
    same session as this HANDOFF entry).** PWA polish: manifest.json,
    apple-touch-icon, viewport / theme-color meta tags. User adds
    the page to home screen via Safari; gets a real-looking app
    icon launcher. Zero infra, no developer account. Already
    sufficient for personal use.

    **Stage 2 — Scriptable widget** ✅ DONE (2026-05-18). Script at
    `docs/barnacle-widget.js` (served as
    `johnurban.github.io/barnacle/barnacle-widget.js`). Free
    Scriptable app from App Store; user copy-pastes the script,
    pins as a home-screen widget. Small (2x2) shows regime label,
    peak ft + time, highest exceeded landmark + depth; medium (4x2)
    adds the plain-language summary and confidence indicator.
    Widget is tappable → opens the live Pages site. Refreshes every
    ~15 min. Zero developer account. Install instructions are in
    the script header AND linked from the Pages site footer.

    **Stage 3 — PWA push notifications (1-2 hours).** iOS 16.4+
    supports push for installed-to-home-screen PWAs. Add service
    worker (`docs/sw.js`), Web Push API integration, small backend
    on GitHub Actions or Vercel/Cloudflare free tier to send
    notifications on regime crossings. Could replace or supplement
    the daily email. User must install-to-home-screen first; not
    just bookmark.

    **Stage 4 — Native iOS app (multiple sessions).** SwiftUI app
    that hits `forecast.json`. Push notifications via APNS, home
    widget via WidgetKit, fully native look. Requires Apple
    Developer Program ($99/yr, free 7-day side-load via Xcode is
    also possible). Target App Store distribution so neighbors can
    install.

    The user's vision: app starts by mirroring the existing Pages
    site, then evolves with:
    - User-customizable notification settings (toggle email vs SMS
      vs push, set threshold levels per channel)
    - Interactive charts (tide curve with predicted vs observed, rain
      timeline overlay, recent-history scrollback)
    - Per-user landmark customization (so a neighbor with different
      elevations can use the same app with their own thresholds)
    - Tie-in with future spin-offs (Atlantic Highlands Marina
      Barnacle as a separate tab or related app)

    Key prereqs already in place: the JSON archive (16c) gives any
    client direct access to the structured forecast data, so iOS
    development can begin without backend changes.
27a. ✅ **Stage 1 Web Clip (Add to Home Screen).** DONE 2026-05-18
    (commit 3bfb966). Pages site has manifest.json + apple-touch-icon
    + meta tags so iOS "Add to Home Screen" produces a real-looking
    app icon with standalone webview.
27b. ✅ **Stage 2 Scriptable widget.** DONE 2026-05-18 (commit 8c97c8f).
    Script at `docs/barnacle-widget.js`. Free Scriptable app, copy-paste
    the JS, pin as home-screen widget. Small + medium sizes, color-coded
    by regime, tappable to open the live page. **Refresh queued
    2026-05-19** (Batch 2 idea #4): widget hasn't been touched since
    its initial ship; everything 9b added (confidence band, lookahead
    spring tides, live gauge reading, accuracy/classifier signals) is
    candidate content. Pending: review what fits in 2x2 vs 4x2 vs
    larger sizes; pick a few high-value additions per size.
27c. ✅ **Map-based depth heat-map.** DONE 2026-05-19
    (commits edac47d + 5be56b5). The user expanded `assets/map_points.csv`
    from 16 pre-seeded landmarks to 52 surveyed points (intersection
    corners + grates, Bay Ave sidewalk pairs, Central Ave north all
    the way to the neighbor's house, crosswalks). `assets/render_map.py`
    grows a `--water-level NAVD88` flag that renders a smooth blue
    semi-transparent overlay using matplotlib's Delaunay triangulation
    (no scipy dep). Darker blue = deeper. Labels hidden by default in
    heat-map mode (NAVD88 numbers read as "predicted depths" against a
    depth-encoded overlay — confusing); `--show-labels` opts back in.

    Wired into the daily forecast: `flood_forecast_daily.py --write-map
    PATH` invokes `render_map.py` as a subprocess. HTML report embeds
    the resulting PNG (new "Predicted water depth" section between
    worst-case detail and rain timing). Workflow installs matplotlib +
    numpy and archives the daily map to `docs/archive/YYYY-MM-DD-map.png`.
    Cold-lockout days skip the overlay cleanly.

    **The `approximated` map-point category (added 2026-05-19).**
    `map_points.csv` `category` now has a third value:
    `landmark` / `extra` / `approximated` (+ `flood_edge` since
    2026-07-07). `approximated` points *shape* the heat-map
    surface — street-crown centerlines, curb/sidewalk/lawn boundary
    lines. Provenance clarified 2026-07-08 (user): the red `extra`
    values were read from the H2M design drawings; the amber points
    were then INTERPOLATED by the user between those anchors using
    known local gradients — anchored interpolation, not free
    guesses. Rendered amber on the base map (vs blue landmark / red
    surveyed-extra) so inferred values are never mistaken for
    direct measurements. All three categories feed the heat-map triangulation
    equally. **This is the practical mechanism for most of the
    polish items below** — rather than build geometry-aware
    interpolation, the user encodes the domain knowledge as
    approximated data points and the triangulation produces the
    structure (crown, curb step) because the data now says so.

    **Known limitations / future polish:**
    - **Convex hull edges show as straight lines.** The triangulation
      stops at the outermost survey points, so the overlay's outer
      boundary is the convex hull of `map_points.csv` rather than
      following real topography. Mitigation: add explicit "high-and-
      dry" perimeter points where the road meets higher ground (lawns,
      yards, property lines) — good `approximated`-category use case.
      (The EE phantom-point fix smooths the boundary SHAPE; real
      perimeter points constrain the flood EXTENT.)
    - **Triangulation doesn't respect barriers.** Water visually
      bridges across the user's house from the upstream grate to the
      neighbor on Central. In reality, the building blocks flow.
      Need to either (a) mask out polygons inside building footprints,
      or (b) add closely-spaced high-elevation points along building
      edges so the surface "stairs up" sharply at the wall.
    - **Curb-to-sidewalk-to-lawn step changes are smoothed out.**
      Street is lower than sidewalk is lower than lawn, but the
      triangulation interpolates linearly across those breaks. The
      sidewalk-pair points the user surveyed help, but the smoothing
      still understates the curb's containment effect. Primary
      mitigation now: dense `approximated`-category points along the
      curb / sidewalk / lawn boundary lines (the user volunteered to
      place these). A constrained-Delaunay-with-breaklines approach is
      the "proper" fix but heavy — approximated points get ~90% of
      the benefit for ~10% of the work.
    - **Colormap saturates at 2 ft depth.** A 6" event and a 2 ft
      event look different; a 2 ft event and a 6 ft event look the
      same. Intentional to keep small floods from looking dramatic,
      but means extreme events lose visual differentiation. Could
      use a non-linear depth mapping.
    - **User feedback (2026-05-19):** "Looks a little silly right
      now — but not all of it. I can see recognizable patterns like
      water building up on the street sides and more on the SE / SW
      side. And so on. Looks pretty good in that regard. Looks like
      it can be even better though." Foundation works; the polish
      items above would make it production-quality.

---

## 9b. Web platform pivot — active development direction (2026-05-19+)

After the heat-map MVP shipped (commits edac47d + 5be56b5), the next
major development direction is to turn the website
(johnurban.github.io/barnacle) into the dynamic, interactive,
sub-daily-updated face of the project, with the daily email staying as
a once-a-day summary plus optional follow-up alerts. The brainstorm
that anchored this section: `dev/ideas/20260519.txt`.

Three architectural decisions anchor the whole section:

1. **Additive, not destructive.** Every new feature *adds* to what's
   there; nothing existing gets removed without an explicit pruning
   pass later. "When in doubt, keep what we have."
2. **Client-side rendering of all map visuals.** GitHub Pages serves
   only data (JSON/CSV) and static HTML. The browser parses the data
   and renders contours in JavaScript (D3.js or similar). No PNG
   storage in git history for time-varying maps. The base map
   (`docs/icons/map_raw.png`) stays static.
3. **One number canonically describes map state.** Water level
   (NAVD88 ft) at any given moment + the static `assets/map_points.csv`
   recovers every landmark depth, regime, map visual. Storage is one
   row per prediction event, not one PNG per prediction event.

The 10 items below are the work queue, roughly in build order.

### 9b.1 — Sub-daily dynamic updates

Workflow runs hourly instead of daily. Each run updates
`docs/forecast.json` in place (and downstream HTML/CSV), and appends
to the master log (9b.3). **Never deletes prior history.**

- **Cadence**: start at every 1 hour (24 ticks/day). Slow to 2-6 h if
  hourly proves too fine. Adaptive cadence (hourly within 12 h of a
  tide, slower otherwise) deferred — we'll know if it's needed after
  watching the data.
- **Email policy**: morning email stays daily-only. A follow-up *alert
  email* lands in the same thread when intra-day regime worsens
  (e.g., DRY → LIGHT or LIGHT → MODERATE before the next morning's
  email), one-two sentences body + link to the live site.
- **Compute**: hourly is well within GitHub Actions free tier
  (~30s/run × 24 = ~12 min/day on public repos which are unlimited).
- **Storage**: text updates are cheap (overwrite same paths).
  Binary-PNG growth was the concern — 9b.10 resolves it.
- Status: ✅ DONE 2026-05-19 (commit 12b160c). Cron flipped from
  `'0 9 * * *'` to `'0 * * * *'`. Daily run (09 UTC + dispatch)
  sends email + archive snapshot; hourly runs are text-only.
- Replaces/extends: HANDOFF 16d (threshold-crossing alerts) and
  HANDOFF 27 Stage-3 PWA push (both ride on this infrastructure).

### 9b.2 — Per-high-tide as the primary unit (additive to current 24h rollup)

Currently the home page is "today's forecast" with two high tides as
table rows. Migrate to a per-tide model: each high tide is its own
object with its own evolution log + final-prediction snapshot. The
current 24h rollup table **stays** and gains:

- A **duration toggle**: 24h / 48h / longer (capped at the surge
  forecast horizon, e.g., 5-7 days; deep "next 1-2 months" view is
  9b.7 — astronomical only)
- **Severity-colored rows** using the regime palette, time-ordered
  (earliest at top)
- **Worst-case detail** auto-selects the worst row
- Worst-case row also gets the heat-map underneath (rendered
  client-side per 9b.10)

New **per-tide deep-link pages** live at `docs/tides/<tide-time>/`:

```
docs/tides/2026-05-18T22-12/
  ├── index.html        # static snapshot of the final prediction
  ├── forecast.json     # final prediction object
  └── evolution.csv     # all updates leading up to this tide's peak
```

- Per-tide pages: generated EAGERLY for upcoming tides in the rollup
  window. (Lazy generation can come later if it becomes a maintenance
  burden.)
- Old per-day archive (`docs/archive/YYYY-MM-DD.html`) keeps
  accumulating in parallel — leave it untouched. Pruning is a later
  decision once the per-tide structure has settled.
- Status: ✅ DONE 2026-05-19 in two parts. Part 1 (4532521):
  severity-colored rollup rows + per-tide deep-link pages with
  index.html + forecast.json + evolution.csv. Part 2 (c28895f):
  24h → 72h rollup window + JS duration toggle (24/48/72h).
- Depends on: 9b.3 (evolution.csv comes from the master log)

### 9b.3 — Master historical log of all predictions over time

One row per `(prediction_made_at, target_tide_time)` pair. CSV
(append-only, both JS and Python read it trivially). Schema:

```
prediction_made_at, target_tide_time,
sh_peak_mllw_predicted, water_navd88_predicted,
regime_predicted, source, confidence_band,
peak_rain_in_hr_predicted, ...
```

User's key insight: from a single row's `water_navd88_predicted` plus
`assets/map_points.csv`, every landmark depth, regime, and map visual
can be reconstructed. So storage is small even at 24 ticks/day × ~3
upcoming tides per tick.

- The existing `data/forecast_accuracy.csv` (HANDOFF 8b) is the
  degenerate one-row-per-day version of this. The new log replaces it
  for new data; the old log stays frozen as a historical artifact.
- Status: ✅ DONE 2026-05-19 (commit 1b54750). `data/predictions_log.csv`
  + `data/predictions_log_README.md`. Foundational; powers per-tide
  evolution.csv files (9b.2), the convergence chart (9b.4(a)), the
  map scrubber (9b.4(c)), and eventually 9b.8's lead-time accuracy.
- Depends on: nothing

### 9b.4 — Interactive website features

All three derive from 9b.3 + 9b.10. Build order:

**(a) Prediction-convergence plot per tide.** x = hours-before-peak
(-12 → 0). y = predicted peak (or water_navd88). One point per
prediction event. LOESS fit shows how the estimate converges as the
tide approaches. Checkboxes to include/exclude prediction-sources or
date ranges.

**(b) Water-level oscillation plot.** Line plot of predicted (and
observed, when available) water level over time. Background banded by
landmark elevation with a blue→red gradient — lowest (pocket, 3.50)
in blue, highest (first porch-step top, 5.41) in red. Reading the plot tells you
which landmarks the water has crossed.

**(c) Map scrubber + play button.** Timeline slider scrolls through
past predictions. "Play" button animates from date X → Y at N-hour
increments. Renders the heat-map client-side from each row's
`water_navd88`. Becomes nearly free once 9b.10 ships.

- Status: ✅ DONE 2026-05-19 in three parts. (a) Convergence plot
  per-tide (67c34fc) — Chart.js loads evolution.csv. (b) Oscillation
  plot on the home page (09e285a) — multi-tide line chart with
  landmark-banded thresholds via chartjs-plugin-annotation;
  curated to 5 landmarks per user feedback. (c) Map scrubber +
  play button on per-tide pages (4d177aa) — slider replays the
  heat-map across each prediction event in evolution.csv.
- Depends on: 9b.3 + 9b.10 (both shipped)

### 9b.5 — Rain in the heat-map (uniform water-level addition)

Current heat-map shows tidal-only water level. Rain-driven events
(Oct 30 2025) get visually undersold. Fix: rain raises water level by
`dZ_rain` feet uniformly across the map. Contour bands shift up by
that amount.

- **Email**: pre-render two maps via `render_map.py` (with rain,
  without rain) — keeps the existing Python pipeline alive for the
  email path. Email is the least-dynamic surface and stays
  server-rendered.
- **Website**: client-side rendering with a checkbox toggle "include
  rain" — same single number drives both states.
- This falls out naturally of model refactor 9c.4 — once the model
  itself uses a single water level, the map just reads that value.
- Status: ✅ DONE 2026-05-19 (commit dcd2242). The website renders
  TWO maps when rain is meaningful — a "Tide + rain" map (default)
  and a "Tide only" comparison — with a radio toggle. The rain
  bonus is added uniformly to the water-level surface that drives
  the contour overlay. Once 9b.10 shipped (client-side render),
  the toggle just re-renders with a different water-level number;
  no second PNG file needed.
- Replaces: per-landmark rain shedding in the v0.6 model.
- The DEPTH predictions in `predict_landmark_depths()` STILL use
  v0.6's per-landmark shedding (intersection -2", lawn/porch -4").
  Map ↔ depth-table disagreement at lawn/porch on rain days. v0.7
  9c.4 unifies both on water-is-level math.

### 9b.6 — Confidence semantics — always pair badge with what+why line

The current confidence indicator ("LOW") doesn't say what it's about,
which confused the user when a DRY day showed LOW confidence. Fix:

- Keep the badge.
- Always pair with an explicit "what + why" line:
  > Confidence: LOW — surge shifted ±0.87 ft in the past 6 h; the
  > forecast peak (6.19 ft MLLW) may differ from actual by ~±0.5 ft.
  > Regime could span DRY → LIGHT depending on which way it resolves.
- When the uncertainty band spans regime categories, state the span
  ("could be DRY through LIGHT" or "could be MODERATE through SEVERE").
- Status: ✅ DONE 2026-05-19 (commit 4cf5a4e). Badge + reason now
  paired with up-to-two italicized qualifier lines spelling out
  (a) what's uncertain (the peak SH MLLW number, ± estimated ft)
  and (b) the regime band that uncertainty implies. Uncertainty
  is currently a heuristic per band (high=±0.10, medium=±0.30,
  low=±0.50 ft); a data-driven version is queued (see N in the
  current solo-work backlog).
- Extends: HANDOFF 16a (confidence indicator) — DONE; this is
  refinement, not replacement.

### 9b.7 — Look-ahead (1-2 months astronomical)

Pull NOAA `tide_predictions` for the next 30-60 days. Surface days
with astronomical peak ≥ thresholds:

- ≥ 6.00 ft MLLW — mention in passing
- ≥ 6.20 ft MLLW — call out (gutter onset)
- ≥ 6.58 ft MLLW — call out clearly (curb at the property)
- ≥ 7.00 ft MLLW — bold warning (lawn step)

**Astronomical only.** Surge isn't forecast that far out; the caveat
must be explicit on every surface: *"These are baseline astronomical
tides; an event of significance also needs surge or rain, neither of
which is forecast this far ahead."*

- **Email**: section at the bottom listing dates / times.
- **Website**: dedicated section, updated once-daily (no need for
  hourly cadence on this view).
- Status: ✅ DONE 2026-05-19 (commit 176214d). Pulls NOAA
  tide_predictions hilo over 45 days, surfaces tides ≥ 6.00 / 6.20
  / 6.58 / 7.00 ft MLLW with progressively heavier visual weight.
  Appears in both the daily email and the website. Astronomical-
  only caveat explicit on every surface.
- Adjacent: HANDOFF 25a (lunar / spring-tide annotation — same
  calendar days, different framing).

### 9b.8 — Accuracy on the website (three modes)

Backward-looking accuracy section, subsettable by start/end dates.
Three modes:

1. **Peak-magnitude accuracy** — predicted SH peak (MLLW) vs observed
   SH peak (MLLW from NOAA 6-min). Input-stage accuracy. Plot:
   predicted vs observed scatter + |error| over time.
2. **Outcome-depth accuracy** — predicted depth at curb (inches) vs
   inferred depth at curb (from `data/labeled_observations.csv` when
   available, else from regime classification). Output-stage
   accuracy.
3. **Binary flood classification** — predicted_flooded vs
   observed_flooded where `flooded = depth at lowest grate > 0`
   (threshold configurable per view). Confusion-matrix metrics:
   false-positive rate (predicted flood, none observed),
   false-negative rate (no prediction, actual flood). Single-number
   "should I trust this?" summary.

Plus a **time-to-peak axis** from 9b.3: plot accuracy by
hours-before-peak. Does accuracy improve sharply at -3 h? -6 h?
Checkboxes for which lead-time bucket to include.

- Status: PARTIAL — modes 1 + 3 shipped 2026-05-19.
  - Mode 1 (peak-magnitude): scatter plot of predicted vs observed
    SH peak with y=x reference line (commit 42bee09). Falls back
    to text-only summary when <2 scored rows.
  - Mode 3 (binary classifier): 2×2 confusion matrix with TP/FP/FN/TN,
    accuracy, FPR, FNR; flooded threshold = SH ≥ 6.02 MLLW (lowest
    grate). Color-coded cells (green = caught/dry, red = missed)
    (commit 357a82b).
  - Mode 2 (outcome-depth) still queued — waits for
    data/labeled_observations.csv to grow.
  - Lead-time accuracy axis (using predictions_log.csv hours_until_peak)
    still queued — waits for log to accumulate.
- Extends: HANDOFF 8b (forecast accuracy log) — DONE; this is the
  visualization layer plus the three modes.

### 9b.9 — Model refactor (v0.7) cross-reference

The single-water-level math + per-landmark rain shedding removal
happens as part of the v0.7 model spec promotion. See dedicated
section **9c** below for the consolidated v0.7 roadmap.

- Status: ✅ **shipped 2026-06-15** as part of v0.7 promotion. The
  data-blocked portions remain at section 9d (v0.8).
- Forces alignment with: 9b.5 (rain map), 9b.10 (storage).

### 9b.10 — Storage refactor: no per-update binary archives

The current pipeline commits `docs/icons/map_today.png` (2 MB) on
every workflow run. At 24 ticks/day that's ~18 GB/year of git history
just for maps — not viable. Fix:

- **No more per-update PNG storage.** The browser renders maps from
  numbers (`water_navd88`) + `docs/icons/map_raw.png` (static base) +
  `assets/map_points.csv`.
- `render_map.py` **stays alive** for the email pipeline (9b.5) —
  emails can't run JavaScript, so pre-rendering is the right answer
  there.
- Existing daily archive PNGs (`docs/archive/YYYY-MM-DD-map.png`) are
  frozen — leave them; they're historical artifacts of v1.
- The map renderer code becomes a static JS module in `docs/` (e.g.
  `docs/map-render.js`), pure function of `(water_navd88, map_points)`
  → SVG/Canvas.
- Status: ✅ DONE 2026-05-19 (commit dcc8da4). New
  `docs/map-render.js` does the contouring in the browser using
  d3-delaunay (CDN) + per-triangle barycentric rasterization onto a
  2D canvas. Map and per-tide pages embed `<canvas>` + inlined
  map_points.csv data + a render() invocation. No more PNG storage
  in git history. `assets/render_map.py` remains for local
  convenience and future email-embed; the workflow no longer calls
  it. `docs/icons/map_today.png` deleted.
- Enables: 9b.4(c) — map scrubber became nearly free once render
  was client-side (shipped same day).
- **Alternative considered + rejected** (Batch 2 idea #1, 2026-05-19):
  pre-compute ~48 PNGs at 1" increments from 3.5 to 7.5 ft NAVD88
  for an interactive slider. Rejected because (a) it reintroduces
  the binary-storage problem this item just got rid of (~96 MB of
  PNGs that get regenerated every time we tune the map's look), and
  (b) the client-side render does it instantly on-demand from one
  number per slider position. Slider use case is already served by
  9b.4(c) (map scrubber) which re-runs `BarnacleMap.render()` on
  each step.

---

## 9c. v0.7 model spec (✅ SHIPPED 2026-06-15)

**Status as of 2026-06-15**: all items in this section landed in one
commit (the `v0.7 promotion` commit). The 6/14 spot-check event
disproved the piecewise enhancement heuristic that this spec
originally proposed; the shipped form is `enhancement = -0.13 ft`
constant. See the "Status update — 2026-06-14" subsection inside
9c.3 below for the data and rationale, and `model/v0.7.md` for the
canonical spec as shipped.

Consolidated view of everything bundled into the v0.7 model promotion.
Per HANDOFF section 12's versioning rule, elevation changes + formula
changes warrant a version bump.

**Status (2026-05-31): spec ready, awaiting implementation approval.**
The original "DO NOT START YET" gate was the surge-dependent
enhancement hypothesis (need ≥2 validating events). That gate is now
**met** — 2026-05-18 (SH 6.58) and 2026-05-31 (SH 6.17) both pin
enhancement at ~0 to −0.13 ft. We can ship v0.7 with a piecewise
heuristic (9c.3) and defer the fitted form to v0.8 once we have a
high-surge event.

Items the v0.7 bundle includes: **9c.1–9c.4, 9c.6, 9c.7**. The old
9c.5 (rain-term recalibration) moved to **9d.2** because we still
only have one rain-flood anchor event (Oct 30 2025), and a one-point
fit isn't a fit.

### 9c.1 — Corrected grate elevations (survey-derived + cross-fit)

Per `model/HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf`
and 2026-05-18 + 2026-05-31 cross-fit measurements:

- `grate_NE` and `grate_NW` = **3.80 NAVD88** (was 3.91 in v0.6; survey)
- `grate_SE` = **3.60 NAVD88** (survey, unchanged)
- `grate_SW` = **3.52 NAVD88** (refined 2026-05-31; previously
  placeholder 3.55–3.58. Three independent measurements across two
  events agree to within 0.05 ft — see
  `assets/observations/2026-05-31/README.md` cross-fit table)
- `grate_bay_ave_upstream` — **grate top is uneven over 1.7″ vertically;
  low point ≈ 3.64, high point ≈ 3.78 NAVD88** (refined 2026-06-14 with
  4 cross-fit cluster estimates pinning the low-point measurement spot
  at 3.640 ± 0.04 ft; 5/18 + 5/31 high-point readings give 3.74–3.78).
  Going forward, measure tape from the lowest visible point of the
  grate top (operationally meaningful — that's where water first
  overtops). For `map_points.csv`, use the low point (3.64) since
  that's the activation elevation.
- `corner_NE` = **3.91 NAVD88** — NEW landmark; the NE pavement corner,
  distinct from the grate
- `corner_SE`, `corner_SW` = **3.64 NAVD88** — NEW landmarks
- Pathway B activation threshold shifts from SH 6.33 to **SH 6.22**.

### 9c.2 — Expanded grate set

Five grates instead of two:

| Key | NAVD88 | Notes |
|---|---:|---|
| `grate_NE` | 3.80 | User's corner (was `corner_grate` in v0.6) |
| `grate_NW` | 3.80 | Across Central, NEW |
| `grate_SE` | 3.60 | Across Bay (was `lowest_sentinel_grate`) |
| `grate_SW` | **3.52** | Across Bay, diagonal; NEW; ~1.1" lower than SE (refined 5/31) |
| `grate_bay_ave_upstream` | **3.64 (low) / 3.78 (high)** | East on Bay Ave, NEW; *the actual primary feeder* of the user's gutter; grate top uneven over 1.7″ vertical span |

### 9c.3 — Storm-surge enhancement (revision pending user approval as of 2026-06-14)

#### Status update — 2026-06-14: piecewise heuristic disproven at high SH

The 2026-06-14 PM event (SH peak 7.161 MLLW) was supposed to validate
the piecewise heuristic at the high end (where the heuristic returns
+0.40). It did the opposite: 19 measurements across 5 grates at 4
time-clusters give a mean enhancement of **−0.13 ft at SH ≈ 7.13** —
**identical to the values measured at SH 6.17 and SH 6.58.** See
`assets/observations/2026-06-14/README.md` for full analysis.

The heuristic now over-predicts by **0.53 ft (~6.4″ at every landmark)
at SH 7.13.** That's the safety-bias-in-the-wrong-direction failure
mode we were trying to avoid.

**Recommended v0.7 revision (awaiting user approval before applying)**:
replace the piecewise heuristic with a constant:

```
enhancement_ft = -0.13   # 3-event mean (5/18, 5/31, 6/14)
```

This matches all 3 spot-check events (SH 6.17, 6.58, 7.13) within
measurement noise (σ ≈ 0.02–0.04 ft per event).

**Caveat I wrote at promotion time (now superseded by 2026-06-15
re-evaluation)**: I originally claimed the v0.6 rain term was
co-fit with the +0.40 enhancement and v0.7 would under-predict
rain-flood events by ~5″. **That was wrong** — a re-computation
on 2026-06-15 confirmed v0.7 actually fits Oct 30 within 0.7″ at
the curb without any rain-term refit. The +0.40 enhancement in
v0.6 was over-fit to noisy memory-based depth observations of Apr
17, Apr 18, and Dec 19 (all pre-spot-check). v0.7 under-predicts
those events by 2–8″ at curb if their reported depths are taken at
face value, but those depths weren't tape-measured. See
`model/v0.7.md` "Historical events — re-evaluated 2026-06-15" for
the full table.

#### v0.8 9d.1 implication

The original 9d.1 plan was "fit f(surge) from a high-SH spot-check."
The 6/14 data answered that question — the +0.40 hypothesis is
disproven; the answer is a constant −0.13 across SH 6.17–7.13. **9d.1
becomes much lighter: just verify −0.13 holds at SH ≥ 7.5 if such an
event comes up.** No fitting needed.

---

#### Original 9c.3 (piecewise heuristic) — kept for context

Replace the constant +0.40 ft local enhancement with a piecewise
linear function of Sandy Hook peak (SH_peak_mllw):

```
enhancement_ft(sh_peak) =
    0.00                                  if sh_peak <= 6.6
    0.40 * (sh_peak - 6.6) / (7.0 - 6.6)  if 6.6 < sh_peak < 7.0
    0.40                                  if sh_peak >= 7.0
```

**Calibration evidence (3 events — 6/14 added 2026-06-14)**:

| Event | SH_peak | n grates | Implied enh | Notes |
|---|---:|:-:|---:|---|
| 2026-05-18 22:12 | 6.58 | 5 | −0.01 to −0.13 | corrected NE elev |
| 2026-05-31 20:42 | 6.17 | 4 | **−0.13** (mean, σ=0.02) | tight cross-fit |
| **2026-06-14 ~20:00** | **7.13** | **15** | **−0.13** (mean across 4 clusters, σ=0.03) | high-SH; *contradicts heuristic* |

5/18 and 5/31 sit below the 6.6 ft pivot, so the heuristic returns 0
— matching the data within measurement noise. **6/14 (added
2026-06-14) sits at 7.13 — well above the pivot — where the heuristic
predicts +0.40 but data says −0.13. The heuristic is wrong at the
high end.** See the "Status update — 2026-06-14" block at the top of
this section for the recommended revision.

**Why the original "piecewise not just 0" rationale was wrong** (kept
for archaeology): the assumption was that the +0.40 from the original
4-event calibration would re-emerge at high SH. 6/14 directly tested
this at SH 7.13 and found enhancement = −0.13, not +0.40. The
+0.40 from the original 4 events was almost certainly co-fit with the
rain term (all 4 historical events had rain). The safety-bias
preference is honored by accepting the constant −0.13 plus an
explicit "rain term may under-predict until v0.8" caveat — not by a
ramp that was never validated by data.

### 9c.4 — Single-water-level math (replacing per-landmark depth math)

v0.6's `predict_landmark_depths()` computes depth per landmark with
ad-hoc rain shedding at intersection (-2") and lawn/porch (-4").
v0.7 replaces this with:

```
water_navd88 = sh_peak_mllw + enhancement(surge) + (-2.82)
              + dZ_rain(peak_rain_rate)
depth(landmark) = max(0, (water_navd88 - landmark.elev)) * 12
```

One water level, every depth derived from it. The per-landmark
shedding constants are removed.

**Why the shedding constants were wrong**: they conflated "water is
level across the surface" (true in connected tidal/rain-driven
flooding — the case at 342) with "this point's local micro-puddle
sheds rain faster" (a different physical model for pure-rain
isolated puddles). Combined tide+rain at 342 is always one
connected water body.

**Calibration constraint**: must reproduce the four labeled events
(Apr 17, Apr 18, Oct 30, Dec 19) and the 2026-05-18 spot-check within
their observed uncertainties.

### 9c.5 — *moved to 9d.2*

The old 9c.5 "rain term as water-level addition (recalibrated)"
content moves to **section 9d.2** because it depends on a second
rain-flood event we don't have yet. v0.7 keeps the v0.6 rain term
form unchanged (`rain_add = 8 * tanh(rate)`) so we don't shift
calibration on something we can't validate. The per-landmark rain
shedding *constants* in v0.6 ARE removed in v0.7 (that's 9c.4 —
water-is-level math; the rain still adds, but now adds to one shared
water level rather than to each landmark independently).

### 9c.6 — Drop the negative-surge clip (`max(0.0, surge)`)

`build_forecast` currently does:

```python
forecast_peak = tide_pred + max(0.0, surge)
```

i.e., the model NEVER predicts water below the astronomical tide,
even when observed surge is negative (high pressure, anti-surge
wind, etc.). Surface origin: probably a "never under-predict
flooding risk" safety bias added at some point — but it loses the
model's ability to predict negative-surge regimes at all.

User position (2026-05-19): "We should revisit max(0.0, surge). I
would need to be convinced we should not be using negative surge
values for some reason."

Status: surge_ft_predicted in `data/predictions_log.csv` IS the
raw signed surge (the clip happens only in forecast_peak), so the
data isn't lost. But the convergence chart and forecast peak DO
embed the clip. On calm days with slightly negative surge (like
today, surge ≈ -0.04 ft), the chart looks flat because the
clipping pins forecast_peak to the astronomical value.

v0.7 decision: drop the clip. Predict actual surge. Accept that
some predictions will be lower than astronomical. Pair with the
storm-surge enhancement work in 9c.3 (which also revisits surge
handling).

Related: 2026-05-19 surge bug fix (commit d67459e) — fetch_current_surge
was returning None on every run due to a zero-duration NOAA query
range; caller defaulted to 0.0. After fix, surge varies as it
should. But forecast_peak still clips it.

### 9c.7 — Rain accumulation window (before-biased, not symmetric)

**Current behavior.** For each high tide, `build_forecast` takes
`peak_rain_rate = MAX(quantitativePrecipitation.value)` over the NWS
hourly buckets falling within a **symmetric ±90 min window** around
the tide peak (`flood_forecast_daily.py` ~line 1224). It's a windowed
peak *rate*, not an accumulation, and it's keyed to the tide time, not
the prediction time.

**Problem (user, 2026-05-20).** Rain that falls *after* the high tide
cannot raise the water level *at* the peak. The symmetric window can
pick a purely post-peak bucket as the "peak rate" and overstate the
rain contribution to that tide. For any timepoint of interest (high
tide or otherwise), only rain *before* that point should count.

**v0.7 decision — before-biased window.** Replace the symmetric ±90 min
window with `[timepoint − 90 min, timepoint + 15 min]`. The small
forward tolerance is deliberate: our tide-time accuracy is not exact,
and observed flooding has lagged the predicted high-tide time (e.g.
one recent event flooded within the 30 min *after* the predicted
peak). A +15 min default is a reasonable compromise; +30 min is
defensible. The point is to bias the weight to *before* the timepoint
while not discarding rain that effectively coincides with it.

NWS QPF nuance: buckets are hourly accumulations stamped at the
*start* of the hour. A bucket stamped 40 min before the peak still
covers ~20 min after it. The before-biased window keeps such
straddling buckets and only drops the buckets that are entirely
post-peak — which is the actual correction wanted.

**Open question — is 90 min of window enough, and should we be
tracking accumulation vs. peak rate?** This open question moves to
**9d.3** because it needs labeled rain events to answer and travels
with the rain-term recalibration in 9d.2. Summary: it's not clear
whether a fixed window captures enough rainfall, and the same rain
depth produces different flooding depending on antecedent moisture
(dry ground vs. already-wet ground). See 9d.3 for the full
discussion.

---

## 9d. v0.8 model spec (✅ SHIPPED 2026-06-16)

Same-night promotion after the 2026-06-15 PM storm-condition event
where v0.7 (enhancement −0.13) under-predicted by 1.3″ structural /
3.5″ operational at curb. The 6/15 event provided exactly the
high-surge + onshore-wind data point we'd been waiting for. The
sub-items below describe the v0.8 scope as shipped — including the
NEW wind-direction adjustment, which wasn't in any prior plan
because we didn't have the calibration data for it.

See `model/v0.8.md` for the canonical spec and
`assets/observations/2026-06-15/README.md` for the full event
analysis.

### 9d.1 — Storm-surge enhancement: high-SH sanity check (scope changed 2026-06-14)

**Original goal (now obsolete)**: fit `enhancement = f(surge_ft)` from
a high-SH spot-check, replacing v0.7's piecewise heuristic.

**What happened**: the 2026-06-14 event provided the high-SH data
point (SH peak 7.161, 19 measurements, 5 grates). Implied enhancement
came back at **−0.13 ft, the same as 5/18 and 5/31** — directly
contradicting both the +0.40 hypothesis and the v0.7 piecewise
heuristic. See 9c.3 status update and
`assets/observations/2026-06-14/README.md`.

So the original storm-surge-amplification hypothesis is essentially
disproven across the SH 6.17–7.13 range: enhancement is constant at
~−0.13, not a function of surge or SH magnitude.

**Revised v0.8 scope for 9d.1**: just verify the constant holds at
even higher SH (SH ≥ 7.5). If a spot-check there also gives ~−0.13,
the picture is closed and 9d.1 is done. If enhancement starts to
diverge at very high SH, revisit the constant-vs-functional choice
with the new data.

**Data needed**: one spot-check at SH ≥ 7.5 with multi-grate
measurements. Not blocking other v0.8 work; opportunistic.

### 9d.2 — Rain term: verify at lower rain rates (scope reduced 2026-06-15)

**Re-evaluation 2026-06-15**: the v0.6 rain term (`8·tanh(rate)`)
applied as a uniform water-level rise (v0.7 water-is-level math)
actually fits Oct 30 2025 within 0.7″ at the curb. The rain term
*magnitude* is well-calibrated at peak rate 1.45 in/hr. So 9d.2 is
no longer a wholesale recalibration — the existing form may already
be right.

The remaining open question is whether the saturating form is right
at lower rain rates. Dec 19 2025 (SH 6.83, 0.44 in/hr peak,
~7–9″ observed at curb) does NOT fit v0.7: predicted 0″ vs
observed 7–9″. Either Dec 19 was misobserved (memory artifact;
pre-spot-check) OR the rain term needs more weight at modest rates
OR Dec 19 was a storm-condition event (real enhancement we can't
model). Cannot distinguish without measured storm/rain data.

**Data needed**: tape-measured rain-flood events spanning a range
of rain rates (especially 0.3–0.7 in/hr) and antecedent moisture
conditions (pairs with 9d.3).

**Pairs with 9d.3** — the rain term's functional form and the
window definition should be re-fit together once we have data.

### 9d.3 — Antecedent-moisture handling + accumulation vs. peak rate

**Open question (user, 2026-05-20)**: is a 90-minute window enough
rainfall accumulation? The Oct 30 2025 event suggests a ~90 min
window may suffice, but the *same* rain depth can produce very
different flooding depending on **antecedent conditions**, and it's
genuinely unclear which direction dominates:

- A flash downpour onto otherwise-dry ground after 24 h of no rain:
  dry soil/pavement may not absorb water fast enough, so runoff and
  ponding could be *worse* than expected.
- The same rain depth after 24 h of lighter rain: the ground is
  already wet/saturated, less infiltration capacity left — runoff
  could also be *worse*.

So a short fixed window may miss the antecedent-moisture signal
entirely. v0.8 should at least consider: (a) whether the rain term
should be driven by *accumulated* rain over the window rather than
the peak hourly *rate*, and (b) whether a longer "antecedent"
lookback (e.g. prior 24 h cumulative) belongs as a separate term
feeding a soil-saturation / infiltration factor.

**Data needed**: multiple rain-flood events at 342 Bay spanning a
range of antecedent conditions. We won't be able to disentangle (a)
vs. (b) without a few events.

### 9d.X — Open bucket

(v0.8 shipped 2026-06-16; new items now accumulate in section 9e.)

---

## 9e. v0.9 agenda (seeded by the 2026-07-06 pluvial event)

The 2026-07-06 flash flood (see
`assets/observations/2026-07-06/README.md`) answered HANDOFF item 14
— heavy rain floods 342 Bay with zero tidal contribution — and
exposed the two failure modes that define the v0.9 work:

### 9e.1 — Pluvial prediction pathway (the architectural gap)

The model predicts only at high-tide timestamps. The 7/6 flood peaked
~1.5 h before high tide; no version of the current architecture could
have flagged it regardless of inputs. v0.9 needs a rain-driven
prediction path with sub-daily timing.

**Candidate unifying frame** (from the 7/6 + Oct 30 contrast):
flood level ≈ f(rain input rate, drainage capacity(bay level)).

- 7/6: bay LOW → drains working → flood tracked rain input; abated
  within ~30 min of rain slowing even against an incoming tide.
- Oct 30 2025: bay HIGH (SH 7.63) → drains blocked → same rain class
  stacked on top of the tide → biggest flood on record.

The existing tide+rain term and pure-pluvial flooding are plausibly
two limits of that one model. If the same convective cell from 7/6
had landed at a 7+ ft tide, we plausibly get another Oct 30.

**THE PHYSICAL LESSON (user, 2026-07-06 evening — remember this):**
above a certain rain rate, flooding here is a variable completely
independent of tide height. The mechanism is CATCHMENT-AMPLIFIED
OUTLET SATURATION — two factors, not one: (a) the ~200-ft bluffs
directly above funnel the ENTIRE hillside's rainfall downhill onto
this low shelf within minutes, so the local rainfall rate understates
the actual water input by a large multiple; (b) the drain system has
a fixed discharge capacity. When the amplified inflow exceeds the
outlet, water backs up at the low corner and "acts as if it's a
high tide" — even at dead low tide (proven 7/6: ~7″ at curb, bay a
foot below the lowest grate). The tide cannot gate a rain flood; it
can only raise its floor (compound = Oct 30 2025 class). Corollary
for all model/UI work: never let a low tide read as "no risk" when
burst-capable rain is forecast. Stated in plain English on the site
("How flooding works here").

**REFINEMENT (user, 2026-07-07): "independent" is two claims, one
right and one needing care.** OCCURRENCE is independent — rain can
flood at any tide (stands as stated). DEPTH is NOT — it is
base level + rain volume pushed through the **stage-storage curve**:
as depth rises, the inundated area grows, so each additional inch
needs more volume. "Tidal depth + X inches of rain" is therefore
wrong arithmetic; rain landing on an existing tide flood adds fewer
inches than the same rain at low tide. This is exactly why the 7/6
rain lift (1.25 ft, narrow street bowl) exceeded Oct 30's (~0.5 ft,
riding a high tide across the whole flooded plain).

**Stage-storage curve COMPUTED (2026-07-07)** from the 96-point
heat-map elevation surface (`history/data/stage_storage_curve.csv`,
0.1″ steps): wet area at curb stage (+8″ vs SW grate) is ~13× the
area just over the grates (+2″); at lawn-step stage (+14″) it's
~35×. I.e., an inch of rise at lawn-step level takes ~35× the water
volume of an inch at grate level. Caveats: relative units (map
pixels, not ft²); surveyed region only, so a LOWER bound above
~+16″ where real flooding extends past the mapped area (7/6 went 3
driveways up Central); ignores storage inside the drain network.

**IMPLEMENTED 2026-07-07 (v0.9-beta pluvial)**: the volume-fill
model replaced the two-regime closed form in
`estimate_pluvial_water()` the same day — rain volume
(`V_K·tanh((rate−D)/1.2)`) fills the stage-storage curve from the
tide-set base. Two-source principle: bay = infinite reservoir →
tide stays level-driven (tide-keyed path untouched); rain = finite
source → volume-filled. **Head-dependent drainage added same
session (user directive)**: D is not constant — full 0.25 in/hr
with the bay below 3.0 NAVD88, linear ramp to zero at 3.52 (grate
tops = outfall backwatered); fixes the Oct 30 drain double-count.
Parameter honesty (user-corrected wording): V_K is the ONLY fitted
parameter; 0.25 is a judgment number (weak brackets, V_K partially
absorbs its error); 1.2 is a placeholder (Michaelis–Menten a
candidate replacement); 3.0 knee is a placeholder (drainage map
would refine). Validation: 7/6 exact (calibration); Oct 30 5.24 vs
obs ≥5.25–5.27; **Dec 19 4.51 vs landmark band [4.36, 4.54] —
inside, with zero additional fitting** (the event every prior
version failed on). Discontinuity gone. Alpha form retained as
fallback if the curve CSV is missing.

**v0.9-gamma (2026-07-07 evening, user directive: "keep the tanh
model and add the power-law runoff model, and report both")**: TWO
input models share the drainage + stage-storage machinery. POWER
(primary): `V = K_pow·net^γ`, self-calibrated from the curve at
load — γ = 0.914, K_pow ≈ 412k — fitted to ALL THREE anchors in the
model's input space; fits each at least as well as tanh. TANH
(co-reported): the beta form unchanged, the saturating alternative
— NOT a fallback (the alpha closed form remains the only true
fallback, used solely if the curve CSV is missing). The pair agree
within ~1″ in the calibrated range (0.4–1.7 in/hr net) and diverge
in extrapolation (+3.4″ at a 3 in/hr low-tide burst, +6.1″ at 4) —
the Sandy question — so surfaces report the spread as model
uncertainty. Wiring (all additive): series `pluvial_navd88`
(primary, drives combined line + windows) + `pluvial_navd88_tanh`;
`pluvial_risk.potential_low_tide_navd88` (primary) + `_tanh`
sibling; site-chart + widget band top = the HIGHER of the two;
advisory banner scenarios print [min–max] brackets. Same session:
equation-widget section relabeled as the TIDE-KEYED math + new
"rain pathway" plain-English subsection; accuracy section gained a
scope note (it scores gauge-space as-run forecasts, append-only,
never recomputed under new models; pluvial skill tracks against
labeled_observations instead); depth-slider readout initializes in
the active unit (was stuck at "ft NAVD88" until first interaction);
curb landmark relabeled "Curb TOP at walkway"; equation widget
defaults to SW grate with regime pinned to the curb. Site-wide
staleness audit (user request): "Sandy Hook peak over time" note
rewritten (was v0.7-era claims), outcome-depth accuracy note now
flags its rows as as-logged v0.7-era history (append-only, not
current skill), cold-advisory text de-garbled + advisory-status
noted, module docstring un-v0.4'd, heat-map extra-rain slider runs
the REAL pluvial pathway with a power-law/tanh toggle (was legacy
8·tanh bump), and the term-by-term section gained an interactive
rain-pathway calculator (JS/python parity verified on all three
anchors).

**Empirical validation route (user proposal, 2026-07-07)**: the
event time series (7/6 has 20 points; 5/31, 6/14, 6/15 have
multi-grate sweeps) encode depth-rise deceleration. Normalize/align
the series (user suggests dynamic time warping) and fit the
dh/dt-vs-stage curve; compare against the geometric curve above.
Honest caveat: observed dh/dt confounds input-rate variation with
geometry — with ~5 series, DTW risks overfitting; grows feasible as
events accumulate. The geometric curve is the prior; the time
series test it.

**v0.9-alpha SHIPPED same-day (2026-07-06 evening)**:
`estimate_pluvial_water(rate, bay)` — two-regime closed form:

```
base = max(bay_water, 3.52)              # street bowl bottom
drains functional (bay < 3.52): lift = 1.40 · tanh(rate / 1.2)
drains blocked   (bay ≥ 3.52): lift = 8 · tanh(rate) / 12   # v0.8 term
```

Fits 7/6 (4.76 vs obs 4.77 at an ASSUMED 1.7 in/hr burst — the free
parameter, since observed rain rate is unknown) and Oct 30 (5.41 vs
obs ≥ 5.25). Surfaced as scenario estimates in the pluvial banner
(burst-at-low-tide + burst-at-worst-high-tide), NOT as a regime
change — the tide-keyed architecture is unchanged. Known wart: the
two regimes are discontinuous at bay = 3.52 (free-drain lift exceeds
blocked-drain lift; defended by bowl-vs-plain geometry in the code
comment, but a proper stage-storage curve should replace it in v0.9
final). Also needed: observed rain rate for 7/6 (Rutgers/NJDEP
records) to pin the 1.7; sub-daily *timing* still unsolved.

### 9e.2 — Rain input beyond QPF (PARTIALLY DONE 2026-07-06 same-day)

**Root cause found — it was our bug, not (only) a QPF miss.** The
NWS `forecastHourly` periods no longer carry
`quantitativePrecipitation` at all (verified live: 0 of 156 periods
have it); our code read that field → always None → **rain was
silently 0.0 in every production run ever**. The user's iPhone
showing rain all week while our forecast said 0.0 is what exposed it.

**Fixed same-day**: `fetch_nws_qpf()` pulls QPF from the raw
gridpoint endpoint (`forecastGridData` →
`quantitativePrecipitation.values`, mm over ISO-8601 intervals),
expands to hourly in/hr buckets. Per-tide rain windows + cumulative
24h rain now use it. Verified live: cumulative 0.74″, nonzero
per-tide rates, banner firing.

**Also added: pluvial flood-risk banner** (first deliverable of
9e.1). Categorical advisory (`possible` / `elevated`) triggered by
peak QPF rate ≥ 0.30 in/hr, OR PoP ≥ 60% + thunderstorm/heavy-rain
wording (convective), OR cumulative ≥ 1.0″ (or ≥ 0.5″ with PoP ≥
70%). Renders on the home page (amber banner) + text email +
`pluvial_risk` field in forecast.json. Honesty note baked into the
banner: QPF's ~6-h buckets smear convective bursts (7/6's
flood-producing cell averaged 0.09 in/hr in QPF), so the PoP +
wording triggers carry the weight for cells. Thresholds are
first-guess; calibrate as pluvial events accumulate.

**Analog scaling added (same day, user proposal)**: the burst
estimate driving the scenario depths now scales off the forecast
magnitude — burst ≈ 1.7 × (max_6h_QPF_accum / 0.55″), clamped to
[QPF peak rate, 3.0], where 0.55″/1.7 is the 7/6 anchor. The ratio
absorbs QPF's convective smearing AND the Highlands-hillside
catchment amplification (rain on the ~200-ft hill drains to this
low corner), because both are baked into the anchor event. This is
MOS-style / analog forecasting with n=1 anchor — every archived
forecast.json (pluvial_risk + QPF fields) + every observed rain
event grows the training set for a proper fit.

**MRMS pipeline WORKING (2026-07-07) — the 7/6 burst is now
MEASURED, not inferred.** `history/scripts/mrms_point_rain.py`
pulls gzipped GRIB2 from the Iowa State mtarchive
(`mtarchive.geol.iastate.edu/YYYY/MM/DD/mrms/ncep/…`): PrecipRate
(2-min instantaneous, EVEN minutes only) and
MultiSensor_QPE_01H_Pass2 (gauge-corrected hourly). Decoding needs
xarray+cfgrib+eccodes (pip into the venv works; eccodes wheels
bundle the C lib). 7/6 result at the house point: peak 2-min rate
**2.95 in/hr @ 11:12 ET** (hill-box max 3.06), ~2 in/hr sustained
11:04–11:20, hour ending noon 0.94″, storm total 1.60″; measured
water peak 11:34 = **~20-min catchment lag** behind peak rain.
Catchment math checked absolutely: bowl fill to +15.4″ ≈ 5.9″
rain-equivalent over the peak footprint vs 0.45″ fallen during the
rise → **≥ ~13× hillside amplification** (lower bound). This
unlocks the explicit rate×duration form V = C·(R−D)·T (C now
fittable) and, later, MRMS-based nowcasting ("cell inbound").

**ALL THREE rain anchors on measured forcing + full event-day sweep
(2026-07-07 follow-up).** Caching added after archive 404 storms
(the mtarchive load balancer intermittently 404s files that exist):
raw GRIB2 → `history/data/mrms/raw/` (gitignored), every extracted
value → `history/data/mrms/mrms_extracted.csv` (committed; doubles
as permanent cache — reruns never re-download).
- **Oct 30 2025 measured**: burst 14:40–15:05 ET, peak 2.71 in/hr
  at 14:50 — **4 minutes before the 14:54 tide peak**; hill-box max
  4.18 in/hr (strongest cell measured over the catchment to date).
  Worst-case-timed compound, on record. (Logged "1.45 peak hourly"
  ≈ MRMS hourly 1.19 — good log.)
- **Dec 19 2025 measured**: 1.83 in/hr spike at 07:00 ET, then
  steady 0.2–0.45 through the 08:12 observation (~0.85″ in 3 h).
- **V = C·(R−D)·T fit** (fill volume from the stage curve vs
  integrated MRMS net input, hand-chosen rise windows): C = 614k
  (7/6) / 449k (Oct 30) / 210k (Dec 19) cell-units. Order-stable —
  all ≫ the ~95k-cell footprint, so amplification is confirmed in
  every event — but NOT constant: **C grows with rain intensity**
  (light rain partly soaks into the hillside; violent rain runs off
  wholesale — intensity-dependent runoff coefficient). Implication:
  constant-C linear is not the upgrade path, and Michaelis–Menten
  (saturating) bends the WRONG way for hillside delivery at these
  intensities; a threshold/power-law runoff fraction is the better
  candidate. The tanh proxy stays serviceable meanwhile (V_K
  calibrated at the violent end; all three events fit in stage
  space). Caveats: n=3, 10–20-min sampling, Dec 19's base was
  tide-moving.
- **Every OTHER event day is MRMS-dry** (< 0.02″ every pulled
  hour): 5/18, 5/19, 5/30, 5/31+6/1, 6/14, 6/15+6/16 (tape-measured
  tide events — the −0.13/0.00 wind-split calibration is
  unconfounded by rain); **Apr 17+18 2026 dry → rain does NOT
  rescue the 2–8″ under-prediction vs memory depths, strengthening
  the inflated-memory interpretation** (landmark-anchor lesson);
  Aug 21 2025 dry (tide+surge only); Feb 22–23 2026 dry (cold
  no-flood mystery stays cold/wind, not rain-masked).

**7/6 anchor validated (same evening, web sources)**: NWS
flash-flood warning reported 1.5–2.5″ fallen by 11:02 AM at the
Bayshore with Sandy Hook explicitly named; radar-estimated rates up
to 3 in/hr over the Monmouth corridor (heaviest south of Highlands —
Neptune/Deal/Oakhurst; a BJ's roof collapsed at 11:15 AM); NWS
messaging cited 2 in/hr. The model's fitted 1.7 in/hr burst sits
mid-band → upgraded from "bare invention" to "consistent with
observed regional rates." Exact rate over the 342 catchment still
wants MRMS gridded data.

**Still open**: radar nowcast (MRMS) for both nowcasting and pinning
the 7/6 point rate; Rutgers mesonet RABCH022 as an *observed*-rain
input; more events → replace one-anchor linear scaling with a fitted
curve (logistic or nearest-neighbor analog lookup).

### 9e.3 — Drainage asymmetry: tide floods vs. rain floods (observed 7/6)

Different spatial signatures, first documented during the 7/6
drain-down (1:05–1:12 PM):

- **Tide floods**: water enters via SE/SW grates first (lowest
  openings, 3.52/3.60 — backflow surfaces there) and those areas
  stay wettest.
- **Rain floods**: NE/NW side dominates late-stage. The NE grate was
  **jetting water upward** (pressurized outflow) while the SW grate
  was accepting inflow and the SE grate sat inactive; the north side
  of Bay took on water while the south side drained.

User's hypothesis (verbatim in the event README): the NE grate sits
on/near the main trunk line toward the outfall; converging forward
drainage pressurizes it. Predicts rain floods persist longest around
NE/NW; tide floods around SE/SW. Cross-reference item 15 (borough
drainage map request) — the map would confirm the trunk topology.

### 9e.4-adjacent someday-project — local flood reanalysis (added 2026-07-06)

The 116-year gauge record contains NO local flood history: it's
tide-only, 4 miles away. Each historical event's local water at 342
is only bounded below (tide floor via the transform); every storm's
rain boost is unrecorded, and pluvial-only floods are entirely
invisible to the gauge (7/6/2026 registered ~6.0 — unremarkable).
The user's spot-check log is, as far as we know, the first local
flood record this corner has ever had.

**Project**: join historical hourly precipitation (Newark/coastal
stations reach back to ~mid-century; NJ climate archives) to the
tide record and run the compound/pluvial model over the century →
*modeled* local water per event with stated error bars. Would (a)
produce an honest local ranking to replace tide-only floors, (b)
flag candidate historical pluvial events the gauge never saw, and
(c) stress-test the rain term against many storms. Inherits all
model uncertainty; label accordingly. Not scheduled — parked here.

### 9e.4 — `lawn_step` elevation revision candidate: 4.58 → ≈ 4.67

Two independent anchors at 7/6 11:43–44 (NE grate → 4.654, sidewalk
→ 4.659, agreeing to 0.005 ft) coincided with the user's observation
"water approximately level with but just under the lawn step" →
lawn_step top ≈ 4.67 ± 0.02, not the 4.58 placeholder (whose 4.54–
4.63 inferred range was already flagged unreliable in item 7.4).
Corroborated by the 7/6 peak (4.77 → ~1″ over the step, matching
"reached the bottom porch step and went up it 1–2″").

Hold for one clean tide-flood anchor at the step edge (tide floods
are more reliably level) before changing the model constant. Also
needs: pin down what the `porch_step` 5.08 landmark actually refers
to (base vs. top of first step) — the 7/6 "bottom porch step + 1–2″"
at 4.77 implies the step base is ~4.6–4.7, well below 5.08.

**CLOSED 2026-07-06 (v0.9 promotion)**: user taped the porch risers
(`assets/porch-measurements.txt`) and the full ladder shipped in
v0.9 — lawn_step 4.66, porch_step_base 4.68, porch_step1_top 5.41,
porch_deck 8.08. Fictitious porch_step 5.08 removed. Details below
kept for provenance.

**Refinement (7/6 evening, photo-timeline interpolation +
user's ordering constraint)**: photos added two anchors — 11:21
porch base DRY with water level with the lawn step; 11:26 porch base
holding 0.5″. User constraint from watching in real time: porch base
is STRICTLY higher than lawn-step top (water visibly "climbs" the
walkway; it doesn't spill straight across). Constrained fit:
**lawn-step top ≈ 4.66–4.67; porch-step base ≈ 4.68; walkway rise
≈ ¼″ (0.1–0.5″)** — user's 1–2″ verbal gradient revises to ~¼″.
Peak water bounded to [4.77, 4.84], most likely 4.78–4.80 (11:34
reading may have missed the crest; the "2″ at most up the step"
memory caps it).
`porch_step` 5.08 was never measured — v0.5.1 estimated it as
lawn_step + 6″; Oct 30's ≥ 5.19 peak reconstruction suggests it
corresponds to ~the top of the first step. **User has offered to
tape the porch riser heights (each step, bottom → deck) — that plus
the 4.33 sidewalk anchor rebuilds the entire vertical ladder and
closes 9e.4.**

---

## 10. Outstanding open questions

- **Did Aug 21 2025 actually flood at 342 Bay?** Historical data confirms
  Sandy Hook reached 6.93 ft + 1.4 ft surge at 19:00 — above the curb
  threshold (6.58), below the lawn step (7.00). User likely had road
  water if home. Worth confirming from memory or photos.
- **Is the +0.40 ft local enhancement truly constant across conditions?**
  Fits 4 events to ±0.05 ft, but those events are similar (moderate
  surge, similar wind). Historical pull can't probe this; would need
  weather data joined to surge-residual analysis. Probable ±0.05 ft
  scatter based on visible event spread.
- **Does the rain term saturate at 8 inches as `tanh` assumes?** Only
  Oct 30 and Dec 19 sample the rain regime meaningfully.
- **Does cold-weather override apply to a single overnight freeze or
  only sustained below-freezing periods?** Only one observation.
- **The 1980s→1990s flood-frequency step (6/yr → 14/yr) — real or
  methodological?** Sharper than smooth trend predicts. Could be SLR
  acceleration onset, storm clustering, or unidentified data factor.
  Quick check: `history/data/annual_means.csv` for MSL step at the
  same time.
- **Does the Hurricane Sandy hourly_height of 12.03 ft mean the GEV
  fit's "5000-year event" classification is wrong?** The 13.31 ft
  instantaneous value would push the fit higher. Worth a re-fit using
  6-min product maxima if you ever want a more defensible return-period
  statement.

---

## 11. Practical immediate next steps

System is in production. Nothing is blocking. The big features added
2026-05-18 (unified landmark table, plain-language summary, confidence
indicator, rain timing, recent recap, low tides, JSON archive,
accuracy log, unusual-forecast flag, spot-check callouts) are all
live. Suggested cadence:

1. **Each morning**: glance at the email. Triage by subject line; only
   open if regime is anything other than DRY. Watch the new "Confidence"
   line — when it's LOW, also peek at NWS directly.
2. **When the spot-check section flags a CALIBRATION OPPORTUNITY**
   (pluvial-only or cold-lockout), actually go look. Those days are
   the high-information-value days for the model.
3. **When a coastal flood event happens**: run
   `forecast/nws_surge_parser.py` once during the event to verify it
   parses the live NWS product cleanly. Paste output if it fails.
4. **In ~24-48 hours**: retry generating an app password from
   `bayavebarnacle@gmail.com`. When successful, update three GitHub
   secrets to move email sending off personal account.
5. **Weekly-ish**: check
   [johnurban.github.io/barnacle/archive/](https://johnurban.github.io/barnacle/archive/)
   to confirm daily runs are accumulating archive entries cleanly.
   The accuracy line should start appearing in emails ~2 days after
   the first JSON archive (2026-05-19+).
6. **Monthly-ish**: review the accuracy log
   (`data/forecast_accuracy.csv`) for any systematic bias. Mean error
   consistently positive = model over-predicts; negative = under-predicts.
   Worth investigating if either drifts beyond ±0.1 ft over many rows.

### Next-session feature picks (in priority order)

The four high-value items most worth picking up in the next session:

a. **v0.6 model spec promotion** (HANDOFF upkeep rule). Move the
   v0.5.1 + v0.5.2 in-place additions to a new `model/v0.6.md` since
   they added 4 new landmarks. Archive `model/v0.5.md` to
   `model/archive/`. Update HANDOFF section 3 + spec cross-references.
a. **HANDOFF item 16d — SMS/push alerts.** Twilio (text messaging
   API, ~$0.0075 per SMS, requires phone number provisioning) or
   Pushover (one-time $5 app, free API, sends to your phone) for
   moderate/severe-only events. Twilio is general-purpose; Pushover
   is hobbyist-friendly. Pushover probably the simpler choice.
b. **HANDOFF item 16f — live NOAA gauge embed on Pages site.** NOAA
   has direct image URLs for the Sandy Hook gauge plot. Drop one
   `<img>` tag in `render_html_page()`.
c. **HANDOFF item 16 (cold-weather retrospective).** Pull historical
   air-temperature data, join to hourly water-level, find past
   high-tide events that would have crossed the curb but had
   72-h mean temp < 32°F. Check whether flooding was reported / not
   reported. Builds calibration without waiting for new events.
d. **HANDOFF item 27c — Map-based heat map of water depth.** New
   addition this turn. See item below.

---

## 12. Voice notes for future Claude conversations

For when you come back to a fresh chat with this document:

- **The system is in production.** Don't propose changes that risk
  breaking the daily loop without explicit testing. The smoke test
  (`forecast/smoke_test.sh`) is the safety net for major refactors.
- **The model is small.** Don't over-engineer. Five constants, three
  inputs, one formula. Everything else is plumbing.
- **The user has done the hard part** — empirical event labeling and
  elevation reading from engineering plans. Trust those numbers.
- **Surge handling is the open frontier.** NWS Coastal Flood products
  are the lowest-friction good-enough source; everything else is worth
  trying but not blocking.
- **The user is technically capable and has good taste.** Long
  explanations of basic stuff aren't needed; offer trade-offs and let
  them choose.
- **"The barnacle" as a project voice / mascot is intentional.** Use it.
- **The repo is reorganized.** Old paths (`dev/highlands_floodwatch/...`)
  no longer exist except as `attic/dev_pre_v0.5_reorg_20260518/`.
  Canonical paths in section 5 above.
- **When sources disagree, latest model/v0.{N}.md wins** (currently
  v0.6). Earlier versions (v0.5, v0.4) had arithmetic errors and
  partial landmark sets; archived for history under model/archive/.
  Python code is canonical alongside the latest spec.
- **The bot commits daily.** Always pull-rebase before pushing local
  changes. User has `git config pull.rebase true` set; safe to use
  bare `git pull`.
- **Sandy Hook dashboard uses 6.70 ft Minor, not 7.20 ft.** The 7.20
  number was a mistake in earlier docs from misreading static HTML
  fallback values. Live dashboard UI and underlying flood-count
  computation both use 6.70 ft (matching NWS standards).
- **The historical-stats project is complete** (`history/` in repo).
  Headline outputs in `history/reports/flood_history_report.md` and
  `history/RESULTS_HANDOFF.md`. Headline numbers in
  `history/data/summary_stats.json`. SLR is real (~4 mm/yr long-term,
  ~5.45 mm/yr post-1980); flood-frequency increase is mostly real
  (15× since 1950s on firm ground; "9× since 1910s" rests on thin
  baseline data).
- **Sandy 2012 is 13.31 ft instantaneous / 12.03 ft hourly_height.**
  Don't conflate these. Forecasts on hourly products that hit 12.0+
  IS Sandy-class.
- **Active development direction (2026-05-19+) is the web platform
  pivot in section 9b.** Email is intentionally the *least* dynamic
  surface going forward — once-daily summary plus optional alert
  follow-ups in the same thread. The website
  (johnurban.github.io/barnacle) is where sub-daily updates,
  interactivity, and historical scrubbing live.
- **Additive, not destructive.** When uncertain whether to keep or
  remove an existing feature/section while building something new,
  KEEP IT. Pruning is a deliberate later pass. The user's words:
  "let's do additive development, and pruning later."
- **One number describes map state.** `water_navd88` at a given moment
  + `assets/map_points.csv` reconstructs every landmark depth, regime,
  and map visual. Don't store rendered binaries (PNGs); store the
  number and re-render on demand (client-side for the website, via
  `render_map.py` for the email). See section 9b.10.
- **v0.7 shipped 2026-06-15** (commit + push completed). The 6/14
  spot-check event disproved the originally-planned piecewise
  enhancement heuristic at high SH; v0.7 ships with `enhancement =
  -0.13 ft` constant (3-event mean). Section 9c is the spec history;
  `model/v0.7.md` is the canonical as-shipped spec. Section 9d (v0.8)
  remains data-blocked: 9d.1 (sanity-check at SH ≥ 7.5) +
  9d.2 (rain-term recalibration, needs second rain-flood event) +
  9d.3 (antecedent moisture). Open bucket for new items.

---

### Upkeep rules (added 2026-05-18)

These four documents live in lockstep with the project and should be
updated in the same commit as the change that necessitated them:

1. **`HANDOFF.md` (this file)** — update whenever:
   - A section 9 future-work item is implemented (mark ~~done~~ ✅
     with date + commit ref, leave the item body for context)
   - A new future-work item is added
   - Section 4 (files inventory) or section 5 (repo layout) changes
   - The model itself changes (sections 3, 5, 6, the elevations table)
   - The deployment infrastructure changes (section 8)

2. **`model/v0.6.md` (or its successor)** — update whenever:
   - LANDMARKS, LOCAL_ENHANCEMENT, MLLW_TO_NAVD88, or any constant
     changes
   - The formula or pathway structure changes
   - Labeled events table changes
   - **Versioning convention:** *real* model changes warrant a version
     bump (`v0.7.md`, `v0.8.md`, …), not inline sub-revisions. Reserve
     same-version edits for typo/wording corrections, not new
     landmarks or formula changes. (v0.5 → v0.6 promotion happened
     2026-05-18 when the 9th landmark was added; v0.5 inline patches
     from earlier the same day were also folded into v0.6's canonical
     spec at the same time.)

3. **`data/labeled_observations.csv`** — append a row whenever the user
   reports an observation. See
   `data/labeled_observations_README.md` for column format. Don't
   rewrite past rows; the log is append-only.

4. **Annual analytics refresh** — once a year (e.g., January) re-run
   `history/scripts/analyze.py` to regenerate the seasonality /
   percentile / event CSVs with the most-recent window. Also a good
   time to re-run `history/scripts/pull_sandy_hook_history.py` to
   pull the new year's data and rebuild the parquet. Update
   `history/reports/flood_history_report.md` numbers if doing a
   thorough refresh.

---

## 13. Cold-start pointer — last work was 2026-05-19 (long session)

If you're a fresh Claude coming in after compaction: the
**web platform pivot** (section 9b) shipped in one long session on
2026-05-19. Plus several follow-up rounds based on user feedback.
**All of section 9b is now shipped or queued explicitly.** Site at
[johnurban.github.io/barnacle](https://johnurban.github.io/barnacle/)
should be visibly transformed from the morning's version.

### What shipped 2026-05-19

**Section 9b — Web platform pivot** (all DONE):
- 9b.1 — Hourly cadence (`'0 * * * *'`). Daily 09 UTC = full run
  (email + map + archive). Other hours = text-only.
- 9b.2 — Severity-colored rollup rows + per-tide deep-link pages
  + 24h/48h/72h duration toggle.
- 9b.3 — Master predictions log at `data/predictions_log.csv`
  (append-only; one row per prediction event per tide).
- 9b.4 — Three interactive features: (a) convergence chart per
  tide, (b) oscillation chart on home, (c) map scrubber on
  per-tide pages.
- 9b.5 — Rain in heat-map via uniform water-level addition +
  tide-only toggle.
- 9b.6 — Confidence semantics — pair badge with what+why line +
  regime band; self-calibrating from accuracy log when ≥3 rows.
- 9b.7 — 1-2 month astronomical look-ahead with spring-tide marker.
- 9b.8 — All three modes (peak-magnitude scatter, outcome-depth
  table, binary classifier matrix) + lead-time accuracy axis.
- 9b.9 — Cross-references v0.7 model refactor (see section 9c).
- 9b.10 — Client-side map render via d3-delaunay; no PNG storage.

**Cleanup + UX polish** (also 2026-05-19):
- R: removed dead `map_url` params from `render_html_page`.
- S: v0.7 FIX-IN-v0.7 comment on per-landmark rain shedding.
- P: HANDOFF lockstep — all 9b items marked DONE with commit refs.
- T: Per-tide page prev/next navigation.
- V: Last-updated indicator + amber when >2h stale.
- W: Open Graph meta tags for link previews.
- X: `history/scripts/cold_weather_retrospective.py` written +
  the user ran it. 19 candidate events identified.
- Y: Live NOAA gauge sparkline on home page (24h).
- Z: Lunar phase / spring-tide annotation in look-ahead.
- M, N (mode 2 + self-calibration above).
- FF: scrubber and convergence chart linked on per-tide pages.
- CC: per-tide log status block.
- DD: workflow-health banner (>3h amber, >24h red).
- EE: heat-map boundary smoothing (phantom NAVD88=6.0 points) +
  256-entry color lookup table.
- Widget refresh: hours-to-peak, confidence ±, next-watch date,
  cold-conditions hint (`docs/barnacle-widget.js`).
- **Oscillation chart axis fix**: now plots actual SH MLLW
  observation, not model-inferred 342 NAVD88.
- **Interactive depth slider** on the home page heat-map:
  3.0-7.5 ft, ~0.6" step, "Snap to current forecast" button.
  Renders client-side via `BarnacleMap.render()` on each input.
- **Per-tide page discoverability**: rollup-table time-column
  links now obviously clickable (blue + arrow); worst-case
  detail section gains "View this tide's full detail page →".

**Big model decision** (2026-05-19, commit 88d1f54):
**Cold-lockout demoted from active override to advisory.** The
v0.6 rule that forced predicted depths to zero when 72-h mean
temp < 32°F + SH peak in [6.58, 8.0] is no longer applied. The
19-event historical retrospective + web cross-check on the 5
named-storm candidates (Hercules 2014, Jonas 2016, Stella 2017,
Grayson 2018, Orlena 2021) showed ~3 of 5 likely flooded
despite conditions being met. Single Feb 22-23 2026 calibration
point may be an outlier. A yellow advisory banner now appears
when cold conditions are met, with a link to
`history/reports/cold_weather_retrospective.md`. v0.7 will either
add a wind-direction condition or drop the rule entirely.

Read these for context if needed:
- `assets/observations/2026-05-18/README.md` — first spot-check
  event surfaced the **storm-surge enhancement hypothesis**: the
  +0.40 ft enhancement is probably a storm-surge propagation effect,
  not a constant. v0.7 9c.3 ships a piecewise heuristic from current
  data; v0.8 9d.1 will fit a proper functional form once we have a
  high-surge spot-check event.
- `history/reports/cold_weather_retrospective.md` — full
  19-candidate analysis, web evidence, decision, and the
  wind-direction refinement hypothesis (NNE/N onshore winds
  correlate with the candidates that likely flooded).
- `data/predictions_log_README.md` — schema of the master log.
- `dev/ideas/20260519.txt` — user's brainstorm (Batch 1 + 2)
  that anchored everything in this session.

**Known v0.6 bugs — all fixed in v0.7 (shipped 2026-06-15):**
- ~~`corner_grate` elevation: 3.91 → 3.80~~ ✅ v0.7 renamed to
  `grate_NE` with correct 3.80 elev.
- ~~Per-landmark rain shedding disagrees with heat-map~~ ✅ v0.7
  uses single-water-level math everywhere; shedding constants removed.
- Cold-lockout rule remains demoted to advisory (HANDOFF 9b cold-
  lockout work). v0.8 may revisit with wind-direction condition or
  drop entirely.

### Two important workflow gotchas

1. **The hourly workflow appends to `data/predictions_log.csv`
   between checkout and commit.** Local commits that touch the
   log will conflict with the bot's appends. Always:
   `git pull --rebase --autostash` (or stash → rebase → unstash)
   before pushing local commits.
2. **The cold-weather retrospective script's `--write-report`
   flag is OFF by default** so reruns don't clobber the curated
   report. The CSV at `history/data/cold_weather_candidates.csv`
   IS always overwritten — it's a pure derived view.

### Where to look on the live site

- **Home page**: `https://johnurban.github.io/barnacle/`
  - Top: last-updated indicator, workflow-health banner when stale
  - Plain-language summary + confidence + regime band
  - Live NOAA gauge sparkline (past 24h)
  - Heat-map + depth slider (3.0-7.5 ft NAVD88) + "Snap to
    current" button + rain-toggle (when rain forecast)
  - Oscillation chart (SH peak over time + landmark thresholds)
  - 72h rollup table with severity colors + duration toggle +
    clickable per-tide deep-links
  - Worst-case detail with "View detail page →" link
  - Accuracy section (peak-magnitude scatter + outcome-depth
    table + lead-time bucket table + binary classifier matrix)
  - 1-2 month look-ahead with spring-tide markers
- **Per-tide pages**: `docs/tides/<YYYY-MM-DDTHH-MM>/`
  - Linked from each row of the home-page rollup table
  - Tide-specific heat-map
  - Time scrubber (slider replaying past predictions)
  - Convergence chart (LOESS over prediction history)
  - Landmark depth table
  - Evolution CSV + log-status block
  - Prev/next tide navigation in header

### ⚡ NEXT-FLOOD PLAYBOOK (the likely next session — user works
### event-driven; written 2026-07-08 for a cold start)

**During the event (user, phone in hand):**
1. Spot-check per the evolved protocol: notes-only tape readings,
   landmark-anchored (which landmark, inches above it), timestamped,
   fast cadence; mainly NE grate + sidewalk-under-lawn-step wall.
   Even "no water" observations are calibration data.
2. Photos are documentary: flood EXTENT (wet/dry lines!), drainage
   behavior (grate jetting), timestamps matter more than framing.
   Every wrack-line photo = a future `edge_YYYYMMDD_*` map point.

**In the session after (Claude, cold start) — follow this RECIPE
in order; every step has been needed at least once:**
1. Read `model/v0.10.1.md` + HANDOFF §§1–3 + 9e; memory has the rest.
2. **Gauge sanity FIRST** (2026-07-09 lesson: the SH sensor spiked
   to 11.87 MLLW during the storm — instrument, not water):
   pull the 6-min series for the event window AND The Battery
   (8518750) for the same window. If SH shows swings ≥1 ft per
   6 min that Battery doesn't echo → malfunction; interpolate the
   bay base across the garbage and SAY SO in the README.
   `_despike_gauge()` (median-window, in the forecast script)
   protects production reads — do NOT hand new gauge-reading code
   paths into production without routing through it.
3. Convert notes → NAVD88 profile: water = landmark_elev +
   inches/12 (elevations in `model/elevations.md`). Cross-check
   two landmarks where sweeps overlap (they should agree ±0.05 ft).
4. Log observations → `data/labeled_observations.csv` — **append
   PLAIN TEXT lines only; the file has legacy unquoted commas and
   csv.DictWriter TRUNCATES it** (happened 2026-07-09; recovered
   from git). Write the event README per prior events.
5. Pull rain forcing. Recent event (<~24 h): NCEP real-time
   `https://mrms.ncep.noaa.gov/2D/PrecipRate/` (2-min frames).
   Older: Iowa mtarchive via `history/scripts/mrms_point_rain.py`
   (cached CSV committed; archive 404s transient — retry).
   venv: `python3 -m venv`, pip xarray+cfgrib+eccodes (rebuild if
   Homebrew bumped python — it broke once).
6. Score the model BOTH ways and keep the two scores separate:
   (a) what the day's forecast SAID (archived day_max fields) vs
   the measured peak — that's forecast skill; (b) what
   `estimate_pluvial_water(true_rate, true_bay)` produces — that's
   model physics. Rate convention: ~1-h-equivalent sustained rate
   (a 30-min burst at 3.4 ≈ 2.5 hour-equivalent); duration is not
   yet explicit in the model (V = C·(R−D)·T is the queued upgrade).
7. **MAKE THE PLOTS — standard practice (user request 2026-07-09),
   save to `assets/observations/YYYY-MM-DD/analysis/*.png`:**
   (1) event hydrograph: rain-rate panel above, water panel below —
   measured street water + despiked bay + raw gauge if it
   malfunctioned + landmark lines; (2) model-test: both model
   curves at event bay level vs the measured-peak band; (3) refresh
   the all-anchors comparison. Style = the site chart grammar:
   y in inches-vs-SW-grate, landmark palette (black grate / green
   gutter / red curb / purple lawn / brown porch), NO dual axes
   (stack panels), legend + selective annotations. Template code:
   the 2026-07-09 session (plots in that event's analysis/).
8. Map: add `edge_YYYYMMDD_*` rows (flood_edge, `~` + that event's
   peak, empty x/y) → user clicks via `assets/pick_coords.py`.
9. Update in the SAME commit family: event README, model doc if
   constants/verdicts move, HANDOFF, memory. Republish the site if
   inputs were poisoned (local run: forecast/ →
   `python3 flood_forecast_daily.py --write-html ../docs/index.html
   --write-json ../docs/forecast.json --no-send`).
10. **Git discipline during live weather**: the hourly bot is a
    second committer. Never `git add -A`; after any pull check
    `git stash list` + `grep -rl '<<<<<<<' data/ docs/`; log-file
    conflicts resolve by UNION of both sides, never ours/theirs.

### ✅ SHIPPED 2026-07-17 (tiers 1+3): observed overlay on the
### water chart — tier 2 deliberately deferred

Extend the home-page water chart ~12 h into the past. THREE HONESTY
TIERS (refined with user 2026-07-09 late — "without my measurements
we can't do a true observed" is true ONLY for the rain pathway):
1. OBSERVED BAY line (despiked 6-min gauge → 30-min resample,
   gray solid): a TRUE observation, and by proven grate-coupling
   (7/9 measurement) + level-driven tidal flooding it is genuinely
   observed street water for the TIDE pathway. Always available.
2. AS-PREDICTED-THEN pluvial (faded dashed, reconstructed from
   archived runs / predictions_log): the ACCOUNTABLE default for
   the past rain side — after an event, the gap between this line
   and a tape diamond IS the visible miss. Do NOT substitute a
   best-estimate hindcast here; that papers over the failures the
   chart exists to show. (User also open to rain SHADING for the
   past window, as the burst band does for the future — acceptable
   alternative rendering of tier 2.)
3. TAPE DIAMONDS from labeled_observations — sparse ground truth,
   outranks both lines where present (reuse _today_lookback /
   _flood_peaks_chart_data patterns).
Optional tier 4 (later): MRMS-driven model hindcast, explicitly
labeled "reanalysis" — for unmeasured events; never silently
replaces tier 2. Same grammar: now-line separates observed from
forecast; observed gray, predicted blue. Rationale: the same
amnesia problem the 'SO FAR TODAY' line fixed, but on the curve —
after event #4 the chart showed a placid forecast while the street
had just been under 19 inches.
SHIPPED (2026-07-17 late): series extends 12 h back; tier 1 =
OBSERVED bay line (despiked gauge, gray, stops at now) attached to
series points as observed_navd88; tier 3 = tape diamonds from
labeled_observations, snapped to series slots; today_* fields now
FUTURE-only (the SO-FAR lookback owns the past); widget chart
slices back to its classic −2 h window (v7.17b). Tier 2
(as-predicted-then pluvial reconstruction) DEFERRED with user
approval ("or just keep what the most recent prediction was") —
the chart note says the past model lines are the CURRENT model's
view and past rain floods can exceed them.

### ★ DESIGNATED NEXT MODELING SESSION (user, 2026-07-09 post-v0.10):
### MRMS NOWCASTING — the input is now the ONLY weak link

v0.10 settled the physics (tank hydrograph, one fit, four events);
event #4 proved the remaining failure mode is INPUT: QPF forecast a
0.74 in/hr analog burst while 5.53 in/hr fell (7×). NWS alerts +
analog floors are stopgaps. The fix is reading MRMS PrecipRate in
near-real-time (NCEP feed, ~2-min frames, proven decodable in this
repo) inside the hourly bot: "cell inbound over the catchment"
→ feed OBSERVED rates into the v0.10 tank → the site's hydrograph
becomes a nowcast with ~15-min physical lead time (the catchment
lag) plus radar advection lead. Sketch: fetch latest frames each
run; if hillside-box rate > threshold, run the tank forward on
observed+persisted rates; surface as a NOWCAST line/banner distinct
from QPF-based forecast. Bot cadence (~hourly, throttled) is the
constraint — consider a lightweight separate 10-min Action for
rain-active periods only.

### Email/SMS policy (2026-07-17, user directive)

NO MORE daily-morning email — it trained the user to ignore it.
Event-driven only: every delivery-capable hourly run evaluates the
alert without side effects, attempts each configured channel
independently, and acknowledges `last_sent_*` in
`data/alert_state.json` only after at least one channel confirms
success. A total delivery failure remains eligible for retry on the
next run; `--no-send` and `--dry-run` never alter alert state. ntfy
push, SMTP email, and the legacy email-to-SMS gateway are isolated so
one failure cannot block another. Alerts fire when flood risk APPEARS
(rank 0→>0), ESCALATES above the last delivered rank, or a genuinely
new same-rank event signature appears. The 24-hour cooldown applies
only to the same signature at the same/lower rank. Ranks:
street/possible=1, light=2, moderate/elevated=3, severe=4 (max of 72h
tide regimes + pluvial level). Subject prefixed [ALERT]. Manual
workflow_dispatch = --force-email (test path). The 09:00 run keeps
map-regen + archive duties only. NEXT QUEUED SESSION (user): chart
observed-overlay (three honesty tiers, spec above).

### Model gap logged 2026-07-18 (user field insight, mid-storm):
### ANTECEDENT WETTING — the tank is memoryless about the hillside

User, watching a 20-min pulse die on the ebb just off a neap high
(bay ~2.2 NAVD88 — below the drainage knee even AT high tide that
day): "slowing down does
not mean it's over — it is still priming the conditions for a
flood." Physically right, and the tank can't represent it: K is
fixed, so a burst on a soaked catchment is treated like a burst on
a dry one. What a first pulse actually does: raises the hillside
runoff fraction (soil wetting), fills pockets/micro-storage (7/18:
pockets full, street dry), charges the drain network. Type
specimen: 7/13 — morning pulse, hours of lull, evening rain on the
PRIMED catchment → +19.5″. The MRMS cross-event C-variation is
consistent with antecedent state as a hidden variable. Candidate
fix (needs events to calibrate): antecedent-precip multiplier on K
(e.g., trailing-6h rain scales K within a bounded range), or a
proper two-layer soil reservoir feeding the tank. Collect: every
double-pulse event is a calibration pair.

### EVENT #5 (2026-07-18) — see assets/observations/2026-07-18/
### README for the full record; v0.10.1 shipped same evening

#2 all-time (+19.9" on rain alone, ebbing neap). k_out measured
3.50/h from the clean recession -> v0.10.1 refit, validation
improved. Six structural insights queued in the README's "Model
consequences" (priming, bidirectional drains, tilted recession,
recirculation, delivery tail, swale) — these are the next model
session's menu, alongside MRMS multi-product forensics for the
radar-underread window (PrecipRate vs QPE vs neighboring products,
15:10-15:30 ET). Autonomy shipped: nowcast day-max memory + SO-FAR
source (c) "modeled (live radar)" — floods now self-report with
nobody home.

### Other likely sessions (refreshed 2026-07-08)

1. **Pluvial input model, next iteration (9e.2)** — candidate
   replacement for the tanh proxy: intensity-dependent runoff
   fraction (threshold/power-law — NOT Michaelis–Menten, which
   saturates the wrong way; the MRMS C·(R−D)·T fit says C GROWS
   with intensity). Needs event #4+. Also open: MRMS nowcast
   ("cell inbound" beats QPF for bursts); pluvial burst TIMING
   (the 7/6 ~20-min catchment lag is the first timing constant);
   Sandy-data saturation test (pre-2014, so Stage IV / gauge
   archives, not MRMS).
2. **Drainage map** — user emails Stephen Winters
   (swinters@highlandsnj.gov); would refine the head-dependent
   drainage knee (3.0 placeholder) + confirm the NE-trunk-line
   hypothesis.
   **Free alternative (user question 2026-07-09): the falling-tide
   stall experiment.** Grate-throat readings track the bay (with the
   −0.13 offshore offset) as long as the drain network is
   backwatered — every reading to date, down to SH 5.71 / bay 2.89
   (7/9 measurement), is consistent with COUPLED. On a calm dry day,
   take 3–4 throat readings across a falling tide: the level where
   the throat STALLS while the gauge keeps falling = the network's
   hydraulic control elevation (outfall/invert), i.e. the floor of
   bay-coupling AND the physically-correct drainage knee. Caveat
   for rainy-day readings: a draining pipe carries a flow gradient
   that confounds the bay-offset interpretation.
3. **Local flood reanalysis** (someday) — join historical precip to
   the tide record; modeled local water per event over the century.
4. **Passive collectors**: high-SH event ≥7.5 (enhancement
   extrapolation), cold-conditions events (cold-lockout hypothesis;
   Feb 22–23 confirmed rain-free by MRMS), NWS surge-parser
   first-event validation, accuracy-log confidence calibration.
5. **Housekeeping**: SMTP migration (Gmail account aging); annual
   seasonality refresh; DTW stage-curve validation as event
   time-series accumulate.

**State as of 2026-07-08 (end of the two-day post-flood sessions)**:
v0.9 live and green with the v0.9-gamma dual pluvial pathway
(power-law γ=0.914 primary + tanh co-reported, head-dependent
drainage, stage-storage fill); all three rain anchors on
MRMS-measured forcing (7/6 burst 2.95 in/hr, ≥13× catchment
amplification, ~20-min lag; Oct 30 burst 4 min before tide peak;
Dec 19 inside the landmark band); every other observed event day
MRMS-dry (tide calibration unconfounded; Apr 17/18 memory-depth gap
NOT rain); site fully current (dual-model reporting, rain-pathway
calculator, Sandy-range depth slider 11.6 NAVD88, depth-bands
shading DEFAULT with classic blue optional, per-point provenance
documented: red=PDF, amber=user interpolation, teal=dated event
marks); map complete (all 18 landmarks + stations + 6/14 edge marks
user-clicked); repo + memory staleness-audited. Working tree clean,
all pushed.

**Evening session 2026-07-07 (iOS/responsive + peaks-chart build):**
- Site responsive pass (iOS Chrome = WebKit; NO UA sniffing):
  scrollable tables, -webkit-text-size-adjust, 16px inputs,
  stacked slider rows, canvas legend/title scale with canvas width.
- "Sandy Hook peak over time" joined the chart grammar, then evolved:
  PER-TIDE observed squares (from predictions_log tide list + the
  shared observed-peaks cache) with faded "as predicted ~24 h ahead"
  halo circles — nearest logged run within 16–36 h; the square↔halo
  gap is the per-tide forecast error, on the home page. Convention
  chosen deliberately (matches the daily-email promise; last-minute
  predictions would flatter, mixed leads wouldn't compare).
- NEW "Flood peaks at 342 Bay — past & forecast (all pathways)"
  section beneath it (kept side-by-side; single-user A/B, keep/retire
  later): continuous TIME axis + local units; measured flood peaks
  from labeled_observations auto-plot as orange diamonds at their
  ACTUAL times (7/6 renders at 11:34 AM +15.0″ — the rain flood a
  per-tide axis cannot represent); day-wide navy dashes = archived
  burst risk (no honest clock time in the daily archive — it holds
  the day's LAST run); rain-burst compound-potential triangles on
  QPF-horizon future tides (dual-model max; SH-equivalent caveat).
- BUG FIXES: NOAA preliminary-feed spike rejection in
  _fetch_actual_peak_around (a phantom 12.48 ft "peak" on calm July 4
  had poisoned observed_peaks_cache AND the lead-time accuracy
  stats; neighbor-agreement filter, ±12 min within 0.3 ft); chart
  aspect-lock crush; phantom-elevation + '~'-value parser fixes from
  earlier in the day stand.
**2026-07-20 → 07-21 window (twin-run repair + glance-first UX
redesign):**
- INFRA: the 02:00 UTC double cron fire made two runs rebase into
  each other INSIDE the commit step (`pull --rebase --autostash ||
  true` swallowed a conflict AFTER the gate) → conflict markers
  shipped in forecast.json, widget "incorrect format", brick-looped
  runs. Repaired origin, then three-part hardening: workflow
  concurrency group (no twin runs), forecast/heal_tree.py self-heal
  at start (unions predictions_log, deletes marked/unparseable
  artifacts), commit-first→rebase→GATE→push retry loop (gate always
  re-runs after a rebase; conflict = abort publish).
- lst_ldt TZ-family sweep ("fix every bug you find"): station-local
  bounds fixed in fetch_observed_recent (observed line was cropped —
  user-caught), fetch_surge_swing_6h (confidence had been inflated),
  fetch_recent_history; two hardcoded +4h conversions (wrong every
  winter) → proper STATION_TZ astimezone. Alert links cache-busted
  (?a= minute param) after user hit the CDN pre-alert page race.
- DAY-SCOPING: pluvial_risk.risk_today + headline_for(scope=) killed
  today/tomorrow contradictions; then DAY CARDS — 3 calendar-day
  boxes (TODAY heavier, id=today-block keeps nowcast override;
  per-day tide rows "Tue 2:35 AM", star on 72-h peak, rain line from
  alert onset/ends; ▲ WORST OF 72 H ribbon) absorbed the old
  24h/72h boxes. forecast.day_outlook exports per-day
  {tide_flood, tide_rank, rain_risk} so the widget never re-derives.
- MULTI-PAGE: landing ends at heat-map+windows; details.html carries
  how-flooding / reference scale / 10-worst / model / spot-check /
  accuracy / glossary behind "For more information" links. Peaks
  charts deduped: all-pathways DEFAULT, tide-only behind a toggle.
- GLANCE-FIRST: series chart is now the TOP of the page; alert
  emails open with a CID-embedded matplotlib PNG of the same chart
  (matplotlib pip-installed in workflow).
- MAP: time-scrubber drives the heat-map through the series
  (burst-potential view DEFAULT ON — user: "0 interest in
  non-flooding tide levels"); ladder-context wording in title +
  readout; thumbnail mini-chart overlay (default ON) with
  scrub-synced ball, burst band, black zero, midnight dashes, fixed
  now-line. Spasm bug was label-length reflow resizing the slider
  track under the finger (user diagnosed it) — CSS reserves the
  label its own line; plus __renderSeq guard + rAF throttle + slider
  floor 1.5.
- WIDGET v7.21a: WORST-72H block → "72H — OUTLOOK" (Tidal flood /
  Rain flood day-name lines from day_outlook + next high tide);
  confidence "LOW ±0.50" line dropped (user: never useful, widget is
  at-a-glance). User must re-copy widget source into Scriptable.
- TIDAL DATUMS (8e5558a8): official Sandy Hook epoch-1983-2001
  datums (NAVD88 = 2.82 ft MLLW — validates the project constant);
  TIDAL_DATUMS constant; details reference-scale table in all three
  frames (MLLW / NAVD88 / vs-grate, MLW −74″ · MSL −45″ · MHW −17″ ·
  MHHW −13″) with SLR-since-epoch caveat (~+0.4-0.5 ft today);
  always-on dashed lines on the live-gauge chart; primary chart gets
  a "Show tidal datums" checkbox (default OFF, persisted, hidden
  datums stay out of the legend, y-floor stretches to −78″).
  DEFERRED (user): later choose ONE datum line for the widget and
  the map-overlay chart versions.

**2026-07-21 audit remediation — Phase 1 (Codex implementation,
Claude Fable 5 review):**
- Fixed the four/five-hour lead-time bug that relabeled the UTC clock
  as Eastern time. All NOAA `lst_ldt` tide parsing and lead-time math
  now routes through `ZoneInfo("America/New_York")`; the prediction
  logger no longer hardcodes EDT. Historical prediction rows remain
  as-run history; the previously missing final-four-hour samples
  cannot be reconstructed and begin accumulating only after this
  cutover.
- Fixed TODAY fields borrowing tomorrow's overnight maximum by
  bounding the forward scan to the station-local calendar date.
- Fixed the nowcast gauge query that used a UTC runner clock as
  `lst_ldt` and therefore silently returned the hard-coded 2.8-ft
  fallback. The nowcast now reports `bay_source=observed`; if the
  gauge is unavailable it uses flagged astronomical tide rather than
  granting maximum drainage. If neither source exists, nowcasting
  publishes an explicit unavailable heartbeat instead of a fake
  level.
- Added offline regression coverage for EDT, EST, both DST
  transitions, local-day scoping, UTC-runner NOAA query bounds, and
  the astronomical fallback. Phase 2 is transactional alert delivery
  (do not mark sent before a channel succeeds; `--no-send` must be
  side-effect free).

**2026-07-21 audit remediation — Phase 2 (Codex implementation,
Claude Fable 5 review):**
- Split alert handling into pure evaluation, independent channel
  delivery, and atomic persistence. A warning is now marked sent only
  after ntfy, email, or SMS actually succeeds; complete failure exits
  nonzero and retries next run.
- Made `--no-send`, `--dry-run`, and the compatibility evaluator
  side-effect free. Generation and local testing can no longer consume
  a live alert or require restoring `data/alert_state.json` afterward.
- Added stable event signatures (tide time; NWS event + onset), retained
  escalation semantics, and narrowed the 24-hour cooldown to the same
  delivered signature. Lower-rank background risks no longer churn the
  active event signature.
- Added offline regression coverage for appearance, all-clear,
  cooldown, escalation, same-rank new events, retry-after-failure,
  recipient restoration, and email/ntfy channel isolation. Phase 3 is
  repair and validation of the append-only CSV ledgers.

**2026-07-21 audit remediation — Phase 3 (Codex implementation,
Claude Fable 5 review):**
- Repaired `forecast_accuracy.csv` without changing historical values:
  its header now includes the eighth `confidence_level` field already
  present in 59 rows, and the one pre-confidence row has an explicit
  empty trailing value. Confidence-stratified calibration can now read
  the stored levels instead of losing them under `DictReader[None]`.
- Repaired five quoting defects in `labeled_observations.csv`. One
  backslash-escaped inch mark had merged two physical records into one;
  four unquoted comma-bearing fields had shifted columns. Strict parsing
  now yields 149 records, all exactly 10 fields wide, with original text,
  values, and row order preserved.
- Extended the publish gate to strict-parse the five canonical live CSV
  ledgers and require exact headers and row widths. Append writers now
  reject schema drift before writing, and regression tests cover the live
  ledgers, broken quotes, extra fields, stale headers, and empty-file
  initialization. Phase 4 is explicit input health and provenance.

**2026-07-21 audit remediation — Phase 4 (Codex implementation,
Claude Fable 5 review):**
- Forecast output now carries `generated_utc`,
  `forecast_schema_version`, `model_version`, per-source
  `input_health`, and a derived `degraded_inputs` list. The publish gate
  requires valid, internally consistent provenance on every generated
  `docs/forecast.json`.
- NWS QPF and inland-alert fetch failures now return unavailable rather
  than an empty/dry result. Missing QPF exports null rain metrics and
  omits the pluvial hydrograph; HTML/email surfaces a degraded-input
  warning that explicitly says missing data was not treated as zero.
- Missing live surge no longer becomes `+0.0 ft` labeled as persistence.
  Tides fall back to `astronomical-only-degraded`, confidence becomes
  LOW, and storm departure is called unknown. Gauge, temperature,
  hourly forecast, coastal product, alerts, QPF, and tide-astronomy
  health are independently recorded.
- Radar gating now fails safe: if the NWS alerts or near-term hourly
  trigger check is unavailable, run the MRMS nowcast rather than declare
  quiet weather. Offline regression coverage exercises unavailable
  versus empty semantics, omitted pluvial output, degraded metadata and
  banners, metadata-gate consistency, and conservative trigger behavior.
  Phase 5 aligns the production model version and documentation.

**2026-07-21 audit remediation — Phase 5 (Codex implementation,
Claude Fable 5 review):**
- Promoted the already-live July 18 refit to the correct `v0.10.1`
  production stamp without retuning: K=1.296e6, gamma=0.78,
  measured k_out=3.50/h, lag=15 min. The former `v0.10` spec is
  preserved under `model/archive/`; `model/v0.10.1.md` documents the
  measured constraint, refit, cutover, evidence, and reproducibility
  limitation.
- Updated `CURRENT_MODEL_VERSION`, the predictions-log README, root
  README, observations README, workflow wording, current HANDOFF
  summary, and the elevation/threshold reference in lockstep. The
  retired +0.40 enhancement and fictitious 5.08-ft porch step no longer
  appear as current guidance; the table now uses enhancement 0.00 and
  the measured 5.41-ft first-step top.
- The publish gate now reads the source model stamp and rejects a
  generated forecast with a different `model_version`. Regression tests
  lock the stamp, production constants, current spec path, archived
  prior spec, and README references together. Historical prediction
  rows remain as-run history; correctly stamped `v0.10.1` rows begin at
  this documentation cutover. Phase 6 improves skill reporting and
  nowcast scheduling.

End of handoff.
