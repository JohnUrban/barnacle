# Independent reply to audit 2026-09-27-a1 — findings R1–R7

Author: Claude Fable 5.1, session nickname **"Curlew"**. Date: 2026-09-27
(reply drafted 17:30–18:30 EDT). Independent of the audit author (Codex,
rounds 01–03) and of the event-support sessions (Claude Opus 5.5) whose work
the audit reviews. **Audit status: remains OPEN.** Implementation is on branch
`audit/2026-09-27-a1-reply` (worktree `../barnacle-a1reply`), unmerged, for
Codex's independent verification; nothing here touched `main`, the bots'
publications, or any other agent's branch.

Reviewed `main` at `0176795e0` (audit reviewed `10ea6c2a2`; the intervening
commits are Codex's rounds 02–03, the owner-originals reconciliation, the
episode registry, the expanded figures and bot publications). Baseline in the
isolated worktree before any change: **342 tests OK, one skip** (absent local
training re-pull), matching the audit's receipt.

Method: every disposition below was checked against primary records — the
append-only ledger, the owner's original note files, git history of
`docs/nowcast.json` and the forecast code, a fresh NOAA re-pull with quality
flags in GMT transport, the MRMS archive, and the audit's own probes — not
against narrative summaries. Where I disagree with the audit or with the
existing implementation I say so; where I could not settle a question it is
listed as unresolved rather than closed.

## Summary of dispositions

| Finding | Disposition | Current state after this branch |
|---|---|---|
| R1 capture discipline | **Confirmed** as a historical process defect; receipt-time qualification upheld | Provenance headers, playbook wording, three-clocks rule and handoff checklist added |
| R2 rain/gate promoted to fact | **Confirmed**; the 2.4-in figure reproduced as a sensitivity; Sep 27 rain finished | Four explicit scenarios per tide, both mornings' hydrographs, errata in both READMEs; no gate formula |
| R3 episode representation | **Confirmed** (production chart collapsed per day); registry independently checked, not rebuilt | Production peaks chart is per-episode; Heron interface documented, not implemented |
| R4 gauge provenance | **Confirmed**; the 08:54 "peak" was a plateau sample | Raw GMT archive with flags and receipts, QC/lag intervals, Battery comparison, as-seen trace |
| R5 surface meaning | **Confirmed, live** — including a public "so far today" line showing a phantom 39.0 in | Wording corrected on every arm that carried it; 39.0 traced to its input; provenance + rejection mechanism; figure superseded |
| R6 time/range handling | **Confirmed**, plus a second latent defect found (fold ignored in same-tz comparison) | Shared-parser/UTC comparisons, inclusive bounds, DST tests, offset-bearing appends, interval sidecar |
| R7 alert failure blocks publication | **Confirmed** (pre-existing; historical incident verified) | Exit 2 reserved for delivery-only failure; workflow publishes then fails; health file; tests |

## R1 — Live raw-note capture and handoff discipline: CONFIRMED (historical), partially addressed

Evidence, from `git show --format=%ad`:

| Record | Commit | Committed (EDT) | Note |
|---|---|---|---|
| Sep 26 morning README + last morning row | `7014329dd` | Sep 26 12:56 | during the event |
| Sep 26 evening batch (13 rows) | `dde559104` | Sep 26 22:42 | received 22:41 per audit |
| Sep 27 morning batch (23 rows) | `65b84fcd9` | Sep 27 10:44 | received 10:43 per audit |
| both `flood-measurements.txt`, Sep 27 README, first four-tide figure | `ebacf9e50` | Sep 27 10:51 | after the owner's 10:49 request |
| HANDOFF rewrite | `10ea6c2a2` | Sep 27 14:48 | |

So the ledger was kept promptly on receipt and the prescribed notes file,
plots and HANDOFF were not produced until prompted. I do not charge the agent
with the hours before each batch arrived; the audit's receipt-time
qualification is correct and I have written it into the record.

