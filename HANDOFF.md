# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-11-10 10:00 EST (health check; three repairs shipped; two
small items wait on John).** Rewrite wholesale each ship; <100 lines. BACKLOG
OPEN LOOPS is authoritative.

## Health check 2026-11-10 — repaired and verified

John asked for a health check six weeks into the break. Core production was
healthy (1,011 hourly runs in 1,026 h, site current, v0.10.6, gate clean,
alerts delivering). Three defects were fixed the same day; all class (c), no
bump. The first two went out in `988e8197c` (CI green).

- **Local launchd arm** had been dead since 2026-11-03T13:06Z: a Homebrew
  upgrade removed python@3.14 under `~/.barnacle/venv`. Now self-healing:
  `bin/ensure_local_venv.sh` rebuilds the environment when the interpreter is
  gone or the checked-in locks change; the tick syncs the clone BEFORE that
  check; the installer delegates to the helper. Installer re-run 13:42Z
  (Python 3.15.2); first live tick pushed `673736215` at 13:43Z; public
  nowcast.json refreshed. Rebuild failures retry hourly and log
  `environment-rebuild-failed` in `~/.barnacle/logs/tick-status.jsonl`.
- **Quiet heartbeat** is keyed to the ledger (`nowcast.quiet_heartbeat_due`,
  50-minute gap per arm), not the wall-clock minute, in BOTH arms. First
  GitHub run on the new workflow recorded `a3e27dff3` at 13:45Z. Expect about
  one `gated-quiet heartbeat` commit an hour from GitHub in quiet weather,
  and about one quiet local publish an hour while the Mac is awake.

- **Accuracy ledger** (`data/forecast_accuracy.csv`): the scorer recorded
  the "observed peak" before the tide finished rising. It now waits for the
  whole ±2 h window. All 166 rows were re-derived from NOAA and 109 corrected
  IN PLACE by owner decision (BACKLOG `DECISION accuracy-ledger-in-place`: a
  derived score is regenerated, not preserved wrong; rule 2 otherwise
  stands). Last 30: mean error +0.34 → −0.09 ft, mean |error| 0.56 → 0.28.
  The as-issued half of every row, the archives and `predictions_log.csv`
  are untouched. Old values and the row-by-row record:
  `history/reports/2026-11-10-forecast-accuracy-rescore.md`.

## Waiting on John

1. **Local-arm failure detection** (proposed): watchdog pages when the tick
   log shows an hour of continuous failure. New page class, owner's call.
2. **Rule 2 wording**: John finds the old rules' scope unclear. A sentence
   separating primary records (never rewrite) from derived scores
   (regenerate when wrong) is his to write; AGENTS.md is unchanged.
3. Housekeeping in John's checkout: Sep 26–28 observation photos untracked
   pending rule 9; stray `del` file; `.claude/worktrees/`.

## During the break (2026-09-28 → 2026-11-10), from the ledgers

Street-level tide peaks on Sep 28–30, Oct 11–13, Oct 21–22, Oct 28–29 and
Nov 7 (`forecast_accuracy.csv`); one SMS (Oct 11); last alert Nov 7. Oct 21
PM reached 6.80 ft MLLW while the morning forecast said dry: surge built
+0.57 → +1.96 ft and persistence lagged, flipping to street 6.5 h ahead
(`predictions_log.csv`). No field observations logged since 2026-09-27.
Heron's October 9 revisit has passed without action. NOAA's verified series
for the Sep 26 storm morning is now out: bay crest 8.805 ft MLLW at 08:36
EDT, 0.14 ft above the preliminary reading (BACKLOG FACT
sep26-verified-bay-peak).

## Standing state from the 2026-09-28 stopping point (unchanged)

Development is paused by owner choice; today's work was ops repair only.
Landmark-bounds implementation/deployment CLOSED (round 22,
`audits/2026-09-27-a1/22-close-out-codex.md`); widget v7.35a copied by John;
native bounded/disputed/long-report/model-claim readability still PENDING
(only v7.32a measured form has screenshot acceptance). Crossing 4.37 vs curb
4.16 NAVD88 remains an OPEN survey discrepancy; no elevation changed.

Audit 2026-09-27-a1 implementation CLOSED; science OPEN: gate transfer (no
gate model authorized), high-base tank, verified NOAA series beside the
preliminary archive, photos (rule 9), Borough gate history, historical
census/hindcasts, Heron's episode-aware as-issued evaluation (score stated
bases only). Exit-75 publish-on-delivery-failure is still untested by a real
outage.

September storm records: read PLAYBOOK before event support; append ledger
AND raw notes on receipt; record landmark bands with
`bin/append_observation_bound.py` and ASK John when a band is not computable.
Bay is not street. Rain increments are model sensitivities.

## Production — v0.10.6 live

Spec `model/v0.10.6.md`. 36-h surge decay/fallback ladder; seven-day tails
and as-issued rain skill experimental. 18 landmarks; hourly site/JSON;
~10-min radar nowcast from two arms (GitHub: trigger-gated; launchd:
unconditional while the Mac is awake). SMS imminent impact; ntfy/email longer
lead; alert tide horizon 48 h. Consult live inputs, not this snapshot.

## Heron, wind-shadow, Tern — ownership unchanged

Wind-shadow c2 CLOSED (`audits/2026-09-24-a3/07-close-out-codex.md`); SHADOW
ONLY; 60 days AND five storms; one storm = one storm however many floods.
Heron evaluator CLOSED at cd17a5a14, research unmerged. Tern social rehearsal
local-only; no posts, merge or push. Storm-communication parity
(email/day-worst headline) still open:
`history/plans/2026-09-25-storm-followup-handoff.md`.

Explicit staging; commit → gate → push; rejection → rebase/abort → gate.
