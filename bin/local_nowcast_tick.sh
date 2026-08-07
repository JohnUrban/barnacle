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
git pull --rebase -q 2>/dev/null || { git rebase --abort 2>/dev/null; exit 0; }
"$V" forecast/nowcast.py >> ~/.barnacle/logs/tick.log 2>&1 || exit 0
python3 forecast/check_artifacts.py >/dev/null 2>&1 || exit 0
git add docs/nowcast.json
git diff --staged --quiet && exit 0
git -c user.name="barnacle-local" -c user.email="actions@users.noreply.github.com" \
  commit -q -m "nowcast $(date -u +'%Y-%m-%d %H:%M') UTC (local tick)"
for i in 1 2 3; do
  git push -q 2>/dev/null && exit 0
  git pull --rebase -q 2>/dev/null || { git rebase --abort 2>/dev/null; exit 0; }
  python3 forecast/check_artifacts.py >/dev/null 2>&1 || exit 0
done
