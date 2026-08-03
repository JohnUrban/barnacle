#!/usr/bin/env python3
"""Build docs/highlands_streets.json for the town street flood map.

Inputs:
  - OSM way geometry (overpass JSON; scratch copy also cached at
    history/data/highlands_streets_osm.json for reproducibility)
  - history/data/highlands_street_elevations.csv — USGS 3DEP 1-m
    LiDAR ground elevations (NAVD88 ft) sampled ~25 m along streets
    (see the elevation-sweep recipe in the same commit as this file)

Output: docs/highlands_streets.json
  {"bbox": [S, W, N, E],
   "streets": [{"name": "...", "pts": [[lat, lon, elev], ...]}, ...]}

Ways keep their OSM polyline order (so the page draws real lines,
not dots); each vertex takes the elevation of the nearest sampled
point within ~35 m, else null (rendered as a gap).
"""
import csv
import json
import math
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OSM = os.path.join(_REPO, "history", "data", "highlands_streets_osm.json")
OSM2 = os.path.join(_REPO, "history", "data", "bayshore_streets_osm.json")
OSM3 = os.path.join(_REPO, "history", "data", "region_streets_osm.json")
ELEV = os.path.join(_REPO, "history", "data", "highlands_street_elevations.csv")
OUT = os.path.join(_REPO, "docs", "highlands_streets.json")


def _town_of(lat, lon):
    """Crude municipal labels for the street readout — approximate
    rectangles, cosmetic only, EXCEPT that the rain view applies only
    to town == "Highlands", so the Highlands rule must stay TIGHT
    (never leak south of the borough or west of Many Mind Creek)."""
    north = lat >= 40.392
    if north:
        if lon < -74.075:
            return "Belford/Port Monmouth"
        if lon < -74.048:
            return "Leonardo"
        if lat < 40.402 and lon > -73.990:
            return "Sea Bright"
        if lon < -74.008:
            return "Atlantic Highlands"
        return "Highlands"
    if lon > -73.995:
        return "Sea Bright"
    if lon > -74.035:
        return "Rumson"
    if lon > -74.062:
        return "Fair Haven"
    return "Red Bank"


def _town_of_way(geom):
    g = geom[len(geom) // 2]
    lat, lon = g.get("lat", 0), g.get("lon", 0)
    if 40.375 <= lat < 40.392 and -74.062 <= lon <= -73.995:
        return "Navesink/Locust (Middletown)"
    return _town_of(lat, lon)


def main():
    seen = set()
    ways = []
    for w in json.load(open(OSM))["elements"]:
        seen.add(w.get("id"))
        ways.append((w, "Highlands"))
    for path in (OSM2, OSM3):
        if not os.path.exists(path):
            continue
        for w in json.load(open(path))["elements"]:
            if w.get("id") in seen:
                continue
            seen.add(w.get("id"))
            ways.append((w, _town_of_way(w.get("geometry") or [{}])))
    grid = {}
    with open(ELEV) as f:
        for r in csv.DictReader(f):
            lat, lon = float(r["lat"]), float(r["lon"])
            grid[(round(lat, 4), round(lon, 4))] = float(r["elev_navd88_ft"])

    def elev_near(lat, lon):
        k = (round(lat, 4), round(lon, 4))
        if k in grid:
            # sub-0.5 ft NAVD88 = water surface under a bridge span
            # (Rumson Rd bridge reads -2.9); no street is below +2.9.
            return grid[k] if grid[k] >= 0.5 else None
        
        best, bd = None, 1e9
        for dlat in (-2, -1, 0, 1, 2):
            for dlon in (-3, -2, -1, 0, 1, 2, 3):
                kk = (round(k[0] + dlat * 1e-4, 4), round(k[1] + dlon * 1e-4, 4))
                if kk in grid:
                    d = (abs(dlat) * 11.1) ** 2 + (abs(dlon) * 8.5) ** 2
                    if d < bd:
                        bd, best = d, grid[kk]
        return best if (best is None or best >= 0.5) else None

    streets, lats, lons = [], [], []
    for w, town in ways:
        geom = w.get("geometry") or []
        if len(geom) < 2:
            continue
        pts = []
        for g in geom:
            e = elev_near(g["lat"], g["lon"])
            pts.append([round(g["lat"], 6), round(g["lon"], 6),
                        round(e, 2) if e is not None else None])
            lats.append(g["lat"])
            lons.append(g["lon"])
        streets.append({"name": (w.get("tags") or {}).get("name", ""),
                        "town": town, "pts": pts})

    out = {"bbox": [round(min(lats), 5), round(min(lons), 5),
                    round(max(lats), 5), round(max(lons), 5)],
           "streets": streets}
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    n = sum(len(s["pts"]) for s in streets)
    missing = sum(1 for s in streets for p in s["pts"] if p[2] is None)
    print(f"wrote {OUT}: {len(streets)} ways, {n} vertices, "
          f"{missing} without elevation")
    if missing > n * 0.2:
        sys.exit("too many vertices missing elevation — rerun the sweep")


if __name__ == "__main__":
    main()
