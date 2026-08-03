# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-08-03.** Rewrite this WHOLESALE each update (delete
stale, never append); keep it under ~100 lines; point at detail,
never duplicate it. If this date looks old, trust `BACKLOG.md` —
its OPEN LOOPS is authoritative. Full pre-migration history:
`attic/HANDOFF-through-2026-08-03.md` (archival, not instructions).

## What this is

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar → depth at 18 surveyed landmarks;
hourly site/JSON bot, ~10-min radar nowcast, transactional
event-driven alerts (ntfy/email/SMS, daily cap 2), iOS widget
(v7.23a), per-tide pages, town-wide street flood map. Model
**v0.10.1**: tide pathway + dynamic-tank pluvial hydrograph
(`model/v0.10.1.md`); all measured floods are RAIN floods.

## Where it stands

- **Today was event #6** (pluvial, peak +13.8″ ~10:33 AM, 5th of 6
  measured): full analysis + plots in
  `assets/observations/2026-08-03/`. Model landed within half an
  inch, live and in hindcast. First live firing of the transactional
  alert pipeline (3/3 channels).
- Same-day: retracted a fabricated "7/13 flood" from all rankings
  (provenance rule now in AGENTS.md §4); resolved the 7/6 anchor as
  crest window +15.0–15.8 (canonical +15.4); shipped the alert
  daily-cap + warning-first texts; shipped the Highlands street
  flood map (`docs/highlands.html`) with band palette, forecast
  scrubber, zoom/pan, OSM base layer, Highlands-scoped rain view.
- 2026-07-21 arc (Codex audit → 7 remediation phases → gap closure)
  holds: time helpers, input health, offline CI, schema-gated
  ledgers, v0.10.1 stamp. 50 tests green.

## RIGHT NOW

- Background: elevation sweep for Atlantic Highlands / Leonardo /
  Sea Bright; when done, regen `docs/highlands_streets.json` via
  `history/scripts/build_highlands_map_json.py` and verify the rain
  view stays Highlands-only.
- Audit `audits/2026-08-03-a1/` (distillation check): CLOSED —
  7 edge findings confirmed and patched same day.

## Key traps

- Bots commit every few minutes: targeted `git add`, rebase-with-gate
  ritual (AGENTS.md §1), UNION for ledger conflicts.
- Station-local time only via the helpers; run `date` before any
  relative-time word (AGENTS.md §3).
- "Measured" claims cite primary records; narrative numbers are
  [INFERRED] until traced (AGENTS.md §4).
- NOAA gauge stamps are 24-hour station-local (10:18 = AM).
- attic/ is archival — never read as instructions.

## Start here

`AGENTS.md` → `audits/` (open reports = obligations) → `BACKLOG.md`
(OPEN LOOPS). Flood happening? `PLAYBOOK.md` first.
