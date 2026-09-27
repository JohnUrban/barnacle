"""Audit 2026-09-27-a1 R5: the nowcast day max carries the inputs it was
modeled from, carried-forward values keep or declare their provenance, and
operator-rejected (day, utc) pairs cannot win the max-wins merge."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import nowcast


def _write_with(payload, prev, origin, rejections=None, now_utc=None):
    tmp = Path(tempfile.mkdtemp())
    out = tmp / "nowcast.json"
    rej = tmp / "rejections.json"
    if prev is not None:
        out.write_text(json.dumps(prev))
    if rejections is not None:
        rej.write_text(json.dumps({"rejections": rejections}))
    with mock.patch.object(nowcast, "OUT_PATH", str(out)), \
            mock.patch.object(nowcast, "HEARTBEAT_PATH", str(tmp / "hb.csv")), \
            mock.patch.object(nowcast, "DAYMAX_REJECTIONS_PATH", str(rej)), \
            mock.patch.object(nowcast, "_origin_day_max", return_value=origin):
        nowcast._write(dict(payload), now_utc=now_utc)
    return json.loads(out.read_text())


class DayMaxProvenanceTests(unittest.TestCase):
    def test_fresh_winner_records_its_bay_input(self):
        got = _write_with({"active": True, "street_now_in": 38.9,
                           "bay_navd88": 6.677, "bay_source": "observed",
                           "radar_quality": "ok"},
                          prev=None, origin=(0, None))
        prov = got["day_max_provenance"]
        self.assertEqual(prov["kind"], "modeled-street-now")
        self.assertEqual(prov["bay_navd88"], 6.677)
        self.assertEqual(prov["bay_source"], "observed")
        self.assertEqual(prov["run_generated_utc"], got["generated_utc"])

    def test_observed_window_peak_is_labeled(self):
        got = _write_with({"active": True, "street_now_in": 2.5,
                           "bay_navd88": 4.0, "bay_source": "observed",
                           "_obs_max": (9.4, "2026-08-03T15:14:00Z")},
                          prev=None, origin=(0, None))
        self.assertEqual(got["day_max_provenance"]["kind"],
                         "modeled-observed-window-peak")

    def test_carried_forward_value_keeps_original_provenance(self):
        prev = {"generated_utc": "2026-09-27T06:54:48Z", "day_local": "2026-09-27",
                "day_max_street_in": 39.0, "day_max_utc": "2026-09-27T06:40:00Z",
                "day_max_provenance": {"kind": "modeled-street-now",
                                       "bay_navd88": 6.677, "bay_source": "observed"}}
        got = _write_with({"active": False}, prev=prev, origin=(0, None),
                          now_utc=nowcast.dt.datetime(2026, 9, 27, 8, 0,
                                                      tzinfo=nowcast.dt.timezone.utc))
        self.assertEqual(got["day_max_street_in"], 39.0)
        self.assertEqual(got["day_max_provenance"]["bay_navd88"], 6.677)

    def test_legacy_carry_forward_is_declared_unlabeled(self):
        prev = {"generated_utc": "2026-09-27T06:54:48Z", "day_local": "2026-09-27",
                "day_max_street_in": 12.0, "day_max_utc": "2026-09-27T06:40:00Z"}
        got = _write_with({"active": False}, prev=prev, origin=(0, None),
                          now_utc=nowcast.dt.datetime(2026, 9, 27, 8, 0,
                                                      tzinfo=nowcast.dt.timezone.utc))
        self.assertEqual(got["day_max_provenance"]["kind"],
                         "carried-forward-unlabeled")

    def test_published_two_tuple_origin_still_merges(self):
        # older callers / tests return (value, utc) without provenance
        got = _write_with({"active": True, "street_now_in": 1.0},
                          prev=None, origin=(13.2, "2026-08-03T14:50:00Z"))
        self.assertEqual(got["day_max_street_in"], 13.2)
        self.assertEqual(got["day_max_provenance"]["kind"],
                         "carried-forward-unlabeled")


class DayMaxRejectionTests(unittest.TestCase):
    NOW = nowcast.dt.datetime(2026, 9, 27, 20, 40, tzinfo=nowcast.dt.timezone.utc)

    def test_rejected_pair_cannot_win_from_any_carrier(self):
        prev = {"generated_utc": "2026-09-27T20:29:00Z", "day_local": "2026-09-27",
                "day_max_street_in": 39.0, "day_max_utc": "2026-09-27T06:40:00Z"}
        got = _write_with(
            {"active": True, "street_now_in": 6.4, "bay_navd88": -0.3,
             "bay_source": "observed"},
            prev=prev,
            origin=(39.0, "2026-09-27T06:40:00Z", {"kind": "modeled-street-now"}),
            rejections=[{"day_local": "2026-09-27",
                         "day_max_utc": "2026-09-27T06:40:00Z"}],
            now_utc=self.NOW)
        self.assertEqual(got["day_max_street_in"], 6.4)
        self.assertEqual(got["day_max_provenance"]["kind"], "modeled-street-now")

    def test_rejection_is_scoped_to_its_day(self):
        prev = {"generated_utc": "2026-09-27T20:29:00Z", "day_local": "2026-09-27",
                "day_max_street_in": 39.0, "day_max_utc": "2026-09-27T06:40:00Z"}
        got = _write_with({"active": True, "street_now_in": 6.4},
                          prev=prev, origin=(0, None),
                          rejections=[{"day_local": "2026-09-26",
                                       "day_max_utc": "2026-09-27T06:40:00Z"}],
                          now_utc=self.NOW)
        self.assertEqual(got["day_max_street_in"], 39.0)

    def test_committed_rejection_file_is_well_formed(self):
        entries = json.loads(Path(nowcast.DAYMAX_REJECTIONS_PATH).read_text())
        for e in entries["rejections"]:
            self.assertRegex(e["day_local"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertRegex(e["day_max_utc"], r"Z$")
            self.assertTrue(e["reason"])
        self.assertIn(("2026-09-27", "2026-09-27T06:40:00Z"),
                      nowcast._daymax_rejections())


class TodayLookbackRejectionTests(unittest.TestCase):
    """The site/widget 'so far today' line reads docs/nowcast.json directly;
    a rejected day max must not become today's peak there either."""

    def _lookback(self, rejections):
        from forecast import flood_forecast_daily as ff
        tmp = Path(tempfile.mkdtemp())
        (tmp / "data").mkdir(); (tmp / "docs").mkdir()
        (tmp / "data" / "labeled_observations.csv").write_text(
            "observation_time_local,landmark_key,observed_depth_in\n")
        (tmp / "docs" / "nowcast.json").write_text(json.dumps({
            "generated_utc": "2026-09-27T20:40:52Z", "day_local": "2026-09-27",
            "day_max_street_in": 39.0, "day_max_utc": "2026-09-27T06:40:00Z"}))
        rej = tmp / "rej.json"
        rej.write_text(json.dumps({"rejections": rejections}))
        now = nowcast.dt.datetime(2026, 9, 27, 17, 0)
        with mock.patch.object(ff, "_REPO_ROOT", str(tmp)), \
                mock.patch.object(ff, "DAYMAX_REJECTIONS_PATH", str(rej)), \
                mock.patch.object(ff, "_station_local_now", return_value=now), \
                mock.patch.object(ff, "_fetch_actual_peak_around",
                                  return_value=(None, None)):
            return ff._today_lookback()

    def test_rejected_day_max_is_not_todays_peak(self):
        self.assertIsNone(self._lookback(
            [{"day_local": "2026-09-27", "day_max_utc": "2026-09-27T06:40:00Z"}]))

    def test_unrejected_day_max_still_reports(self):
        lb = self._lookback([])
        self.assertEqual(lb["rel_grate_in"], 39.0)
        self.assertEqual(lb["evidence"], "modeled")


if __name__ == "__main__":
    unittest.main()
