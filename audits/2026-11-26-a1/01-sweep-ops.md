<!-- audits/2026-11-26-a1 supporting file for 01-full-audit-claude-fable-5-2.md -->
> **Sweep report: operations and infrastructure (finding IDs OP-n).** Written 2026-11-26 by a read-only
> subagent of the lead auditor's session (Claude Fable 5.2), filed unedited except
> that scratch paths were rewritten to `audits/2026-11-26-a1/01-probes/ops/` (scripts only; large
> data dumps were not committed) and, in the records sweep, one line of personal
> context was redacted. It is evidence for report 01, not an independent review:
> the lead re-checked only the items listed in report 01's verification table.

# Ops / infrastructure audit slice (agent-ops), 2026-11-26-a1

Basis: `~/.barnacle/repo` at `bbbf5678b` (= origin/main at 2026-11-27 03:10Z), the working clone at `ab7e41c59`, `gh` API reads at about 03:15–03:40Z, and `~/.barnacle/logs`. All times are UTC unless marked; git statistics use committer dates. Nothing in the repo, `~/.barnacle` or LaunchAgents was modified. Scratch scripts and raw run JSON are in `audits/2026-11-26-a1/01-probes/ops/` (`gaps.py`, `runs.py`, `pages.py`, `runs_*.json`, `logutc.txt`).

Test suite: `BARNACLE_REQUIRE_GRIB=1 ~/.barnacle/venv/bin/python -m unittest discover -s tests -q` ran 511 tests, OK, 1 skipped (`test_wind_shadow ... R5_Q1`, "local training re-pull not present"); tree status unchanged. `bash -n` is clean on all four `bin/*.sh` and `forecast/smoke_test.sh`.

## Findings (ranked)

### OP-1. Daily 00:00 UTC schedule hole on GitHub; the local arm computes through it but discards, and cannot dispatch alerts (answers K4)
- **Severity: high.** Every evening 18:55–19:35 EST (19:55–20:35 EDT) there is no GitHub nowcast run and no alert-dispatch check for 35–40 min. On 2026-11-26 the hole contained the evening flood onset (HANDOFF: first owner reading 19:16 EST = 00:16Z).
- **Evidence (MEASURED):**
  - Nowcast run starts, last 1000 runs (2026-11-19 08:44Z to 11-27 02:54Z): median gap 9.8 min, p90 17.8, p99 27.0, max 40.1; 1000 of 1117 nominal slots ran (89.5%).
  - All 8 midnights in the window show the same gap, 23:55Z to 00:30–00:35Z (35.0–40.1 min). The 00Z hour averages 2.8 runs against a nominal 6. Of 13 gaps over 25 min, 8 start in hour 23 and 5 in hour 05.
  - Hourly forecast, 998 scheduled runs since 10-16: start minute at 00Z is median :22, max :34; other hours are median :06–:14. The 8 largest hourly commit gaps in 14 days (74–79 min) are all the 23:07 to 00:2x slot.
  - No hour was missed in the last 14 days (336 of 336). Two clock hours had no scheduled start in 41 days (10-26 12Z, 11-01 08Z); the warm job dropped the same slots, so these look GitHub-side.
  - 2026-11-26: GitHub nowcast commits at 23:55:40Z then 00:33:31Z; hourly at 23:07:24Z then 00:21:08Z. Nobody covered it: `~/.barnacle/logs/tick-status.jsonl` shows local ticks at 00:08:14, 00:18:36, 00:29:01 and 00:39:22Z, all `gated-quiet quiet-publication-coalesced`.
  - Cause of the discard (READ): `bin/local_nowcast_tick.sh:110-114` publishes only when radar `active` or the hourly quiet row is due, while the GitHub arm publishes every run once triggered. The local arm has no dispatch path (`.github/workflows/nowcast.yml:168-173` comment).
  - All 1000 nowcast runs are `event=schedule`, so the external trigger in `history/plans/external-trigger-scheduler.md` is not deployed.
- **Commands:** `gh run list --workflow nowcast.yml --limit 1000 --json ...` then `runs.py`; `TZ=UTC git log --since=2026-10-20 --date=format-local:... --format='%h|%cd|%an|%s'` then `gaps.py`.
- **Confidence:** high on the numbers; the cause (GitHub top-of-day congestion) is inferred.
- **Fix direction:** have the local arm publish every tick while the trigger condition holds or the GitHub arm's last heartbeat is over 15 min old, and/or fire `workflow_dispatch` from an off-GitHub scheduler (dispatch bypasses the schedule queue).

