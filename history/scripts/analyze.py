#!/usr/bin/env python3
"""
Analysis driver: produces the data behind every section of the report.

Loads sandy_hook_hourly_history.parquet and writes:
  - history/data/seasonality_by_threshold.csv     (3a)
  - history/data/return_periods.csv               (3b)
  - history/data/annual_means.csv                 (3c)
  - history/data/decadal_threshold_crossings.csv  (3c)
  - history/data/hour_of_day_peaks.csv            (3d)
  - history/data/doy_heatmap.csv                  (3d)
  - history/data/event_class_by_year.csv          (3e)
  - history/data/calibration_check.csv            (3f)
  - history/data/summary_stats.json               (one-page summary inputs)
  - figures/*.png

Run after build_dataset.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ----- model constants (must match build_dataset.py) -----
LOCAL_ENHANCEMENT_FT = 0.40
MLLW_TO_NAVD88 = -2.82
CURB_TOP = 4.16
ROAD_MIDDLE = 4.36
INTERSECTION = 4.54
LAWN_STEP = 4.58

THRESHOLDS_FT = {
    "6.58 (curb / flood onset)": 6.58,
    "7.00 (lawn)":               7.00,
    "7.20 (dashboard Minor)":    7.20,
    "7.70 (NWS Moderate)":       7.70,
    "8.70 (NWS Major)":          8.70,
}

DASHBOARD_MONTHLY_CSV = "data/raw/sandyhook_dashboard_monthly.csv"  # if present

# Hurricane Sandy peak at Sandy Hook (NOAA published max observed)
HURRICANE_SANDY_MLLW = 13.31
HURRICANE_SANDY_DATE = pd.Timestamp("2012-10-29")

# Labeled events (homeowner-observed) for calibration check
LABELED_EVENTS = [
    ("2025-10-30", "Compound rain+tide; ~12in at 342 Bay"),
    ("2025-12-19", "Confirmed by user video; tide+0.44/hr rain"),
    ("2026-04-17", "Light flood ~2in"),
    ("2026-04-18", "Moderate ~10in"),
]


# ============================================================
# helpers
# ============================================================

def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_hourly() -> pd.DataFrame:
    p = repo_root() / "data" / "sandy_hook_hourly_history.parquet"
    df = pd.read_parquet(p)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def detect_events_at(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Group contiguous above-threshold hours into events. Returns events frame."""
    s = df.dropna(subset=["observed_mllw"]).sort_values("timestamp").reset_index(drop=True)
    above = (s["observed_mllw"] >= threshold).to_numpy()
    if not above.any():
        return pd.DataFrame()
    starts = above & ~np.concatenate(([False], above[:-1]))
    event_id = np.where(above, starts.cumsum(), 0)
    s["event_id"] = event_id
    s = s[s["event_id"] > 0]
    g = s.groupby("event_id")
    return pd.DataFrame({
        "start":      g["timestamp"].min(),
        "end":        g["timestamp"].max(),
        "duration_h": g["timestamp"].count(),
        "peak_mllw":  g["observed_mllw"].max(),
    }).reset_index(drop=True)


