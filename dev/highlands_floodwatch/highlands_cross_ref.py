"""Cross-reference rainfall, water level, and met data with labeled flood events."""
import pandas as pd
import numpy as np

# ============ Load water levels (GMT) ============
wl = pd.read_csv("wl.csv")
wl.columns = [c.strip() for c in wl.columns]
wl["dt_gmt"] = pd.to_datetime(wl["Date"] + " " + wl["Time (GMT)"])
wl["predicted"] = pd.to_numeric(wl["Predicted (ft)"], errors="coerce")
wl["verified"] = pd.to_numeric(wl["Verified (ft)"], errors="coerce")
wl["preliminary"] = pd.to_numeric(wl["Preliminary (ft)"], errors="coerce")
# Use verified where available, else preliminary
wl["observed"] = wl["verified"].fillna(wl["preliminary"])
wl["surge"] = wl["observed"] - wl["predicted"]

# Convert GMT → local NY time (DST-aware)
wl["dt_gmt"] = wl["dt_gmt"].dt.tz_localize("UTC")
wl["dt_local"] = wl["dt_gmt"].dt.tz_convert("America/New_York").dt.tz_localize(None)
print(f"WL rows: {len(wl)}, with observed: {wl['observed'].notna().sum()}")
print(f"WL coverage local: {wl['dt_local'].min()} to {wl['dt_local'].max()}")

# ============ Load meteorological (GMT) ============
met = pd.read_csv("met.csv")
met.columns = [c.strip() for c in met.columns]
met["dt_gmt"] = pd.to_datetime(met["Date"] + " " + met["Time (GMT)"])
met["wind_kn"] = pd.to_numeric(met["Wind Speed (kn)"], errors="coerce")
met["wind_gust_kn"] = pd.to_numeric(met["Wind Gust (kn)"], errors="coerce")
met["wind_dir_deg"] = pd.to_numeric(met["Wind Dir (deg)"], errors="coerce")
met["pressure_mb"] = pd.to_numeric(met["Baro (mb)"], errors="coerce")

# Wind decomposition. For Highlands, the most surge-favorable direction
# is from N/NNW (longest fetch over Sandy Hook Bay + Raritan Bay).
# Compute "onshore component" toward Highlands = -cos(dir - bearing_to_target)
# Bearing FROM water TO Highlands is ~150° SE → wind FROM NNW (330°) blows toward Highlands.
# So onshore component = cos(wind_dir - 330°) when wind_dir is the direction
# wind is FROM. Maximum when wind is from 330° (NNW).
met["wind_dir_rad"] = np.radians(met["wind_dir_deg"])
met["onshore_NNW"] = met["wind_kn"] * np.cos(np.radians(met["wind_dir_deg"] - 330))
# Also: wind from N (0°) component
met["wind_from_N"] = met["wind_kn"] * np.cos(np.radians(met["wind_dir_deg"]))

met["dt_gmt"] = met["dt_gmt"].dt.tz_localize("UTC")
met["dt_local"] = met["dt_gmt"].dt.tz_convert("America/New_York").dt.tz_localize(None)
print(f"MET rows: {len(met)}")

# ============ Rainfall (already local) ============
rain = pd.read_csv("rainfall_raw.csv")
rain["dt_local"] = pd.to_datetime(rain["Date"] + " " + rain["Hour"], format="%m/%d/%y %H:%M")
rain["rain_in"] = pd.to_numeric(rain["Value"], errors="coerce").fillna(0)

# ============ Merge by local hour ============
wl_h = wl[["dt_local","predicted","observed","surge"]].copy()
met_h = met[["dt_local","wind_kn","wind_gust_kn","wind_dir_deg","onshore_NNW","wind_from_N","pressure_mb"]].copy()
rain_h = rain[["dt_local","rain_in"]].copy()

# Floor to hour for merging
for d in (wl_h, met_h, rain_h):
    d["hour"] = d["dt_local"].dt.floor("h")
df = wl_h.merge(met_h, on="hour", how="outer", suffixes=("","_m"))
df = df.merge(rain_h, on="hour", how="outer")
df = df.sort_values("hour").reset_index(drop=True)
df = df[["hour","predicted","observed","surge","wind_kn","wind_gust_kn","wind_dir_deg","onshore_NNW","wind_from_N","pressure_mb","rain_in"]]
print(f"Merged rows: {len(df)}, with WL+wind: {df[['observed','wind_kn']].notna().all(axis=1).sum()}")
df.to_csv("merged_hourly.csv", index=False)

