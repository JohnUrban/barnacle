"""Audit 2026-09-27-a1 R7: alert transport health is separate from forecast
publication. A run whose forecast generated but whose every requested rail
failed records the failure, keeps the alert eligible for retry, and signals
the workflow with a DISTINCT exit code so validated artifacts still publish.
Nothing here may mark a failed alert as delivered."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from forecast import flood_forecast_daily as ff

NOW = dt.datetime(2026, 9, 26, 11, 9, tzinfo=dt.timezone.utc)


def _decision(previous=None, send=True):
    return {"send": send, "rank": 3, "sig": "tide:2026-09-26 08:54-04:00",
            "label": "SEVERE", "reason": "test", "now_utc": NOW,
            "previous": previous or {}}


def _gate(send=False):
    return {"send": send, "reason": "test gate", "class": 3}


class DeliveryHealthRecordTests(unittest.TestCase):
    def _record(self, delivery):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "health.json")
            health = ff.record_delivery_health(
                delivery, _decision(), {"ntfy", "email"}, path=path)
            on_disk = json.loads(Path(path).read_text())
        self.assertEqual(health, on_disk)
        return health

    def test_total_failure_is_failed_and_retry_eligible(self):
        h = self._record({"attempted": ["ntfy", "email"], "succeeded": [],
                          "failed": [{"channel": "ntfy", "error": "latin-1"},
                                     {"channel": "email", "error": "smtp"}]})
        self.assertEqual(h["status"], "failed")
        self.assertTrue(h["retry_eligible"])
        self.assertFalse(h["publication_blocked"])
        self.assertEqual([f["channel"] for f in h["failed"]], ["ntfy", "email"])

    def test_partial_failure_is_partial(self):
        h = self._record({"attempted": ["ntfy", "email"], "succeeded": ["email"],
                          "failed": [{"channel": "ntfy", "error": "boom"}]})
        self.assertEqual(h["status"], "partial")
        self.assertTrue(h["retry_eligible"])
        self.assertEqual(h["succeeded"], ["email"])

    def test_clean_delivery_is_ok(self):
        h = self._record({"attempted": ["ntfy"], "succeeded": ["ntfy"],
                          "failed": []})
        self.assertEqual(h["status"], "ok")
        self.assertFalse(h["retry_eligible"])


class SettleDeliveryTests(unittest.TestCase):
    def _settle(self, delivery, previous=None):
        with tempfile.TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "alert_state.json")
            health = str(Path(tmp) / "health.json")
            ok = ff._settle_delivery(
                _decision(previous), delivery, {"ntfy", "email"},
                _gate(), _gate(), _gate(), "subject",
                state_path=state, health_path=health)
            return ok, json.loads(Path(state).read_text()), \
                json.loads(Path(health).read_text())

    def test_total_failure_keeps_alert_unsent_and_returns_false(self):
        ok, state, health = self._settle(
            {"attempted": ["ntfy", "email"], "succeeded": [],
             "failed": [{"channel": "ntfy", "error": "x"},
                        {"channel": "email", "error": "y"}]})
        self.assertFalse(ok)
        self.assertEqual(health["status"], "failed")
        # honest sent-state: nothing acknowledged, both rails pending
        self.assertEqual(state["last_sent_sig"], "")
        self.assertEqual(state["last_sent_channels"], [])
        self.assertEqual(state["pending_base"]["channels"], ["email", "ntfy"])

    def test_partial_failure_acknowledges_only_the_delivered_rail(self):
        ok, state, health = self._settle(
            {"attempted": ["ntfy", "email"], "succeeded": ["email"],
             "failed": [{"channel": "ntfy", "error": "x"}]})
        self.assertTrue(ok)
        self.assertEqual(health["status"], "partial")
        self.assertEqual(state["last_sent_channels"], ["email"])
        self.assertEqual(state["pending_base"]["channels"], ["ntfy"])

    def test_success_clears_pending_and_records_ok(self):
        ok, state, health = self._settle(
            {"attempted": ["ntfy", "email"], "succeeded": ["ntfy", "email"],
             "failed": []},
            previous={"pending_base": {"sig": "tide:2026-09-26 08:54-04:00",
                                       "rank": 3, "channels": ["ntfy"]}})
        self.assertTrue(ok)
        self.assertEqual(health["status"], "ok")
        self.assertNotIn("pending_base", state)
        self.assertEqual(state["last_sent_channels"], ["email", "ntfy"])

    def test_exit_code_contract(self):
        # the workflow keys on this value AND a fresh receipt (round 05 R4)
        self.assertEqual(ff.DELIVERY_FAILED_EXIT, 75)
        src = Path(ff.__file__).read_text()
        self.assertIn("raise SystemExit(DELIVERY_FAILED_EXIT)", src)
        self.assertNotIn("raise SystemExit(2)", src)


class DeliveryHealthPrivacyTests(unittest.TestCase):
    """Round 05 R3: the health file is committed to a public repository, so
    it may carry an error class, category and protocol code — never transport
    message text, which includes recipient addresses (the SMS gateway
    address is a phone number) and topic URLs."""

    def _persist(self, exc):
        delivery = {"attempted": ["sms"], "succeeded": [],
                    "failed": [{"channel": "sms", "error": str(exc), "exception": exc,
                                **ff._delivery_error_facts(exc)}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "health.json")
            ff.record_delivery_health(delivery, _decision(), {"sms"}, path=path)
            return Path(path).read_text()

    def test_smtp_recipient_address_never_reaches_the_file(self):
        import smtplib
        recipient = "15555550123@sms.example.invalid"
        text = self._persist(smtplib.SMTPRecipientsRefused({recipient: (550, b"recipient refused")}))
        self.assertNotIn(recipient, text)
        self.assertNotIn("15555550123", text)
        self.assertNotIn("refused", text)
        entry = json.loads(text)["failed"][0]
        self.assertEqual((entry["error_class"], entry["error_category"], entry["error_code"]),
                         ("SMTPRecipientsRefused", "smtp-recipients", 550))
        self.assertNotIn("error", entry)

    def test_smtp_auth_and_ntfy_url_are_reduced_to_facts(self):
        import smtplib
        import urllib.error
        text = self._persist(smtplib.SMTPAuthenticationError(535, b"auth failed for user secret@example.invalid"))
        self.assertNotIn("secret@example.invalid", text)
        self.assertIn('"smtp-auth"', text)
        text = self._persist(urllib.error.HTTPError("https://ntfy.sh/private-topic-xyz", 429, "Too Many", {}, None))
        self.assertNotIn("private-topic-xyz", text)
        entry = json.loads(text)["failed"][0]
        self.assertEqual((entry["error_category"], entry["error_code"]), ("http", 429))

    def test_encoding_and_config_categories(self):
        facts = ff._delivery_error_facts(UnicodeEncodeError("latin-1", "\u2033", 0, 1, "ordinal not in range"))
        self.assertEqual(facts["error_category"], "encoding")
        self.assertEqual(ff._delivery_error_facts("incomplete configuration; missing SMTP_TO")["error_category"], "config")

    def test_legacy_failure_dict_without_facts_is_still_sanitized(self):
        delivery = {"attempted": ["email"], "succeeded": [],
                    "failed": [{"channel": "email", "error": "SMTP said no to 15555550123@sms.example.invalid"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "health.json")
            ff.record_delivery_health(delivery, _decision(), {"email"}, path=path)
            text = Path(path).read_text()
        self.assertNotIn("15555550123", text)


if __name__ == "__main__":
    unittest.main()
