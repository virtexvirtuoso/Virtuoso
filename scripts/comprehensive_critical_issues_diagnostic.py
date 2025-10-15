#!/usr/bin/env python3
"""
Comprehensive diagnostic script to investigate root causes of critical issues:
1. Why all 15 symbol processing tasks return None (silent failures)
2. Service restart cascade trigger patterns
3. Data quality issues causing insufficient HTF candles and missing data
"""

import asyncio
import logging
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

async def investigate_symbol_processing_failures():
    """Root Cause Analysis: Why do all 15 symbol processing tasks return None?"""

    print("🔍 INVESTIGATION 1: Symbol Processing Task Failures")
    print("=" * 60)

    issues_found = []

    try:
        # Test 1: Import and inspect monitoring system
        print("\n📋 Test 1: Monitoring System Import Analysis")
        try:
            from monitoring.monitor import MarketMonitor
            from monitoring.optimized_alpha_scanner import OptimizedAlphaScanner
            from core.market.top_symbols import TopSymbolsProvider

            print("✅ Core monitoring modules import successfully")

            # Test symbol provider
            symbol_provider = TopSymbolsProvider()
            top_symbols = symbol_provider.get_top_symbols()
            print(f"✅ Symbol provider returns {len(top_symbols)} symbols: {top_symbols[:5]}...")

        except Exception as e:
            issue = f"❌ Module import failure: {str(e)}"
            print(issue)
            issues_found.append(issue)
            return issues_found

        # Test 2: Examine alpha scanner processing logic
        print("\n📋 Test 2: Alpha Scanner Processing Logic")
        try:
            scanner = OptimizedAlphaScanner()

            # Test single symbol processing (simulate what happens in tasks)
            test_symbol = top_symbols[0] if top_symbols else "BTCUSDT"
            print(f"🧪 Testing symbol processing for: {test_symbol}")

            # This simulates what happens in the monitoring tasks
            start_time = time.time()

            # Mock the process_symbol call to see where it fails
            try:
                # Check if the method exists and what parameters it expects
                if hasattr(scanner, 'process_symbol'):
                    print("✅ process_symbol method exists")

                    # Try to get the method signature
                    import inspect
                    sig = inspect.signature(scanner.process_symbol)
                    print(f"📝 Method signature: {sig}")

                    # Test with minimal parameters first
                    result = await scanner.process_symbol(test_symbol)
                    processing_time = time.time() - start_time

                    print(f"✅ Symbol processing returned: {type(result)} in {processing_time:.2f}s")

                    if result is None:
                        issue = f"❌ FOUND ROOT CAUSE: process_symbol returns None for {test_symbol}"
                        print(issue)
                        issues_found.append(issue)
                    else:
                        print(f"✅ Symbol processing successful: {result}")

                else:
                    issue = "❌ process_symbol method not found in OptimizedAlphaScanner"
                    print(issue)
                    issues_found.append(issue)

            except Exception as e:
                issue = f"❌ Symbol processing failed: {str(e)}"
                print(issue)
                issues_found.append(issue)
                print(f"📋 Exception details:\n{traceback.format_exc()}")

        except Exception as e:
            issue = f"❌ Alpha scanner initialization failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

        # Test 3: Check data dependencies
        print("\n📋 Test 3: Data Dependencies Analysis")
        try:
            from core.exchanges.manager import ExchangeManager
            from data_processing.data_processor import DataProcessor

            # Test exchange connection
            exchange_manager = ExchangeManager()
            print("✅ ExchangeManager initialized")

            # Test data processor
            data_processor = DataProcessor()
            print("✅ DataProcessor initialized")

            # Check if we can fetch basic market data
            test_data = await exchange_manager.fetch_ticker(test_symbol)
            if test_data:
                print(f"✅ Market data available for {test_symbol}")
            else:
                issue = f"❌ No market data available for {test_symbol}"
                print(issue)
                issues_found.append(issue)

        except Exception as e:
            issue = f"❌ Data dependencies check failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

        # Test 4: Check confluence analysis requirements
        print("\n📋 Test 4: Confluence Analysis Requirements")
        try:
            from core.analysis.confluence import ConfluenceAnalyzer

            analyzer = ConfluenceAnalyzer()
            print("✅ ConfluenceAnalyzer initialized")

            # Check what data is required for analysis
            print("🔍 Checking confluence analysis data requirements...")

            # This is likely where the silent failures occur
            result = await analyzer.analyze_symbol(test_symbol)

            if result is None:
                issue = f"❌ FOUND ROOT CAUSE: ConfluenceAnalyzer.analyze_symbol returns None for {test_symbol}"
                print(issue)
                issues_found.append(issue)
            else:
                print(f"✅ Confluence analysis successful: {type(result)}")

        except Exception as e:
            issue = f"❌ Confluence analysis failed: {str(e)}"
            print(issue)
            issues_found.append(issue)
            print(f"📋 Exception details:\n{traceback.format_exc()}")

    except Exception as e:
        issue = f"❌ Overall investigation failed: {str(e)}"
        print(issue)
        issues_found.append(issue)

    return issues_found

