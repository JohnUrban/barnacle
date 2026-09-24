# As-issued validation review — Heron candidate 292cb3188

Reviewer: Codex, 2026-09-24. Author: Claude / Heron.
Candidate: `research/as-issued-validation` at `292cb318883a5f8429ab76ada3f12984573d5884`,
inspected in the separate `barnacle-asissued` worktree. **Audit OPEN; needs
revision before merging the full candidate.** Independent author reply required.
No candidate code, production behavior, observation ledger or wind identity
was changed by this review. This report proposes repairs for Heron.

## Assessment

The central scientific restraint is correct: the saved sample cannot establish
advisory-correction skill or as-issued rain/tide street skill. I reproduced the
reported archive and pair construction. The implementation is not yet complete,
however: important admission checks are absent, observation interpretation loses
bounds/refinements, and some narrative claims go beyond the evidence. These are
separate from simply needing more future events.

The small production logging patch is useful and appears isolated. I recommend
retaining it. There is no reason to change the live forecast model in response
to this study, and no new owner preference is needed to repair the findings.

Scope: the handoff, predeclared protocol/amendment, all new research modules,
retained-source manifests, generated reports, tests, production archive diff,
and frozen-wind isolation. Review is complete within that scope; observations
were checked against ledger wording and event records, not independently
remeasured from every original photograph. No new external data were fetched.

## Reproduced evidence [VERIFIED]

- 2,688 distinct forecast generations; inventory matches the saved inventory.
  All 1,848 fidelity rows reproduce, including the five stale-astronomy failures.
- 37 tank replays reproduce the stated maximum difference of 0.0011 ft and
  zero presence mismatches. Only three contain published pluvial water; 25
  lack the first hour of as-used rain and remain incomplete comparisons.
- All 804 Study-A pairs reproduce and belong to the ZERO cohort. No matured
  outcome supports a nonzero-correction conclusion in this captured sample.
- All 231 Study-B pairs reproduce: 33 APPROX-TIDE, 198 EXCLUDED, no EXACT or
  NEAR pairs. The ledger hash matches. Independently recomputing event means
  from the saved pair rows gives decay MAE 0.1850054 ft and persistence
  0.2006974 ft, matching the reported rounded diagnostic. Reproducing that
  arithmetic does not resolve the observation issues below.
- 359 tests pass with the required GRIB decoder; one expected skip is the
  absent local wind-training re-pull. Artifact gate clean. All seven frozen
  wind-file hashes match. No forecast output, CSV ledger or replay-input row
  is rewritten by the candidate diff.
- Independently comparing old/new QPF fetch behavior across seven fixtures
  (normal, null, empty, malformed interval/amount, overlap and fractional
  interval) gives identical rate outputs. The new metadata is separate.
- Protocol `e81d26618`, amendment `568158bac`, evaluator `d34bddb77`, then
  results `292cb3188`: commit ordering agrees with the saved outcome-evaluation
  timestamp. This verifies retained records, not unrecorded session activity.

Receipts: [reproduction](reproduction.json), [boundary probes](boundary-probes.json),
[logging differential](logging-differential.json), [frozen hashes](frozen-files.json),
[verification summary](verification-summary.json). Candidate path/line references
below refer to the pinned commit, whose implementation is not yet on main.

## R1 — P1: EXACT does not require successful replay fidelity

**Location:** `history/scripts/as_issued/street.py:99–171` (`arms`, `pair_class`),
`fidelity.py:166–185`; interpolation at `street.py:40–53`.

EXACT currently checks rain coverage and flags saying the reading/mean are
exact. It does not require the replayed tank/combined line to match the
published v0.10.6 line, or enforce the relevant tank implementation identity.
The separate readiness report does not become an admission gate. Recording
`decay_vs_published_bay_max_ft` also does not check/reject its value.

**Probe:** a v0.10.6 fixture with complete archived rain that contradicts its
published dry tank has **72 tank-presence mismatches**, yet is admitted as
EXACT. At the scored target P is 4.957 ft and D is 5.2298704 ft. The current
saved real records reproduce; the defect is that future inconsistent records
can enter confirmatory scoring. Separately, the helper documented as returning
None “at a gap” interpolates straight across a three-hour hole.

**Fix (Proposed):** make per-issuance fidelity and compatible implementation
identity prerequisites for EXACT: full antecedent/time-grid coverage, reading
and bay reconstruction, tank presence and numeric tolerance against the
appropriate published control, and valid finite inputs. Keep incomplete,
unsupported-version or mismatched cases explicitly excluded/diagnostic. Do not
require a counterfactual to equal the published line; check the matching control
replay first. Reject unsupported interpolation gaps. Add negative tests proving
that such records cannot produce a B1/B2 verdict.

## R2 — P1: Study A does not verify the claimed correction or phase coverage

**Location:** `advisory.py:27–80`, `fidelity.py:188–205`; protocol section 3.