# ============================================================
# 3a — Monthly seasonality
# ============================================================
def section_3a(df: pd.DataFrame, out: Path) -> pd.DataFrame:
    rows = []
    # Determine span in (year, month) pairs to scale by years observed per month
    df_y = df.dropna(subset=["observed_mllw"]).copy()
    df_y["ym"] = df_y["timestamp"].dt.to_period("M")
    # months in dataset where we have any data
    months_present = df_y["ym"].drop_duplicates()
    # for each calendar month, count the number of years it appears
    years_per_month = months_present.dt.month.value_counts().sort_index()

    for label, thresh in THRESHOLDS_FT.items():
        events = detect_events_at(df, thresh)
        if events.empty:
            for m in range(1, 13):
                rows.append({
                    "threshold_label": label, "threshold_ft": thresh, "month": m,
                    "avg_events_per_month": 0.0, "avg_hours_per_month": 0.0,
                    "max_peak_mllw": np.nan, "max_duration_h": 0,
                })
            continue
        events["month"] = events["start"].dt.month
        ev_by_m = events.groupby("month").agg(
            n_events=("peak_mllw", "size"),
            max_peak=("peak_mllw", "max"),
            max_duration=("duration_h", "max"),
        )
        # total hours above threshold by month using raw hourly count
        hours_above = (df_y[df_y["observed_mllw"] >= thresh]
                       .assign(m=lambda x: x["timestamp"].dt.month)
                       .groupby("m").size())
        for m in range(1, 13):
            yrs = max(int(years_per_month.get(m, 0)), 1)
            n_events = int(ev_by_m["n_events"].get(m, 0))
            tot_hours = int(hours_above.get(m, 0))
            rows.append({
                "threshold_label": label,
                "threshold_ft": thresh,
                "month": m,
                "years_observed": yrs,
                "avg_events_per_month": n_events / yrs,
                "avg_hours_per_month": tot_hours / yrs,
                "max_peak_mllw": float(ev_by_m["max_peak"].get(m, np.nan)),
                "max_duration_h": int(ev_by_m["max_duration"].get(m, 0)),
            })
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out / "seasonality_by_threshold.csv", index=False)

    # dashboard cross-check: read CSV from data/ folder (project)
    try:
        repo = Path(__file__).resolve().parent.parent.parent
        dash = pd.read_csv(repo / "data" / "floods_by_month.tsv", sep="\t")
        dash.to_csv(out / "dashboard_seasonality.csv", index=False)
    except FileNotFoundError:
        pass

    return out_df