### OP-2. Alert sent-state and the daily cap reach origin only through the artifact commit, after the gate
- **Severity: high** (latent). If the gate or push fails while risk is alertable, each hourly run would re-send ntfy and email, with the cap not counting.
- **Evidence (READ; INFERRED consequence):**
  - Delivery happens inside "Run forecast" (`.github/workflows/daily_forecast.yml:77-121`; `forecast/flood_forecast_daily.py:8795-8846`), which writes `data/alert_state.json` locally.
  - "Publish gate" (`:174-175`) and commit/push (`:177-215`) come afterwards; a failure in either discards the state. The next run checks out the old state and re-evaluates.
  - `_refresh_alert_state_from_origin` (`flood_forecast_daily.py:5493-5530`) only helps when the state reached origin.
  - `ALERT_DAILY_CAP = 2` (`:4687`) counts in the same file (`:5111-5141`).
  - Precedents: `BACKLOG.md:654` (2026-09-13, deliver then failed push then duplicate texts) and `BACKLOG.md:692` (42 consecutive gate failures, 2026-09-19 to 09-20).
- **Confidence:** medium-high on the mechanism. I found no evidence it fired during the September outage.
- **Fix direction:** push alert state on its own (state-only commit with retries, or a store outside the artifact commit) immediately after delivery and before the artifact gate.

### OP-3. Any earlier failure in the nowcast workflow skips both alert-dispatch checks, and the whole-tree gate couples them to human-edited ledgers
- **Severity: medium-high.** A ledger typo pushed mid-flood, a PyPI hiccup, a nowcast crash, three lost pushes or a job timeout silently removes the fast alert path until the hourly run.
- **Evidence:**
  - READ: steps `adc`, `rac` and `dispatch` (`nowcast.yml:155-206`) have no `if:`, so they default to `success()`.
  - MEASURED: run 38210645130 (2026-10-12) shows "Commit nowcast.json" failed and all three dispatch steps `skipped`.
  - The 2026-11-17 fix covers only the `docs/nowcast.json` rebase conflict (`nowcast.yml:131-135`). Lines 137 and 142 still `exit 1` before dispatch.
  - `forecast/check_artifacts.py:700-768` validates the whole tree (`data/labeled_observations.csv`, `forecast.json`, every HTML surface) and runs in the nowcast workflow (`:93`, `:139`) and the local tick (`local_nowcast_tick.sh:105,138`). There is no branch protection (`gh api .../branches/main/protection` returns 404), so CI reports a bad push only afterwards.
  - Local log: one `artifact-gate-failed` (October). Since 09-28: 16 nowcast failures and 2 forecast failures, including 10-05 "job was not acquired by Runner" and 11-09 "workflow file issue".
- **Confidence:** high.
- **Fix direction:** run the dispatch checks under `if: ${{ !cancelled() }}`, and scope the nowcast arms' gate to the files they write.

### OP-4. A crash in a dispatch check is treated as "nothing to dispatch" and the run stays green
- **Severity: medium.** A broken alert check would be invisible.
- **Evidence (READ):** `nowcast.yml:157-165` and `:176-184` map every non-zero exit to `dispatch=false`. The trigger step, by contrast, separates 0, 3 and other codes (`:54-79`). `radar_alert_check` (`forecast/nowcast.py:632-676`) calls `ff.imminent_gate` at `:656-662` with no exception handling, so a traceback (exit 1) equals exit 3. The comment at `nowcast.yml:187-188` promises a red run only for API failure.
- **Confidence:** high.
- **Fix direction:** treat 3 as "no dispatch" and fail the step on anything else.

### OP-5. Pages uses the legacy branch build on every push; it exceeded the documented 10 builds/hour during the storm and failed deploys are not retried
- **Severity: medium.** Site and widget read `johnurban.github.io` only; a failed deploy leaves them stale until a later push happens to succeed.
- **Evidence (MEASURED):**
  - `gh api repos/JohnUrban/barnacle/pages` gives `build_type: legacy`, source `main:/docs`; there is no `docs/.nojekyll`.
  - Last 1000 `pages-build-deployment` runs (12.3 days): 970 success, 25 cancelled, 5 failed.
  - Failures are `Failed to create deployment (status: 500)`. Three in a row on 2026-11-25 (15:42, 16:11, 16:17Z) left no successful deploy from 15:13:44Z to 16:35:11Z (81 min). The watchdog pages only past 130 min (`bin/public_health_watchdog.py:48`).
  - Builds per clock hour: median 3, max 13 (2026-11-27 02Z); max 17 in a rolling 60 min. Create-to-done: median 51 s, p99 93 s, max 369 s.
  - Data-only commits (heartbeats, guidance) also trigger a full build.
