"""Station-local time handling for Sandy Hook (seam 1 of the Phase-3
module split, extracted 2026-09-02 per forecast/README.md — no network
or file I/O; `flood_forecast_daily` re-exports every name so all
existing imports keep working).

NOAA CO-OPS queries with time_zone=lst_ldt interpret begin_date /
end_date as STATION-LOCAL time (US/Eastern for Sandy Hook). Passing
UTC-now strings shifts the window +4/5 h — caught 2026-07-06 when
the widget chart's hour labels came out 4 h late. Use this module for
any begin/end sent to an lst_ldt query, and for every local-calendar
decision (AGENTS.md rule 3).
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


def parse_station_local_time(value):
    """Parse a NOAA ``lst_ldt`` timestamp as America/New_York.

    NOAA's local products omit an explicit UTC offset.  Attaching a fixed
    ``-04:00`` works only during daylight time, while relabeling a UTC clock
    with a local offset shifts lead times by four or five hours.  Keep this
    conversion in one place so every consumer gets EDT/EST handling from the
    IANA timezone database.
    """
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=STATION_TZ)
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
