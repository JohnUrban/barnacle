# HANDOFF — Bay Ave Barnacle in two minutes

**Snapshot: 2026-09-27 18:40 EDT** (branch `audit/2026-09-27-a1-reply`, worktree
`../barnacle-a1reply`, three commits on `main` `0176795e0`, UNMERGED). Rewrite
wholesale each ship; <100 lines. `BACKLOG.md` OPEN LOOPS is authoritative.

## Immediate obligation — Codex verification of the independent reply

Audit **2026-09-27-a1 remains OPEN.** Independent reply filed:
`audits/2026-09-27-a1/04-independent-reply-claude-curlew.md` (Claude Fable 5.1,
"Curlew"). R1–R7 all CONFIRMED against primary records; repairs are on this
branch for Codex's independent review, then merge via the ship ritual
(commit → gate → push, rebase-with-gate). Commits: `bc645ed5c` (production
repairs + tests), `5b614a076` (event analysis artifacts), plus the docs commit
carrying the reply/HANDOFF/BACKLOG. 374 tests OK (one absent-training skip; 32
new), gate clean, three frozen replays PASS, seven frozen wind hashes match,
offline site render verified. `docs/`, ledgers, model constants, wind files,
Heron/Tern branches untouched. Do not close the audit on tests alone.

What changed on the branch (review focus in the reply's last section):
- **R7** exit 2 = delivery-only failure; hourly workflow publishes validated
  artifacts, then fails the job after push; `data/alert_delivery_health.json`;
  sent-state untouched on failure (pending_base retry). Production workflow
  change — needs Codex's eyes.
- **R6** near-term tape dots and all-pathways peaks parse through the shared
  station helpers and compare UTC instants (also fixes a fold-collapse on
  fall-back night); `bin/append_observation.py` stores offsets; 77 rows kept
  naive; interval sidecar `2026-09-27/analysis/observation_intervals.json`.
- **R3** production peaks chart is per registered episode (Sep 26 shows both
  floods). Heron needs: `history/plans/2026-09-27-heron-episode-interface.md`.
- **R5** landing/details wording no longer calls the gauge line street water or
  Oct 30 the worst measured flood; nowcast `day_max_provenance` + operator
  rejection record `data/nowcast_daymax_rejections.json` honored by the merge
  and the "so far today" line. Widget/email/SMS: objective exemptions, no bump.
- **R4/R2** raw GMT gauge archive with flags + receipts, `gauge_qc.json` (peak
  and lag INTERVALS, Battery, spike screen, cache comparison, nowcast bay-input
  trace), `rain_scenarios.json` (four tides, four explicit assumptions),
  `event10_hydrographs.png` (supersedes the Sep 26 four-tide figure).

## Event #10 — September 25–27 coastal flooding (storm 2026-09-25-coastal)

Three floods + one negative window, IDs Sep25-e01 / Sep26-e01 / Sep26-e02 /
Sep27-e01 (registry `assets/observations/episodes.json`, 30 records total).
Tape crests 5.701 (09:06–09:13 Sep 26), 4.20–4.24 (22:11–22:29 Sep 26), 5.618
(09:44–10:06 Sep 27); both mornings exceeded Oct 30 2025 (owner: whole garage
Sep 26, ~90% Sep 27). Sandy Hook (still preliminary, q=p): 5.847 @08:36 with a
flat top 08:12–08:54 → corner lag 12–61 min; 5.703 @09:06, flat 08:48–09:24 →
lag 20–78 min; Sep 26 PM lag 83–125 min. Gate: SEEN closed only at 18:19 Sep 26
(photo pending, rule 9); "almost certainly" ~21:58 and ~08:30 (untimed
surrogates); inferred otherwise. Rain: Sep 26 AM 1.30 in (14:24Z frame
missing), "~2.4 in" is scenario A (fixed base, zero drain) only; Sep 27 AM
0.23 in, not rain-assisted. No gate threshold or leakage model exists; none
authorized. Garage entry = proxy, not a surveyed elevation.

**Public defect, now traced:** the 2026-09-27 nowcast day max **39.0 in @02:40**
came from runs whose "observed" bay input was 4.6→6.7 ft while NOAA had
0.2–0.8 ft; the site's "so far today" line showed it as SEVERE +39.0 above the
25.2-in tape crest all day. Rolls off at local midnight; rejection recorded on
the branch. **Owner DECISION needed:** may a modeled value ever outrank a
same-day tape crest on that line? (code = max wins; docstring = modeled only
when nothing better).

Still pending: Codex review/merge; Heron episode-aware evaluator; verified
NOAA series (archive beside, not over); episode photos; Borough gate history.
## Production — v0.10.6 live; release audit CLOSED

Spec `model/v0.10.6.md`; promotion `75a9933ff`. 18 landmarks, hourly site/JSON,
~10-min radar nowcast; widget v7.29a re-copy by John unconfirmed. SMS imminent
impact; ntfy/email longer lead; alert tide horizon 48 h. Consult live inputs,
not this snapshot, for conditions. Seven-day tails and as-issued rain skill
remain experimental. Live bug fixes from Sep 26 (ntfy Latin-1, true-time tape
dots) stand; this branch supersedes the tape-dot boundary handling.

## Wind-shadow c2 — CLOSED implementation audit; trial collecting

`audits/2026-09-24-a3/07-close-out-codex.md`; frozen bundle 82d156a6… (hashes
re-verified on this branch). Shadow only. Minimum 60 days AND five eligible
completed storms; three flood episodes = ONE storm.

## Heron — evaluator closed; research unmerged; science awaits evidence

`audits/2026-09-24-a4/09-close-out-codex.md`, candidate `cd17a5a14`. Not
modified here. Interface/gap note above; issuance coverage for the storm
unchecked. Revisit 2026-10-09 or earlier.

## Social and remaining owner work

Tern rehearsal local-only; owner copy/geography acceptance open. No
accounts/posts, no production copy change, no merge/push of the social branch.
Neutral landmark survey remains John's future task.

## Prior storm follow-up remains open

`history/plans/2026-09-25-storm-followup-handoff.md`: email/day-worst headline
parity. Guidance-first is an offline candidate. SMS-policy review separate.

Read PLAYBOOK before event support (three-clocks rule + handoff checklist
added). Log ledger AND raw notes on receipt. Explicit staging; commit → gate →
push; rejected push → rebase/abort → gate. Never overwrite newer work.
