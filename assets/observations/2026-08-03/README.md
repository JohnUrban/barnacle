# 2026-08-03 — Pluvial flood #6 (measured), ~10:33 AM ET peak

**Peak: ≈ +13.8″ vs SW grate (water ≈ 4.67 NAVD88), ~10:31–10:36 AM.**
4th-largest measured flood (after #5 +19.9″, #4 +18.7″, 7/6 +15.0″).
Pure pluvial: bay 2.31→2.95 NAVD88 through the event — below every
grate, full drain head the whole time. The peak is bracketed by TWO
landmarks ~¼″ apart ("a little above the lawn step [4.66], not quite
the porch-step bottom [4.68], but close-ish") — the tightest peak fix
of any event, from live narration alone.

## Timeline (ET; full dictation in `flood-measurements.txt`)

| time | what |
|---|---|
| ~02:34 | separate overnight episode, tank day-max +5.8″ (not observed) |
| 10:02–10:12 | ramp: MRMS catchment mean 0.15→0.52 in/hr |
| 10:14–10:26 | violent phase: 1.35→**2.84** in/hr mean @10:22 (hill max 3.97); ~14 min |
| ~10:25 | onset drain JETS at upstream Bay Ave grate + untracked grates further up (network pressurized at onset — differs from #5's corner-first order) |
| 10:26 | water over the sidewalk (≥ +9.7″), rising |
| 10:28 | rain breaks (0.94) → tail 0.2–0.36 in/hr |
| 10:29 | water at the lawn step (+13.7″) — ~+1.3″/min rise |
| ~10:33 | **PEAK ≈ +13.8″** (lawn-step/porch-base bracket) — ~11 min after the rain-rate peak |
| 10:40 | slightly under the lawn step (~+13.4″) |
| 10:45 | nearer sidewalk than lawn step (~+11″) |
| 11:03 | Flash Flood Warning WEA blast (town-wide) — **after** this corner's peak; Barnacle alert (email+ntfy+SMS) delivered 11:03:41 |
| 11:40 | high tide ~2.95 NAVD88 arrives with radar quiet — no compound event |
| ~13:06 | catchment 0.0 in/hr from here on; single-burst day confirmed |
| 13:50 | post-event survey: **no mud on driveway** (mud-tracer negative — see below) |

## Scores (kept separate per playbook)

- **Forecast skill (what the day said):** morning forecast carried
  rain-flood risk for today (day card + elevated pluvial risk; user:
  "Barnacle did well to predict rain flood risk"); burst-potential
  envelope ~+15.6″ vs actual +13.8″. Alert pipeline escalated on the
  FFW — first live firing of the Phase-2 transactional path, 3/3
  channels confirmed. Ingestion latency note: NWS's first FFW cut was
  ~10:36; Barnacle's hourly look caught it at 11:00.
- **Live nowcast (as-run):** tank street estimate peaked **+13.2″ @
  10:50** (−0.6″; +17 min late). The 11:03 projections during the
  climb read +13.5–15.8″.
- **Physics hindcast (true 2-min rates, v0.10.1, V=0 @ 09:50):**
  **+13.4″ @ 10:42** (−0.4″ magnitude; +9 min late). See
  `analysis/hydrograph.png` (doubles as the model-test figure —
  agreement is sub-half-inch; all-anchors refresh queued).
- Timing: observed ran ~10–15 min AHEAD of both model passes —
  consistent with MRMS underreading the core (hill max 3.97 vs mean
  2.84; #5 precedent) and/or shorter true lag on this cell.

## Evidence & methods

- 6 ledger rows in `data/labeled_observations.csv` (5 water fixes +
  mud-tracer negative); raw dictation in `flood-measurements.txt`.
- Gauge sanity: SH 6-min vs Battery, 09:00–12:30 ET — both smooth,
  zero ≥0.5 ft jumps; no despike events. Clean.
- MRMS: 31×2-min PrecipRate frames 13:50–14:50Z + QPE (burst total
  ~0.67″ box-mean in the 14–15Z hour) cached in
  `history/data/mrms/mrms_extracted.csv`.
- **MUD-TRACER METHOD (user, new this event):** rain floods here run
  muddy and deposit mud where water stood; the driveway marks
  higher-water events. No mud on driveway = independent upper bound
  confirming the peak stayed lawn-step-class and there was no second,
  larger event while unobserved. Candidate standard post-event step.
- **Third-party:** `third-party/` holds a Highlands OEM photo (via
  Joe Martucci / JoeMartWx Facebook, posted ~noon) claiming 8–12″ of
  water at the 140–144 Bay Ave block (Fresh restaurant; arrow at the
  hydrant) — town-wide extent of the same burst, DOWNTOWN drainage,
  not this catchment. **Date unverified:** the file is a Facebook
  re-encode (FBMD fingerprint, no EXIF/XMP, composite banner) so
  metadata cannot confirm capture date; in-scene evidence (active
  rain on the floodwater, summer foliage/tents/bunting, post context
  = today's warning) supports but does not prove today. True original
  would need Joe/OEM (joe@cupajoe.live).
- **Downtown elevation vs ours (user hypothesis, confirmed):** USGS
  3DEP LiDAR puts ground at 144 Bay Ave at **3.28 ft NAVD88** —
  BELOW our lowest grate (3.52) and ~1.1 ft below our road middle
  (4.36). With OEM's 8–12″ of water, the downtown water surface was
  ~3.9–4.3 NAVD88 vs 4.67 here — the flood was NOT worse there;
  depth-over-grade was comparable (8–12″ vs ~12″ over our lowest road
  corner), ours marginally higher. The devastation difference is
  **freeboard**: those shops/houses sit at grade (doorsills ~½ ft up),
  so a foot of street water enters buildings; 342's porch deck sits
  at 8.08 NAVD88, ~4.4 ft above its street. Same water, different
  exposure. Corollary: at 3.28 ground, downtown's tidal first-water
  is ~6.10 ft MLLW — it floods ~0.24 ft of tide EARLIER than our
  corner does.

## Infrastructure findings (this event as live test)

1. **Cadence gap at onset:** last scheduled nowcast finished 09:56,
   burst began 10:02, water crossed the sidewalk before the next slot
   fired. Claude ran the nowcast manually 10:29–11:40 (site/widget
   live strip restored ~27 min after onset). The audit's open item —
   nowcast off best-effort cron — has now cost visibility during a
   real event.
2. **day-max memory regression (bug, open):** tank day-max correctly
   reached 13.2″ @10:50 across racing writers, then a ~15:14Z cron
   run that started from a stale checkout recomputed 9.0″ and
   overwrote it; the site's SO-FAR-TODAY automatic line understates
   the day. Fix direction: refresh `docs/nowcast.json` from origin
   immediately before the day-max merge (or make the merge
   monotonic-per-day at push time).
3. Stateless tank window: each nowcast run integrates from V=0 over
   its ~1-h frame window — fine mid-burst, understates once the burst
   is older than the window. Known design; document, don't fix yet.
4. WEA/FFW comparison: official warning landed ~30 min after this
   corner peaked. Barnacle's morning risk call + live radar strip is
   the coverage that exists before official products.
