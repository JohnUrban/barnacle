#!/usr/bin/env python3
"""Bot-integrated MRMS nowcast (v1, 2026-07-17) — writes docs/nowcast.json.

The manual nowcast_tank.py promoted to an unattended pipeline: pull
the last ~60 min of real-time MRMS PrecipRate over the hillside
catchment, integrate the v0.10 tank from the live bay level, project
45 min forward, and publish a small JSON the website + widget render
client-side (no full site rebuild needed — nowcast.json is its own
tiny data file, per the client-side-rendering doctrine).

Cheap-exit design (GHA free-tier): the caller workflow gates on a
stdlib-only trigger check (--check mode: active NWS flood alert OR
thunder-capable hourly forecast OR nonzero recent QPF) before paying
for the xarray/cfgrib install. When inactive, nowcast.json still gets
a fresh {active: false} heartbeat so consumers can tell "quiet" from
"stale".

Modes:
  nowcast.py --check   -> exit 0 = triggers met (run the full pass)
                          exit 3 = quiet (skip heavy deps)
  nowcast.py           -> full pass, writes docs/nowcast.json
"""
import datetime as dt
import glob
import gzip
import json
import os
import re
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flood_forecast_daily as ff

UA = {"User-Agent": "barnacle flood model (dr.john.urban@gmail.com)"}
LAT, LON = 40.4015, -73.991
# CATCHMENT sampling region (2026-07-18 evening, user directive:
# "capture the rain over me and over all the parts that drain to
# me"). The old +/-0.015-deg box was CENTERED on the house — which
# sits on the shoreline, so ~half the box was Sandy Hook Bay: rain
# that drains to nobody diluted the mean, and during event #5 the
# storm core sat south over the bluffs, OUTSIDE the wet half —
# frames read 0.1 in/hr during observed torrents. Backtest with this
# land-only box (shoreline south to the ridge, Mount Mitchill
# included): those frames read 2.4-3.8 in/hr and the tank hindcast
# peak improved +13.0 -> +15.9 in (measured +19.9).
CATCH_LAT_N = 40.4030   # just inland of the shoreline
CATCH_LAT_S = 40.3860   # ridge crest
CATCH_LON_W = -74.001
CATCH_LON_E = -73.980
BOX = 0.015
MRMS_BASE = "https://mrms.ncep.noaa.gov/2D/PrecipRate/"
OUT_PATH = os.path.join(HERE, "..", "docs", "nowcast.json")


def _write(payload):
    payload["generated_utc"] = dt.datetime.now(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    # DAY-MAX MEMORY (2026-07-18, user autonomy requirement: "the
    # goal is Barnacle reporting stuff and looking right without our
    # live intervention"): each run previously overwrote the last, so
    # the system forgot its own floods by evening. Carry the max
    # modeled street water forward across same-day runs; the site's
    # SO-FAR-TODAY line reads it as the automatic (modeled) source
    # when no tape/gauge truth exists.
    try:
        with open(OUT_PATH) as f:
            prev = json.load(f)
        prev_day = (prev.get("generated_utc") or "")[:10]
        today = payload["generated_utc"][:10]
        cand = [payload.get("street_now_in") or 0]
        if prev_day == today:
            cand.append(prev.get("day_max_street_in") or 0)
            if prev.get("day_max_street_in", 0) > (payload.get("street_now_in") or 0):
                payload["day_max_utc"] = prev.get("day_max_utc")
        if "day_max_utc" not in payload and (payload.get("street_now_in") or 0) > 0:
            payload["day_max_utc"] = payload["generated_utc"]
        payload["day_max_street_in"] = round(max(cand), 1)
    except (OSError, ValueError):
        if (payload.get("street_now_in") or 0) > 0:
            payload["day_max_street_in"] = payload["street_now_in"]
            payload["day_max_utc"] = payload["generated_utc"]
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, OUT_PATH)
    print(f"wrote nowcast.json: active={payload.get('active')}")


def trigger_check():
    """Stdlib-only: is there any reason to pay for radar? exit 0/3."""
    try:
        alerts = ff.fetch_nws_flood_alerts()
        if alerts:
            print("trigger: flood alert active:", alerts[0]["event"])
            return 0
    except Exception:
        pass
    try:
        hourly = ff.fetch_nws_hourly_forecast() or []
        for p in hourly[:6]:
            pop = ((p.get("probabilityOfPrecipitation") or {}).get("value")) or 0
            sf = (p.get("shortForecast") or "").lower()
            if pop >= 50 and ("thunder" in sf or "heavy rain" in sf or
                              "shower" in sf):
                print(f"trigger: near-term convective wording (PoP {pop})")
                return 0
    except Exception:
        pass
    print("quiet: no flood alert, no near-term convective wording")
    return 3


def latest_frames(minutes=60):
    listing = urllib.request.urlopen(
        urllib.request.Request(MRMS_BASE, headers=UA), timeout=30).read().decode()
    stamps = sorted(set(re.findall(
        r"MRMS_PrecipRate_00\.00_(\d{8}-\d{6})\.grib2\.gz", listing)))
    newest = dt.datetime.strptime(stamps[-1], "%Y%m%d-%H%M%S")
    keep = [(dt.datetime.strptime(s, "%Y%m%d-%H%M%S"), s) for s in stamps]
    keep = [k for k in keep if (newest - k[0]).total_seconds() <= minutes * 60]
    return keep[::3]   # 2-min cadence -> every 6 min


