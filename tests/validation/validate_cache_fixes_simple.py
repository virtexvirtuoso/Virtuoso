#!/usr/bin/env python3
"""
Simple Code Analysis Validation for Technical Indicator Cache Fixes
Analyzes the code statically to verify the fixes are properly implemented.
"""

import os
import re
import sys

def analyze_cache_fixes():
    """Analyze the cache fixes implementation"""

    indicators_file = "src/indicators/technical_indicators.py"
    base_file = "src/indicators/base_indicator.py"

    print("=" * 60)
    print("TECHNICAL INDICATOR CACHE FIXES - CODE ANALYSIS")
    print("=" * 60)

    # 1. Check if _ensure_cache_ready method exists in base_indicator.py
    with open(base_file, 'r') as f:
        base_content = f.read()

    ensure_cache_ready_exists = "async def _ensure_cache_ready" in base_content
    print(f"✓ _ensure_cache_ready method exists: {ensure_cache_ready_exists}")

    # 2. Check for iscoroutine usage in _ensure_cache_ready
    iscoroutine_check = "iscoroutine(self.cache)" in base_content
    print(f"✓ Coroutine detection implemented: {iscoroutine_check}")

    # 3. Check for cache awaiting in _ensure_cache_ready
    cache_await_fix = "self.cache = await self.cache" in base_content
    print(f"✓ Cache coroutine awaiting fix: {cache_await_fix}")

    # 4. Check cached methods in technical_indicators.py
    with open(indicators_file, 'r') as f:
        indicators_content = f.read()

    cached_methods = [
        "_calculate_rsi_score_cached",
        "_calculate_macd_score_cached",
        "_calculate_ao_score_cached",
        "_calculate_williams_r_score_cached",
        "_calculate_atr_score_cached",
        "_calculate_cci_score_cached"
    ]

    print("\nCached Methods Analysis:")
    for method in cached_methods:
        method_exists = f"async def {method}" in indicators_content
        print(f"  ✓ {method}: {method_exists}")

        if method_exists:
            # Extract method content
            pattern = rf"async def {method}.*?(?=async def|\Z)"
            match = re.search(pattern, indicators_content, re.DOTALL)
            if match:
                method_content = match.group(0)

                # Check for _ensure_cache_ready call
                has_ensure_call = "await self._ensure_cache_ready()" in method_content
                print(f"    - Has _ensure_cache_ready call: {has_ensure_call}")

                # Check for try/except around cache operations
                has_try_except = "try:" in method_content and "except Exception:" in method_content
                print(f"    - Has try/except fallback: {has_try_except}")

                # Check for fallback to direct calculation
                fallback_pattern = rf"return self\.{method.replace('_cached', '')}.*?\(.*?\)"
                has_fallback = re.search(fallback_pattern, method_content)
                print(f"    - Has direct calculation fallback: {bool(has_fallback)}")

    # 5. Check error handling patterns
    print("\nError Handling Analysis:")

    # Check for exception catching in cache guard
    guard_exceptions = "except Exception:" in base_content and "_ensure_cache_ready" in base_content
    print(f"✓ Cache guard has exception handling: {guard_exceptions}")

    # Check for cache operation exception handling
    cache_try_blocks = indicators_content.count("try:") >= len(cached_methods)
    print(f"✓ Sufficient try/except blocks: {cache_try_blocks}")

    # 6. Check for proper async patterns
    print("\nAsync Pattern Analysis:")

    # Check for proper async function definitions
    async_methods = len(re.findall(r"async def _calculate.*_cached", indicators_content))
    print(f"✓ Async cached methods count: {async_methods} (expected: {len(cached_methods)})")

    # Check for await usage in cache calls
    await_cache_calls = indicators_content.count("await self.cache.get_indicator")
    print(f"✓ Proper await usage in cache calls: {await_cache_calls >= len(cached_methods)}")

    # 7. Summary Analysis
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    checks = [
        ensure_cache_ready_exists,
        iscoroutine_check,
        cache_await_fix,
        guard_exceptions,
        async_methods == len(cached_methods),
        await_cache_calls >= len(cached_methods)
    ]

    passed = sum(checks)
    total = len(checks)

    print(f"Core Checks Passed: {passed}/{total} ({(passed/total)*100:.1f}%)")

    if passed == total:
        print("\n✅ ALL CRITICAL FIXES APPEAR TO BE IMPLEMENTED CORRECTLY")
        return True
    else:
        print("\n❌ SOME CRITICAL FIXES MAY BE MISSING OR INCOMPLETE")
        return False

def check_potential_issues():
    """Check for potential remaining issues"""

    print("\n" + "=" * 60)
    print("POTENTIAL ISSUES ANALYSIS")
    print("=" * 60)

    base_file = "src/indicators/base_indicator.py"
    indicators_file = "src/indicators/technical_indicators.py"

    with open(base_file, 'r') as f:
        base_content = f.read()

    with open(indicators_file, 'r') as f:
        indicators_content = f.read()

    issues = []

    # Check for any remaining direct cache assignments without proper checks
    if "self.cache = " in base_content:
        # Count safe assignments vs potentially unsafe ones
        safe_assignments = base_content.count("self.cache = None") + base_content.count("self.cache = await")
        total_assignments = base_content.count("self.cache = ")

        if total_assignments > safe_assignments:
            issues.append("Potential unsafe cache assignments detected")

    # Check for missing symbol parameter in cached calls
    symbol_checks = indicators_content.count("symbol: str = None")
    if symbol_checks < 6:  # Should have symbol param in all 6 cached methods
        issues.append("Missing symbol parameters in some cached methods")

    # Check for proper cache initialization checks
    cache_checks = indicators_content.count("if not self.enable_caching or not self.cache")
    if cache_checks < 6:
        issues.append("Missing cache state checks in some methods")

    if issues:
        print("⚠️  POTENTIAL ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ NO OBVIOUS ISSUES DETECTED")

    return len(issues) == 0

def main():
    """Main validation function"""

    try:
        # Change to script directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Run analysis
        fixes_ok = analyze_cache_fixes()
        no_issues = check_potential_issues()

        if fixes_ok and no_issues:
            print("\n🎉 VALIDATION SUCCESSFUL - Cache fixes appear to be correctly implemented")
            return True
        else:
            print("\n⚠️  VALIDATION CONCERNS - Some issues may need attention")
            return False

    except Exception as e:
        print(f"\n💥 VALIDATION ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)