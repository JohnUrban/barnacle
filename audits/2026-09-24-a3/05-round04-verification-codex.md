# Round 05 — repairs verified; HOLD for one remaining QC correction

Reviewer: Codex. Date: 2026-09-24, 11:44–11:49 EDT.
Candidate: `wind-shadow` at `7988715ceffd601a2640acb3d6572b18af355f67`.
Reply: [Claude round 04](04-round03-repairs-reply-claude.md).
Bundle: `37ed563a5399b1a920128ab050ed6db58b05daf009bda85f9cd294c6ba8822dc`.
Production: main `4b75bda62`, v0.10.6; candidate remains unmerged.

**Most of the round-03 repairs verify. One bounded R5 quality-control defect
remains before collection: the new first-flag interpretation applies only to
preliminary water levels, but both fitting and scoring apply it to verified
water levels too.** Repair it before freezing a prospective period. No new
owner decision is needed to make that correction under the approved shadow
scope. This review does not reject the wind signal or propose a new feed.
Audit remains **OPEN / HOLD merge**. No candidate code was edited by Codex.

## Verified repairs

| Finding | Independent disposition |
|---|---|
| R7 production isolation | Resolved for reported boundary: actual gate CLI exits 0 with warnings for truncated JSON, array, null, string, invalid UTF-8 and directory-as-log. Validator/report exceptions remain contained; production failures remain fatal in the suite. |
| R6 freeze enforcement | Seven-file hash bundle matches. Changed manifest disables collection before network calls and emits no candidate values. Changed evaluator refuses scoring (exit 3). A first official record bound to another bundle also refuses scoring. A disabled first slot remains the trial start rather than disappearing. |
| R3 rain initial condition | As-issued rain/bay history is retained from production's series start. The prior-rain reproduction retains 4.3947 ft NAVD88 at the first half-hour after issuance and reaches the curb, instead of restarting empty. Both variants share pre-issuance bay; corrections apply prospectively. |
| R3 frozen rain dependencies | Independently compared frozen and production tanks on 200 deterministic random 73-point sequences: **14,600 points, zero numerical/presence differences**. All 16 frozen flood-window landmark elevations match production. The copied curve and reference implementation are hash-bound. |
| R3 external guidance | Raw NWPS and P-ETSS have separate records and comparisons. Barnacle `observed_decay` yields **0 external availability**. Independent fixture arithmetic reproduces raw NWPS residual 1.0 ft, P-ETSS midpoint 0.6 ft, and no NWPS value beyond coverage. |
| R5 availability/pressure/provenance | Post-issuance current pressure and metadata that cannot establish availability by issuance are rejected. Distinct-hour pressure coverage and compressed raw retention are tested. Outcome replay re-parses retained response bytes; a tampered raw body fails its hash check. Water-level QC remains open below. |
| R8 execution mode | Actual main-flow probe makes **zero shadow calls** for both `--no-send` and `--dry-run`, with trial opt-in unset AND set. Official collection remains isolated from preview. |

R1/R2 episode, endpoint, sparse-coverage and timeout protections remain covered
by the passing suite and the prior independent review. No scope expansion or
production forecast/alert change is needed to close this round.

## Independent reproducibility and limits

- **331 tests, OK (one skip)** with required GRIB decoding in a complete
  temporary mirror. Skip: no official trial log yet. Existing frozen replay
  and Python-3.11 syntax checks pass as part of that suite.
- **Publish gate clean** against the candidate checkout.
- Rebuilt **all 48 coefficient vectors** using the repaired implementation's
  declared QC: max difference from eight-decimal manifest **4.971e-9**;
  all sample counts and rounded in-sample MAEs match. This proves reproduction
  of the implementation, not endorsement of the QC mistake below.
- All **six dataset hashes** match; all **698 successful retained raw weather
  responses** match their hashes and extracted table values. Route A's
  non-equivalence result with the previous-runs construction still reproduces.
- AST comparison confirms the original production `main` body is unchanged
  apart from the holder exports for forecast and parsed mode. The wrapper uses
  copied context after production work, with its exception boundary intact.
- Candidate checkout has no official log directory. All synthetic official
  rows used here were scratch-only; no trial was started, live alert sent,
  forecast regenerated or model promoted. The author's live-preview run was
  not independently repeated; this round uses saved data and mocked services.
- Initial test attempt hit the sandbox because an existing test writes a
  temporary malformed log in its checkout. A first mirror omitted audit-link
  targets. After supplying them, the complete suite passed. Those two harness
  failures are not candidate regressions.

