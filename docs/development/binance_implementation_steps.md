# Binance Implementation Steps - Detailed Developer Guide

## Implementation Strategy Overview

We'll implement Binance integration by **extending the existing CCXT system** rather than building from scratch. This approach is:
- ✅ **Faster**: Leverage existing, tested code
- ✅ **More reliable**: CCXT handles edge cases and API changes
- ✅ **Maintainable**: Follows existing Virtuoso patterns

### Implementation Approach
```
Existing CCXT System     →     Enhanced for Binance
┌─────────────────┐      →     ┌─────────────────────┐
│  CCXTExchange   │      →     │  BinanceExchange   │
│  (Generic)      │      →     │  (Binance-specific) │
└─────────────────┘      →     └─────────────────────┘
```

---

## Week 1: Foundation (Days 1-5)

### Day 1: Create Basic Binance Exchange Class

**Objective**: Create a `BinanceExchange` class that extends `CCXTExchange`

**Step 1.1: Create the File Structure**
```bash
# Create the directory if it doesn't exist
mkdir -p src/data_acquisition/binance

# Create the basic files
touch src/data_acquisition/binance/__init__.py
touch src/data_acquisition/binance/client.py
touch src/data_acquisition/binance/rate_limiter.py
touch src/core/exchanges/binance.py
```

**Step 1.2: Create Basic BinanceExchange Class**

Create `src/core/exchanges/binance.py`:

```python
"""
Binance Exchange Implementation for Virtuoso Trading System

This module provides Binance-specific extensions to the CCXT exchange framework,
optimized for market data analysis and sentiment indicators.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Import the base CCXT exchange class we'll extend
from .ccxt_exchange import CCXTExchange
from .base import BaseExchange

# Set up logging so we can see what's happening
logger = logging.getLogger(__name__)

class BinanceExchange(CCXTExchange):
    """
    Binance-specific implementation extending CCXTExchange.
    
    This class adds Binance-specific features like:
    - Enhanced futures market support
    - Funding rate analysis  
    - Open interest tracking
    - Binance-specific rate limiting
    
    For junior developers: This class inherits from CCXTExchange, which means
    it automatically gets all the basic exchange functionality (fetch_ticker,
    fetch_orderbook, etc.) and we only need to add Binance-specific features.
    """
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """
        Initialize Binance exchange.
        
        Args:
            config: Configuration dictionary from config.yaml
            error_handler: Optional error handler for logging/alerts
        """
        # Call the parent class constructor first
        # This sets up all the basic CCXT functionality
        super().__init__(config, error_handler)
        
        # Set the exchange ID so CCXT knows we want Binance
        self.exchange_id = 'binance'
        self.logger = logging.getLogger(__name__)
        
        # Binance-specific configuration
        self.binance_config = config.get('exchanges', {}).get('binance', {})
        
        # Rate limiting settings (important!)
        rate_limits = self.binance_config.get('rate_limits', {})
        self.max_requests_per_minute = rate_limits.get('requests_per_minute', 1200)
        self.max_weight_per_minute = rate_limits.get('weight_per_minute', 6000)
        
        # Track our API usage to avoid hitting limits
        self.request_count = 0
        self.weight_used = 0
        self.last_minute_reset = time.time()
        
        # Binance-specific endpoints we'll use
        self.futures_endpoints = {
            'open_interest': '/fapi/v1/openInterest',
            'funding_rate': '/fapi/v1/fundingRate',
            'premium_index': '/fapi/v1/premiumIndex'
        }
        
        self.logger.info("Binance exchange initialized successfully")
    
    async def initialize(self) -> bool:
        """
        Initialize the Binance exchange connection.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing Binance exchange...")
            
            # Call parent initialization (sets up CCXT)
            if not await super().initialize():
                self.logger.error("Failed to initialize parent CCXT exchange")
                return False
            
            # Verify we can connect to Binance
            await self._test_connection()
            
            self.logger.info("Binance exchange initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance exchange: {str(e)}")
            return False
    
    async def _test_connection(self):
        """Test basic connectivity to Binance API."""
        try:
            # Try to get exchange info (this is a lightweight test)
            await self.ccxt.load_markets()
            self.logger.info("✅ Binance API connection test successful")
        except Exception as e:
            self.logger.error(f"❌ Binance API connection test failed: {str(e)}")
            raise
    
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch comprehensive market data from Binance.
        
        This method extends the parent class to add Binance-specific data
        like funding rates and open interest for futures markets.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dict containing all market data
        """
        try:
            self.logger.debug(f"Fetching market data for {symbol} from Binance")
            
            # Get the basic market data from parent class
            # This includes ticker, orderbook, trades, etc.
            market_data = await super().fetch_market_data(symbol)
            
            # Add Binance-specific enhancements
            await self._add_binance_specific_data(market_data, symbol)
            
            self.logger.debug(f"Successfully fetched market data for {symbol}")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            raise
    
    async def _add_binance_specific_data(self, market_data: Dict[str, Any], symbol: str):
        """
        Add Binance-specific data to the market data structure.
        
        This includes:
        - Funding rates (for futures)
        - Open interest (for futures) 
        - Premium index
        
        Args:
            market_data: Existing market data to enhance
            symbol: Trading pair symbol
        """
        try:
            # Check if this is a futures symbol
            if self._is_futures_symbol(symbol):
                # Add futures-specific data
                funding_rate = await self._fetch_funding_rate(symbol)
                open_interest = await self._fetch_open_interest(symbol)
                
                # Add to sentiment section (where Virtuoso expects it)
                if 'sentiment' not in market_data:
                    market_data['sentiment'] = {}
                
                market_data['sentiment']['funding_rate'] = funding_rate
                market_data['sentiment']['open_interest'] = open_interest
                
        except Exception as e:
            self.logger.warning(f"Could not fetch Binance-specific data for {symbol}: {str(e)}")
            # Don't fail the entire request if specific data is unavailable
    
    def _is_futures_symbol(self, symbol: str) -> bool:
        """
        Check if a symbol is a futures contract.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            bool: True if it's a futures symbol
        """
        # Simple heuristic: futures symbols usually don't have '/' 
        # and end with 'USDT' (like 'BTCUSDT')
        # Spot symbols have '/' (like 'BTC/USDT')
        return '/' not in symbol and symbol.endswith('USDT')
    
    async def _fetch_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current funding rate for futures symbol.
        
        Funding rates indicate market sentiment:
        - Positive funding rate: Long positions pay short positions (bearish sentiment)
        - Negative funding rate: Short positions pay long positions (bullish sentiment)
        
        Args:
            symbol: Futures symbol
            
        Returns:
            Dict with funding rate data
        """
        try:
            # Convert symbol format for Binance API
            binance_symbol = symbol.replace('/', '')
            
            # Use CCXT to fetch funding rate
            funding = await self.ccxt.fetch_funding_rate(binance_symbol)
            
            return {
                'rate': float(funding.get('fundingRate', 0)),
                'timestamp': funding.get('timestamp', int(time.time() * 1000)),
                'next_funding_time': funding.get('fundingDatetime')
            }
            
        except Exception as e:
            self.logger.debug(f"Could not fetch funding rate for {symbol}: {str(e)}")
            return {'rate': 0, 'timestamp': int(time.time() * 1000)}
    
    async def _fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch open interest for futures symbol.
        
        Open interest indicates market activity:
        - Rising OI + rising price = bullish
        - Rising OI + falling price = bearish
        - Falling OI = trend weakening
        
        Args:
            symbol: Futures symbol
            
        Returns:
            Dict with open interest data
        """
        try:
            # Convert symbol format for Binance API  
            binance_symbol = symbol.replace('/', '')
            
            # This is a custom call since CCXT might not have this method
            endpoint = f"{self.futures_endpoints['open_interest']}?symbol={binance_symbol}"
            response = await self._make_request('GET', endpoint)
            
            return {
                'current': float(response.get('openInterest', 0)),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.debug(f"Could not fetch open interest for {symbol}: {str(e)}")
            return {'current': 0, 'timestamp': int(time.time() * 1000)}
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        Make a custom API request to Binance.
        
        This is for endpoints that CCXT doesn't support directly.
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint path
            params: Optional parameters
            
        Returns:
            API response as dictionary
        """
        # For now, we'll implement this as a placeholder
        # In a real implementation, you'd use the requests library
        # or CCXT's internal request system
        
        self.logger.debug(f"Making {method} request to {endpoint}")
        
        # TODO: Implement actual HTTP request logic here
        # This is where you'd make the actual API call
        
        return {}

# TODO for next development session:
# 1. Implement _make_request method with actual HTTP calls
# 2. Add proper error handling and rate limiting
# 3. Add unit tests for each method
# 4. Test with real Binance API
```

