#!/bin/bash
# Simple connection monitor for Virtuoso

LOG_FILE="/tmp/virtuoso_connections.log"

echo "Starting connection monitor..."
echo "Logging to: $LOG_FILE"

while true; do
    # Get process PID
    PID=$(pgrep -f "python.*main.py" | head -1)
    
    if [ -z "$PID" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Virtuoso process not found" >> "$LOG_FILE"
        sleep 60
        continue
    fi
    
    # Count connections
    TOTAL=$(lsof -p "$PID" 2>/dev/null | grep -c TCP)
    ESTABLISHED=$(ss -tn | grep -c ESTAB)
    TIME_WAIT=$(ss -tn | grep -c TIME-WAIT)
    BYBIT=$(ss -tn | grep ESTAB | grep -c "18\.161")
    
    # Get CPU and memory
    CPU=$(ps -p "$PID" -o %cpu= | tr -d ' ')
    MEM_KB=$(ps -p "$PID" -o rss= | tr -d ' ')
    MEM_MB=$((MEM_KB / 1024))
    
    # Log results
    echo "$(date '+%Y-%m-%d %H:%M:%S') | PID: $PID | Connections: $ESTABLISHED/$TOTAL (Bybit: $BYBIT) | TIME_WAIT: $TIME_WAIT | CPU: $CPU% | Mem: ${MEM_MB}MB" | tee -a "$LOG_FILE"
    
    # Alert on high connections
    if [ "$ESTABLISHED" -gt 100 ]; then
        echo "⚠️  WARNING: High connection count: $ESTABLISHED" | tee -a "$LOG_FILE"
    fi
    
    # Check every 60 seconds
    sleep 60
done