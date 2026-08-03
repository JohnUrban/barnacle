# Brain-migration distillation audit — independent auditor report

Audit: 2026-08-03-a1, round 01. Auditor: Claude (independent of the
migration author). Scope: LOSS and DISTORTION between
`attic/HANDOFF-through-2026-08-03.md` (2,930 lines, archived verbatim)
and the five new files (`AGENTS.md`, `HANDOFF.md`, `BACKLOG.md`,
`PLAYBOOK.md`, `audits/README.md`). Method: full read of the five new
files; full read of archive sections 9 (incl. 9b–9e), 10, 11, 12, 13,
and every dated entry after section 13; each candidate loss verified
against the rest of the repo (model/, history/, data/, forecast/,
per-event READMEs, workflows, tests, code comments) before being
declared lost.

## Verdict

The distillation is substantially faithful. Every hard rule, operational
trap, live thread, and same-day (8/3) decision I could trace in the
archive is either present in the new files or verifiably owned by
another repo document, and I found no fabricated or numerically
distorted claim: spot-checks all passed ("50 tests green" = exactly 50
test methods across tests/; event #6 figures +13.8″ / ~10:33 / 5th-of-6
/ hindcast +13.4″ / 3/3 channels match `assets/observations/2026-08-03/
README.md`; "all measured floods are RAIN floods" is consistent with the
six-event ranking; BACKLOG's "drain-coupling breathing first written up
7/13 tide event" cites the REAL 2026-07-13 tide-event README, not the
retracted phantom 7/13 flood). The defects found are at the edges: one
completed item imported into BACKLOG as still-open, one stale
cross-reference and one truncated copy-paste fragment in PLAYBOOK, and a
handful of minor open loops (passive collectors and the someday/
speculative queue) that now live only in the attic, which AGENTS.md rule
9 instructs agents never to read as instructions. Nothing rises to
LOST-CRITICAL.

## Findings

### 1. STALE-IMPORT — "Porch riser tape-out" listed as open; it was completed 2026-07-06

`BACKLOG.md` Parked list: "Porch riser tape-out (user offered): rebuilds
vertical ladder above porch base." The archive marks this CLOSED:
§9e.4 (attic lines ~1986–1990) — "CLOSED 2026-07-06 (v0.9 promotion):
user taped the porch risers (`assets/porch-measurements.txt`) and the
full ladder shipped in v0.9 — lawn_step 4.66, porch_step_base 4.68,
porch_step1_top 5.41, porch_deck 8.08. Details below kept for
provenance." The still-open-sounding offer text (lines ~2004–2008) sits
under that CLOSED banner as retained provenance, and the migration
author imported it as a live item. Verified done in the repo:
`assets/porch-measurements.txt` exists (5 risers, 40.75″ total) and
`model/elevations.md` lines 60–62 carry the measured ladder ("Measured
porch ladder, v0.9"). Fix: delete the BACKLOG item (or reword to
whatever genuinely remains, if anything — I found nothing).

### 2. STALE-IMPORT — PLAYBOOK recipe step 1 points at HANDOFF sections that no longer exist

`PLAYBOOK.md` line 25 (and archive line 2356, copied verbatim): "Read
`model/v0.10.1.md` + HANDOFF §§1–3 + 9e; memory has the rest." The
post-migration `HANDOFF.md` is a ~60-line snapshot with no §§1–3 and no
§9e; those sections now exist only in
`attic/HANDOFF-through-2026-08-03.md`, which AGENTS.md rule 9 says is
"archival, never read as instructions." A cold-start agent following the
recipe literally hits a dead reference on step 1 of the crown-jewel doc.
Fix: repoint to `AGENTS.md` + `HANDOFF.md` + `model/v0.10.1.md` (the 9e
physics context is owned by the model spec and the 7/06–8/03 event
READMEs).

### 3. DISTORTED (editorial defect) — orphaned truncated heading in PLAYBOOK

`PLAYBOOK.md` line 78: "### ✅ SHIPPED 2026-07-17 (tiers 1+3): observed
overlay on the" — a heading cut off mid-sentence with no body, sitting
between the post-event recipe and the Live-support section. It is the
first line of the archive's two-line heading (attic lines 2409–2410:
"…on the / water chart — tier 2 deliberately deferred") whose body was
(reasonably) not carried over. The underlying content is owned
elsewhere: the honesty-tier structure and the deliberate tier-2 deferral
live as code comments in `forecast/flood_forecast_daily.py` (~lines
474–479). Fix: delete the fragment.

### 4. LOST-MINOR — three "passive collector" open loops appear in no current file

Archive "Other likely sessions" item 4 (lines 2552–2555) and their
source sections:

- (a) **Verify enhancement holds at SH ≥ 7.5** (revised 9d.1 scope,
  lines ~1613–1620: "opportunistic," one multi-grate spot-check). Not in
  BACKLOG, not in `model/v0.10.1.md` (grep for 7.5/extrapolation: no
  hits), not in PLAYBOOK.
- (b) **Cold-conditions event collection** (cold-lockout hypothesis;
  §13 demotion story, lines ~2264–2276). The advisory-only STATUS is
  owned (`model/v0.10.1.md` line 68 "The retired cold-lockout remains
  advisory only"; `history/reports/cold_weather_retrospective.md`; user
  memory), but the collect-when-it-happens loop is absent from
  BACKLOG's parked list while peer items (falling-tide stall, Sandy-era
  archives) made the cut.