# ============================================================
# 3b — Return periods via GEV fit on annual maxima
# ============================================================
def section_3b(df: pd.DataFrame, out: Path, figdir: Path) -> dict:
    df_y = df.dropna(subset=["observed_mllw"]).copy()
    ann_max = df_y.groupby(df_y["timestamp"].dt.year)["observed_mllw"].max()
    # Use years with reasonable coverage (>= 7000 hours = ~80% of year)
    hours_per_year = df_y.groupby(df_y["timestamp"].dt.year)["observed_mllw"].count()
    good_years = hours_per_year[hours_per_year >= 7000].index
    ann_max = ann_max.loc[good_years].sort_index()

    # Fit GEV (scipy: genextreme uses shape c = -xi in EVT convention)
    c, loc, scale = stats.genextreme.fit(ann_max.values)

    return_periods = [2, 5, 10, 25, 50, 100, 500]
    rl = stats.genextreme.ppf(1 - 1.0 / np.array(return_periods), c, loc=loc, scale=scale)

    # Convert return levels to depth at each landmark
    out_rows = []
    for T, level in zip(return_periods, rl):
        water_navd88 = level + LOCAL_ENHANCEMENT_FT + MLLW_TO_NAVD88
        out_rows.append({
            "return_period_yr": T,
            "return_level_mllw": float(level),
            "depth_at_curb_in":         max(0.0, water_navd88 - CURB_TOP) * 12,
            "depth_at_road_middle_in":  max(0.0, water_navd88 - ROAD_MIDDLE) * 12,
            "depth_at_intersection_in": max(0.0, water_navd88 - INTERSECTION) * 12,
            "depth_at_lawn_step_in":    max(0.0, water_navd88 - LAWN_STEP) * 12,
        })
    rp_df = pd.DataFrame(out_rows)
    rp_df.to_csv(out / "return_periods.csv", index=False)

    # Where does Hurricane Sandy sit?
    sandy_prob = 1 - stats.genextreme.cdf(HURRICANE_SANDY_MLLW, c, loc=loc, scale=scale)
    sandy_T = 1.0 / sandy_prob if sandy_prob > 0 else float("inf")

    # Bootstrap CI for return-level curve
    rng = np.random.default_rng(seed=42)
    n_boot = 500
    boot_rl = np.zeros((n_boot, len(return_periods)))
    for i in range(n_boot):
        sample = rng.choice(ann_max.values, size=len(ann_max), replace=True)
        try:
            cb, lb, sb = stats.genextreme.fit(sample)
            boot_rl[i, :] = stats.genextreme.ppf(1 - 1 / np.array(return_periods), cb, loc=lb, scale=sb)
        except Exception:
            boot_rl[i, :] = np.nan
    ci_lo = np.nanpercentile(boot_rl, 2.5, axis=0)
    ci_hi = np.nanpercentile(boot_rl, 97.5, axis=0)

    # Plot
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    # empirical Weibull plotting positions
    sorted_max = np.sort(ann_max.values)
    n = len(sorted_max)
    emp_T = (n + 1) / (n - np.arange(n))
    ax.scatter(emp_T, sorted_max, s=22, color="#1f6feb", label="annual maxima (empirical)")
    Tgrid = np.logspace(np.log10(1.05), np.log10(500), 200)
    grid_rl = stats.genextreme.ppf(1 - 1 / Tgrid, c, loc=loc, scale=scale)
    ax.plot(Tgrid, grid_rl, color="#0b1f3a", lw=2, label="GEV fit")
    # bootstrap envelope at the chosen return periods
    ax.fill_between(return_periods, ci_lo, ci_hi, color="#1f6feb", alpha=0.18,
                    label="95% CI (bootstrap)")
    # Hurricane Sandy
    ax.axhline(HURRICANE_SANDY_MLLW, color="#d2444a", lw=1, ls=":",
               label=f"Hurricane Sandy 2012 ({HURRICANE_SANDY_MLLW} ft)")
    # Landmark thresholds
    for label, sh in [("curb 6.58", 6.58), ("road 6.78", 6.78), ("lawn 7.00", 7.00)]:
        ax.axhline(sh, color="#444", lw=0.7, alpha=0.5)
        ax.text(450, sh + 0.05, label, fontsize=8, ha="right", color="#444")
    ax.set_xscale("log")
    ax.set_xlim(1, 500)
    ax.set_xlabel("Return period (years)")
    ax.set_ylabel("Annual maximum water level (ft MLLW, Sandy Hook)")
    ax.set_title(f"Return-level curve — Sandy Hook annual maxima ({ann_max.index.min()}–{ann_max.index.max()})")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(figdir / "3b_return_periods.png", dpi=130)
    plt.close(fig)

    return {
        "n_years": int(len(ann_max)),
        "year_min": int(ann_max.index.min()),
        "year_max": int(ann_max.index.max()),
        "gev_shape": float(c),
        "gev_loc": float(loc),
        "gev_scale": float(scale),
        "return_levels": [
            {"T": T, "level_mllw": float(L), "ci_lo": float(lo), "ci_hi": float(hi)}
            for T, L, lo, hi in zip(return_periods, rl, ci_lo, ci_hi)
        ],
        "hurricane_sandy_level": HURRICANE_SANDY_MLLW,
        "hurricane_sandy_return_yr": float(sandy_T),
    }


