# BACKLOG — open loops + ledger

**OPEN LOOPS is authoritative for "what's unfinished."** When HANDOFF
looks stale, trust this file. Ledger lines are append-only:
`YYYY-MM-DD | TAG | topic | one line` with tags
`[DECISION] [FACT] [DONE] [OPEN] [BLOCKER] [PREF]` and confidence
`[VERIFIED]/[STATED]/[INFERRED]` where a claim isn't ledger-backed.

## OPEN LOOPS (force-ranked)

- [ ] **Independent repo / v0.10.5 audit — HOLD (2026-09-23).** Codex
      reviewed candidate `ece4c2314`, all 11 Claude commits in the preceding
      24-hour window, and wider production contracts. Report:
      `audits/2026-09-23-a1/01-repository-and-v0.10.5-candidate-codex.md`.
      Release findings R1–R9: isolate outlook fetches from alert delivery;
      count unique tides for shadow readiness; propagate missing rain and
      complete the rolling horizon; reject expired guidance; conserve rain
      amounts/timing; repair map time/pathway controls; extend worst-pathway
      semantics to existing headline arms; reconcile central-source ladders;
      run decoder tests in CI (full-dependency suite currently fails).
      R10–R12 are explicit follow-ups: semantic gates/writer parity, date-scope
      labels, and honest gauge-error statistics. Claude owes round-02 reply;
      repaired-candidate verification + John's promotion DECISION precede bump.

- [ ] **7-DAY OUTLOOK (arc opened 2026-09-23, John).** Extend
      predictions to 7 days as a NEW display-only field + page, never by
      widening `all_tides` (which feeds alerts, per-tide pages, the
      ledger and the widget). Two layers on every surface: the honest
      astronomical layer and a labeled guidance layer (surge, wind,
      rain) with its band and source. Surge ladder by lead: CFW row →
      NWPS gauge forecast (72 h) → P-ETSS percentiles (102 h) →
      decayed persistence → astronomy labeled "no surge guidance".
      Rain beyond the 72-h NWS QPF grid uses NBM amounts, WPC fallback
      (decision recorded 2026-09-23). Alerts stay short-
      horizon (DECISION alert-horizon-48h). Widget unchanged; email
      link-only. Prereq Phase 0: ALERT_WINDOW_HOURS filter so the
      outlook cannot change alerting. Survey + plan in chat 2026-09-23
      07:45. SHIPPED 2026-09-23 (outlook v1): adapters + shadow ledger +
      page. OPEN: v0.10.5 class-(b) bump (AGENTS rule 5) for the new
      inputs, alert window and shadow policy — needs an independent
      candidate review + owner DECISION before the promoting commit
      (rule 12); replay goldens must pass unchanged. NBM percentile bands
      and human confidence-label phase-out shipped; audit repairs above and
      confidence-JSON removal remain open. Continue score collector (c).
**Active / near-term**
- [x] Audit `2026-09-18-a1` CLOSED 2026-09-18 (round 03, b24220653):
      Codex's work verified and stands; trailer erratum + AGENTS rule 12
      landed; v0.10.3 ratified retrospectively by John.
- [ ] Writer/validator parity (2026-09-20 outage lesson, for Codex): a
      producer round-trip test for EVERY ledger/JSON writer against the
      gate — predictions_log, day_risk_log, heartbeats, observed_peaks,
      tide caches; and surface hourly-run gate failures as a workflow-level
      alert (42 red runs went unnoticed for 42 h).
- [ ] Re-copy widget source v7.29a into Scriptable: exact fall-back-hour
      parsing (v7.27a) and the driveway rung REMOVED (v0.10.4); v7.26a
      remains installed as of 2026-09-14 and renders correctly meanwhile.
- [ ] Nowcast scheduler: trigger TRIPPED by event #7 (18-min publish
      gap covered the entire rise). Half-A (launchd, Mac-awake hours)
      believed installed 2026-08-07 but NEVER fired until revived
      2026-09-02 (see scheduler-half-A-correction ledger line);
      external trigger (24/7) ready for owner credentials in
      history/plans/external-trigger-scheduler.md. It covers cron failure,
      not a wedged Actions queue. The independent Mac watchdog was deployed
      and notification-armed 2026-09-14; it covers awake hours, while an
      always-on host remains optional. Local execution redundancy for alert
      delivery remains owner/security-gated (production secrets).
- [ ] Durable alert outbox/idempotency: per-rail acknowledgments now retry
      ordinary partial failures, but a process death after provider acceptance
      and before the state commit remains duplicate-over-miss by explicit
      safety choice. True exactly-once needs provider idempotency or a durable
      external delivery service; do not fake it with pre-send suppression.
- [ ] Town map, staged features: bands/classic shading toggle;
      per-building doorsill tagging (user point-and-click, feeds
      freeboard); possible georeferenced user snapshot base layer.
- [ ] Antecedent wetting (model gap, user field insight 7/18): tank
      is memoryless about hillside priming; every double-pulse event
      is a calibration pair. Candidate: trailing-rain multiplier on
      K or two-layer soil reservoir. Related: duration-explicit
      V=C·(R−D)·T upgrade. Priming is ONE of SIX structural insights
      queued as the next model session's menu — see "Model
      consequences" in assets/observations/2026-07-18/README.md. The
      2026-09-18 offline assessment found no independent wetness
      covariate yet; do not fit a post-hoc wet/dry label.
- [ ] Stateless-nowcast tank window: each run integrates from V=0
      over ~1 h of frames — understates once a burst ages out.
      Current decay leaves only 2.4% after 60 dry minutes; standalone
      persistence is deferred until paired with a tested long-tail or
      antecedent structure. (day-max memory partially compensates.)
- [x] Time-varying nowcast bay-head prototype completed 2026-09-18 against
      102 official NOAA six-minute rows: moving astronomy + constant surge
      improves Oct 30 strongly but is neutral/slightly worse on Dec 19 when
      surge evolves. Production remains fixed-head pending the next item.
- [ ] Surge-tendency / head-expiry candidate: predeclare a bounded observable
      recent-surge rule and explicit degraded-tail behavior. Do not select
      fixed/constant/trend per event after seeing the outcome; reserve the
      next compound event for independent validation.

- [ ] edge_20260901 map points from event-#8 photos 14-16 (Central
      arm extent at peak) — needs user pick_coords clicks.
- [ ] Aug 27 brother's Rt 36 photos → third-party/ when obtainable.

- [ ] Ponding-dip field verification: user drives the top-20 list
      (history/data/ponding_top20.md, GPS-ready coords) as time and
      events allow — each yes/no calibrates layer precision. Future:
      pooled-volume routing to final minima (user sketch 2026-09-02);
      grate-backup probability by drainage position — deliberately
      out of scope until the 342-corner methodology earns extension.

- [ ] WATCH: nowcast.yml dispatch-after-publish path is regression-tested
      and its two intents consolidate into one fail-closed retry (2026-09-14),
      but still needs observation at the next production radar trigger.
- [ ] Event #9 residual: edge_20260913 map points need user pick_coords.
      EXIF timeline, peak pin, model plot, nine-anchor refresh, and the
      last-published overnight forecast-skill score are complete.
- [x] GH Actions outage runs 34737703470 and 34737375383 are completed
      failures, not queued zombies (registry correction 2026-09-14).
- [ ] Extra-rain slider on the town map (DEFERRED low-priority,
      user 2026-09-02): if built, option (a) only — drive the
      calibrated 342 models and repaint Highlands low-shelf streets,
      parity with the main page's scope; no town-wide fabricated
      depths.

**Parked (user-gated or seasonal)**
- [x] NOAA fall-back-hour ambiguity CLOSED 2026-09-18: all NOAA transport
      uses GMT; current tide, gauge, cache, forecast, and prediction-log
      identifiers are offset-bearing station-local ISO. Both repeated 01:xx
      hours remain distinct; legacy naive rows retain explicit fold=0.
- [x] Static DOM/accessibility contract: dependency-free parser checks every
      current landing/reference/map/tide-index/per-tide surface for document
      landmarks, unique IDs, valid fragments, accessible controls/links/
      buttons/images/canvases; source labels repaired and the production
      publish gate now enforces the contract.
- [x] Incremental static typing started at the two pure seams:
      `station_time.py` and `html_contract.py` are fully annotated and
      strict-mypy gated in CI with an exact tool version. Expansion remains
      seam-by-seam; this does not imply the facade is typed.
- [ ] Engineering breadth: checksum-pinned actionlint 1.7.12 and ShellCheck
      0.11.0 are CI gates. Real browser runtime smoke tests and incremental
      typing beyond the two pure seams remain as modules become tractable;
      static DOM/accessibility and the two audit-regression contracts are
      covered.
- [ ] Falling-tide stall experiment (user field task; drain coupling
      "breathing" first written up 7/13 tide event).
- [ ] Drainage-map email to Stephen Winters (user task).
- [ ] SMTP migration off current provider.
- [ ] Annual analytics refresh each January
      (`history/scripts/analyze.py` + `pull_sandy_hook_history.py`).
- [ ] Sandy-era rain archives hunt (extend anchor set backward).
- [ ] PASSIVE COLLECTORS (opportunistic, when conditions occur):
      (a) verify enhancement holds at SH ≥ 7.5 ft (one multi-grate
      spot-check during a big tide); (b) cold-conditions events —
      each is a cold-lockout-hypothesis data point (advisory-only
      since 2026-05-19); (c) NWS surge-parser first-real-event
      SCORING — the parser saw its first real product 2026-09-23
      (CF.Y.0021) and was fixed the same morning to read the raw CFW
      product; what remains is comparing its Sandy Hook projections
      (6.9 / 7.2 / 7.2 / 7.5 ft MLLW for the 09-23 PM .. 09-25 PM
      tides) against observed peaks in the ledger before the
      confidence rule's "awaits first independently verified real
      event" medium cap is lifted.
- [ ] Confirm/deny 2025-08-21 flood (user saw swirly mud stains at
      August rental inspection — proto-mud-tracer): if primary evidence
      emerges, add it to labeled_observations.csv plus an event README;
      labeled_events.csv is frozen legacy. Low value; tide calibration
      no longer gates anything.
- [ ] Someday/speculative queue: attic archive §9 items 17–27 +
      §9e.4-adjacent (ETSS retry, NYHOPS, multi-town spin-offs,
      subscribe flow, iOS app stages, reanalysis, mesonet rain).
      Consciously move an item OUT of the attic to activate it.
- [ ] Datum line for widget + map-overlay chart (single chosen datum;
      deferred from the 2026-07-21 datums feature).
- [ ] forecast/flood_forecast_daily.py split — REGATED 2026-09-02:
      not season-gated (there is no off-season here: convective
      May–Sep, tropical Jun–Nov peaking ~Sep 10, nor'easters
      Oct–Apr); gate is a quiet WEATHER WINDOW per extraction, one
      seam at a time per forecast/README.md. Low-risk seams first
      (station_time, rendering — any calm evening); model_core and
      alerts only in a verified 7–10-day quiet spell; never with
      weather inbound. Additive evidence schemas + SLO monitor +
      erratum convention are NOT gated at all.
- [ ] Choose/retire duplicated peaks charts after longer A/B (user
      single-user A/B since 7/07).

