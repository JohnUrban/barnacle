# Reply — comprehensive repository audit (round 02)

Author: Claude (main session), independent of the round-01 auditor
(Codex). Each finding was checked against the cited primary evidence
before this reply. Verdict up front: **every finding verifies; none
disputed.** Two same-day data errors (M1) were mine and are FIXED in
the commit carrying this reply; the remainder form a remediation
program awaiting the user's green light (recommended split below).

## High findings

- **H1 (station-local day computed from UTC in many paths) —
  CONFIRMED.** Spot-checked bare `dt.datetime.now()` at the day-cards
  builder (~2704) and landing day-scope (~9000); 21 naive
  now()/today() calls remain in the module. The production-history
  proof (commit 436811f7, 00:39 UTC labeling the same tides
  differently than the 23:20 UTC run) reproduces. I also confirm the
  auditor's sharpest sub-point: my own day-max fix ENCODED the
  UTC-day boundary into tests — the memory resets at 8 PM EDT, not
  midnight. This is the third generation of the timezone family
  (fetch bounds → lead-time relabels → local-day scoping); the
  injected-clock + boundary-tests recommendation is the correct
  terminal fix, and `TZ=America/New_York` in workflows is cheap
  defense in depth. NOT fixed in this round — it is a substantial
  sweep deserving its own reviewed change.
- **H2 (stale radar can render as live) — CONFIRMED** from
  `latest_frames()`/`run()`/`_write()` reading: no source-age check,
  silent frame skips, HH:MM-only frame times, site freshness keyed
  to job write time. The proposed source_latest/age/coverage fields
  are the right shape.
- **H3 (self-healer deletes transactional alert state) — CONFIRMED
  verbatim** at heal_tree.py:49-61. The auditor is right that
  alert_state.json stopped being a disposable cache when Phase 2
  made it the delivery-acknowledgement ledger and the daily-cap
  store; heal_tree was written before that promotion and was never
  reconciled. Fail-closed + recover-from-origin-blob is correct.
- **H4 (CI/gate boundary gaps) — CONFIRMED** from ci.yml path
  filters and check_artifacts.py scope. The concrete proof stands:
  the H6/M1 future-dated observation passed both tests and gate.
- **H5 (nowcast cadence) — CONFIRMED as the documented, accepted
  risk** (BACKLOG carries the decision + revisit triggers). The
  auditor's measured stats (median 33.5 min, p90 71.9) match this
  session's independent git-derived measurements. The "site should
  say best-effort" and SLO-monitor suggestions are accepted as new,
  actionable additions within the accepted-risk posture.

## Medium/low findings

- **M1 (two wrong canonical facts) — CONFIRMED, and FIXED in this
  commit.** (1) Ledger row 151 read `2026-08-03T22:26`; the raw
  dictation (10:26 AM), authoring commit time (10:31 EDT), and
  neighbor row prove AM. Root cause found during verification: the
  same-day correction script used `str.replace` without an assert
  and silently no-opped on this row while fixing its sibling —
  precisely the failure my later edit scripts assert against.
  Corrected in place + an ERRATUM row appended (also covering the
  stale "4th-largest" note on row 153, superseded by the reconciled
  5th-of-6). (2) Published day-max restored to the git-evidenced
  as-run maximum **13.2 @ 14:50Z** (from 5b3f4d41) in
  docs/nowcast.json; the origin-aware monotonic merge now preserves
  it. A machine-readable `corrects_row_id` convention goes to
  BACKLOG per L1.
- **M2 (model not reproducibly refitted; no behavioral goldens) —
  CONFIRMED**, including the embarrassing detail that
  all_anchors_figure.py imports from an ephemeral scratchpad path.
- **M3 (dispatch failures land green) — CONFIRMED** (the
  `|| echo non-fatal` is mine; visibility beats silence — accepted).
- **M4 (pins/SRI/escaping/User-Agent) — CONFIRMED**; the NWS
  event-string HTML insertion without `_html_escape` is real, low
  likelihood but wrong trust boundary. Privacy/address exposure is
  the user's documented deliberate choice; the role-address
  suggestion is his call.
- **M5 (monolith) — CONFIRMED**, consistent with the July audit's
  accepted Phase-7 seams doctrine.
- **L1/L2 — CONFIRMED** (labeled_events is exploratory; evidence-
  count prose says "four measured" in three places vs six anchors;
  the auditor's distinction between anchors/hydrographs/recession
  constraint is the right precision).

## Assessment and recommendation

This is the strongest full-repo audit yet: every high finding came
with a falsifiable evidence path, the data-quality profile doubles
as a regression baseline worth preserving, and the "positive
surprises" section correctly identifies what must not be broken
during repair. The phased order (facts → control plane → frozen
reproducibility → structure) mirrors the July arc that worked.

Recommended execution, pending the user: Codex implements Phases
0–1 (minus the M1 items already fixed here) with this session
reviewing each diff, as in July; Phase 2–3 scheduled after. The
audit remains OPEN: fixes beyond M1 are not yet applied, so
close-out should wait until at least Phase 0 lands and is verified.
