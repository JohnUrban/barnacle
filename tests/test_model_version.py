import unittest
from pathlib import Path

from forecast import check_artifacts
from forecast import flood_forecast_daily as ff


ROOT = Path(check_artifacts.ROOT)


class ModelVersionTests(unittest.TestCase):
    def test_production_constants_are_stamped_v0_10_1(self):
        self.assertEqual(ff.CURRENT_MODEL_VERSION, "v0.10.1")
        self.assertEqual(ff.TANK_K, 1.296e6)
        self.assertEqual(ff.TANK_GAMMA, 0.78)
        self.assertEqual(ff.TANK_KOUT, 3.50)
        self.assertEqual(ff.TANK_LAG_MIN, 15)

    def test_current_spec_and_readmes_match_source_stamp(self):
        version = ff.CURRENT_MODEL_VERSION
        spec = ROOT / "model" / f"{version}.md"
        self.assertTrue(spec.exists())
        self.assertIn(
            f"Flood Prediction Model {version}", spec.read_text(encoding="utf-8")
        )
        self.assertTrue((ROOT / "model" / "archive" / "v0.10.md").exists())
        self.assertFalse((ROOT / "model" / "v0.10.md").exists())
        self.assertIn(
            f"model/{version}.md", (ROOT / "README.md").read_text(encoding="utf-8")
        )
        self.assertIn(
            f"`{version}`",
            (ROOT / "data" / "predictions_log_README.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_gate_reads_same_model_stamp(self):
        self.assertEqual(
            check_artifacts.source_model_version(), ff.CURRENT_MODEL_VERSION
        )


if __name__ == "__main__":
    unittest.main()
