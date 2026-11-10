"""The 2026-11-10 in-place correction of data/forecast_accuracy.csv.

Owner decision: the accuracy ledger is a derived score, so rows scored
before the tide peaked are corrected in place. These tests pin what the
correction may and may not touch.
"""
import csv
import datetime as dt
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "rescore_forecast_accuracy",
    ROOT / "history" / "scripts" / "rescore_forecast_accuracy.py")
rescore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rescore)

HEADER = ("forecast_run_date,forecast_peak_predicted_mllw,"
          "forecast_peak_predicted_time,forecast_regime,"
          "actual_peak_observed_mllw,actual_peak_observed_time,"
          "mllw_error_ft,confidence_level\n")
# legacy naive row scored correctly; multi-day row scored on the rising
# limb; row whose reading NOAA later revised
ROW_OK = "2026-05-19,5.927,2026-05-19 12:56,dry,5.488,2026-05-19 12:36,0.43899999999999917,low\n"
ROW_EARLY = "2026-10-09,6.414017,2026-10-11 08:46-04:00,street,5.18,2026-10-11 07:00-04:00,1.2340169999999997,\n"
ROW_REVISED = "2026-09-26,8.5,2026-09-26 08:01-04:00,severe,8.667,2026-09-26 08:36-04:00,-0.16699999999999982,\n"


def _t(text):
    return rescore.ff.parse_station_local_time(text)


FETCH = {
    "2026-05-19 12:56": (5.488, "2026-05-19 12:36-04:00",
                         [(_t("2026-05-19 12:36-04:00"), 5.488)]),
    "2026-10-11 08:46-04:00": (6.482, "2026-10-11 09:06-04:00",
                               [(_t("2026-10-11 07:00-04:00"), 5.18),
                                (_t("2026-10-11 09:06-04:00"), 6.482)]),
    "2026-09-26 08:01-04:00": (8.805, "2026-09-26 08:36-04:00",
                               [(_t("2026-09-26 08:36-04:00"), 8.805)]),
}


