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
import math
import os
import re
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# Prefer the package import so tests and nowcast share ONE module
# object — the old unconditional path hack loaded a SECOND copy of
# flood_forecast_daily, and mock.patch on the package copy silently
# missed the copy trigger_check() actually called (live NWS from
# inside the "offline" suite; passed only while a real Flood Watch
# was active). Script mode (python forecast/nowcast.py) still falls
# back to the path hack.
try:
    from forecast import flood_forecast_daily as ff
except ImportError:
    sys.path.insert(0, HERE)
    import flood_forecast_daily as ff

UA = {"User-Agent": "barnacle flood model (dr.john.urban@gmail.com)"}
LAT, LON = 40.405479, -73.995195  # true intersection (2026-09-02 fix)
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
RADAR_MAX_AGE_MIN = 10
RADAR_MIN_SUCCESS_RATIO = 0.60
RADAR_MIN_SUCCESS_COUNT = 4


def _utc_iso(value):
    """Canonical UTC ISO stamp for an aware or naive-UTC datetime."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _station_day(value):
    """Station-local ISO date for a UTC datetime or ISO timestamp."""
    return ff.utc_to_station_local(value).date().isoformat()


def _unavailable_radar_meta():
    return {
        "radar_quality": "unavailable",
        "source_latest_utc": None,
        "source_age_min": None,
        "frames_expected": 0,
        "frames_succeeded": 0,
        "coverage_minutes": 0.0,
        "frames": [],
        "projection_assumption": "last observed radar rate held for 45 min",
    }


def _origin_day_max(today):
    """(day_max_in, day_max_utc) from the PUBLISHED nowcast.json, or
    (0, None). Guards the day-max merge against stale checkouts: on
    2026-08-03 a cron runner whose checkout predated the flood's
    manual-loop pushes recomputed day-max from its own window (9.0)
    and overwrote the true 13.2 — the merge must see the freshest
    published value, not just the local file. Uses the API with
    GITHUB_TOKEN when available (raw.githubusercontent caches ~5 min
    and unauthenticated api.github.com rate-limits shared runners)."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    urls = ["https://api.github.com/repos/JohnUrban/barnacle/contents/"
            "docs/nowcast.json?ref=main"] if token else [
            "https://raw.githubusercontent.com/JohnUrban/barnacle/main/"
            "docs/nowcast.json"]
    for url in urls:
        try:
            hdrs = dict(UA)
            if token:
                hdrs["Authorization"] = "Bearer " + token
                hdrs["Accept"] = "application/vnd.github.raw+json"
            j = json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers=hdrs), timeout=6))
            if (j.get("day_max_utc")
                    and _station_day(j["day_max_utc"]) == today
                    and (j.get("day_max_street_in") or 0) > 0):
                return j["day_max_street_in"], j["day_max_utc"]
        except Exception:
            continue
    return 0, None


HEARTBEAT_PATH = os.path.join(HERE, "..", "data",
                              "nowcast_heartbeats.csv")
HEARTBEAT_KEEP_DAYS = 30


def _append_heartbeat(payload, now):
    """Rolling OPS log (cadence SLO, audit a2 residual): one line per
    nowcast run. NOT an evidence ledger — 30-day window, pruned on
    write; the details page computes active-period gap stats from it.
    Fail-quiet: cadence accounting must never break a nowcast run."""
    try:
        rows = []
        try:
            with open(HEARTBEAT_PATH) as f:
                rows = [ln.strip() for ln in f if ln.strip()][1:]
        except OSError:
            pass
        cutoff = (now - dt.timedelta(days=HEARTBEAT_KEEP_DAYS)
                  ).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = [r for r in rows if r.split(",")[0] >= cutoff]
        rows.append("{},{},{}".format(
            payload.get("generated_utc", ""),
            "1" if payload.get("active") else "0",
            payload.get("source_age_min", "")))
        with open(HEARTBEAT_PATH, "w") as f:
            f.write("generated_utc,active,source_age_min\n")
            f.write("\n".join(rows) + "\n")
    except Exception:
        pass


