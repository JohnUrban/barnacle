# Round 03 — c2 verification: HOLD merge; audit remains OPEN

**Reviewer:** Codex. **Date:** 2026-09-24, 10:56 EDT.
**Candidate:** `wind-shadow` at `fe7e1ebc9`, candidate `wind-shadow-c2`.
**Reply verified:** [02-repairs-reply-claude.md](02-repairs-reply-claude.md).
**Production checkout:** `423566856`, v0.10.6; candidate not merged.

The repair is substantial, and the refit reproduces. It is not yet ready to
merge or begin official collection. R1, R2 and the mean-construction portion
of R4 are resolved to the extent below. R3/R5/R6/R7/R8 still have specific
implementation gaps. No feed-choice decision is needed from John. Repair the
candidate under the existing shadow-only authorization; no production
promotion is being considered.

All mutation probes ran in temporary copies or temporary output directories,
with mocked networking. No actual trial records, live alerts, candidate-file
edits or production forecast changes were made by this review. Some synthetic
records deliberately say `collection: official` to exercise the guard; they
exist only in scratch and are not trial opportunities.

## Confirmed repairs and independent checks

- **R1:** six-hour onset and 48-hour quiet-tail counters now reset across
  missing/invalid hours, and the actual completion time determines the cutoff.
  The original sparse case returns INCONCLUSIVE at 30/1,464 coverage, with
  zero scorable storms. The new 80% coverage and five adequately scored storms
  at both 24/30 h are declared before official collection. The fixed cutoff
  and subsequent maturity requirement remain intact.
- **R2:** bounded timeouts retain all 48 baseline/candidate-fallback values.
  Outcome parsing rejects missing/malformed flags and nonfinite values.
  Four records through 03:30 now mean four opportunities, zero missing.
- **R4:** independently rebuilt all **48 coefficient vectors**, sample counts
  and rounded baseline/candidate MAEs using the verified-hourly mean policy
  and QC-filtered pressure. Maximum coefficient difference versus the
  eight-decimal manifest: **4.961e-9**. All five dataset hashes match.
  The 24-day verified-data lag is explicitly an approximation measured once,
  not reconstructed historical availability. The live pressure substitution
  and nominal-hour convention are also now disclosed. These qualifications
  must remain attached to “exact construction” shorthand.
- All 698 successful Open-Meteo raw-run hashes and every extracted value
  match the retained table; route A's equivalence statistics reproduce.
  Spring/summer-only fitting still does not establish winter performance.
- **322 tests pass**, with the required GRIB decoder enabled. The one skip is
  the expected absence of an official trial log. Existing frozen replay tests
  pass unchanged. The unmodified candidate artifact gate passes. An initial
  incomplete scratch copy lacked test assets; after supplying those assets,
  the complete suite passes. That harness error is not a candidate defect.
- Production `_main_core` remains AST-identical to the original entry point
  at `e640f0a27` apart from the holder export. The shadow computation remains
  after production outputs/alert work, protected by the wrapper exception
  handler. This verifies code isolation there, not the gate behavior below.
- c1's retirement and reconstructed smoke record are described honestly.
  The original deleted bytes cannot be recovered or verified from their
  reconstruction. Starting c2 under a new identity avoids conflating them
  with its trial. Default local execution now performs no collection.

