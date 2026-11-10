#!/bin/bash
# Verifies the local scheduler's Python environment and rebuilds it when it
# is broken or out of date. Called by install_local_scheduler.sh and, on
# every tick, by local_nowcast_tick.sh.
#
# Why this exists (2026-11-03 → 2026-11-10 outage): a venv is only symlinks
# into its base interpreter. Homebrew removed python@3.14 during a routine
# upgrade, ~/.barnacle/venv/bin/python dangled, and the local arm failed
# more than 650 ticks (`missing-interpreter`) over a week. The installer
# could not repair it either: it created the venv only when the directory
# was absent. Any Homebrew minor-version turnover will do this again, so
# the environment is now disposable-by-design like the clone beside it.
#
#   ensure_local_venv.sh --check   exit 0 = ready, 1 = needs a rebuild
#   ensure_local_venv.sh           rebuild only if needed; exit 0 = ready,
#                                  69 = no environment could be built
#
# "Ready" means: the interpreter starts AND the ready-marker matches the
# hash of the checked-in requirement locks. A changed lock therefore
# rebuilds too (before this, a pin bump never reached the local arm).
# launchd runs with PATH=/usr/bin:/bin:/usr/sbin:/sbin, where `python3` is
# Apple's 3.9 — too old for the pinned stack — so the base interpreter is
# chosen explicitly and version-checked. Override with BARNACLE_PYTHON.
set -uo pipefail

BARNACLE_DIR="${BARNACLE_DIR:-$HOME/.barnacle}"
R="${BARNACLE_REPO:-$BARNACLE_DIR/repo}"
VENV="$BARNACLE_DIR/venv"
V="$VENV/bin/python"
READY="$VENV/.barnacle-ready"
MIN_MINOR=11
# Both locks are checked in and pinned. The second is a superset used by
# the forecast workflow (adds matplotlib, which the observation-analysis
# scripts run from this environment need).
LOCKS=("$R/forecast/nowcast-requirements.txt" "$R/forecast/requirements.txt")

lock_hash() {
  local lock
  for lock in "${LOCKS[@]}"; do
    [ -r "$lock" ] || return 1
  done
  # One content hash per lock, joined: path-independent and order-stable.
  shasum -a 256 "${LOCKS[@]}" | cut -d' ' -f1 | tr '\n' '-'
}

venv_ready() {
  local want
  [ -x "$V" ] || return 1
  "$V" -c 'import sys' >/dev/null 2>&1 || return 1
  want=$(lock_hash) || return 1
  [ -n "$want" ] && [ -f "$READY" ] && [ "$(cat "$READY" 2>/dev/null)" = "$want" ]
}

pick_python() {
  local candidate
  for candidate in "${BARNACLE_PYTHON:-}" /opt/homebrew/bin/python3 \
      /usr/local/bin/python3 "$(command -v python3 2>/dev/null || true)"; do
    [ -n "$candidate" ] && [ -x "$candidate" ] || continue
    if "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, $MIN_MINOR) else 1)" 2>/dev/null; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

record_old_packages() {
  # A rebuild discards anything installed by hand; leave a list behind.
  local listing
  [ -d "$VENV/lib" ] || return 0
  mkdir -p "$BARNACLE_DIR/logs" || return 0
  listing="$BARNACLE_DIR/logs/venv-packages-$(date -u +'%Y%m%dT%H%M%SZ').txt"
  find "$VENV/lib" -maxdepth 3 -name '*.dist-info' -exec basename {} .dist-info \; \
    2>/dev/null | sort > "$listing" || true
  echo "previous package list: $listing"
}

build() {
  local base want args lock
  want=$(lock_hash) || { echo "requirement locks unreadable under $R/forecast"; return 69; }
  base=$(pick_python) || {
    echo "no Python >= 3.$MIN_MINOR found (set BARNACLE_PYTHON)"; return 69; }
  echo "rebuilding $VENV from $base ($("$base" -V 2>&1))"
  record_old_packages
  rm -rf -- "${VENV:?}"
  "$base" -m venv "$VENV" || return 69
  args=()
  for lock in "${LOCKS[@]}"; do
    args+=(-r "$lock")
  done
  "$V" -m pip install --quiet --disable-pip-version-check "${args[@]}" || return 69
  "$V" -m pip check || return 69
  # Self-test: the radar decoder stack imports and the entry points compile.
  "$V" -c 'import xarray, cfgrib, eccodes' || return 69
  "$V" -m py_compile "$R/forecast/nowcast.py" \
    "$R/forecast/flood_forecast_daily.py" || return 69
  # Written last: a half-built environment is never mistaken for ready.
  printf '%s\n' "$want" > "$READY" || return 69
  echo "environment ready"
}

if [ "${1:-}" = "--check" ]; then
  venv_ready
  exit $?
fi
if venv_ready; then
  exit 0
fi
build