**Step 1.3: Update the Exchange Factory**

Edit `src/core/exchanges/factory.py` to include Binance:

```python
# Add this import at the top
from .binance import BinanceExchange

# Update the EXCHANGE_MAP dictionary
EXCHANGE_MAP = {
    'bybit': BybitExchange,
    'bybit_demo': BybitDemoExchange,
    'coinbase': CoinbaseExchange,
    'hyperliquid': HyperliquidExchange,
    'ccxt': CCXTExchange,
    'binance': BinanceExchange,  # Add this line
}
```

**Step 1.4: Test Your Basic Implementation**

Create a test file `tests/test_binance_basic.py`:

```python
"""
Basic tests for Binance exchange implementation.

These tests verify that our BinanceExchange class can be created
and initialized without errors.
"""

import pytest
import asyncio
from unittest.mock import Mock
from src.core.exchanges.binance import BinanceExchange

@pytest.mark.asyncio
async def test_binance_exchange_creation():
    """Test that we can create a BinanceExchange instance."""
    
    # Create a mock configuration (like what would come from config.yaml)
    config = {
        'exchanges': {
            'binance': {
                'enabled': True,
                'use_ccxt': True,
                'rate_limits': {
                    'requests_per_minute': 1200,
                    'weight_per_minute': 6000
                }
            }
        }
    }
    
    # Create the exchange
    exchange = BinanceExchange(config)
    
    # Verify it was created successfully
    assert exchange.exchange_id == 'binance'
    assert exchange.max_requests_per_minute == 1200
    
    print("✅ BinanceExchange creation test passed!")

@pytest.mark.asyncio 
async def test_futures_symbol_detection():
    """Test that we can correctly identify futures symbols."""
    
    config = {'exchanges': {'binance': {}}}
    exchange = BinanceExchange(config)
    
    # Test futures symbols (no slash)
    assert exchange._is_futures_symbol('BTCUSDT') == True
    assert exchange._is_futures_symbol('ETHUSDT') == True
    
    # Test spot symbols (with slash)
    assert exchange._is_futures_symbol('BTC/USDT') == False
    assert exchange._is_futures_symbol('ETH/USDT') == False
    
    print("✅ Futures symbol detection test passed!")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_binance_exchange_creation())
    asyncio.run(test_futures_symbol_detection())
    print("🎉 All basic tests passed!")
```

Run the test:
```bash
cd /path/to/Virtuoso_ccxt
python -m pytest tests/test_binance_basic.py -v
```

You should see:
```
✅ BinanceExchange creation test passed!
✅ Futures symbol detection test passed!
🎉 All basic tests passed!
```

### Day 2: Implement Rate Limiting

**Objective**: Add proper rate limiting to avoid getting banned by Binance

**Step 2.1: Create Rate Limiter**

Create `src/data_acquisition/binance/rate_limiter.py`:

```python
"""
Binance-specific rate limiter.

Binance uses a "weight" system where different API calls have different costs.
This rate limiter tracks both request count and weight usage.
"""

import time
import asyncio
import logging
from typing import Dict, Any
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class BinanceRateLimiter:
    """
    Rate limiter for Binance API that respects both request and weight limits.
    
    Binance limits:
    - 1200 requests per minute
    - 6000 weight per minute
    - Some endpoints have burst limits
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Configuration dictionary with rate limit settings
        """
        config = config or {}
        
        # Rate limits from configuration
        self.max_requests_per_minute = config.get('requests_per_minute', 1200)
        self.max_weight_per_minute = config.get('weight_per_minute', 6000)
        
        # Safety margins (use 80% of limits to be safe)
        self.safe_requests_per_minute = int(self.max_requests_per_minute * 0.8)
        self.safe_weight_per_minute = int(self.max_weight_per_minute * 0.8)
        
        # Tracking structures
        self.request_history = deque()  # Store timestamps of requests
        self.weight_history = deque()   # Store (timestamp, weight) tuples
        
        # Locks for thread safety
        self.request_lock = asyncio.Lock()
        self.weight_lock = asyncio.Lock()
        
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Rate limiter initialized: {self.safe_requests_per_minute} req/min, {self.safe_weight_per_minute} weight/min")
    
    async def wait_if_needed(self, endpoint_weight: int = 1) -> None:
        """
        Wait if necessary to respect rate limits before making a request.
        
        Args:
            endpoint_weight: Weight cost of the endpoint (default 1)
        """
        async with self.request_lock:
            await self._cleanup_old_requests()
            await self._wait_for_request_limit()
        
        async with self.weight_lock:
            await self._cleanup_old_weights()
            await self._wait_for_weight_limit(endpoint_weight)
    
    async def record_request(self, endpoint_weight: int = 1) -> None:
        """
        Record that a request was made.
        
        Args:
            endpoint_weight: Weight cost of the endpoint
        """
        now = time.time()
        
        async with self.request_lock:
            self.request_history.append(now)
        
        async with self.weight_lock:
            self.weight_history.append((now, endpoint_weight))
        
        self.logger.debug(f"Recorded request with weight {endpoint_weight}")
    
    async def _cleanup_old_requests(self) -> None:
        """Remove request records older than 1 minute."""
        cutoff = time.time() - 60  # 1 minute ago
        
        while self.request_history and self.request_history[0] < cutoff:
            self.request_history.popleft()
    
    async def _cleanup_old_weights(self) -> None:
        """Remove weight records older than 1 minute."""
        cutoff = time.time() - 60  # 1 minute ago
        
        while self.weight_history and self.weight_history[0][0] < cutoff:
            self.weight_history.popleft()
    
    async def _wait_for_request_limit(self) -> None:
        """Wait if we're close to the request limit."""
        if len(self.request_history) >= self.safe_requests_per_minute:
            # Calculate how long to wait
            oldest_request = self.request_history[0]
            wait_time = 60 - (time.time() - oldest_request) + 1  # +1 for safety
            
            if wait_time > 0:
                self.logger.warning(f"Request limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
    
    async def _wait_for_weight_limit(self, needed_weight: int) -> None:
        """Wait if adding this request would exceed weight limit."""
        current_weight = sum(weight for _, weight in self.weight_history)
        
        if current_weight + needed_weight > self.safe_weight_per_minute:
            # Calculate how long to wait
            oldest_weight_time = self.weight_history[0][0] if self.weight_history else time.time()
            wait_time = 60 - (time.time() - oldest_weight_time) + 1  # +1 for safety
            
            if wait_time > 0:
                self.logger.warning(f"Weight limit reached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
    
    def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current rate limit usage statistics.
        
        Returns:
            Dict with current usage info
        """
        current_requests = len(self.request_history)
        current_weight = sum(weight for _, weight in self.weight_history)
        
        return {
            'requests': {
                'current': current_requests,
                'limit': self.safe_requests_per_minute,
                'percentage': (current_requests / self.safe_requests_per_minute) * 100
            },
            'weight': {
                'current': current_weight,
                'limit': self.safe_weight_per_minute,
                'percentage': (current_weight / self.safe_weight_per_minute) * 100
            }
        }

# Endpoint weights for common Binance API calls
# These are the "costs" of different API endpoints
ENDPOINT_WEIGHTS = {
    # Spot market endpoints
    '/api/v3/ticker/24hr': 1,      # Single symbol
    '/api/v3/ticker/24hr_all': 40, # All symbols
    '/api/v3/klines': 1,           # Candlestick data
    '/api/v3/depth': 1,            # Order book (limit 100)
    '/api/v3/depth_500': 5,        # Order book (limit 500)
    '/api/v3/depth_1000': 10,      # Order book (limit 1000)
    '/api/v3/trades': 1,           # Recent trades
    '/api/v3/avgPrice': 1,         # Average price
    '/api/v3/exchangeInfo': 10,    # Exchange information
    
    # Futures market endpoints
    '/fapi/v1/ticker/24hr': 1,     # Single futures symbol
    '/fapi/v1/ticker/24hr_all': 40, # All futures symbols
    '/fapi/v1/klines': 1,          # Futures candlestick data
    '/fapi/v1/depth': 2,           # Futures order book
    '/fapi/v1/openInterest': 1,    # Open interest
    '/fapi/v1/fundingRate': 1,     # Funding rate
    '/fapi/v1/premiumIndex': 1,    # Premium index
}

def get_endpoint_weight(endpoint: str, params: Dict[str, Any] = None) -> int:
    """
    Get the weight cost for a specific endpoint.
    
    Args:
        endpoint: API endpoint path
        params: Request parameters (affect weight for some endpoints)
        
    Returns:
        Weight cost of the endpoint
    """
    # Handle special cases where parameters affect weight
    if endpoint == '/api/v3/depth' and params:
        limit = params.get('limit', 100)
        if limit <= 100:
            return 1
        elif limit <= 500:
            return 5
        elif limit <= 1000:
            return 10
        else:
            return 50
    
    # Return the standard weight for this endpoint
    return ENDPOINT_WEIGHTS.get(endpoint, 1)  # Default weight is 1
```