- **Confidence:** high on the measurements. Whether GitHub enforces the soft limit is unknown.
- **Fix direction:** deploy with a custom Pages workflow filtered to `docs/**` with retry, or at least add `.nojekyll` and stop data-only commits from building.

### OP-6. The requirement "locks" pin only four top-level packages; transitive versions float, and the two arms run different interpreters
- **Severity: medium.** An upstream release can change or break production with no commit and no CI run.
- **Evidence:**
  - READ: `forecast/requirements.txt` and `forecast/nowcast-requirements.txt` pin xarray, cfgrib, eccodes and matplotlib, with no hashes and no transitive pins.
  - MEASURED drift between the two local builds (`~/.barnacle/logs/venv-packages-20261110T134239Z.txt` against `pip list` today): eccodeslib 2.48.0.26 to 2.50.0.34 (the native GRIB decoder), eckitlib 2.1.1 to 2.5.0, numpy 2.5.1 to 2.5.4, pandas 3.0.5 to 3.1.1, pillow 12.3.0 to 13.0.0, python-dateutil 2.9.0 to 4.0.0.
  - GitHub re-resolves on every run (`daily_forecast.yml:49` with no cache, `nowcast.yml:83`), so PyPI is a hard dependency of every forecast.
  - CI runs only on push or PR (`ci.yml:7-9`), with no schedule.
  - The local arm runs Python 3.15.2; GitHub and CI run 3.11.
- **Confidence:** high on the facts. I could not check for yanked or vulnerable versions offline.
- **Fix direction:** a fully hashed lock installed with `--require-hashes`, pip cache on the hourly job, and a scheduled CI run.

### OP-7. Every run checks out the full 410 MB tree (301 MB of photos) under 5- and 6-minute job timeouts
- **Severity: medium.** A slow checkout alone nearly killed an hourly run.
- **Evidence (MEASURED):**
  - Tracked tree by `git ls-tree -r -l HEAD`: assets 301.5 MB, docs 65.1 MB, data 35.1 MB.
  - Run 41718729878 (2026-11-03 21:06Z): "Checkout repo" took 222 s and the job 270 s against `timeout-minutes: 5`. The two runs before it took 167 s and 207 s. Typical checkout is 10 s.
  - Assets added 91.3 MB in November alone.
- **Confidence:** high.
- **Fix direction:** sparse checkout that excludes `assets/` (and `history/`, `audits/`) in the three production workflows.

### OP-8. The first local tick after the Mac wakes publishes a degraded nowcast over production; the adopt-on-conflict path ignores quality
- **Severity: medium-low.** Opening the laptop during a storm can replace a good active nowcast with "radar unavailable" until the next GitHub run, and a degraded file never dispatches.
- **Evidence:**
  - MEASURED: both degraded local rows in `data/nowcast_heartbeats.csv` are the first tick after a sleep gap. 2026-11-15T07:16:04Z ("MRMS newest frame is 11.9 min in the future", after a 306-min gap) and 2026-11-24T13:03:46Z ("The read operation timed out", after 578 min). Ledger rows exist only for published ticks.
  - READ: they publish because the quiet row is always due after a long gap (`local_nowcast_tick.sh:96-114`). `nowcast.yml:131-135` adopts the other arm's file unconditionally.
- **Confidence:** medium. The clock explanation for the 11.9 min is a guess.
- **Fix direction:** do not publish a degraded result when origin's file is newer and ok (or retry once after wake), and prefer ok/active over degraded on adoption.

### OP-9. In quiet weather only the laptop refreshes `docs/nowcast.json`
- **Severity: medium-low.** "Quiet" and "stale" are indistinguishable on the public file whenever the Mac sleeps.
- **Evidence:**
  - READ: the GitHub quiet path writes only the CSV row (`nowcast.yml:59-73`, `:104-110`). The docstring at `forecast/nowcast.py:14-16` says the JSON gets a fresh heartbeat.
  - MEASURED (`git log -- docs/nowcast.json`, 30 days): gaps of 64.2 h, 57.3 h and 35.0 h during the 11-03 to 11-10 outage; since 11-10, 15 gaps over 2 h and 8 over 5 h, max 11.1 h.
  - The watchdog tolerates 26 h (`public_health_watchdog.py:60`).
- **Confidence:** high on the facts. How the site and widget render an old inactive file belongs to the display slice.
- **Fix direction:** have the GitHub quiet heartbeat also rewrite a minimal inactive `nowcast.json`, or point consumers at the ledger.