async def investigate_service_restart_patterns():
    """Root Cause Analysis: What triggers the service restart cascade?"""

    print("\n🔄 INVESTIGATION 2: Service Restart Cascade Analysis")
    print("=" * 60)

    issues_found = []

    try:
        # Test 1: Check monitoring loop error handling
        print("\n📋 Test 1: Monitoring Loop Error Handling")

        from monitoring.monitor import MarketMonitor

        # Create a monitor instance and examine its error handling
        monitor = MarketMonitor()
        print("✅ MarketMonitor initialized")

        # Check error count and restart logic
        if hasattr(monitor, '_error_count'):
            print(f"📊 Current error count: {monitor._error_count}")

        if hasattr(monitor, '_max_consecutive_errors'):
            print(f"📊 Max consecutive errors: {monitor._max_consecutive_errors}")

        # Test 2: Examine the monitoring cycle
        print("\n📋 Test 2: Monitoring Cycle Stress Test")

        # Simulate a monitoring cycle to see what causes failures
        try:
            start_time = time.time()

            # This should replicate what happens in the monitoring loop
            print("🧪 Simulating monitoring cycle...")

            # Run a short monitoring cycle
            cycle_result = await asyncio.wait_for(
                monitor._monitoring_cycle(),
                timeout=30.0  # Shorter timeout for testing
            )

            cycle_time = time.time() - start_time
            print(f"✅ Monitoring cycle completed in {cycle_time:.2f}s")

            if cycle_result is None:
                issue = "❌ FOUND ROOT CAUSE: Monitoring cycle returns None"
                print(issue)
                issues_found.append(issue)

        except asyncio.TimeoutError:
            issue = "❌ Monitoring cycle timeout (>30s) - this triggers restarts"
            print(issue)
            issues_found.append(issue)

        except asyncio.CancelledError:
            issue = "❌ Monitoring cycle cancelled - this triggers restarts"
            print(issue)
            issues_found.append(issue)

        except Exception as e:
            issue = f"❌ Monitoring cycle failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

        # Test 3: Check resource constraints
        print("\n📋 Test 3: Resource Constraints Analysis")

        import psutil

        # Check memory usage
        memory = psutil.virtual_memory()
        print(f"📊 Memory usage: {memory.percent}% ({memory.used / 1024**3:.1f}GB used)")

        if memory.percent > 85:
            issue = f"❌ High memory usage: {memory.percent}% - may cause restarts"
            print(issue)
            issues_found.append(issue)

        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"📊 CPU usage: {cpu_percent}%")

        if cpu_percent > 80:
            issue = f"❌ High CPU usage: {cpu_percent}% - may cause restarts"
            print(issue)
            issues_found.append(issue)

    except Exception as e:
        issue = f"❌ Service restart investigation failed: {str(e)}"
        print(issue)
        issues_found.append(issue)

    return issues_found

