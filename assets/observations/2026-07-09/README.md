# 2026-07-09 — EVENT #4: compound flash flood ON the high tide (top-3 all-time)

**The day had two acts.** Act 1 (morning–afternoon): Flood Watch,
near-miss appearance, and a calm-window grate measurement (kept
below). Act 2 (15:25–16:30): a convective core regenerated and
delivered **5.53 in/hr (MRMS point; hillside cells 6.2)** — nearly
2× the 7/6 peak — landing EXACTLY on the 15:30 high tide.
User verdict: as bad or worse than Oct 30 2025; water reached the
house FOUNDATION at peak (walkway side). All three worst events on
record are now rain-driven.

## Plots (analysis/)

- `event_hydrograph.png` — rain, bay (raw + despiked), and measured
  street water on one clock. THE two-source picture: street +18.7″
  while the bay never crossed the grates.
- `model_gamma_test.png` — both pluvial models vs the measured peak.
- `four_rain_floods.png` — all four rain anchors compared.

## Numbers

| Quantity | Value |
|---|---|
| Street peak (tape, lawn-step wall + porch-step wall agree) | **5.08 NAVD88 = +18.7″ vs SW grate @ 15:56** |
| Rain peak (MRMS 19:40Z) | **5.53 in/hr point / 6.2 hillside** |
| Sustained burst (15:25–15:55) | ~3.4 in/hr (≈2.3″ in ~40 min) |
| Catchment lag (rain peak → water peak) | **16 min** (7/6: ~20) |
| Rise rate | NE grate **+7.75″ in 12 min** (fastest recorded) |
| True bay base (despiked gauge) | ~6.0 MLLW ≈ 3.2 NAVD88 (3–4″ BELOW grate tops all event) |
| Rain-driven lift | ~+22″ above base |
| Ranking | #2-3 street-pool all-time: Oct 30 (≥+21) ~ 7/9 (+18.7) > 7/6 (+15.4) > Dec 19 (+11) |

21 timed measurements in `data/labeled_observations.csv`; raw notes
`flood-measurements.txt`; 28 photos in `images/` (uncategorized:
mostly porch → intersection / up Bay; some walkway → porch step;
a few porch → car zoom; image 1 = widget screenshot mid-event).

## Gauge malfunction (CRITICAL context for all 7/9 gauge data)

The SH sensor went insane during the cell: 6.02 → 11.87 MLLW
(would be #2 all-time) → back, with ±5 ft swings in 6-min steps,
15:12–15:48. **The Battery (same harbor) sat flat → instrument,
not water.** Decisive local proof: drains are bay-coupled (14:28
measurement below), so bay at 9+ NAVD88 would have level-driven the
street to +50″; measured +18.7″. The spike fed surge-persistence —
the widget read "SEVERE +40.2″" mid-event from garbage (image 1) —
and would have poisoned the accuracy ledger. **Fix shipped
same-night: `_despike_gauge()` median-window filter** in the peak
fetcher + the surge input (the 2026-07-08 neighbor-agreement check
was defeated by the 40-min-wide malfunction).

## How the model did

- **Pre-event forecast: under by ~8″ on INPUTS, not physics.**
  Elevated (alerts-driven, shipped that morning), burst analog 0.74
  in/hr → +10.9″ potential. Actual forcing 3.4+ sustained — the
  QPF-analog under-called (QPF showed ~0.24″/6h; the analog clamp of
  3.0 was itself exceeded). Feed the model the TRUE forcing and:
- **THE γ TEST (what this event settles): tanh is REFUTED, power-law
  validated in extrapolation.** tanh saturates at ~+16.5″ and cannot
  reach +18.7″ at ANY rate. The power-law brackets the peak
  (+2.5″ over at sustained 3.4; −0.1″ at the hour-equivalent ~2.5).
  First event in the regime where the two models diverge; the
  2026-07-07 MRMS finding (delivery grows with intensity — no
  saturation) is confirmed by an actual flood.
- **Recalibration decision: NO refit tonight.** Power-law error at
  event conditions is within the ±3″ class. The right next model
  step is formalizing DURATION (V = C·(R−D)·T — this event: 30-min
  burst ≈ hour-equivalent 2.5 in/hr), not nudging γ. The analog
  QPF→burst mapping now has two wildly different anchors
  (0.55″→1.7 vs 0.24″→3.4+): treat analog scenarios as floors, not
  estimates; MRMS nowcast remains the real fix.

## Act 1 (kept from the original write-up)

**14:28 ET — water in the SW grate throat 9.25″ below the grate
top** (2.749 NAVD88) vs concurrent gauge 2.888 → local−gauge =
−0.139 ft, matching the v0.8 offshore-wind adjustment (−0.13) at
the lowest gauge level (5.71) and lightest wind (S 3.3 kt) ever
tested. Also proves grate–bay coupling down to bay 2.89 — which is
what made the throat a truth-check against the gauge malfunction
90 minutes later. Falling-tide stall experiment (find the coupling
floor = true drainage knee) parked in HANDOFF.

## Open follow-ups

- Foundation elevation: user reports peak water AT the foundation —
  survey/derive `foundation` as a landmark (photo cross-fit
  possible from images/).
- edge_20260709_* wrack-line map points from photos once
  categorized (picker auto-opens photos; see assets/README).
- Duration-explicit input model (V = C·(R−D)·T) — event #4 provides
  the second (rate, duration, volume) triple.
- NWS gauge data for 7/9 will remain garbage in the 15:12–15:48
  window even in the verified product — the despike filter and this
  README are the record of why local numbers disagree.
