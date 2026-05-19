# Bay Ave Barnacle

A hyperlocal flood forecast for 342 Bay Avenue, Highlands NJ. A daily
email + a public page at
[johnurban.github.io/barnacle](https://johnurban.github.io/barnacle/)
predict water depth at 8 named landmarks at the property — from the
lowest road corner across Bay (early-warning sentinel) up through the
front porch first step — using NOAA Sandy Hook tide + surge data, NWS
rainfall + temperature forecasts, and a v0.5 model calibrated against
firsthand flood observations.

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
