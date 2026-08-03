# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-08-03 17:40 EDT.** Rewrite this WHOLESALE each update
(delete stale, never append); keep it under ~100 lines. `BACKLOG.md`
OPEN LOOPS is authoritative. Full pre-migration history:
`attic/HANDOFF-through-2026-08-03.md` (archival, not instructions).

## What this is

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar → depth at 18 surveyed landmarks;
hourly site/JSON bot, best-effort radar nowcast (10-min requested
cadence), transactional alerts (ntfy/email/SMS, daily cap 2), iOS
widget v7.24a, per-tide pages, and town-wide street flood map. Model
**v0.10.1** (`model/v0.10.1.md`): tide pathway + dynamic pluvial tank.

## Where it stands

- Audit `2026-08-03-a2`: Codex found 5 high + 7 medium/low issues;
  Claude independently confirmed every finding. Phases 0–1 are
  implemented in `5332dd70`: station-local clock sweep, source-aged
  radar with frame coverage, fail-closed alert-state recovery,
  semantic gates/all-path CI, visible dispatch failures, pinned
  actions/dependencies/CDN+SRI, and escaped NWS HTML. Offline suite:
  **67 tests green**. Round-03 implementation report awaits Claude's
  verification before audit closeout.
- M1 facts repaired with provenance: August 3 day-max restored to
  +13.2″ @14:50Z; 22:26 observation corrected to 10:26 by Claude;
  Codex appended an erratum clarifying that its retained bay-time note
  also means 10:18 AM, not 22:18.
- 2026-08-03 event #6: pluvial peak +13.8″ ~10:33 AM, fifth of six
  measured; full evidence in `assets/observations/2026-08-03/`.
- Audit `2026-08-03-a1` is closed; all seven migration-edge findings
  were fixed.

## RIGHT NOW

- Town map now covers all FOUR towns (Highlands, Atlantic
  Highlands, Leonardo, Sea Bright — 7,227 LiDAR street points,
  bridge-over-water guard, widened base layer); rain view stays
  Highlands-only.
- Audit a2 Phases 0–1: implemented by Codex, verified PASS in
  `audits/2026-08-03-a2/03-…` (67/67 tests).
- Audit a2 Phase 2 remains: reproducible repo-relative v0.10.1
  refit/hindcast + physics/golden tests + precise evidence-count prose,
  with **no retuning**. Phase 3 is the production-module split/schema
  evolution after a quiet stretch.
- Accepted residual risk: GitHub's requested 10-min nowcast cadence is
  best effort and much slower in practice. Site wording now says so;
  cadence SLO monitoring/external scheduler remain open.

## Key traps

- Bots commit continuously: explicit `git add`, commit → gate → push;
  on rejection fetch/rebase → gate again → retry. UNION ledgers.
- Station-local calendar decisions only through `_station_local_now()` /
  `_station_local_today()`; UTC is storage/transport. Run `date` before
  relative-time prose.
- `alert_state.json` is transactional delivery state, never a disposable
  cache. Recovery restores exact `origin/main` state or fails closed.
- Nowcast consumers trust `source_latest_utc`, never `generated_utc`,
  for radar freshness.
- Measured claims cite primary records; attic is never instructions.

## Start here

`AGENTS.md` → `audits/2026-08-03-a2/` → `BACKLOG.md`. Flood happening?
Read `PLAYBOOK.md` first.
