# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-08-03 18:21 EDT.** Rewrite this WHOLESALE each update
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

- Ask Claude to review audit-a2 round 04 Phase 2 implementation. The
  audit remains open until that independent review reconciles M2/L2.
- Town map covers Highlands, Atlantic Highlands, Leonardo, and Sea
  Bright: 7,227 LiDAR street points, bridge-over-water guard, widened
  base layer; rain view remains Highlands-only.
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
