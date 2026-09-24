# wind-shadow FREEZE (candidate wind-shadow-c2)

frozen_candidate_id: `wind-shadow-c2`

Pre-trial freeze. Merging ENABLES the production workflow; the trial STARTS at the
first durable (committed) official record of wind-shadow-c2 (production workflow,
BARNACLE_WIND_SHADOW_TRIAL=1, not --no-send/--dry-run), whatever its status. Before
that record exists, review changes update this table. Enforcement (audit 2026-09-24-a3
round 03, R6): the runtime verifies every file below (and the manifest it actually
loads) before each official record and writes a `disabled` record on any mismatch;
every record carries `bundle_sha256` = SHA-256 of the canonical (id, sorted path/hash)
text of this table; the evaluator refuses to score unless all files match AND the
trial log's FIRST official record binds this same bundle; CI (tests/test_wind_shadow.py)
checks the hashes and that first-record binding. After the start, any change here
fails that binding: it requires a NEW candidate_id and a new prospective period.

| file | sha256 |
|---|---|
| `models/wind_shadow/manifest.json` | `6bc231b43e26a6ecfe4b0c917ea2f6af2cfa1f0bf7eb3f55e2fcb96f71841822` |
| `models/wind_shadow/DESIGN.md` | `1eff1f7d99a46d80d2990682c5e0e8b9bc2ea2c0aec6b081a24daa85435db271` |
| `forecast/wind_shadow.py` | `6fe6a0996629c61082e67e344aae5683d945b623bd65d05a8b49fd1bc9978250` |
| `history/scripts/evaluate_wind_shadow.py` | `ef2cf2c8d0fa8b70e2f28862f850c7018438ac4624197debd1ed962a392aae47` |
| `history/scripts/fit_wind_shadow_c2.py` | `6bf76222dd7deb9dab2fa0f8033197645bb53e68ebd4e42ee46500f72326279b` |
| `models/wind_shadow/rain_ref.py` | `ea66d9a6731455befd073401df409ef01bb2fc2f2ff32b7c1f55e65bc519d65b` |
| `models/wind_shadow/stage_storage_curve.csv` | `3cd2a0e58d238a227b84dc200b1f595a8ea7c950154485181b62e04bd6ba119d` |

candidate_id `wind-shadow-c2`; route A (single runs only, exact live construction); fit span ['2026-04-02T06Z', '2026-09-20T23Z'].
Training datasets are bound by SHA-256 inside the manifest (`dataset_sha256`).

## Retired: wind-shadow-c1 (d82a82970)
Frozen 2026-09-24 (FREEZE table in d82a82970) and retired before any official record after audit
2026-09-24-a3. Its only records were two local smoke tests (SMOKE_TESTS.md), excluded from any trial.
Its fit script (`history/scripts/fit_wind_shadow_c1.py`) is kept unchanged as history.
