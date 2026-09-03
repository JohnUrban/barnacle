# Bay Ave Barnacle

A hyperlocal flood forecast for 342 Bay Avenue, Highlands NJ. An
hourly-updated public page plus event-driven flood alerts at
[johnurban.github.io/barnacle](https://johnurban.github.io/barnacle/)
predict water depth at 18 named landmarks at the property — from the
SW storm grate across Bay (first water) up through the porch deck —
using NOAA Sandy Hook tide + surge data, NWS rainfall + wind +
temperature forecasts, and the v0.10.2 model calibrated against
tape-measured flood observations (see `model/v0.10.2.md` and
`data/labeled_observations.csv`). Includes a pluvial (rain-only)
flood advisory — heavy rain floods this intersection with no tidal
contribution at all.

The system is in production. GitHub Actions runs the forecast hourly
(best-effort), refreshing the site, `forecast.json`, and per-tide pages.
ntfy push, SMTP email, and optional email-to-SMS alerts fire only when
flood risk appears, escalates, or a genuinely new same-rank event begins;
the 09:00 UTC run retains the daily archive snapshot under `docs/archive/`
but does not imply a routine morning email.

**For state-of-the-project / model spec / future work: read
[AGENTS.md](AGENTS.md) first (the charter and read order), then
[HANDOFF.md](HANDOFF.md) (2-minute snapshot); `BACKLOG.md` OPEN
LOOPS is authoritative for what's unfinished.** This README is just
a pointer.


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

The widget evolves continuously (v7.25a as of 2026-08-07 — the
version footer bumps on every edit and requires re-copying into
Scriptable); see the header comments in `docs/barnacle-widget.js`
for the current field list.
