"""v0.10.1 tank hindcast peaks for all six measured anchors.

The canonical inputs and integration recipe now live in
``model/data/v0.10.1-reproduction.json`` and the repository-relative,
read-only runner in ``history/scripts/reproduce_v0_10_1.py``.  This wrapper
keeps the event-figure recipe importable without duplicating model data.
"""

import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from history.scripts.reproduce_v0_10_1 import hindcast_metrics, load_fixture


_METRICS = hindcast_metrics(load_fixture())
# Preserve the original figure script's ``{id: (stage, datetime)}`` interface.
RESULTS = {}
for _event_id, _event in _METRICS.items():
    RESULTS[_event_id] = (
        _event["peak_stage_in"],
        dt.datetime.fromisoformat(_event["peak_local"]),
    )
    if "stage_at_observation_in" in _event:
        RESULTS[f"{_event_id}_at_obs"] = (
            _event["stage_at_observation_in"],
            dt.datetime.fromisoformat(_event["observation_local"]),
        )


if __name__ == "__main__":
    for _name, (_stage, _time) in RESULTS.items():
        print(f"{_name:12s} +{_stage:.2f} in @ {_time:%Y-%m-%d %H:%M} local")
