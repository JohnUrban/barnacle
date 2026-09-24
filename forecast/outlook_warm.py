#!/usr/bin/env python3
"""Warm job for the 7-day outlook's expensive sources (audit 2026-09-23-a1 R1).

The hourly production job must never wait on NOMADS: NBM amounts (up to 44
subsets to reach now+168 h), NBM percentiles (~9 s each, synoptic cycles
only, published 3+ h late), P-ETSS text and WPC GRIBs are fetched here, on
this job's own budget, into data/outlook_guidance.json. The hourly run
admits each source by its cycle age (outlook_sources.admit_guidance).

  python3 forecast/outlook_warm.py            # refresh the file
  python3 forecast/outlook_warm.py --check    # print each source's health
"""

import argparse
import datetime as dt
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import outlook_sources as srcs  # noqa: E402
import surge_mean  # noqa: E402

PATH = srcs.GUIDANCE_PATH_DEFAULT


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report each source's health and exit")
    ap.add_argument("--budget", type=float, default=480.0,
                    help="seconds allowed for the NBM percentile subsets (default 480)")
    ap.add_argument("--path", default=PATH)
    args = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    existing = srcs.load_guidance(args.path)
    if args.check:
        worst = 0
        for key in ("nbm", "petss", "wpc"):
            _d, h = srcs.admit_guidance(existing, key, now)
            print(f"{key:8s} {h['status']:11s} {h['detail']}")
            worst = max(worst, {"ok": 0, "degraded": 1, "unavailable": 2}[h["status"]])
        h = srcs.merge_nbm_qmd({"buckets": []}, existing.get("nbm_qmd"), now)
        print(f"{'nbm_qmd':8s} {h['status']:11s} {h['detail']}")
        return 0 if worst < 2 else 1
    # v0.10.6: trailing 365-d mean surge for the surge decay (production
    # input; the hourly run age-gates it and has a documented fallback)
    rec, note = surge_mean.refresh(now)
    print(f"surge_mean {note}: {rec.get('mean_ft') if rec else 'none'}", flush=True)
    data = srcs.fetch_guidance(now, existing, qmd_budget_s=args.budget)
    srcs.save_guidance(args.path, data)
    for key in ("nbm", "nbm_qmd", "petss", "wpc"):
        d = data.get(key) or {}
        print(f"{key:8s} {d.get('summary', 'MISSING')}"
              + (f"  [{data['errors'][key]}]" if key in data["errors"] else ""), flush=True)
    print(f"wrote {args.path}")
    return 0 if any(data.get(k) for k in ("nbm", "nbm_qmd", "petss", "wpc")) else 1


if __name__ == "__main__":
    sys.exit(main())
