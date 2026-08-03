# Comprehensive repository audit — round 01

Audit: `2026-08-03-a2`  
Auditor: OpenAI Codex (5.6 Sol High)  
Repository state: `70324996` (`main` and `origin/main` synchronized at audit start)  
Date: 2026-08-03, America/New_York

## Verdict

Barnacle is a serious, evidence-rich hyperlocal flood-forecasting system, not
a toy weather dashboard. Its best properties are unusually good: raw event
dictation is preserved beside derived claims; forecasts and verification
records are append-only; model limitations are stated plainly; external-input
failures are usually surfaced rather than converted to zero; alert delivery is
transactional across three independent rails; and a small offline suite plus a
strict-JSON publish gate catches several important regression classes.

The audit nevertheless found **five high-severity concerns**, seven medium or
lower concerns, and two currently incorrect canonical/public facts. The most
important new correctness finding is a pervasive split between UTC runner time
and the station's local calendar day. It has already produced demonstrably
wrong user-facing “today/tonight/tomorrow” prose in production history and also
resets the nowcast's day-max memory at 8 PM EDT/7 PM EST. The other high items
are stale-radar freshness, destructive recovery of transactional alert state,
verification paths that exclude canonical data/model artifacts, and the
already-acknowledged inability of GitHub's best-effort schedule to provide a
10-minute live-nowcast service level.

No model retuning is recommended as part of these repairs. Correctness,
provenance, delivery safety, and reproducibility should land first.

## Scope and method

I read the repository governance and operational documents first:
`AGENTS.md`, `HANDOFF.md`, `BACKLOG.md`, `PLAYBOOK.md`, and
`audits/README.md`. I then inspected production forecast/nowcast code,
workflows, tests, model specifications and fitting scripts, generated site
artifacts, all canonical CSV ledgers, the August 3 event primary record, and
the relevant git history. The public GitHub Actions API was sampled for recent
run cadence.

Checks run:

- `git fetch origin`; local `HEAD` and `origin/main` both resolved to
  `70324996`.
- `python -m compileall -q forecast tests history/scripts analysis` — pass.
- `python -m unittest discover -s tests -q` — **50/50 pass** in 0.021 s.
- `python forecast/check_artifacts.py` — **publish gate clean**.
- Strict YAML parsing of all workflow files — pass.
- `git diff --check` excluding the active street-elevation sweep — pass.
- Canonical-ledger profiling for shape, duplicates, chronology, arithmetic,
  provenance stamps, and composite keys.
- Git-history reconstruction for the local-day bug, August 3 observation
  timestamp, and nowcast day-max regression.

I did not run a live forecast or send alerts because those are externally
mutating production actions. I also deliberately excluded the user's active,
uncommitted town-map sweep in
`history/data/highlands_street_elevations.csv` (1,197 added rows) from audit
conclusions and made no changes to it.

Severity meanings used here:

- **High:** can materially misstate live flood state, compromise alert
  delivery, or let unsafe production state bypass intended controls.
- **Medium:** meaningful integrity, reproducibility, security, or operational
  weakness without evidence of an immediate false live alert.
- **Low:** maintainability, documentation, privacy, or future-risk issue.

## Findings

### H1 — Station-local “today” is still computed from the UTC runner in many production paths

**Status: confirmed with production git history.**

The code correctly introduced `STATION_TZ` and `_station_local_now()`, but the
migration is incomplete. `forecast/flood_forecast_daily.py` still contains
many bare `dt.date.today()` and naive `dt.datetime.now()` calls in
user-visible or day-scoped logic, including:

- accuracy roll-forward (`update_forecast_accuracy`, line 869),
- seasonal context (1786),
- percentile month selection (2594/2618),
- day cards (2704),
- `plain_language_summary` (4096),
- landmark/spot-check text (4270–4496),
- email date/time (4585, 4691, 4810),
- past-tide/chart windows (4880, 4984, 6925),
- per-tide archive generation time (8445), and
- landing-page day scope (9000/9005).

