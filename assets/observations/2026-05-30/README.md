# 2026-05-30 — two-tide observation set

Two tides observed on this date, one calibration photo and qualitative
post-peak notes for the other. The 2026-05-31 PM tide (different,
follow-up event with measurements) lives in a separate sibling folder.

---

## AM high tide — 07:53 ET predicted

- **NOAA Sandy Hook observed peak: 4.592 ft MLLW at 08:06 ET** (vs
  predicted 4.355 at 07:53; surge +0.24, time delay +13 min — modest
  morning tide, no surprises).
- **Final logged barnacle forecast** (T−4.8 h, made 2026-05-30 07:06 UTC =
  03:06 ET): SH peak 5.014 → water 2.594 ft NAVD88 → all landmarks dry.
  Over-predicted SH by 0.42 ft via surge-persistence carrying yesterday's
  surge forward, but the outcome was *dry* either way (lowest grate at
  3.60 NAVD88 vs predicted 2.59).
- **Observation @ 08:21 ET, grate_SE**: dry. Photo expected in
  `grate-SE-proximal/` (filename TBD). Photo timestamp ~15 min after
  the AM peak; SH was ~4.56 ft MLLW at that moment.
- **Calibration verdict**: model agrees with observation (predicted
  dry, observed dry). One more "no false-alarm at modest tide" point.

## PM high tide — 20:07 ET predicted

- **NOAA Sandy Hook observed peak: 6.538 ft MLLW at 20:36 ET** (vs
  predicted 5.491 at 20:07; **surge +1.05 ft, time delay +29 min** — a
  meaningful event).
- **Final logged barnacle forecast** (T−4.57 h, made 2026-05-30 19:32
  UTC = 15:32 ET): SH peak 5.844, water 3.424 NAVD88 → "dry" regime.
  Actual SH peak 6.538 → **under-predicted by 0.69 ft even at T−4.6 h**;
  the regime should have been "street" at minimum. (CORRECTION: an
  earlier draft of this README claimed the hourly bot stopped logging
  this tide after T−11.6 h. That was wrong — I had a faulty grep. The
  bot kept logging hourly through T−4.6 h; the under-prediction is a
  real model/surge-persistence accuracy concern, not a workflow gap.
  See the "Hourly bot cadence" note below for the actual cadence
  finding.)
- **Observation: post-peak drive-by, ~21:00–21:30 ET (1–1.5 h after
  peak)**, no photos. User confirmed qualitatively:
  - water *surfaced over* grate_SE (i.e. the SE grate top, 3.60 NAVD88,
    was overtopped at peak — by inference from residual water at
    observation time + pocket fill, since water was still receding);
  - grate_SW is ~0.5″ lower than SE (~3.55–3.58 NAVD88), so SW was
    overtopped as well — not directly observed, inferred from SE;
  - pocket_SE_retention held water as it has on prior events.
- **Calibration verdict**: model under-predicted at T−11.6 h (and never
  got a closer prediction in the log because the hourly job didn't run
  through the afternoon — see note below). With the *observed* SH peak
  6.538 fed into the v0.6 model, water at 342 Bay would be 4.118 ft
  NAVD88 → grate_SE depth 6.2″, grate_SW depth ~6.6″, curb (4.16) just
  dry. The qualitative observation (SE/SW over, curb not observed
  flooded) is consistent with this either with or without the +0.40
  enhancement — this event does *not* discriminate +0.40 vs. 0 (both
  predict over-grate, under-curb). The discriminating events remain
  the 2026-05-18 set.

### Hourly bot cadence — investigation result

Investigated 2026-05-31. **The bot is not failing — it just isn't
actually hourly.** GitHub Actions throttles the `'0 * * * *'`
schedule:

- Over the last 7 days, **120 runs in 192 hour-slots = 62% coverage**.
- UTC hours that NEVER ran in those 7 days: **02, 04, 06**. Hours 08,
  10, 11, 12, 14, 16 ran inconsistently. The other hours (00, 01, 03,
  05, 07, 09, 13, 15, 17–23) are reliable.
- 51 normal-jitter gaps (60–90 min), 74 single-skip gaps (90–180 min),
  2 multi-skip gaps (>180 min, both ~4 h around 09–13 UTC).
- This is consistent with GitHub Actions free-tier load-shedding;
  scheduled cron is best-effort, not guaranteed.

So my earlier "the bot stopped logging this tide after T−11.6 h" was
just a misread of the log — the bot actually kept logging through
T−4.57 h on the 5/30 PM tide. The under-prediction at T−4.57 h
(SH 5.844 vs actual 6.538) is a **real surge-persistence accuracy
issue** at moderate short-term lead times, not a workflow gap.

Operational implication: convergence charts have ~1.5–2 h effective
resolution, not 1 h. Worth noting in HANDOFF as a known limitation
rather than a fix-it-now bug.

---

## Photos

- `grate-SE-proximal/` — AM 08:21 ET photo (dry above the grate, ~15
  min post-AM-peak).

(PM tide had no photos.)
