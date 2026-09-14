# Independent review of the 2026-09-14 comprehensive audit

**Author:** Claude (Fable 5), main-session reviewer — a different
agent from the report author, per `audits/README.md`.
**Reviewed:** `01-comprehensive-repository-audit-codex.md` at repo
state 4c3d025d9 (2026-09-14 ~15:30 UTC), i.e. slightly after the
audit snapshot; where drift matters it is noted.
**Verification method:** every H/M/D/L item checked against primary
code, data, git history, and live GitHub state; statistics
recomputed from the CSVs; workflow claims checked against run logs
and the GitHub API. G items checked against the event archive and
ledger. **No fixes were performed** — per the owner's instruction,
Codex intakes this reply and performs the work.

Conflict-of-interest note, stated plainly: findings H1, H2 (SMS
half), H5, D5, D6, and L3 concern code and records I authored on
2026-09-12/13. All are **confirmed**. Where my authorship created
the defect I say so; none of these verdicts soften on that account.

## Verdict table

| Item | Verdict | One-line basis |
|---|---|---|
| H1 | CONFIRMED | producer/consumer field mismatch reproduced in source |
| H2 | CONFIRMED + expanded | dedup keys on observed sig; see worse path below |
| H3 | CONFIRMED + causal history | watchdog step predates the dispatch reorder |
| H4 | CONFIRMED | `current_bay` takes `pairs[-1]` with no row-age check |
| H5 | CONFIRMED | my own hardening; lock + exit-0 inventory accurate |
| H6 | CONFIRMED | warn-only wrappers verified verbatim |
| M1 | CONFIRMED | docstring claims last-run archive; workflow archives 09:00Z only |
| M2 | CONFIRMED | no labeled_events branch in the gate; fixtures accepted |
| M3 | CONFIRMED | stats reproduced to 3 decimals; +1 hygiene note |
| M4 | CONFIRMED | both warn-only sites verified |
| M5 | CONFIRMED + expanded | heartbeat also conflates quiet-gating with outage |
| M6 | CONFIRMED | tick pushes observed triggering CI + Pages |
| M7 | CONFIRMED | 2b40dd3bc reproduced (20:35 EDT titled 09-13 00:00 UTC) |
| M8 | CONFIRMED | all four sub-claims; incl. correction of the DictWriter myth |
| M9 | CONFIRMED | I attempted a dispute and lost it — see note |
| M10 | CONFIRMED | documented trade-off; endorse outbox/idempotency work |
| G1–G10 | CONFIRMED | consistent with the event archive; G10 stats verified |
| D1–D9 | CONFIRMED | each verified individually; D1/D3/D5/D6 are my misses |
| L1 | PLAUSIBLE, not re-measured | no coverage tool in this environment |
| L2 | PLAUSIBLE, not re-run | consistent with dual-mode shim design |
| L3 | CONFIRMED | my test, line 100 |
| L4 | CONFIRMED | installer bypasses existing nowcast-requirements.txt |
| L5 | CONFIRMED | fold unhandled in parse_station_local_time |
| L6 | CONFIRMED | privacy framing endorsed as owner-decision |

No item is rejected. Two audit details were candidates for dispute
and both resolved in Codex's favor on primary evidence (M9's
"unlabeled" is the literal cell value in 38 rows; D1's "18
landmarks" survives in README.md:6 three words from the v0.10.2
pointer I updated around it).

## High-severity notes and expansions

### H1 — confirmed; my defect, and my test methodology hid it

`forecast/nowcast.py:445` writes `peak_proj_in`;
`_nowcast_snapshot` (flood_forecast_daily.py:4456) reads
`projected_peak_in`, which no producer writes. My
`tests/test_sms_policy.py` injected dicts directly, so the suite
validated the gate against a payload shape that does not exist.
The live 2026-09-13 10:01 firing worked only because
`street_now_in` (11.2) alone crossed the curb class — actual-impact
texts work; projection-only texts silently cannot.

Expansions for the fix:

1. There is a SECOND, correct reader: flood_forecast_daily.py:4206
   already uses `peak_proj_in`. Canonicalize the key in ONE place
   (a shared constant or a tiny schema module) and make both
   readers and the writer import it.
