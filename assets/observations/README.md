# Field-observation archive

Read [PLAYBOOK](../../PLAYBOOK.md) before live support. Record reports in both
the append-only observation ledger and the date's `flood-measurements.txt`.
Keep raw reports, interpreted observations and model reconstructions distinct.

## Current witnessed-flood benchmark — updated 2026-09-27

**Both September 26 and September 27, 2026 morning floods exceeded October 30,
2025 in John's witnessed experience.** John explicitly confirms these were the
first two floods to enter the garage: the entire garage flooded September 26,
and about 90% September 27. Primary source: [owner's exact follow-up](2026-09-27/owner-ranking-followup.txt)
`[STATED]`; the observation ledger contains a retrospective clarification, not
a new measurement at the time that clarification was recorded.

| Flood episode | Existing measured peak at the reference intersection | Garage extent reported by John |
|---|---|---|
| [2026-09-26 morning](2026-09-26/README.md) | 12.25 in above porch-step base; about 5.701 ft NAVD88 / 26.2 in above SW grate | Entire garage |
| [2026-09-27 morning](2026-09-27/README.md) | 11.25 in above porch-step base; about 5.618 ft NAVD88 / 25.2 in above SW grate | About 90% |

Peak source: the dated raw reports and corresponding landmark/depth ledger rows
(September 26 09:06–09:13; September 27 09:44–10:06). The garage extent is
separate qualitative evidence, not a conversion to an exact surveyed elevation.
These statements concern the owner's witnessed local floods, not the largest
flood in Highlands history or the historical Sandy Hook gauge ranking.

[October 30](2025-10-30/README.md) remains a historical calibration reference;
its numerical crest is reconstructed, not tape-measured. Its former “biggest”
label is superseded. Older dated rankings describe knowledge at their writing
date; consult this note for the current benchmark. No fit constants or frozen
calibration results change merely because a larger flood has been observed.

## More than one episode on a date

Existing convention is one date directory with separately identified episodes:

- [2026-05-30](2026-05-30/README.md): explicitly a **two-tide observation set**,
  AM and PM sections; the AM check was dry, PM had post-peak flooding evidence.
- [2026-09-13](2026-09-13/flood-measurements.txt): round 1 rain flood and round 2
  compound flood, separate timelines in the same dated notes; these were not
  two separate high tides.
- September 26: morning and evening floods in one dated folder.

Proposed refinement, pending the open audit response: keep existing date paths,
add stable date-scoped IDs such as `2026-09-26-e01` and `2026-09-26-e02`, and
link their explicit windows/source rows in an episode registry. If separate
episode directories become useful, nest `e01/` and `e02/` under the date.
The ordinal is per date, not the historical storm number. Preserve “Event #10,
round 1/2/3” as aliases. Keep storm grouping distinct from episode counts.
**No directory migration or registry has been implemented yet.**

For originals offered by the owner, convenient locations are
`2026-09-26/rawnotes/morning-original.txt`,
`2026-09-26/rawnotes/evening-original.txt`, and
`2026-09-27/rawnotes/morning-original.txt`. These are proposed destinations,
not a claim that the originals have been received. Preserve wording, dates,
AM/PM labels and uncertain times; annotate interpretations separately. Original
file format is also welcome. Review personal information before committing
owner-supplied originals to this public repository.

Outstanding propagation problems (daily-max displays, scoring identities and
timestamp handling) are tracked in [audit 2026-09-27-a1](../../audits/2026-09-27-a1/01-event-records-and-repo-audit-codex.md).
