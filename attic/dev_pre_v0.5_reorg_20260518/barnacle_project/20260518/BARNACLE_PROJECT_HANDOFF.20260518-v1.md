# Bay Ave Barnacle — Project Handoff

**A hyperlocal flood prediction system for 342 Bay Avenue, Highlands NJ.**

This document is the authoritative state-of-the-project. It captures
the model, the architecture, what works, what didn't and why, what's
next, and all design context worth carrying into future work.

If anything anywhere disagrees with this document, **assume the file
with the higher version number wins** (currently model spec v0.5).

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
intersection high point, and lawn step — driven by:

- NOAA Sandy Hook predicted astronomical tide (next 24 h)
- NOAA Sandy Hook observed surge (and NWS Coastal Flood product when active)
- NWS hourly rainfall forecast for Highlands
- NOAA Sandy Hook air temperature (cold-weather override)
- A calibrated v0.5 hyperlocal model with surveyed elevation anchors

The model is small but earned: every parameter is grounded in either
surveyed engineering elevations from a Borough PDF, or in empirical fit
across four labeled flood events the user observed firsthand.

---

## 2. Status at handoff

| Component | State |
|---|---|
| Model v0.5 specification | ✅ Complete, validated against 4 events |
| Daily forecast script (`flood_forecast_daily.py`) | ✅ Works end-to-end in `--dry-run`; needs SMTP setup + scheduling |
| NWS surge parser (`nws_surge_parser.py`) | ✅ Self-test passes; awaits first live event |
| Cron / GitHub Actions deployment | ⏳ Handoff doc written; user setting up |
| Historical statistics project | ⏳ Handoff doc started in Claude Code |
| First real-event validation of NWS parser | ⏳ Pending next coastal flood event |
| Seasonal context in email | ⏸ Designed, not yet built |
| Stevens NYHOPS surge fallback | ⏸ Not investigated further |
| ETSS direct fetch | ❌ Abandoned — network blocked from user's ISP |

✅ = done · ⏳ = in progress · ⏸ = backlog · ❌ = ruled out

---

## 3. The model in one screen (v0.5)

**Inputs:**
- `SH_forecast` = forecast peak Sandy Hook total tide in next 24 h (ft MLLW), preferably from NWS Coastal Flood product if active, else predicted-tide + current-surge persistence
- `peak_rain` = max NWS-forecast hourly precipitation rate in ±90 min of peak tide
- `temp_72h` = mean air temp at Sandy Hook over past 72 h

**Formula:**

