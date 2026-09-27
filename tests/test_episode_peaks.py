"""Audit 2026-09-27-a1 R3: the all-pathways chart keeps one measured peak
per registered flood EPISODE (registry rows matched by content hash), so a
second flood on the same date is not hidden behind the day's maximum;
unregistered rows still collapse per day and say so."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from forecast import flood_forecast_daily as ff

FIELDS = ["observation_time_local", "landmark_key", "landmark_label",
          "observed_depth_in", "observed_qualitative", "sh_obs_mllw_actual",
          "model_predicted_depth_in", "weather_in_window", "observer", "notes"]


def _row(t, key, depth):
    r = dict.fromkeys(FIELDS, "")
    r.update(observation_time_local=t, landmark_key=key,
             observed_depth_in=depth, observer="john")
    return r


class EpisodePeakTests(unittest.TestCase):
    def _run(self, rows, episodes):
        with tempfile.TemporaryDirectory() as tmp:
            obs = Path(tmp) / "obs.csv"
            with open(obs, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
            with open(obs, newline="") as f:
                parsed = list(csv.DictReader(f))
            reg = Path(tmp) / "episodes.json"
            reg.write_text(json.dumps({"episodes": [
                {"episode_id": eid, "ledger_rows": [
                    {"csv_row": i + 2, "sha256": ff._observation_row_hash(parsed[i])}
                    for i in idx]} for eid, idx in episodes.items()]}))
            return ff._measured_flood_peaks(obs_path=str(obs),
                                            registry_path=str(reg))

    def test_two_episodes_on_one_date_both_survive(self):
        rows = [_row("2026-09-26T09:06", "porch_step_base", "12.25"),
                _row("2026-09-26T22:11", "curb", "0.75"),
                _row("2026-09-27T09:44", "porch_step_base", "11.25")]
        peaks = self._run(rows, {"2026-09-26-e01": [0], "2026-09-26-e02": [1],
                                 "2026-09-27-e01": [2]})
        self.assertEqual([p["episode_id"] for p in peaks],
                         ["2026-09-26-e01", "2026-09-26-e02", "2026-09-27-e01"])
        self.assertEqual([p["grouping"] for p in peaks], ["episode"] * 3)
        self.assertAlmostEqual(peaks[0]["navd88"], 5.701, places=3)
        self.assertAlmostEqual(peaks[1]["navd88"], 4.223, places=3)
        self.assertEqual(peaks[1]["time"], "2026-09-26 22:11")

    def test_unregistered_rows_collapse_per_day_and_say_so(self):
        rows = [_row("2026-09-26T09:06", "porch_step_base", "12.25"),
                _row("2026-09-26T22:11", "curb", "0.75")]
        peaks = self._run(rows, {})
        self.assertEqual(len(peaks), 1)
        self.assertEqual(peaks[0]["grouping"], "day")
        self.assertIsNone(peaks[0]["episode_id"])

    def test_negative_and_pocket_rows_never_mark(self):
        rows = [_row("2026-09-25T20:06", "grate_SW", ""),
                _row("2026-05-31T20:00", "grate_SW", "0"),
                _row("2026-05-31T20:10", "grate_SW", "-2.0"),
                _row("2026-05-19T08:00", "pocket_nw", "2.0")]
        self.assertEqual(self._run(rows, {"2026-09-25-e01": [0]}), [])

    def test_offset_bearing_times_group_by_station_date(self):
        rows = [_row("2026-09-26T22:11:00-04:00", "curb", "0.75")]
        peaks = self._run(rows, {})
        self.assertEqual(peaks[0]["time"], "2026-09-26 22:11")

    def test_live_registry_keeps_sep26_evening_flood(self):
        peaks = ff._measured_flood_peaks()
        ids = {p["episode_id"] for p in peaks}
        self.assertIn("2026-09-26-e01", ids)
        self.assertIn("2026-09-26-e02", ids)
        e02 = next(p for p in peaks if p["episode_id"] == "2026-09-26-e02")
        self.assertLess(e02["navd88"], 4.4)


if __name__ == "__main__":
    unittest.main()
