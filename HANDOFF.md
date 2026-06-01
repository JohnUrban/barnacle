# Bay Ave Barnacle — Project Handoff

**A hyperlocal flood prediction system for 342 Bay Avenue, Highlands NJ.**

This document is the authoritative state-of-the-project. It captures
the model, the architecture, what works, what didn't and why, what's
next, and all design context worth carrying into future work.

If anything anywhere disagrees with this document, **assume the file
with the higher version number wins** (currently model spec v0.5).

**Status: PRODUCTION.** The system is deployed, scheduled, and
self-publishing. Daily forecasts arrive by email; daily reports
publish to GitHub Pages. As of the handoff date the loop runs without
intervention; the work ahead is refinement, not bootstrap.

---

## 1. The project in one paragraph

A homeowner at 342 Bay Avenue, a low-lying property in Highlands NJ on
Sandy Hook Bay, has experienced repeated flooding from tidal + rainfall
events. Public sources (NOAA Sandy Hook gauge, the Sandy Hook Tidal
Flooding Dashboard, tide-prediction apps) give regional-scale signal
that misses the user's specific property in two directions: false
positives (predicted flooding that doesn't materialize at this house)
and false negatives (actual flooding without sufficient warning).

The project produces a **daily morning email** with predicted water
depth at four named landmarks at 342 Bay Ave — curb, road middle,
intersection high point, and lawn step — for **both high tides in the
next 24 hours**, plus a publicly-readable web page at
[johnurban.github.io/barnacle](https://johnurban.github.io/barnacle/).

The model is small but earned: every parameter is grounded in either
surveyed engineering elevations from a Borough PDF, or in empirical fit
across four labeled flood events the user observed firsthand.

---

## 2. Status at handoff

| Component | State |
|---|---|
| Model v0.6 specification (9 landmarks, formal spec) | ✅ Complete, validated against 4-6 events. Old v0.5 in model/archive/ |
| Daily forecast script (`forecast/flood_forecast_daily.py`) | ✅ In production, runs daily via GitHub Actions |
| Multi-tide forecast (both high tides per day) | ✅ Live since 2026-05-18 |
| NWS surge parser (`forecast/nws_surge_parser.py`) | ✅ Self-test passes; awaits first live event |
| GitHub Actions workflow | ✅ Scheduled daily 09:00 UTC (5 AM EDT / 4 AM EST) |
| Email delivery (Gmail SMTP) | ✅ Working from personal Gmail |
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
| v0.6 grate elevation bug surfaced (NE/NW grates 3.80 not 3.91) | ⏸ Per survey PDF `model/HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf`: NE/NW grates = 3.80; 3.91 is the NE pavement corner (separate landmark). v0.6's `corner_grate` should have been 3.80. Pathway B threshold should be SH 6.22, not 6.33. Queue for v0.7. |
| Photos from 2026-05-18 event distributed to 7 subdirectories | ✅ Done 2026-05-19. Medium-size exports (~13 MB total) under `assets/observations/2026-05-18/<grate-or-landmark>/`. 13 calibration rows in `data/labeled_observations.csv`. Plus 3 morning-after pocket photos (cba8338) confirming ≥11.4h pocket retention. |
| Second + third real spot-check events (2026-05-30, 2026-05-31) | ✅ Logged 2026-05-31. 2026-05-30 PM tide qualitative (SE/SW overtopped at SH 6.538). 2026-05-31 PM tide cleanly measured at 4 grates (water 7.25/7/5/4 in below NE/upstream/SE/SW respectively at SH 6.17 peak) — water at 342 Bay = 3.20 ± 0.05 NAVD88, implied local enhancement = -0.13 ft, **consistent with 5/18 finding**. Two events now contradict the +0.40 constant. 9 new rows in `data/labeled_observations.csv`. See `assets/observations/2026-05-30/README.md` and `assets/observations/2026-05-31/README.md`. |
| High-res measuring-tape reference photos | ✅ Added 2026-05-31. Two straight-on photos + README in `assets/observations/0-measuring-tape/` covering the digit-after-line convention, subdivision marks, color cues, and common photo-reading failure modes. Use when independently verifying tape readings from spot-check photos. |
| Hourly bot cadence — actually ~62%, not 100% | ⚠️ Documented 2026-05-31 (see `assets/observations/2026-05-30/README.md` cadence section). GitHub Actions throttles the `'0 * * * *'` schedule. Last 7 days: 120/192 hour-slots filled. UTC hours 02/04/06 never run; 08/10/11/12/14/16 partial. No fix — this is GHA free-tier load shedding behavior. Convergence charts have ~1.5-2 h effective resolution, not 1 h. |
| Web platform pivot — sub-daily updates, interactive site | ✅ Foundation shipped 2026-05-19. See section 9b. Workflow hourly; per-tide deep-link pages; client-side heat-map renderer; convergence + oscillation + scrubber charts; severity-colored rollup with 24/48/72h toggle; rain-toggle map; refined confidence with regime band; 1-2 month astronomical look-ahead; accuracy scatter + binary classifier matrix. Master predictions log at `data/predictions_log.csv` accumulating since 2026-05-19. |
| v0.7 model spec promotion (5 grates + storm-surge-dependent enhancement + corrected elevations) | ⏸ Queued. (a) Fix grate_NE elevation 3.91→3.80 (survey). (b) Add grate_NW (3.80), grate_SW (~3.55-3.58), grate_bay_ave_upstream (~3.76). (c) Add corner_NE (3.91), corner_SE (3.64), corner_SW (3.64), rename `intersection`→`intersection_highpoint` (4.54). (d) Rename existing corner_grate→grate_NE, lowest_sentinel_grate→grate_SE. (e) Replace constant +0.40 enhancement with storm-surge-dependent function — current hypothesis: +0.40 only develops during meaningful surge (likely tied to wind/pressure pushing surge into the bay), ~0 for normal tides. Needs ≥2 more events to firm up the surge-dependent form. |
| Move to `bayavebarnacle@gmail.com` SMTP account | ⏸ Awaiting account-aging for Gmail app passwords |
| First real-event validation of NWS parser | ⏸ Awaiting next coastal flood event |
| v0.6 model-spec promotion + 9th landmark added | ✅ Live (2026-05-18). model/v0.6.md canonical; v0.5 archived. New lowest sentinel at 3.60 NAVD88 (SH 6.02). |
| SMS/push alerts for moderate/severe (Twilio/Pushover) | ⏸ Next-turn item |
| iOS Stage-1 Web Clip (Add to Home Screen) | ✅ Live (2026-05-18). manifest.json + apple-touch-icon + meta tags |
| iOS Stage-2 Scriptable widget | ✅ Live (2026-05-18). Script at docs/barnacle-widget.js |
| iOS Stage-3 PWA push notifications | ⏸ Next-turn item |
| iOS Stage-4 native iOS app | ⏸ Multi-session, requires Apple Developer Program |
| Live NOAA gauge link/embed on Pages site | ⏸ Next-turn item |
| Stevens NYHOPS surge fallback | ⏸ Not investigated further |
| ETSS direct fetch | ❌ Abandoned — network blocked from user's ISP |
| Node.js 20 deprecation in workflow | ⏸ Bump action versions before June 2 2026 |

✅ done · ⏳ in progress · ⏸ backlog · ❌ ruled out

---

## 3. The model in one screen (v0.5)

**Inputs:**
- `high_tides_24h` = list of high tides in next 24 hours, each with predicted MLLW value and exact time (from NOAA hilo product)
- `SH_peak` for each = forecast peak Sandy Hook total tide (ft MLLW), preferably from NWS Coastal Flood product if active, else predicted-tide + current-surge persistence
- `peak_rain` for each = max NWS-forecast hourly precipitation rate in ±90 min of *that specific* high tide
- `temp_72h` = mean air temp at Sandy Hook over past 72 h (single value, applies to all tides today)

**Formula (applied per high tide):**

```
water_at_342_MLLW   = SH_peak + 0.40              # local enhancement
water_at_342_NAVD88 = water_at_342_MLLW − 2.82    # datum convert
depth(landmark)     = max(0, (water − landmark_NAVD88)) × 12   # inches

# Rain term (Pathway C amplification)
if peak_rain ≥ 0.1: depth += 8 × tanh(peak_rain)   # saturating, ≤8"
                    (lawn and intersection shed more, get less)

# Cold override (Pathway B suppression) — DEMOTED 2026-05-19
# After the 19-event retrospective, this rule was demoted from
# active override to advisory note. Predictions now go through
# unchanged when conditions are met; a yellow banner explains
# the hypothesis is open but not applied. See
# history/reports/cold_weather_retrospective.md.
# Old behavior (preserved here for the spec history):
#   if temp_72h < 32°F and SH_peak < 8.0:  depth = 0
```

**Landmark elevations at 342 Bay Ave (ft NAVD88):**

| Landmark | NAVD88 | MLLW | Sandy Hook threshold |
|---|---|---|---|
| Lowest corner across Bay | 3.64 | 6.46 | **6.06** |
| Gutter at walkway | 3.78 | 6.60 | 6.20 |
| Storm inlet grate (lowest) | 3.91 | 6.73 | 6.33 |
| **Curb top at walkway** | **4.16** | **6.98** | **6.58** ← flood onset |
| Bay Ave road middle | 4.36 | 7.18 | 6.78 |
| Intersection center | 4.54 | 7.36 | 6.96 |
| **Lawn / walkway step** | **4.58** | **7.40** | **7.00** |
| Road middle near driveway | 4.70 | 7.52 | 7.12 |

Datum constants: `NAVD88 = MLLW − 2.82` at Sandy Hook (NOAA-published).

**Hurricane Sandy reference:** 13.31 ft MLLW on NOAA 6-min product
(instantaneous peak), 12.03 ft on hourly_height (centered-hour average).
The 6-min number is what historical accounts cite. A forecast hitting
12.0 ft on hourly products IS a Sandy-class event — don't anchor
expectations on the 13.31 number when comparing to hourly products.

**Reference depths from labeled events:**

| Event | Sandy Hook obs MLLW | Observed depth | Model predicted |
|---|---|---|---|
| Apr 17 2026 | 6.76 | ~2" light | 2.2" |
| Apr 18 2026 | 7.32 | ~10" moderate | 10.8" |
| Dec 19 2025 | 6.83 + 0.44"/hr rain | ~7–9" | ~6" (under-predicts rain term) |
| Oct 30 2025 | 7.57 + 1.45"/hr rain | ~12" severe | ~14" |
| Feb 22–23 2026 | 7.19 + cold | **No flood** | 0 (cold lockout) |
| Aug 21 2025 | 6.93 + surge 1.4 ft (per historical pull) | unknown (user not home/didn't log?) | ~4–5" predicted |

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
│   ├── v0.5.md                   # ★ CURRENT spec
│   ├── elevations.md             # surveyed landmark elevations
│   ├── elevations.pdf
│   ├── h2m_pdf_extracts.md       # extracted key text from Borough PDF
│   ├── HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf
│   └── archive/                  # v0.1 - v0.4 specs
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
│   │   └── analyze.py                   # all derived analytics
│   ├── data/
│   │   ├── summary_stats.json           # ★ headline numbers
│   │   ├── calibration_check.csv        # ★ 4-event validation
│   │   ├── seasonality_recent.csv       # ★ 1996-2025 8-stratum table, used by daily email
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
4. **Field-measure the lawn/walkway step elevation.** Current 4.58 NAVD88
   is the midpoint of an inferred 4.54–4.63 range. A precise reading
   tightens the moderate-flood threshold.
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
14. **Pluvial-only flooding test.** Does heavy rain at low tide flood
    342 Bay? No event in the dataset confirms or denies. **Spot-check
    prompt now calls this out when conditions match** (≥0.25" rain
    forecast over 24 h AND no high tide reaches the lowest sentinel)
    — ✅ wired 2026-05-18. One good observation in that regime would
    resolve the question.
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
    `landmark` / `extra` / `approximated`. `approximated` points are
    best-guess elevations the user places to *shape* the heat-map
    surface — street-crown centerlines, curb/sidewalk/lawn boundary
    lines — where a height can be inferred from nearby known points
    but wasn't surveyed. Rendered amber on the base map (vs blue
    landmark / red surveyed-extra) so guesses are never mistaken for
    measurements. All three categories feed the heat-map triangulation
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
in blue, highest (porch step, 5.08) in red. Reading the plot tells you
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

- Status: queued — **DO NOT START YET** (see 9c).
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

## 9c. v0.7 model spec roadmap (DO NOT START YET)

Consolidated view of everything queued for the v0.7 model promotion.
Per HANDOFF section 12's versioning rule, elevation changes + formula
changes warrant a version bump — v0.7 is the bundle of all five items
below.

**DO NOT START YET.** Two reasons to bundle rather than land
piecewise:

1. The **storm-surge enhancement hypothesis** (9c.3) needs at least
   one more validating event before freezing v0.7's enhancement
   function. A single 2026-05-18 observation isn't enough.
2. Several **9b.X items depend on v0.7's water-level architecture**
   (9b.5, 9b.9 explicitly; 9b.4 indirectly). Bundling avoids two
   migrations.

### 9c.1 — Corrected grate elevations (survey-derived)

Per `model/HLND2303-Road-Reconstruction-Supplement-Set-2024.05.06.pdf`:

- `grate_NE` and `grate_NW` = **3.80 NAVD88** (was 3.91 in v0.6)
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
| `grate_SW` | ~3.55-3.58 | Across Bay, diagonal; NEW; ~0.5" lower than SE |
| `grate_bay_ave_upstream` | ~3.76 | East on Bay Ave, NEW; *the actual primary feeder* of the user's gutter |

### 9c.3 — Storm-surge propagation enhancement

Replace the constant +0.40 ft local enhancement with a function of
surge magnitude.

Working hypothesis (one validating event: 2026-05-18; non-validating):

> +0.40 ft is a storm-surge propagation effect, not a constant.
> Storm events with meaningful surge (Apr 18: +1.30 ft; Oct 30:
> +2.90 ft) amplify water at 342 Bay relative to Sandy Hook.
> Normal tides without meaningful surge track Sandy Hook directly
> or slightly lag.

Form to fit: probably `enhancement = f(surge_ft)`, monotone, ~0 at
surge=0, saturating at ~+0.4 around surge ~+2 ft. Linear or piecewise
linear is fine pending more events.

**Validation gate**: next storm event with meaningful surge. If
enhancement re-emerges at ~+0.40 → hypothesis confirmed. If
enhancement stays ~0 → look for a different driver.

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

### 9c.5 — Rain term as water-level addition (recalibrated)

The v0.6 `rain_add = 8 * tanh(rate)` (inches) becomes
`dZ_rain = something(rate)` (ft) applied as a uniform water-level
rise. Recalibrate against Oct 30 (SH 7.57 + 1.45 in/hr → ~12" at
curb observed).

Trade-off acknowledgment: the simple uniform-rise model slightly
overstates depth at higher points (lawn, intersection) compared to
v0.6's shedding-based predictions. User accepts this in exchange for
a coherent water-is-level architecture (required for the heat-map to
agree with the depth predictions per 9c.4 + 9b.5).

### 9c.6 — Review the negative-surge clip (`max(0.0, surge)`)

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

v0.7 candidate: drop the clip. Predict actual surge. Accept that
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

**v0.7 change — before-biased window.** Replace the symmetric ±90 min
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

**Open question — is 90 min of window enough?** (User, 2026-05-20,
explicitly flagged as speculation, recorded so v0.7 calibration can
test it.) The Oct 30 2025 event suggests a ~90 min window may capture
enough of the relevant rainfall. But the *same* rain depth can produce
very different flooding depending on **antecedent conditions**, and it
is genuinely unclear which direction dominates:

- A flash downpour onto otherwise-dry ground after 24 h of no rain:
  dry soil/pavement may not absorb water fast enough, so runoff and
  ponding could be *worse* than expected.
- The same rain depth after 24 h of lighter rain: the ground is
  already wet/saturated, less infiltration capacity left — runoff
  could also be *worse*.

So a short fixed window may miss the antecedent-moisture signal
entirely. v0.7 should at least consider: (a) whether the rain term
should be driven by *accumulated* rain over the window rather than the
peak hourly *rate*, and (b) whether a longer "antecedent" lookback
(e.g. prior 24 h cumulative) belongs as a separate term feeding a
soil-saturation / infiltration factor. No decision yet — needs data
from labeled rain events. Pairs with the rain-term recalibration in
9c.5.

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
- **v0.7 is bundled work — DO NOT START YET.** Section 9c consolidates
  the five v0.7 changes. The storm-surge enhancement hypothesis (9c.3)
  needs a validating event first, and the other items want to ship
  bundled to avoid two migrations.

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
  not a constant. Validation gates v0.7 (see 9c.3).
- `history/reports/cold_weather_retrospective.md` — full
  19-candidate analysis, web evidence, decision, and the
  wind-direction refinement hypothesis (NNE/N onshore winds
  correlate with the candidates that likely flooded).
- `data/predictions_log_README.md` — schema of the master log.
- `dev/ideas/20260519.txt` — user's brainstorm (Batch 1 + 2)
  that anchored everything in this session.

**Known v0.6 bugs deferred to v0.7 (DO NOT START v0.7 YET):**
- `corner_grate` elevation: 3.91 → 3.80 (survey-confirmed).
- `predict_landmark_depths()`'s per-landmark rain shedding
  (intersection -2", lawn/porch -4") disagrees with the
  client-side heat-map's uniform additive. See FIX-IN-v0.7 comment
  in the function. v0.7 9c.4 picks water-is-level for both.
- Cold-lockout rule: possibly add wind-direction condition OR
  drop entirely. Currently demoted to advisory only.

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

### Next likely sessions

1. **Mode 2 + lead-time accuracy fill in** once predictions_log
   accumulates a few days of past-tide data (mode 2 needs
   labeled_observations rows; lead-time needs past tides).
2. **Self-calibrated confidence ± uncertainty** activates once
   the accuracy log has ≥3 rows per confidence band.
3. **Next storm event with meaningful surge** — test the
   storm-surge enhancement hypothesis (9c.3). Validation gates
   the v0.7 model promotion.
4. **Cold-conditions data collection**: every cold-conditions-met
   event observed at 342 Bay going forward becomes a new
   validation data point for the cold-lockout hypothesis.
5. **v0.7 model promotion** when the surge hypothesis lands —
   section **9c** consolidates everything in one place. **DO
   NOT START YET.**

v0.7 is queued but not started. Don't start it yet.

End of handoff.
