import datetime as dt
import json
import unittest
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import nowcast


UTC = dt.timezone.utc


class StationTimeTests(unittest.TestCase):
    def test_summer_lead_time_uses_edt_offset(self):
        now = dt.datetime(2026, 7, 21, 14, 15, tzinfo=UTC)
        self.assertAlmostEqual(
            ff.hours_until_station_time("2026-07-21 14:24", now),
            4.15,
            places=6,
        )

    def test_winter_lead_time_uses_est_offset(self):
        now = dt.datetime(2026, 1, 21, 14, 15, tzinfo=UTC)
        self.assertAlmostEqual(
            ff.hours_until_station_time("2026-01-21 10:24", now),
            1.15,
            places=6,
        )

    def test_spring_dst_boundary_compares_real_elapsed_time(self):
        # 01:30 EST -> 03:30 EDT spans one real hour on spring-forward day.
        now = dt.datetime(2026, 3, 8, 6, 30, tzinfo=UTC)
        self.assertAlmostEqual(
            ff.hours_until_station_time("2026-03-08 03:30", now),
            1.0,
        )

    def test_fall_dst_boundary_compares_real_elapsed_time(self):
        # 01:30 EDT -> 02:30 EST spans two real hours on fall-back day.
        now = dt.datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
        self.assertAlmostEqual(
            ff.hours_until_station_time("2026-11-01 02:30", now),
            2.0,
        )

    def test_today_peak_does_not_borrow_tomorrow(self):
        series = [
            {"time": "2026-07-21 10:00", "water_navd88": 3.6},
            {"time": "2026-07-21 14:30", "water_navd88": 4.1},
            {"time": "2026-07-22 02:30", "water_navd88": 5.2},
        ]
        now = dt.datetime(2026, 7, 21, 9, 0, tzinfo=ff.STATION_TZ)
        self.assertEqual(
            ff._future_today_peak(series, now),
            (4.1, "2026-07-21 14:30"),
        )


class NowcastBayTests(unittest.TestCase):
    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def read(self):
            return json.dumps(self.payload).encode()

    def test_current_bay_queries_station_local_window(self):
        payload = {"data": [
            {"t": "2026-07-21 09:06", "v": "5.90"},
            {"t": "2026-07-21 09:12", "v": "5.92"},
            {"t": "2026-07-21 09:18", "v": "5.94"},
            {"t": "2026-07-21 09:24", "v": "5.96"},
            {"t": "2026-07-21 09:30", "v": "5.98"},
        ]}
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            return self._Response(payload)

        now = dt.datetime(2026, 7, 21, 9, 30)
        with mock.patch.object(nowcast.urllib.request, "urlopen", fake_urlopen):
            level, source = nowcast.current_bay(now)

        self.assertEqual(source, "observed")
        self.assertAlmostEqual(level, 5.98 - 2.82)
        self.assertIn("begin_date=20260721%2006:30", captured["url"])
        self.assertIn("end_date=20260721%2009:30", captured["url"])

    def test_current_bay_uses_flagged_astronomical_fallback(self):
        now = dt.datetime(2026, 7, 21, 9, 30)
        with mock.patch.object(
            nowcast.urllib.request, "urlopen", side_effect=OSError("offline")
        ), mock.patch.object(nowcast, "_predicted_bay", return_value=(3.24, "x")):
            level, source = nowcast.current_bay(now)

        self.assertEqual(level, 3.24)
        self.assertEqual(source, "astronomical-fallback")


if __name__ == "__main__":
    unittest.main()
