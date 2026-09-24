#!/usr/bin/env python3
"""Replay golden for model v0.10.6 (surge decay toward the recent average).

`--write` freezes model/data/v0.10.6-reproduction.json from the CURRENT code:
decay values on a fixed grid, ladder rungs for canonical readings, and the
outlook's hourly surge estimator on the committed test fixtures. Default
mode verifies the code still reproduces the file exactly (read-only).
Run: python3 history/scripts/reproduce_v0_10_6.py [--write]
"""
import datetime as dt
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from forecast import flood_forecast_daily as ff  # noqa: E402  (import order: facade first)
from forecast import outlook, surge_decay as sd  # noqa: E402

GOLDEN = ROOT / "model" / "data" / "v0.10.6-reproduction.json"
UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 24, 0, 0, tzinfo=UTC)


def build():
    out = {"model_version": "v0.10.6",
           "constants": {"tau_h": sd.SURGE_DECAY_TAU_H, "fresh_max_age_min": sd.SURGE_FRESH_MAX_AGE_MIN,
                         "snap_departure_ft": sd.SURGE_SNAP_DEPARTURE_FT, "snap_max_age_h": sd.SURGE_SNAP_MAX_AGE_H,
                         "mean_fallback_ft": sd.SURGE_MEAN_FALLBACK_FT,
                         "outlook_tau_h": outlook.PERSISTENCE_DECAY_TAU_H}}
    grid = []
    for s_obs in (-1.0, 0.0, 0.54, 1.5, 2.5, 4.0):
        a = sd.SurgeAnchor("fresh", 0.54, "golden", s_obs, T0)
        grid.append({"s_obs": s_obs, "values": [round(a.at(T0 + dt.timedelta(hours=h)), 6)
                                                for h in (0, 1, 6, 12, 24, 30, 36, 48, 72, 102, 168)]})
    out["decay_grid_mean_0.54"] = grid
    cases = {
        "fresh": dict(fresh=(2.0, T0 - dt.timedelta(minutes=10))),
        "stale-download": dict(stale=(2.0, T0 - dt.timedelta(hours=3))),
        "stale-state": dict(state=(2.0, T0 - dt.timedelta(hours=40))),
        "newest-wins": dict(stale=(1.0, T0 - dt.timedelta(hours=2)), state=(3.0, T0 - dt.timedelta(hours=20))),
        "snap-age": dict(state=(3.0, T0 - dt.timedelta(hours=200))),
        "snap-faded": dict(state=(0.56, T0 - dt.timedelta(hours=2))),
        "none": {},
    }
    out["ladder"] = {k: sd.choose_anchor(T0, 0.54, "golden", **v).as_json(T0) for k, v in cases.items()}
    import test_outlook as to
    data = to._fixture_data()
    data.setdefault("astro_hourly", json.loads((to.FIX / "astro_hourly_20260923.json").read_text()))
    est = outlook.hourly_surge_estimator(to.NOW, data, [
        {"time": "2026-09-23 18:19-04:00", "forecast_peak_mllw": 6.9, "source": "nws-coastal-flood-product"},
        {"time": "2026-09-24 06:47-04:00", "forecast_peak_mllw": 6.4, "source": "nws-coastal-flood-product"},
        {"time": "2026-09-25 19:40-04:00", "forecast_peak_mllw": 7.5, "source": "nws-coastal-flood-product"}],
        0.54, (1.8, to.NOW - dt.timedelta(minutes=20)))
    hours = [to.NOW + dt.timedelta(hours=h) for h in range(-6, 169, 3)]
    out["estimator_on_fixtures"] = [{"utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "surge_ft": round(est(t)[0], 6),
                                     "source": est(t)[1]} for t in hours]
    out["advisory_corrections"] = [{"utc": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "ft": round(c, 6)} for a, c in est.anchors]
    return out


def verify():
    golden = json.loads(GOLDEN.read_text())
    now = build()
    if ff.CURRENT_MODEL_VERSION != golden["model_version"]:
        archived = ROOT / "model" / "archive" / f"{golden['model_version']}.md"
        if not archived.exists():
            raise AssertionError("production stamp differs from the v0.10.6 golden and no archived spec documents a bump")
    bad = []

    def cmp(path, a, b):
        if isinstance(a, dict):
            for k in a:
                cmp(f"{path}.{k}", a[k], b.get(k))
        elif isinstance(a, list):
            if len(a) != len(b or []):
                bad.append(f"{path}: length {len(a)} vs {len(b or [])}")
            for i, (x, y) in enumerate(zip(a, b or [])):
                cmp(f"{path}[{i}]", x, y)
        elif isinstance(a, float) and isinstance(b, (int, float)):
            if not math.isclose(a, b, abs_tol=1e-9):
                bad.append(f"{path}: {a} vs {b}")
        elif a != b and path.split(".")[-1] not in ("label", "age_h", "surge_now_ft"):
            bad.append(f"{path}: {a!r} vs {b!r}")
    cmp("golden", golden, now)
    if bad:
        raise AssertionError("v0.10.6 golden mismatch:\n  " + "\n  ".join(bad[:20]))
    return golden


if __name__ == "__main__":
    if "--write" in sys.argv:
        GOLDEN.write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")
        print(f"wrote {GOLDEN.relative_to(ROOT)}")
    else:
        verify()
        print(f"verification: PASS (production {ff.CURRENT_MODEL_VERSION}; surge decay golden v0.10.6)")
