<!-- audits/2026-11-26-a1 supporting file for 01-full-audit-claude-fable-5-2.md -->
> **Sweep report: alerting and the live radar nowcast (finding IDs AL-n).** Written 2026-11-26 by a read-only
> subagent of the lead auditor's session (Claude Fable 5.2), filed unedited except
> that scratch paths were rewritten to `audits/2026-11-26-a1/01-probes/alerts/` (scripts only; large
> data dumps were not committed) and, in the records sweep, one line of personal
> context was redacted. It is evidence for report 01, not an independent review:
> the lead re-checked only the items listed in report 01's verification table.

# Alerting and live radar nowcast: findings (auditor slice AL)

Read-only audit at HEAD `ab7e41c59` (2026-11-26 22:07 EST). Nothing in the repo was touched: `git status` still shows only the existing `?? del`, and the suite passes (511 tests, 1 skipped).

Reproduction scripts and extracted history are in `audits/2026-11-26-a1/01-probes/alerts/`:
- `repro.py` … `repro6.py`: pure-function calls with synthetic inputs (R-numbers below refer to their printed sections). Run with `~/.barnacle/venv/bin/python -B <script>`.
- `state_all.json`: all 3,040 committed versions of `data/alert_state.json`; `analyze_state.py` and `analyze_sends.py` produce the history counts.
- `nowcast_history.txt`: every `docs/nowcast.json` commit from 2026-11-26 12:00Z.

Send counts come from committed state, so a send whose state commit never landed is invisible; treat counts as lower bounds. `ff` = `forecast/flood_forecast_daily.py`, `nc` = `forecast/nowcast.py`.

## Ranked findings

### AL-1. Street estimate and imminent rail are gated on rain above 0.30 in/hr; a tidal flood publishes nothing (K3 root cause)
**Severity: high.** A tide-driven flood gets no live street level and no imminent push; on 2026-11-26 the morning flood got none and the evening push came only when rain crossed the threshold.

- **Cause.** `nc:519-520`: `drain = PLUVIAL_DRAIN_RATE * min(1, max(0, (3.52 - bay)/0.52))` then `active = recent_max > max(0.3, drain)`. `PLUVIAL_DRAIN_RATE` is 0.25 (`ff:4276`), so `max(0.3, drain)` is always 0.3 and the drain term is dead.
- **What is skipped.** Everything that computes a street level sits inside `if active:` (`nc:532-598`), including `base_stage = max(0, (bay - 3.52)*12)` at `nc:534`. When inactive the payload has no `street_now_in`, `peak_proj_in` or `trend`.
- **Why no alert.** `_nowcast_contract_reason` returns "nowcast inactive" (`ff:4735-4736`), which stops both the imminent gate (`ff:5413-5416`) and the base radar pathway (`ff:4764`).
- **By design?** Yes for tide-only: the `evaluate_sms_gate` docstring says "v1 scope: nowcast-driven only" (`ff:5399-5401`), and there is no bay-keyed trigger anywhere.
- **Evening history.** All 24 payloads from `712c8cc43` (22:11:51Z) to `1232d2ad6` (01:47:04Z) have `active: false`, `radar_quality: ok`, `bay_source: observed`, no `error`, `recent_max_in_hr` 0.14–0.27, and bay rising 2.107 → 6.293. First `active: true` is `d46b9c1d0` (01:55:16Z, `recent_max` 0.32, `street_now_in` 33.5). The forecast run generated at 01:56:12Z and delivered at 01:56:36Z.
- **Morning flood.** Never active (`caa5f5980` 14:14Z: bay 5.434, rain 0.07), so no imminent push and no day-max.
- **The first value was the bay, labelled radar.** Of the +33.5 in, bay head alone is 32.9 in; the push read `[342 Bay] STREET FLOODING PORCH-STEP LEVEL: +34" now, bay over grates. 8:56PM`, titled "LIVE radar: …". It skipped class 1 and 2 entirely.
- **The gate also hides the tank's own answer.** With the drain tide-locked at bay 3.52 and steady 0.27 in/hr, the production tank arithmetic gives 9.4 in (over the 7.68 in curb) while the gate says inactive (`repro5.py`).
- **Caveat for any fix.** Bay head crossed curb at 23:45Z (`bb00c065a`, 4.189), lawn step by 00:33Z, porch by 00:49Z, but the owner logged "not above the curb" at 19:16 EST. A bay-keyed rule would have fired early, consistent with the closed-gate note in HANDOFF.

