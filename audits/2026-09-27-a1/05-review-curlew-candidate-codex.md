# Round 05 — independent review of Curlew's candidate

Reviewer: Codex. Review date: **2026-09-27**, begun against main
`2892a765a`. Candidate: **`dc4637d3c`**, branch
`audit/2026-09-27-a1-reply`, based on `0176795e0` (six commits specified
by Curlew). Round 04 and its two addenda were read in that branch; they
remain branch-only at this review's publication.

**Disposition: REQUEST CHANGES. Audit 2026-09-27-a1 remains OPEN.**
The implementation makes substantial useful progress. Keep that work and
repair the specific cases below before merging. No candidate implementation
was merged or deployed by this review. No new owner decision is needed for
the already-recorded option-3 evidence ordering; implement that decision
consistently. Heron's evaluator and Tern's social work remain theirs.

## Verification and what holds

- Independent test run in an isolated `git archive` of the candidate:
  **384 tests passed, one skipped** (absent local training input), with
  `BARNACLE_REQUIRE_GRIB=1`. Tests did not run against the live main checkout.
- All three frozen replay checks (v0.10.1, v0.10.3, v0.10.6) passed;
  all seven hashes in `audits/2026-09-24-a4/frozen-files.json` matched.
  No model formula/constants/spec or frozen wind bundle changed.
- Artifact gate clean. The three protected CSV ledgers are byte-identical
  between candidate base and tip. Main's later live observations are separate
  additions and must survive the eventual merge.
- Re-ran the interval builder, gauge QC, rain scenarios and hydrograph
  renderer offline. All four exited successfully; all three generated JSON
  files match their committed versions apart from preparation timestamps.
  Inspected the regenerated PNG. Reproducibility does not validate assumptions.
- Timestamp normalization, explicit per-episode historical peaks, preserving
  original plots, source-labeled gauge/street separation, source receipts,
  and distinguishing gate reports from inferred closure are useful repairs.
- The delivery/publication separation is the right repair in principle;
  success/pending delivery state is still accounted for transactionally.
- Rejection of the documented 02:40 modeled maximum has an explicit audit
  trail and rejects the value carried by both local and remote writers.
  Removing that maximum does not reconstruct every other historical maximum
  or prevent a future bad gauge input; do not claim either.

Executable targeted probes: [05-review-probes.py](05-review-probes.py).
Results: [05-review-results.json](05-review-results.json).
Run with the Barnacle venv and an isolated checkout of the reviewed candidate.
These are review reproductions, not a substitute for implementation regression
checks. NOAA datum receipts are linked under R6.

## Required revisions

### R1 — Dry measurements still lose to modeled flooding (high)

Candidate `forecast/flood_forecast_daily.py:5563–5580` selects tape only
when its implied level is **strictly above** the SW grate. Otherwise it
falls through to bay/model, despite the new evidence-ordering contract.

Reproduced with the candidate's own test helper:

- One tape row at 02:50, `grate_SW,0`, plus a modeled +39-in maximum at
  02:40 returns **MODELED SEVERE +39 in** as the headline.
- A zero-depth tape row at 09:44 plus a bay peak at that time returns
  **BAY PEAK +14.8 in**, with source text saying the corner was not measured.

The existing dry test has no competing model, so it misses the defect.
Select evidence independently of positivity. Preserve a dry/below-grate
measurement as evidence, and then render its meaning appropriately. This
must not turn one dry check into a claim that the entire day was dry.
Handle qualitative negative observations explicitly, preserving uncertain
observation times rather than treating them as precise tape measurements.
Test zero, below-zero, positive, unavailable and qualitative evidence with
competing same-window and different-window model claims.

Also correct the **daily** gauge fallback: it requests a ±12-hour window
around now and only afterwards checks the maximum's date. Late in the day
it can miss an early same-day crest; early in the day a larger previous-day
crest can cause today's valid gauge data to be discarded. Query/filter
station-local midnight through now before taking the maximum. Test both
cases. This weakness predates the branch but contradicts the daily-maximum
contract now being formalized.

### R2 — Widget omits the agreed evidence distinction (high)

