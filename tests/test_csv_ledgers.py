import csv
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from forecast import check_artifacts
from forecast import flood_forecast_daily as ff
from bin.append_observation import FIELDS, append_observation


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

    def test_safe_observation_append_quotes_notes_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "observations.csv"
            with path.open("w", newline="") as dest:
                csv.writer(dest).writerows([FIELDS, [
                    "2026-09-14T10:00", "grate_SW", "SW grate", "0",
                    "dry", "", "", "clear", "John", "first"]])
            append_observation({
                "observation_time_local": "2026-09-14T10:06",
                "landmark_key": "curb_SW", "landmark_label": "SW curb",
                "observed_qualitative": "wet edge", "observer": "John",
                "notes": "comma, quote \"and detail\""}, str(path))
            with path.open(newline="") as source:
                rows = list(csv.DictReader(source, strict=True))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["notes"], "first")
        self.assertEqual(rows[1]["notes"], 'comma, quote "and detail"')
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

    def test_labeled_events_gate_rejects_impossible_rows(self):
        fields = check_artifacts.CSV_SCHEMAS["data/labeled_events.csv"]
        row = dict(zip(fields, [
            "not-a-date", "2026-01-01 01:00:00", "-2", "-1", "nan",
            "2027-01-01 00:00:00", "invented", "bad fixture"]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            with path.open("w", newline="") as dest:
                writer = csv.DictWriter(dest, fieldnames=fields)
                writer.writeheader(); writer.writerow(row)
            failures = check_artifacts.validate_csv_semantics(
                str(path), "data/labeled_events.csv")
        self.assertTrue(any("invalid labeled event" in x for x in failures))
        self.assertTrue(any("invalid event label" in x for x in failures))

    def test_accuracy_gate_rejects_nonfinite_and_bad_enums(self):
        fields = check_artifacts.CSV_SCHEMAS["data/forecast_accuracy.csv"]
        row = dict(zip(fields, [
            "2026-09-14", "nan", "bad-time", "bogus", "6.0",
            "bad-time", "nan", "certain"]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accuracy.csv"
            with path.open("w", newline="") as dest:
                writer = csv.DictWriter(dest, fieldnames=fields)
                writer.writeheader(); writer.writerow(row)
            failures = check_artifacts.validate_csv_semantics(
                str(path), "data/forecast_accuracy.csv")
        self.assertTrue(any("invalid accuracy row" in x for x in failures))
        self.assertTrue(any("invalid forecast_regime" in x for x in failures))
        self.assertTrue(any("invalid confidence_level" in x for x in failures))

    def test_nowcast_gate_rejects_schema_negative_rate_and_active_gaps(self):
        payload = {
            "active": True, "generated_utc": "2026-09-14T18:00:00Z",
            "day_local": "2026-09-14", "radar_quality": "ok",
            "source_latest_utc": "2026-09-14T17:59:00Z",
            "source_age_min": 1, "frames_expected": 1,
            "frames_succeeded": 1, "coverage_minutes": 0,
            "projection_assumption": "test",
            "frames": [{"utc": "2026-09-14T17:59:00Z", "in_hr": -1}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nowcast.json"
            path.write_text(json.dumps(payload))
            failures = check_artifacts.validate_nowcast_metadata(str(path))
        self.assertTrue(any("nowcast_schema_version" in x for x in failures))
        self.assertTrue(any("nonnegative" in x for x in failures))
        self.assertTrue(any("peak_proj_in" in x for x in failures))

    def test_alert_gate_rejects_bad_types_channels_and_sms_event(self):
        state = {"rank": "1", "sig": [], "updated": "bad",
                 "last_sent_rank": 9, "last_sent_sig": {},
                 "last_sent_ts": "bad", "last_sent_channels": ["pager"],
                 "sends_today": {}, "sms_event": {"ts": "bad", "class": 7}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps(state))
            failures = check_artifacts.validate_alert_state(str(path))
        self.assertTrue(any("rank must" in x for x in failures))
        self.assertTrue(any("unknown rail" in x for x in failures))
        self.assertTrue(any("sms_event" in x for x in failures))

    def test_surface_gate_requires_same_build_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); docs = root / "docs"; docs.mkdir()
            forecast = {"generated_utc": "2026-09-14T18:00:00Z",
                        "forecast_schema_version": "1.0",
                        "model_version": "v0.10.2", "all_tides": []}
            (docs / "forecast.json").write_text(json.dumps(forecast))
            good = "".join(
                f'<meta name="{key}" content="{value}">' for key, value in (
                    ("barnacle-generated-utc", forecast["generated_utc"]),
                    ("barnacle-schema-version", "1.0"),
                    ("barnacle-model-version", "v0.10.2")))
            (docs / "index.html").write_text(good)
            (docs / "details.html").write_text(good.replace(
                "2026-09-14T18:00:00Z", "stale"))
            failures = check_artifacts.validate_surface_stamps(str(root))
        self.assertTrue(any("details.html" in path for path, _ in failures))


class ErratumConventionTests(unittest.TestCase):
    """Erratum rows (codified 2026-09-02) must reference a timestamp
    that exists EARLIER in the observations ledger — a correction
    that corrects nothing is either a typo or a fabrication."""

    def test_erratum_rows_reference_prior_timestamps(self):
        import csv as _csv
        import re as _re
        path = (Path(__file__).resolve().parent.parent
                / "data" / "labeled_observations.csv")
        seen, problems = set(), []
        with open(path) as f:
            for i, row in enumerate(_csv.DictReader(f), 2):
                label = (row.get("landmark_label") or "").strip()
                # convention enforced from 2026-09-02; the two
                # 2026-08-03 errata predate it (they cite the
                # erroneous value, since corrected) — grandfathered
                if label == "ERRATUM" and (
                        row.get("observation_time_local") or ""
                ) >= "2026-09-02":
                    q = row.get("observed_qualitative") or ""
                    m = _re.search(
                        r"timestamp (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", q)
                    if not m:
                        problems.append(f"line {i}: no timestamp cited")
                    elif m.group(1) not in seen:
                        problems.append(
                            f"line {i}: cites {m.group(1)} which does "
                            f"not appear earlier in the ledger")
                ts = (row.get("observation_time_local") or "")[:16]
                if ts:
                    seen.add(ts)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
