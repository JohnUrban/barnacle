# Remediation implementation — Phase 2 (round 04)

Author: OpenAI Codex (5.6 Sol High), original round-01 auditor.
Review status: awaiting independent Claude review.

## Outcome

Phase 2 is implemented without changing `CURRENT_MODEL_VERSION` or any of the
four v0.10.1 production parameters. The repository can now run one offline,
read-only command from any working directory to reproduce the published
24-point RMS, six retained event hindcasts, and prediction-log version
cutover:

```text
python history/scripts/reproduce_v0_10_1.py
```

The command exits nonzero on a parameter, RMS, event peak/time, observation-
time check, or cutover mismatch. It writes no production files.

## What changed

- Added `model/data/v0.10.1-reproduction.json`, the versioned fit/hindcast
  fixture and evidence registry: six measured peak anchors, two full fit
  hydrographs, two inherited independent peak checks, one measured recession
  constraint, and the August 3 out-of-sample hindcast.
- Added `history/scripts/reproduce_v0_10_1.py`. It imports the production
  constants and stage curve by repository-relative path, replays the retained
  linear-interpolation fit recipe and step-held MRMS hindcasts, and verifies
  the first correctly stamped v0.10.1 prediction-log row.
- Added `tests/test_model_reproduction.py`: ten golden/physics gates covering
  the 1.3167779-inch RMS over 24 points, all six event peak depths/times,
  December 19's observation-time band, evidence taxonomy, version cutover,
  stage-curve/storage monotonicity, zero/rising rain, head-dependent drainage,
  and dynamic rise/recession/nonnegative storage.
- Replaced the August 3 all-anchor model's duplicated data with the canonical
  runner and replaced both machine-local/scratchpad paths in the figure recipe
  with repository-relative paths.
- Corrected production/model prose. It now distinguishes six measured peak
  anchors from two full fit hydrographs, two independent peak checks, one
  recession constraint, and one out-of-sample hindcast.
- Regenerated `docs/index.html` and `docs/details.html` from the current
  forecast artifact after the source wording change.

## Reproduction result

```text
v0.10.1 frozen production vector: K=1296000, gamma=0.78,
k_out=3.50/h, lag=15 min
fit replay: RMS 1.316778 in over 24 points (reported 1.32 in)
jul6 +14.6 @11:38; jul9 +19.0 @16:14; oct30 +20.9 @15:24
dec19 +14.2 @07:34 (+11.0 at 08:12 observation)
jul18 +15.8 @15:50; aug3 +13.4 @10:42
model-version log cutover: 2026-07-21T15:27:30Z
```

## Provenance limitation made explicit

The retained inputs reproduce the published v0.10.1 score and frozen
production vector. They do **not** retain the original optimizer trace or an
exact independently replayable v0.10 baseline recipe. The original session's
“1.44 to 1.32 inches” improvement remains an as-run historical statement; the
new command proves the 1.32 endpoint, not optimizer uniqueness. The model spec
now says this plainly instead of overstating reproducibility.

## New low-severity model debt characterized, not changed

While writing stage physics tests, I found that `_pluvial_fill()` begins a
non-grid `base_stage` at the preceding 0.1-inch curve bin. With a tiny positive
storage budget, the returned stage can therefore be up to about 0.08 inch
below its starting base. Production suppresses pluvial excess below 0.25 inch,
and the six frozen event outputs include current behavior, so this appears to
be an onset-scale quantization issue rather than evidence of changed recorded
peaks. Fixing it would nevertheless change model behavior and must not be
smuggled into v0.10.1. It is recorded in `BACKLOG.md` for impact analysis and
a versioned correction.

## Verification

- `python -m compileall -q forecast tests history/scripts assets/observations/2026-08-03/analysis` — pass.
- `python -m unittest discover -s tests -v` — 77/77 pass.
- `python history/scripts/reproduce_v0_10_1.py` — pass.
- `python forecast/check_artifacts.py` — publish gate clean.
- `git diff --check` — clean before living-document edits.

Requested independent review: verify the reproduction math against the old
fit recipe and six-event script, confirm the no-retuning claim, assess the
optimizer-provenance wording, and decide whether M2/L2 can close while the
sub-bin stage issue remains separately queued.
