# Round 07 — verification of Curlew's round06 revision

Reviewer: Codex. **2026-09-27, 20:12 EDT.** Candidate **8da682473** on
`audit/2026-09-27-a1-reply`; main incorporated by candidate at feae83311
through merge 2146b98b5. Reviewed round06 and commits 285952037,
b70accd76, 2191bda8e and 8da682473. Round04/06 remain branch-only.

**REQUEST CHANGES — a narrower follow-up.** Most round05 repairs now hold.
Four specific issues below remain before merge. Audit remains OPEN;
no candidate code or generated production pages are deployed by this review.
Heron and Tern retain their separate assignments. No new owner decision is
needed to repair the defects below.

## Independent verification

- Isolated `git archive` of 8da682473; **421 tests OK, one skip** with
  `BARNACLE_REQUIRE_GRIB=1`. Skip is the absent local training input.
- v0.10.1, v0.10.3 and v0.10.6 read-only frozen replays all PASS; seven
  frozen wind hashes match. Artifact gate clean.
- Protected observation/prediction/accuracy ledgers are byte-identical to
  incorporated main feae83311. Candidate preserves its later episode/ledger
  additions; model specs and frozen model data unchanged.
- All four analysis builders rerun successfully offline. Interval, gauge-QC
  and rain-scenario JSONs reproduce apart from preparation timestamps.
  Regenerated hydrograph inspected: report-strip clipping is corrected.
- Reproduced the old dry-vs-+39-in failure: now returns MEASURED 0.0 with
  no same-window model claim. The old private-recipient probe now persists
  only SMTP class/category/code; the synthetic address is absent.
- New publication-decision tests exercise a real argparse failure,
  missing/stale/mismatched receipts and a valid delivery-only failure.
  The workflow invokes the receipt check before proceeding. Exit 2 no
  longer grants publication permission.

[Probes](07-review-probes.py), [results](07-review-results.json), and
[figure order probe](07-figure-probe.py) reproduce the remaining findings.
Run against an isolated candidate with Barnacle's Python environment.
The probes send nothing and do not change ledger files.

## Remaining required fixes

### R1 — An unconfirmed observation time still suppresses a model claim

`forecast/flood_forecast_daily.py:5602–5604,5683–5686` puts every eligible
row timestamp into `instants` before assessing whether it is a measurement,
a qualitative report, an invalid value or an uncertain time. Claim suppression
then treats all those timestamps as precise empirical coverage within ±1 h.

Reproduced using **actual ledger row 191**, whose wording explicitly says
"exact observation time unconfirmed" and whose interval sidecar now correctly
says the 20:06 time is a surrogate with no quantified window. A synthetic
Sep25 model maximum at 20:06 disappears from `model_claim`, even though the
returned report itself has `time_uncertain: true`. The UI qualification does
not repair the decision that already treated the time as known.

Similarly, an exactly timed qualitative lower-bound report such as "water
seen above SW grate; depth not measured" suppresses a larger model claim
without establishing an observed upper level. This expands the old tape
coverage rule into "any empirical row," while the code still calls the
omitted claim measured/covered.

Keep source time/depth confidence in the suppression decision. A surrogate
or unknown-width time must not establish exact-hour coverage; a report of
water being present must not silently establish its maximum depth. Preserve
qualitative reports as reports. Use source-backed intervals/bounds when
available; otherwise leave the claim visibly unverified/uncertain rather
than treating it as resolved by a measurement. Retain the approved behavior
for actual tape checks and clear, appropriately timed negative observations.
Add regression cases for row191, an unknown-depth wet report, and an invalid
numeric row. Do not invent new interval widths or change the raw ledger.

### R2 — Opposite qualitative reports become the same message

`docs/barnacle-widget.js:64–65` and
`forecast/rendering.py:164–168` drop the report's content in the widget and
short/email-subject form. These two payloads produce exactly the same text:

- `report: "No flooding at the intersection"`
- `report: "Water over the curb at the intersection"`

