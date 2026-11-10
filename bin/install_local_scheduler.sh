#!/bin/bash
# Installs the local 10-min nowcast scheduler (launchd). Reversible:
#   launchctl bootout gui/$(id -u)/com.barnacle.nowcast
#   rm ~/Library/LaunchAgents/com.barnacle.nowcast.plist
set -eu
mkdir -p ~/.barnacle/logs
[ -d ~/.barnacle/repo ] || git clone -q "https://github.com/JohnUrban/barnacle.git" ~/.barnacle/repo
# ALWAYS sync: the 2026-08-07 install cloned 42 s before bin/ existed
# on origin and never pulled — 26 days / 2,077 silent launchd failures
git -C ~/.barnacle/repo fetch -q origin main
git -C ~/.barnacle/repo reset --hard -q origin/main
# Environment: built from the checked-in locks
# (forecast/nowcast-requirements.txt + forecast/requirements.txt), with
# pip check and an import/compile self-test, by the same helper the tick
# uses to heal itself. It REBUILDS a venv whose interpreter is gone or
# whose locks changed — the old "create only if the directory is absent"
# line could not repair the 2026-11-03 Homebrew breakage.
/bin/bash ~/.barnacle/repo/bin/ensure_local_venv.sh
cat > ~/Library/LaunchAgents/com.barnacle.nowcast.plist <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.barnacle.nowcast</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string>
    <string>$HOME/.barnacle/repo/bin/local_nowcast_tick.sh</string>
  </array>
  <key>StartInterval</key><integer>600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME/.barnacle/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$HOME/.barnacle/logs/launchd.log</string>
</dict></plist>
PLIST
launchctl bootout "gui/$(id -u)/com.barnacle.nowcast" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.barnacle.nowcast.plist"
echo "installed; next tick within 10 min"
