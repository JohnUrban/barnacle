# Forecast-accuracy ledger: in-place correction of 2026-11-10

Internal record. Written for whoever maintains Barnacle later and wants to
know why `data/forecast_accuracy.csv` changed on this date and what it said
before.

## What was wrong

Each row of the ledger compares a forecast's predicted peak tide with the
peak the Sandy Hook gauge then recorded. In 109 of the 166 rows the
"observed peak" was read off the gauge **before the tide had peaked**, so it
was too low and the forecast looked like an over-prediction.

Example: the 2026-10-09 forecast predicted 6.41 ft MLLW for the tide of
2026-10-11 08:46. The scorer ran about 07:00 that morning, took the highest
reading so far (5.18 ft, still rising) and logged an error of +1.23 ft. The
tide peaked at 6.48 ft at 09:06. The real error was −0.07 ft.

Cause: `update_forecast_accuracy()` scored an archived forecast once its run
date was in the past and NOAA returned any data for the ±2 h window around
the target tide. It never checked that the window had finished.

| Variant | Rows | Dates | Status |
|---|---|---|---|
| Target tide one to three days after the run date; scored about 2 h before the peak | 89 | 2026-05-21 → 2026-11-09 | mechanism traced in code and observed live on 2026-11-10 |
| Same-day evening tide; scored that evening, up to about two hours before the peak | 19 | 2026-05-18 → 2026-08-01 | cause INFERRED (an older "day is over" test on the UTC date); the old code was not traced |
| NOAA revised the reading | 1 (+1 that was also scored early) | 2026-09-26 (and 2026-09-25) | NOAA's value at the recorded minute changed, see below |

Every one of the 109 corrections raises the observed peak: median +0.53 ft,
largest +1.35 ft, smallest +0.03 ft. None lowers it.

## Effect on the published figures

| | As recorded | Corrected |
|---|---|---|
| Last 30 forecasts: mean error | +0.34 ft | −0.09 ft |
| Last 30: mean absolute error | 0.56 ft | 0.28 ft |
| Last 30: worst | 1.77 ft | 1.57 ft |
| All 166: mean error | +0.32 ft | −0.07 ft |
| All 166: mean absolute error | 0.44 ft | 0.25 ft |

The sign of the bias changes. The details page said Barnacle over-predicts
by a third of a foot; it under-predicts slightly. The largest real miss is
the 2026-10-19 forecast for the 2026-10-21 16:44 tide: predicted 5.23 ft,
observed 6.80 ft (−1.57 ft; surge built from +0.57 to +1.96 ft and the
persistence estimate lagged it).

The by-lead sentence on the landing page (`accuracy_by_lead`) is computed
from `predictions_log.csv` and the observed-peaks cache, which already
waited two hours after each tide. It was never affected.

## What was done

Owner decision (John, 2026-11-10; BACKLOG `DECISION accuracy-ledger-in-place`):
this ledger is a derived score that can be regenerated from the archived
forecast and the gauge, so wrong rows are corrected in place and the old
values are kept here, away from the pages users read.

1. **Scorer guard.** A forecast is scored only after the whole window around
   its target tide has passed (`ACCURACY_WINDOW_HOURS`), the same rule the
   lead-time and chart readers already used.
2. **Rescore.** `history/scripts/rescore_forecast_accuracy.py` asked NOAA for
   the full window of every row using the scorer's own fetch (retrieval
   began 2026-11-10T14:56Z) and replaced observed peak, observed time and
   error where the peak differed. 57 rows were unchanged and keep their
   original bytes.
3. **Untouched:** run date, predicted peak, predicted time, regime and the
   old confidence label in every row; the daily archives in `docs/archive/`;
   `predictions_log.csv`; `data/replay_inputs/`. No forecast was re-run.

## Where the old values are

- `history/data/forecast_accuracy_as_recorded_2026-11-10.csv` — byte copy of
  the ledger as committed immediately before the correction.
- `history/reports/2026-11-10-forecast-accuracy-rescore.csv` — one line per
  row: recorded and re-derived peak, time and error, the change, the reason,
  NOAA's current value at the originally recorded minute, retrieval time.
- `history/reports/2026-11-10-forecast-accuracy-rescore.json` — the summary
  statistics above.

## NOAA revisions (as seen then vs as known now)

Corrected rows use NOAA's series as it stands on 2026-11-10. For two storm
rows that series differs from what the gauge reported at the time:

| Run date | Recorded | NOAA now, same minute | Re-derived peak |
|---|---|---|---|
| 2026-09-26 | 8.667 ft @ 08:36 | 8.805 ft | 8.805 ft @ 08:36 |
| 2026-09-25 | 8.188 ft @ 06:30 (also scored early) | 7.939 ft | 8.805 ft @ 08:36 |

NOAA's readings for 2026-09-26 11:30–13:30Z now carry the verified flag
(`q = v`) and form a smooth crest, so this is NOAA's quality-controlled
series replacing the preliminary one, not our spike filter. It bears on the
open follow-up "verified NOAA series beside the preliminary archive" for the
September storm: the verified bay peak that morning is 8.805 ft MLLW
(5.985 ft NAVD88), 0.14 ft above the preliminary reading. Bay is not street;
the house-corner crest figures in the event records are separate
measurements and are not changed by this.

The inputs each forecast actually used are preserved in its archive file.
The May archives carry fewer fields than recent ones (surge, tide table and
gauge trace, without the later per-input health detail).

## Re-running

`python3 history/scripts/rescore_forecast_accuracy.py` is a dry run and
prints what it would change. After this correction it should report zero
corrections apart from any later NOAA revision.
