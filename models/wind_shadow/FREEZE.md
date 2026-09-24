# wind-shadow FREEZE (candidate wind-shadow-c2)

Pre-trial freeze. The trial starts at the first OFFICIAL record (production workflow,
BARNACLE_WIND_SHADOW_TRIAL=1) after this branch is merged. Before the merge (no official
records exist), review changes update this table. After the first official record,
changing any file below requires a NEW candidate_id and a new prospective period.
CI enforces that these hashes match (tests/test_wind_shadow.py FreezeInvariantTests).

| file | sha256 |
|---|---|
| `models/wind_shadow/manifest.json` | `e594b4eeaf9e04306af9b377db56d99a22b21019bededbe807402cc8e78ca489` |
| `models/wind_shadow/DESIGN.md` | `1d3d253e7dbddd7908003021485a3907325e1709e2158ab4dff8682069f15567` |
| `forecast/wind_shadow.py` | `784e908149684a91bfc52072be9ab4a44301f2838d231e1f004b0edde3ca9105` |
| `history/scripts/evaluate_wind_shadow.py` | `8e82f2ba213ddd915eaa96d429cef8f34bf1483389656c198fc6494e8a204365` |
| `history/scripts/fit_wind_shadow_c2.py` | `3b76d59d38dee4c26d240efe2b1bd14cf50d5b3e6631e8d3d46fad399488c8df` |

candidate_id `wind-shadow-c2`; route A (single runs only, exact live construction); fit span ['2026-04-02T06Z', '2026-09-20T23Z'].
Training datasets are bound by SHA-256 inside the manifest (`dataset_sha256`).

## Retired: wind-shadow-c1 (d82a82970)
Frozen 2026-09-24 (FREEZE table in d82a82970) and retired before any official record after audit
2026-09-24-a3. Its only records were two local smoke tests (SMOKE_TESTS.md), excluded from any trial.
Its fit script (`history/scripts/fit_wind_shadow_c1.py`) is kept unchanged as history.
