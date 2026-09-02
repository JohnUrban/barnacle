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
- **Witness record [STATED + photos, added 2026-09-02]:** the
  user's brother Kevin made the cat visit ~1:50–2:41 PM and drove
  home into the storm's peak. Texts (ET — confirmed by the user's
  2:17 PM screenshot-time cross-check and photo EXIF): 1:43 "It's
  flash flooding" + 1:44 WEA "no one should be driving" (the storm
  hit western Middletown BEFORE our catchment — radar shows our
  heavy rain from ~2:30); 2:59 "It's completely up the sidewalks";
  3:13 report of a violently smashed SUV from a speeding driver.
  Five photos, EXIF **3:03:36–3:08:54 PM** — inside the radar peak
  window: sheet flooding across a signalized divided highway
  (photo 1), a vehicle rooster-tailing through ponded lanes
  (photo 2), and a **NORTH 36 route shield over a bank-to-bank
  flooded roadway (photo 5)** — Route 36 confirmed by signage. GPS
  was stripped in transit (messaging preserves times, drops
  location); exact positions unknown — original files from Kevin
  would restore them. Photos 3–4 show identifiable faces and are
  HELD OUT of the public repo pending the user's decision
  (exclude / blur / include).
- **Timeline verdict (user's question, answered from radar+hindcast):
  CONFIRMED** — the corner flooding most likely began right at or
  just after Kevin's ~2:41 departure. Catchment heavy rain started
  ~2:30; street response (5–15 min delivery) ≈ 2:40–2:50; hindcast
  peak 3:24. That explains the absence of any "waded to the car"
  report, and the 2:59 "up the sidewalks" text — sent 18 min into
  the drive, minutes before photographing Rt 36 flooding — most
  plausibly describes Route 36, though the corner would also have
  been sidewalk-deep by ~2:55–3:05.
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