```
water_at_342_MLLW  = SH_forecast + 0.40           # local enhancement
water_at_342_NAV88 = water_at_342_MLLW − 2.82     # datum convert
depth(landmark)    = max(0, (water − landmark_NAVD88)) × 12  inches

# Rain term (Pathway C amplification)
if peak_rain ≥ 0.1: depth += 8 × tanh(peak_rain)   # saturating, ≤8"
                    (lawn and intersection shed more, get less rain add)

# Cold override (Pathway B suppression)
if temp_72h < 32°F and SH_forecast < 8.0:  depth = 0
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

## 4. Files inventory

All files in this project:

| File | Purpose | Status |
|---|---|---|
| `flood_model_spec_v0.5.md` | **Authoritative model spec.** Read first. | Current |
| `flood_model_spec_v0.4.md` | Previous version. Had arithmetic errors in landmark threshold table. | Obsolete |
| `flood_model_spec_v0.3.md` | Used wrong curb elevation (5.30 vs actual 4.16) | Obsolete |
| `flood_model_spec_v0.2.md` | Pre-elevation-data version. Had a wrong "antecedent saturation" hypothesis. | Obsolete |
| `flood_model_spec_v0.1.md` | Initial sketch. | Obsolete |
| `highlands_local_elevations.md` | Surveyed elevations + sources. Cross-referenced from spec. | Current (corrected with v0.5) |
| `h2m_pdf_key_extracts.md` | Borough engineering plan extracts. Source data for elevations. | Current |
| `flood_forecast_daily.py` | The daily forecast script. Wires v0.5 model + NWS surge parser + email. | Current |
| `nws_surge_parser.py` | NWS Coastal Flood text parser. Used by main script. | Current |
| `etss_fetcher.py` | NOAA ETSS attempt. Doesn't work from user's network. | Archived |
| `highlands_merged_hourly.csv` | Hourly tide+met+rain data Sep 2025–May 2026. Used in model calibration. | Reference data |
| `highlands_rain_events_labeled_v2.csv` | 42 rain events with flood labels. | Reference data |
| `highlands_cross_ref.py`, `highlands_rain_analysis.py` | Calibration scripts. | Reference |
| `avg-num-floods-by-month.csv` | Monthly flood averages from Sandy Hook dashboard (7.20 ft threshold). | Reference |
| `HANDOFF_deploy_script.md` | Cron / GitHub Actions setup guide. | Handoff |
| `HANDOFF_historical_data.md` | Claude Code project: pull NOAA history, compute hyperlocal stats. | Handoff |
| `BARNACLE_PROJECT_HANDOFF.md` | This document. | Current |

**Repo layout (user's):**
```
~/searchPaths/github/barnacle/
├── dev/
│   └── highlands_floodwatch/
│       ├── forecast/
│       │   ├── flood_forecast_daily.py
│       │   ├── nws_surge_parser.py
│       │   └── ETSS/
│       │       └── etss_fetcher.py     (archived attempt)
│       └── history/
│           └── HANDOFF_historical_data.md
```

---

## 5. How we got here — key insights and reversals

These are the model corrections that actually moved the needle, listed
because each was a non-trivial moment of "the previous version was
wrong":

1. **The user's tide app shows only astronomical tide, not surge.** Every
   flood event in the dataset had +0.8 to +2.9 ft of surge on top of the
   predicted tide. The app silently misled the user. (Implication:
   *observed* total water level is the right input variable, not
   forecast astronomical alone.)

2. **The "antecedent saturation" theory for April 18 was wrong.** Earlier
   versions of the model claimed April 18 flooded worse than April 17
   despite a lower tide due to ground saturation. Actually, April 18's
   observed tide was higher (7.32 vs 6.76 ft) once surge was included.
   No saturation theory needed — more water → more flooding.

3. **Oct 30 wasn't a "rain event with modest tide."** Its predicted
   astronomical tide was only 4.67 ft (very modest). But surge added
   +2.90 ft for an actual observed peak of 7.57 ft, on top of which a
   1.45"/hr rain peak landed during high tide. Three reinforcing
   factors, not one.

4. **The "5.30 ft NAVD88 curb elevation" Gemini cited was a legend
   sample, not the actual curb at 342 Bay.** The H2M engineering PDF
   exists and is real, but the 5.30 value appearing in it was a sample
   showing the labeling convention. The actual surveyed curb at 342 Bay
   is 4.16 NAVD88. This corrected the model substantially — local
   enhancement dropped from +1.5 ft (with wrong curb) to +0.4 ft (with
   correct curb), a far more physically plausible number.

5. **The intersection at Bay+Central is a local high point (4.54 NAVD88)
   that often stays dry while surrounding road floods.** The user
   noticed this on Dec 19 video. Confirmed by surveyed elevations. It's
   now an explicit landmark in the model and produces predictions
   like "road covered but intersection still dry" that match observed
   reality.

6. **Cold weather suppresses the Pathway B drain backflow mechanism.**
   Feb 22–23 had observed Sandy Hook of 7.19 ft + strong onshore winds
   — should have flooded — but the user (awake and checking through the
   night) confirmed nothing happened. Hypothesis: ice at storm drain
   outfalls blocks the bay→street pathway. Single observation, plausible
   mechanism, in the model as an override but not deeply validated.

7. **NWS Mt Holly's coastal flood Minor threshold (6.7 ft MLLW) is
   exactly the user's empirical flood onset (~6.6 ft).** Independent
   validation: NWS thinks "minor coastal flooding" happens at the same
   water level the user sees water at the curb. The dashboard's "Minor
   7.20 ft" threshold is what was confusing — it's a different (perhaps
   later or impact-weighted) definition than the standard NWS Sandy
   Hook 6.7 ft.

---

## 6. Surge investigation — what was tried, what worked, what didn't

The user is correct that surge is the single biggest information gap.
The astronomical-tide prediction is static and known years in advance;
surge is the part that varies with weather and that we need to
forecast. Here's everything we explored:

### What worked
- **NWS Coastal Flood product via api.weather.gov.** When NWS issues a
  Coastal Flood Warning, Advisory, or Statement for the area, the text
  includes Sandy Hook tide projections (DD/HH AM|PM + total tide MLLW
  + departure ft + flood category). We have a self-tested parser
  (`nws_surge_parser.py`) that extracts these and uses them as the
  forecast.
- **NOAA tidesandcurrents.noaa.gov API.** Works reliably. Used in the
  main script for predicted tide, current observed surge (persistence),
  and air temperature.
- **NWS api.weather.gov gridded hourly forecast.** Works reliably. Used
  for rainfall forecast.

### What didn't work, and why
- **NOAA ETSS direct fetch from `ftp.ncep.noaa.gov`.** Connection
  timeout — Comcast-issued IP can't TCP-connect. DNS resolves fine; the
  route is blocked. (Could work from a different network. Worth trying
  from any cloud-hosted runner.)
- **NOAA ETSS via `nomads.ncep.noaa.gov` (Akamai mirror).** Returns HTTP
  403 for directory listings *and* for specific files, even with browser
  User-Agent. The host is reachable; the content is gated. (Could work
  from a non-residential IP or with a different identifying header. Not
  worth more debugging time from this network.)
- **Iowa Environmental Mesonet API**. Initial URL guess was wrong.
  Their archive does exist; just used the wrong endpoint. The right
  URL pattern is likely
  `https://mesonet.agron.iastate.edu/api/1/nwstext/{product_id}` but
  finding product IDs requires a separate search step that I didn't
  pin down. **Retry candidate.** This would let us find historical
  Mt Holly CFW from known storm dates (Oct 30 2025 etc.) without
  waiting for live events.
