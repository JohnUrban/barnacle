"""Reconstruct production's trailing surge mean AS OF an issuance (v0.10.6
policy, forecast/surge_mean.py): verified hourly_height minus hourly
predictions over [date(t) - 364 d, date(t)] as returned, i.e. up to the
verified-data end, which is not archived for dates before v0.10.6; it is
ASSUMED to be t - LAG_D (24 d, measured once on 2026-09-24). No flag QC
(production applies none). >= 7,200 paired hours required.
The reconstruction is an approximation for pre-v0.10.6 issuances and is
checked against the published v0.10.6 means."""
from __future__ import annotations

import bisect
import datetime as dt
import json
import math
import os

from . import noaa

UTC = dt.timezone.utc
DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "history", "data", "as_issued", "mean_inputs")
LAG_D = 24
WINDOW_D = 364
MIN_HOURS = 24 * 300


def fetch(begin=dt.datetime(2025, 7, 1, tzinfo=UTC), end=dt.datetime(2026, 9, 25, tzinfo=UTC), directory=DIR):
    ents = []
    ents += noaa.fetch_range("hourly_height", begin, end, directory, extra={"datum": "MLLW"}, chunk_days=300)
    ents += noaa.fetch_range("predictions", begin, end, directory, extra={"datum": "MLLW", "interval": "h"}, chunk_days=300)
    with open(os.path.join(directory, "manifest.json"), "w") as f:
        json.dump({"purpose": "verified hourly heights and hourly predictions for the as-of mean", "responses": ents}, f, indent=1)


class MeanSeries:
    def __init__(self, directory=DIR):
        bodies = noaa.load_bodies(os.path.join(directory, "manifest.json"))
        obs, prd = {}, {}
        for e, body in bodies:
            js = json.loads(body)
            if e["product"] == "hourly_height":
                for r in js.get("data") or []:
                    try:
                        v = float(r["v"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if math.isfinite(v):
                        obs[noaa._t(r["t"])] = v
            else:
                for r in js.get("predictions") or []:
                    prd[noaa._t(r["t"])] = float(r["v"])
        self.times = sorted(t for t in obs if t in prd)
        self.cum = [0.0]
        for t in self.times:
            self.cum.append(self.cum[-1] + obs[t] - prd[t])
        self.verified_end = self.times[-1] if self.times else None

    def as_of(self, t, lag_d=LAG_D, verified_end=None):
        """(mean, n_hours, window_start, window_end) or (None, n, ...)."""
        start = dt.datetime.combine((t - dt.timedelta(days=WINDOW_D)).date(), dt.time(0), tzinfo=UTC)
        day_end = dt.datetime.combine(t.date(), dt.time(23), tzinfo=UTC)
        end = min(day_end, verified_end or (t - dt.timedelta(days=lag_d)))
        i = bisect.bisect_left(self.times, start)
        j = bisect.bisect_right(self.times, end)
        n = j - i
        if n < MIN_HOURS:
            return None, n, start, end
        return (self.cum[j] - self.cum[i]) / n, n, start, end
