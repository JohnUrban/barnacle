# Prospective replay inputs

Append-only monthly JSONL, produced by `forecast/replay_archive.py` on each
hourly forecast run. First production-generation record: `2026-09-24T05:46:59Z`,
model v0.10.6. Starts with promotion; no retrospective records are invented.

Records include raw NWPS hourly levels with issuance/retrieval times,
advisory rows and corrections, hourly astronomy and corrected outlook with
source labels (-6 to +72 h), production QPF, selected surge/mean, tank start,
and model version. Null inputs have an unavailable reason. Levels/rates
are rounded; `expand()` reverses the columnar representation. The publish
gate checks strict JSON, required keys and nondecreasing generation stamps.

Purpose: future raw-vs-corrected high/mid/low-tide scoring and rain-flood
replays. Collection does not itself validate the advisory adjustments or
establish multi-event as-issued flood skill. Owner decisions and review:
`BACKLOG.md` items2/5 and `audits/2026-09-24-a1/`.
