# BACKLOG — open loops + ledger

**OPEN LOOPS is authoritative for "what's unfinished."** When HANDOFF
looks stale, trust this file. Ledger lines are append-only:
`YYYY-MM-DD | TAG | topic | one line` with tags
`[DECISION] [FACT] [DONE] [OPEN] [BLOCKER] [PREF]` and confidence
`[VERIFIED]/[STATED]/[INFERRED]` where a claim isn't ledger-backed.

## OPEN LOOPS (force-ranked)

**Active / near-term**
- [ ] Nowcast scheduler: trigger TRIPPED by event #7 (18-min publish
      gap covered the entire rise). Half-A (launchd, Mac-awake hours)
      INSTALLED 2026-08-07 via bin/install_local_scheduler.sh;
      half-B (external cron, 24/7) ready-to-execute in
      history/plans/external-cron-scheduler.md — needs the user's
      ~10 min for a fine-grained PAT.
- [ ] Town map, staged features: bands/classic shading toggle;
      per-building doorsill tagging (user point-and-click, feeds
      freeboard); possible georeferenced user snapshot base layer.
- [ ] RAIN PONDING IN LOCAL MINIMA (user idea 2026-08-03): detect
      sag points along the street network from the LiDAR profile —
      vertices lower than both neighbors, scored by basin depth
      below the enclosing saddle — and badge them as rain-ponding
      candidates ("collects water in downpours") independent of the
      tidal surface. Type example: the Route 36 valley between two
      hills in Highlands that floods in rain despite high elevation.
      Geometry-only (no drainage physics claimed); the region street
      elevations shipped 2026-08-03 already contain the needed data.
- [ ] Antecedent wetting (model gap, user field insight 7/18): tank
      is memoryless about hillside priming; every double-pulse event
      is a calibration pair. Candidate: trailing-rain multiplier on
      K or two-layer soil reservoir. Related: duration-explicit
      V=C·(R−D)·T upgrade. Priming is ONE of SIX structural insights
      queued as the next model session's menu — see "Model
      consequences" in assets/observations/2026-07-18/README.md.
- [ ] Stateless-nowcast tank window: each run integrates from V=0
      over ~1 h of frames — understates once a burst ages out.
      Candidate: persist V with decay across runs. (Documented
      design; day-max memory partially compensates.)

**Parked (user-gated or seasonal)**
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
      August rental inspection — proto-mud-tracer): would add a row
      to data/labeled_events.csv. Low value; tide calibration no
      longer gates anything.
- [ ] Someday/speculative queue: attic archive §9 items 17–27 +
      §9e.4-adjacent (ETSS retry, NYHOPS, multi-town spin-offs,
      subscribe flow, iOS app stages, reanalysis, mesonet rain).
      Consciously move an item OUT of the attic to activate it.
- [ ] Datum line for widget + map-overlay chart (single chosen datum;
      deferred from the 2026-07-21 datums feature).
- [ ] forecast/flood_forecast_daily.py file split (seams documented
      in `forecast/README.md`; do after a quiet stretch, not
      mid-season).
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
      scratchpad import — implemented with 77 tests, pending Claude
      round-04 review.
- [ ] Versioned model follow-up: `_pluvial_fill()` starts a non-grid
      base at the preceding 0.1-inch stage bin, so tiny positive
      storage can calculate up to ~0.08″ below the base. Assess impact,
      fix only with a model version bump, and update goldens in lockstep.
- [ ] corrects_row_id / erratum convention for append-only ledgers
      (first hand-written erratum row shipped 2026-08-03).
- [ ] Cadence SLO monitor (within accepted-risk posture). "BEST
      EFFORT" site wording shipped in `5332dd70`.
- [ ] Audit a2 closeout: Phases 0–1 verified PASS in Claude round 03;
      close only after independent Phase 2 review reconciles M2/L2.

- [ ] House-point constant (40.4015, -73.991 in mrms_point_rain.py /
      nowcast UA context) sits ~568 m SE of the true Bay & Central
      intersection (40.405479, -73.995195 — OSM shared vertex, LiDAR
      4.36 ft = surveyed road middle). Harmless for catchment-box
      means (explicit CATCH_* bounds) but shifts the informational
      MRMS "point" column ~1 cell; correct deliberately, not
      drive-by, and note comparability in the MRMS cache README.

**Standing obligations**
- List `audits/` at session start; reply to open reports.
- Keep the living-documents registry (AGENTS.md) satisfied.

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
