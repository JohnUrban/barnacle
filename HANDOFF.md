# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-02 23:35 EDT.** Rewrite this WHOLESALE each update
(delete stale, never append); keep it under ~100 lines. `BACKLOG.md`
OPEN LOOPS is authoritative. Full pre-migration history:
`attic/HANDOFF-through-2026-08-03.md` (archival, not instructions).

## What this is

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar → depth at 18 surveyed landmarks;
hourly site/JSON bot, best-effort radar nowcast (10-min requested
cadence), transactional alerts (ntfy/email/SMS, daily cap 2), iOS
widget v7.24a, per-tide pages, and four-town street flood map. Model
**v0.10.1** (`model/v0.10.1.md`): tide pathway + dynamic pluvial tank.

## Where it stands

- Audit `2026-08-03-a2` found 5 high + 7 medium/low issues; Claude
  independently confirmed every finding. Phases 0–1 are CLOSED after
  Claude round-03 PASS: station-local clock, source-aged radar,
  fail-closed alert recovery, semantic gates/all-path CI, dispatch
  visibility, supply-chain pins/SRI, and external HTML escaping.
- Phase 2 is implemented for independent review: repository-relative,
  read-only v0.10.1 replay; versioned fit/hindcast fixture; six event
  goldens; stage/drain/rise/recession physics tests; exact evidence
  taxonomy; scratchpad dependency removed. **77 tests green**; model
  constants and outputs were not retuned.
- M1 facts were repaired with provenance: August 3 day-max +13.2″
  @14:50Z; observation corrected to 10:26; appended erratum clarifies
  the retained bay-time note means 10:18 AM.
- August 3 event #6: pluvial peak +13.8″ ~10:33 AM, fifth of six
  measured; evidence in `assets/observations/2026-08-03/`.

## RIGHT NOW

- Phase-3 wave 1 COMPLETE (2026-09-02 evening): seam 1 station_time
  + seam 2 rendering extracted (facade 10,339→7,007, all names
  re-exported); additive residuals closed (nowcast_schema_version,
  cadence SLO heartbeats + details ops line, erratum convention +
  test). Remaining seams (model_core, data_sources, ledgers, alerts)
  need a verified quiet weather window each.

- Ponding-dips layer shipped + v2 same evening: road-profile sags
  with cross-street-drain discount (71 pruned), two tiers (teal
  rain-only / purple tide-reachable low shelf), tap readouts, top-20
  GPS field list (history/data/ponding_top20.md). Validated: Rt 36
  valley detected; 342 corner correctly does NOT register (curb-
  scale, drain-driven — the calibrated model's territory), boundary
  documented in the explainer.

- **Event #8 (2026-09-01 ~19:25 ET):** pluvial peak ~+13.9″ (lawn-step
  bottom) on a DEAD-LOW bay; 19-photo EXIF timeline; nowcast's best
  showing (+14.3 projected 8 min early) but the radar alert LOST A
  RACE to the push and no text went out — dispatch now runs after the
  commit step (fixed 2026-09-02). Analysis DONE: hindcast +12.0
  (−1.9, +11 min — 3rd near-core-lag + tail-overhold confirmations);
  all-anchors now 7 measured.
- **2026-08-27:** evidenced-unmeasured flood while user traveled —
  radar 1.9–3.8 in/hr ×45 min, full-window hindcast +16.4 [INFERRED],
  mud up the driveway [VERIFIED residue], Kevin's witness timeline
  (cat-bowl EXIF), 2 alerts delivered incl. mid-burst FFW; nowcast
  dark 7 h (the launchd tick was in California) — strongest case yet
  for external-cron half-B. Witness bounds overlaid on the tank curve
  (companion plot): model −2.1″ short / ~19 min late vs the 2:43
  driveway bound — 4th near-core-lag quantification, first from
  testimony. Hindcast recipe now committed
  (`history/scripts/event_hindcast.py`).
- Aug 10–13 perigean-spring sequence: four consecutive photo-verified
  street-regime evenings logged (EXIF-timed, landmark-bounded,
  gauge-cross-checked; as-run errors ≤0.18 ft at 25–85-min leads) —
  tidal pathway visually verified 4/4.
- All-pathways peaks chart: full-history payload (2026-05-18→) with
  From/To picker (default view = 7 days + forecast; axis bounds now
  derive per-render — first-paint full-span bug fixed same day) and
  a low-tides toggle (astronomical lows, cached, default off).
  Per-tide twin exempt (ordinal axis — objective parallel-arms
  exemption).

- Audit a2 is CLOSED (round 05): Phase 2 reviewed PASS — cold
  reproduction verified, no retuning, M2/L2 closed; residuals below.
- Town map covers the FULL map view: nine towns (Highlands, AH,
  Leonardo, Sea Bright, Rumson, Fair Haven, Red Bank,
  Navesink/Locust, Belford edge) + all of Route 36 — 27,457 LiDAR
  street points, magma elevation view, historic-flood slider
  ticks/chips, Sandy-class range. Rain view remains Highlands-only.
- Phase 3 is the production-module split and additive evidence schemas;
  do it only after a quiet stretch and behind the new goldens.
- Accepted residual risk: GitHub's requested 10-min nowcast cadence is
  best effort and much slower in practice; cadence SLO monitoring and
  an external scheduler remain open.
- Newly characterized model debt: `_pluvial_fill()` can quantize a
  non-grid base downward by <0.1″ for tiny positive storage. Do not fix
  silently under v0.10.1; assess and version the behavior change.

## Key traps

- Bots commit continuously: explicit `git add`, commit → gate → push;
  on rejection fetch/rebase → gate again → retry. UNION ledgers.
- Station-local calendar decisions only through `_station_local_now()` /
  `_station_local_today()`; UTC is storage/transport. Run `date` before
  relative-time prose.
- `alert_state.json` is transactional delivery state. Recovery restores
  exact `origin/main` state or fails closed.
- Nowcast consumers trust `source_latest_utc`, not `generated_utc`.
- Frozen model replay: `python history/scripts/reproduce_v0_10_1.py`.
  It verifies behavior; it is not authorization to retune.
- Measured claims cite primary records; attic is never instructions.

## Start here

`AGENTS.md` → `audits/2026-08-03-a2/` → `BACKLOG.md`. Flood happening?
Read `PLAYBOOK.md` first.
