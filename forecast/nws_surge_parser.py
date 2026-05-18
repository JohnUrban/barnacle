#!/usr/bin/env python3
"""
NWS Mount Holly Coastal Flood product parser for Sandy Hook NJ.

Real Mt Holly format (observed in an Aug 2025 product):

    Sandy Hook Bay at Sandy Hook
    MLLW Categories - Minor 6.7 ft, Moderate 7.7 ft, Major 8.7 ft
    MHHW Categories - Minor 1.5 ft, Moderate 2.5 ft, Major 3.5 ft
                      Total       Total       Departure
    Day/Time          Tide        Tide        from Norm    Flood
                      ft MLLW     ft MHHW     ft           Impact
    --------          ---------   ---------   ---------    --------
    21/07 AM          6.7         1.5         1.9          Minor
    21/07 PM          8.0         2.8         2.4          Moderate
    22/08 AM          7.2         2.0         2.1          Minor

Workflow:
  1. Fetch active Coastal Flood alerts at 40.4015,-73.991
  2. Find the Sandy Hook Bay at Sandy Hook block
  3. Parse the DD/HH AM|PM table rows
  4. Combine each DD with the product's issuance month/year (with rollover)
  5. Return list of forecast tide rows

Run modes:
  python3 nws_surge_parser.py             # check live alerts
  python3 nws_surge_parser.py --self-test # run built-in test against sample
  python3 nws_surge_parser.py --text FILE # parse FILE as if it were a product
"""

import argparse
import json
import re
import sys
import datetime as dt
from urllib.request import Request, urlopen

UA = "barnacle/0.1 (bayavebarnacle@example.com)"
HIGHLANDS_LAT = 40.4015
HIGHLANDS_LON = -73.991