def _write(payload, now_utc=None):
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    payload["generated_utc"] = _utc_iso(now)
    # DAY-MAX MEMORY (2026-07-18, user autonomy requirement: "the
    # goal is Barnacle reporting stuff and looking right without our
    # live intervention"): each run previously overwrote the last, so
    # the system forgot its own floods by evening. Carry the max
    # modeled street water forward across same-day runs; the site's
    # SO-FAR-TODAY line reads it as the automatic (modeled) source
    # when no tape/gauge truth exists.
    today = _station_day(now)
    payload["day_local"] = today
    # (value, utc) candidates; winner takes both fields. Monotonic
    # within the day across racing writers (2026-08-03 regression).
    cand = [(payload.get("street_now_in") or 0, payload["generated_utc"])]
    obs_max = payload.pop("_obs_max", None)
    if obs_max:
        cand.append(obs_max)
    try:
        with open(OUT_PATH) as f:
            prev = json.load(f)
        prev_day = prev.get("day_local")
        if not prev_day and prev.get("generated_utc"):
            prev_day = _station_day(prev["generated_utc"])
        max_day = (_station_day(prev["day_max_utc"])
                   if prev.get("day_max_utc") else None)
        if prev_day == today and max_day == today:
            cand.append((prev.get("day_max_street_in") or 0,
                         prev.get("day_max_utc")))
    except (OSError, ValueError):
        pass
    cand.append(_origin_day_max(today))
    best, best_utc = max(cand, key=lambda x: x[0] or 0)
    if best and best_utc:
        payload["day_max_street_in"] = round(best, 1)
        payload["day_max_utc"] = best_utc
    payload.setdefault("nowcast_schema_version", "1.0")
    _append_heartbeat(payload,
                      now_utc or dt.datetime.now(dt.timezone.utc))
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, OUT_PATH)
    print(f"wrote nowcast.json: active={payload.get('active')}")


def trigger_check():
    """Stdlib-only: is there any reason to pay for radar? exit 0/3."""
    try:
        alerts = ff.fetch_nws_flood_alerts()
        if alerts is None:
            print("trigger: NWS alerts unavailable — run radar conservatively")
            return 0
        if alerts:
            print("trigger: flood alert active:", alerts[0]["event"])
            return 0
    except Exception as e:
        print(f"trigger: NWS alerts check failed ({e}) — run radar conservatively")
        return 0
    try:
        hourly = ff.fetch_nws_hourly_forecast() or []
        for p in hourly[:6]:
            pop = ((p.get("probabilityOfPrecipitation") or {}).get("value")) or 0
            sf = (p.get("shortForecast") or "").lower()
            if pop >= 50 and ("thunder" in sf or "heavy rain" in sf or
                              "shower" in sf):
                print(f"trigger: near-term convective wording (PoP {pop})")
                return 0
    except Exception as e:
        print(f"trigger: hourly forecast check failed ({e}) — "
              "run radar conservatively")
        return 0
    print("quiet: no flood alert, no near-term convective wording")
    return 3


def latest_frames(minutes=60, now_utc=None):
    listing = urllib.request.urlopen(
        urllib.request.Request(MRMS_BASE, headers=UA), timeout=30).read().decode()
    stamps = sorted(set(re.findall(
        r"MRMS_PrecipRate_00\.00_(\d{8}-\d{6})\.grib2\.gz", listing)))
    if not stamps:
        raise RuntimeError("MRMS listing contains no precipitation-rate frames")
    newest = dt.datetime.strptime(stamps[-1], "%Y%m%d-%H%M%S")
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    age_min = (now - newest.replace(tzinfo=dt.timezone.utc)).total_seconds() / 60
    if age_min < -2:
        raise RuntimeError(f"MRMS newest frame is {abs(age_min):.1f} min in the future")
    if age_min > RADAR_MAX_AGE_MIN:
        raise RuntimeError(
            f"MRMS newest frame is stale ({age_min:.1f} min old; "
            f"limit {RADAR_MAX_AGE_MIN} min)"
        )
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


