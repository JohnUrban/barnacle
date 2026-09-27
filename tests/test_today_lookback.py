"""Owner DECISION 2026-09-27 (audit 2026-09-27-a1 reply 04, option 3): on the
"so far today" line an empirical value beats a model guess. Headline by
evidence class — tape, else bay peak labeled as bay, else the nowcast model —
and a higher model day max at an UNMEASURED time is appended as a claim,
never promoted. Every arm renders the same phrase."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import rendering

NOW = dt.datetime(2026, 9, 27, 17, 0)
FIELDS = "observation_time_local,landmark_key,observed_depth_in\n"


def lookback(rows="", nowcast=None, gauge=(None, None)):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data").mkdir()
    (tmp / "docs").mkdir()
    (tmp / "data" / "labeled_observations.csv").write_text(FIELDS + rows)
    if nowcast is not None:
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nowcast))
    with mock.patch.object(ff, "_REPO_ROOT", str(tmp)), \
            mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(tmp / "none.json")), \
            mock.patch.object(ff, "_station_local_now", return_value=NOW), \
            mock.patch.object(ff, "_fetch_actual_peak_around", return_value=gauge):
        return ff._today_lookback()


MODEL_39 = {"generated_utc": "2026-09-27T20:40:52Z", "day_local": "2026-09-27",
            "day_max_street_in": 39.0, "day_max_utc": "2026-09-27T06:40:00Z"}
TAPE = "2026-09-27T09:44,porch_step_base,11.25\n2026-09-27T12:48:00-04:00,curb,0.75\n"


class PrecedenceTests(unittest.TestCase):
    def test_tape_beats_higher_model_and_model_is_appended_as_claim(self):
        lb = lookback(TAPE, MODEL_39)
        self.assertEqual(lb["evidence"], "measured")
        self.assertEqual(lb["rel_grate_in"], 25.2)
        self.assertEqual(lb["time_local"], "09:44")
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 39.0)
        self.assertEqual(lb["model_claim"]["time_local"], "02:40")

    def test_model_claim_inside_a_measured_hour_is_discarded(self):
        # a dry check at 02:50 covers the model's 02:40: empirical wins the window
        lb = lookback(TAPE + "2026-09-27T02:50,grate_SW,0\n", MODEL_39)
        self.assertEqual(lb["rel_grate_in"], 25.2)
        self.assertNotIn("model_claim", lb)

    def test_lower_model_is_not_a_claim(self):
        lb = lookback(TAPE, dict(MODEL_39, day_max_street_in=6.4))
        self.assertNotIn("model_claim", lb)

    def test_bay_peak_is_labeled_bay_not_corner_regime(self):
        lb = lookback("", None, gauge=(7.57, "2026-09-27 20:06"))
        self.assertEqual(lb["evidence"], "bay")
        self.assertEqual(lb["regime"], "bay")
        self.assertIn("corner not measured", lb["source"])
        self.assertAlmostEqual(lb["navd88"], 4.75, places=2)

    def test_bay_beats_higher_model_which_is_appended(self):
        lb = lookback("", dict(MODEL_39, day_max_street_in=20.0,
                               day_max_utc="2026-09-27T19:00:00Z"),
                      gauge=(7.57, "2026-09-27 20:06"))
        self.assertEqual(lb["evidence"], "bay")
        self.assertEqual(lb["model_claim"]["rel_grate_in"], 20.0)

    def test_model_alone_when_nothing_empirical(self):
        lb = lookback("", dict(MODEL_39, day_max_street_in=6.4))
        self.assertEqual(lb["evidence"], "modeled")
        self.assertIn("unverified", lb["source"])
        self.assertEqual(lb["rel_grate_in"], 6.4)
        self.assertNotIn("model_claim", lb)

    def test_nothing_above_grate_is_none(self):
        self.assertIsNone(lookback("2026-09-27T09:44,grate_SW,0\n", None))


class PhraseTests(unittest.TestCase):
    def test_measured_phrase_with_claim(self):
        lb = {"evidence": "measured", "rel_grate_in": 25.2, "time_local": "09:44",
              "regime": "severe", "model_claim": {"rel_grate_in": 39.0, "time_local": "02:40"}}
        self.assertEqual(rendering._lookback_phrase(lb, short=True),
                         'MEASURED +25.2″ at 09:44; model claims +39.0″ at 02:40')
        self.assertIn("(unmeasured then)", rendering._lookback_phrase(lb))
        self.assertIn("&Prime;", rendering._lookback_phrase(lb, html=True))

    def test_bay_and_model_phrases(self):
        self.assertIn("BAY PEAK +14.8", rendering._lookback_phrase(
            {"evidence": "bay", "rel_grate_in": 14.8, "time_local": "20:06"}))
        self.assertIn("unverified", rendering._lookback_phrase(
            {"evidence": "modeled", "rel_grate_in": 6.4, "time_local": "16:40"}))

    def test_every_arm_uses_the_shared_phrase(self):
        src = Path(rendering.__file__).read_text()
        self.assertEqual(src.count("_lookback_phrase("), 6)   # 1 def + 5 arms
        # no arm composes its own so-far text from the raw fields any more
        self.assertNotIn('_lb["source"]', src)
        self.assertNotIn("_lbt['rel_grate_in']", src)


if __name__ == "__main__":
    unittest.main()
