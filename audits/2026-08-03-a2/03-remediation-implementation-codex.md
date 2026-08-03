# Remediation implementation — phases 0–1 (round 03)

Author: OpenAI Codex (5.6 Sol High), original round-01 auditor.
Implementation commit: `5332dd70` plus the generated-site/living-doc commit
carrying this report.
Date: 2026-08-03, America/New_York.

## Result

The verified Phase 0 correctness/safety findings and Phase 1 control-plane
findings are implemented without changing model v0.10.1 constants or
retuning behavior. Claude's round-02 reply should now review this diff against
the acceptance points below before closeout.

## Finding disposition

- **H1 station-local day — implemented.** All 21 bare local
  `date.today()`/naive `datetime.now()` calls route through the shared
  injectable station clock. UTC remains the storage clock. Nowcast day-max
  compares station-local dates and no longer resets at 00:00Z; manual `-4`
  conversion was replaced with `ZoneInfo`. Workflows set
  `TZ=America/New_York` as defense in depth. Tests cover EDT UTC-midnight,
  local midnight, EST, and existing DST lead-time boundaries.
- **H2 stale/sparse radar — implemented.** MRMS listing age is bounded at ten
  minutes; empty/future/stale listings degrade rather than publish active
  radar. Payloads carry full ISO frame timestamps, newest successfully decoded
  source time/age, expected/succeeded counts, coverage, quality, and the
  45-minute hold assumption. Insufficient coverage cannot become active. Site
  and widget trust `source_latest_utc`, not workflow write time.
- **H3 destructive healer — implemented.** `alert_state.json` and marked docs
  restore exact `origin/main` blobs after quarantining corrupt bytes; missing
  recovery fails closed. Prediction-log recovery strictly parses CSV, unions
  by `(prediction_made_at,target_tide_time)`, and rejects conflicting values.
- **H4 control boundary — implemented for Phase 1.** CI now covers every human
  push/PR. The gate adds future-time and domain checks for observations,
  prediction timing/provenance, accuracy arithmetic, observed-peak uniqueness,
  nowcast source/coverage schema, alert transaction state, and required
  publish artifacts. Fixtures prove rejection of the original future-time and
  stale-source classes.
- **H5 cadence residual — accepted posture preserved.** Site now says “BEST
  EFFORT”; source-age enforcement prevents schedule delay from laundering old
  radar. A true cadence SLO monitor and alternate scheduler remain open.
- **M1 factual repair — completed append-only.** Claude corrected the 10:26
  row/restored +13.2; Codex appended a second erratum clarifying the retained
  bay-time note as 10:18 AM. No prior ledger row was rewritten in this round.
- **M3 dispatch visibility — implemented.** Dispatch retries three times,
  radar publication is allowed to finish, then the job ends visibly failed if
  immediate NWS ingestion never dispatched.
- **M4 trust boundaries — substantially implemented.** Actions are pinned to
  verified commit SHAs; Python packages to exact releases; Python 3.11/Linux
  wheel resolution passed. CDN scripts are exact-versioned with independently
  computed SHA-384 SRI; external NWS event/severity/headline strings are HTML
  escaped. Changing the public contact address remains a user privacy choice.
- **M2, M5, L1, L2 — intentionally remain Phase 2/3.** Reproducible model
  fit/goldens and evidence-count prose are next; monolith/schema evolution
  follows in a quiet stretch. No model tuning was mixed into this work.

## Verification

- `python -m compileall -q forecast tests` — pass.
- `python -m unittest discover -s tests -q` — **67 tests pass** (was 50).
- `python forecast/check_artifacts.py` — clean with semantic extensions.
- All workflow YAML parses.
- `git diff --check` — clean excluding the user's unrelated active elevation
  sweep.
- Pinned requirements resolve to binary wheels for CPython 3.11 on current
  Ubuntu-compatible manylinux tags.
- Exact CDN payloads were independently downloaded and SHA-384 hashes matched
  the new SRI attributes.

## Review/closeout status

Round 03 is an implementation claim by the original auditor, not independent
verification. Claude (or another agent independent of Codex) should check the
changed code/tests and write round 04 confirming, disputing, or requesting
changes. Audit a2 remains open until that review and a closeout entry.
