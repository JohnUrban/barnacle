"""Replay-archive provenance repairs (as-issued validation, 2026-09-24):
QPF source metadata, advisory issuance field, no generation-time substitution
for the NWPS retrieval. None of these may change a forecast value."""
import datetime as dt
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from forecast import flood_forecast_daily as ff
from forecast import replay_archive as ra

GRID = {"properties": {"updateTime": "2026-09-24T15:02:11+00:00", "quantitativePrecipitation": {
    "uom": "wmoUnit:mm", "values": [{"validTime": "2026-09-24T12:00:00+00:00/PT6H", "value": 3.0},
                                     {"validTime": "2026-09-24T18:00:00+00:00/PT1H", "value": None}]}}}


def _fake_get(url, *a, **k):
    if "points" in url:
        return {"properties": {"forecastGridData": "https://grid"}}
    return GRID


class QpfProvenanceTests(unittest.TestCase):
    def test_rates_unchanged_and_provenance_captured(self):
        with patch.object(ff, "_get", side_effect=_fake_get):
            rates = ff.fetch_nws_qpf()
        t0 = dt.datetime(2026, 9, 24, 12, tzinfo=dt.timezone.utc)
        expect = [(t0 + dt.timedelta(hours=i), (3.0 / 25.4) / 6) for i in range(6)] + [(t0 + dt.timedelta(hours=6), 0.0)]
        self.assertEqual(rates, expect)
        m = ff._LAST_REPLAY_INPUTS["qpf_meta"]
        self.assertEqual((m["status"], m["grid_update_time"], m["uom"]), ("ok", "2026-09-24T15:02:11+00:00", "wmoUnit:mm"))
        self.assertEqual(m["intervals"], [["2026-09-24T12:00:00+00:00/PT6H", 3.0], ["2026-09-24T18:00:00+00:00/PT1H", None]])

    def test_capture_status_is_not_usability(self):
        """a4: qpf_source.status reports provenance CAPTURE; an empty grid is captured
        ('ok') while the forecast has no usable QPF (fetch returns None)."""
        empty = {"properties": {"updateTime": "t", "quantitativePrecipitation": {"uom": "wmoUnit:mm", "values": []}}}
        with patch.object(ff, "_get", side_effect=lambda url, *a, **k: {"properties": {"forecastGridData": "g"}} if "points" in url else empty):
            self.assertIsNone(ff.fetch_nws_qpf())
        m = ff._LAST_REPLAY_INPUTS["qpf_meta"]
        self.assertEqual((m["status"], m["intervals"]), ("ok", []))
        r = ra.build_record({"generated_utc": "2026-09-24T16:14:12Z", "water_series": [], "all_tides": [],
                             "input_health": {"nws_qpf": {"status": "unavailable", "detail": "no usable buckets"}}},
                            qpf_hourly=None, qpf_meta=m)
        self.assertIsNone(r["qpf_hourly"]); self.assertIn("qpf_hourly", r["unavailable"])
        self.assertEqual(r["qpf_source"]["status"], "ok")

    def test_failed_fetch_records_unavailable(self):
        with patch.object(ff, "_get", side_effect=OSError("down")):
            self.assertIsNone(ff.fetch_nws_qpf())
        self.assertEqual(ff._LAST_REPLAY_INPUTS["qpf_meta"]["status"], "unavailable")


class RecordProvenanceTests(unittest.TestCase):
    def _forecast(self, status):
        return {"generated_utc": "2026-09-24T16:14:12Z", "model_version": "v0.10.6", "nws_status": status,
                "water_series": [], "all_tides": []}

    def test_advisory_issuance_field(self):
        r = ra.build_record(self._forecast("NWS event active: 6 Sandy Hook rows from CFW KPHI issued 2026-09-24T09:36:00+00:00"))
        self.assertEqual((r["advisory"]["issued_utc"], r["advisory"]["issued_reason"]), ("2026-09-24T09:36Z", None))
        r = ra.build_record(self._forecast("no active coastal flood product"))
        self.assertIsNone(r["advisory"]["issued_utc"]); self.assertIn("no advisory issuance", r["advisory"]["issued_reason"])

    def test_nwps_retrieval_is_never_the_generation_time(self):
        od = {"nwps": {"issued": "2026-09-24T09:10:00Z", "series": [{"utc": "2026-09-24T17:00:00Z", "ft": 6.1}]}}
        r = ra.build_record(self._forecast(""), od, {"nwps": {}})
        self.assertIsNone(r["nwps"]["retrieved"]); self.assertIn("unavailable", r["nwps"]["retrieved_basis"])
        r = ra.build_record(self._forecast(""), od, {"nwps": {"fetched_at": "2026-09-24T16:14:12Z"}})
        self.assertEqual(r["nwps"]["retrieved"], "2026-09-24T16:14:12Z"); self.assertIn("run time", r["nwps"]["retrieved_basis"])

    def test_qpf_source_in_record_and_schema_1_rows_stay_valid(self):
        r = ra.build_record(self._forecast(""), qpf_meta={"status": "ok", "grid_update_time": "x"})
        self.assertEqual(r["qpf_source"]["grid_update_time"], "x"); self.assertEqual(r["v"], 2)
        self.assertEqual(ra.build_record(self._forecast(""))["qpf_source"]["reason"], "not captured")
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "2026-09.jsonl"), "w") as f:
            old = dict(r, v=1); old.pop("qpf_source")
            f.write(json.dumps(old) + "\n" + json.dumps(r) + "\n")
        self.assertEqual(ra.validate_file(os.path.join(d, "2026-09.jsonl")), [])


if __name__ == "__main__":
    unittest.main()
