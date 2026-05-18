**Rain → depth at the curb (peak hourly rate during ±1.5h of high tide):**

| Peak rainfall rate | Inches added at curb |
|---|---|
| < 0.1"/hr | ~0 |
| 0.1–0.3"/hr | +1 to +2 |
| 0.3–0.5"/hr | +2 to +4 |
| 0.5–0.8"/hr | +3 to +5 |
| 0.8–1.2"/hr | +4 to +6 |
| 1.2"/hr+ | +5 to +8 (saturating around 8) |

Closed form if you want it: `depth_added ≈ 8 × tanh(peak_rate_in_per_hr)`, capped at 8".

Honest caveats: this is the *least* certain part of the model. We have only 4 events to fit, and Oct 30 (1.45"/hr) was so dominated by tide alone that the rain term is hard to isolate. The shape (saturating curve, max ~8") is physically reasonable — water spreads laterally rather than getting infinitely deep — but the exact numbers will need more events to refine. Treat as a rough rule, not a precise prediction. Less rain on the intersection center (high point) and lawn (slight slope) — subtract 2" and 4" respectively from the table values for those landmarks.

