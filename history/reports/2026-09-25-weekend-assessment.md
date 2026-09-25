# September 25–27 storm: operational assessment

Codex, 2026-09-25. Public forecast and offline-rendering assessment.
Snapshot: deployed forecast generated 2026-09-25 10:13:38 EDT; local JSON matches.
[Selected evidence](2026-09-25-weekend-assessment.json). No forecast, alert policy,
model, wind trial or social implementation changed by this assessment.

## Severity

Serious coastal flooding and disruptive wind are supported. Barnacle's tide
peaks match the NWS coastal bulletin: 7.5 ft MLLW Friday evening, 8.0 Saturday
morning, 7.8 Saturday evening and Sunday morning, then 6.7 Sunday evening.
These are gauge water elevations, not street-water depths. At the reference
curb the corresponding modeled excesses are approximately 6.2, 12.2, 9.8,
9.8 and 0 inches. Saturday's high point is about 7.7 inches underwater, SW grate
about 19.9 inches. These are model projections, not local observations.

Barnacle calls the 8.0/7.8-ft cases SEVERE by local landmark thresholds.
NWS calls them MODERATE at Sandy Hook: its thresholds are minor 6.7, moderate
7.7, major 8.7 ft MLLW. Do not equate Barnacle SEVERE with NWS major or a
historic catastrophe. The forecast merits preparation; a record-breaking
claim is not established.

Eastern Monmouth's Coastal Flood Warning runs through Sunday 3 PM, with
1–2 ft inundation in low-lying shore/tidal areas and widespread road impacts.
High Wind Warning Friday 6 PM–Sunday 6 AM: north winds 30–40 mph, gusts up to
60 mph, possible tree/power damage. These hazards support canceled outdoor
activities independent of the Bay/Central flood model.

Barnacle grid totals: Friday remaining outlook 0.15 in, Saturday 1.45, Sunday
1.68 (~3.3 combined). NWS discussion anticipates 2–4 in along northern NJ coast
across 48+ hours; coastal/wind hazards dominate the discussion. Hourly grid
rates are interval averages, not an upper bound on short rain bursts. The
outlook retains conditional compound-rain scenarios; do not present them as
guaranteed added water or calibrated street-flood probabilities. Point-forecast
period rain ranges differ from grid day totals; neither should be silently
substituted for the other without aligning issuance/window/units.

## Forecast-method disagreement is operationally material

The core/near-term curve uses observed-surge decay toward +0.53 ft with tau
36 h. At this snapshot it peaks Friday 19:30 at 7.206 ft MLLW equivalent and
Saturday 08:00 at 7.035 ft, versus the NWS-product tide table 7.5 and 8.0.
For Saturday this is about 11.6 inches of water-level difference: core curve
about 0.7 inches over the marked curb vs product tide about 12.2 inches over it.
The core horizon ends Saturday afternoon; it cannot stand in for Sunday.

This is a source/method disagreement under strengthening storm forcing, not
proof of observed error and not the old worst-product constant-lift bug. The
curve's decay cannot anticipate future surge growth from the storm. Do not
use the lower curve to discount the NWS warning or product peak. Record this
case for prospective evaluation; changing the production curve requires a
separately reviewed model/input-policy change, not an ad hoc global offset.

## Reproducible presentation defect

An offline call to `render_email` with the public 10:13 forecast produces a
TODAY label of LIGHT, while the same forecast's `day_worst` says MODERATE.
The Friday-evening NWS-product tide also says MODERATE. No delivery is needed
to reproduce this discrepancy. Account/message records are not evidence in
this public report.

`forecast/rendering.py` email subject/text/HTML use `today_regime` (core curve),
while the per-day worst summary includes NWS tide peaks. This dilutes the
warning and violates the intended shared meaning. Needs a coordinated
warning/headline parity repair; preserve date scoping and separate
estimate/forecast/scenario semantics. A broad copy rewrite or SMS-policy
change does not follow automatically. Offline social copy work is not
production repair.

