# Round 05 — review of round 04 and selective recovery implementation

Codex, 2026-09-23. Author of reviewed round-04 changes: Claude.
Reviewed baseline `60430d833` (repair `017ab4a63`, Python-3.11 hotfix
`aba853908`, guard/fix `8034e1c24` / `c5a761147`).

**Disposition:** Claude's targeted S1–S7 repairs pass the reproductions and
independent source inspection described below, with one additional S6 defect
repaired here. The user-authorized selective recovery is implemented. **This is
not independent approval of Codex's new changes and not approval to promote
v0.10.5. Claude should independently review this patch next.**

The two roles in this record are deliberately separate: independent review of
Claude's changes, and author verification of Codex's implementation. No
Reviewed-by credit is claimed for Codex's own implementation.

## Independent follow-up to Claude's round 04

The full decoder-enabled local suite and `verify_round04_claude.py` pass.
The latter renders the actual email subject, text and HTML; verifies repaired
score cancellation/pairing, unknown-rain payload/chart, explicit null coverage,
rolling horizon, future-only headline, point-level compound plot, malformed warm
bucket handling, nested requests, wall-clock return, and timestamped rain windows.
`verify_repairs_claude.js` also passes against the actual town-map handler.
These are targeted contract checks, not a forecast-skill evaluation.

| Finding | Independent disposition |
|---|---|
| S1 | Absolute errors are aggregated before averaging; bias remains signed, pairings share a ledger row. ±1-ft candidate loses to 0.2-ft baseline; disjoint source rows give no pair. Distinct-tide gate retained. |
| S2 | Unknown-rain flag reaches map/chart, explicit null intervals reduce daily known hours. Page explains partial/unknown coverage. |
| S3 | Rolling series and calendar-date cards now include the partial last date; nominal 168 hours has hourly sampling resolution. |
| S4 | Shared worst-72h text feeds actual subject/text/HTML. Past same-day points no longer enter forward day_worst. |
| S5 | Chart reads per-point compound potential; rounding accounts for <0.01-ft plot/map difference. Daily hypothetical high-tide burst is labeled separately. |
| S6 | Required durations and other warm-bucket fields validated; malformed bucket probe passes. One remaining percentile issue found and fixed below. |
| S7 | Nested grid/cross-check calls recompute timeout. Caller joins a daemon worker for a wall-clock limit, so slow transport no longer holds optional quick acquisition indefinitely. The worker is not canceled and this is not a bound on every step of forecast building; optional work still consumes up to 75 s before alerts. |

**Additional S6 defect:** P-ETSS crossed p90 points were filtered without
incrementing `dropped`, and a 0.05-ft tolerance accepted small inversions despite
the documented p10 <= p90 rule. This patch rejects every inverted matched point,
counts the removal, and degrades the source. A two-point test with one p90=0.98
below p10=1 and one valid point now keeps the valid point and reports one dropped.
This additional fix needs Claude's review along with the recovery.

The Python-3.11 failed publish remains part of the historical record. Local
compile and the compatibility guard pass; remote CI on this commit is checked
separately at publication. Broader writer/validator parity, hourly-failure
visibility, and scientific validation remain open. None of those is silently
claimed complete by the focused S1–S7 dispositions.

## Recovery implementation (Codex-authored; independent review pending)

John explicitly authorized the plan in this session and said Claude will check
it afterward. Implemented the first recovery work unit in
`history/plans/2026-09-23-selective-recovery-plan.md`:

1. Production `water_series` now receives the existing **fresh, despiked,
   age-validated observed surge**, not `worst['surge_ft']`. The tank sees that
   restored bay curve. NWS high-tide product rows remain unchanged.
2. `water_series_input` records actual source, value, observation time, age,
   status and detail. `current_surge_ft` retains the historical worst-tide
   meaning; no silent field semantic change.
3. Missing/stale observed surge gives an empty continuous series and visible
   unavailable notice, not a numeric zero-surge tank forecast. Explicit zero is
   still valid for the nowcast astronomy-only caller. Existing per-tide NWS /
   persistence / astronomical-degraded behavior is unchanged.
4. `input_health` retains ALL sources. `degraded_inputs` is production-only;
   `outlook_degraded_inputs` is outlook-only. Core email/widget do not inherit an
   unused outlook warning. Outlook page and landing map show scoped failures;
   town map shows core and outlook health because it consumes both. The gate
   validates the split while supporting old artifacts without the new field.
5. Both maps identify the production/outlook source transition. The chart's
   explanation distinguishes persistence from individual NWS high-tide products.
   No blending was introduced to conceal different source predictions.
