"""Station-local time handling for Sandy Hook (seam 1 of the Phase-3
module split, extracted 2026-09-02 per forecast/README.md — no network
or file I/O; `flood_forecast_daily` re-exports every name so all
existing imports keep working).

NOAA CO-OPS transport uses ``time_zone=gmt``. Query boundaries are
converted from station time to UTC here, and returned timestamps are
converted to offset-bearing station-local ISO strings for storage. Human
formatters preserve ordinary local clock labels. This avoids the repeated
01:xx ambiguity at the fall-back transition (AGENTS.md rule 3).
"""
import datetime as dt
from zoneinfo import ZoneInfo

STATION_TZ = ZoneInfo("America/New_York")


def _station_local_now(now_utc=None):
    """Now in the Sandy Hook station's local timezone (naive).

    ``now_utc`` is an injection seam for boundary/DST tests.  Production
    callers omit it; tests can supply one aware instant and prove that every
    local-day decision is derived from the same clock.
    """
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(STATION_TZ).replace(tzinfo=None)


def _station_local_today(now_utc=None):
    """Station-local calendar date from the shared injectable clock."""
    return _station_local_now(now_utc).date()


def utc_to_station_local(value):
    """Parse an aware UTC/offset timestamp and convert it to station time."""
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC/offset timestamp must be timezone-aware")
    return parsed.astimezone(STATION_TZ)


def station_local_to_noaa_gmt(value):
    """Format a station-local instant as a NOAA GMT query boundary."""
    return parse_station_local_time(value).astimezone(
        dt.timezone.utc).strftime("%Y%m%d %H:%M")


def noaa_gmt_to_station_time(value):
    """Parse a naive NOAA GMT timestamp into aware station-local time."""
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    else:
        parsed = parsed.astimezone(dt.timezone.utc)
    return parsed.astimezone(STATION_TZ)


def noaa_gmt_to_station_string(value):
    """Return an unambiguous offset-bearing station-local ISO minute."""
    return noaa_gmt_to_station_time(value).isoformat(" ", timespec="minutes")


def station_time_storage_key(value):
    """Canonical offset-bearing key; accepts legacy naive local values."""
    return parse_station_local_time(value).isoformat(" ", timespec="minutes")


def station_time_sort_key(value):
    """Chronological UTC key for current or legacy station timestamps.

    Offset-bearing local ISO strings cannot be sorted lexically across the
    repeated fall-back hour: 01:00 EST sorts before 01:30 EDT even though it
    occurs later.
    """
    return parse_station_local_time(value).astimezone(dt.timezone.utc)


def station_times_match(left, right):
    """Whether two legacy/new station stamps identify the same instant."""
    try:
        a = parse_station_local_time(left).astimezone(dt.timezone.utc)
        b = parse_station_local_time(right).astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return False
    return a == b


def parse_station_local_time(value):
    """Parse an offset-bearing or legacy naive station-local timestamp.

    NOAA's local products omit an explicit UTC offset.  Attaching a fixed
    ``-04:00`` works only during daylight time, while relabeling a UTC clock
    with a local offset shifts lead times by four or five hours.  Keep this
    conversion in one place so every consumer gets EDT/EST handling from the
    IANA timezone database. New NOAA values carry an offset after the GMT
    transport migration. Legacy LST/LDT values remain readable; their
    repeated fall-back hour cannot be recovered, so fold=0 is the explicit
    historical interpretation.
    """
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=STATION_TZ, fold=0)
    return parsed.astimezone(STATION_TZ)


def hours_until_station_time(value, now_utc=None):
    """Signed hours from an aware UTC ``now`` to a station-local time."""
    target = parse_station_local_time(value).astimezone(dt.timezone.utc)
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    else:
        now = now.astimezone(dt.timezone.utc)
    return (target - now).total_seconds() / 3600.0