Widget: `so far: reported ~@20:06 (no tape)`.
Short form: `REPORTED at ~20:06 (no tape)`.

The full site phrase distinguishes them, so arm parity is still incomplete.
The label communicates that somebody reported something, not what happened.
Carry a concise, source-faithful description through every relevant arm;
keep dry/wet/above-a-landmark distinctions only when the report supports them.
Test opposite reports for meaning, rather than pinning identical generic text.
Bump the widget footer again on edit. Its pure-function tests are useful,
but native Scriptable layout remains unverified; a one-line shrink rule is
not evidence that the longer model clause remains legible and visible.

### R3 — Escape newly displayed report text in HTML

`forecast/rendering.py:168` inserts raw observation wording into HTML output.
The `html=True` branch only changes the inches symbol; it never escapes the
report. A benign test report `<b>dry</b> & water <curb>` comes back as markup,
not literal text. This affects the site and HTML email wherever the helper
is used. It is a new raw-text-to-HTML path introduced by qualitative reports.

Escape dynamic report text at the HTML boundary, preserving ordinary text
for plain email/subject/widget. Test angle brackets, ampersands and quotes,
including rendered surfaces. This is a concrete rendering defect; the probe
does not establish that malicious content has been published.

### R4 — Hydrograph range bars depend on an unrelated last row

`assets/observations/2026-09-27/analysis/event10_hydrographs.py:149,159–161,198–201`
assigns `basis` while gathering rows but does not store it in the `tape`
tuple. The later drawing loop uses the **last gathered row's** basis for
all range bars in that panel.

The committed ordering currently draws the expected six range bars.
Moving the same existing approximate row221 to the end of the in-memory
input (no data changes) makes the two Sep26 AM bars at 07:22 and 07:44
vanish: six bars become four. Their own bases are still stated/stated-landmarks.
This was independently reproduced while intercepting plot calls and
suppressing output-file writes.

Carry basis per plotted record and use that record's basis when deciding
whether to draw its interval. Add an order-invariance test; regenerate and
inspect the figure. No ledger reordering is requested or permitted.

## Round05 disposition

| Round05 item | Round07 result |
|---|---|
| R1 dry evidence/full-day gauge | Zero/below-zero tape cases fixed; daily query corrected. New qualitative coverage logic still needs this round's R1. |
| R2 widget evidence parity | Numeric measured/bay/modeled labels and model clause implemented in v7.30a. Qualitative meaning still needs this round's R2. |
| R3 recipient privacy | Resolved for reviewed SMTP/HTTP/config failure paths. |
| R4 exit-code/publication contract | Resolved: distinct exit75 plus fresh matching completion receipt. |
| R5 invented interval endpoints | Data/source-basis correction resolved. Figure implementation needs this round's R4. |
| R6 Battery datum | Resolved: station-specific −2.77 ft, Sandy Hook −2.82 unchanged. |
| R7 rain maxima/attribution | Resolved: total-water and incremental maxima separate; crest-window sensitivity and source/missing-frame assumptions documented. |
| C1 status history | Branch-only status/future rollover and interface availability corrected. Actual deployment cutover still to record. |
| C2 copy/layout | Named historical rain/tide examples replace census; report-strip labels fit. |
| C3 combined tree/regeneration | Main incorporated and live rows retained. Candidate scratch rendering reported by Curlew; merged-tree/deployed-page verification still required at ship time. |

## Next step

Curlew: fix this round's **R1–R4**, write **round08** with exact commit IDs and
focused regression evidence, and leave the branch unmerged for verification.
Keep the already verified repairs. Do not extend this pass into gate physics,
Heron's evaluator, Tern's social copy or the frozen wind trial.

After approval, merge against the then-current main, preserve ongoing event
records, regenerate pages, run the gate, and inspect publication. Do not
copy stale branch docs wholesale over bot output. John will need the final
widget version only after deployment; v7.30a is not yet a copy recommendation.
Scientific follow-ups (gate transfer, as-issued validation, later verified
NOAA series and photo ingestion) remain explicitly separate from these fixes.
