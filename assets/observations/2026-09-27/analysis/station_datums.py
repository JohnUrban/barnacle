"""Station-specific MLLW → NAVD88 conversions (audit 2026-09-27-a1 round 05 R6).

NOAA CO-OPS datums, tidal epoch 1983–2001, feet relative to station datum:
  Sandy Hook 8531680: MLLW 2.51, NAVD88 5.33  → NAVD88 = MLLW − 2.82
  The Battery 8518750: MLLW 3.29, NAVD88 6.06 → NAVD88 = MLLW − 2.77
Primary receipts (official API URL, retrieval time, response) archived by
Codex on 2026-09-27 22:42Z: audits/2026-09-27-a1/05-noaa-8531680-datums.json
and 05-noaa-8518750-datums.json. The production constant
forecast.flood_forecast_daily.MLLW_TO_NAVD88_OFFSET is Sandy Hook's and is
NOT changed; applying it to The Battery put that series 0.05 ft too low.
"""
STATIONS = {
    "8531680": {"name": "Sandy Hook", "mllw_station_ft": 2.51, "navd88_station_ft": 5.33},
    "8518750": {"name": "The Battery", "mllw_station_ft": 3.29, "navd88_station_ft": 6.06},
}
RECEIPTS = ["audits/2026-09-27-a1/05-noaa-8531680-datums.json",
            "audits/2026-09-27-a1/05-noaa-8518750-datums.json"]


def mllw_to_navd88_offset(station):
    """NAVD88 = MLLW + offset (negative here)."""
    d = STATIONS[str(station)]
    return round(d["mllw_station_ft"] - d["navd88_station_ft"], 3)
