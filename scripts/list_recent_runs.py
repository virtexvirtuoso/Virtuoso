#!/usr/bin/env python3
"""
List recent application runs from saved run info files
"""

import os
import json
import glob
from datetime import datetime
from pathlib import Path

def list_recent_runs():
    """List recent application runs"""
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / "logs"
    
    print("\n" + "="*70)
    print("VIRTUOSO TRADING SYSTEM - RECENT RUNS")
    print("="*70 + "\n")
    
    if not logs_dir.exists():
        print("❌ No logs directory found")
        return
    
    # Find all run info files
    run_info_files = sorted(glob.glob(str(logs_dir / "run_info_RUN-*.json")), reverse=True)
    
    if not run_info_files:
        print("❌ No run information files found")
        return
    
    print(f"Found {len(run_info_files)} run(s):\n")
    
    # Display information for each run
    for i, run_file in enumerate(run_info_files[:20]):  # Show last 20 runs
        try:
            with open(run_file, 'r') as f:
                run_info = json.load(f)
            
            print(f"{i+1}. Run ID: {run_info['run_id']}")
            print(f"   Started: {run_info['start_time']}")
            print(f"   PID: {run_info['pid']}")
            
            # Check if process is still running
            pid = run_info['pid']
            try:
                os.kill(pid, 0)
                print(f"   Status: 🟢 RUNNING")
            except OSError:
                print(f"   Status: 🔴 STOPPED")
            
            # Calculate age
            try:
                start_time = datetime.strptime(run_info['start_time'], '%Y-%m-%d %H:%M:%S')
                age = datetime.now() - start_time
                hours, remainder = divmod(age.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                print(f"   Age: {age.days}d {hours}h {minutes}m")
            except:
                pass
            
            print()
            
        except Exception as e:
            print(f"❌ Error reading {run_file}: {e}\n")
    
    # Check current running instance
    print("\n" + "-"*70)
    print("To check current running instance:")
    print("  python scripts/show_run_info.py")
    print("\nTo start a new instance:")
    print("  python src/main.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    list_recent_runs()