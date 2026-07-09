# 2026-07-09 — Flood Watch day, near-miss + the grate-coupling measurement

No flood. A **Flood Watch** (14:03–24:00) and later a **Flash Flood
Warning** (14:42–18:45) were active while a convective system
approached; it veered northeast and mostly missed Highlands
(~0.4″ total here). First day the model ingested NWS alerts
(shipped mid-event after the user noticed Barnacle silent under a
live watch): site/widget escalated possible → elevated from the
alerts while the smeared QPF numbers (0.05 in/hr, PoP 52%) never
tripped a numeric trigger.

## The measurement (raw: flood-measurements.txt)

**14:28 ET — water in the SW grate throat 9.25″ below the grate
top** (= 2.749 NAVD88), taken during light rain as a false-alarm
check ("is the tide over the grates?" — it wasn't).

| Quantity | Value |
|---|---|
| Concurrent gauge (14:24, rising) | 5.71 MLLW = 2.888 NAVD88 |
| Measured local | 2.749 NAVD88 |
| Local − gauge | **−0.139 ft** |
| Model's own pre-recorded call (per-tide snapshot, forecast wind S 10 mph → offshore) | −0.13 ft |
| Prediction vs tape | **0.009 ft ≈ 0.1″** |

Significance:
1. **Wind adjustment validated far outside its calibration range** —
   lowest gauge level ever measured (5.71 vs the 6.17–7.29 range)
   and near-calm wind (obs S 3.3 kt): the direction-only design
   (no speed threshold) gets its first direct support. Open
   question: if −0.13 appears at 3 kt, is it wind stress at all, or
   a standing bay-vs-gauge offset with direction as correlate? A
   calm ONSHORE-wind grate reading discriminates.
2. **Grate–bay coupling holds at bay 2.89 NAVD88** — the throat
   read the wind-adjusted bay through the pipes, so the drain
   network is backwatered at least this low. The decoupling floor
   (= outfall/invert control elevation = the physically-correct
   head-dependent drainage knee, currently a 3.0 placeholder) is
   LOWER; find it with the falling-tide stall experiment (HANDOFF
   "Other likely sessions" §2): track a throat down a falling tide
   until it stalls while the gauge keeps dropping.
3. Caveat: light rain was draining through the system — a flowing
   pipe carries a gradient, so a small part of −0.139 could be
   hydraulic rather than bay offset.

Logged: 1 row in `data/labeled_observations.csv` (14:28, grate_SW,
−9.25″). Day-max archive records the day as elevated / burst 0.74 /
potential 4.43 — a flagged day that didn't flood (the false-alarm
side of the alert-trigger calibration ledger).