# ---------------------------------------------------------------------------
# Sample text for self-test (real Mt Holly CFW from Aug 21 2025)
# ---------------------------------------------------------------------------
SAMPLE_TEXT = """\
Coastal Hazard Message
National Weather Service Mount Holly NJ
531 AM EDT Thu Aug 21 2025

NJZ014-024-212300-
/O.CON.KPHI.CF.W.0001.250821T2100Z-250823T0600Z/
Eastern Monmouth-Atlantic Coastal-

...COASTAL FLOOD WARNING REMAINS IN EFFECT FROM 5 PM THIS AFTERNOON
TO 2 AM EDT SATURDAY...

Sandy Hook Bay at Sandy Hook
MLLW Categories - Minor 6.7 ft, Moderate 7.7 ft, Major 8.7 ft
MHHW Categories - Minor 1.5 ft, Moderate 2.5 ft, Major 3.5 ft
                  Total       Total       Departure
Day/Time          Tide        Tide        from Norm    Flood
                  ft MLLW     ft MHHW     ft           Impact
--------          ---------   ---------   ---------    --------
21/07 AM          6.7         1.5         1.9          Minor
21/07 PM          8.0         2.8         2.4          Moderate
22/08 AM          7.2         2.0         2.1          Minor
22/08 PM          7.5         2.3         1.8          Minor
23/09 AM          6.6         1.4         1.4          None
23/09 PM          6.8         1.6         1.2          Minor

&&
"""


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------
def get_active_coastal_flood():
    """Return list of active 'Coastal Flood' alerts at our location."""
    url = (f"https://api.weather.gov/alerts/active?"
           f"point={HIGHLANDS_LAT},{HIGHLANDS_LON}")
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    out = []
    for f in data.get("features", []):
        evt = f["properties"].get("event", "")
        if "Coastal Flood" in evt:
            out.append(f["properties"])
    return out


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
MONTHS = {m: i+1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

def find_issuance_date(text):
    """Find month/year from the product header.
    Example: '531 AM EDT Thu Aug 21 2025' -> (8, 21, 2025)
    Returns (month, day, year) or None.
    """
    m = re.search(
        r"\b(\d{1,4})\s+(AM|PM)\s+[A-Z]{3,4}\s+"
        r"(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2})\s+(\d{4})",
        text,
    )
    if m:
        mon = MONTHS[m.group(4)]
        day = int(m.group(5))
        year = int(m.group(6))
        return (mon, day, year)
    return None


def parse_tide_projections(text, station_label="Sandy Hook Bay at Sandy Hook"):
    """Extract Sandy Hook tide projections from product text.

    Returns list of dicts:
      [{"when": datetime, "total_mllw_ft": float,
        "departure_ft": float, "cat": str, "raw": str}, ...]
    """
    # Find the Sandy Hook block (case-insensitive)
    m = re.search(re.escape(station_label), text, re.IGNORECASE)
    if not m:
        # Fall back to just "Sandy Hook"
        m = re.search(r"Sandy\s*Hook", text, re.IGNORECASE)
    if not m:
        return [], "No Sandy Hook section in product text"

    # Block is from this header until the next "&&" delimiter or another
    # station header, capped at 3000 chars.
    block_start = m.start()
    block_end = block_start + 3000
    end_match = re.search(r"\n\s*&&\s*\n", text[block_start:block_end])
    if end_match:
        block_end = block_start + end_match.start()
    block = text[block_start:block_end]

    issue = find_issuance_date(text)
    if issue is None:
        return [], "Could not find issuance date in product header"
    issue_mon, issue_day, issue_year = issue

    # Match: DD/HH AM|PM   FLOAT   FLOAT   FLOAT   CATEGORY
    pat = re.compile(
        r"^\s*(?P<day>\d{1,2})/(?P<hh>\d{1,2})\s+(?P<ampm>AM|PM)\s+"
        r"(?P<tide_mllw>\d+\.\d+)\s+"
        r"(?P<tide_mhhw>\d+\.\d+)\s+"
        r"(?P<dep>[-+]?\d+\.\d+)\s+"
        r"(?P<cat>None|Minor|Moderate|Major)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )

    rows = []
    for hit in pat.finditer(block):
        day = int(hit.group("day"))
        hour12 = int(hit.group("hh"))
        ampm = hit.group("ampm").upper()
        hour = (hour12 % 12) + (12 if ampm == "PM" else 0)

        # Day rollover: if day is much smaller than issue_day, assume next month
        mon, year = issue_mon, issue_year
        if day < issue_day - 5:
            mon += 1
            if mon > 12:
                mon = 1
                year += 1

        try:
            when = dt.datetime(year, mon, day, hour, 0)
        except ValueError:
            continue

        rows.append({
            "when": when,
            "total_mllw_ft": float(hit.group("tide_mllw")),
            "total_mhhw_ft": float(hit.group("tide_mhhw")),
            "departure_ft": float(hit.group("dep")),
            "cat": hit.group("cat").title(),
            "raw": hit.group(0).strip(),
        })

    return rows, ("ok" if rows else "No DD/HH rows matched in Sandy Hook block")


def get_surge_forecast():
    """Live fetch: (active, projections, raw_text, diagnostic_msg)."""
    alerts = get_active_coastal_flood()
    if not alerts:
        return False, [], None, "No active Coastal Flood event"
    raw_text = "\n\n---\n\n".join(a.get("description", "") for a in alerts)
    rows, msg = parse_tide_projections(raw_text)
    return True, rows, raw_text, msg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def run_self_test():
    print("Running self-test against embedded Aug 2025 sample...")
    rows, msg = parse_tide_projections(SAMPLE_TEXT)
    expected = [
        # (when, total_mllw, departure, cat)
        ("2025-08-21 07:00", 6.7, 1.9, "Minor"),
        ("2025-08-21 19:00", 8.0, 2.4, "Moderate"),
        ("2025-08-22 08:00", 7.2, 2.1, "Minor"),
        ("2025-08-22 20:00", 7.5, 1.8, "Minor"),
        ("2025-08-23 09:00", 6.6, 1.4, "None"),
        ("2025-08-23 21:00", 6.8, 1.2, "Minor"),
    ]
    ok = True
    if len(rows) != len(expected):
        print(f"FAIL: expected {len(expected)} rows, got {len(rows)}")
        ok = False
    for row, exp in zip(rows, expected):
        w, t, d, c = exp
        if (row["when"].strftime("%Y-%m-%d %H:%M") != w
                or abs(row["total_mllw_ft"] - t) > 0.05
                or abs(row["departure_ft"] - d) > 0.05
                or row["cat"] != c):
            print(f"FAIL: got {row['when']} {row['total_mllw_ft']} "
                  f"{row['departure_ft']:+.1f} {row['cat']}")
            print(f"      expected {w} {t} {d:+.1f} {c}")
            ok = False
    if ok:
        print(f"PASS: parsed all {len(rows)} rows correctly")
        print()
        print("Sample output formatting:")
        print("-" * 60)
        for r in rows:
            print(f"  {r['when'].strftime('%a %m/%d %I:%M %p'):<20} "
                  f"{r['total_mllw_ft']:.1f} ft MLLW, "
                  f"{r['departure_ft']:+.1f} ft surge, "
                  f"category: {r['cat']}")
        return 0
    else:
        print(f"\nDiagnostic: {msg}")
        return 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--self-test", action="store_true",
                    help="Run built-in parser test (no network)")
    ap.add_argument("--text", metavar="FILE",
                    help="Parse FILE as if it were a NWS product")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    if args.text:
        with open(args.text) as f:
            text = f.read()
        rows, msg = parse_tide_projections(text)
        print(f"Parsed {len(rows)} rows ({msg})")
        for r in rows:
            print(f"  {r['when'].strftime('%a %m/%d %I:%M %p')}  "
                  f"{r['total_mllw_ft']:.1f} ft MLLW, "
                  f"{r['departure_ft']:+.1f} ft, {r['cat']}")
        return 0 if rows else 1

    active, rows, raw_text, msg = get_surge_forecast()
    if not active:
        print(f"No active Coastal Flood event at 342 Bay Ave: {msg}")
        print("Main script will fall back to surge-persistence logic.")
        return 0

    print(f"ACTIVE coastal flood event")
    print(f"Parser status: {msg}")
    print(f"Parsed {len(rows)} tide projections:")
    print()
    for r in rows:
        print(f"  {r['when'].strftime('%a %m/%d %I:%M %p')}  "
              f"{r['total_mllw_ft']:.1f} ft MLLW, "
              f"{r['departure_ft']:+.1f} ft surge, {r['cat']}")
    if not rows:
        print()
        print("Parser found no rows. First 1500 chars of raw text follow.")
        print("If parser is broken, paste this text into a chat and ask")
        print("for the parser regex to be updated.")
        print("=" * 60)
        print(raw_text[:1500] if raw_text else "(no text)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
