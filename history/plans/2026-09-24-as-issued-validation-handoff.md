# Deferred validation: advisory corrections and rain/tide street forecasts

Prepared by Codex, 2026-09-24, for Claude and John's subsequent review.
Status: **research implementation ready to start; forecast skill not established**.
Production remains v0.10.6. This is separate from the frozen wind-shadow trial
and Tern's social work. John's existing item-2/5 acceptance remains in force;
this work does not reopen the completed v0.10.6 release.

## Assignment and authorization

John asked to resume the accepted validation follow-ups and prepare this
handoff. Use a separate worktree and branch, suggested
`research/as-issued-validation`. Build the offline evaluator, its tests and
reports; commit the study protocol before scoring outcomes. Return for
independent Codex review before merging any implementation. No retuning,
production forecast or alert changes, new feed, or live wind promotion.
Do not change any file in `models/wind_shadow/FREEZE.md`: the c2 trial has
started. Read its QC/evaluation work as evidence without changing its identity,
eligibility rules, period or evaluator to accommodate this separate study.

## Starting evidence — checked at main 5d281b19c

[Readiness census](../reports/2026-09-24-validation-archive-readiness.json),
reproducible with `python3 history/scripts/profile_validation_archive.py`:

- [VERIFIED] 12 replay-input records, all v0.10.6, from
  2026-09-24T05:46:59Z through 2026-09-24T16:14:12Z: 10.454 hours.
  No duplicate generation stamps, reported unavailable fields, unequal column
  lengths, unordered target arrays, or failures of the archive validator.
  These checks do not prove semantic completeness.
- [VERIFIED] **All saved advisory correction anchors are zero.** This sample
  cannot estimate the effect of nonzero corrections. Treat identical paired
  predictions as a control/parity check, not evidence that corrections help
  or are harmless. The earlier nonzero capture in the spec is not represented
  by these 12 records; locate its original evidence before using it.
- [VERIFIED] The replay schema saves hourly outlook astronomy/output, QPF as
  used, surge state and empty-tank start, but not the full half-hourly core bay
  trajectory. In the latest record the tank starts at 10:00Z while the saved
  outlook array starts at 11:00Z. A replay cannot silently omit that first hour.
  Identify recoverable as-used astronomy/outputs in immutable Git blobs and
  tide caches, or classify the record as incomplete for that comparison.
- [VERIFIED] NWPS issue/retrieval stamps are present. Advisory issuance is
  embedded in a status string; source QPF issuance/retrieval stamps are not
  dedicated fields. `replay_archive.build_record` can substitute generation
  time for absent NWPS retrieval metadata. Distinguish source issuance,
  actual retrieval, generation and target times. An archived as-used QPF is
  useful even where its upstream issue age cannot be established.