class RescoreTests(unittest.TestCase):
    def _run(self, argv, fetch=None, ledger_text=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.ledger = base / "forecast_accuracy.csv"
        self.ledger.write_text(
            ledger_text or HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)
        self.history = base / "history"
        fetch = fetch or (lambda pred_time, retries=6: FETCH[pred_time])
        with mock.patch.object(rescore, "LEDGER", str(self.ledger)), \
                mock.patch.object(rescore, "HISTORY", str(self.history)), \
                mock.patch.object(rescore, "fetch_window", fetch), \
                mock.patch.object(rescore.time, "sleep"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            return rescore.main(argv)

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self._run([]), 0)
        self.assertEqual(self.ledger.read_text(),
                         HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)
        self.assertFalse(self.history.exists())

    def test_apply_corrects_only_the_observed_half(self):
        self.assertEqual(self._run(["--apply", "--tag", "t"]), 0)
        lines = self.ledger.read_text().splitlines(keepends=True)
        self.assertEqual(lines[0], HEADER)
        self.assertEqual(lines[1], ROW_OK)          # byte-identical
        before = list(csv.DictReader(
            io.StringIO(HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)))
        after = list(csv.DictReader(io.StringIO(self.ledger.read_text())))
        for old, new in zip(before, after):
            for field in ("forecast_run_date", "forecast_peak_predicted_mllw",
                          "forecast_peak_predicted_time", "forecast_regime",
                          "confidence_level"):
                self.assertEqual(old[field], new[field])   # as issued
        self.assertEqual(after[1]["actual_peak_observed_mllw"], "6.482")
        self.assertEqual(after[1]["actual_peak_observed_time"],
                         "2026-10-11 09:06-04:00")
        self.assertAlmostEqual(float(after[1]["mllw_error_ft"]),
                               6.414017 - 6.482)
        self.assertEqual(after[2]["actual_peak_observed_mllw"], "8.805")
        self.assertEqual(rescore.check_artifacts.validate_csv_semantics(
            str(self.ledger), "data/forecast_accuracy.csv"), [])

    def test_apply_keeps_the_as_recorded_file_and_itemises_reasons(self):
        self._run(["--apply", "--tag", "t"])
        snapshot = self.history / "data" / "forecast_accuracy_as_recorded_t.csv"
        self.assertEqual(snapshot.read_text(),
                         HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)
        report = list(csv.DictReader(io.StringIO(
            (self.history / "reports" /
             "t-forecast-accuracy-rescore.csv").read_text())))
        by_date = {r["forecast_run_date"]: r for r in report}
        self.assertEqual(by_date["2026-05-19"]["outcome"], "unchanged")
        self.assertEqual(by_date["2026-10-09"]["reason"], "scored-early")
        self.assertEqual(by_date["2026-10-09"]["recorded_observed_mllw"], "5.18")
        self.assertEqual(by_date["2026-10-09"]["change_ft"], "+1.302")
        self.assertEqual(by_date["2026-09-26"]["reason"], "noaa-revised")
        self.assertTrue(by_date["2026-09-26"]["noaa_retrieved_utc"])

    def test_second_apply_changes_nothing(self):
        self._run(["--apply", "--tag", "t"])
        corrected = self.ledger.read_text()

        def fetch(pred_time, retries=6):
            peak, when, raw = FETCH[pred_time]
            return peak, when, raw
        with mock.patch.object(rescore, "LEDGER", str(self.ledger)), \
                mock.patch.object(rescore, "HISTORY", str(self.history)), \
                mock.patch.object(rescore, "fetch_window", fetch), \
                mock.patch.object(rescore.time, "sleep"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(rescore.main(["--apply", "--tag", "u"]), 0)
        self.assertEqual(self.ledger.read_text(), corrected)
        self.assertFalse((self.history / "data" /
                          "forecast_accuracy_as_recorded_u.csv").exists())

    def test_one_unfetchable_row_aborts_everything(self):
        def fetch(pred_time, retries=6):
            if pred_time.startswith("2026-09-26"):
                return None, None, []
            return FETCH[pred_time]
        self.assertEqual(self._run(["--apply", "--tag", "t"], fetch=fetch), 3)
        self.assertEqual(self.ledger.read_text(),
                         HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)
        self.assertFalse(self.history.exists())

    def test_a_row_whose_window_is_still_open_is_left_alone(self):
        future = (dt.datetime.now(dt.timezone.utc)
                  + dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        row = f"2026-11-09,5.9,{future},dry,4.805,{future},1.0950000000000006,\n"

        def fetch(pred_time, retries=6):
            self.assertNotEqual(pred_time, future)   # never asked
            return FETCH[pred_time]
        self.assertEqual(self._run(
            ["--apply", "--tag", "t"], fetch=fetch,
            ledger_text=HEADER + ROW_OK + ROW_EARLY + row), 0)
        self.assertEqual(self.ledger.read_text().splitlines()[-1],
                         row.rstrip("\n"))

    def test_existing_snapshot_is_never_overwritten(self):
        self._run(["--apply", "--tag", "t"])
        snapshot = self.history / "data" / "forecast_accuracy_as_recorded_t.csv"
        snapshot.write_text("sentinel")
        self.ledger.write_text(HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)
        with mock.patch.object(rescore, "LEDGER", str(self.ledger)), \
                mock.patch.object(rescore, "HISTORY", str(self.history)), \
                mock.patch.object(rescore, "fetch_window",
                                  lambda pred_time, retries=6: FETCH[pred_time]), \
                mock.patch.object(rescore.time, "sleep"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(rescore.main(["--apply", "--tag", "t"]), 4)
        self.assertEqual(snapshot.read_text(), "sentinel")
        self.assertEqual(self.ledger.read_text(),
                         HEADER + ROW_OK + ROW_EARLY + ROW_REVISED)


if __name__ == "__main__":
    unittest.main()
