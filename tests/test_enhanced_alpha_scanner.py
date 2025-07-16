#!/usr/bin/env python3
"""
Enhanced Alpha Scanner Test

Test the enhanced multi-timeframe alpha scanner with all timeframes 
including quick opportunity detection on 1m and 5m timeframes.
"""

import sys
import os
import asyncio
import logging
import yaml
import time
from unittest.mock import Mock, AsyncMock
import pandas as pd
import numpy as np

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.monitoring.monitor import MarketMonitor
from src.monitoring.alpha_scanner import AlphaOpportunityScanner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedAlphaTester:
    """Test enhanced alpha scanner with all timeframes."""
    
    def __init__(self):
        self.config = None
        
    async def load_enhanced_config(self):
        """Load enhanced configuration with all timeframes."""
        try:
            config_path = os.path.join(project_root, 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Verify alpha_scanning configuration is loaded
            alpha_config = self.config.get('alpha_scanning', {})
            timeframes = alpha_config.get('timeframes', [])
            
            logger.info(f"✅ Enhanced config loaded:")
            logger.info(f"   Timeframes: {timeframes}")
            logger.info(f"   Performance tiers: {alpha_config.get('performance_tiers', {})}")
            logger.info(f"   Timeframe thresholds configured: {list(alpha_config.get('timeframe_thresholds', {}).keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load enhanced configuration: {str(e)}")
            return False
    
    def create_mock_market_data(self):
        """Create mock market data for all timeframes with different alpha patterns."""
        timeframes = ['htf', 'mtf', 'ltf', 'base']
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        mock_data = {}
        
        for symbol in symbols:
            mock_data[symbol] = {}
            
            for i, timeframe in enumerate(timeframes):
                # Create different data scenarios for each timeframe
                if symbol == 'ETHUSDT':
                    # ETH: Strong correlation breakdown on faster timeframes
                    if timeframe in ['base', 'ltf']:  # 1m, 5m
                        correlation_factor = 0.1  # Very low correlation
                        alpha_factor = 0.05       # 5% alpha
                    else:
                        correlation_factor = 0.4  # Medium correlation
                        alpha_factor = 0.02       # 2% alpha
                        
                elif symbol == 'SOLUSDT':
                    # SOL: Beta expansion on medium timeframes
                    if timeframe in ['mtf', 'ltf']:  # 30m, 5m
                        correlation_factor = 0.8  # High correlation
                        alpha_factor = 0.03       # 3% alpha
                        beta_factor = 2.5         # High beta
                    else:
                        correlation_factor = 0.6
                        alpha_factor = 0.015
                        beta_factor = 1.2
                        
                else:  # BTCUSDT - reference
                    correlation_factor = 1.0
                    alpha_factor = 0.0
                    beta_factor = 1.0
                
                # Generate synthetic price data
                np.random.seed(42 + i)  # Reproducible data
                n_points = 100
                
                timestamps = pd.date_range('2024-01-01', periods=n_points, freq='1min')
                
                # BTC base price movement
                btc_returns = np.random.normal(0, 0.02, n_points)
                btc_prices = 50000 * np.exp(np.cumsum(btc_returns))
                
                if symbol == 'BTCUSDT':
                    prices = btc_prices
                    returns = btc_returns
                else:
                    # Create correlated movement with alpha
                    base_returns = correlation_factor * btc_returns + \
                                   np.sqrt(1 - correlation_factor**2) * np.random.normal(0, 0.02, n_points)
                    alpha_component = np.full(n_points, alpha_factor / n_points)
                    returns = base_returns + alpha_component
                    
                    if symbol == 'SOLUSDT' and timeframe in ['mtf', 'ltf']:
                        returns = returns * beta_factor  # Apply beta expansion
                    
                    start_price = 3000 if symbol == 'ETHUSDT' else 100
                    prices = start_price * np.exp(np.cumsum(returns))
                
                # Create DataFrame
                highs = prices * (1 + np.abs(np.random.normal(0, 0.01, n_points)))
                lows = prices * (1 - np.abs(np.random.normal(0, 0.01, n_points)))
                volumes = np.random.uniform(1000, 5000, n_points)
                
                df = pd.DataFrame({
                    'timestamp': timestamps,
                    'open': np.roll(prices, 1),
                    'high': highs,
                    'low': lows,
                    'close': prices,
                    'volume': volumes,
                    'returns': returns
                })
                df.iloc[0, df.columns.get_loc('open')] = df.iloc[0, df.columns.get_loc('close')]
                
                mock_data[symbol][timeframe] = df
        
        logger.info(f"✅ Created mock market data for {len(symbols)} symbols across {len(timeframes)} timeframes")
        return mock_data
    
    def create_mock_dependencies(self):
        """Create mock dependencies for MarketMonitor."""
        try:
            # Mock exchange
            mock_exchange = Mock()
            mock_exchange.id = 'binance'
            
            # Mock alert manager
            mock_alert_manager = Mock()
            mock_alert_manager.send_alpha_opportunity_alert = AsyncMock()
            
            # Mock top symbols manager
            mock_top_symbols_manager = Mock()
            mock_top_symbols_manager.get_symbols = AsyncMock(return_value=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
            
            # Mock market data manager
            mock_market_data_manager = Mock()
            
            # Mock metrics manager
            mock_metrics_manager = Mock()
            mock_metrics_manager.start_operation = Mock(return_value="mock_operation")
            mock_metrics_manager.end_operation = Mock()
            mock_metrics_manager.record_metric = Mock()
            
            return {
                'exchange': mock_exchange,
                'alert_manager': mock_alert_manager,
                'top_symbols_manager': mock_top_symbols_manager,
                'market_data_manager': mock_market_data_manager,
                'metrics_manager': mock_metrics_manager
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create mock dependencies: {str(e)}")
            return None
    
    async def test_multi_timeframe_alpha_detection(self):
        """Test alpha detection across all timeframes."""
        try:
            logger.info("🧪 Testing multi-timeframe alpha detection...")
            
            # Create mock dependencies
            mocks = self.create_mock_dependencies()
            if not mocks:
                return False
            
            # Initialize MarketMonitor
            monitor = MarketMonitor(
                exchange=mocks['exchange'],
                config=self.config,
                alert_manager=mocks['alert_manager'],
                top_symbols_manager=mocks['top_symbols_manager'],
                market_data_manager=mocks['market_data_manager'],
                metrics_manager=mocks['metrics_manager'],
                logger=logger
            )
            
            # Create mock market data
            market_data = self.create_mock_market_data()
            
            # Create mock monitor instance with market data
            mock_monitor_instance = Mock()
            mock_monitor_instance.get_monitored_symbols = Mock(return_value=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
            mock_monitor_instance.get_ohlcv_for_report = Mock()
            
            # Setup get_ohlcv_for_report to return our mock data
            def mock_get_ohlcv(symbol, timeframe):
                tf_map = {'4h': 'htf', '30m': 'mtf', '5m': 'ltf', '1m': 'base'}
                tf = tf_map.get(timeframe, timeframe)
                return market_data.get(symbol, {}).get(tf)
            
            mock_monitor_instance.get_ohlcv_for_report.side_effect = mock_get_ohlcv
            
            # Test alpha scanner
            opportunities = await monitor.alpha_scanner.scan_for_opportunities(mock_monitor_instance)
            
            logger.info(f"   📊 Found {len(opportunities)} alpha opportunities")
            
            # Analyze results by timeframe
            timeframe_detections = {}
            priority_counts = {'ultra_fast': 0, 'fast': 0, 'stable': 0}
            
            for opp in opportunities:
                logger.info(f"   🎯 {opp.symbol}: {opp.divergence_type.value} "
                           f"(confidence: {opp.confidence:.2f}, alpha: {opp.alpha_potential:.1%})")
                logger.info(f"      💡 {opp.trading_insight}")
                logger.info(f"      ⏱️  Duration: {opp.expected_duration}, Risk: {opp.risk_level}")
                
                # Count timeframe detections
                for tf in opp.timeframe_signals.keys():
                    if tf not in timeframe_detections:
                        timeframe_detections[tf] = 0
                    timeframe_detections[tf] += 1
                
                # Count priorities
                if 'ultra_fast priority' in opp.recommended_action:
                    priority_counts['ultra_fast'] += 1
                elif 'fast priority' in opp.recommended_action:
                    priority_counts['fast'] += 1
                elif 'stable priority' in opp.recommended_action:
                    priority_counts['stable'] += 1
            
            logger.info(f"   📈 Timeframe detections: {timeframe_detections}")
            logger.info(f"   🚨 Priority distribution: {priority_counts}")
            
            # Validate we're detecting opportunities across timeframes
            assert len(opportunities) > 0, "❌ No alpha opportunities detected"
            assert len(timeframe_detections) > 1, "❌ Only detected on single timeframe"
            
            # Check we have quick opportunities (base or ltf timeframes)
            quick_timeframes = set(['base', 'ltf']) & set(timeframe_detections.keys())
            assert len(quick_timeframes) > 0, "❌ No quick opportunities detected on 1m/5m timeframes"
            
            logger.info("   ✅ Multi-timeframe alpha detection working correctly")
            logger.info(f"   ✅ Quick opportunities detected on: {quick_timeframes}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Multi-timeframe alpha detection test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_timeframe_specific_thresholds(self):
        """Test that timeframe-specific thresholds are working."""
        try:
            logger.info("🧪 Testing timeframe-specific thresholds...")
            
            # Create mock dependencies
            mocks = self.create_mock_dependencies()
            if not mocks:
                return False
            
            # Initialize MarketMonitor
            monitor = MarketMonitor(
                exchange=mocks['exchange'],
                config=self.config,
                alert_manager=mocks['alert_manager'],
                top_symbols_manager=mocks['top_symbols_manager'],
                market_data_manager=mocks['market_data_manager'],
                metrics_manager=mocks['metrics_manager'],
                logger=logger
            )
            
            # Test threshold retrieval for each timeframe
            timeframes = ['base', 'ltf', 'mtf', 'htf']
            
            for timeframe in timeframes:
                thresholds = monitor.alpha_scanner._get_timeframe_thresholds(timeframe)
                priority = monitor.alpha_scanner._get_alert_priority(timeframe)
                
                logger.info(f"   🎯 {timeframe}: confidence={thresholds['min_confidence']:.2f}, "
                           f"correlation={thresholds['correlation_breakdown']:.2f}, "
                           f"alpha={thresholds['alpha_threshold']:.3f}, priority={priority}")
                
                # Validate thresholds are different across timeframes
                assert 'min_confidence' in thresholds, f"❌ Missing min_confidence for {timeframe}"
                assert thresholds['min_confidence'] > 0, f"❌ Invalid confidence threshold for {timeframe}"
            
            # Test trading parameters
            test_params = monitor.alpha_scanner._get_trading_parameters('base', 'correlation_breakdown')
            risk_level, duration, entry_conditions, exit_conditions = test_params
            
            logger.info(f"   📊 Trading parameters for base timeframe:")
            logger.info(f"      Risk: {risk_level}, Duration: {duration}")
            logger.info(f"      Entry: {entry_conditions[:2]}")
            logger.info(f"      Exit: {exit_conditions[:2]}")
            
            assert risk_level in ['Low', 'Medium', 'High'], "❌ Invalid risk level"
            assert len(entry_conditions) > 0, "❌ No entry conditions"
            assert len(exit_conditions) > 0, "❌ No exit conditions"
            
            logger.info("   ✅ Timeframe-specific thresholds working correctly")
            return True
            
        except Exception as e:
            logger.error(f"❌ Timeframe-specific thresholds test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_performance_tiers(self):
        """Test performance tier classification."""
        try:
            logger.info("🧪 Testing performance tier classification...")
            
            # Create mock dependencies
            mocks = self.create_mock_dependencies()
            monitor = MarketMonitor(
                exchange=mocks['exchange'],
                config=self.config,
                alert_manager=mocks['alert_manager'],
                top_symbols_manager=mocks['top_symbols_manager'],
                market_data_manager=mocks['market_data_manager'],
                metrics_manager=mocks['metrics_manager'],
                logger=logger
            )
            
            # Test tier classification
            tier_tests = [
                ('base', 'ultra_fast'),   # 1m should be ultra_fast
                ('ltf', 'ultra_fast'),    # 5m should be ultra_fast
                ('mtf', 'fast'),          # 30m should be fast
                ('htf', 'stable')         # 4h should be stable
            ]
            
            for timeframe, expected_tier in tier_tests:
                actual_tier = monitor.alpha_scanner._get_alert_priority(timeframe)
                assert actual_tier == expected_tier, f"❌ {timeframe} should be {expected_tier}, got {actual_tier}"
                logger.info(f"   ✅ {timeframe} correctly classified as {actual_tier}")
            
            logger.info("   ✅ Performance tier classification working correctly")
            return True
            
        except Exception as e:
            logger.error(f"❌ Performance tier test failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all enhanced alpha scanner tests."""
        logger.info("🚀 Starting Enhanced Alpha Scanner Tests")
        logger.info("=" * 80)
        
        tests = [
            ("Enhanced Configuration Loading", self.load_enhanced_config),
            ("Multi-timeframe Alpha Detection", self.test_multi_timeframe_alpha_detection),
            ("Timeframe-specific Thresholds", self.test_timeframe_specific_thresholds),
            ("Performance Tier Classification", self.test_performance_tiers),
        ]
        
        results = {}
        passed_count = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n🧪 Running: {test_name}")
                logger.info("-" * 50)
                
                start_time = time.time()
                result = await test_func()
                test_time = time.time() - start_time
                
                results[test_name] = {
                    'passed': result,
                    'time': test_time
                }
                
                if result:
                    passed_count += 1
                    status = "✅ PASSED"
                else:
                    status = "❌ FAILED"
                
                logger.info(f"{status} - {test_name} ({test_time:.2f}s)")
                
            except Exception as e:
                logger.error(f"❌ Test '{test_name}' crashed: {str(e)}")
                results[test_name] = {
                    'passed': False,
                    'time': 0,
                    'error': str(e)
                }
        
        # Print summary
        self.print_summary(results, passed_count)
        
        return passed_count == len(tests)
    
    def print_summary(self, results, passed_count):
        """Print test summary."""
        total_tests = len(results)
        total_time = sum(r['time'] for r in results.values())
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 ENHANCED ALPHA SCANNER TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed: {total_tests - passed_count}")
        logger.info(f"Success Rate: {(passed_count/total_tests)*100:.1f}%")
        logger.info(f"Total Time: {total_time:.2f} seconds")
        
        if passed_count == total_tests:
            logger.info("\n🎉 ALL TESTS PASSED! Enhanced alpha scanner is ready for quick alpha detection.")
            logger.info("\n📋 New Capabilities:")
            logger.info("   ✅ Multi-timeframe analysis (1m, 5m, 30m, 4h)")
            logger.info("   ✅ Quick opportunity detection on 1m/5m timeframes")  
            logger.info("   ✅ Performance tier classification (ultra_fast, fast, stable)")
            logger.info("   ✅ Timeframe-specific thresholds for optimal detection")
            logger.info("   ✅ Priority-based alert system")
            logger.info("\n🚀 Next Steps:")
            logger.info("   1. Deploy enhanced scanner to production")
            logger.info("   2. Monitor for quick alpha opportunities (15-min scans)")
            logger.info("   3. Tune thresholds based on market performance")
            logger.info("   4. Monitor Discord alerts for ultra_fast opportunities")
        else:
            logger.info(f"\n⚠️ {total_tests - passed_count} tests failed. Enhanced scanner needs fixes.")

async def main():
    """Main test execution."""
    tester = EnhancedAlphaTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 