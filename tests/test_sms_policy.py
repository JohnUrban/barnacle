"""SMS imminent-impact policy (user directive 2026-09-13).

The gate must fire on fresh actual/projected street impact regardless
of base-alert signature dedup, text once per event, re-arm after
SMS_REARM_HOURS or on class escalation, never emit a multi-segment
body, and never be blocked by quiet hours or the daily cap. Born from
the 2026-09-13 morning: two duplicate watch texts at 7:46/7:56, then
the 10:00 compound street crossing that never texted at all.
"""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import flood_forecast_daily as ff
from forecast import nowcast

UTC = dt.timezone.utc
NOON = dt.datetime(2026, 9, 13, 16, 0, tzinfo=UTC)   # 12:00 EDT


def _nc(street=None, proj=None, bay=None, age=5.0):
    source = (NOON - dt.timedelta(minutes=age)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    return {"nowcast_schema_version": ff.NOWCAST_SCHEMA_VERSION,
            "active": True, "radar_quality": "ok", "trend": "rising",
            "source_latest_utc": source,
            ff.NOWCAST_STREET_NOW_KEY: street,
            ff.NOWCAST_PEAK_PROJ_KEY: proj, "bay_navd88": bay}


class SmsGateTests(unittest.TestCase):
    def test_fires_on_actual_street_over_curb(self):
        g = ff.evaluate_sms_gate({}, state={}, now_utc=NOON,
                                 nowcast=_nc(street=11.2, bay=3.95))
        self.assertTrue(g["send"])
        self.assertEqual(g["class"], 1)

    def test_fires_on_projection_alone(self):
        g = ff.evaluate_sms_gate({}, state={}, now_utc=NOON,
                                 nowcast=_nc(street=2.0, proj=14.3))
        self.assertTrue(g["send"])
        self.assertEqual(g["class"], 2)

    def test_stale_nowcast_is_no_basis(self):
        g = ff.evaluate_sms_gate({}, state={}, now_utc=NOON,
                                 nowcast=_nc(street=11.2, age=45))
        self.assertFalse(g["send"])
        self.assertIn("outside", g["reason"])

    def test_below_curb_stays_quiet(self):
        g = ff.evaluate_sms_gate({}, state={}, now_utc=NOON,
                                 nowcast=_nc(street=5.0, proj=6.0))
        self.assertFalse(g["send"])

    def test_falling_projection_is_not_alertable(self):
        nc = _nc(street=2.0, proj=22.0)
        nc["trend"] = "falling"
        g = ff.evaluate_sms_gate({}, state={}, now_utc=NOON, nowcast=nc)
        self.assertFalse(g["send"])

    def test_actual_writer_payload_round_trips_to_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nowcast.json"
            heartbeat = Path(tmp) / "heartbeats.csv"
            payload = _nc(street=11.2, proj=14.3, bay=3.95)
            with mock.patch.object(nowcast, "OUT_PATH", str(path)), \
                    mock.patch.object(nowcast, "HEARTBEAT_PATH",
                                      str(heartbeat)), \
                    mock.patch.object(nowcast, "_origin_day_max",
                                      return_value=(0, None)):
                nowcast._write(payload, now_utc=NOON)
            snapshot = ff._nowcast_snapshot(str(path), now_utc=NOON)
            gate = ff.evaluate_sms_gate(
                {}, state={}, now_utc=NOON, nowcast=snapshot)
        self.assertTrue(gate["send"])
        self.assertEqual(gate["class"], 2)

    def test_once_per_event_suppression(self):
        st = {"sms_event": {"ts": "2026-09-13T14:00:00Z", "class": 1}}
        g = ff.evaluate_sms_gate({}, state=st, now_utc=NOON,
                                 nowcast=_nc(street=9.0))
        self.assertFalse(g["send"])
        self.assertIn("re-arms", g["reason"])

    def test_class_escalation_refires_immediately(self):
        st = {"sms_event": {"ts": "2026-09-13T14:00:00Z", "class": 1}}
        g = ff.evaluate_sms_gate({}, state=st, now_utc=NOON,
                                 nowcast=_nc(street=14.0))
        self.assertTrue(g["send"])
        self.assertIn("escalation", g["reason"])

    def test_rearms_after_quiet_window(self):
        old = (NOON - dt.timedelta(hours=ff.SMS_REARM_HOURS,
                                   minutes=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        st = {"sms_event": {"ts": old, "class": 2}}
        g = ff.evaluate_sms_gate({}, state=st, now_utc=NOON,
                                 nowcast=_nc(street=9.0))
        self.assertTrue(g["send"])

    def test_imminent_body_single_segment_present_tense(self):
        g = ff.evaluate_sms_gate({}, state={}, now_utc=NOON,
                                 nowcast=_nc(street=11.2, proj=14.0,
                                             bay=3.95))
        body = ff.build_sms_imminent(g)
        self.assertLessEqual(len(body), 160)
        self.assertIn("NOW", body.upper())
        self.assertIn("bay over grates", body)
        self.assertNotIn("72H", body)


class SmsPersistTests(unittest.TestCase):
    def _decision(self, state):
        return {"send": False, "reason": "steady", "rank": 3,
                "label": "x", "sig": "pluv|X@1", "now_utc": NOON,
                "previous": state}

    def test_sms_only_delivery_counts_but_keeps_sig_dedup(self):
        import os
        st = {"last_sent_sig": "pluv|X@1", "last_sent_ts":
              "2026-09-13T11:56:34Z", "last_sent_rank": 3,
              "sends_today": {"date": "2026-09-13", "count": 1}}
        gate = {"class": 1}
        path = os.path.join(tempfile.mkdtemp(), "alert_state.json")
        new = ff.persist_alert_state(self._decision(st), [], path=path,
                                     sms_gate=gate, sms_delivered=True)
        self.assertEqual(new["sends_today"]["count"], 2)
        self.assertEqual(new["base_sends_today"]["count"], 1)
        self.assertEqual(new["sms_sends_today"]["count"], 1)
        self.assertEqual(new["last_sent_ts"], "2026-09-13T11:56:34Z")
        self.assertEqual(new["sms_event"]["class"], 1)
        self.assertEqual(new["imminent_channels"]["sms"]["class"], 1)
        with open(path) as saved:
            self.assertEqual(json.load(saved)["sms_event"]["class"], 1)

    def test_sms_event_carried_through_steady_persists(self):
        import tempfile, os
        st = {"sms_event": {"ts": "2026-09-13T14:00:00Z", "class": 2}}
        path = os.path.join(tempfile.mkdtemp(), "alert_state.json")
        new = ff.persist_alert_state(self._decision(st), [], path=path)
        self.assertEqual(new["sms_event"]["class"], 2)

    def test_ntfy_and_sms_acknowledge_independently(self):
        import os
        path = os.path.join(tempfile.mkdtemp(), "alert_state.json")
        gate = {"class": 2}
        first = ff.persist_alert_state(
            self._decision({}), [], path=path, sms_gate=gate,
            imminent_delivered_channels=["ntfy"])
        sms = ff.evaluate_sms_gate(
            {}, state=first, now_utc=NOON,
            nowcast=_nc(street=14.0), channel="sms")
        ntfy = ff.evaluate_sms_gate(
            {}, state=first, now_utc=NOON,
            nowcast=_nc(street=14.0), channel="ntfy")
        self.assertTrue(sms["send"])
        self.assertFalse(ntfy["send"])


class ChannelSelectionTests(unittest.TestCase):
    def test_channels_param_excludes_rails(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": "t",
                                          "ALERT_SMS_TO": "x@y"},
                             clear=False):
            r = ff.deliver_alert({}, "s", "t", None,
                                 channels={"email"})
            self.assertNotIn("ntfy", r["attempted"])
            self.assertNotIn("sms", r["attempted"])


if __name__ == "__main__":
    unittest.main()
