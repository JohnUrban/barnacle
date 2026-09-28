"""Round 05 R6: each NOAA station uses its own MLLW→NAVD88 conversion; the
production Sandy Hook constant is unchanged and The Battery is −2.77 ft."""
import importlib.util
import unittest
from pathlib import Path

from forecast import flood_forecast_daily as ff

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "station_datums", ROOT / "assets/observations/2026-09-27/analysis/station_datums.py")
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)


class StationDatumTests(unittest.TestCase):
    def test_sandy_hook_matches_production_constant(self):
        self.assertEqual(sd.mllw_to_navd88_offset("8531680"), -2.82)
        self.assertEqual(sd.mllw_to_navd88_offset("8531680"), ff.MLLW_TO_NAVD88_OFFSET)

    def test_battery_uses_its_own_datums(self):
        self.assertEqual(sd.mllw_to_navd88_offset("8518750"), -2.77)
        self.assertAlmostEqual(7.999 + sd.mllw_to_navd88_offset("8518750"), 5.229, places=3)

    def test_receipts_are_committed(self):
        for rel in sd.RECEIPTS:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
