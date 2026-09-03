# Forecast code boundaries

`flood_forecast_daily.py` is the production entry point. It grew with the
project and currently contains data acquisition, model math, persistence,
alerting, and HTML/email rendering in one file. That makes broad extraction
risky while the hourly bot and event-driven alerts are live.

Use these seams for incremental refactoring; keep the entry point as the
compatibility facade until each extraction has offline tests:

1. `station_time` — station-local parsing and UTC conversion; no network or
   file I/O. **EXTRACTED 2026-09-02** (`station_time.py`).
2. `model_core` — landmark thresholds, tidal conversion, pluvial tank,
   regimes, and flood windows; pure inputs/outputs only.
3. `data_sources` — NOAA/NWS/MRMS adapters returning explicit unavailable
   states and provenance.
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
