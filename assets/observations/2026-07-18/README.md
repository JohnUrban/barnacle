# 2026-07-18 — THE #2 FLOOD OF RECORD, live-dictated end to end

**Peak: 6.0″ up the first porch riser = 5.18 NAVD88 = +19.9″ vs the
SW grate, at 3:37 PM ET** — second only to Oct 30 2025 (≥5.25, ~+21″),
achieved **on rain alone**, on an *ebbing neap tide* (bay ~2.2 NAVD88,
16″ below the grates — zero tidal assist, maximal drain capacity).
44 user-dictated timestamps over 116 minutes: rise, peak, recession,
and the drain network's full pressure cycle. The most completely
documented flood in this corner's history.

Raw log: `flood-measurements.txt` (verbatim dictation).
Analysis artifacts: `analysis/` (hydrograph, all-events alignment,
k_out fit, MRMS record, nowcast scorecard). 27 rows appended to
`data/labeled_observations.csv`.

## Timeline (all ET)

| Phase | Times | What happened |
|---|---|---|
| Pulse 1 | ~1:40–2:05 | 20 min, hard middle; pockets filled, drains swallowed all of it — and PRIMED the catchment (user called it live) |
| Lull | 2:05–2:44 | trace rain; "slowing down doesn't mean over" |
| Pulse 2 rise | 2:44–3:37 | hard rain ~55 min. Grates over 2:56 (NE/NW FIRST — trunk signature), all five 2:57, Central sheet 2:58, **curb 3:01 (5 min!)**, +2″/min at 3:02, crown under 3:11, lawn step 3:13, porch base 3:17; passes 7/6's peak 3:19, 7/9's 3:28, 7/13's 3:33 |
| PEAK | **3:37** | **6.0″ up the riser = +19.9″; #2 all-time** |
| Recession | 3:37–4:40+ | −1″/7min quickening to −0.31″/min; off riser 4:03, crown out 4:10, curb out ~4:35, sidewalk clear 4:40 (user predicted it 2 min ahead, verified) |

Drain-network pressure cycle: NE/NW jets 2:56 → SE/SW jets 3:15 →
**unmonitored upstream-Bay grate GEYSERING 3:29** → weakening
3:48–3:52 → SE whirlpool 4:19 → SW whirlpool 4:22 → simultaneous
NW-jet + SE-whirlpool (through-flow + partial recirculation, user
synthesis) → north-side discharge tail ≥1 h post-rain.

## This event among all events

| # | Event | Peak vs SW grate | Type | Tide under it |
|---|---|---|---|---|
| 1 | Oct 30 2025 | ~+21″ (≥5.25) | rain on high storm tide | 7.63 MLLW |
| **2** | **7/18/2026** | **+19.9″** | **rain alone** | **ebbing neap ~5.3** |
| 3 | 7/13/2026 | +19.5″ | rain (double-pulse) | modest |
| 4 | 7/9/2026 | +18.7″ | rain on high tide (gauge failed) | ~6.0 |
| 5 | 7/6/2026 | +15.4″ | rain alone, low tide | ~5.4 |
| 6 | Dec 19 2025 | ~+11″ | rain, drains tide-blocked | 6.86 |

**All six measured floods are rain events.** Four of the top five
happened in THIRTEEN DAYS (July 6–18, 2026). Today at Oct-30's tide
would have been the flood of record by several inches — the +19.9″
was bought with zero tidal floor.

## Instrument scorecard (see analysis/nowcast_scorecard.txt)

- **Observer (live dictation): champion.** Minute-resolution truth;
  even predicted the sidewalk clearing 2 min ahead, verified.
- **Nowcast (tank on live radar), unattended: peaked at +14.5″ AT
  19:37Z — the true peak minute exactly.** Timing perfect; magnitude
  under by 5.4″ because MRMS underread the storm core (~0.1 in/hr
  frames during observed torrents, 3:10–3:30 window; opposite
  failure from 7/9 where radar nailed 5.5 in/hr). Site showed
  FLOODING NOW (feature demanded by the user at 3:20, shipped 3:23,
  bug-fixed 3:23→3:35 mid-event).
- **QPF outlook: 'street' (+6.9″)** — missed by 13″. Third
  consecutive event QPF couldn't see. The input problem is
  structural; the nowcast layer exists because of it.
- **Alerts**: Watch active since 7/17 21:35 (alert sent then);
  Flash Flood Warning mid-event escalated the ladder.
- **Bay gauge: spiked garbage again** (9.75 MLLW) — and found the
  despike guard's short-window hole; fixed live at ~2:20 PM.

## Model consequences

1. **k_out MEASURED: 3.50/h** from the clean recession limb
   (16:03–16:40, rain ≈ 0) — vs calibrated 3.12; jets still feeding
   → 3.50 is a floor. → **v0.10.1 shipped**: k_out=3.50, K/γ/lag
   jointly refit on the 7/6+7/9 hydrographs with k_out pinned
   (K=1.296e6, γ=0.78, lag=15 min). Validation RMS IMPROVED
   1.44→1.32″. The rare legitimate tuning: measurement first,
   refit second, better everywhere.
2. **Structural gaps observed (not tuned — queued as structure):**
   - antecedent PRIMING (pulse 1 wetted the catchment; fastest rise
     ever followed) — user called it before it happened
   - drains are BIDIRECTIONAL with hysteresis (jet → neutral →
     whirlpool; the tank models a one-way sink)
   - recession pool is TILTED, not level (SE/SW exposed while
     NE/NW still fed; conveyance gradient)
   - partial RECIRCULATION (SE intake re-emerging at NW)
   - hillside delivery TAIL ≥1 h (lag-in ≠ memory-out)
   - sidewalk SWALE micro-basin (curb-backed, drains NE-ward)
3. **Radar underread** joins the input-failure catalog: QPF misses
   convection; radar can miss cores. No single input is trustable;
   the observer, gauge cross-checks, and multi-product MRMS (QPE
   vs PrecipRate) are the defenses. Deep forensics queued.

## Site/UX shipped mid-event (user-driven)

- "⚠ FLOODING NOW" headline override from live nowcast (+ mid-event
  targeting fix — outlook said "light" during a top-2 flood)
- Post-event: SO FAR TODAY carries +19.9″ measured (tape) — the day
  remembers. Nowcast day-max memory (autonomy: floods self-report
  without the observer) ships with this commit batch.

## Vantage notes

Images (28): mostly porch → intersection / up Bay; some walkway →
porch step; a few porch-zoom at a car. Uncategorized as yet.

## POSTSCRIPT (same evening): the "radar underread" was mostly OUR box

Backtest (`analysis/box_geometry_backtest.txt`): the old radar
sampling box was **centered on the house — half of it was Sandy Hook
Bay**. During 15:16–15:36 the storm core sat south over the bluffs:
the old box read 0.01–0.12 in/hr (the number the live nowcast ate)
while a **land-only catchment box** (shoreline→ridge, Mount Mitchill
included) reads **2.4–3.8 in/hr** for the same frames. Radar saw the
flood; we sampled the wrong pixels. Tank hindcast peak: old box
+13.0″ → catchment box **+15.9″** (measured +19.9). Residual ~4″ ≈
priming (K on soaked ground) + shortened lag (peak trailed the last
strong frame by ~1–4 min, not 15 — soaked hillside delivers faster).
Fix shipped to nowcast.py, nowcast_tank.py, mrms_point_rain.py
(cached pre-7/18 box rows not comparable; point values unaffected).
Instrument ranking revised: observer >> radar-with-right-box >>
radar-with-wrong-box >> QPF.
