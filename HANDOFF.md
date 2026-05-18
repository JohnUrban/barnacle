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
| Model v0.5 specification | ✅ Complete, validated against 4 events |
| Daily forecast script (`forecast/flood_forecast_daily.py`) | ✅ In production, runs daily via GitHub Actions |
| Multi-tide forecast (both high tides per day) | ✅ Live since 2026-05-18 |
| NWS surge parser (`forecast/nws_surge_parser.py`) | ✅ Self-test passes; awaits first live event |
| GitHub Actions workflow | ✅ Scheduled daily 09:00 UTC (5 AM EDT / 4 AM EST) |
| Email delivery (Gmail SMTP) | ✅ Working from personal Gmail |
| GitHub Pages site | ✅ Live at johnurban.github.io/barnacle/ |
| Forecast archive (every day kept forever) | ✅ docs/archive/YYYY-MM-DD.html |
| Bcc privacy for multi-recipient | ✅ Built into send_email |
| Repo reorganization | ✅ Clean structure, old work archived in `attic/` |
| Historical statistics project (Claude Code) | ✅ Complete (2026-05-18). Report + CSVs in `history/` |
| Dashboard threshold correction | ✅ Corrected to 6.70 ft (was wrongly documented as 7.20 ft) |
| Move to `bayavebarnacle@gmail.com` SMTP account | ⏸ Awaiting account-aging for Gmail app passwords |
| First real-event validation of NWS parser | ⏸ Awaiting next coastal flood event |
| Seasonal context line in email | ⏸ Designed, data ready, not yet built (next priority) |
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

# Cold override (Pathway B suppression)
if temp_72h < 32°F and SH_peak < 8.0:  depth = 0
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
│   ├── merged_hourly.csv         # tide + met + rain joined, ~6200 rows
│   ├── floods_by_month{,_minor,_moderate,_major,_total}.tsv
│   ├── top10_highest_tides.tsv
│   └── raw/                      # source pulls before merging
├── analysis/
│   ├── cross_ref.py              # calibration cross-reference
│   ├── rain_analysis.py
│   └── how-rain-adds.md          # rain mechanism notes
├── docs/                         # GitHub Pages site
│   ├── index.html                # today's forecast (auto-replaced)
│   ├── style.css
│   └── archive/
│       ├── index.html            # auto-regenerated list
│       └── YYYY-MM-DD.html       # one per day, forever
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
│   │   ├── seasonality_by_threshold.csv # ★ for seasonal-context email line
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
├── deploy/
│   └── HANDOFF.md                # superseded by section 4 above
└── attic/                        # archived dead-ends + old structure
    ├── etss_fetcher.py
    └── dev_pre_v0.5_reorg_20260518/   # original dev/ tree
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
8b. **Forecast accuracy log.** Auto-compare each day's forecast to the
    next day's observed Sandy Hook peak + actual landmark depth from
    NOAA. Append to `data/forecast_accuracy.csv`. Surface a small
    "model accuracy: last 30 days mean error X.X ft, X.X" at landmarks"
    line in the email. Self-validating system. Could also feed back
    into model recalibration as data accumulates.
    *Depends on:* #16c (JSON archive).
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
    the 72-h, 32°F trigger. **The daily spot-check prompt should
    explicitly call this out as a high-value observation when conditions
    match** (cold weather + high tide that would otherwise flood). See
    also item 16 for retrospective calibration from historical data.
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
    342 Bay? No event in the dataset confirms or denies. **The daily
    spot-check prompt should explicitly call this out as a high-value
    observation when conditions match** (heavy rain forecast with all
    tides well below curb). One good observation could resolve the
    question.
15. **Borough drainage map.** Email Stephen Winters (Floodplain Admin,
    swinters@highlandsnj.gov) for the storm sewer map. Would clarify
    Pathway B outfall locations.
16. **Cold-weather override calibration from historical data.** Two
    related ideas:
    (a) Use historical air-temperature data (NOAA `air_temperature`
        product at Sandy Hook) joined to hourly water-level data to
        find past events where the cold-weather override SHOULD have
        applied — i.e., 72-h mean temp < 32°F AND Sandy Hook peak
        > 6.58 ft (would have crossed the curb without the override).
        Check newspaper / borough archives or rain/met records to see
        if flooding actually occurred. If most such past events also
        produced no flooding, that's strong retrospective validation
        of the cold-weather override without waiting for new events.
        (Original Feb 22 2026 observation gives one data point.)
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

System is in production. Nothing is blocking. Suggested cadence:

1. **Each morning**: glance at the email. Triage by subject line; only
   open if regime is anything other than DRY.
2. **When a coastal flood event happens**: run
   `forecast/nws_surge_parser.py` once during the event to verify it
   parses the live NWS product cleanly. Paste output if it fails.
3. **In ~24-48 hours**: retry generating an app password from
   `bayavebarnacle@gmail.com`. When successful, update three GitHub
   secrets to move email sending off personal account.
4. **Weekly-ish**: check
   [johnurban.github.io/barnacle/archive/](https://johnurban.github.io/barnacle/archive/)
   to confirm daily runs are accumulating archive entries cleanly.
5. **Monthly-ish**: review prediction accuracy against any actual
   observations. If predictions consistently miss in one direction,
   that's information for refining the +0.40 enhancement or rain term.
6. **Now, before the seasonal-context build**: commit the historical-stats
   project outputs (`history/scripts/`, `history/reports/`, `history/data/*.csv`,
   `history/data/*.json`, `history/figures/`, `history/RESULTS_HANDOFF.md`,
   `history/pull.log`). Don't commit `history/data/raw_chunks/` or
   `history/data/sandy_hook_hourly_history.parquet` — both regeneratable
   and bulky. Update `.gitignore` accordingly.
7. **Build the seasonal-context feature** — pull from
   `history/data/seasonality_by_threshold.csv` and
   `history/data/slr_trend_by_window.csv`; small change to
   `render_email()` and `render_html_page()`.

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
- **When sources disagree, v0.5 spec wins.** v0.4 had three arithmetic
  errors. Python code was always correct.
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

End of handoff.
