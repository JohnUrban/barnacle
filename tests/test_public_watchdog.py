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


class QuietModeTests(unittest.TestCase):
    def test_quiet_coalesced_nowcast_is_healthy(self):
        # 2026-09-15 regression: quiet weather coalesces publication, so
        # a 3-hour-old inactive nowcast + 60-minute workflow drift must
        # NOT page (they paged all night).
        forecast = {"generated_utc": "2026-09-14T17:10:00Z"}
        nowcast = {"generated_utc": "2026-09-14T15:00:00Z",
                   "active": False}
        runs = {"workflow_runs": [{
            "status": "completed", "conclusion": "success",
            "updated_at": "2026-09-14T17:00:00Z"}]}
        self.assertEqual(
            watchdog.assess(forecast, nowcast, runs, now=NOW), [])

    def test_quiet_multiday_corpse_still_detected(self):
        forecast = {"generated_utc": "2026-09-14T17:10:00Z"}
        nowcast = {"generated_utc": "2026-09-12T10:00:00Z",
                   "active": False}
        runs = {"workflow_runs": [{
            "status": "completed", "conclusion": "success",
            "updated_at": "2026-09-14T17:00:00Z"}]}
        issues = watchdog.assess(forecast, nowcast, runs, now=NOW)
        self.assertTrue(any("nowcast artifact" in x for x in issues))


class NotifyDebounceTests(unittest.TestCase):
    def _notify(self, issues, tmp, now, sent):
        import os
        from unittest import mock

        def fake_urlopen(req, timeout=0):
            sent.append(req.data.decode())
            class R:
                def read(self):
                    return b""
            return R()

        with mock.patch.dict(os.environ,
                             {"WATCHDOG_NTFY_TOPIC": "t"}, clear=False),                 mock.patch.object(watchdog.urllib.request, "urlopen",
                                  fake_urlopen):
            watchdog._notify(issues, tmp, now)

    def test_first_sighting_never_pages_and_counts_do_not_repage(self):
        import os
        import tempfile
        sent = []
        tmp = os.path.join(tempfile.mkdtemp(), "state.json")
        self._notify(["nowcast artifact is 104 minutes old"], tmp, NOW, sent)
        self.assertEqual(sent, [])          # debounce: first sighting
        later = NOW + dt.timedelta(minutes=15)
        self._notify(["nowcast artifact is 106 minutes old"], tmp, later,
                     sent)
        self.assertEqual(len(sent), 1)      # persisted -> one page
        later2 = NOW + dt.timedelta(minutes=30)
        self._notify(["nowcast artifact is 121 minutes old"], tmp, later2,
                     sent)
        self.assertEqual(len(sent), 1)      # same class in cooldown: silent

    def test_new_issue_class_pages_after_its_own_debounce(self):
        import os
        import tempfile
        sent = []
        tmp = os.path.join(tempfile.mkdtemp(), "state.json")
        self._notify(["nowcast artifact is 104 minutes old"], tmp, NOW, sent)
        self._notify(["nowcast artifact is 106 minutes old"], tmp,
                     NOW + dt.timedelta(minutes=15), sent)
        self._notify(["forecast artifact is 200 minutes old"], tmp,
                     NOW + dt.timedelta(minutes=30), sent)
        self.assertEqual(len(sent), 1)      # new class: first sighting
        self._notify(["forecast artifact is 215 minutes old"], tmp,
                     NOW + dt.timedelta(minutes=45), sent)
        self.assertEqual(len(sent), 2)      # persisted -> pages


if __name__ == "__main__":
    unittest.main()
