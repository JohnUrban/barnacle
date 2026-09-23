#!/usr/bin/env python3
"""
NWS Mount Holly Coastal Flood (CFW) product parser for Sandy Hook NJ.

Where the Sandy Hook tide table actually lives (verified 2026-09-23,
the parser's first real coastal-flood event, CF.Y.0021):

  * api.weather.gov/alerts `description` carries ONLY the bulleted
    WHAT/WHERE/WHEN/IMPACTS narrative (~1 KB). The per-gauge tide
    table sits AFTER the first `&&` of the zone segment, and the
    alerts API drops everything past `&&`. Parsing alert descriptions
    therefore never finds a Sandy Hook table (all runs 2026-09-22
    21:00Z .. 2026-09-23 10:00Z: "No Sandy Hook section").
  * The raw product text (api.weather.gov/products/<id>, listed newest
    first at /products/types/CFW/locations/PHI) carries every zone
    segment WITH its tables. Real segment, product issued 08:28Z:

    NJZ014-232200-
    /O.EXT.KPHI.CF.Y.0021.260923T2000Z-260926T0600Z/
    Eastern Monmouth-
    428 AM EDT Wed Sep 23 2026
    ...bullets...PRECAUTIONARY/PREPAREDNESS ACTIONS...
    &&

    Time of high total tides are approximate to the nearest hour.

    Sandy Hook Bay at Sandy Hook
    MLLW Categories - Minor 6.7 ft, Moderate 7.7 ft, Major 8.7 ft
    MHHW Categories - Minor 1.5 ft, Moderate 2.5 ft, Major 3.5 ft

                 Total      Total    Departure
     Day/Time    Tide       Tide     from Norm   Flood
                ft MLLW    ft MHHW       ft      Impact
     --------  ---------  ---------  ---------  --------
     23/06 AM     5.9        0.7        1.4       None
     23/06 PM     6.9        1.7        1.8      Minor

    Watson Creek at Manasquan        <- next gauge: the block ends HERE,
    MLLW Categories - ...               not at the following `&&`
    ...
    &&
    $$

Workflow:
  1. Active Coastal Flood alerts at the house point decide ACTIVE.
  2. Alert descriptions are tried first (cheap; the pre-2026-09-23
     path, kept in case the API ever inlines the table again).
  3. Otherwise KPHI's CFW products are fetched newest-first, the one
     issued at the alert's `sent` instant preferred, and the Sandy
     Hook block is parsed from the first product that carries one.
  4. DD/HH AM|PM rows are dated from the product header
     ("428 AM EDT Wed Sep 23 2026"); fallback is the product's
     issuance instant in station-local time.

Run modes:
  python3 nws_surge_parser.py             # check live alerts + products
  python3 nws_surge_parser.py --self-test # built-in legacy-format sample
  python3 nws_surge_parser.py --text FILE # parse FILE as a raw product
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

UA = os.environ.get("USER_AGENT",
                    "highlands-flood-forecast (contact@example.com)")
HIGHLANDS_LAT = 40.405479   # true Bay & Central (2026-09-02 fix)
HIGHLANDS_LON = -73.995195  # (2026-09-02 fix)
STATION_LABEL = "Sandy Hook Bay at Sandy Hook"
STATION_TZ = ZoneInfo("America/New_York")
CFW_PRODUCTS_URL = "https://api.weather.gov/products/types/CFW/locations/PHI"
PRODUCT_URL = "https://api.weather.gov/products/{id}"
MAX_PRODUCT_FETCHES = 4      # newest candidates tried per run
MAX_PRODUCT_AGE_H = 24.0     # relative to the newest active alert's `sent`
BLOCK_CAP_CHARS = 3000

# ---------------------------------------------------------------------------
# Sample text for --self-test (legacy inline layout: table BEFORE `&&`,
# as the Aug 21 2025 product was transcribed). tests/fixtures/
# cfw_phi_20260923_0828z.txt is the real captured product.
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
# Fetchers (each raises on transport failure; callers decide the status)
# ---------------------------------------------------------------------------
def _fetch_json(url, timeout=15):
    # No Accept header on purpose: the alerts endpoint must answer GeoJSON
    # (`features`) while the products endpoints answer JSON-LD (`@graph`).
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_active_coastal_flood():
    """Return the active 'Coastal Flood *' alert property dicts at the house."""
    url = (f"https://api.weather.gov/alerts/active?"
           f"point={HIGHLANDS_LAT},{HIGHLANDS_LON}")
    data = _fetch_json(url)
    out = []
    for f in data.get("features", []):
        props = f.get("properties") or {}
        if "Coastal Flood" in (props.get("event") or ""):
            out.append(props)
    return out


def list_cfw_products():
    """KPHI CFW products, newest first: [{id, issuanceTime, ...}, ...]."""
    data = _fetch_json(CFW_PRODUCTS_URL)
    out = []
    for g in data.get("@graph", []):
        if not g.get("id"):
            continue
        out.append({
            "id": g["id"],
            "issuanceTime": g.get("issuanceTime") or "",
            "issuingOffice": g.get("issuingOffice") or "",
            "wmoCollectiveId": g.get("wmoCollectiveId") or "",
        })
    out.sort(key=lambda p: p["issuanceTime"], reverse=True)
    return out


def fetch_product_text(product_id):
    data = _fetch_json(PRODUCT_URL.format(id=product_id))
    return data.get("productText") or ""


# ---------------------------------------------------------------------------
# Product selection
# ---------------------------------------------------------------------------
def _parse_iso(stamp):
    """ISO-8601 with offset -> aware datetime (naive is taken as UTC)."""
    if not stamp:
        return None
    try:
        when = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return when


def select_candidate_products(products, alerts):
    """Order CFW products for the tide-table search.

    The product issued at an active alert's `sent` instant (that alert's
    own product) comes first; the rest follow newest-first. Products more
    than MAX_PRODUCT_AGE_H older than the newest alert are dropped so a
    stale table is never used silently.
    """
    sent = [s for s in (_parse_iso(a.get("sent")) for a in alerts) if s]
    newest_sent = max(sent) if sent else None
    exact, rest = [], []
    for p in sorted(products, key=lambda x: x.get("issuanceTime") or "",
                    reverse=True):
        issued = _parse_iso(p.get("issuanceTime"))
        if issued is None:
            continue
        if (newest_sent is not None
                and newest_sent - issued > dt.timedelta(hours=MAX_PRODUCT_AGE_H)):
            continue
        if any(abs((issued - s).total_seconds()) < 60 for s in sent):
            exact.append(p)
        else:
            rest.append(p)
    return exact + rest


def issued_local_date(product):
    """(month, day, year) of the product's issuance in station-local time."""
    issued = _parse_iso(product.get("issuanceTime"))
    if issued is None:
        return None
    local = issued.astimezone(STATION_TZ)
    return (local.month, local.day, local.year)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

