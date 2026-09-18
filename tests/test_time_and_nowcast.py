import datetime as dt
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import nowcast
from forecast import rendering


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

    def test_noaa_gmt_repeated_hour_has_distinct_storage_keys(self):
        first = ff.noaa_gmt_to_station_string("2026-11-01 05:30")
        second = ff.noaa_gmt_to_station_string("2026-11-01 06:30")
        self.assertEqual(first, "2026-11-01 01:30-04:00")
        self.assertEqual(second, "2026-11-01 01:30-05:00")
        self.assertNotEqual(first, second)
        self.assertEqual(ff.station_local_to_noaa_gmt(first),
                         "20261101 05:30")
        self.assertEqual(ff.station_local_to_noaa_gmt(second),
                         "20261101 06:30")
        self.assertFalse(ff.station_times_match(first, second))

    def test_offset_tide_lead_time_uses_exact_fall_back_fold(self):
        now = dt.datetime(2026, 11, 1, 5, 15, tzinfo=UTC)
        self.assertAlmostEqual(
            ff.hours_until_station_time("2026-11-01 01:30-04:00", now),
            0.25,
        )
        self.assertAlmostEqual(
            ff.hours_until_station_time("2026-11-01 01:30-05:00", now),
            1.25,
        )

    def test_offset_tides_sort_by_instant_across_fall_back(self):
        scrambled = [
            "2026-11-01 01:30-05:00",
            "2026-11-01 01:00-05:00",
            "2026-11-01 01:30-04:00",
            "2026-11-01 01:00-04:00",
        ]
        self.assertEqual(sorted(scrambled, key=ff.station_time_sort_key), [
            "2026-11-01 01:00-04:00",
            "2026-11-01 01:30-04:00",
            "2026-11-01 01:00-05:00",
            "2026-11-01 01:30-05:00",
        ])

    def test_tide_fetch_transports_gmt_and_stores_offset_local(self):
        response = {"predictions": [
            {"t": "2026-11-01 05:30", "v": "5.1", "type": "H"},
            {"t": "2026-11-01 06:30", "v": "5.0", "type": "H"},
        ]}
        captured = {}

        def fake_get(_url, params):
            captured.update(params)
            return response

        with mock.patch.object(
            ff, "_station_local_now", return_value=dt.datetime(2026, 11, 1, 1, 15)
        ), mock.patch.object(ff, "_get", side_effect=fake_get), \
                mock.patch.object(ff, "_tide_cache_save"):
            tides = ff.fetch_tides_24h()

        self.assertEqual(captured["time_zone"], "gmt")
        self.assertEqual(captured["begin_date"], "20261101 03:15")
        self.assertEqual(tides["high"][0][0], "2026-11-01 01:30-04:00")
        self.assertEqual(tides["high"][1][0], "2026-11-01 01:30-05:00")
        self.assertNotEqual(tides["high"][0][0], tides["high"][1][0])

    def test_time_formatters_hide_storage_offset(self):
        stamp = "2026-11-01 01:30-05:00"
        self.assertEqual(ff.format_time_short(stamp), "Sun 1:30 AM")
        self.assertIn("Sun 1:30 AM", ff.format_time_full(stamp))

    def test_clock_only_formatter_does_not_render_utc_offset(self):
        self.assertEqual(
            rendering._clock_hhmm("2026-11-01 01:30-05:00"), "01:30"
        )
        self.assertEqual(
            rendering._clock_hhmm("2026-11-01 01:30"), "01:30"
        )

    def test_low_tide_cache_collapses_legacy_and_offset_duplicate(self):
        cached = {
            "rows": [
                ["2026-11-16 18:48", 0.977],
                ["2026-11-16 18:48-05:00", 0.977],
            ],
            "hrows": [
                ["2026-11-16 12:18", 4.373],
                ["2026-11-16 12:18-05:00", 4.373],
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "low_tides.json"
            path.write_text(json.dumps(cached))
            with mock.patch.object(ff, "LOW_TIDES_CACHE_PATH", str(path)), \
                    mock.patch.object(ff, "_get", return_value={
                        "predictions": []
                    }), mock.patch.object(
                        ff, "_station_local_now",
                        return_value=dt.datetime(2026, 9, 18, 12, 0)
                    ):
                lows = ff._low_tides_span()
            persisted = json.loads(path.read_text())

        self.assertEqual(len(lows), 1)
        self.assertEqual(lows[0]["time"], "2026-11-16 18:48-05:00")
        self.assertEqual(len(persisted["rows"]), 1)
        self.assertEqual(len(persisted["hrows"]), 1)

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

    def test_current_bay_queries_gmt_window(self):
        payload = {"data": [
            {"t": "2026-07-21 13:06", "v": "5.90"},
            {"t": "2026-07-21 13:12", "v": "5.92"},
            {"t": "2026-07-21 13:18", "v": "5.94"},
            {"t": "2026-07-21 13:24", "v": "5.96"},
            {"t": "2026-07-21 13:30", "v": "5.98"},
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
        self.assertIn("time_zone=gmt", captured["url"])
        self.assertIn("begin_date=20260721%2010:30", captured["url"])
        self.assertIn("end_date=20260721%2013:30", captured["url"])

    def test_current_bay_uses_flagged_astronomical_fallback(self):
        now = dt.datetime(2026, 7, 21, 9, 30)
        with mock.patch.object(
            nowcast.urllib.request, "urlopen", side_effect=OSError("offline")
        ), mock.patch.object(nowcast, "_predicted_bay", return_value=(3.24, "x")):
            level, source = nowcast.current_bay(now)

        self.assertEqual(level, 3.24)
        self.assertEqual(source, "astronomical-fallback")

    def test_current_bay_rejects_nonempty_but_stale_observations(self):
        payload = {"data": [
            {"t": "2026-07-21 12:54", "v": "5.90"},
        ]}
        now = dt.datetime(2026, 7, 21, 9, 30)
        with mock.patch.object(
            nowcast.urllib.request, "urlopen",
            return_value=self._Response(payload),
        ), mock.patch.object(
            nowcast, "_predicted_bay", return_value=(3.24, "x")
        ):
            level, source = nowcast.current_bay(now)

        self.assertEqual(level, 3.24)
        self.assertEqual(source, "astronomical-fallback-stale-gauge")


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


class NowcastHeartbeatTests(unittest.TestCase):
    def test_legacy_rows_migrate_to_named_structured_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "heartbeat.csv"
            path.write_text(
                "generated_utc,active,source_age_min\n"
                "2026-09-14T17:00:00Z,1,3.0\n")
            now = dt.datetime(2026, 9, 14, 18, 0, tzinfo=UTC)
            with mock.patch.object(nowcast, "HEARTBEAT_PATH", str(path)), \
                    mock.patch.dict(nowcast.os.environ, {
                        "BARNACLE_SCHEDULER_ARM": "github-actions"}):
                ok, error = nowcast._append_heartbeat(
                    {"generated_utc": "2026-09-14T18:00:00Z",
                     "active": False, "source_age_min": ""},
                    now, phase="gate", outcome="gated-quiet")
            with path.open() as source:
                rows = list(csv.DictReader(source))
        self.assertTrue(ok, error)
        self.assertEqual(rows[0]["arm"], "legacy-unknown")
        self.assertEqual(rows[1]["arm"], "github-actions")
        self.assertEqual(rows[1]["outcome"], "gated-quiet")


if __name__ == "__main__":
    unittest.main()
