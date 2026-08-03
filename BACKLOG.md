# BACKLOG — open loops + ledger

**OPEN LOOPS is authoritative for "what's unfinished."** When HANDOFF
looks stale, trust this file. Ledger lines are append-only:
`YYYY-MM-DD | TAG | topic | one line` with tags
`[DECISION] [FACT] [DONE] [OPEN] [BLOCKER] [PREF]` and confidence
`[VERIFIED]/[STATED]/[INFERRED]` where a claim isn't ledger-backed.

## OPEN LOOPS (force-ranked)

**Active / near-term**
- [ ] Nowcast scheduler: user chose ACCEPT-THE-GAP 2026-08-03.
      Revisit trigger: next event where the radar strip is dark
      during a rise, or when user has ~10 min for the external-cron
      + fine-grained-PAT option (options analyzed in the 2026-08-03
      HANDOFF-archive entry).
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
