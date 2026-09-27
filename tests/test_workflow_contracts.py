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


class DailyWorkflowContractTests(unittest.TestCase):
    def test_commit_uses_utc_date_and_archive_uses_local_date(self):
        text = (ROOT / ".github" / "workflows" /
                "daily_forecast.yml").read_text()
        self.assertIn("utc_date=$(date -u +%Y-%m-%d)", text)
        self.assertIn("local_date=$(date +%Y-%m-%d)", text)
        self.assertIn("hourly update ${{ steps.when.outputs.utc_date }}", text)
        self.assertIn('docs/archive/${{ steps.when.outputs.local_date }}', text)

    def test_delivery_failure_publishes_then_fails_after_push(self):
        """Audit 2026-09-27-a1 R7: exit 2 (every alert rail failed after the
        forecast generated) must not withhold validated artifacts. The
        forecast step captures the code, the gate and commit steps still run,
        and a FINAL step fails the job so the outage stays visible."""
        text = (ROOT / ".github" / "workflows" /
                "daily_forecast.yml").read_text()
        forecast_i = text.index("id: forecast")
        gate_i = text.index("Publish gate (no markers, strict JSON)")
        commit_i = text.index("Commit and push docs/ + data/ updates")
        fail_i = text.index("Fail the run if alert delivery failed (after publication)")
        self.assertLess(forecast_i, gate_i)
        self.assertLess(gate_i, commit_i)
        self.assertLess(commit_i, fail_i)
        self.assertIn('if [ "$rc" -eq 2 ]; then', text)
        self.assertIn('echo "delivery_failed=true" >> "$GITHUB_OUTPUT"', text)
        self.assertIn('elif [ "$rc" -ne 0 ]; then\n            exit "$rc"', text)
        self.assertIn("if: steps.forecast.outputs.delivery_failed == 'true'", text)
        self.assertIn("data/alert_delivery_health.json", text)
        # the gate and commit steps carry no condition that would skip them
        gate_block = text[gate_i:commit_i]
        self.assertNotIn("if:", gate_block)
        commit_block = text[commit_i:fail_i]
        self.assertNotIn("\n        if:", commit_block)


if __name__ == "__main__":
    unittest.main()