# ============================================================
# 3c — Sea level rise
# ============================================================
def section_3c(df: pd.DataFrame, out: Path, figdir: Path) -> dict:
    df_y = df.dropna(subset=["observed_mllw"]).copy()
    df_y["year"] = df_y["timestamp"].dt.year
    hours = df_y.groupby("year")["observed_mllw"].count()
    good = hours[hours >= 7000].index
    ann_mean = df_y[df_y["year"].isin(good)].groupby("year")["observed_mllw"].mean()

    yrs = ann_mean.index.values.astype(float)
    vals = ann_mean.values
    slope, intercept, r, p, se = stats.linregress(yrs, vals)
    mm_per_yr = slope * 304.8  # ft -> mm
    ft_per_century = slope * 100

    # Trend by window — captures acceleration
    trend_rows = []
    for a, b, label in [(1910, 2025, "full record"),
                        (1932, 2024, "NOAA published window"),
                        (1950, 2025, "post-1950"),
                        (1980, 2025, "post-1980 (accelerated era)")]:
        sub = ann_mean[(ann_mean.index >= a) & (ann_mean.index <= b)]
        if len(sub) < 5:
            continue
        s, _, r2, p2, _ = stats.linregress(sub.index.astype(float), sub.values)
        trend_rows.append({
            "window": label,
            "year_min": a, "year_max": b,
            "mm_per_year": s * 304.8,
            "ft_per_century": s * 100,
            "r2": r2 ** 2,
            "n_years": len(sub),
        })
    pd.DataFrame(trend_rows).to_csv(out / "slr_trend_by_window.csv", index=False)

    ann_mean.to_csv(out / "annual_means.csv", header=["mean_mllw"])

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(yrs, vals, "o-", ms=3, lw=0.8, color="#1f6feb", alpha=0.85)
    ax.plot(yrs, slope * yrs + intercept, color="#d2444a", lw=2,
            label=f"trend {mm_per_yr:.2f} mm/yr ({ft_per_century:.2f} ft/century)")
    ax.set_xlabel("Year"); ax.set_ylabel("Annual mean water level (ft MLLW)")
    ax.set_title("Sandy Hook annual mean sea level")
    ax.grid(True, alpha=0.25); ax.legend()
    fig.tight_layout(); fig.savefig(figdir / "3c_annual_mean.png", dpi=130); plt.close(fig)

    # Decadal threshold-crossings
    decade_rows = []
    for label, thresh in THRESHOLDS_FT.items():
        events = detect_events_at(df, thresh)
        if events.empty:
            continue
        events["decade"] = (events["start"].dt.year // 10) * 10
        cnt = events.groupby("decade").size()
        for decade, n in cnt.items():
            # how many years of coverage in that decade?
            ds = df_y[(df_y["year"] >= decade) & (df_y["year"] < decade + 10)]
            yrs_in_decade = ds["year"].nunique()
            decade_rows.append({
                "threshold_label": label,
                "threshold_ft": thresh,
                "decade": int(decade),
                "events": int(n),
                "years_observed": int(yrs_in_decade),
                "events_per_year": n / max(yrs_in_decade, 1),
            })
    dec_df = pd.DataFrame(decade_rows)
    dec_df.to_csv(out / "decadal_threshold_crossings.csv", index=False)

    # Plot the 6.58 ft (curb) threshold crossings per decade
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for label, thresh in THRESHOLDS_FT.items():
        sub = dec_df[dec_df["threshold_ft"] == thresh].sort_values("decade")
        if sub.empty:
            continue
        ax.plot(sub["decade"], sub["events_per_year"], "o-", ms=5, lw=1.5,
                label=f"{thresh} ft")
    ax.set_xlabel("Decade")
    ax.set_ylabel("Flood events per year (decadal average)")
    ax.set_title("Threshold-crossing frequency at 342 Bay landmarks, by decade")
    ax.grid(True, alpha=0.25); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(figdir / "3c_decadal_crossings.png", dpi=130); plt.close(fig)

    return {
        "mm_per_year": float(mm_per_yr),
        "ft_per_century": float(ft_per_century),
        "regression_p": float(p),
        "regression_r2": float(r ** 2),
        "year_min": int(yrs.min()),
        "year_max": int(yrs.max()),
        "n_years": int(len(yrs)),
    }


# ============================================================
# 3d — Hour-of-day and day-of-year patterns
# ============================================================
def section_3d(df: pd.DataFrame, out: Path, figdir: Path) -> None:
    threshold = 6.58
    events = detect_events_at(df, threshold)
    if events.empty:
        return
    # peak-hour distribution: find the row inside each event where observed_mllw is max
    df_t = df.dropna(subset=["observed_mllw"]).copy()
    df_t["above"] = df_t["observed_mllw"] >= threshold
    df_t = df_t.sort_values("timestamp").reset_index(drop=True)
    above = df_t["above"].to_numpy()
    starts = above & ~np.concatenate(([False], above[:-1]))
    df_t["event_id"] = np.where(above, starts.cumsum(), 0)
    in_event = df_t[df_t["event_id"] > 0]
    peaks = in_event.loc[in_event.groupby("event_id")["observed_mllw"].idxmax()]
    hod = peaks["timestamp"].dt.hour.value_counts().reindex(range(24), fill_value=0).sort_index()
    hod.to_csv(out / "hour_of_day_peaks.csv", header=["events_peaking"])

    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.bar(hod.index, hod.values, color="#1f6feb")
    ax.set_xlabel("Hour of day (local, lst_ldt)"); ax.set_ylabel("# events peaking")
    ax.set_title(f"Hour-of-day distribution of event peaks (threshold {threshold} ft MLLW)")
    ax.set_xticks(range(0, 24, 2)); ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(figdir / "3d_hour_of_day.png", dpi=130); plt.close(fig)

    # Day-of-year heat map (week-of-year x flood-count)
    peaks["week"] = peaks["timestamp"].dt.isocalendar().week.astype(int)
    peaks["year"] = peaks["timestamp"].dt.year
    n_years = peaks["year"].nunique()
    weekly = peaks["week"].value_counts().reindex(range(1, 54), fill_value=0).sort_index()
    weekly_per_yr = weekly / max(n_years, 1)
    weekly_per_yr.to_csv(out / "doy_heatmap.csv", header=["events_per_year"])

    fig, ax = plt.subplots(figsize=(9.5, 3.2))
    ax.bar(weekly_per_yr.index, weekly_per_yr.values, color="#0b1f3a")
    ax.set_xlabel("ISO week of year"); ax.set_ylabel("avg events / yr")
    ax.set_title(f"When in the year do floods cluster? (threshold {threshold} ft MLLW)")
    ax.set_xlim(0.5, 53.5); ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(figdir / "3d_week_of_year.png", dpi=130); plt.close(fig)


# ============================================================
# 3e — Storm vs nuisance events
# ============================================================
def section_3e(df: pd.DataFrame, out: Path, figdir: Path) -> dict:
    events = detect_events_at(df, 6.58)
    if events.empty:
        return {}
    def classify(row):
        if row["peak_mllw"] >= 8.5 or row["duration_h"] >= 12:
            return "storm"
        if row["peak_mllw"] < 7.5 and row["duration_h"] < 6:
            return "nuisance"
        return "middle"
    events["class"] = events.apply(classify, axis=1)
    events["year"] = events["start"].dt.year
    by_year = events.groupby(["year", "class"]).size().unstack(fill_value=0)
    for c in ["nuisance", "middle", "storm"]:
        if c not in by_year.columns:
            by_year[c] = 0
    by_year = by_year[["nuisance", "middle", "storm"]]
    by_year.to_csv(out / "event_class_by_year.csv")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    by_year.plot(kind="bar", stacked=True, ax=ax,
                 color=["#a6c8ff", "#1f6feb", "#0b1f3a"], width=0.95)
    ax.set_xlabel("Year"); ax.set_ylabel("Number of events")
    ax.set_title("Flood events per year at 342 Bay (curb threshold 6.58 ft MLLW)")
    # thin x labels
    xt = ax.get_xticks()
    yrs_all = by_year.index.tolist()
    keep = [i for i, y in enumerate(yrs_all) if y % 10 == 0]
    ax.set_xticks([xt[i] for i in keep]); ax.set_xticklabels([yrs_all[i] for i in keep])
    ax.legend(fontsize=9); ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(figdir / "3e_event_classes.png", dpi=130); plt.close(fig)

    # ratio over time
    by_year["total"] = by_year.sum(axis=1)
    return {
        "total_events": int(by_year["total"].sum()),
        "total_nuisance": int(by_year["nuisance"].sum()),
        "total_storm": int(by_year["storm"].sum()),
        "year_min": int(by_year.index.min()),
        "year_max": int(by_year.index.max()),
    }


# ============================================================
# 3f — Calibration check on observed events + recent audit
# ============================================================
def section_3f(df: pd.DataFrame, out: Path) -> dict:
    rows = []
    for date_str, note in LABELED_EVENTS:
        d0 = pd.Timestamp(date_str)
        sub = df[(df["timestamp"] >= d0) & (df["timestamp"] < d0 + pd.Timedelta(days=1))]
        if sub.empty:
            rows.append({"date": date_str, "note": note,
                         "peak_obs_mllw": np.nan, "peak_pred_mllw": np.nan,
                         "peak_surge_ft": np.nan, "peak_hour": np.nan})
            continue
        idx = sub["observed_mllw"].idxmax()
        row = sub.loc[idx]
        rows.append({
            "date": date_str,
            "note": note,
            "peak_obs_mllw":  float(row["observed_mllw"]),
            "peak_pred_mllw": float(row["predicted_mllw"]),
            "peak_surge_ft":  float(row["surge_ft"]),
            "peak_hour":      int(row["timestamp"].hour),
            "max_depth_curb_in":         float(sub["depth_at_curb_in"].max()),
            "max_depth_road_in":         float(sub["depth_at_road_middle_in"].max()),
            "max_depth_intersection_in": float(sub["depth_at_intersection_in"].max()),
            "max_depth_lawn_in":         float(sub["depth_at_lawn_step_in"].max()),
        })
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out / "calibration_check.csv", index=False)

    # Sep 1 2025 -- May 17 2026 audit (hours above 6.58 ft)
    win_start = pd.Timestamp("2025-09-01")
    win_end = pd.Timestamp("2026-05-17 23:59:59")
    win = df[(df["timestamp"] >= win_start) & (df["timestamp"] <= win_end)]
    hours_above = int((win["observed_mllw"] >= 6.58).sum())
    events_window = detect_events_at(win, 6.58)
    return {
        "window_start": str(win_start.date()),
        "window_end": str(win_end.date()),
        "hours_above_6.58": hours_above,
        "events_in_window": int(len(events_window)),
        "peak_in_window_mllw": float(win["observed_mllw"].max()) if not win.empty else None,
    }


