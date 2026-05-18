"""Analyze 8 months of hourly rainfall at Highlands RABCH022 and identify rain events."""
import pandas as pd
from datetime import datetime, timedelta

# Load
df = pd.read_csv("rainfall_raw.csv")
df["dt"] = pd.to_datetime(df["Date"] + " " + df["Hour"], format="%m/%d/%y %H:%M")
df = df.sort_values("dt").reset_index(drop=True)
df["rain_1px"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)
df["rain_9px"] = pd.to_numeric(df["9pixAvg"], errors="coerce").fillna(0)

print(f"Coverage: {df['dt'].min()} to {df['dt'].max()}")
print(f"Total hours: {len(df)}")
print(f"Total rainfall (1px): {df['rain_1px'].sum():.2f} in")
print(f"Hours with any rain (>0.01\"): {(df['rain_1px']>0.01).sum()}")
print(f"Hours with heavy rain (>0.25\"): {(df['rain_1px']>0.25).sum()}")
print(f"Hours with very heavy rain (>0.5\"): {(df['rain_1px']>0.5).sum()}")
print(f"Max hourly: {df['rain_1px'].max():.2f} in at {df.loc[df['rain_1px'].idxmax(),'dt']}")

# Group rainy hours into events: cluster within 6 hours
RAIN_THRESHOLD = 0.05  # inches/hr to count as "rainy hour"
GAP_HOURS = 6  # hours of dryness to separate events

rainy = df[df["rain_1px"] > RAIN_THRESHOLD].copy()
print(f"\nRainy hours (>{RAIN_THRESHOLD}\"/hr): {len(rainy)}")

# Build events
events = []
if len(rainy) > 0:
    rainy = rainy.reset_index(drop=True)
    current_event = {"start": rainy.loc[0,"dt"], "end": rainy.loc[0,"dt"], "hours": [rainy.loc[0,"dt"]], "totals": [rainy.loc[0,"rain_1px"]]}
    for i in range(1, len(rainy)):
        t = rainy.loc[i,"dt"]
        v = rainy.loc[i,"rain_1px"]
        if t - current_event["end"] <= pd.Timedelta(hours=GAP_HOURS):
            current_event["end"] = t
            current_event["hours"].append(t)
            current_event["totals"].append(v)
        else:
            events.append(current_event)
            current_event = {"start": t, "end": t, "hours": [t], "totals": [v]}
    events.append(current_event)

# Build event summary table
event_rows = []
for e in events:
    total = sum(e["totals"])
    peak = max(e["totals"])
    peak_hour = e["hours"][e["totals"].index(peak)]
    duration_h = (e["end"] - e["start"]).total_seconds()/3600 + 1
    event_rows.append({
        "start": e["start"],
        "end": e["end"],
        "duration_h": duration_h,
        "total_in": round(total,2),
        "peak_hr_in": round(peak,2),
        "peak_hr_time": peak_hour,
    })
ev = pd.DataFrame(event_rows).sort_values("total_in", ascending=False).reset_index(drop=True)
print(f"\nTotal distinct rain events: {len(ev)}")
print(f"\nTop 20 events by total rainfall:")
print(ev.head(20).to_string(index=False))

# Cross-reference with user's known floods
user_floods = [
    ("2025-10-12", "2025-10-13", "flood",   "Nor'easter — town flooded per video, user not present"),
    ("2025-10-30", "2025-10-30", "flood",   "Compound rain+tide, ~1 ft on Bay Ave"),
    ("2026-02-22", "2026-02-23", "noflood", "Blizzard, regional underperformance"),
    ("2026-04-17", "2026-04-17", "flood",   "Tidal drain backup, light"),
    ("2026-04-18", "2026-04-18", "flood",   "Tidal+antecedent, moderate"),
]

print("\n\n=== Cross-reference with user-logged events ===")
for start_s, end_s, label, note in user_floods:
    start = pd.to_datetime(start_s)
    end = pd.to_datetime(end_s) + pd.Timedelta(days=1)
    date_str = start_s if start_s == end_s else f"{start_s} to {end_s}"
    window = df[(df["dt"]>=start) & (df["dt"]<end)]
    total = window["rain_1px"].sum()
    peak = window["rain_1px"].max()
    peak_t = window.loc[window["rain_1px"].idxmax(),"dt"] if peak>0 else None
    print(f"{date_str:20s} [{label}] tot={total:.2f}\" peak={peak:.2f}\"/hr"
          f" at {peak_t}" if peak_t is not None else f"{date_str:20s} [{label}] no rain")
    print(f"    note: {note}")

# Save event list
ev.to_csv("rain_events.csv", index=False)
print(f"\nSaved {len(ev)} events to rain_events.csv")
