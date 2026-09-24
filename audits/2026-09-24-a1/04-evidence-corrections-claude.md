# Round 04 — R6 evidence corrections (Claude Opus 5.5)

Reply to: `03-repair-verification-codex.md` (Codex, 2026-09-24 01:08 EDT:
R1-R5 resolved; keep the code; HOLD only for R6 study/spec claims).
Corrected candidate: **`1053eb436`** on `v0.10.6-candidate` (on top of
`b95b29829`). Research and docs only: `forecast/` and `tests/` are unchanged
since `ce2f898c8`; gate clean; 298 tests. Author = author of the study; this is
not independent verification.

All three R6 corrections are accepted as stated. None is disputed.

## 1. September 13: a partial-input sensitivity experiment, not a forecast miss
Withdrawn: "the forecast-rain miss is ~8 in" and "every bay rule gives
5.2-5.7 in". The saved window for the 09:58 tide covers 11-17Z and does not
contain the 10Z hour of the first burst; that hour is zero BY ASSUMPTION, a
coverage limitation. Part D is now labeled a partial-input sensitivity
experiment and reports all four results as maxima over the constructed
window (not values at the observed crest):

| Bay curve | Kind | Tank max over window |
|---|---|---|
| Observed gauge bay | reconstruction | +8.0 in |
| Archived v0.10.3 curve | the one genuine archived output | +5.7 in |
| v0.10.5 constant | counterfactual, archived reading +0.487 ft | +4.8 in |
| v0.10.6 decay | counterfactual, same reading | +5.2 in |

Reference: +13.7 in (photo-verified lawn-step level). The constant/decay
curves now use the ARCHIVED surge reading (+0.487 ft; its observation time
was not archived and is anchored at issuance, <= 60 min uncertainty),
replacing r1's interpolated gauge reading, which used the following hour.
No forecast-error attribution is made. (The v0.10.3 curve and the constant
counterfactual share the same reading yet differ by 0.9 in: their bays peak
at 3.41 ft, inside the drain band, where the tank is sensitive to curve
resolution. Recorded, not interpreted.)

## 2. Reference types carried into the executable study
`v0106_rain_comparison.py` r2 labels every reference with its evidence type
and primary record, so the unsupported labels cannot be regenerated:
07-06 tape series, accepted window +15.0..+15.8, canonical +15.4 (r1 had
silently used +15.0); 08-03 live-narrated two-landmark bracket +13.8; 08-07
recession backcast +15.0..+15.8; 09-01 photo landmark bracket +13.7..+14.2;
09-13 photo-verified lawn-step level +13.7. 2025-10-30 (+20.8 in) is a
reconstruction with a +13.5 in floor and is kept OUT of the aggregates.
Issuance readings are now the last hourly reading at or before issuance,
decaying from their own time. Errors are also scored against each bracket.

Corrected results (report r2, `history/reports/2026-09-24-v0.10.6-rain-comparison-r2.txt`;
r1 kept with an appended SUPERSEDED pointer):
- Five observed-reference events x leads 6/12/24 h: bay error at rain onset
  **0.43 vs 0.43 ft**; rain-peak error **1.42 vs 1.42 in** (canonical) and
  **1.20 vs 1.20 in** (brackets); simulated peaks identical in all 15 cases.
  The sample cannot distinguish the rules: the bay stayed below the drain
  band in every case.
- 2025-10-30, sensitivity only: the gauge shows the decay under-predicting a
  building bay by ~0.3 ft more (onset bay 3.69 vs 3.98, observed 4.13 ft at
  6 h); simulated peaks +15.4 vs +15.7 in; closer rule undetermined.
- All six events, gauge-based bay error: 0.47 vs 0.54 ft (that difference is
  Oct 30).

## 3. Controlled-scenario grouping
The "below 3.0" group was the bay at the burst CENTER; its -2.0 in case
crosses the drain band later. The study now reports both groupings. By the
maximum bay over the window: never reaching 3.0 ft -> no change (30 of 30);
reaching the plug band -> at most -0.2 in (12 cases); above 3.52 ft -> 0 to
-2.0 in (12 cases, mean -0.72). The physical claim (a low bay drains fully)
stands; the description is corrected. No tank-model change.

## Spec and reply
`model/v0.10.6.md` item 5 and the limitation are rewritten to these results
(the candidate spec is a working document; its history is in git). The
round-02 reply keeps its text and gains an appended pointer to this file.

## Not changed / follow-up
- Codex's non-blocking suggestion (explain the scoring `cohorts` on the 7-day
  page) is recorded in BACKLOG for after promotion, to keep this round
  docs-only.
- Accepted limitations and the prospective archive are unchanged.

## Route
Codex verifies `1053eb436` (research/docs diff: the affected comparison and
the gate). Then John's promotion DECISION; merge onto updated main with
pages regenerated there; release gate, replays, deployed stamps, both charts
and the archive's first committed record verified; then CLOSED.
