"""Surge decay toward the recent average (model v0.10.6 CANDIDATE).

Every forecast of a future hour guesses that hour's surge (observed minus
astronomical) from the latest reading. v0.10.5 held the reading constant;
twenty years of Sandy Hook data say a reading that decays toward the recent
average surge is more accurate at every lead, most in storms
(history/plans/2026-09-23-surge-decay-plan.md,
history/reports/2026-09-23-surge-decay-views.txt):

    surge(t) = mean + (s_obs - mean) * exp(-(t - t_obs) / TAU)

The decay runs from the READING's time, not the run's, so a fresh reading
and a silent gauge are the same formula (owner decisions 2026-09-23,
BACKLOG missing-surge-ladder, missing-surge-ladder-decay, fresh-surge-decay).

Ladder (the newest valid reading wins):
  fresh           reading <= SURGE_FRESH_MAX_AGE_MIN old
  stale-download  older reading still inside the 6-h observation download
  stale-state     last good reading saved by an earlier run (data/surge_state.json)
  typical-offset  no usable reading, or its decayed departure is negligible or
                  older than SURGE_SNAP_MAX_AGE_H: surge = mean exactly,
                  labeled "surge unavailable, using the typical offset"

Pure module: no network, no file I/O; callers supply readings and the mean.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import math

SURGE_DECAY_TAU_H = 36.0            # measured: best or near-best in all three views, both decades
SURGE_FRESH_MAX_AGE_MIN = 60        # unchanged v0.10.5 freshness limit
SURGE_SNAP_DEPARTURE_FT = 0.05      # decayed departure below this: indistinguishable from the mean
SURGE_SNAP_MAX_AGE_H = 168.0        # a reading older than a week is never used
# Fallback when the warm job's trailing-365-d mean is unavailable or too old:
# trailing 365-d mean of observed surge at Sandy Hook ending 2026-09-22
# (history/scripts/pull_surge_forecast_test_data.py output), rounded.
SURGE_MEAN_FALLBACK_FT = 0.54
SURGE_MEAN_FALLBACK_NOTE = "trailing 365-d mean to 2026-09-22, +0.541 ft"
SURGE_MEAN_OK_AGE_H = 7 * 24.0      # a 364-day mean barely moves in a week: ok up to 7 d
SURGE_MEAN_MAX_AGE_D = 45.0         # older than this: fall back to the constant

RUNGS = ("fresh", "stale-download", "stale-state", "typical-offset")


@dataclasses.dataclass(frozen=True)
class SurgeAnchor:
    """What every future hour's surge is computed from."""
    rung: str
    mean_ft: float
    mean_source: str
    surge_ft: float | None = None           # the reading (None for typical-offset)
    obs_utc: dt.datetime | None = None      # the reading's time (aware UTC)
    tau_h: float = SURGE_DECAY_TAU_H

    def at(self, when_utc: dt.datetime) -> float:
        """Surge (ft) expected at `when_utc`. Hours before the reading keep the
        reading itself (the lookback part of the curve)."""
        if self.surge_ft is None or self.obs_utc is None:
            return self.mean_ft
        age_h = (when_utc - self.obs_utc).total_seconds() / 3600.0
        if age_h <= 0:
            return self.surge_ft
        return self.mean_ft + (self.surge_ft - self.mean_ft) * math.exp(-age_h / self.tau_h)

    def age_h(self, now_utc: dt.datetime) -> float | None:
        if self.obs_utc is None:
            return None
        return (now_utc - self.obs_utc).total_seconds() / 3600.0

    def label(self, now_utc: dt.datetime) -> str:
        if self.rung == "typical-offset":
            return (f"surge unavailable, using the typical offset "
                    f"({self.mean_ft:+.2f} ft, {self.mean_source})")
        age = self.age_h(now_utc) or 0.0
        when = ("just now" if age < 1.0 else f"{age:.0f} h ago")
        return (f"surge {self.surge_ft:+.2f} ft from a reading {when}, decaying toward "
                f"the typical offset {self.mean_ft:+.2f} ft (time constant {self.tau_h:.0f} h)")

    def as_json(self, now_utc: dt.datetime) -> dict:
        age = self.age_h(now_utc)
        return {"rung": self.rung, "surge_obs_ft": _r(self.surge_ft, 4),
                "observation_utc": (self.obs_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if self.obs_utc else None),
                "age_h": _r(age, 2), "mean_ft": _r(self.mean_ft, 4), "mean_source": self.mean_source,
                "tau_h": self.tau_h, "surge_now_ft": _r(self.at(now_utc), 4),
                "label": self.label(now_utc)}