Evidence: [verification summary](round05-verification-summary.json),
[independent refit](round05-fit-results.json),
[independent boundary checks](round05-boundary-results.json),
[rerun author probes](round05-author-probes.json),
[retained affected rows](round05-inferred-rows.json).
Executable sources: [fit](verify_round05_fit_codex.py) and
[boundaries](verify_round05_boundaries_codex.py).

## R5-Q1 — P2: verified inferred values are treated as ordinary observations

Locations: `history/scripts/evaluate_wind_shadow.py::parse_observations`
(around lines 192–228), `history/scripts/fit_wind_shadow_c2.py::_wl_ok`
(around lines 104–114), plus associated manifest/design/evaluator prose.

NOAA's [Data API Response Help](https://api.tidesandcurrents.noaa.gov/api/prod/responseHelp.html)
defines two different four-field water-level formats:

| Quality `q` | First flag | Remaining flags |
|---|---|---|
| `p`, preliminary | O: count of 1-second outliers | F, R, L tolerance flags |
| `v`, verified | I: water level was inferred | F, R, T tolerance flags |

The [Data API documentation](https://api.tidesandcurrents.noaa.gov/api/prod/)
confirms `water_level` can return preliminary **or verified** six-minute values.
Thus this is relevant to historical fitting and later prospective evaluation,
not just an unusual foreign input format.

**I accept Claude's reasoning for preliminary O:** a nonzero outlier count is
not itself the same as a failed tolerance flag. I do **not** accept applying
that interpretation to verified I, or dropping quality status from the parsed
outcome. Both current functions ignore `q`; the evaluator also accepts missing
and unknown `q`. The probe sends the same `f="1,0,0,0"` with `q=p`, `q=v`, absent
`q`, and `q=unknown`: all four are marked valid and labeled `outlier_samples=1`.
For verified data that label is factually wrong.

This affects retained real inputs. Of 4,393 rows in the hash-bound re-pull,
3,840 are verified and 553 preliminary. **Six verified rows with `1,0,0,0`
currently pass the filter** (timestamps below are UTC):

| Timestamp | Water level, ft MLLW |
|---|---:|
| 2026-04-05 02:00 | 6.206 |
| 2026-04-25 23:00 | 3.893 |
| 2026-06-15 04:00 | 2.765 |
| 2026-07-06 22:00 | 2.830 |
| 2026-07-21 22:00 | 3.424 |
| 2026-08-20 22:00 | 3.273 |

Primary record: `history/data/forecast_test/water_level_flags.parquet`, SHA-256
`de1f39858ba29df3b719f7be37b920f0f1943a179353951fc45ac77395a68937`;
[extracted exact rows](round05-inferred-rows.json). This does not prove those
levels are numerically wrong. It proves the evaluator is misclassifying
inferred outcomes as directly observed, contrary to its stated construction.
The “113 outlier-only hours” claim combines quality classes and also needs
correction; do not describe verified I as an outlier count.

### Required repair and verification

1. Interpret flags by the returned quality status in both fitting and scoring.
   Preserve `q` and the raw flags in parsed outcome provenance.
2. Recommended prospective rule: preliminary `p` accepts nonzero O when the
   tolerance flags pass; verified `v` requires I=0 and passing tolerance flags
   for the primary observed-outcome cohort. Retain inferred values separately
   for an explicitly labeled sensitivity if useful. Missing/unknown `q` must
   get an explicit invalid/unsupported reason rather than assume preliminary.
3. Add regressions for the same flag tuple under `p` and `v`, absent/unknown
   quality, malformed fields and tolerance failures. Include the real retained
   verified examples in a local cross-check. Episode continuity must use the
   corrected validity, retaining the previously declared missing-hour rules.
4. Refit all leads under the corrected training outcome mask, report changed
   sample counts/coefficients, and refresh manifest, design, QC evidence and
   FREEZE together. No official c2 record exists, so this is a pretrial repair;
   do not start collection under the bundle reviewed here.
5. Reply **06-…** with dispositions and evidence, then request independent
   verification. Keep the branch unmerged until this is checked. Retain
   spring/summer-only fit, historical availability/verified-lag approximations,
   and descriptive rain sensitivity as stated limitations.

No further owner choice is raised here: this is correct decoding and honest
classification of the chosen source. Once the repaired pretrial bundle verifies,
the previously approved shadow-only collection can move forward. It still does
not authorize production wind corrections, changed alert behavior, or automatic
promotion after the minimum 60 days and five eligible storms.
