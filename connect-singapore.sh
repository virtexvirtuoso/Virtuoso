#!/bin/bash

echo "🌐 Connecting to ProtonVPN Singapore..."

# Open ProtonVPN if not already open
open -a ProtonVPN
sleep 3

# Use AppleScript to connect to Singapore
osascript << 'EOF'
tell application "ProtonVPN"
    activate
end tell

delay 2

tell application "System Events"
    tell process "ProtonVPN"
        -- Open search
        keystroke "f" using command down
        delay 1
        
        -- Type Singapore
        keystroke "Singapore"
        delay 1
        
        -- Press Enter to select
        keystroke return
        delay 1
        
        -- Try to click Connect button if available
        try
            click button "Connect" of window 1
        end try
    end tell
end tell
EOF

echo "✅ Connection command sent!"
echo "Please check ProtonVPN window to confirm connection to Singapore."