GitHub's Ubuntu runner uses UTC and the workflow does not set `TZ`. This is
not theoretical: commit `436811f7`, generated at `2026-08-02T00:39:56Z`
(8:39 PM EDT on August 1), contains this production summary:

> 10:25 PM Sat Aug 1 night ... 10:57 AM this morning ... 11:06 PM tonight

At that moment, 10:25 PM was still “tonight” and the following morning was
“tomorrow morning.” The preceding 23:20 UTC run (`40c4525f`) labeled the same
tides correctly.

The nowcast repeats the same defect more consequentially. `_write()` derives
its logical day from `generated_utc[:10]` (`forecast/nowcast.py:98-124`), so
day-max memory resets at 8 PM EDT or 7 PM EST, not local midnight. Tests encode
the UTC-day behavior as intended (`tests/test_daymax_and_dispatch.py:51-60`).
`_today_lookback()` then compares station-local `today` with a UTC
`generated_utc` prefix and manually subtracts four hours
(`flood_forecast_daily.py:5757-5769`), which both drops late-evening day-max
state and fails during standard time.

**Impact:** incorrect TODAY/TOMORROW labels, wrong month/day context near UTC
midnight, premature nowcast day-max reset during evening storms, and loss of
the automatic “so far today” witness exactly when a flood continues past 8 PM.

**Recommendation:** establish one injected, aware station clock and derive
every operational `local_now`, `local_date`, archive date, and display time
from it. UTC should remain the storage/transport timestamp only. Replace the
manual `-4` conversion with `ZoneInfo`. Add boundary tests for 19:59/20:00 EDT,
23:59/00:00 local, EST, both DST transitions, month-end, and year-end. Set
`TZ=America/New_York` in the workflow as defense in depth, not as a substitute
for explicit code.

### H2 — A newly written nowcast can make old or incomplete radar look “live”

**Status: confirmed code path; current artifact happened to be fresh.**

`latest_frames()` selects the newest timestamp present in the MRMS directory
listing but never compares it with current UTC (`forecast/nowcast.py:166-174`).
`run()` silently skips any frame that fails to download/decode and accepts any
non-empty remainder (`252-261`). The published payload records frame times as
`HH:MM` only (`270-271`), without a date, newest-source timestamp, source age,
expected-frame count, or successful-frame count. `_write()` then supplies a
fresh `generated_utc`, and the site decides “live” solely from that workflow
timestamp (`flood_forecast_daily.py:9170-9181`).

If the MRMS listing stalls while remaining reachable, or if ten of eleven
frames fail but one old frame succeeds, Barnacle can republish that input with
a fresh generation timestamp and render it as live radar. The projection also
holds the last observed rain rate constant for 45 minutes
(`nowcast.py:287-299`); that can be a useful conservative scenario, but it is
presented without a quality/assumption field.

**Impact:** stale or sparse radar can override the TODAY headline as observed
truth during a live event.

**Recommendation:** publish full ISO timestamps plus `source_latest_utc`,
`source_age_min`, `frames_expected`, `frames_succeeded`, coverage span, and a
quality/degraded reason. Reject or visibly degrade a latest frame older than a
small explicit limit and require a minimum coverage threshold before setting
`active`. Make the site freshness decision from the source timestamp, not job
write time. Label the 45-minute hold assumption and test stale-listing,
partial-frame, empty-listing, cross-midnight, and clock-skew cases.

### H3 — The self-healer deletes transactional alert history and can create duplicate alerts

**Status: confirmed code path.**

`forecast/heal_tree.py:49-61` deletes `data/alert_state.json` whenever it is
unparseable or contains conflict markers, while the module documentation says
all such caches regenerate or degrade gracefully. Alert state is not an
ordinary cache: it is the acknowledgement ledger for the last delivered
signature/channels and the station-local daily send cap. Deleting it makes an
already-delivered warning look new and resets the cap.

The healer also repairs `predictions_log.csv` with raw line filtering/sorting
rather than strict CSV parsing (`29-47`) and deletes any marked file anywhere
under `docs/` (`63-70`), including historical artifacts that the next run may
not regenerate.

