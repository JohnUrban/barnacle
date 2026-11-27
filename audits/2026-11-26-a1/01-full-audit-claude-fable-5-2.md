# Audit 2026-11-26-a1 — full audit of Barnacle: everything that needs fixing

**Report 01. Author: Claude Fable 5.2 (lead auditor, the session that ran the
2026-11-10 health check and the 2026-11-26 storm support).** Requested by
John on 2026-11-26 at 22:10 EST: "Let's do a full audit of barnacle to find
all the things that need fixing. We can pass the audit off to Codex as well
for enriching the findings further. We can later decide on who implements
what." Written 2026-11-26 23:30 EST, during the storm, with the evening flood
still receding. **Findings only. Nothing was fixed, and no owner is assigned.**

This report needs an independent reply (`02-…`, a different agent) before any
close-out, per `audits/README.md`. Part of what it criticises is the lead's own
work since 2026-11-10; see section 6.

## 1. How this was done, and how far to trust it

- Five read-only sweeps ran in parallel as subagents of this session, one per
  slice. Their reports are filed unedited as `01-sweep-*.md` (finding IDs
  AL, FC, OP, DD, UX) with their small probe scripts under `01-probes/`. They
  hold the evidence (file:line, commits, reproduction steps). This report
  ranks, merges and cross-references them; it does not repeat the evidence.
- John contributed two findings with screenshots (`01-owner-screenshot-*.png`),
  recorded here as O-1.
- Repo state: main at about `ab7e41c59` to `bbbf5678b`. Tests: 511 pass, 1 skipped.
- **The sweeps and the lead are one model in one session.** They are evidence
  gathered quickly, not independent review. The lead re-checked only the items
  in the table below. Everything else is "as reported by the sweep" until the
  reply checks it.

| Item | Lead's check | Result |
|---|---|---|
| O-1 (owner) | published JSON at 2026-11-27T03:09Z and 04:09Z | confirmed: curve +29.2 in then +24.7 in, table +6.7 in, for the same tide |
| FC-1 | `git show 7386bc773` forecast, gauge tail, `data/surge_state.json`; next run `fc515b6a2` | confirmed: surge +7.219 ft, rung "fresh", no degraded input, state saved |
| AL-1 / FC-9 | read the gate in the nowcast script (lines 519–534); own history dump of 32 nowcast commits | confirmed |
| AL-2 | read `persist_alert_state` (FFD:5154); `alert_state.json` at `813f7e9f6`, `9599e8036` | code confirmed; both states show "rain risk elevated", rank 3, signature unchanged from the earlier send. Whether a later send followed was not re-checked |
| AL-4 | `alert_state.json` at `4d6e5fe18` | confirmed: a 07:29 tide alerted at 08:15 local |
| UX-2 | `today_regime` in three runs (11:09, 12:07, 13:09 EST) | confirmed: moderate / light / moderate while `day_worst` said severe |
| FC-11 | read FFD:8484–8488 | confirmed in code; not triggered yet this season |
| DD-3 | `docs/details.html` ("N = 21"), ledger row 75 | partly: the page and the free-text cell are as described; the lead counts 28 numeric cells, not 21, so another filter applies. Unresolved |
| OP-1 | commit times on 2026-11-26 | the 23:55Z → 00:33Z gap is confirmed; the eight-day pattern is the sweep's measurement from the Actions API, not re-run |

**Not audited:** real pixels (no browser or Scriptable run), the literal bytes
of sent alerts (re-rendered from the sending run's files), photo privacy (not
re-reviewed), the research code (wind-shadow, Heron, Tern), `history/scripts`
analysis code, GitHub repository settings beyond workflow permissions, and the
coverage of the nowcast script (a privacy control on this machine blocks shell
commands that name that file, because it holds a contact address; it was read
directly instead).

## 2. The short version

Eight problems matter most. Each is a theme joining findings from several sweeps.

