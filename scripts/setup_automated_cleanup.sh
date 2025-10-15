#!/bin/bash
#############################################################################
# Setup Automated Cleanup System for Virtuoso CCXT Trading System
# Configures cron jobs and maintenance schedules
#############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Setting up automated cleanup system..."

# Create config directory and default config
CONFIG_DIR="$PROJECT_ROOT/config"
mkdir -p "$CONFIG_DIR"

# Create default maintenance config if it doesn't exist
if [[ ! -f "$CONFIG_DIR/maintenance_config.json" ]]; then
    cat > "$CONFIG_DIR/maintenance_config.json" << 'EOF'
{
  "thresholds": {
    "disk_usage_warning": 80,
    "disk_usage_critical": 90,
    "log_file_max_size_mb": 500,
    "archive_retention_days": 30
  },
  "cleanup_rules": {
    "logs": {
      "retention_days": 30,
      "max_size_mb": 100,
      "compress_after_days": 7
    },
    "backups": {
      "retention_days": 14,
      "max_count": 5
    },
    "reports": {
      "retention_days": 21,
      "max_size_mb": 1000
    },
    "archives": {
      "retention_days": 60,
      "max_depth": 3
    }
  },
  "monitoring": {
    "check_interval_minutes": 60,
    "alert_cooldown_hours": 4,
    "enable_notifications": true
  },
  "vps": {
    "host": "linuxuser@5.223.63.4",
    "enable_remote_cleanup": true,
    "sync_config": true
  }
}
EOF
    echo "✅ Created default maintenance configuration"
fi

# Create log rotation config
cat > "$CONFIG_DIR/logrotate.conf" << EOF
$PROJECT_ROOT/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        # Optional: restart services if needed
        # pkill -HUP -f "python.*web_server.py" || true
    endscript
}

$PROJECT_ROOT/logs/ccxt_run.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    size 500M
    postrotate
        echo "$(date): CCXT log rotated" >> $PROJECT_ROOT/logs/rotation.log
    endscript
}
EOF

echo "✅ Created log rotation configuration"

# Create wrapper scripts for cron
cat > "$SCRIPT_DIR/cron_maintenance.sh" << EOF
#!/bin/bash
# Cron wrapper for maintenance tasks
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT"
source venv311/bin/activate 2>/dev/null || true

# Run local maintenance (excluding VPS for safety in cron)
"$SCRIPT_DIR/automated_maintenance.py" --categories logs archives reports >> "$PROJECT_ROOT/logs/cron_maintenance.log" 2>&1
EOF

cat > "$SCRIPT_DIR/cron_disk_check.sh" << EOF
#!/bin/bash
# Cron wrapper for disk usage monitoring
cd "$PROJECT_ROOT"
USAGE=\$(df -P "$PROJECT_ROOT" | awk 'NR==2 {print \$5}' | tr -d '%')

if [[ \$USAGE -gt 90 ]]; then
    echo "\$(date): CRITICAL - Disk usage \${USAGE}% - Running emergency cleanup" >> "$PROJECT_ROOT/logs/disk_monitor.log"
    "$SCRIPT_DIR/comprehensive_cleanup.sh" --local-only >> "$PROJECT_ROOT/logs/emergency_cleanup.log" 2>&1
elif [[ \$USAGE -gt 80 ]]; then
    echo "\$(date): WARNING - Disk usage \${USAGE}%" >> "$PROJECT_ROOT/logs/disk_monitor.log"
fi
EOF

chmod +x "$SCRIPT_DIR/cron_maintenance.sh"
chmod +x "$SCRIPT_DIR/cron_disk_check.sh"

echo "✅ Created cron wrapper scripts"

# Create sample crontab entries
cat > "$CONFIG_DIR/sample_crontab.txt" << EOF
# Virtuoso CCXT Automated Maintenance
# Add these entries to your crontab with: crontab -e

# Daily maintenance at 3 AM
0 3 * * * $SCRIPT_DIR/cron_maintenance.sh

# Disk usage check every 2 hours
0 */2 * * * $SCRIPT_DIR/cron_disk_check.sh

# Weekly comprehensive cleanup (Sundays at 2 AM)
0 2 * * 0 $SCRIPT_DIR/comprehensive_cleanup.sh --local-only

# Log rotation (daily at 1 AM)
0 1 * * * /usr/sbin/logrotate -s $PROJECT_ROOT/logs/logrotate.state $CONFIG_DIR/logrotate.conf

# VPS cleanup (weekly, Sundays at 4 AM) - uncomment if desired
# 0 4 * * 0 $SCRIPT_DIR/comprehensive_cleanup.sh --vps-only
EOF

