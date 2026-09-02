# 2026-08-27 — Evidenced, unmeasured pluvial flood (user away)

**No direct street measurement — NOT in the measured-event rankings.**
The user was in California; evidence assembled 2026-09-02:

- **Radar [VERIFIED]:** MRMS catchment box-mean 1.9–3.8 in/hr
  sustained ~18:30–19:14Z (2:30–3:14 PM ET), peak **3.8 in/hr at
  2:58 PM** — more total water (~2.15″ in two hours) than event #8.
  Frames cached in `history/data/mrms/mrms_extracted.csv`.
- **Tank hindcast [INFERRED]:** **+16.1″ @ ~3:24 PM ET** (bay
  −1.30 NAVD88 dead low, full drain) — `analysis/hydrograph.png`,
  via the shared `event_hindcast.py` recipe. Given the model's
  recent −1–2″ near-core bias, the true peak plausibly reached
  +15–18″: top-five territory, unwitnessed.
- **Residue [VERIFIED, per the residue doctrine]:** on 2026-08-29
  the user found mud across the Central Ave sidewalk, near the fire
  hydrant, and UP THE DRIVEWAY. Driveway mud-reach matches event
  #8's photographed water extent at ~+13.9″, and event #6 (+13.8,
  driveway-negative) bounds the threshold — so residue alone puts
  this event AT OR ABOVE lawn-step class [INFERRED bound].
  Preservation held (presence is robust to later wash; deposit was
  heavy enough to survive to 8/29).
- **Witness [STATED, second-hand]:** the user's brother (cat visit)
  reported flooding and photographed Route 36 flooding elsewhere in
  Highlands (photos not yet in repo — add to `third-party/` if
  obtained).
- **Barnacle's calls [VERIFIED]:** pluvial risk escalated through
  the day; **two alert deliveries** — 10:43 AM (Flood Watch) and
  2:35 PM (Flash Flood Warning, mid-burst) — hitting the daily cap.
  The user saw the flood prediction from California: directional
  confirmation of the full alert chain.
- **Coverage gap [VERIFIED]:** nowcast published at 12:53 PM, then
  NOTHING until 7:40 PM — the launchd half of the scheduler was in
  California with the user's laptop, and GH cron alone collapsed
  across the entire storm. The strongest field evidence yet for the
  external-cron half-B (BACKLOG).

Ledger rows: `data/labeled_observations.csv` 2026-08-29 (residue) —
the flood itself has no observation row (nothing was directly
observed at the corner).
