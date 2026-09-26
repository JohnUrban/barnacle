# 2026-09-26 — Event #10: nor'easter coastal-surge flood (first major surge event)

**Status:** live log complete for the morning tide; analysis PENDING (see
BACKLOG `event-#10-study`, `event-#10-rain-attribution`,
`event-#10-infrastructure-inquiry`). Primary record: every reading below is a
row in `data/labeled_observations.csv` (observer john), appended live.

## Crest
**+12.25 in over porch_step_base = 5.70 ft NAVD88 (+26.2 in vs SW grate),
~3.5 in over the first porch step top, 09:06–09:13 EDT** [VERIFIED user
readings]. Garage flooded to the back (≈3 in at the mouth, ≈1 in at the back,
08:53). Barnacle's SEVERE call (SMS 06:40) verified; pre-spike nowcast
magnitude (+25–28 in) matched the crest; timing ran ~1 h early.

## Timeline (corner, NAVD88; landmark + inches)
| EDT | Reading | ≈ Corner |
|---|---|---|
| 07:00 | Central SE→SW covered, other grates over | — |
| 07:15 | over curb, near lawn-step top | ~4.6 |
| 07:18 | level with lawn step | 4.66 |
| 07:22 | over lawn step, below porch base | ~4.67 |
| 07:28 | porch step base | 4.68 |
| 07:37 / 07:44 / 07:52 / 07:56 | +1 / +1.45 / +2 / +3 in up step wall | 4.76 / 4.80 / 4.85 / 4.93 |
| 08:13 / 08:18 / 08:21 / 08:25 / 08:29 | +5.1 / +6 / +6.25 / +7 / +7.5 | 5.11 → 5.31 |
| 08:37 | over first step top (+9 in over base) | 5.43 |
| 08:43 / 08:53 / 09:00 | +10 / +11.25 / +12 | 5.51 / 5.62 / 5.68 |
| **09:06 / 09:13** | **+12.25 (crest)** | **5.70** |
| 09:24 / 09:48 | +12 / +11.75 | 5.68 / 5.66 |
| 10:02 / 10:14 / 10:27 | +11 / +10.2 / +9.5 (rain resumes, moderate) | 5.60 → 5.47 |
| 10:50 / 10:59 / 11:10 / 11:21 / 11:42 / 12:06 | +8 / +7 / +6.2 / +5.2 / +3.2 / +1 (under first step) | 5.35 → 4.76 |
| 12:42 | level with lawn-step bottom | 4.33 |
| 12:52 | ~1 cm under the curb top | ~4.13 |
| 12:52 | roads virtually clear, intersection clear, safe to drive | — |

## Findings to carry into the study
- **Gauge vs corner:** Sandy Hook (NOAA-revised) peaked 5.83 at 08:54; corner
  peak 0.13 ft below it (inside the Jul–Aug tidal band −0.05…−0.21) but
  ~15 min later. Rising limb corner ran ~0.8 ft BELOW the gauge; falling limb
  up to +1.7 ft ABOVE it (11:42). SH had repeated live sensor spikes
  (06:42, 08:18–08:42) — Battery smooth.
- **Rain:** MRMS box-mean ≈1.26 in 04:00–10:30; burst 08:36–08:48 (1.67 in/hr).
  With drains shut (bay over grates) the tank adds ~+1.1–1.3 in through the
  rise and ~+2.4 in at ~09:02 — ≈ tide 23.8 + rain 2.4 at the crest
  [INFERRED; tank calibrated on low-bay events].
- **Drain-down:** a flat ~5.5 in/hr from 10:50 to 12:06 even after the bay fell
  below grate height (~11:24) — flow limited by something other than bay head;
  12:06–12:52 accelerates (8.7 → ~14 in/hr), mostly explained by the shrinking
  flooded area in the stage-storage curve; no clear step change.
- **Prequel 9/25 evening:** SH peak 7.57 MLLW / 4.75 NAVD88 (surge +2.1;
  gauge forecast err −0.07 ft via the NWS coastal product — first real
  validation of `nws_surge_parser.py`), yet the corner stayed DRY (user home
  20:00–20:30; wife home throughout).
- **Mechanism (user hypothesis, 11:38):** manually operated tide gates /
  check valves (police open and close them) hold the bay out until overtopped,
  then trap water. Consistent with all four observations; Borough 2021 Flood
  Mitigation plan documents Snug Harbor tide check valves and a North Street
  backflow sluice gate. Overtopping threshold bracketed 4.75–~5.4 NAVD88.
- **Ops:** SMS imminent pipeline fired for real (06:40); ntfy latin-1 header
  crash fixed live (11:09Z run failed, fixed before 13:09Z); nowcast day_max
  (34.5 in) inflated by gauge spikes.
