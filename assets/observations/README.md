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

John approved stable date-scoped episode IDs and subfolders on 2026-09-27.
[The episode index](EPISODES.md) and [machine-readable registry](episodes.json)
now cover the existing dated field archives, the December historical ledger
observation, and the September 25 negative window: **27 registered episodes**,
including dry checks and reconstructed/unmeasured events, not 27 measured floods.

Each episode has an `e01/`, `e02/`, etc. home under its date. IDs are
`YYYY-MM-DD-eNN`; never renumber an assigned ID. A later-discovered earlier
flood gets the next unused ID and its true time in metadata. The ordinal is
not a severity ranking or historical storm number. Keep storm grouping separate.
Existing images and raw notes remain at their original paths, linked from the
new episode homes. New episode-specific material belongs under that episode;
date-level analysis can compare multiple episodes. Register row associations
using content hashes; leave the append-only ledger unchanged. Run
`python3 history/scripts/check_observation_episodes.py` to check coverage.
This is an offline source index; production and research consumers have not
silently switched their grouping rules.

Original notes supplied by John are preserved byte-for-byte at
`2026-09-26/rawnotes/01-morning.txt`, `2026-09-26/rawnotes/02-evening.txt`, and
`2026-09-27/rawnotes/01-morning.txt`. See the
[reconciliation](2026-09-27/analysis/README.md). Interpretation and time
normalization are recorded separately. Photos for these episodes are pending;
use their `eNN/photos/` folders, following the existing privacy rule before
publication. A date directory can contain multiple independent records while
still belonging to one correlated storm.

[Updated all-anchors comparison](2026-09-27/analysis/all_anchors.png): measured
September crests distinguished from the reconstructed October reference.

Outstanding propagation problems (daily-max displays, scoring identities and
timestamp handling) are tracked in [audit 2026-09-27-a1](../../audits/2026-09-27-a1/01-event-records-and-repo-audit-codex.md).
