import datetime as dt
import json
import unittest
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import nowcast


UTC = dt.timezone.utc


class StationTimeTests(unittest.TestCase):
    def test_shared_clock_maps_utc_evening_to_previous_local_day(self):
        now = dt.datetime(2026, 8, 2, 0, 39, tzinfo=UTC)
        self.assertEqual(
            ff._station_local_now(now),
            dt.datetime(2026, 8, 1, 20, 39),
        )
        self.assertEqual(ff._station_local_today(now), dt.date(2026, 8, 1))

    def test_utc_to_station_local_uses_winter_offset(self):
        self.assertEqual(
            ff.utc_to_station_local("2026-01-02T00:05:00Z").strftime(
                "%Y-%m-%d %H:%M %z"
            ),
            "2026-01-01 19:05 -0500",
        )

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

    def test_plain_summary_uses_station_day_near_utc_midnight(self):
        forecast = {"all_tides": [
            {"time": "2026-08-01 22:25", "forecast_peak_mllw": 5.5,
             "depths_in": {"regime": "dry"}},
            {"time": "2026-08-02 10:57", "forecast_peak_mllw": 5.5,
             "depths_in": {"regime": "dry"}},
        ]}
        with mock.patch.object(
            ff, "_station_local_today", return_value=dt.date(2026, 8, 1)
        ):
            text = ff.plain_language_summary(forecast)
        self.assertIn("10:25 PM tonight", text)
        self.assertIn("10:57 AM tomorrow morning", text)


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


class NowcastRadarFreshnessTests(unittest.TestCase):
    class _ListingResponse:
        def __init__(self, text):
            self._text = text

        def read(self):
            return self._text.encode()

    @staticmethod
    def _listing(*stamps):
        return "\n".join(
            f'MRMS_PrecipRate_00.00_{stamp}.grib2.gz' for stamp in stamps
        )

    def test_latest_frames_rejects_stale_listing(self):
        listing = self._listing("20260803-120000", "20260803-120200")
        now = dt.datetime(2026, 8, 3, 12, 20, tzinfo=UTC)
        with mock.patch.object(
            nowcast.urllib.request, "urlopen",
            return_value=self._ListingResponse(listing),
        ):
            with self.assertRaisesRegex(RuntimeError, "stale"):
                nowcast.latest_frames(now_utc=now)

    def test_latest_frames_rejects_empty_listing(self):
        now = dt.datetime(2026, 8, 3, 12, 20, tzinfo=UTC)
        with mock.patch.object(
            nowcast.urllib.request, "urlopen",
            return_value=self._ListingResponse("no frames"),
        ):
            with self.assertRaisesRegex(RuntimeError, "no precipitation"):
                nowcast.latest_frames(now_utc=now)

    def test_run_degrades_when_too_few_frames_decode(self):
        now = dt.datetime(2026, 8, 3, 12, 10, tzinfo=UTC)
        frames = [
            (dt.datetime(2026, 8, 3, 11, 10) + dt.timedelta(minutes=6 * i),
             f"stamp-{i}")
            for i in range(11)
        ]
        captured = []

        def sparse_rate(stamp):
            if stamp not in {"stamp-0", "stamp-10"}:
                raise OSError("decode failed")
            return 0.5

        with mock.patch.object(nowcast.ff, "_load_stage_curve"), \
                mock.patch.object(nowcast, "current_bay", return_value=(2.5, "observed")), \
                mock.patch.object(nowcast, "latest_frames", return_value=frames), \
                mock.patch.object(nowcast, "box_rate", side_effect=sparse_rate), \
                mock.patch.object(nowcast, "_write",
                                  side_effect=lambda payload, stamp: captured.append(payload)):
            nowcast.run(now)

        self.assertEqual(captured[0]["radar_quality"], "degraded")
        self.assertEqual(captured[0]["frames_expected"], 11)
        self.assertEqual(captured[0]["frames_succeeded"], 2)
        self.assertIn("insufficient radar coverage", captured[0]["error"])

    def test_run_publishes_full_source_provenance(self):
        now = dt.datetime(2026, 8, 3, 12, 10, tzinfo=UTC)
        frames = [
            (dt.datetime(2026, 8, 3, 11, 10) + dt.timedelta(minutes=6 * i),
             f"stamp-{i}")
            for i in range(11)
        ]
        captured = []
        with mock.patch.object(nowcast.ff, "_load_stage_curve"), \
                mock.patch.object(nowcast, "current_bay", return_value=(2.5, "observed")), \
                mock.patch.object(nowcast, "latest_frames", return_value=frames), \
                mock.patch.object(nowcast, "box_rate", return_value=0.0), \
                mock.patch.object(nowcast, "_write",
                                  side_effect=lambda payload, stamp: captured.append(payload)):
            nowcast.run(now)

        payload = captured[0]
        self.assertEqual(payload["radar_quality"], "ok")
        self.assertEqual(payload["source_latest_utc"], "2026-08-03T12:10:00Z")
        self.assertEqual(payload["source_age_min"], 0.0)
        self.assertEqual(payload["frames_succeeded"], 11)
        self.assertEqual(payload["coverage_minutes"], 60.0)
        self.assertTrue(payload["frames"][0]["utc"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()
