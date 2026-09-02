#!/usr/bin/env python3
"""Detect rain-ponding candidate sags along the region street network
(user idea 2026-08-03: "a valley between two hills... floods in rain
despite high elevation" — the Rt 36 valley in Highlands is the type
example).

GEOMETRY ONLY — no drainage physics claimed: a sag is a street vertex
you cannot walk away from without climbing, and its basin depth is
pour-point elevation minus sag elevation. Real ponding also depends on
storm drains, which we do not model; the badge wording on the map says
"collects water in downpours (terrain only)".

Method (1-D per-road profile — the user's phrasing verbatim: "a
valley between two hills" ON the road; immune to graph-sparsity
artifacts that made hillside benches read as 10-ft basins):
  For each interior vertex of each way, walk the way's own elevation
  profile in both directions; on each side record the maximum
  elevation reached before the profile first drops BELOW the vertex.
  depth = min(riseLeft, riseRight), capped. Keep depth ≥ MIN_DEPTH_FT
  and elevation ≥ MIN_ELEV_FT (below that, tides own the story).
  Side-shoulder and storm-drain drainage remain unmodeled — the map
  badge says "terrain only".

Input:  docs/highlands_streets.json (region network + LiDAR elevs)
Output: docs/highlands_sags.json  [{lat, lon, elev, depth, street,
                                    town, pour}]
"""
import json
import os

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(_REPO, "docs", "highlands_streets.json")
OUT = os.path.join(_REPO, "docs", "highlands_sags.json")
MIN_DEPTH_FT = 1.0
MIN_ELEV_FT = 6.0     # above routine spring-tide reach
MAX_DEPTH_FT = 10.0   # street ponds deeper than this don't happen


def main():
    d = json.load(open(SRC))
    sags = []
    for st in d["streets"]:
        pts = [p for p in st["pts"] if p[2] is not None]
        n = len(pts)
        if n < 5:
            continue
        elevs = [p[2] for p in pts]
        for i in range(1, n - 1):
            e = elevs[i]
            if e < MIN_ELEV_FT:
                continue
            if elevs[i - 1] < e or elevs[i + 1] < e:
                continue
            rises = []
            for step in (-1, 1):
                mx, j = e, i + step
                while 0 <= j < n and elevs[j] >= e:
                    mx = max(mx, elevs[j])
                    j += step
                rises.append(mx - e)
            depth = min(min(rises), MAX_DEPTH_FT)
            if depth >= MIN_DEPTH_FT:
                sags.append({"lat": pts[i][0], "lon": pts[i][1],
                             "elev": round(e, 1),
                             "depth": round(depth, 1),
                             "street": st.get("name") or "(unnamed)",
                             "town": st.get("town") or ""})

    sags.sort(key=lambda s: -s["depth"])
    kept = []
    for s in sags:
        if all(abs(s["lat"] - t["lat"]) * 111320 > 120
               or abs(s["lon"] - t["lon"]) * 85000 > 120
               for t in kept):
            kept.append(s)
    with open(OUT, "w") as f:
        json.dump({"min_depth_ft": MIN_DEPTH_FT,
                   "min_elev_ft": MIN_ELEV_FT, "sags": kept}, f,
                  separators=(",", ":"))
        f.write("\n")
    print(f"wrote {OUT}: {len(kept)} sags (from {len(sags)} raw)")
    for s2 in kept[:14]:
        print(f"  {s2['depth']:4.1f} ft dip @ {s2['elev']:5.1f} ft — "
              f"{s2['street']} ({s2['town']})")


if __name__ == "__main__":
    main()
