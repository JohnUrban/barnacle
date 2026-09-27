"""Audit 2026-09-27-a1 R6: near-term chart tape dots use the shared station
parser for BOTH the series bounds and the ledger rows, compare instants,
and keep readings on the window edges. Offset-bearing rows, legacy naive
rows and the repeated fall-back hour all plot at their true positions."""
import csv
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff

FIELDS = ["observation_time_local", "landmark_key", "observed_depth_in"]


def _render(series, rows):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data").mkdir()
        with open(root / "data" / "labeled_observations.csv", "w",
                  newline="") as f:
            w = csv.writer(f)
            w.writerow(FIELDS)
            w.writerows(rows)
        with mock.patch.object(ff, "_REPO_ROOT", str(root)):
            html = ff._render_water_series_section({"water_series": series})
    cfg = json.loads(re.search(r"var cfg = (\{.*?\});", html).group(1))
    tape = [d for d in cfg["data"]["datasets"] if "tape" in d["label"].lower()]
    return tape[0]["data"] if tape else []


def _series(prefix, stamps):
    return [{"time": f"{prefix} {s}", "tide_navd88": 4.0,
             "pluvial_navd88": None, "observed_navd88": None} for s in stamps]


class TapeBoundaryTests(unittest.TestCase):
    def test_offset_rows_on_both_edges_are_plotted(self):
        # the audit's probe: 07:00 sat exactly on the offset-bearing left edge
        series = _series("2026-09-26", ["07:00-04:00", "07:30-04:00",
                                         "08:00-04:00", "08:30-04:00"])
        dots = _render(series, [
            ("2026-09-26T07:00:00-04:00", "lawn_step", "0"),
            ("2026-09-26T07:18:00-04:00", "lawn_step", "0"),
            ("2026-09-26T08:30:00-04:00", "lawn_step", "0"),
            ("2026-09-26T08:31:00-04:00", "lawn_step", "0"),   # just outside
        ])
        self.assertEqual([d["t"] for d in dots], ["07:00", "07:18", "08:30"])
        self.assertAlmostEqual(dots[0]["x"], 0.0)
        self.assertAlmostEqual(dots[1]["x"], 0.6, places=3)
        self.assertAlmostEqual(dots[2]["x"], 3.0)

    def test_legacy_naive_rows_share_the_same_instant_axis(self):
        series = _series("2026-09-26", ["07:00-04:00", "07:30-04:00",
                                         "08:00-04:00", "08:30-04:00"])
        dots = _render(series, [("2026-09-26T07:00", "lawn_step", "0"),
                                ("2026-09-26T07:45", "lawn_step", "0")])
        self.assertEqual([round(d["x"], 3) for d in dots], [0.0, 1.5])

    def test_naive_series_with_offset_rows(self):
        series = _series("2026-09-26", ["07:00", "07:30", "08:00", "08:30"])
        dots = _render(series, [("2026-09-26T07:30:00-04:00", "curb", "1")])
        self.assertEqual([round(d["x"], 3) for d in dots], [1.0])

    def test_fall_back_repeated_hour_positions_by_instant(self):
        # 2026-11-01: 01:30 EDT (-04:00) and 01:30 EST (-05:00) are an hour apart
        series = _series("2026-11-01", ["01:00-04:00", "01:30-04:00",
                                         "01:00-05:00", "01:30-05:00",
                                         "02:00-05:00"])
        dots = _render(series, [("2026-11-01T01:30:00-04:00", "curb", "1"),
                                ("2026-11-01T01:30:00-05:00", "curb", "2")])
        self.assertEqual([round(d["x"], 3) for d in dots], [1.0, 3.0])

    def test_unparseable_stamp_is_skipped_not_fatal(self):
        series = _series("2026-09-26", ["07:00-04:00", "07:30-04:00",
                                         "08:00-04:00", "08:30-04:00"])
        dots = _render(series, [("garbage", "curb", "1"),
                                ("2026-09-26T07:30:00-04:00", "curb", "1")])
        self.assertEqual(len(dots), 1)


if __name__ == "__main__":
    unittest.main()
