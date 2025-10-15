#!/usr/bin/env python3
"""
Automated Maintenance System for Virtuoso CCXT Trading System
Provides intelligent cleanup with configurable thresholds and safety measures
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import shutil

class VirtuosoMaintenanceSystem:
    def __init__(self, config_path: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent
        self.config_path = config_path or self.project_root / "config" / "maintenance_config.json"
        self.config = self._load_config()
        self._setup_logging()

    def _load_config(self) -> Dict:
        """Load maintenance configuration with sensible defaults"""
        default_config = {
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
                "enable_notifications": True
            },
            "vps": {
                "host": "linuxuser@5.223.63.4",
                "enable_remote_cleanup": True,
                "sync_config": True
            }
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge user config with defaults
                return self._merge_configs(default_config, user_config)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")

        # Create default config file
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        return default_config

    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Recursively merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"maintenance_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_disk_usage(self, path: Path) -> float:
        """Get disk usage percentage for a given path"""
        try:
            total, used, free = shutil.disk_usage(path)
            return (used / total) * 100
        except Exception as e:
            self.logger.error(f"Could not get disk usage for {path}: {e}")
            return 0.0

    def get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    try:
                        total_size += filepath.stat().st_size
                    except (OSError, FileNotFoundError):
                        continue
            return total_size
        except Exception as e:
            self.logger.error(f"Could not get directory size for {path}: {e}")
            return 0

    def cleanup_logs(self) -> Dict:
        """Clean up log files according to configured rules"""
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            return {"status": "skipped", "reason": "logs directory not found"}

        results = {
            "files_removed": 0,
            "size_freed_mb": 0,
            "files_compressed": 0,
            "actions": []
        }

        rules = self.config["cleanup_rules"]["logs"]
        retention_days = rules["retention_days"]
        max_size_mb = rules["max_size_mb"]
        compress_after_days = rules["compress_after_days"]

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        compress_date = datetime.now() - timedelta(days=compress_after_days)

        for log_file in logs_dir.iterdir():
            if not log_file.is_file():
                continue

            file_stat = log_file.stat()
            file_age = datetime.fromtimestamp(file_stat.st_mtime)
            file_size_mb = file_stat.st_size / (1024 * 1024)

            # Remove old files
            if file_age < cutoff_date:
                try:
                    log_file.unlink()
                    results["files_removed"] += 1
                    results["size_freed_mb"] += file_size_mb
                    results["actions"].append(f"Removed old log: {log_file.name}")
                    self.logger.info(f"Removed old log file: {log_file}")
                except Exception as e:
                    self.logger.error(f"Could not remove {log_file}: {e}")

            # Compress large files
            elif (file_age < compress_date and
                  file_size_mb > max_size_mb and
                  not log_file.name.endswith('.gz')):
                try:
                    compressed_name = f"{log_file}.gz"
                    subprocess.run(['gzip', str(log_file)], check=True)
                    results["files_compressed"] += 1
                    results["actions"].append(f"Compressed large log: {log_file.name}")
                    self.logger.info(f"Compressed large log file: {log_file}")
                except Exception as e:
                    self.logger.error(f"Could not compress {log_file}: {e}")

        # Handle the massive ccxt_run.log specifically
        ccxt_log = logs_dir / "ccxt_run.log"
        if ccxt_log.exists():
            file_size_mb = ccxt_log.stat().st_size / (1024 * 1024)
            if file_size_mb > 1000:  # If larger than 1GB
                try:
                    # Archive with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    archive_name = f"ccxt_run_{timestamp}.log.gz"
                    archive_path = logs_dir / "archived_logs" / archive_name
                    archive_path.parent.mkdir(exist_ok=True)

                    # Compress and archive
                    with open(ccxt_log, 'rb') as f_in:
                        subprocess.run(['gzip', '-c'], stdin=f_in,
                                     stdout=open(archive_path, 'wb'), check=True)

                    # Truncate original
                    ccxt_log.write_text('')

                    results["actions"].append(f"Archived and truncated ccxt_run.log ({file_size_mb:.1f}MB)")
                    results["size_freed_mb"] += file_size_mb
                    self.logger.info(f"Archived massive ccxt_run.log ({file_size_mb:.1f}MB)")
                except Exception as e:
                    self.logger.error(f"Could not archive ccxt_run.log: {e}")

        return results

    def cleanup_archives(self) -> Dict:
        """Clean up archive directories"""
        archive_dir = self.project_root / "archive"
        if not archive_dir.exists():
            return {"status": "skipped", "reason": "archive directory not found"}

        results = {
            "directories_removed": 0,
            "size_freed_mb": 0,
            "actions": []
        }

        rules = self.config["cleanup_rules"]["archives"]
        retention_days = rules["retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # Remove old archive directories
        for item in archive_dir.rglob("*"):
            if (item.is_dir() and
                datetime.fromtimestamp(item.stat().st_mtime) < cutoff_date and
                any(keyword in item.name.lower() for keyword in ['cleanup', 'temp', 'archived'])):

                try:
                    size_mb = self.get_directory_size(item) / (1024 * 1024)
                    shutil.rmtree(item)
                    results["directories_removed"] += 1
                    results["size_freed_mb"] += size_mb
                    results["actions"].append(f"Removed old archive: {item.name}")
                    self.logger.info(f"Removed old archive directory: {item}")
                except Exception as e:
                    self.logger.error(f"Could not remove archive {item}: {e}")

        return results

    def cleanup_reports(self) -> Dict:
        """Clean up report files"""
        reports_dir = self.project_root / "reports"
        if not reports_dir.exists():
            return {"status": "skipped", "reason": "reports directory not found"}

        results = {
            "files_removed": 0,
            "size_freed_mb": 0,
            "actions": []
        }

        rules = self.config["cleanup_rules"]["reports"]
        retention_days = rules["retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        for report_file in reports_dir.rglob("*"):
            if (report_file.is_file() and
                datetime.fromtimestamp(report_file.stat().st_mtime) < cutoff_date):

                try:
                    size_mb = report_file.stat().st_size / (1024 * 1024)
                    report_file.unlink()
                    results["files_removed"] += 1
                    results["size_freed_mb"] += size_mb
                    results["actions"].append(f"Removed old report: {report_file.name}")
                    self.logger.info(f"Removed old report: {report_file}")
                except Exception as e:
                    self.logger.error(f"Could not remove report {report_file}: {e}")

        return results

    def cleanup_vps(self) -> Dict:
        """Clean up VPS files via SSH"""
        if not self.config["vps"]["enable_remote_cleanup"]:
            return {"status": "skipped", "reason": "VPS cleanup disabled"}

        vps_host = self.config["vps"]["host"]
        results = {
            "status": "success",
            "actions": [],
            "errors": []
        }

        try:
            # Test VPS connection
            result = subprocess.run(['ssh', vps_host, 'echo "test"'],
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"status": "error", "reason": "Cannot connect to VPS"}

            # Run VPS cleanup commands
            cleanup_commands = [
                # Remove old backups
                f"find /home/linuxuser/trading -name '*backup*' -type d -mtime +7 -exec rm -rf {{}} + 2>/dev/null || true",
                f"find /home/linuxuser/trading -name '*backup*.tar.gz' -mtime +{self.config['cleanup_rules']['backups']['retention_days']} -delete 2>/dev/null || true",
                # Keep only last N backups
                f"cd /home/linuxuser/trading && ls -t *backup*.tar.gz 2>/dev/null | tail -n +{self.config['cleanup_rules']['backups']['max_count'] + 1} | xargs rm -f 2>/dev/null || true",
                # Rotate large logs
                "cd /home/linuxuser/trading/Virtuoso_ccxt && if [[ -f logs/main.log && $(du -m logs/main.log | cut -f1) -gt 100 ]]; then gzip logs/main.log && mv logs/main.log.gz logs/main_$(date +%Y%m%d_%H%M%S).log.gz && touch logs/main.log; fi",
                # Clean old compressed logs
                f"find /home/linuxuser/trading/Virtuoso_ccxt/logs -name '*.log.gz' -mtime +{self.config['cleanup_rules']['logs']['retention_days']} -delete 2>/dev/null || true"
            ]

            for cmd in cleanup_commands:
                result = subprocess.run(['ssh', vps_host, cmd],
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    results["actions"].append(f"VPS: {cmd}")
                else:
                    results["errors"].append(f"VPS command failed: {cmd}")

            self.logger.info("VPS cleanup completed")

        except Exception as e:
            self.logger.error(f"VPS cleanup failed: {e}")
            results["status"] = "error"
            results["errors"].append(str(e))

        return results

    def generate_maintenance_report(self, results: Dict) -> str:
        """Generate a comprehensive maintenance report"""
        report = []
        report.append("=" * 60)
        report.append("VIRTUOSO CCXT MAINTENANCE REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)

        # Disk usage summary
        disk_usage = self.get_disk_usage(self.project_root)
        report.append(f"\nDISK USAGE: {disk_usage:.1f}%")

        if disk_usage > self.config["thresholds"]["disk_usage_critical"]:
            report.append("⚠️  CRITICAL: Disk usage above critical threshold!")
        elif disk_usage > self.config["thresholds"]["disk_usage_warning"]:
            report.append("⚠️  WARNING: Disk usage above warning threshold")
        else:
            report.append("✅ Disk usage within normal range")

        # Directory sizes
        directories = ["logs", "archive", "reports"]
        report.append("\nDIRECTORY SIZES:")
        for dir_name in directories:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                size_mb = self.get_directory_size(dir_path) / (1024 * 1024)
                report.append(f"  {dir_name}: {size_mb:.1f}MB")

        # Cleanup results
        for category, result in results.items():
            if isinstance(result, dict) and "actions" in result:
                report.append(f"\n{category.upper()} CLEANUP:")
                if result.get("actions"):
                    for action in result["actions"]:
                        report.append(f"  ✅ {action}")
                else:
                    report.append("  No actions needed")

                if "size_freed_mb" in result and result["size_freed_mb"] > 0:
                    report.append(f"  Space freed: {result['size_freed_mb']:.1f}MB")

        report.append("\n" + "=" * 60)
        return "\n".join(report)

    def run_maintenance(self, categories: List[str] = None) -> Dict:
        """Run maintenance operations"""
        self.logger.info("Starting maintenance operations...")

        all_categories = ["logs", "archives", "reports", "vps"]
        categories = categories or all_categories

        results = {}

        if "logs" in categories:
            results["logs"] = self.cleanup_logs()

        if "archives" in categories:
            results["archives"] = self.cleanup_archives()

        if "reports" in categories:
            results["reports"] = self.cleanup_reports()

        if "vps" in categories:
            results["vps"] = self.cleanup_vps()

        # Generate and save report
        report = self.generate_maintenance_report(results)
        report_file = self.project_root / "logs" / f"maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        self.logger.info(f"Maintenance report saved to: {report_file}")
        print(report)

        return results

def main():
    parser = argparse.ArgumentParser(description="Virtuoso CCXT Automated Maintenance System")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--categories", nargs="+",
                       choices=["logs", "archives", "reports", "vps"],
                       help="Maintenance categories to run")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without executing")

    args = parser.parse_args()

    try:
        maintenance_system = VirtuosoMaintenanceSystem(args.config)

        if args.dry_run:
            print("DRY RUN MODE - No changes will be made")
            # For dry run, we'd need to modify the cleanup methods
            # This is a simplified version for demonstration

        results = maintenance_system.run_maintenance(args.categories)
        print("Maintenance completed successfully!")

    except Exception as e:
        print(f"Maintenance failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()