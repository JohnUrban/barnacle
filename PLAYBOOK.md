# PLAYBOOK — flood-event operations (live + post-event)

The crown-jewel operational doc: what the human does DURING a flood
and the exact recipe an agent follows AFTER one. Battle-tested on
events #4 (7/9), #5 (7/18), #6 (8/3). Update it in the same commit
as any lesson that changes it.

## During the event (user, phone in hand)

1. Spot-check per the evolved protocol: notes-only tape readings,
   landmark-anchored (which landmark, inches above it), timestamped,
   fast cadence; mainly NE grate + sidewalk-under-lawn-step wall.
   Even "no water" observations are calibration data.
2. Photos are documentary: flood EXTENT (wet/dry lines!), drainage
   behavior (grate jetting), timestamps matter more than framing —
   EXIF DateTimeOriginal pins the timeline to the second (extract
   with PIL in ~/.barnacle/venv; event #7's crest bracket came from
   photo times).
   Every wrack-line photo = a future `edge_YYYYMMDD_*` map point.
3. RESIDUE EVIDENCE — optional detective work, NOT a standard
   measurement (user doctrine 2026-08-09; primary data is always
   the direct landmark-crossing observations). Mud lines: RAIN
   floods only (hillside transport + muddy grate jets; tidal water
   doesn't paint them), and only when preservation held — transient
   daytime downpour, abrupt clearing, sun-dried in place (may read
   slightly LOW). Continued rain washes the evidence; evening/night
   floods don't dry readably. ABSENCE of mud is evidence ONLY when
   presence would have survived (event #6's driveway-negative:
   valid; a rain-washed clean surface proves nothing). Expect NO
   mud data as a rule. Tidal floods leave WRACK lines
   (debris/seaweed/silt film) instead — those become
   edge_YYYYMMDD map points.

**In the session after (Claude, cold start) — follow this RECIPE
in order; every step has been needed at least once:**
1. Read `AGENTS.md` + `HANDOFF.md` + `model/v0.10.1.md`; event
   physics context lives in the per-event READMEs under
   `assets/observations/`.
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


## Live-support mode (agent, during the event — added 2026-08-03, event #6)
- Log every user report IMMEDIATELY: ledger row (strict CSV — run
  tests/test_csv_ledgers) + a line in the event's
  flood-measurements.txt. Timestamps: run `date` first; NOAA stamps
  are 24-hour station-local (10:18 = AM).
- Check the radar nowcast is publishing (docs/nowcast.json
  generated_utc); if the cron is in a gap, run forecast/nowcast.py
  manually and push each cycle (~6 min) until it recovers.
- Bay level + tide direction early: pure-pluvial (bay below grates,
  fast recession) vs compound (bay near/over grates) changes the
  crest call.
- Give the user the crest/recession forecast out loud (tank timing:
  peak minutes after the rain-rate break at full drain head).
- Residue evidence (mud/wrack) is OPTIONAL detective work under
  the step-3 conditions above — never expected, never primary.
- COASTAL-FLOOD events only: capture the NWS coastal product and
  validate nws_surge_parser.py against it — live in production,
  never yet seen a real product (BACKLOG passive collector c).
