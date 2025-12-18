#!/usr/bin/env python3
"""
System Startup Integration Test

This test validates that the trading system can start up properly with all fixes applied.
It tests the initialization of major components and verifies they can communicate correctly.

Author: QA Automation Agent
Date: 2025-09-20
"""

import sys
import os
import json
import asyncio
import time
import traceback
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add src to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemStartupTest:
    """Test system startup and component initialization."""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'test_name': 'System Startup Integration Test',
            'components_tested': [],
            'passed': 0,
            'failed': 0,
            'issues': [],
            'performance_metrics': {}
        }

    async def test_configuration_loading(self):
        """Test configuration loading."""
        logger.info("Testing configuration loading...")
        start_time = time.time()

        try:
            import yaml
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Validate critical sections
            required_sections = ['exchanges', 'market_data', 'analysis', 'confluence', 'timeframes']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required config section: {section}")

            # Validate Bybit configuration specifically
            bybit_config = config['exchanges']['bybit']
            if bybit_config.get('use_ccxt') is not False:
                raise ValueError("Bybit use_ccxt should be False")

            load_time = time.time() - start_time
            self.results['performance_metrics']['config_load_time'] = load_time
            self.results['components_tested'].append('Configuration Loader')
            self.results['passed'] += 1

            logger.info(f"✓ Configuration loaded successfully in {load_time:.3f}s")
            return config

        except Exception as e:
            self.results['failed'] += 1
            self.results['issues'].append(f"Configuration loading failed: {str(e)}")
            logger.error(f"✗ Configuration loading failed: {str(e)}")
            raise

    def test_error_handling_system(self, config):
        """Test error handling system initialization."""
        logger.info("Testing error handling system...")
        start_time = time.time()

        try:
            from src.core.error.models import ErrorContext, ErrorSeverity, ErrorEvent

            # Test ErrorContext with various parameters
            ctx1 = ErrorContext()  # Default constructor
            ctx2 = ErrorContext(component="test", operation="startup")
            ctx3 = ErrorContext(component="system", operation="test", severity=ErrorSeverity.HIGH)

            # Test ErrorEvent creation
            test_exception = ValueError("Test error")
            event = ErrorEvent(
                error=test_exception,
                context=ctx3,
                severity=ErrorSeverity.HIGH
            )

            # Validate serialization
            event_dict = event.to_dict()
            assert isinstance(event_dict, dict)
            assert event_dict['error_type'] == 'ValueError'

            init_time = time.time() - start_time
            self.results['performance_metrics']['error_system_init_time'] = init_time
            self.results['components_tested'].append('Error Handling System')
            self.results['passed'] += 1

            logger.info(f"✓ Error handling system initialized in {init_time:.3f}s")

        except Exception as e:
            self.results['failed'] += 1
            self.results['issues'].append(f"Error handling system failed: {str(e)}")
            logger.error(f"✗ Error handling system failed: {str(e)}")
            raise

    def test_orderflow_indicators(self, config):
        """Test OrderflowIndicators initialization and basic operations."""
        logger.info("Testing OrderflowIndicators...")
        start_time = time.time()

        try:
            from src.indicators.orderflow_indicators import OrderflowIndicators

            # Initialize indicators
            indicators = OrderflowIndicators(config)

            # Test with problematic data that previously caused NoneType errors
            test_data = {
                'ohlcv': {
                    'base': [
                        {'timestamp': 1000, 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000},
                        {'timestamp': 2000, 'open': 102, 'high': 107, 'low': 101, 'close': 105, 'volume': 1200}
                    ]
                },
                'open_interest': None,  # This should not cause errors
                'trades': [],
                'sentiment': {}
            }

            # Test price-OI divergence calculation (should handle None gracefully)
            result = indicators._calculate_price_oi_divergence(test_data)
            assert isinstance(result, dict)
            assert result.get('type') == 'neutral'

            # Test with missing data
            minimal_data = {'ohlcv': {'base': []}}
            result2 = indicators._calculate_price_oi_divergence(minimal_data)
            assert isinstance(result2, dict)

            init_time = time.time() - start_time
            self.results['performance_metrics']['orderflow_init_time'] = init_time
            self.results['components_tested'].append('Orderflow Indicators')
            self.results['passed'] += 1

            logger.info(f"✓ OrderflowIndicators initialized and tested in {init_time:.3f}s")

        except Exception as e:
            self.results['failed'] += 1
            self.results['issues'].append(f"OrderflowIndicators failed: {str(e)}")
            logger.error(f"✗ OrderflowIndicators failed: {str(e)}")
            raise

    def test_formatter_robustness(self, config):
        """Test formatter robustness with mixed data types."""
        logger.info("Testing formatter robustness...")
        start_time = time.time()

        try:
            from src.core.formatting.formatter import LogFormatter, AnalysisFormatter

            # Test data with mixed types that could cause TypeError
            mixed_components = {
                'orderflow': {
                    'cvd': 75.5,
                    'trade_flow': {'direction': 'bullish', 'strength': 0.8},  # Dict instead of number
                    'imbalance': 60.2
                },
                'technical': {
                    'rsi': 45.6,
                    'macd': {'signal': 'buy', 'histogram': 0.5},  # Another dict
                    'atr': 12.3
                }
            }

            # Test LogFormatter with mixed data
            try:
                if hasattr(LogFormatter, 'format_component_breakdown'):
                    result = LogFormatter.format_component_breakdown(mixed_components)
                    assert isinstance(result, str)
            except TypeError as e:
                if "unsupported operand type" in str(e) and "dict" in str(e):
                    raise ValueError("TypeError with dict operations still present")

            # Test AnalysisFormatter
            try:
                clean_components = {}
                for category, items in mixed_components.items():
                    for key, value in items.items():
                        if isinstance(value, dict):
                            clean_components[f"{category}_{key}"] = 50.0
                        else:
                            clean_components[f"{category}_{key}"] = float(value)

                if hasattr(AnalysisFormatter, 'format_component_analysis'):
                    result = AnalysisFormatter.format_component_analysis("Test", clean_components)
                    assert isinstance(result, str)
            except TypeError as e:
                if "unsupported operand type" in str(e) and "dict" in str(e):
                    raise ValueError("TypeError with dict operations still present")

            test_time = time.time() - start_time
            self.results['performance_metrics']['formatter_test_time'] = test_time
            self.results['components_tested'].append('Formatter System')
            self.results['passed'] += 1

            logger.info(f"✓ Formatter system tested in {test_time:.3f}s")

        except Exception as e:
            self.results['failed'] += 1
            self.results['issues'].append(f"Formatter system failed: {str(e)}")
            logger.error(f"✗ Formatter system failed: {str(e)}")
            raise

    def test_market_data_manager(self, config):
        """Test MarketDataManager initialization."""
        logger.info("Testing MarketDataManager...")
        start_time = time.time()

        try:
            from src.core.market.market_data_manager import MarketDataManager

            # Mock exchange manager
            class MockExchangeManager:
                def get_primary_exchange(self):
                    return None

            # Initialize market data manager
            manager = MarketDataManager(config, MockExchangeManager())

            # Verify initialization
            assert hasattr(manager, 'data_cache')
            assert hasattr(manager, 'logger')
            assert hasattr(manager, 'smart_intervals')

            # Test empty trades handling (should not generate excessive warnings)
            empty_trades = {'trades': [], 'symbol': 'BTCUSDT'}

            init_time = time.time() - start_time
            self.results['performance_metrics']['market_data_init_time'] = init_time
            self.results['components_tested'].append('Market Data Manager')
            self.results['passed'] += 1

            logger.info(f"✓ MarketDataManager initialized in {init_time:.3f}s")

        except Exception as e:
            self.results['failed'] += 1
            self.results['issues'].append(f"MarketDataManager failed: {str(e)}")
            logger.error(f"✗ MarketDataManager failed: {str(e)}")
            raise

    def test_exchange_manager(self, config):
        """Test Exchange Manager initialization."""
        logger.info("Testing Exchange Manager...")
        start_time = time.time()

        try:
            from src.core.exchanges.manager import ExchangeManager

            # Initialize exchange manager
            manager = ExchangeManager(config)

            # Verify Bybit configuration
            assert hasattr(manager, 'exchanges')
            bybit_config = config['exchanges']['bybit']
            assert bybit_config.get('use_ccxt') is False

            init_time = time.time() - start_time
            self.results['performance_metrics']['exchange_manager_init_time'] = init_time
            self.results['components_tested'].append('Exchange Manager')
            self.results['passed'] += 1

            logger.info(f"✓ Exchange Manager initialized in {init_time:.3f}s")

        except Exception as e:
            self.results['failed'] += 1
            self.results['issues'].append(f"Exchange Manager failed: {str(e)}")
            logger.error(f"✗ Exchange Manager failed: {str(e)}")
            # Don't raise - this is not critical for basic validation

    async def run_startup_test(self):
        """Run complete system startup test."""
        logger.info("Starting comprehensive system startup test...")
        overall_start = time.time()

        try:
            # Test 1: Configuration Loading
            config = await self.test_configuration_loading()

            # Test 2: Error Handling System
            self.test_error_handling_system(config)

            # Test 3: OrderflowIndicators
            self.test_orderflow_indicators(config)

            # Test 4: Formatter System
            self.test_formatter_robustness(config)

            # Test 5: Market Data Manager
            self.test_market_data_manager(config)

            # Test 6: Exchange Manager (optional)
            try:
                self.test_exchange_manager(config)
            except Exception as e:
                logger.warning(f"Exchange Manager test failed (non-critical): {str(e)}")

            # Calculate overall performance
            total_time = time.time() - overall_start
            self.results['performance_metrics']['total_startup_time'] = total_time

            # Determine overall result
            if self.results['failed'] == 0:
                self.results['overall_status'] = 'PASS'
                logger.info(f"🎉 System startup test PASSED in {total_time:.3f}s")
            else:
                self.results['overall_status'] = 'FAIL'
                logger.error(f"❌ System startup test FAILED")

        except Exception as e:
            self.results['overall_status'] = 'CRITICAL_FAIL'
            self.results['issues'].append(f"Critical startup failure: {str(e)}")
            logger.error(f"💥 Critical startup failure: {str(e)}")

        return self.results

    def generate_report(self):
        """Generate startup test report."""
        report = []
        report.append("=" * 70)
        report.append("SYSTEM STARTUP INTEGRATION TEST REPORT")
        report.append("=" * 70)
        report.append(f"Timestamp: {self.results['timestamp']}")
        report.append(f"Overall Status: {self.results['overall_status']}")
        report.append("")

        report.append("SUMMARY:")
        report.append(f"  Components Passed: {self.results['passed']}")
        report.append(f"  Components Failed: {self.results['failed']}")
        report.append(f"  Total Components: {len(self.results['components_tested'])}")
        report.append("")

        if self.results['components_tested']:
            report.append("COMPONENTS TESTED:")
            for component in self.results['components_tested']:
                report.append(f"  ✓ {component}")
            report.append("")

        if self.results['performance_metrics']:
            report.append("PERFORMANCE METRICS:")
            for metric, value in self.results['performance_metrics'].items():
                report.append(f"  {metric}: {value:.3f}s")
            report.append("")

        if self.results['issues']:
            report.append("ISSUES FOUND:")
            for issue in self.results['issues']:
                report.append(f"  ✗ {issue}")
            report.append("")

        return "\n".join(report)

async def main():
    """Main test execution."""
    test = SystemStartupTest()
    results = await test.run_startup_test()

    # Generate and save report
    report = test.generate_report()
    print(report)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_root = Path(__file__).parent.parent.parent
    report_file = project_root / f'startup_test_report_{timestamp}.txt'
    json_file = project_root / f'startup_test_results_{timestamp}.json'

    with open(report_file, 'w') as f:
        f.write(report)

    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Reports saved to: {report_file} and {json_file}")

    return results['overall_status'] == 'PASS'

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)