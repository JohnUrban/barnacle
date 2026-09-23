# Verification record — 2026-09-23 audit

All candidate checks below refer to `ece4c2314dbafb2dce2e4f4f09015200bdda51a0`.
The root working tree was clean except pre-existing untracked `.claude/worktrees/`.
Later audit documentation changes do not alter the executable candidate.

## Commands and results

| Check | Result |
|---|---|
| `python3 -m unittest discover -s tests -q` | 238 tests in 1.625s; OK, **3 skipped** |
| `/Users/johnurban/.barnacle/venv/bin/python -m unittest discover -s tests -q` | 238 tests in 2.048s; **FAILED, errors=1**, no skips |
| `python3 forecast/check_artifacts.py` | publish gate: clean |
| `python3 history/scripts/reproduce_v0_10_1.py` | PASS; RMS 1.316778 in / 24 points, six frozen hindcasts, cutover |
| `python3 history/scripts/reproduce_v0_10_3.py` | PASS; reference error 1.07e-14 in, maximum correction 0.090 in |
| `python3 audits/2026-09-23-a1/reproduce_findings.py` | All candidate-defect assertions reproduced; output in reproduction-output.json |
| `node audits/2026-09-23-a1/reproduce_map_controls.js` | Actual town selector picks synthetic 6.0 NAVD88 water, display shows 2.0 NAVD88 with rain off |

These probes deliberately assert the reviewed defects. They are outside test
discovery and are historical audit reproductions, not desired-behavior regression
tests. Repairs should add ordinary regression tests expecting correct behavior.
The Python probe imports captured fixtures/test builders without network calls.
The JavaScript probe extracts only the selector/display functions into an offline
VM with synthetic state; it does not control a browser or modify the site.

Production-dependency suite failure:

```text
ERROR: test_nbm_qmd_fetch_honours_time_budget
  (test_outlook.AdapterParseTests.test_nbm_qmd_fetch_honours_time_budget)
  tests/test_outlook.py, line 203:
    data = srcs.fetch_nbm_qmd(NOW, steps=(6, 12, 18), time_budget_s=-1)
  forecast/outlook_sources.py, line 583:
    raise RuntimeError(...)
RuntimeError: NBM qmd: no buckets decoded
  (['f006: time budget', 'f012: time budget', 'f018: time budget'])
Ran 238 tests in 2.048s
FAILED (errors=1)
```

The default-Python skip set consists of the three eccodes-dependent adapter tests
in test_outlook.py. The local Barnacle environment is Python 3.14; production CI
uses 3.11. The failure arises from deterministic budget control flow, not a
version-specific decoder result. The two GRIB fixture parsers passed in the
installed decoder environment. No new packages were installed for this audit.

## GitHub verification (read only)

Read via `gh run list` / `gh run view` after sandboxed network access failed; the
read-only network escalation succeeded. No automatic approval rejection occurred.

