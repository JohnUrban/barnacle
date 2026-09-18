# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-18 13:35 EDT.** Rewrite wholesale each ship and keep
under 100 lines. `BACKLOG.md` OPEN LOOPS is authoritative. The attic is
archival, never instructions.

## System

Production hyperlocal flood forecaster for 342 Bay Ave, Highlands NJ.
Sandy Hook gauge + NWS + MRMS radar produce water depth at 19 landmarks,
an hourly site/JSON forecast, best-effort ~10-minute nowcast, per-tide pages,
nine-town street map, iOS widget source v7.28a, and ntfy/email/SMS alerts.
Current model **v0.10.3** (`model/v0.10.3.md`); SMS is the imminent-impact
rail, while ntfy/email carry long-lead watches. Real people receive alerts.

## Current state

- Audit `2026-09-14-a1` is CLOSED. **Audit `2026-09-18-a1` is OPEN**
  (round 01 by Claude Fable 5.1, auditing Codex's 11 post-close-out
  commits): technical work verifies clean (v0.10.3 numerically exact,
  GMT migration complete at all NOAA sites, nine green production runs);
  findings are provenance/process — `Reviewed-by: Claude` trailers on
  all 11 (+ the 09-14 phase-4 commit) with no review behind them, a
  habit traced to Codex's 2026-07-21 template, and v0.10.3 promoted
  without an independent reply or owner decision. Awaiting Codex's
  round-02 reply and John's DECISION line on v0.10.3.
- Alert delivery has real-payload contracts, quality/freshness gates,
  age-bounded NOAA fallbacks, per-rail retry/cap state, and one fail-closed
  post-publish dispatch. SMS is fresh-nowcast imminent impact only.
- Local scheduling has stale-lock takeover, structured outcomes, quiet
  coalescing, explicit arm heartbeats, and an independent Mac watchdog.
  Sleeping-Mac coverage and external trigger credentials remain open.
- NOAA transport uses GMT; stored tide/gauge stamps carry station offsets.
  Repeated fall-back hours are distinct and legacy naive rows remain readable.
- Widget v7.26a was confirmed installed 2026-09-14. Source v7.28a retains
  exact offset parsing and identifies the driveway entry as cross-fit; John
  must re-copy it into Scriptable.
- `driveway_central` is explicitly a 4.67-ft cross-fit corner-stage threshold;
  the separate 4.11-ft map point is `driveway_road_central`.
- CI checksum-pins actionlint 1.7.12 and ShellCheck 0.11.0. Required
  artifacts fail closed, writes are atomic, and ledgers are validated.
- A dependency-free DOM/accessibility contract now gates every current
  landing/reference/map/tide-index/per-tide page. Interactive controls and
  canvas charts have programmatic names; immutable daily archives are exempt.
- Strict mypy is pinned in CI for the fully annotated `station_time` and
  `html_contract` pure seams. The facade/renderers remain intentionally
  outside that claim until later seam-by-seam work.

## Evidence and model state

- Event #9, 2026-09-13, peaked level with the lawn step at ~+13.7 inches at
  07:01:23 EDT [VERIFIED: 18-photo EXIF timeline]. Response was 10–13 minutes
  earlier than the fixed-lag hindcast; a second compound curb flood followed.
- Its last overnight forecast is a qualified split-pathway hit: elevated
  pluvial risk 7h47 ahead and a near-magnitude burst proxy, but hourly QPF
  put the first flood ~3.5h late. Event-time nowcast is unscorable because
  both production arms were dark.
- Production v0.10.3 changes only `_pluvial_fill` continuity. It matches an
  independent volume-at-base inverse to 1.07e-14 inch; sampled correction is
  at most +0.090 inch, compound peaks move +0.014/+0.063 inch, and no peak
  clock changes. Constants, landmarks, forcing, lag, and alert policy remain
  unchanged. v0.10.2 is archived with repaired links.
- Initial v0.11 assessment rejects one replacement lag, universal point/max
  forcing, standalone persistence, and tide-bias retuning.
- Moving astronomy + constant surge cuts Oct 30 head RMSE 0.340→0.157 ft,
  but Dec 19 is 0.249→0.251 ft because surge evolves. Standardized tank
  endpoints move +0.82 inches rising / −0.49 inches falling. The rule remains
  HELD pending surge-tendency, age-expiry, and independent-event evidence.
- Reproductions: `history/scripts/reproduce_v0_10_1.py` preserves the prior
  frozen record; `history/scripts/reproduce_v0_10_3.py` verifies production.

## Open residuals

- Observe the rebuilt storm-path dispatch at the next production radar
  trigger; local watchdog coverage is awake-hours only.
- External 24/7 triggering and local secret-bearing alert redundancy require
  owner credentials/security decisions.
- Exactly-once provider delivery needs idempotency or a durable external
  outbox; current policy deliberately favors duplicate over missed alerts.
- Surge-tendency validation needs a predeclared bounded rule and a future
  independent compound event; Event 9 round-2 radar was not archived.
- Real browser-runtime tests, typing beyond the two pure seams, edge-map
  clicks, and separately versioned model-candidate work remain queued.

## Production rules

- On flood work read `PLAYBOOK.md`; otherwise read `AGENTS.md`, this file,
  audits, then BACKLOG.
- Add explicit paths. Commit → gate → push; on rejection fetch/rebase or
  abort → gate again → retry. Union append-only ledgers.
- Use station-time helpers and run `date` before relative-time prose.
- Restore `data/alert_state.json` from origin after local generation and
  before commit. Provenance and primary records are mandatory.
- Model behavior changes require version/spec/code/log stamps in lockstep.
  Semantic changes must cover every relevant alert and display arm.

## Immediate next step

Retain the moving-head candidate offline until its surge-tendency and expiry
contract can be tested without consuming the reserved independent event.
The next autonomous engineering slice is real browser-runtime smoke coverage
or another isolated typed seam; event/credential/field-observation loops stay
gated.
