# Storm follow-up: implementation order and stopping point

Codex, 2026-09-25. Owner permits starting work and requests durable plans.
Evidence: [sanitized assessment](../reports/2026-09-25-weekend-assessment.md)
and its public-source JSON. These are repository records, not a website bulletin.
Production remains v0.10.6. This plan is not approval to promote a new model or
expand SMS eligibility. Refresh inputs before making operational statements.

## 1. Repair day-headline consistency first

Restore the existing worst-across-pathways rule; do not change curve physics.
The captured 10:13 forecast renders email TODAY LIGHT while day_worst says
MODERATE. A larger advisory tide is already available to the daily comparison.

Start in `forecast/flood_forecast_daily.py`: `compute_day_worst` already
compares product tides, tank and burst pathways; `headline_for` promotes rain
but not a higher product-tide regime. Keep the raw series-derived `today_regime`
meaning explicit; introduce/reuse a shared day-headline result with matching
source, level, event time and conditional status rather than relabeling every
field blindly. A worst forecast must not be phrased as water present now.

| Arm | Inspection / required disposition |
|---|---|
| Email subject, text and HTML | `rendering.render_email` uses `today_regime` in several locations; fix all day-headline copies and matching detail. |
| ntfy / legacy `build_sms_text` | Trace actual routing; warning and TODAY note must use the same day result. Preserve lead warning, eligibility, caps and quiet hours. |
| Widget small and medium | `docs/barnacle-widget.js` selects `forecast.today_regime`; reconcile labels, depths, source/time, not just severity. Bump footer and tell John to re-copy. |
| Landing, strip, details and day cards | Some already use day_worst. Verify each emitted result; record evidence for already-correct exemptions. Check legacy banner code reachability. |
| Outlook, per-tide pages, maps and curves | Keep source distinctions explicit. Do not move water levels to force agreement with a headline; verify captions describe the displayed state. |
| Imminent SMS | `evaluate_sms_gate` carries fresh-nowcast impact, not a day forecast. Preserve that policy; verify routing and document this objective exemption. |
| Offline social draft | Retain source/conditional meaning; do not adopt all draft public wording into production incidentally. |

Regression cases: product tide higher than curve; rain higher than tide; low-tide
rain; missing inputs; elapsed peak versus remaining day; local-midnight/DST
boundaries; warning level and depth/time from the same selected event. Use the
captured public snapshot for the reproduced mismatch. Preserve frozen model
replays and ledger bytes. Regenerate affected pages, visually inspect email/site
and widget layouts, run artifact gate, and verify deployed artifacts. Document
all arms or objective exemptions in the commit. This is a rule-restoring bug
fix, not a new model formula. Independent review is useful before shipment.

## 2. Make disagreement understandable

Show official warning lifecycle and source/horizon beside local predictions.
Distinguish NWS gauge flood classes from Barnacle local impact classes. A
one-foot discrepancy is material; neither method has won an observed skill
comparison merely because one forecasts a higher level. Avoid declaring the
core curve safe while a different source warns of serious flooding. Specify
shared wording before changing any arm; separate this from a new input policy.

## 3. Build a guidance-first core candidate separately

Recommendation: use healthy, issued hourly gauge guidance when available;
retain observed-surge decay as an explicitly labeled fallback. This is a
candidate to evaluate, not a claim that decay is always wrong or guidance
always right. Do not wait for months of scoring to investigate a known source
mismatch; do wait for review before promoting a different model.

Write a source contract first: issuance/freshness, datum conversion, hourly
coverage, observed-to-forecast seam, missing intervals, transition beyond the
last supported hour and unavailable semantics. Separate raw hourly guidance
from advisory high-tide corrections. Do not spread a worst high-tide residual
across every low tide, double-count surge, or simply choose the larger curve.
Low-tide advisory corrections remain unvalidated and need paired scoring.

Replay storm and non-storm inputs with identical rain: high/low tide, drain
capacity and plug band, tank output, burst scenario and day-worst selection.
Check chart/map/widget/headline equality for each represented state and retain
source uncertainty. New input/fallback policy requires model spec/version,
unchanged existing replay goldens where applicable, independent candidate
review and John's recorded DECISION; formula changes require new goldens too.
Do not modify the frozen wind c2 candidate to implement this work.

## 4. Keep SMS policy separate

Current SMS scope explains why a long-lead coastal warning need not send a
text. Draft an optional imminent-tidal-impact rule with concrete examples,
lead time, observed vs forecast semantics, re-arming and cap/quiet-hour
interaction. Present a recommendation to John before changing eligibility.
No new alert channel, delivery or policy is authorized by this planning note.

## 5. Preserve prospective evaluation and reviewed research

Heron's evaluator at cd17a5a14 has independent close-out a4/09 and needs a
separate integration preserving newer main coordination. No Heron repair is
pending. A/B1/B2 science still awaits informative as-issued inputs and matched
outcomes. Follow [October 9 checkpoint](2026-09-25-heron-validation-checkpoint.md),
or revisit earlier after an informative event with usable outcomes. Keep
baseline/guidance/candidate predictions paired; do not refit to the event
being scored. Wind c2's 60-day AND five-storm trial is a different clock.

## State at handoff

Only a test-isolation repair was implemented in this work unit: the accuracy
HTML test patched facade names although the renderer uses imported bindings.
It now patches the lookup sites and asserts no NOAA fetch/cache write. Four
accuracy tests pass. No production forecast, page, widget or alert change has
been made; items 1–4 are still implementation/review work.

Social doc28 independently closes Tern doc26 R1/R2/C1 at db2070ff7. Keep the
social branch local-only. Remaining owner review: representative copy, phone
cards/geography and queued-post expiry; Facebook setup comes after that.
All coordination is in HANDOFF/BACKLOG so work can resume without this chat.
