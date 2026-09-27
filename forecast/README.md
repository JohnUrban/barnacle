# Forecast code boundaries

`flood_forecast_daily.py` is the production entry point. It grew with the
project and currently contains data acquisition, model math, persistence,
alerting, and HTML/email rendering in one file. That makes broad extraction
risky while the hourly bot and event-driven alerts are live.

Use these seams for incremental refactoring; keep the entry point as the
compatibility facade until each extraction has offline tests:

1. `station_time` — station-local parsing and UTC conversion; no network or
   file I/O. **EXTRACTED 2026-09-02** (`station_time.py`) and strict-mypy
   gated with the pure HTML publish-contract seam since 2026-09-18.
2. `model_core` — landmark thresholds, tidal conversion, pluvial tank,
   regimes, and flood windows; pure inputs/outputs only.
3. `data_sources` — NOAA/NWS/MRMS adapters returning explicit unavailable
   states and provenance.
   **First module 2026-09-23:** `outlook_sources.py` (7-day outlook
   adapters: CO-OPS, NWS grid, NWPS gauge forecast, P-ETSS, NBM, WPC,
   cross-check) with a cache/health contract; `outlook.py` (pure
   builder, ledger, shadow scoring) and `outlook_page.py` (renderer)
   sit beside it. None import the facade; the facade calls them.
4. `ledgers` — strict append-only CSV readers/writers and observed-peak/tide
   caches; atomic writes where state is replaced.
5. `alerts` — pure evaluation, independent delivery channels, then atomic
   acknowledgement.
6. `rendering` — email, site, details, per-tide pages, and JSON serializers;
   consumes a completed forecast object and never fetches live data.
   **EXTRACTED 2026-09-02** (`rendering.py`; silently reverted the same
   night by a stale-copy recovery, restored — `tests/test_module_split.py`
   now fails on any facade/module duplication).

Seams 2–5 remain pending, one per verified quiet-weather window
(BACKLOG owns the gating decision).

Extraction rule: move one seam at a time, retain re-exports from
`flood_forecast_daily.py`, run `python -m unittest discover -s tests -q` and
`python forecast/check_artifacts.py`, regenerate, then review the generated
diff. Do not combine structural extraction with parameter tuning, ledger
rewrites, or model-version changes.

The nowcast intentionally imports the production facade so it shares the
same tank, drainage, station-time, and health semantics. Move that import only
after `model_core` and `data_sources` have stable public interfaces.

## Frozen v0.10.1 reproduction

Run `python history/scripts/reproduce_v0_10_1.py` from any directory to replay
the production parameter vector, 24-point fit RMS, six measured-event
hindcasts, and prediction-log version cutover. The command is offline and
read-only. Its source-controlled inputs and expected outputs are in
`model/data/v0.10.1-reproduction.json`; `tests/test_model_reproduction.py`
holds the corresponding behavioral and physics gates. This is a frozen replay,
not authorization to search for or promote new parameters.

### Continuous curve and scoped health (2026-09-23 recovery)

`water_series` uses fresh observed-surge persistence, independent of each
high tide's NWS product projection. `water_series_input` records the actual
source/value/observation time/age; `current_surge_ft` keeps its historical
worst-tide meaning for compatibility. An unavailable observed surge produces
no continuous forecast, never a zero-surge tank forecast. Explicit zero passed
to `build_water_series` remains valid (nowcast astronomy-only use).

`input_health` retains all sources. `degraded_inputs` is production-only;
`outlook_degraded_inputs` scopes the optional outlook. The gate accepts legacy
artifacts without the split and validates both lists when the new field exists.
The widget source is unchanged and consumes the corrected JSON automatically.

## Delivery health and day-max provenance (audit 2026-09-27-a1, 2026-09-27)

- **Publication vs delivery.** `flood_forecast_daily.py` writes and validates
  every forecast artifact before it attempts alert delivery. A run whose
  every requested alert rail fails exits with `DELIVERY_FAILED_EXIT` (2) and
  records `data/alert_delivery_health.json` (`status` ok / partial / failed,
  attempted / succeeded / failed rails, `retry_eligible`). The hourly workflow
  treats exit 2 as "publish, then fail the job after the push"; any other
  non-zero exit is a generation failure and still stops publication. Sent-state
  is owned by `persist_alert_state` alone: a failed rail is never acknowledged
  and stays in `pending_base` for the next run.
- **Nowcast day max.** `docs/nowcast.json` carries `day_max_provenance`
  (`kind` modeled-street-now / modeled-observed-window-peak /
  carried-forward-unlabeled, the bay input and its source, radar quality, the
  run). `data/nowcast_daymax_rejections.json` is an append-only operator record
  of (day_local, day_max_utc) pairs whose input was bad; `nowcast._write` and
  `_today_lookback` both skip them so a contaminated maximum cannot outlive its
  correction through the max-wins merge. Adding an entry is a human decision
  with cited evidence; it is not automation and not an input-policy change.
