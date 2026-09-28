# Round 13 — independent implementation and deployment close-out

Reviewer: Codex. **2026-09-27 23:03 EDT** (2026-09-28 03:03Z).
Reviewed Curlew's round12, ship **c2569c07a**, documentation **193c3949d**,
and the first post-merge nowcast publication **224f1e1a4**.

**Implementation/deployment review CLOSED.** The reviewed repairs are live;
no further Curlew repair is requested for rounds05/07/09/11. Native
Scriptable readability remains an explicitly **OPEN owner acceptance
check**, not a passed check. The separately approved landmark-bounds work
and scientific follow-ups remain open. This closes neither those tasks nor
the broader question of bay-to-street transfer during gate operation.

## Independent verification

- Ship code, tests, model/specs, analysis scripts and observation assets
  match approved candidate **6e9fe57cb**. The merge parents are that
  candidate and then-current main **d3cd2b92b**. The ship cites round11 and
  the existing owner DECISION; no retrospective approval is disguised as
  earlier review.
- All three protected CSV ledgers are byte-identical to pre-merge main
  d3cd2b92b: 270 observation rows, 16,157 prediction rows and 123 accuracy
  rows, excluding headers. Newer event records survive. Registry validation:
  31 registered episodes, 270 indexed rows, zero pending rows. Registered
  episodes include negative checks and reconstructions, not just floods.
- Independent isolated archive of **193c3949d**: **443 tests OK, one skip**
  (`BARNACLE_REQUIRE_GRIB=1`; absent local training input); all three
  read-only frozen replays PASS; all seven wind hashes match; artifact gate
  clean. Subsequent 224f1e1a4 changes only the nowcast and heartbeat data.
- GitHub confirms ship CI **36371161800** and Pages **36371161755**
  succeeded. Post-merge nowcast **36371782663** and its Pages deployment
  **36371852868** also succeeded.
- Public assets fetched independently at **03:01:26Z**: forecast generated
  **02:46:31Z**, model **v0.10.6**, `today_lookback.evidence=measured`,
  **+25.2 in above SW grate at 09:44**. Landing source carries the explicit
  measured-bay/not-measured-street explanation. Deployed widget is byte-
  identical to the approved/shipped **v7.32a** asset. This is source/response
  verification, not a native Scriptable layout inspection.
- The rejected **+39.0 in at 06:40Z** maximum is **actually removed before
  midnight rollover**. Nowcast run 36371782663 logs rejection of both carried
  candidates at **02:58:18Z**. Public nowcast generated **02:57:54Z**, still
  assigned to local day **2026-09-27**, has no `day_max_*` fields. It does not
  invent a replacement maximum when no positive retained candidate remains.
  The measured historical crest remains in forecast.json. This supersedes
  round12's honestly pending post-merge-run status.

[Verification receipt](13-verification-results.json) contains asset hashes,
workflow links, ledger/code/hash comparisons, live values and the rejection
log excerpt. No review alerts were sent and no model physics changed.

## Remaining work and handoff

1. **John:** re-copy deployed v7.32a into Scriptable; check the medium widget
   with a long quoted report and a model-claim clause. Source tests cannot
   establish native readability. Keep this pending until actually checked.
2. **Curlew, next separate work unit:** owner-approved
   `landmark-relation-bounds` (BACKLOG 22:44 PREF/OPEN). Encode explicit
   survey-based bands with provenance; ask where a band cannot be computed;
   carry bounded evidence and neutral claim wording across the relevant
   surfaces. Reports relating water to landmarks are quantitative evidence,
   even when not tape measurements. The shipped quote-only handling is not
   the final implementation of this new request. Do not manufacture precision
   from approximate survey points or treat different places/times as one
   exact level. Review the resulting implementation separately.
3. **Retained scientific/record follow-ups:** gate transfer, high-base tank,
   verified versus as-seen NOAA, owner photos, historical census/hindcasts,
   and Heron's episode-aware as-issued evaluation. The four-window study
   ends Sep27 AM, not Sep27 evening e02. Tern and Heron retain their scopes.
4. Delivery-failure publication is test-verified; no real transport outage
   has exercised the new production path. Do not claim otherwise or trigger
   an outage solely to close this record.

Documentation housekeeping in this round updates stale v7.29a recopy text,
dates HANDOFF accurately and appends the observed rejection cutover without
rewriting Curlew's earlier pending receipt.
