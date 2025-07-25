#!/usr/bin/env python3
"""
Log Analysis Diagnostic Script

This script helps distinguish between normal confluence analysis operations
and actual system errors in the trading system logs.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class LogAnalyzer:
    """Analyzes trading system logs to distinguish normal operations from errors."""
    
    def __init__(self):
        self.normal_patterns = [
            r"📊 Confluence Analysis for \w+:",
            r"Generating enhanced formatted data for \w+ \(interpretations missing\)",
            r"Successfully added enhanced data: market_interpretations",
            r"Component score calculation completed",
            r"Bias classification: \w+",
            r"Technical: \d+\.\d+ \(bullish/bearish/neutral bias\)",
            r"Volume: \d+\.\d+ \(bullish/bearish/neutral bias\)",
            r"Orderbook: \d+\.\d+ \(bullish/bearish/neutral bias\)",
            r"Orderflow: \d+\.\d+ \(bullish/bearish/neutral bias\)",
            r"Sentiment: \d+\.\d+ \(bullish/bearish/neutral bias\)",
            r"Price Structure: \d+\.\d+ \(bullish/bearish/neutral bias\)"
        ]
        
        self.error_patterns = [
            r"❌ ERROR:",
            r"System webhook alert timed out",
            r"Memory usage alert",
            r"WebSocket connection failed",
            r"API timeout",
            r"Connection error",
            r"Failed to fetch",
            r"Exception occurred",
            r"Traceback"
        ]
        
        self.warning_patterns = [
            r"⚠️ WARNING:",
            r"High memory usage",
            r"WebSocket reconnecting",
            r"API rate limit",
            r"Timeout warning"
        ]
        
        self.debug_patterns = [
            r"=== CONFLUENCE ANALYSIS PROCESS DEBUG ===",
            r"=== SYSTEM WEBHOOK ALERT DEBUG ===",
            r"=== MEMORY THRESHOLD CHECK DEBUG ===",
            r"=== WEBSOCKET RECONNECT DEBUG ===",
            r"=== FETCH TICKER DEBUG ==="
        ]
    
    def analyze_log_file(self, log_file_path: str) -> Dict[str, List[str]]:
        """Analyze a log file and categorize entries."""
        results = {
            'normal_operations': [],
            'errors': [],
            'warnings': [],
            'debug_info': [],
            'other': []
        }
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    categorized = False
                    
                    # Check for normal operations
                    for pattern in self.normal_patterns:
                        if re.search(pattern, line):
                            results['normal_operations'].append(f"Line {line_num}: {line}")
                            categorized = True
                            break
                    
                    if categorized:
                        continue
                    
                    # Check for errors
                    for pattern in self.error_patterns:
                        if re.search(pattern, line):
                            results['errors'].append(f"Line {line_num}: {line}")
                            categorized = True
                            break
                    
                    if categorized:
                        continue
                    
                    # Check for warnings
                    for pattern in self.warning_patterns:
                        if re.search(pattern, line):
                            results['warnings'].append(f"Line {line_num}: {line}")
                            categorized = True
                            break
                    
                    if categorized:
                        continue
                    
                    # Check for debug info
                    for pattern in self.debug_patterns:
                        if re.search(pattern, line):
                            results['debug_info'].append(f"Line {line_num}: {line}")
                            categorized = True
                            break
                    
                    if not categorized:
                        results['other'].append(f"Line {line_num}: {line}")
                        
        except FileNotFoundError:
            print(f"❌ Error: Log file not found: {log_file_path}")
            return results
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            return results
        
        return results
    
    def print_analysis_summary(self, results: Dict[str, List[str]], log_file: str):
        """Print a summary of the log analysis."""
        print(f"\n{'='*60}")
        print(f"📊 LOG ANALYSIS SUMMARY: {log_file}")
        print(f"{'='*60}")
        
        total_entries = sum(len(entries) for entries in results.values())
        
        print(f"\n📈 STATISTICS:")
        print(f"   Total entries analyzed: {total_entries}")
        print(f"   Normal operations: {len(results['normal_operations'])}")
        print(f"   Errors: {len(results['errors'])}")
        print(f"   Warnings: {len(results['warnings'])}")
        print(f"   Debug info: {len(results['debug_info'])}")
        print(f"   Other entries: {len(results['other'])}")
        
        # Show normal operations (these are expected)
        if results['normal_operations']:
            print(f"\n✅ NORMAL OPERATIONS (Expected behavior):")
            for entry in results['normal_operations'][:5]:  # Show first 5
                print(f"   {entry}")
            if len(results['normal_operations']) > 5:
                print(f"   ... and {len(results['normal_operations']) - 5} more normal operations")
        
        # Show errors (these need attention)
        if results['errors']:
            print(f"\n❌ ERRORS (Need attention):")
            for entry in results['errors']:
                print(f"   {entry}")
        
        # Show warnings (these should be monitored)
        if results['warnings']:
            print(f"\n⚠️ WARNINGS (Monitor closely):")
            for entry in results['warnings']:
                print(f"   {entry}")
        
        # Show debug info (enhanced debugging we added)
        if results['debug_info']:
            print(f"\n🔍 DEBUG INFO (Enhanced debugging):")
            for entry in results['debug_info']:
                print(f"   {entry}")
        
        # Provide recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if results['errors']:
            print(f"   ⚠️  {len(results['errors'])} errors detected - Immediate attention required")
            print(f"   🔧 Focus on fixing webhook timeouts, memory issues, and connection problems")
        else:
            print(f"   ✅ No errors detected - System appears healthy")
        
        if results['warnings']:
            print(f"   📊 {len(results['warnings'])} warnings - Monitor system performance")
        else:
            print(f"   ✅ No warnings detected - Good system performance")
        
        if results['normal_operations']:
            print(f"   📈 {len(results['normal_operations'])} normal operations - System functioning as expected")
        
        print(f"\n{'='*60}")

def main():
    """Main function to run the log analysis diagnostic."""
    print("🔍 Trading System Log Analysis Diagnostic")
    print("=" * 50)
    
    analyzer = LogAnalyzer()
    
    # Default log file paths to check
    log_paths = [
        "logs/trading_system.log",
        "logs/alert_manager.log", 
        "logs/monitor.log",
        "logs/websocket.log"
    ]
    
    # Check if specific log file provided as argument
    if len(sys.argv) > 1:
        log_paths = [sys.argv[1]]
    
    found_logs = []
    for log_path in log_paths:
        if Path(log_path).exists():
            found_logs.append(log_path)
    
    if not found_logs:
        print("❌ No log files found. Please specify a log file path:")
        print("   python log_analysis_diagnostic.py <log_file_path>")
        print("\nOr ensure log files exist in the default locations:")
        for path in log_paths:
            print(f"   - {path}")
        return
    
    print(f"📁 Found {len(found_logs)} log file(s) to analyze:")
    for log_path in found_logs:
        print(f"   - {log_path}")
    
    print(f"\n🔍 Analyzing logs...")
    
    for log_path in found_logs:
        results = analyzer.analyze_log_file(log_path)
        analyzer.print_analysis_summary(results, log_path)
    
    print(f"\n✅ Analysis complete!")
    print(f"💡 Remember: Confluence analysis logs are NORMAL operations, not errors.")

if __name__ == "__main__":
    main() 