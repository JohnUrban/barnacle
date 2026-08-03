#!/usr/bin/env python3
"""Build docs/highlands_base.json — the license-clean vector base
layer under the town street flood map (water / green / sand / Route
36 context), from OSM data (ODbL; attribution in the page footer).

Water is the interesting part: OSM oceans aren't polygons, only
`natural=coastline` ways with WATER ON THE RIGHT of the way's
direction of travel. We stitch coastline ways into chains, clip to
the bbox, and close each chain into a water polygon by walking the
bbox perimeter from the chain's exit point to its entry point,
choosing the walk direction that keeps water enclosed. Verified
visually against a test render before first ship (2026-08-03).

Input: scratch OSM dump (also cached at
history/data/highlands_base_osm.json). Output: compact JSON of
lat/lon rings/lines.
"""
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(_REPO, "history", "data", "highlands_base_osm.json")
OUT = os.path.join(_REPO, "docs", "highlands_base.json")
BBOX = (40.330, -74.096, 40.430, -73.955)   # S, W, N, E (widened 2026-08-03 for full Sea Bright + Leonardo west)


def _chains(ways):
    """Join coastline ways end-to-start into chains (dicts by endpoint)."""
    segs = [[(g["lat"], g["lon"]) for g in w.get("geometry", [])]
            for w in ways]
    segs = [s for s in segs if len(s) >= 2]
    changed = True
    while changed:
        changed = False
        for i in range(len(segs)):
            if segs[i] is None:
                continue
            for j in range(len(segs)):
                if i == j or segs[j] is None:
                    continue
                if segs[i][-1] == segs[j][0]:
                    segs[i] = segs[i] + segs[j][1:]
                    segs[j] = None
                    changed = True
                    break
            if changed:
                break
    return [s for s in segs if s]


def _perimeter_walk(p_from, p_to, ccw=False):
    """Points along the bbox perimeter from p_from to p_to (exclusive
    of p_from, inclusive of p_to), walking clockwise in (lat, lon)
    screen orientation (N up), or counter-clockwise if ccw."""
    S, W, N, E = BBOX

    def edge_of(p):
        lat, lon = p
        cands = [(abs(lat - N), 0), (abs(lon - E), 1),
                 (abs(lat - S), 2), (abs(lon - W), 3)]
        return min(cands)[1]

    corners_cw = [(N, E), (S, E), (S, W), (N, W)]   # after edges 0,1,2,3
    e_from, e_to = edge_of(p_from), edge_of(p_to)
    pts = []
    e = e_from
    for _ in range(5):
        if e == e_to:
            pts.append(p_to)
            break
        if ccw:
            pts.append(corners_cw[(e - 1) % 4])
            e = (e - 1) % 4
        else:
            pts.append(corners_cw[e])
            e = (e + 1) % 4
    return pts