echo "✅ Created sample crontab configuration"

# Create maintenance dashboard script
cat > "$SCRIPT_DIR/maintenance_dashboard.py" << 'EOF'
#!/usr/bin/env python3
"""Simple maintenance dashboard to view cleanup status"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

def get_project_root():
    return Path(__file__).parent.parent

def get_disk_usage():
    import shutil
    project_root = get_project_root()
    total, used, free = shutil.disk_usage(project_root)
    return (used / total) * 100

def get_directory_sizes():
    project_root = get_project_root()
    directories = ["logs", "archive", "reports"]
    sizes = {}

    for dir_name in directories:
        dir_path = project_root / dir_name
        if dir_path.exists():
            total_size = 0
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except (OSError, FileNotFoundError):
                        continue
            sizes[dir_name] = total_size / (1024 * 1024)  # MB
        else:
            sizes[dir_name] = 0

    return sizes

def get_recent_maintenance_logs():
    project_root = get_project_root()
    logs_dir = project_root / "logs"

    maintenance_logs = []
    if logs_dir.exists():
        for log_file in logs_dir.glob("maintenance_*.log"):
            try:
                stat = log_file.stat()
                maintenance_logs.append({
                    "file": log_file.name,
                    "size_mb": stat.st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
            except (OSError, FileNotFoundError):
                continue

    return sorted(maintenance_logs, key=lambda x: x["modified"], reverse=True)[:5]

def main():
    print("=" * 60)
    print("VIRTUOSO CCXT MAINTENANCE DASHBOARD")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Disk usage
    disk_usage = get_disk_usage()
    print(f"\nDISK USAGE: {disk_usage:.1f}%")

    if disk_usage > 90:
        print("🔴 CRITICAL: Disk usage above 90%!")
    elif disk_usage > 80:
        print("🟡 WARNING: Disk usage above 80%")
    else:
        print("🟢 OK: Disk usage within normal range")

    # Directory sizes
    sizes = get_directory_sizes()
    print("\nDIRECTORY SIZES:")
    for directory, size_mb in sizes.items():
        print(f"  {directory}: {size_mb:.1f}MB")

    # Recent maintenance
    recent_logs = get_recent_maintenance_logs()
    print("\nRECENT MAINTENANCE LOGS:")
    if recent_logs:
        for log in recent_logs:
            print(f"  {log['file']} - {log['modified'].strftime('%Y-%m-%d %H:%M')} ({log['size_mb']:.1f}MB)")
    else:
        print("  No recent maintenance logs found")

    # Configuration status
    config_path = get_project_root() / "config" / "maintenance_config.json"
    print(f"\nCONFIGURATION:")
    print(f"  Config file: {'✅ Found' if config_path.exists() else '❌ Missing'}")

    # Check if cron scripts exist
    scripts_dir = get_project_root() / "scripts"
    cron_scripts = ["cron_maintenance.sh", "cron_disk_check.sh"]
    print(f"  Cron scripts:")
    for script in cron_scripts:
        script_path = scripts_dir / script
        print(f"    {script}: {'✅ Found' if script_path.exists() else '❌ Missing'}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
EOF

chmod +x "$SCRIPT_DIR/maintenance_dashboard.py"

echo "✅ Created maintenance dashboard"

# Show summary
echo ""
echo "🎉 Automated cleanup system setup complete!"
echo ""
echo "📁 Files created:"
echo "  - $CONFIG_DIR/maintenance_config.json (configuration)"
echo "  - $CONFIG_DIR/logrotate.conf (log rotation)"
echo "  - $CONFIG_DIR/sample_crontab.txt (cron examples)"
echo "  - $SCRIPT_DIR/cron_maintenance.sh (cron wrapper)"
echo "  - $SCRIPT_DIR/cron_disk_check.sh (disk monitoring)"
echo "  - $SCRIPT_DIR/maintenance_dashboard.py (status dashboard)"
echo ""
echo "📋 Next steps:"
echo "1. Review configuration: $CONFIG_DIR/maintenance_config.json"
echo "2. Test scripts manually:"
echo "   ./scripts/automated_maintenance.py --categories logs"
echo "   ./scripts/comprehensive_cleanup.sh --dry-run --local-only"
echo "3. View maintenance dashboard:"
echo "   ./scripts/maintenance_dashboard.py"
echo "4. Setup cron jobs (optional):"
echo "   cat $CONFIG_DIR/sample_crontab.txt"
echo "   crontab -e  # Add desired entries"
echo ""
echo "⚠️  Important: Test all scripts in dry-run mode first!"
echo "   Use --dry-run flag to see what would be done"