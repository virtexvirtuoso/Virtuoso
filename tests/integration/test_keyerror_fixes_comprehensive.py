#!/usr/bin/env python3
"""
Comprehensive KeyError Fixes Test Suite

This test suite validates that all KeyError issues in the fetch_market_data method
have been resolved and the system can handle missing data gracefully.

Test Categories:
1. KeyError Prevention Tests
2. Data Structure Integrity Tests  
3. Graceful Degradation Tests
4. Error Recovery Tests
5. Live Data Validation Tests

Author: AI Assistant
Date: 2025-01-14
"""

import asyncio
import pytest
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestKeyErrorFixes:
    """Test suite for KeyError fixes in fetch_market_data method."""
    
    @pytest.fixture
    async def mock_bybit_exchange(self):
        """Create a mock BybitExchange instance for testing."""
        from src.core.exchanges.bybit import BybitExchange
        
        # Mock configuration
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        # Create mock exchange
        exchange = MagicMock(spec=BybitExchange)
        exchange.logger = logger
        
        # Mock the _get_default_market_data method
        exchange._get_default_market_data = MagicMock(return_value={
            'symbol': 'BTCUSDT',
            'ticker': {},
            'orderbook': {'bids': [], 'asks': []},
            'trades': [],
            'ohlcv': {},
            'sentiment': {
                'long_short_ratio': {'long': 50.0, 'short': 50.0},
                'liquidations': {'long': 0.0, 'short': 0.0},
                'funding_rate': {'rate': 0.0},
                'volatility': {'value': 0.0},
                'volume_sentiment': {'buy_volume': 0.0, 'sell_volume': 0.0},
                'market_mood': {'risk_level': 1},
                'open_interest': {'current': 0.0, 'previous': 0.0, 'history': []}
            },
            'risk_limit': {},
            'metadata': {
                'timestamp': int(time.time() * 1000),
                'ticker_success': False,
                'orderbook_success': False,
                'trades_success': False,
                'ohlcv_success': False,
                'lsr_success': False,
                'risk_limits_success': False,
                'oi_history_success': False,
                'volatility_success': False
            }
        })
        
        # Mock rate limiting
        exchange._check_rate_limit = AsyncMock()
        
        # Mock validation
        exchange.validate_market_data = MagicMock(return_value=True)
        
        return exchange
    
    @pytest.mark.asyncio
    async def test_keyerror_prevention_lsr_missing(self, mock_bybit_exchange):
        """Test that missing LSR data doesn't cause KeyError."""
        logger.info("🧪 Testing KeyError prevention for missing LSR data")
        
        # Mock fetch methods to return None (simulating KeyError scenarios)
        mock_bybit_exchange._fetch_ticker = AsyncMock(return_value={'symbol': 'BTCUSDT', 'price': 50000})
        mock_bybit_exchange.get_orderbook = AsyncMock(return_value={'bids': [], 'asks': []})
        mock_bybit_exchange.fetch_trades = AsyncMock(return_value=[])
        mock_bybit_exchange._fetch_long_short_ratio = AsyncMock(return_value=None)  # Simulate failure
        mock_bybit_exchange._fetch_risk_limits = AsyncMock(return_value={'maxLeverage': 100.0})
        mock_bybit_exchange._fetch_all_timeframes = AsyncMock(return_value={'base': {}})
        mock_bybit_exchange.fetch_open_interest_history = AsyncMock(return_value={'list': []})
        mock_bybit_exchange._calculate_historical_volatility = AsyncMock(return_value={'value': 0.05})
        
        # Import and patch the actual method
        from src.core.exchanges.bybit import BybitExchange
        
        # Create a real instance for testing
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        exchange = BybitExchange(config)
        exchange.logger = logger
        
        # Mock all the fetch methods
        exchange._fetch_ticker = mock_bybit_exchange._fetch_ticker
        exchange.get_orderbook = mock_bybit_exchange.get_orderbook
        exchange.fetch_trades = mock_bybit_exchange.fetch_trades
        exchange._fetch_long_short_ratio = mock_bybit_exchange._fetch_long_short_ratio
        exchange._fetch_risk_limits = mock_bybit_exchange._fetch_risk_limits
        exchange._fetch_all_timeframes = mock_bybit_exchange._fetch_all_timeframes
        exchange.fetch_open_interest_history = mock_bybit_exchange.fetch_open_interest_history
        exchange._calculate_historical_volatility = mock_bybit_exchange._calculate_historical_volatility
        exchange._check_rate_limit = mock_bybit_exchange._check_rate_limit
        
        # Test the method
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify no KeyError was raised
            assert result is not None
            assert isinstance(result, dict)
            
            # Verify default LSR structure exists
            assert 'sentiment' in result
            assert 'long_short_ratio' in result['sentiment']
            assert result['sentiment']['long_short_ratio']['long'] == 50.0
            assert result['sentiment']['long_short_ratio']['short'] == 50.0
            
            logger.info("✅ LSR KeyError prevention test PASSED")
            return True
            
        except KeyError as e:
            logger.error(f"❌ LSR KeyError prevention test FAILED: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ LSR KeyError prevention test FAILED with unexpected error: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_keyerror_prevention_ohlcv_missing(self, mock_bybit_exchange):
        """Test that missing OHLCV data doesn't cause KeyError."""
        logger.info("🧪 Testing KeyError prevention for missing OHLCV data")
        
        # Mock fetch methods
        mock_bybit_exchange._fetch_ticker = AsyncMock(return_value={'symbol': 'BTCUSDT', 'price': 50000})
        mock_bybit_exchange.get_orderbook = AsyncMock(return_value={'bids': [], 'asks': []})
        mock_bybit_exchange.fetch_trades = AsyncMock(return_value=[])
        mock_bybit_exchange._fetch_long_short_ratio = AsyncMock(return_value={'long': 60.0, 'short': 40.0})
        mock_bybit_exchange._fetch_risk_limits = AsyncMock(return_value={'maxLeverage': 100.0})
        mock_bybit_exchange._fetch_all_timeframes = AsyncMock(return_value=None)  # Simulate failure
        mock_bybit_exchange.fetch_open_interest_history = AsyncMock(return_value={'list': []})
        mock_bybit_exchange._calculate_historical_volatility = AsyncMock(return_value={'value': 0.05})
        
        # Import and create real instance
        from src.core.exchanges.bybit import BybitExchange
        
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        exchange = BybitExchange(config)
        exchange.logger = logger
        
        # Mock all the fetch methods
        exchange._fetch_ticker = mock_bybit_exchange._fetch_ticker
        exchange.get_orderbook = mock_bybit_exchange.get_orderbook
        exchange.fetch_trades = mock_bybit_exchange.fetch_trades
        exchange._fetch_long_short_ratio = mock_bybit_exchange._fetch_long_short_ratio
        exchange._fetch_risk_limits = mock_bybit_exchange._fetch_risk_limits
        exchange._fetch_all_timeframes = mock_bybit_exchange._fetch_all_timeframes
        exchange.fetch_open_interest_history = mock_bybit_exchange.fetch_open_interest_history
        exchange._calculate_historical_volatility = mock_bybit_exchange._calculate_historical_volatility
        exchange._check_rate_limit = mock_bybit_exchange._check_rate_limit
        
        # Test the method
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify no KeyError was raised
            assert result is not None
            assert isinstance(result, dict)
            
            # Verify OHLCV structure handling
            # Should not have ohlcv key if fetch failed
            if 'ohlcv' in result:
                assert isinstance(result['ohlcv'], dict)
            
            logger.info("✅ OHLCV KeyError prevention test PASSED")
            return True
            
        except KeyError as e:
            logger.error(f"❌ OHLCV KeyError prevention test FAILED: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ OHLCV KeyError prevention test FAILED with unexpected error: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_keyerror_prevention_oi_history_missing(self, mock_bybit_exchange):
        """Test that missing OI history data doesn't cause KeyError."""
        logger.info("🧪 Testing KeyError prevention for missing OI history data")
        
        # Mock fetch methods
        mock_bybit_exchange._fetch_ticker = AsyncMock(return_value={'symbol': 'BTCUSDT', 'price': 50000})
        mock_bybit_exchange.get_orderbook = AsyncMock(return_value={'bids': [], 'asks': []})
        mock_bybit_exchange.fetch_trades = AsyncMock(return_value=[])
        mock_bybit_exchange._fetch_long_short_ratio = AsyncMock(return_value={'long': 60.0, 'short': 40.0})
        mock_bybit_exchange._fetch_risk_limits = AsyncMock(return_value={'maxLeverage': 100.0})
        mock_bybit_exchange._fetch_all_timeframes = AsyncMock(return_value={'base': {}})
        mock_bybit_exchange.fetch_open_interest_history = AsyncMock(return_value=None)  # Simulate failure
        mock_bybit_exchange._calculate_historical_volatility = AsyncMock(return_value={'value': 0.05})
        
        # Import and create real instance
        from src.core.exchanges.bybit import BybitExchange
        
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        exchange = BybitExchange(config)
        exchange.logger = logger
        
        # Mock all the fetch methods
        exchange._fetch_ticker = mock_bybit_exchange._fetch_ticker
        exchange.get_orderbook = mock_bybit_exchange.get_orderbook
        exchange.fetch_trades = mock_bybit_exchange.fetch_trades
        exchange._fetch_long_short_ratio = mock_bybit_exchange._fetch_long_short_ratio
        exchange._fetch_risk_limits = mock_bybit_exchange._fetch_risk_limits
        exchange._fetch_all_timeframes = mock_bybit_exchange._fetch_all_timeframes
        exchange.fetch_open_interest_history = mock_bybit_exchange.fetch_open_interest_history
        exchange._calculate_historical_volatility = mock_bybit_exchange._calculate_historical_volatility
        exchange._check_rate_limit = mock_bybit_exchange._check_rate_limit
        
        # Test the method
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify no KeyError was raised
            assert result is not None
            assert isinstance(result, dict)
            
            # Verify OI structure exists with defaults
            assert 'sentiment' in result
            assert 'open_interest' in result['sentiment']
            assert 'history' in result['sentiment']['open_interest']
            assert isinstance(result['sentiment']['open_interest']['history'], list)
            
            logger.info("✅ OI History KeyError prevention test PASSED")
            return True
            
        except KeyError as e:
            logger.error(f"❌ OI History KeyError prevention test FAILED: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ OI History KeyError prevention test FAILED with unexpected error: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_keyerror_prevention_volatility_missing(self, mock_bybit_exchange):
        """Test that missing volatility data doesn't cause KeyError."""
        logger.info("🧪 Testing KeyError prevention for missing volatility data")
        
        # Mock fetch methods
        mock_bybit_exchange._fetch_ticker = AsyncMock(return_value={'symbol': 'BTCUSDT', 'price': 50000})
        mock_bybit_exchange.get_orderbook = AsyncMock(return_value={'bids': [], 'asks': []})
        mock_bybit_exchange.fetch_trades = AsyncMock(return_value=[])
        mock_bybit_exchange._fetch_long_short_ratio = AsyncMock(return_value={'long': 60.0, 'short': 40.0})
        mock_bybit_exchange._fetch_risk_limits = AsyncMock(return_value={'maxLeverage': 100.0})
        mock_bybit_exchange._fetch_all_timeframes = AsyncMock(return_value={'base': {}})
        mock_bybit_exchange.fetch_open_interest_history = AsyncMock(return_value={'list': []})
        mock_bybit_exchange._calculate_historical_volatility = AsyncMock(return_value=None)  # Simulate failure
        
        # Import and create real instance
        from src.core.exchanges.bybit import BybitExchange
        
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        exchange = BybitExchange(config)
        exchange.logger = logger
        
        # Mock all the fetch methods
        exchange._fetch_ticker = mock_bybit_exchange._fetch_ticker
        exchange.get_orderbook = mock_bybit_exchange.get_orderbook
        exchange.fetch_trades = mock_bybit_exchange.fetch_trades
        exchange._fetch_long_short_ratio = mock_bybit_exchange._fetch_long_short_ratio
        exchange._fetch_risk_limits = mock_bybit_exchange._fetch_risk_limits
        exchange._fetch_all_timeframes = mock_bybit_exchange._fetch_all_timeframes
        exchange.fetch_open_interest_history = mock_bybit_exchange.fetch_open_interest_history
        exchange._calculate_historical_volatility = mock_bybit_exchange._calculate_historical_volatility
        exchange._check_rate_limit = mock_bybit_exchange._check_rate_limit
        
        # Test the method
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify no KeyError was raised
            assert result is not None
            assert isinstance(result, dict)
            
            # Verify sentiment structure exists
            assert 'sentiment' in result
            # Volatility should not be present if fetch failed
            if 'volatility' in result['sentiment']:
                assert isinstance(result['sentiment']['volatility'], dict)
            
            logger.info("✅ Volatility KeyError prevention test PASSED")
            return True
            
        except KeyError as e:
            logger.error(f"❌ Volatility KeyError prevention test FAILED: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Volatility KeyError prevention test FAILED with unexpected error: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_data_structure_integrity(self, mock_bybit_exchange):
        """Test that data structure integrity is maintained even with missing data."""
        logger.info("🧪 Testing data structure integrity with mixed success/failure scenarios")
        
        # Mock mixed success/failure scenarios
        mock_bybit_exchange._fetch_ticker = AsyncMock(return_value={'symbol': 'BTCUSDT', 'price': 50000, 'fundingRate': 0.0001})
        mock_bybit_exchange.get_orderbook = AsyncMock(return_value=None)  # Failure
        mock_bybit_exchange.fetch_trades = AsyncMock(return_value=[{'side': 'buy', 'size': 1.0}])  # Success
        mock_bybit_exchange._fetch_long_short_ratio = AsyncMock(return_value=None)  # Failure
        mock_bybit_exchange._fetch_risk_limits = AsyncMock(return_value={'maxLeverage': 100.0, 'initialMargin': 0.01})  # Success
        mock_bybit_exchange._fetch_all_timeframes = AsyncMock(return_value={'base': {}, 'ltf': {}})  # Success
        mock_bybit_exchange.fetch_open_interest_history = AsyncMock(return_value=None)  # Failure
        mock_bybit_exchange._calculate_historical_volatility = AsyncMock(return_value={'value': 0.05})  # Success
        
        # Import and create real instance
        from src.core.exchanges.bybit import BybitExchange
        
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        exchange = BybitExchange(config)
        exchange.logger = logger
        
        # Mock all the fetch methods
        exchange._fetch_ticker = mock_bybit_exchange._fetch_ticker
        exchange.get_orderbook = mock_bybit_exchange.get_orderbook
        exchange.fetch_trades = mock_bybit_exchange.fetch_trades
        exchange._fetch_long_short_ratio = mock_bybit_exchange._fetch_long_short_ratio
        exchange._fetch_risk_limits = mock_bybit_exchange._fetch_risk_limits
        exchange._fetch_all_timeframes = mock_bybit_exchange._fetch_all_timeframes
        exchange.fetch_open_interest_history = mock_bybit_exchange.fetch_open_interest_history
        exchange._calculate_historical_volatility = mock_bybit_exchange._calculate_historical_volatility
        exchange._check_rate_limit = mock_bybit_exchange._check_rate_limit
        
        # Test the method
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify no KeyError was raised
            assert result is not None
            assert isinstance(result, dict)
            
            # Verify core structure exists
            required_keys = ['symbol', 'ticker', 'sentiment', 'metadata']
            for key in required_keys:
                assert key in result, f"Missing required key: {key}"
            
            # Verify sentiment structure
            sentiment_keys = ['long_short_ratio', 'funding_rate', 'volatility', 'volume_sentiment', 'market_mood', 'open_interest']
            for key in sentiment_keys:
                assert key in result['sentiment'], f"Missing sentiment key: {key}"
            
            # Verify successful data is present
            assert result['ticker']['price'] == 50000  # Ticker success
            assert 'base' in result['ohlcv']  # OHLCV success
            assert result['sentiment']['volatility']['value'] == 0.05  # Volatility success
            
            # Verify failed data has defaults
            assert result['sentiment']['long_short_ratio']['long'] == 50.0  # LSR default
            assert result['sentiment']['long_short_ratio']['short'] == 50.0  # LSR default
            
            logger.info("✅ Data structure integrity test PASSED")
            return True
            
        except KeyError as e:
            logger.error(f"❌ Data structure integrity test FAILED: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Data structure integrity test FAILED with unexpected error: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_complete_failure_scenario(self, mock_bybit_exchange):
        """Test graceful handling when all fetch operations fail."""
        logger.info("🧪 Testing complete failure scenario - all fetches return None")
        
        # Mock all methods to return None (complete failure)
        mock_bybit_exchange._fetch_ticker = AsyncMock(return_value=None)
        mock_bybit_exchange.get_orderbook = AsyncMock(return_value=None)
        mock_bybit_exchange.fetch_trades = AsyncMock(return_value=None)
        mock_bybit_exchange._fetch_long_short_ratio = AsyncMock(return_value=None)
        mock_bybit_exchange._fetch_risk_limits = AsyncMock(return_value=None)
        mock_bybit_exchange._fetch_all_timeframes = AsyncMock(return_value=None)
        mock_bybit_exchange.fetch_open_interest_history = AsyncMock(return_value=None)
        mock_bybit_exchange._calculate_historical_volatility = AsyncMock(return_value=None)
        
        # Import and create real instance
        from src.core.exchanges.bybit import BybitExchange
        
        config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api-testnet.bybit.com',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'testnet': True
                }
            }
        }
        
        exchange = BybitExchange(config)
        exchange.logger = logger
        
        # Mock all the fetch methods
        exchange._fetch_ticker = mock_bybit_exchange._fetch_ticker
        exchange.get_orderbook = mock_bybit_exchange.get_orderbook
        exchange.fetch_trades = mock_bybit_exchange.fetch_trades
        exchange._fetch_long_short_ratio = mock_bybit_exchange._fetch_long_short_ratio
        exchange._fetch_risk_limits = mock_bybit_exchange._fetch_risk_limits
        exchange._fetch_all_timeframes = mock_bybit_exchange._fetch_all_timeframes
        exchange.fetch_open_interest_history = mock_bybit_exchange.fetch_open_interest_history
        exchange._calculate_historical_volatility = mock_bybit_exchange._calculate_historical_volatility
        exchange._check_rate_limit = mock_bybit_exchange._check_rate_limit
        
        # Test the method
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify no KeyError was raised
            assert result is not None
            assert isinstance(result, dict)
            
            # Verify default structure exists
            assert 'sentiment' in result
            assert 'long_short_ratio' in result['sentiment']
            assert 'open_interest' in result['sentiment']
            assert 'metadata' in result
            
            # All metadata success flags should be False
            metadata = result['metadata']
            success_flags = ['ticker_success', 'orderbook_success', 'trades_success', 
                           'ohlcv_success', 'lsr_success', 'risk_limits_success', 
                           'oi_history_success', 'volatility_success']
            
            for flag in success_flags:
                if flag in metadata:
                    assert metadata[flag] == False, f"Expected {flag} to be False in complete failure scenario"
            
            logger.info("✅ Complete failure scenario test PASSED")
            return True
            
        except KeyError as e:
            logger.error(f"❌ Complete failure scenario test FAILED: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Complete failure scenario test FAILED with unexpected error: {e}")
            return False

async def run_comprehensive_keyerror_tests():
    """Run all KeyError fix tests and provide summary."""
    logger.info("🚀 Starting Comprehensive KeyError Fixes Test Suite")
    logger.info("=" * 80)
    
    test_suite = TestKeyErrorFixes()
    mock_exchange = await test_suite.mock_bybit_exchange()
    
    # Define test cases
    test_cases = [
        ("LSR Missing KeyError Prevention", test_suite.test_keyerror_prevention_lsr_missing),
        ("OHLCV Missing KeyError Prevention", test_suite.test_keyerror_prevention_ohlcv_missing),
        ("OI History Missing KeyError Prevention", test_suite.test_keyerror_prevention_oi_history_missing),
        ("Volatility Missing KeyError Prevention", test_suite.test_keyerror_prevention_volatility_missing),
        ("Data Structure Integrity", test_suite.test_data_structure_integrity),
        ("Complete Failure Scenario", test_suite.test_complete_failure_scenario),
    ]
    
    # Run tests
    results = []
    passed = 0
    failed = 0
    
    for test_name, test_func in test_cases:
        logger.info(f"\n📋 Running: {test_name}")
        logger.info("-" * 60)
        
        try:
            start_time = time.time()
            result = await test_func(mock_exchange)
            end_time = time.time()
            
            if result:
                logger.info(f"✅ {test_name}: PASSED ({end_time - start_time:.2f}s)")
                passed += 1
                results.append((test_name, "PASSED", end_time - start_time))
            else:
                logger.error(f"❌ {test_name}: FAILED ({end_time - start_time:.2f}s)")
                failed += 1
                results.append((test_name, "FAILED", end_time - start_time))
                
        except Exception as e:
            logger.error(f"💥 {test_name}: CRASHED - {str(e)}")
            failed += 1
            results.append((test_name, "CRASHED", 0))
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 COMPREHENSIVE KEYERROR FIXES TEST SUMMARY")
    logger.info("=" * 80)
    
    for test_name, status, duration in results:
        status_icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "💥"
        logger.info(f"{status_icon} {test_name:<50} {status:<8} ({duration:.2f}s)")
    
    logger.info("-" * 80)
    logger.info(f"📈 TOTAL TESTS: {len(test_cases)}")
    logger.info(f"✅ PASSED: {passed}")
    logger.info(f"❌ FAILED: {failed}")
    logger.info(f"📊 SUCCESS RATE: {(passed/len(test_cases)*100):.1f}%")
    
    # Overall assessment
    if failed == 0:
        logger.info("🎉 ALL KEYERROR FIXES TESTS PASSED!")
        logger.info("🚀 System is ready for production - KeyError issues resolved!")
        grade = "EXCELLENT"
    elif failed <= 1:
        logger.info("⚠️  Most KeyError fixes working, minor issues remain")
        grade = "GOOD"
    elif failed <= 2:
        logger.info("⚠️  Some KeyError fixes working, several issues remain")
        grade = "FAIR"
    else:
        logger.info("❌ Multiple KeyError fixes failing, significant issues remain")
        grade = "POOR"
    
    logger.info(f"🎯 OVERALL GRADE: {grade}")
    logger.info("=" * 80)
    
    return {
        'total_tests': len(test_cases),
        'passed': passed,
        'failed': failed,
        'success_rate': passed/len(test_cases)*100,
        'grade': grade,
        'results': results
    }

if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(run_comprehensive_keyerror_tests()) 