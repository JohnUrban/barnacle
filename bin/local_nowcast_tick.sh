#!/bin/bash
# One nowcast tick from the DEDICATED clone at ~/.barnacle/repo —
# never the human's working tree (event-#7 scheduler half-A,
# 2026-08-07). Fired by launchd every 10 min while the Mac is awake;
# GH cron remains the floor when it isn't. Safe with concurrent bot
# pushes: rebase-with-gate + monotonic day-max merge.
set -u
R=~/.barnacle/repo
V=~/.barnacle/venv/bin/python
LOCK=~/.barnacle/tick.lock
[ -d "$R" ] && [ -x "$V" ] || exit 0
mkdir "$LOCK" 2>/dev/null || exit 0          # one tick at a time
trap 'rmdir "$LOCK"' EXIT
cd "$R" || exit 0
# The clone is DISPOSABLE: never let a stale local commit wedge every
# future tick. (2026-09-03->13 incident: one exhausted push-retry left
# an unpushed commit; every later pull conflicted on nowcast.json,
# aborted, exited 0 -- half-A silently dark for 10 days, including
# event #9's flood morning.) On conflict: reset to origin, continue.
git pull --rebase -q 2>/dev/null || {
  git rebase --abort 2>/dev/null
  git fetch -q origin 2>/dev/null && git reset --hard -q origin/main || exit 0
}
"$V" forecast/nowcast.py >> ~/.barnacle/logs/tick.log 2>&1 || exit 0
python3 forecast/check_artifacts.py >/dev/null 2>&1 || exit 0
git add docs/nowcast.json data/nowcast_heartbeats.csv
git diff --staged --quiet && exit 0
git -c user.name="barnacle-local" -c user.email="actions@users.noreply.github.com" \
  commit -q -m "nowcast $(date -u +'%Y-%m-%d %H:%M') UTC (local tick)"
for i in 1 2 3; do
  git push -q 2>/dev/null && exit 0
  git pull --rebase -q 2>/dev/null || {
    # conflicted mid-retry: drop this tick's commit so the NEXT tick
    # starts clean (losing one tick is fine; wedging forever is not)
    git rebase --abort 2>/dev/null
    git fetch -q origin 2>/dev/null; git reset --hard -q origin/main 2>/dev/null
    exit 0
  }
  python3 forecast/check_artifacts.py >/dev/null 2>&1 || exit 0
done
# Push retries exhausted: abandon this tick's commit for the same
# reason -- an unpushed commit here is what wedged 2026-09-03->13.
git fetch -q origin 2>/dev/null; git reset --hard -q origin/main 2>/dev/null
