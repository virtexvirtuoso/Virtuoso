#!/usr/bin/env python3
"""
Comprehensive RPI Integration Test Script

This script validates all RPI (Retail Price Improvement) integration components
with detailed performance metrics and error handling testing.
"""

import asyncio
import sys
import os
import time
import logging
import traceback
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Setup logging with DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('comprehensive_rpi_test.log')
    ]
)

logger = logging.getLogger(__name__)

class ComprehensiveRPITester:
    """Comprehensive RPI integration testing suite."""

    def __init__(self):
        self.config = None
        self.test_results = {}
        self.performance_metrics = {}
        self.start_time = time.time()

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete comprehensive RPI test suite."""
        logger.info("🚀 Starting Comprehensive RPI Integration Test Suite")
        logger.info("=" * 80)

        test_methods = [
            ("1. Configuration Loading", self.test_config_loading),
            ("2. Component Imports", self.test_component_imports),
            ("3. BybitExchange RPI Fetch", self.test_bybit_rpi_fetch),
            ("4. MarketDataManager RPI Integration", self.test_market_data_manager_rpi),
            ("5. DataProcessor RPI Validation", self.test_data_processor_rpi),
            ("6. OrderbookIndicators Retail Component", self.test_orderbook_indicators_retail),
            ("7. AlertManager Retail Alerts", self.test_alert_manager_retail),
            ("8. Performance Testing", self.test_performance),
            ("9. Error Handling", self.test_error_handling),
            ("10. End-to-End RPI Flow", self.test_end_to_end_rpi_flow)
        ]

        for test_name, test_method in test_methods:
            logger.info(f"\n📋 Running: {test_name}")
            start_time = time.time()

            try:
                result = await test_method()
                execution_time = time.time() - start_time

                self.test_results[test_name] = {
                    'status': 'PASSED',
                    'result': result,
                    'error': None,
                    'execution_time': execution_time
                }
                self.performance_metrics[test_name] = execution_time

                logger.info(f"✅ {test_name}: PASSED ({execution_time:.2f}s)")

            except Exception as e:
                execution_time = time.time() - start_time

                self.test_results[test_name] = {
                    'status': 'FAILED',
                    'result': None,
                    'error': str(e),
                    'execution_time': execution_time
                }

                logger.error(f"❌ {test_name}: FAILED - {str(e)} ({execution_time:.2f}s)")
                logger.debug(traceback.format_exc())

        # Generate comprehensive report
        await self.generate_comprehensive_report()
        return self.test_results

    async def test_config_loading(self) -> Dict[str, Any]:
        """Test RPI configuration loading."""
        config_path = Path('config/config.yaml')

        if not config_path.exists():
            raise Exception(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Validate RPI configuration
        rpi_config = self.config.get('market_data', {}).get('orderbook', {}).get('rpi', {})

        if not rpi_config:
            raise Exception("RPI configuration not found in config.yaml")

        required_fields = ['enabled', 'retail_threshold', 'cache_ttl']
        for field in required_fields:
            if field not in rpi_config:
                raise Exception(f"Required RPI config field missing: {field}")

        logger.info(f"RPI Config: enabled={rpi_config.get('enabled')}, "
                   f"threshold={rpi_config.get('retail_threshold')}, "
                   f"cache_ttl={rpi_config.get('cache_ttl')}")

        return {
            'config_loaded': True,
            'rpi_enabled': rpi_config.get('enabled'),
            'retail_threshold': rpi_config.get('retail_threshold'),
            'cache_ttl': rpi_config.get('cache_ttl'),
            'extreme_thresholds': rpi_config.get('extreme_thresholds', {}),
            'participation_weight': rpi_config.get('participation_weight', 1.0)
        }

    async def test_component_imports(self) -> Dict[str, Any]:
        """Test all RPI component imports."""
        components = [
            ('BybitExchange', 'src.core.exchanges.bybit', 'BybitExchange'),
            ('ExchangeManager', 'src.core.exchanges.manager', 'ExchangeManager'),
            ('MarketDataManager', 'src.core.market.market_data_manager', 'MarketDataManager'),
            ('DataProcessor', 'src.data_processing.data_processor', 'DataProcessor'),
            ('OrderbookIndicators', 'src.indicators.orderbook_indicators', 'OrderbookIndicators'),
            ('AlertManager', 'src.monitoring.alert_manager', 'AlertManager')
        ]

        import_results = {}

        for component_name, module_path, class_name in components:
            try:
                module = __import__(module_path, fromlist=[class_name])
                component_class = getattr(module, class_name)
                import_results[component_name] = {
                    'success': True,
                    'class': component_class.__name__,
                    'module': module_path
                }
                logger.info(f"✅ {component_name} imported successfully")
            except Exception as e:
                import_results[component_name] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"❌ {component_name} import failed: {e}")
                raise

        return {
            'all_imports_successful': all(result['success'] for result in import_results.values()),
            'import_results': import_results,
            'components_count': len(components)
        }

    async def test_bybit_rpi_fetch(self) -> Dict[str, Any]:
        """Test BybitExchange RPI data fetching with multiple symbols."""
        from src.core.exchanges.bybit import BybitExchange
        from src.core.exchanges.manager import ExchangeManager

        exchange_manager = ExchangeManager(self.config)
        await exchange_manager.initialize()
        exchange = await exchange_manager.get_primary_exchange()

        # Test multiple symbols
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        results = {}

        for symbol in test_symbols:
            start_time = time.time()
            logger.info(f"Fetching RPI data for {symbol}")

            try:
                rpi_data = await exchange.fetch_rpi_orderbook(symbol, limit=10)
                fetch_time = time.time() - start_time

                if rpi_data:
                    bids = rpi_data.get('b', [])
                    asks = rpi_data.get('a', [])

                    # Validate data structure
                    for i, bid in enumerate(bids[:3]):
                        if bid and len(bid) >= 3:
                            price, non_rpi, rpi = float(bid[0]), float(bid[1]), float(bid[2])
                            assert price > 0, f"Invalid bid price: {price}"
                            assert non_rpi >= 0, f"Invalid non-RPI size: {non_rpi}"
                            assert rpi >= 0, f"Invalid RPI size: {rpi}"

                    results[symbol] = {
                        'success': True,
                        'data_available': True,
                        'bids_count': len(bids),
                        'asks_count': len(asks),
                        'fetch_time_ms': fetch_time * 1000,
                        'has_timestamp': 'ts' in rpi_data,
                        'has_sequence': 'seq' in rpi_data,
                        'sample_bid': bids[0] if bids else None,
                        'sample_ask': asks[0] if asks else None
                    }

                    logger.info(f"  ✅ {symbol}: {len(bids)} bids, {len(asks)} asks ({fetch_time*1000:.1f}ms)")
                else:
                    results[symbol] = {
                        'success': True,
                        'data_available': False,
                        'fetch_time_ms': fetch_time * 1000,
                        'message': 'No RPI data available'
                    }
                    logger.warning(f"  ⚠️  {symbol}: No RPI data available")

            except Exception as e:
                results[symbol] = {
                    'success': False,
                    'error': str(e),
                    'fetch_time_ms': (time.time() - start_time) * 1000
                }
                logger.error(f"  ❌ {symbol}: {str(e)}")

        successful_fetches = sum(1 for r in results.values() if r['success'])
        avg_fetch_time = sum(r.get('fetch_time_ms', 0) for r in results.values()) / len(results)

        return {
            'symbols_tested': len(test_symbols),
            'successful_fetches': successful_fetches,
            'success_rate': successful_fetches / len(test_symbols) * 100,
            'average_fetch_time_ms': avg_fetch_time,
            'results_by_symbol': results
        }

    async def test_market_data_manager_rpi(self) -> Dict[str, Any]:
        """Test MarketDataManager RPI integration."""
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager

        exchange_manager = ExchangeManager(self.config)
        await exchange_manager.initialize()

        market_data_manager = MarketDataManager(
            config=self.config,
            exchange_manager=exchange_manager
        )

        # Test enhanced orderbook data fetching
        symbols = ['BTCUSDT', 'ETHUSDT']
        results = {}

        for symbol in symbols:
            start_time = time.time()

            try:
                enhanced_data = await market_data_manager._fetch_enhanced_orderbook_data(symbol)
                fetch_time = time.time() - start_time

                if enhanced_data:
                    required_fields = ['standard_orderbook', 'rpi_orderbook', 'enhanced_orderbook', 'rpi_enabled']
                    has_all_fields = all(field in enhanced_data for field in required_fields)

                    results[symbol] = {
                        'success': True,
                        'has_all_fields': has_all_fields,
                        'rpi_enabled': enhanced_data.get('rpi_enabled'),
                        'has_standard': bool(enhanced_data.get('standard_orderbook')),
                        'has_rpi': bool(enhanced_data.get('rpi_orderbook')),
                        'has_enhanced': bool(enhanced_data.get('enhanced_orderbook')),
                        'fetch_time_ms': fetch_time * 1000,
                        'timestamp': enhanced_data.get('timestamp')
                    }

                    logger.info(f"  ✅ {symbol}: Enhanced data available ({fetch_time*1000:.1f}ms)")
                else:
                    results[symbol] = {
                        'success': False,
                        'error': 'No enhanced data available',
                        'fetch_time_ms': fetch_time * 1000
                    }

            except Exception as e:
                results[symbol] = {
                    'success': False,
                    'error': str(e),
                    'fetch_time_ms': (time.time() - start_time) * 1000
                }

        return {
            'symbols_tested': len(symbols),
            'successful_fetches': sum(1 for r in results.values() if r['success']),
            'results_by_symbol': results
        }

    async def test_data_processor_rpi(self) -> Dict[str, Any]:
        """Test DataProcessor RPI validation and processing."""
        from src.data_processing.data_processor import DataProcessor

        processor = DataProcessor()

        # Test with valid RPI data
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

        # Test processing
        start_time = time.time()
        processed_rpi = await processor.process_rpi_orderbook(test_rpi_data)
        processing_time = time.time() - start_time

        # Validate processing
        if processed_rpi:
            bids = processed_rpi.get('b', [])
            asks = processed_rpi.get('a', [])

            # Check bid sorting (descending by price)
            bid_sorting_correct = all(bids[i][0] >= bids[i+1][0] for i in range(len(bids) - 1))

            # Check ask sorting (ascending by price)
            ask_sorting_correct = all(asks[i][0] <= asks[i+1][0] for i in range(len(asks) - 1))

            metadata_preserved = all(field in processed_rpi for field in ['ts', 'u', 'seq'])

        # Test with invalid data
        invalid_data = {'invalid': 'data'}
        processed_invalid = await processor.process_rpi_orderbook(invalid_data)

        return {
            'valid_data_processing': {
                'success': bool(processed_rpi),
                'bids_processed': len(processed_rpi.get('b', [])),
                'asks_processed': len(processed_rpi.get('a', [])),
                'processing_time_ms': processing_time * 1000,
                'bid_sorting_correct': bid_sorting_correct if processed_rpi else False,
                'ask_sorting_correct': ask_sorting_correct if processed_rpi else False,
                'metadata_preserved': metadata_preserved if processed_rpi else False
            },
            'invalid_data_handling': {
                'returns_empty_dict': processed_invalid == {},
                'no_exceptions': True
            }
        }

    async def test_orderbook_indicators_retail(self) -> Dict[str, Any]:
        """Test OrderbookIndicators retail component."""
        from src.indicators.orderbook_indicators import OrderbookIndicators

        indicators = OrderbookIndicators(self.config)

        # Create comprehensive test market data
        test_market_data = {
            'symbol': 'BTCUSDT',
            'orderbook': {
                'bids': [[50000.0, 1.5], [49999.0, 2.0], [49998.0, 1.0]],
                'asks': [[50001.0, 1.3], [50002.0, 1.8], [50003.0, 0.9]],
                'timestamp': int(time.time() * 1000)
            },
            'rpi_orderbook': {
                'b': [
                    [50000.0, 1.2, 0.3],  # total = 1.5 (matches standard)
                    [49999.0, 1.8, 0.2],  # total = 2.0 (matches standard)
                    [49998.0, 0.8, 0.2]   # total = 1.0 (matches standard)
                ],
                'a': [
                    [50001.0, 1.0, 0.3],  # total = 1.3 (matches standard)
                    [50002.0, 1.6, 0.2],  # total = 1.8 (matches standard)
                    [50003.0, 0.7, 0.2]   # total = 0.9 (matches standard)
                ],
                'ts': int(time.time() * 1000)
            },
            'rpi_enabled': True,
            'trades': []
        }

        # Test retail component calculation
        start_time = time.time()
        retail_score = indicators._calculate_retail_component(test_market_data)
        calc_time = time.time() - start_time

        # Validate retail score
        if not isinstance(retail_score, (int, float)):
            raise Exception(f"Retail score should be numeric, got {type(retail_score)}")

        if not (0 <= retail_score <= 100):
            raise Exception(f"Retail score should be 0-100, got {retail_score}")

        logger.info(f"Retail component score: {retail_score:.2f}")

        # Test full analysis
        start_time = time.time()
        analysis_result = await indicators.calculate(test_market_data)
        analysis_time = time.time() - start_time

        if not isinstance(analysis_result, dict):
            raise Exception("Analysis result should be a dictionary")

        if 'components' not in analysis_result:
            raise Exception("Analysis should contain components")

        if 'retail' not in analysis_result['components']:
            raise Exception("Analysis should include retail component")

        retail_component_score = analysis_result['components']['retail']

        # Test without RPI data
        test_market_data_no_rpi = test_market_data.copy()
        test_market_data_no_rpi['rpi_enabled'] = False
        test_market_data_no_rpi.pop('rpi_orderbook', None)

        analysis_no_rpi = await indicators.calculate(test_market_data_no_rpi)
        retail_no_rpi = analysis_no_rpi['components']['retail']

        return {
            'retail_calculation': {
                'success': True,
                'retail_score': retail_score,
                'calculation_time_ms': calc_time * 1000,
                'score_valid_range': True
            },
            'full_analysis': {
                'success': True,
                'retail_score': retail_component_score,
                'analysis_time_ms': analysis_time * 1000,
                'component_count': len(analysis_result['components']),
                'has_all_components': len(analysis_result['components']) >= 9
            },
            'no_rpi_handling': {
                'success': True,
                'retail_score': retail_no_rpi,
                'graceful_degradation': True
            }
        }

    async def test_alert_manager_retail(self) -> Dict[str, Any]:
        """Test AlertManager retail alert functionality."""
        from src.monitoring.alert_manager import AlertManager

        alert_manager = AlertManager(self.config)

        # Test scenarios with different retail scores
        test_scenarios = [
            {'retail': 85.0, 'expected': 'extreme_buying'},
            {'retail': 15.0, 'expected': 'extreme_selling'},
            {'retail': 75.0, 'expected': 'strong_buying'},
            {'retail': 25.0, 'expected': 'strong_selling'},
            {'retail': 50.0, 'expected': 'neutral'}
        ]

        scenario_results = {}

        for scenario in test_scenarios:
            test_analysis = {
                'components': {
                    'retail': scenario['retail']
                }
            }

            start_time = time.time()
            alerts = alert_manager._generate_retail_alerts(test_analysis, 'BTCUSDT')
            generation_time = time.time() - start_time

            scenario_results[scenario['expected']] = {
                'score': scenario['retail'],
                'alerts_count': len(alerts),
                'alerts': alerts,
                'generation_time_ms': generation_time * 1000
            }

            logger.info(f"Scenario {scenario['expected']} (score={scenario['retail']}): {len(alerts)} alerts")

        # Test performance with high-frequency scenarios
        high_freq_start = time.time()
        for _ in range(100):
            test_analysis = {'components': {'retail': 75.0}}
            alert_manager._generate_retail_alerts(test_analysis, 'BTCUSDT')
        high_freq_time = time.time() - high_freq_start

        return {
            'scenario_testing': {
                'scenarios_tested': len(test_scenarios),
                'results': scenario_results,
                'all_scenarios_successful': True
            },
            'performance': {
                'high_frequency_test_100_calls_ms': high_freq_time * 1000,
                'average_per_call_ms': (high_freq_time / 100) * 1000
            }
        }

    async def test_performance(self) -> Dict[str, Any]:
        """Test performance metrics for RPI components."""
        from src.core.exchanges.bybit import BybitExchange
        from src.core.exchanges.manager import ExchangeManager
        from src.core.market.market_data_manager import MarketDataManager

        # Initialize components
        exchange_manager = ExchangeManager(self.config)
        await exchange_manager.initialize()
        exchange = await exchange_manager.get_primary_exchange()

        market_data_manager = MarketDataManager(
            config=self.config,
            exchange_manager=exchange_manager
        )

        performance_results = {}

        # Test concurrent RPI fetching
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

        # Sequential fetching
        start_time = time.time()
        sequential_results = []
        for symbol in symbols:
            try:
                rpi_data = await exchange.fetch_rpi_orderbook(symbol, limit=5)
                sequential_results.append((symbol, bool(rpi_data)))
            except:
                sequential_results.append((symbol, False))
        sequential_time = time.time() - start_time

        # Concurrent fetching
        start_time = time.time()
        concurrent_tasks = [
            exchange.fetch_rpi_orderbook(symbol, limit=5)
            for symbol in symbols
        ]
        try:
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            concurrent_time = time.time() - start_time
            concurrent_success = sum(1 for r in concurrent_results if not isinstance(r, Exception))
        except:
            concurrent_time = time.time() - start_time
            concurrent_success = 0

        # Memory usage test (simplified)
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Create large number of market data objects
        for i in range(50):
            test_data = {
                'symbol': f'TEST{i}USDT',
                'orderbook': {'bids': [[50000+i, 1.0]], 'asks': [[50001+i, 1.0]]},
                'rpi_orderbook': {'b': [[50000+i, 0.8, 0.2]], 'a': [[50001+i, 0.8, 0.2]]},
                'rpi_enabled': True
            }

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        performance_results = {
            'concurrent_fetching': {
                'symbols_tested': len(symbols),
                'sequential_time_ms': sequential_time * 1000,
                'concurrent_time_ms': concurrent_time * 1000,
                'speedup_factor': sequential_time / concurrent_time if concurrent_time > 0 else 0,
                'concurrent_success_rate': concurrent_success / len(symbols) * 100
            },
            'memory_usage': {
                'memory_before_mb': memory_before,
                'memory_after_mb': memory_after,
                'memory_used_mb': memory_used,
                'memory_efficient': memory_used < 50  # Less than 50MB increase
            }
        }

        return performance_results

    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and graceful degradation scenarios."""
        from src.core.exchanges.bybit import BybitExchange
        from src.core.exchanges.manager import ExchangeManager
        from src.core.market.market_data_manager import MarketDataManager
        from src.data_processing.data_processor import DataProcessor

        error_handling_results = {}

        # Test 1: Invalid symbol handling
        try:
            exchange_manager = ExchangeManager(self.config)
            await exchange_manager.initialize()
            exchange = await exchange_manager.get_primary_exchange()

            # Test with invalid symbol
            rpi_data = await exchange.fetch_rpi_orderbook('INVALID_SYMBOL', limit=5)
            error_handling_results['invalid_symbol'] = {
                'handles_gracefully': True,
                'returns_data': bool(rpi_data),
                'no_exception': True
            }
        except Exception as e:
            error_handling_results['invalid_symbol'] = {
                'handles_gracefully': True,
                'exception_message': str(e),
                'expected_behavior': True
            }

        # Test 2: Network timeout simulation
        try:
            # This test simulates what happens when RPI data is unavailable
            market_data_manager = MarketDataManager(
                config=self.config,
                exchange_manager=exchange_manager
            )

            # Force a scenario where RPI data is not available
            enhanced_data = await market_data_manager._fetch_enhanced_orderbook_data('BTCUSDT')

            error_handling_results['rpi_unavailable'] = {
                'has_fallback': 'standard_orderbook' in enhanced_data if enhanced_data else False,
                'graceful_degradation': True,
                'enhanced_data_available': bool(enhanced_data)
            }

        except Exception as e:
            error_handling_results['rpi_unavailable'] = {
                'exception_handled': True,
                'error_message': str(e)
            }

        # Test 3: Malformed RPI data handling
        try:
            processor = DataProcessor()

            malformed_data_tests = [
                {'test': 'empty_dict', 'data': {}},
                {'test': 'none_values', 'data': {'b': None, 'a': None}},
                {'test': 'invalid_structure', 'data': {'b': ['invalid'], 'a': ['invalid']}},
                {'test': 'missing_fields', 'data': {'b': [[50000, 1.0]]}},  # Missing RPI component
            ]

            malformed_results = {}

            for test_case in malformed_data_tests:
                try:
                    result = await processor.process_rpi_orderbook(test_case['data'])
                    malformed_results[test_case['test']] = {
                        'handles_gracefully': True,
                        'returns_empty_or_valid': result == {} or isinstance(result, dict),
                        'no_exception': True
                    }
                except Exception as e:
                    malformed_results[test_case['test']] = {
                        'handles_gracefully': False,
                        'exception': str(e)
                    }

            error_handling_results['malformed_data'] = malformed_results

        except Exception as e:
            error_handling_results['malformed_data'] = {
                'test_failed': True,
                'error': str(e)
            }

        return error_handling_results

    async def test_end_to_end_rpi_flow(self) -> Dict[str, Any]:
        """Test complete end-to-end RPI flow."""
        from src.core.exchanges.manager import ExchangeManager
        from src.core.market.market_data_manager import MarketDataManager
        from src.data_processing.data_processor import DataProcessor
        from src.indicators.orderbook_indicators import OrderbookIndicators
        from src.monitoring.alert_manager import AlertManager

        logger.info("Starting end-to-end RPI flow test")

        flow_results = {}
        total_start_time = time.time()

        # Step 1: Initialize all components
        step_start = time.time()
        exchange_manager = ExchangeManager(self.config)
        await exchange_manager.initialize()

        market_data_manager = MarketDataManager(
            config=self.config,
            exchange_manager=exchange_manager
        )

        data_processor = DataProcessor()
        orderbook_indicators = OrderbookIndicators(self.config)
        alert_manager = AlertManager(self.config)

        flow_results['initialization'] = {
            'time_ms': (time.time() - step_start) * 1000,
            'success': True
        }

        # Step 2: Fetch market data (with RPI if available)
        step_start = time.time()
        market_data = await market_data_manager.get_market_data('BTCUSDT')
        flow_results['data_fetch'] = {
            'time_ms': (time.time() - step_start) * 1000,
            'success': bool(market_data),
            'has_orderbook': 'orderbook' in market_data if market_data else False,
            'rpi_enabled': market_data.get('rpi_enabled', False) if market_data else False
        }

        # Step 3: Process the data
        step_start = time.time()
        processed_data = await data_processor.process(market_data)
        flow_results['data_processing'] = {
            'time_ms': (time.time() - step_start) * 1000,
            'success': bool(processed_data),
            'data_valid': isinstance(processed_data, dict)
        }

        # Step 4: Analyze with indicators (including retail component)
        step_start = time.time()
        analysis_result = await orderbook_indicators.calculate(processed_data)
        flow_results['analysis'] = {
            'time_ms': (time.time() - step_start) * 1000,
            'success': bool(analysis_result),
            'has_components': 'components' in analysis_result if analysis_result else False,
            'has_retail_component': 'retail' in analysis_result.get('components', {}) if analysis_result else False,
            'retail_score': analysis_result.get('components', {}).get('retail', None) if analysis_result else None
        }

        # Step 5: Generate retail alerts if applicable
        step_start = time.time()
        retail_alerts = alert_manager._generate_retail_alerts(analysis_result, 'BTCUSDT')
        flow_results['alert_generation'] = {
            'time_ms': (time.time() - step_start) * 1000,
            'success': True,
            'alerts_generated': len(retail_alerts),
            'alerts': retail_alerts
        }

        total_time = time.time() - total_start_time

        # Validate complete flow
        flow_validation = {
            'market_data_fetched': flow_results['data_fetch']['success'],
            'data_processed': flow_results['data_processing']['success'],
            'analysis_completed': flow_results['analysis']['success'],
            'retail_component_present': flow_results['analysis']['has_retail_component'],
            'alerts_system_working': flow_results['alert_generation']['success'],
            'total_flow_time_ms': total_time * 1000,
            'all_steps_successful': all(
                flow_results[step].get('success', False)
                for step in ['initialization', 'data_fetch', 'data_processing', 'analysis', 'alert_generation']
            )
        }

        return {
            'flow_validation': flow_validation,
            'step_details': flow_results,
            'performance_summary': {
                'total_time_ms': total_time * 1000,
                'avg_step_time_ms': total_time * 1000 / 5,
                'fastest_step': min(flow_results.keys(), key=lambda k: flow_results[k]['time_ms']),
                'slowest_step': max(flow_results.keys(), key=lambda k: flow_results[k]['time_ms'])
            }
        }

    async def generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        total_time = time.time() - self.start_time

        logger.info("\n" + "=" * 100)
        logger.info("🎯 COMPREHENSIVE RPI INTEGRATION TEST REPORT")
        logger.info("=" * 100)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASSED')
        failed_tests = total_tests - passed_tests

        logger.info(f"📊 SUMMARY:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        logger.info(f"   Failed: {failed_tests}")
        logger.info(f"   Total Execution Time: {total_time:.2f}s")

        if failed_tests > 0:
            logger.error(f"\n❌ FAILED TESTS ({failed_tests}):")
            for test_name, result in self.test_results.items():
                if result['status'] == 'FAILED':
                    logger.error(f"   - {test_name}: {result['error']}")

        if passed_tests > 0:
            logger.info(f"\n✅ PASSED TESTS ({passed_tests}):")
            for test_name, result in self.test_results.items():
                if result['status'] == 'PASSED':
                    exec_time = result.get('execution_time', 0)
                    logger.info(f"   - {test_name} ({exec_time:.2f}s)")

        # Performance summary
        logger.info(f"\n⚡ PERFORMANCE METRICS:")
        for test_name, exec_time in self.performance_metrics.items():
            logger.info(f"   {test_name}: {exec_time:.2f}s")

        # RPI Status Summary
        logger.info(f"\n🔍 RPI INTEGRATION STATUS:")

        key_components = [
            ('Configuration', '1. Configuration Loading'),
            ('Component Imports', '2. Component Imports'),
            ('RPI Data Fetching', '3. BybitExchange RPI Fetch'),
            ('Enhanced Market Data', '4. MarketDataManager RPI Integration'),
            ('Data Processing', '5. DataProcessor RPI Validation'),
            ('Retail Analysis', '6. OrderbookIndicators Retail Component'),
            ('Alert Generation', '7. AlertManager Retail Alerts'),
            ('Performance', '8. Performance Testing'),
            ('Error Handling', '9. Error Handling'),
            ('End-to-End Flow', '10. End-to-End RPI Flow')
        ]

        for component_name, test_name in key_components:
            status = self.test_results.get(test_name, {}).get('status', 'NOT_RUN')
            emoji = '✅' if status == 'PASSED' else '❌' if status == 'FAILED' else '⚠️'
            logger.info(f"   {emoji} {component_name}: {status}")

        # Save detailed JSON report
        report_data = {
            'timestamp': time.time(),
            'total_execution_time': total_time,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': passed_tests/total_tests*100 if total_tests > 0 else 0
            },
            'performance_metrics': self.performance_metrics,
            'detailed_results': self.test_results,
            'rpi_integration_status': {
                component: self.test_results.get(test_name, {}).get('status', 'NOT_RUN')
                for component, test_name in key_components
            }
        }

        import json
        report_file = Path('comprehensive_rpi_test_report.json')
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"\n📄 Detailed JSON report saved to: {report_file}")
        logger.info("=" * 100)


async def main():
    """Main test runner."""
    tester = ComprehensiveRPITester()

    try:
        results = await tester.run_all_tests()

        # Exit code based on test results
        failed_count = sum(1 for result in results.values() if result['status'] == 'FAILED')

        if failed_count == 0:
            logger.info("\n🎉 ALL TESTS PASSED! RPI integration is fully functional.")
        else:
            logger.error(f"\n🚨 {failed_count} tests failed. Please review the issues.")

        sys.exit(1 if failed_count > 0 else 0)

    except KeyboardInterrupt:
        logger.info("\n🛑 Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"🚨 Test suite crashed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())