# 2026-08-07 — Pluvial flood #7 (measured), crest ~6:40 PM EDT

**Crest: +15.0–15.8″ vs SW grate, most likely ~+15.4 (~4.80 NAVD88),
~18:40 EDT.** Bracketed by a photo-timed rise (porch base +13.9 at
18:37:00) and a receding tape point (+14.9 at 18:43); backcast along
the measured recession slope (−0.2 in/min). **Ties the 7/6 anchor
(+15.4) for 4th of 7 measured street peaks.** Pure pluvial on a
DEAD-LOW tide — bay 0.77 NAVD88 (−33″ below the grates) at onset, the
largest drainage headroom of any measured event.

A SURPRISE event: morning QPF carried ~nothing; no NWS flood product
existed at onset (Flash Flood Warning cut at 18:39 — *after* the lawn
step was underwater). The 18:20 burst frame (4.40 in/hr catchment
mean, revised 4.4+) is the **2nd-highest rate on record** (after #4's
5.53).

## Timeline (EDT; dictation in `flood-measurements.txt`, photos in `images/`)

| time | source | what |
|---|---|---|
| 18:02 | MRMS | pulse 1: 2.14 in/hr, brief |
| 18:14–18:36 | MRMS | main burst: 1.73 → **4.40 @18:20** → 3.97 → 3.85 → 2.0 |
| ~18:26 | live report | water over the sidewalk (≥ +9.7), rising |
| **18:33:16** | **photo 7 (EXIF)** | **level with the LAWN STEP (+13.7)** |
| **18:37:00** | **photos 10–11 (EXIF)** | **bottom of first porch step (+13.9)** — rise decelerating as rates fell |
| ~18:40 | backcast | **CREST ~+15.4** (window 18:37–18:43) |
| 18:43 | tape/report | +14.9 (1″ up the riser), RECEDING; rain stopped |
| 18:47:44–53 | photos 12–13 | supplementary recession views |
| 18:49 | report | level with lawn step (+13.7); −0.2 in/min |
| ~18:52 | report | light rain resumed → recession slowed, momentary steady state (live tank-balance demonstration) |
| 18:58 | report | +11.7 (2″ above sidewalk); recession resumed |
| 19:04 | report | sidewalk AT lawn step exposed; TILTED POOL along the swale (2nd event confirming non-level recession) |
| 19:07 | report | SE/SW grates draining; NE/NW still discharging (north-pair tail, 3rd confirmation) |
| ~19:16 | household-2 | ~sidewalk-top level [STATED 50–60%] — first second-observer point |

## Scores (kept separate per playbook)

- **Forecast skill (what the day said):** miss — QPF-blind surprise
  (the documented convective weak link). NWS FFW arrived at 18:39,
  ~6 min before the crest; Barnacle's alert-ingest path delivered
  email+ntfy+SMS at 18:57 (3/3), during recession.
- **Live nowcast (as-run):** the 18:17 run saw pulse 1 but computed
  street +0.0 (15-min lag + stateless window); an **18-min publish
  gap (18:17→18:35) covered the entire rise**; the 18:35 run's
  +10.9″/proj +16.9″ was honest but its headline word was "LIGHT"
  and the widget's outlook headline said "NO FLOODING" over the red
  live line. No alert pathway existed from radar. All three failures
  fixed same evening (see below).
- **Physics hindcast (true revised 2-min rates, V=0 @17:50):**
  **+16.9″ @18:50 vs measured ~+15.4 @18:40** — +1.1–1.9″ high,
  ~10 min late; the rising limb threads the three photo-timed
  observations almost exactly (`analysis/hydrograph.png`). First
  HIGH-side miss of the tank. Reconciliation of the live-run errors:
  the live rising-limb undershoot was **MRMS first-pass latency**
  (frames revised upward between runs: 18:24 read 3.66 live, 3.97
  final), not physics; the live falling-limb overshoot (+16.6 while
  the street drained) was the revised-data reintegration in a
  stateless window. Model-session hypotheses for the residual high
  bias, NOT retuned here: (a) MRMS upward revision overcorrects
  small cells; (b) k_out underestimates true drainage at maximum
  head (bay −33″ — deepest ever measured; drains may exceed 3.5/h
  e-fold with that much gradient).

## Evidence & methods

- 10 ledger rows (incl. photo-verified refinement row + household-2
  point with stated confidence); dictation file; 13 photos with EXIF
  times (extraction: PIL in `~/.barnacle/venv`); 2 surface
  screenshots (site "LIGHT", widget "NO FLOODING" + live line).
- Gauge sanity: SH vs Battery 17:30–20:30, both smooth, 0 spikes.
- MRMS: 37×2-min PrecipRate + QPE (hour ending 19:00 EDT: **1.59″
  box-mean / 1.86″ point** — most of the storm in ~35 min) cached in
  `history/data/mrms/mrms_extracted.csv`.
- Second observer (household) debut; observer-calibration caveat
  logged honestly; a 5-minute dry-day landmark walk-through would
  make household-2 readings anchorable.
- Mud line on the riser: still collectable for crest refinement.

## Infrastructure consequences (all SHIPPED same evening / weekend)

1. **Radar-fed alerting** — live street/projection now ranks alerts
   through the transactional pipeline + workflow dispatch;
   fail-closed freshness; falling-trend guard (projection never
   alerts during recession).
2. **Worst-truth headlines** — strip shows projected class while
   rising / drain-clock class while falling; widget v7.25a overrides
   its outlook headline with the live class; SMS + email lead with
   the warning.
3. **Scheduler** — revisit trigger tripped by the publish gap;
   half-A (launchd true-10-min local tick, dedicated clone)
   INSTALLED 2026-08-07 evening; half-B (24/7 external cron) plan in
   `history/plans/external-cron-scheduler.md`.
4. **Quiet hours (2026-08-09)** — all channels hold 20:00–07:00
   local unless the alert concerns THAT night (live radar, pre-7AM
   tide, active Warning); held alerts deliver after 07:00. Driven by
   1:23/2:18 AM texts about a next-evening minor tide; the 1:23 AM
   email also exposed that emails lacked the warning-first fix —
   subject/body now lead with the alert label.
