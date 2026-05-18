#!/usr/bin/env python3
"""
NWS Coastal Flood product parser for Sandy Hook NJ.

When NWS Mount Holly (PHI) issues a Coastal Flood Warning, Advisory, or
Statement (all under product code CFW), the text typically includes a
"Highest tide projections" or similar table with Sandy Hook entries
formatted roughly:

    Sandy Hook NJ
    Day/Date         Time      Total Tide   Departure   Flood Category
                               (FT MLLW)    (FT)
    ----------------------------------------------------------------
    Thu 30/Oct       3:32 PM   7.6          2.5         Minor
    Fri 31/Oct       4:13 AM   6.8          1.8         None
    Fri 31/Oct       4:39 PM   7.4          2.3         Minor

This module:
  1. Fetches active alerts at 40.4015,-73.991 from api.weather.gov
  2. Filters for any event name containing "Coastal Flood"
  3. Parses tide projections out of the description text
  4. Returns a list of (datetime_local, total_tide_ft, departure_ft, category)

Used as a drop-in upgrade for the surge-forecast portion of the main
flood_forecast_daily.py script. When no coastal flood is active, returns
empty list and caller falls back to surge-persistence logic.
"""

import json
import re
import sys
import datetime as dt
from urllib.request import Request, urlopen

UA = "barnacle/0.1 (bayavebarnacle@example.com)"
HIGHLANDS_LAT = 40.4015
HIGHLANDS_LON = -73.991


def get_active_coastal_flood():
    """Return list of active 'Coastal Flood' alerts at our location."""
    url = f"https://api.weather.gov/alerts/active?point={HIGHLANDS_LAT},{HIGHLANDS_LON}"
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    out = []
    for f in data.get("features", []):
        evt = f["properties"].get("event", "")
        if "Coastal Flood" in evt:
            out.append(f["properties"])
    return out


def parse_tide_projections(text):
    """
    Parse Sandy Hook tide projections out of NWS coastal flood product text.

    Returns list of dicts:
      [{"when": datetime, "total_ft": float, "departure_ft": float, "cat": str}, ...]
    """
    rows = []

    # Find Sandy Hook section
    m = re.search(r"Sandy\s*Hook(?:\s*NJ)?", text, re.IGNORECASE)
    if not m:
        return rows
    # Look in the ~40 lines after the Sandy Hook header
    block_start = m.start()
    block = text[block_start:block_start + 3000]

    # Strategy A: lines matching day/date, time, total, departure, category
    # Examples we've seen formats include:
    #   "Thu 30/Oct  3:32 PM   7.6   2.5   Minor"
    #   "Thu Oct 30  03:32 PM EDT   7.6   2.5   Minor"
    # Use a flexible regex with multiple anchor patterns.
    line_patterns = [
        # "Day DD/Mon   HH:MM AM/PM   total  departure  cat"
        re.compile(
            r"^\s*(?P<dow>Sun|Mon|Tue|Wed|Thu|Fri|Sat)\.?\s+"
            r"(?P<day>\d{1,2})/(?P<mon>[A-Z][a-z]{2})\s+"
            r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)\s+"
            r"(?P<total>\d+\.\d+)\s+"
            r"(?P<dep>[-+]?\d+\.\d+)\s+"
            r"(?P<cat>None|Minor|Moderate|Major)",
            re.MULTILINE | re.IGNORECASE,
        ),
        # "Day Mon DD   HH:MM AM/PM [TZ]   total  departure  cat"
        re.compile(
            r"^\s*(?P<dow>Sun|Mon|Tue|Wed|Thu|Fri|Sat)\.?\s+"
            r"(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
            r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)(?:\s+[A-Z]{2,4})?\s+"
            r"(?P<total>\d+\.\d+)\s+"
            r"(?P<dep>[-+]?\d+\.\d+)\s+"
            r"(?P<cat>None|Minor|Moderate|Major)",
            re.MULTILINE | re.IGNORECASE,
        ),
    ]

    today = dt.date.today()
    year_hint = today.year

    for pat in line_patterns:
        for m in pat.finditer(block):
            try:
                day = int(m.group("day"))
                mon_str = m.group("mon")
                mon = dt.datetime.strptime(mon_str, "%b").month
                # Year inference: if month is more than 6 months behind current,
                # assume next year (e.g. parsing in Dec, sees Feb)
                year = year_hint
                if mon < today.month - 6:
                    year += 1
                elif mon > today.month + 6:
                    year -= 1
                time_str = re.sub(r"\s+", " ", m.group("time")).strip().upper()
                when = dt.datetime.strptime(
                    f"{year}-{mon:02d}-{day:02d} {time_str}",
                    "%Y-%m-%d %I:%M %p",
                )
                rows.append({
                    "when": when,
                    "total_ft": float(m.group("total")),
                    "departure_ft": float(m.group("dep")),
                    "cat": m.group("cat").title(),
                    "raw": m.group(0).strip(),
                })
            except (ValueError, AttributeError):
                continue
        if rows:
            break

    # Dedupe by (when, total_ft)
    seen = set()
    unique = []
    for r in rows:
        key = (r["when"], r["total_ft"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda r: r["when"])
    return unique


def get_surge_forecast():
    """
    Main entry point: returns (active, projections, raw_text).

    active: bool, True if a Coastal Flood event is active
    projections: list of parsed tide rows (may be empty even if active, if parser fails)
    raw_text: full NWS product description (for debugging / fallback)
    """
    alerts = get_active_coastal_flood()
    if not alerts:
        return False, [], None
    # Combine all active coastal flood descriptions
    raw_text = "\n\n---\n\n".join(a.get("description", "") for a in alerts)
    projections = parse_tide_projections(raw_text)
    return True, projections, raw_text


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-text", metavar="FILE",
                    help="Parse text from FILE instead of fetching API (for testing parser)")
    args = ap.parse_args()

    if args.test_text:
        with open(args.test_text) as f:
            text = f.read()
        active = True
        projections = parse_tide_projections(text)
        raw_text = text
    else:
        active, projections, raw_text = get_surge_forecast()

    if not active:
        print("No active Coastal Flood event at 342 Bay Ave location.")
        print("Surge forecast falls back to surge-persistence logic in main script.")
        return 0

    print(f"ACTIVE coastal flood event - parsed {len(projections)} tide projections")
    print()
    if projections:
        for p in projections:
            print(f"  {p['when'].strftime('%a %m/%d %I:%M %p')}: "
                  f"{p['total_ft']:.1f} ft total, "
                  f"{p['departure_ft']:+.1f} ft surge, "
                  f"category: {p['cat']}")
    else:
        print("WARNING: parser found no tide projections in the text.")
        print("First 1000 chars of raw text:")
        print(raw_text[:1000] if raw_text else "(no text)")
        print()
        print("Send this output back so the parser can be hardened.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