Verified: REPRODUCED (`repro2.py` R9, R11; `repro5.py`) plus READ of the 24 commits. Confidence: high.
Fix direction: separate "is there a street estimate" from "is rain exceeding the drain" (compute the stage whenever bay ≥ 3.52 or the tank holds volume); decide separately whether a tidal imminent rule may alert while the gate question is open.

### AL-2. `last_sent_rank` ratchet (K1): introduced 2026-09-14, locked at 4 since 2026-09-25, with real missed escalations
**Severity: high.** A risk already alerted at a low level and later upgraded sends nothing.

- **Cause.** `ff:5154-5155` stores `max(st.last_sent_rank, decision.rank)`. Commit `cdaaf2d98` (2026-09-14, "Audit a1 phase 1") changed it from `decision["rank"]`, apparently to merge partial retries, but the max is applied whether or not it is the same event. Nothing resets it.
- **History.** Before that commit the value moved both ways; it reached 4 at `b596ebb5a` (2026-09-25T11:11Z) and has not dropped since. The BACKLOG's "since at least 2026-11-10" understates this.
- **Effects.** `escalation` (`ff:5017`) is dead. The cooldown test `rank <= last_rank` (`ff:5050`) is always true, so its log text "a higher rank would send immediately" is false (R16).
- **Real misses** (the storm plan says none are known):
  - 2026-10-10 20:12Z "rain risk possible" was sent; `813f7e9f6` (2026-10-11 04:15Z) went to "rain risk elevated" with signature `pluv` unchanged. No base alert followed; the imminent rail fired at 22:12Z, 18 h later.
  - 2026-11-05 14:08Z possible sent; `9599e8036` (22:07Z) elevated; never alerted.
  - `779136109` (2026-11-23 02:09 EST): the 06:01 tide went street → light four hours ahead; never alerted.
  - `9878a9140` (2026-09-23 08:18 EDT): light → moderate while the value was pinned at 3 by an unrelated rain alert.
- R1 shows a street → severe upgrade of one tide returns "steady (rank 4, was 1)"; the same input with `last_sent_rank=1` returns "alert escalated".

Verified: REPRODUCED (R1, R16) plus history. Confidence: high.
Fix direction: scope the stored rank to the current signature (max only when `same_event`), or reset at all-clear.

### AL-3. Signature changes when pathways tie or drop out, producing false "new event" sends that burn the daily cap
**Severity: high.** Duplicate and night alerts for unchanged risk; on 2026-09-27 the burned cap suppressed a real rain alert 91 minutes before street water.

- **Cause.** `ff:4929-4945` builds the signature only from pathways equal to the top rank, plus a radar bit carrying class and day. `new_event` is plain inequality with the last-sent signature (`ff:5022-5023`). The comment at `ff:4926-4928` claims de-escalation cannot look like a new event; it can.
- **Production cases** (each a base send; "composition-only" list in `analyze_sends.py`):
  - `0311518eb`, 2026-11-07 00:07 EST: `tide:…06:00|pluv` → `tide:…06:00`, rank 1, sent just after the cap reset at midnight (R4).
  - `963e19614`, 2026-09-27 07:10 EDT: radar bit dropped, same severe tide re-alerted; this was that day's second send.
  - `65ecb3480`, 2026-11-13 07:11 EST, and `7199ead9d`, 2026-11-22 07:10 EST: the same pattern.
  - `d0d288a58`, 2026-11-12 19:21 EST: radar class severe → street sent as a new rank-1 event an hour after the severe alert.
- **Borderline-tide flapping.** A tide crossing the dry/street line moves the signature between tides: 2026-10-21 to 10-29 had two rank-1 alerts on most days. Since 2026-09-25, 40 of 55 base sends were rank 1, and 21 of 34 send-days hit the cap.
- **Cap consequence.** On 2026-09-27 "rain risk elevated" appeared at 17:10 EDT (`4bf57ce8b`) with the cap at 2/2; it was suppressed, then held by quiet hours, and never sent. The imminent rail fired at 18:41 EDT (`bf58db98a`).
- R14 shows a radar drop-out after a radar-tagged send returns "alert new event: rank 4→4".

