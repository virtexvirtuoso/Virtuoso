#!/usr/bin/env python3
"""
Test the newly added Market Reporter methods
Tests fetch_market_data, create_analysis_report, and format_report_data
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

class NewMethodsTester:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def test_fetch_market_data(self):
        """Test the new fetch_market_data method"""
        print("🔍 Testing fetch_market_data method...")
        
        try:
            from monitoring.market_reporter import MarketReporter
            
            # Create a mock exchange for testing
            class MockExchange:
                def __init__(self):
                    self.exchange_id = 'test_exchange'
                    
                async def fetch_ohlcv(self, symbol, timeframe='1d', limit=100):
                    # Return mock OHLCV data
                    import time
                    now = int(time.time() * 1000)
                    return [
                        [now - i * 86400000, 50000 + i * 100, 50500 + i * 100, 49500 + i * 100, 50200 + i * 100, 1000]
                        for i in range(limit)
                    ]
                    
                async def fetch_ticker(self, symbol):
                    return {
                        'symbol': symbol,
                        'last': 50000,
                        'bid': 49995,
                        'ask': 50005,
                        'baseVolume': 1000,
                        'quoteVolume': 50000000,
                        'info': {'price24hPcnt': '2.5%'}
                    }
                    
                async def fetch_order_book(self, symbol):
                    return {
                        'bids': [[49995, 10], [49990, 20]],
                        'asks': [[50005, 15], [50010, 25]]
                    }
            
            # Initialize market reporter with mock exchange
            mock_exchange = MockExchange()
            reporter = MarketReporter(exchange=mock_exchange, logger=self.logger)
            
            # Test fetch_market_data
            result = await reporter.fetch_market_data('BTCUSDT', '1d', 10)
            
            if result:
                print("✅ fetch_market_data returned data successfully")
                print(f"   - Symbol: {result.get('symbol')}")
                print(f"   - Timeframe: {result.get('timeframe')}")
                print(f"   - Current price: {result.get('price', {}).get('current')}")
                print(f"   - 24h change: {result.get('price', {}).get('change_24h')}%")
                print(f"   - Volatility: {result.get('statistics', {}).get('volatility')}%")
                print(f"   - Data points: {result.get('statistics', {}).get('data_points')}")
                return True
            else:
                print("❌ fetch_market_data returned None")
                return False
                
        except Exception as e:
            print(f"❌ Error testing fetch_market_data: {e}")
            return False
    
    async def test_create_analysis_report(self):
        """Test the new create_analysis_report method"""
        print("\n🔍 Testing create_analysis_report method...")
        
        try:
            
            # Create sample market data
            sample_market_data = {
                'symbol': 'BTCUSDT',
                'price': {
                    'current': 50000,
                    'change_24h': 2.5,
                    'high_24h': 51000,
                    'low_24h': 49000
                },
                'volume': {
                    'total_24h': 50000000,
                    'average': 2000000
                },
                'statistics': {
                    'volatility': 3.5,
                    'spread_pct': 0.02,
                    'data_points': 10
                },
                'market_overview': {
                    'regime': '📈 Bullish',
                    'total_volume': 1000000000
                },
                'smart_money_index': {
                    'index': 65.0,
                    'signal': 'BULLISH'
                }
            }
            
            # Initialize market reporter
            reporter = MarketReporter(logger=self.logger)
            
            # Test different analysis types
            analysis_types = ['comprehensive', 'technical', 'sentiment', 'fundamental']
            
            for analysis_type in analysis_types:
                print(f"   Testing {analysis_type} analysis...")
                result = await reporter.create_analysis_report(sample_market_data, analysis_type)
                
                if result:
                    print(f"   ✅ {analysis_type} analysis completed")
                    print(f"      - Analysis type: {result.get('analysis_type')}")
                    print(f"      - Data quality score: {result.get('data_quality_score')}")
                    print(f"      - Insights count: {len(result.get('insights', []))}")
                    print(f"      - Recommendations count: {len(result.get('recommendations', []))}")
                    
                    # Check for specific analysis components
                    if analysis_type == 'comprehensive':
                        components = ['technical_analysis', 'market_structure', 'sentiment_analysis', 'risk_analysis']
                        found_components = [comp for comp in components if comp in result]
                        print(f"      - Components found: {found_components}")
                    
                else:
                    print(f"   ❌ {analysis_type} analysis failed")
                    return False
            
            print("✅ create_analysis_report working for all analysis types")
            return True
            
        except Exception as e:
            print(f"❌ Error testing create_analysis_report: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_format_report_data(self):
        """Test the new format_report_data method"""
        print("\n🔍 Testing format_report_data method...")
        
        try:
            
            # Create sample raw data
            sample_raw_data = {
                'timestamp': int(datetime.now().timestamp() * 1000),
                'market_overview': {
                    'regime': '📈 Bullish',
                    'total_volume': 1000000000,
                    'trend_strength': 75.5
                },
                'smart_money_index': {
                    'index': 65.0,
                    'signal': 'BULLISH'
                },
                'whale_activity': {
                    'transactions': [
                        {'symbol': 'BTCUSDT', 'side': 'buy', 'usd_value': 1500000}
                    ]
                },
                'performance_metrics': {
                    'data_quality': {'avg_score': 95},
                    'processing_time': {'avg': 2.5, 'max': 5.0}
                }
            }
            
            # Initialize market reporter
            reporter = MarketReporter(logger=self.logger)
            
            # Test different format types and targets
            format_configs = [
                ('standard', 'general'),
                ('compact', 'general'),
                ('executive', 'executive'),
                ('technical', 'technical'),
                ('detailed', 'technical'),
                ('api', 'api')
            ]
            
            for format_type, target in format_configs:
                print(f"   Testing {format_type} format for {target} audience...")
                result = await reporter.format_report_data(sample_raw_data, format_type, target)
                
                if result:
                    print(f"   ✅ {format_type}/{target} formatting completed")
                    
                    # Check format info
                    if 'format_info' in result:
                        format_info = result['format_info']
                        print(f"      - Format type: {format_info.get('format_type')}")
                        print(f"      - Target audience: {format_info.get('target_audience')}")
                        print(f"      - Processing time: {format_info.get('processing_time_seconds', 0):.3f}s")
                    
                    # Check for API-specific structure
                    if format_type == 'api':
                        if 'status' in result and 'data' in result:
                            print(f"      - API structure: ✅ (status: {result['status']})")
                        else:
                            print(f"      - API structure: ❌ Missing status/data fields")
                    
                    # Check content structure
                    if 'content' in result:
                        content_keys = list(result['content'].keys())
                        print(f"      - Content sections: {len(content_keys)}")
                    elif format_type != 'api':  # API format doesn't use 'content' wrapper
                        print(f"      - Warning: No content section found")
                    
                else:
                    print(f"   ❌ {format_type}/{target} formatting failed")
                    return False
            
            print("✅ format_report_data working for all format types and targets")
            return True
            
        except Exception as e:
            print(f"❌ Error testing format_report_data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self):
        """Run all tests for the new methods"""
        print("🧪 Testing New Market Reporter Methods")
        print("=" * 60)
        
        tests = [
            ("fetch_market_data", self.test_fetch_market_data),
            ("create_analysis_report", self.test_create_analysis_report),
            ("format_report_data", self.test_format_report_data)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'=' * 20} {test_name.upper()} TEST {'=' * 20}")
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} test crashed: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 New Methods Test Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All new methods are working correctly!")
        else:
            print(f"\n⚠️ {total - passed} test(s) failed - check output above")
        
        return passed == total

async def main():
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise for testing
    
    tester = NewMethodsTester()
    success = await tester.run_all_tests()
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)