async def investigate_data_quality_issues():
    """Root Cause Analysis: Why is historical data insufficient/missing?"""

    print("\n📊 INVESTIGATION 3: Data Quality & Availability Issues")
    print("=" * 60)

    issues_found = []

    try:
        # Test 1: Check data storage
        print("\n📋 Test 1: Data Storage Analysis")

        from data_storage.database import DatabaseManager

        db_manager = DatabaseManager()
        print("✅ DatabaseManager initialized")

        # Check if database is accessible
        try:
            # Test basic database operations
            db_status = await db_manager.health_check()
            print(f"📊 Database health: {db_status}")

            if not db_status:
                issue = "❌ Database health check failed - data unavailable"
                print(issue)
                issues_found.append(issue)

        except Exception as e:
            issue = f"❌ Database connection failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

        # Test 2: Check historical data availability
        print("\n📋 Test 2: Historical Data Availability")

        from core.exchanges.manager import ExchangeManager

        exchange_manager = ExchangeManager()
        test_symbol = "BTCUSDT"

        # Check different timeframes
        timeframes = ['1m', '5m', '30m', '4h', '1d']

        for tf in timeframes:
            try:
                # Fetch historical data for each timeframe
                since = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)

                candles = await exchange_manager.fetch_ohlcv(
                    test_symbol,
                    tf,
                    since=since,
                    limit=100
                )

                if candles and len(candles) > 0:
                    print(f"✅ {tf}: {len(candles)} candles available")

                    if len(candles) < 50:
                        issue = f"❌ Insufficient {tf} candles: {len(candles)} < 50 required"
                        print(issue)
                        issues_found.append(issue)
                else:
                    issue = f"❌ No {tf} data available for {test_symbol}"
                    print(issue)
                    issues_found.append(issue)

            except Exception as e:
                issue = f"❌ Failed to fetch {tf} data: {str(e)}"
                print(issue)
                issues_found.append(issue)

        # Test 3: Check specific data types mentioned in logs
        print("\n📋 Test 3: Specific Data Type Analysis")

        # Check Open Interest data
        try:
            oi_data = await exchange_manager.fetch_open_interest(test_symbol)
            if oi_data:
                print("✅ Open Interest data available")
            else:
                issue = "❌ No Open Interest data - causes divergence calculation failures"
                print(issue)
                issues_found.append(issue)
        except Exception as e:
            issue = f"❌ Open Interest fetch failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

        # Check Liquidation data
        try:
            # This might not be available on all exchanges
            liquidation_data = await exchange_manager.fetch_liquidations(test_symbol)
            if liquidation_data:
                print("✅ Liquidation data available")
            else:
                issue = "❌ No Liquidation data - causes neutral sentiment scores"
                print(issue)
                issues_found.append(issue)
        except Exception as e:
            issue = f"❌ Liquidation data check failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

        # Test 4: Check data freshness
        print("\n📋 Test 4: Data Freshness Analysis")

        try:
            ticker = await exchange_manager.fetch_ticker(test_symbol)
            if ticker and 'timestamp' in ticker:
                data_age = time.time() * 1000 - ticker['timestamp']
                data_age_seconds = data_age / 1000

                print(f"📊 Market data age: {data_age_seconds:.1f}s")

                if data_age_seconds > 60:  # More than 1 minute old
                    issue = f"❌ Stale market data: {data_age_seconds:.1f}s old"
                    print(issue)
                    issues_found.append(issue)
            else:
                issue = "❌ No timestamp in ticker data - cannot verify freshness"
                print(issue)
                issues_found.append(issue)

        except Exception as e:
            issue = f"❌ Data freshness check failed: {str(e)}"
            print(issue)
            issues_found.append(issue)

    except Exception as e:
        issue = f"❌ Data quality investigation failed: {str(e)}"
        print(issue)
        issues_found.append(issue)

    return issues_found

