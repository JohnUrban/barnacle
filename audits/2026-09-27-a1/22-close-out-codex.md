# Round 22 — landmark-bounds implementation and deployment CLOSED

Reviewer: Codex. Independent verification **2026-09-28, 12:14–12:18 EDT**.
Reviewed ship `7248c500d`, test repair `ad2b66a52`, and author record
`0dfc307ce`; then synchronized bot publications through `07840a36a`.

**CLOSED for implementation/deployment.** No further Curlew code revision
is requested for this work unit. The round13 close-out still stands.
Native widget acceptance and scientific follow-ups below remain open.

**Score: 9/10 for this ship round.** Curlew preserved the approved code,
regenerated and checked deployment, caught and repaired a legitimate CI
failure, and disclosed both that failure and the limits of live verification.
The deductions are documentation housekeeping: authoritative OPEN LOOPS
still described the candidate as unmerged, and round21's merge row has
incorrect commit metadata. Both are reconciled here without rewriting the
historical record.

## Verification

- Production code, writer, model specs/data and widget are unchanged from
  approved candidate `648c7db8d`. The sole subsequent change under tests is
  `ad2b66a52`. No formula, surveyed elevation or model stamp changed.
- **487 tests OK, one skip** in an isolated archive of `0dfc307ce`, with
  `BARNACLE_REQUIRE_GRIB=1`; the skip is unavailable local training input.
  Three read-only frozen replays PASS; seven frozen wind hashes match.
  Gate clean; registry contains 31 episodes, 270 indexed rows, zero pending
  (episodes include negative checks/reconstructions, not 31 floods).
- All three protected CSV ledgers are byte-identical between actual
  pre-merge main `1f42ca699` and `0dfc307ce`; bounds records are identical
  to the approved candidate. Subsequent bot publications through
  `07840a36a` preserve all three prefixes, adding six prediction rows only.
- Re-executed round20's whole-build/render probes on the merged archive:
  missing bounds degrade visibly, a clean subsequent read clears that
  status, and landing/email/widget text retain the disputed-cap qualification
  alongside the higher model claim. These are offline fixtures, not live
  flood occurrences. No alerts were sent by this review.
- Independently read failed CI **36445097545**: the sole failure was
  `5 != 6` in the fixed-count tide-page assertion. The corrected test follows
  unique payload tide times, retains a 4–7 sanity range, and still requires
  every resulting page to exist; the separate DOM contract remains intact.
  This is a valid repair, not removal of a production failure check.
  CI **36446596736** and **36448482105** succeeded; ship Pages
  **36445097941**, repair Pages **36446596325**, and later bot Pages
  **36449685407** succeeded.
- Public assets fetched **12:17:50 EDT**: widget is **v7.35a**, byte-identical
  to the approved candidate; landing, details and outlook carry **v0.10.6**.
  Forecast generated **2026-09-28T16:14:33Z**, `degraded_inputs=[]`, no
  bounds health error. Its lookback is **bay peak +10.7 in at 09:30**,
  explicitly “gauge; corner not measured,” with zero local checks. No
  unsupported `(tape` marker on those pages. All six downloaded assets
  match synchronized main `07840a36a` exactly. This proves deployed source
  and artifacts, not native Scriptable layout or a live bounded report.

Receipt: [22-verification-results.json](22-verification-results.json).
Integration probe source: [round20](20-integration-probes.py).

## Documentation corrections and remaining work

Round21's merge row names `4309dcc3c` and 11:26. Git records
`f815877cb` with parents **648c7db8d / 1f42ca699** and commit time
**11:36:01 EDT**. The earlier round20 review commit is an ancestor of the
merged main, not its tip. This is a metadata correction; approved work and
newer bot records were preserved. BACKLOG OPEN LOOPS is updated from its
stale unmerged/not-deployed state; append-only historical lines remain.

John should copy the **deployed v7.35a** and inspect bounded, disputed-cap,
long-report and model-claim forms in Scriptable when available. Only the
v7.32a measured form has an owner screenshot; that does not certify these
longer forms. No further Curlew development is needed unless that inspection
finds a problem.

Still open: crossing-versus-curb survey conflict (4.37 vs 4.16 NAVD88),
gate transfer, high-base rain tank, verified versus as-seen NOAA evidence,
photos, Borough gate history, historical census/hindcasts and Heron's
episode-aware as-issued evaluation. Tern and Heron retain their scopes.
No scientific accuracy conclusion or new production model is approved here.