2. The contract test should round-trip an actual `nowcast._write`
   payload through `_nowcast_snapshot` into `evaluate_sms_gate` —
   not a hand-built dict. That is the test that would have failed.
3. Gate additionally on `active` (a quiet-weather file with a fresh
   `source_latest_utc` should never be an imminence basis) and
   `nowcast_schema_version`.
4. For trend gating, REUSE `radar_alert_check`'s exact falling-pool
   semantics (nowcast.py:523-525) rather than writing a third
   trend interpretation; the repo already has two.
5. On the freshness triad (site 20 / dispatch 25 / SMS 30): I can
   reconstruct no principled reason for three values — I set 30
   without reconciling. Recommend one constant with documented
   per-consumer offsets only if a reason is found.

### H2 — confirmed, and one path is shorter than the report states

The report's ntfy-succeeds/SMS-fails sequence is verified. Note
additionally: `persist_alert_state` writes the top-level observed
`sig` on EVERY persist, including no-delivery persists, and
`radar_alert_check` dedups on `bit in sig` of that observed field
(nowcast.py:533-541). If any run persists state between radar
dispatch and a successful SMS — including a steady run that
delivered nothing — the radar class can be marked "already
alerted" without any rail having fired. Codex should verify this
shorter path while implementing; if real, it strengthens the
recommendation to key redispatch on confirmed `sms_event` state.

Also fold in (new, related): the daily cap now counts imminent SMS
sends into the same `sends_today` budget that gates base
ntfy/email alerts. Two SMS-bearing episodes in a morning can
therefore silently exhaust the cap for the evening's base email —
channel-role separation (2026-09-13 policy) was not extended to cap
accounting. Recommend per-rail or per-kind accounting in the same
H2 work.

### H3 — confirmed; causal history for the fix

`git log -S` shows the "Surface alert-ingest dispatch failure"
step landed in 5332dd702 (audit-a2 phases 0-1) directly below the
dispatch step it watches. My 2026-09-02 dispatch-after-push reorder
moved the dispatch step below the commit step but left the watchdog
in place — so the watchdog now precedes its subject and its
`steps.dispatch.outcome` condition can never be true. The a2-era
"dispatch-failure visibility" claim in HANDOFF/BACKLOG was true
when written and regressed by my reorder: a workflow-structure
check (actionlint or a step-order unit test on the parsed YAML)
belongs in the SAME commit as this fix, or it will regress again.
The radar-path `|| echo "dispatch failed (non-fatal)"` swallow and
the double-dispatch possibility are confirmed as written.

### H4 — confirmed

`current_bay` (nowcast.py:299-326) despikes and then takes
`pairs[-1]` with no check that the last row is near `now`; the
3-hour request window means a stalled feed can serve rows up to 3 h
old as "observed", and the forecast-side sites accept older still.
Endorse the recommendation set as written, with one number
suggested: drainage/bay-head use ≤30 min, surge persistence ≤60
min, display flags degraded beyond those — aligned with the
existing input-health vocabulary (rule 7: unavailable ≠ zero, and
stale should not equal current).

### H5 — confirmed (my hardening; its limits accurately stated)

The exit-0 inventory is accurate, and the lock critique is the
sharpest part: `mkdir` + `trap rmdir EXIT` leaves a permanent
silent lockout after any kill -9/crash/power event — the exact
"status 0, dark forever" failure class as the wedge I fixed, one
layer up. Two macOS practicalities for the implementation: stock
macOS has no `flock(1)`, so prefer the mkdir-lock plus a PID file
with an mtime-staleness takeover (a tick is seconds long; a lock
older than ~5 min is stale); and structured per-tick outcome
logging is cheap since the log file already exists. On the
half-B rename: agreed — as planned it is an external TRIGGER of
the same GitHub execution domain, and on 2026-09-13 it would have
kept dispatch attempts flowing (making the wedge visible sooner,
worth something) but executed nothing. The honest decomposition is
trigger-redundancy (half-B as planned, cheap, still worth doing)
versus execution-redundancy (local arm gaining radar-alert
delivery, since it already computes the street state), versus
observation-redundancy (the external watchdog on public artifact
age — cheapest of the three and currently absent entirely).

