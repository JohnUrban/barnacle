# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-11-26 21:55 EST (COASTAL STORM LIVE: evening flood reached
the second porch step, highest in the ledger; receding; event support).**
Rewrite wholesale each ship; <100 lines. BACKLOG OPEN LOOPS is authoritative.

## Health check 2026-11-10 and follow-ups — repaired and verified

Core production was healthy; defects fixed since (all class (c), no bump):

- **Local launchd arm** self-heals its Python environment
  (`bin/ensure_local_venv.sh`; a Homebrew upgrade had killed it for a week).
- **Quiet heartbeat** is keyed to the ledger (50-minute gap per arm), not
  the wall-clock minute, in both arms.
- **Alert dispatch** (2026-11-17): the radar alert check runs on every
  GitHub nowcast run and a lost push race between the two arms no longer
  fails the run before it can alert.
- **Accuracy ledger** (`data/forecast_accuracy.csv`): the scorer recorded
  the "observed peak" before the tide finished rising. It now waits for the
  whole ±2 h window. All 166 rows were re-derived from NOAA and 109 corrected
  IN PLACE by owner decision (BACKLOG `DECISION accuracy-ledger-in-place`: a
  derived score is regenerated, not preserved wrong; rule 2 otherwise
  stands). Last 30: mean error +0.34 → −0.09 ft, mean |error| 0.56 → 0.28.
  The as-issued half of every row, the archives and `predictions_log.csv`
  are untouched. Old values and the row-by-row record:
  `history/reports/2026-11-10-forecast-accuracy-rescore.md`.

## Tide gate — closed on 2026-11-10 (tracking only)

John found the Snug Harbor Beach gate closed at 08:33 EST (photo) and infers
it never reopened after late September `[INFERRED]`. Barnacle is gate-blind:
tidal street calls are expected to be wrong while it is closed. Evidence:
Sep 28 09:06 EDT corner dry with the bay 10.4 in over the grate
(2026-09-28-e01); both 2026-11-26 floods lagged the bay. No model change.

## LIVE 2026-11-26 — read first

Two floods, one storm. **e01 morning:** bay 8.267 ft MLLW at 08:54 EST, street
flooded from about 09:37, about lawn-step level (recollection), no rain. **e02 evening:** bay crest 9.0 to 9.2 ft
(preliminary, noisy; highest reading 9.211 at 20:54); John's 13 readings run
from "not above the curb" (19:16) to level with the SECOND porch step at
21:15 (about 6.08 ft NAVD88, derived from the taped 8 in riser), flow reversed
by 21:20, 4 in above the first step at 21:54. The street ran up to a foot
BELOW the bay on the rise and crested when the two met (gate suspected, not
seen). Table and first-pass scoring: `assets/observations/2026-11-26/e02/`.
Still open with John (rows 285-286 superseded by 298, 300): the second 8:59 time,
the second-step riser, later readings, photos. PLAYBOOK items PENDING for
both episodes (gauge re-pull, MRMS, plots). Log every report at once; give
windows in clock times. Next tide 2026-11-27 09:23 EST.
Queued development and evidence, nothing approved:
`history/plans/2026-11-26-storm-evidence-and-queue.md` (alert defect
`last_sent_rank`; evening addendum: late nowcast, street shown as bay level).

## Waiting on John

0. **Rain calls.** 2026-11-12 evening was a verified hit: lawn-step level
   at 18:24 EST, modeled peak 13.4 vs 13.7 in observed, alert 12 min ahead
   (episode 2026-11-12-e02; rise late, recession slow). Unconfirmed: the
   same day's midday call and 2026-10-11 (BACKLOG
   `rain-nowcast-overcall-check`). SMS retired (ntfy only); dispatch race
   fixed (2026-11-17). e02 gauge archive, MRMS forcing, plots PENDING.
1. **Local-arm failure detection** (proposed): watchdog pages when the tick
   log shows an hour of continuous failure. New page class, owner's call.
2. **Rule 2 wording** (primary records vs derived scores) is John's to
   write; AGENTS.md is unchanged.

## Standing state from the 2026-09-28 stopping point (unchanged)

Development is paused by owner choice; today's work was ops repair only.
Landmark-bounds CLOSED (round 22, `audits/2026-09-27-a1/22-close-out-codex.md`);
widget v7.35a copied by John; native bounded/disputed/long-report/model-claim
readability still PENDING (only v7.32a measured form has screenshot
acceptance). Crossing 4.37 vs curb 4.16 NAVD88: OPEN survey discrepancy.

Audit 2026-09-27-a1 implementation CLOSED; science OPEN: gate transfer (no
gate model authorized), high-base tank, verified NOAA series beside the
preliminary archive, Borough gate history, historical
census/hindcasts, Heron's episode-aware as-issued evaluation (stated bases
only). Exit-75 publish-on-delivery-failure is untested by a real outage.

Event support: read PLAYBOOK first; append ledger AND raw notes on receipt;
record landmark bands with `bin/append_observation_bound.py`; ASK John when
a band is not computable. Bay is not street.

## Production — v0.10.6 live

Spec `model/v0.10.6.md`. 36-h surge decay/fallback ladder; seven-day tails
and as-issued rain skill experimental. 18 landmarks; hourly site/JSON;
~10-min radar nowcast from two arms (GitHub: trigger-gated; launchd:
unconditional while the Mac is awake). ntfy imminent impact (SMS retired);
ntfy/email longer lead; alert tide horizon 48 h. Consult live inputs, not this snapshot.

## Heron, wind-shadow, Tern — ownership unchanged

Wind-shadow c2 CLOSED (`audits/2026-09-24-a3/07-close-out-codex.md`); SHADOW
ONLY; 60 days AND five storms; one storm = one storm however many floods.
Heron evaluator CLOSED at cd17a5a14, research unmerged. Tern social rehearsal
local-only; no posts, merge or push. Storm-communication parity still open:
`history/plans/2026-09-25-storm-followup-handoff.md`.