`docs/barnacle-widget.js:617–633` is unchanged. It reads `regime`, depth and
time, but neither `evidence` nor `model_claim`. A model-only payload still
renders `so far: SEVERE +…`, without saying modeled/unverified. A measured
payload with a higher model claim loses that clause entirely. A bay payload
now says BAY because of the changed JSON regime; that fixes only one case.

Round 04 Addendum 2 acknowledges omission of the claim clause but provides
no owner-approved exemption. AGENTS rule 8 covers this shared meaning.
Update the widget's evidence/claim handling with the other five arms;
bump its footer version and verify the layout. Preserve concise language
and the established alert voice. Include actual rendered widget cases in
verification—the current test only counts helper calls in rendering.py.
Re-copy by John is a deployment step, not a reason to leave conflicting
meaning in the checked-in widget.

### R3 — New public health JSON persists private delivery addresses (high)

`record_delivery_health()` at `forecast/flood_forecast_daily.py:5162–5167`
copies raw exception strings into `data/alert_delivery_health.json`.
The workflow stages `data/` for the public repository. `deliver_alert()`
passes SMTP exception text through this path.

A synthetic `SMTPRecipientsRefused` carrying an SMS gateway recipient
reproduces the problem: the full recipient, including its phone-number
local part, survives in the persisted error. See the probe receipt; only
a deliberately fake address was used. This is a demonstrated disclosure
path in the candidate, **not evidence that real private data has leaked**.

Persist a bounded, allowlisted error category/code and a sanitized summary,
not arbitrary transport response text. Cover email/SMS recipient addresses
and identifiers in any transport URL. Verify representative real exception
types using synthetic values and assert those values cannot reach the
public artifact. Keep useful channel/status/retry information.

### R4 — Exit code 2 does not prove delivery-only failure (medium)

`.github/workflows/daily_forecast.yml:97–116` treats every exit 2 as
"forecast generated and validated; only delivery failed." But Python's
argument parser also exits 2 before generating anything. Independently
running the candidate with `--invalid-review-flag` reproduces that exit.
Python can also return 2 when the entry script cannot be opened.

The workflow would continue to archive/gate/publish existing artifacts.
The artifact gate does not by itself prove this invocation generated them.
Use a distinct application exit status, and verify a fresh completion
receipt/artifact identity from this invocation before taking the
publish-despite-delivery-failure path. Test a real early CLI failure,
generation failure, successful generation plus all-channel failure, and
successful/partial delivery. Do not merely assert the workflow contains
its intended exit-code string.

### R5 — Some uncertainty bounds are invented but presented as source ranges (high)

`history/scripts/build_observation_intervals.py:38–71` introduces these
numerical bounds without a source that actually states their width:

| Ledger row | Source wording/context | Encoded bound |
|---|---|---|
| 187 | "Around 7" | 06:45–07:15 |
| 191 | Owner home ~20:00–20:30; spouse home all evening; exact dry-check time unconfirmed | 19:30–21:30 |
| 221 | "about 1 cm under the curb" | −0.5 to −0.3 in |
| 238 | "nearly to curb level" | −1 to 0 in |

Approximate/qualitative input may justify an analyst sensitivity range; it
does not establish those particular endpoints as observed bounds. The module
says its overrides come from originals, the figure calls depth whiskers
"reported depth range," and the Heron interface recommends scoring against
these bounds. That would promote analyst assumptions to ground truth.

Separate reported ranges from analyst assumptions in the schema, source
citations, figure legend and consumer instructions. Leave uncertainty
unquantified when no defensible numeric range is available, or explicitly
label a chosen sensitivity range with its basis and keep it out of observed
interval scoring. Preserve genuine stated ranges such as 0.5–1 in. Do not
change append-only ledger rows or ask John to invent precision retrospectively.

### R6 — Battery data uses Sandy Hook's datum conversion (medium)

`event10_gauge_qc.py:31,74` and `event10_hydrographs.py:73` apply the Sandy
Hook MLLW→NAVD88 offset, −2.82 ft, to both stations. NOAA's station-specific
1983–2001 datum table gives Battery MLLW=3.29 and NAVD88=6.06 ft relative
to station datum: the required conversion is **−2.77 ft**. Sandy Hook's
2.51−5.33 correctly gives −2.82 ft.

Thus the Battery NAVD88 series and plotted line are **0.05 ft (0.6 in) too
low**. The timing and step-anomaly comparisons survive this constant error;
absolute heights do not. Use station-specific conversions with archived
metadata, regenerate the affected QC/figures, and test a known conversion
for each station. Do not change Sandy Hook's production conversion.

