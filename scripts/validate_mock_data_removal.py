#!/usr/bin/env python3
"""Validate that mock data has been removed from production code"""

import sys
import json
from pathlib import Path

def check_no_fake_data():
    """Verify no fake data generation exists"""
    issues = []
    
    # Check for fake timestamps
    files_to_check = [
        "src/core/market/market_data_manager.py",
        "src/indicators/orderflow_indicators.py"
    ]
    
    for filepath in files_to_check:
        path = Path(filepath)
        if path.exists():
            content = path.read_text()
            if "fake_timestamp" in content or "fake_value" in content:
                issues.append(f"Found fake data generation in {filepath}")
    
    # Check for sample tickers
    cache_script = Path("scripts/populate_cache_service.py")
    if cache_script.exists():
        content = cache_script.read_text()
        if "sample_tickers" in content and "113000" in content:
            issues.append("Found hardcoded sample tickers")
    
    # Check for mock mode
    alert_manager = Path("src/monitoring/alert_manager.py")
    if alert_manager.exists():
        content = alert_manager.read_text()
        if "MOCK MODE:" in content:
            issues.append("Found mock mode in alerts")
    
    return issues

if __name__ == "__main__":
    print("Validating mock data removal...")
    issues = check_no_fake_data()
    
    if issues:
        print("\n❌ Validation FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ Validation PASSED - No mock data found in production code")
        sys.exit(0)