Verified: REPRODUCED (R4, R14) plus history. Confidence: high.
Fix direction: key the event on a stable identity (tide time, NWS event and onset, radar episode) and treat removal of a component or a rank drop as no event.

### AL-4. Tide signature is the first top-rank tide, with no lower time bound (K2 root cause and siblings)
**Severity: medium-high.** Later same-rank tides are alerted late, and tides already past can be alerted.

- **Cause.** `ff:4881-4886` uses strict `>`, so the first tide at the top rank wins. `_alert_window_tides` (`ff:4783-4786`) keeps `hours_from_now <= 48` with no floor, and the table holds tides for 2 h after peak (`PAST_TIDE_VISIBILITY_HOURS`, `ff:317`, `ff:397`).
- **This storm.** The 21:07 tide was forecast severe from the 2026-11-24 13:08Z run (8.40 ft, higher than the morning's 8.10) and entered the 48 h window at 2026-11-24 21:07 EST. Its first ntfy alert was `c712c8365`, 2026-11-26 11:09 EST.
- **Alerts for past tides.** `4d6e5fe18` sent "street tide 2026-10-25 07:29" at 08:15 EDT (`hours_from_now` −0.78). `6fdc9e9ab` sent the 08:09 tide at 09:41 EDT (−1.54). The text reads "street tide flooding Sun 7:29 AM (6.37 ft)" as if upcoming (R3). Both tides were reclassified dry → street after their peak.
- **One alert at the window edge.** A steady forecast is alerted once, when the tide enters the window: the 2026-11-26 morning tide was alerted only at 2026-11-24 09:08 EST, 47.3 h ahead, with nothing day-of. Reminders are an owner policy question.

Verified: REPRODUCED (R2, R3) plus history. Confidence: high.
Fix direction: exclude `hours_from_now < 0` from alert rank and signature; evaluate "new event" per tide.

### AL-5. Quiet hours ignore severity and lead time (K4 answers)
**Severity: medium.** A severe tide just after 07:00 gets little or no notice.

- **Severe tide at 09:23 first seen at 22:00.** `_night_urgent` (`ff:4968-4998`) exempts only a "LIVE radar" label, a tide between now and the next 07:00, or any active NWS warning. The alert is held at 22:00 and 06:59 and sent at 07:08, about 2 h 15 m ahead. A tide at 07:10 is sent at about 07:08; a tide at 06:50 is sent at 22:00 (R6).
- **Precedent.** `21bd9ea57`: a moderate 09:15 tide, top-ranked from 04:23 EDT on 2026-09-28, was sent at 07:12 EDT.
- **Rain is never "tonight".** "Rain risk elevated" is held unless a warning is active: 2026-10-15 20:30 → 2026-10-16 07:11 EDT (11 runs held).
- **A third alert on 2026-11-26.** The two slots went at 11:09 EST (evening tide) and 20:56 EST (radar bit added, concurrent with the imminent push). After that (R12):
  - Same-tide escalation: never, because of AL-2; the cap is not even reached.
  - A new Flash Flood Warning: masked while the severe tide tops the table (AL-7). After the tide leaves, "daily cap reached" until local midnight, then sent at about 00:08 because a warning passes quiet hours.
  - Tomorrow's 09:23 tide: held by quiet hours, sent about 07:08 on 2026-11-27 (it is forecast "street").
- The imminent rail is exempt from both, but its top class was already sent, so it re-arms only after 6 h.

Verified: REPRODUCED (R6, R12) plus history. Confidence: high on behaviour; whether it is wrong is owner policy.
Fix direction: let rank and lead time enter the rule; consider a cap exemption for NWS warnings.

### AL-6. A held or capped alert survives only if its signature differs from the last one sent
**Severity: medium.** A rain-risk alert first seen during quiet hours can be dropped silently.

- **Cause.** On a no-send run `_main_core` calls `persist_alert_state(decision)` (`ff:8803-8808`), which writes the current `rank` (`ff:5101-5104`). That consumes `appearance` (`prev_rank == 0`, `ff:5016`). With AL-2, later delivery depends solely on `sig != last_sent_sig`.
- **Repeating signature.** Rain risk without an NWS alert is the constant `pluv` (sent six times: 09-20, 10-02, 10-10, 10-16, 11-05, 11-11).
- R7: last sent `pluv`, rank 0, elevated rain appears at 22:00 EST → "quiet hours: held"; 07:10 → "steady (rank 3, was 3)"; 13:10 → the same. The `_night_urgent` docstring ("delivers naturally after 07:00") is not true here.
- Not seen in production: each `pluv` episode so far followed a different signature.

Verified: REPRODUCED (R7). Confidence: high on mechanism.
Fix direction: record a held or suppressed decision explicitly (as `pending_base` does for transport failures).

### AL-7. A lower-ranked pathway is invisible to alerting, and a masked NWS alert re-dispatches the forecast every nowcast run
**Severity: medium.** A new Flash Flood Warning during a severe-tide window gets no base alert.

- **Cause.** `pluv` and NWS ids enter the signature only when `pl_rank == rank` (`ff:4936-4944`); pluvial rank tops out at 3 (`ff:4678`). Under a rank-4 tide or radar the signature and text (`ff:5570`) cannot change for any rain development. The window is long: 2026-11-24 09:08 → 2026-11-26 about 23:07 EST this week.
- **Dispatch side effect.** `alert_dispatch_check` (`nc:623-627`) tests `key not in sig`, so a masked alert returns 0 on every 10-minute run: R8 gives `[0, 0, 0]` on three consecutive calls and "steady (rank 4, was 4)" from the evaluator.
- Not observed in production: daily archives show no NWS inland alert under a higher tide rank, and no dispatch bursts this week.

Verified: REPRODUCED synthetically (R8). Confidence: high on mechanism, unobserved live.
Fix direction: sign every active pathway; compare the dispatch check against a list of ingested alert ids.

### AL-8. Alerts send before state is durable; a failed gate or push after the send repeats the alert hourly, uncapped
**Severity: medium.** Hourly duplicates for as long as publication fails.

- `daily_forecast.yml:77-115` runs the forecast step (send, then local state write). The publish gate is at `:174-175` and the commit/push at `:177-215`. Any failure there discards `alert_state.json`, including the cap counters.
- The next run starts from a fresh checkout; `_refresh_alert_state_from_origin` (`ff:5493-5545`) helps only if origin received the state. The code comment records one such duplicate on 2026-09-13.
- The gate validates hand-edited ledgers (`check_artifacts.py` `CSV_SCHEMAS`), which are edited most on event days.

Verified: READ only; not reproduced. Confidence: medium.
Fix direction: persist and push sent-markers in their own always-run step, or send after publication.

### AL-9. Base radar pathway: no curb floor, automatic night bypass, and a "new event" at local midnight
**Severity: medium.** Rank-1 night alerts for inches of modeled water.

- **No floor.** The comment says "CURRENT street water alerts from curb class up" (`ff:4892-4893`); the code ranks any `_eff > 0` (`ff:4910-4913`). +0.1 in over the grate is rank 1.
- **Night bypass.** Any "LIVE radar" label is urgent (`ff:4975-4976`). R13: `street_now_in=0.1` at 03:00 EST → "alert appeared: rank 0→1", while the imminent gate says "street below curb" for the same payload.
- **Midnight.** The radar bit carries `day_local` (`ff:4933-4935`). `29d97ddc8` sent `radar:2026-09-20:street` at 23:16 EDT and `972569dca` sent `radar:2026-09-21:street` at 00:15 EDT, both rank 1 (+4.9 and +5.2 in) (R5).

Verified: REPRODUCED (R5, R13) plus history. Confidence: high.
Fix direction: apply the curb floor to the base radar rank; key the radar episode on continuity, not calendar date.

### AL-10. Alert label prints a projection the policy rejects
**Severity: medium.** Title, subject and body can state a level that alerting itself refuses to use.

- `ff:4900` reads the raw `peak_proj_in`; `ff:4914-4916` prints it regardless of trend, although `nowcast_projected_peak` (`ff:4702-4713`) discards it when the trend is not rising.
- R10: `street_now_in=5.0`, `peak_proj_in=17.1`, trend falling → label "LIVE radar: street +5.0″ now → +17.1″ projected (street)" and text "FLOODING (radar): street +5.0″ now → +17.1″ projected (street). Verify on the site chart.." (double full stop).
- The imminent body correctly omits it (`ff:5471-5473`), so the ntfy title and body disagree.
- Real instance: `d0d288a58`, 2026-11-12 19:21 EST, label "street +6.8″ now → +13.7″ projected (street)" at rank 1.
- Stale comment at `ff:4905-4906` ("Missing trend … counts as rising").

Verified: REPRODUCED (R10). Confidence: high.
Fix direction: build the label from the same projection the rank uses.

### AL-11. Nowcast bay fallback ignores surge, and the alert contract ignores `bay_source`
**Severity: medium.** When the gauge head is stale mid-storm, the nowcast runs on a bay several feet too low.

- `current_bay` falls back to `_predicted_bay`, which calls `build_water_series(0.0, …)` (`nc:415-428`, `:456-463`). The spec confirms the zero-surge caller is deliberate (`model/v0.10.6.md:295`).
- `991ecc2ff` (2026-11-26 16:51Z): `bay_navd88 −0.269`, `astronomical-fallback-stale-gauge`. The forecast run 16 minutes later (`e8acc1164`) shows observed 3.321 at 11:30 and 2.668 at 12:00 EST with surge +2.94 ft. The error is about 3 ft. It was harmless then, because the drain is fully open below 3.0 either way.
- `_nowcast_contract_reason` (`ff:4729-4751`) never checks `bay_source`, so alerts are decided on the fallback bay.

Verified: READ plus the two commits. Confidence: high on the numbers.
Fix direction: reuse the forecast's surge-persistence state in the fallback; make a non-observed bay a contract condition or a visible caveat.

### AL-12. Email and ntfy can headline different tides (charter rule 8)
**Severity: low-medium.** ntfy-only recipients learned of the record evening tide two days after email readers.

- The alert label names the first top-rank tide within 48 h; the email subject and body also carry "WORST 72H".
- Rebuilt from the committed forecast for the 2026-11-24 09:08 EST send (`d174fdd39`, `repro3.py`, `repro4.py`):
  - Email subject: "[ALERT] severe tide 2026-11-26 08:28-05:00 | [342 Bay] TODAY NO FLOODING … | WORST 72H SEVERE: tide peak 8.40 ft at Thu 9:07 PM (Porch step 1 +2.9")".
  - ntfy body: "[Barnacle] ALERT: severe tide flooding Thu 8:28 AM (8.10 ft). Now: dry."
