"""Round 05 R4: exit status alone must not authorize publishing on a
delivery-only failure. publish_decision.py requires DELIVERY_FAILED_EXIT (75)
AND a fresh completion receipt; argparse's exit 2, generation failures and
stale/mismatched receipts all refuse."""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forecast import flood_forecast_daily as ff
from forecast import publish_decision as pd

ROOT = Path(__file__).resolve().parents[1]
STARTED = "2026-09-27T23:00:00Z"


def _files(tmp, *, updated="2026-09-27T23:01:30Z", status="failed",
           generated="2026-09-27T23:01:00Z", receipt_generated="2026-09-27T23:01:00Z"):
    health = Path(tmp) / "health.json"
    forecast = Path(tmp) / "forecast.json"
    health.write_text(json.dumps({"updated_utc": updated, "status": status,
                                  "run": {"forecast_generated_utc": receipt_generated}}))
    forecast.write_text(json.dumps({"generated_utc": generated}))
    return str(forecast), str(health)


class ExitStatusTests(unittest.TestCase):
    def test_delivery_failed_exit_is_not_pythons_two(self):
        self.assertEqual(ff.DELIVERY_FAILED_EXIT, 75)
        self.assertEqual(pd.DELIVERY_FAILED_EXIT, ff.DELIVERY_FAILED_EXIT)
        src = Path(ff.__file__).read_text()
        self.assertIn("raise SystemExit(DELIVERY_FAILED_EXIT)", src)
        self.assertNotIn("raise SystemExit(2)", src)

    def test_real_early_cli_failure_exits_two_and_is_refused(self):
        run = subprocess.run([sys.executable, str(ROOT / "forecast" / "flood_forecast_daily.py"),
                              "--invalid-review-flag"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(run.returncode, 2)
        with tempfile.TemporaryDirectory() as tmp:
            outcome, reason = pd.decide(run.returncode, STARTED, *_files(tmp))
        self.assertIsNone(outcome)
        self.assertIn("not a delivery-only failure", reason)

    def test_generation_failure_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _ = pd.decide(1, STARTED, *_files(tmp))
        self.assertIsNone(outcome)


class ReceiptTests(unittest.TestCase):
    def test_fresh_matching_receipt_allows_publish_then_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(pd.decide(75, STARTED, *_files(tmp)), ("publish-then-fail", None))

    def test_success_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(pd.decide(0, STARTED, *_files(tmp)), ("publish", None))

    def test_stale_receipt_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, reason = pd.decide(75, STARTED, *_files(tmp, updated="2026-09-27T22:10:00Z"))
        self.assertIsNone(outcome)
        self.assertIn("predates this run", reason)

    def test_receipt_not_matching_forecast_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, reason = pd.decide(75, STARTED, *_files(tmp, receipt_generated="2026-09-27T22:01:00Z"))
        self.assertIsNone(outcome)
        self.assertIn("does not match", reason)

    def test_stale_forecast_artifact_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _ = pd.decide(75, STARTED, *_files(tmp, generated="2026-09-27T22:01:00Z",
                                                        receipt_generated="2026-09-27T22:01:00Z"))
        self.assertIsNone(outcome)

    def test_partial_status_with_exit_75_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, reason = pd.decide(75, STARTED, *_files(tmp, status="partial"))
        self.assertIsNone(outcome)
        self.assertIn("not 'failed'", reason)

    def test_missing_receipt_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _ = pd.decide(75, STARTED, str(Path(tmp) / "nope.json"), str(Path(tmp) / "no.json"))
        self.assertIsNone(outcome)

    def test_settle_delivery_writes_the_receipt_the_decision_checks(self):
        now = dt.datetime(2026, 9, 27, 23, 1, 30, tzinfo=dt.timezone.utc)
        decision = {"send": True, "rank": 3, "sig": "x", "label": "SEVERE", "reason": "t",
                    "now_utc": now, "previous": {}}
        gate = {"send": False, "reason": "g", "class": 3}
        with tempfile.TemporaryDirectory() as tmp:
            health = str(Path(tmp) / "health.json")
            forecast = Path(tmp) / "forecast.json"
            forecast.write_text(json.dumps({"generated_utc": "2026-09-27T23:01:00Z"}))
            ok = ff._settle_delivery(decision, {"attempted": ["ntfy"], "succeeded": [],
                                                "failed": [{"channel": "ntfy", "error": "x"}]},
                                     {"ntfy"}, gate, gate, gate, "subject",
                                     state_path=str(Path(tmp) / "state.json"), health_path=health,
                                     forecast_generated_utc="2026-09-27T23:01:00Z")
            self.assertFalse(ok)
            self.assertEqual(pd.decide(75, STARTED, str(forecast), health), ("publish-then-fail", None))

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            forecast, health = _files(tmp)
            run = subprocess.run([sys.executable, str(ROOT / "forecast" / "publish_decision.py"),
                                  "--rc", "75", "--started-utc", STARTED,
                                  "--forecast-json", forecast, "--health", health],
                                 capture_output=True, text=True)
            self.assertEqual((run.returncode, run.stdout.strip()), (0, "publish-then-fail"))
            run = subprocess.run([sys.executable, str(ROOT / "forecast" / "publish_decision.py"),
                                  "--rc", "2", "--started-utc", STARTED,
                                  "--forecast-json", forecast, "--health", health],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn("DO NOT PUBLISH", run.stderr)


if __name__ == "__main__":
    unittest.main()