Reconciliation verified: I read all three owner originals end to end against
`rawnotes-reconciliation.json` and the 77 ledger rows. Every explicitly timed
line maps; the qualified entries (approximate 07:00, 1.4–1.5 → 1.45,
21:20–21:40 → 21:30, untimed gate visits → 21:58 and 08:30, "or slightly
lower" scalars, curb +0.5–1 → 0.75, the midday "12:06") are exactly the ones
I found independently. The "12:06" resolution is the owner's, recorded in
`rawnotes/clarifications.txt` with the pre-edit hash retained.

Defect that remained: both `flood-measurements.txt` files still opened with
"VERBATIM as relayed live". They now carry a PROVENANCE header naming the
assembly time (10:51 EDT Sep 27), the receipt times, and every surrogate or
window time; the bodies are unchanged. PLAYBOOK step 6's "duration is not yet
explicit … V = C·(R−D)·T is queued" predated the v0.10 tank and is corrected;
a three-clocks rule (observation / receipt / assembly) and a six-item handoff
checklist are added to live-support mode.

Not done: the PLAYBOOK still relies on an agent following it. That is an
operational fact, not something a code change fixes.

## R2 — Rain and gate hypotheses promoted into facts: CONFIRMED

The reviewed HANDOFF's "Rain added ~2.4 in" is gone (Codex's round 02
corrected it prospectively); BACKLOG line `event-#10-rain` still reads
"crest ≈ tidal ~23.8 + rain ~2.4 in" with Codex's erratum line below it. I
reproduced the number: production tank, box-mean rate, base held at the crest
bay level (5.703 ft), drain zero → **2.45 in at 09:02 local**, within
rounding of the probe's 2.452 (`rain_scenarios.json`, scenario A). That is a
sensitivity of one assumption, and it is now shown beside three others
(bay-tracking base with zero drain; bay-tracking base with the production
head-dependent drain; low base with full drain). Scenario B's largest lifts
occur when the bay is *below* the grates, where a zero-drain assumption is
unphysical — which is the point of showing them side by side rather than
promoting one. No gate formula is fitted anywhere on this branch.

Sep 27 rain forcing is now finished: 91 of 91 six-minute frames 04:00–13:00
local, catchment box-mean total **0.23 in**, peak rate 0.35 in/hr at 05:26
local, before first water; the fixed-base sensitivity lifts at most 0.9 in and
peaks before the flood. Under every explicit assumption the Sep 27 morning
flood is not materially rain-assisted. Sep 26 morning: 90 of 91 frames, the
archive's 14:24Z frame is missing (noted in the coverage record), total 1.30
in, burst 08:36–08:48 local. Both evenings are pulled as well (73/76 and
70/71 frames) so all four tides have a rain panel.

Gate evidence is now stated per tide with the owner's confidence: **direct**
only at Sep 26 18:19 (photo); "almost certainly" at the untimed Sep 26 late
visit (ledger 21:58 is a surrogate) and Sep 27 ~08:30 (surrogate); inferred
for Sep 25 PM and Sep 26 AM. The superseded figure's global "gate closed"
title is one of the reasons it is superseded.

Garage entry: retained as a proxy. The new figure labels the porch-step-top
line "≈ garage entry (proxy)"; no elevation constant was added.

Unresolved: no calibrated overtopping threshold or leakage rate exists and
none should be inferred from four tides; the tank was calibrated on low-bay
rain events and its high-base response is untested; the missing 14:24Z frame.

## R3 — Three floods retained but not represented consistently: CONFIRMED; registry checked, not rebuilt

Registry check: `check_observation_episodes.py` → 30 episodes, rows 2–267
associated exactly once, 0 rows awaiting review. I verified the four storm
windows' associations (35 / 14 / 27 / 1 rows) against row content, and that
`storm_id = 2026-09-25-coastal` is carried separately from the episode IDs
with the Sep 25 negative window as `negative_observation_window`. Nothing was
renumbered.

Consumer inventory (which still collapsed to a calendar-day maximum):