### H6 — confirmed

Verbatim warn-only wrappers at 7019-7035. The cross-surface stamp
recommendation is the right shape; note `forecast["generated_utc"]`
already exists as the natural stamp value and the gate already
parses every surface — the missing piece is only the equality
assertion.

## Medium-severity notes

- **M1:** the `_flood_peaks_chart_data` docstring's "the daily
  archive is the day's LAST run" is directly contradicted by
  `is_daily` gating (daily_forecast.yml:61-67; all recent archives
  ~09:00 UTC). The append-only `day_summary` product proposal is
  right; it should NOT overwrite the as-issued morning snapshot,
  which the skill scorer needs immutable.
- **M2:** confirmed; when adding validators, wire them behind the
  existing gate's per-file dispatch so CI and the ship ritual get
  them for free, and add Codex's adversarial fixtures AS the tests.
- **M3:** all five statistics reproduced exactly (n=112, MAE 0.417,
  signed +0.332, max 1.621; low 71/0.420, medium 40/0.417). One
  addition: one row has an EMPTY confidence cell (n=1, |err| 0.174)
  — include in the hygiene pass. The auto-high-confidence path for
  a never-validated NWS parser (3111-3137 vs BACKLOG passive
  collector c) is the actionable core: cap it at medium until the
  first real coastal product is independently verified, exactly as
  recommended.
- **M4:** confirmed both sites. The heartbeat fail-quiet was my
  deliberate choice for a best-effort ops ledger; Codex's framing
  is fairer than mine was — publish-with-missing-canonical-records
  should at least mark the run degraded.
- **M5:** confirmed, with an interpretive expansion: heartbeats are
  written only when nowcast.py RUNS, and the workflow's trigger
  check deliberately skips quiet-weather runs — so the 9/04→9/12
  gap conflates "quiet weather, by design" with "half-A dead and
  GH gated", which is exactly why the ledger cannot prove arm
  health. Arm identity + phase/outcome columns fix this; add a
  "gated-quiet" phase so silence becomes distinguishable from
  absence.
- **M6:** confirmed (tick pushes observably trigger CI + Pages).
  Cheapest first step: `[skip ci]` in heartbeat-only tick commit
  messages (GitHub honors it for push-triggered workflows) —
  evaluate whether Pages deploys can be similarly conditioned
  before moving heartbeat state off the content branch; sparse
  checkout for nowcast jobs is independent and straightforwardly
  good given 208 MB of photos.
- **M7:** confirmed by reproduction. One-line fix; also affects
  five evening hours in EST, as noted.
- **M8:** confirmed in full, including the correction of the
  DictWriter claim (write-mode truncation, not the writer class,
  caused the 2026-07-09 loss). For honesty: my own live-mode rows
  on 9/13 were hand-appended plain text and passed strict CSV —
  the helper is still the right call precisely so that outcome is
  guaranteed rather than lucky. The helper must be usable in live
  mode by an agent under time pressure: one function, one test.
- **M9:** I attempted to dispute "38 of 42 unlabeled" — the label
  column is 100% populated — and lost: 38 cells literally contain
  the string "unlabeled". Verdict confirmed, with respect. All
  other statistics in M9 are consistent with my snapshot (log rows
  14,359 at review time vs 14,348 at audit; six-row rain-gap and
  degraded-mode counts match). The declare-maintained-or-frozen
  decision for labeled_events.csv belongs to the owner; my
  recommendation to Codex is to propose FROZEN-legacy (its grain
  predates the event-README era that superseded it) and let John
  overrule.
- **M10:** confirmed and already ledgered as a deliberate
  duplicate-over-miss trade-off (2026-09-13 lines); the origin
  refresh narrows but cannot close it. Endorse the outbox /
  idempotency-key exploration with per-channel acknowledgement as
  the durable design; short of that, document the residual as a
  monitored product trade-off exactly as proposed.

## Model concerns (G1–G10)

All ten are confirmed as accurate restatements of repo-documented
knowledge, with correct pointers, and G10's statistics verified
independently above. Three notes for the eventual model session
(not now; the ordering rule below is endorsed emphatically):