- When base and imminent fire together, ntfy carries only the imminent body (`ff:8322`), yet the base ntfy rail is acknowledged (`ff:5308`).
- Wording: the label leaks the storage stamp ("2026-11-26 08:28-05:00") into subject and title, and "(8.10 ft)" has no datum.

Verified: REPRODUCED from committed forecasts. Confidence: high.
Fix direction: one shared headline builder for label, subject and push.

### AL-13. `pending_base` retries bypass quiet hours and the cap, and never expire
**Severity: low.** After an evening transport failure, the retry can deliver at 03:00.

- `_base_channels_to_attempt` (`ff:5482-5490`) returns pending channels whenever the signature matches, whatever the hold decision.
- R15: failure at 19:10 EST; at 03:10 the decision is "quiet hours: held" but both channels are still attempted; on success `base_sends_today` stays empty.
- `started_ts` is stored but never read, so a persistently failing rail retries hourly with exit 75.

Verified: REPRODUCED (R15). Confidence: high.
Fix direction: apply the hold rules to retries and add an expiry.

### AL-14. Tests pass around the defects
**Severity: medium.** The suite gives false assurance on exactly these paths.

- `tests/test_alert_delivery.py:253-263` `test_escalation_sends_immediately`: starts from `last_sent_rank=0`; nothing starts from a prior higher-rank episode.
- `:219-238` (cooldown) and `:510-515` (`test_morning_delivers_held_alert`): evaluate against a clean state, not the state the suppressed or held run persists.
- `:61-104` `AlertWindowTests`: only the >48 h side; nothing for `hours_from_now < 0` or two same-rank tides.
- `:265-274`: covers a lower-rank tide only; nothing for same-rank composition change, radar drop-out or radar day rollover.
- `tests/test_radar_alerts.py:86-92` `test_small_projection_does_not_alert`: asserts rank 1 with a radar signature for +3.0 in, which does alert (AL-9).
- No test exercises the `active` gate with a high bay.
- Classes after the `__main__` guard at `test_alert_delivery.py:349` run only under discovery.

