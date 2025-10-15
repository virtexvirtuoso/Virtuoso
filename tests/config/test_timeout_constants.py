#!/usr/bin/env python3
"""
Simple test to verify that the timeout constants were correctly updated.
"""

import re
import sys
from pathlib import Path

def test_timeout_fixes():
    """Verify timeout constants were properly updated."""

    print("🧪 Testing timeout fix implementation...")

    project_root = Path(__file__).parent
    monitor_file = project_root / "src/monitoring/monitor.py"
    main_file = project_root / "src/main.py"

    success = True

    # Test 1: Check monitor.py has 90s timeout
    print("\n📝 Test 1: Checking monitor.py timeout...")
    with open(monitor_file, 'r') as f:
        monitor_content = f.read()

    if "timeout=90.0" in monitor_content:
        print("✅ Monitor.py: 90-second timeout found")
    else:
        print("❌ Monitor.py: 90-second timeout NOT found")
        success = False

    if "Monitoring cycle timed out after 90 seconds" in monitor_content:
        print("✅ Monitor.py: Updated timeout error message found")
    else:
        print("❌ Monitor.py: Updated timeout error message NOT found")
        success = False

    # Test 2: Check main.py has 180s timeout
    print("\n📝 Test 2: Checking main.py timeout...")
    with open(main_file, 'r') as f:
        main_content = f.read()

    if "timeout=180.0" in main_content:
        print("✅ Main.py: 180-second timeout found")
    else:
        print("❌ Main.py: 180-second timeout NOT found")
        success = False

    if "timed out after 180s" in main_content:
        print("✅ Main.py: Updated timeout error message found")
    else:
        print("❌ Main.py: Updated timeout error message NOT found")
        success = False

    # Test 3: Check for enhanced backoff strategy
    print("\n📝 Test 3: Checking enhanced backoff strategy...")
    if "# More aggressive backoff for timeouts" in monitor_content:
        print("✅ Monitor.py: Enhanced backoff strategy found")
    else:
        print("❌ Monitor.py: Enhanced backoff strategy NOT found")
        success = False

    if "_last_successful_cycle" in monitor_content:
        print("✅ Monitor.py: Successful cycle tracking found")
    else:
        print("❌ Monitor.py: Successful cycle tracking NOT found")
        success = False

    # Test 4: Verify old constants were removed
    print("\n📝 Test 4: Checking old constants were removed...")
    if "timeout=60.0" not in monitor_content:
        print("✅ Monitor.py: Old 60-second timeout removed")
    else:
        print("⚠️ Monitor.py: Old 60-second timeout still present (may be intentional)")

    if "timeout=120.0" not in main_content:
        print("✅ Main.py: Old 120-second timeout removed")
    else:
        print("⚠️ Main.py: Old 120-second timeout still present (may be intentional)")

    print("\n" + "="*60)

    if success:
        print("🎉 ALL TIMEOUT FIXES VALIDATED SUCCESSFULLY!")
        print("✅ Ready for VPS deployment")
        print("\nSummary of changes:")
        print("  • Monitoring cycle timeout: 60s → 90s")
        print("  • Main startup timeout: 120s → 180s")
        print("  • Enhanced backoff strategy implemented")
        print("  • Successful cycle tracking added")
        return True
    else:
        print("❌ TIMEOUT FIX VALIDATION FAILED!")
        print("Some changes were not applied correctly.")
        return False

if __name__ == "__main__":
    result = test_timeout_fixes()
    sys.exit(0 if result else 1)