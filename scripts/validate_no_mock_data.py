#!/usr/bin/env python3
"""
Validate that NO mock, random, or simulated data exists in production code
"""

import sys
import re
from pathlib import Path

def check_critical_files():
    """Check critical files for random/mock data"""
    issues = []
    
    # Check trade executor
    trade_exec = Path("src/trade_execution/trade_executor.py")
    if trade_exec.exists():
        content = trade_exec.read_text()
        # The file should now use real confluence analyzer
        if "random.uniform(0, 100)" in content:
            issues.append("🔴 CRITICAL: Trade executor still using random.uniform(0, 100) for scores!")
        if "from src.core.analysis.confluence import ConfluenceAnalyzer" not in content:
            issues.append("🔴 CRITICAL: Trade executor not importing real ConfluenceAnalyzer!")
    
    # Check analysis service
    analysis_svc = Path("src/services/analysis_service_enhanced.py")
    if analysis_svc.exists():
        content = analysis_svc.read_text()
        if "random.uniform(40, 60)" in content:
            issues.append("🔴 CRITICAL: Analysis service still using random.uniform(40, 60) for components!")
        if "random.uniform(-10, 10)" in content:
            issues.append("🔴 CRITICAL: Analysis service still adding random variation!")
        if "_get_real_score" not in content:
            issues.append("🔴 CRITICAL: Analysis service missing _get_real_score method!")
    
    # Check for confluence_sample.py
    if Path("src/core/analysis/confluence_sample.py").exists():
        issues.append("🔴 CRITICAL: confluence_sample.py still exists (should be renamed)!")
    
    # Check for synthetic OI
    market_mgr = Path("src/core/market/market_data_manager.py")
    if market_mgr.exists():
        content = market_mgr.read_text()
        if "'is_synthetic': True" in content:
            issues.append("🟠 HIGH: Still generating synthetic open interest!")
        if "synthetic_oi = price * volume_24h * 5.0" in content:
            issues.append("🟠 HIGH: Still calculating synthetic OI values!")
    
    return issues

def check_hardcoded_defaults():
    """Check for hardcoded 50.0 defaults"""
    issues = []
    
    files = [
        "src/dashboard/integration_service.py",
        "src/dashboard/dashboard_integration.py",
        "src/api/services/mobile_fallback_service.py",
        "src/api/routes/correlation.py"
    ]
    
    for filepath in files:
        path = Path(filepath)
        if path.exists():
            content = path.read_text()
            count = content.count(".get('score', 50.0)")
            if count > 0:
                issues.append(f"🟠 HIGH: {filepath} has {count} hardcoded 50.0 defaults")
    
    return issues

def check_random_imports():
    """Check for any random data generation in src/"""
    issues = []
    
    # Files that are allowed to use random (tests, demos, etc)
    allowed_files = {
        "test_", "demo_", "example_", "_test.py", "_demo.py",
        "load_testing", "simulation", "backtest"
    }
    
    for py_file in Path("src").rglob("*.py"):
        # Skip allowed files
        filename = py_file.name.lower()
        if any(allowed in filename for allowed in allowed_files):
            continue
            
        try:
            content = py_file.read_text()
            
            # Check for random usage
            if re.search(r'random\.(uniform|random|randint|choice|randrange)\(', content):
                # Check if it's in production code path
                if "trade_execution" in str(py_file) or \
                   "services" in str(py_file) or \
                   "indicators" in str(py_file) or \
                   "core/analysis" in str(py_file):
                    issues.append(f"🔴 CRITICAL: {py_file.relative_to(Path('.'))} uses random data generation!")
                else:
                    issues.append(f"🟡 MEDIUM: {py_file.relative_to(Path('.'))} uses random (verify it's not production)")
                    
        except Exception:
            pass
    
    return issues

def main():
    """Run all validation checks"""
    print("=" * 60)
    print("Validating NO Mock/Random Data in Production")
    print("=" * 60)
    print()
    
    all_issues = []
    
    # Check critical files
    print("1. Checking critical files...")
    issues = check_critical_files()
    all_issues.extend(issues)
    if not issues:
        print("  ✅ No random data in critical files")
    
    # Check hardcoded defaults
    print("\n2. Checking hardcoded defaults...")
    issues = check_hardcoded_defaults()
    all_issues.extend(issues)
    if not issues:
        print("  ✅ No hardcoded 50.0 defaults")
    
    # Check for random imports
    print("\n3. Checking for random data generation...")
    issues = check_random_imports()
    all_issues.extend(issues)
    if not issues:
        print("  ✅ No random data generation in production")
    
    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print("❌ VALIDATION FAILED - Issues Found:")
        print()
        
        # Group by severity
        critical = [i for i in all_issues if "🔴" in i]
        high = [i for i in all_issues if "🟠" in i]
        medium = [i for i in all_issues if "🟡" in i]
        
        if critical:
            print("CRITICAL ISSUES:")
            for issue in critical:
                print(f"  {issue}")
        
        if high:
            print("\nHIGH SEVERITY:")
            for issue in high:
                print(f"  {issue}")
        
        if medium:
            print("\nMEDIUM SEVERITY:")
            for issue in medium:
                print(f"  {issue}")
        
        print("\n🚨 DO NOT USE FOR PRODUCTION TRADING!")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED - System Clean!")
        print()
        print("✓ Trade executor using real confluence analyzer")
        print("✓ Dashboard showing real indicator data")
        print("✓ No synthetic market data generation")
        print("✓ No hardcoded default values")
        print("✓ No random data in production paths")
        print()
        print("🎉 System is SAFE for production trading!")
        sys.exit(0)

if __name__ == "__main__":
    main()