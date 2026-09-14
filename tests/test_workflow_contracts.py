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

    def test_quiet_gate_records_named_arm_without_heavy_install(self):
        gate = self.text.index("- name: Trigger check")
        install = self.text.index("- name: Install radar deps")
        between = self.text[gate:install]
        self.assertIn("--record-gated-quiet", between)
        self.assertIn("BARNACLE_SCHEDULER_ARM: github-actions", self.text)


class LocalSchedulerContractTests(unittest.TestCase):
    def setUp(self):
        self.tick = (ROOT / "bin" / "local_nowcast_tick.sh").read_text()
        self.install = (ROOT / "bin" / "install_local_scheduler.sh").read_text()

    def test_tick_has_stale_lock_recovery_and_nonzero_failures(self):
        self.assertIn("LOCK_STALE_SECONDS=300", self.tick)
        self.assertIn("kill -0", self.tick)
        self.assertIn("tick-status.jsonl", self.tick)
        self.assertIn("fail publish 75 push-retries-exhausted", self.tick)
        self.assertNotIn("|| exit 0", self.tick)

    def test_installer_uses_checked_in_dependency_lock(self):
        self.assertIn("forecast/nowcast-requirements.txt", self.install)
        self.assertIn("pip check", self.install)
        self.assertNotIn("pip install --quiet xarray", self.install)


if __name__ == "__main__":
    unittest.main()
