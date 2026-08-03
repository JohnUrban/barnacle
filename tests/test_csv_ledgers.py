import csv
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import check_artifacts
from forecast import flood_forecast_daily as ff


class CsvLedgerTests(unittest.TestCase):
    def test_canonical_ledgers_have_exact_schema_and_width(self):
        for relpath, fields in check_artifacts.CSV_SCHEMAS.items():
            with self.subTest(ledger=relpath):
                failures = check_artifacts.validate_csv_ledger(
                    str(Path(check_artifacts.ROOT) / relpath), fields
                )
                self.assertEqual(failures, [])

    def test_shape_gate_reports_extra_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.csv"
            path.write_text("a,b\n1,2,3\n", encoding="utf-8")
            failures = check_artifacts.validate_csv_ledger(
                str(path), ["a", "b"]
            )
        self.assertEqual(len(failures), 1)
        self.assertIn("3 fields; expected 2", failures[0])

    def test_shape_gate_uses_strict_quote_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.csv"
            path.write_text('a,b\n1,"unterminated\n2,ok\n', encoding="utf-8")
            failures = check_artifacts.validate_csv_ledger(
                str(path), ["a", "b"]
            )
        self.assertTrue(any("strict CSV parse" in item for item in failures))

    def test_append_writer_rejects_stale_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([
                    ["old", "header"],
                    ["value", "value"],
                ])
            with self.assertRaisesRegex(ValueError, "CSV header mismatch"):
                ff._csv_needs_header(str(path), ["new", "header", "field"])

    def test_missing_or_empty_ledger_needs_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.csv"
            self.assertTrue(ff._csv_needs_header(str(path), ["a"]))
            path.touch()
            self.assertTrue(ff._csv_needs_header(str(path), ["a"]))

    def test_tide_cache_is_multiline_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tides.json"
            now = dt.datetime(2026, 7, 21, 12, 0, tzinfo=ff.STATION_TZ)
            with mock.patch.object(ff, "_tide_cache_path", return_value=str(path)), \
                 mock.patch.object(ff, "_station_local_now", return_value=now):
                ff._tide_cache_save("series", [["2026-07-21 12:00", 4.2]])

            raw = path.read_bytes()
            self.assertNotIn(b"\r\n", raw)
            self.assertGreater(raw.count(b"\n"), 3)
            self.assertEqual(
                json.loads(raw)["series"], [["2026-07-21 12:00", 4.2]]
            )

    def test_semantic_gate_rejects_future_observation(self):
        fields = check_artifacts.CSV_SCHEMAS["data/labeled_observations.csv"]
        now = dt.datetime(2026, 8, 3, 14, 0, tzinfo=dt.timezone.utc)
        row = {
            "observation_time_local": "2026-08-03T22:26",
            "landmark_key": "curb",
            "landmark_label": "Curb",
            "observed_qualitative": "wet",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "observations.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerow(row)
            failures = check_artifacts.validate_csv_semantics(
                str(path), "data/labeled_observations.csv", now
            )
        self.assertTrue(any("future" in failure for failure in failures))

    def test_nowcast_gate_rejects_write_time_that_masks_stale_source(self):
        payload = {
            "active": True,
            "generated_utc": "2026-08-03T15:30:00Z",
            "day_local": "2026-08-03",
            "radar_quality": "ok",
            "source_latest_utc": "2026-08-03T15:00:00Z",
            "source_age_min": 30,
            "frames_expected": 1,
            "frames_succeeded": 1,
            "coverage_minutes": 0,
            "projection_assumption": "test",
            "frames": [{"utc": "2026-08-03T15:00:00Z", "in_hr": 1.0}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nowcast.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            failures = check_artifacts.validate_nowcast_metadata(str(path))
        self.assertTrue(any("older than 10" in failure for failure in failures))

    def test_alert_state_gate_requires_transaction_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alert_state.json"
            path.write_text(json.dumps({"rank": 1}), encoding="utf-8")
            failures = check_artifacts.validate_alert_state(str(path))
        self.assertTrue(any("last_sent_sig" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