1. **One tide, several numbers, and each screen picks a different one.** (T1)
2. **A burst of bad gauge readings became a "fresh" +7.2 ft surge and was
   published for an hour with every input marked healthy.** (T2)
3. **In a tide-driven flood nothing says what the water is doing now**, and the
   live push is blind until rain passes 0.3 in/hr. (T3)
4. **Barnacle shows bay level as street level**; with the tide gate closed the
   street lags by up to a foot and no screen says so. (T4)
5. **The alert state machine has holes**: upgrades never alert, unchanged risk
   re-alerts and uses up the daily cap, past tides get alerted. (T5)
6. **The scheduler has a daily hole at 00:00 UTC (7 PM EST)**, and several
   failure paths silently skip the alert check. (T6)
7. **Published accuracy describes the NWS-assisted table, not the curve that
   drives the chart and widget**, and one accuracy table drops every miss. (T7)
8. **The record-keeping rules no longer match practice** (append-only rule,
   three correction styles, stale open loops, lapsed checkpoints). (T9)

## 3. Findings by theme

Severity is the lead's, after merging; the sweep's own rating is in its file.
"Class" is the charter rule 5 change class a fix would probably fall under
(a: formula/constant/landmark, b: inputs/policy/alerts, c: bug fix or docs).

### T1 — One tide, several numbers (critical)

Three estimates exist for the same high tide: the **table** (the NWS coastal
flood product when it lists the tide, otherwise Barnacle's surge with a 36-h
fade), the **curve** (`water_series`: always Barnacle's own surge with the
fade), and the **seven-day series** (NWPS/P-ETSS guidance plus the advisory).

| ID | Finding | Sev. | Class |
|---|---|---|---|
| O-1 | Owner, 2026-11-26 22:27: main chart shows the next tide as bad as tonight's; the seven-day chart shows it far lower; the cards differ the same way; the widget follows the main page | critical | b |
| FC-2, UX-1 | Full map of which field and surface reads which estimate. Alerts, day outlook, summary sentence, per-tide pages and scoring read the table; the chart, flood windows, `today_*` fields, widget headline and map slider read the curve; the day badge takes the worse of the two | critical | b |
| UX-2 | On 2026-11-26 from 11:09 to 13:09 EST the widget headline and the alert email's "TODAY" line said MODERATE or LIGHT for the evening that produced the highest flood on record, while the site card said SEVERE | critical | b |
| UX-7 | "Worst" points at a different tide on the ribbon, the star, the map buttons, the seven-day page and the link preview in the same run | medium | b |
| FC-3 | A product row is never checked against the gauge: the table stayed 0.4 to 1.0 ft below water already observed | high | b |
| FC-5 | Where the product's rows end, or if it lapses for one run, table values jump by feet (6.9 → 9.15 ft computed for the 02:11Z run) and the alert signature would change | high | b |
| FC-16 | Product values rounded to 0.1 ft sit on class thresholds (6.9 "street", 7.0 "light") | low | b |
| FC-17 | Seven-day table pairs a product central value with a P-ETSS band that does not contain it | low | c |

Already queued as items 2 and 4 of
`history/plans/2026-11-26-storm-evidence-and-queue.md`; the sweeps add the
complete consumer map, which is what a fix needs.

### T2 — Bad gauge data became a forecast (critical)

| ID | Finding | Sev. | Class |
|---|---|---|---|
| FC-1, UX-3 | Run 2026-11-26T19:06:47Z took a garbage gauge tail (7.302 ft at 14:00 EST; the next run showed 3.58 for the same stamp) as a +7.22 ft surge. Published: widget "peak +54.3″", flood windows up to "+83.9″", day peak 8.05 ft NAVD88. Saved to `data/surge_state.json` and written into `predictions_log.csv` and `outlook_log.csv`. No alert went out only because NWS product rows covered every tide inside 48 h | critical | c (guard) |
| — | Cause as reported: the despike filter is one-sided at the newest reading, so a run of six bad samples passes; nothing bounds the surge or its change between runs; the gate only requires a finite number | | |
| OP-12 | No retry on any upstream fetch | low | c |

