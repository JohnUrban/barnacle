#!/usr/bin/env python3
"""Extract MRMS radar rainfall over the 342 Bay Ave catchment.

Pulls gzipped GRIB2 files from the Iowa State mtarchive
(https://mtarchive.geol.iastate.edu/YYYY/MM/DD/mrms/ncep/<product>/)
and reports rain at the house point plus the CATCHMENT box (land
from the shoreline south to the ridge — see CATCH_* constants;
box geometry changed 2026-07-18: cached box_mean/box_max rows
extracted before that date used the old house-centered half-water
box and are NOT comparable to newer rows. Point values unaffected).

Products:
  PrecipRate                 instantaneous rate, mm/hr, every 2 min
  MultiSensor_QPE_01H_Pass2  gauge-corrected accumulation, mm, hourly,
                             for the hour ENDING at the stamp

Caching (added 2026-07-07 after flaky-archive 404 storms — the
mtarchive load balancer intermittently 404s files that exist):
  - raw .grib2.gz cached in history/data/mrms/raw/ (GITIGNORED —
    ~0.6 MB each; never committed)
  - extracted values appended to history/data/mrms/mrms_extracted.csv
    (COMMITTED — tiny, diffable, the durable copy; deduped on
    product+stamp). Reruns hit cache/CSV, never the network.

Needs: xarray + cfgrib + eccodes (pip-installable; eccodes wheels
bundle the C library). System python lacks them (PEP 668) — use a
venv. First used 2026-07-07 to pin the 7/6 burst: peak 2-min rate
2.95 in/hr at 11:12 ET (hill max 3.06), ~2 in/hr sustained
11:04-11:20, storm total 1.60 in, hour ending 12:00 ET = 0.94 in.

Usage:
  mrms_point_rain.py 2026-07-06 PrecipRate 1440 1444 1448 ...
  mrms_point_rain.py 2026-07-06 MultiSensor_QPE_01H_Pass2 1400 1500
Stamps are HHMM UTC (PrecipRate exists on even minutes).
"""
import csv
import glob
import gzip
import os
import sys
import tempfile
import time
import urllib.request

LAT, LON = 40.4015, -73.991     # 342 Bay Ave (MRMS longitudes are 0-360)
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
BOX = 0.015                     # deg half-width ≈ 1.5 km — the hillside catchment
UA = {"User-Agent": "barnacle flood model (dr.john.urban@gmail.com)"}

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MRMS_DIR = os.path.join(_REPO, "history", "data", "mrms")
RAW_DIR = os.path.join(MRMS_DIR, "raw")
CSV_PATH = os.path.join(MRMS_DIR, "mrms_extracted.csv")
CSV_FIELDS = ["product", "utc", "point", "box_mean", "box_max", "unit"]


def _csv_index():
    """(product, utc) -> row dict for everything already extracted."""
    idx = {}
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH) as f:
            for row in csv.DictReader(f):
                idx[(row["product"], row["utc"])] = row
    return idx


def _csv_append(row):
    new = not os.path.exists(CSV_PATH)
    os.makedirs(MRMS_DIR, exist_ok=True)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def _download(url, dest, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=30).read()
            with open(dest + ".part", "wb") as f:
                f.write(data)
            os.replace(dest + ".part", dest)
            return
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 + 2 * attempt)   # archive 404s are often transient


def fetch(date, product, hhmm, use_cache=True):
    """Return (point, box_mean, box_max) in the product's native units.

    date 'YYYY-MM-DD', hhmm 'HHMMSS' or 'HHMM' UTC. Checks the
    extracted CSV first, then the raw cache, then the network.
    """
    if len(hhmm) == 4:
        hhmm += "00"
    y, m, d = date.split("-")
    utc = f"{date}T{hhmm[:2]}:{hhmm[2:4]}:{hhmm[4:]}Z"

    if use_cache:
        row = _csv_index().get((product, utc))
        if row:
            return float(row["point"]), float(row["box_mean"]), float(row["box_max"])

    fname = f"{product}_00.00_{y}{m}{d}-{hhmm}.grib2.gz"
    raw = os.path.join(RAW_DIR, fname)
    if not (use_cache and os.path.exists(raw)):
        os.makedirs(RAW_DIR, exist_ok=True)
        url = (f"https://mtarchive.geol.iastate.edu/{y}/{m}/{d}/mrms/ncep/"
               f"{product}/{fname}")
        _download(url, raw)

    import xarray as xr
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as f:
        f.write(gzip.decompress(open(raw, "rb").read()))
        tmp = f.name
    try:
        ds = xr.open_dataset(tmp, engine="cfgrib", decode_timedelta=True)
        var = list(ds.data_vars)[0]
        pt = float(ds[var].sel(latitude=LAT, longitude=LON + 360,
                               method="nearest").values)
        box = ds[var].sel(latitude=slice(CATCH_LAT_N, CATCH_LAT_S),
                          longitude=slice(360 + CATCH_LON_W, 360 + CATCH_LON_E))
        out = (pt, float(box.mean().values), float(box.max().values))
        ds.close()
    finally:
        os.remove(tmp)
        for idx in glob.glob(tmp + "*.idx"):
            os.remove(idx)

    if use_cache:
        _csv_append({"product": product, "utc": utc,
                     "point": f"{out[0]:.2f}", "box_mean": f"{out[1]:.2f}",
                     "box_max": f"{out[2]:.2f}",
                     "unit": "mm" if "QPE" in product else "mm/hr"})
    return out


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    date, product, stamps = sys.argv[1], sys.argv[2], sys.argv[3:]
    in_unit = "in" if "QPE" in product else "in/hr"
    print(f"{product} {date}  (point / hill-box mean / hill-box max)")
    for s in stamps:
        try:
            pt, mean, mx = fetch(date, product, s)
            print(f"  {s} UTC  {pt:7.1f}  {mean:7.1f}  {mx:7.1f}"
                  f"   point = {pt / 25.4:.2f} {in_unit}")
        except Exception as exc:
            print(f"  {s} UTC  ERR {str(exc)[:70]}")


if __name__ == "__main__":
    main()
