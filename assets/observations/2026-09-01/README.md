# 2026-09-01 — Event #8: evening pluvial flood on a dead-low bay

**Peak ≈ +13.9″ vs SW grate (bracket +13.7–14.2; water at the lawn-step
bottom, ≤½″ up it), window 19:23–19:27 ET.** Ties event #6's class.
Pure pluvial at maximum drainage: bay −1.2 to +1.0 NAVD88 (2.5–4 ft
below every grate), gauge clean. Nineteen EXIF-timed photos at ~1-min
cadence — rise, peak, and recession all photographed
(`flood-measurements.txt` = the annotated timeline; ledger rows in
`data/labeled_observations.csv` 2026-09-01).

## Timeline (ET; radar = MRMS catchment-box mean, cached)

| time | what |
|---|---|
| 23:04–06Z (19:04–06) | first drops on radar (point only) |
| 19:08–19:16 | **burst: ~1.9–2.0 in/hr box-mean sustained** (house-point 2.9–3.2 — core sat near the house); user's rain-start guess 19:08–10 EXACT |
| ~19:13–15 | flooding official (user); NE grate jetting by 19:16:01 (photo 1) |
| ~19:21 | over the curb (+7.7″; photo 8, 19:22:12, "a minute or so" in) |
| 19:18–20 | radar tapering 1.2–1.4 in/hr |
| 19:22 | rain break (0.35 in/hr); photo 12 (19:23:29) "slowing considerably" |
| 19:23–27 | **PEAK ≈ +13.9″** — lawn-step bottom (photos 11, 13) |
| 19:28 | receding, ~2″ off the step (photo 17) |
| 19:32 | below the curb (photos 18–19) — peak-to-curb ~6–8 min |

Onset-to-peak ~10–12 min; rain-start-to-flooding ~5–7 min — among the
fastest recorded, on the LOWEST bay of any measured event.

## Scores

- **Live nowcast (as-run): its best event yet.** The 19:15 ET run
  (23:15Z, `a39ad6704`) projected **+14.3″ while street_now read 0.0**
  — eight minutes before the actual ~+13.9 peak, error +0.4″. Cadence
  held ~10–13 min through the event (launchd + cron). Recession-side
  street_now 11.5→10.8→9.1 tracked the observed fall.
- **Alerting: correctly triggered, lost to a race (FIXED same
  analysis).** The 23:15Z projection crossed the moderate threshold →
  radar dispatch fired → but the dispatched forecast run checked out
  main seconds BEFORE the nowcast commit landed, read the pre-burst
  file, and evaluated sig "pluv" only (rank 3 steady, no send). Later
  runs saw proj < lawn threshold (12.1) + street "light" < standing
  pluvial rank. NO TEXT was delivered for a lawn-step flood the system
  had projected. Root cause: dispatch preceded the push. Fix shipped
  with this README: nowcast.yml dispatch steps moved AFTER the commit/
  push step (a failed push now correctly skips dispatch).
- **Forecast skill (day-ahead):** QPF-blind convective pop-up, as
  usual for this class; pluvial risk stood "elevated" generically.
  The event-specific signal was radar-only.

## Notes

- Second-fastest onset recorded; dead-low bay bounds the drainage term:
  ~10 min × ~1.9 in/hr box-mean at D=0.25 → the tank's rate-held
  projection (+14.3) essentially matched reality (+13.9) because the
  burst died right as the projection's holding assumption would have
  overshot — same shape as event #7.
- **Hindcast (2026-09-02, `analysis/hydrograph.png`):** true 2-min
  rates → **+12.0″ @ 19:36 — −1.9″ low and ~11 min late** vs the
  photographed +13.9 @ ~19:25. Two known biases, both now on their
  third confirmation: (1) the 15-min lag overestimates delivery when
  the storm core sits ON the house (point 2.9–3.2 vs box 1.9–2.0 —
  reality responded in ~5–7 min); (2) the recession over-holds under
  a light tail (tank kept water above the curb until ~20:10; the
  street cleared by 19:32). Notably the as-run rate-held projection
  (+14.3) beat the hindcast — the holding assumption compensated the
  lag+underread. Model-session queue: shortened/dynamic lag +
  tail-recession drainage are two of the standing six insights.
- QPE storm total (fetched 2026-09-02): 0.57″ box-mean in the
  event hour — a small storm, delivered fast, on a dead-low bay.
- `analysis/all_anchors.png`: refreshed with #8, then re-refreshed
  2026-09-03 to **all eight measured floods** — the audit sweep found
  event #7 (Aug 7) had never been added, and the stale six-event xlim
  had been clipping Oct 30 (the largest measured flood) out of the
  committed PNG entirely. Six frozen v0.10.1 anchors + ‡ post-cutover
  events (Aug 7, Sep 1) hindcast via the committed
  `history/scripts/event_hindcast.py` recipe.
- Photo 14–16: hydrant/driveway/sidewalk extent documents the Central
  Ave arm at peak — candidate edge_20260901 map points.