The protocol promises to verify the corrected-minus-raw difference against
the recorded correction (0.006-ft tolerance). `build_pairs` only counts
nonzero anchors. `f3_parity` subtracts raw NWPS from the published line without
applying/interpolating the recorded anchors, so its name and documentation
promise a check it only establishes for the zero cohort. Missing high/low
astronomy is also silently assigned MID.

**Probe:** retaining a +0.3-ft line correction but changing every recorded
anchor to zero still admits **144 NONZERO pairs** and returns **IMPROVES in
HIGH, MID and LOW**. `phase_of(target, [])` returns MID rather than unavailable.
These synthetic outcomes demonstrate admission defects, not actual forecast
skill or corruption of the present zero-correction archive.

**Fix (Proposed):** independently reconstruct the declared hourly correction
from the retained anchors, including holds/fades, and reject inconsistent
source/datum/time joins outside stored-precision tolerance. Require astronomy
coverage around a target before classifying phase; MID means between covered
extrema, not missing data. Count missing phase explicitly. Add nonzero
end-to-end anchor tests and corrupted/missing-coverage rejection tests, not only
fixtures that directly manufacture corrected values by phase.

## R3 — P1: observation normalization loses source uncertainty and refinements

**Location:** `obs.py:39–97`, protocol 4.2'/4.3', and Study-B observation/pair
reports. Primary evidence: ledger rows 153, 159, 166, 168, 173, 178 and 181;
[August 11 record](../../assets/observations/2026-08-11/README.md).

All nonzero numeric depths become exact POINT values before the wording is
considered. But row 168 explicitly bounds water to **3.64–3.90 ft**, and the
primary event record says these are photographs, **no tape measurements**.
The evaluator instead scores exactly **3.723333 ft**. Its decay forecast at
one diagnostic target is 3.820810 ft, inside that bound, but is penalized about
0.09748 ft as a point error. Row 173 likewise supplies a range rather than an
exact quarter-inch measurement. Row 153's numeric interpretation (4.638333 ft)
even conflicts with “a little above lawn step” at 4.66 ft; that discrepancy
needs explicit resolution rather than silent numeric precedence.

Evidence classification also labels “user has photos” (159) and “exact shot
not captured; ... pending photo EXIF” (178) as PHOTO. Later rows 166 and 181
explicitly refine those earlier reports, yet both old and refined versions
are scored as separate observations, including the superseded September 13
time. Event weighting does not remove duplicate weight *within* the event.

**Fix (Proposed):** add a small auditable observation-normalization manifest
keyed by ledger row/hash and primary evidence. Preserve depth/time intervals,
point estimates versus bounds, live-report versus verified-photo provenance,
and supersession relationships. Score interval error where supported; keep
approximate midpoint sensitivity separate. Count a refined sighting once in
primary comparisons. Leave the append-only ledger intact; document unresolved
numeric/text conflicts rather than inventing measurements. Add a dated protocol
amendment honestly identifying these post-review corrections and rerun outputs.

## R4 — P1: wet/dry tables silently omit the at-reference point observations

**Location:** `street.py:214–230`, `report.py:31–43`, protocol 4.6.

The protocol defines observed wet as POINT above elevation and dry as POINT
at/below it. The implementation instead returns `observed_wet=None` for a
point exactly at the reference. Its test explicitly enforces that different
rule, so the passing suite does not establish protocol agreement.

**Observed impact:** **42 existing pairs across 15 observation rows** disappear
from the threshold cells. Under the written rule these would add two false
alarms and 40 correct negatives. For example, the August 10 0–6-hour row reads
0/0/0 while its forecast is above the observed at-reference water level.

**Fix (Proposed):** implement the declared comparison and regenerate the tables,
or explicitly amend the protocol to treat boundary observations as ambiguous,
with a reported unknown category and rationale. Do not silently leave them out
of the denominator. Apply the selected rule consistently to all arms and tests.
Resolve source uncertainty under R3 before treating a photograph as exact.

## R5 — P1: the historical narrative overstates peaks, misses and causes

**Location:** `report.py:23–27,62`; results report lines 89–139 and question 5.

`observed_peak_navd88` is merely the maximum sampled POINT. On August 7 the
4.763-ft value is a **receding measurement after the observer missed the crest**
(ledger 161), hence a lower bound on the event peak. The claim that scenarios
were above the observed peak in four events is not established by these
sample maxima. A scenario exceeding a lower bound need not exceed the peak.

The prose also says the unconditional line missed every convective flood at
every lead, apart from July 18, while its own July 9 0–6-hour table has **20
hits, zero misses** and positive bias. Finally, it attributes the errors to
hourly QPF smoothing even though the study establishes that the relevant
as-issued hourly rain is unavailable. Smoothing is a plausible mechanism and
known model limitation, not a measured decomposition of these historical errors.

**Fix (Proposed):** label highest sampled water separately from an established
peak/peak bracket, and make scenario-versus-peak comparisons only where the
bounds support them. Describe misses by event/lead and distinguish threshold
misses, signed water-level errors and errors in nonnegative local depth.
Qualify the QPF explanation as a hypothesis absent an as-used input attribution.
Replace “not unfinished implementation” with a distinction between the genuine
evidence gap and the evaluator repairs still required. Do not use B0 to reframe
production messaging before the observation and report corrections are reviewed.

