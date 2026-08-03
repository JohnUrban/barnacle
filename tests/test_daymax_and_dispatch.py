import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import nowcast


class DayMaxMergeTests(unittest.TestCase):
    """The 2026-08-03 regression: day-max memory must be monotonic
    within a day even when a racing writer starts from a stale
    checkout (local prev is old) or when the peak occurred inside the
    run's own observed window (street_now already receded)."""

    def _write_with(self, payload, prev, origin):
        tmp = Path(tempfile.mkdtemp())
        out = tmp / "nowcast.json"
        if prev is not None:
            out.write_text(json.dumps(prev))
        with mock.patch.object(nowcast, "OUT_PATH", str(out)), \
                mock.patch.object(nowcast, "_origin_day_max",
                                  return_value=origin):
            nowcast._write(dict(payload))
        return json.loads(out.read_text())

    def test_origin_day_max_survives_stale_local_prev(self):
        # local checkout predates the flood (day_max 5.8); origin has 13.2
        got = self._write_with(
            {"active": True, "street_now_in": 9.0},
            prev={"generated_utc": "2026-08-03T13:56:00Z",
                  "day_max_street_in": 5.8,
                  "day_max_utc": "2026-08-03T06:34:00Z"},
            origin=(13.2, "2026-08-03T14:50:00Z"),
        )
        self.assertEqual(got["day_max_street_in"], 13.2)
        self.assertEqual(got["day_max_utc"], "2026-08-03T14:50:00Z")

    def test_observed_window_peak_beats_receded_street_now(self):
        got = self._write_with(
            {"active": True, "street_now_in": 2.5,
             "_obs_max": (9.4, "2026-08-03T15:14:00Z")},
            prev=None,
            origin=(0, None),
        )
        self.assertEqual(got["day_max_street_in"], 9.4)
        self.assertEqual(got["day_max_utc"], "2026-08-03T15:14:00Z")
        self.assertNotIn("_obs_max", got)

    def test_yesterday_day_max_does_not_leak(self):
        got = self._write_with(
            {"active": True, "street_now_in": 1.0},
            prev={"generated_utc": "2026-08-02T23:56:00Z",
                  "day_max_street_in": 19.9,
                  "day_max_utc": "2026-08-02T15:00:00Z"},
            origin=(0, None),
        )
        self.assertLess(got["day_max_street_in"], 19.9)

    def test_quiet_run_carries_same_day_max_forward(self):
        got = self._write_with(
            {"active": False},
            prev=None,
            origin=(13.2, "2026-08-03T14:50:00Z"),
        )
        self.assertEqual(got["day_max_street_in"], 13.2)


class AlertDispatchCheckTests(unittest.TestCase):
    def _run(self, alerts, sig):
        tmp = Path(tempfile.mkdtemp())
        state = tmp / "alert_state.json"
        state.write_text(json.dumps({"sig": sig}))
        real_join = nowcast.os.path.join

        def fake_join(*parts):
            if parts[-1] == "alert_state.json":
                return str(state)
            return real_join(*parts)

        with mock.patch.object(ff, "fetch_nws_flood_alerts",
                               return_value=alerts), \
                mock.patch.object(nowcast.os.path, "join", fake_join):
            return nowcast.alert_dispatch_check()

    def test_new_alert_triggers_dispatch(self):
        alerts = [{"event": "Flash Flood Warning",
                   "onset": "2026-08-03T10:36:00-04:00"}]
        self.assertEqual(self._run(alerts, "pluv|Flood Watch@x"), 0)

    def test_known_alert_does_not_dispatch(self):
        alerts = [{"event": "Flash Flood Warning",
                   "onset": "2026-08-03T10:36:00-04:00"}]
        sig = ("pluv|Flash Flood Warning@2026-08-03T10:36:00-04:00"
               "|Flood Watch@2026-08-03T03:13:00-04:00")
        self.assertEqual(self._run(alerts, sig), 3)

    def test_unknown_status_fails_closed(self):
        self.assertEqual(self._run(None, ""), 3)

    def test_no_alerts_no_dispatch(self):
        self.assertEqual(self._run([], "anything"), 3)


if __name__ == "__main__":
    unittest.main()
