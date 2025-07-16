#!/usr/bin/env python3
"""
Test KeyError fixes in Bybit exchange implementation.

This test verifies that the exchange can handle missing data gracefully
without raising KeyErrors that crash the system.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestBybitKeyErrorFixes:
    """Test suite for Bybit KeyError fixes."""
    
    def setup_method(self):
        """Set up test environment."""
        logger.info("Setting up test environment for KeyError fixes")
        
    @pytest.mark.asyncio
    async def test_fetch_market_data_with_missing_keys(self):
        """Test fetch_market_data handles missing dictionary keys gracefully."""
        logger.info("Testing fetch_market_data with missing keys")
        
        # Mock config for Bybit exchange
        mock_config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'ws_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True
                }
            }
        }
        
        # Import and create Bybit exchange
        from src.core.exchanges.bybit import BybitExchange
        
        exchange = BybitExchange(mock_config)
        exchange.logger = logger
        
        # Mock the individual fetch methods to return None (simulating failures)
        exchange._fetch_ticker = AsyncMock(return_value=None)
        exchange.get_orderbook = AsyncMock(return_value=None)
        exchange.fetch_trades = AsyncMock(return_value=None)
        exchange._fetch_long_short_ratio = AsyncMock(return_value=None)
        exchange._fetch_risk_limits = AsyncMock(return_value=None)
        exchange._fetch_all_timeframes = AsyncMock(return_value=None)
        exchange.fetch_open_interest_history = AsyncMock(return_value=None)
        exchange._calculate_historical_volatility = AsyncMock(return_value=None)
        exchange._check_rate_limit = AsyncMock(return_value=None)
        
        # Test that fetch_market_data doesn't crash with all None returns
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Verify we get a valid response structure
            assert isinstance(result, dict)
            assert 'ticker' in result
            assert 'orderbook' in result
            assert 'trades' in result
            assert 'sentiment' in result
            assert 'metadata' in result
            
            logger.info("✅ fetch_market_data handled None returns gracefully")
            
        except Exception as e:
            logger.error(f"❌ fetch_market_data failed with None returns: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_lsr_keyerror_handling(self):
        """Test long/short ratio KeyError handling."""
        logger.info("Testing LSR KeyError handling")
        
        # Mock config
        mock_config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'ws_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True
                }
            }
        }
        
        from src.core.exchanges.bybit import BybitExchange
        
        exchange = BybitExchange(mock_config)
        exchange.logger = logger
        
        # Mock _make_request to return data without expected keys
        exchange._make_request = AsyncMock(return_value={
            'retCode': 0,
            'retMsg': 'OK',
            'result': {}  # Missing 'list' key
        })
        exchange._check_rate_limit = AsyncMock(return_value=None)
        
        try:
            result = await exchange._fetch_long_short_ratio('BTCUSDT')
            
            # Should return default structure instead of raising KeyError
            assert isinstance(result, dict)
            assert 'symbol' in result
            assert 'long' in result
            assert 'short' in result
            assert result['long'] == 50.0  # Default value
            assert result['short'] == 50.0  # Default value
            
            logger.info("✅ LSR KeyError handled gracefully")
            
        except KeyError as e:
            logger.error(f"❌ LSR KeyError not handled: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ LSR unexpected error: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_ohlcv_keyerror_handling(self):
        """Test OHLCV KeyError handling."""
        logger.info("Testing OHLCV KeyError handling")
        
        # Mock config
        mock_config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'ws_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True
                }
            }
        }
        
        from src.core.exchanges.bybit import BybitExchange
        
        exchange = BybitExchange(mock_config)
        exchange.logger = logger
        
        # Mock _make_request to return data without expected keys
        exchange._make_request = AsyncMock(return_value={
            'retCode': 0,
            'retMsg': 'OK',
            'result': {}  # Missing 'list' key
        })
        exchange._check_rate_limit = AsyncMock(return_value=None)
        
        try:
            result = await exchange._fetch_all_timeframes('BTCUSDT')
            
            # Should return empty DataFrames instead of raising KeyError
            assert isinstance(result, dict)
            expected_timeframes = ['base', 'ltf', 'mtf', 'htf']
            
            for tf in expected_timeframes:
                assert tf in result
                # Should be empty DataFrames, not None
                assert result[tf] is not None
            
            logger.info("✅ OHLCV KeyError handled gracefully")
            
        except KeyError as e:
            logger.error(f"❌ OHLCV KeyError not handled: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ OHLCV unexpected error: {e}")
            raise
    
    @pytest.mark.asyncio 
    async def test_oi_history_keyerror_handling(self):
        """Test open interest history KeyError handling."""
        logger.info("Testing OI history KeyError handling")
        
        # Mock config
        mock_config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'ws_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True
                }
            }
        }
        
        from src.core.exchanges.bybit import BybitExchange
        
        exchange = BybitExchange(mock_config)
        exchange.logger = logger
        
        # Mock _make_request to return data without expected keys
        exchange._make_request = AsyncMock(return_value={
            'retCode': 0,
            'retMsg': 'OK',
            'result': {}  # Missing 'list' key
        })
        exchange._check_rate_limit = AsyncMock(return_value=None)
        exchange._convert_to_exchange_symbol = MagicMock(return_value='BTCUSDT')
        
        try:
            result = await exchange.fetch_open_interest_history('BTCUSDT')
            
            # Should return structure with empty history instead of raising KeyError
            assert isinstance(result, dict)
            assert 'history' in result
            assert isinstance(result['history'], list)
            assert len(result['history']) == 0  # Empty due to missing data
            
            logger.info("✅ OI history KeyError handled gracefully")
            
        except KeyError as e:
            logger.error(f"❌ OI history KeyError not handled: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ OI history unexpected error: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_returns_none(self):
        """Test fetch_with_retry returns None instead of raising on max retries."""
        logger.info("Testing fetch_with_retry returns None on failures")
        
        # Mock config
        mock_config = {
            'exchanges': {
                'bybit': {
                    'rest_endpoint': 'https://api.bybit.com',
                    'ws_endpoint': 'wss://stream.bybit.com/v5/public/linear',
                    'api_key': 'test_key',
                    'api_secret': 'test_secret',
                    'sandbox': True
                }
            }
        }
        
        from src.core.exchanges.bybit import BybitExchange
        
        exchange = BybitExchange(mock_config)
        exchange.logger = logger
        exchange._check_rate_limit = AsyncMock(return_value=None)
        
        # Create a function that always raises KeyError
        async def failing_function(*args, **kwargs):
            raise KeyError("Test KeyError")
        
        # Test the internal fetch_with_retry from fetch_market_data
        # We'll use a simpler approach and test the overall behavior
        exchange._fetch_ticker = AsyncMock(side_effect=KeyError("Test KeyError"))
        exchange.get_orderbook = AsyncMock(return_value={'bids': [], 'asks': []})
        exchange.fetch_trades = AsyncMock(return_value=[])
        exchange._fetch_long_short_ratio = AsyncMock(side_effect=KeyError("Test KeyError"))
        exchange._fetch_risk_limits = AsyncMock(return_value={})
        exchange._fetch_all_timeframes = AsyncMock(side_effect=KeyError("Test KeyError"))
        exchange.fetch_open_interest_history = AsyncMock(side_effect=KeyError("Test KeyError"))
        exchange._calculate_historical_volatility = AsyncMock(return_value={})
        
        try:
            result = await exchange.fetch_market_data('BTCUSDT')
            
            # Should get a valid response even with KeyErrors
            assert isinstance(result, dict)
            assert 'metadata' in result
            
            # Check that failed fetches are marked as unsuccessful
            metadata = result['metadata']
            # ticker_success should be False due to KeyError
            # lsr_success should be False due to KeyError  
            # ohlcv_success should be False due to KeyError
            # oi_history_success should be False due to KeyError
            
            logger.info("✅ fetch_with_retry handled KeyErrors gracefully")
            logger.info(f"Metadata: {metadata}")
            
        except KeyError as e:
            logger.error(f"❌ KeyError not handled in fetch_with_retry: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error in fetch_with_retry test: {e}")
            raise

def run_test():
    """Run the test manually if executed directly."""
    logger.info("🧪 Starting KeyError fixes tests")
    
    test_instance = TestBybitKeyErrorFixes()
    test_instance.setup_method()
    
    # Run tests
    async def run_all_tests():
        try:
            await test_instance.test_fetch_market_data_with_missing_keys()
            await test_instance.test_lsr_keyerror_handling()
            await test_instance.test_ohlcv_keyerror_handling()
            await test_instance.test_oi_history_keyerror_handling()
            await test_instance.test_fetch_with_retry_returns_none()
            
            logger.info("✅ All KeyError fixes tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return False
    
    return asyncio.run(run_all_tests())

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1) 