- (c) **NWS surge-parser first-real-event validation** (§9 item 1,
  lines 628–631; §11 item 3). `forecast/nws_surge_parser.py` is live in
  production (imported at `flood_forecast_daily.py:1911`) and has never
  been validated against a real coastal-flood product (all six measured
  events were rain events). The "run it once during the next coastal
  event" instruction survives nowhere — PLAYBOOK's live-support list
  would be its natural home.

Fix: one BACKLOG "passive collectors" bullet covering (a)–(c), plus a
one-line PLAYBOOK live-support item for (c).

### 5. LOST-MINOR — event #5's six-insight "next model session menu" reduced to one item

Archive lines 2513–2519: "Six structural insights queued in the
README's 'Model consequences' (priming, bidirectional drains, tilted
recession, recirculation, delivery tail, swale) — these are the next
model session's menu." BACKLOG carries only priming (the
antecedent-wetting item). The six ARE owned by
`assets/observations/2026-07-18/README.md` ("Model consequences,"
line 82 ff., verified all six present), so this is a pointer loss, not a
content loss — but nothing in the new files tells a future modeling
session that the menu exists. Fix: extend BACKLOG's antecedent item with
"...one of six structural insights queued in the 7/18 README's Model
consequences." (The related "MRMS multi-product forensics 15:10–15:30"
task is owned — and largely resolved — by that README's POSTSCRIPT.)

### 6. LOST-MINOR — the speculative/someday queue was dropped with no pointer

Archive §9 items 17–27 and adjacent parked projects appear in none of
the new files: ETSS / P-ETSS retry, Stevens NYHOPS, Iowa-Mesonet
historical NWS products (lines 809–825), USGS TWL API, multi-location
expansion + Atlantic Highlands Marina Barnacle spin-off (826–840),
self-serve subscribe flow (852–874), iOS app stages 3–4 (875–924),
heat-map polish list (974–1009), local flood reanalysis someday-project
(§9e.4-adjacent, 1951–1968), Rutgers mesonet RABCH022 observed-rain
input (1927–1930; partially owned by the 2026-07-06 README). Dropping
these from a force-ranked BACKLOG is defensible curation — but AGENTS
rule 9 ("attic = archival, never read") means no future agent will ever
resurface them. Fix: one line in BACKLOG's Parked section: "Someday
/speculative queue: see attic archive §9 items 17–27 + §9e.4-adjacent
(consciously move items out to activate)."

### 7. LOST-MINOR — Aug 21 2025 flood confirmation exists only in stale form outside the attic

Archive §9 item 8 (lines 691–697) and §10 (2014–2017): tentative-yes
that 342 Bay flooded 2025-08-21 (user saw swirly mud stains during an
August rental inspection — proto-mud-tracer evidence); confirming would
upgrade `data/labeled_events.csv`. The open question is owned by
`history/RESULTS_HANDOFF.md` line 156 ff., but in its PRE-mud-stain form
("if you weren't home... the threshold-crossing was real"); the
2026-05-18 tentative confirmation lives only in the attic, and
`data/labeled_events.csv` has no 2025-08-21 row. Low value (tide-side
calibration no longer gates anything), hence minor.

### 8. OK-BY-DESIGN — verified owned elsewhere or superseded (no action needed)

- Pocket-retention ≥11 h + grate-slot disambiguation rule (§9 item −1):
  owned by `assets/observations/2026-05-18/README.md` (lines 193–208,
  incl. the "textbook disambiguation example").
- 6/14 residual todos (§9 item 4): owned by
  `assets/observations/2026-06-14/README.md` "Open todos" (line 213);
  partially done (`fire_hydrant_central` is in `assets/map_points.csv`
  line 101; `flood_edge` category shipped 2026-07-07).
- `cold_weather_retrospective.py --write-report` clobber guard: owned by
  the script itself (lines ~438–494).
- 6.70-vs-7.20 ft Minor threshold trap and Sandy 12.03-hourly vs
  13.31-instantaneous trap (§12): owned by `history/RESULTS_HANDOFF.md`
  (lines 55–108).
- 1990s flood-frequency discontinuity + GEV "5000-year" caveat (§10):
  owned by `history/RESULTS_HANDOFF.md` (lines 128–133, 169–170).
- GitHub Actions version bump before June 2026 (§9 item 6): done —
  workflows are on checkout@v7 / setup-python@v6.
- Phase 1 road-reconstruction verification (§9 item 13): owned and
  contextualized by `model/elevations.md` (Bay Ave was not in Phase 1
  scope; design-vs-as-built distinction documented).
- Observed-overlay tier-2 deferral + tier-4 "reanalysis never silently
  replaces tier 2" doctrine: owned by code comments in
  `forecast/flood_forecast_daily.py` (~474–479).
- §12 smoke-test voice note (`forecast/smoke_test.sh` as refactor safety
  net): superseded by offline CI (compile + unittest + publish gate) and
  `forecast/README.md`'s extraction-seam verification rules.
- Known deliberate corrections (7/13 retraction, 7/6 crest window,
  5th-of-6 ranking, additive-only directive, daily-email-era text,
  "currently v0.6" voice notes): confirmed handled as intended; not
  flagged.

## Counts

LOST-CRITICAL: 0 · LOST-MINOR: 4 (findings 4–7) · STALE-IMPORT: 2
(findings 1–2) · DISTORTED: 1 (finding 3) · OK-BY-DESIGN: 1 grouped
(finding 8).

## Recommendation

One small patch commit: delete the BACKLOG porch-tape-out item and the
PLAYBOOK orphan heading, repoint PLAYBOOK recipe step 1 away from
"HANDOFF §§1–3 + 9e", and add three BACKLOG lines (passive collectors
a–c; the 7/18 six-insight menu pointer; a someday-queue pointer to attic
§9 items 17–27).
