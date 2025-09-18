#!/usr/bin/env python3
"""Verify that chart generation is working properly."""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_chart_generation():
    """Verify all components are in place for chart generation."""

    issues = []

    print("=" * 60)
    print("Chart Generation Verification")
    print("=" * 60)

    # 1. Check PDF generator has chart methods
    logger.info("1. Checking PDF generator chart methods...")
    pdf_gen_path = Path("src/core/reporting/pdf_generator.py")
    if pdf_gen_path.exists():
        content = pdf_gen_path.read_text()
        if "_create_candlestick_chart" in content:
            print("✅ _create_candlestick_chart method exists")
        else:
            issues.append("❌ _create_candlestick_chart method missing")

        if "_create_simulated_chart" in content:
            print("✅ _create_simulated_chart method exists")
        else:
            issues.append("❌ _create_simulated_chart method missing")
    else:
        issues.append("❌ PDF generator file not found")

    # 2. Check signal generator fetches OHLCV
    logger.info("\n2. Checking signal generator OHLCV fetching...")
    sig_gen_path = Path("src/signal_generation/signal_generator.py")
    if sig_gen_path.exists():
        content = sig_gen_path.read_text()
        if "fetch_ohlcv" in content and "ohlcv_data" in content:
            print("✅ Signal generator fetches OHLCV data")
        else:
            issues.append("❌ Signal generator doesn't fetch OHLCV")
    else:
        issues.append("❌ Signal generator file not found")

    # 3. Check market_data_manager has fetch_ohlcv method
    logger.info("\n3. Checking market_data_manager fetch_ohlcv method...")
    mdm_path = Path("src/core/market/market_data_manager.py")
    if mdm_path.exists():
        content = mdm_path.read_text()
        if "async def fetch_ohlcv" in content:
            print("✅ market_data_manager has fetch_ohlcv method")
        else:
            issues.append("❌ market_data_manager missing fetch_ohlcv method")
    else:
        issues.append("❌ market_data_manager file not found")

    # 4. Check alert manager passes OHLCV data
    logger.info("\n4. Checking alert manager OHLCV handling...")
    alert_mgr_path = Path("src/monitoring/alert_manager.py")
    if alert_mgr_path.exists():
        content = alert_mgr_path.read_text()
        if "ohlcv_data" in content and "_generate_chart_from_signal_data" in content:
            print("✅ Alert manager handles OHLCV data for charts")
        else:
            issues.append("❌ Alert manager doesn't handle OHLCV properly")
    else:
        issues.append("❌ Alert manager file not found")

    # 5. Check charts directory exists
    logger.info("\n5. Checking charts directory...")
    charts_dir = Path("reports/charts")
    if charts_dir.exists():
        print(f"✅ Charts directory exists: {charts_dir.absolute()}")
        # Check for any existing charts
        charts = list(charts_dir.glob("*.png"))
        if charts:
            print(f"   Found {len(charts)} existing chart files")
    else:
        charts_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created charts directory: {charts_dir.absolute()}")

    # 6. Check matplotlib installation
    logger.info("\n6. Checking matplotlib installation...")
    try:
        import matplotlib
        import mplfinance
        print(f"✅ matplotlib v{matplotlib.__version__} installed")
        print(f"✅ mplfinance installed")
    except ImportError as e:
        issues.append(f"❌ Missing dependency: {e}")

    # Summary
    print("\n" + "=" * 60)
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ ALL CHECKS PASSED!")
        print("\nChart generation system is properly configured:")
        print("• PDF generator has chart creation methods")
        print("• Signal generator fetches OHLCV data")
        print("• Market data manager provides OHLCV data")
        print("• Alert manager passes data to chart generator")
        print("• Charts directory is ready")
        print("• Required dependencies are installed")
        return True

if __name__ == "__main__":
    success = verify_chart_generation()
    sys.exit(0 if success else 1)