#!/bin/bash
#
# Setup Alerts for Virtuoso Trading System
# Configures system monitoring with webhook notifications
#

# Check for webhook URL
if [[ -z "$SYSTEM_ALERTS_WEBHOOK_URL" ]]; then
    echo "Error: SYSTEM_ALERTS_WEBHOOK_URL environment variable not set"
    echo "Please set it in your .env file or environment"
    exit 1
fi

# Create alert script
cat > ~/virtuoso_alerts.sh << 'EOF'
#!/bin/bash

WEBHOOK_URL="$SYSTEM_ALERTS_WEBHOOK_URL"
SERVICE="virtuoso-trading"
ALERT_LOCKFILE="/tmp/virtuoso_alert.lock"
ALERT_INTERVAL=300  # 5 minutes between alerts

send_alert() {
    local message="$1"
    local alert_type="$2"
    local color="$3"
    
    # Check if we should send alert (rate limiting)
    if [[ -f "$ALERT_LOCKFILE" ]]; then
        local last_alert=$(cat "$ALERT_LOCKFILE")
        local current_time=$(date +%s)
        if (( current_time - last_alert < ALERT_INTERVAL )); then
            return
        fi
    fi
    
    # Send Discord webhook
    local payload=$(cat <<JSON
{
    "username": "Virtuoso System Monitor",
    "embeds": [{
        "title": "System Alert: $alert_type",
        "description": "$message",
        "color": $color,
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "fields": [
            {
                "name": "Server",
                "value": "$(hostname)",
                "inline": true
            },
            {
                "name": "Time",
                "value": "$(date)",
                "inline": true
            }
        ]
    }]
}
JSON
)
    
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null 2>&1
    
    # Update lockfile
    date +%s > "$ALERT_LOCKFILE"
}

# Check service status
check_service() {
    if ! systemctl is-active --quiet $SERVICE; then
        send_alert "⚠️ Virtuoso Trading service is DOWN! Attempting automatic restart..." "Service Down" "16711680"
        systemctl start $SERVICE
        sleep 10
        
        if systemctl is-active --quiet $SERVICE; then
            send_alert "✅ Service successfully restarted" "Service Recovered" "65280"
        else
            send_alert "🚨 Service restart FAILED! Manual intervention required" "Critical Error" "16711680"
        fi
    fi
}

# Check API health
check_api() {
    if systemctl is-active --quiet $SERVICE; then
        if ! curl -s -f -m 5 http://localhost:8000/health > /dev/null 2>&1; then
            send_alert "⚠️ API is not responding! Service is running but API is down" "API Error" "16776960"
            systemctl restart $SERVICE
        fi
    fi
}

# Check memory usage
check_memory() {
    local mem_percent=$(free | grep Mem | awk '{print int($3/$2 * 100.0)}')
    if (( mem_percent > 90 )); then
        send_alert "🔴 High memory usage: ${mem_percent}%" "Memory Warning" "16776960"
    fi
}

# Check disk space
check_disk() {
    local disk_percent=$(df /home | tail -1 | awk '{print int(substr($5, 1, length($5)-1))}')
    if (( disk_percent > 90 )); then
        send_alert "🔴 Low disk space: ${disk_percent}% used" "Disk Warning" "16776960"
    fi
}

# Main monitoring loop
case "${1:-all}" in
    service)
        check_service
        ;;
    api)
        check_api
        ;;
    memory)
        check_memory
        ;;
    disk)
        check_disk
        ;;
    all)
        check_service
        check_api
        check_memory
        check_disk
        ;;
esac
EOF

chmod +x ~/virtuoso_alerts.sh

# Create systemd timer for periodic checks
sudo tee /etc/systemd/system/virtuoso-alerts.service > /dev/null << EOF
[Unit]
Description=Virtuoso Trading Alert Monitor
After=network-online.target

[Service]
Type=oneshot
User=linuxuser
Environment="SYSTEM_ALERTS_WEBHOOK_URL=$SYSTEM_ALERTS_WEBHOOK_URL"
ExecStart=/home/linuxuser/virtuoso_alerts.sh all
EOF

sudo tee /etc/systemd/system/virtuoso-alerts.timer > /dev/null << EOF
[Unit]
Description=Run Virtuoso alerts every 5 minutes
Requires=virtuoso-alerts.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable virtuoso-alerts.timer
sudo systemctl start virtuoso-alerts.timer

echo "✅ Alert monitoring configured!"
echo ""
echo "Alert script: ~/virtuoso_alerts.sh"
echo "Timer status: systemctl status virtuoso-alerts.timer"
echo "Manual test: ~/virtuoso_alerts.sh all"
echo ""
echo "Alert types monitored:"
echo "- Service down/up"
echo "- API health"
echo "- High memory usage (>90%)"
echo "- Low disk space (<10% free)"