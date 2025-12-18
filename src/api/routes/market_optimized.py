"""Optimized market routes with parallel API calls and caching."""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
import logging
from functools import lru_cache
import time

from ..dependencies import get_exchange_manager
from ...core.exchanges.exchange_manager import ExchangeManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["market"])

# In-memory cache with TTL
class SimpleCache:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str, ttl_seconds: int = 60) -> Optional[Any]:
        if key in self.cache:
            if time.time() - self.timestamps[key] < ttl_seconds:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear_expired(self):
        current_time = time.time()
        expired_keys = [k for k, t in self.timestamps.items() if current_time - t > 300]
        for key in expired_keys:
            del self.cache[key]
            del self.timestamps[key]

# Global cache instance
market_cache = SimpleCache()

async def fetch_ticker_safe(exchange_manager: ExchangeManager, symbol: str) -> Optional[Dict]:
    """Safely fetch ticker data with timeout and error handling."""
    try:
        # Set a timeout for individual ticker fetches
        ticker = await asyncio.wait_for(
            exchange_manager.fetch_ticker(symbol),
            timeout=5.0  # 5 second timeout per symbol
        )
        return ticker
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching {symbol}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {symbol}: {e}")
        return None

@router.get("/overview")
async def get_market_overview_optimized(
    request: Request,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager),
    use_cache: bool = Query(True, description="Use cached data if available")
) -> Dict[str, Any]:
    """Get market overview with optimized parallel fetching and caching."""
    try:
        # Check cache first
        cache_key = "market_overview"
        if use_cache:
            cached_data = market_cache.get(cache_key, ttl_seconds=30)  # 30 second cache
            if cached_data:
                cached_data["cached"] = True
                return cached_data
        
        # Key symbols for market analysis
        key_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", 
                      "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT"]
        
        # Fetch all tickers in parallel
        start_time = time.time()
        tasks = [fetch_ticker_safe(exchange_manager, symbol) for symbol in key_symbols]
        results = await asyncio.gather(*tasks)
        fetch_time = time.time() - start_time
        
        # Process results
        total_volume = 0
        btc_price = 0
        eth_price = 0
        market_data = []
        
        for symbol, ticker in zip(key_symbols, results):
            if ticker:
                volume = float(ticker.get('quoteVolume', 0))
                total_volume += volume
                
                market_data.append({
                    'symbol': symbol,
                    'price': float(ticker.get('last', 0)),
                    'change': float(ticker.get('percentage', 0)),
                    'volume': volume
                })
                
                if symbol == "BTCUSDT":
                    btc_price = float(ticker.get('last', 0))
                elif symbol == "ETHUSDT":
                    eth_price = float(ticker.get('last', 0))
        
        # Calculate market metrics
        if not market_data:
            raise HTTPException(status_code=503, detail="Unable to fetch market data")
        
        # Market breadth
        advancing = len([x for x in market_data if x['change'] > 0])
        declining = len([x for x in market_data if x['change'] < 0])
        
        # Market regime calculation
        avg_change = sum([x['change'] for x in market_data]) / len(market_data)
        btc_change = next((x['change'] for x in market_data if x['symbol'] == 'BTCUSDT'), 0)
        
        # Determine market regime
        if avg_change > 5 and advancing > declining * 1.5:
            regime = "BULLISH"
        elif avg_change < -5 and declining > advancing * 1.5:
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"
        
        # Calculate trend strength (0-100)
        trend_strength = min(100, abs(avg_change) * 10)
        
        # Calculate volatility (simplified)
        price_changes = [abs(x['change']) for x in market_data]
        volatility = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # Calculate BTC dominance (simplified)
        btc_volume = next((x['volume'] for x in market_data if x['symbol'] == 'BTCUSDT'), 0)
        btc_dominance = (btc_volume / total_volume * 100) if total_volume > 0 else 0
        
        # Momentum score
        momentum_score = 50 + (avg_change * 5)  # Scale -10 to +10 change to 0-100 score
        momentum_score = max(0, min(100, momentum_score))
        
        response_data = {
            "status": "active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": regime,
            "trend_strength": round(trend_strength, 1),
            "volatility": round(volatility, 2),
            "avg_volatility": round(volatility * 0.8, 2),  # Historical average approximation
            "btc_dominance": round(btc_dominance, 1),
            "total_volume": total_volume,
            "market_sentiment": "BULLISH" if avg_change > 2 else "BEARISH" if avg_change < -2 else "NEUTRAL",
            "momentum_score": round(momentum_score, 1),
            "breadth": {
                "advancing": advancing,
                "declining": declining,
                "neutral": len(market_data) - advancing - declining
            },
            "btc_price": btc_price,
            "eth_price": eth_price,
            "avg_change": round(avg_change, 2),
            "fetch_time_seconds": round(fetch_time, 2),
            "symbols_fetched": len(market_data),
            "cached": False
        }
        
        # Cache the response
        market_cache.set(cache_key, response_data)
        
        # Clear expired cache entries periodically
        market_cache.clear_expired()
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        # Return default values on error
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": "NEUTRAL",
            "trend_strength": 50.0,
            "volatility": 0.0,
            "avg_volatility": 0.0,
            "btc_dominance": 0.0,
            "total_volume": 0.0,
            "market_sentiment": "NEUTRAL",
            "momentum_score": 50.0,
            "breadth": {"advancing": 0, "declining": 0, "neutral": 0},
            "error": str(e),
            "cached": False
        }

@router.get("/movers")
async def get_market_movers_optimized(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager),
    limit: int = Query(10, ge=1, le=50, description="Number of top movers to return"),
    use_cache: bool = Query(True, description="Use cached data if available")
) -> Dict[str, Any]:
    """Get top gainers and losers with optimized fetching."""
    try:
        # Check cache
        cache_key = f"market_movers_{limit}"
        if use_cache:
            cached_data = market_cache.get(cache_key, ttl_seconds=60)  # 1 minute cache
            if cached_data:
                cached_data["cached"] = True
                return cached_data
        
        # Get all tickers from exchange
        all_tickers = await exchange_manager.fetch_all_tickers()
        
        # Process and filter valid tickers
        processed_tickers = []
        for symbol, ticker in all_tickers.items():
            if ticker and 'percentage' in ticker and ticker['percentage'] is not None:
                processed_tickers.append({
                    'symbol': symbol,
                    'price': ticker.get('last', 0),
                    'change': ticker['percentage'],
                    'volume': ticker.get('quoteVolume', 0)
                })
        
        # Sort by change percentage
        sorted_tickers = sorted(processed_tickers, key=lambda x: x['change'], reverse=True)
        
        # Get top gainers and losers
        gainers = sorted_tickers[:limit]
        losers = sorted_tickers[-limit:][::-1]  # Reverse to get worst first
        
        response_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gainers": gainers,
            "losers": losers,
            "total_symbols": len(processed_tickers),
            "cached": False
        }
        
        # Cache the response
        market_cache.set(cache_key, response_data)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting market movers: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gainers": [],
            "losers": [],
            "error": str(e),
            "cached": False
        }