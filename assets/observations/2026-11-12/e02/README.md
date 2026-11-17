# 2026-11-12-e02 — Evening rain flood: level with the lawn step at 18:24, gone before 19:10

Record type: `flood_episode`. Storm grouping: none assigned.
John created this folder, the note and the photos; registered 2026-11-17.

## Sources

- [flood-measurements.txt](flood-measurements.txt): the owner's own note,
  kept exactly as he wrote it. The file was saved here on 2026-11-17, but
  the content is CONTEMPORANEOUS: he wrote it in his phone's notes app
  while it was happening ([clarifications.txt](clarifications.txt)).
- Photos: `barnacle-20261112-e02 - 1.jpeg` (EXIF 18:23:07 EST) and
  `- 2.jpeg` (18:23:54 EST), from the porch steps and the walkway: the
  intersection under water at night, water at the fence line. Rule 9
  review 2026-11-17: no people in frame, nothing altered, EXIF kept.
- Ledger rows: [episode registry](../../episodes.json), keyed by row-content hash

## What was observed

| Time (EST) | Observation | Level |
|---|---|---|
| 18:24 | "level with lawn step" `[STATED]`, photos one minute earlier | 4.66 ft NAVD88, +13.7 in over the SW grate |
| about 19:10 | "Gone" `[STATED]`: his next look, the water had already cleared | not quantified |

There was no look between 18:24 and about 19:10, so the crest is not
bracketed by readings and the clearing time is only bounded: some time
before about 19:10.

**Owner's impression (his word: speculation):** he believes he caught the
peak. The flooding came up fast ("It wasn't flooded.. then it was"); while
he watched around 18:24 it "seemed like it was threat[en]ing to come up the
lawnstep, but never did", and by the time he walked away "it was clear it
never would" ([clarifications.txt](clarifications.txt)). Read that way the
crest was at the lawn step, about 4.66 ft NAVD88, at roughly 18:24, and did
not go over it while he stood there `[STATED as impression, not a second
reading]`.

Bay at 18:24: 4.54 ft MLLW (1.72 ft NAVD88, preliminary), 22 in below the SW grate
and rising slowly. This was a rain flood with the tide out of the picture.

## What Barnacle said (radar nowcast, both arms; `docs/nowcast.json` history)

| Published (EST) | Rain, max in/hr | Modeled water now | Projected peak |
|---|---|---|---|
| 18:06 | 1.0 | 0.0 in | 11.6 in |
| 18:10 | 2.55 | 0.0 in | 15.8 in |
| 18:17 | 2.84 | 5.5 in | 16.7 in |
| 18:26–18:27 | 2.4–2.8 | 9.8–10.8 in | 13.6–14.3 in |
| 18:36–18:45 | 2.4–2.8 | 13.4 in | 13.6–14.3 in |
| 18:55–18:58 | 2.4–2.8 | 10.2–10.6 in | 13.6–14.3 in |
| 19:08 | 2.84 | 9.1 in | 15.8 in |
| 19:19 | 1.94 | 6.8 in | 13.7 in |
| 19:33 | 0.27 | inactive | |

Imminent alert sent 18:11:49 EST at the lawn-step class, from the 18:10
projection: about 12 minutes before John's photos. (ntfy delivered; the
SMS copy bounced, see BACKLOG `sms-gateway-decommissioned`.)

- **Peak height: hit.** Observed 13.7 in at 18:24; modeled peak 13.4 in.
- **Rise: model about 10–15 min late.** At 18:24 it showed roughly 10 in and
  did not reach 13.4 until 18:36. If the owner's impression is right that
  18:24 was the crest, the model's crest (18:36–18:45) was 12–20 min late
  and its projections of 14–16 in were 0.5–2.5 in too high.
- **Recession: model too slow.** When John looked again at about 19:10 the
  water was gone; the model still carried 9.1 in at 19:08 and 6.8 in at
  19:19.

The late rise and slow recession are the same two tendencies recorded for
earlier rain events (BACKLOG `event-#8-analysis`).

## Still to do (PLAYBOOK hand-off checklist)

PENDING: raw gauge pull with flags for Sandy Hook and The Battery; rain
forcing for the whole window from the MRMS archive; the standard plots.
Not done at registration, five days after the event.
