"""Round 09 R1: the complete path ledger row → today_lookback payload →
short / site-HTML / widget text → model-claim coverage, using actual and
ordinary report wordings. Reports are quoted, never paraphrased or attached
to a landmark by keyword; only an unambiguous whole-report negative at an
exact time can suppress a model claim."""
import csv
import datetime as dt
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from forecast import flood_forecast_daily as ff
from forecast import rendering
from tests.test_today_lookback import MODEL_39, lookback

ROOT = Path(__file__).resolve().parents[1]
WIDGET = ROOT / "docs" / "barnacle-widget.js"
NODE = shutil.which("node")


def _widget(lb):
    src = WIDGET.read_text(encoding="utf-8")
    js = src[src.index("// SOFAR-BEGIN"):src.index("// SOFAR-END")]
    js += "\nconsole.log(soFarText(JSON.parse(process.argv[1])));"
    run = subprocess.run(["node", "-e", js, json.dumps(lb)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    return run.stdout.strip()


def _row(time, key, text, depth=""):
    return f'{time},{key},{depth},"{text}"\n'


def _ledger_row(n):
    with (ROOT / "data" / "labeled_observations.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    r = rows[n - 2]
    return r, _row(r["observation_time_local"], r["landmark_key"],
                   r["observed_qualitative"].replace('"', "'"), r["observed_depth_in"])


class EndToEndReportTests(unittest.TestCase):
    def _all_arms(self, lb):
        short = rendering._lookback_phrase(lb, short=True)
        html = rendering._lookback_phrase(lb, html=True)
        widget = _widget(lb) if NODE else ""
        return short, html, widget

    def test_actual_row_238_is_quoted_not_reinterpreted(self):
        r, packed = _ledger_row(238)
        self.assertIn("over the curb elsewhere", r["observed_qualitative"])
        lb = lookback(packed, None, now=dt.datetime(2026, 9, 27, 8, 13))
        self.assertEqual(lb["evidence"], "reported")
        self.assertEqual(lb["report_kind"], "water")
        short, html, widget = self._all_arms(lb)
        for text in (lb["report_summary"], short, html, widget):
            self.assertNotIn("water over the curb", text)
            self.assertNotIn("over the curb (depth", text)
        # the arms quote the owner's own opening words
        self.assertTrue(lb["report_summary"].startswith("substantially more: lining both sides of Bay"))
        self.assertIn("substantially more", short)
        if NODE:
            self.assertIn("substantially more", widget)
        self.assertIn("over the curb elsewhere", html)          # full arm keeps the qualification

    def test_negation_is_not_reassurance_and_does_not_cover(self):
        lb = lookback(_row("2026-09-27T02:50", "grate_SW", "Not dry; water above the SW grate"), MODEL_39)
        self.assertEqual(lb["report_kind"], "water")
        short, html, widget = self._all_arms(lb)
        for text in (short, html, widget):
            self.assertNotIn("no flooding", text.lower())
            self.assertIn("Not dry", text)
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)
        self.assertIn("unverified", lb["model_claim"]["verification"])
        self.assertIn("model claims +39.0", short)

    def test_dry_sidewalk_with_water_in_the_street_keeps_claim(self):
        lb = lookback(_row("2026-09-27T02:50", "curb", "Sidewalk dry but water in the street"), MODEL_39)
        self.assertNotEqual(lb["report_kind"], "negative")
        self.assertIn("model_claim", lb)
        self.assertIn("Sidewalk dry but water", rendering._lookback_phrase(lb, short=True))

    def test_negative_at_marked_curb_but_over_another_grate_is_ambiguous(self):
        lb = lookback(_row("2026-09-27T02:50", "curb",
                           "no water at the curb in front of the lawn step, but over the curb at the upstream grate"),
                      MODEL_39)
        self.assertEqual(lb["report_kind"], "ambiguous")
        self.assertIn("model_claim", lb)
        self.assertIn("mixed or qualified", lb["model_claim"]["verification"])
        short, html, widget = self._all_arms(lb)
        for text in (short, widget):
            self.assertNotIn("water over the curb", text)
            self.assertIn("no water at the curb", text)

    def test_unambiguous_whole_intersection_negative_covers(self):
        lb = lookback(_row("2026-09-27T02:50", "grate_SW",
                           "still NO flooding at the Bay/Central intersection (user)"), MODEL_39)
        self.assertEqual(lb["report_kind"], "negative")
        self.assertNotIn("model_claim", lb)
        short, html, widget = self._all_arms(lb)
        self.assertIn("still NO flooding at the Bay/Central intersection", short)
        if NODE:
            self.assertIn("still NO flooding", widget)

    def test_actual_row_191_uncertain_time_still_does_not_cover(self):
        r, packed = _ledger_row(191)
        model = {"generated_utc": "2026-09-26T01:10:00Z", "day_local": "2026-09-25",
                 "day_max_street_in": 26.0, "day_max_utc": "2026-09-26T00:06:00Z"}
        lb = lookback(packed, model, now=dt.datetime(2026, 9, 25, 22, 0))
        self.assertEqual(lb["report_kind"], "negative")       # the wording is negative…
        self.assertTrue(lb["time_uncertain"])                  # …but its time is not exact
        self.assertIn("unconfirmed", lb["model_claim"]["verification"])
        self.assertIn("~20:06", rendering._lookback_phrase(lb, short=True))

    def test_measured_tape_still_covers_and_renders(self):
        lb = lookback("2026-09-27T02:50,grate_SW,0,\n", MODEL_39)
        self.assertEqual(lb["evidence"], "measured")
        self.assertNotIn("model_claim", lb)
        short, html, widget = self._all_arms(lb)
        self.assertIn("MEASURED no street water at 02:50", short)
        if NODE:
            self.assertIn("no water @02:50 (measured", widget)

    def test_html_arm_escapes_the_quoted_report(self):
        lb = lookback(_row("2026-09-27T02:50", "grate_SW", "<b>dry</b> & water <curb>"), None)
        html = rendering._lookback_phrase(lb, html=True)
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;b&gt;dry&lt;/b&gt; &amp; water &lt;curb&gt;", html)


class ReportKindTests(unittest.TestCase):
    def test_kinds(self):
        k = ff._report_kind
        self.assertEqual(k("still NO flooding at the Bay/Central intersection (user)"), "negative")
        self.assertEqual(k("No water"), "negative")
        self.assertEqual(k("Not dry; water above the SW grate"), "water")
        self.assertEqual(k("Sidewalk dry but water in the street"), "water")
        self.assertEqual(k("no water at the lawn step, but water over the curb"), "ambiguous")
        self.assertEqual(k("no flooding here; some puddles at the grates"), "ambiguous")
        self.assertEqual(k("flood receded completely as far as visible; maybe lingering bits"), "ambiguous")
        self.assertEqual(k("Roads virtually clear; intersection clear; safe to drive"), "unclassified")
        self.assertEqual(k(""), "unclassified")

    def test_excerpt_is_verbatim_and_bounded(self):
        text = ("substantially more: lining both sides of Bay, not yet spanning Bay; widely across "
                "Central SE-SW; proper flooding nearly to curb level at lawn step (user)")
        ex = ff._report_excerpt(text)
        self.assertTrue(text.startswith(ex.rstrip("…")))
        self.assertLessEqual(len(ex), 61)
        self.assertTrue(ex.endswith("…"))
        self.assertEqual(ff._report_excerpt("No water (user)"), "No water")


if __name__ == "__main__":
    unittest.main()
