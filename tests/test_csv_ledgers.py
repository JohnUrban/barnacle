import csv
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
