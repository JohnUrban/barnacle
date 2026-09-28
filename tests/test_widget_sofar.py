"""Round 05 R2: the widget's "so far" line carries the same evidence and
model-claim meaning as the five site/email arms. The pure functions between
the SOFAR-BEGIN/END markers are executed with node on representative payloads."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDGET = ROOT / "docs" / "barnacle-widget.js"

CASES = [
    ({"evidence": "measured", "rel_grate_in": 25.2, "time_local": "09:44", "regime": "severe",
      "model_claim": {"rel_grate_in": 39.0, "time_local": "02:40"}},
     "so far: +25.2″ @09:44 (tape) · model +39″ @02:40 unmeasured"),
    ({"evidence": "measured", "rel_grate_in": 0.0, "time_local": "02:50", "regime": "dry", "n_checks": 1},
     "so far: no water @02:50 (tape, 1 check)"),
    ({"evidence": "measured", "rel_grate_in": -2.0, "time_local": "02:50", "regime": "dry", "n_checks": 3},
     "so far: no water @02:50 (tape, 3 checks)"),
    ({"evidence": "reported", "rel_grate_in": None, "time_local": "21:10", "time_uncertain": True},
     "so far: reported ~@21:10 (no tape)"),
    ({"evidence": "bay", "rel_grate_in": 14.8, "time_local": "20:06", "regime": "bay"},
     "so far: BAY +14.8″ @20:06 (gauge)"),
    ({"evidence": "modeled", "rel_grate_in": 6.4, "time_local": "16:40", "regime": "street"},
     "so far: MODELED +6.4″ @16:40 (unverified)"),
    ({"rel_grate_in": 12.0, "time_local": "10:00", "regime": "moderate", "source": "measured (tape)"},
     "so far: +12.0″ @10:00 (tape)"),   # legacy payload without `evidence`
]
VISIBLE = [({"evidence": "measured", "rel_grate_in": 0.0}, True),
           ({"evidence": "reported"}, True),
           ({"evidence": "bay", "rel_grate_in": 0}, False),
           ({"evidence": "modeled", "rel_grate_in": 4.0}, True),
           (None, False)]


@unittest.skipUnless(shutil.which("node"), "node is required to execute the widget functions")
class WidgetSoFarTests(unittest.TestCase):
    def _run(self):
        src = WIDGET.read_text(encoding="utf-8")
        a, b = src.index("// SOFAR-BEGIN"), src.index("// SOFAR-END")
        script = (src[a:b] + "\nconst cases = JSON.parse(process.argv[1]);"
                  "\nconst vis = JSON.parse(process.argv[2]);"
                  "\nconsole.log(JSON.stringify({text: cases.map(soFarText), vis: vis.map(soFarVisible)}));")
        run = subprocess.run(["node", "-e", script, json.dumps([c for c, _ in CASES]),
                              json.dumps([v for v, _ in VISIBLE])], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_rendered_text_matches_every_evidence_class(self):
        out = self._run()
        for (payload, expected), got in zip(CASES, out["text"]):
            self.assertEqual(got, expected, payload)

    def test_visibility_matches_the_site_gate(self):
        out = self._run()
        self.assertEqual(out["vis"], [v for _, v in VISIBLE])

    def test_widget_render_block_uses_the_functions_and_version_bumped(self):
        src = WIDGET.read_text(encoding="utf-8")
        self.assertIn('const WIDGET_VERSION = "v7.30a";', src)
        self.assertIn("if (soFarVisible(lb)) {", src)
        self.assertIn("left.addText(soFarText(lb));", src)
        self.assertNotIn("lb.rel_grate_in > 0)", src)


if __name__ == "__main__":
    unittest.main()
