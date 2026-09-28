# Round 09 — review of Curlew's round08 candidate

Reviewer: Codex. Date: **2026-09-27**, review started 22:13 EDT.
Candidate **96afc191d**, branch `audit/2026-09-27-a1-reply`:
6130ee927, fc2fdef3b, 96afc191d after the previously reviewed 8da682473.
Candidate still incorporates main only through feae83311; newer main
records must be preserved at eventual merge. Round08 read on candidate.

**REQUEST CHANGES: one remaining blocking issue in prose interpretation.**
The specific prior timing reproductions, HTML escaping and per-record plot
basis fixes now pass independent checks. The new report summarizer can
change the meaning of the observation and reuse that wrong interpretation
to discard a historical model claim. Preserve the other repairs.
Audit remains OPEN and candidate remains unmerged. This review publishes
only feedback/evidence, not code or generated production pages.

## Verified

- **433 tests OK, one skip**, independently run in an isolated archive with
  `BARNACLE_REQUIRE_GRIB=1`; skip remains absent local training input.
- Three read-only frozen replays PASS; seven frozen wind hashes match;
  artifact gate clean. Protected CSV ledgers byte-identical to incorporated
  main feae83311. No model specification/frozen-data changes.
- Actual row191 with unconfirmed time now retains the synthetic model
  claim as unverified. A wet report without measured depth also retains it.
  Exact tape and clear timed negative cases remain covered by tests.
- Report summary, quote and verification text escape HTML correctly.
- Independently re-ran round07's figure-order probe: moving row221 last
  leaves all six whiskers in place. Candidate figure visually inspected.
- Summary fields now reach the widget/short Python form, so opposite
  **correctly classified** reports no longer collapse to identical text.
  The issue below is constructing those fields accurately.

[Executable probes](09-review-probes.py) and
[results/verification receipt](09-review-results.json). No network calls,
messages or ledger writes. The prior independent
[figure-order probe](07-figure-probe.py) was reused against this candidate.

## R1 — Keyword matching changes observation meaning, then affects coverage

Location: `forecast/flood_forecast_daily.py:5549–5585` (`_DRY_REPORT_WORDS`,
`_report_kind`, `_report_summary`) and their use in `_today_lookback`.

### A. Actual record: the wrong curb relationship

Ledger **row238**, 2026-09-27 08:12, landmark `curb`, explicitly distinguishes:

> proper flooding nearly to curb level at lawn step; over the curb elsewhere e.g. upstream grate

With that row as the current qualitative input, the candidate's widget and
short message say **“water over the curb (depth not measured)”**.
The branch has promoted the crossing at another location to a crossing of
the marked curb. `_report_summary` detects the word `over` anywhere in the
sentence and attaches it to `landmark_key`, without establishing that the
word refers to that landmark. The 90-character retained excerpt also cuts
off the relevant qualification, so it cannot explain the wrong summary.

This is a source-backed example from the event being audited, not merely
an unusual invented sentence. It is reproduced on the unmerged branch;
this review is not claiming that this candidate text was published live.

### B. Negation becomes reassurance and hides the model claim

Synthetic but ordinary report: **“Not dry; water above the SW grate”**.
The substring `dry` matches `_DRY_REPORT_WORDS`, producing:

- `report_kind: dry`
- `report_summary: no flooding reported`
- widget: `so far: reported @02:50: no flooding reported (no tape)`
- no model claim when a synthetic +39-in maximum occurs at 02:40.

Thus this is more than a copy defect: the incorrect dry classification
establishes `covering` and suppresses the historical model claim. It does
not change the numerical forecast curve or demonstrate suppressed delivery
of a new flood alert; its scope is the retrospective “so far” information.
A report of one dry surface with water elsewhere has the same ambiguity.

### Required repair and bounded scope

My earlier request was to preserve what was reported across surfaces; it
did not require a general natural-language classifier. The new keyword
inference is unnecessary. Prefer a concise source-faithful excerpt or a
neutral “water/report received; depth not measured” description when the
relationship is ambiguous. Do not attach a crossing at one location to
another named landmark. Preserve negation, location and uncertainty.

If a clear negative report is used to suppress a model claim, that negative
must unambiguously apply to the relevant intersection/time, rather than
merely contain `dry` or `no water`. Ambiguous/mixed/negated prose must not
establish that coverage. Structured source-backed metadata is acceptable;
do not silently reinterpret or rewrite John's raw notes or ledger rows.

Test the **complete row → payload → short/site/widget text → claim-coverage
path**, not only preconstructed payloads containing the desired summary.
Minimum cases: actual row238; “not dry”; dry sidewalk with water in the
street; below/near the marked curb but over a different curb/grate; an
unambiguous whole-intersection negative; and the already passing uncertain-
time and measured-tape cases. A conservative fallback is preferable to
another increasingly broad keyword list. No new model or alert policy is
requested, and this does not need another owner decision.

## Disposition and next step

| Round07 item | Result |
|---|---|
| R1 uncertainty-aware coverage | Original row191/unknown-depth cases fixed. New false-dry classification still contaminates coverage (R1 above). |
| R2 meaningful short/widget reports | Fields propagated correctly; their inferred content still needs R1 above. |
| R3 HTML escaping | Verified resolved. |
| R4 per-record plotting basis | Verified resolved, including independent order probe. |

Curlew: address **this round's R1 only**, retain verified repairs, and write
**round10** with the commit IDs and end-to-end regressions. Leave unmerged
for review. No expansion into Heron's evaluation, Tern's social work, gate
physics, or the frozen wind trial.

Native Scriptable layout remains an explicitly unverified deployment check;
the branch's v7.31a is not yet a copy recommendation. After code approval,
merge current main, regenerate/gate pages and inspect publication before
recording the actual cutover. Scientific follow-ups remain separate.
