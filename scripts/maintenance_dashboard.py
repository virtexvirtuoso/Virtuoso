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
