# 2026-09-27 — Event #10, round 3: morning surge tide (gate closed)

**Original owner notes received 2026-09-27:** see [rawnotes/](rawnotes/).
The existing `flood-measurements.txt` is a retrospectively assembled transcript;
original wording and explicit normalization are preserved separately in the
[reconciliation](../2026-09-27/analysis/README.md). Photos remain pending.

Part of Event #10 (nor'easter coastal surge, 2026-09-25 → 27). Rounds 0–2,
the tide-gate discovery, rain attribution and the cross-tide figure live in
[`../2026-09-26/`](../2026-09-26/README.md). Verbatim reports:
[`flood-measurements.txt`](flood-measurements.txt). Ledger rows:
`data/labeled_observations.csv`, 2026-09-27, observer john.

**Owner ranking clarification (2026-09-27):** this morning flood and the other
September 26/27 morning flood both exceeded October 30, 2025. These were the
first two witnessed garage-entry floods: the whole garage September 26 and
about 90% September 27 `[STATED]`. [Exact owner statement](../2026-09-27/owner-ranking-followup.txt);
[current benchmark and episode organization](../README.md).

## Crest
**11.25 in over porch_step_base = 5.62 ft NAVD88 (+25.2 in vs SW grate),
09:44–10:06 EDT**, ~2.5 in over the first porch step top [VERIFIED user
readings]. Second-largest measured flood (after 2026-09-26, 5.70).
Sandy Hook peaked 5.71 at 09:06: corner −0.09 ft, ~40–60 min later.

## Garage (user rule, logged as PREF `garage-intrusion-warning`)
Water reached the garage mouth at 09:12 exactly as it reached the first
porch step top (5.41) → **first porch step top = garage entry**. Inside by
09:14 (waves pushing it in and out); ~1/3 of the length 09:24, ~2/3 09:33,
~90% (to the back-wall refrigerator) 09:44–10:06; receding to ~1/3 by 10:38. Out of the garage by 10:54 (wet; water at the mouth but not over the lip → garage lip ≈ 5.36–5.41 NAVD88).

## Recession
10:54 +8.2 in (5.36) · 11:20 +6 (5.18) · 12:01 +2 (4.85) · 12:48 ~0.5–1 in over the curb (~4.22): Bay Ave no longer crossed, Central still crossed at both grate pairs. ~6 in/hr, like 9/26 AM.

## Gate
User at the beach ~08:30: water extremely high, no sign it was open — almost
certainly CLOSED (as on 9/26, when it was seen closed).

## Reading
Bay above grate height from 06:24, but corner water only from ~07:48 (bay
~5.0), curb breached 08:14, then a FAST rise (4.24 @08:16 → 5.41 @09:12, ≈15
in/hr) while the bay passed ~5.3–5.6. Consistent with the gated-corner
picture from 9/25–26: below a ~5.0–5.3 ft threshold the closed gate holds the
bay out (slow, late seepage); above it the street fills fast and nearly
matches the bay. Surge ROSE through the morning (+2.1 → +3.1 ft by 10:30).

Figure: [`../2026-09-26/analysis/corner_vs_gauge.png`](../2026-09-26/analysis/corner_vs_gauge.png)
(panel 4). Pending: rain check for this morning; the event-wide study.

## Stable episode IDs (assigned 2026-09-27)

- [2026-09-27-e01](e01/README.md): Morning coastal flood.

[Full episode index](../EPISODES.md). Historical source paths and storm/round aliases are retained.

## Updated historical comparison

![Recorded flood levels](analysis/all_anchors.png)

[Data, method and qualifications](analysis/README.md).

## Erratum and provenance notes — 2026-09-27 (audit 2026-09-27-a1, Claude Fable 5.1 "Curlew")

- "Sandy Hook peaked 5.71 at 09:06: corner −0.09 ft, ~40–60 min later" —
  the archived preliminary series has its maximum **5.703 ft at 09:06** with a
  flat top **08:48–09:24**; against the corner crest 09:44–10:06 the lag is
  **20–78 min** (38–60 min against the single maximum); corner −0.085 ft.
  See [`analysis/gauge_qc.json`](analysis/gauge_qc.json).
- "Gate: almost certainly CLOSED" is the owner's stated confidence for an
  untimed visit between the 08:24 and 08:36 entries; the ledger's 08:30 is a
  surrogate. Not visual confirmation.
- Rain this morning: MRMS catchment box mean **0.23 in** over 04:00–13:00
  local (91 of 91 frames), peak 6-min rate 0.35 in/hr at 05:26 local, before
  the flood. The fixed-base zero-drain sensitivity lifts at most 0.9 in and
  peaks before first water; see [`analysis/rain_scenarios.json`](analysis/rain_scenarios.json).
  This morning's flood is not materially rain-assisted under any of the four
  explicit assumptions.
- The public nowcast's retained day maximum of **39.0 in at 02:40 local** is
  a model output driven by a bay input of 6.68 ft NAVD88 stamped "observed"
  while the archived series had the bay at 0.2 ft
  ([`analysis/gauge_qc.json` → `nowcast_bay_input_trace`](analysis/gauge_qc.json)).
  It is not a street measurement; the tape crest was 5.62 ft (+25.2 in).
  Recorded for rejection in `data/nowcast_daymax_rejections.json`.
- Corrected four-tide figure with rain forcing and a separate report strip:
  [`analysis/event10_hydrographs.png`](analysis/event10_hydrographs.png).