## Recommended work, in order (proposal, not implemented)

1. **Repair warning/headline parity.** One day-scoped worst-pathway summary
   for every arm that carries it. Explicitly distinguish current conditions
   from the forecast peak and conditional scenarios. Reproduce this public
   snapshot across email, site, widget and notifications; record objective
   exemptions. This restores intended meaning without changing physics.
2. **Expose forecast-source disagreement.** Label the core curve as an
   observed-surge extrapolation; keep official peak markers/forecast visible.
   Explain Barnacle local impact classes vs NWS coastal categories. Show
   applicable official coastal/wind warnings distinctly from model results;
   official warnings must not be inferred from a local class label.
3. **Develop a guidance-first core-series candidate.** Prefer valid, fresh,
   hourly total-water guidance for the covered forecast hours, whether higher
   OR lower than decay. Use decay where usable guidance is unavailable or
   after its horizon, with an explicit transition and source per hour. Keep
   present observations as the present-state reference; avoid jumps at the
   observation/forecast handoff. Do not add astronomy/surge twice to a
   total-water forecast. Sparse CFW peak rows are not an hourly hydrograph:
   preserve them as explicit official peak constraints/markers until the
   hourly reconciliation is justified. Do not automatically carry peak
   corrections into low tides or spread one maximum across all hours.
4. **Validate effects on rain and all surfaces before promotion.** The bay
   curve controls drain capacity and the rain tank. Test low tides, drain-band
   crossings, compound rain, missing/stale guidance, source changes and horizon
   tails. Feed matching published curves/maps/tank calculations from an explicit
   shared source contract. Reuse reviewed outlook machinery where applicable,
   but do not blindly promote its experimental correction/tail assumptions.
   New production input precedence requires the model-version/spec/replay and
   independent-review/owner-decision checkpoint. It is not a copy-only fix.
5. **Review SMS scope separately.** Current policy is radar-nowcast imminent
   impact only; advance tide forecasts go to other channels. Consider adding
   a bounded imminent tidal-impact trigger, including rise/threshold/re-arm
   semantics. This is a proposed alert-policy change, not an approved switch
   to sending all storm forecasts by SMS. No personal delivery data are needed
   to describe or test that policy.
6. **Continue evaluation in parallel.** Preserve as-issued raw hourly guidance,
   official peaks, corrected outlook, decay baseline, rain inputs and observed
   outcomes. Run technical replay checks before release; do not wait months to
   fix misleading presentation. Longer multi-event scoring determines comparative
   skill and any later tuning. One higher forecast during a developing storm
   is not proof that higher is always better. Leave the frozen wind trial intact.

The fading assumption remains a defensible fallback; it is not a substitute
for checking available storm-aware guidance. Recommend a reviewed candidate
now, with ongoing scoring, rather than waiting passively or making an untested
live substitution during the event. These recommendations do not constitute
approval to promote a new model or alter alert policy.

## Publication scope

This sanitized report is for the public repository's `history/reports/` only.
It does not add a website page, change forecast outputs, send alerts or post to
social media. It omits private communications, delivery/account metadata,
residential landmark details and residence framing. Public NWS issuance stamps
and gauge/intersection forecasts remain as scientific provenance. Prior private
content was removed from the unpublished commit before any push.

## Primary sources checked

- [NWS CFW issued 07:33 EDT](https://api.weather.gov/products/09b8b1e7-6579-43de-9171-2bab1cb84ba6)
- [NWS discussion issued 07:44 EDT](https://api.weather.gov/products/af26e5f3-6dea-45d7-919c-7bac3f09ac06)
- [Active NWS alerts at Highlands](https://api.weather.gov/alerts/active?point=40.403,-73.99)
- [NWS point forecast](https://api.weather.gov/gridpoints/PHI/87,105/forecast)
- Deployed [forecast JSON](https://johnurban.github.io/barnacle/forecast.json)
- [NWS explanation of coastal forecasts](https://www.weather.gov/erh/coastalflood)
