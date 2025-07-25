# Virtuoso Trading System - VPS Command Reference

## Table of Contents
1. [Service Management](#service-management)
2. [Process Monitoring](#process-monitoring)
3. [Log Management](#log-management)
4. [System Resources](#system-resources)
5. [Network & Ports](#network--ports)
6. [Application Control](#application-control)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## 🔑 Quick Reference - Most Used Commands

### Essential Daily Commands
```bash
# Check service status
sudo systemctl status virtuoso-trading

# View live logs
sudo journalctl -u virtuoso-trading -f

# Restart service
sudo systemctl restart virtuoso-trading

# Check if running
ps aux | grep python | grep main.py

# Test API health
curl http://localhost:8000/health
```

### Quick Troubleshooting
```bash
# View recent errors
sudo journalctl -u virtuoso-trading -p err -n 50

# Check ports
sudo ss -tlnp | grep 8000

# System resources
free -h && df -h

# Kill and restart
sudo systemctl stop virtuoso-trading
sudo systemctl start virtuoso-trading
```

### One-Line Status Check
```bash
# Complete system status
echo "SERVICE:" && sudo systemctl is-active virtuoso-trading && echo "PORT:" && sudo ss -tlnp | grep 8000 && echo "PROCESS:" && ps aux | grep python | grep -c main.py
```

### SSH Quick Connect
```bash
# Connect to VPS
ssh linuxuser@45.77.40.77

# Connect and check status immediately
ssh linuxuser@45.77.40.77 "sudo systemctl status virtuoso-trading"
```

---

## Service Management

### Start/Stop/Restart Service
```bash
# Start the service
sudo systemctl start virtuoso-trading

# Stop the service
sudo systemctl stop virtuoso-trading

# Restart the service
sudo systemctl restart virtuoso-trading

# Check service status
sudo systemctl status virtuoso-trading

# Enable auto-start on boot
sudo systemctl enable virtuoso-trading

# Disable auto-start
sudo systemctl disable virtuoso-trading

# Reload systemd after config changes
sudo systemctl daemon-reload
```

---

## Process Monitoring

### View Running Processes
```bash
# All processes
ps aux

# Python processes only
ps aux | grep python | grep -v grep

# Virtuoso-specific processes
ps aux | grep -E "(virtuoso|trading|main.py)" | grep -v grep

# Top CPU consumers
ps aux --sort=-%cpu | head -20

# Top memory consumers
ps aux --sort=-%mem | head -20

# Real-time process monitor
htop  # or 'top' if htop not installed

# Kill a specific process
kill <PID>
kill -9 <PID>  # Force kill

# Kill all Python processes (careful!)
pkill -f python
```

---

## Log Management

### Systemd Journal Logs
```bash
# View recent logs
sudo journalctl -u virtuoso-trading -n 100

# Follow logs in real-time
sudo journalctl -u virtuoso-trading -f

# Logs from specific time
sudo journalctl -u virtuoso-trading --since "1 hour ago"
sudo journalctl -u virtuoso-trading --since "2024-01-25 14:00"
sudo journalctl -u virtuoso-trading --since today

# Filter by priority
sudo journalctl -u virtuoso-trading -p err  # Errors only
sudo journalctl -u virtuoso-trading -p warning  # Warnings and above

# Export logs
sudo journalctl -u virtuoso-trading > virtuoso_logs.txt

# Clear old logs (careful!)
sudo journalctl --vacuum-time=7d  # Keep only 7 days
```

### Application Logs (if not using systemd)
```bash
# View logs
tail -f ~/trading/Virtuoso_ccxt/app.log
tail -n 1000 ~/trading/Virtuoso_ccxt/app.log

# Search logs
grep ERROR ~/trading/Virtuoso_ccxt/app.log
grep -i "websocket" ~/trading/Virtuoso_ccxt/app.log

# Log size
du -h ~/trading/Virtuoso_ccxt/logs/
```

---

## System Resources

### Memory Usage
```bash
# Memory overview
free -h

# Detailed memory info
cat /proc/meminfo

# Memory usage by process
ps aux --sort=-%mem | head -20

# Clear cache (if needed)
sudo sync && sudo sysctl -w vm.drop_caches=3
```

### CPU Usage
```bash
# CPU info
lscpu

# CPU usage per core
mpstat -P ALL 1

# Load average
uptime

# Process CPU usage
top -b -n 1 | head -20
```

### Disk Usage
```bash
# Disk space
df -h

# Directory sizes
du -sh ~/trading/Virtuoso_ccxt/
du -sh ~/trading/Virtuoso_ccxt/*/ | sort -h

# Find large files
find ~/trading/Virtuoso_ccxt -type f -size +100M -ls

# Cleanup old logs
find ~/trading/Virtuoso_ccxt/logs -name "*.log" -mtime +7 -delete
```

---

## Network & Ports

### Check Ports
```bash
# All listening ports
sudo ss -tlnp
sudo netstat -tlnp

# Check specific port
sudo ss -tlnp | grep 8000
sudo lsof -i :8000

# Test if port is accessible
curl http://localhost:8000/health
curl http://localhost:8000/mobile

# External connectivity test
curl -I http://45.77.40.77:8000/health
```

### Network Connections
```bash
# Active connections
ss -tan
netstat -an

# Connection count
ss -s

# Network statistics
ip -s link
```

---

## Application Control

### Manual Start (without systemd)
```bash
# Navigate to project
cd ~/trading/Virtuoso_ccxt

# Activate virtual environment
source venv311/bin/activate

# Run in foreground
python src/main.py

# Run in background
nohup python src/main.py > app.log 2>&1 &

# Run with screen
screen -S trading
python src/main.py
# Ctrl+A, D to detach
# screen -r trading to reattach
```

### Environment & Dependencies
```bash
# Check Python version
python --version

# List installed packages
pip list

# Install/Update requirements
pip install -r requirements.txt
pip install --upgrade package_name

# Virtual environment
deactivate  # Exit venv
source venv311/bin/activate  # Enter venv
```

---

## Troubleshooting

### Common Issues
```bash
# Check if service is enabled
systemctl is-enabled virtuoso-trading

# Check for port conflicts
sudo lsof -i :8000

# Check system limits
ulimit -a

# Increase file descriptor limit
ulimit -n 65536

# Check for zombie processes
ps aux | grep defunct

# System messages
dmesg | tail -50
sudo tail -f /var/log/syslog
```

### Performance Debugging
```bash
# IO statistics
iostat -x 1

# Network statistics
netstat -i
iftop  # Real-time network traffic

# Process tree
pstree -p | grep python

# Strace a process
sudo strace -p <PID>

# Check open files
lsof -p <PID>
```

---

## Maintenance

### System Updates
```bash
# Update package list
sudo apt update

# Upgrade packages
sudo apt upgrade

# Clean old packages
sudo apt autoremove
sudo apt clean
```

### Backup Commands
```bash
# Backup config
cp -r ~/trading/Virtuoso_ccxt/config ~/backup/

# Backup entire project
tar -czf virtuoso_backup_$(date +%Y%m%d).tar.gz ~/trading/Virtuoso_ccxt/

# Rsync to another server
rsync -avz ~/trading/Virtuoso_ccxt/ user@backup-server:/path/to/backup/
```

### Service Configuration
```bash
# Edit service file
sudo nano /etc/systemd/system/virtuoso-trading.service

# View service configuration
systemctl cat virtuoso-trading

# Check service logs
journalctl -xe
```

---

## Quick Status Check Script

Create this as `check_status.sh`:
```bash
#!/bin/bash
echo "=== VIRTUOSO TRADING STATUS ==="
echo
echo "Service Status:"
sudo systemctl status virtuoso-trading --no-pager | head -10
echo
echo "Running Processes:"
ps aux | grep -E "(virtuoso|trading|main.py)" | grep -v grep
echo
echo "Port Status:"
sudo ss -tlnp | grep -E "(8000|8080)"
echo
echo "Memory Usage:"
free -h
echo
echo "Recent Logs:"
sudo journalctl -u virtuoso-trading -n 10 --no-pager
```

Make it executable:
```bash
chmod +x check_status.sh
./check_status.sh
```

---

## API & Dashboard Access

### Test Endpoints
```bash
# Health check
curl http://localhost:8000/health
curl http://localhost:8000/api/health

# Mobile dashboard
curl http://localhost:8000/mobile

# API documentation
curl http://localhost:8000/docs

# Market data endpoints
curl http://localhost:8000/api/market/symbols
curl http://localhost:8000/api/market/top-symbols
curl http://localhost:8000/api/market/data/BTCUSDT

# WebSocket status
curl http://localhost:8000/api/websocket/status

# System metrics
curl http://localhost:8000/api/metrics
```

### External Access Testing
```bash
# Test from outside (replace with your IP)
curl http://45.77.40.77:8000/health
wget -O- http://45.77.40.77:8000/health

# Test with timeout
curl --max-time 5 http://45.77.40.77:8000/health

# Verbose connection test
curl -v http://45.77.40.77:8000/mobile
```

---

## Security & Firewall

### UFW Firewall Management
```bash
# Check firewall status
sudo ufw status verbose

# Allow port 8000
sudo ufw allow 8000/tcp

# Allow SSH (if not already)
sudo ufw allow 22/tcp

# Enable firewall (careful with SSH!)
sudo ufw enable

# Check specific port rule
sudo ufw status numbered | grep 8000

# Delete a rule
sudo ufw delete allow 8000/tcp
```

### SSH Key Management
```bash
# View authorized keys
cat ~/.ssh/authorized_keys

# Add new SSH key
echo "ssh-rsa YOUR_KEY_HERE" >> ~/.ssh/authorized_keys

# Change SSH permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

---

## Database & Cache Management

### SQLite Database
```bash
# Check database size
ls -lh ~/trading/Virtuoso_ccxt/data/virtuoso.db

# Backup database
cp ~/trading/Virtuoso_ccxt/data/virtuoso.db ~/backup/virtuoso_$(date +%Y%m%d).db

# View database tables (if sqlite3 installed)
sqlite3 ~/trading/Virtuoso_ccxt/data/virtuoso.db ".tables"

# Database integrity check
sqlite3 ~/trading/Virtuoso_ccxt/data/virtuoso.db "PRAGMA integrity_check;"
```

### Cache Management
```bash
# Clear application cache
rm -rf ~/trading/Virtuoso_ccxt/cache/*

# Clear Python cache
find ~/trading/Virtuoso_ccxt -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Clear pip cache
pip cache purge
```

---

## Git & Version Control

### Check Current Version
```bash
cd ~/trading/Virtuoso_ccxt
git log -1 --oneline
git status
git branch -a

# Show recent commits
git log --oneline -10

# Check for uncommitted changes
git diff --stat
```

### Update from Repository
```bash
# Fetch latest changes
git fetch origin

# Pull updates (stash local changes first)
git stash
git pull origin main
git stash pop

# Hard reset to origin (loses local changes!)
git reset --hard origin/main
```

---

## Performance Tuning

### System Limits
```bash
# View current limits
ulimit -a

# Set in current session
ulimit -n 65536  # File descriptors
ulimit -u 32768  # Max processes

# Set permanently (edit)
sudo nano /etc/security/limits.conf
# Add:
# linuxuser soft nofile 65536
# linuxuser hard nofile 65536
```

### Memory Management
```bash
# Check swap usage
swapon -s
free -h

# Add swap file (if needed)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Monitoring & Alerts

### System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop iftop

# Monitor disk I/O
sudo iotop -o

# Monitor network traffic
sudo iftop -i eth0

# Watch system stats
watch -n 1 'free -h; echo; df -h'
```

### Log Monitoring
```bash
# Watch for errors across all logs
sudo tail -f /var/log/syslog | grep -i error

# Monitor failed SSH attempts
sudo grep "Failed password" /var/log/auth.log | tail -20

# Check for OOM killer activity
sudo dmesg | grep -i "killed process"
```

---

## Data Export & Backup

### Export Data
```bash
# Export logs for analysis
sudo journalctl -u virtuoso-trading --since "7 days ago" > ~/virtuoso_logs_week.txt

# Compress logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz ~/trading/Virtuoso_ccxt/logs/

# Export metrics/reports
find ~/trading/Virtuoso_ccxt/reports -name "*.html" -mtime -7 -exec cp {} ~/export/ \;
```

### Automated Backup Script
```bash
#!/bin/bash
# Save as backup_virtuoso.sh
BACKUP_DIR=~/backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup config
cp -r ~/trading/Virtuoso_ccxt/config $BACKUP_DIR/
# Backup database
cp ~/trading/Virtuoso_ccxt/data/*.db $BACKUP_DIR/
# Backup recent logs
sudo journalctl -u virtuoso-trading --since "24 hours ago" > $BACKUP_DIR/logs.txt

# Compress
tar -czf ~/backups/virtuoso_$(date +%Y%m%d).tar.gz $BACKUP_DIR
# Clean up
rm -rf $BACKUP_DIR

echo "Backup completed: ~/backups/virtuoso_$(date +%Y%m%d).tar.gz"
```

---

## Docker Commands (if using Docker)

### Container Management
```bash
# List containers
docker ps -a

# View logs
docker logs virtuoso-trading

# Enter container
docker exec -it virtuoso-trading bash

# Restart container
docker restart virtuoso-trading

# Resource usage
docker stats virtuoso-trading
```

---

## Emergency Commands

```bash
# Stop everything
sudo systemctl stop virtuoso-trading
pkill -f python

# Restart server
sudo reboot

# Check system health
df -h && free -h && top -b -n 1 | head -10

# Emergency log cleanup
find ~/trading/Virtuoso_ccxt -name "*.log" -size +1G -delete

# Fix permission issues
sudo chown -R linuxuser:linuxuser ~/trading/Virtuoso_ccxt

# Clear system logs (if disk full)
sudo journalctl --vacuum-size=100M

# Kill resource hogs
ps aux --sort=-%mem | head -5
ps aux --sort=-%cpu | head -5
```

---

## Useful Aliases

Add to `~/.bashrc`:
```bash
alias vtrade-status='sudo systemctl status virtuoso-trading'
alias vtrade-start='sudo systemctl start virtuoso-trading'
alias vtrade-stop='sudo systemctl stop virtuoso-trading'
alias vtrade-restart='sudo systemctl restart virtuoso-trading'
alias vtrade-logs='sudo journalctl -u virtuoso-trading -f'
alias vtrade-errors='sudo journalctl -u virtuoso-trading -p err -n 50'
alias vtrade-health='curl http://localhost:8000/health'
alias vtrade-check='ps aux | grep -E "(virtuoso|trading)" | grep -v grep'
alias vtrade-ports='sudo ss -tlnp | grep -E "(8000|8080)"'
alias vtrade-cd='cd ~/trading/Virtuoso_ccxt'
```

Then reload:
```bash
source ~/.bashrc
```

---

## Cron Jobs

### View Current Cron Jobs
```bash
crontab -l
sudo crontab -l
```

### Add Automated Tasks
```bash
crontab -e
# Add these lines:

# Daily backup at 3 AM
0 3 * * * /home/linuxuser/backup_virtuoso.sh

# Check service health every 5 minutes
*/5 * * * * systemctl is-active virtuoso-trading || systemctl start virtuoso-trading

# Clean old logs weekly
0 2 * * 0 find /home/linuxuser/trading/Virtuoso_ccxt/logs -name "*.log" -mtime +30 -delete
```

---

## Advanced Debugging

### Trace System Calls
```bash
# Trace a running process
sudo strace -p $(pgrep -f "python src/main.py") -o trace.log

# Trace network calls only
sudo strace -p $(pgrep -f "python src/main.py") -e trace=network

# Time system calls
sudo strace -p $(pgrep -f "python src/main.py") -T
```

### Python Debugging
```bash
# Install Python debugger
pip install ipdb

# Run with debugger
python -m pdb src/main.py

# Profile memory usage
pip install memory_profiler
python -m memory_profiler src/main.py
```

### Network Debugging
```bash
# Capture network traffic
sudo tcpdump -i any -w capture.pcap port 8000

# Monitor HTTP traffic
sudo tcpdump -i any -A -s 0 'tcp port 8000'

# Check DNS resolution
nslookup api.bybit.com
dig api.bybit.com
```