Evidence: [independent fit](round03-fit-results.json),
[rerun of the author's regression probes](round03-author-probes.json),
[independent boundary probes](round03-boundary-results.json),
[verification summary](round03-verification-summary.json).

## Remaining findings, in repair order

### R7 — P1: the actual publication command can still crash on shadow data

`forecast/check_artifacts.py:742–758` calls `shadow_log_report()` before the
production checks, without an exception boundary. `wind_shadow.validate_file`
parses valid JSON and then assumes it is a dictionary. Testing the **actual
CLI**, rather than only `check_artifacts()` as the unit test does:

| Shadow line in an otherwise clean temporary checkout | Command result |
|---|---|
| Truncated JSON | Warning, exit 0 — repaired |
| `[]` | AttributeError, exit 1 — still blocks publication |
| `null` | TypeError, exit 1 — still blocks publication |

This is a remaining route for the same original isolation failure. File-read
errors and validator/import exceptions also escape this supposedly nonfatal
path. No claim is made that the current writer normally emits an array; the
isolation contract must survive malformed shadow evidence.

**Required:** contain the entire shadow diagnostic path, validate top-level
types, and report failures without skipping or weakening production validation.
Test the CLI exit code for malformed JSON, valid non-object JSON and a read or
validator failure. Preserve the bad evidence and report it through isolated
shadow health/CI; do not delete it to make the production gate pass.

### R6 — P1: the freeze is checked in tests, but not enforced at execution

Record filtering now rejects a foreign manifest/runtime hash. However:

1. `wind_shadow.run` checks only `candidate_id` before writing. A temporary
   manifest with **tau changed from 36 to 999**, under the same c2 ID, writes
   a full `collection: official` candidate record. Its hash does not match
   FREEZE. The evaluator later rejects it, losing an opportunity; collection
   has already breached the promised freeze.
2. The evaluator prints its actual and expected SHA-256, but does not compare
   them before scoring. Appending a comment to the evaluator in a temporary
   mirror yields **different hashes, exit 0, and a normal interim verdict**.
   This probe uses a harmless comment; an actual methodological edit has the
   same missing enforcement.
3. `rain_tank_sensitivity` imports the current production tank implementation,
   constants and stage curve. These scientific dependencies are outside the
   frozen bundle. A later production change can change this supposedly frozen
   comparison without changing the evaluator or candidate identity.

**Required:** verify the frozen bundle before official collection and before
scoring; a mismatch must disable that shadow action with an explicit reason
while leaving production unaffected. Keep setup failures and the actual trial
start visible rather than shifting the first opportunity to the first later
valid record. Bind or preserve the numerical dependencies needed to reproduce
rain evaluation. CI matching file hashes is useful, but updating both a file
and its FREEZE entry is not itself proof that a post-start change has a new ID.
State and enforce the start/bundle boundary independently of future edits.

### R3 — P1: the new rain comparison drops initial storage and prior rainfall

`rain_tank_sensitivity` begins at the first future lead, calls the tank with
empty storage there, and never reads the archived `tank_init`. The production
series starts earlier (normally six hours before issuance). A forecast issued
during or after rain can therefore lose water already accumulated in the tank.

Independent synthetic example, using the real tank and stage curve:

- Archive starts at **04:00Z**, with 1 in/h rain through 10:00Z.
- Issuance is 10:00Z; rain is zero afterward. First compared target: 11:00Z.
- With that archived history, tank water at 11:00Z is **4.621 ft NAVD88**.
- The evaluator restarts at 11:00Z and returns no pluvial contribution; total
  baseline water is only the bay's **3.680 ft NAVD88**. It classifies the
  issuance as dry and reports zero wet events.

This is synthetic sensitivity evidence, not a measured street flood. It proves
that the evaluator can miss the drain/storage interaction it is intended to
check. Both forecast variants must begin from the same as-issued initial
condition, retaining preceding rain and a justified shared pre-issuance bay
history; apply the wind difference prospectively. Archive what is missing now,
while collection has not started. Score the requested landmark depths, not
only a hardcoded grate/curb summary. Keep fewer-than-three-wet-events results
explicitly descriptive.

### R3 — P1: “NWS/P-ETSS” comparison still mixes guidance with Barnacle's outlook

`pre_network_part` derives `nws_outlook_surge` from Barnacle's final outlook
`tide_navd88`, and the evaluator treats every non-null source as guidance.
That series can include advisory-adjusted NWPS, guidance-tail extrapolation,
observed decay and the typical-offset fallback (`outlook.py`'s source ladder).
The raw NWPS and P-ETSS values are not separate simultaneous comparators.

A synthetic record with source **`observed_decay`** is reported under
`vs_nws_petss_guidance` with **100% NWS/P-ETSS coverage**. The source name is
retained, but the enclosing label/coverage still misstates what was available.
The actual candidate snapshot also contains both `nwps` and `nws_product`
outlook cohorts; the latter is Barnacle's advisory-adjusted construction.

**Required:** preserve actual as-issued NWPS and P-ETSS guidance and its issue/
retrieval provenance separately, use explicit eligibility for each comparator,
and report availability against the same opportunity/target denominator.
Barnacle's final outlook is a useful additional comparator under its own name.
The replay archive already retains raw NWPS values; extend the join/retention
for the remaining guidance rather than treating a fallback as external advice.

### R5 — P2: availability bounds and raw pressure provenance remain incomplete

- `select_run` checks `meta_available <= issuance` only when the metadata init
  exactly equals the selected init. With metadata one cycle newer but its
  availability **after issuance**, the selected older run is accepted without
  evidence of that older run's actual availability by issuance. This proves a
  missing check, not that the old run was necessarily late. Use confirmed
  availability history or conservative fallback when the metadata cannot
  establish the required cutoff.
- Current-pressure fallback accepts a returned reading **one hour after
  issuance** because it checks only “not older than 60 minutes.” The request
  bounds normally prevent this; explicitly enforce `0 <= age <= 60 min` on
  returned data as well. The synthetic response is accepted with no pressure
  error. Count/deduplicate actual eligible hourly timestamps for the anomaly.
- Hourly pressure retains filtered values and a raw-body hash, but **not the
  raw body or rejected rows/flags**. A hash cannot recover those discarded
  inputs or independently establish that QC was applied correctly. The six-
  minute response is preserved; apply equivalent provenance to the hourly
  response. Outcome bundles preserve merged rows, but their per-response
  original bodies likewise are not retained alongside their hashes.
- The training surge table still has only `timestamp`, `observed_mllw`,
  `predicted_mllw`, `surge_ft`; the fit checks finiteness but cannot replay
  gauge QC. Pressure flags are fixed. Recover/declare the water-level QC
  construction rather than implying that all training QC was repaired.

These are bounded provenance/input repairs, not a request for another weather
provider. Historical availability remains an explicit unverified assumption;
the live trial must not be presented as retrospectively proving it.

### R8 — P2: dry-run exclusion depends on the environment being clean

Default-environment probes correctly produce zero shadow calls. Repeating the
same actual-main-flow probe with `BARNACLE_WIND_SHADOW_TRIAL=1` produces **one
shadow invocation for each of `--no-send` and `--dry-run`**. Neither flag is
checked by the wrapper. An explicit opt-in is a good repair, but it does not
implement the advertised exclusion of regeneration/test runs.

**Required:** carry parsed execution mode into the wrapper and exclude these
modes from official collection even when the environment opts in. Permit an
explicit preview only in its separate location/identity. Distinguish “merge”
from “first official record”: merge enables the workflow; the first properly
bound durable official record starts the trial. Do not equate the timestamps.

## Author handoff and scope

Keep the branch unmerged, repair the remaining items, and reply **04-…** with
finding-by-finding disposition and regression evidence. The current c2 official
period has not started, so corrections can update its pretrial bundle; do not
claim an implementation freeze is enforced merely because the hash table was
updated. Preserve the retired c1 record/reconstruction distinction.

No displayed curve, widget, rain model, alert policy or production version
needs changing to address this review. Its rain and guidance findings concern
the shadow trial's ability to support a future decision. The audit remains
**OPEN / HOLD before merge**, not a rejection of the candidate wind signal.

Reproduce independently against the candidate checkout:

```bash
python3 audits/2026-09-24-a3/verify_c2_boundaries_codex.py --repo /path/to/wind-shadow --out /tmp/c2-boundaries.json
python3 audits/2026-09-24-a3/verify_c2_fit_codex.py --repo /path/to/wind-shadow --out /tmp/c2-fit.json
```

The boundary script creates an isolated temporary mirror and uses no live
network. The fit script reads the retained local training datasets, needs
NumPy/pandas, and does not refit or write the candidate manifest. The separate
NDFD mapping experiment remains outside this verification; no prospective
skill or live-service availability was established.