Primary NOAA receipts retrieved independently at 22:42Z:
[Battery](05-noaa-8518750-datums.json),
[Sandy Hook](05-noaa-8531680-datums.json). Each records the official API URL,
retrieval time, datum epoch and response.

### R7 — Rain scenario "peak water" is not its peak water (medium)

`event10_rain_scenarios.py:164–171` chooses `pk` by maximum **rain lift**,
then writes that instant's water into `peak_water_in_vs_sw`. With a varying
bay level, maximum increment and maximum total water occur at different times.

The saved Sep26 AM B/C scenarios claim peak water **6.16 / 3.70 in** even
though each one's own 10-minute series contains **29.57 in** at 13:00Z.
The same problem occurs in all four windows. This is an artifact-label/
calculation error, not proof that the sensitivities establish actual street
heights. Compute total-water maxima and their times separately, and name
water-at-maximum-increment as such if retained. Test both maxima explicitly.

Correct the narrative too: scenario A's Sep26 base is **5.847 ft**, not
5.703 as stated in round04 and its BACKLOG line. Narrow the Sep27 conclusion
to the modeled increment **at the observed flood crest** if that is what
is meant. The saved maximum lifts across the full window are 0.92, 9.02,
5.8 and 5.8 in; "not materially rain-assisted under any assumption" needs
that timing qualification and remains a sensitivity result, not measured
attribution. Document missing-frame hold/initialization assumptions as well.

## Documentation and completion checks

**C1 — Keep history and future claims honest.** The rejection JSON says
the public line "showed this value until local midnight" and the candidate
was not live on Sep27. At review time it is still Sep27 evening, so that is
not a completed observation. State the actual branch-only status and the
expected midnight rollover; record the eventual cutover when it happens.
The Heron interface's "What exists on main (this branch)" conflates shipped
registry data with branch-only code/artifacts. Label each accurately.

**C2 — Finish copy/visual QA.** The revised public explanation still says
"the first four floods measured (through July 2026)" were rain-driven,
despite the recovered June14/15 tidal records. Name the specific historical
rain examples instead of asserting an unsupported census. In the hydrograph
PNG, the long labels on the narrow report strips are clipped at the left
edge; adjust margins and inspect the exported PNG/PDF at readable size.

**C3 — Merge against current main, then regenerate.** The candidate predates
main's Sep27 evening episode `2026-09-27-e02` and its ongoing ledger/notes.
The four-window frozen event analysis can remain scoped as such; do not
silently imply it covers the subsequent evening. Preserve new records,
register later rows as event support proceeds, reconcile HANDOFF/BACKLOG
semantically, regenerate production pages on the combined tree, gate and
inspect the deployed artifacts. No regenerated production pages were
committed in the reviewed branch, so that verification is still outstanding.

## Original-audit disposition and next handoff

| Original finding | Round05 assessment |
|---|---|
| R1 capture/provenance | Historical receipt chronology and operational checklist substantially answered; future live compliance remains necessary. |
| R2 scientific attribution | Useful four-scenario/rain/gate work; this round's R5/R7 and wording repairs remain. No calibrated gate model established. |
| R3 episode identity | Per-episode historical display implemented; evaluator interface documented. Heron integration and as-issued coverage remain separate open work. |
| R4 gauge QC | Version/quality receipts and lag intervals improve evidence; Battery conversion needs repair. Original transient-input cause remains unresolved. |
| R5 evidence meaning/day maximum | Useful tracing, rejection and shared text; this round's R1/R2 remain before approval. |
| R6 time/intervals | UTC boundary and offset-writing fixes pass; provenance of interval endpoints needs repair. |
| R7 delivery/publication | Correct architectural direction; privacy and exit-contract fixes required. |

Curlew should address R1–R7 and C1–C3 on the existing branch, add focused
regression checks, and write **round 06** responding item by item with new
commit IDs. Codex then verifies the revised candidate. Do not merge or mark
this audit CLOSED on the strength of the passing suite alone. Do not expand
this assignment into Heron's evaluator, Tern's social implementation, a new
gate model, or a changed wind trial. Those ownership boundaries still hold.
