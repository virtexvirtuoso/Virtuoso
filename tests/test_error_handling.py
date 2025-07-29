#!/usr/bin/env python3
"""
Test the enhanced error handling implementation.

This script tests:
- Rate limit handling
- Network failure recovery
- Connection monitoring
- Error classification
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import aiohttp

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.exchanges.base import (
    BaseExchange, NetworkError, TimeoutError, RateLimitError, 
    AuthenticationError, ExchangeError, retry_on_error
)


class TestExchange(BaseExchange):
    """Test exchange implementation"""
    
    def __init__(self, config):
        super().__init__(config)
        self.exchange_id = "test_exchange"
        self.api_urls = {
            'public': 'https://api.test.com/v1',
            'private': 'https://api.test.com/v1/private'
        }
        self.request_count = 0
        self.health_check_count = 0
        
    async def initialize(self) -> bool:
        """Initialize test exchange"""
        await self.init()
        return True
        
    async def health_check(self) -> bool:
        """Test health check"""
        self.health_check_count += 1
        # Simulate health check
        return self.request_count < 5  # Fail after 5 requests
        
    def sign(self, method, path, params=None, headers=None, body=None):
        """Mock signing"""
        url = f"{self.api_urls['private']}{path}"
        return url, params or {}, headers or {}, body or {}
    
    # Implement abstract methods for testing
    async def connect_ws(self): pass
    async def fetch_market_data(self, timeframe, limit): return {}
    async def get_markets(self): return []
    def parse_balance(self, response): return {}
    def parse_ohlcv(self, response): return []
    def parse_order(self, order): return {}
    def parse_orderbook(self, orderbook, symbol): return {}
    def parse_ticker(self, ticker): return {}
    def parse_trades(self, trades): return []
    async def subscribe_ws(self, channels, symbols): pass


class TestErrorHandling:
    """Test error handling functionality"""
    
    def __init__(self):
        self.config = {
            'timeout': 30000,
            'enableRateLimit': True,
            'rateLimit': 100
        }
        
    async def test_retry_decorator(self):
        """Test retry decorator with exponential backoff"""
        print("\n=== Testing Retry Decorator ===")
        
        attempt_count = 0
        
        @retry_on_error(max_retries=3, initial_delay=0.1, backoff_factor=2.0)
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            print(f"Attempt {attempt_count}")
            if attempt_count < 3:
                raise NetworkError("Network error")
            return "Success"
        
        start_time = time.time()
        result = await failing_function()
        elapsed = time.time() - start_time
        
        print(f"✓ Function succeeded after {attempt_count} attempts")
        print(f"✓ Total time with backoff: {elapsed:.2f}s")
        assert result == "Success"
        assert attempt_count == 3
        
    async def test_rate_limit_handling(self):
        """Test rate limit handling"""
        print("\n=== Testing Rate Limit Handling ===")
        
        exchange = TestExchange(self.config)
        await exchange.initialize()
        
        # Mock response with rate limit error
        with patch.object(exchange.session, 'request') as mock_request:
            # First call returns rate limit error
            mock_response_429 = AsyncMock()
            mock_response_429.status = 429
            mock_response_429.text = AsyncMock(return_value='{"error": "rate limit exceeded", "retry_after": 2}')
            
            # Second call succeeds
            mock_response_200 = AsyncMock()
            mock_response_200.status = 200
            mock_response_200.text = AsyncMock(return_value='{"result": "success"}')
            
            mock_request.return_value.__aenter__.side_effect = [
                mock_response_429,
                mock_response_200
            ]
            
            start_time = time.time()
            try:
                result = await exchange.public_request('GET', '/test')
                elapsed = time.time() - start_time
                print(f"✓ Request succeeded after rate limit retry")
                print(f"✓ Retry delay: {elapsed:.2f}s")
                assert result['result'] == 'success'
            except Exception as e:
                print(f"✗ Rate limit test failed: {e}")
                raise
        
        await exchange.close()
        
    async def test_network_error_recovery(self):
        """Test network error recovery"""
        print("\n=== Testing Network Error Recovery ===")
        
        exchange = TestExchange(self.config)
        await exchange.initialize()
        
        with patch.object(exchange.session, 'request') as mock_request:
            # First two calls fail with network error
            mock_request.return_value.__aenter__.side_effect = [
                aiohttp.ClientError("Connection failed"),
                aiohttp.ClientError("Connection failed"),
                self._create_success_response()
            ]
            
            try:
                result = await exchange.public_request('GET', '/test')
                print(f"✓ Request succeeded after network error recovery")
                assert result['result'] == 'success'
            except Exception as e:
                print(f"✗ Network recovery test failed: {e}")
                raise
        
        await exchange.close()
        
    async def test_error_classification(self):
        """Test error classification"""
        print("\n=== Testing Error Classification ===")
        
        exchange = TestExchange(self.config)
        await exchange.initialize()
        
        test_cases = [
            (401, AuthenticationError, "Authentication failed"),
            (408, TimeoutError, "Request timeout"),
            (429, RateLimitError, "Rate limit exceeded"),
            (500, NetworkError, "Server error"),
            (503, NetworkError, "Service unavailable"),
            (400, ExchangeError, "Bad request")
        ]
        
        for status, expected_error, description in test_cases:
            with patch.object(exchange.session, 'request') as mock_request:
                mock_response = AsyncMock()
                mock_response.status = status
                mock_response.text = AsyncMock(return_value=f'{{"error": "{description}"}}')
                mock_request.return_value.__aenter__.return_value = mock_response
                
                try:
                    await exchange.public_request('GET', '/test')
                    print(f"✗ Expected {expected_error.__name__} for status {status}")
                except expected_error:
                    print(f"✓ Correctly raised {expected_error.__name__} for status {status}")
                except Exception as e:
                    print(f"✗ Wrong error type for status {status}: {type(e).__name__}")
                    raise
        
        await exchange.close()
        
    async def test_connection_monitoring(self):
        """Test connection monitoring and recovery"""
        print("\n=== Testing Connection Monitoring ===")
        
        exchange = TestExchange(self.config)
        exchange._health_check_interval = 0.1  # Speed up for testing
        await exchange.initialize()
        
        # Initial state
        print(f"Initial health check count: {exchange.health_check_count}")
        
        # Monitor connection
        await exchange.monitor_connection()
        print(f"✓ First health check performed: {exchange.health_check_count}")
        
        # Simulate time passing
        exchange._last_health_check = time.time() - 1
        
        # Make requests to trigger health failure
        exchange.request_count = 10
        
        # Monitor again - should trigger recovery
        with patch.object(exchange, 'recover_connection') as mock_recover:
            mock_recover.return_value = None
            await exchange.monitor_connection()
            print(f"✓ Recovery triggered on health check failure")
            assert mock_recover.called
        
        await exchange.close()
        
    async def test_request_rate_limiting(self):
        """Test request rate limiting"""
        print("\n=== Testing Request Rate Limiting ===")
        
        exchange = TestExchange(self.config)
        exchange._request_interval = 0.1  # 100ms between requests
        await exchange.initialize()
        
        # Make rapid requests
        start_time = time.time()
        
        with patch.object(exchange.session, 'request') as mock_request:
            mock_request.return_value.__aenter__.return_value = self._create_success_response()
            
            # Make 3 rapid requests
            for i in range(3):
                await exchange.public_request('GET', f'/test{i}')
            
            elapsed = time.time() - start_time
            print(f"✓ 3 requests took {elapsed:.2f}s with rate limiting")
            
            # Should take at least 0.2s (2 intervals)
            assert elapsed >= 0.2
        
        await exchange.close()
        
    def _create_success_response(self):
        """Create mock success response"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"result": "success"}')
        return mock_response
        
    async def run_all_tests(self):
        """Run all tests"""
        print("Starting Error Handling Tests...")
        
        tests = [
            self.test_retry_decorator,
            self.test_rate_limit_handling,
            self.test_network_error_recovery,
            self.test_error_classification,
            self.test_connection_monitoring,
            self.test_request_rate_limiting
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"\n❌ Test failed: {test.__name__}")
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        print("\n✅ All tests passed!")
        return True


async def main():
    """Run tests"""
    tester = TestErrorHandling()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())