#!/usr/bin/env python3
"""
Interactive Log Monitoring Dashboard for Virtuoso CCXT
Shows real-time log statistics and health status
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

class LogMonitorDashboard:
    def __init__(self, logs_dir, refresh_interval=5):
        self.logs_dir = Path(logs_dir)
        self.refresh_interval = refresh_interval
        self.stats = defaultdict(int)
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_dir_size(self, path):
        """Get directory size in MB"""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total / (1024 * 1024)
    
    def get_log_stats(self):
        """Gather statistics about log files"""
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'by_category': defaultdict(lambda: {'count': 0, 'size_mb': 0}),
            'large_files': [],
            'old_files': [],
            'recent_errors': [],
            'growth_rate': 0
        }
        
        # Scan all log files
        for log_file in self.logs_dir.rglob('*.log*'):
            if log_file.is_file():
                stats['total_files'] += 1
                size_mb = log_file.stat().st_size / (1024 * 1024)
                stats['total_size_mb'] += size_mb
                
                # Categorize
                if 'error' in log_file.name.lower():
                    category = 'errors'
                elif 'debug' in log_file.name.lower():
                    category = 'debug'
                elif 'test' in log_file.name.lower():
                    category = 'test'
                elif any(x in log_file.name.lower() for x in ['app', 'startup', 'service']):
                    category = 'operational'
                else:
                    category = 'other'
                
                stats['by_category'][category]['count'] += 1
                stats['by_category'][category]['size_mb'] += size_mb
                
                # Track large files
                if size_mb > 10:
                    stats['large_files'].append((log_file.name, size_mb))
                
                # Track old files
                age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
                if age_days > 7:
                    stats['old_files'].append((log_file.name, age_days))
        
        # Sort lists
        stats['large_files'].sort(key=lambda x: x[1], reverse=True)
        stats['old_files'].sort(key=lambda x: x[1], reverse=True)
        
        # Check for recent errors
        error_log = self.logs_dir / 'error.log'
        if error_log.exists():
            try:
                with open(error_log, 'r') as f:
                    lines = f.readlines()
                    stats['recent_errors'] = lines[-5:] if lines else []
            except:
                pass
        
        return stats
    
    def format_size(self, size_mb):
        """Format size for display"""
        if size_mb < 1:
            return f"{size_mb*1024:.1f} KB"
        elif size_mb < 1024:
            return f"{size_mb:.1f} MB"
        else:
            return f"{size_mb/1024:.1f} GB"
    
    def display_dashboard(self, stats):
        """Display the monitoring dashboard"""
        self.clear_screen()
        
        # Header
        print("="*80)
        print(f"{'VIRTUOSO CCXT LOG MONITOR':^80}")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Logs Directory: {self.logs_dir}")
        print("-"*80)
        
        # Overview
        print(f"\n📊 OVERVIEW")
        print(f"  Total Files: {stats['total_files']}")
        print(f"  Total Size: {self.format_size(stats['total_size_mb'])}")
        print()
        
        # Category breakdown
        print("📁 BY CATEGORY")
        for category, data in sorted(stats['by_category'].items()):
            bar_length = int(data['size_mb'] / stats['total_size_mb'] * 30) if stats['total_size_mb'] > 0 else 0
            bar = '█' * bar_length + '░' * (30 - bar_length)
            print(f"  {category:12} [{bar}] {data['count']:3} files, {self.format_size(data['size_mb']):>8}")
        print()
        
        # Warnings
        if stats['large_files'] or stats['old_files']:
            print("⚠️  WARNINGS")
            
            if stats['large_files']:
                print("  Large files (>10 MB):")
                for name, size in stats['large_files'][:3]:
                    print(f"    • {name[:40]:40} {self.format_size(size):>8}")
            
            if stats['old_files']:
                print("  Old files (>7 days):")
                for name, age in stats['old_files'][:3]:
                    print(f"    • {name[:40]:40} {age:>3} days old")
            print()
        
        # Recent errors
        if stats['recent_errors']:
            print("❌ RECENT ERRORS (last 5)")
            for error in stats['recent_errors'][-3:]:
                print(f"  {error.strip()[:75]}")
            print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS")
        if stats['total_size_mb'] > 100:
            print("  • Consider running aggressive cleanup (logs > 100 MB)")
        if len(stats['old_files']) > 10:
            print(f"  • {len(stats['old_files'])} old files detected - run cleanup")
        if stats['by_category'].get('debug', {}).get('size_mb', 0) > 20:
            print("  • Debug logs consuming significant space")
        if not any([stats['total_size_mb'] > 100, len(stats['old_files']) > 10]):
            print("  • Log health is good ✅")
        
        print()
        print("-"*80)
        print(f"Refreshing every {self.refresh_interval} seconds... (Press Ctrl+C to exit)")
    
    def run(self):
        """Run the monitoring dashboard"""
        try:
            while True:
                stats = self.get_log_stats()
                self.display_dashboard(stats)
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")
            return

def main():
    parser = argparse.ArgumentParser(description='Monitor Virtuoso CCXT logs')
    parser.add_argument('--logs-dir', default='~/Desktop/Virtuoso_ccxt/logs',
                       help='Path to logs directory')
    parser.add_argument('--refresh', type=int, default=5,
                       help='Refresh interval in seconds')
    parser.add_argument('--vps', action='store_true',
                       help='Monitor VPS logs via SSH')
    
    args = parser.parse_args()
    
    if args.vps:
        # Monitor VPS logs
        print("Connecting to VPS...")
        os.system('ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && python3 scripts/utilities/log_monitor_dashboard.py"')
    else:
        # Monitor local logs
        logs_dir = Path(args.logs_dir).expanduser()
        
        if not logs_dir.exists():
            print(f"Error: Logs directory not found: {logs_dir}")
            return
        
        dashboard = LogMonitorDashboard(logs_dir, args.refresh)
        dashboard.run()

if __name__ == '__main__':
    main()