"""Phase-3 module-split integrity guards.

Born from the 2026-09-02 seam-2 revert incident (rule-11 #6): a
conflict-ritual recovery reapplied a stale pre-extraction copy of the
facade over the landed split. Every test stayed green because the
monolith defines every name itself — so this file makes duplication
ITSELF the failure. If a name is defined at top level in both the
facade and an extracted module, the extraction has been (partially)
reverted and the two copies can silently diverge.
"""
import ast
import unittest
from pathlib import Path

FORECAST = Path(__file__).resolve().parent.parent / "forecast"


def _top_level_defs(path):
    tree = ast.parse(path.read_text())
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef))}


class ModuleSplitTests(unittest.TestCase):
    def test_no_name_defined_in_both_facade_and_extracted_modules(self):
        facade = _top_level_defs(FORECAST / "flood_forecast_daily.py")
        for seam in ("station_time.py", "rendering.py"):
            dup = facade & _top_level_defs(FORECAST / seam)
            self.assertFalse(
                dup,
                f"{sorted(dup)} defined in BOTH the facade and {seam} — "
                "the extraction was reverted or a copy crept back; "
                "restore the split instead of shipping two copies")

    def test_facade_still_reexports_extracted_names(self):
        # a sample per seam; ImportError/AttributeError = broken facade
        import forecast.flood_forecast_daily as ff
        for name in ("parse_station_local_time", "_station_local_now",
                     "render_html_page", "_render_accuracy_html"):
            self.assertTrue(callable(getattr(ff, name)), name)


if __name__ == "__main__":
    unittest.main()
