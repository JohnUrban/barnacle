# 2026-11-26 storm: evidence and queued work

Claude Fable 5.2, 2026-11-26, written during the event at John's request
("we can queue up the development you suggested, which may need more
discussion and planning anyway. You can begin to make notes and plans").
This ADDS evidence to the existing plan
[2026-09-25-storm-followup-handoff.md](2026-09-25-storm-followup-handoff.md)
and queues items; it replaces none of it. Nothing here is approved to
build. Production is v0.10.6. Numbers were pulled 2026-11-26 09:50–10:00
EST and are preliminary where they depend on the gauge.

## What happened this morning

| | |
|---|---|
| Bay peak | 8.267 ft MLLW at 08:54 EST, 2.23 ft above the astronomical tide |
| Tide table (NWS coastal flood product) | 8.1–8.3 ft from two days out |
| Barnacle's own water curve, 4 h before | 7.18 ft |
| Street | reported flooded about 09:37–09:48, 43–54 min AFTER the bay peak; dry before, with the bay above the SW grate since 06:42 (`assets/observations/2026-11-26/`) |

## Evidence by topic

### A. Two views of the same tide (existing plan sections 1–3)

The table and headline use the NWS product while one is active; the water
curve uses the observed surge fading toward the trailing mean (v0.10.6).
Tonight (21:07 EST) they read 8.6 ft and 7.0 ft. The chart and map slider
show the curve; the headline, per-tide rows and alert level show the table.

Track record of the table when the product drives it, final 12 h, 19 tides
since 2026-09-23: mean |error| about 0.17 ft, 17 of 19 within 0.25 ft;
misses 2026-09-27 08:37 (−0.66) and 2026-11-13 22:31 (+0.63)
(`data/predictions_log.csv` vs `data/observed_peaks_cache.csv`).

### B. The surge rule in a building storm (existing plan section 3)

Neither persistence nor the fade can see a surge that is still growing.
Surge this morning: +1.16 ft at 04:30, +2.23 ft at the 08:54 peak.

| From 04:30 for the 08:30 high | Value | Miss |
|---|---|---|
| Fade toward the mean (v0.10.6 rule) | 7.20 ft | −1.07 |
| Hold the surge constant (v0.10.5 and earlier) | 7.27 ft | −1.00 |
| Observed | 8.27 ft | |

So this morning the fade cost 0.07 ft and the growth cost 1.0 ft. At longer
lead the fade costs more: for tonight, from the 09:42 surge of +2.48 ft,
the fade gives about 6.7 ft and constant persistence about 7.25 ft.

Storm tides (observed at least 1.0 ft above astronomical), table error at
12–24 h lead:

| Era and source | n | Mean error | Mean abs error | Worst |
|---|---|---|---|---|
| Before 2026-09-23, persistence | 20 | −0.28 ft | 0.30 ft | −0.60 |
| Since 2026-09-23, NWS product active | 12 | −0.08 ft | 0.21 ft | −0.72 |
| Since 2026-09-23, no product (fade rule) | 19 | −0.46 ft | 0.49 ft | −1.00 |

Reading: Barnacle has always under-called storm tides at half-day lead.
With the product it now does better than it ever did. Without the product
it does worse than before, and the size of the extra bias (about 0.2 ft) is
what the fade would remove from a 1.5 ft surge over 18 h. That is
SUGGESTIVE, not established: the storms differ between eras (the pre-
September ones were 1.0–1.5 ft surges; the later set includes bigger ones).
The v0.10.6 spec itself calls the fade "a promising exploratory candidate,
not established live skill".

Queued question: should the fade be suspended while the surge is rising,
or while an NWS coastal product is active? Needs an as-issued comparison of
fade vs constant vs product on every storm tide in the log, before any
proposal. Class (a) if the formula changes.

### C. Alerts in a tidal storm (existing plan section 4, plus two defects)

1. **`last_sent_rank` never resets** (defect). `persist_alert_state` keeps a
   running maximum and nothing clears it, including an all-clear. It has
   read 4 since at least 2026-11-10. `evaluate_alert`'s "escalation" test
   (`rank > last_sent_rank`) can therefore never fire. Sends now happen only
   on appearance (rank 0 → above 0) or a changed signature. A tide first
   alerted as "street" and later upgraded to "severe" would not re-alert,
   because the signature is the tide's time and does not change. No missed
   alert is known from this, but storm forecasts upgrade over time, so the
   exposure is real. Fix is small (scope the maximum to the current
   signature / reset at all-clear); it changes when alerts fire, so it
   waits for John's go-ahead. Class (c): restores the documented rule.
2. **A second severe tide the same day is alerted late.** The signature
   names the FIRST tide in the window at the top rank. Tonight's 8.6 ft tide
   shares the rank of this morning's, so it gets no alert of its own until
   the morning tide leaves the table, 2 h after its predicted time (about
   10:28 EST; next run about 11:08). Here that leaves ten hours of notice.
   With tides twelve hours apart it always will; the weakness is that a
   HIGHER later tide at the same rank is not an escalation. Design
   question, not a bug.
3. **No day-of or imminent alert for tidal flooding.** The alert for this
   morning went out 2026-11-24 09:08 EST and nothing followed. The imminent
   rail is radar-only by design (v1 scope). With the gate closed, a tidal
   imminent alert keyed to the bay would also fire two to three hours
   before any water reaches the street, or when none does.

### D. The gate (BACKLOG open loop "Tide gate")

Today is the first recorded case of the street flooding well after the bay
peak with no rain: onset about 09:37, bay peak 08:54 and falling. Compare
2026-09-27 (first water while the bay was still rising) and 2026-09-25 PM
and 2026-09-28 AM (dry at 7.57 and 7.21 ft). A slow path through or around
a closed gate would behave this way; the gate was not seen today. Needs
today's crest and clearing times to say more.

## Queue (order is a suggestion; each needs John's go-ahead)

| # | Item | Class | Size |
|---|---|---|---|
| 1 | Fix `last_sent_rank` so escalation alerts work | (c) | small |
| 2 | Existing plan section 1: one day-headline across arms | (c) | medium |
| 3 | As-issued storm-tide comparison: fade vs constant vs product | research | medium |
| 4 | Existing plan section 3: curve follows healthy NWS guidance, fade as labeled fallback | (b), maybe (a) | large; review + DECISION |
| 5 | Alert a higher later tide at the same rank; optional imminent tidal rule | policy | discussion first |
| 6 | Gate-aware wording once the delay pattern is better observed | wording | discussion first |

## Questions for John

- For item 4, when the NWS product and the curve disagree, should every
  surface show the product's level, or both with labels (existing plan
  section 2 leans to "both, labeled")?
- For item 5, do you want a second alert when a later tide the same day is
  forecast higher, even at the same severity word?