Verified: READ. Confidence: high.
Fix direction: add production-shaped state fixtures (`last_sent_rank=4`, non-empty `last_sent_sig`, persisted hold) and a high-bay, low-rain nowcast case.

### AL-15. Retired-SMS remnants and stale text that mislead diagnosis
**Severity: low.**

- The "No alert delivery" and "Delivered alert via" log lines print only the SMS gate (`ff:8806-8807`, `ff:5318-5319`), which now always says "sms rail retired". The live ntfy gate's reason (for example "nowcast inactive") is never logged on a normal run.
- `ff:8791-8794` still says "72h window" and "a short SMS … rides along"; `daily_forecast.yml:75` says "ntfy/email/SMS" and still passes `ALERT_SMS_TO` (`:89`).
- `deliver_alert(channels=None)` still includes `"sms"` (`ff:8315-8316`); production always passes `channels`, so this is latent.
- AGENTS rule 8 and the gate docstring (`ff:5397-5398`) say the imminent push "still counts" toward the cap; the code and `test_sms_count_does_not_exhaust_base_cap` keep it out of `base_sends_today`.
- `compute_alert_level`'s docstring promises a "reset after all-clear" that no code performs.
- `publication_blocked` and `retry_eligible` in the health file are constant or redundant; `bit` in `radar_alert_check` (`nc:674`) is only printed.