# ============ Cross-reference each labeled event ============
events = [
    ("2025-10-12 06:00", "2025-10-14 06:00", "flood",   "Oct 12-13 Nor'easter"),
    ("2025-10-30 06:00", "2025-10-31 00:00", "flood",   "Oct 30 compound"),
    ("2026-02-22 06:00", "2026-02-24 06:00", "noflood", "Feb 22-23 Blizzard"),
    ("2026-04-17 12:00", "2026-04-18 06:00", "flood",   "Apr 17 light"),
    ("2026-04-18 12:00", "2026-04-19 06:00", "flood",   "Apr 18 moderate"),
    # Unlabeled high-peak candidates
    ("2025-12-19 04:00", "2025-12-20 00:00", "?",        "Dec 19 0.44/hr peak"),
    ("2025-11-25 12:00", "2025-11-26 06:00", "?",        "Nov 25 0.37/hr peak"),
    ("2026-03-06 00:00", "2026-03-06 12:00", "?",        "Mar 6 0.39/hr peak"),
    ("2026-04-30 00:00", "2026-04-30 12:00", "?",        "Apr 30 0.28/hr peak"),
]
print("\n=== Event windows (local time) ===")
for s,e,label,note in events:
    w = df[(df["hour"]>=s) & (df["hour"]<e)].copy()
    if w["observed"].notna().any():
        peak_idx = w["observed"].idxmax()
        peak_tide = w.loc[peak_idx, "observed"]
        peak_pred = w.loc[peak_idx, "predicted"]
        peak_surge = w.loc[peak_idx, "surge"]
        peak_time = w.loc[peak_idx, "hour"]
    else:
        peak_idx = w["predicted"].idxmax()
        peak_tide = np.nan; peak_pred = w.loc[peak_idx,"predicted"]; peak_surge = np.nan
        peak_time = w.loc[peak_idx, "hour"]
    # rainfall in window
    rain_tot = w["rain_in"].sum()
    rain_peak = w["rain_in"].max()
    rain_peak_time = w.loc[w["rain_in"].idxmax(), "hour"] if rain_peak>0 else None
    # wind during window
    wind_max = w["wind_kn"].max() if w["wind_kn"].notna().any() else np.nan
    gust_max = w["wind_gust_kn"].max() if w["wind_gust_kn"].notna().any() else np.nan
    # mean wind direction weighted by speed
    valid = w.dropna(subset=["wind_kn","wind_dir_deg"])
    if len(valid)>0:
        u = (valid["wind_kn"] * np.sin(np.radians(valid["wind_dir_deg"]))).sum()
        v = (valid["wind_kn"] * np.cos(np.radians(valid["wind_dir_deg"]))).sum()
        mean_dir = (np.degrees(np.arctan2(u, v)) + 360) % 360
        onshore_peak = valid["onshore_NNW"].max()
    else:
        mean_dir = np.nan; onshore_peak = np.nan
    pres_min = w["pressure_mb"].min() if w["pressure_mb"].notna().any() else np.nan

    print(f"\n[{label:8s}] {note}")
    print(f"  Peak tide: obs={peak_tide:.2f}ft pred={peak_pred:.2f}ft surge={peak_surge:+.2f}ft at {peak_time}")
    print(f"  Rainfall: tot={rain_tot:.2f}\" peak={rain_peak:.2f}\"/hr"
          + (f" at {rain_peak_time}" if rain_peak_time else ""))
    print(f"  Wind: max={wind_max:.1f}kn gust={gust_max:.1f}kn mean_dir={mean_dir:.0f}° onshore_NNW_peak={onshore_peak:.1f}")
    print(f"  Min pressure: {pres_min:.1f} mb")

# ============ Specifically: Dec 19 7-11 AM tide check ============
print("\n\n=== Dec 19 0.44 in/hr rain — tide phase check ===")
dec19 = df[(df["hour"]>="2025-12-19 04:00") & (df["hour"]<"2025-12-19 14:00")]
print(dec19[["hour","predicted","observed","rain_in","wind_kn","wind_dir_deg"]].to_string(index=False))