def box_rate(stamp):
    import xarray as xr
    raw = gzip.decompress(urllib.request.urlopen(urllib.request.Request(
        f"{MRMS_BASE}MRMS_PrecipRate_00.00_{stamp}.grib2.gz",
        headers=UA), timeout=30).read())
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as f:
        f.write(raw)
        tmp = f.name
    try:
        ds = xr.open_dataset(tmp, engine="cfgrib", decode_timedelta=True)
        var = list(ds.data_vars)[0]
        box = ds[var].sel(latitude=slice(CATCH_LAT_N, CATCH_LAT_S),
                          longitude=slice(360 + CATCH_LON_W, 360 + CATCH_LON_E))
        out = float(box.mean()) / 25.4
        ds.close()
    finally:
        os.remove(tmp)
        for g in glob.glob(tmp + "*.idx"):
            os.remove(g)
    return out


def _predicted_bay(now_local):
    """Best available astronomical bay level when observations fail."""
    series = ff.build_water_series(
        0.0, qpf_hourly=[], hours_back=1, hours_forward=1, interval_min=30
    )
    if not series:
        raise RuntimeError("no observed or predicted bay level available")
    target = now_local.strftime("%Y-%m-%d %H:%M")
    point = min(series, key=lambda row: abs(
        (dt.datetime.strptime(row["time"], "%Y-%m-%d %H:%M")
         - now_local).total_seconds()
    ))
    # With surge_ft=0 this is the astronomical prediction in NAVD88.
    return float(point["tide_navd88"]), target


def current_bay(now_local=None):
    """Return ``(NAVD88 level, source)`` for the bay at the current time.

    GitHub runners keep a UTC system clock, while NOAA ``lst_ldt`` query
    parameters are station-local.  Build the window from the shared Sandy
    Hook timezone helper.  If observations are unavailable, retain useful
    drainage physics with the astronomical tide instead of silently granting
    the tank maximum drainage through the old hard-coded 2.8-ft fallback.
    """
    now = now_local or ff._station_local_now()
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
            "station=8531680&product=water_level&datum=MLLW&time_zone=lst_ldt"
            "&units=english&begin_date={b}&end_date={e}&format=json".format(
                b=(now - dt.timedelta(hours=3)
                   ).strftime("%Y%m%d%%20%H:%M"),
                e=now.strftime("%Y%m%d%%20%H:%M")),
            headers=UA), timeout=15))
        pairs = [(r["t"], float(r["v"])) for r in d["data"]]
        pairs = ff._despike_gauge(pairs)
        if pairs:
            return pairs[-1][1] - 2.82, "observed"
    except Exception:
        pass
    predicted, _target = _predicted_bay(now)
    return predicted, "astronomical-fallback"


def run():
    ff._load_stage_curve()
    try:
        bay, bay_source = current_bay()
    except Exception as e:
        _write({"active": False, "error": f"bay level unavailable: {e}",
                "bay_source": "unavailable"})
        return
    frames = latest_frames()
    series = []
    for t, s in frames:
        try:
            series.append((t, round(box_rate(s), 3)))
        except Exception:
            continue
    if not series:
        _write({"active": False, "error": "no radar frames"})
        return
    recent_max = max(r for _, r in series)
    drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
    active = recent_max > max(0.3, drain)
    payload = {
        "active": active,
        "bay_navd88": round(bay, 3),
        "bay_source": bay_source,
        "drain_in_hr": round(drain, 3),
        "frames": [{"utc": t.strftime("%H:%M"), "in_hr": r}
                   for t, r in series],
        "recent_max_in_hr": round(recent_max, 2),
    }
    if active:
        lag = dt.timedelta(minutes=ff.TANK_LAG_MIN)
        base_stage = max(0.0, (bay - 3.52) * 12)

        def rate_at(t):
            tl = t - lag
            prev = series[0]
            for pt in series:
                if pt[0] > tl:
                    break
                prev = pt
            return prev[1]

        V, t = 0.0, series[0][0]
        end_obs = series[-1][0]
        horizon = end_obs + dt.timedelta(minutes=45)
        traj = []
        while t <= horizon:
            r = rate_at(t) if t <= end_obs + lag else series[-1][1]
            net = max(0.0, r - drain)
            V = max(0.0, V + (ff.TANK_K * net ** ff.TANK_GAMMA
                              - ff.TANK_KOUT * V) * (2.0 / 60.0))
            stage = (ff._pluvial_fill(ff._STAGE_CURVE, base_stage, V)
                     if V > 0 else base_stage)
            traj.append((t, stage))
            t += dt.timedelta(minutes=2)
        now_stage = next((st for tt, st in traj if tt >= end_obs),
                         traj[-1][1])
        pk_t, pk = max(traj, key=lambda x: x[1])
        payload.update({
            "street_now_in": round(now_stage, 1),
            "peak_proj_in": round(pk, 1),
            "peak_proj_utc": pk_t.strftime("%H:%M"),
            "regime_now": ff.classify_regime_from_water(3.52 + now_stage / 12.0),
            "traj": [{"utc": tt.strftime("%H:%M"), "in": round(st, 1)}
                     for tt, st in traj[::5]],
        })
    _write(payload)


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(trigger_check())
    run()