async def generate_diagnostic_report(all_issues: Dict[str, List[str]]):
    """Generate comprehensive diagnostic report with actionable fixes."""

    print("\n📋 COMPREHENSIVE DIAGNOSTIC REPORT")
    print("=" * 80)

    total_issues = sum(len(issues) for issues in all_issues.values())

    if total_issues == 0:
        print("🎉 No critical issues found - system appears healthy!")
        return

    print(f"🚨 FOUND {total_issues} CRITICAL ISSUES:")
    print("")

    # Categorize and prioritize issues
    for investigation, issues in all_issues.items():
        if issues:
            print(f"🔍 {investigation}:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
            print("")

    # Generate specific fixes
    print("🔧 RECOMMENDED FIXES:")
    print("=" * 40)

    # Fix 1: Symbol processing failures
    if any("process_symbol returns None" in issue for issues in all_issues.values() for issue in issues):
        print("""
1. 🎯 SYMBOL PROCESSING FAILURES:
   - Root cause: process_symbol method returning None
   - Fix: Add error handling and default values in OptimizedAlphaScanner
   - Action: Review confluence analysis requirements and data validation
        """)

    # Fix 2: Data availability issues
    if any("data" in issue.lower() for issues in all_issues.values() for issue in issues):
        print("""
2. 📊 DATA QUALITY ISSUES:
   - Root cause: Insufficient historical data or missing data types
   - Fix: Implement data validation and fallback mechanisms
   - Action: Ensure minimum data requirements are met before analysis
        """)

    # Fix 3: Performance issues
    if any("timeout" in issue.lower() or "slow" in issue.lower() for issues in all_issues.values() for issue in issues):
        print("""
3. ⚡ PERFORMANCE ISSUES:
   - Root cause: Slow calculations causing timeouts
   - Fix: Optimize confluence analysis components
   - Action: Implement caching and reduce calculation complexity
        """)

    # Fix 4: Resource constraints
    if any("memory" in issue.lower() or "cpu" in issue.lower() for issues in all_issues.values() for issue in issues):
        print("""
4. 🖥️ RESOURCE CONSTRAINTS:
   - Root cause: High memory/CPU usage
   - Fix: Implement resource monitoring and limits
   - Action: Optimize memory usage and add resource checks
        """)

    print("""
📋 NEXT STEPS:
1. Deploy fixes for highest priority issues first
2. Implement monitoring for early detection
3. Add comprehensive error handling
4. Set up data quality validation
5. Monitor performance metrics continuously
""")

    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"CRITICAL_ISSUES_DIAGNOSTIC_REPORT_{timestamp}.md"

    with open(report_file, 'w') as f:
        f.write(f"# Critical Issues Diagnostic Report\n")
        f.write(f"Generated: {datetime.now()}\n\n")

        f.write(f"## Summary\n")
        f.write(f"Total issues found: {total_issues}\n\n")

        for investigation, issues in all_issues.items():
            if issues:
                f.write(f"## {investigation}\n")
                for issue in issues:
                    f.write(f"- {issue}\n")
                f.write("\n")

    print(f"📝 Full diagnostic report saved to: {report_file}")

async def main():
    """Main diagnostic function."""

    print("🔍 COMPREHENSIVE CRITICAL ISSUES DIAGNOSTIC")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print("")

    print("🎯 Investigating three critical issues:")
    print("1. Symbol processing tasks returning None (silent failures)")
    print("2. Service restart cascade trigger patterns")
    print("3. Data quality issues causing insufficient HTF candles")
    print("")

    all_issues = {}

    try:
        # Investigation 1: Symbol processing failures
        print("Starting Investigation 1...")
        issues_1 = await investigate_symbol_processing_failures()
        all_issues["Symbol Processing Failures"] = issues_1

        # Investigation 2: Service restart patterns
        print("\nStarting Investigation 2...")
        issues_2 = await investigate_service_restart_patterns()
        all_issues["Service Restart Patterns"] = issues_2

        # Investigation 3: Data quality issues
        print("\nStarting Investigation 3...")
        issues_3 = await investigate_data_quality_issues()
        all_issues["Data Quality Issues"] = issues_3

        # Generate comprehensive report
        await generate_diagnostic_report(all_issues)

    except Exception as e:
        print(f"❌ Diagnostic failed: {str(e)}")
        print(traceback.format_exc())
        return 1

    return 0

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)