- **NWS alerts archive at api.weather.gov.** Only retains active +
  recently-expired (24–48 h). Cannot pull historical events. Not a
  bug; documented behavior.
- **Stevens Institute NYHOPS forecast.** Didn't investigate the AJAX
  layer behind their UI. They run an excellent operational forecast
  model for Sandy Hook surge specifically. **Retry candidate** —
  inspect their JavaScript app's network calls to find a JSON
  endpoint.

### Plan-B architecture (what we shipped)
Main script tries NWS Coastal Flood product first; if no active event,
falls back to "current surge persists" (today's observed surge applied
forward). This means:
- **Routine days:** surge persistence (rough but adequate when nothing
  is brewing)
- **Active coastal storm days:** NWS forecaster-vetted tide projections

This is actually what the Borough's emergency management uses. The
gap from ETSS would have been having always-on numeric surge; we
have it only when forecasters bother to issue a product, which is
the moments that matter.

---

## 7. Future work (prioritized)

### High value, near-term
1. **Validate NWS parser against next real event.** Will happen on its
   own. When a Coastal Flood Warning/Advisory fires in Eastern Monmouth,
   run `python3 nws_surge_parser.py` and confirm it parses cleanly.
   Tighten regex if needed.
2. **Historical statistics project** (`HANDOFF_historical_data.md`,
   already in Claude Code). Pulls all NOAA Sandy Hook hourly data and
   computes hyperlocal flood-event statistics using *user's* 6.58 ft
   threshold, not the dashboard's 7.20 ft. Outputs return periods,
   sea-level-rise trend, monthly frequency.
3. **Investigate Aug 21 2025 NWS Coastal Flood Warning.** The search
   that gave us the parser sample was for a real event — Sandy Hook
   forecast 8.0 ft at 7 PM Aug 21, surge +2.4 ft, Moderate category.
   The user has no logged flood event for Aug 21. Worth checking
   whether they were away, weren't paying attention, or the forecast
   didn't fully materialize.
4. **Field-measure the lawn/walkway step elevation.** Current 4.58 NAVD88
   is the midpoint of an inferred 4.54–4.63 range. A precise reading
   tightens the moderate-flood threshold.
5. **Add seasonal context line to email** (the "B" item we deferred).
   Use `avg-num-floods-by-month.csv` to add e.g. "October avg: 4.4
   flood events/month at Sandy Hook (likely ~10 at your house).
   You've had 3 so far this October." Small change to `render_email()`.

### Medium value
6. **Decompose the +0.40 local enhancement.** Currently treated as a
   constant. With 8–10 more events, may correlate with wind direction
   / wind speed / pressure / lunar phase. Becomes a function of those
   instead of a constant.
7. **Calibrate cold-weather override threshold.** Only Feb 22–23 in the
   dataset. Several more cold-weather high-tide events would refine the
   72-h, 32°F trigger.
