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
| Historical statistics project (Claude Code) | ⏳ In progress |
| Move to `bayavebarnacle@gmail.com` SMTP account | ⏸ Awaiting account-aging for Gmail app passwords |
| First real-event validation of NWS parser | ⏸ Awaiting next coastal flood event |
| Seasonal context line in email | ⏸ Designed, not yet built |
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

**Reference depths from labeled events:**

| Event | Sandy Hook obs MLLW | Observed depth | Model predicted |
|---|---|---|---|
| Apr 17 2026 | 6.76 | ~2" light | 2.2" |
| Apr 18 2026 | 7.32 | ~10" moderate | 10.8" |
| Dec 19 2025 | 6.83 + 0.44"/hr rain | ~7–9" | ~6" (under-predicts rain term) |
| Oct 30 2025 | 7.57 + 1.45"/hr rain | ~12" severe | ~14" |
| Feb 22–23 2026 | 7.19 + cold | **No flood** | 0 (cold lockout) |

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
│   ├── labeled_events.csv        # 5 flood events used for calibration
│   ├── merged_hourly.csv         # tide + met + rain joined, ~6200 rows
│   ├── monthly_flood_averages.csv
│   ├── floods_by_month{,_minor,_moderate,_major,_total}.tsv
│   ├── top10_highest_tides.tsv
│   └── raw/                      # source pulls before merging
│       ├── sandyhook_water_levels.csv
│       ├── sandyhook_met.csv
│       ├── njdep_rainfall_2026_05_17.csv
│       └── met_monthly/          # monthly chunks
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
├── history/                      # Claude Code's project area
│   └── HANDOFF.md
├── deploy/
│   └── HANDOFF.md                # superseded by section 4 above
└── attic/                        # archived dead-ends + old structure
    ├── etss_fetcher.py
    └── dev_pre_v0.5_reorg_20260518/   # original dev/ tree
```

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

7. **NWS Mt Holly's coastal flood Minor threshold (6.7 ft MLLW) is**
   exactly the user's empirical flood onset (~6.6 ft). Independent
   validation: NWS thinks "minor coastal flooding" happens at the same
   water level the user sees water at the curb.

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
1. **Validate NWS parser against next real event.** Will happen on its
   own. When a Coastal Flood Warning/Advisory fires for Eastern Monmouth,
   run `python3 nws_surge_parser.py` and confirm it parses cleanly.
   Tighten regex if needed.
2. **Historical statistics project** (`history/HANDOFF.md`, in progress
   with Claude Code). Pulls all NOAA Sandy Hook hourly data and computes
   hyperlocal flood-event statistics at *user's* 6.58 ft threshold,
   not the dashboard's 7.20 ft. Outputs return periods, sea-level-rise
   trend, monthly frequency.
3. **Switch SMTP_USER to `bayavebarnacle@gmail.com`** once the account
   ages enough to support app passwords. Update three GitHub secrets;
   no code change. Keeps forecast emails out of personal Sent folder.
4. **Investigate Aug 21 2025 NWS Moderate Coastal Flood Warning.** The
   search that gave us the parser sample was a real event — Sandy Hook
   forecast 8.0 ft at 7 PM Aug 21, surge +2.4 ft. User has no logged
   flood for that date. Worth checking whether they were away or the
   forecast didn't fully materialize.
5. **Field-measure the lawn/walkway step elevation.** Current 4.58 NAVD88
   is the midpoint of an inferred 4.54–4.63 range. A precise reading
   tightens the moderate-flood threshold.
6. **Add seasonal context line to email.** Use `data/monthly_flood_averages.csv`
   to add e.g. "May avg: 1.2 flood events/month at Sandy Hook. You've
   had 0 so far this May." Small change to `render_email`.
7. **Day-name labeling in tide times.** Currently shows
   "2026-05-18 22:14" — accurate but a mouthful. Could format as
   "Mon 10:14 PM" for readability. Easy strftime change.
8. **Update GitHub Actions versions before June 2 2026.** Node.js 20
   deprecation in `actions/checkout@v4` and `actions/setup-python@v5`.
   One-line PR each when new majors land.

### Medium value
9. **Decompose the +0.40 local enhancement.** Currently a constant; with
   8–10 more events, may correlate with wind direction / speed / pressure /
   lunar phase. Becomes a function instead of a constant.
10. **Calibrate cold-weather override threshold.** Only Feb 22–23 in the
    dataset. Several more cold-weather high-tide events would refine
    the 72-h, 32°F trigger.
11. **Low tide times in email for "all-clear" indicators.** Users might
    want to know when it's safe to leave (low tide windows). Fetcher
    already supports returning both highs and lows from hilo product.
12. **Severity-based notifications.** Currently emails daily regardless.
    Could suppress emails for DRY days and use a separate channel (SMS,
    push) for SEVERE days. Reduces noise.
13. **Verify Phase 1 reconstruction status.** If the road has been
    rebuilt to design (4.20 NAVD88), all thresholds shift up ~0.04 ft
    (sub-inch).
14. **Pluvial-only flooding test.** Does heavy rain at low tide flood
    342 Bay? No event in the dataset confirms or denies.
15. **Borough drainage map.** Email Stephen Winters (Floodplain Admin,
    swinters@highlandsnj.gov) for the storm sewer map. Would clarify
    Pathway B outfall locations.

### Worth retrying later
16. **NOAA ETSS direct fetch from GitHub Actions runner.** Different IP,
    different routing. If successful, gives always-on numeric surge
    forecast — complementary to NWS products (event-only).
17. **Stevens NYHOPS API inspection.** Focused attempt to find the
    JSON endpoint behind their SFAS visualization.
18. **Iowa Mesonet historical NWS products.** Right URL pattern would
    let us pull e.g. the Oct 30 2025 Mt Holly CFW text for parser
    hardening before relying on a live event.

### Speculative / nice-to-have
19. **Probabilistic ETSS (P-ETSS) ensemble.** 21 GEFS members → spread.
    Once ETSS works, gives probability of flooding directly.
20. **Bayesian seasonality update.** Use monthly priors to flag unusual
    forecasts.
21. **USGS Total Water Level Forecast API.** Mentioned but not
    explored. Serves coastal forecasts including Sandy Hook.
22. **Multi-location expansion.** Same model architecture, different
    anchors, for neighbors. "Atlantic Highlands Barnacle." Repo named
    generically for this.
23. **NJ LiDAR DEM extraction.** Currently use surveyed plan elevations.
    LiDAR would let us see full neighborhood microtopography and produce
    flood-extent maps for any Sandy Hook level.

---

## 10. Outstanding open questions

- Was the Aug 21 2025 NWS-forecast Moderate flood actually a flood at
  342 Bay, or did the forecast over-shoot?
- Why is the +0.40 ft local enhancement so consistent across 4 events
  with very different wind/pressure conditions? Suggests structural
  factor (drain backflow geometry) more than meteorological.
- Does the rain term saturate at 8 inches as `tanh` assumes? Only
  Oct 30 and Dec 19 sample the rain regime meaningfully.
- Does cold-weather override apply to a single overnight freeze or
  only sustained below-freezing periods? Only one observation.

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
6. **When Claude Code's historical-statistics project completes**:
   review outputs. Compare to existing labeled events. Consider
   integrating long-term stats into the daily email (point #6 above).

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

End of handoff.
