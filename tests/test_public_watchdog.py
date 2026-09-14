import datetime as dt
import unittest

from bin import public_health_watchdog as watchdog


UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 14, 18, 0, tzinfo=UTC)


def _inputs():
    forecast = {"generated_utc": "2026-09-14T17:10:00Z"}
    nowcast = {"generated_utc": "2026-09-14T17:50:00Z", "active": True,
               "source_latest_utc": "2026-09-14T17:49:00Z",
               "radar_quality": "ok"}
    runs = {"workflow_runs": [{"status": "completed", "conclusion": "success",
                                "updated_at": "2026-09-14T17:50:00Z"}]}
    return forecast, nowcast, runs


class PublicWatchdogTests(unittest.TestCase):
    def test_healthy_inputs(self):
        self.assertEqual(watchdog.assess(*_inputs(), now=NOW), [])

    def test_detects_control_plane_and_publication_staleness(self):
        forecast, nowcast, runs = _inputs()
        forecast["generated_utc"] = "2026-09-14T15:00:00Z"
        runs["workflow_runs"][0]["updated_at"] = "2026-09-14T16:00:00Z"
        issues = watchdog.assess(forecast, nowcast, runs, now=NOW)
        self.assertTrue(any("forecast artifact" in x for x in issues))
        self.assertTrue(any("workflow" in x for x in issues))

    def test_active_nowcast_checks_source_not_only_file_time(self):
        forecast, nowcast, runs = _inputs()
        nowcast["source_latest_utc"] = "2026-09-14T17:20:00Z"
        issues = watchdog.assess(forecast, nowcast, runs, now=NOW)
        self.assertTrue(any("active nowcast source" in x for x in issues))

    def test_required_arm_uses_structured_heartbeat(self):
        heartbeat = ("generated_utc,arm,phase,outcome,active,source_age_min,detail\n"
                     "2026-09-14T17:50:00Z,local-launchd,publish,ok,0,3.0,\n")
        self.assertEqual(watchdog.assess(
            *_inputs(), heartbeat_text=heartbeat, now=NOW,
            required_arms=["local-launchd"]), [])
        issues = watchdog.assess(
            *_inputs(), heartbeat_text=heartbeat, now=NOW,
            required_arms=["external-trigger"])
        self.assertIn("scheduler arm external-trigger has no heartbeat", issues)


if __name__ == "__main__":
    unittest.main()
