from pathlib import Path
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
        paths = current_surface_paths(ROOT)
        tide_pages = [path for path in paths if path.parent.parent.name == "tides"]
        self.assertEqual(len(tide_pages), 6)
        self.assertTrue(all(path.is_file() for path in tide_pages))

    def test_contract_rejects_unnamed_controls_and_canvas(self):
        fixture = ROOT / "tests" / "fixtures" / "inaccessible-surface.html"
        failures = validate_surface(fixture)
        self.assertIn("unnamed input control: rate", failures)
        self.assertIn("canvas lacks img role: chart", failures)
        self.assertIn("canvas lacks accessible name: chart", failures)


if __name__ == "__main__":
    unittest.main()
