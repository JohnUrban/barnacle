import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import nowcast

UTC = dt.timezone.utc


def _fresh_nc(**over):
    nc = {
        "active": True, "radar_quality": "ok",
        "source_latest_utc": "2026-08-07T22:32:00Z",
        "source_age_min": 3.6, "day_local": "2026-08-07",
        "generated_utc": "2026-08-07T22:35:33Z",
        "street_now_in": 10.9, "peak_proj_in": 16.9,
        "trend": "rising",
    }
    nc.update(over)
    return nc


class RadarLiveStateTests(unittest.TestCase):
    def _with_file(self, nc, now):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "docs").mkdir()
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nc))
        with mock.patch.object(ff, "_REPO_ROOT", str(tmp)):
            return ff._radar_live_state(now_utc=now)

    def test_fresh_ok(self):
        now = dt.datetime(2026, 8, 7, 22, 40, tzinfo=UTC)
        self.assertIsNotNone(self._with_file(_fresh_nc(), now))

    def test_stale_fails_closed(self):
        now = dt.datetime(2026, 8, 7, 23, 20, tzinfo=UTC)
        self.assertIsNone(self._with_file(_fresh_nc(), now))

    def test_degraded_fails_closed(self):
        now = dt.datetime(2026, 8, 7, 22, 40, tzinfo=UTC)
        self.assertIsNone(
            self._with_file(_fresh_nc(radar_quality="degraded"), now))

    def test_inactive_fails_closed(self):
        now = dt.datetime(2026, 8, 7, 22, 40, tzinfo=UTC)
        self.assertIsNone(self._with_file(_fresh_nc(active=False), now))


class RadarAlertRankTests(unittest.TestCase):
    """Event #7 scenarios: the radar pathway must rank, label, and
    sign the alert; projection counts only at lawn-step class."""

    def _level(self, nc):
        forecast = {"all_tides": [], "pluvial_risk": {}}
        with mock.patch.object(ff, "_radar_live_state",
                               return_value=nc):
            return ff.compute_alert_level(forecast)

    def test_event7_would_have_alerted(self):
        rank, label, sig = self._level(_fresh_nc())
        # +16.9 projected = curb+9.2 = SEVERE in the established bands
        self.assertEqual(rank, 4)
        self.assertIn("LIVE radar", label)
        self.assertIn("radar:2026-08-07:severe", sig)

    def test_current_street_alone_alerts_at_curb_class(self):
        rank, label, _ = self._level(
            _fresh_nc(street_now_in=8.5, peak_proj_in=9.0,
                      trend="falling"))
        self.assertEqual(rank, 2)          # light, from street_now
        self.assertIn("LIVE radar", label)

    def test_small_projection_does_not_alert(self):
        # proj below lawn-step class and street below curb: no rank
        rank, label, sig = self._level(
            _fresh_nc(street_now_in=3.0, peak_proj_in=9.0))
        self.assertEqual(rank, 1)          # street-water class from now
        # rank 1 comes from street regime; radar sig present
        self.assertIn("radar:", sig)

    def test_no_radar_no_change(self):
        rank, label, sig = self._level(None)
        self.assertEqual(rank, 0)
        self.assertNotIn("radar:", sig)


class RadarDispatchCheckTests(unittest.TestCase):
    def _run(self, nc, sig):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "docs").mkdir(); (tmp / "data").mkdir()
        (tmp / "docs" / "nowcast.json").write_text(json.dumps(nc))
        (tmp / "data" / "alert_state.json").write_text(
            json.dumps({"sig": sig}))
        nc_path = str(tmp / "docs" / "nowcast.json")
        st_path = str(tmp / "data" / "alert_state.json")
        real_join = nowcast.os.path.join

        def fake_join(*parts):
            if parts[-1] == "nowcast.json":
                return nc_path
            if parts[-1] == "alert_state.json":
                return st_path
            return real_join(*parts)

        with mock.patch.object(nowcast.os.path, "join", fake_join):
            return nowcast.radar_alert_check()

    def test_event7_dispatches(self):
        self.assertEqual(self._run(_fresh_nc(), ""), 0)

    def test_already_signed_class_does_not_redispatch(self):
        self.assertEqual(
            self._run(_fresh_nc(),
                      "radar:2026-08-07:severe|pluv"), 3)

    def test_new_higher_class_redispatches(self):
        # signed at light earlier; now projecting severe -> dispatch
        self.assertEqual(
            self._run(_fresh_nc(),
                      "radar:2026-08-07:light"), 0)

    def test_stale_never_dispatches(self):
        self.assertEqual(
            self._run(_fresh_nc(source_age_min=40.0), ""), 3)

    def test_below_thresholds_no_dispatch(self):
        self.assertEqual(
            self._run(_fresh_nc(street_now_in=3.0, peak_proj_in=9.0),
                      ""), 3)


if __name__ == "__main__":
    unittest.main()