**Impact:** a merge artifact can turn recovery into repeated email/SMS/ntfy
delivery, exceed the daily cap, or erase historical site artifacts. The
recovery operation can therefore be more harmful than a failed publish.

**Recommendation:** treat `alert_state.json` as transactional state: fail
closed, quarantine the damaged file, and recover a validated copy from the
exact `origin/main` blob or a known-good ancestor. Never silently reset it.
Parse/union the prediction ledger as CSV using its composite key and schema.
Only delete artifacts explicitly proven to be regenerated in the same run;
otherwise restore or quarantine them. Add healer tests for all three classes.

### H4 — CI and the publish gate leave important production changes outside their control boundary

**Status: confirmed workflow configuration.**

CI runs only for changes under `forecast/**`, `tests/**`, and workflow files
(`.github/workflows/ci.yml:3-14`). Direct changes to the canonical `data/**`
ledgers, `model/**`, `history/data/stage_storage_curve.csv`, map inputs, and
generated `docs/**` can land without any CI job. The public workflow history
had only six recent CI runs, all green, despite continuous repository writes;
that low count is consistent with the narrow path filter.

The publish gate is valuable but mostly structural. CSV validation checks
header and row width only (`check_artifacts.py:55-78`); it does not validate
timestamps, enums, numeric domains, required outcome fields, landmark keys,
lead-time arithmetic, or chronology. Forecast provenance checks parse
`generated_utc` but do not reject stale or future generations
(`95-146`). There is no nowcast schema/source-freshness validation and no
alert-state schema validation.

This gap already has a concrete result: the invalid future observation in H6
passes both the tests and publish gate.

**Impact:** malformed or semantically false canonical data/model inputs can be
pushed to `main` and Pages before the hourly bot happens to run a gate; some
changes may never exercise behavioral tests at all.

**Recommendation:** remove the CI path filter, or expand it to every consumed
data/model/site input and explicitly skip only known bot-generated commits.
Keep a lightweight artifact/ledger job for human changes. Extend the gate with
domain schemas and invariants, nowcast/alert-state schemas, source and
generation freshness, required artifact existence, timestamp bounds, and
cross-file model/version consistency. Add fixtures proving each rejection.

### H5 — The advertised 10-minute nowcast remains a best-effort service with much poorer observed cadence

**Status: known, documented, and explicitly accepted as residual risk.**

