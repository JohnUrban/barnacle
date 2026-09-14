"""Static safety contracts for production workflow ordering."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NowcastWorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / ".github" / "workflows" / "nowcast.yml").read_text()

    def test_alert_checks_and_dispatch_follow_publish(self):
        commit = self.text.index("- name: Commit nowcast.json")
        official = self.text.index("- name: Alert-ingest dispatch check")
        radar = self.text.index("- name: Radar alert dispatch check")
        dispatch = self.text.index(
            "- name: Dispatch forecast workflow for immediate alert evaluation")
        self.assertLess(commit, official)
        self.assertLess(official, dispatch)
        self.assertLess(radar, dispatch)

    def test_one_fail_closed_forecast_dispatch(self):
        endpoint = "actions/workflows/daily_forecast.yml/dispatches"
        self.assertEqual(self.text.count(endpoint), 1)
        self.assertNotIn("continue-on-error: true", self.text)
        self.assertNotIn("dispatch failed (non-fatal)", self.text)
        dispatch = self.text.index(
            "- name: Dispatch forecast workflow for immediate alert evaluation")
        block = self.text[dispatch:]
        self.assertIn("for attempt in 1 2 3", block)
        self.assertIn("exit 1", block)


if __name__ == "__main__":
    unittest.main()
