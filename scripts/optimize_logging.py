#!/usr/bin/env python3
"""
Logging Optimization Utility for Virtuoso Trading System
Analyzes current logs and applies optimizations.
"""

import os
import sys
import gzip
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

def analyze_log_performance(logs_dir: Path = Path("src/logs")) -> dict:
    """Analyze current logging performance and patterns."""
    
    analysis = {
        'file_sizes': {},
        'log_rates': {},
        'error_patterns': {},
        'storage_usage': 0,
        'recommendations': []
    }
    
    if not logs_dir.exists():
        logs_dir = Path("logs")
    
    print(f"🔍 Analyzing logs in: {logs_dir}")
    
    # Analyze file sizes
    total_size = 0
    for log_file in logs_dir.glob("*.log*"):
        size_mb = log_file.stat().st_size / 1024 / 1024
        analysis['file_sizes'][log_file.name] = round(size_mb, 2)
        total_size += size_mb
    
    analysis['storage_usage'] = round(total_size, 2)
    
    # Analyze main app log
    app_log = logs_dir / "app.log"
    if app_log.exists():
        print(f"📊 Analyzing {app_log}")
        
        # Count log levels and patterns
        level_counts = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
        pattern_counts = {}
        
        try:
            with open(app_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
                for line in recent_lines:
                    # Count log levels
                    for level in level_counts:
                        if f'[{level}]' in line:
                            level_counts[level] += 1
                            break
                    
                    # Identify repetitive patterns
                    if 'making request to' in line.lower():
                        pattern_counts['api_requests'] = pattern_counts.get('api_requests', 0) + 1
                    elif 'websocket' in line.lower():
                        pattern_counts['websocket_msgs'] = pattern_counts.get('websocket_msgs', 0) + 1
                    elif 'cache' in line.lower():
                        pattern_counts['cache_operations'] = pattern_counts.get('cache_operations', 0) + 1
                
                analysis['log_rates'] = level_counts
                analysis['patterns'] = pattern_counts
                
        except Exception as e:
            print(f"⚠️  Error analyzing app.log: {e}")
    
    # Generate recommendations
    if analysis['storage_usage'] > 100:  # > 100MB
        analysis['recommendations'].append("Enable log compression to reduce storage usage")
    
    if analysis['log_rates'].get('DEBUG', 0) > 500:
        analysis['recommendations'].append("Reduce DEBUG log verbosity with intelligent filtering")
    
    if pattern_counts.get('api_requests', 0) > 100:
        analysis['recommendations'].append("Implement rate limiting for API request logs")
    
    if pattern_counts.get('websocket_msgs', 0) > 50:
        analysis['recommendations'].append("Filter repetitive WebSocket messages")
    
    return analysis

def compress_old_logs(logs_dir: Path = Path("src/logs"), days_old: int = 7) -> int:
    """Compress log files older than specified days."""
    
    if not logs_dir.exists():
        logs_dir = Path("logs")
    
    compressed_count = 0
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    print(f"🗜️  Compressing logs older than {days_old} days...")
    
    for log_file in logs_dir.glob("*.log*"):
        # Skip already compressed files
        if log_file.suffix == '.gz':
            continue
            
        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        
        if file_time < cutoff_date:
            compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
            
            try:
                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Verify compression worked
                if compressed_file.exists():
                    original_size = log_file.stat().st_size
                    compressed_size = compressed_file.stat().st_size
                    ratio = round((1 - compressed_size/original_size) * 100, 1)
                    
                    print(f"✅ Compressed {log_file.name}: {original_size//1024}KB → {compressed_size//1024}KB ({ratio}% reduction)")
                    
                    log_file.unlink()  # Remove original
                    compressed_count += 1
                    
            except Exception as e:
                print(f"❌ Failed to compress {log_file.name}: {e}")
    
    return compressed_count

def apply_optimized_logging():
    """Apply the optimized logging configuration."""
    
    try:
        from src.utils.optimized_logging import configure_optimized_logging
        
        print("🚀 Applying optimized logging configuration...")
        
        # Apply optimizations
        configure_optimized_logging(
            log_level="INFO",  # Reduce from DEBUG to INFO
            enable_async=True,
            enable_structured=False,  # Keep human-readable for now
            enable_compression=True,
            enable_intelligent_filtering=True
        )
        
        print("✅ Optimized logging configuration applied!")
        
    except ImportError as e:
        print(f"❌ Could not import optimized logging: {e}")
        print("Make sure you're running from the project root directory")

def cleanup_old_logs(logs_dir: Path = Path("src/logs"), keep_days: int = 30) -> int:
    """Remove very old log files to save space."""
    
    if not logs_dir.exists():
        logs_dir = Path("logs")
    
    removed_count = 0
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    print(f"🧹 Removing logs older than {keep_days} days...")
    
    for log_file in logs_dir.glob("*.log.*"):
        # Skip current logs
        if log_file.name.endswith('.log'):
            continue
            
        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        
        if file_time < cutoff_date:
            try:
                file_size = log_file.stat().st_size
                log_file.unlink()
                print(f"🗑️  Removed old log: {log_file.name} ({file_size//1024}KB)")
                removed_count += 1
            except Exception as e:
                print(f"❌ Failed to remove {log_file.name}: {e}")
    
    return removed_count

def main():
    parser = argparse.ArgumentParser(description="Optimize Virtuoso Trading System logging")
    parser.add_argument("--analyze", action="store_true", help="Analyze current logging performance")
    parser.add_argument("--compress", action="store_true", help="Compress old log files")
    parser.add_argument("--cleanup", action="store_true", help="Remove very old log files")
    parser.add_argument("--optimize", action="store_true", help="Apply optimized logging configuration")
    parser.add_argument("--all", action="store_true", help="Run all optimization steps")
    parser.add_argument("--logs-dir", type=str, default="src/logs", help="Log directory path")
    
    args = parser.parse_args()
    
    logs_dir = Path(args.logs_dir)
    
    print("🔧 Virtuoso Trading System - Logging Optimizer")
    print("=" * 50)
    
    if args.all or args.analyze:
        print("\n📊 PERFORMANCE ANALYSIS")
        print("-" * 30)
        
        analysis = analyze_log_performance(logs_dir)
        
        print(f"\n📁 Storage Usage: {analysis['storage_usage']} MB")
        print("\n📄 File Sizes:")
        for filename, size in analysis['file_sizes'].items():
            print(f"   {filename}: {size} MB")
        
        print("\n📈 Log Level Distribution:")
        for level, count in analysis['log_rates'].items():
            print(f"   {level}: {count}")
        
        if analysis.get('patterns'):
            print("\n🔄 Pattern Analysis:")
            for pattern, count in analysis['patterns'].items():
                print(f"   {pattern}: {count}")
        
        print("\n💡 Recommendations:")
        for rec in analysis['recommendations']:
            print(f"   • {rec}")
    
    if args.all or args.compress:
        print("\n🗜️  COMPRESSION")
        print("-" * 20)
        compressed = compress_old_logs(logs_dir)
        print(f"Compressed {compressed} log files")
    
    if args.all or args.cleanup:
        print("\n🧹 CLEANUP")
        print("-" * 15)
        removed = cleanup_old_logs(logs_dir)
        print(f"Removed {removed} old log files")
    
    if args.all or args.optimize:
        print("\n🚀 OPTIMIZATION")
        print("-" * 20)
        apply_optimized_logging()
    
    print("\n✅ Logging optimization complete!")

if __name__ == "__main__":
    main() 