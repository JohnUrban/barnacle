# Bay Ave Barnacle

A hyperlocal flood forecast for 342 Bay Avenue, Highlands NJ. A daily
email + an hourly-updated public page at
[johnurban.github.io/barnacle](https://johnurban.github.io/barnacle/)
predict water depth at 18 named landmarks at the property — from the
SW storm grate across Bay (first water) up through the porch deck —
using NOAA Sandy Hook tide + surge data, NWS rainfall + wind +
temperature forecasts, and a v0.9 model calibrated against
tape-measured flood observations (see `model/v0.9.md` and
`data/labeled_observations.csv`). Includes a pluvial (rain-only)
flood advisory — heavy rain floods this intersection with no tidal
contribution at all.

The system is in production. GitHub Actions runs the forecast each
morning, delivers an email via SMTP, publishes an HTML snapshot to
GitHub Pages, and archives both HTML + JSON copies under `docs/archive/`.

**For state-of-the-project / model spec / future work, start with
[HANDOFF.md](HANDOFF.md).** It's the authoritative document; this
README is just a pointer.


## To install on your iPhone after you push + the Action runs:
- Open johnurban.github.io/barnacle in Safari (must be Safari, not Chrome — only Safari can install PWAs on iOS)
- Tap the Share button (square with up arrow)
- Scroll down → "Add to Home Screen"
- Title defaults to "Barnacle" — keep or rename, tap Add

## To install the widget on your iPhone (after you push + the Action runs):
- Install Scriptable from the App Store (free)
- In Safari on your iPhone, visit: https://johnurban.github.io/barnacle/barnacle-widget.js (also linked from the Pages site footer once tomorrow's run lands)
- Long-press the page, Select All → Copy
- Open Scriptable → tap + (top right) → paste the code → tap the script name and rename to "Barnacle" → tap Done
- Go to your home screen, long-press an empty spot → + (top left) → search "Scriptable" → pick widget size (small 2x2 or medium 4x2) → Add Widget
- Tap the new widget → set Script: Barnacle → tap outside

## To **update** an existing widget after a refresh of `barnacle-widget.js`:
- Open Scriptable on your iPhone
- Tap the existing "Barnacle" script
- Select all the old code → delete
- Visit https://johnurban.github.io/barnacle/barnacle-widget.js in Safari → Select All → Copy
- Paste into the empty Scriptable script → Done
- The widget on your home screen will pick up the new code on its next refresh (or long-press → Edit Widget → Done to force one)

Recent refresh (2026-05-19) added: hours-to-peak, confidence ±,
"next watch" date from the look-ahead table, and a cold-conditions
hint. See widget header comments for the up-to-date list of fields
shown.