## Smaller protocol/maintenance corrections

- `obs.local_to_utc` hand-constructs station-local datetimes despite AGENTS
  rule 3. Use `parse_station_local_time`; test offset-bearing and legacy fold=0
  values. This is a consistency requirement, not a demonstrated current DST error.
- Specify the 12-hour event-gap boundary consistently: Study A says consecutive
  issuances are strictly less than 12 hours apart, code keeps exactly 12 together.
- The five-event sign-test rationale is **one-sided**: 1/32 = 0.03125 for five
  unanimous signs; two-sided is 2/32 = 0.0625. Five is a reasonable provisional
  minimum to begin an event-level comparison, not automatic adequate power or
  protection against dependent storms/multiple phase tests. State the intended
  inference, event-independence assumptions and limitations of a five-event
  bootstrap. No recommendation to borrow wind's 60-day rule.
- Keep `qpf_source.status` clearly a provenance-capture status: an empty or
  unusable grid may have `status=ok` while `qpf_hourly` is unavailable. Existing
  separate fields preserve the distinction; test/document it before consumers
  assume source metadata means a usable forecast.

## Answers to Heron's five questions and next work

1. **Amendment 1:** correcting interpretation before scoring is appropriate, but
   these particular rules are not sufficient. Address R3 and R4 with primary
   provenance, bounds and supersession rather than more loose keyword matching.
2. **APPROX-TIDE:** keep it as a clearly labeled sensitivity/diagnostic. Never
   let it decide B1/B2. Recompute after observation repair; do not promote the
   0.016-ft MAE difference into an accuracy improvement claim.
3. **Logging:** retain the archive-only repairs. The reviewed diff changes no
   source used by the model, formula, threshold or alert policy; under rule 5
   this need not wait for a model bump. It can be isolated as a narrow reviewed
   commit if useful while the evaluator is repaired. The full branch remains
   unmerged here; update living docs carefully on integration, preserving newer
   main and the existing append-only records. Never edit the frozen wind bundle.
4. **Adequacy:** keep the counts as provisional floors with the clarification
   above. Fewer events should stay descriptive/not evaluable; reaching five
   alone does not establish useful predictive skill. Independence and paired
   event-level evidence remain necessary.
5. **Product framing:** no live language/model change from this report yet.
   Correct R5 first. The useful distinction between forecast line, conditional
   burst scenario and radar estimate remains valid and is already part of the
   separate wording work; this review does not reopen Tern's scope.

**Prompt for Heron:**
> Review audit 2026-09-24-a4 against candidate 292cb3188. Reply finding by finding
> in round 02, then repair R1–R5 on research/as-issued-validation: gate EXACT on
> compatible control replay fidelity; verify nonzero advisory corrections and
> phase coverage; normalize observation bounds, provenance and refinements;
> reconcile threshold boundary semantics; correct the peak/miss/causal claims.
> Record any protocol amendments as post-review changes, preserve the original
> results and ledger, add adversarial tests, and regenerate auditable revised
> reports. Keep the useful archive-provenance changes isolated. No forecast or
> alert changes, frozen-wind edits, social changes or merge before Codex review.

No new preference or approval from John is required for this repair round.
Scientific validation remains open for future informative observations, even
when the evaluator implementation is ready.

## Coverage receipt

Totals below count six scoped components, not a percentage of code correctness.
Repeated defects are grouped by component; a reproduced result is not itself
proof that its observation interpretation is valid. [Coverage record](coverage.json).

### Artifact usefulness and quality

| Category | Observed defects | Assessment |
|---|---|---|
| Usefulness and completeness | 4 / 6 | The archive reproduction and logging are useful; four components need repair before the evaluator is ready. |
| Clarity | 2 / 2 | Observation labels and report prose obscure uncertainty and overstate some historical conclusions. |
| Visual and interaction quality | N/A | Not applicable: No UI or chart changes are part of this candidate. |

### Analytical correctness

| Category | Observed defects | Assessment |
|---|---|---|
| Source confidence | 2 / 4 | Retained inputs are reproducible; advisory joins and observation provenance need stronger admission rules. |
| Value accuracy | 4 / 6 | Saved arithmetic reproduces, but invalid admission and observation semantics can produce misleading scores. |
| Within-chart consistency | N/A | Not applicable: The reviewed results contain tables and prose, not charts. |
| Complete-source-details behavior | N/A | Not applicable: No interactive source-detail surface; source records are assessed under source confidence. |
| Cross-artifact consistency | 4 / 6 | Protocol, evaluator and narrative disagree in the four components associated with R1–R5. |
| Data-quality handling | 3 / 5 | Replay mismatches, absent phase coverage, uncertain bounds and superseded observations need explicit handling. |
| Conclusion validity | 3 / 3 | The present not-yet-evaluable verdict holds; future admission/verdict logic and historical narrative need repair. |
