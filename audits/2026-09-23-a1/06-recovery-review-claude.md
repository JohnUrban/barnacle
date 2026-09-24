# Round 06 — independent review of Codex's recovery patch (Claude Opus 5.5)

Reviewed: `eb8e79475` (recovery + extra S6 fix) and `3fc6be082` (HANDOFF
link), against Codex's round 05 and the plan
`history/plans/2026-09-23-selective-recovery-plan.md`. Review written
2026-09-23 after 22:31 EDT. Reviewer did not author the patch.

**Verdict: PASS for the recovery as a corrective restoration, with one
finding (F1) that changes pre-today behaviour and needs John's decision.**
This is not approval to promote v0.10.5; the owner DECISION stays separate.

## Checks run (this reviewer, at `b012229b7`)
- Decoder-enabled suite (`BARNACLE_REQUIRE_GRIB=1`): 266 tests OK, exit 0.
- Frozen replays v0.10.1 and v0.10.3: PASS unchanged. Gate: clean.
- `verify_round04_claude.py`: exit 0 on the patched code.
- CI: `eb8e79475` failed only the documentation contract Codex reports;
  `3fc6be082` green.
- Live artifact 02:17Z (2026-09-24 UTC): `water_series_input` =
  surge-persistence +2.197 ft, observation 22:12 EDT, 5.7 min old;
  `degraded_inputs` empty; `outlook_degraded_inputs` = [outlook_petss].

## Source review, item by item
1. **Curve source.** `build_water_series(persisted_surge, ...)` replaces
   `worst["surge_ft"]`. This restores the pre-2026-09-23 input exactly
   (the product rows never reached the series before the parser fix). PASS.
2. **Per-tide peaks.** The per-tide ladder (product row, else persistence,
   else astronomical-only-degraded) is untouched; `current_surge_ft` keeps
   its meaning. PASS.
3. **Metadata.** `water_series_input` records source, value, observation
   time, age, status and detail; gate validates it and rejects a numeric
   curve under an "unavailable" source. PASS.
4. **Health split.** `degraded_inputs` is production-only,
   `outlook_degraded_inputs` outlook-only, `input_health` keeps every
   entry. Gate is backward compatible (old artifacts without the new
   field keep the old rule). `_degraded_health_rows` derives rows from
   `input_health` by scope, so text, HTML, email and landing banners read
   production only; the outlook page and the landing map's map section show
   the outlook scope; the town map shows both because it consumes both.
   This implements the DEGRADED-INPUTS SPLIT proposal stored earlier today;
   the plan records John's authorization. PASS.
5. **P-ETSS inversion (extra S6).** Strict `p10 <= p90`, dropped points
   counted, source degraded. My round-04 0.05-ft tolerance contradicted
   my own spec; Codex is right. PASS.
6. **Labels.** Production map points read "(observed-surge persistence)",
   outlook points "(7-day outlook guidance)", with a note that a change at
   the boundary is a source seam, not an observed jump. Honest; the seam
   is visible, not smoothed. PASS.
7. **Nowcast caller.** `nowcast._predicted_bay` passes an explicit 0.0,
   so the new `None -> []` branch cannot reach it. PASS.
8. **Codex output detail.** Its verification JSON shows day_worst
   `water_navd88: null` on all three days. Not a defect: when the tide
   candidate wins, the entry carries no continuous level. The live
   artifact shows levels (1.164, 4.688) where the series decides.

## F1 — missing observed surge now deletes the rain tank line (decision needed)
Before today, when the gauge had no fresh observation and no product row
existed, the per-tide ladder fell to `surge = 0.0` (astronomical-only-
degraded) and the series ran on that worst tide's 0.0: the tank line,
flood windows and the tank pathway in day_worst stayed alive on astronomy,
labeled degraded. After this patch `build_water_series(None)` returns `[]`,
so during a gauge outage the site chart, the widget curve, the flood
windows and the tank pathway disappear together. The burst potential in
`pluvial_risk` uses a fixed low bay and survives, so the rain pathway is
reduced, not removed.

So this is not purely a restoration: it is a new missing-input policy.
Codex's reasoning (no definite curve without bay forcing, never a silent
zero) is honest under rule 7. Against it: the rain doctrine says never
defer rain modeling, and the tank's result is flat for a bay at or below
3.0 ft NAVD88, so at low and mid tide an unknown surge barely changes the
rain answer. Two defensible options for John:
- (a) Keep Codex's choice: no curve, visible "unavailable" notice.
- (b) Pre-today behaviour, made explicit: run the tank on astronomy with
  surge unknown, label the curve "astronomy only, surge unavailable", and
  keep `water_series_input.source = "unavailable"` with status degraded
  (the gate's numeric-curve rule would need to allow a labeled
  astronomy-only curve).

Reviewer recommendation: (b), because it keeps the rain pathway alive in
exactly the outage conditions (storms knock gauges out) where it matters,
while staying honest about the missing surge. Either way, rule-5 class:
(a) and (b) are input/policy behaviour, so they belong in the candidate
spec's Inputs & policy section, not in a class-(c) note.

## Not covered by this review
Scientific skill of persistence versus a time-varying curve, compound
rain/tide validation, and the source seam between the 30-h production curve
and the outlook line remain open, as Codex states. Hourly-failure visibility
and writer/validator parity remain scheduled.

## Status
Recovery: PASS (reviewer), pending John's choice on F1. S1-S7 (Codex round
05) and this round together leave no open code finding except F1. Next:
John's F1 choice and, separately, his v0.10.5 promotion DECISION.
