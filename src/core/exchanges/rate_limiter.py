import asyncio
import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class BybitRateLimiter:
    """Rate limiter for Bybit API to prevent exceeding API limits"""
    
    def __init__(self):
        # IP-based rate limit: 600 requests per 5-second window
        self.ip_limit = 600
        self.ip_window = 5  # seconds
        self.ip_request_timestamps = []
        
        # Endpoint-specific rate limits (default values)
        self.endpoint_limits = {
            # Market data endpoints (most are 10 req/s)
            'v5/market/': 10,
            'v5/market/orderbook': 10,
            'v5/market/tickers': 10,
            'v5/market/recent-trade': 10,
            'v5/market/funding/history': 10,
            'v5/market/account-ratio': 10,
            'v5/market/risk-limit': 10,
            'v5/market/kline': 10,
            'v5/market/instruments-info': 10,
            # Default for any other endpoint
            'default': 5
        }
        self.endpoint_request_timestamps = {}
        
        # Track rate limit from response headers
        self.dynamic_limits = {}
        self.last_reset_time = {}
        self.api_calls = {}  # Track number of calls per endpoint
        
        self.lock = asyncio.Lock()
    
    async def wait_if_needed(self, endpoint: str) -> float:
        """Check if we need to wait before making a request to stay within rate limits
        
        Args:
            endpoint: The API endpoint being called
            
        Returns:
            float: The current timestamp after waiting if necessary
        """
        async with self.lock:
            current_time = time.time()
            
            # Clean up old requests from IP limit tracking
            self.ip_request_timestamps = [t for t in self.ip_request_timestamps 
                                         if current_time - t < self.ip_window]
            
            # Check if we're approaching IP limit
            if len(self.ip_request_timestamps) >= self.ip_limit * 0.95:  # 95% of limit
                # Calculate time to wait
                oldest_timestamp = min(self.ip_request_timestamps) if self.ip_request_timestamps else current_time
                time_to_wait = self.ip_window - (current_time - oldest_timestamp)
                if time_to_wait > 0:
                    logger.warning(f"Approaching IP rate limit, waiting {time_to_wait:.2f}s")
                    await asyncio.sleep(time_to_wait)
                    current_time = time.time()  # Update current time after waiting
            
            # Determine endpoint rate limit
            endpoint_key = 'default'
            for key in self.endpoint_limits:
                if key in endpoint:
                    endpoint_key = key
                    break
            
            # Initialize endpoint tracking if needed
            if endpoint_key not in self.endpoint_request_timestamps:
                self.endpoint_request_timestamps[endpoint_key] = []
            
            # Clean up old requests from endpoint tracking (1-second window)
            self.endpoint_request_timestamps[endpoint_key] = [
                t for t in self.endpoint_request_timestamps[endpoint_key] 
                if current_time - t < 1
            ]
            
            # Check if we're approaching endpoint limit
            endpoint_limit = self.endpoint_limits.get(endpoint_key, self.endpoint_limits['default'])
            
            # Check if we have dynamic limit information from previous responses
            if endpoint in self.dynamic_limits:
                endpoint_limit = self.dynamic_limits[endpoint]
            
            if len(self.endpoint_request_timestamps[endpoint_key]) >= endpoint_limit * 0.95:  # 95% of limit
                time_to_wait = 1.0  # Default to 1 second
                if endpoint in self.last_reset_time:
                    time_to_wait = max(0, self.last_reset_time[endpoint] - current_time)
                
                if time_to_wait > 0:
                    logger.warning(f"Approaching endpoint rate limit for {endpoint}, waiting {time_to_wait:.2f}s")
                    await asyncio.sleep(time_to_wait)
                    current_time = time.time()  # Update current time after waiting
            
            # Record this request
            self.ip_request_timestamps.append(current_time)
            self.endpoint_request_timestamps[endpoint_key].append(current_time)
            
            # Record API call
            if endpoint not in self.api_calls:
                self.api_calls[endpoint] = 0
            self.api_calls[endpoint] += 1
            
            return current_time
    
    def update_from_headers(self, endpoint: str, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers
        
        Args:
            endpoint: The API endpoint that was called
            headers: Response headers from the API call
        """
        try:
            # Example headers:
            # X-Bapi-Limit: 100
            # X-Bapi-Limit-Status: 99
            # X-Bapi-Limit-Reset-Timestamp: 1672738134824
            
            if 'X-Bapi-Limit' in headers:
                limit = int(headers['X-Bapi-Limit'])
                self.dynamic_limits[endpoint] = limit
                
            if 'X-Bapi-Limit-Reset-Timestamp' in headers:
                reset_timestamp = int(headers['X-Bapi-Limit-Reset-Timestamp']) / 1000  # Convert to seconds
                self.last_reset_time[endpoint] = reset_timestamp
                
            if 'X-Bapi-Limit-Status' in headers:
                remaining = int(headers['X-Bapi-Limit-Status'])
                # If we're below 10% of our limit, log a warning
                if remaining < (self.dynamic_limits.get(endpoint, 10) * 0.1):
                    logger.warning(f"Low rate limit remaining for {endpoint}: {remaining}")
        except Exception as e:
            logger.warning(f"Error parsing rate limit headers: {e}")
    
    def record_api_call(self, endpoint: str) -> None:
        """Record an API call for tracking purposes
        
        Args:
            endpoint: The API endpoint that was called
        """
        if endpoint not in self.api_calls:
            self.api_calls[endpoint] = 0
        self.api_calls[endpoint] += 1
    
    def get_api_call_stats(self) -> Dict[str, int]:
        """Get statistics on API calls made
        
        Returns:
            Dict mapping endpoints to call counts
        """
        return self.api_calls.copy() 