The workflow requests six runs per hour (`nowcast.yml:13-17`), but GitHub cron
is best effort. In the most recent 100 public nowcast runs sampled during this
audit, all 100 concluded successfully, yet the median scheduled-run gap was
**33.47 minutes**, p90 **71.90 minutes**, and maximum **84.17 minutes**. The
hourly forecast's latest 100 runs were also 100/100 successful, but its median
gap was 59.74 minutes, p90 115.77, maximum 128.53. A green run history therefore
does not imply the requested service cadence. Primary API snapshots are the
public workflow-run endpoints for
[`nowcast.yml`](https://api.github.com/repos/JohnUrban/barnacle/actions/workflows/nowcast.yml/runs?per_page=100)
and
[`daily_forecast.yml`](https://api.github.com/repos/JohnUrban/barnacle/actions/workflows/daily_forecast.yml/runs?per_page=100);
the statistics above are the auditor's calculation from their scheduled-run
`created_at` values at audit time.

The August 3 primary record confirms real impact:
`assets/observations/2026-08-03/README.md:98-103` says the last scheduled
nowcast finished at 09:56, the burst began at 10:02, and water crossed the
sidewalk before the next slot. Manual operation restored the live strip about
27 minutes after onset. `BACKLOG.md` records the decision to accept this gap,
so this audit does not present it as an unacknowledged defect.

**Impact:** the automated observed-radar layer can be absent for most or all of
a short convective flood, even while every workflow run is “successful.”

**Recommendation:** retain the explicit risk acceptance until an external
scheduler/runner or fine-grained dispatch credential is authorized, but add a
cadence SLO and monitor actual inter-publication time. The site should state
“best effort” rather than imply ten-minute observation. Alert when the system
misses the SLO during rain-capable conditions.

### M1 — Two August 3 canonical facts are currently wrong, even though the primary evidence is clear

**Status: confirmed against raw dictation and git history.**

1. `data/labeled_observations.csv` logical row 151 records the first August 3
   sidewalk report as `2026-08-03T22:26`. The raw dictation says **10:26 AM**
   and bay 10:18 (`assets/observations/2026-08-03/flood-measurements.txt:4,10`).
   The introducing commit `db1fd9e0` was authored at 10:31 EDT and its subject
   says “sidewalk 10:26”; the next ledger row is 10:29. This is an unambiguous
   AM/PM transcription error. `_today_lookback()` does not reject future rows,
   so the bad time can enter public “so far today” selection.
2. `docs/nowcast.json` still reports `day_max_street_in: 9.0` at 15:14Z.
   Git history proves the as-run value reached **13.2** at 14:50Z in
   `5b3f4d41`, then regressed to 9.0 in `39b8f5c7`. The origin-aware source fix
   landed later in `a9031211`, but it can only preserve the already-corrupted
   published value; it did not reconstruct the true maximum. The event README
   correctly calls the bug open (`README.md:104-110`), while `BACKLOG.md` does
   not carry the unresolved data repair.

The row-153 note also says “4th-largest measured flood,” whereas the reconciled
event record ranks it fifth of six. As-run notes may properly remain immutable,
but the correction needs an explicit annotation/erratum so consumers do not
mistake stale narrative for current truth.

**Recommendation:** use the repository's independent-reply process to choose a
provenance-preserving correction mechanism. Correct or supersede the 22:26
timestamp with an explicit evidence citation; restore/annotate the 13.2
nowcast maximum from commit history rather than recomputation; and add a
machine-readable correction/errata convention for append-only rows. Add
future-time and current-rank consistency checks where appropriate.

### M2 — Production v0.10.1 behavior is neither regression-tested nor reproducibly refitted

**Status: confirmed and partly acknowledged in the model spec.**

The 50 tests pin the four parameter constants and documentation stamp
(`tests/test_model_version.py:11-41`), but no test runs the production tank
against a known hydrograph, verifies stage-storage behavior, checks monotonic
response/mass behavior, or pins known-event peak/time outputs. A sign, unit,
interpolation, drainage, or stage-curve regression can pass if the four
constants remain unchanged.

`model/v0.10.1.md:90-93` explicitly concedes that the linked fit script only
documents v0.10. `history/scripts/tank_model_fit.py` hard-codes the author's
absolute path, searches the v0.10 grid, emits a v0.10 title/constants, and
cannot reproduce the documented v0.10.1 refit/RMS. The newer August 3
all-anchor scripts are closer to a useful hindcast fixture, but
`all_anchors_figure.py:12-14` imports its model from an ephemeral Claude
scratchpad path even though a repository-local copy exists.

**Impact:** the model version is documented but not independently rebuildable,
and behavioral changes can clear CI without evidence that known events still
behave as expected.

**Recommendation:** create one repository-relative, pinned v0.10.1 refit and
hindcast command that writes no production files by default and reproduces
the stated parameters/RMS from versioned inputs. Add small golden/physics
tests for the stage curve, zero/rising rain, head-dependent drainage, known
event peak bands/timing, and model-version cutover. Do not retune while doing
this; freeze today's documented behavior first.

### M3 — Alert-ingest dispatch failures are deliberately converted into green workflow runs

**Status: confirmed workflow path.**

The new nowcast fast path checks for an unacknowledged NWS alert, then dispatches
the hourly forecast. Its `curl` command ends with
`|| echo "dispatch failed (non-fatal)"` (`nowcast.yml:80-88`). A credential,
API, permission, or transient-network failure therefore leaves the workflow
green and creates no durable degraded-state artifact. The next hourly run may
eventually ingest the alert, but August 3 already showed why minutes matter.

**Recommendation:** retry with bounded backoff and expose a failed/degraded
dispatch as a job annotation and machine-readable health field. Prefer a
separate step/job whose failure is visible while allowing radar publication to
continue. Monitor dispatch-to-forecast-start latency.

### M4 — Dependency and browser trust boundaries are not fully pinned or escaped

**Status: confirmed; no tracked credential file found.**

- Workflows use floating major action tags (`actions/checkout@v7`,
  `setup-python@v6`). Daily installs floating `matplotlib`; nowcast requirements
  contain unpinned `xarray`, `cfgrib`, and `eccodes`.
- Generated pages load CDN scripts without Subresource Integrity. Chart.js and
  its plugin specify package versions, while `d3-delaunay@6` floats within the
  major line.
- NWS `event`, `severity`, and `headline` strings are fetched externally
  (`flood_forecast_daily.py:1361-1366`) and inserted into HTML without the
  `_html_escape` used elsewhere (`6261-6267`). NWS is a trusted government
  source, so exploit likelihood is low, but external feed text should not be an
  HTML trust boundary.
- The public source embeds a personal email address in the NWS/MRMS User-Agent
  and deliberately identifies a precise home/intersection. No tracked
  `.env`, credential, private key, or obvious live secret file was found.

**Recommendation:** pin actions to reviewed commit SHAs; lock Python
dependencies with constraints/hashes and controlled updates; self-host or add
SRI/crossorigin attributes to CDN assets; HTML-escape all external text; move
the contact User-Agent to a role address; and document that exact-address and
observation publication is an intentional privacy decision.

### M5 — The 9,898-line production module concentrates too many failure domains

`forecast/flood_forecast_daily.py` handles API clients, cache policy, tide and
rain physics, ledger writes, accuracy scoring, alert transactions, email/SMS,
HTML generation, JavaScript payloads, and CLI orchestration. The file contains
the correct extraction-seam doctrine and many good helpers, but its size makes
timezone mistakes, unescaped fields, duplicated rendering logic, and partial
fixes more likely. Several broad `except Exception` blocks turn failures into
silent omissions, making this harder to observe.

**Recommendation:** after the correctness fixes and golden tests, extract
pure modules in low-risk order: clock/time, schemas/provenance, external API
adapters, model core, alert state/delivery, and renderers. Keep the CLI as a
thin orchestrator. Preserve exact generated outputs with golden fixtures
during each extraction.

### L1 — Canonical observation/event schemas are valid CSV but not yet analysis-safe

The canonical data is structurally clean but semantically heterogeneous:

- `labeled_events.csv` has 42 rows, of which 38 have a blank label; it is an
  exploratory event candidate table, not a training-ready labeled set.
- `labeled_observations.csv` has 155 rows and no exact duplicates, but gauge
  and model fields mix numbers with status phrases such as “gauge
  malfunction” and “n/a.” Landmark keys include legacy or not-yet-production
  keys (`pocket_SE_retention`, `driveway_central`, `fire_hydrant_central`,
  `porch_step`) without a versioned registry in the ledger.
- There is no explicit observation-quality/status field, uncertainty band,
  correction link, event ID, or landmark-schema version; those concepts live
  mainly in prose notes.

**Recommendation:** do not rewrite history. For new rows, add additive fields
or companion tables for event ID, numeric nullable observations, status/reason,
uncertainty, landmark registry/version, and `corrects_row_id`. Document which
tables are production inputs versus exploratory evidence.

### L2 — Generated/model prose understates the current evidence base

Production source and `docs/details.html` still say there are “currently four
measured rain events” (`flood_forecast_daily.py:3704-3706`) and other sections
say the tank was “validated on four measured floods” (`2852`, `7469`). The
current repo records six measured flood anchors, with August 3 as an
out-of-sample hindcast. `model/v0.10.1.md` ends at Event #5 and does not include
that validation evidence. Some “two measured floods” wording is correctly
about the two full hydrographs and should remain precise rather than simply
changing every count to six.

**Recommendation:** centralize evidence counts/definitions or generate them
from a versioned event registry. Distinguish “six measured peak anchors,” “two
full fit hydrographs,” “independent checks,” and “one measured recession
constraint.” Add August 3 as validation evidence without changing the model
version or constants.

## Data-quality profile

The following snapshot is encouraging and should be preserved as a regression
baseline:

| Dataset | Rows | Duplicate/integrity result | Main caveat |
|---|---:|---|---|
| `forecast_accuracy.csv` | 72 | no duplicates; unique dates; error arithmetic exact | Aug 2 archive not yet scored at audit time (normal lag) |
| `labeled_events.csv` | 42 | no exact duplicates | 38 blank labels; exploratory |
| `labeled_observations.csv` | 155 | no exact duplicates; every row has numeric or qualitative outcome | one impossible future time; mixed numeric/status fields |
| `observed_peaks_cache.csv` | 147 | no exact duplicates found | cache semantics, not primary event truth |
| `predictions_log.csv` | 8,646 | no exact or `(made_at,target)` duplicates; 1,521 runs | long operational gaps exist; confidence only low/medium |

Predictions span `2026-05-19T16:26:29Z` through
`2026-08-03T20:32:43Z`. The recorded lead time agrees with independent
timestamp arithmetic to within 0.005 hours. Version counts are coherent with
the documented history: v0.6 2,834; v0.7 62; v0.8 2,059; v0.9 519; v0.10
1,521; v0.10.1 1,651. There are 74 daily archive JSON files and 72 scored
dates; only the immediately preceding day was pending.

These strengths make the semantic gaps more fixable: the repository already
has enough provenance to repair the bad August 3 timestamp and day-max without
guessing.

## Positive surprises worth preserving

- **Evidence discipline:** raw dictation, event README, ledger rows, model
  consequence, and git history can be triangulated. That is why the 22:26 typo
  and 13.2→9.0 regression are provable.
- **Honest model boundaries:** the spec explicitly separates fitted physics
  from rain-input skill and lists unresolved structures without silently
  retuning them.
- **Append-only operational history:** 8,646 predictions across six model
  stamps form a valuable as-run record rather than a rewritten backtest.
- **Failure semantics:** unavailable tide/surge inputs are generally labeled
  degraded rather than turned into false zeros; the astronomical fallback for
  nowcast drainage is the right direction.
- **Transactional multi-rail alerts:** independent ntfy/email/SMS attempts and
  acknowledgement only after at least one success are a strong design. August
  3's 3/3 delivery is meaningful live evidence.
- **Fast offline safety net:** 50 tests in milliseconds, compilation, and the
  artifact gate make frequent bot commits practical.
- **Adversarial audit protocol:** mandatory independent replies, preserved
  disputes, and primary-record verification are exactly appropriate for a
  safety-relevant personal forecast.

## Recommended implementation order

### Phase 0 — Repair facts and prevent live misrepresentation

1. Unify station-local day/time and add UTC-boundary/DST tests.
2. Add source freshness and coverage semantics to nowcast; make consumers use
   source time.
3. Make alert-state recovery fail closed and non-destructive.
4. Correct/supersede the August 3 22:26 observation and restore/annotate the
   13.2 day-max from as-run git evidence.

### Phase 1 — Strengthen the production control plane

5. Expand CI triggers and semantic artifact/ledger gates.
6. Make alert dispatch failure visible and retried.
7. Add nowcast/forecast cadence SLO monitoring; preserve the documented
   accepted scheduling risk until infrastructure changes are authorized.
8. Pin actions/dependencies/browser assets and escape external feed text.

### Phase 2 — Freeze and reproduce model behavior

9. Make a repository-relative v0.10.1 refit/hindcast command.
10. Add physical and known-event golden tests, without changing parameters.
11. Update evidence-count prose with precise definitions.

### Phase 3 — Reduce future change risk

12. Split the monolith behind tested seams.
13. Add versioned landmark/event/correction schemas for new evidence.
14. Revisit the nowcast scheduler only with an explicitly authorized external
    execution path.

## Audit closeout status

This is round `01` and therefore an **open obligation** under
`audits/README.md`. A different agent must verify each finding against the
cited primary evidence and write the next indexed reply before any closeout.
No production code, data, workflow, or model constant was changed by this
audit.