def main():
    d = json.load(open(SRC))
    coast, water, green, sand, roads = [], [], [], [], []
    for e in d.get("elements", []):
        t = e.get("tags", {}) or {}
        geom = [(round(g["lat"], 6), round(g["lon"], 6))
                for g in e.get("geometry", [])]
        if len(geom) < 2:
            continue
        if t.get("natural") == "coastline":
            coast.append(e)
        elif t.get("natural") == "water" or t.get("waterway"):
            water.append(geom)
        elif t.get("natural") in ("beach", "sand"):
            sand.append(geom)
        elif t.get("highway"):
            roads.append(geom)
        else:
            green.append(geom)

    # Per-chain closure chosen by GROUND-TRUTH PROBES, not orientation
    # math: tidal-river banks in this bbox are also tagged coastline,
    # and pure orientation rules mis-close them (verified by test
    # renders 2026-08-03). A closure is accepted only if it contains
    # NO known land point; among survivors prefer one containing a
    # known water point. Chains failing both closures are dropped
    # (logged) rather than shipped wrong.
    LAND = [(40.4015, -73.9910),   # 342 Bay corner
            (40.4040, -74.0330),   # downtown Atlantic Highlands
            (40.4080, -74.0580),   # Leonardo, inland side
            (40.3860, -74.0200),   # Navesink hills
            (40.3680, -74.0100),   # Rumson peninsula
            (40.3720, -74.0530),   # Fair Haven
            (40.3610, -73.9745)]   # Sea Bright village (spit)
    WATER = [(40.4200, -73.9950),  # Sandy Hook Bay
             (40.4210, -74.0300),  # bay off Atlantic Highlands
             (40.3880, -73.9770),  # Shrewsbury River
             (40.3620, -74.0550)]  # Navesink River

    def _inside(pt, ring):
        lat, lon = pt
        n, hit = len(ring), False
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            if (a[0] > lat) != (b[0] > lat):
                x = a[1] + (lat - a[0]) * (b[1] - a[1]) / (b[0] - a[0])
                if x > lon:
                    hit = not hit
        return hit

    def _clip_runs(chain):
        """Split a chain into within-bbox runs; crossing points are
        interpolated onto the bbox edge so every run starts and ends
        ON the perimeter (or wholly inside for untouched chains)."""
        S, W, N, E = BBOX

        def inb(p):
            return S <= p[0] <= N and W <= p[1] <= E

        def cross(a, b):
            # first boundary crossing on segment a→b (a in, b out or
            # vice versa) — clip parametrically against each edge
            t_best, pt_best = None, None
            for (lo, hi, idx) in ((S, N, 0), (W, E, 1)):
                for bound in (lo, hi):
                    d = b[idx] - a[idx]
                    if d == 0:
                        continue
                    t = (bound - a[idx]) / d
                    if 0 < t < 1:
                        q = (a[0] + (b[0] - a[0]) * t,
                             a[1] + (b[1] - a[1]) * t)
                        if S - 1e-9 <= q[0] <= N + 1e-9 and \
                                W - 1e-9 <= q[1] <= E + 1e-9:
                            if t_best is None or t < t_best:
                                t_best, pt_best = t, q
            return pt_best

        runs, cur = [], []
        for a, b in zip(chain, chain[1:]):
            if inb(a) and inb(b):
                if not cur:
                    cur = [a]
                cur.append(b)
            elif inb(a) and not inb(b):
                if not cur:
                    cur = [a]
                q = cross(a, b)
                if q:
                    cur.append(q)
                runs.append(cur)
                cur = []
            elif not inb(a) and inb(b):
                q = cross(a, b)
                cur = [q, b] if q else [b]
        if cur:
            runs.append(cur)
        return [r for r in runs if len(r) >= 2]

    clipped = []
    for chain in _chains(coast):
        if chain[0] == chain[-1]:
            continue
        clipped.extend(_clip_runs(chain))

    # RING ASSEMBLY (the osmcoastline construction): every clipped run
    # ends on the bbox perimeter with water on its RIGHT. Rings form by
    # walking from each run's exit point along the perimeter to the
    # NEXT run's entry point, inserting corners, until closed — runs
    # connect to EACH OTHER (this is what closes a river between its
    # two banks). The global walk direction is picked empirically: try
    # both, keep the one whose rings contain no known land probe.
    S, W, N, E = BBOX
    PERI = [(N, W), (N, E), (S, E), (S, W)]     # clockwise corners

    def peri_pos(pt):
        lat, lon = pt
        dN, dE, dS, dW = abs(lat - N), abs(lon - E), abs(lat - S), abs(lon - W)
        m = min(dN, dE, dS, dW)
        LTOP = E - W
        LSIDE = N - S
        if m == dN:
            return lon - W
        if m == dE:
            return LTOP + (N - lat)
        if m == dS:
            return LTOP + LSIDE + (E - lon)
        return LTOP + LSIDE + LTOP + (lat - S)

    TOTAL = 2 * (E - W) + 2 * (N - S)
    CORNER_POS = [peri_pos(c) for c in PERI]

    def corners_between(a, b, cw=True):
        out_pts = []
        if cw:
            span = (b - a) % TOTAL
            cands = sorted(((cp - a) % TOTAL, i)
                           for i, cp in enumerate(CORNER_POS))
            for off, i in cands:
                if 1e-12 < off < span:
                    out_pts.append(PERI[i])
        else:
            span = (a - b) % TOTAL
            cands = sorted(((a - cp) % TOTAL, i)
                           for i, cp in enumerate(CORNER_POS))
            for off, i in cands:
                if 1e-12 < off < span:
                    out_pts.append(PERI[i])
        return out_pts

    def assemble(runs, cw):
        starts = [(peri_pos(r[0]), i) for i, r in enumerate(runs)]
        used, rings = set(), []
        for seed in range(len(runs)):
            if seed in used:
                continue
            ring, cur = [], seed
            for _ in range(len(runs) + 1):
                used.add(cur)
                ring.extend(runs[cur])
                endp = peri_pos(runs[cur][-1])
                best = None
                for sp, i in starts:
                    if i in used and i != seed:
                        continue
                    off = ((sp - endp) % TOTAL) if cw else ((endp - sp) % TOTAL)
                    if off < 1e-12:
                        off = TOTAL
                    if i == seed:
                        pass
                    if best is None or off < best[0]:
                        best = (off, i, sp)
                if best is None:
                    break
                ring.extend(corners_between(endp, best[2], cw))
                if best[1] == seed:
                    break
                cur = best[1]
            rings.append(ring)
        return rings

    def _ring_ok(rings):
        return not any(_inside(pl, ring) for ring in rings for pl in LAND)

    chosen = None
    for cw in (True, False):
        rings = assemble(clipped, cw)
        if _ring_ok(rings):
            chosen = rings
            break
    if chosen is None:
        print("  WARNING: neither assembly direction passed land probes;"
              " falling back to coastline strokes only")
        chosen = []
    for ring in chosen:
        water.append([(round(a, 6), round(b, 6)) for a, b in ring])

    out = {"bbox": list(BBOX), "water": water, "green": green,
           "sand": sand, "roads_ctx": roads}
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print(f"wrote {OUT}: water {len(water)} polys, green {len(green)}, "
          f"sand {len(sand)}, ctx roads {len(roads)}")


if __name__ == "__main__":
    main()
