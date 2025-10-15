#!/bin/bash

echo "=== InfluxDB Disk Diagnostic ==="
echo "Timestamp: $(date)"
echo

# Check overall disk space
echo "=== System Disk Usage ==="
df -h

echo
echo "=== InfluxDB Directory Usage ==="
if [ -d "/var/lib/influxdb" ]; then
    sudo du -sh /var/lib/influxdb/* 2>/dev/null | sort -h
    echo
    echo "=== WAL Directory Details ==="
    sudo du -sh /var/lib/influxdb/engine/wal/* 2>/dev/null | sort -h | tail -10
else
    echo "InfluxDB directory not found at /var/lib/influxdb"
    echo "Checking alternative locations..."
    find /var -name "influxdb*" -type d 2>/dev/null
fi

echo
echo "=== InfluxDB Process Status ==="
ps aux | grep influx | grep -v grep

echo
echo "=== Bucket Retention Settings ==="
if command -v influx &> /dev/null; then
    influx bucket list --json 2>/dev/null | jq -r '.[] | "\(.name): \(.retentionRules[0].everySeconds // "infinite") seconds"' 2>/dev/null || influx bucket list 2>/dev/null
else
    echo "InfluxDB CLI not available"
fi