# BACKLOG — open loops + ledger

**OPEN LOOPS is authoritative for "what's unfinished."** When HANDOFF
looks stale, trust this file. Ledger lines are append-only:
`YYYY-MM-DD | TAG | topic | one line` with tags
`[DECISION] [FACT] [DONE] [OPEN] [BLOCKER] [PREF]` and confidence
`[VERIFIED]/[STATED]/[INFERRED]` where a claim isn't ledger-backed.

## OPEN LOOPS (force-ranked)

**Active / near-term**
- [ ] Re-copy widget source v7.27a into Scriptable. It preserves exact
      hours-to-peak across the fall-back repeated hour; v7.26a remains
      installed as of 2026-09-14 and otherwise renders current timestamps.
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
- [ ] Engineering breadth: checksum-pinned actionlint 1.7.12 and ShellCheck
      0.11.0 are now CI gates. Browser DOM/accessibility smoke tests and
      incremental static typing remain as module seams make them tractable.
      Contract tests cover the two audit regressions.
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
      validation — nws_surge_parser.py is live but has never seen a
      real coastal-flood product (all six measured events were rain).
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
- [ ] Versioned model candidate: `_pluvial_fill()` continuity repair is
      assessed (sampled maximum correction 0.090″; frozen peak changes
      0–0.063″; no clock changes). Include it only in a model-version bump
      with goldens updated in lockstep; do not patch v0.10.2 silently.
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
      2026-09-18: fixed-head + fill-continuity advance to candidate work;
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
