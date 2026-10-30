#!/bin/bash
# Install (or remove) the AREPO autopilot launchd agent on the Mac.
#   scripts/autopilot/install.sh              install + load (checks every 30 min, and at login/wake)
#   scripts/autopilot/install.sh --uninstall  unload + remove the plist
# Sessions start only when none is running and no usage-limit reset is pending (see autopilot.py).
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
LABEL=com.arepo.autopilot
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"; echo "removed $LABEL"; exit 0
fi
mkdir -p "$HOME/.arepo/autopilot/logs" "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>$REPO/scripts/autopilot/autopilot.py</string><string>tick</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key><dict>
    <key>HOME</key><string>$HOME</string>
    <key>AREPO_AUTOPILOT_MODE</key><string>full</string>
  </dict>
  <key>StandardOutPath</key><string>$HOME/.arepo/autopilot/launchd.out</string>
  <key>StandardErrorPath</key><string>$HOME/.arepo/autopilot/launchd.err</string>
</dict></plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed $LABEL ($PLIST)"