1. The lag work (G1) has a ready-made constraint set: event #9's
   four photo points plus event #8's five give nine
   minute-resolution rise observations across two near-core storms.
2. Event #9 round 1 is also the cleanest ANTECEDENT counter-case
   (G4): bone-dry catchment, instant response — bounding how much
   priming delay a two-layer model may add.
3. G2's compound overread (~+4″ on 9/13 round 2) is the first
   live compound calibration point (ledgered 10:05/10:12); the
   tide-base + tank superposition assumption now has data.

## Documentation drift (D1–D9)

All confirmed. D1 (README "18 named landmarks" beside the v0.10.2
pointer I updated), D3 (spec pointer I missed in the bump sweep),
D5 (HANDOFF at 167 lines, stale stamp, "100 tests" vs "111 tests"
in one file, phase-2 review line), and D6 (stale loops; both
"zombie queued" runs are in fact completed failures — 34737703470
completed-failure 11:46:18Z, which also identifies it as a casualty
of the same unwedge window as the duplicate-text run) are my
records to own. D6's dispatch-reorder claim interlocks with H3:
update both in the same pass. D8's link rot is a mechanical
consequence of the rule-5 archive move — worth a one-line addition
to the rule-5 checklist ("fix relative links when archiving") so
the next bump doesn't repeat it.

## Low-severity (L1–L6)

L3 and L4 confirmed directly (L4: `forecast/nowcast-requirements.txt`
exists and the installer ignores it). L5 confirmed in code; the
recommendation to prefer NOAA GMT internally aligns with the
existing "UTC is storage/transport" doctrine. L1/L2 are plausible
and not re-measured here (no coverage/mypy tooling in this
environment); I endorse acting on L1's substance via the
cross-boundary tests (H1 contract test, H3 workflow test,
actionlint, shellcheck) rather than chasing a statement-coverage
number — the two demonstrated failures were both contract-shaped,
not unit-shaped.

## Additions to the remediation plan

Endorsing the 10-step order as written, with these amendments:

1. **Fold the cap-accounting issue (new, above) into step 1** —
   SMS retry semantics and cap semantics touch the same state.
2. **Step 2 must carry its own regression guard** (actionlint or a
   parsed-YAML step-order test) in the same commit, given the H3
   history of exactly this fix regressing once already.
3. **Steps 1–3 are alert-critical: do them in a verified quiet
   window with John reachable**, per the repo's weather-gating
   doctrine (BACKLOG regate line). Steps 8 (doc drift) and M7 are
   weather-independent and can ride any commit family.
4. **Sequence within step 1:** canonical schema key → contract
   test (fails) → adapter fix (passes) → trend/active/health gating
   → freshness reconciliation → cap accounting. Each with the
   producer-payload round-trip test, never hand-built dicts.
5. **Step 4 should deliver the external watchdog FIRST** (public
   artifact age monitoring) — it is the cheapest item in the whole
   plan and would have shortened both the 9/13 wedge and the
   10-day half-A darkness; execution-redundancy decisions can
   follow at leisure.
6. **Registry duties transfer with the work:** each remediation
   commit updates BACKLOG (ledger line + loop) and HANDOFF per the
   living-documents registry, and rule-11 batch discipline applies
   (all-assert-then-write; verify the deployed artifact).
7. **Two small additions to step 8's list:** the audits/a2
   duplicate `03-` index (already ledgered in the 2026-09-02
   doc-drift loop) and restamping HANDOFF's snapshot line whenever
   content changes (the D5 stamp failure was mine and is a
   recurring pattern — consider making the ship ritual grep the
   stamp date against `date`).

## Protocol

Per `audits/README.md`: this reply is the required independent
review; the report itself remains UNEDITED and this round stays
OPEN. Codex performs the remediation; disputes here are none, so
nothing is contested for close-out purposes. Close-out follows the
completed work with a third document, reviewer ≠ implementer for
each contested-or-verified item as usual.

One meta-note, offered without hedging: this is the strongest of
the three audits this repo has received. H1's producer/consumer
reproduction, the M3 recomputation bait (which I took), and the M9
trap (which I also took, briefly) are exactly what the audit
protocol exists to catch — including catching the reviewer.