# ============================================================
# main
# ============================================================
def main():
    repo = repo_root()
    out = repo / "data"; out.mkdir(exist_ok=True)
    figdir = repo / "figures"; figdir.mkdir(exist_ok=True)

    df = load_hourly()
    print(f"hourly rows: {len(df):,}", flush=True)

    print("3a monthly seasonality...", flush=True)
    s3a = section_3a(df, out)

    print("3b GEV return periods...", flush=True)
    s3b = section_3b(df, out, figdir)

    print("3c sea level rise...", flush=True)
    s3c = section_3c(df, out, figdir)

    print("3d hour/day patterns...", flush=True)
    section_3d(df, out, figdir)

    print("3e storm vs nuisance...", flush=True)
    s3e = section_3e(df, out, figdir)

    print("3f calibration check...", flush=True)
    s3f = section_3f(df, out)

    # also useful: how many days per year does 342 Bay flood (any depth at curb)?
    df_h = df.dropna(subset=["observed_mllw"]).copy()
    df_h["year"] = df_h["timestamp"].dt.year
    df_h["date"] = df_h["timestamp"].dt.date
    hours_per_yr = df_h.groupby("year")["observed_mllw"].count()
    good = hours_per_yr[hours_per_yr >= 7000].index
    df_h = df_h[df_h["year"].isin(good)]
    flood_hours = df_h[df_h["observed_mllw"] >= 6.58]
    days_per_year = flood_hours.groupby("year")["date"].nunique()
    days_per_year.to_csv(out / "flood_days_per_year.csv", header=["flood_days"])

    # Recent-window stratified seasonality (1996-2025) for forecast-email
    # context. Five strata so the user can see severity, not just a single
    # "flood day" count that conflates barely-overflowing curb with porch
    # underwater. Thresholds correspond to 342 Bay landmarks.
    recent = df_h[df_h["year"].between(1996, 2025)].copy()
    n_years_recent = recent["year"].nunique()

    # Stratification thresholds and landmark labels (in ascending order
    # of severity). Sandy Hook MLLW = landmark NAVD88 + 2.42 ft.
    strata = [
        ("curb",          "Curb at walkway",          6.58),
        ("road_middle",   "Bay Ave road middle",      6.78),
        ("intersection",  "Intersection center",      6.96),
        ("lawn_step",     "Lawn / walkway step",      7.00),
        ("porch_step",    "Front porch first step",   7.50),
    ]
    rows = []
    for key, label, thresh in strata:
        events_t = detect_events_at(recent, thresh)
        if not events_t.empty:
            events_t["month"] = events_t["start"].dt.month
        for m in range(1, 13):
            n_ev = 0 if events_t.empty else int((events_t["month"] == m).sum())
            mask = (recent["month"] == m) & (recent["observed_mllw"] >= thresh)
            flood_days_in_m = recent[mask].groupby("date").size().shape[0]
            flood_hours_in_m = int(mask.sum())
            rows.append({
                "landmark_key": key,
                "landmark_label": label,
                "threshold_ft": thresh,
                "month": m,
                "avg_events_per_month": n_ev / max(n_years_recent, 1),
                "avg_flood_days_per_month": flood_days_in_m / max(n_years_recent, 1),
                "avg_flood_hours_per_month": flood_hours_in_m / max(n_years_recent, 1),
            })
    rec_df = pd.DataFrame(rows)
    # Per-stratum descriptor: wettest, quietest, above-avg, below-avg
    # If all months tie at 0 (extreme threshold barely ever hit in some
    # strata), descriptors are empty strings.
    descriptors = []
    for key, label, thresh in strata:
        sub = rec_df[rec_df["threshold_ft"] == thresh].sort_values("month")
        days = sub["avg_flood_days_per_month"].values
        if days.max() == 0:
            descriptors.extend([""] * 12)
            continue
        mean_v = days.mean()
        wettest_m = int(sub.iloc[int(days.argmax())]["month"])
        quietest_m = int(sub.iloc[int(days.argmin())]["month"])
        for _, r in sub.iterrows():
            m = int(r["month"])
            if m == wettest_m:
                descriptors.append("wettest month")
            elif m == quietest_m and r["avg_flood_days_per_month"] < mean_v:
                descriptors.append("quietest month")
            elif r["avg_flood_days_per_month"] >= mean_v:
                descriptors.append("above-average")
            else:
                descriptors.append("below-average")
    rec_df["descriptor"] = descriptors
    rec_df["window"] = f"1996-2025 ({n_years_recent} yrs)"
    # Sort: month ascending, then by severity ascending
    rec_df = rec_df.sort_values(["month", "threshold_ft"]).reset_index(drop=True)
    rec_df.to_csv(out / "seasonality_recent.csv", index=False)

    summary = {
        "rows": int(len(df)),
        "span_min": str(df["timestamp"].min()),
        "span_max": str(df["timestamp"].max()),
        "flood_days_per_year_mean_all": float(days_per_year.mean()),
        "flood_days_per_year_recent": float(days_per_year.tail(10).mean()),
        "flood_days_per_year_earliest": float(days_per_year.head(10).mean()),
        "3b": s3b,
        "3c": s3c,
        "3e": s3e,
        "3f": s3f,
    }
    with open(out / "summary_stats.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print("done. summary written to summary_stats.json", flush=True)


if __name__ == "__main__":
    main()