### OP-10. Watchdog: same laptop, does not watch the local arm, treats unavailable radar as quiet, and logs no proof of a page (deepens K1)
- **Severity: medium.** The one independent observer is absent about a fifth of the time and blind to several failure classes.
- **Evidence:**
  - MEASURED from `~/.barnacle/logs/watchdog.log*`, last 30 days: 2265 of 2892 expected ticks; 21.1% of wall time uncovered; max gap 812 min. The Mac is a MacBook Pro, on battery when checked.
  - Local tick coverage since the 11-10 fix: 1772 of 2384 slots; 23.0% of wall time with no tick; longest 664 min. Only 2 failures since (two rebase conflicts on 11-13).
  - 30-day heartbeat ledger: local arm has 44 gaps over 90 min, including the 168.6 h outage; GitHub arm since 11-10 has a max of 86 min (the OP-1 hole). Either arm: 3850, 3440 and 2098 min gaps, all before the 11-10 fixes, and none over 90 min since.
  - READ: `bin/watchdog_tick.sh:28` passes no `--require-arm`. Radar quality is checked only when `active` (`public_health_watchdog.py:64-70`). `_notify` prints nothing on success (`:119-158`). The script runs under `/usr/bin/env python3`, which is Apple's 3.9.6 under launchd, while CI tests it on 3.11. No installer writes `com.barnacle.watchdog.plist` (hand-installed 2026-09-14).
  - The log has 157 UNHEALTHY ticks ("nowcast artifact is N minutes old") from 11-04 to 11-10.
- **Confidence:** high on the facts.
- **Fix direction:** move the watchdog to an always-on host, add `--require-arm local-launchd` or the proposed hour-of-failures page, log each send, and send a periodic self-test page.

### OP-11. `ensure_local_venv.sh` deletes the working environment before it builds the replacement
- **Severity: low-medium.** A requirements edit that coincides with a PyPI or wheel problem takes the local arm down, silently.
- **Evidence (READ):** `bin/ensure_local_venv.sh:85` runs `rm -rf` before `venv` and `pip` (`:86-98`). Readiness is a content hash of both requirement files (`:37-52`), so even a comment edit triggers a rebuild within 10 minutes. `pick_python` (`:54-65`) takes whatever Homebrew's `python3` is (3.15.2 today), with a floor of 3.11 and no ceiling. Retries are hourly (`local_nowcast_tick.sh:77-89`). `venv_ready` tests only `import sys`.
- **Confidence:** high on the code; no occurrence observed.
- **Fix direction:** build into a sibling directory and swap on success; cap or pin the base interpreter.

### OP-12. No retries on any upstream fetch; worst-case timeouts exceed the job budgets
- **Severity: low-medium.** A hanging (not failing) NOAA, NWS or MRMS endpoint cancels the job instead of degrading the input.
- **Evidence:**
  - READ: `_get` has `timeout=30`, no retry, 18 call sites (`flood_forecast_daily.py:283-288`) against a 300 s job. The nowcast fetches about 11 frames at 30 s each plus listing and gauge (`forecast/nowcast.py:369-412`, `:442-449`) against 360 s.
  - INFERRED: 18 × 30 s and 11 × 30 s exceed those budgets.
  - MEASURED: no `timed_out` run since 09-28; 4 degraded heartbeat rows of 1071 in 30 days; typical forecast step 35 s, nowcast step 27 s.
- **Confidence:** medium (arithmetic, not an observed kill).
- **Fix direction:** one bounded retry per fetch and a total wall-clock budget inside each script.

### OP-13. Repository growth is fine today; local clones carry heavy loose-object churn
- **Severity: low.** Clones and checkouts slow down over the next year.
- **Evidence (MEASURED):**
  - GitHub size 392,554 KB. 8,389 commits since 2026-05-18; 82 per day over the last 14 days, 98% from bots.
  - Bot churn is about 7.3–7.6 GiB/month of raw blobs. `data/wind_shadow/2026-11.jsonl` is 9.6 MB and rewritten hourly. This packs to roughly 22 MiB/month (the fully packed October figure).
  - Assets average about 46 MB/month.
  - `docs/archive` is 48.7 MB, growing about 13.7 MB/month. `docs/tides` is 11.7 MB in 1,126 files. `data/replay_inputs` is 6.3 MB.
  - `.git` is 521 MB in the working clone and 804 MB in `~/.barnacle/repo` (393 MiB loose).
  - INFERRED: about 1 GB on GitHub in 9–10 months. The published site (65 MB) is years from the 1 GB Pages limit. No file exceeds 10 MB.