8. **Verify Phase 1 reconstruction status.** If the road in front of
   342 has been rebuilt to the design (4.20 NAVD88) elevation, current
   thresholds shift up by ~0.04 ft (sub-inch). Field check or ask the
   Borough.
9. **Pluvial-only flooding test.** Does heavy rain at low tide flood
   342 Bay? No event in the dataset confirms or denies. Awaiting a
   suitable storm pattern.
10. **Borough drainage map.** Email Stephen Winters (Floodplain
    Administrator, swinters@highlandsnj.gov) for the storm sewer map.
    Would clarify Pathway B outfall locations exactly.

### Worth retrying later
11. **NOAA ETSS direct fetch from a non-residential IP.** Try from
    GitHub Actions runner, cloud function, or different network. If
    successful, gives us always-on numeric surge forecast.
12. **Stevens NYHOPS API inspection.** Worth a focused attempt to find
    the JSON endpoint behind their SFAS visualization. Better surge
    forecast for Sandy Hook than ETSS would have been.
13. **Iowa Mesonet historical NWS products.** Right URL pattern, would
    let us pull e.g. the actual Oct 30 2025 Mt Holly CFW text for
    parser hardening before relying on a live event.

### Speculative / nice-to-have
14. **Probabilistic ETSS (P-ETSS) ensemble.** 21 GEFS members → spread.
    Once ETSS works, P-ETSS gives probability of flooding directly
    rather than a point estimate.
15. **Bayesian seasonality update.** Use monthly priors to flag unusual
    forecasts (e.g., July moderate flood = high anomaly, worth extra
    attention).
16. **USGS Total Water Level Forecast API.** Mentioned but not
    explored. Their REST API serves coastal forecasts including
    Sandy Hook.
17. **Notification logic.** SMS / push for severe events, suppress
    daily emails on "dry" days (current behavior sends one every day).
18. **Multi-location.** Same model architecture, different anchors,
    for neighbors. "Atlantic Highlands Barnacle." Marketable as a
    template — `barnacle` repo already named for this expansion.
19. **NJ LiDAR DEM extraction.** Currently use surveyed plan
    elevations. LiDAR would let us see the full neighborhood
    microtopography and produce a flood-extent map for any given
    Sandy Hook level.

---

## 8. Outstanding open questions

These came up but weren't resolved:

- Was the Aug 21 2025 forecast Moderate flood actually a Moderate event
  in reality, and did 342 Bay flood that day? (User doesn't have it
  logged. Could mean: not home, didn't notice, or forecast over-shot.)
- Why is the +0.40 ft local enhancement so consistent across 4 events
  with very different wind/pressure conditions? Suggests structural
  factor (drain backflow geometry, road topography) more than
  meteorological one. Worth investigating with 4–6 more events.
- Does the rain term saturate at 8 inches as the `tanh` function
  assumes, or higher? Only Oct 30 and Dec 19 sample the rain regime
  meaningfully.
- Does the cold weather override apply to a single overnight freeze,
  or only to sustained below-freezing periods? Only one cold-weather
  observation in the dataset.

---

## 9. Practical immediate next steps for the user

1. **Resolve Claude Code's question:** Use **v0.5** thresholds (which
   match the HANDOFF_historical_data.md you gave it). The HANDOFF was
   correct; v0.4 had bugs; v0.5 reconciles. The historical-stats
   project can proceed.
2. **Deploy the daily script:** Use `HANDOFF_deploy_script.md` with
   another chat or Claude Code. Pick cron-on-Mac or GitHub Actions.
3. **Wait for next coastal flood event.** When one happens, run
   `python3 nws_surge_parser.py` during the event and verify it parses.
   Paste output here if it doesn't.
4. **Consider seasonal context line** as a small follow-on once the
   above are running.

---

## 10. Voice notes for future-Claude conversations

For when you come back to a fresh chat with this document:

- The model is small. Don't over-engineer. Five constants, three
  inputs, one formula. Everything else is plumbing.
- The user has done the hard part — the empirical event labeling and
  the elevation reading from engineering plans. Trust those numbers.
- Surge handling is the open frontier. NWS Coastal Flood products are
  the lowest-friction good-enough source; everything else is worth
  trying but not blocking.
- The user is technically capable and has good taste. Long explanations
  of basic stuff aren't needed; offer trade-offs and let them choose.
- "The barnacle" as a project voice / mascot is intentional. Use it.

End of handoff.
