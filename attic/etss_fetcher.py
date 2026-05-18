#!/usr/bin/env python3
"""
NOAA Extra-Tropical Storm Surge (ETSS) fetcher for Sandy Hook NJ.

ETSS is NOAA/NWS Meteorological Development Lab's operational model that
forecasts total water level (predicted tide + storm surge + 5-day anomaly
correction) at 82 coastal stations including Sandy Hook (8531680).

Runs 4x daily at 00z, 06z, 12z, 18z. Output is plain text at:
  https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/etss.YYYYMMDD/

Key files:
  etss.t{cycle}z.stormtide.est.txt   - East coast TOTAL WATER LEVEL (what we want)
  etss.t{cycle}z.stormsurge.est.txt  - East coast surge only
  etss.t{cycle}z.init_wl.txt         - Initial water levels (small)

Usage:
  python3 etss_fetcher.py             # Try today's latest, print Sandy Hook forecast
  python3 etss_fetcher.py --raw       # Print the raw file (debugging)
  python3 etss_fetcher.py --raw --save etss_sample.txt    # Save raw text to file

Once we see the actual format, we'll integrate cleanly into the main
flood forecast script.
"""

import argparse
import datetime as dt
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "highlands-flood-forecast-etss-fetcher (test@example.com)"

# Mirrors that serve the same data:
MIRRORS = [
    "https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/",
    "https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/",
]


def fetch_url(url, timeout=30):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_latest_etss(verbose=True):
    """Try mirrors and recent run cycles until one works. Returns (url, text)."""
    now = dt.datetime.utcnow()
    # Try today's runs, then yesterday's, going back in time
    attempts = []
    for days_back in range(0, 4):
        date = (now - dt.timedelta(days=days_back)).strftime("%Y%m%d")
        # Cycles in reverse order: try most recent first
        for cycle in ["18", "12", "06", "00"]:
            # Skip future cycles for today
            if days_back == 0:
                cycle_dt = dt.datetime.utcnow().replace(
                    hour=int(cycle), minute=0, second=0, microsecond=0)
                if cycle_dt > now - dt.timedelta(hours=2):
                    # Too recent, may not be uploaded yet
                    continue
            attempts.append((date, cycle))

    last_err = None
    for date, cycle in attempts:
        for mirror in MIRRORS:
            url = f"{mirror}etss.{date}/etss.t{cycle}z.stormtide.est.txt"
            if verbose:
                print(f"trying: {url}", file=sys.stderr)
            try:
                text = fetch_url(url)
                if verbose:
                    print(f"SUCCESS: {url}", file=sys.stderr)
                return url, text, date, cycle
            except (HTTPError, URLError, TimeoutError) as e:
                last_err = e
                continue
    raise RuntimeError(f"All ETSS fetch attempts failed. Last error: {last_err}")


