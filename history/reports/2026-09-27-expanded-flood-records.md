# Expanded flood records and source recovery — 2026-09-27

Author: Codex (GPT-6). Descriptive archive work, not a production model change
or independent reply to audit 2026-09-27-a1.

## What was missing, and why

The September27 `all_anchors` comparison extended September1's curated nine-entry
figure to thirteen. It was **not an inventory query** of either observations or
the whole repo. That selection excluded real minor events, uncertain-height
events, and early reports outside `assets/observations`. John's criticism is
correct: it was incomplete as a picture of our flood experience.

The [separate expanded figure](../../assets/observations/2026-09-27/analysis/expanded_events.png)
now represents 30 registered episodes/windows, including every date John named.
The original all_anchors renderer, JSON, PNG and PDF remain byte-identical.
Unknown local heights are visibly retained without a numeric marker; negative
checks are explicitly labeled. This is not a count of 30 floods or independent
storms, and not a comprehensive census of every Highlands flood.

## Raw notes versus Claude's record

[Line-level reconciliation](../../assets/observations/2026-09-27/analysis/rawnotes-reconciliation.json)
accounts for every explicitly timed original line. The earlier comparison found
no missing timed water-height report. There were meaningful transformations:

- Reported depth ranges sometimes became a midpoint in the numeric ledger;
  the qualitative text retained the range. A midpoint is not an exact tape read.
- Sep26 evening's 21:20–21:40 onset estimate became 21:30.
- Two untimed gate visits were assigned ~21:58 Sep26 and ~08:30 Sep27 from
  surrounding entries. These are inferred timestamps, not clock readings.
- Sep26 “12:06 am” was interpreted as midday. **John confirmed this on Sep27
  and corrected the original file to “pm”.** [Confirmation](../../assets/observations/2026-09-26/rawnotes/clarifications.txt).
  Previous source/hash preserved through git and reconciliation metadata.
- Some later prose sounded more certain about gate causation/rain attribution
  than the raw account supports. Matching raw lines does not validate that prose.
- Sep26 evening “curb +0.5–1 inch” and “base of lawn step and a little up” do
  not describe the same height with current surveyed elevations. Both originals
  remain; the chart uses the explicit curb-depth bracket, not an invented average.

The capture-process gap remains real: original-style raw files were assembled
only after prompting. Most ledger batches were appended promptly when received.
Audit R1 distinguishes those two findings. Owner photos are still pending.

## April18: substantial evidence, but no anchored tape crest

**[STATED]** John's Sep27 report says this evening flood stranded and surprised
visiting guests and helped inspire Barnacle. This detail is now preserved in
[owner-history-followup](../../assets/observations/2026-09-27/analysis/owner-history-followup.txt).
I did not find an older primary guest account in the searched current files or
selected early HANDOFF revisions; absence from that search is not proof none exists.

The repo's source chain is:

| Source | What it records / limitation |
|---|---|
| model/archive/v0.1.md, lines38–41 and145 | Moderate flood, ~10 inches; erroneous claim of a lower bay tide than Apr17 plus antecedent amplification. No fixed height reference in original quoted wording. |
| model/archive/v0.2.md, lines32,134,176 | Corrected higher observed tide 7.32 vs astronomy6.02; removes the need for the earlier lower-tide explanation. This does not prove antecedent effects never occur. |
| model/archive/v0.3.md, v0.4.md, v0.5.md, v0.6.md calibration tables | Repeated ~10-inch memory alongside evolving modeled depths. Repetition is not independent measurement. Later curb attribution is not established by the earliest wording. |
| history/data/calibration_check.csv; history/data/342_bay_flood_events.csv | Apr18 hourly observed7.322, predicted6.023, modeled curb depth8.904. Modeled depth columns are not observations. |
| history/reports/flood_history_report.md:251; history/RESULTS_HANDOFF.md; history/HANDOFF.md | Recaps of that four-event calibration set and hourly retrieval. |
| model/archive/v0.7.md:219,238; v0.8.md:175 | Later six-minute gauge7.473; competing model interpretations. Saying the memory was overstated because a model predicted less is an inference, not an independent disproof. |
| assets/observations/2025-10-30/README.md:12; 2026-06-15/README.md:4 | Relative-severity memories: Apr18 among the larger earlier floods. Historical statements are not a new September ranking. |
| history/scripts/analyze.py; model/elevations.md | Calibration date selection and model/elevation context, not additional field measurements. |

**[VERIFIED: newly archived NOAA six-minute response]** Apr18 bay peak was
**7.473 ft MLLW at 21:36 EDT**; Apr17 was **6.833 at 20:24 EDT**.
The earlier 7.322/6.758 figures are hourly-product values, while v0.1's 6.25/6.41
were erroneous observed-peak references. Do not mix these quantities.