def run(now_utc=None):
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    ff._load_stage_curve()
    try:
        bay, bay_source = current_bay()
    except Exception as e:
        _write({"active": False, "error": f"bay level unavailable: {e}",
                "bay_source": "unavailable", **_unavailable_radar_meta()},
               now)
        return
    try:
        frames = latest_frames(now_utc=now)
    except Exception as e:
        _write({"active": False, "error": str(e),
                "bay_source": bay_source, **_unavailable_radar_meta()},
               now)
        return
    series = []
    for t, s in frames:
        try:
            series.append((t, round(box_rate(s), 3)))
        except Exception:
            continue
    expected = len(frames)
    succeeded = len(series)
    # Freshness must describe the newest frame that actually decoded.  A fresh
    # directory listing cannot launder an older successful frame as current.
    source_latest = (series[-1][0] if series else frames[-1][0]).replace(
        tzinfo=dt.timezone.utc
    )
    source_age_min = max(0.0, (now - source_latest).total_seconds() / 60)
    required = max(RADAR_MIN_SUCCESS_COUNT,
                   math.ceil(expected * RADAR_MIN_SUCCESS_RATIO))
    coverage_min = ((series[-1][0] - series[0][0]).total_seconds() / 60
                    if len(series) > 1 else 0.0)
    source_meta = {
        "source_latest_utc": _utc_iso(source_latest),
        "source_age_min": round(source_age_min, 1),
        "frames_expected": expected,
        "frames_succeeded": succeeded,
        "coverage_minutes": round(coverage_min, 1),
        "projection_assumption": "last observed radar rate held for 45 min",
    }
    if succeeded < required:
        _write({"active": False,
                "error": (f"insufficient radar coverage: {succeeded}/{expected} "
                          f"frames; require {required}"),
                "bay_source": bay_source, "radar_quality": "degraded",
                **source_meta}, now)
        return
    recent_max = max(r for _, r in series)
    drain = ff.PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay) / 0.52))
    active = recent_max > max(0.3, drain)
    payload = {
        "active": active,
        "bay_navd88": round(bay, 3),
        "bay_source": bay_source,
        "drain_in_hr": round(drain, 3),
        "frames": [{"utc": _utc_iso(t), "in_hr": r}
                   for t, r in series],
        "recent_max_in_hr": round(recent_max, 2),
        "radar_quality": "ok",
        **source_meta,
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
        obs_pk_t, obs_pk = max(((tt, st) for tt, st in traj
                                if tt <= end_obs),
                               key=lambda x: x[1], default=(None, 0))
        pk_t, pk = max(traj, key=lambda x: x[1])
        regime_now = ff.classify_regime_from_water(3.52 + now_stage / 12.0)
        regime_proj = ff.classify_regime_from_water(3.52 + pk / 12.0)
        # WORST TRUTH WINS THE HEADLINE (event #7, 2026-08-07: the
        # strip said LIGHT while water climbed the porch riser, and
        # the widget said NO FLOODING above a live +10.9 line).
        # rising = the projected peak is ahead of the observed window
        # and meaningfully above the current stage; then the headline
        # class is the PROJECTED class with an arrow. Falling = trust
        # the drain clock (current stage), not the stale projection.
        rising = (pk_t > end_obs) and (pk > now_stage + 0.5)
        headline_in = pk if rising else now_stage
        regime_headline = regime_proj if rising else regime_now
        display = (regime_now.upper() + " → " + regime_proj.upper()
                   + " (rising)"
                   if rising and regime_proj != regime_now
                   else regime_headline.upper()
                   + (" (rising)" if rising else ""))
        payload.update({
            "street_now_in": round(now_stage, 1),
            "peak_proj_in": round(pk, 1),
            "peak_proj_utc": pk_t.strftime("%H:%M"),
            "regime_now": regime_now,
            "regime_proj": regime_proj,
            "trend": "rising" if rising else "falling",
            "headline_in": round(headline_in, 1),
            "regime_headline": regime_headline,
            "regime_display": display,
            "traj": [{"utc": tt.strftime("%H:%M"), "in": round(st, 1)}
                     for tt, st in traj[::5]],
        })
        if obs_pk_t is not None and obs_pk > 0:
            # peak already realized inside this run's observed window —
            # a day-max candidate even if street_now has receded
            payload["_obs_max"] = (round(obs_pk, 1),
                                   obs_pk_t.strftime("%Y-%m-%dT%H:%M:%SZ"))
    _write(payload, now)


def alert_dispatch_check():
    """Exit 0 when an active NWS flood alert is NOT yet reflected in
    data/alert_state.json — the workflow then dispatches the forecast
    workflow immediately instead of letting the alert wait for the
    next hourly slot (2026-08-03: the Flash Flood Warning was cut at
    ~10:36 and ingested at 11:00 — ~30 min after the street peaked).
    Exit 3 = nothing new. Failure-open is NOT wanted here: unknown
    alert status must not spam dispatches, so failures exit 3."""
    try:
        alerts = ff.fetch_nws_flood_alerts()
    except Exception:
        alerts = None
    if not alerts:
        print("alert-dispatch: no active alerts (or status unknown)")
        return 3
    try:
        with open(os.path.join(HERE, "..", "data",
                               "alert_state.json")) as f:
            sig = json.load(f).get("sig", "") or ""
    except (OSError, ValueError):
        sig = ""
    for a in alerts:
        key = f"{a.get('event', '')}@{a.get('onset', '')}"
        if key.strip("@") and key not in sig:
            print(f"alert-dispatch: NEW alert not in state: {key}")
            return 0
    print("alert-dispatch: all active alerts already ingested")
    return 3


RADAR_ALERT_MAX_AGE_MIN = 25


def radar_alert_check():
    """Exit 0 when the just-written nowcast shows alertable street
    water that alert_state has not yet alerted on (event #7: Barnacle
    projected +16.9 in live and no alert pathway existed). Alertable:
    CURRENT street water at curb class or higher, or PROJECTED peak
    at lawn-step class or higher. Fail-closed: stale/degraded radar
    never dispatches. The forecast run it dispatches makes the actual
    send decision transactionally (incl. the daily cap)."""
    try:
        with open(os.path.join(HERE, "..", "docs", "nowcast.json")) as f:
            nc = json.load(f)
    except (OSError, ValueError):
        print("radar-alert: no readable nowcast.json")
        return 3
    if not nc.get("active") or nc.get("radar_quality") != "ok":
        print("radar-alert: inactive or degraded radar")
        return 3
    if (nc.get("source_age_min") or 999) > RADAR_ALERT_MAX_AGE_MIN:
        print("radar-alert: source too old "
              f"({nc.get('source_age_min')} min)")
        return 3
    street = nc.get("street_now_in") or 0
    proj = nc.get("peak_proj_in") or 0
    curb_in = (4.16 - 3.52) * 12      # light class floor
    lawn_in = (4.66 - 3.52) * 12      # moderate class floor
    # falling pool: the projection is a stateless-window overshoot
    # artifact (event #7) — only current street water counts
    proj_ok = proj >= lawn_in and nc.get("trend") != "falling"
    if street < curb_in and not proj_ok:
        print(f"radar-alert: below thresholds (now {street}, proj {proj},"
              f" trend {nc.get('trend')})")
        return 3
    live_class = ff.classify_regime_from_water(
        3.52 + max(street, proj if proj_ok else 0) / 12.0)
    day = nc.get("day_local") or (nc.get("generated_utc") or "")[:10]
    bit = f"radar:{day}:{live_class}"
    try:
        with open(os.path.join(HERE, "..", "data",
                               "alert_state.json")) as f:
            sig = json.load(f).get("sig", "") or ""
    except (OSError, ValueError):
        sig = ""
    if bit in sig:
        print(f"radar-alert: already alerted this class ({bit})")
        return 3
    print(f"radar-alert: DISPATCH ({bit}; now {street}, proj {proj})")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(trigger_check())
    if "--alert-dispatch-check" in sys.argv:
        sys.exit(alert_dispatch_check())
    if "--radar-alert-check" in sys.argv:
        sys.exit(radar_alert_check())
    run()
