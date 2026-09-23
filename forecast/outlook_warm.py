#!/usr/bin/env python3
"""Warm job for the 7-day outlook's NBM rain percentiles (2026-09-23).

NOAA's NBM probabilistic (qmd) file is published for the 00/06/12/18Z
cycles a few hours after the hourly amount files, and each house-sized
precipitation subset costs ~9 s at NOMADS. 28 of them do not fit the
hourly production job's 5-minute budget, so this script fetches them on
its own schedule (nbm_qmd.yml, every 6 h) into data/outlook_nbm_qmd.json,
which the hourly run merges by valid time (outlook_sources.gather).

  python3 forecast/outlook_warm.py            # fetch + write the file
  python3 forecast/outlook_warm.py --check    # print the file's age/health
"""

import argparse
import datetime as dt
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import outlook_sources as srcs  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
PATH = os.path.join(REPO_ROOT, srcs.NBM_QMD_PATH_DEFAULT)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report the file's health and exit")
    ap.add_argument("--budget", type=float, default=420.0,
                    help="seconds allowed for the subset requests (default 420)")
    ap.add_argument("--path", default=PATH)
    args = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    if args.check:
        health = srcs.merge_nbm_qmd({"buckets": []}, srcs.load_nbm_qmd(args.path), now)
        print(json.dumps(health))
        return 0 if health["status"] != "unavailable" else 1
    existing = srcs.load_nbm_qmd(args.path)
    try:
        data = srcs.fetch_nbm_qmd(now, time_budget_s=args.budget)
    except Exception as e:
        print(f"NBM qmd fetch failed: {e}", flush=True)
        if existing:
            print("keeping the previous file", flush=True)
            return 0
        return 1
    if existing and existing.get("qmd_cycle") == data["qmd_cycle"] \
            and len(existing.get("buckets") or {}) >= len(data["buckets"]):
        print(f"already have {data['qmd_cycle']} with {len(existing['buckets'])} buckets; no change")
        return 0
    os.makedirs(os.path.dirname(args.path), exist_ok=True)
    tmp = args.path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, args.path)
    print(f"wrote {args.path}: {data['summary']}; missing {len(data['missing'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
