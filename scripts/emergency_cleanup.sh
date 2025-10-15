#!/bin/bash
# Emergency disk cleanup script for Virtuoso Trading System

echo "=== EMERGENCY DISK CLEANUP ==="
echo "Current disk usage:"
df -h /

echo ""
echo "Removing large backup directories (>7 days old)..."
find /home/linuxuser/trading -name "*backup*" -type d -mtime +7 -exec du -sh {} \; 2>/dev/null
find /home/linuxuser/trading -name "*backup*" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "Removing old backup files (>7 days old)..."
find /home/linuxuser/trading -name "*backup*.tar.gz" -mtime +7 -exec ls -lah {} \; 2>/dev/null
find /home/linuxuser/trading -name "*backup*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo ""
echo "Cleaning Docker system..."
docker system prune -f 2>/dev/null || echo "Docker not available or no cleanup needed"

echo ""
echo "Cleaning package cache..."
sudo apt-get clean 2>/dev/null || echo "Cannot clean package cache (no sudo access)"

echo ""
echo "Cleaning temporary files..."
rm -rf /tmp/virtuoso_* 2>/dev/null || true
rm -rf /home/linuxuser/trading/Virtuoso_ccxt/logs/*.log.* 2>/dev/null || true

echo ""
echo "After cleanup:"
df -h /

echo ""
echo "=== CLEANUP COMPLETE ==="
echo "If disk usage is still critical, consider:"
echo "1. Removing older exports: rm -rf /home/linuxuser/trading/Virtuoso_ccxt/exports/*"
echo "2. Clearing application logs: truncate -s 0 /home/linuxuser/trading/Virtuoso_ccxt/logs/*.log"
echo "3. Contacting system administrator for additional disk space"