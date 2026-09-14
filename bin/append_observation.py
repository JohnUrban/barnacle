#!/usr/bin/env python3
"""Safely append one live field observation to the canonical ledger."""
import argparse
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from forecast import flood_forecast_daily as ff  # noqa: E402


FIELDS = [
    "observation_time_local", "landmark_key", "landmark_label",
    "observed_depth_in", "observed_qualitative", "sh_obs_mllw_actual",
    "model_predicted_depth_in", "weather_in_window", "observer", "notes",
]
DEFAULT_PATH = os.path.join(ROOT, "data", "labeled_observations.csv")


def append_observation(row, path=DEFAULT_PATH):
    """Validate the header and append exactly one RFC-compatible CSV row."""
    ff._csv_needs_header(path, FIELDS)
    if not (row.get("observation_time_local") or "").strip():
        raise ValueError("observation_time_local is required")
    ff.parse_station_local_time(row["observation_time_local"])
    if not (row.get("landmark_key") or "").strip():
        raise ValueError("landmark_key is required")
    if not ((row.get("observed_depth_in") or "").strip()
            or (row.get("observed_qualitative") or "").strip()):
        raise ValueError("numeric or qualitative observation is required")
    if (row.get("observed_depth_in") or "").strip():
        float(row["observed_depth_in"])
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(
        buf, fieldnames=FIELDS, extrasaction="raise", lineterminator="\n")
    writer.writerow({field: row.get(field, "") for field in FIELDS})
    encoded = buf.getvalue().encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    for field in FIELDS:
        parser.add_argument("--" + field.replace("_", "-"),
                            required=field in {
                                "observation_time_local", "landmark_key"})
    parser.add_argument("--path", default=DEFAULT_PATH)
    args = parser.parse_args()
    row = {field: getattr(args, field) or "" for field in FIELDS}
    append_observation(row, args.path)
    print(f"appended observation {row['observation_time_local']} "
          f"{row['landmark_key']}")


if __name__ == "__main__":
    main()
