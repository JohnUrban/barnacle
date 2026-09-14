#!/bin/bash
# Mac-hosted deployment of the GitHub-independent public freshness
# watchdog (audit 2026-09-14-a1, H5/M5 residual). Runs every 15 min
# via launchd (com.barnacle.watchdog); checks the PUBLIC forecast/
# nowcast artifacts and workflow history and notifies ntfy when
# Barnacle goes quiet. Coverage caveat, documented honestly: a
# sleeping Mac is a sleeping watchdog — daytime/awake coverage only;
# the forever home is an always-on box (Pi / VPS).
#
# The ntfy topic lives in ~/.barnacle/watchdog_topic (one line,
# NEVER committed); without it the check still runs and logs, but
# cannot notify.
set -u
R="${BARNACLE_REPO:-$HOME/.barnacle/repo}"
LOG="$HOME/.barnacle/logs/watchdog.log"
mkdir -p "$HOME/.barnacle/logs" || exit 73
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 524288 ]; then
  mv -f "$LOG" "${LOG}.1"
fi
TOPIC=""
if [ -f "$HOME/.barnacle/watchdog_topic" ]; then
  TOPIC="$(head -1 "$HOME/.barnacle/watchdog_topic" | tr -d '[:space:]')"
fi
{
  echo "--- watchdog tick $(date -u +'%Y-%m-%dT%H:%M:%SZ') topic=$([ -n "$TOPIC" ] && echo set || echo MISSING)"
  WATCHDOG_NTFY_TOPIC="$TOPIC" \
  WATCHDOG_STATE_PATH="$HOME/.barnacle/watchdog_state.json" \
    /usr/bin/env python3 "$R/bin/public_health_watchdog.py" --notify
  echo "exit=$?"
} >> "$LOG" 2>&1