**Audit 2026-08-03-a2 remediation program (Codex full-repo audit;
all findings verified — see audits/2026-08-03-a2/)**
- [x] Phase 0: unify station-local day/time everywhere (21 naive
      now()/today() calls; injected clock + UTC-boundary/DST tests;
      TZ env as defense) — shipped `5332dd70`.
- [x] Phase 0: nowcast source-freshness semantics (source_latest_utc,
      age, frames expected/succeeded; site keys "live" off SOURCE
      time); 45-min hold labeled — shipped `5332dd70`.
- [x] Phase 0: heal_tree fail-closed for alert_state.json (quarantine
      + recover origin blob — it is transactional state now, not a
      cache); CSV-parse the predictions-log union; stop deleting
      unregenerated docs artifacts — shipped `5332dd70`.
- [x] Phase 1: CI triggers beyond forecast/tests (data/model/docs
      inputs); semantic gate checks (timestamps, enums, future-time
      rejection, freshness); dispatch-failure visibility + retry;
      pin actions/deps/CDN (SRI); _html_escape NWS feed text — shipped
      `5332dd70`; 67 tests + gate green; Claude round-03 PASS
      (`e9dcdff0`).
- [x] Phase 2: repo-relative v0.10.1 refit/hindcast command +
      golden/physics tests (freeze behavior, no retuning);
      evidence-count prose precision (six anchors / two hydrographs /
      one recession constraint); all_anchors recipe moved off the
      scratchpad import — implemented (77 tests then, 100 now);
      Phase 2 reviewed PASS in round 05.
- [x] v0.10.3 `_pluvial_fill()` continuity correction promoted atomically
      2026-09-18: reference-equivalent to 1.07e-14″; sampled maximum
      correction 0.090″; frozen peak changes 0–0.063″; no clock changes,
      constants, landmarks, or retuning. The held moving-head rule remains
      excluded.
- [x] Erratum convention codified + test-enforced (2026-09-02;
      pre-convention rows grandfathered) — see
      data/labeled_observations_README.md.
- [x] Cadence SLO monitor shipped 2026-09-02: rolling heartbeat
      ops ledger (data/nowcast_heartbeats.csv, 30 d) + details-page
      active-period gap stats line ("measured truth" of best-effort).
- [x] Audit a2 closeout: CLOSED round 05 (Phase 2 reviewed PASS,
      M2/L2 reconciled — audits/2026-08-03-a2/05). This checkbox
      lagged HANDOFF/audits until the 2026-09-02 sweep caught the
      contradiction in the file declared authoritative.
- [x] Anchor-count reconciliation (2026-09-02 sweep; CLOSED
      2026-09-03): canonical framing settled — SIX frozen v0.10.1
      anchors (fixture/spec/tests, immutable model provenance) +
      post-cutover measured events as ‡ recipe hindcasts. Figure
      rebuilt with all EIGHT measured floods (Aug 7 added for the
      first time; the stale six-event xlim had been CLIPPING Oct 30
      out of the committed PNG); ‡ footnote added; titles/docstring/
      README/HANDOFF counts reconciled. Spec + tests correctly kept
      at six.
- [x] driveway_central landmark (2026-09-02 sweep; CLOSED
      2026-09-03): cross-fit DONE — threshold 13.8–13.9″ vs SW grate
      ≈ 4.67 NAVD88 from the #6-negative/#8-positive bracket, landing
      within 0.01 ft of the independently surveyed porch_step_base
      (4.68) — two methods, same grade. Documented in the ledger
      README's new "Non-model landmark keys" section along with
      fire_hydrant_central, pocket_SE_retention, and legacy
      porch_step (erratum row appended for the 2025-10-30T14:54 row
      — the retracted-key row was the Oct 30 reconstruction, not
      2026-06-14). Registration in ff.LANDMARKS deferred to the next
      model version bump per rule 5.
- [ ] WATCH: nowcast.yml storm-path dispatch still untested until
      the next radar trigger. (The launchd half of this watch
      CLOSED 2026-09-03: three timer-fired ticks at exact 10-min
      cadence, 04:03/04:13/04:23Z, all status 0 — half-A verified
      in production, not just kickstarted.)
