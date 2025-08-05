#!/usr/bin/env python3
"""
Verify that the critical fixes were applied correctly.
"""

import os
import re
from pathlib import Path

def verify_bybit_fix():
    """Verify Bybit timeout fix was applied."""
    print("\n1. Verifying Bybit timeout fix...")
    
    bybit_file = Path(__file__).parent.parent / "src/core/exchanges/bybit.py"
    if not bybit_file.exists():
        print(f"❌ File not found: {bybit_file}")
        return False
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    checks = [
        ("Reduced timeouts", "total=15,  # Reduced total timeout to fail faster"),
        ("asyncio.wait_for wrapper", "asyncio.wait_for("),
        ("Timeout error handling", "except asyncio.TimeoutError:")
    ]
    
    all_good = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  ✅ {name}: Found")
        else:
            print(f"  ❌ {name}: Not found")
            all_good = False
    
    return all_good

def verify_pdf_fix():
    """Verify PDF generator fix was applied."""
    print("\n2. Verifying PDF generator fix...")
    
    pdf_file = Path(__file__).parent.parent / "src/core/reporting/pdf_generator.py"
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_file}")
        return False
    
    with open(pdf_file, 'r') as f:
        content = f.read()
    
    checks = [
        ("entry_pos initialization", "entry_pos = None  # Initialize to prevent undefined variable error"),
        ("entry_pos null check", "if entry_pos is not None:")
    ]
    
    all_good = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  ✅ {name}: Found")
        else:
            print(f"  ❌ {name}: Not found")
            all_good = False
    
    # Count how many times entry_pos is initialized
    init_count = content.count("entry_pos = None  # Initialize to prevent undefined variable error")
    print(f"  ℹ️  entry_pos initialization found {init_count} times")
    
    return all_good

def verify_market_data_fix():
    """Verify market data manager fix was applied."""
    print("\n3. Verifying market data manager fix...")
    
    market_file = Path(__file__).parent.parent / "src/core/market/market_data_manager.py"
    if not market_file.exists():
        print(f"❌ File not found: {market_file}")
        return False
    
    with open(market_file, 'r') as f:
        content = f.read()
    
    checks = [
        ("_fetch_immediate_symbol_data method", "async def _fetch_immediate_symbol_data"),
        ("Enhanced get_symbol_data", "await self._fetch_immediate_symbol_data(symbol)")
    ]
    
    all_good = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  ✅ {name}: Found")
        else:
            print(f"  ❌ {name}: Not found")
            all_good = False
    
    return all_good

def check_backups():
    """Check that backup files were created."""
    print("\n4. Checking backup files...")
    
    backup_patterns = [
        "src/core/exchanges/bybit.py.backup_*",
        "src/core/reporting/pdf_generator.py.backup_*",
        "src/core/market/market_data_manager.py.backup_*"
    ]
    
    project_root = Path(__file__).parent.parent
    
    for pattern in backup_patterns:
        files = list(project_root.glob(pattern))
        if files:
            latest = max(files, key=os.path.getctime)
            print(f"  ✅ Found backup: {latest.name}")
        else:
            print(f"  ❌ No backup found for pattern: {pattern}")

def main():
    """Run all verifications."""
    print("🔍 Verifying critical fixes...")
    print("=" * 60)
    
    results = []
    
    results.append(verify_bybit_fix())
    results.append(verify_pdf_fix())
    results.append(verify_market_data_fix())
    
    check_backups()
    
    print("\n" + "=" * 60)
    
    if all(results):
        print("✅ All fixes verified successfully!")
        return True
    else:
        print("❌ Some fixes were not applied correctly.")
        return False

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)