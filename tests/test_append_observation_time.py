"""Audit 2026-09-27-a1 R6: new ledger rows are stored with an explicit UTC
offset; naive station-local input is normalized through the shared parser."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "append_observation", ROOT / "bin" / "append_observation.py")
ao = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ao)


class AppendObservationTimeTests(unittest.TestCase):
    def _append(self, stamp):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "obs.csv"
            path.write_text(",".join(ao.FIELDS) + "\n")
            ao.append_observation({"observation_time_local": stamp,
                                   "landmark_key": "curb",
                                   "observed_depth_in": "1.0"}, str(path))
            with path.open(newline="") as f:
                return list(csv.DictReader(f))[0]["observation_time_local"]

    def test_naive_summer_stamp_gains_edt_offset(self):
        self.assertEqual(self._append("2026-09-27T17:40"),
                         "2026-09-27T17:40:00-04:00")

    def test_naive_winter_stamp_gains_est_offset(self):
        self.assertEqual(self._append("2026-12-01 08:00"),
                         "2026-12-01T08:00:00-05:00")

    def test_naive_fall_back_hour_uses_first_occurrence(self):
        self.assertEqual(self._append("2026-11-01T01:30"),
                         "2026-11-01T01:30:00-04:00")

    def test_offset_bearing_stamp_is_stored_verbatim(self):
        self.assertEqual(self._append("2026-09-27T15:26:00-04:00"),
                         "2026-09-27T15:26:00-04:00")


if __name__ == "__main__":
    unittest.main()
