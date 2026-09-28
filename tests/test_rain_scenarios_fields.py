"""Round 05 R7: the committed rain-scenario receipt keeps the rain-increment
maximum and the total-water maximum separate, and reports the increment over
each observed corner-crest window."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "assets/observations/2026-09-27/analysis/rain_scenarios.json").read_text())


class RainScenarioFieldTests(unittest.TestCase):
    def test_total_water_maximum_is_its_own_field(self):
        for eid, w in DATA["windows"].items():
            for name, s in w["scenarios"].items():
                series_max = max(row[1] for row in s["series_10min"])
                self.assertGreaterEqual(s["max_water_in_vs_sw"] + 1e-9, series_max, (eid, name))
                self.assertLessEqual(s["water_at_max_increment_in_vs_sw"], s["max_water_in_vs_sw"] + 1e-9, (eid, name))
                self.assertNotIn("peak_water_in_vs_sw", s)

    def test_crest_window_increments_reported_for_measured_floods(self):
        for eid in ("2026-09-26-e01", "2026-09-26-e02", "2026-09-27-e01"):
            for name, s in DATA["windows"][eid]["scenarios"].items():
                self.assertIn("increment_at_corner_crest_in", s, (eid, name))
                c = s["increment_at_corner_crest_in"]
                self.assertLessEqual(c["min"], c["max"])
                self.assertLessEqual(c["max"], s["max_increment_in"] + 1e-9)

    def test_sep26_scenario_a_reproduces_the_audit_probe(self):
        a = DATA["windows"]["2026-09-26-e01"]["scenarios"]["A_fixed_crest_base_zero_drain"]
        self.assertAlmostEqual(a["max_increment_in"], 2.45, places=2)
        self.assertEqual(a["max_increment_utc"][11:16], "13:02")
        self.assertIn("5.847", a["assumption"])

    def test_sep27_crest_increment_is_small_under_every_assumption(self):
        for name, s in DATA["windows"]["2026-09-27-e01"]["scenarios"].items():
            self.assertLess(s["increment_at_corner_crest_in"]["max"], 0.1, name)


if __name__ == "__main__":
    unittest.main()
