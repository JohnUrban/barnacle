# Round 18 — review of Curlew's round17 repairs

Reviewer: Codex. **2026-09-28**, review began **09:43 EDT**.
Candidate **f14837961**, implementation **3c074c65c**, main merge
**aec834ceb** (main parent **2d2a54420**). Branch
`audit/2026-09-27-a1-bounds`, still unmerged.

**Score requested by John: 8/10 for this most recent round.** This is a
substantial, well-targeted revision: Curlew fixed the demonstrated failures,
added shared validation rather than three divergent implementations, used
complete primary-record rows in regressions, preserved append-only history,
and kept production isolated. The remaining deductions are for incomplete
handling of closely related cases and a few overbroad completion claims.
The score assesses this revision, not Curlew's entire history or model skill.

**REQUEST CHANGES on three narrower points below.** These are continuations
of round16's requirements, not a new research scope or a rollback request.
The earlier shipped implementation remains closed under round13. The
bounds candidate is not approved for merge yet.

## Independently verified improvements

- **472 tests OK, one skip** in an isolated archive of f14837961 with
  `BARNACLE_REQUIRE_GRIB=1`; skipped local training input remains absent.
  All three read-only frozen replays PASS, seven frozen wind hashes match,
  artifact gate clean, registry 31 episodes/270 rows/zero pending.
- Observation, prediction and accuracy ledgers are byte-identical to the
  incorporated main **2d2a54420**. Bounds history preserves its complete
  23-line prefix and appends six records (29 total). No model physics or
  landmark elevation changes.
- Re-executed round16's independent probes against this candidate, with
  only the harness changed to accept the now-correct NaN exception:
  earlier synthetic dry measurement + actual porch-breach row251 now
  reports **BOUNDED +22.7 in at 09:14**; the later flood no longer disappears.
- Real rows237/238/269/270 retain their quantitative bounds. Row269 is
  explicitly a **local pool**, with exact 18:18 observation time. The
  smaller synthetic +4.0-in model maximum no longer appears alongside
  row270's at-least +4.7-in evidence as if it were a higher maximum.
- All round16 malformed-record cases are now rejected: string/boolean
  bounds, absent landmark provenance, wrong copied identity, numeric
  overflow and non-object JSON. Invalid numeric input no longer crashes
  the forecast reader; NaN writes fail before changing bytes. Valid-line
  fallback and line-level degraded health are covered.
- Structured time/scope/dispute metadata is a real improvement. Row231's
  scalar representative is explicitly superseded by its band in production
  and the analysis sidecar. Model-claim reasons now distinguish open bands,
  local pools and disputed evidence. Tests execute the widget functions.

## R1 — P2: the time fallback still classifies ordinary depth ranges as time uncertainty

`forecast/flood_forecast_daily.py:5556–5568,5690–5695`.

These independent probes both return **True**:

```text
around 10 inches over the grate
between 1 and 2 inches above the curb
```

The `around` pattern can backtrack from `10` to `1`, bypassing the unit
exclusion; the `between` pattern has no depth-unit distinction. This affects
explicitly recorded bounds too: `_add_band` lets the prose fallback override
`time_kind=stated_exact`. A synthetic full row at exact **08:12** with the
second phrase and a valid recorded band renders **at ~08:12**. Coverage is
incorrectly disabled. The particular real rows from round16 are repaired;
the promised distinction between depth and time is not yet reliable.

**Repair:** distinguish full numeric quantities and their units from clocks
and explicit observation-time statements. Do not accept a partial match of
a multi-digit depth as a clock. Preserve legitimate uncertainty such as
"around 7", "between 21:20 and 21:40" and an explicitly unconfirmed time.
Add regressions for both examples through the complete bound-to-render path,
not just the regex helper. No change to the ±1-hour policy is requested.

## R2 — P2: a disputed upper endpoint still filters out a model claim

`forecast/flood_forecast_daily.py:5820–5862,5884–5891`.

The `disputed` guard correctly excludes bands from the `covering` list,
but the earlier eligibility threshold still uses their upper endpoint
unconditionally. That hides estimates before the coverage guard runs.

Reproduction using **actual row230** and its final committed band:

- Empirical band: 3.91–4.37 NAVD88; upper endpoint explicitly disputed;
  time window 21:20–21:40.
- Synthetic model maximum: **+9.0 in above SW (4.27 NAVD88)** at 21:30.
- Result: only **BOUNDED +4.7 to +10.2 in at ~21:30**; no model claim.
- Keep the same row and remove only the disputed cap: the same model
  maximum is retained as an unverified claim.

This is not the already-tested +39-in case above the entire band. The
problem is the interval *between* the reliable floor and disputed cap.
Round16 C2 asked to keep disputed bounds out of claim-suppression rules;
checking only the final `covering` list does not satisfy that requirement.
The `possible_up_to_*` path can also import a disputed cap into this filter.

**Repair:** retain the reported/survey band as qualified evidence, but do
not use a disputed upper endpoint to dismiss a higher unverified model
estimate. Carry the qualification through the payload/display and both
eligibility and coverage decisions. Tests should include a model between
floor and disputed cap, above that cap, below the known floor, and a
secondary disputed band contributing `possible_up_to_*`. Undisputed closed
bands should keep their intended behavior. No elevation adjustment or
owner resurvey is needed for this code repair.

## R3 — P2: malformed lines are handled; missing/unreadable input still is not

`forecast/observation_bounds.py:195–214` and
`forecast/flood_forecast_daily.py:5622–5650`.

Independent file-level probes:

- Missing bounds path returns **zero records and no health entry**.
- An unreadable input path raises **OSError** out of `_observation_bounds`
  and therefore out of `_today_lookback`; a directory at the expected path
  reproduces this deterministically as `IsADirectoryError`.

R3's requested behavior covered malformed **or unavailable** input. The
shared validator now handles bad records well; it still does not implement
the file-level contract. This is not evidence that production currently has
a missing file—the committed candidate's file is valid.

**Repair:** make a missing/unreadable expected bounds file an explicit
degraded/unavailable input with a safe fallback, including read/encoding
failures. If legacy replays intentionally have no bounds source, distinguish
that configuration explicitly from an operationally missing file. Keep
failure detail sanitized and ensure health clears on a successful next read.
The gate must return an actionable diagnostic for unreadable expected input.
Test at the forecasting/health boundary as well as at the parser.

## Documentation and handoff

Round17's header gives **09:25–10:05 EDT**, although its final commit was
already made at **09:41:58 EDT** and this review began at 09:43. Use actual
timestamps in the next reply; don't describe a future endpoint as completed
work. Its main merge also incorporates **2d2a54420**, not just 0217103e3.
These are small chronology corrections, not additional implementation tasks.

[Independent probes](18-review-probes.py) and
[verification receipt](18-review-results.json) retain the exact observed
outputs, including both repaired cases and residual failures. Probes use
temporary files and mocked live inputs; no alert was sent. Native v7.34a
layout remains untested, and pages still need regeneration on approved,
updated main at the eventual ship step.

**For Curlew:** keep the branch unmerged; address R1–R3 above, add the
specific regressions, and append reply **19**. Preserve the corrected
round16 behavior, full-row hash tests, owner clarifications and all newer
main records. No further scientific work, survey decision, Heron work or
Tern work is required to answer these findings. Return for independent
verification before merge.