This is the open loop `gauge-ingest-no-battery-check` (2026-09-27) recurring in
the hourly surge anchor. The raw NOAA values were not archived, so the exact
path through the filter is inferred.

### T3 — No "now" in a tidal flood (high)

| ID | Finding | Sev. | Class |
|---|---|---|---|
| AL-1, FC-9, UX-4 | The nowcast computes a street level only when radar rain exceeds 0.3 in/hr (the drain term in that test is dead code). On 2026-11-26 the bay rose from 2.1 to 6.3 ft NAVD88 over 24 published runs with no street level; the morning flood never got one. The first value (+33.5 in) and the live push came at 20:55–20:56 EST, about 100 minutes after the owner saw water at the curb, labelled "LIVE radar" though 32.9 of the 33.5 inches were bay level | high | b |
| FC-9, UX-8 | Consumers read a missing street level as zero (`or 0`), against charter rule 7 | medium | c |
| AL-11 | When the gauge is stale the nowcast falls back to the astronomical tide with zero surge (3 ft low at 11:51 EST on 2026-11-26) and the alert contract ignores the fallback flag | medium | c |
| UX-4 | The strip prints UTC clock times; "past" appeared on the tide four minutes before the street crested; trend said "falling" while the street rose | medium | c |

A bay-keyed rule would have fired **early** on 2026-11-26 (bay over the curb
height at 18:45 EST, owner saw the curb still dry at 19:16). So a fix depends
on T4.

### T4 — Street is not bay; the gate is undisclosed (high; science open)

| ID | Finding | Sev. | Class |
|---|---|---|---|
| UX-5 | No screen that carries a tidal call mentions that the Snug Harbor gate is not modelled. Flood-window wording ("approximate, 10–20 min"), "recent peaks" depths and "flood recall 74.6%" all state street conditions from the gauge | high | c (wording) |
| FC (K4 list) | The assumption lives in seven places in code (listed in the forecast sweep) | — | a if changed |
| — | Evidence from 2026-11-26-e02: street 0.5 to 1.25 ft below the bay on the rise, level at the crest, above on the fall; e01 the same pattern | | |

No gate model is authorised (audit 2026-09-27-a1). Disclosure is a wording
change; anything more is the owner's decision.

### T5 — Alert state machine (high)

