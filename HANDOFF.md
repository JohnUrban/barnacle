# HANDOFF — Bay Ave Barnacle

**Snapshot · 2026-11-27 · Production v0.10.6.** Start with the
[merged audit](audits/2026-11-26-a1/02-merged-audit-sounding.md) for defects
and BACKLOG OPEN LOOPS for decisions. Read PLAYBOOK first for field support.

## Audit and operations

Sounding independently audited production and seven development worktrees,
then evaluated all 82 of Fable’s numbered findings. The [first pass](audits/2026-11-27-a1/01-independent-sounding.md)
was frozen before opening the November 26 audit. Both reports are findings
only. Implementation and model/policy decisions remain open.

- Protect the gauge anchor before writing fallback state. At 14:06 EST on
  Nov 26, production accepted +7.219 ft surge and marked inputs healthy.
- Repair event-scoped alert escalation and reconcile conflicting headlines.
  Three historical upgrades have no base-channel acknowledgement. The
  September case received a delayed upgrade. Radar can miss tidal street
  flooding, and the tide gate makes a bay-only “street now” claim unreliable.
- Public-photo privacy requires remediation. John has the filename privately.
- Freshness, station-time fold, incomplete radar coverage, archive links,
  capped/held sends and the 35–40-minute UTC-midnight schedule gaps remain
  open. Exit-75 recovery has offline coverage; a real full outage remains
  unverified. The audit ran the generator separately with delivery disabled.

## November field evidence

Nov 26 e01 and e02 were separate flooding episodes in one storm. e01’s
morning crest is an approximate lawn-step recollection with surrogate time.
For e02, the observer reported level with the second porch step at 21:15 EST.
About 6.08 ft NAVD88 is derived from the first step and prior riser tape.
At 21:54 the report was 4 in above the first step. The preliminary Sandy Hook
series reached 9.211 ft MLLW. Street lagged bay on the rise; gate state was
unobserved. The [episode record](assets/observations/2026-11-26/e02/README.md)
documents owner corrections. Open items include the recession, photos,
riser check, full and verified gauge pulls, MRMS forcing and plots.
Use absolute local times, record raw observations promptly, and keep
evidence type distinct from derived level.

The gate was photographed closed Sep 28 and Nov 10. The Borough inquiry,
bay-to-street transfer and high-base tank science remain open. Nov 12 e02
was a rain-driven flood with a lawn-step report at 18:24 EST. Its gauge
archive, MRMS forcing and plots remain pending. The midday call on Nov 12
and the Oct 11 rain call still need field confirmation.

## Production and paused research

- [Current spec](model/v0.10.6.md). Hourly forecast and two radar arms,
  18 landmarks, 36-hour surge decay, experimental seven-day/rain skill.
  ntfy carries imminent impact; ntfy/email carry longer-lead alerts.
  SMS was retired by owner decision. Quiet hours and reminder policy
  questions are recorded in the audit.
- The Nov 10 derived-score correction covered 166 rows, 109 adjusted.
  Its corrected last-30 signed mean is −0.093 ft. Owner decisions on
  general record-correction wording and independent arm monitoring remain open.
- Wind c2 remains shadow-only. The [frozen evaluation](audits/2026-11-27-a1/wind-evaluation.json)
  on 1,534 opportunities found four scorable completed storms at 24/30 h.
  The decision endpoint has not been reached.
- Heron’s reviewed evaluator at cd17a5a14 remains research-only. Integration
  needs fresh astronomy and episode-aware handling of stated bases. Tern’s
  rehearsal at 1ca80d9a0 remains local-only, with queued expiry and owner
  phone/readability review outstanding. See the worktree inventory before
  reviving either branch.
- Landmark bounds implementation is closed. Widget v7.35a was copied; native
  long-form/bounds readability and the 4.37 vs 4.16 survey discrepancy remain
  open. Storm communication parity and historical census/hindcasts remain
  in BACKLOG. Further development awaits the owner’s chosen arc.
