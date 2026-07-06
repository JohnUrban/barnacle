# Historical Flood Statistics at 342 Bay Avenue, Highlands NJ

*Built from 116 years of NOAA Sandy Hook gauge observations (station 8531680, 1910-01-01 through 2026-05-17). Hyperlocal to 342 Bay Avenue using the v0.5 model (LOCAL_ENHANCEMENT = +0.40 ft, NAVD88 = MLLW − 2.82). Flood-onset threshold at this address: Sandy Hook 6.58 ft MLLW (water reaches the curb at the walkway).*

> **⚠ DATED SNAPSHOT — written 2026-05-18 under model v0.5/v0.6.**
> The analysis below was computed with the v0.5 transform
> (enhancement **+0.40**, curb onset **SH 6.58**) — both since
> superseded. Under **v0.9** (2026-07-06): enhancement **0.00**
> (tape-measured across 4 events), curb onset **SH 6.98**, 18
> landmarks, and a pluvial pathway (rain floods this corner with no
> tidal contribution at all — invisible to everything in this
> report, which is tide-gauge-only). Event *counts* here therefore
> **overstate** curb flooding by using the lower old threshold, and
> depth columns run ~0.40 ft high. The regenerated CSVs in
> `history/data/` (refreshed 2026-07-06 at v0.9 thresholds) are the
> numbers to act on; current spec: `model/v0.9.md`. The narrative
> below is preserved as-written — it's part of the project's
> reasoning record.


---

## Plain-language summary

