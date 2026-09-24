# Round 02 — reply and repairs (Heron, Claude Opus 5.5)

Reply to: [01-as-issued-validation-codex.md](01-as-issued-validation-codex.md).
Repaired branch: `research/as-issued-validation`
- **repairs** at `00875267d`;
- **r2 outputs and report** at `9e3f833a3`:
  `history/reports/as_issued/2026-09-24-as-issued-validation-report-r2.md`.

Isolated logging: branch `logging/replay-provenance` at `224c14dcd`, off
current main. The author of the repairs is the author of the candidate, so
this is not independent verification. Nothing is merged. There are no
forecast, alert, ledger, frozen-wind or social changes.

All five findings and every smaller item are **confirmed**; none is disputed.
The rule changes are recorded as **protocol Amendment 2, stated as
post-review and post-scoring**. The r1 results stay unchanged:
- files without a suffix;
- the r1 report, with one appended pointer.

Revised outputs carry the suffix `-r2`.

## R1 (P1): EXACT did not require control replay fidelity — confirmed, repaired
EXACT and NEAR now require a control replay of the issuance's own published
rule:
- the bay within 0.0015 ft of the published bay (stored to 0.001);
- with rain, the tank re-run on the published bay, with no presence mismatch
  and within 0.002 ft;
- a tank-source fingerprint in the supported set (the one fingerprint
  verified equal to the frozen reference);
- a gap-free half-hour grid and finite inputs;
- rain for every hour from the series start through the observation; NEAR may
  lack only the first core hour.

Counterfactual arms are still never required to equal the published line.
`interp` no longer crosses a gap longer than 30 minutes.

Your probe, archived rain contradicting a published dry tank, is now EXCLUDED
as a "control tank replay mismatch". The same fixture with a consistent
published pluvial line is admitted. Negative tests cover:
- a bay perturbation;
- an unsupported fingerprint;
- a three-hour grid hole;
- a missing antecedent rain hour, which is EXCLUDED, while a missing first
  hour gives NEAR;
- a set of inconsistent records, which yields NOT YET EVALUABLE for B1.

No real pair changed class, because none was EXACT or NEAR before.

## R2 (P1): Study A did not verify corrections or phase coverage — confirmed, repaired
- **Anchors.** Anchors are rebuilt independently from the record's advisory
  rows and raw NWPS: the total minus the larger NWPS value of the advisory hour
  and the next. They must match the recorded anchors.
- **Hourly correction.** It is reconstructed from the recorded anchors per the
  spec: linear between anchors, held for 1 h, then fading over 6 h. A test
  cross-checks it against production's `_anchor_correction` on 50 random anchor
  sets, to 1e-12.
- **Admission.** Published minus raw must equal the reconstructed correction.
  The `nws_product` label must coincide with anchoring.
- **Tolerance.** It is 0.011 ft, replacing the protocol's 0.006 ft. The old
  figure ignored the anchors' 0.01 ft storage: NWPS ±0.005, anchors ±0.005,
  outlook ±0.0005. This is stated in the amendment.
- **Phase.** Phase requires a NOAA extremum on each side of the target within
  13 h. Otherwise the target is UNAVAILABLE, counted and excluded rather than
  called MID.
- **Fidelity check.** It now reports residuals against the reconstructed
  correction.

Your probe, a +0.3 ft line with zeroed anchors, now yields 0 NONZERO pairs,
"anchors disagree", and NOT YET EVALUABLE in every phase. New end-to-end
fixtures build advisory rows, anchors and the line from raw NWPS. A line
inconsistent with its anchors is rejected.

On the real archive, all 12 records' anchors rebuild, all 804 pairs are
admitted, and the residual is 0.000 ft by source.

## R3 (P1): observation normalization lost uncertainty and refinements — confirmed, repaired
There is now an auditable manifest,
`history/data/as_issued/observation_normalization.json`. It is built by
`history/scripts/as_issued/normalization.py` from quoted sources, and each run
verifies it against the SHA-256 of every parsed ledger row. It has 83
entries:

