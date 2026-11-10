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

    def test_quiet_heartbeat_is_ledger_due_not_clock_minute(self):
        """2026-11-10: the heartbeat was gated on the UTC minute being
        exactly 03; GitHub starts that slot at :08-:20, so it fired 8 times
        in six weeks. The due decision belongs to the ledger."""
        gate = self.text.index("- name: Trigger check")
        install = self.text.index("- name: Install radar deps")
        between = self.text[gate:install]
        self.assertIn("--record-gated-quiet --if-due", between)
        self.assertNotIn("date -u +'%M'", between)
        self.assertIn('exit "$hb"', between)   # heartbeat write errors stay red


class LocalSchedulerContractTests(unittest.TestCase):
    def setUp(self):
        self.tick = (ROOT / "bin" / "local_nowcast_tick.sh").read_text()
        self.install = (ROOT / "bin" / "install_local_scheduler.sh").read_text()
        self.ensure = (ROOT / "bin" / "ensure_local_venv.sh").read_text()

    def test_tick_has_stale_lock_recovery_and_nonzero_failures(self):
        self.assertIn("LOCK_STALE_SECONDS=300", self.tick)
        self.assertIn("kill -0", self.tick)
        self.assertIn("tick-status.jsonl", self.tick)
        self.assertIn("fail publish 75 push-retries-exhausted", self.tick)
        self.assertNotIn("|| exit 0", self.tick)

    def test_installer_uses_checked_in_dependency_lock(self):
        # The lock install moved into the shared environment helper
        # (2026-11-10); the installer must delegate to it and never
        # install by hand.
        self.assertIn("bin/ensure_local_venv.sh", self.install)
        self.assertNotIn("pip install", self.install)
        self.assertNotIn("-m venv", self.install)
        self.assertIn("forecast/nowcast-requirements.txt", self.ensure)
        self.assertIn("pip check", self.ensure)
        self.assertNotIn("pip install --quiet xarray", self.ensure)

    def test_environment_is_rebuilt_not_assumed(self):
        """2026-11-03 outage: Homebrew removed the venv's base interpreter
        and the arm failed more than 650 ticks; the installer could not repair an
        existing venv directory."""
        # ready = interpreter runs AND marker matches the lock hash
        self.assertIn('"$V" -c \'import sys\'', self.ensure)
        self.assertIn(".barnacle-ready", self.ensure)
        self.assertIn("shasum -a 256", self.ensure)
        # marker is written only after install, pip check and self-test
        build = self.ensure[self.ensure.index("build() {"):]
        self.assertLess(build.index("pip check"), build.index('> "$READY"'))
        self.assertLess(build.index("import xarray, cfgrib"),
                        build.index('> "$READY"'))
        # launchd's PATH python3 is Apple's 3.9: choose and version-check
        self.assertIn("/opt/homebrew/bin/python3", self.ensure)
        self.assertIn("sys.version_info >= (3, $MIN_MINOR)", self.ensure)
        self.assertNotIn("[ -d ~/.barnacle/venv ] ||", self.install)

    def test_tick_syncs_before_healing_and_heals_before_running(self):
        sync = self.tick.index("git reset --hard -q origin/main || fail sync")
        heal = self.tick.index('ensure_local_venv.sh" --check')
        run = self.tick.index('"$V" forecast/nowcast.py >>')
        self.assertLess(sync, heal)
        self.assertLess(heal, run)
        self.assertIn("HEAL_RETRY_SECONDS=3600", self.tick)
        self.assertIn("fail preflight 69 environment-rebuild-failed", self.tick)
        self.assertNotIn("missing-interpreter", self.tick)

    def test_tick_quiet_publication_is_ledger_due_not_clock_minute(self):
        due = self.tick.index("forecast/nowcast.py --quiet-heartbeat-due")
        run = self.tick.index('"$V" forecast/nowcast.py >>')
        self.assertLess(due, run)   # asked before this run appends its row
        self.assertIn('[ "$quiet_due" = "0" ]', self.tick)
        self.assertNotIn("date -u +'%M'", self.tick)
        self.assertIn("fail inspect 70 quiet-due-check-failed", self.tick)


class DailyWorkflowContractTests(unittest.TestCase):
    def test_commit_uses_utc_date_and_archive_uses_local_date(self):
        text = (ROOT / ".github" / "workflows" /
                "daily_forecast.yml").read_text()
        self.assertIn("utc_date=$(date -u +%Y-%m-%d)", text)
        self.assertIn("local_date=$(date +%Y-%m-%d)", text)
        self.assertIn("hourly update ${{ steps.when.outputs.utc_date }}", text)
        self.assertIn('docs/archive/${{ steps.when.outputs.local_date }}', text)

    def test_delivery_failure_publishes_then_fails_after_push(self):
        """Audit 2026-09-27-a1 R7 / round 05 R4: a delivery-only failure
        (exit 75, never Python's 2) publishes validated artifacts only after
        publish_decision.py verifies a fresh completion receipt; the gate and
        commit steps still run; a FINAL step fails the job after the push."""
        text = (ROOT / ".github" / "workflows" /
                "daily_forecast.yml").read_text()
        forecast_i = text.index("id: forecast")
        gate_i = text.index("Publish gate (no markers, strict JSON)")
        commit_i = text.index("Commit and push docs/ + data/ updates")
        fail_i = text.index("Fail the run if alert delivery failed (after publication)")
        self.assertLess(forecast_i, gate_i)
        self.assertLess(gate_i, commit_i)
        self.assertLess(commit_i, fail_i)
        run_block = text[forecast_i:gate_i]
        self.assertIn('started=$(date -u +%Y-%m-%dT%H:%M:%SZ)', run_block)
        self.assertLess(run_block.index("started=$(date"), run_block.index("python3 flood_forecast_daily.py"))
        self.assertIn('publish_decision.py --rc "$rc" --started-utc "$started"', run_block)
        self.assertIn('if [ "$decision" = "publish-then-fail" ]; then', run_block)
        self.assertIn('echo "delivery_failed=true" >> "$GITHUB_OUTPUT"', run_block)
        self.assertNotIn('-eq 2', run_block)
        self.assertIn("if: steps.forecast.outputs.delivery_failed == 'true'", text)
        self.assertIn("data/alert_delivery_health.json", text)
        gate_block = text[gate_i:commit_i]
        self.assertNotIn("if:", gate_block)
        commit_block = text[commit_i:fail_i]
        self.assertNotIn("\n        if:", commit_block)

if __name__ == "__main__":
    unittest.main()