- **Fix direction:** OP-7's sparse checkout; consider moving photos out of the main history; occasional `git gc` on the local clones.

### OP-14. The daily archive depends on the 09Z run starting before 10:00Z
- **Severity: low.** A dropped or hour-late slot silently loses that day's snapshot.
- **Evidence:** READ: `daily_forecast.yml:59-65` reads the hour at run time. MEASURED: 9 missing days in `docs/archive` (06-15, 06-16, 06-22, 07-20, 08-27, 08-28, 09-13, 09-19, 09-20), none in the last 60 days. The 09Z start minute is median :09, max :20 over 41 days; another hour started at :60.
- **Fix direction:** archive when today's file is missing, not when the hour equals 09.

### OP-15. Hygiene bundle
- **Severity: low.**
- **Stray files:** untracked `del` at the repo root is a 548-byte muffin recipe, unrelated to the project. `.claude/worktrees/` is empty. One of 9 git worktrees is prunable (`/private/tmp/barnacle-audit-20260914.*`).
- **Addresses in a public repo (file and line only):**
  - One gmail address used as a User-Agent contact: `forecast/nowcast.py:55`, `assets/observations/2026-09-27/analysis/fetch_event_gauges.py:24`, and ten `history/scripts/*.py` files.
  - Three other gmail local parts: `attic/HANDOFF-through-2026-08-03.md:96,536,637,2058`; `attic/superseded_handoffs/deploy_HANDOFF.md:69-97`; `attic/dev_pre_v0.5_reorg_20260518/.../HANDOFF_deploy_script.md:69-97`; `.../flood_forecast_README.md:32-35`. I did not judge whether these are real or placeholders.
  - A `highlandsnj.gov` address appears 9 times.
  - No phone-like strings found. The watchdog topic string is not in the tree or history.
- **Secrets and permissions:** `ALERT_SMS_TO` is still stored and passed (`daily_forecast.yml:89`) though SMS is retired. `~/.barnacle/watchdog_topic` is mode 0644. The local arm pushes with the owner's keychain credential. `nowcast.yml:195` puts the token in a curl argument.
- **Logs:** `tick.log` (431 KB) and `launchd.log` (370 KB) have no rotation and no timestamps; growth is under 3 MB a year. `tick-status.jsonl` and `watchdog.log` rotate to one generation.
- **Other:** no dependabot config for the SHA pins.

## Checked and found sound
- Both actions are SHA-pinned and the SHAs match the tags (`actions/checkout` v7.0.1, `actions/setup-python` v6.3.0, verified by `gh api .../git/ref/tags/...`).
- Default token permission is read; each workflow declares the minimum it needs. Only the forecast job receives secrets.
- All four workflows have concurrency groups. Production groups never cancel in progress. CI cancels per ref, and every cancelled human-commit run was superseded by a later run on a newer head.
- `data/nowcast_heartbeats.csv` is union-merged (`.gitattributes`). Local rebase conflicts: 4 in 8,647 logged ticks; 1,205 pushes on the first attempt, 15 on the second, 1 on the third.
- The local tick resets to origin every run, so the clone cannot stay diverged. Stale-lock recovery is present, and there were zero `active-lock` skips in the whole log.
- `publish_decision.py` and the exit-75 path fail closed on any other non-zero code.
- The warm job runs a median 526 s, max 833 s, against a 20-minute timeout, with no failures in 518 runs.
- Hourly job duration is median 48 s, p90 74 s. The nowcast job is median 21 s, max 73 s.
- No tracked file matches an ignore rule.
- K3's adopt-on-conflict path matches its description and is covered by `tests/test_workflow_contracts.py`.

## Could not determine
- Whether the roughly 6-hourly ntfy pages implied by the 157 UNHEALTHY watchdog ticks of 11-04 to 11-10 were sent or seen. The state file keeps only the last send (2026-11-10T11:53:15Z) and the log records no sends.
- Why GitHub delays the 00:00 UTC slots, and whether moving cron minutes would help. Only the pattern is measured.
- Whether GitHub enforces the Pages 10 builds/hour soft limit or the 60-day inactivity disable against bot-only activity. The longest gap between human commits was 43 days (09-28 to 11-10) and schedules kept running.
- Which transitive versions the GitHub arm resolves; pip is `--quiet` in the logs.
- Whether OP-2 has ever fired from a gate failure, as opposed to the documented push failure.
- shellcheck and actionlint are not installed locally (K2 unchanged).
- A privacy hook blocked shell greps that named `forecast/nowcast.py`, so that file was read directly, not grepped.
