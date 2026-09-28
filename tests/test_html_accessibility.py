from pathlib import Path
import json
import unittest

from forecast.html_contract import (
    current_surface_paths,
    validate_current_surfaces,
    validate_surface,
)


ROOT = Path(__file__).resolve().parents[1]


class HtmlAccessibilityTests(unittest.TestCase):
    def test_current_surfaces_have_stable_dom_and_accessible_names(self):
        self.assertEqual(validate_current_surfaces(ROOT), [])

    def test_current_tide_pages_are_derived_from_forecast_payload(self):
        # One page per tide in the committed payload. The count is NOT a
        # constant: how many high tides fall inside the forecast window
        # depends on the generation time (2026-09-28: the 14:00Z bot run
        # carried six tides, a 15:36Z regeneration five). A fixed "6" failed
        # CI on the landmark-bounds ship (run 36445097545) although every
        # derived page existed and the gate passed.
        paths = current_surface_paths(ROOT)
        tide_pages = [path for path in paths if path.parent.parent.name == "tides"]
        forecast = json.loads((ROOT / "docs" / "forecast.json").read_text(encoding="utf-8"))
        self.assertEqual(len(tide_pages), len({t["time"] for t in forecast["all_tides"]}))
        self.assertGreaterEqual(len(tide_pages), 4)
        self.assertLessEqual(len(tide_pages), 7)
        self.assertTrue(all(path.is_file() for path in tide_pages))

    def test_contract_rejects_unnamed_controls_and_canvas(self):
        fixture = ROOT / "tests" / "fixtures" / "inaccessible-surface.html"
        failures = validate_surface(fixture)
        self.assertIn("unnamed input control: rate", failures)
        self.assertIn("canvas lacks img role: chart", failures)
        self.assertIn("canvas lacks accessible name: chart", failures)


if __name__ == "__main__":
    unittest.main()