def parse_sandy_hook(text):
    """
    Parse the ETSS east coast stormtide text for Sandy Hook forecast.

    The format isn't perfectly documented; this attempts several patterns.
    Sandy Hook should appear identified by:
      - Name string "Sandy Hook" or "SANDY HOOK"
      - Station ID 8531680
      - State "NJ"

    Returns a list of dicts: [{"timestamp": ..., "tide_ft": ..., ...}, ...]
    Or returns an empty list and the raw block if we can't parse cleanly.
    """
    # Find a block that mentions Sandy Hook. The block is typically delimited
    # by a station header (often with name + station id + lat/lon).
    lines = text.splitlines()

    # Find lines mentioning Sandy Hook (case-insensitive)
    sh_line_idxs = [
        i for i, line in enumerate(lines)
        if re.search(r"sandy\s*hook", line, re.IGNORECASE)
        or "8531680" in line
    ]

    if not sh_line_idxs:
        return None, "No Sandy Hook reference found in file"

    # Extract a block: from the first Sandy Hook line, until the next station
    # header (or end of file). Station headers typically have a recognizable
    # pattern (station name + ID + lat/lon, or all caps).
    start = sh_line_idxs[0]

    # Heuristic: end block at the next line that looks like a new station header
    # (contains uppercase name followed by lat/lon or station id), or after
    # ~120 lines (typical block size for hourly 48-96h forecast).
    end = min(start + 200, len(lines))
    for j in range(start + 5, end):
        l = lines[j]
        # New station header heuristic: line with many uppercase + a number
        if re.match(r"^\s*[A-Z][A-Z\s,\.]+\s+\d{7}", l):
            if "SANDY" not in l.upper():
                end = j
                break
        if re.match(r"^\s*[A-Z]{3,}.*\d{4,}", l) and "SANDY" not in l.upper():
            # Possible alternative station header pattern
            if j - start > 20:  # only break if we've captured some data
                end = j
                break

    block = "\n".join(lines[start:end])

    # Try to parse rows of forecast data. The most common format is:
    #   YYYYMMDD HHMM  tide  surge  anomaly  total
    # or with header like: DATE TIME TIDE SURGE ANOM TOTAL
    # Some ETSS outputs use: DDMMM HH (e.g., 18MAY 12)
    # We'll try a few patterns.
    rows = []

    # Pattern A: YYYYMMDD HHMM  followed by 2-6 floats
    for m in re.finditer(
        r"^\s*(\d{8})\s+(\d{2})(\d{2})?\s+"
        r"([-+]?\d+\.\d+)\s+([-+]?\d+\.\d+)"
        r"(?:\s+([-+]?\d+\.\d+))?(?:\s+([-+]?\d+\.\d+))?(?:\s+([-+]?\d+\.\d+))?",
        block, re.MULTILINE,
    ):
        d, hh, mm = m.group(1), m.group(2), (m.group(3) or "00")
        try:
            ts = dt.datetime.strptime(d + hh + mm, "%Y%m%d%H%M")
        except ValueError:
            continue
        vals = [float(v) for v in m.groups()[3:] if v]
        rows.append({"utc": ts, "values": vals, "raw": m.group(0).strip()})

    # Pattern B: hh + dd + mmm (e.g., "12 18MAY") followed by floats
    if not rows:
        # Try to find a year context in the file (often a "DATE:" or similar header)
        year_match = re.search(r"\b(20\d\d)\b", text[:2000])
        year = int(year_match.group(1)) if year_match else dt.date.today().year
        for m in re.finditer(
            r"^\s*(\d{1,2})\s+(\d{1,2})([A-Z]{3})\s+"
            r"([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)",
            block, re.MULTILINE,
        ):
            hh, dd, mon = m.group(1), m.group(2), m.group(3)
            try:
                ts = dt.datetime.strptime(
                    f"{int(dd):02d} {mon} {year} {int(hh):02d}",
                    "%d %b %Y %H"
                )
            except ValueError:
                continue
            vals = [float(v) for v in m.groups()[3:] if v]
            rows.append({"utc": ts, "values": vals, "raw": m.group(0).strip()})

    if not rows:
        return None, block

    return rows, block


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", action="store_true",
                    help="Print raw file contents (for inspecting format)")
    ap.add_argument("--save", metavar="FILE",
                    help="Save raw text to FILE for inspection")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress 'trying URL' messages")
    args = ap.parse_args()

    try:
        url, text, date, cycle = fetch_latest_etss(verbose=not args.quiet)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"# Fetched: {url}")
    print(f"# Run: {date} {cycle}Z")
    print(f"# Total length: {len(text)} chars, {len(text.splitlines())} lines")
    print()

    if args.save:
        with open(args.save, "w") as f:
            f.write(text)
        print(f"Saved raw text to {args.save}")

    if args.raw:
        print(text)
        return 0

    rows, block = parse_sandy_hook(text)

    if rows is None:
        print("WARNING: could not parse Sandy Hook block as time series.")
        print("Raw block follows:")
        print("=" * 60)
        print(block)
        print("=" * 60)
        print()
        print("Re-run with --raw to see full file, or --save raw.txt to inspect.")
        return 1

    print(f"# Parsed {len(rows)} forecast hours for Sandy Hook:")
    print(f"# {'UTC':<20} {'values'}")
    for r in rows[:40]:
        print(f"{r['utc'].strftime('%Y-%m-%d %H:%M'):<20} {r['values']}")
    if len(rows) > 40:
        print(f"... and {len(rows)-40} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
