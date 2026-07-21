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


if __name__ == "__main__":
    unittest.main()