**Step 2.2: Test Rate Limiter**

Create `tests/test_binance_rate_limiter.py`:

```python
"""
Tests for Binance rate limiter.
"""

import pytest
import asyncio
import time
from src.data_acquisition.binance.rate_limiter import BinanceRateLimiter, get_endpoint_weight

@pytest.mark.asyncio
async def test_rate_limiter_creation():
    """Test that rate limiter can be created."""
    
    config = {
        'requests_per_minute': 1200,
        'weight_per_minute': 6000
    }
    
    limiter = BinanceRateLimiter(config)
    
    assert limiter.max_requests_per_minute == 1200
    assert limiter.max_weight_per_minute == 6000
    assert limiter.safe_requests_per_minute == 960  # 80% of 1200
    assert limiter.safe_weight_per_minute == 4800   # 80% of 6000
    
    print("✅ Rate limiter creation test passed!")

@pytest.mark.asyncio
async def test_rate_limiter_recording():
    """Test that requests are recorded correctly."""
    
    limiter = BinanceRateLimiter()
    
    # Record a few requests
    await limiter.record_request(1)
    await limiter.record_request(5)
    await limiter.record_request(2)
    
    # Check usage statistics
    usage = limiter.get_current_usage()
    
    assert usage['requests']['current'] == 3
    assert usage['weight']['current'] == 8  # 1 + 5 + 2
    
    print("✅ Rate limiter recording test passed!")

def test_endpoint_weights():
    """Test that endpoint weights are calculated correctly."""
    
    # Test standard endpoints
    assert get_endpoint_weight('/api/v3/ticker/24hr') == 1
    assert get_endpoint_weight('/fapi/v1/openInterest') == 1
    assert get_endpoint_weight('/api/v3/exchangeInfo') == 10
    
    # Test depth endpoint with different limits
    assert get_endpoint_weight('/api/v3/depth', {'limit': 100}) == 1
    assert get_endpoint_weight('/api/v3/depth', {'limit': 500}) == 5
    assert get_endpoint_weight('/api/v3/depth', {'limit': 1000}) == 10
    
    # Test unknown endpoint (should default to 1)
    assert get_endpoint_weight('/api/v3/unknown') == 1
    
    print("✅ Endpoint weights test passed!")

if __name__ == "__main__":
    asyncio.run(test_rate_limiter_creation())
    asyncio.run(test_rate_limiter_recording())
    test_endpoint_weights()
    print("🎉 All rate limiter tests passed!")
```

Run the tests:
```bash
python -m pytest tests/test_binance_rate_limiter.py -v
```

---

## Success Validation for Day 1-2

After completing Days 1-2, you should be able to:

1. **Create a BinanceExchange instance**:
   ```python
   from src.core.exchanges.binance import BinanceExchange
   config = {'exchanges': {'binance': {'enabled': True}}}
   exchange = BinanceExchange(config)
   print(exchange.exchange_id)  # Should print 'binance'
   ```

2. **Run rate limiting tests**:
   ```bash
   python -m pytest tests/test_binance_rate_limiter.py
   # Should show all tests passing
   ```

3. **Verify configuration loading**:
   ```python
   python test_config.py
   # Should show "✅ Configuration is valid!"
   ```

### Common Issues and Solutions

**Issue**: `ImportError: No module named 'ccxt'`
**Solution**: Install CCXT: `pip install ccxt`

**Issue**: `KeyError: 'exchanges'` in tests
**Solution**: Check your test configuration - make sure the config dict has the right structure

**Issue**: Tests hang forever
**Solution**: Make sure you're using `pytest-asyncio` and your async tests have `@pytest.mark.asyncio`

---

### Next Steps

Continue to [Day 3-4: Data Fetching Implementation](binance_implementation_days_3_4.md) where we'll:
- Implement actual data fetching methods
- Add proper error handling
- Create comprehensive test cases
- Test with real Binance API (optional) 