import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff


UTC = dt.timezone.utc


def _state(**changes):
    value = {
        "rank": 0,
        "sig": "",
        "last_sent_rank": 0,
        "last_sent_sig": "",
        "last_sent_ts": "",
        "last_sent_channels": [],
    }
    value.update(changes)
    return value


def _rain_forecast(onset="2026-07-21T12:00:00-04:00", level="elevated"):
    return {
        "all_tides": [],
        "pluvial_risk": {
            "level": level,
            "nws_flood_alerts": [{"event": "Flood Watch", "onset": onset}],
        },
    }


def _tide_forecast(regime, when="2026-07-21 14:30"):
    return {
        "all_tides": [{
            "time": when,
            "depths_in": {"regime": regime},
        }],
        "pluvial_risk": {},
    }


class AlertDecisionTests(unittest.TestCase):
    def setUp(self):
        self.t0 = dt.datetime(2026, 7, 21, 16, 0, tzinfo=UTC)

    def test_appearance_sends_without_mutating_state(self):
        state = _state()
        decision = ff.evaluate_alert(_rain_forecast(), state, self.t0)
        self.assertTrue(decision["send"])
        self.assertIn("appeared", decision["reason"])
        self.assertEqual(state, _state())

    def test_failed_delivery_remains_retryable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alert_state.json"
            first = ff.evaluate_alert(_rain_forecast(), _state(), self.t0)
            saved = ff.persist_alert_state(first, [], str(path))
            retry = ff.evaluate_alert(
                _rain_forecast(), saved, self.t0 + dt.timedelta(hours=1)
            )

        self.assertTrue(retry["send"])
        self.assertEqual(saved["last_sent_rank"], 0)
        self.assertEqual(saved["last_sent_ts"], "")

    def test_successful_delivery_acknowledges_and_stops_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alert_state.json"
            first = ff.evaluate_alert(_rain_forecast(), _state(), self.t0)
            saved = ff.persist_alert_state(first, ["ntfy"], str(path))
            repeat = ff.evaluate_alert(
                _rain_forecast(), saved, self.t0 + dt.timedelta(hours=1)
            )

        self.assertFalse(repeat["send"])
        self.assertEqual(saved["last_sent_channels"], ["ntfy"])
        self.assertEqual(saved["last_sent_rank"], 3)

    def test_same_event_after_all_clear_obeys_24_hour_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alert_state.json"
            first = ff.evaluate_alert(_rain_forecast(), _state(), self.t0)
            sent = ff.persist_alert_state(first, ["email"], str(path))
            clear = ff.evaluate_alert(
                {"all_tides": [], "pluvial_risk": {}}, sent,
                self.t0 + dt.timedelta(hours=1),
            )
            cleared = ff.persist_alert_state(clear, [], str(path))
            early = ff.evaluate_alert(
                _rain_forecast(), cleared, self.t0 + dt.timedelta(hours=2)
            )
            late = ff.evaluate_alert(
                _rain_forecast(), cleared, self.t0 + dt.timedelta(hours=25)
            )

        self.assertFalse(early["send"])
        self.assertIn("cooldown", early["reason"])
        self.assertTrue(late["send"])

    def test_new_same_rank_warning_sends_inside_cooldown(self):
        first = ff.evaluate_alert(_rain_forecast(), _state(), self.t0)
        with tempfile.TemporaryDirectory() as tmp:
            sent = ff.persist_alert_state(
                first, ["ntfy"], str(Path(tmp) / "state.json")
            )
        second = ff.evaluate_alert(
            _rain_forecast("2026-07-22T08:00:00-04:00"), sent,
            self.t0 + dt.timedelta(hours=2),
        )
        self.assertTrue(second["send"])
        self.assertIn("new event", second["reason"])

    def test_escalation_sends_immediately(self):
        street = ff.evaluate_alert(_tide_forecast("street"), _state(), self.t0)
        with tempfile.TemporaryDirectory() as tmp:
            sent = ff.persist_alert_state(
                street, ["email"], str(Path(tmp) / "state.json")
            )
        severe = ff.evaluate_alert(
            _tide_forecast("severe"), sent, self.t0 + dt.timedelta(minutes=5)
        )
        self.assertTrue(severe["send"])
        self.assertIn("escalated", severe["reason"])

    def test_lower_rank_tide_does_not_destabilize_rain_signature(self):
        forecast = _rain_forecast()
        forecast["all_tides"] = [{
            "time": "2026-07-21 14:30",
            "depths_in": {"regime": "street"},
        }]
        first_sig = ff.compute_alert_level(forecast)[2]
        forecast["all_tides"][0]["time"] = "2026-07-22 03:00"
        second_sig = ff.compute_alert_level(forecast)[2]
        self.assertEqual(first_sig, second_sig)

    def test_compatibility_wrapper_does_not_write_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alert_state.json"
            original = _state()
            path.write_text(json.dumps(original))
            with mock.patch.object(ff, "ALERT_STATE_PATH", str(path)):
                send, _reason = ff.should_send_alert(_rain_forecast())
            after = json.loads(path.read_text())

        self.assertTrue(send)
        self.assertEqual(after, original)


class AlertDeliveryTests(unittest.TestCase):
    class _Response:
        def read(self):
            return b"ok"

    def test_ntfy_still_succeeds_when_email_fails(self):
        env = {
            "NTFY_TOPIC": "private-test-topic",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_USER": "user",
            "SMTP_PASS": "secret",
            "SMTP_FROM": "from@example.test",
            "SMTP_TO": "to@example.test",
        }
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            ff, "build_sms_text", return_value="alert"
        ), mock.patch.object(
            ff, "urlopen", return_value=self._Response()
        ), mock.patch.object(
            ff, "send_email", side_effect=OSError("smtp unavailable")
        ):
            result = ff.deliver_alert(
                _rain_forecast(), "subject", "text", "<html></html>"
            )

        self.assertEqual(result["succeeded"], ["ntfy"])
        self.assertIn("email", result["attempted"])
        self.assertEqual(result["failed"][0]["channel"], "email")

    def test_sms_failure_restores_original_email_recipient(self):
        env = {
            "SMTP_HOST": "smtp.example.test",
            "SMTP_USER": "user",
            "SMTP_PASS": "secret",
            "SMTP_FROM": "from@example.test",
            "SMTP_TO": "mail@example.test",
            "ALERT_SMS_TO": "sms@example.test",
        }
        recipients = []

        def fail_sms(_subject, _text, _html, inline_png=None):
            recipients.append(os.environ["SMTP_TO"])
            if os.environ["SMTP_TO"] == "sms@example.test":
                raise OSError("gateway unavailable")

        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            ff, "build_sms_text", return_value="alert"
        ), mock.patch.object(ff, "send_email", side_effect=fail_sms):
            result = ff.deliver_alert(
                _rain_forecast(), "subject", "text", "<html></html>"
            )
            restored = os.environ["SMTP_TO"]

        self.assertEqual(recipients, ["mail@example.test", "sms@example.test"])
        self.assertEqual(restored, "mail@example.test")
        self.assertEqual(result["succeeded"], ["email"])


if __name__ == "__main__":
    unittest.main()