def _r(v, n):
    return None if v is None else round(float(v), n)


def _valid(reading):
    """reading = (surge_ft, obs_utc) or None."""
    if not reading:
        return False
    s, t = reading
    return (isinstance(s, (int, float)) and math.isfinite(s) and -10.0 < s < 20.0
            and isinstance(t, dt.datetime) and t.tzinfo is not None)


def choose_anchor(now_utc, mean_ft, mean_source, fresh=None, stale=None, state=None,
                  tau_h=SURGE_DECAY_TAU_H):
    """Pick the ladder rung. `fresh`, `stale`, `state` are (surge_ft, obs_utc)
    or None; the newest valid, non-future reading wins. A reading whose
    decayed departure from the mean has become negligible, or which is older
    than SURGE_SNAP_MAX_AGE_H, snaps to typical-offset (labeled)."""
    if not (isinstance(mean_ft, (int, float)) and math.isfinite(mean_ft)):
        raise ValueError("mean_ft must be finite (use SURGE_MEAN_FALLBACK_FT)")
    cands = []
    for rung, reading in (("fresh", fresh), ("stale-download", stale), ("stale-state", state)):
        if _valid(reading) and reading[1] <= now_utc + dt.timedelta(minutes=2):
            cands.append((reading[1], rung, reading[0]))
    if cands:
        obs_utc, rung, s = max(cands, key=lambda c: (c[0], -RUNGS.index(c[1])))
        age_h = (now_utc - obs_utc).total_seconds() / 3600.0
        if rung == "fresh" and age_h * 60.0 > SURGE_FRESH_MAX_AGE_MIN:
            rung = "stale-download"
        departure = abs(s - mean_ft) * math.exp(-max(age_h, 0.0) / tau_h)
        if age_h <= SURGE_SNAP_MAX_AGE_H and (rung == "fresh" or departure >= SURGE_SNAP_DEPARTURE_FT):
            return SurgeAnchor(rung, float(mean_ft), mean_source, float(s), obs_utc, tau_h)
    return SurgeAnchor("typical-offset", float(mean_ft), mean_source, None, None, tau_h)


def resolve_mean(now_utc, warm):
    """(mean_ft, mean_source, health) from the warm job's record
    {mean_ft, computed_utc, window_start, window_end, n_hours}, else the
    documented fallback constant."""
    fallback = (SURGE_MEAN_FALLBACK_FT, f"fallback constant ({SURGE_MEAN_FALLBACK_NOTE})")
    if not isinstance(warm, dict):
        return fallback[0], fallback[1], {"status": "degraded", "detail": "no trailing-mean record; using the fallback constant"}
    try:
        mean = float(warm["mean_ft"])
        computed = dt.datetime.fromisoformat(str(warm["computed_utc"]).replace("Z", "+00:00"))
        n = int(warm.get("n_hours") or 0)
    except (KeyError, TypeError, ValueError):
        return fallback[0], fallback[1], {"status": "degraded", "detail": "malformed trailing-mean record; using the fallback constant"}
    age_h = (now_utc - computed).total_seconds() / 3600.0
    if not (math.isfinite(mean) and -2.0 < mean < 3.0) or n < 24 * 300 or age_h < -1:
        return fallback[0], fallback[1], {"status": "degraded", "detail": f"implausible trailing mean {mean!r} (n={n}); using the fallback constant"}
    if age_h > SURGE_MEAN_MAX_AGE_D * 24:
        return fallback[0], fallback[1], {"status": "degraded", "detail": f"trailing mean {age_h / 24:.0f} d old; using the fallback constant"}
    src = f"trailing 365-d mean {warm.get('window_start', '?')}..{warm.get('window_end', '?')}"
    status = "ok" if age_h <= SURGE_MEAN_OK_AGE_H else "degraded"
    return mean, src, {"status": status, "detail": f"{mean:+.3f} ft, {src}, computed {age_h:.0f} h ago"}
