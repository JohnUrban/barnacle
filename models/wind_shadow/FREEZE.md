# wind-shadow-c1 FREEZE

Frozen before the first evaluable shadow record (collection starts when this
branch is merged into main and the hourly job first writes data/wind_shadow/).
Before the merge (no records exist), review changes update this table. After the FIRST
record, changing any file below requires a NEW candidate_id and a new prospective period.

| file | sha256 |
|---|---|
| `models/wind_shadow/manifest.json` | `b000aa71f93bf7b5562b217617e3b092cb05e17f8791e0a41e2710c82a6987a1` |
| `models/wind_shadow/DESIGN.md` | `6db8ae26aea03987b3636cb954fc1ff57f3c3802f2e52ad7ff3c5b92403c3b98` |
| `forecast/wind_shadow.py` | `813a27f94c571567cf5e7d6a316f6c2b70b202bb4643765aa1b137f4a7a59fed` |
| `history/scripts/evaluate_wind_shadow.py` | `753fec2c8933551b913e1fe62d033027c88f7711a4bc47bf9182723e0f9ddff6` |
| `history/scripts/fit_wind_shadow_c1.py` | `b58976285f033bad8301ea3e4f0c20eb58fb99ef849363d754b08950b4247403` |

candidate_id `wind-shadow-c1`, route A (single runs only, exact live construction), fit span ['2026-04-02T06Z', '2026-09-20T23Z'].