6. Candidate spec and forecast README describe the actual behavior. Model
   constants, formulas, surveyed landmarks and golden files are unchanged.

Classified as rule-5(c) corrective restoration: undo the unexpected propagation
of a future product surge into the legacy continuous forecast, enforce existing
unavailable-not-zero behavior, and scope warnings to actual consumers. This does
not add a new surge model or promote an experimental source. The outstanding
class-(b) changes already on main still require v0.10.5 review + owner promotion
DECISION; they are not retrospectively approved by this recovery authorization.

## Arm-by-arm coverage

| Arm | Treatment |
|---|---|
| Website near-term curve + flood windows | Restored shared series; explanation states source; unavailable notice when no fresh surge. |
| Scriptable widget | Same JSON field restored automatically; core-only degraded list. Source untouched, so no new copy/version step. Existing v7.29a re-copy obligation is unchanged. |
| Landing strip/day cards | Recomputed day_worst from restored tank/curve plus retained per-tide product and rain pathways. |
| Landing/details/per-tide maps | Shared map renderer now labels persistence/outlook and exposes scoped outlook health. Generated together. |
| Town map | Same source labels and core/outlook health shown from fetched JSON. |
| Seven-day page/chart | Intentionally retains experimental guidance; shows scoped failures; no promotion into core. |
| Email subject, text, HTML | Core result recalculated; outlook-only failures absent. Rendered equivalence test for failed vs available optional outlook. |
| ntfy/email alert gate | Existing per-tide/rain/radar gate preserved; tests show optional outlook failure cannot change it. No live notification sent during verification. |
| SMS / radar nowcast | Fresh imminent-impact role unchanged; no source edits. Explicit zero-surge astronomical helper contract preserved. |
| Prediction/outcome ledgers | Normal generator append only; original byte prefixes verified, no historical observations rewritten. |

## Verification and concrete generated result

`tests/test_selective_recovery.py` uses the real build_forecast + tank with frozen
external inputs. It verifies positive/negative/zero/missing surge, product-surge
independence for both dry and heavy-rain cases, retained official tide values,
metadata, gate rejection of inconsistent health/numeric unavailable curves,
optional-outlook failure isolation including rendered emails and alert ranking,
48-hour tide filtering, map series payload, and the remaining percentile defect.

Executed:

- Decoder-enabled full suite: **266 tests OK, no skips**.
- Frozen v0.10.1 and v0.10.3 replays: **PASS, unchanged**.
- Claude round-04 probe and repaired JS map probe: **PASS**.
- Python compile and compatibility guard; artifact gate: **PASS**.
- Real no-delivery generation: `forecast/flood_forecast_daily.py --no-send
  --write-html docs/index.html --write-json docs/forecast.json`.
- Browser: restored chart visibly renders against gauge overlay; day cards use
  LIGHT for September 23/24 and retain SEVERE for September 25's product tide;
  scoped outlook warning appears at the map, not as a core forecast warning.

Primary output: [round05-recovery-verification.json](round05-recovery-verification.json),
forecast issue **2026-09-23T20:43:29Z**. Observed surge **1.4752 ft**, observation
**16:36 EDT**, age **7.5 minutes**. Legacy worst-tide surge still **2.5 ft**.
All 72 common tide-curve timestamps versus `d17aa402e` are **1.025 ft lower**
(after output rounding), approximately **12.3 inches**. The six official
high-tide totals remain **7.0, 6.4, 7.1, 7.0, 7.9, 7.9 ft MLLW**.
No fixed downward correction was applied: fresh observed surge drives the curve.

Production degraded list is empty; outlook list contains `outlook_petss` (aged
cycle). All input-health records remain present. Notification log explicitly
says skipping delivery; neither alert state nor observational ledger changed.
The generated forecast, per-tide pages, map payload and core rendering passed
the same artifact gate before commit.

## What Claude should check next

Review the small source diff, especially unavailable-surge behavior, each health
consumer, backward-compatible gate, retained per-tide source behavior, and the
P-ETSS inversion fix. Confirm generated source/curve identity, all shared arms,
no notification-state changes, and unchanged goldens. An author PASS cannot
replace this independent review.

Still separate: scientific comparison of persistence vs a time-varying curve,
independent rain/tide compound validation, optional acquisition entirely off the
alert critical path, and final v0.10.5 promotion. The plan intentionally did not
turn those research candidates into production behavior. A map source seam can
still show differing predictions and is labeled; this is an explicit remaining
modeling limitation, not a secretly smoothed or silently unified curve.
