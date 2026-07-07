#!/usr/bin/env python3
"""Extract MRMS radar rainfall over the 342 Bay Ave catchment.

Pulls gzipped GRIB2 files from the Iowa State mtarchive
(https://mtarchive.geol.iastate.edu/YYYY/MM/DD/mrms/ncep/<product>/)
and reports rain at the house point plus a ~1.5 km hillside box
(the bluff catchment that funnels onto the corner).

Products:
  PrecipRate                 instantaneous rate, mm/hr, every 2 min
                             (EVEN minutes only — :14:45 etc. 404)
  MultiSensor_QPE_01H_Pass2  gauge-corrected accumulation, mm, hourly,
                             for the hour ENDING at the stamp

Needs: xarray + cfgrib + eccodes (pip-installable; eccodes wheels
bundle the C library). System python lacks them (PEP 668) — use a
venv. First used 2026-07-07 to pin the 7/6 burst: peak 2-min rate
2.95 in/hr at 11:12 ET (hill max 3.06), ~2 in/hr sustained
11:04-11:20, storm total 1.60 in, hour ending 12:00 ET = 0.94 in.

Usage:
  mrms_point_rain.py 2026-07-06 PrecipRate 1440 1444 1448 ...
  mrms_point_rain.py 2026-07-06 MultiSensor_QPE_01H_Pass2 1400 1500 1600
Stamps are HHMM UTC.
"""
import glob
import gzip
import os
import sys
import tempfile
import urllib.request

LAT, LON = 40.4015, -73.991     # 342 Bay Ave (MRMS longitudes are 0-360)
BOX = 0.015                     # deg half-width ≈ 1.5 km — the hillside catchment
UA = {"User-Agent": "barnacle flood model (dr.john.urban@gmail.com)"}


def fetch(date, product, hhmm):
    """Return (point, box_mean, box_max) in the product's native units."""
    import xarray as xr
    y, m, d = date.split("-")
    url = (f"https://mtarchive.geol.iastate.edu/{y}/{m}/{d}/mrms/ncep/"
           f"{product}/{product}_00.00_{y}{m}{d}-{hhmm}00.grib2.gz")
    req = urllib.request.Request(url, headers=UA)
    raw = gzip.decompress(urllib.request.urlopen(req, timeout=30).read())
    with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as f:
        f.write(raw)
        tmp = f.name
    try:
        ds = xr.open_dataset(tmp, engine="cfgrib", decode_timedelta=True)
        var = list(ds.data_vars)[0]
        pt = float(ds[var].sel(latitude=LAT, longitude=LON + 360,
                               method="nearest").values)
        box = ds[var].sel(latitude=slice(LAT + BOX, LAT - BOX),
                          longitude=slice(LON + 360 - BOX, LON + 360 + BOX))
        out = (pt, float(box.mean().values), float(box.max().values))
        ds.close()
    finally:
        os.remove(tmp)
        for idx in glob.glob(tmp + "*.idx"):
            os.remove(idx)
    return out


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    date, product, stamps = sys.argv[1], sys.argv[2], sys.argv[3:]
    unit = "mm" if "QPE" in product else "mm/hr"
    print(f"{product} {date}  (point / hill-box mean / hill-box max, {unit})")
    for s in stamps:
        try:
            pt, mean, mx = fetch(date, product, s)
            in_unit = "in" if "QPE" in product else "in/hr"
            print(f"  {s} UTC  {pt:7.1f}  {mean:7.1f}  {mx:7.1f}"
                  f"   point = {pt / 25.4:.2f} {in_unit}")
        except Exception as exc:
            print(f"  {s} UTC  ERR {str(exc)[:70]}")


if __name__ == "__main__":
    main()
