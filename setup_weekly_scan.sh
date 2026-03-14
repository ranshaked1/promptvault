#!/bin/bash
# Installs a weekly launchd job on macOS to scan for new Claude assets.
# Run once: bash ~/Claude/setup_weekly_scan.sh

set -e

CLAUDE_HOME="$HOME/Claude"
PLIST_NAME="com.claude.vault.weekly-scan"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$CLAUDE_HOME/logs"
PYTHON3=$(which python3)

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Create the launchd plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON3}</string>
        <string>${CLAUDE_HOME}/vault.py</string>
        <string>scan</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${CLAUDE_HOME}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/weekly-scan.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/weekly-scan-error.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# Load the job
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "  Weekly scan installed!"
echo ""
echo "  Schedule: Every Monday at 9:00 AM"
echo "  Plist:    $PLIST_PATH"
echo "  Logs:     $LOG_DIR/weekly-scan.log"
echo ""
echo "  To test it now:    launchctl start $PLIST_NAME"
echo "  To uninstall:      launchctl unload $PLIST_PATH && rm $PLIST_PATH"
echo ""
