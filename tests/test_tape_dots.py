"""Near-term chart tape dots: one dot per 30-min slot = the reading
every reading at its true time (2026-09-26, event #10: the old
max-per-slot rule drew every dot too high on both limbs)."""
import csv
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff


class TapeDotTests(unittest.TestCase):
    def test_slot_uses_nearest_reading_not_max(self):
        series = [{"time": f"2026-09-26 {h:02d}:{m:02d}",
                   "tide_navd88": 4.0, "pluvial_navd88": None,
                   "observed_navd88": None}
                  for h in range(7, 9) for m in (0, 30)]
        fields = ["observation_time_local", "landmark_key",
                  "observed_depth_in"]
        rows = [  # rising limb: 07:18 / 07:28 / 07:44 all near the 07:30 slot
            ("2026-09-26T07:18", "lawn_step", "0.0"),
            ("2026-09-26T07:28", "porch_step_base", "0.0"),
            ("2026-09-26T07:44", "porch_step_base", "1.45"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            with open(root / "data" / "labeled_observations.csv", "w",
                      newline="") as f:
                w = csv.writer(f); w.writerow(fields); w.writerows(rows)
            with mock.patch.object(ff, "_REPO_ROOT", str(root)):
                html = ff._render_water_series_section(
                    {"water_series": series})
        cfg = json.loads(re.search(r'var cfg = (\{.*?\});', html).group(1))
        tape = next(d for d in cfg["data"]["datasets"]
                    if "tape" in d["label"].lower())
        # every reading plotted, at its true fractional slot position
        self.assertEqual(tape["type"], "scatter")
        self.assertEqual(len(tape["data"]), 3)
        first = min(tape["data"], key=lambda p: p["x"])
        self.assertAlmostEqual(first["x"], 18 / 30, places=3)   # 07:18
        self.assertAlmostEqual(first["y"], round((4.66 - 3.52) * 12, 1), places=1)
        scale = cfg["options"]["scales"]["xtape"]
        self.assertEqual((scale["min"], scale["max"]),
                         (0, len(cfg["data"]["labels"]) - 1))


if __name__ == "__main__":
    unittest.main()
