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
      believed installed 2026-08-07 but NEVER fired until revived
      2026-09-02 (see scheduler-half-A-correction ledger line);
      half-B (external cron, 24/7) ready-to-execute in
      history/plans/external-cron-scheduler.md — needs the user's
      ~10 min for a fine-grained PAT.
- [ ] Town map, staged features: bands/classic shading toggle;
      per-building doorsill tagging (user point-and-click, feeds
      freeboard); possible georeferenced user snapshot base layer.
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

- [ ] edge_20260901 map points from event-#8 photos 14-16 (Central
      arm extent at peak) — needs user pick_coords clicks.
- [ ] Aug 27 brother's Rt 36 photos → third-party/ when obtainable.

- [ ] Ponding-dip field verification: user drives the top-20 list
      (history/data/ponding_top20.md, GPS-ready coords) as time and
      events allow — each yes/no calibrates layer precision. Future:
      pooled-volume routing to final minima (user sketch 2026-09-02);
      grate-backup probability by drainage position — deliberately
      out of scope until the 342-corner methodology earns extension.

- [ ] WATCH: nowcast.yml step reorder (dispatch after push, shipped
      2026-09-02) is untested in production until the next radar
      trigger — verify the first triggered run completes all steps
      and, if an alert-worthy burst, that dispatch fires post-push.
- [ ] Extra-rain slider on the town map (DEFERRED low-priority,
      user 2026-09-02): if built, option (a) only — drive the
      calibrated 342 models and repaint Highlands low-shelf streets,
      parity with the main page's scope; no town-wide fabricated
      depths.

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
- [ ] Versioned model follow-up: `_pluvial_fill()` starts a non-grid
      base at the preceding 0.1-inch stage bin, so tiny positive
      storage can calculate up to ~0.08″ below the base. Assess impact,
      fix only with a model version bump, and update goldens in lockstep.
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
