# 2026-09-13 — Event #9: dawn pluvial flash flood (measured ≈ lawn-step level)

**Peak: water level with the lawn-step top = +13.7″ vs SW grate,
photographed at 7:01:23 and still there 7:04:21 [VERIFIED, photos
14/18 EXIF]. Not the highest — but "I've rarely seen it flood with
such speed and ferocity"** — and the 18-photo EXIF timeline proves
it: **sidewalk edge to peak in FOUR minutes** (6:57:02 → 7:01:23),
intersection fully covered by 6:58:26. Pure pluvial on a RISING
mid-tide (bay ~0.8→2.0 NAVD88 — below the grates, full drainage;
NOT a dead-low like #8). Ninth measured flood; ledger rows
T07:10 [STATED, pre-photos] refined by T06:57:02 / T07:01:23 /
T07:02:13 [VERIFIED] + T07:30 recession.

- **Rain [VERIFIED, MRMS cached]:** first catchment rain 10:48Z
  (6:48 AM ET — user woke minutes earlier; matches "6:45–6:50").
  Six minutes later the core was ON the house: **10:54–10:58Z
  box-mean 3.16→2.62 in/hr, house point 3.78 in/hr, box-max 4.05
  up-hill/east**. Collapsed below 0.8 by 11:00Z, drizzle after
  11:12Z. Total ~0.4″ box-mean in ~25 min — a small storm delivered
  brutally fast (compare #8: ~0.5″, gentler peak).
- **Sequence [STATED, live account 07:39]:** woke → rain starting →
  moved van to the lot past the SW corner ("raining very hard...
  pooling but not backed-up grates yet") → walking back, grates
  ejecting + Central covered SE→SW ("not substantial at first") →
  **very fast** rise to intersection covered, level with lawn step —
  "water came flooding like a river from the upstream direction of
  Bay" (east — Snug Harbor / Water Witch): the hillside catchment
  delivering as visible open-channel flow down Bay Ave, consistent
  with box-max sitting east/up-hill. By **7:30 well-receded,
  driveable**.
- **Gauge sanity [VERIFIED]:** SH 6-min clean (max swing 0.18 ft;
  Battery corroborates). Rising limb: 3.38 MLLW @6:30 → 4.15 @7:00
  → 4.81 @7:30.
- **Hindcast (`history/scripts/event_hindcast.py`, despiked-gauge
  bay): +12.2″ @ 7:14 ET** — `analysis/hydrograph.png`, now with
  the four photo points overlaid. Verdicts — ALL THREE standing
  biases in one event, and the lag one decisively: (1) **the
  street was at peak (7:01) before the modeled rise even reached
  6″** — heavy rain 6:54 → real response in ~3–7 min vs the
  15-min lag's 7:14 peak, **10–13 min late; the cleanest lag
  falsification in the archive** (an earlier pre-photo note here
  called the timing "good" — WRONG, corrected same morning);
  (2) peak **−1.5″ low** with the point≫box near-core signature
  (3.78 vs 3.16) — 4th low-side confirmation; (3) recession
  overhold — tank ~9″ above the curb at 7:30 vs "driveable
  roads" — 4th overhold confirmation.
- **Driveway [VERIFIED, photos 15–16 @ 7:02]:** water ENTERED the
  driveway, line partway up the LOWER ramp, at corner stage
  ~+13.7 — the v0.10.2 "entering" observable firing at/just below
  its bracket's 13.8 lower edge. Consistent with the spec's
  mud-lags-water caveat (#6's negative was MUD) and the ramp
  geometry (apron floods first). Registered threshold 4.67 stands
  within its stated uncertainty; refine only via a version bump.
- **First flood of the watch window [STATED]:** overnight Flood
  Watch (surfaced by Barnacle ~2 AM Sept 12 per user); on waking,
  "little evidence that it had already flooded" — this was the
  window's first flood, not a repeat.
- **Forecast skill — QUALIFIED, SPLIT-PATHWAY HIT [VERIFIED]:** the
  last published overnight forecast was generated **03:14:36Z
  (11:14:36 PM EDT), 7 h 47 min before the photographed first peak**
  ([as-run JSON at `3a6c96f`](https://github.com/JohnUrban/barnacle/blob/3a6c96faf7ebbf98c3e69322948aa5c1ddbbcedc/docs/forecast.json);
  the later 03:56Z nowcast did not replace `forecast.json`). There is no
  honest Brier-style single score: `pluvial_risk` was categorical and
  the burst scenario had no probability or exact clock. Component
  scoring preserves what the product actually claimed:

  | Component | As-run forecast | Verified outcome | Score |
  |---|---|---|---|
  | Hazard + pathway | `ELEVATED` pluvial risk, active Flood Watch, thunderstorms; tidal regime dry | Two rain-driven floods; first was pure pluvial with bay below the grates | **HIT** |
  | First-round magnitude | Untimed 3.0 in/hr burst scenario: **+16.4 to +17.9″ vs SW grate** (4.89–5.01 NAVD88) | **+13.7″** at 07:01:23 ([ledger rows 180–184](../../../data/labeled_observations.csv)) | **NEAR HIT, 2.7–4.2″ high; one severity class high** |
  | First-round timing | Burst-capable window covered 07:01, but hourly-QPF hydrograph showed no rain water then and first crossed the grate at **09:50**, peaking **+5.6″ at 10:30** | First rise 06:57; peak 07:01; driveable by 07:30 | **TIMING MISS, ~3.5 h late** |
  | Second-round timing | Predicted street-water window **09:50–11:31** | Compound crest photographed 10:03–10:12; driveable by 10:59 | **HIT** (peak clock 18–27 min late) |
  | Second-round magnitude | **+5.6″ vs grate**, street regime | **~+7.2–7.5″**, at/near curb | **NEAR MISS, 1.6–1.9″ low; one class low** |
  | Rain forcing | Hourly QPF peak **0.183 in/hr**; convective burst proxy **3.0 in/hr** | MRMS box mean **3.16**, house **3.78**, box max **4.05 in/hr** | QPF **MISS** (17–22× low); burst proxy **HIT** for box mean (5% low) |

  Bottom line: the warning layer did its job and the crude convective
  proxy was directionally strong. The deterministic hourly-QPF path
  missed the fast dawn cell entirely, while its predicted window aligned
  with the later compound episode. Event-time nowcast/alert skill is **not
  scorable** because the production arms were dark; do not count missing
  output as either a meteorological hit or miss.
- **OPS FAILURE [VERIFIED — see BACKLOG post-mortem]:** Barnacle was
  **dark for the entire event** (no nowcast or forecast publication
  03:56Z–11:5xZ): GitHub Actions queue wedged since ~04:15Z (runs
  stuck "queued", later runs replaced-and-cancelled) AND launchd
  half-A silently wedged since 2026-09-03 10:32Z (an exhausted
  push-retry left an unpushed clone commit; every later tick's
  pull conflicted, aborted, exited 0). **No radar alert was
  possible; the dispatch-after-push storm path remains untested.**
  Tick script hardened at all three wedge points same morning
  (clone now disposable-by-design); an external cron trigger (the
  third, GitHub-independent scheduler) got its third strong field
  argument — but this one was a GITHUB-side wedge, which that trigger
  alone would NOT have fixed for radar runs (they execute on
  Actions); it would have kept dispatch attempts flowing and made
  the wedge visible sooner.

Photos: 18 committed (EXIF + GPS intact, no identifiable people;
descriptions in `barnacle-2026091-descriptions.txt`). All-anchors
refreshed to NINE. Remaining: edge_20260913 map points require the
user's pick_coords selection; photo GPS alone is only ±few m and does
not identify the intended visible water edge.