Verified: READ. Confidence: high.
Fix direction: log each enabled rail's reason and reconcile the "counts toward cap" wording.

## Checked and found sound

- **Arms and `alert_state.json`:** only the GitHub forecast workflow writes it; `bin/local_nowcast_tick.sh` adds only `docs/nowcast.json` and the heartbeat CSV. Forecast runs are serialized by the `barnacle-forecast` concurrency group.
- **Heartbeat ledger:** `data/nowcast_heartbeats.csv` is `merge=union` in `.gitattributes`, so the lost-race branch in `nowcast.yml:131-135` does see `docs/nowcast.json` as the only conflict.
- **Dispatch ordering:** checks follow the push, and the radar check runs on every scheduled run (`nowcast.yml:155-206`). On 2026-11-26 the chain took 80 s from nowcast generation to delivery.
- **Day boundaries:** cap counters, quiet hours and nowcast day-max all use station-local time; quiet hours are hour-of-day on an aware datetime, so DST-safe. No UTC-date leak was found.
- **Freshness:** stale, degraded, inactive or schema-mismatched nowcasts never alert (`ff:4729-4751`); source age is recomputed from `source_latest_utc`.
- **Imminent re-arm:** the marker stores the last sent class and time, not a running maximum, so there is no AL-2 sibling there. Per-rail markers are independent.
- **Transactional acknowledgement:** partial delivery leaves only the failed rail pending; total failure leaves `last_sent_*` untouched and exits 75; `publish_decision.py` requires a fresh receipt.
- **Delivery health file:** carries class, category and code only. The current file is `ok` for the 01:56:36Z send.
- **ntfy headers:** folded to latin-1 (`ff:8292-8300`).
- **Day-max merge:** `nc:310-318` cannot hit an empty `max()`, because the origin candidate has no timestamp and is never rejected.

## Could not determine

- **The 36-minute publication gap** (23:57Z → 00:33Z on 2026-11-26/27) during the rise. The local arm coalesces quiet ticks by design; why three GitHub slots are missing needs the Actions run list, which I did not fetch (no network). Source age was 7.2–8.4 min afterwards, against the 10-minute `RADAR_MAX_AGE_MIN`.
- **Whether AL-8 has recurred** since 2026-09-13; lost state leaves no trace in the repo.
- **What recipients actually received:** texts were rebuilt from committed forecast, nowcast and state with the current code.
- **Street versus push level at 20:56 EST:** the push said +34 in; the owner's 21:15 reading is about 30.7 in (6.08 ft NAVD88, per HANDOFF). I did not open the e02 table.
- **Count 3 on 2026-09-23** (`d17aa402e`): `base_sends_today` exceeded the cap of 2; probably a forced manual dispatch, not confirmed.
- **Policy questions:** a bay-keyed imminent rule, a day-of reminder, and severity-aware quiet hours are the owner's decisions; the findings state behaviour only.
