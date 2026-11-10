#!/bin/bash
# One nowcast tick from the disposable dedicated clone. launchd invokes this
# every 10 minutes while the Mac is awake; quiet publications are coalesced
# to roughly hourly, while active radar publishes every tick.
#
# Order matters (2026-11-10): the clone syncs BEFORE the Python environment
# is checked, so a repair pushed to origin can reach an arm whose
# interpreter is broken, and a broken or out-of-date environment is rebuilt
# in place by bin/ensure_local_venv.sh instead of failing every tick (a
# Homebrew upgrade removed the venv's base interpreter on 2026-11-03 and
# the arm then failed more than 650 ticks over a week).
set -uo pipefail

BARNACLE_DIR="${HOME}/.barnacle"
R="${BARNACLE_DIR}/repo"
V="${BARNACLE_DIR}/venv/bin/python"
LOCK="${BARNACLE_DIR}/tick.lock"
LOG_DIR="${BARNACLE_DIR}/logs"
STATUS_LOG="${LOG_DIR}/tick-status.jsonl"
LOCK_STALE_SECONDS=300
HEAL_STAMP="${BARNACLE_DIR}/venv-heal.last"
HEAL_RETRY_SECONDS=3600

mkdir -p "$LOG_DIR" || exit 73
if [ -f "$STATUS_LOG" ] && [ "$(wc -c < "$STATUS_LOG")" -gt 1048576 ]; then
  mv -f "$STATUS_LOG" "${STATUS_LOG}.1"
fi

log_event() {
  # Callers pass fixed, quote-free details so each line remains valid JSON.
  printf '{"ts":"%s","arm":"local-launchd","phase":"%s","outcome":"%s","detail":"%s"}\n' \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2" "$3" >> "$STATUS_LOG"
}

fail() {
  log_event "$1" "failed" "$3"
  exit "$2"
}

[ -d "$R/.git" ] || fail preflight 69 missing-clone

if ! mkdir "$LOCK" 2>/dev/null; then
  lock_mtime=$(stat -f %m "$LOCK" 2>/dev/null || stat -c %Y "$LOCK" 2>/dev/null || echo 0)
  lock_pid=$(sed -n '1p' "$LOCK/pid" 2>/dev/null || echo "")
  lock_age=$(( $(date +%s) - lock_mtime ))
  if [ "$lock_age" -gt "$LOCK_STALE_SECONDS" ] && \
       { [ -z "$lock_pid" ] || ! kill -0 "$lock_pid" 2>/dev/null; }; then
    rm -f "$LOCK/pid"
    rmdir "$LOCK" 2>/dev/null || fail lock 75 stale-lock-takeover-failed
    mkdir "$LOCK" 2>/dev/null || fail lock 75 stale-lock-reacquire-failed
    log_event lock recovered stale-lock-taken-over
  else
    log_event lock skipped active-lock
    exit 75
  fi
fi
printf '%s\n' "$$" > "$LOCK/pid"
# Invoked indirectly by the EXIT trap below.
# shellcheck disable=SC2329
cleanup_lock() {
  rm -f "$LOCK/pid"
  rmdir "$LOCK" 2>/dev/null || true
}
trap cleanup_lock EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$R" || fail preflight 73 clone-not-readable
git fetch -q origin main || fail sync 69 fetch-failed
# This clone contains no human work. Dropping an orphan tick is safer than
# carrying it into the next run and wedging the arm.
git reset --hard -q origin/main || fail sync 69 reset-failed

# Self-healing environment. A rebuild needs the network and about a minute,
# so a failed attempt is retried at most hourly rather than every tick.
if ! /bin/bash "$R/bin/ensure_local_venv.sh" --check; then
  heal_last=$(stat -f %m "$HEAL_STAMP" 2>/dev/null || stat -c %Y "$HEAL_STAMP" 2>/dev/null || echo 0)
  if [ $(( $(date +%s) - heal_last )) -lt "$HEAL_RETRY_SECONDS" ]; then
    fail preflight 69 environment-broken-rebuild-throttled
  fi
  touch "$HEAL_STAMP"
  if /bin/bash "$R/bin/ensure_local_venv.sh" >> "${LOG_DIR}/venv-heal.log" 2>&1; then
    rm -f "$HEAL_STAMP"
    log_event preflight recovered environment-rebuilt
  else
    fail preflight 69 environment-rebuild-failed
  fi
fi

export BARNACLE_SCHEDULER_ARM="local-launchd"
# Hourly quiet publication is keyed to this arm's last COMMITTED heartbeat
# row, asked before this run appends its own. The old wall-clock rule
# (publish only when the UTC minute was below 8) skipped whole hours
# whenever the 10-minute launchd phase drifted past :08.
"$V" forecast/nowcast.py --quiet-heartbeat-due >> "${LOG_DIR}/tick.log" 2>&1
due_rc=$?
case "$due_rc" in
  0) quiet_due=1 ;;
  3) quiet_due=0 ;;
  *) fail inspect 70 quiet-due-check-failed ;;
esac
"$V" forecast/nowcast.py >> "${LOG_DIR}/tick.log" 2>&1 || \
  fail nowcast 70 nowcast-failed
"$V" forecast/check_artifacts.py >> "${LOG_DIR}/tick.log" 2>&1 || \
  fail gate 65 artifact-gate-failed

active=$("$V" -c 'import json; print(1 if json.load(open("docs/nowcast.json")).get("active") else 0)' 2>/dev/null) || \
  fail inspect 65 nowcast-json-unreadable
if [ "$active" = "0" ] && [ "$quiet_due" = "0" ]; then
  git restore docs/nowcast.json data/nowcast_heartbeats.csv
  log_event publish gated-quiet quiet-publication-coalesced
  exit 0
fi

git add docs/nowcast.json data/nowcast_heartbeats.csv
if git diff --staged --quiet; then
  log_event publish skipped no-change
  exit 0
fi
message="nowcast $(date -u +'%Y-%m-%d %H:%M') UTC (local tick)"
[ "$active" = "1" ] || message="$message [skip ci]"
git -c user.name="barnacle-local" \
    -c user.email="actions@users.noreply.github.com" \
    commit -q -m "$message" || fail commit 70 commit-failed

for attempt in 1 2 3; do
  if git push -q 2>/dev/null; then
    log_event publish ok "pushed-attempt-$attempt"
    exit 0
  fi
  git fetch -q origin main || fail sync 69 retry-fetch-failed
  if ! git rebase origin/main >/dev/null 2>&1; then
    git rebase --abort >/dev/null 2>&1 || true
    git reset --hard -q origin/main || true
    fail rebase 75 rebase-conflict-tick-dropped
  fi
  "$V" forecast/check_artifacts.py >> "${LOG_DIR}/tick.log" 2>&1 || \
    fail gate 65 post-rebase-gate-failed
done
git fetch -q origin main >/dev/null 2>&1 || true
git reset --hard -q origin/main >/dev/null 2>&1 || true
fail publish 75 push-retries-exhausted
