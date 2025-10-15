#!/usr/bin/env python3
"""
RPI Integration Test Script

This script validates the complete RPI (Retail Price Improvement) integration
by testing all components systematically.

Test Coverage:
1. BybitExchange RPI data fetching
2. MarketDataManager RPI integration
3. DataProcessor RPI validation
4. OrderbookIndicators retail component
5. AlertManager retail alerts
6. Configuration loading

Usage:
    python test_rpi_integration.py [--symbol BTCUSDT] [--verbose]
"""

import asyncio
import sys
import os
import argparse
import yaml
import logging
import time
import traceback
from typing import Dict, Any, List
from pathlib import Path

# Add src directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rpi_integration_test.log')
    ]
)

logger = logging.getLogger(__name__)

class RPIIntegrationTester:
    """Test suite for RPI integration functionality."""

    def __init__(self, symbol: str = "BTCUSDT", verbose: bool = False):
        self.symbol = symbol
        self.verbose = verbose
        self.config = None
        self.test_results = {}

        if self.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete RPI integration test suite."""
        logger.info("🚀 Starting RPI Integration Test Suite")
        logger.info(f"Testing symbol: {self.symbol}")
        logger.info("=" * 60)

        test_methods = [
            ("Configuration Loading", self.test_config_loading),
            ("BybitExchange RPI Fetch", self.test_bybit_rpi_fetch),
            ("MarketDataManager RPI Integration", self.test_market_data_manager_rpi),
            ("DataProcessor RPI Validation", self.test_data_processor_rpi),
            ("OrderbookIndicators Retail Component", self.test_orderbook_indicators_retail),
            ("AlertManager Retail Alerts", self.test_alert_manager_retail),
            ("End-to-End RPI Flow", self.test_end_to_end_rpi_flow)
        ]

        for test_name, test_method in test_methods:
            logger.info(f"\n📋 Running: {test_name}")
            try:
                result = await test_method()
                self.test_results[test_name] = {
                    'status': 'PASSED',
                    'result': result,
                    'error': None
                }
                logger.info(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.test_results[test_name] = {
                    'status': 'FAILED',
                    'result': None,
                    'error': str(e)
                }
                logger.error(f"❌ {test_name}: FAILED - {str(e)}")
                if self.verbose:
                    logger.debug(traceback.format_exc())

        # Generate test report
        self.generate_test_report()
        return self.test_results

    async def test_config_loading(self) -> Dict[str, Any]:
        """Test RPI configuration loading."""
        try:
            config_path = script_dir / 'config' / 'config.yaml'
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)

            # Validate RPI configuration exists
            rpi_config = self.config.get('market_data', {}).get('orderbook', {}).get('rpi', {})

            assert rpi_config, "RPI configuration not found in config.yaml"
            assert 'enabled' in rpi_config, "RPI enabled flag not found"
            assert 'retail_threshold' in rpi_config, "RPI retail_threshold not found"
            assert 'cache_ttl' in rpi_config, "RPI cache_ttl not found"

            logger.info(f"RPI Config: enabled={rpi_config.get('enabled')}, "
                       f"threshold={rpi_config.get('retail_threshold')}, "
                       f"cache_ttl={rpi_config.get('cache_ttl')}")

            return {
                'rpi_enabled': rpi_config.get('enabled'),
                'retail_threshold': rpi_config.get('retail_threshold'),
                'cache_ttl': rpi_config.get('cache_ttl'),
                'extreme_thresholds': rpi_config.get('extreme_thresholds', {})
            }

        except Exception as e:
            raise Exception(f"Configuration loading failed: {str(e)}")

    async def test_bybit_rpi_fetch(self) -> Dict[str, Any]:
        """Test BybitExchange RPI data fetching."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            from src.core.exchanges.manager import ExchangeManager

            # Initialize exchange with config
            if not self.config:
                raise Exception("Configuration not loaded")

            exchange_manager = ExchangeManager(self.config)
            await exchange_manager.initialize()

            exchange = await exchange_manager.get_primary_exchange()

            # Test RPI data fetching
            logger.info(f"Fetching RPI data for {self.symbol}")
            rpi_data = await exchange.fetch_rpi_orderbook(self.symbol, limit=10)

            # Validate RPI data structure
            assert isinstance(rpi_data, dict), "RPI data should be a dictionary"

            if rpi_data:  # If data is available
                assert 'b' in rpi_data or 'a' in rpi_data, "RPI data should contain bids ('b') or asks ('a')"

                bids = rpi_data.get('b', [])
                asks = rpi_data.get('a', [])

                logger.info(f"RPI data received: {len(bids)} bids, {len(asks)} asks")

                # Validate structure of first few levels
                for i, bid in enumerate(bids[:3]):
                    if bid and len(bid) >= 3:
                        price, non_rpi, rpi = float(bid[0]), float(bid[1]), float(bid[2])
                        logger.debug(f"Bid {i+1}: price={price:.2f}, non_rpi={non_rpi:.4f}, rpi={rpi:.4f}")
                        assert price > 0, f"Invalid bid price: {price}"
                        assert non_rpi >= 0, f"Invalid non-RPI size: {non_rpi}"
                        assert rpi >= 0, f"Invalid RPI size: {rpi}"

                return {
                    'data_available': True,
                    'bids_count': len(bids),
                    'asks_count': len(asks),
                    'sample_bid': bids[0] if bids else None,
                    'sample_ask': asks[0] if asks else None,
                    'has_timestamp': 'ts' in rpi_data,
                    'has_sequence': 'seq' in rpi_data
                }
            else:
                logger.warning("No RPI data available (may be normal for some symbols)")
                return {
                    'data_available': False,
                    'message': 'No RPI data available for symbol'
                }

        except Exception as e:
            raise Exception(f"BybitExchange RPI fetch failed: {str(e)}")

    async def test_market_data_manager_rpi(self) -> Dict[str, Any]:
        """Test MarketDataManager RPI integration."""
        try:
            from src.core.market.market_data_manager import MarketDataManager
            from src.core.exchanges.manager import ExchangeManager

            # Initialize components
            exchange_manager = ExchangeManager(self.config)
            await exchange_manager.initialize()

            market_data_manager = MarketDataManager(
                config=self.config,
                exchange_manager=exchange_manager
            )

            # Test enhanced orderbook data fetching
            logger.info(f"Testing enhanced orderbook fetch for {self.symbol}")
            enhanced_data = await market_data_manager._fetch_enhanced_orderbook_data(self.symbol)

            assert isinstance(enhanced_data, dict), "Enhanced orderbook data should be a dictionary"

            if enhanced_data:
                required_fields = ['standard_orderbook', 'rpi_orderbook', 'enhanced_orderbook', 'rpi_enabled']
                for field in required_fields:
                    assert field in enhanced_data, f"Missing required field: {field}"

                logger.info(f"Enhanced orderbook data: "
                          f"standard={bool(enhanced_data.get('standard_orderbook'))}, "
                          f"rpi={bool(enhanced_data.get('rpi_orderbook'))}, "
                          f"enhanced={bool(enhanced_data.get('enhanced_orderbook'))}, "
                          f"rpi_enabled={enhanced_data.get('rpi_enabled')}")

                return {
                    'enhanced_data_available': True,
                    'rpi_enabled': enhanced_data.get('rpi_enabled'),
                    'has_standard': bool(enhanced_data.get('standard_orderbook')),
                    'has_rpi': bool(enhanced_data.get('rpi_orderbook')),
                    'has_enhanced': bool(enhanced_data.get('enhanced_orderbook')),
                    'symbol': enhanced_data.get('symbol'),
                    'timestamp': enhanced_data.get('timestamp')
                }
            else:
                return {
                    'enhanced_data_available': False,
                    'message': 'No enhanced orderbook data available'
                }

        except Exception as e:
            raise Exception(f"MarketDataManager RPI integration failed: {str(e)}")

    async def test_data_processor_rpi(self) -> Dict[str, Any]:
        """Test DataProcessor RPI validation and processing."""
        try:
            from src.data_processing.data_processor import DataProcessor

            # Create test RPI data
            test_rpi_data = {
                'b': [  # bids
                    [50000.0, 1.2, 0.3],  # [price, non_rpi, rpi]
                    [49999.5, 0.8, 0.2],
                    [49999.0, 1.0, 0.1]
                ],
                'a': [  # asks
                    [50001.0, 1.1, 0.4],
                    [50001.5, 0.9, 0.2],
                    [50002.0, 1.3, 0.1]
                ],
                'ts': int(time.time() * 1000),
                'u': 12345,
                'seq': 67890
            }

            processor = DataProcessor()

            # Test RPI data processing
            logger.info("Testing RPI data processing")
            processed_rpi = await processor.process_rpi_orderbook(test_rpi_data)

            assert isinstance(processed_rpi, dict), "Processed RPI data should be a dictionary"

            if processed_rpi:
                assert 'b' in processed_rpi, "Processed RPI should contain bids"
                assert 'a' in processed_rpi, "Processed RPI should contain asks"

                bids = processed_rpi.get('b', [])
                asks = processed_rpi.get('a', [])

                # Validate bid sorting (descending by price)
                for i in range(len(bids) - 1):
                    assert bids[i][0] >= bids[i+1][0], "Bids should be sorted in descending order"

                # Validate ask sorting (ascending by price)
                for i in range(len(asks) - 1):
                    assert asks[i][0] <= asks[i+1][0], "Asks should be sorted in ascending order"

                logger.info(f"RPI processing successful: {len(bids)} bids, {len(asks)} asks")

                return {
                    'processing_successful': True,
                    'bids_processed': len(bids),
                    'asks_processed': len(asks),
                    'metadata_preserved': all(field in processed_rpi for field in ['ts', 'u', 'seq']),
                    'sorting_correct': True
                }

            # Test with invalid data
            logger.info("Testing RPI data validation with invalid data")
            invalid_data = {'invalid': 'data'}
            processed_invalid = await processor.process_rpi_orderbook(invalid_data)

            assert processed_invalid == {}, "Invalid RPI data should return empty dict"

            return {
                'processing_successful': True,
                'validation_works': True,
                'handles_invalid_data': True
            }

        except Exception as e:
            raise Exception(f"DataProcessor RPI processing failed: {str(e)}")

    async def test_orderbook_indicators_retail(self) -> Dict[str, Any]:
        """Test OrderbookIndicators retail component."""
        try:
            from src.indicators.orderbook_indicators import OrderbookIndicators

            # Create test market data with RPI
            test_market_data = {
                'symbol': self.symbol,
                'orderbook': {
                    'bids': [[50000.0, 1.5], [49999.0, 2.0]],
                    'asks': [[50001.0, 1.3], [50002.0, 1.8]],
                    'timestamp': int(time.time() * 1000)
                },
                'rpi_orderbook': {
                    'b': [
                        [50000.0, 1.2, 0.3],  # total = 1.5 (matches standard)
                        [49999.0, 1.8, 0.2]   # total = 2.0 (matches standard)
                    ],
                    'a': [
                        [50001.0, 1.0, 0.3],  # total = 1.3 (matches standard)
                        [50002.0, 1.6, 0.2]   # total = 1.8 (matches standard)
                    ],
                    'ts': int(time.time() * 1000)
                },
                'rpi_enabled': True,
                'trades': []  # Empty for test
            }

            indicators = OrderbookIndicators(self.config)

            # Test retail component calculation directly
            logger.info("Testing retail component calculation")
            retail_score = indicators._calculate_retail_component(test_market_data)

            assert isinstance(retail_score, (int, float)), "Retail score should be numeric"
            assert 0 <= retail_score <= 100, f"Retail score should be 0-100, got {retail_score}"

            logger.info(f"Retail component score: {retail_score:.2f}")

            # Test full orderbook analysis with retail component
            logger.info("Testing full orderbook analysis with retail component")
            analysis_result = await indicators.calculate(test_market_data)

            assert isinstance(analysis_result, dict), "Analysis result should be a dictionary"
            assert 'components' in analysis_result, "Analysis should contain components"
            assert 'retail' in analysis_result['components'], "Analysis should include retail component"

            retail_component_score = analysis_result['components']['retail']
            assert isinstance(retail_component_score, (int, float)), "Retail component should be numeric"
            assert 0 <= retail_component_score <= 100, "Retail component should be 0-100"

            logger.info(f"Full analysis retail component: {retail_component_score:.2f}")

            # Test with no RPI data
            test_market_data_no_rpi = test_market_data.copy()
            test_market_data_no_rpi['rpi_enabled'] = False
            test_market_data_no_rpi.pop('rpi_orderbook', None)

            analysis_no_rpi = await indicators.calculate(test_market_data_no_rpi)
            retail_no_rpi = analysis_no_rpi['components']['retail']

            logger.info(f"Analysis without RPI - retail component: {retail_no_rpi:.2f}")

            return {
                'retail_calculation_works': True,
                'retail_score': retail_score,
                'full_analysis_includes_retail': True,
                'full_analysis_retail_score': retail_component_score,
                'handles_no_rpi_data': True,
                'no_rpi_retail_score': retail_no_rpi,
                'component_count': len(analysis_result['components']),
                'has_9_components': len(analysis_result['components']) >= 9
            }

        except Exception as e:
            raise Exception(f"OrderbookIndicators retail component failed: {str(e)}")

    async def test_alert_manager_retail(self) -> Dict[str, Any]:
        """Test AlertManager retail alert functionality."""
        try:
            from src.monitoring.alert_manager import AlertManager

            alert_manager = AlertManager(self.config)

            # Test retail alert generation helper
            test_analysis = {
                'components': {
                    'retail': 75.0  # Strong buying pressure
                }
            }

            logger.info("Testing retail alert generation")
            retail_alerts = alert_manager._generate_retail_alerts(test_analysis, self.symbol)

            assert isinstance(retail_alerts, list), "Retail alerts should be a list"
            logger.info(f"Generated {len(retail_alerts)} retail alerts")

            for alert in retail_alerts:
                logger.info(f"Alert: {alert}")

            # Test different retail score scenarios
            test_scenarios = [
                {'retail': 85.0, 'expected': 'extreme_buying'},
                {'retail': 15.0, 'expected': 'extreme_selling'},
                {'retail': 75.0, 'expected': 'strong_buying'},
                {'retail': 25.0, 'expected': 'strong_selling'},
                {'retail': 50.0, 'expected': 'neutral'}
            ]

            scenario_results = {}
            for scenario in test_scenarios:
                test_analysis['components']['retail'] = scenario['retail']
                alerts = alert_manager._generate_retail_alerts(test_analysis, self.symbol)
                scenario_results[scenario['expected']] = {
                    'score': scenario['retail'],
                    'alerts_count': len(alerts),
                    'alerts': alerts
                }
                logger.info(f"Scenario {scenario['expected']} (score={scenario['retail']}): {len(alerts)} alerts")

            return {
                'alert_generation_works': True,
                'initial_alerts_count': len(retail_alerts),
                'scenario_results': scenario_results,
                'all_scenarios_tested': len(scenario_results) == 5
            }

        except Exception as e:
            raise Exception(f"AlertManager retail alerts failed: {str(e)}")

    async def test_end_to_end_rpi_flow(self) -> Dict[str, Any]:
        """Test complete end-to-end RPI flow."""
        try:
            from src.core.exchanges.manager import ExchangeManager
            from src.core.market.market_data_manager import MarketDataManager
            from src.data_processing.data_processor import DataProcessor
            from src.indicators.orderbook_indicators import OrderbookIndicators
            from src.monitoring.alert_manager import AlertManager

            logger.info("Starting end-to-end RPI flow test")

            # Initialize all components
            exchange_manager = ExchangeManager(self.config)
            await exchange_manager.initialize()

            market_data_manager = MarketDataManager(
                config=self.config,
                exchange_manager=exchange_manager
            )

            data_processor = DataProcessor()
            orderbook_indicators = OrderbookIndicators(self.config)
            alert_manager = AlertManager(self.config)

            # Step 1: Fetch market data (with RPI if available)
            logger.info("Step 1: Fetching market data")
            market_data = await market_data_manager.get_market_data(self.symbol)

            # Step 2: Process the data
            logger.info("Step 2: Processing market data")
            processed_data = await data_processor.process(market_data)

            # Step 3: Analyze with indicators (including retail component)
            logger.info("Step 3: Analyzing with indicators")
            analysis_result = await orderbook_indicators.calculate(processed_data)

            # Step 4: Generate retail alerts if applicable
            logger.info("Step 4: Generating retail alerts")
            retail_alerts = alert_manager._generate_retail_alerts(analysis_result, self.symbol)

            # Validate end-to-end flow
            flow_validation = {
                'market_data_fetched': bool(market_data),
                'has_orderbook': 'orderbook' in market_data,
                'rpi_data_available': market_data.get('rpi_enabled', False),
                'data_processed': bool(processed_data),
                'analysis_completed': bool(analysis_result),
                'retail_component_present': 'retail' in analysis_result.get('components', {}),
                'retail_alerts_generated': len(retail_alerts) > 0,
                'retail_score': analysis_result.get('components', {}).get('retail', 50.0)
            }

            logger.info("End-to-end flow validation:")
            for key, value in flow_validation.items():
                logger.info(f"  {key}: {value}")

            return {
                'end_to_end_success': True,
                'flow_validation': flow_validation,
                'retail_alerts_count': len(retail_alerts),
                'retail_alerts': retail_alerts,
                'final_retail_score': flow_validation['retail_score']
            }

        except Exception as e:
            raise Exception(f"End-to-end RPI flow failed: {str(e)}")

    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 RPI INTEGRATION TEST REPORT")
        logger.info("=" * 80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASSED')
        failed_tests = total_tests - passed_tests

        logger.info(f"📊 SUMMARY: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")

        if failed_tests > 0:
            logger.error(f"❌ FAILED TESTS: {failed_tests}")
            for test_name, result in self.test_results.items():
                if result['status'] == 'FAILED':
                    logger.error(f"  - {test_name}: {result['error']}")

        logger.info(f"✅ PASSED TESTS: {passed_tests}")
        for test_name, result in self.test_results.items():
            if result['status'] == 'PASSED':
                logger.info(f"  - {test_name}")

        # RPI Integration Status
        logger.info("\n🔍 RPI INTEGRATION STATUS:")

        key_indicators = [
            ('RPI Data Fetching', 'BybitExchange RPI Fetch'),
            ('Enhanced Market Data', 'MarketDataManager RPI Integration'),
            ('Data Processing', 'DataProcessor RPI Validation'),
            ('Retail Analysis', 'OrderbookIndicators Retail Component'),
            ('Alert Generation', 'AlertManager Retail Alerts'),
            ('End-to-End Flow', 'End-to-End RPI Flow')
        ]

        for indicator_name, test_name in key_indicators:
            status = self.test_results.get(test_name, {}).get('status', 'NOT_RUN')
            emoji = '✅' if status == 'PASSED' else '❌' if status == 'FAILED' else '⚠️'
            logger.info(f"  {emoji} {indicator_name}: {status}")

        # Configuration Status
        config_test = self.test_results.get('Configuration Loading', {})
        if config_test.get('status') == 'PASSED':
            config_data = config_test.get('result', {})
            logger.info(f"\n⚙️  RPI CONFIGURATION:")
            logger.info(f"  - Enabled: {config_data.get('rpi_enabled')}")
            logger.info(f"  - Retail Threshold: {config_data.get('retail_threshold')}")
            logger.info(f"  - Cache TTL: {config_data.get('cache_ttl')}s")

        logger.info("\n" + "=" * 80)

        # Write detailed report to file
        report_file = script_dir / 'rpi_integration_test_report.json'
        import json
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': passed_tests/total_tests*100
                },
                'results': self.test_results
            }, f, indent=2, default=str)

        logger.info(f"📄 Detailed report saved to: {report_file}")


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='RPI Integration Test Suite')
    parser.add_argument('--symbol', default='BTCUSDT', help='Trading symbol to test')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    tester = RPIIntegrationTester(symbol=args.symbol, verbose=args.verbose)

    try:
        results = await tester.run_all_tests()

        # Exit code based on test results
        failed_count = sum(1 for result in results.values() if result['status'] == 'FAILED')
        sys.exit(1 if failed_count > 0 else 0)

    except KeyboardInterrupt:
        logger.info("\n🛑 Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"🚨 Test suite crashed: {str(e)}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())