| ID | Finding | Sev. | Class |
|---|---|---|---|
| AL-2 | `last_sent_rank` is a running maximum (introduced 2026-09-14, at 4 since 2026-09-25): an upgrade of an already-alerted risk never sends. Candidate real misses: rain risk possible → elevated on 2026-10-11 and 2026-11-05; tide street → light on 2026-11-23; light → moderate on 2026-09-23 | high | c |
| AL-3 | The signature changes when a pathway ties or drops out, so unchanged risk is sent as a "new event" (five production cases listed). Since 2026-09-25, 40 of 55 base sends were rank 1 and 21 of 34 send-days hit the cap. On 2026-09-27 the used-up cap suppressed a real rain alert 91 minutes before street water | high | b |
| AL-4 | The signature is the first top-rank tide with no lower time bound: a later same-rank tide waits (tonight's record tide was first pushed at 11:09 EST though forecast severe for two days), and tides already past have been alerted as if upcoming | high | c / b |
| AL-8, OP-2 | Alerts are sent before their state reaches origin; a gate or push failure afterwards repeats the alert hourly without counting toward the cap | medium, latent | c |
| AL-5 | Quiet hours ignore severity and lead time: a severe tide at 09:23 first seen at 22:00 is sent at about 07:08. Rain risk is never "tonight" | medium | b (policy) |
| AL-6 | A held or capped alert is delivered later only if its signature differs from the last one sent; a held "rain risk" can be dropped | medium | c |
| AL-7 | A lower-ranked pathway is invisible: a new Flash Flood Warning under a severe-tide window sends nothing, and makes the dispatch check fire every ten minutes | medium | b |
| AL-9 | Base radar alerts have no curb floor, bypass quiet hours on any "LIVE radar" label, and re-send at local midnight | medium | c |
| AL-10 | The alert label prints a projection the policy itself rejects (falling trend) | medium | c |
| AL-12 | Email and push can headline different tides; subject leaks the storage timestamp | low-medium | c |
| AL-13 | Retries after a transport failure bypass quiet hours and the cap and never expire | low | c |
| AL-14 | The tests pass around all of the above (clean-state fixtures only) | medium | c |
| AL-15 | Retired-SMS remnants: the log prints only the retired rail's reason, so the live rail's reason is never logged | low | c |

### T6 — Operations (high to low)

| ID | Finding | Sev. |
|---|---|---|
| OP-1 | Every day there is no GitHub nowcast run and no alert check for 35–40 minutes from 23:55Z (6:55 PM EST). The Mac arm ran through it on 2026-11-26 but discarded its results by design and cannot dispatch alerts. The evening flood's onset fell in that hole | high |
| OP-3 | Any earlier failure in the nowcast workflow skips both alert-dispatch checks; the whole-tree gate couples them to hand-edited ledgers (a typo pushed mid-flood disables the fast alert path) | medium-high |
| OP-4 | A crash in a dispatch check counts as "nothing to dispatch" and the run stays green | medium |
| OP-5 | Pages builds on every push (up to 17 in an hour during the storm); failed deploys are not retried (81 minutes stale on 2026-11-25) | medium |
| OP-6 | Requirement files pin four packages; everything else floats; the two arms run Python 3.11 and 3.15 | medium |
| OP-7 | Every run checks out 410 MB (301 MB photos) under a 5-minute timeout; one run took 222 s to check out | medium |
| OP-10 | The watchdog runs on the same laptop (absent 21% of the time), does not watch the local arm, and logs no proof that a page was sent | medium |
| OP-8, OP-9 | A degraded first tick after wake can overwrite a good nowcast; in quiet weather only the laptop refreshes `docs/nowcast.json` | medium-low |
| OP-11 | The venv self-heal deletes the working environment before building its replacement | low-medium |
| OP-13, OP-14, OP-15 | Repo growth; the daily archive depends on one run's start time (nine days missing, none recent); hygiene (stray `del` file is an unrelated note; `ALERT_SMS_TO` still passed) | low |

### T7 — Scoring and accuracy claims (medium)

| ID | Finding | Sev. |
|---|---|---|
| FC-6 | The published accuracy sentences reproduce exactly, but they score the table, and 13 of 27 scored tides are NWS-product rows. On those tides the curve's rule has two to four times the error (0.22–0.65 ft against 0.12–0.15). The curve is never scored | medium |
| FC-4 | As issued for the two 2026-11-26 tides at 12–24 h: product +0.03 and −0.98 ft; constant surge −1.41 and −3.04; fade −1.47 and −3.34. The fade costs 0.05–0.5 ft beyond constant; surge growth is the rest | high (science) |
| DD-3, UX-11 | "Outcome-depth accuracy" on the details page keeps only rows whose prediction cell is numeric, which drops the 20 rows of 2026-07-06 recorded as predicted dry. All remaining errors are over-predictions; nothing after 2026-07-09 is included | high |
| DD-7 | The observed-peaks cache keeps preliminary values for ever (8.667 against the verified 8.805 for 2026-09-26); tonight's noisy crest will be frozen too | medium |
| DD-4 | "Six measured peak anchors" counts two reconstructions (2025-12-19, 2025-10-30); the phrase is on the landing page, in the spec and pinned by a test | medium |
| UX-11 | "Peak MAE at this lead 0.11–0.16 ft" was shown beside a tide that erred by 0.4–1.0 ft; the note "rows are never recomputed" predates the 2026-11-10 correction | medium |

### T8 — Model behaviour needing a decision (medium to low)

| ID | Finding | Sev. | Class |
|---|---|---|---|
| FC-8 | With the bay at or above the SW grate the drain is zero, so 0.01 in/hr of drizzle models 3.9 in of street water; a constant meant to prevent this is never referenced. Whether the street really ponds then is unknown (open item "high-base tank") | medium | a |
| FC-10, UX-6 | A surge flood was headlined "SEVERE (RAIN)" because rain added 0.6 in of about 33 | medium | c |
| FC-7, UX-9 | The first six hours of the curve are a back-cast with the current surge; "Flooding windows (coming 30 h)" lists past windows without dates, and the widget's "wet" line showed the morning episode all afternoon | medium | c |
| FC-12 | The per-tide table adds rain with a v0.6 formula that is not in the v0.10.6 spec and has a step at 0.1 in/hr | medium-low | a or c |
| FC-13, UX-10 | Two threshold schemes for "light / moderate / severe" (server: curb +4/+8 in; widget live line: lawn step / porch step). The morning and evening floods of 2026-11-26 were the same rank | medium | b |
| FC-11 | The retired cold-lockout rule still removes the map and blanks the ledger's water level when the 72-h mean is below 32°F and the peak is under 8 ft. Dormant now; winter is coming | medium | c |
| FC-14, FC-15, FC-18 | Tank uses the previous sample's bay level; unknown rain is read as zero in production; small label slips (3.64 for 3.52, "365-d mean") | low | c |

### T9 — Records, charter, documents, tests (medium)

| ID | Finding | Sev. |
|---|---|---|
| DD-2 | Charter rule 2 names three files of different kinds and nothing enforces it. The sweep's inventory classifies every file in `data/` as primary record, as-issued prediction, derived score or operational state. Proposed wording is in section 5 | high |
| DD-1 | The observation ledger has three correction styles (labelled ERRATUM rows, free-form `none` rows, in-place edits) and its README describes only the first; no code reads any erratum. The lead used two styles on the same day (2026-11-26) | high |
| DD-5 | Any local run of the forecast appends to the "as-issued" ledgers; `--no-send` and `--dry-run` do not prevent it; rows carry no provenance; the writers are untested | medium |
| DD-6 | The production entry point and all page renderers are never executed by tests (59 of 166 functions in the main script) | medium |
| DD-8 | `model/elevations.md` is cited as the survey source but does not source six of the eighteen landmarks, contradicts itself on the corner grate, and omits the second porch step, the garage floor and the open 4.37 against 4.16 discrepancy | medium |
| DD-9 | BACKLOG OPEN LOOPS lists done items as open, has duplicates and stale pointers; 41 of 47 OPEN ledger lines have no later line | medium |
| DD-10 | Two dated obligations lapsed unrecorded: the Heron checkpoint (2026-10-09) and the wind-shadow trial's 60-day mark (2026-11-23). November episodes have no storm ID | medium |
| DD-11 | Seven reports since September have neither a depth nor a band; episode 2026-11-26-e01 has no machine-readable level | medium |
| UX-12 | "So far today" shows a derived level as MEASURED (+30.7 in at 21:15), shows a 21:57 recollection at 09:48, misreads "around 9:37'" as exact, and resets at midnight | medium-low |
| DD-12, DD-13, DD-14, DD-18, UX-13, UX-14 | Stale READMEs and copy: ledger schemas, `README.md` still promises email-to-SMS, widget version, "benchmark 5.70 ft", PLAYBOOK paths, UTC on the strip | low-medium |
| DD-15 | Rule 5 is ambiguous for removing an alert channel; three production commits since 2026-09-28 (`988e8197c`, `da16cd11c`, `9f36fca41`) have no independent review. This audit's reply could cover them | low-medium |
| DD-16 | CI does not provision Node, so widget tests skip there; the episode checker runs nowhere automatically | low |
| DD-17, OP-15 | A contact email address is hard-coded in User-Agent strings in twelve scripts of this public repo; other addresses in `attic/` and model docs. Locations are in the sweeps; the owner decides | low |
| UX-15 | Small warning text on the widget is below 4.5:1 contrast; no dark scheme | low |

## 4. Decisions only John can make

1. **Which number is "the" forecast for a tide**, and how the other is shown. (T1)
2. **Whether a tide-driven "now" line and push may exist while the gate is
   unmodelled**, and with what wording. (T3, T4)
3. **Alert policy:** severity and lead time in quiet hours; a day-of reminder;
   whether NWS warnings bypass the cap. (AL-5, AL-4, AL-7)
4. **Rule 2 wording** and one correction style for observations. (DD-1, DD-2)
5. **Rule 5:** is removing a channel a class (b) change? (DD-15)
6. **The hard-coded contact address** in a public repo. (DD-17)
7. **Where the watchdog should live.** (OP-10)
8. **Keep, fix or retire** the outcome-depth table and the "six measured
   anchors" wording. (DD-3, DD-4)

## 5. Proposed wording for charter rule 2 (for John to edit)

> **Records by class.** *Primary records* (owner observations, raw gauge and
> radar pulls) are never altered in meaning; an entry error the owner corrects
> is fixed in place, with the original wording kept in the episode's notes
> file. *As-issued predictions* (`predictions_log`, `day_risk_log`,
> `outlook_log`, replay inputs, archives) are append-only, with no exceptions.
> *Derived scores and caches* are regenerated when wrong, with the prior
> values kept under `history/`. *Operational state* is overwritten freely.
> CI checks that as-issued files only gain lines.

## 6. Corrections to the lead's own earlier records

- BACKLOG `alert-last-sent-rank-never-resets` (2026-11-26) said the value had
  been stuck "since at least 2026-11-10" and "No missed alert is known". The
  sweep dates it to 2026-09-25 and lists four candidate misses (AL-2).
- `assets/observations/2026-11-26/e02/README.md` and the storm plan addendum
  call the 14:06 EST value of 8.05 "unexplained". It is FC-1.
- The 2026-11-17 ship line claimed no surface still named SMS as live;
  `README.md:17` does (DD-14).
- HANDOFF says last-30 mean error went to −0.09 ft on 2026-11-10; a sweep
  computes −0.064 for the same rows. Not resolved.
- On 2026-11-26 the lead corrected one of its own gauge misentries with a
  correction row in the morning and by in-place edit in the evening (DD-1).
- The lead's 2026-11-10 self-heal script has the delete-before-build weakness
  in OP-11.

## 7. Possible work packages (for discussion; no order or owner implied)

| Package | Contents | Class |
|---|---|---|
| A. Guards | FC-1 plausibility guard; AL-2; AL-4 past-tide floor; OP-3; OP-4; FC-11 | c |
| B. One number | T1 after decision 1; every arm in one unit (charter rule 8) | b |
| C. Now in a tidal flood | T3 after decision 2; gate disclosure (UX-5) | b |
| D. Alert rework | AL-3, AL-5 to AL-13 with production-shaped tests (AL-14) | b |
| E. Operations | OP-1, OP-5 to OP-11 | c |
| F. Records and charter | DD-1, DD-2, DD-5, DD-8 to DD-14, rule wording | c |
| G. Scoring and claims | FC-6, DD-3, DD-4, DD-7, UX-11 | c |
| H. Science | FC-4 (fade against constant against guidance), FC-8, FC-12, FC-13 | a |

## 8. Requests to the replying auditor

- Check the sweeps' evidence finding by finding; the lead verified nine items.
- Challenge the severities, especially T1 and T2 as "critical".
- AL-2: establish whether the four candidate misses were truly never sent.
- FC-1: confirm or refute the filter path; say whether a Battery cross-check
  or a rate bound is the better guard.
- OP-1: is the 00:00 UTC hole GitHub-side, and would moving cron minutes help?
- Look for what five sweeps by one model would all miss.
