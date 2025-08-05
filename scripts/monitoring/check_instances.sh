#!/bin/bash
# Check for running Virtuoso instances

echo "=== Checking for Virtuoso Instances ==="
echo

# Check PID file
if [ -f /tmp/virtuoso.pid ]; then
    PID=$(cat /tmp/virtuoso.pid)
    echo "PID file exists: $PID"
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "Process $PID is running:"
        ps -fp $PID
    else
        echo "Process $PID is NOT running (stale PID file)"
    fi
else
    echo "No PID file found at /tmp/virtuoso.pid"
fi

echo
echo "=== All Python Processes ==="
ps aux | grep -E "python.*main\.py|python.*virtuoso" | grep -v grep

echo
echo "=== Process Count ==="
COUNT=$(ps aux | grep -E "python.*main\.py" | grep -v grep | wc -l)
echo "Found $COUNT Virtuoso process(es)"

if [ $COUNT -gt 1 ]; then
    echo "WARNING: Multiple instances detected!"
fi