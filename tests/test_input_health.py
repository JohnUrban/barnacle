import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import check_artifacts
from forecast import flood_forecast_daily as ff
from forecast import nowcast


class InputHealthTests(unittest.TestCase):
    def test_qpf_failure_is_unavailable_not_empty_forecast(self):
        with mock.patch.object(ff, "_get", side_effect=OSError("offline")):
            self.assertIsNone(ff.fetch_nws_qpf())

    def test_alert_failure_is_unavailable_not_no_active_alerts(self):
        with mock.patch.object(ff, "_get", side_effect=OSError("offline")):
            self.assertIsNone(ff.fetch_nws_flood_alerts())

    def test_water_series_omits_pluvial_line_when_qpf_unavailable(self):
        stamp = ff._station_local_now().strftime("%Y-%m-%d %H:%M")
        response = {"predictions": [{"t": stamp, "v": "5.0"}]}
        with mock.patch.object(ff, "_get", return_value=response), \
                mock.patch.object(ff, "_tide_cache_save"), \
                mock.patch.object(ff, "_tide_cache_load", return_value={}), \
                mock.patch.object(ff, "fetch_observed_recent", return_value=[]), \
                mock.patch.object(ff, "simulate_pluvial_series") as simulate:
            series = ff.build_water_series(
                0.2, qpf_hourly=None, hours_back=1, hours_forward=1
            )

        self.assertEqual(len(series), 1)
        self.assertNotIn("pluvial_navd88", series[0])
        self.assertEqual(series[0]["water_navd88"], series[0]["tide_navd88"])
        simulate.assert_not_called()

    def test_forecast_exports_metadata_and_degraded_sources(self):
        tide_time = (ff._station_local_now() + dt.timedelta(hours=6)).strftime(
            "%Y-%m-%d %H:%M"
        )
        patches = [
            mock.patch.object(ff, "fetch_tides_24h", return_value={
                "high": [(tide_time, 5.8)], "low": [],
            }),
            mock.patch.object(
                ff, "fetch_temperature_72h_mean", side_effect=OSError("offline")
            ),
            mock.patch.object(
                ff, "fetch_nws_hourly_forecast", side_effect=OSError("offline")
            ),
            mock.patch.object(ff, "fetch_nws_qpf", return_value=None),
            mock.patch.object(ff, "fetch_current_surge", return_value=None),
            mock.patch.object(ff, "fetch_nws_flood_alerts", return_value=None),
            mock.patch.object(ff, "fetch_surge_swing_6h", return_value=None),
            mock.patch.object(ff, "fetch_recent_history", return_value=[]),
            mock.patch.object(ff, "fetch_high_tides_lookahead", return_value=[]),
            mock.patch.object(ff, "fetch_observed_recent", return_value=[]),
            mock.patch.object(ff, "build_water_series", return_value=[]),
            mock.patch.object(ff, "build_seasonal_context", return_value={}),
            mock.patch.object(ff, "_today_lookback", return_value=None),
        ]
        with patches[0], patches[1], patches[2], patches[3], patches[4], \
                patches[5], patches[6], patches[7], patches[8], patches[9], \
                patches[10], patches[11], patches[12]:
            forecast = ff.build_forecast()

        self.assertRegex(forecast["generated_utc"], r"Z$")
        self.assertEqual(forecast["forecast_schema_version"], "1.0")
        self.assertEqual(forecast["model_version"], ff.CURRENT_MODEL_VERSION)
        self.assertIsNone(forecast["cumulative_rain_24h_in"])
        self.assertIsNone(forecast["peak_rain_rate_in_hr"])
        self.assertEqual(forecast["surge_source"], "astronomical-only-degraded")
        self.assertEqual(
            forecast["input_health"]["nws_qpf"]["status"], "unavailable"
        )
        self.assertIn("nws_qpf", forecast["degraded_inputs"])
        self.assertIn("surge_observation", forecast["degraded_inputs"])

    def test_health_banner_says_missing_is_not_zero(self):
        forecast = {
            "degraded_inputs": ["nws_qpf"],
            "input_health": {
                "nws_qpf": {"status": "unavailable", "detail": "offline"},
            },
        }
        self.assertIn("not being treated as zero", " ".join(
            ff._render_input_health_text(forecast)
        ))
        self.assertIn("not being treated", ff._render_input_health_html(forecast))

    def test_nowcast_runs_conservatively_when_alert_status_is_unknown(self):
        with mock.patch.object(
            ff, "fetch_nws_flood_alerts", return_value=None
        ), mock.patch.object(ff, "fetch_nws_hourly_forecast") as hourly:
            code = nowcast.trigger_check()
        self.assertEqual(code, 0)
        hourly.assert_not_called()

    def test_nowcast_runs_conservatively_when_hourly_check_fails(self):
        with mock.patch.object(
            ff, "fetch_nws_flood_alerts", return_value=[]
        ), mock.patch.object(
            ff, "fetch_nws_hourly_forecast", side_effect=OSError("offline")
        ):
            code = nowcast.trigger_check()
        self.assertEqual(code, 0)

    def test_forecast_metadata_gate_checks_degraded_consistency(self):
        payload = {
            "generated_utc": "2026-07-21T16:00:00Z",
            "forecast_schema_version": "1.0",
            "model_version": "v0.10",
            "input_health": {
                "nws_qpf": {"status": "unavailable", "detail": "offline"},
            },
            "degraded_inputs": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forecast.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            failures = check_artifacts.validate_forecast_metadata(str(path))
            payload["degraded_inputs"] = ["nws_qpf"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            repaired = check_artifacts.validate_forecast_metadata(str(path))
        self.assertTrue(any("degraded_inputs mismatch" in f for f in failures))
        self.assertEqual(repaired, [])


if __name__ == "__main__":
    unittest.main()
