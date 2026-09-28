"""Independent, offline probes of Curlew's landmark-bounds candidate.

Usage: python 16-review-probes.py /path/to/isolated/candidate
Writes only temporary files. Printed results describe observed behavior,
including defects; they are not a passing regression suite.
"""
import copy
import csv
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
from forecast import flood_forecast_daily as ff, rendering, check_artifacts

spec = importlib.util.spec_from_file_location("bound_writer", ROOT / "bin/append_observation_bound.py")
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
with (ROOT / "data/labeled_observations.csv").open(newline="") as f:
    rows = list(csv.DictReader(f))
bounds = {}
for line in (ROOT / "data/observation_bounds.jsonl").read_text().splitlines():
    rec = json.loads(line)
    bounds[rec["csv_row"]] = rec


def lookback(selected, records, nowcast=None):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "data").mkdir()
        (root / "docs").mkdir()
        with (root / "data/labeled_observations.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(selected)
        path = root / "data/observation_bounds.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in records))
        if nowcast:
            (root / "docs/nowcast.json").write_text(json.dumps(nowcast))
        with mock.patch.object(ff, "_REPO_ROOT", str(root)), \
                mock.patch.object(ff, "OBSERVATION_BOUNDS_PATH", str(path)), \
                mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(root / "none")), \
                mock.patch.object(ff, "_station_local_now", return_value=ff.parse_station_local_time("2026-09-27T23:00:00-04:00")), \
                mock.patch.object(ff, "_fetch_actual_peak_around", return_value=(None, None)):
            lb = ff._today_lookback()
        return {"payload": lb, "short": rendering._lookback_phrase(lb, short=True)}


out = {"candidate": "2fb8454ae", "imported_root": str(ROOT)}
dry = dict(rows[0], observation_time_local="2026-09-27T06:00:00-04:00",
           landmark_key="grate_SW", observed_depth_in="0", observed_qualitative="",
           notes="synthetic earlier dry measurement; all other metadata unused")
out["earlier_measured_dry_later_porch_breach"] = lookback(
    [dry, rows[251 - 2]], [bounds[251]])
for n in [237, 238, 269, 270]:
    out[f"actual_row_{n}"] = lookback([rows[n - 2]], [bounds[n]])

claim = {"generated_utc": "2026-09-27T22:30:00Z", "day_local": "2026-09-27",
         "day_max_street_in": 4.0, "day_max_utc": "2026-09-27T22:30:00Z"}
out["lower_bound_with_smaller_model"] = lookback([rows[270 - 2]], [bounds[270]], claim)

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "bounds.jsonl"
    ledger = ROOT / "data/labeled_observations.csv"
    rec = copy.deepcopy(bounds[238])
    for label, mutation in [
        ("string_bound", {"lo_navd88": "4.14"}),
        ("boolean_bound", {"lo_navd88": True}),
        ("empty_provenance", {"landmarks": []}),
        ("wrong_copied_identity", {"csv_row": 2, "observation_time_local": "1999-01-01T00:00", "landmark_key": "bogus"}),
        ("overflow_number", {"lo_navd88": None, "hi_navd88": float("inf")}),
    ]:
        bad = dict(rec, **mutation)
        encoded = json.dumps(bad)
        if label == "overflow_number":
            encoded = encoded.replace("Infinity", "1e309")
        path.write_text(encoded + "\n")
        try:
            problems = check_artifacts.validate_observation_bounds(str(path), str(ledger))
        except Exception as e:
            problems = {"raised": type(e).__name__, "message": str(e)}
        out["validator_" + label] = problems
        if label == "string_bound":
            try:
                out["runtime_string_bound"] = lookback([rows[238 - 2]], [bad])
            except Exception as e:
                out["runtime_string_bound"] = {"raised": type(e).__name__, "message": str(e)}
    path.write_text('null\n')
    try:
        out["validator_nonobject"] = check_artifacts.validate_observation_bounds(str(path), str(ledger))
    except Exception as e:
        out["validator_nonobject"] = {"raised": type(e).__name__, "message": str(e)}
    path.unlink()
    writer.append_bound(238, float("nan"), 4.16, "stated_landmarks", rec["landmarks"],
                        "synthetic invalid bound", "Codex probe", str(ledger), str(path))
    out["writer_nan"] = {"appended_nonstandard_nan": 'NaN' in path.read_text()}

print(json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False))