1. `_flood_peaks_chart_data` (production site, all-pathways chart) — **fixed**:
   `_measured_flood_peaks()` groups by registered episode (rows matched by
   content hash, the registry's identity) and only unregistered rows fall
   back per day, each marker saying which. Offline render: 20 markers, all
   episode-grouped; Sep 26 shows both e01 (5.701) and e02 (4.223). Legend and
   explainer updated. Test: `tests/test_episode_peaks.py`.
2. `_today_lookback` ("so far today" on site and widget) — day-scoped by
   definition; unchanged except for the R5 rejection guard.
3. Heron's `obs.events()` (≤12-h clustering) and `report.per_event()`
   (date-keyed `EVENT_PEAKS`) on `research/as-issued-validation` — **not
   modified**. What Heron will need — episode identity beside cluster
   identity, episode-keyed peak intervals, interval-preserving
   classification, as-seen inputs for as-issued replay — is documented in
   `history/plans/2026-09-27-heron-episode-interface.md`.
4. `history/data/342_bay_flood_events.csv` — a gauge-derived catalog; correctly
   left alone.

All 77 new rows keep a blank `model_predicted_depth_in`; nothing was
backfilled and no hindcast was relabeled as issued. The frozen wind trial
was not touched (all seven hashes match); three episodes remain one storm.

## R4 — Gauge provenance and lag statements: CONFIRMED

`gauge_qc.json`, from a fresh archive (`gauge-sources/`, GMT transport, MLLW,
all NOAA fields, request receipts, retrieved 2026-09-27 21:45Z):

| Tide | Sandy Hook max (ft NAVD88) | flat top (±0.03 ft) | corner crest | lag interval |
|---|---|---|---|---|
| Sep 25 PM | 4.748 @ 20:06 | 19:48–20:48 | dry (bounded) | — |
| Sep 26 AM | 5.847 @ 08:36 | 08:12–08:54 | 5.701 @ 09:06–09:13 | 12–61 min (30–37 vs the single max) |
| Sep 26 PM | 4.899 @ 20:42 | 20:24–20:48 | 4.223 @ 22:11–22:29 | 83–125 min |
| Sep 27 AM | 5.703 @ 09:06 | 08:48–09:24 | 5.618 @ 09:44–10:06 | 20–78 min (38–60 vs the single max) |

- The Sep 26 README's "peaked 5.83 at 08:54 … ~15 min later" and the plot
  cache's 5.852 at 08:36 are the **same series**: 08:54 is one sample on a
  42-minute plateau, not the maximum. Both statements are wrong as
  single-minute claims; the lag is an interval. Errata appended to both event
  READMEs; original prose retained.
- The committed `gauge_cache.json` differs from the new archive by a uniform
  −0.005/−0.006 ft (NOAA's own NAVD datum offset versus MLLW − 2.82), with no
  revised samples; **all rows are still `q='p'`**. A later download is not
  the verified record; the archive script writes new dated files on re-run
  and never overwrites.
- The spikes the live system saw — Sep 26 06:42 (9.894 MLLW in Codex's
  excerpt) and Sep 27 01:31–03:21 (bay 4.633 → 6.677 ft "observed" in the
  nowcast history) — are **absent** from the retained series; no 6-min step
  ≥ 1 ft remains. The as-seen record therefore lives only in the nowcast
  commit history and the audit's excerpt; both are now cited from
  `gauge_qc.json: nowcast_bay_input_trace`. The Battery peaks 24–60 min after
  Sandy Hook on all four tides (normal), and ebbed smoothly through the Sep 27
  01:30–03:30 window.
- Curiosity, not a conclusion: the Sep 27 01:31 phantom value 4.633 equals
  Codex's Sep 26 09:30Z preliminary sample (7.453 − 2.82) exactly. I could
  not determine why NOAA served it and do not claim a mechanism.

Unresolved: the retrieval time of the 10:51 cache is unrecoverable; the
verified (`q='v'`) series will arrive later and should be archived beside,
not over, the preliminary files.

## R5 — Public meaning and plot conventions: CONFIRMED, live

Arms enumerated under rule 8 for the meaning "the gray/observed line is
measured street water" and "October 30 is the worst measured flood":

| Arm | Carried it? | Action |
|---|---|---|
| Site landing, water-series note (`_render_water_series_section`) | yes: "a true observation, and via the drains' proven bay-coupling, the tide-pathway street water" — live in `docs/index.html` at `0176795e0` | rewritten: a measured **bay** level, the tide-pathway input, never a street measurement, with the Sep 25–27 lag evidence |
| Details page, historical ranking (`flood_forecast_daily.py` ~5520) | yes: "worst events measured … Oct 30 2025 (~5.27 NAVD88 measured…)" | Sep 26/27 tape crests named as the largest recorded; Oct 30 labeled reconstructed |
| Details page, how-flooding (`rendering.py` ~310–320) | yes, twice: "All four floods measured to date — including the two worst — were rain-driven"; "The biggest flood in this project's records — October 30, 2025" | dated and corrected; frozen calibration references untouched |
| Site all-pathways chart legend/explainer | "MEASURED flood (spot-check, any cause)" implied every flood was shown | per-episode label and explainer (R3) |
| Email chart PNG title "observed (gray) → forecast" | states observation, no street claim | objective exemption, unchanged |
| Widget v7.29a | draws the gray line; the only "observed" wording is a code comment; the "so far" line takes its source label from `forecast.json` | objective exemption; **no widget edit, no version bump** |
| SMS / ntfy imminent text ("bay over grates") | names the bay | exempt |
| Outlook page, per-tide pages | no such claim (grep) | exempt |
| Superseded four-tide PNG | every qualitative report on the SW-grate line; global "gate closed" | superseded by `event10_hydrographs.png` with a separate report strip (dry / water-not-measured / gate; surrogate times hollow across their window), bounds drawn as half-markers, per-panel gate confidence; the old PNG and script are retained with a SUPERSEDED header |

Rendered pages were regenerated offline from the branch (`--no-send`, output
to the scratchpad, the worktree's ledger side-effects restored) and grepped:
the corrected sentences are present and none of the three stale phrases
remains. `docs/` was not modified on the branch; the bots publish it.

**The 39.0-inch daily maximum, traced.** `docs/nowcast.json` history:

| Commit | Run (local) | bay input, ft NAVD88 (source) | street now | archived Sandy Hook |
|---|---|---|---|---|
| `62a848d5f` | 01:31 | 4.633 (observed) | 14.8 | 0.79 |
| `a5020b395` | 02:33 | 5.667 (observed) | 26.7 | 0.17 |
| `5f80bcf04` | 02:54 | 6.677 (observed) | 38.9 → day max **39.0 @ 02:40** | 0.20 |
| `e5c15508c` | 03:21 | 6.625 (observed) | 37.8 | 0.23 |
| `68c86c575` | 03:55 | 0.325 (observed) | — | 0.44 |

The value is the tank's observed-window peak from a run whose bay input was a
phantom 6.68 ft; `_despike_gauge` cannot reject a run of bad samples that
fills the tail of the 3-h window. `_write`'s max-wins merge (local previous +
published origin) then carried it all day, and `_today_lookback` — whose
docstring says the modeled source is used "only when tape and gauge have
nothing higher" but whose code takes the maximum — published it as **"so far
today: SEVERE +39.0 @02:40 modeled (live radar)"** above the 25.2-in tape
crest (verified in `docs/forecast.json` at `0176795e0`). It is not a street
measurement and not a sensor spike in the retained data.

Repair on this branch, bounded to provenance and an operator correction path
(no input or fallback policy change, which would need versioning):
`day_max_provenance` (kind, bay input and source, radar quality, run) travels
with the winner and carried-forward values declare themselves;
`data/nowcast_daymax_rejections.json` lists rejected (day, utc) pairs that
the merge and the lookback both skip; the Sep 27 entry is recorded with its
evidence. It was not live today; the line rolls off at local midnight.

**Owner decision needed (not taken here):** whether a same-day tape crest may
ever be outranked on the "so far today" line by a modeled value. The code's
max-wins rule and the documented "only when nothing better" intent disagree;
changing it is a display-policy choice under rule 8.

## R6 — Timestamp and range handling: CONFIRMED, plus one more defect

- The audit's probe reproduced: a reading exactly on the offset-bearing left
  boundary was dropped by a truncated string comparison. Fixed by parsing both
  the series bounds and the rows through `parse_station_local_time`, comparing
  inclusive **UTC instants**, and labeling from the parsed local time.
- Found while testing: aware datetimes that share one `tzinfo` compare and
  subtract by wall time and ignore `fold`, so 01:30 EDT and 01:30 EST on
  2026-11-01 would land on the same slot. The repo already has
  `station_time_sort_key` for this trap; the chart code now converts to UTC
  first. Tests: offset rows on both edges, legacy naive rows, naive series with
  offset rows, the repeated fall-back hour, and an unparseable stamp.
- `_flood_peaks_chart_data` used `strptime(ts[:16])`; now the shared parser.
- The event plot script's naive-vs-aware `TypeError` is confirmed; that script
  is superseded (header explains why) and the replacement compares in UTC.
- All 77 rows remain naive and untouched. `bin/append_observation.py` now
  stores an explicit offset for new rows (naive input normalized, fold=0) with
  tests for EDT, EST, the fall-back hour, and a verbatim offset stamp; the
  ledger README documents the convention.
- `observation_intervals.json` (built by
  `history/scripts/build_observation_intervals.py`, row-hash identity) records
  time kind and depth kind for all 77 rows: 45 exact points; 7 ranges; 4
  upper bounds; 4 lower bounds; 3 "or slightly lower"; 2 surrogate-time gate
  reports; the Sep 25 surrogate-time negative window; the 21:20–21:40 onset
  window; the approximate "around 7". Consumers do not read it yet (Heron
  handoff).

## R7 — Alert failure can still block forecast publication: CONFIRMED (pre-existing)

Historical incident verified: the 11:09Z Sep 26 hourly run exited 2 after the
ntfy Latin-1 failure and `forecast.json` stayed at 10:40Z until 13:09Z, in
the middle of the largest flood on record, because the gate and commit steps
require prior-step success.

Repair: `_settle_delivery` acknowledges rails transactionally as before and
writes `data/alert_delivery_health.json` (status ok / partial / failed,
attempted, succeeded, failed with errors, `retry_eligible`,
`publication_blocked: false`); a total failure returns exit
`DELIVERY_FAILED_EXIT = 2` and every other non-zero exit still means the
generation failed. The workflow captures the code: on 2 it records
`delivery_failed=true`, runs the gate and commit/push unchanged, and a final
step fails the job with an `::error::` pointing at the health file — the run
stays red, the artifacts publish, `last_sent_*` stays untouched and
`pending_base` keeps the retry. Tests: total failure (health failed, nothing
acknowledged, both rails pending, returns False), partial failure (only the
delivered rail acknowledged, the other pending), success clearing a prior
pending, the exit-code contract, and a workflow-contract test pinning the
step order and the post-push failure step.

This is a production workflow change and needs Codex's independent review
before merge; it is not a suppression of errors and does not mark anything
delivered.

## Validation performed (branch `audit/2026-09-27-a1-reply`)

- `python -m unittest discover -s tests` with `BARNACLE_REQUIRE_GRIB=1`:
  **374 tests OK, one skip** (32 new).
- `forecast/check_artifacts.py`: clean. `reproduce_v0_10_1/3/6.py`: PASS,
  read-only. Seven frozen wind files: hashes match
  `audits/2026-09-24-a4/frozen-files.json`.
- Offline site regeneration from the branch (no send, scratchpad output):
  corrected wording present on landing and details pages, stale phrases
  absent, per-episode peaks in the chart payload. The worktree's ledger
  side-effects from that run were restored, so no bot-owned file is on the
  branch.
- `event10_hydrographs.png` visually inspected twice (first render had title
  collisions and a clipped label; fixed).
- No model constant, landmark, input ladder, alert policy, wind-candidate
  file, frozen golden, ledger row, or another agent's branch was changed.
  `docs/` untouched. Widget untouched (objective exemptions recorded above).

## Still unresolved after this reply

1. Scientific: no gate threshold or leakage model; tank behavior at high base
   untested; Sep 26 14:24Z MRMS frame missing; verified NOAA series pending.
2. Heron: episode-aware evaluator and interval-preserving scoring not
   implemented (documented interface); issuance coverage for the storm not
   checked.
3. Owner decisions: the "so far today" ranking rule (above); Borough gate
   operation history and gate photo (privacy rule 9) still pending; photos
   for the three episodes still pending as of this reply.
4. Display policy for a retained-but-rejected day max is an operator record,
   not automation; a future rejection needs a human to add an entry.

## Handoff to Codex

- Branch `audit/2026-09-27-a1-reply` in worktree `../barnacle-a1reply`, three
  commits on top of `0176795e0`: `bc645ed5c` (production repairs + tests),
  `5b614a076` (event analysis artifacts), and the documentation commit that
  adds this reply, HANDOFF and BACKLOG.
- Changed behavior: (a) hourly workflow publishes validated artifacts on a
  delivery-only failure and fails afterwards; (b) near-term chart tape dots
  and all-pathways peaks parse through the shared station helpers and compare
  in UTC, peaks are per registered episode; (c) nowcast day max carries
  provenance and honors an operator rejection list, as does the "so far
  today" line; (d) `append_observation.py` stores offsets; (e) public wording
  on the landing/details pages no longer calls the bay line street water or
  October 30 the worst measured flood.
- Review focus: the workflow exit-code contract and `_settle_delivery`
  (production alerting); the UTC-comparison change in the tape loader; the
  rejection mechanism's interaction with `_origin_day_max` on racing writers;
  the four rain scenarios' assumptions; the errata wording in both READMEs.
- Recommended next action: independent verification, then merge with the
  ship ritual (commit → gate → push, rebase-with-gate). The Sep 27 rejection
  entry is moot by the time of merge but documents the case. Do not close the
  audit on tests alone; the scientific items above stay open.

## Addendum — additional observations and one retraction (added 2026-09-27 18:25 EDT, same author)

John asked what else looked off and what the "radar vs my measurements"
inconsistency actually is. Recorded here so the reviewer sees the same list.

**What the "so far today" line really compares.** The nowcast's street number
is the bay level converted to a base stage at the corner PLUS the radar-rain
tank on top; `_today_lookback` labels it "modeled (live radar)". Today's
+39.0 in at 02:40 was almost entirely the bay term from the phantom 6.68-ft
input; radar rain that morning was 0.23 in. The label misattributes the
source. Live at 22:12Z: light rain 0.34 in/hr, bay 1.78 ft rising, model
claims +4.6 in at the corner rising to +6.5 (STREET); no owner report since
12:48. A "no water" observation at such a moment is calibration data.

**Erratum to the R5 arm table above (my miss).** The same `_today_lookback`
has a gauge branch that converts the Sandy Hook peak to the corner and labels
it "observed (gauge)"; the site strip and the widget "so far" line then show
a BAY level as the corner's peak. On Sep 25 evening that line would have read
about +14.8 in while the corner was dry. It is the R5 meaning on an arm I did
not enumerate. Fix belongs with the ranking decision below.

**Recommendation on the ranking rule (owner decision).** Tape measurements
should win the "so far today" line whenever any exist for the day; gauge and
model values only as fallbacks, labeled "bay (gauge)" / "modeled (bay + radar
tank)", never as corner water. Not implemented on this branch pending John's
answer (rule 8: site strip + widget line + email if it carries it).

**Other items seen while working, ranked:**

1. Metadata rows in the observation ledger: rows 264–268 (`landmark_key =
   none`, retrospective clarifications, three by Codex and two recording
   John's statements) force every consumer to special-case them and made the
   registry exclude them explicitly. Keep them (append-only); future
   clarifications belong in a separate append-only file.
2. Production gauge ingestion (`nowcast.current_bay`, surge reads) takes the
   single latest despiked sample with no Battery cross-check; a run of bad
   samples at the end of the 3-h window passes the median filter, which is
   what happened 01:31–03:21 today. Any fix is an input-policy change (class
   (b) bump, review, DECISION); not touched here.
3. The first phantom value, 4.633 ft NAVD88, equals Sep 26's 09:30Z
   preliminary sample (7.453 MLLW) exactly. Unexplained; not concluded.
4. `assets/observations/README.md` said "27 registered episodes" while the
   registry holds 30 (Apr 17/18 and Aug 2025 were added later the same day).
   Corrected in this addendum's commit.
5. The two scheduler arms disagreed on `active` within minutes on
   2026-09-27 21:17–21:46Z (GitHub Actions 0, local launchd 1): the radar
   rate was sitting at the 0.3-in/hr activity threshold. Threshold flapping,
   not a fault; the day-max merge tolerates it.
6. The Sep 26 18:19 gate photo and the three episodes' photos are still not
   in the repo (rule 9 applies before publishing).

**Retraction.** I told John there was a ~50-minute nowcast publish gap
between 16:41 and 17:31 local today. There was not: commits and
`data/nowcast_heartbeats.csv` show publishes at 16:41, 16:48, 16:50, 16:55,
17:00, 17:17, 17:20, 17:29 and on (longest interval 17 min). The "78.6 min
source age" I saw came from my worktree's stale copy of `docs/nowcast.json`
during the offline render, not from production. Withdrawn.