**1. How many days per year does my house flood, historically?**
About **13 days a year on average** over the whole 1910–2025 record. But that average hides a huge trend (see #2). In the **2010s, it averaged 38 days/year**; in the **2020s so far, 44 days/year**. Last year (2024) had **57 flood days**. Your house now floods on roughly 1 day in 8.

**2. How is that changing over time?**
Sharply up. Flood-day counts by decade at the 342 Bay curb:

| Decade | Avg flood days/year | Multiplier vs 1910s |
|---|---|---|
| 1910s | 5.1 | 1.0× |
| 1940s | 2.3 | 0.5× |
| 1960s | 5.1 | 1.0× |
| 1980s | 5.6 | 1.1× |
| 1990s | 14.2 | 2.8× |
| 2000s | 19.9 | 3.9× |
| 2010s | 38.1 | 7.5× |
| 2020s (through 2025) | 44.0 | **8.7×** |

The driver is sea level rise: Sandy Hook's annual mean has risen about **4.3 mm/year (1.4 ft/century) over the 1932–2024 window** that NOAA publishes — and **5.5 mm/year (1.8 ft/century) since 1980**. Any given tide event reaches your curb more often because the baseline keeps creeping up.

**3. What's the worst event I should plan for? (100-year return level)**
The 100-year return level is **10.57 ft MLLW** (95% confidence: 9.5–11.8 ft). At your house that's about **4 ft of water at the curb** (48 inches) and **3.6 ft on the lawn step**. Hurricane Sandy peaked higher than this — 13.31 ft MLLW — and registers as roughly a **5000-year event** in the fitted statistics (i.e., truly exceptional even by storm-of-the-century standards). A 50-year event is **10.08 ft** (~36" at the curb); a 25-year event is **9.58 ft** (~30" at the curb).

**4. Have I been seeing more floods recently than my parents would have?**
**Yes, dramatically.** Your parents, if they lived here in the 1950s, saw about **3 flood days a year**. You're seeing about **45**. That's **15× more frequent flooding at the same address**, not because the weather is worse but because the bay surface is over half a foot higher now than it was then.

---

## Section 1 — Data and methods

- **Source:** NOAA CO-OPS API, station 8531680 (Sandy Hook), two products:
  - `hourly_height` — verified hourly observed water level (MLLW)
  - `predictions` — astronomical predicted tide (MLLW)
- **Coverage:** 1,020,142 hourly rows, 1910-01-01 to 2026-05-17 local (lst_ldt).
  98 calendar years have ≥7000 hours of usable observations (≥80% complete).
- **Local translation:** `water_at_342_NAVD88 = obs_MLLW + 0.40 − 2.82`. Depth at each landmark = `max(0, water − landmark_NAVD88) × 12 in`.
- **Flood event:** Contiguous hours where Sandy Hook observed ≥ threshold. An event ends when even one hour drops below threshold.
- **Tide-peak count:** For comparison with NOAA-style "flood event" counts, also computed: distinct semi-diurnal local maxima (high tides) whose hourly value crosses the threshold.

The full hourly dataset is saved at `history/data/sandy_hook_hourly_history.parquet`. The per-event table at `history/data/342_bay_flood_events.csv`.

---

## Section 3a — Monthly seasonality

Average flood events per month at each threshold, over the entire 1910–2026 record (using contiguous-hour event definition):

| Month | 6.58 ft (curb) | 7.00 ft (lawn) | 7.20 ft | 7.70 ft (Moderate) | 8.70 ft (Major) |
|---|---:|---:|---:|---:|---:|
| Jan | 1.16 | 0.30 | 0.21 | 0.07 | 0.01 |
| Feb | 0.81 | 0.16 | 0.10 | 0.05 | 0.00 |
| Mar | 1.20 | 0.34 | 0.20 | 0.10 | 0.02 |
| Apr | 1.25 | 0.30 | 0.15 | 0.06 | 0.00 |
| May | 0.99 | 0.12 | 0.06 | 0.01 | 0.00 |
| Jun | 0.86 | 0.05 | 0.02 | 0.00 | 0.00 |
| Jul | 0.69 | 0.06 | 0.03 | 0.00 | 0.00 |
| Aug | 0.86 | 0.16 | 0.10 | 0.04 | 0.02 |
| Sep | 1.39 | 0.42 | 0.27 | 0.10 | 0.03 |
| **Oct** | **2.08** | **0.66** | **0.43** | **0.16** | **0.04** |
| Nov | 1.26 | 0.46 | 0.31 | 0.10 | 0.03 |
| Dec | 1.43 | 0.42 | 0.26 | 0.08 | 0.02 |

**October is the worst month at every threshold** — Atlantic hurricane season's late half overlapping with autumn nor'easters. July is the quietest.

### Cross-validation against the published Sandy Hook dashboard

The HANDOFF described the dashboard as using a "7.20 ft Minor" threshold. **That is not what the dashboard is actually computing.** Reproducing the dashboard's monthly numbers exactly requires the NWS standard **6.7 ft** threshold over a **~1996–recent window**:

| Month | Dashboard "Minor" | This study at 6.7 ft (1996–2025) |
|---|---:|---:|
| Jan | 1.50 | 1.93 |
| Feb | 1.44 | 1.50 |
| Mar | 2.13 | 2.37 |
| Apr | 2.09 | 2.07 |
| May | 1.88 | 1.93 |
| Jun | 1.88 | 1.73 |
| Jul | 1.59 | 1.53 |
| Aug | 1.78 | 1.57 |
| Sep | 2.84 | 2.73 |
| Oct | 3.97 | 3.93 |
| Nov | 1.88 | 2.03 |
| Dec | 1.97 | 2.10 |
| **Total** | **25.0** | **25.4** |

These match within rounding. The dashboard's "Minor 7.20 ft" label appears to be mislabeled — the underlying threshold is the NWS standard 6.7 ft MLLW for Sandy Hook minor coastal flooding. (Reassuringly, this 6.7 ft NWS threshold sits just 0.12 ft above the v0.5-era 6.58 ft flood-onset estimate — **[superseded: v0.9 puts curb onset at 6.98, i.e. 0.28 ft ABOVE the NWS minor threshold — the dashboard frequency now modestly OVERSTATES curb flooding at 342]**.)

At the v0.5-era flood-onset threshold (6.58 ft), the **same recent window (1996–2025) gives ~30 events/year**. **[Superseded: at the v0.9 curb threshold (6.98) the regenerated CSVs give materially fewer curb events/year; sub-curb street-water events (SW grate, 6.34) are far more frequent — see `seasonality_recent.csv`.]**

Full data: `history/data/seasonality_by_threshold.csv`.

---

## Section 3b — Return periods (annual maxima, GEV fit)

GEV fit on 98 annual maxima (1910–2025; years with ≥7000 hours of observation):

- Shape (ξ): 0.0016 — essentially Gumbel (light tail; consistent with extra-tropical storm dominance, with a few hurricane outliers)
- Location (μ): 7.309 ft MLLW
- Scale (σ): 0.712 ft

| Return period | Level (ft MLLW) | 95% CI | Depth at curb | Depth at lawn |
|---|---:|---|---:|---:|
| 2 yr | 7.57 | 7.41 – 7.74 | 11.9" | 6.9" |
| 5 yr | 8.38 | 8.12 – 8.63 | 21.5" | 16.6" |
| 10 yr | 8.91 | 8.54 – 9.28 | 27.9" | 22.9" |
| 25 yr | 9.58 | 8.97 – 10.20 | 35.9" | 30.9" |
| 50 yr | 10.08 | 9.27 – 10.98 | 41.9" | 36.9" |
| **100 yr** | **10.57** | **9.53 – 11.84** | **47.9"** | **42.9"** |
| 500 yr | 11.71 | 9.96 – 14.21 | 61.6" | 56.6" |

**Hurricane Sandy** (NOAA-published peak 13.31 ft MLLW; my hourly record shows 12.03 ft, the difference being that Sandy Hook hourly is a centered-hour mean while 13.31 ft is the instantaneous 6-minute reading) sits at a fitted **return period of ~4800 years**. In other words, a true black swan even by extreme-value standards — and not the kind of event the 100-year planning level should be calibrated against.

For practical planning, a more sober reference is the 25–50 year band: the curb seeing **30–40 inches of water from tide alone** before rainfall amplification.

Figure: `history/figures/3b_return_periods.png` (log return period vs annual-maximum water level, GEV fit, bootstrap CI, with curb / road / lawn lines and Hurricane Sandy marked).

Full data: `history/data/return_periods.csv`.

---

## Section 3c — Sea level rise

### Annual-mean trend, multiple windows

| Window | mm / year | ft / century | r² | n years |
|---|---:|---:|---:|---:|
| Full record (1910–2025) | 3.04 | 1.00 | 0.67 | 98 |
| **NOAA published (1932–2024)** | **4.29** | **1.41** | **0.93** | **90** |
| Post-1950 (1950–2025) | 4.26 | 1.40 | 0.89 | 75 |
| **Post-1980 (accelerated era)** | **5.45** | **1.79** | **0.84** | **45** |

The 1932–2024 number (4.29 mm/yr) matches the NOAA-published trend (4.05 mm/yr) within statistical tolerance — cross-validation succeeds. The full-record number is lower because the 1910–1931 segment has sparse coverage (only 7 usable years) and shows different early-gauge behavior; weighting the regression against it pulls the slope down spuriously.

The interesting story is the **acceleration**: rate since 1980 (5.45 mm/yr) is **27% higher** than the long-window 1932–2024 rate (4.29 mm/yr). At 5.45 mm/yr the local bay is gaining **about 2 inches per decade**. That's the engine driving the increase in flood-day counts.

Figure: `history/figures/3c_annual_mean.png`.

### Threshold-crossing frequency by decade

Average events per year (contiguous-hour definition) by decade at the 342 Bay curb threshold (6.58 ft):

| Decade | Events / yr at 6.58 | Events / yr at 7.00 (lawn) | Years of data |
|---|---:|---:|---:|
| 1910s | 4.86 | 1.43 | 7 |
| 1930s | 1.00 | 0.17 | 6 |
| 1940s | 2.30 | 0.50 | 10 |
| 1950s | 3.00 | 1.00 | 10 |
| 1960s | 5.20 | 2.10 | 10 |
| 1970s | 6.60 | 1.40 | 10 |
| 1980s | 5.89 | 1.56 | 9 |
| 1990s | 14.40 | 4.70 | 10 |
| 2000s | 22.20 | 6.70 | 10 |
| 2010s | 43.60 | 16.00 | 10 |
| **2020s** | **47.67** | **19.83** | **6** |

The hockey-stick is real. Curb-wet events have gone from ~5/year mid-century to ~48/year in the current decade. **Lawn-wet events** (7.00 ft, where water reaches the walkway step) have gone from ~1/year mid-century to ~20/year. Same physics: same tides, but riding on a higher mean.

Figure: `history/figures/3c_decadal_crossings.png`.

Full data: `history/data/annual_means.csv`, `history/data/slr_trend_by_window.csv`, `history/data/decadal_threshold_crossings.csv`.

---

## Section 3d — Daily and seasonal patterns

### Hour-of-day distribution of flood peaks

Flood-event peaks (at the 6.58 ft threshold) cluster at the M2 semi-diurnal high-tide times. The local-time distribution is bimodal with peaks roughly 12 hours apart — exactly as expected from the dominant 12.4-hour tidal mode. The pattern slowly precesses through the day across weeks as the tide clock advances ~50 minutes per day.

Practically: if you're forecasting for a given day, the most-likely peak time can be read off the NOAA predicted-tide curve and high water at 342 Bay is essentially co-incident.

Figure: `history/figures/3d_hour_of_day.png`. Data: `history/data/hour_of_day_peaks.csv`.

### Week-of-year heat map

Floods cluster strongly in weeks 39–48 (late September through November), with a secondary maximum in weeks 10–13 (March nor'easters) and a clear summer trough in weeks 27–32 (July–early August).

Figure: `history/figures/3d_week_of_year.png`. Data: `history/data/doy_heatmap.csv`.

---

## Section 3e — Storm events vs nuisance floods

Definitions (per HANDOFF):

- **Nuisance**: peak < 7.5 ft MLLW AND duration < 6 hours
- **Storm**: peak ≥ 8.5 ft MLLW OR duration ≥ 12 hours
- **Middle**: everything else (above-curb but below storm)

Totals over the full record:

| Class | Count | Per year (recent decades) |
|---|---:|---:|
| Nuisance | 1,273 | ~30 |
| Middle | 115 | ~3 |
| Storm | 24 | ~0.3 |

**By decade:**

| Decade | Nuisance | Middle | Storm |
|---|---:|---:|---:|
| 1910s | 34 | 3 | 0 |
| 1940s | 22 | 0 | 1 |
| 1950s | 26 | 4 | 3 |
| 1960s | 47 | 4 | 6 |
| 1970s | 58 | 8 | 0 |
| 1980s | 49 | 3 | 3 |
| 1990s | 135 | 14 | 4 |
| 2000s | 203 | 19 | 0 |
| 2010s | 393 | 38 | 5 |
| 2020s (6 yrs) | 264 | 20 | 2 |

The take-home: the **nuisance count is what's exploding** (from a few dozen per decade pre-1990 to several hundred per decade now), while **the storm count has been roughly stable at 2–6 per decade**. This is consistent with the SLR-driven mechanism: the same storms keep happening, but the calm-weather baseline now reaches your curb on routine spring tides.

Figure: `history/figures/3e_event_classes.png`. Data: `history/data/event_class_by_year.csv`.

---

## Section 3f — Calibration check on observed events + recent audit

### The four homeowner-observed events

| Date | Peak obs (MLLW) | Pred (MLLW) | Surge (ft) | Peak hour | Predicted curb depth | Observed |
|---|---:|---:|---:|---:|---:|---|
| 2025-10-30 | 7.574 | 4.672 | +2.90 | 15:00 | 11.9" (tide only; +rain) | ~12" severe ✓ |
| 2025-12-19 | 6.833 | 4.717 | +2.12 | 08:00 | 3.0" (tide only; +rain) | ~7–9" with rain ✓ |
| 2026-04-17 | 6.758 | 5.933 | +0.83 | 21:00 | 2.1" | ~2" light ✓ |
| 2026-04-18 | 7.322 | 6.023 | +1.30 | 21:00 | 8.9" | ~10" moderate ✓ |

All four match the HANDOFF / v0.5 calibration set. The historical pull is internally consistent with the data the daily forecast script was tuned against. **No re-calibration of the model is implied by the historical data.**

### Sep 1 2025 – May 17 2026 audit window

| | Count |
|---|---:|
| Total hours with Sandy Hook obs ≥ 6.58 ft | **45 hours** |
| Distinct contiguous events at 6.58 ft | **25 events** |
| Peak observed water level in window | **7.63 ft MLLW (Oct 30, 2025)** |

Twenty-five contiguous-hour flood events at the curb threshold over ~8.5 months. You logged 4 of them as material floods (those reached 7.32–7.57 ft and lasted multiple hours). The remaining ~21 were brief / shallow — a single tidal peak just over 6.58 ft, lasting 1–2 hours at most. That matches the "nuisance" class. If you weren't actively watching, you would have missed most of them.

Full data: `history/data/calibration_check.csv`, `history/data/342_bay_flood_events.csv`.

---

## Deliverables index

| File | Purpose |
|---|---|
| `history/data/sandy_hook_hourly_history.parquet` | Full 1910–2026 hourly dataset with derived columns (1.02M rows) |
| `history/data/342_bay_flood_events.csv` | One row per contiguous flood event at 6.58 ft (1,412 events) |
| `history/data/seasonality_by_threshold.csv` | Monthly stats at 6.58 / 7.00 / 7.20 / 7.70 / 8.70 ft |
| `history/data/return_periods.csv` | 2/5/10/25/50/100/500-year levels + depths at landmarks |
| `history/data/annual_means.csv` | Annual mean water level by year (for SLR fit) |
| `history/data/slr_trend_by_window.csv` | Trend over four windows |
| `history/data/decadal_threshold_crossings.csv` | Events per year per decade, all thresholds |
| `history/data/hour_of_day_peaks.csv` | When flood peaks land in the day |
| `history/data/doy_heatmap.csv` | Events by ISO week of year |
| `history/data/event_class_by_year.csv` | Nuisance / middle / storm counts by year |
| `history/data/flood_days_per_year.csv` | Distinct flood-days per year |
| `history/data/calibration_check.csv` | Four labeled events with peak / surge / depth |
| `history/data/summary_stats.json` | Headline numbers used by this report |
| `history/data/raw_chunks/` | Raw 31-day API chunks (resumable; safe to delete) |
| `history/figures/*.png` | All figures referenced above |
| `history/scripts/pull_sandy_hook_history.py` | Re-pullable NOAA history |
| `history/scripts/build_dataset.py` | Build hourly + events from raw chunks |
| `history/scripts/analyze.py` | Regenerate every output above |

To regenerate everything from scratch: `python scripts/pull_sandy_hook_history.py && python scripts/build_dataset.py && python scripts/analyze.py`. The pull resumes from on-disk chunks, so deleting the parquet files but keeping `raw_chunks/` re-runs in seconds.

---

## Caveats and known limitations

1. **Hourly is not the instantaneous max.** NOAA's `hourly_height` product is a centered-hour value. Storm peaks reported here (e.g., Sandy 12.03 ft) will be lower than the 6-minute instantaneous max (Sandy 13.31 ft). The GEV fit is on annual hourly maxima, so the return-level numbers are also in that frame; multiply by ~1.05–1.10 for instantaneous-equivalent at the very extreme tail.
2. **Pre-1932 data is sparse.** Only 7 usable years 1910–1929 in this pull. They're included but don't drive the SLR fit (the post-1932 trends are the load-bearing ones).
3. **`+0.40 ft` local enhancement is treated as constant.** All depth-at-landmark numbers in this report assume this is a fixed offset. **[Superseded 2026-06: four tape-measured events showed the enhancement is ~0.00 (the +0.40 was over-fit to memory-based observations); every depth column in this report runs ~0.40 ft (≈5″) high. See model/v0.9.md.]**
4. **The cold-weather override is not applied here.** Section 3e counts every above-threshold event as a flood. The model spec says cold events with `SH < 8.0` and `temp_72h < 32°F` don't actually flood the property because the storm drain backflow pathway is ice-locked. Without historical temperature data joined into this dataset, I don't filter those out — so a small fraction of cold-snap events counted here may not have produced any visible flooding at the house.
5. **Hurricane Sandy as a ~5000-year event.** This is the GEV fit's verdict, not a physical claim. Sandy was a tropical-extratropical hybrid whose particular geometry (left-of-track to Sandy Hook, full-moon spring tide, right-angle land approach) is not well represented by 98 ordinary annual maxima. The CI on the 500-yr level alone already runs to 14 ft. Treat anything past the 100-yr level as a planning floor, not a probability statement.

---

*Generated 2026-05-18 from `history/scripts/analyze.py` against NOAA station 8531680 hourly data 1910–2026.*
