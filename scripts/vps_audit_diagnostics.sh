#!/bin/bash

echo "=== VPS Dashboard Audit - Quick Diagnostics ==="
echo "Timestamp: $(date)"
echo

echo "1. Testing VPS Service Status:"
ssh linuxuser@${VPS_HOST} "
    echo 'Main service status:'
    sudo systemctl status virtuoso.service --no-pager -l | grep -E 'Active|Main PID|Memory'
    echo
    echo 'Port listening check:'
    sudo netstat -tlnp | grep -E ':800[13]'
    echo
    echo 'Process check:'
    ps aux | grep -E 'python.*main|uvicorn' | grep -v grep
"

echo "2. Testing Cache Connectivity:"
ssh linuxuser@${VPS_HOST} "
    echo 'Memcached status:'
    sudo systemctl status memcached --no-pager | grep Active
    echo 'Memcached connectivity test:'
    echo 'stats' | timeout 3 nc localhost 11211 | head -5 || echo 'Memcached not accessible'
    echo
    echo 'Redis status (if available):'
    redis-cli ping 2>/dev/null || echo 'Redis not available'
"

echo "3. Testing Local API Endpoints from VPS:"
ssh linuxuser@${VPS_HOST} "
    echo 'Local health check:'
    curl -s -w 'Response time: %{time_total}s\n' 'http://localhost:8003/health' | tail -1
    echo
    echo 'Local dashboard data:'
    curl -s -w 'Response time: %{time_total}s\n' 'http://localhost:8003/api/dashboard/data' | tail -1
    echo
    echo 'Monitoring API (port 8001):'
    curl -s -w 'Response time: %{time_total}s\n' 'http://localhost:8001/api/monitoring/status' | tail -1 || echo 'Monitoring API failed'
"

echo "4. Testing Recent Logs:"
ssh linuxuser@${VPS_HOST} "
    echo 'Recent error logs (last 20 lines):'
    sudo journalctl -u virtuoso.service --no-pager -n 20 | grep -E 'ERROR|CRITICAL|Exception' || echo 'No recent errors in systemd logs'
    echo
    echo 'Application log check:'
    find /home/linuxuser -name '*.log' -type f -exec tail -10 {} \; 2>/dev/null | grep -E 'ERROR|Exception' | head -10 || echo 'No application logs with errors found'
"

echo "5. Resource Usage:"
ssh linuxuser@${VPS_HOST} "
    echo 'Memory usage:'
    free -h
    echo
    echo 'Disk usage:'
    df -h | grep -E '/$|home'
    echo
    echo 'CPU load:'
    uptime
"

echo "=== End of Diagnostics ==="
echo "Run this script with: ./scripts/vps_audit_diagnostics.sh"