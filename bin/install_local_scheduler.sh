#!/bin/bash
# Installs the local 10-min nowcast scheduler (launchd). Reversible:
#   launchctl bootout gui/$(id -u)/com.barnacle.nowcast
#   rm ~/Library/LaunchAgents/com.barnacle.nowcast.plist
set -eu
mkdir -p ~/.barnacle/logs
[ -d ~/.barnacle/venv ] || python3 -m venv ~/.barnacle/venv
~/.barnacle/venv/bin/pip install --quiet xarray cfgrib eccodes
[ -d ~/.barnacle/repo ] || git clone -q "https://github.com/JohnUrban/barnacle.git" ~/.barnacle/repo
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
launchctl bootout gui/$(id -u)/com.barnacle.nowcast 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.barnacle.nowcast.plist
echo "installed; next tick within 10 min"