- [VERIFIED] The first official wind record is now present: c2, status
  `candidate`, issuance 2026-09-24T16:14:12Z, written 16:14:26Z,
  nominal trial slot 16:00Z. Bundle `82d156a63089573e837ae2e122336ec62f24fc80548aa8080105e3160aed5029`
  matches the frozen files and record binding. Successful hourly run
  [36025879659](https://github.com/JohnUrban/barnacle/actions/runs/36025879659).
  Its richer rain context may supplement matched records read-only; wind
  sensitivity output is not observed street-flood validation.

## First deliverable: establish what is replayable

Inventory archive coverage by issuance, target, model version and source.
Retain file/blob hashes and row identifiers. Verify units/datum, target grids,
rain interval meaning, missing versus dry hours, timezone/DST, cache age,
rounding, initialization and all antecedent input hours the tank actually used.
Separate genuine archived outputs, exactly reproducible counterfactuals,
approximate reconstruction and unavailable cases. Prove reproduction against
an archived published forecast before interpreting error differences; report
the tolerance justified by stored precision. Preserve available evidence now
rather than waiting until the end of the study to discover a logging gap.

If records are insufficient, first inspect immutable Git history and existing
caches/logs. Propose or build a narrowly scoped append-only archive enhancement
on the research branch if needed, with tests and independent review before
merge. It must preserve existing rows and production behavior and must not
modify the frozen wind bundle. Missing inputs are never fabricated or backfilled
as if available at issuance. Keep failures visible without breaking publishing.

## Study A: do advisory corrections improve the hourly outlook?

The subject is the **seven-day outlook's NWPS-supported hourly line**. The
core 30-hour `water_series` deliberately ignores advisory corrections; do not
conflate these surfaces or resurrect the former worst-product constant lift.

Predeclare an ablation: corrected and uncorrected NWPS predictions at the
same issuance and target, with identical astronomy and datum conversions.
Verify which source labels actually carry the correction. Separate P-ETSS,
fallback and guidance-tail intervals; they are not raw-NWPS comparison rows.
If studying a correction propagated into a guidance tail, report that as a
separate estimand with its own uncorrected counterfactual.

Match against subsequently observed Sandy Hook levels. Retain raw observation
bodies, quality flags, acquisition date and verified/preliminary status;
exclude inferred/invalid outcomes and specify treatment of later revisions.
Reuse the quality-aware wind review's lessons. Do not count forecast values
or inferred gauge levels as observations.

Define high/mid/low phase from astronomical tides before examining outcome
errors; specify lead bins and nonzero-correction cohorts. Report paired MAE,
bias and underprediction, plus drain/landmark threshold implications with
explicit gauge-to-site conversion. Separate zeros from informative exposures.
Give issuance counts, unique targets and independent event counts: overlapping
hourly forecasts are not independent storms. Predeclare event segmentation,
weighting and event-level uncertainty. No pooled improvement claim that hides
harm at low tide. Zero eligible nonzero corrections means **not yet evaluable**.

## Study B: does the combined rain/tide forecast predict street floods better?

Keep two questions separate:

1. The original v0.10.6 residual: does the decay rule improve as-issued street
   prediction over the pre-v0.10.6 persisted-reading curve? Reproduce the
   precise baseline from the reviewed spec/code; hold rain, tank mechanics,
   initial conditions and known-at-issuance information constant.
2. John's broader coupling question: when does bay height change rain flooding,
   and does that help against real street observations? Predeclare diagnostic
   comparisons with tide-only and a fixed-low-bay rain-tank ablation, using
   the same as-issued rainfall. Explain each comparator and the plug band.
   These ablations isolate mechanisms; they are not alternate deployed models.

Score the product's actual published quantities separately: the time-varying
   combined line and any conditional burst scenario/window. A conditional burst
   estimate is not an unconditional hourly forecast or a calibrated probability.
   Distinguish core and extended-outlook horizons and their rain sources.

Use issuance-time rainfall, surge reading/mean and actual initialization and
history, never later radar rain or observed bay as a forecast input. Radar/
observed-bay substitutions may be separately labeled hindsight diagnostics to
locate error, not evidence of forecast skill. No coefficient tuning on the
evaluation events. Match forecasts to street observations with time, location,
datum, uncertainty/brackets and primary provenance. Include documented dry
windows where available; an absent flood report is not a dry observation.

Predeclare depth/bracket error, timing and threshold hit/miss/false-alarm
measures where the observation supports them. Distinguish measured points,
witness bounds, photographs and reconstructions. Do not score an unknown peak
as exact. Cluster uncertainty by event and expose missingness/coverage.

Keep prior evidence corrections intact: five observed-reference radar-rain
events tied; they are not as-issued validation. The 2025-10-30 crest is a
reconstruction, excluded from observed-peak aggregates; +13.5 in is a photo
bound. July 6's canonical reference is +15.4 in. The partial September 13
QPF experiment omitted the 10Z burst hour and assumed it dry: sensitivity
only, not a complete as-issued error attribution.

## Completion criteria for this development pass

- Committed protocol, input/observation eligibility and adequacy rules before
  outcome scoring. Do not copy the wind trial's 60-day/five-storm requirement
  without justification; this study has different exposures and ground truth.
  Disclose already-inspected history and reserve prospective confirmatory data.
- Offline reproducible evaluator with saved source hashes and meaningful tests:
  zero-correction parity, known nonzero effects, source boundaries, missing
  hours/initial history, datum/time alignment, observation QC and incomplete
  evidence exclusion. Synthetic fixtures establish mechanics, never skill.
- Coverage/readiness report plus whatever paired results are supportable.
  Say INCONCLUSIVE or NOT YET EVALUABLE when appropriate. State precisely what
  future corrections, compound floods or observations would resolve each gap.
- A small field-observation checklist for John if new observations are needed:
  time, marked landmark, depth/bound and wet/dry evidence; no new survey assumed.
- Update branch-local living docs; leave production and other worktrees alone.
  Summarize findings, exclusions, proposed logging repairs and unresolved owner
  choices for independent Codex review. Scientific completion may require more
  events; evaluator implementation need not wait for those events.

## Read first

- `AGENTS.md`, `HANDOFF.md`, `BACKLOG.md` scientific follow-ups and DECISION
  `v0.10.6-items-2-and-5` (2026-09-24 00:31 EDT).
- `model/v0.10.6.md`, checklist items 2/5, archive and known limitations;
  `history/plans/2026-09-23-v0.10.6-outlook-review.md`.
- `audits/2026-09-24-a1/03-repair-verification-codex.md`,
  `04-evidence-corrections-claude.md`, `05-candidate-approval-codex.md`.
- `forecast/replay_archive.py`, `data/replay_inputs/README.md`,
  `forecast/outlook.py` (`hourly_surge_estimator`), core series/tank code.
- `history/scripts/v0106_rain_comparison.py` and
  `history/reports/2026-09-24-v0.10.6-rain-comparison-r2.txt`.
- Observation ledger and each event's primary evidence; wind a3 QC review
  and frozen evaluator for relevant lessons, without editing frozen files.