_ISSUANCE_RE = re.compile(
    r"\b(\d{1,4})\s+(AM|PM)\s+[A-Z]{3,4}\s+"
    r"(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(\d{1,2})\s+(\d{4})")

# A gauge header is a name line immediately followed by its category line.
_STATION_HEADER_RE = re.compile(
    r"^[^\n]*Sandy\s*Hook[^\n]*\n(?:MLLW|MHHW) Categories",
    re.MULTILINE | re.IGNORECASE)
_CATEGORIES_RE = re.compile(r"^MLLW Categories", re.MULTILINE)
_BLOCK_DELIM_RE = re.compile(r"\n\s*&&\s*(?:\n|$)")

_ROW_RE = re.compile(
    r"^\s*(?P<day>\d{1,2})/(?P<hh>\d{1,2})\s+(?P<ampm>AM|PM)\s+"
    r"(?P<tide_mllw>-?\d+\.\d+)\s+"
    r"(?P<tide_mhhw>-?\d+\.\d+)\s+"
    r"(?P<dep>[-+]?\d+\.\d+)\s+"
    r"(?P<cat>None|Minor|Moderate|Major)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def find_issuance_date(text):
    """(month, day, year) from a product header such as
    '531 AM EDT Thu Aug 21 2025'; None when the header is absent."""
    m = _ISSUANCE_RE.search(text)
    if not m:
        return None
    return (MONTHS[m.group(4)], int(m.group(5)), int(m.group(6)))


def find_station_block(text, station_label=STATION_LABEL):
    """The Sandy Hook table block, or None.

    Starts at the gauge header; ends at the next `&&` delimiter OR the
    next gauge's category line, whichever comes first (Watson Creek at
    Manasquan follows Sandy Hook inside the same `&&` block), capped at
    BLOCK_CAP_CHARS.
    """
    m = re.search(re.escape(station_label), text, re.IGNORECASE)
    if not m:
        m = _STATION_HEADER_RE.search(text)
    if not m:
        return None
    start = m.start()
    window = text[start:start + BLOCK_CAP_CHARS]
    end = len(window)
    delim = _BLOCK_DELIM_RE.search(window)
    if delim:
        end = delim.start()
    categories = [c.start() for c in _CATEGORIES_RE.finditer(window[:end])]
    if len(categories) >= 2:
        # Cut at the START of the next gauge's name line, which sits
        # directly above its "MLLW Categories" line.
        end = window.rfind("\n", 0, categories[1] - 1) + 1
    return window[:end]


def parse_tide_projections(text, station_label=STATION_LABEL, issued=None):
    """Extract Sandy Hook tide projections from product text.

    `issued` = (month, day, year) fallback when the text has no
    '... AM EDT Wed Sep 23 2026' header (alert descriptions never do).

    Returns (rows, diagnostic):
      rows: [{"when": naive station-local datetime, "total_mllw_ft",
              "total_mhhw_ft", "departure_ft", "cat", "raw"}, ...]
    """
    block = find_station_block(text, station_label)
    if block is None:
        return [], "No Sandy Hook section in product text"

    issue = find_issuance_date(text) or issued
    if issue is None:
        return [], "Could not find issuance date in product header"
    issue_mon, issue_day, issue_year = issue

    rows = []
    for hit in _ROW_RE.finditer(block):
        day = int(hit.group("day"))
        hour12 = int(hit.group("hh"))
        ampm = hit.group("ampm").upper()
        hour = (hour12 % 12) + (12 if ampm == "PM" else 0)

        # Day rollover: a day well below the issuance day is next month.
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


# ---------------------------------------------------------------------------
# Live entry point
# ---------------------------------------------------------------------------
def get_surge_forecast():
    """Live fetch: (active, projections, source_text, diagnostic).

    `active` is decided by the alerts endpoint alone. When active, the
    projections come from the alert text if it carries the table, else
    from the newest matching KPHI CFW product that does. The diagnostic
    names the source on success and every candidate's failure otherwise.
    """
    alerts = get_active_coastal_flood()
    if not alerts:
        return False, [], None, "No active Coastal Flood event"

    desc_text = "\n\n---\n\n".join(a.get("description") or "" for a in alerts)
    rows, msg = parse_tide_projections(desc_text)
    if rows:
        return True, rows, desc_text, f"{len(rows)} Sandy Hook rows from alert text"
    diag = [f"alert text: {msg}"]

    try:
        products = list_cfw_products()
    except Exception as e:  # transport/JSON failure: report, stay active
        diag.append(f"CFW product list fetch failed: {e}")
        return True, [], desc_text, "; ".join(diag)

    candidates = select_candidate_products(products, alerts)[:MAX_PRODUCT_FETCHES]
    if not candidates:
        diag.append(f"no KPHI CFW product within {MAX_PRODUCT_AGE_H:.0f} h "
                    "of the active alert")
    for p in candidates:
        stamp = p.get("issuanceTime") or "?"
        try:
            text = fetch_product_text(p["id"])
        except Exception as e:
            diag.append(f"CFW {stamp}: fetch failed ({e})")
            continue
        rows, msg = parse_tide_projections(text, issued=issued_local_date(p))
        if rows:
            return True, rows, text, (f"{len(rows)} Sandy Hook rows from CFW "
                                      f"KPHI issued {stamp}")
        diag.append(f"CFW {stamp}: {msg}")
    return True, [], desc_text, "; ".join(diag)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_rows(rows):
    for r in rows:
        print(f"  {r['when'].strftime('%a %m/%d %I:%M %p'):<20} "
              f"{r['total_mllw_ft']:.1f} ft MLLW, "
              f"{r['departure_ft']:+.1f} ft surge, {r['cat']}")


def run_self_test():
    print("Running self-test against the embedded legacy-layout sample...")
    rows, msg = parse_tide_projections(SAMPLE_TEXT)
    expected = [
        ("2025-08-21 07:00", 6.7, 1.9, "Minor"),
        ("2025-08-21 19:00", 8.0, 2.4, "Moderate"),
        ("2025-08-22 08:00", 7.2, 2.1, "Minor"),
        ("2025-08-22 20:00", 7.5, 1.8, "Minor"),
        ("2025-08-23 09:00", 6.6, 1.4, "None"),
        ("2025-08-23 21:00", 6.8, 1.2, "Minor"),
    ]
    ok = len(rows) == len(expected)
    if not ok:
        print(f"FAIL: expected {len(expected)} rows, got {len(rows)}")
    for row, (w, t, d, c) in zip(rows, expected):
        if (row["when"].strftime("%Y-%m-%d %H:%M") != w
                or abs(row["total_mllw_ft"] - t) > 0.05
                or abs(row["departure_ft"] - d) > 0.05
                or row["cat"] != c):
            print(f"FAIL: got {row['when']} {row['total_mllw_ft']} "
                  f"{row['departure_ft']:+.1f} {row['cat']}; "
                  f"expected {w} {t} {d:+.1f} {c}")
            ok = False
    if ok:
        print(f"PASS: parsed all {len(rows)} rows correctly")
        _print_rows(rows)
        return 0
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
                    help="Parse FILE as if it were a raw NWS CFW product")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    if args.text:
        with open(args.text) as f:
            text = f.read()
        rows, msg = parse_tide_projections(text)
        print(f"Parsed {len(rows)} rows ({msg})")
        _print_rows(rows)
        return 0 if rows else 1

    active, rows, source_text, msg = get_surge_forecast()
    if not active:
        print(f"No active Coastal Flood event at 342 Bay Ave: {msg}")
        print("Main script will fall back to surge-persistence logic.")
        return 0

    print("ACTIVE coastal flood event")
    print(f"Parser status: {msg}")
    print(f"Parsed {len(rows)} tide projections:")
    _print_rows(rows)
    if not rows:
        print()
        print("Parser found no rows. First 1500 chars of the alert text follow.")
        print("=" * 60)
        print(source_text[:1500] if source_text else "(no text)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