**Owner clarification later on 2026-09-27:** John recalls water level with the
lawn step or at least that high, and guests stepping into water to reach their
car. [Verbatim source](../../assets/observations/2026-04-18/owner-recollection.txt).
The expanded figure now plots **~13.7 inches above SW /4.66 NAVD88**, using
lawn-step elevation as the likely representative level. It is an open
reconstruction marker, not direct measurement. Water may have been higher;
no numeric upper bound is established. The earlier ~10-inch memory was not
securely referenced; the new named-landmark recollection makes a useful plotted
estimate possible without treating it as tape data.

The gauge-equivalent bay peak4.653 NAVD88 is close to that landmark. This is
supporting evidence, not an independent street measurement. The owner supplied
the recollection after seeing the gauge comparison; do not score it as blind
validation of the gauge-to-street transfer. Exact street crest time is unknown.

[April18 archive](../../assets/observations/2026-04-18/README.md) now exists, as
does an Apr17 companion. Neither is inserted into the frozen rain classifier.

## August2025: remembered flood, tentative August21 association

**[STATED]** John confirms an August2025 flood, without a precise date or
measurement. The older record associates sidewalk mud evidence with August21;
that date-to-evidence link remains tentative.

| Source | What it records / limitation |
|---|---|
| git 863d36bf2:HANDOFF.md, lines526–532 | May18 note: rental inspection found swirly mud stains on sidewalks, consistent with recent flooding; explicitly tentative about event/date. |
| model/archive/v0.5.md:191 | Gauge6.93 and model4–5 inches over curb; no observed depth. |
| model/archive/v0.6.md:190 | Carries the tentative mud evidence forward. |
| history/RESULTS_HANDOFF.md:156–164; git 5b87182cf:HANDOFF.md | Claims6.93 at19:00 and inferred street water from now-obsolete thresholds. Not field proof. |
| history/data/342_bay_flood_events.csv | Aug21 evening hourly peak7.607, conflicting with6.93 prose; adjacent Aug20 evening6.869 and Aug22 evening7.086. |
| forecast/nws_surge_parser.py SAMPLE_TEXT | Transcribed Aug21 NWS example predicts8.0 MLLW in the evening. It is forecast/test text, not an observed crest or pristine original issuance. |
| audits/2026-08-03-a1/01-brain-migration-distillation-auditor.md:135–145 | Flags the buried tentative evidence; did not establish a local depth. |
| BACKLOG.md confirm/deny August21 loop | Confirmation was still outstanding; new evidence belongs in observation archive, not frozen classifier. |

**[VERIFIED: newly archived NOAA response]** Aug21 six-minute peak is
**7.666 ft MLLW at 19:30 EDT**. Aug20 is6.912 and Aug22 is7.145. Thus the
6.93 claim is not the Aug21 six-minute or archived hourly daily maximum.
The cause of the historical prose error is not established. The source is
preserved; this report provides an erratum rather than rewriting old specs.

The [new August archive](../../assets/observations/2025-08-21/README.md) retains
that tentative date association explicitly. Even a high verified bay tide does
not recover a measured local depth or identify which tide left the mud.

## June14 / June15 analyses

Both dates now have reproducible field hydrographs and residual plots:
[June14](../../assets/observations/2026-06-14/analysis/README.md),
[June15](../../assets/observations/2026-06-15/analysis/README.md).
Survey elevation + observed inches/12 reconstructs each tape water level.
The expanded chart uses corner-grate peak-window means (sample spreads, not
confidence intervals): **8.413 inches above SW** June14, **11.145** June15.
These are observed-window summaries, not guaranteed exact crests.

June14 street readings remain roughly1–2 inches below converted Sandy Hook
through the sampled interval. June15 begins below the bay reference and reaches
it around the sampled crest, then sits above it as the bay recedes. The plots
support a time-dependent street/bay relationship; they do not identify a unique
wind, rain or gate cause. No coefficient has been fitted here.

Both gauge days contain 240 six-minute samples, NOAA quality `v`; some Sandy
Hook rows retain nonzero flags. Raw flags are preserved, no smoothing/deletion
applied, and Battery is checked separately for timing. This is a transparent
historical reconstruction, not a claim of complete instrument QC. Rain forcing,
as-issued forecast scoring and causal attribution are outside these figures.

## Scope still open

The requested comparison is broader, but still not a complete regional flood
inventory. Old specs also describe Oct13 2025 and Feb22–23 2026 **non-flood**
reports; those negative controls should receive source-backed episode records
before anyone calls this an exhaustive local event dataset. We have not invented
precise dates/times or added them to this flood-centered expansion. No production
consumer or Heron scoring grouping was changed. Audit R1–R7 remains OPEN and
needs an independent response; this work does not close it.
