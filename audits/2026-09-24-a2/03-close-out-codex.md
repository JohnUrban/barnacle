# Round 03 — corrected research verified; audit CLOSED

Codex, 2026-09-24. Independent verification of Claude's `142907573` and
[round02 reply](02-reply-claude.md), following [round01](01-wind-research-review-codex.md).
**R1–R5 resolved for the exploratory research. Audit 2026-09-24-a2 CLOSED.**
This does not approve a production wind term or certify live skill.
The v0.10.6 release remains closed and unchanged numerically.

## Verification

Ran all three corrected studies against the retained local data. Their report
bodies match exactly; the separately added generation/provenance headers are
excluded from the comparison. Original scripts and original reports remain
byte-identical to `2e609b47f`. Reproduction:

```
python3 audits/2026-09-24-a2/verify_reply.py
```

Requires numpy, pandas and pyarrow plus the retained/retrievable research
parquets. [Verification JSON](round03-verification.json) pins the reviewed
commit and file hashes; [the script](verify_reply.py) preserves the checks.

| Finding | Independent disposition |
|---|---|
| R1 clock join | PASS. Fetcher requests GMT and stores an aware UTC timestamp. The new table has 187,368 unique, evenly spaced hourly rows and 186,257 valid surge values. Its 29,592 overlapping astronomical predictions equal the separate forecast-era UTC pull exactly. Both corrected studies and the transfer fit use the new table. |
| R2 target masks | PASS. High/low/plug views use t+k; storm starts use t. All 50 refit MAEs (two sources × five leads × five views) match the earlier independent forward-window calculation within 1.12e-16 ft. |
| R3 split leakage | PASS. Source inspection confirms target-before-split selection in M2, M3, transfer and forecast refits. Theta uses training-period observations. The independent purged refit matches the repaired author implementation. |
| R4 claims/construction | PASS for corrected research claims. Erratum withdraws guaranteed live gain, incorrect forecast age, and oracle-as-bound wording. Production-policy replay and actual availability are explicitly future candidate gates, not completed evidence. |
| R5 chronology | PASS as an honest correction. Both historical rounds are exploratory with unverified predeclaration. The uncommitted session account is the author's statement, not independent proof. Method deviations are disclosed; the new candidate plan has a prior commit. |

Corrected historical results support continued development: 24-h GFS refit
MAE 0.289 -> 0.237 ft overall and 0.477 -> 0.355 in storm starts; target
low/plug comparisons improve. The 6-h ECMWF plug-band exception is disclosed.
Canonical-UTC round1 reproduces the stronger future-forcing signal and the
modest past-forcing storm benefit that still fails the plug-band criterion.
The transferred GFS fit remains worse after alignment, supporting source
matching rather than an assertion that transfer can never work.
The UTC decay rerun retains support for tau36; it is not best in every subset
at every lead, and neither reply nor this close-out should be read that way.

Quality limits remain: the UTC water archive now retains observation flags,
but the studies do not filter them. Meteorology flags and actual historical
publication/retrieval availability are not recovered by this repair. Verified
hourly history and recent preliminary forecast-era water are distinct inputs.
No fresh bulk source download, independent new holdout, rare-event safety or
observed street-flood skill is claimed. These limits are tracked in the
candidate's precollection source/QC contract and evaluation plan.

## Small documentation corrections

The immutable round02 reply's “-5/-4” clock wording describes the reverse
conversion: local labels become UTC by ADDING five/four hours. Its day2
47–18 h age example applies to a 30-h window; a 48-h window spans 47–0 h.
A new research-plan addendum records those clarifications; the r2 forecast
script's docstring now says both explicitly. The UTC fetcher's docstring
names the timezone encoded in the Parquet timestamp schema rather than
claiming a separately written metadata key. Report values are unchanged.
The current model spec's “past wind did not help” summary is qualified to
match the repaired evidence, with no formula/constant/version change.

## Owner decision and next work

John explicitly approved Codex's recommendation and Claude's shadow-only
proposal in this session. BACKLOG DECISION `wind-shadow-open-meteo` records
approval to develop the Open-Meteo `gfs_seamless` wind/pressure candidate and
log hourly shadow predictions. No further source-choice permission is owed.
Displayed forecasts, maps, widget, rain outputs and alerts stay on production.

The [updated candidate plan](../../history/plans/2026-09-24-wind-term-candidate-plan.md)
incorporates the authorized recommendation and makes the initial evaluation
more precise BEFORE any shadow implementation/collection:

- Exact live/training construction, pressure as well as wind, forecast timing,
  raw provenance, cached production mean, complete-input fallback and bounded
  shadow execution; no assumed equivalence between previous-runs and live data.
- Versioned coefficients, manifest, evaluator and missing-data/clock rules
  frozen before the first eligible trial record. No test-period refitting.
- At least 60 days AND five completed storm episodes; deterministic endpoint,
  target maturation, paired denominators and fallback/coverage reporting.
  The 48-h decay extension is labeled an offline baseline, since the published
  core curve reaches about 30 h. Production-version changes get separate cohorts.
- Low/high/plug, storm, underprediction and rain-tank comparisons; NWS/P-ETSS
  comparisons do not authorize wholesale replacement merely because decay loses.
- A bounded NDFD archive feasibility check, including grid/issuance matching
  and pressure availability, instead of assuming no NWS archive exists.

The existing pass tolerances are retained; the implementation manifest must
complete the enumerated details before collection. Three wet events are not
an automatic rain-skill pass, and 60 days/five storms are not a promotion date.
Approval covers development/shadow collection, not a paid subscription or
production activation. Implementation and the prospective evaluation remain
open work; neither exists on the reviewed main yet. Their eventual review is
separate from this closed research-correction audit.

Verification for this work unit: corrected study reruns, independent score
comparison, source/diff review, local links and artifact gate. No runtime,
forecast JSON, canonical ledger, alert state or generated page was edited;
site regeneration and a production-model replay are unnecessary for these
documentation/research-comment changes.
