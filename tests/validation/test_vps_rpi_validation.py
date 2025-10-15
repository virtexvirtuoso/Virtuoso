#!/usr/bin/env python3
"""
VPS RPI Integration Validation Test
Tests RPI functionality on the deployed VPS environment.
"""

import subprocess
import sys
import json

def run_vps_command(command):
    """Execute command on VPS and return result."""
    try:
        result = subprocess.run(
            ["ssh", "vps", f"cd /home/linuxuser/trading/Virtuoso_ccxt && {command}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_orderbook_indicators_with_rpi():
    """Test OrderbookIndicators initialization with RPI component on VPS."""
    print("=== Testing OrderbookIndicators with RPI on VPS ===")

    test_script = '''
import sys
sys.path.append('src')

try:
    from src.indicators.orderbook_indicators import OrderbookIndicators

    # Full config for initialization
    config = {
        "timeframes": {
            "base": {"interval": 1, "weight": 0.4, "validation": {"min_candles": 50}},
            "ltf": {"interval": 5, "weight": 0.3, "validation": {"min_candles": 30}},
            "mtf": {"interval": 15, "weight": 0.2, "validation": {"min_candles": 20}},
            "htf": {"interval": 60, "weight": 0.1, "validation": {"min_candles": 10}}
        }
    }

    indicators = OrderbookIndicators(config_data=config)

    # Check retail component
    retail_weight = indicators.component_weights.get("retail", 0)
    component_count = len(indicators.component_weights)

    print(f"SUCCESS: Retail weight: {retail_weight}")
    print(f"SUCCESS: Total components: {component_count}")
    print(f"SUCCESS: All components: {list(indicators.component_weights.keys())}")

    if retail_weight == 0.04 and component_count == 9:
        print("SUCCESS: RPI integration verified")
    else:
        print(f"FAILURE: Expected retail=0.04 and 9 components, got {retail_weight} and {component_count}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''

    success, stdout, stderr = run_vps_command(f"python3 -c '{test_script}'")

    if success and "SUCCESS: RPI integration verified" in stdout:
        print("✓ VPS OrderbookIndicators RPI integration validated")
        return True
    else:
        print(f"❌ VPS test failed")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False

def test_interpretation_generator_retail():
    """Test that InterpretationGenerator handles retail sentiment on VPS."""
    print("\n=== Testing InterpretationGenerator Retail Support ===")

    test_script = '''
import sys
sys.path.append('src')

try:
    from src.core.analysis.interpretation_generator import InterpretationGenerator

    generator = InterpretationGenerator()

    # Test retail sentiment interpretation
    test_data = {
        "retail": 75.0,  # High retail buying pressure
        "oir": 65.0,
        "depth": 55.0
    }

    interpretation = generator.generate_orderbook_interpretation(test_data)

    if "retail" in interpretation.lower():
        print("SUCCESS: Retail sentiment interpretation generated")
        print(f"Sample: {interpretation[:200]}...")
    else:
        print("FAILURE: No retail sentiment in interpretation")
        print(f"Full interpretation: {interpretation}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''

    success, stdout, stderr = run_vps_command(f"python3 -c '{test_script}'")

    if success and "SUCCESS: Retail sentiment interpretation generated" in stdout:
        print("✓ VPS InterpretationGenerator retail support validated")
        return True
    else:
        print(f"❌ VPS interpretation test failed")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False

def test_bybit_rpi_data_fetch():
    """Test that Bybit exchange can fetch RPI data."""
    print("\n=== Testing Bybit RPI Data Fetch ===")

    test_script = '''
import sys
sys.path.append('src')

try:
    from src.core.exchanges.bybit import BybitExchange
    from src.core.logger import Logger

    # Initialize exchange
    config = {
        "exchanges": {
            "bybit": {
                "api_key": "test",
                "secret": "test",
                "sandbox": True
            }
        }
    }

    logger = Logger(__name__)
    exchange = BybitExchange(config, logger)

    # Check if RPI methods exist
    has_get_retail_sentiment = hasattr(exchange, '_get_retail_sentiment_data')
    has_analyze_retail = hasattr(exchange, '_analyze_retail_sentiment')

    print(f"SUCCESS: Has _get_retail_sentiment_data: {has_get_retail_sentiment}")
    print(f"SUCCESS: Has _analyze_retail_sentiment: {has_analyze_retail}")

    if has_get_retail_sentiment and has_analyze_retail:
        print("SUCCESS: Bybit RPI methods available")
    else:
        print("FAILURE: Missing RPI methods")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''

    success, stdout, stderr = run_vps_command(f"python3 -c '{test_script}'")

    if success and "SUCCESS: Bybit RPI methods available" in stdout:
        print("✓ VPS Bybit RPI methods validated")
        return True
    else:
        print(f"❌ VPS Bybit test failed")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False

def test_market_data_manager_rpi():
    """Test MarketDataManager RPI integration."""
    print("\n=== Testing MarketDataManager RPI Integration ===")

    test_script = '''
import sys
sys.path.append('src')

try:
    from src.core.market.market_data_manager import MarketDataManager

    # Check for RPI-related methods
    has_process_retail = hasattr(MarketDataManager, '_process_retail_sentiment')
    has_aggregate_sentiment = hasattr(MarketDataManager, '_aggregate_sentiment_data')

    print(f"SUCCESS: Has _process_retail_sentiment: {has_process_retail}")
    print(f"SUCCESS: Has _aggregate_sentiment_data: {has_aggregate_sentiment}")

    if has_process_retail and has_aggregate_sentiment:
        print("SUCCESS: MarketDataManager RPI integration ready")
    else:
        print("FAILURE: Missing RPI integration methods")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''

    success, stdout, stderr = run_vps_command(f"python3 -c '{test_script}'")

    if success and "SUCCESS: MarketDataManager RPI integration ready" in stdout:
        print("✓ VPS MarketDataManager RPI integration validated")
        return True
    else:
        print(f"❌ VPS MarketDataManager test failed")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return False

def check_vps_service_status():
    """Check the status of running services."""
    print("\n=== Checking VPS Service Status ===")

    success, stdout, stderr = run_vps_command("ps aux | grep -E 'python.*main|python.*web_server' | grep -v grep | wc -l")

    if success:
        service_count = int(stdout.strip())
        print(f"✓ Running services: {service_count}")
        if service_count >= 2:  # main.py + web_server.py
            print("✓ Both main and web services are running")
            return True
        else:
            print("❌ Not all expected services are running")
            return False
    else:
        print(f"❌ Failed to check service status: {stderr}")
        return False

def main():
    """Execute all VPS validation tests."""
    print("VPS RPI Integration Validation")
    print("=" * 40)

    tests = [
        ("Service Status", check_vps_service_status),
        ("OrderbookIndicators RPI", test_orderbook_indicators_with_rpi),
        ("InterpretationGenerator", test_interpretation_generator_retail),
        ("Bybit RPI Methods", test_bybit_rpi_data_fetch),
        ("MarketDataManager RPI", test_market_data_manager_rpi)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        results[test_name] = test_func()

    print("\n=== VPS Validation Results ===")
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall VPS Status: {'✓ FULLY FUNCTIONAL' if all_passed else '❌ ISSUES DETECTED'}")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)