- [CI 35890370985](https://github.com/JohnUrban/barnacle/actions/runs/35890370985):
  ece4c2314, success; log confirms **238 tests / skipped=3**. Its pinned
  actionlint/ShellCheck, compile, and strict-mypy steps completed in that run;
  local lint binaries were not available, so this is CI evidence, not a claimed
  local lint rerun.
- [Hourly 35887279745](https://github.com/JohnUrban/barnacle/actions/runs/35887279745):
  success; job 16:13:49–16:14:25Z (36s), dependency install 16:13:55–16:14:09Z,
  forecast/delivery step 16:14:09–16:14:21Z (12s).
- [Nowcast 35891179372](https://github.com/JohnUrban/barnacle/actions/runs/35891179372):
  success, created 16:47:27Z on ece4c2314.
- [NBM warm 35884916730](https://github.com/JohnUrban/barnacle/actions/runs/35884916730):
  success on e0912aafe (preceding the warm-job refetch optimization).
- Pages deployment 35890370348: success on ece4c2314.

Healthy ordinary-path timings do not bound repeated network timeouts. The R1
420-second failure budget was computed from mocked request timeouts, **not** an
observed production outage or a deliberately stalled live workflow.

## Ledger conservation and provenance

Parsed strict CSV from Git blobs at `8f0c32d94` and `ece4c2314`. Compared multisets
of complete rows, preserving multiplicity and verifying identical headers:

| Ledger | Before | After | Missing old rows |
|---|---:|---:|---:|
| labeled_observations | 184 | 184 | 0 |
| predictions_log | 15,315 | 15,485 | 0 |
| forecast_accuracy | 117 | 117 | 0 |

This confirms conservation across the window, not physical truth of every
historical observation. No new measured flood event was inferred from narrative.
No tracked unpublished-original image filenames or credential-shaped file paths
were found. No actual secret values were printed or copied into the audit.

## Browser and artifact checks

Read the published [landing](https://johnurban.github.io/barnacle/),
[town map](https://johnurban.github.io/barnacle/highlands.html), and
[outlook](https://johnurban.github.io/barnacle/outlook.html) in Chrome during the
audit. Their forecast stamp was 2026-09-23T16:14:10Z, matching the local committed
artifact. Existing browser display preferences were retained; no settings were
reset and no user data was submitted.

- Landing opens on September 23 13:00 as NOW; Worst flood chance moves the time
  slider from index 14 to 110, September 26 08:00. Display rounds to +15.4 inches
  because its physical level slider steps by 0.05 ft; outlook says +15.2 inches.
- Town map opens on index 14 and Worst flood chance moves to 110 / September 26
  08:00 / 7.60 MLLW. No console errors observed on that tab. The current tidal
  event cannot exercise the synthetic rain-over-tide counterexample; the offline
  extraction demonstrates the actual code's wrong display with rain disabled.
- Outlook source labels, every-high-tide table, rain scenario text, seven cards,
  shadow NO DATA YET verdicts, and the two chart canvases are present.
- Published landing “Landmarks today” gives 13.9 inches, while its source peak
  time is September 25 19:40. It also lists September 26 lows under a 24-hour label.
- `docs/forecast.json` has ten missing-rain future hours (September 30 03:00–12:00
  EDT), a series through September 30 12:00, cards only through September 29,
  and NBM/outlook health marked ok.
- Full DOM/accessibility contract passed via the gate. No claim is made of a
  mobile-device matrix, screen-reader usability review, automated console coverage
  of every page, or an actual Scriptable execution.

Offset-loss reproduction outside the browser, using the actual initializer's
expression under `TZ=UTC`:

```javascript
const stamp = '2026-09-23 13:00-04:00';
const m = stamp.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
new Date(+m[1], m[2]-1, +m[3], +m[4], +m[5]).toISOString();
// 2026-09-23T13:00:00.000Z (wrong instant)
new Date(stamp.replace(' ', 'T')).toISOString();
// 2026-09-23T17:00:00.000Z (offset preserved)
```

## External source cross-checks

Official [NCEP P-ETSS product inventory](https://www.nco.ncep.noaa.gov/pmb/products/petss/)
identifies eEE as **exceedance** levels: mapping e10 to the upper/p90 side and e90
to the lower/p10 side is appropriate. The captured files and parser tests also
verify ordering and tenths-of-foot conversion.

Official [NOAA NBM documentation](https://blend.mdl.nws.noaa.gov/nbm-documentation)
describes QMD guidance at 00/06/12/18Z with percentiles and exceedance probabilities
for multiple accumulation durations. That supports using a separate probabilistic
cycle and explicit accumulation windows. It does not validate summing marginal
six-hour percentiles into a daily percentile or turning a rainfall percentile into
a calibrated flood-depth probability; those are separate model assumptions.

## Boundaries

The audit did not backfill missing September 19/20 daily archives, alter delivery
policy, score the not-yet-completed advisory event, retune the rain model, repair
candidate code, or promote v0.10.5. It leaves a review and reproducible acceptance
work for Claude and John's decision, exactly as requested. Prior live operational
residuals remain open in BACKLOG.