- [x] Doc-drift batch (2026-09-02 sweep; CLOSED 2026-09-03): README
      authority pointer → AGENTS-first + stale widget-refresh line
      replaced; archived spec paths now cite model/archive/ (5
      READMEs + flood_history_report, which also got its scripts/
      → history/scripts/ command fix); orphaned pre-v0.5
      analysis/{cross_ref,rain_analysis}.py (inputs don't exist)
      moved to attic/; audits/README documents the a2 03- index
      collision as a standing exception; nowcast_tank.py runner
      path corrected to ~/.barnacle/venv; cold_weather report now
      flags rain_24h_in as an unpopulated placeholder; 2026-08-27
      README documents the objective forecast_accuracy omission
      (no measured peak); 2026-07-13 README documents analysis/
      absence (tide event — PLAYBOOK plots target pluvial);
      2026-05-18 README points at the 5/19 photo subdir.
      (2026-07-13 was NOT the retracted event — it is a real
      measured tide session; the fabricated flood merely claimed
      its date.)
- [x] Machine-local paths (2026-09-02 sweep; CLOSED 2026-09-03):
      tank_model_fit.py + fit_crdt.py now repo-relative via
      __file__; guard test widened to both all_anchors copies +
      all three history/scripts recipes (event_hindcast.py made
      the list by already being clean).
- [ ] tanh 1.2 in/hr scale in the pluvial advisory self-labels as
      PLACEHOLDER in the live model path — promote to the
      model-session menu (assess, never retune casually).


**Standing obligations**
- List `audits/` at session start; reply to open reports.
- Keep the living-documents registry (AGENTS.md) satisfied.

**Audit 2026-09-14-a1 remediation (independently verified; CLOSED)**
- [x] Phase 1: canonical nowcast contract; projection/trend/health/freshness
      gating; stale-gauge fallbacks; per-rail alert retry; separate SMS/base
      caps; one fail-closed post-publish workflow dispatch; contract and
      workflow regression tests.
- [x] Phase 2 code: local scheduler gets PID-aware stale-lock recovery,
      nonzero failures, rotated JSONL outcomes, pinned install/self-test,
      quiet-publication coalescing; heartbeats gain arm/phase/outcome and
      gated-quiet rows; stdlib public watchdog + tests; half-B renamed
      external trigger. The Mac watchdog was deployed and armed 2026-09-14;
      the external trigger still requires owner credentials.
- [x] Phase 3: atomic per-file writes and fail-closed required surfaces;
      generation/schema/model stamps checked across landing, details, JSON,
      and current tide pages; adversarial ledger/state/nowcast validators;
      append-only hourly day-risk product while preserving 09Z snapshots;
      80th-percentile error radius + NWS parser medium cap; safe observation
      append CLI; correct UTC commit dates. Full site regenerated and gated.
- [x] Phase 4 disposition/docs: D1-D9 repaired; labeled_events declared frozen;
      privacy posture explicit; confidence analysis recorded; archive links
      now tested; exactly-once delivery, external activation, and broader
      tooling remain open. DST ambiguity subsequently closed 2026-09-18.
- [x] Phase 5 triage: G1-G10 consolidated into
      history/plans/model-v0.11-assessment.md with acceptance criteria. No
      formula or constant changed; any accepted candidate needs its own model
      version and frozen-golden update. Initial offline pass completed
      2026-09-18: time-varying head + fill-continuity advance to candidate work;
      single-lag, forcing switch, standalone persistence, and tide-bias
      retune rejected (history/reports/model-v0.11-assessment-2026-09-18.md).

## LEDGER (append-only; newest last)

2026-07-21 | DONE | codex-audit-arc | 4 criticals verified→fixed same day; transactional alerts, time helpers, input health, v0.10.1 stamp, offline CI [VERIFIED: tests/ + audits practice]
2026-08-03 | FACT | event-#6 | pluvial flood, peak +13.8″ ~10:33 ET, 5th of 6 measured; hindcast +13.4″; first live transactional-alert firing (3/3 channels) [VERIFIED: assets/observations/2026-08-03/]
2026-08-03 | DONE | retraction | "7/13 +19.5″ flood" never happened — all-hours QPE 0.00; removed from rankings; provenance rule added [VERIFIED: 2026-07-18 README retraction]
2026-08-03 | DECISION | 7/6-anchor | crest window [+15.0,+15.8], canonical +15.4 (window center); calibration unchanged [VERIFIED: model docs + event README]
2026-08-03 | DECISION | nowcast-scheduler | accept the cadence gap for now; revisit triggers recorded [STATED by user]
2026-08-03 | DECISION | alert-volume | daily cap 2 confirmed deliveries; warning-first texts [STATED by user; VERIFIED in tests]
2026-08-03 | DONE | town-map | Highlands street flood map shipped: LiDAR street elevations, band palette, scrubber, zoom/pan, OSM base layer, burst-aware rain view (Highlands-scoped) [VERIFIED: docs/highlands.html live]
2026-08-03 | DECISION | brain-migration | HANDOFF→short wholesale snapshot; AGENTS/BACKLOG/PLAYBOOK/audits split; old HANDOFF archived verbatim in attic/ [STATED by user; this commit]
2026-08-03 | DONE | audit-2026-08-03-a1 | distillation audit: 0 critical, 7 edge findings, all confirmed + patched same day (porch-tape stale-import, PLAYBOOK dead ref + fragment, collectors/someday-queue pointers restored) [VERIFIED: audits/2026-08-03-a1/]
2026-08-03 | FACT | audit-2026-08-03-a2 | Codex full-repo audit: 5 high + 7 med/low, ALL verified in reply; M1 data errors (row-151 AM/PM, day-max 9.0→13.2) fixed same day; remediation program queued above [VERIFIED: audits/2026-08-03-a2/]
2026-08-03 | DONE | audit-a2-phases-0-1 | station-local clock, source-aged radar/coverage, fail-closed transactional recovery, semantic gates/all-path CI, dispatch visibility, supply-chain pins/SRI, external HTML escaping; 67 tests green [VERIFIED: 5332dd70 + audits/2026-08-03-a2/03-remediation-implementation-codex.md]
2026-08-03 | DONE | town-map-expansion | all four towns live: 739 ways / 8,067 vertices / 7,227 LiDAR points (0 missing; Rumson-bridge water reads nulled); widened base layer; rain view Highlands-only confirmed [VERIFIED: docs/highlands_streets.json + this commit]
2026-08-03 | DONE | audit-a2-phase-2 | frozen v0.10.1 reproduction: versioned 24-point fit + six-event hindcast fixture, RMS 1.3168→reported 1.32, event goldens/timing, stage/drain/rise/recession physics gates, exact evidence taxonomy, scratchpad path removed; no retuning; 77 tests green [VERIFIED: history/scripts/reproduce_v0_10_1.py + tests/test_model_reproduction.py]
2026-08-03 | DONE | region-map | full map-view street coverage: 9 towns (incl. Rumson/Fair Haven/Red Bank/Navesink/Belford edge) + all of Rt 36; 2,347 ways / 26,116 vertices / 27,457 LiDAR points, 0.2% missing (bridges); magma elevation view + historic-flood ticks shipped same evening [VERIFIED: docs/highlands_streets.json]
2026-08-07 | FACT | event-#7 | surprise pluvial flood: lawn step 18:30-34, porch base 18:37, peak >= +14.9 (backcast ~+15.5 @18:40), 7 water fixes + drain phases + tilted pool (2nd) + north-pair tail (3rd) [VERIFIED: ledger + assets/observations/2026-08-07/]
2026-08-07 | FACT | event-#7-surfaces | app said NO FLOODING through the rise: 18-min publish gap, headline owned by outlook, radar had no alert pathway, no text (state file: rank 0 all evening) [VERIFIED: screenshots + git nowcast history]
2026-08-07 | DONE | radar-alerts | live radar street/projection now ranks alerts (transactional + daily cap + falling-trend guard) + workflow dispatch; 92 tests [VERIFIED: tests/test_radar_alerts.py]
2026-08-07 | DONE | worst-truth-headline | strip regime_display (rising→projected class, falling→drain clock); widget v7.25a live-class override; SMS leads with radar line [VERIFIED: commit + site regen]
2026-08-07 | DONE | scheduler-half-A | launchd 10-min local tick from dedicated clone ~/.barnacle/repo; first tick pushed 23:23Z [VERIFIED: origin log "local tick"]
2026-08-07 | OPEN | event-#7-analysis | README + plots + 2-min hindcast (rising-undershoot/falling-overshoot question; day-max +16.9 vs measured ~+15.5) + mud-line peak refinement [STATED plan]
2026-08-09 | DONE | event-#7-wrapup | README + photo-EXIF timeline (lawn 18:33:16, porch base 18:37:00) + hydrograph/hindcast (+16.9@18:50 vs ~+15.4@18:40 — first HIGH-side miss; live undershoot was MRMS first-pass latency) + gauge sanity + QPE 1.59in/35min; crest ~+15.4 TIES 7/6 for 4th of 7 [VERIFIED: assets/observations/2026-08-07/]
2026-08-09 | DONE | quiet-hours | all alert channels hold 20:00-07:00 local unless about THAT night; email warning-first fixed (1:23 AM NO FLOODING email); 97 tests [VERIFIED: tests + commit]
2026-08-09 | OPEN | model-session-menu | event-#7 additions: MRMS first-pass vs revised latency handling; k_out at maximum head (bay -33in); stateless-window state persistence [STATED hypotheses, do NOT retune casually]
2026-08-09 | DECISION | parallel-arms-rule | AGENTS.md rule 8 hardened: any semantic update to one arm applies to ALL arms carrying that meaning, same work unit; exemptions must be objective (concept absent / already present), never channel-worthiness judgment; ask John when unsure [STATED by user]
2026-08-09 | DECISION | residue-evidence-doctrine | mud lines demoted: optional rain-flood detective tool, valid only under preservation conditions (transient daytime burst + abrupt clearing); absence probative only when presence would have survived; tidal floods use wrack lines; primary data = landmark-crossing observations [STATED by user; PLAYBOOK updated]
2026-08-20 | FACT | aug-10-13-springs | 4 consecutive photo-verified street evenings; visual bounds bracket gauge <=0.1 ft; as-run errs <=0.18 ft [VERIFIED: ledger rows + assets/observations/2026-08-1x]
2026-08-20 | DONE | peaks-chart-range | all-pathways chart: full-history payload + From/To picker, default view unchanged; per-tide twin objectively exempt (ordinal axis) [VERIFIED: docs/index.html]
2026-08-20 | DONE | peaks-chart-fixes | default-window bug fixed (axis bounds now derive per build from the sliced window — first render had pinned to Oct 30 full span); picker dates local not UTC; low-tide toggle added (191 astronomical lows 2026-05-18→, cached data/low_tides_cache.json, small slate down-triangles, default off) [VERIFIED: docs/index.html node-checked]
2026-08-20 | DONE | peaks-chart-backfill | observed tide peaks backfilled 2025-10-01→2026-05-18 from NOAA VERIFIED high_low (624 observed peaks now in payload; fetched once, cached forever); lows cache extended to same start (633). Pre-Barnacle era shows observed squares only — no fabricated predictions [VERIFIED: docs/index.html payload]
2026-08-20 | DONE | peaks-chart-future | future extended +60 days via astronomy: 111 tide-only peaks (paler circles, 'no surge' label) + lows to same horizon; payload now spans 2025-10-01 → 2026-10-19 [VERIFIED: payload counts]
2026-09-02 | FACT | event-#8 | 2026-09-01 ~19:25 ET pluvial peak ~+13.9 (lawn-step bottom, bracket 13.7-14.2) on DEAD-LOW bay; burst 1.9-2.0 in/hr box-mean x ~10 min; 19 EXIF photos [VERIFIED: assets/observations/2026-09-01/]
2026-09-02 | FACT | nowcast-skill | 19:15 run projected +14.3 with street 0.0 — 8 min early, err +0.4 vs measured; cadence 10-13 min throughout [VERIFIED: nowcast commits a39ad6704..]
2026-09-02 | DONE | radar-alert-race | dispatched run raced the nowcast push and read the pre-burst file — NO text for a projected lawn-step flood; nowcast.yml dispatch steps moved AFTER commit/push [VERIFIED: event README + workflow]
2026-09-02 | DONE | event-#8-analysis | hindcast +12.0 @19:36 (-1.9, +11 min vs photos) — 3rd confirmation of near-core lag overestimate + tail-recession overhold; as-run projection beat the hindcast; all-anchors refreshed to 7 [VERIFIED: 2026-09-01/analysis/]
2026-09-02 | FACT | 2026-08-27-event | EVIDENCED UNMEASURED flood (user in CA): radar 1.9-3.8 in/hr ~45 min, hindcast +16.1 [INFERRED]; residue mud up driveway >= lawn-step class; 2 alerts delivered incl. mid-burst FFW; nowcast dark 12:53-19:40 (launchd traveled) [VERIFIED: 2026-08-27/README.md]
2026-09-02 | DECISION | photo-privacy | standing rule: blur every identifiable face except John before committing photos (public repo); John has standing consent [STATED by user; AGENTS.md rule 9]
2026-09-02 | DONE | ponding-dips | user's 2026-08-03 local-minima idea shipped: 1-D road-profile sag detector (history/scripts/detect_street_sags.py) -> 414 dips (>=1 ft, >=6 ft elev, cap 10) -> town-map toggle w/ tap readouts; VALIDATED: the Rt 36/Navesink valley type-example detected (10 ft dip @ 74 ft + 8.4 @ 49). Two earlier graph-based attempts produced absurd 140-ft basins (road-graph pour ignores overland flow) — rejected before shipping [VERIFIED: docs/highlands_sags.json]
2026-09-02 | DONE | ponding-v2 | cross-street discount (71 drained), low-shelf tier (56 purple), top-20 GPS field list; DIAGNOSTIC: the 342 corner does NOT register — its bowl is curb-scale + drain-driven, below 25-m profile resolution — documented as the scope boundary between this layer and the calibrated corner model [VERIFIED: docs/highlands_sags.json + explainer]
2026-09-02 | DECISION | town-rain-slider | deferred low priority; if ever built, calibrated-scope option only [STATED by user]
2026-09-02 | DECISION | phase3-regate | split gated on quiet weather windows per-seam, not on a season; additive items ungated [STATED by user concern -> assessed; forecast/README.md seams]
2026-09-02 | DONE | phase3-wave1 | seam 1 (station_time) extracted w/ facade re-exports; additive items shipped: nowcast_schema_version, cadence SLO monitor, erratum convention+test; rendering seam extraction delegated to a worktree agent for review [VERIFIED: 98 tests + gate + both import modes]
2026-09-02 | DONE | phase3-seam2 | rendering seam landed: 37 renderers / 3,460 lines to forecast/rendering.py, facade 10,339->7,007 w/ full re-exports; worktree agent extraction (killed by session limit AFTER committing), independently verified + landed post-reset [VERIFIED: 98 tests + gate + dual-mode imports + live-data-only docs diff]
2026-09-02 | DONE | house-point-fix | constant corrected to the true intersection (40.405479,-73.995195) at all 5 sites; MRMS point-column comparability noted (pre-2026-09-03 rows used the old bluff-toe point; box means unaffected) [VERIFIED: grep + 98 tests]
2026-09-02 | DONE | aug27-witness-overlay | event_hindcast.py recipe COMMITTED (history/scripts/ — was scratchpad-only despite two README citations; rule 4 applies to scripts) + witness lower-bound overlay support; Aug 27 companion plot hydrograph_witness.png (original untouched per user): model +11.7 at the 2:43 driveway bound >=13.8 (-2.1 short), first reaches 13.8 at 3:02 PM (~19 min after witnesses) — 4th near-core-lag quantification, first from testimony [VERIFIED: 2026-08-27/analysis/ + README]
2026-09-02 | DONE | aug27-nine-storm-figure | onset-aligned street-water overlay of all 9 logged storms (6 frozen-replay + 3 MRMS-cache curves; each reproduces its committed hindcast peak exactly), Aug 27 emphasized, witness driveway bound marked; audience = Kevin+Jackie per user [VERIFIED: 2026-08-27/analysis/event_comparison.png + printed peaks]
2026-09-02 | FACT | seam2-revert-incident | rule-11 incident #6: the 23:19 house-point ship's conflict-ritual recovery reapplied a STALE pre-seam-2 facade copy from the scratchpad, silently reverting the rendering extraction (~40 min; 3 nowcast runs executed the behaviorally-identical monolith — so the "refactored facade's first production run" claim was FALSE). Caught by the loose-ends audit sweep; confirmed via git show --stat 0398f0416 (+3,514 lines on a 2-line commit) [VERIFIED]
2026-09-02 | DONE | seam2-restore | facade restored from 5854089db, house-point 2-line fix reapplied via all-assert batch; NEW tests/test_module_split.py makes facade/module duplication itself a test failure (the exact mode 98 green tests could not see); 100 tests green [VERIFIED: wc 7,007 + gate + dual-mode imports]
2026-09-02 | DONE | heartbeat-staging-fix | audit-sweep findings 3+4: data/nowcast_heartbeats.csv was written every nowcast run but staged by NEITHER publish path — SLO ledger stuck at 1 row ("collecting..." forever) AND the dirty tracked file would fail the rebase-retry on any push race (same class as the event-#8 dispatch race). Fixed: both git-add lines stage it; .gitattributes union-merge so racing appenders never conflict; cadence reader now sorts rows [VERIFIED: grep both paths + 100 tests + gate]
2026-09-02 | FACT | scheduler-half-A-correction | half-A NEVER ran: 2,077 consecutive launchd failures since 2026-08-07 — the dedicated clone was created 42 s before bin/ existed on origin and never pulled. The 08-07 DONE line's [VERIFIED: origin log "local tick"] was a manual main-tree run, not launchd. GH cron was the SOLE nowcast scheduler 8/7-9/2 incl. the 8/27 dark window (post-mortem cause corrected via ledger erratum). Fixed: clone pulled current, installer now always-syncs, kickstart-verified genuine tick e6f6c05dd 03:52Z, launchctl status 0 [VERIFIED: ~/.barnacle/logs/launchd.log + clone log]
2026-09-02 | DONE | audit-sweep-records | records batch: public "calibrated on FOUR events" claim (survived closed audit a2/L2 in the one renderer its close-out missed) fixed + guard test widened to BOTH split halves; a2 closeout checkbox closed (BACKLOG lagged audits/); +16.1-vs-+16.4 hindcast discrepancy resolved by ledger erratum + README supersession markers; HANDOFF drift fixed (v7.25a, 100 tests, nine-town, launchd cause); forecast/README.md seam statuses marked; 7 new OPEN loops queued (anchor-count, driveway_central, doc-drift batch, local paths, tanh placeholder, launchd watch) [VERIFIED: 100 tests + gate]
2026-09-03 | DONE | all-anchors-eight | figure rebuilt: Aug 7 (#7, +15.4 crest window 15.0-15.8, hindcast +16.9 ‡) added for the FIRST time; stale six-event xlim had been clipping Oct 30 (+20.8, largest measured) out of the committed PNG while title said six and docstring said 7; ‡ footnote defined (post-cutover recipe hindcasts vs six frozen fixture anchors — spec/tests correctly stay at six); README/HANDOFF counts reconciled [VERIFIED: regenerated all_anchors.png, all 8 visible]
2026-09-03 | DONE | driveway-central-crossfit | threshold cross-fit from the #6/#8 bracket: 13.8-13.9 in vs SW grate ~ 4.67 NAVD88, within 0.01 ft of the independently surveyed porch_step_base (4.68) — driveway apron and walkway share a grade, two methods agree. Documented in ledger README "Non-model landmark keys" (with fire_hydrant_central, pocket_SE_retention, legacy porch_step + erratum row for 2025-10-30T14:54); ff.LANDMARKS registration deferred to next model version bump per rule 5 [VERIFIED: ledger tests + README]
2026-09-03 | DONE | doc-drift-batch | tier-3 sweep findings closed in one pass: README authority+staleness, archive spec paths (6 files), orphan scripts -> attic, audits 03- collision documented, nowcast_tank runner path, rain_24h_in placeholder flagged, forecast_accuracy 8/27 omission documented, 07-13 analysis-absence + 05-19 photo-location notes; machine-local paths fixed (tank_model_fit, fit_crdt -> __file__-relative) and the local-path guard test widened to 7 files; pre-existing joined-bullet formatting in 8/27 README repaired [VERIFIED: 100 tests + py_compile + gate]
2026-09-03 | FACT | half-A-timer-verified | three consecutive timer-fired launchd ticks at exact 10-min cadence (04:03/04:13/04:23Z, status 0, each pushing nowcast + heartbeat row) — half-A production-verified end to end; watch item narrowed to the nowcast.yml storm-path dispatch [VERIFIED: origin log + launchctl]
2026-09-03 | DECISION | v0.10.2-bump | user ordered the landmark registration bump ("might as well bump it up for the sake of explicit progress"), landmark-only scope; _pluvial_fill fix deliberately NOT folded in (needs its own assessed bump + goldens) [STATED by user]
2026-09-03 | FACT | driveway-ramp-correction | user field correction logged: the driveway is a RAMP (sidewalk drops to street at curb cut; road rises intersection->driveway; past the sidewalk it climbs ~1 SUV length to the garage; a stretch beyond the sidewalk plausibly near yard grade); "up the driveway" in his usage = beyond the sidewalk; mud deposits preferentially along Central (NE corner->hydrant->driveway) vs thin on lawn-step walkway. The "apron and walkway visibly share a grade" claim was agent overreach — RETRACTED in ledger README; cross-fit reframed as a THRESHOLD OBSERVABLE (corner stage where driveway-entering flips), not a point elevation [STATED by user]
2026-09-03 | DONE | v0.10.2-shipped | driveway_central registered at 4.67 NAVD88 (SH 7.49) as threshold observable: spec model/v0.10.2.md written (ramp + mud caveats in honesty register), v0.10.1.md archived, CURRENT_MODEL_VERSION restamped, ladder 18->19 in facade AND widget (v7.26a — USER MUST RE-COPY into Scriptable), README/predictions_log_README/AGENTS/HANDOFF/ledger-README counts+stamps in lockstep, frozen-replay cutover guard made lineage-aware (constants equality stays the hard retuning guard), site regenerated (forecast.json v0.10.2, driveway row on index+details) [VERIFIED: 100 tests + gate + deployed-artifact greps]
2026-09-03 | FACT | driveway-conflation-note | user (01:12 AM, closing the topic): historical "driveway" mentions likely CONFLATE distinct observables — (a) the water's EDGE advancing up Central reaching the driveway's LOCATION (an edge-elevation opportunity: take a landmark measurement at that same moment and the water level assigns that ground point an elevation — the likely original weeks-old goal), vs (b) water coming UP the driveway ramp itself (higher stage; by then the Central edge is at the next-door neighbor's or beyond). The v0.10.2 threshold observable stands as defined (photographed-entering, #6/#8 bracket), but read pre-2026-09-03 "driveway" prose with this caveat. User's framing, agreed: these are map-improvement refinements — Barnacle's core instruments for 342 Bay remain the intersection, grates, lawn step, and porch ladder [STATED by user]
2026-09-13 | FACT | event-#9 | dawn pluvial flash flood: rain onset 10:48Z (6:48 ET), core ON the house by 10:54 (box-mean 3.16, point 3.78, box-max 4.05 east/up-hill), ~0.4 in in ~25 min; peak ~lawn-step level ~+13.7 [STATED, photos pending]; rising mid-tide bay ~1.5 NAVD88 (pure pluvial, full drain); receded driveable by 7:30; user witnessed river-like inflow down Bay from the east (hillside delivery made visible) [VERIFIED radar+gauge; assets/observations/2026-09-13/]
2026-09-13 | FACT | event-#9-model | hindcast +12.2 @ 7:14 vs ~+13.7 measured: -1.5 low with point>>box near-core signature (4th low-side confirmation) AND recession overhold (tank ~9 in at 7:30 vs driveable roads — 4th overhold confirmation); timing good. BOTH standing biases in one event [VERIFIED: analysis/hydrograph.png]
2026-09-13 | FACT | outage-post-mortem | Barnacle DARK 03:56Z-11:5xZ — through the ENTIRE flood: (a) GH Actions queue wedge ~04:15Z (runs stuck queued; two zombies left: 34737703470, 34737375383 — cancel manually or let GH cull); (b) launchd half-A silently wedged since 2026-09-03 10:32Z — exhausted push-retry left an unpushed clone commit, every later pull conflicted/aborted/exit-0 (status 0 for 10 days). NO radar alert possible; storm-path dispatch STILL untested. Flood Watch had been surfaced ~2 AM Sept 12 (pre-outage) [VERIFIED: gh run list + launchd.log + clone log]
2026-09-13 | DONE | tick-script-hardening | local_nowcast_tick.sh: clone now disposable-by-design at all 3 wedge points (initial pull conflict -> reset+continue; mid-retry conflict -> reset+exit; retry exhaustion -> reset) — losing one tick is fine, wedging forever is not; clone reset to origin, salvaged 2 orphan heartbeat rows to scratchpad; manual nowcast+forecast published per PLAYBOOK live-support [VERIFIED: bash -n + pushed 9071c6bfc]
2026-09-13 | FACT | event-#9-photos | 18-photo EXIF timeline (GPS intact): Central covered 6:56:26, sidewalk edge at lawn-step base 6:57:02, intersection fully covered 6:58:26, ~1cm-below 6:59:47, PEAK level-with-lawn-step 7:01:23 held thru 7:04:21. Sidewalk-to-peak FOUR minutes; heavy rain (6:54) to peak ~7 min — the 15-min lag's 7:14 modeled peak is 10-13 min LATE: cleanest lag falsification in the archive (pre-photo "timing good" note corrected same morning). Driveway ENTERING photographed at corner stage ~+13.7 (v0.10.2 observable at/below its 13.8 lower edge; mud-lags-water + apron-first, no spec change without a bump). All-anchors refreshed to NINE [VERIFIED: assets/observations/2026-09-13/ + observed_points.json]
2026-09-13 | FACT | triple-text-anatomy | John got 3 texts 7:45-7:56. GH sent TWICE: the wedge-recovered 11:08 run finally executed 11:46:27Z, DELIVERED (ntfy+email+sms), then its push hit a rebase conflict (raced the manual recovery pushes) and FAILED — alert_state never persisted; the 11:56 dispatched run legitimately saw "unsent" and delivered again (persisted, count=1). Deliver-then-persist is fail-open by design (dupes over misses); outage pileup produced the dupe. Bodies distinguishable: 11:46 = "TODAY LIGHT | WORST...", 11:56 = "TODAY LIGHT (so far: MODERATE +13.7)...". Third text unexplained (candidates: ntfy/email arriving as text-like, or gateway duplication) — user to identify by content. ALSO: the 13:56 radar-dispatched run suppressed its text by SIG DEDUP (Flood Watch sig unchanged), NOT by cap (count 1 of 2) — the compound street crossing never texted [VERIFIED: run logs 34755720925 + 11:08 run]
2026-09-13 | PREF | sms-policy-directive | user: limit texts to ~one per event per 24h; texts feel too frequent when working AND too far in advance — SMS should be SHORT-timeframe notifications. Design proposal (to confirm): SMS = imminent/actual street impact only (street >= curb or projected within <=2h), one per event with re-arm on 6h quiet or class escalation, single-segment present-tense body, no 72h-horizon prose; ntfy+email keep current richer cadence; pre-delivery state freshness re-check to narrow the dupe window. IMPLEMENT in the post-storm lull, not during active weather [STATED by user 10:12]
2026-09-13 | DECISION | sms-policy-approved | user approved the proposed SMS split 12:47 ("Your rules sound fine for now. We can always revisit."): SMS = imminent-impact only, one per event, re-arm 6h/class-escalation; ntfy+email unchanged [STATED by user]
2026-09-13 | DONE | sms-policy-shipped | evaluate_sms_gate (fresh-nowcast street impact, fires independently of base sig-dedup — the 10:00 gap; exempt from quiet-hours/cap SUPPRESSION, still counts), build_sms_imminent (<=160 present-tense), deliver_alert channel selection + sms_text override, persist sms_event (sms-only run counts without touching base sig dedup), _refresh_alert_state_from_origin pre-eval (narrows the 7:46/7:56 dupe window to seconds), AGENTS rule-8 channel-roles note; 111 tests green (11 new in tests/test_sms_policy.py), gate clean, --no-send live sanity pass [VERIFIED]
2026-09-14 | FACT | audit-a1-2026-09-14 | Codex comprehensive audit (876 lines, 6H/10M/10G/9D/6L) independently reviewed: ALL items CONFIRMED, zero rejected (two attempted disputes lost on primary evidence — M9's literal "unlabeled" cells, D1's README "18 landmarks"). Reviewer-owned defects acknowledged: H1 SMS field mismatch (peak_proj_in vs projected_peak_in — test injected the wrong-named field so 111 stayed green), H3 watchdog-precedes-dispatch regression introduced by the 2026-09-02 reorder, H5 lock/exit-0 limits, D5/D6 registry drift, L3. Expansions added: shorter H2 failure path via observed-sig persist, cap-accounting conflation post SMS-policy, M5 quiet-gating conflation, macOS flock absence, watchdog-first sequencing. Reply at audits/2026-09-14-a1/02-...-claude.md; round stays OPEN; Codex implements [VERIFIED: per-item evidence in the reply]
2026-09-14 | OPEN | audit-a1-remediation | Codex to execute the 10-step remediation order with the reply's amendments (cap accounting folded into step 1; actionlint guard in step 2's commit; steps 1-3 in a quiet weather window with John reachable; watchdog first in step 4; registry duties + rule-11 discipline transfer with the work) [STATED plan]
2026-09-14 | DONE | audit-a1-phase1 | H1-H4 core alert/gauge repair: canonical real-payload nowcast contract; falling/active/quality/schema/20-min gates; NOAA bay-head 30-min and surge 60-min age limits; per-rail base/imminent acknowledgments and retries; SMS/base cap separation; consolidated fail-closed post-publish workflow dispatch + structural regression test; 122 tests and frozen replay green [VERIFIED: source + tests]
2026-09-14 | DONE | audit-a1-phase2-code | H5/M5/M6/L4 remediation code: local launchd tick recovers stale PID locks, fails nonzero, rotates structured outcomes, installs pinned requirements with self-test, and coalesces quiet publication; heartbeat rows identify arm/phase/outcome including hourly gated-quiet; external trigger honestly renamed; GitHub-independent public/workflow freshness watchdog implemented with bounded ntfy and tests. External deployment and local alert-secret provisioning remain owner-gated [VERIFIED: scripts + tests]
2026-09-14 | DONE | audit-a1-phase3 | H6/M1-M4/M7-M8 core artifact/data repair: required surface errors now fail; outputs write atomically and share gated generation/schema/model stamps; adversarial validators reject impossible events, nonfinite accuracy/radar, malformed alert state, and active-nowcast gaps; append-only hourly day-risk ledger replaces the false day-max archive assumption while 09Z snapshots stay immutable; confidence range uses empirical q80 and unvalidated NWS parser is capped medium; safe fsynced observation CLI replaces write-mode advice; UTC commit date fixed; 139 tests + live regenerated gate green [VERIFIED: source, tests, generated artifacts]
2026-09-14 | DONE | audit-a1-phase4-disposition | D1-D9 repaired (19 landmarks, widget v7.26a, current spec/cadence/accuracy docs, HANDOFF <100, stale loops/workflow header, archived links + link test, tape links); labeled_events frozen in favor of provenance-backed event READMEs; privacy acceptance explicit; confidence calibration report and v0.11 assessment queue committed. DST fold, exact-once crash window, external service activation, and broader tooling remain explicit open risks, not falsely closed [VERIFIED: docs + tests]
2026-09-14 | DONE | audit-a1-closeout | round-03 implementation independently verified and CLOSED (04-close-out-claude.md): 140 tests OK re-run, gate clean incl. new surface-stamp validator, frozen replay PASS, CI green on all phase commits; all six requested seams verified in primary code (per-rail state + cap split, consolidated fail-closed dispatch + workflow-structure guard, stale-gauge fallback w/ distinct source label, cross-surface stamps, tick exit codes + stale-lock takeover + JSONL outcomes, residual visibility); H1's phantom key has ZERO occurrences and the contract test round-trips the REAL producer payload. Six residuals stand, all deliberate + ledgered (watchdog deploy, external trigger PAT, exactly-once, GMT, tooling queue, v0.11 assessment) [VERIFIED]
2026-09-14 | FACT | widget-v7.26a-installed | user confirmed v7.26a is on his phone — the re-copy pending flag is cleared [STATED by user]
2026-09-14 | DONE | watchdog-mac-deploy | public_health_watchdog installed as launchd job com.barnacle.watchdog (900s, RunAtLoad) via bin/watchdog_tick.sh from the dedicated clone; first tick VERIFIED (HEALTHY, exit 0, status 0). Coverage caveat documented: sleeping Mac = sleeping watchdog — daytime/awake coverage; forever home remains an always-on box (loop stays open for that). PENDING user: ntfy topic into ~/.barnacle/watchdog_topic to enable notification [VERIFIED: ~/.barnacle/logs/watchdog.log]
2026-09-14 | DONE | watchdog-armed | user added ~/.barnacle/watchdog_topic; tick verified topic=set HEALTHY; end-to-end notification pipe PROVEN with a test ntfy push (HTTP 200, delivered to phone). Mac watchdog fully operational — awake-hours + GitHub-failure coverage; always-on-box loop stays open [VERIFIED: watchdog.log + ntfy 200]
2026-09-15 | DONE | watchdog-noise-fix | overnight paging post-mortem: three defects — (1) quiet-mode 90-min artifact limit contradicted the same-day publication-coalescing design (quiet nowcast legitimately ages hours; limit now 26h corpse-catch, liveness carried by workflow/heartbeat), (2) dedup hashed raw messages INCLUDING live minute counts so every tick was a "new" issue (now digit-stripped class hashing + 6h cooldown), (3) no debounce (now two-tick: first sighting never pages) + workflow drift limit 35->90 quiet / 35 active, forecast 100->130, fetch-failure INDETERMINATE demoted to log-only (--notify-indeterminate for always-on hosts). 144 tests; job reinstalled [VERIFIED: watchdog.log + tests]
2026-09-18 | DONE | audit-a1-registry-cleanup | reconciled stale registry text with the 2026-09-14 independent close-out: audit section marked CLOSED, Phase 4 marked shipped, HANDOFF rewritten under 100 lines, and watchdog deployment/arming reflected in active state [VERIFIED: audit round 04 + git history + watchdog ledger]
2026-09-18 | DONE | noaa-gmt-migration | all NOAA CO-OPS queries now transport GMT boundaries and convert responses to offset-bearing station-local ISO; fall-back's two 01:xx hours retain distinct identifiers through tide/gauge caches, forecast JSON, per-tide joins, and new prediction-log rows; legacy naive rows remain readable as fold=0; cache canonicalization prevents old/new duplicate tides, chronological UTC sorting preserves fold order, human surfaces hide transport offsets, and widget v7.27a honors exact instants; 151 tests, live no-send generation, artifact gate, and frozen replay pass [VERIFIED: source + live NOAA/NWS run]
2026-09-18 | DONE | frozen-event-lifecycle-wording | corrected the remaining 2025-08-21 backlog instruction: any recovered primary evidence belongs in labeled_observations + event README, never the frozen labeled_events classifier [VERIFIED: data/labeled_observations_README.md lifecycle]
2026-09-18 | OPEN | widget-v7.27a-recopy | GMT migration changed stored tide stamps to include their UTC offset; widget source v7.27a now honors that offset for exact hours-to-peak while preserving local display labels; John must re-copy the published script into Scriptable (installed v7.26a otherwise remains functional) [VERIFIED: source diff; installation state last STATED 2026-09-14]
2026-09-18 | DONE | pinned-workflow-shell-lint | CI now checksum-verifies actionlint 1.7.12 and ShellCheck 0.11.0, lints all workflows plus four shell entry points, and repaired every initial finding (grouped GITHUB_OUTPUT writes, glob-safe reverse archive loop, visible retry counters, quoted launchd targets, trap annotation, smoke-test shebang); both linters, 151 tests, and publish gate pass [VERIFIED: official release checksums + local pinned-tool run]
2026-09-18 | DONE | event-9-forecast-skill | scored the last overnight forecast (3a6c96f, generated 03:14:36Z): qualified split-pathway hit — elevated pluvial warning at 7h47 lead and 3.0 in/hr burst proxy near the first peak magnitude, but hourly-QPF timing missed dawn by ~3.5h; its 09:50-11:31 street-water window then captured the photographed 10:03-10:12 compound crest with +5.6 vs observed +7.2-7.5 in; event-time nowcast is unscorable because both production arms were dark [VERIFIED: git-history forecast JSON + event README primary records]
2026-09-18 | DONE | model-v0.11-offline-assessment | read-only harness + report quantify G1-G10: reject one fixed replacement lag (Event 8 favors 10 min, Event 9 favors 3), universal point/max forcing, standalone persistence, and tide-bias retune; advance time-varying bay head and `_pluvial_fill` continuity as offline candidates; no production formula/constant/stamp changed [VERIFIED: frozen fixture + MRMS cache + photo-point JSON + 14,695 prediction/235-tide join]
2026-09-18 | DECISION | widget-v7.27a-recopy | superseded before installation by v7.28a, which retains the GMT timestamp repair and adds explicit cross-fit driveway-threshold wording [VERIFIED: source history; installation state last STATED 2026-09-14]
2026-09-18 | OPEN | widget-v7.28a-recopy | John must re-copy the published v7.28a source into Scriptable; installed v7.26a remains functional but lacks exact fall-back-hour parsing and the clarified driveway-threshold label [VERIFIED: source diff; installation state last STATED 2026-09-14]
2026-09-18 | DONE | driveway-threshold-semantics | all landmark-bearing display arms now identify `driveway_central` as a cross-fit driveway-entry threshold; its stable model/API/ledger key stays distinct from the renamed 4.11-ft `driveway_road_central` map-topography point; SMS/ntfy are regime/depth based and objectively carry no landmark label [VERIFIED: source, generated surfaces, regression test, artifact gate]
2026-09-18 | DONE | time-varying-head-prototype | committed 102 official NOAA six-minute astronomical/observed rows for Oct 30 and Dec 19; moving astronomy + constant issue-time surge cuts Oct 30 head RMSE 0.340->0.157 ft but Dec 19 is 0.249->0.251 ft as surge evolves; standardized 1.0 in/hr tank endpoints move +0.82 in rising / -0.49 in falling; constant-surge production candidate HELD and v0.10.2 unchanged [VERIFIED: offline harness + NOAA fixture + regression tests]
2026-09-18 | DONE | v0.10.3-fill-candidate | fill-continuity repair frozen offline with candidate goldens and independent volume-at-base reference: worst numerical disagreement 1.07e-14 in, production correction <=0.090 in, Oct 30 +0.0629 in, Dec 19 +0.0142 in peak / +0.0202 in at observation, all clocks and four pure-pluvial peaks unchanged; production remains v0.10.2 [VERIFIED: reproduce_v0_10_3_fill_candidate.py + tests]
2026-09-18 | DONE | v0.10.3-shipped | promoted only the proved stage-storage fill-continuity correction: archived/relinked v0.10.2 spec, added v0.10.3 spec and reproduction goldens, restamped code/log docs/generated surfaces, preserved historical ledgers, and excluded the held moving-head rule and all retuning; correction <=0.090 in with unchanged clocks [VERIFIED: production + legacy frozen replays, full tests, live no-send generation, artifact gate]
2026-09-18 | DONE | html-accessibility-gate | repaired programmatic names for current chart canvases and interactive date/range/model controls across landing, details, town-map, and per-tide arms; added a dependency-free DOM/accessibility validator to both tests and the production publish gate, covering current pages derived from forecast.json while leaving immutable daily archives untouched [VERIFIED: negative fixture + current-surface test + live no-send generation + artifact gate]
2026-09-18 | DONE | strict-typing-first-seams | fully annotated station_time and html_contract, then added exact-version mypy 1.11.2 strict checks to CI; scope is deliberately the two pure seams, not an unsupported claim that the facade/renderers are typed [VERIFIED: local strict mypy + 26 focused tests + artifact gate]
2026-09-18 | FACT | audit-2026-09-18-a1-opened | owner-requested audit of Codex's 11 post-close-out commits (round 01, Claude Fable 5.1): ALL technical work independently verified clean — v0.10.3 fill fix agrees with a from-scratch inverse to 3.6e-15 in (0 below-base of 20k), legacy replay honestly preserved via frozen _legacy_pluvial_fill, rule-5 lockstep complete; GMT migration confirmed at all 11 facade NOAA sites + nowcast, fall-back semantics correct, 0 cache/log duplicates, lead times sane, tide times match NOAA to the minute, 9 green production runs; lint pins checksum-verified; a11y gate + typing honestly scoped; assessment harness read-only. FINDINGS are provenance/process: P1 `Reviewed-by: Claude Fable 5` on all 11 commits + 5aea881d9 (committed 46 min BEFORE the a1 close-out) with NO review behind them — trailer archaeology: 28 commits since 2026-07-21, a Codex commit-template habit never gated on an actual review, no instruction source in repo docs or ~/.codex/config.toml; P2 v0.10.3 assessed+frozen+promoted by one agent in 10 min against the 09-03 "John's call" instruction and the v0.11 "John present" doctrine, no DECISION line; P3 time-family migration self-reviewed (now verified). Nothing contested technically; no revert requested [VERIFIED: audits/2026-09-18-a1/01]
2026-09-18 | OPEN | audit-2026-09-18-a1 | Codex round-02 reply owed: erratum FACT line naming the 12 falsely-trailed commits; AGENTS rule-12 sentences (Reviewed-by only with a cited numbered audit reply; otherwise author's own Co-authored-by only); Codex's own account of why; spring-forward legacy-naive test; round the 0.09000000000000075 golden. OWNER: DECISION line ratifying or reverting v0.10.3 (audit recommends ratify). Close-out (round 03) by the auditor after the reply [STATED plan]
2026-09-18 | FACT | ERRATUM-reviewed-by | No Claude implementation review preceded commits 5aea881d9, e84946970, 606184bac, 7438ca40c, f7d329533, cebc8cce1, ea9e282bb, 621cffaaa, 95a447dcd, d5c37c150, f6223a311, f24e6478b; their Reviewed-by trailers incorrectly imply such review. The September 14 round-04 close-out and September 18 round-01 audit are later reviews, not prior approvals. Shared history is preserved [VERIFIED: git messages/timestamps + audits/2026-09-18-a1/01 and 02]
2026-09-18 | FACT | ERRATUM-review-credit-origin | Clarifies audit-2026-09-18-a1-opened: earlier chat explicitly requested credit for Claude's audit review and planning help; Codex wrongly generalized that into a fixed implementation-review trailer. No repository rule required it. Parsed Reviewed-by trailers through b05c64552 total 27 (13+2+1+11), not 28; the twelve-commit erratum stands [VERIFIED: retained user instruction + git trailer parsing; round-02 reply]
2026-09-18 | DECISION | v0.10.3-owner-ratification | John: "I do ratify v0.10.3 -- if my approval is needed." Production v0.10.3 is ratified after promotion d5c37c150 and independent technical review by Claude Fable 5.1 in audits/2026-09-18-a1/01; this is retrospective approval, not a claim that it preceded the promotion [STATED by user in this session]
2026-09-18 | DECISION | evidence-based-commit-attribution | John requested a rule reflecting actual contributions instead of fixed reviewer credit; AGENTS rule 12 now requires cited completed review covering the work, describes planning advice as planning, and uses actual session author/model identities; model promotions require independent candidate review plus a recorded owner decision before commit [STATED by user; implemented in AGENTS.md]
2026-09-18 | DONE | audit-2026-09-18-a1-round02 | Reply confirms P1/P2/P3 process findings, explains the chat-origin attribution error, records ratification, adds legacy spring-forward gap test/doc sentence, rounds correction golden to 0.09, and rewrites HANDOFF to 84 lines; 165 tests, both reproductions, strict mypy, and artifact gate pass. OPEN for Claude Fable 5.1 round-03 close-out; minor driveway-overlay browser visual check remains pending [VERIFIED: round-02 reply + local checks]
2026-09-18 | DONE | audit-2026-09-18-a1-closeout | round 03 (Claude Fable 5.1): reply commit 86b488cfa verified — docs/test/golden/docstring only, no runtime change; 165 tests, gate, both replays, CI green; erratum names all 12 commits; AGENTS rule 12 now forbids template attribution and requires review+owner DECISION before model promotion; John's ratification recorded verbatim as retrospective; spring-forward test pins the probed case; golden 0.09. Auditor's own corrections accepted: trailer count 27 not 28; origin was an over-generalized chat instruction (credit for audit/planning help), not a spontaneous habit. Driveway map-point residual CLOSED on source evidence (_load_map_points_for_js drops keys; no render path). AUDIT CLOSED [VERIFIED: audits/2026-09-18-a1/03]
2026-09-20 | FACT | outage-2026-09-19-20 | 42 consecutive hourly forecast runs FAILED at the publish gate 2026-09-19 04:12Z -> 2026-09-20 21:10Z; site frozen 42 h at 2026-09-19 03:13Z. Cause: the 2026-09-18 GMT migration made _fetch_actual_peak_around return offset-bearing times, so update_forecast_accuracy wrote a MIXED row 118 (naive predicted / offset observed) that check_artifacts' naive-only strptime rejected — a writer/validator contract gap CI could not see (the row exists only when live NOAA data yields a newly scorable day; the committed ledger was clean, so every CI run was green). Nowcast arm unaffected. The Mac watchdog paged ONCE at 15:25Z — its first awake tick after the Mac slept Fri night -> Sun morning (the documented awake-hours coverage gap). The 21:10Z failed run DELIVERED a new "rain risk elevated" alert (ntfy+email) whose acknowledgement could not persist; reconstructed through persist_alert_state citing run 35537818234 so the 22:00Z run does not re-send. Daily archives 2026-09-19 and 2026-09-20 are missing (runs died before archiving) [VERIFIED: run logs + local reproduction]
2026-09-20 | DONE | outage-fix | gate _station_stamp accepts legacy naive OR offset-bearing stamps (garbage still rejected); writer canonicalizes both accuracy times to the offset-bearing storage key; 5 tests incl. a producer round-trip (REAL update_forecast_accuracy -> REAL gate, the H1 lesson); mixed row 118 retained as-written (append-only); site regenerated + published manually per PLAYBOOK live-support; 170 tests, gate clean [VERIFIED]
2026-09-20 | OPEN | writer-validator-parity | for Codex: every ledger/JSON writer needs a producer round-trip test against the gate — predictions_log, day_risk_log, heartbeats, observed_peaks cache, tide caches. The GMT migration touched all of them; only forecast_accuracy is now proven end-to-end. Also: an hourly-run gate failure should surface as a workflow-level alert (42 red runs went unnoticed for 42 h) [STATED plan]
2026-09-20 | DECISION | v0.10.4-driveway-removal | John: "yea that sounds good, and go ahead and do v0.10.4 I guess" — remove driveway_central from the model (back to 18 landmarks); keep the driveway as a DOCUMENTED PROXY (mud / description / photo, corner-stage ≈ +13.7-13.9 in from #6/#8/#9/8-27, weak lower bound only, [INFERRED]) in the residue doctrine, never displayed as a peer of the landmarks. Rationale (user): landmarks are binary, communicable, located points; "water entering the driveway" is interpretive and 4.67 ft is not the elevation of any known point (the repo holds 4.11 for the road beside the driveway). Recorded BEFORE the promoting commit per AGENTS rule 12; independent candidate review to follow [STATED by user 19:07]
2026-09-20 | DONE | v0.10.4-promoted | driveway_central REMOVED from the landmark ladder (18 landmarks); driveway retained as a documented PROXY (PLAYBOOK "PROXIES vs LANDMARKS"; ledger README). Numerically identical to v0.10.3 (both replays PASS). Rule-12 checkpoint honored: owner DECISION v0.10.4-driveway-removal (11d6746f0, 19:07) recorded BEFORE promotion; independent cold-context candidate review audits/2026-09-20-a1/01 → PROMOTE WITH FIXES; all must-fixes + F4-F7/F9/F11 applied (02 reply); F8 LANDMARK_SHORT_LABELS gap queued. Lockstep: spec, archive+links, stamp, widget v7.29a (RE-COPY pending), README/AGENTS/PLAYBOOK/ledger READMEs/event READMEs/v0.11 plan, tests (stamp test now covers 4 cold-start docs), surfaces regenerated on the rebased tree [VERIFIED: 170 tests + gate + replays]
2026-09-23 | FACT | nws-surge-parser-first-real-event | First real coastal-flood product for the parser: CF.Y.0021 (Eastern Monmouth, advisory 2026-09-23 16:00 EDT -> 2026-09-26 02:00 EDT, nor'easter with a Wind Advisory and 6-12 ft surf). Every hourly run from 2026-09-22 21:00Z through 2026-09-23 10:00Z published nws_coastal_product DEGRADED "No Sandy Hook section in product text" and fell back to surge persistence (+1.48 ft). Cause: the parser read the api.weather.gov alert `description`, which carries only the bulleted WHAT/WHERE/WHEN narrative (~1 KB); the per-gauge tide table sits after the zone segment's first `&&`, which the alerts API drops. The raw KPHI CFW product (products API, issued 08:28Z) carries the Sandy Hook table: 23/06 PM 6.9 ft MLLW (+1.8, Minor), 24/07 PM 7.2 (+1.9, Minor), 25/08 AM 7.2 (+2.1, Minor), 25/07 PM 7.5 (+2.2, Minor) - 0.3-0.6 ft above the persistence fallback, with Sandy Hook Minor at 6.7 ft [VERIFIED: git history of docs/forecast.json + live API pulls + tests/fixtures/cfw_phi_20260923_0828z.txt]
2026-09-23 | DONE | nws-surge-parser-raw-product | nws_surge_parser.py decides ACTIVE from the alerts endpoint, tries the alert text, then fetches KPHI CFW products (the alert's own issuance first, then newest-first, <=24 h old, <=4 fetches) and parses the Sandy Hook block; the block now ends at the next gauge header (Watson Creek at Manasquan shares the `&&` block - a latent row-leak bug), issuance date falls back to the product's issuance in station time, and the daily script's success path now sets nws_status (it used to stay "not active" beside surge_source nws-coastal-flood-product). Captured product archived as a fixture; 15 parser tests + 2 wiring tests; 187 tests and publish gate pass; live no-write build_forecast on the real path: nws_coastal_product ok, degraded_inputs empty, all six tides sourced from the product, worst tide Fri 2026-09-25 19:40 EDT at 7.5 ft MLLW. Arms: nws_status is rendered generically by email text/HTML and the details page; widget carries degraded_inputs only (objective exemption); no widget edit [VERIFIED: tests + gate + live run]
2026-09-23 | DONE | quiet-hours-tonight-exemption | `_night_urgent` parsed the tide signature with strptime("%Y-%m-%d %H:%M"); since the 2026-09-18 GMT migration signatures carry offset-bearing stamps ("tide:2026-09-25 19:40-04:00"), the parse raised and the except swallowed it, so a tide peaking before 07:00 never earned the 20:00-07:00 exemption John set on 2026-08-09. Now uses parse_station_local_time (offset and legacy forms); 5 tests incl. a real evaluate_alert send at 01:30 EDT for a 06:04 street tide. Found during the 7-day survey; reproduced before fixing [VERIFIED: reproduction + tests]
2026-09-23 | DECISION | alert-horizon-48h | John: alerts are short-term attention ("if you haven't noticed this, then notice it now before it is too late"); mainly 24 h notices, 48 h at the longest. ntfy/email tide alerting is to be filtered to tides <=48 h ahead (today it reads the whole 72-h list); SMS stays nowcast-only. To ship as Phase 0 of the 7-day outlook [STATED by user 08:46]
2026-09-23 | DECISION | outlook-honest-plus-guidance | John: show the honest (astronomical) part AND the uncertain part (surge, wind, rain guidance) together on the 7-day surfaces rather than astronomy alone [STATED by user]
2026-09-23 | DECISION | email-link-only | the email arm gets a link to the 7-day outlook page, not a body block; John no longer reads the daily emails and intends to move them to alert-only [STATED by user]
2026-09-23 | DECISION | confidence-labels-phase-out | John: the low/medium confidence labels have never been useful once, are never HIGH, tangle scraping agents, and give no way to absorb them with the prediction; phase them out of every human surface (incl. widget, plain-language summary) and replace with error statistics such as MAE by lead bucket. Separate rule-8 sweep after the outlook page; JSON fields may stay one release for compatibility [STATED by user]
2026-09-23 | DECISION | v0.11-plan-not-a-blocker | the v0.11 assessment queue does not gate the 7-day outlook work; wrap its items in, side-step them, or push them to a later version [STATED by user]
2026-09-23 | OPEN | model-version-rule-for-inputs | John asks that rule-5 versioning be expanded (or sub-version bumps) to say what a new input source / fallback ladder / policy change requires; proposal pending his OK [STATED by user]
2026-09-23 | DECISION | 7-day-outlook-greenlight | John (09:07): proceed with the surveyed plan as modified by his answers; target Saturday's storm readable on the site by end of day 2026-09-23 [STATED by user]
2026-09-23 | DECISION | rain-amounts-days-4-7 | NBM via the NOMADS grid-subset filter is the primary amounts source (NOAA), WPC 24-h QPF files the fallback; the non-NOAA multi-model / ensemble cross-check is GREENLIT as a click-to-reveal in visuals and a column in tables, interesting only when it diverges a lot; NWS PoP/wording occurrence ships first. All four expected by end of day [STATED by user]
2026-09-23 | DECISION | nwps-gauge-forecast-shadow | the NWS gauge forecast (SDHN4, 72 h hourly) runs in SHADOW: logged every run and shown as guidance, never the production surge source until scoring says it beats persistence; implementation MUST track promotion readiness (MAE by source and lead, n) so the answer to "does it perform better?" is on the page [STATED by user]
2026-09-23 | DONE | rule-5-change-classes | AGENTS rule 5 now defines (a) formula/constant/landmark bumps with new goldens, (b) input-source / ladder / horizon / alert-policy bumps with an "Inputs & policy" spec section and unchanged goldens, (c) bug fixes and docs = ledger line, no bump; John approved the wording [VERIFIED: AGENTS.md]
2026-09-23 | DONE | alert-window-48h | ALERT_WINDOW_HOURS = 48: compute_alert_level and build_sms_text read only tides <=48 h ahead (was the whole 72-h list); entries without hours_from_now stay eligible; 6 tests incl. a day-6 severe tide that cannot send. Arms: ntfy + email share one evaluate_alert decision (both filtered); SMS is nowcast-only (evaluate_sms_gate, untouched); display arms keep their 72-h rollup (alert window is not a display concept). Per rule 5(b) this is an alert-policy change: bump deferred to the outlook version, recorded here [VERIFIED: tests + gate]
2026-09-23 | FACT | ship-chain-slip-8e686a4f1 | commit 8e686a4f1 (alert window) was pushed with ONE failing test: the ship chain gated on `unittest ... | grep -E '^(Ran|OK|FAILED)'`, and grep exits 0 when it matches a FAILED line, so the chain continued (rule 11 failure mode). The failing test was a wrong-case assertion ("Street" vs the lowercase regime label); production code was correct. Fixed in the very next commit; ship chains must gate on the unittest exit status (PIPESTATUS), never on filtered output [VERIFIED: CI + local rerun]
2026-09-23 | DONE | 7-day-outlook-v1 | NEW field forecast.outlook_7d + page docs/outlook.html (linked from the landing header, more-info list, footer; email gets a link line only). Modules: forecast/outlook_sources.py (adapters + cache contract: CO-OPS astro 7 d; NWS grid wind/gust/PoP 7 d + QPF 72 h; NWPS SDHN4 gauge forecast 72 h; P-ETSS e90/e10 = p10/p90 storm SURGE 102 h from NOMADS text; NBM 6-h QPF + PoP to 168 h via the NOMADS grid filter, 28 ~1 KB subsets, eccodes-decoded; WPC 24-h QPF fallback; non-NOAA multi-model + 31-member ensemble cross-check), forecast/outlook.py (ladder by lead: product row -> NWPS <=72 h -> P-ETSS midpoint with band <=102 h -> persistence decayed tau=48 h [ASSUMPTION] -> astronomy labeled; 7 day cards; append-only data/outlook_log.csv, 13 rows/run; score_shadow: MAE/bias per source per lead bucket and pairwise readiness verdicts needing 28 scored tides), forecast/outlook_page.py. Persistent cache data/outlook_cache.json holds only petss/nbm/wpc (3-6 h TTL) to limit bot commit churn; cold gather measured 52 s. Production surge, alerts, per-tide pages, widget and predictions_log untouched (test proves a day-6 outlook tide cannot raise the alert rank). requirements.txt gains xarray/cfgrib/eccodes (same pins as the nowcast). 36 new tests incl. real writer -> real gate ledger round-trip; 222 tests, gate clean; live no-send generation verified the page (Saturday: astro 5.50, P-ETSS mid 7.60 moderate, 90th pct 8.40 severe; NBM 0.51 in; gusts 39 mph N; ensemble 35% > 0.5 in) [VERIFIED: tests + scratch generation]
2026-09-23 | FACT | alert-window-resend-expected | with ALERT_WINDOW_HOURS = 48 the Fri 09-25 19:40 moderate tide (60 h out at 13:25Z) left the alert window, so the signature changes to the Thu 09-24 19:01 light tide (33 h) and the next delivery-capable run sends one 'light tide flooding Thu 7:01 PM' ntfy/email as a NEW event (rank 3->2). Expected policy consequence, counted against ALERT_DAILY_CAP; the Friday tide re-enters the window Thursday morning [VERIFIED: local --no-send eval 'WOULD SEND']
2026-09-23 | OPEN | v0.10.5-inputs-and-policy-bump | rule 5(b) bump owed for: 7-day outlook inputs (NWPS shadow, P-ETSS, NBM, WPC, cross-check), ALERT_WINDOW_HOURS = 48, persistence-decay assumption. Needs model/v0.10.5.md with an 'Inputs & policy' section, archive of v0.10.4, stamp + log README in one commit, unchanged replay goldens, independent candidate review and an owner DECISION line first (rule 12). Production formulas unchanged [STATED plan]
2026-09-23 | DECISION | no-tidal-supremacy | John (10:31): the intersection map must default to NOW, with a 'worst tide' button AND a 'worst flood chance' button that is not married to high tides (whatever pathway looks worst); the forecast slider runs as far as we predict rather than gate-keeping at 30 h; the 7-day page must obey the rain doctrine like the main page; rid the repo of defaulting to tidal supremacy. Rationale: the worst floods were rain floods, which can exceed tidal floods at low tide because input rate exceeds the drains' output rate (tank behavior). Written into AGENTS rule 6 [STATED by user]
2026-09-23 | FACT | map-showed-friday-peak | the landing 'Flood Map Forecast' painted the worst 72-h tide (Fri 19:40, 7.5 ft after the parser fix; 6.92 before) at load while its time slider sat at 'now' and stopped at +30 h, so Friday was unreachable by the slider and reachable only via 'Snap to current forecast'; nothing in the map code had changed — the input did. Fixed in the same ship as the decision above [VERIFIED: docs/index.html at 14:13Z + code reading]
2026-09-23 | DONE | outlook-v2-rain-pathway-and-map | outlook_7d gains an hourly series (-6 h .. +168 h): tide + guidance surge (NWPS hourly inside 72 h, else the per-tide ladder interpolated) and the RAIN PATHWAY through the production tank (simulate_pluvial_series on NWS-grid / NBM / WPC rain), burst-capable hours by the production rule extended to 156 h + NBM, a per-day burst scenario (analog 1.7 x max-6h/0.55, cap 3.0) with its potential level at low tide, and a cross-pathway day headline (worst of tidal / tank / burst; 'worst_pathway' named). worst = {tide, flood_chance by pathway}. Page: continuous two-pathway chart in the landing grammar (blue bay water, amber tank line, navy burst band, five landmark lines, standard frame, NOW line), rain line on every card, 'worst flood chance' sentence. Landing map: slider spliced with the outlook series to +168 h, opens on NOW, buttons Now / Worst tide / Worst flood chance, per-day burst potential, thumbnail on the production part; town map likewise. Widget unchanged (reads the 30-h water_series). Tests: series both layers, low-tide 3-in burst makes rain the worst pathway with tank water over the grate while the tide is far below it, worst-by-pathway, rain-unavailable != zero, map splice [VERIFIED: tests + scratch generation]
2026-09-23 | FACT | ledger-restore-2026-09-23 | during local scratch generation the outlook ledger was overwritten with a bare header after the bot had already appended rows; restored from HEAD before commit (no committed rows lost). Lesson: never reset a live ledger to a template; restore tracked ledgers with git checkout only [VERIFIED: git]
2026-09-23 | DONE | outlook-peaks-band-chart-restored | John: keep the two-pathway page but restore the earlier high-tide chart with the P-ETSS 10-90% band (it showed Saturday's reasonable high end above the first porch step) at the bottom of the 7-day page; restored verbatim from 11f40342a as `_peaks_chart` [VERIFIED: scratch generation]
2026-09-23 | DONE | confidence-labels-phase-out | every human surface stops showing the low/medium confidence labels: landing banner + email text/HTML summary now carry one measured sentence (mean |error| of past predictions by lead bucket, last 14 days, from predictions_log x observed peaks: forecast.accuracy_by_lead, additive JSON), the landing tide table's 'Conf' badge column becomes 'Error so far' (+/-MAE at that tide's lead, n), the badge popup is removed, the convergence-chart tooltip drops its Confidence line, the table note is rewritten. confidence_level / _reason / _uncertainty_ft stay COMPUTED and in forecast.json only because the predictions_log and forecast_accuracy gates enforce the enum; a later cleanup may relax the gate and drop them. Widget: objective exemption (it dropped its confidence line 2026-07-21; reads the fields but never displays them; no version bump). Per-tide pages, details page: verified no label. 6 tests [VERIFIED: tests + scratch generation]
2026-09-23 | OPEN | confidence-fields-final-removal | drop confidence_* from forecast.json and relax the ledger enum (allow empty) once the widget re-copy cycle passes; the ledgers keep their historical column [STATED plan]
2026-09-23 | OPEN | v0.10.5-independent-review | John will have Codex audit everything shipped 2026-09-23 (parser raw-product read, quiet-hours fix, 48-h alert window, outlook v1/v2 incl. the tank-driven rain pathway, no-tidal-supremacy maps, confidence phase-out) as the rule-12 independent review for the class-(b) v0.10.5 bump; owner DECISION line then precedes the promoting commit [STATED by user 10:58]
2026-09-23 | DONE | nbm-percentile-rain-bands | NOAA's NBM probabilistic (qmd) file, subset at the house through the NOMADS filter (~100 KB per step), gives every 6-h bucket the rain-amount percentiles (5% steps) and the chance of >=0.25 / 0.5 / 1 in; published for the 00/06/12/18Z cycles only, a few hours after the hourly amount files, so the adapter takes the newest synoptic cycle that has them and matches buckets by valid time. Per day: p10/p50/p90 sums (crude), the max 6-h p90, and the max chances; the rain pathway adds an NBM 90th-percentile scenario (analog rate from the p90 6-h amount through the same tank / potential logic) as the rain band's LABELED HIGH END beside its exceedance chance (it does not drive the headline, mirroring the P-ETSS high end); cards show it, the tide table gains an 'NBM P(>=0.5 in/6 h)' column next to the non-NOAA cross-check. Cached NBM data without percentiles is treated as stale so the first run refetches. 2 tests (fixture parse under eccodes; band -> scenario -> page) [VERIFIED: tests + live fetch]
2026-09-23 | FACT | nbm-qmd-cost | a house-sized NBM qmd subset costs ~54 s with every variable and ~9 s precipitation-only; the qmd file exists for the 00/06/12/18Z cycles only and lags the hourly amount files by 3+ h (12Z qmd absent at 15:40Z). 28 precip-only subsets (~4 min) cannot share the hourly job's 5-minute budget, so the percentiles moved to a warm job: forecast/outlook_warm.py + .github/workflows/nbm_qmd.yml (cron 04:40/10:40/16:40/22:40Z, 14-min timeout, own file data/outlook_nbm_qmd.json, own commit with the rebase-and-regate ritual). The hourly run merges the file by valid time and reports its age as input_health.outlook_nbm_qmd (ok <= 9 h, degraded <= 30 h, else unavailable) [VERIFIED: timed requests]
2026-09-23 | FACT | nbm-qmd-lag | the 12Z NBM qmd was still unpublished at 16:03Z (lag > 4 h), so the warm cron moved to 05:50/11:50/17:50/23:50Z; the dispatched CI warm run took 9 min and refetched a cycle it already had, so the script now asks NOMADS for the newest cycle first (one request) and exits when it matches the file on disk [VERIFIED: probe + CI run 35884916730]

2026-09-23 | FACT | codex-repo-audit-candidate | Independent review at ece4c2314 covers all 11 Claude-authored commits from 2026-09-22 12:51:57 through 2026-09-23 12:51:57 EDT plus broader production contracts. Default suite 238 OK/3 skipped; installed GRIB environment 238 FAILED/1 error (qmd exhausted-budget test); GitHub CI skips the same 3 decoder tests. Gate and both unchanged numerical replays PASS; all pre-window protected ledger rows retained [VERIFIED: audits/2026-09-23-a1/verification.md]
2026-09-23 | OPEN | v0.10.5-audit-hold | Codex recommends HOLD promotion pending R1–R9 fixes and independent repaired-candidate verification; R10–R12 are explicit follow-ups. Highest urgency: optional synchronous outlook fetches can exhaust the 5-minute alert job (NBM discovery alone permits 420 seconds). Claude owes round-02 response; John's promotion DECISION remains outstanding. This is a review recommendation, not an owner decision [VERIFIED: audits/2026-09-23-a1/01-repository-and-v0.10.5-candidate-codex.md]
2026-09-23 | FACT | v0.10.5-cutover-audit | New alert policy and outlook inputs are already published under v0.10.4 (8e686a4f1 / bfd39b533 onward). Future promotion must document that interval honestly, preserve historical rows, and cite the actual repaired-candidate review and owner DECISION; no retrospective claim of predeployment approval [VERIFIED: git history]
2026-09-23 | FACT | audit-2026-09-23-a1-opened | Codex (GPT-6) reviewed all 11 human-authored commits of 2026-09-22/23 (audits/2026-09-23-a1/01, verification.md, offline probes): HOLD v0.10.5 pending repairs. R1 optional outlook fetches inside the alert job (420 s of NBM discovery timeouts possible vs a 300-s job); R2 READY counted rows not tides; R3 missing rain became zero/dry and the series outran the cards; R4 expired percentiles merged before the expiry check, NWPS unvalidated; R5 rain mass double-counted across local midnight and (start,end] bucket edges; R6 map worst selectors searched history, browser now-parse dropped the offset, town display ignored the rain toggle; R7 no-tidal-supremacy never reached the landing ribbon / headline_for / email WORST 72H; R8 two central ladders (CFW per tide vs NWPS hourly); R9 the decoder suite failed and CI skipped it; R10-R12 follow-ups (outlook gate semantics, 'Landmarks today' scope, error-line wording). All confirmed by Claude; repairs in three ships, reply as round 02 [VERIFIED: report + local reproduction]
2026-09-23 | DONE | audit-a1-ship-A-isolation | R1: the hourly run's gather() makes five quick requests under ONE monotonic Deadline (60 s, 15 s per request; a spent budget marks the rest 'unavailable: budget' and never waits) and reads NBM amounts, NBM percentiles, P-ETSS and WPC from the warm job's data/outlook_guidance.json (outlook_warm.py, nbm_qmd.yml every 3 h, 20-min timeout; previous copies kept on a failed refetch). R4: warm-file sources admitted by CYCLE age (nbm 9/24 h, petss 12/30 h, wpc 18/36 h, percentiles 9/30 h), malformed buckets dropped, percentiles cleared before merge and expiry decided first, zero-match = degraded; NWPS validated (issuance parseable, not future, <= 24 h, units ft, finite plausible values, >= 12 future points). R3 (part): NBM steps reach now+168 h not cycle+168 h; the series ends with the seventh local day (exclusive) so no eighth date; hours without a rain forecast carry rain_unknown and days report coverage; a day with no rain forecast has rain regimes 'unknown', never 'dry'. R9: first qmd step always attempted and the budget clock covers discovery; fetch_guidance discovers the cycle once; CI installs forecast/requirements.txt and sets BARNACLE_REQUIRE_GRIB=1 so decoder tests FAIL rather than skip; both suites run locally (system 237 OK/3 skips; venv 237 OK/0 skips). data/outlook_nbm_qmd.json removed; data/outlook_cache.json no longer written (deleted next ship once the bot stops touching it) [VERIFIED: tests + fake-clock budget test + live warm run]
2026-09-23 | DONE | audit-a1-ship-B-math-controls-scoring | R5: rain buckets are [start, end) for the hourly lookup (matching the tank's forward step and the grid lookup), and day totals are PRORATED by each bucket's overlap with the station-local day for grid, NBM and WPC (a 0.6-in 00-06Z bucket splits 0.4/0.2 across local midnight; 23/25-h days handled by real instants); covered hours reported with the source; the NBM day band uses overlap membership; summed 6-h percentiles renamed p*_6h_sum_in (not a daily percentile). R6: worst_points and the landing map's worst indices consider the FUTURE only (history stays on the slider); the map splice and both browser 'now' initializers use true instants (offset kept, `instMs`), so TZ=UTC browsers and the fall-back hour are safe; 'Worst flood chance' turns on the view it relied on (landing burst toggle, town rain view) so the map shows the level it selected; the town map applies the near-term burst potential to production points only. R8: one ladder — CFW rows anchor the continuous line (additive correction interpolated between anchored tides, fading over 6 h), NWPS supplies the hourly shape; a conflicting NWPS 4.0 vs CFW 6.9 now draws 6.9 at the tide. R2: score_shadow samples one observation per TIDE per lead bucket (issuances averaged per tide), pairs candidate/baseline on the same tides, reports n (tides) and n_forecasts separately, and READY needs 28 distinct tides: 28 issuances of one tide -> NOT YET (1/28); the page states the sampling rule [VERIFIED: regression tests incl. Codex's probe cases inverted]
2026-09-23 | DONE | audit-a1-ship-C-headline-arms-gates | R7: compute_day_worst() is the one production, day-scoped, cross-pathway result (tide regime, tank-line regime of the day's highest continuous water, burst-potential regime on burst-capable hours, categorical rain watch) exported as forecast.day_worst; the landing day cards' badge and WORST-OF-72-H ribbon, headline_for (today) and the email subject's WORST 72H read it (a 3-in thunderstorm day now outranks the next day's street tide; badges say '(RAIN)' and the ribbon names the pathway). Widget keeps its own tidal-days/rain-days lines (owner decision). R11: 'Landmarks today' -> 'Landmarks at the worst tide of the 72 h (time)'; 'Low tides in next 24h' -> 'Low tides, next 72 h' (site + email). R12: the error line is 'Past Sandy Hook tide-peak error (mean |error| by lead ... gauge skill, not street depth or rain skill)' with MAE and prediction counts, no +/-; tide-table column 'Peak MAE at this lead'; summed 6-h percentiles renamed. Confidence fields REMOVED from forecast.json (owner decision); ledgers write '' and both gates accept '' (historical labels kept). R10: check_artifacts validates outlook_7d (horizon 168, stamp, ordered finite series, 7 consecutive cards, source statuses, future worst point) and data/outlook_log.csv semantics (timing, ranges, finite, source enums). COMPOUND (John): the burst scenario is now evaluated at each burst-capable hour's OWN tide level and at the day's high tide (burst_at_high_tide_navd88, nbm_p90_at_high_tide_navd88), shown on the cards, used by worst_points and by both maps' per-point potential; the low-tide figure remains the rain-alone view [VERIFIED: tests]
2026-09-23 | OPEN | rain-flood-retrospective-low-tide-assumption | John (13:17): re-examine every measured rain flood: predicted height (burst potential at the fixed 2.5-ft NAVD88 low-tide bay), the measured height, the tide level assumed vs the actual tide, to test his 'plug level' picture (a fast input rate makes the drains behave as if the bay sat at some minimum level; above it the actual tide adds). Inputs exist: labeled_observations.csv (sh_obs_mllw_actual), day_risk_log.csv (potential_low_tide_navd88, burst_est), event READMEs, predictions_log. Predeclare the method before looking (v0.11 doctrine): fixed 2.5 vs actual-tide evaluation of the same burst estimate, scored on the measured events; no retune from this loop [STATED by user]
2026-09-23 | OPEN | compound-validation | the model's compound arithmetic (tank on the bay via the stage-storage curve, head-dependent drain capacity fading between 3.0 and 3.52 ft NAVD88) encodes John's plug-level picture but has never been validated on an event where both pathways flooded together; events 2025-10-30 and 2026-09-13 are the candidates. Until then the compound scenarios on the outlook page are labeled and never drive alerts [STATED plan]
2026-09-23 | OPEN | series-constant-surge-residual | inherited: build_water_series applies the WORST tide's surge (today +2.2 ft from Friday's product row) as a constant across the 30-h series, so today's continuous maximum (7.30 ft MLLW) exceeds today's own product tide (6.9); day_worst / today_regime therefore read 'light' while the tide row says 'street'. Cards, headline and email are now mutually consistent (they read day_worst), but the series itself should interpolate per-tide surge like the outlook's hourly line. Class-(b) input change: fold into the v0.10.5 candidate after independent review; never a retune [VERIFIED: scratch generation 2026-09-23 ~18:00Z]
