# Round 12 — ship verification for audit 2026-09-27-a1

Author: Claude Fable 5.1 ("Curlew"). Date: 2026-09-28 02:55Z (2026-09-27
22:55 EDT). Ship authorized by Codex round 11
(`11-candidate-approval-codex.md`, candidate `6e9fe57cb`); owner
authorization: BACKLOG DECISION `sofar-line-empirical-wins` (2026-09-27
18:20/18:24). Attribution: implementation and this record by Claude Fable 5.1
("Curlew"); independent review rounds 05/07/09/11 by Codex (GPT-6).

## Ship record

| Step | Result |
|---|---|
| Merge then-current main | `87511aab5` merges `origin/main` (`d3cd2b92b`, 36 newer commits: bot publishes, live e02 rows, Codex rounds 09/11) into the candidate; BACKLOG ledger union, Codex's open-loop text kept, HANDOFF taken from main and rewritten; registry checker clean (31 episodes, 270 rows, 0 pending) |
| Tests / gate on the combined tree | 443 tests OK, one skip; `check_artifacts.py` clean; three frozen replays PASS; seven frozen wind hashes match (verified before merge on identical code) |
| Regenerate pages | `flood_forecast_daily.py --write-html --write-json --no-send` on the merged tree at 02:46:31Z; no alert sent (quiet hours held; nowcast inactive); local-run ledger appends NOT committed (docs only, as `10ea6c2a2`); gate clean; landing carries the bay-not-street note and `SO FAR: MEASURED +25.2″ at 09:44 (tape, severe)`; details carries both corrected sentences |
| Commit → gate → push | ship commit `c2569c07a` (2026-09-28T02:47:16Z), main fast-forwarded, pushed on the first attempt (no rebase needed) |
| CI | run 36371161800 on `c2569c07a`: success |
| Pages | run 36371161755: success; live by 02:50:21Z |
| Live site | `barnacle-widget.js` serves `WIDGET_VERSION = "v7.32a"`; `index.html` carries "measured BAY level, not measured street water" and no "true observation"; `forecast.json` generated 02:46:31Z with `today_lookback.evidence = measured`, +25.2 in at 09:44 (the pre-ship line had shown the phantom modeled +39.0 at 02:40) |
| Rejected day max | At write time (02:55Z) the latest published nowcast was still the pre-merge run 2026-09-28T02:38:13Z (day max 39.0 @ 2026-09-27T06:40:00Z); the first post-merge nowcast run will apply the rejection. The line's local-midnight rollover (04:00Z) retires the value regardless. Recorded in `data/nowcast_daymax_rejections.json` (`cutover`). |
| Widget native layout | **PENDING, owner-only**: John re-copies the DEPLOYED v7.32a and checks the medium widget with a long quoted report and a model-claim clause. Not claimed. |
| Alert-transport path | Ship verification only; the exit-75 / receipt path has not been exercised by a real transport outage. |

## What is live now

Evidence-class "so far today" line with quoted reports and verified-labeled
model claims on site, email and widget; per-episode measured peaks on the
all-pathways chart; station-time/UTC tape window; offset-bearing ledger
appends; day-max provenance and the operator rejection record; sanitized
delivery health and the exit-75 + receipt publication contract in the
hourly workflow; corrected landing/details wording; the event analysis
artifacts (raw gauge archive, QC, rain scenarios, interval sidecar with
bases, corrected hydrographs); PLAYBOOK three-clocks rule and handoff
checklist.

## Status

Implementation audit 2026-09-27-a1: **shipped and verified, with one
owner-only check pending** (widget native layout). Retained follow-ups stay
OPEN in BACKLOG and are not closed by this record: gate-transfer physics,
high-base tank behavior, verified-vs-as-seen NOAA series, photos, the
historical census/hindcasts, Heron's episode-aware as-issued evaluation,
and the new `landmark-relation-bounds` item (John's 22:44 rule that field
reports are quantitative; bands from the survey, e.g. 4.14–4.16 ft for
"over the upstream-grate sidewalk, not over the walkway curb"). The
four-window study ends at Sep 27 AM; the Sep 27 evening episode e02 is
registered on main through its 18:33 row and is not covered by it.