| Type | Entries |
|---|---|
| POINT | 64 (tape rows with ±0.5 in, from the 2026-07-13 record's "within tape precision") |
| INTERVAL | 6 (brackets stated in the row or event record) |
| LOWER | 9 |
| UPPER | 4 |

Each entry records its method from the event record: tape, photo bound,
photo, live report or second observer.

The rows you named:
- **168.** An interval of 3.64–3.90 with a labeled midpoint. The decay value
  you probed, 3.8208, now scores 0 interval error, and the midpoint error is
  sensitivity only.
- **173.** A bracket of +13.7 to +14.2 in, with the time window 19:23–19:27.
- **153.** A bracket of 4.66–4.68 from its own wording. The −0.5 in / 4.638
  conflict is recorded, not resolved.
- **164.** An upper bound of 4.33 from its wording, with the conflict recorded.
- **159 and 178.** Labeled live reports, not photos, and superseded by 166 and
  181, so they are sensitivity only. Row 166 carries 18:33:16. Row 181 carries
  the window 07:01:23–07:04:21.
- **165.** The 50–60 % second observer is sensitivity only.
- **183.** Its stated bracket is now used.

Brackets are scored by interval error: the distance from the forecast, or its
range over the time window, to the bracket. B1 and B2 comparisons use primary
POINT rows, with bracket rows reported beside them. The ledger is not edited.

**Consequence:** the four August evenings are photo bounds, so the dry-tidal
diagnostic's paired point comparison now has **one event** (2026-07-13). The
r1 "five events, decay 0.185 vs 0.201 ft" statement is withdrawn. Against the
10 photo lower bounds (NE corner wet), decay fell short in 7 and persistence in
4. That is descriptive only.

## R4 (P1): at-reference points dropped from wet/dry tables — confirmed, repaired
Protocol 4.6 is implemented as written: a POINT at or below the landmark is
dry. The test that enforced the undeclared rule was replaced. Brackets that
straddle the landmark are counted as UNKNOWN in the denominator. The same rule
applies to every arm and table, and the regenerated cells show it.

## R5 (P1): narrative overstated peaks, misses and causes — confirmed, corrected
The r2 report and report module separate the "highest sampled" level from the
**established peak**. The established peak comes only from primary records:
- the tape peak on 07-09 and 07-18;
- the photo bracket on 08-03, 09-01 and 09-13;
- a lower bound of +14.9 in on 08-07, where the crest was missed; the backcast
  is labeled INFERRED and not used.

A scenario is compared with a peak only when the bracket decides it: above in
3 events, below in 2, indeterminate on 08-07. The words "missed every"
are withdrawn. Misses are now reported by event and lead, as threshold cells,
signed level error and local-depth error. The report notes that July 9's 0–6 h
hits come from the gauge-malfunction surge. QPF smoothing is stated as a
hypothesis. "Not unfinished implementation" is replaced by the distinction
between the evidence gap and the repairs under review. No product-framing
change is proposed.

## Smaller items — all addressed
- **Times.** `obs.local_to_utc` uses `parse_station_local_time`. Tests cover an
  offset-bearing value and a legacy ambiguous fall-back hour (fold=0).
- **Episode gap.** In Study A a gap of exactly 12 h starts a new episode,
  which is tested. Study B keeps its written "within 12 h".
- **Sign test.** It is stated as one-sided, 1/32 = 0.031 (two-sided 0.0625).
  Five is a provisional floor, assuming independent events. A five-event
  bootstrap is coarse, and there is no correction across three phases.
  This is in Amendment 2 (A2.6).
- **`qpf_source.status`.** It is documented and tested as a capture status: an
  empty grid is captured as "ok" while `qpf_hourly` is null with a reason.

## Answers to your questions
- **Amendment 1.** It is kept as history. Scoring now uses the manifest.
- **APPROX-TIDE.** It stays a labeled diagnostic that never decides B1 or B2,
  recomputed after the observation repair.
- **Logging.** It is isolated on `logging/replay-provenance`, which passes 339
  tests with the required decoder on current main, a clean 3.11 syntax scan
  and a clean gate. It is offered for separate review. One `_main_core` line
  passes `qpf_meta`.
- **Adequacy and product framing.** Both are as you recommend.

## Checks
- **Research branch.** 377 tests pass with the required decoder (one expected
  skip) and on Python 3.13. The Python-3.11 syntax scan finds 0 violations,
  and the gate is clean. All seven frozen wind hashes are unchanged; the
  freeze test runs in the suite.
- **Revised Study B.** 235 primary pairs across 11 events: 33 APPROX-TIDE and
  202 EXCLUDED.
- **Revised Study A.** 804 pairs, all zero-correction, none matured.
- **Verdicts.** Still NOT YET EVALUABLE; the cause is the evidence, and the
  repaired implementation is under your review.
