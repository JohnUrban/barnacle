# Forecast code boundaries

`flood_forecast_daily.py` is the production entry point. It grew with the
project and currently contains data acquisition, model math, persistence,
alerting, and HTML/email rendering in one file. That makes broad extraction
risky while the hourly bot and event-driven alerts are live.

Use these seams for incremental refactoring; keep the entry point as the
compatibility facade until each extraction has offline tests:

1. `station_time` — station-local parsing and UTC conversion; no network or
   file I/O.
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

Extraction rule: move one seam at a time, retain re-exports from
`flood_forecast_daily.py`, run `python -m unittest discover -s tests -q` and
`python forecast/check_artifacts.py`, regenerate, then review the generated
diff. Do not combine structural extraction with parameter tuning, ledger
rewrites, or model-version changes.

The nowcast intentionally imports the production facade so it shares the
same tank, drainage, station-time, and health semantics. Move that import only
after `model_core` and `data_sources` have stable public interfaces.
