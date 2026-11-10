# 2026-11-10 — Snug Harbor Beach tide gate found closed (no flood)

Not a flood record. John checked the tide gate at Snug Harbor Beach this
morning and found it closed `[STATED]`; he took one photo. His message,
verbatim, is in [flood-measurements.txt](flood-measurements.txt). Episode
home: [e01/](e01/README.md).

| | |
|---|---|
| Observation | Gate **closed**, seen in person `[STATED]` |
| Time | 08:33:05 EST, from the photo's EXIF (John's text says "today"); reported 10:24 EST |
| Photo | [gate-closed/barnacle-20261110-gate-closed - 1.jpeg](<gate-closed/barnacle-20261110-gate-closed - 1.jpeg>) (received as `snug-harbor-beach-flood-gate-is-closed-today - 1.jpeg`; no people in frame, rule 9 checked; EXIF kept) |
| Bay at the time | 5.72 ft MLLW at 08:30 (2.90 ft NAVD88), just after the morning peak of 5.734 ft at 08:24; 7.3 in below the SW grate. Preliminary NOAA reading. |
| Barnacle's call | dry |
| Ledger | `data/labeled_observations.csv`, row `2026-11-10T08:33:05-05:00`, `tide_gate_snug_harbor` |

The tide this morning would not have reached the street with the gate open
or closed, so today's check says nothing by itself about whether the gate
held water back. Its value is as a second endpoint.

## What John concludes, and how firm each part is

- **Closed on 2026-11-10** — `[STATED]`, with photo.
- **Closed continuously since late September** — `[INFERRED]` (owner). The
  earlier sightings are 2026-09-26 18:19 (photo) and later that evening
  (~21:58 in the notes; photos at 22:06, "almost certainly" closed),
  2026-09-27 ~08:30 ("almost certainly"), and 2026-09-28 09:01 EDT (photos
  under `2026-09-28/gate-closed/`, ledger row added 2026-11-10). His reasoning:
  nothing about today's ordinary tide would call for closing it, so it was
  probably never reopened. Two sightings six weeks apart do not rule out an
  open spell in between.
- **No street flooding noticed in the past month** — `[STATED]`, with his own
  caveat: he was not looking for it, and could have missed anything that
  happened while he slept.
- **The closed gate has been preventing light tidal flooding** — `[INFERRED]`
  (owner). Consistent with his September summary: the gate prevented
  apparent local flooding on Sep 25 PM, nearly prevented it on Sep 26 PM,
  and delayed the Sep 26 and Sep 27 morning floods (BACKLOG
  `event-10-owner-update`).
- **For rain the effect would be the opposite: a closed gate should make rain
  flooding worse, an open one better** — owner hypothesis, `[INFERRED]`. One
  consistent observation: 2026-09-27 evening (episode 2026-09-27-e02), water
  spanned the intersection in steady rain while the bay was near 2.3 ft
  NAVD88, below the grates, with the gate almost certainly closed. How the
  gate, outfalls and any check valves or pumps actually work is still the
  open Borough question (BACKLOG `event-#10-infrastructure-inquiry`).

## What this means for Barnacle's predictions

Barnacle has no gate in it. It assumes the bay reaches the street drains
freely. John's point: **while the gate is closed, a tidal street-flooding
call for this intersection is expected to be wrong** (water stays out unless
the bay overtops the gate), and tidal flooding at the intersection should be
expected when the gate is open. No model or wording change is requested or
made; this note is so the pattern can be tracked.

From the evening of 2026-09-28 through this morning there were 81 high
tides. The bay peaked above the SW grate (6.34 ft MLLW) on 15 of them.
Barnacle's last call before each
was "street" on 14 and "dry" on one. All were the lowest street class; none
was forecast or observed at light, moderate or severe. These are bay-gauge
facts `[VERIFIED: data/observed_peaks_cache.csv, data/predictions_log.csv]`.
Whether any water reached the street on any of them is **not observed**;
if the gate was closed throughout, these are the tides where Barnacle said
street water and the corner probably stayed dry.

| High tide (local) | Bay peak, ft MLLW | Above SW grate | Barnacle's last call |
|---|---|---|---|
| 2026-09-28 21:40 | 6.48 | +1.7 in | street |
| 2026-09-29 09:58 | 6.75 | +5.0 in | street |
| 2026-09-30 10:47 | 6.65 | +3.8 in | street |
| 2026-10-11 08:46 | 6.48 | +1.7 in | street |
| 2026-10-11 21:03 | 6.45 | +1.3 in | street |
| 2026-10-12 09:25 | 6.67 | +4.0 in | street |
| 2026-10-13 10:03 | 6.38 | +0.4 in | street |
| 2026-10-21 16:44 | 6.80 | +5.6 in | street |
| 2026-10-22 05:21 | 6.57 | +2.8 in | street |
| 2026-10-23 06:07 | 6.53 | +2.2 in | dry |
| 2026-10-24 06:49 | 6.52 | +2.2 in | street |
| 2026-10-27 08:52 | 6.58 | +2.9 in | street |
| 2026-10-28 09:40 | 6.74 | +4.8 in | street |
| 2026-10-29 10:33 | 6.55 | +2.5 in | street |
| 2026-11-07 06:00 | 6.55 | +2.5 in | street |

Rain side over the same period: a rain-flood risk level was issued on eight
days (2026-09-28, 10-02, 10-10, 10-11, 10-15, 10-16, 11-05, 11-06;
`data/day_risk_log.csv`), and the radar nowcast went active once, on
2026-10-11, when one imminent-impact text was sent
(`data/alert_state.json`). No street observation exists for any of them.

## The one tide where the street WAS photographed: 2026-09-28 morning

Filed on 2026-11-10 from photos John took that morning
([../2026-09-28/README.md](../2026-09-28/README.md), episode 2026-09-28-e01).
Gate photographed closed at 09:01 EDT; at 09:06 the corner was not flooded
while the bay stood at 7.21 ft MLLW, 10.4 in above the SW grate, and
Barnacle's call was MODERATE. That is the best single piece of evidence for
John's reading, and it is photo evidence, 24 minutes before the bay peak.

## Follow-up the same morning (received 10:35 EST)

- **2026-10-11 evening** (the one rain event Barnacle texted about): John has
  no memory of flooding and no photos; he recalls some alerts and does not
  think the rain got severe enough to flood `[STATED, recollection]`. This is
  a weak negative, not an observation.
- **Thursday 2026-11-12**: John will try to look for flooding. The
  experimental outlook showed the 09:11 EST tide possibly reaching the
  grates (6.7 ft MLLW from NWPS guidance at 47 h lead; the core forecast said
  5.73, dry). If the bay tops 6.34 ft and the corner stays dry, that is a
  direct test with the gate known closed two days earlier.
