#!/usr/bin/env python3
"""
Simple Session Cleanup Validation

This script validates the session cleanup fix by analyzing the source code directly
without importing the complex modules that may have dependency issues.
"""

import re
from pathlib import Path

def analyze_alert_manager_cleanup():
    """Analyze AlertManager cleanup implementation"""
    print("🔍 Analyzing AlertManager session cleanup implementation...")

    alert_manager_file = Path("src/monitoring/alert_manager.py")
    if not alert_manager_file.exists():
        print("❌ AlertManager file not found")
        return False

    content = alert_manager_file.read_text()

    # Check if cleanup method exists
    cleanup_match = re.search(r'async def cleanup\(self\):(.*?)(?=^\s{4}def|\Z)', content, re.MULTILINE | re.DOTALL)
    if not cleanup_match:
        print("❌ cleanup() method not found")
        return False

    cleanup_code = cleanup_match.group(1)

    # Check if stop method exists
    stop_match = re.search(r'async def stop\(self\):(.*?)(?=^\s{4}def|\Z)', content, re.MULTILINE | re.DOTALL)
    if not stop_match:
        print("❌ stop() method not found")
        return False

    stop_code = stop_match.group(1)

    # Analyze what each method does
    print("\n📋 Cleanup method analysis:")

    # Check if cleanup closes _client_session
    if "_client_session" in cleanup_code and "close" in cleanup_code:
        print("✅ cleanup() closes _client_session")
        cleanup_closes_client = True
    else:
        print("❌ cleanup() does NOT close _client_session")
        cleanup_closes_client = False

    # Check if cleanup calls stop
    if "await self.stop()" in cleanup_code or "self.stop()" in cleanup_code:
        print("✅ cleanup() calls stop()")
        cleanup_calls_stop = True
    else:
        print("❌ cleanup() does NOT call stop()")
        cleanup_calls_stop = False

    print("\n📋 Stop method analysis:")

    # Check if stop closes _client_session
    if "_client_session" in stop_code and "close" in stop_code:
        print("✅ stop() closes _client_session")
        stop_closes_client = True
    else:
        print("❌ stop() does NOT close _client_session")
        stop_closes_client = False

    # Summary
    print("\n📊 AlertManager Session Cleanup Summary:")
    print(f"  - cleanup() closes _client_session: {'✅' if cleanup_closes_client else '❌'}")
    print(f"  - cleanup() calls stop(): {'✅' if cleanup_calls_stop else '❌'}")
    print(f"  - stop() closes _client_session: {'✅' if stop_closes_client else '❌'}")

    # The fix is correct if either:
    # 1. cleanup() closes _client_session directly, OR
    # 2. cleanup() calls stop() which closes _client_session
    fix_correct = cleanup_closes_client or (cleanup_calls_stop and stop_closes_client)

    if fix_correct:
        print("✅ PASS: AlertManager session cleanup is correctly implemented")
    else:
        print("❌ FAIL: AlertManager session cleanup has issues")

    return fix_correct

def analyze_main_cleanup_sequence():
    """Analyze main.py cleanup sequence"""
    print("\n🔍 Analyzing main.py cleanup sequence...")

    main_file = Path("src/main.py")
    if not main_file.exists():
        print("❌ main.py file not found")
        return False

    content = main_file.read_text()

    # Find cleanup_all_components function
    cleanup_func_match = re.search(r'async def cleanup_all_components\(\):(.*?)(?=^async def|\Z)', content, re.MULTILINE | re.DOTALL)
    if not cleanup_func_match:
        print("❌ cleanup_all_components() function not found")
        return False

    cleanup_func_code = cleanup_func_match.group(1)

    print("\n📋 Main cleanup sequence analysis:")

    # Check what alert manager methods are called
    alert_stop_called = "alert_manager.stop()" in cleanup_func_code
    alert_cleanup_called = "alert_manager.cleanup()" in cleanup_func_code

    print(f"  - Calls alert_manager.stop(): {'✅' if alert_stop_called else '❌'}")
    print(f"  - Calls alert_manager.cleanup(): {'✅' if alert_cleanup_called else '❌'}")

    # Check the order if both are called
    if alert_stop_called and alert_cleanup_called:
        stop_pos = cleanup_func_code.find("alert_manager.stop()")
        cleanup_pos = cleanup_func_code.find("alert_manager.cleanup()")

        if stop_pos < cleanup_pos and stop_pos != -1:
            print("✅ Correct order: stop() is called before cleanup()")
            order_correct = True
        else:
            print("❌ Incorrect order: cleanup() is called before stop()")
            order_correct = False
    elif alert_stop_called:
        print("✅ Only stop() is called (sufficient)")
        order_correct = True
    elif alert_cleanup_called:
        print("⚠️  Only cleanup() is called (may not close _client_session)")
        order_correct = False
    else:
        print("❌ Neither stop() nor cleanup() is called")
        order_correct = False

    return alert_stop_called or order_correct

def analyze_trade_executor():
    """Analyze TradeExecutor session management"""
    print("\n🔍 Analyzing TradeExecutor session management...")

    trade_executor_file = Path("src/trade_execution/trade_executor.py")
    if not trade_executor_file.exists():
        print("❌ TradeExecutor file not found")
        return False

    content = trade_executor_file.read_text()

    # Check if close method exists and closes session
    close_match = re.search(r'async def close\(self\):(.*?)(?=^\s{4}def|\Z)', content, re.MULTILINE | re.DOTALL)
    if not close_match:
        print("❌ close() method not found")
        return False

    close_code = close_match.group(1)

    # Check if it closes the session
    closes_session = "_session" in close_code and "close" in close_code

    print(f"📋 TradeExecutor close() method closes session: {'✅' if closes_session else '❌'}")

    return closes_session

def check_session_patterns():
    """Check for common session leak patterns"""
    print("\n🔍 Checking for common session leak patterns...")

    issues = []

    # Find all Python files that use aiohttp.ClientSession
    src_path = Path("src")
    py_files = list(src_path.glob("**/*.py"))

    session_files = []
    for py_file in py_files:
        try:
            content = py_file.read_text()
            if "aiohttp.ClientSession" in content:
                session_files.append(py_file)
        except:
            continue

    print(f"📊 Found {len(session_files)} files using aiohttp.ClientSession")

    # Check each file for potential issues
    for py_file in session_files:
        try:
            content = py_file.read_text()

            # Check for session creation without async context manager
            if re.search(r'aiohttp\.ClientSession\([^)]*\)(?!\s+as\s+\w+:)', content):
                # Check if there's a corresponding close() call
                if "session.close()" not in content and "_session.close()" not in content:
                    issues.append(f"Potential session leak in {py_file.name}")
        except:
            continue

    if issues:
        print("⚠️  Potential session management issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ No obvious session leak patterns detected")
        return True

def main():
    """Run all validation checks"""
    print("=" * 70)
    print("SESSION CLEANUP IMPLEMENTATION VALIDATION")
    print("=" * 70)

    results = []

    # Run all analyses
    results.append(analyze_alert_manager_cleanup())
    results.append(analyze_main_cleanup_sequence())
    results.append(analyze_trade_executor())
    results.append(check_session_patterns())

    print("\n" + "=" * 70)
    print("VALIDATION RESULTS SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"Checks passed: {passed}/{total}")

    if passed == total:
        print("✅ VALIDATION PASSED: Session cleanup appears to be correctly implemented")
        return True
    else:
        print(f"❌ VALIDATION FAILED: {total - passed} issues found")
        return False

if __name__ == "__main__":
    result = main()
    exit(0 if result else 1)