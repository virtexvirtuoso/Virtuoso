from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from ..models.market import MarketData, OrderBook, Trade, MarketComparison, TechnicalAnalysis
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request
from datetime import datetime
import time
import logging
import asyncio
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.api.cache_adapter_direct import cache_adapter

# Initialize logger early
logger = logging.getLogger(__name__)

# Import shared cache bridge for live data
try:
    from src.core.cache.web_service_adapter import get_web_service_cache_adapter
    web_cache = get_web_service_cache_adapter()
except ImportError:
    web_cache = None
    logger.warning("Shared cache web adapter not available - using fallback")

# Import cache functionality with safe fallback
try:
    from src.core.cache.unified_cache import get_cache
except ImportError:
    # Fallback if cache module is not available
    def get_cache():
        """Fallback cache implementation"""
        return None

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

async def get_market_reporter(request: Request):
    """Dependency to get market reporter from app state"""
    if not hasattr(request.app.state, "market_reporter"):
        raise HTTPException(status_code=503, detail="Market reporter not initialized")
    return request.app.state.market_reporter

@router.get("/exchanges")
async def list_exchanges(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[str]:
    """List all available exchanges"""
    return list(exchange_manager.exchanges.keys())

@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange_id: str = Query("bybit", description="Exchange to use for ticker data"),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict[str, Any]:
    """Get ticker data for a specific symbol from an exchange (with caching)"""
    try:
        # Enhanced symbol validation
        if not symbol or symbol.upper() in ['UNKNOWN', 'NULL', 'UNDEFINED', 'NONE', '', 'INVALID', 'ERROR']:
            logger.warning(f"Invalid symbol request: '{symbol}' from client")
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Invalid symbol",
                    "message": f"'{symbol}' is not a valid trading symbol",
                    "examples": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                    "hint": "Please check your symbol configuration in the frontend"
                }
            )
        
        # Clean and format symbol
        clean_symbol = symbol.strip().upper()
        
        # Log the request for debugging
        logger.debug(f"Fetching ticker data for {clean_symbol} from {exchange_id}")
        
        # Use unified cache for ticker data
        cache = get_cache()
        
        # Define compute function for cache miss
        async def compute_ticker():
            return await exchange_manager.get_market_data(clean_symbol, exchange_id)
        
        # Get market data with caching (5 second TTL for tickers)
        market_data = await cache.get_ticker(
            exchange=exchange_id,
            symbol=clean_symbol,
            compute_func=compute_ticker
        )
        
        # Validate response structure
        if not market_data:
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "No data available",
                    "message": f"No market data found for {clean_symbol}",
                    "symbol": clean_symbol,
                    "exchange": exchange_id
                }
            )
        
        if exchange_id not in market_data:
            available_exchanges = list(market_data.keys()) if market_data else []
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "Exchange not found",
                    "message": f"Exchange '{exchange_id}' not found in response",
                    "available_exchanges": available_exchanges,
                    "symbol": clean_symbol
                }
            )
        
        exchange_data = market_data[exchange_id]
        if 'error' in exchange_data:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Exchange error",
                    "message": exchange_data['error'],
                    "symbol": clean_symbol,
                    "exchange": exchange_id
                }
            )
            
        # Extract ticker data
        ticker_data = exchange_data.get('ticker', {})
        
        if not ticker_data:
            available_data = list(exchange_data.keys()) if isinstance(exchange_data, dict) else []
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "No ticker data",
                    "message": f"No ticker data found for {clean_symbol}",
                    "symbol": clean_symbol,
                    "exchange": exchange_id,
                    "available_data": available_data
                }
            )
        
        # Log successful data retrieval
        logger.debug(f"Successfully retrieved ticker data for {clean_symbol}")
            
        # Return standardized ticker format
        return {
            "symbol": clean_symbol,
            "exchange": exchange_id,
            "price": ticker_data.get('last', 0),
            "price_change_24h": ticker_data.get('change', 0),
            "price_change_percent_24h": ticker_data.get('percentage', 0),
            "volume_24h": ticker_data.get('baseVolume', ticker_data.get('volume', 0)),
            "quote_volume_24h": ticker_data.get('quoteVolume', 0),
            "high_24h": ticker_data.get('high', 0),
            "low_24h": ticker_data.get('low', 0),
            "bid": ticker_data.get('bid', 0),
            "ask": ticker_data.get('ask', 0),
            "bid_volume": ticker_data.get('bidVolume', 0),
            "ask_volume": ticker_data.get('askVolume', 0),
            "open_24h": ticker_data.get('open', 0),
            "timestamp": ticker_data.get('timestamp', int(time.time() * 1000)),
            "datetime": datetime.fromtimestamp(ticker_data.get('timestamp', time.time() * 1000) / 1000).isoformat() if ticker_data.get('timestamp') else datetime.utcnow().isoformat(),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Internal server error",
                "message": str(e),
                "symbol": symbol,
                "exchange": exchange_id
            }
        )

@router.post("/ticker/batch")
async def get_ticker_batch(
    symbols: List[str] = Body(..., description="List of symbols to fetch ticker data for"),
    exchange_id: str = Body("bybit", description="Exchange to use for ticker data"),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict[str, Any]:
    """Get ticker data for multiple symbols in a single request"""
    try:
        if not symbols:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Empty symbols list",
                    "message": "Please provide at least one symbol"
                }
            )
        
        if len(symbols) > 50:  # Limit batch size to prevent abuse
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Too many symbols",
                    "message": "Maximum 50 symbols allowed per batch request"
                }
            )
        
        # Clean and validate symbols
        clean_symbols = []
        for symbol in symbols:
            if not symbol or symbol.upper() in ['UNKNOWN', 'NULL', 'UNDEFINED', 'NONE', '', 'INVALID', 'ERROR']:
                logger.warning(f"Skipping invalid symbol: '{symbol}'")
                continue
            clean_symbols.append(symbol.strip().upper())
        
        if not clean_symbols:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No valid symbols",
                    "message": "No valid symbols found in the request"
                }
            )
        
        logger.debug(f"Fetching batch ticker data for {len(clean_symbols)} symbols from {exchange_id}")
        
        # Fetch ticker data for all symbols in parallel
        async def fetch_single_ticker(symbol: str) -> Dict[str, Any]:
            try:
                market_data = await exchange_manager.get_market_data(symbol, exchange_id)
                
                if not market_data or exchange_id not in market_data:
                    return {
                        "symbol": symbol,
                        "error": "No data available",
                        "status": "error"
                    }
                
                exchange_data = market_data[exchange_id]
                if 'error' in exchange_data:
                    return {
                        "symbol": symbol,
                        "error": exchange_data['error'],
                        "status": "error"
                    }
                
                ticker_data = exchange_data.get('ticker', {})
                if not ticker_data:
                    return {
                        "symbol": symbol,
                        "error": "No ticker data available",
                        "status": "error"
                    }
                
                # Return standardized ticker format
                return {
                    "symbol": symbol,
                    "exchange": exchange_id,
                    "price": ticker_data.get('last', 0),
                    "price_change_24h": ticker_data.get('change', 0),
                    "price_change_percent_24h": ticker_data.get('percentage', 0),
                    "volume_24h": ticker_data.get('baseVolume', ticker_data.get('volume', 0)),
                    "quote_volume_24h": ticker_data.get('quoteVolume', 0),
                    "high_24h": ticker_data.get('high', 0),
                    "low_24h": ticker_data.get('low', 0),
                    "bid": ticker_data.get('bid', 0),
                    "ask": ticker_data.get('ask', 0),
                    "bid_volume": ticker_data.get('bidVolume', 0),
                    "ask_volume": ticker_data.get('askVolume', 0),
                    "open_24h": ticker_data.get('open', 0),
                    "timestamp": ticker_data.get('timestamp', int(time.time() * 1000)),
                    "datetime": datetime.fromtimestamp(ticker_data.get('timestamp', time.time() * 1000) / 1000).isoformat() if ticker_data.get('timestamp') else datetime.utcnow().isoformat(),
                    "status": "success"
                }
                
            except Exception as e:
                logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
                return {
                    "symbol": symbol,
                    "error": str(e),
                    "status": "error"
                }
        
        # Execute all requests in parallel with controlled concurrency
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
        async def fetch_with_semaphore(symbol: str):
            async with semaphore:
                return await fetch_single_ticker(symbol)
        
        # Fetch all tickers concurrently
        results = await asyncio.gather(
            *[fetch_with_semaphore(symbol) for symbol in clean_symbols],
            return_exceptions=True
        )
        
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({
                    "symbol": "unknown",
                    "error": str(result),
                    "status": "error"
                })
            elif result.get("status") == "success":
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        response = {
            "request_timestamp": int(time.time() * 1000),
            "exchange": exchange_id,
            "total_requested": len(clean_symbols),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "data": successful_results
        }
        
        if failed_results:
            response["errors"] = failed_results
        
        logger.debug(f"Batch ticker request completed: {len(successful_results)}/{len(clean_symbols)} successful")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch ticker request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e)
            }
        )

@router.get("/smart-intervals/status")
async def get_smart_intervals_status(
    request: Request = None
) -> Dict[str, Any]:
    """Get current smart intervals status and activity summary"""
    try:
        # Get market data manager from app state
        if hasattr(request.app.state, "market_data_manager"):
            manager = request.app.state.market_data_manager
            if hasattr(manager, 'smart_intervals'):
                activity_summary = manager.smart_intervals.get_activity_summary()
                current_intervals = manager.get_refresh_intervals()
                
                return {
                    "smart_intervals": activity_summary,
                    "current_intervals": current_intervals,
                    "timestamp": int(time.time() * 1000),
                    "status": "active"
                }
        
        return {
            "smart_intervals": {
                "status": "not_available",
                "message": "Smart intervals manager not initialized"
            },
            "timestamp": int(time.time() * 1000),
            "status": "inactive"
        }
        
    except Exception as e:
        logger.error(f"Error getting smart intervals status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e)
            }
        )

# Simple in-memory cache
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

market_cache = SimpleCache()

async def fetch_ticker_safe(exchange_manager: ExchangeManager, symbol: str) -> Optional[Dict]:
    """Safely fetch ticker data with timeout."""
    try:
        ticker = await asyncio.wait_for(
            exchange_manager.fetch_ticker(symbol),
            timeout=5.0
        )
        return ticker
    except asyncio.TimeoutError:
        logger.warning(f"Timeout fetching {symbol}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching {symbol}: {e}")
        return None

@router.get("/overview")
async def get_market_overview(
    request: Request,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict[str, Any]:
    """Get general market overview with regime analysis using LIVE data from shared cache."""
    try:
        # CRITICAL FIX: Use shared cache bridge for live data
        if web_cache:
            try:
                live_data = await web_cache.get_market_overview()
                if live_data and live_data.get('total_symbols', 0) > 0:
                    logger.info(f"✅ Market overview from shared cache: {live_data.get('total_symbols')} symbols")
                    return {
                        **live_data,
                        "cached": True,
                        "data_source": "shared_cache_live",
                        "timestamp": int(time.time())
                    }
                logger.warning("Shared cache returned empty data, falling back to direct fetch")
            except Exception as e:
                logger.error(f"Shared cache error: {e}, falling back to direct fetch")

        # Fallback to direct exchange fetch if shared cache unavailable
        cache_key = "market_overview"
        cached_data = market_cache.get(cache_key, ttl_seconds=30)
        if cached_data:
            cached_data["cached"] = True
            cached_data["data_source"] = "direct_cache_fallback"
            return cached_data
        
        # Initialize variables
        total_volume = 0
        btc_price = 0
        eth_price = 0
        market_data = []
        
        # Key symbols for market analysis
        key_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", 
                      "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT"]
        
        # Fetch all tickers in parallel with timeout
        start_time = time.time()
        tasks = [fetch_ticker_safe(exchange_manager, symbol) for symbol in key_symbols]
        results = await asyncio.gather(*tasks)
        fetch_time = time.time() - start_time
        
        # Process results
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
        
        # Calculate market breadth (advancing vs declining)
        advancing = len([x for x in market_data if x['change'] > 0])
        declining = len([x for x in market_data if x['change'] < 0])
        neutral = len([x for x in market_data if x['change'] == 0])
        
        # Calculate market regime based on live data
        avg_change = sum([x['change'] for x in market_data]) / len(market_data) if market_data else 0
        btc_change = next((x['change'] for x in market_data if x['symbol'] == 'BTCUSDT'), 0)
        
        regime = "NEUTRAL"
        trend_strength = 50.0
        
        if avg_change > 2 and btc_change > 1 and advancing > declining:
            regime = "BULLISH"
            trend_strength = min(85.0, 60 + (avg_change * 5))
        elif avg_change < -2 and btc_change < -1 and declining > advancing:
            regime = "BEARISH"
            trend_strength = max(15.0, 40 - (abs(avg_change) * 5))
        else:
            trend_strength = 50 + (avg_change * 2)
            
        # Calculate volatility based on price changes
        changes = [abs(x['change']) for x in market_data]
        current_volatility = sum(changes) / len(changes) if changes else 2.0
        avg_volatility = 2.0  # Historical baseline
        
        # Calculate BTC dominance (simplified)
        btc_volume = next((x['volume'] for x in market_data if x['symbol'] == 'BTCUSDT'), 0)
        btc_dominance = (btc_volume / total_volume * 100) if total_volume > 0 else 48.5
        btc_dominance = min(max(btc_dominance, 35.0), 65.0)  # Cap between realistic bounds
        
        # If we don't have live data, use reasonable fallbacks
        if not market_data:
            logger.warning("No live market data available, using fallback values")
            btc_price = 98500  # Reasonable current BTC price
            total_volume = 25000000000  # $25B
            current_volatility = 2.8
            btc_dominance = 48.2
            
        return {
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "regime": regime,
            "trend_strength": round(trend_strength, 1),
            "volatility": round(current_volatility, 1),
            "avg_volatility": round(avg_volatility, 1),
            "btc_dominance": round(btc_dominance, 1),
            "total_volume": int(total_volume),
            "market_sentiment": regime,
            "momentum_score": round(trend_strength, 1),
            "btc_price": btc_price,
            "eth_price": eth_price,
            "avg_market_change": round(avg_change, 2),
            "breadth": {
                "advancing": advancing,
                "declining": declining,
                "neutral": neutral,
                "total": len(market_data)
            },
            "data_quality": "live" if market_data else "fallback"
        }
            
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        # Return default values on error
        return {
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "regime": "NEUTRAL",
            "trend_strength": 50.0,
            "volatility": 0.0,
            "avg_volatility": 0.0,
            "btc_dominance": 0.0,
            "total_volume": 0.0,
            "market_sentiment": "NEUTRAL",
            "momentum_score": 50.0,
            "breadth": {"advancing": 0, "declining": 0},
            "message": "Using fallback market data"
        }

@router.get("/movers")
async def get_market_movers(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager),
    limit: int = Query(10, ge=1, le=50, description="Number of top movers to return")
) -> Dict[str, Any]:
    """Get top gainers and losers from all linear markets."""
    try:
        # Get all linear/perpetual markets from Bybit
        bybit = exchange_manager.exchanges.get('bybit')
        if not bybit:
            raise HTTPException(status_code=500, detail="Bybit exchange not available")
            
        # Get markets using the proper method
        markets_list = await bybit.get_markets()
        
        # Convert list to dict for easier access
        markets = {m['symbol']: m for m in markets_list}
            
        # Filter for linear/perpetual USDT markets
        linear_symbols = []
        for symbol, market in markets.items():
            if (market.get('type') == 'swap' and 
                market.get('linear') and 
                symbol.endswith('USDT') and
                market.get('active', True)):
                linear_symbols.append(symbol)
        
        logger.info(f"Found {len(linear_symbols)} linear markets")
        
        # Fetch tickers for all linear markets
        tickers = {}
        batch_size = 50  # Process in batches to avoid overwhelming the API
        
        for i in range(0, len(linear_symbols), batch_size):
            batch_symbols = linear_symbols[i:i + batch_size]
            try:
                # Fetch multiple tickers at once if supported
                batch_tickers = await bybit.fetch_tickers(batch_symbols)
                tickers.update(batch_tickers)
            except Exception as e:
                logger.warning(f"Error fetching batch tickers: {e}")
                # Fallback to individual ticker fetching
                for symbol in batch_symbols:
                    try:
                        ticker = await bybit.fetch_ticker(symbol)
                        if ticker:
                            tickers[symbol] = ticker
                    except:
                        continue
        
        # Process tickers to find gainers and losers
        market_data = []
        for symbol, ticker in tickers.items():
            try:
                change_pct = float(ticker.get('percentage', 0))
                if change_pct == 0:  # Skip if no change data
                    continue
                
                # Clean symbol for display (remove 1000 prefix)
                display_symbol = symbol
                if symbol.startswith('1000') and len(symbol) > 4:
                    display_symbol = symbol[4:]  # Remove "1000" prefix
                    
                market_data.append({
                    'symbol': symbol,  # Keep original for API calls
                    'display_symbol': display_symbol,  # Cleaned for display
                    'price': float(ticker.get('last', 0)),
                    'change': change_pct,
                    'volume': float(ticker.get('quoteVolume', 0)),
                    'high': float(ticker.get('high', 0)),
                    'low': float(ticker.get('low', 0))
                })
            except:
                continue
        
        # Sort by percentage change
        market_data.sort(key=lambda x: x['change'], reverse=True)
        
        # Get top gainers and losers
        gainers = [item for item in market_data if item['change'] > 0][:limit]
        losers = [item for item in market_data if item['change'] < 0][-limit:]
        losers.reverse()  # Make losers show biggest loss first
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_markets": len(linear_symbols),
            "markets_analyzed": len(market_data),
            "gainers": gainers,
            "losers": losers,
            "summary": {
                "advancing": len([m for m in market_data if m['change'] > 0]),
                "declining": len([m for m in market_data if m['change'] < 0]),
                "unchanged": len([m for m in market_data if m['change'] == 0])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market movers: {e}")
        # Return empty movers on error
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_markets": 0,
            "markets_analyzed": 0,
            "gainers": [],
            "losers": [],
            "summary": {
                "advancing": 0,
                "declining": 0,
                "unchanged": 0
            },
            "error": str(e)
        }

@router.get("/{exchange_id}/{symbol}/data", response_model=MarketData)
async def get_market_data(
    exchange_id: str,
    symbol: str,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> MarketData:
    """Get market data for a symbol from a specific exchange"""
    try:
        data = await exchange_manager.get_market_data(symbol, exchange_id)
        return MarketData(**data[exchange_id])
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{exchange_id}/{symbol}/orderbook", response_model=OrderBook)
async def get_orderbook(
    exchange_id: str,
    symbol: str,
    limit: int = Query(50, ge=1, le=500),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> OrderBook:
    """Get orderbook data for a symbol from a specific exchange (with caching)"""
    try:
        # Use unified cache for orderbook data
        cache = get_cache()
        
        # Define compute function for cache miss
        async def compute_orderbook():
            return await exchange_manager.get_orderbook(symbol, exchange_id, limit)
        
        # Get orderbook with caching (2 second TTL for orderbooks)
        data = await cache.get_orderbook(
            exchange=exchange_id,
            symbol=symbol,
            limit=limit,
            compute_func=compute_orderbook
        )
        return OrderBook(**data)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{exchange_id}/{symbol}/trades", response_model=List[Trade])
async def get_recent_trades(
    exchange_id: str,
    symbol: str,
    limit: int = Query(100, ge=1, le=1000),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[Trade]:
    """Get recent trades for a symbol from a specific exchange"""
    try:
        data = await exchange_manager.get_market_data(symbol, exchange_id)
        trades = data[exchange_id].get('recent_trades', [])
        return [Trade(**trade) for trade in trades[:limit]]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/compare/{symbol}", response_model=MarketComparison)
async def compare_markets(
    symbol: str,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> MarketComparison:
    """Compare market data across all exchanges for a symbol"""
    try:
        all_data = await exchange_manager.get_market_data(symbol)
        
        # Extract ticker data from each exchange
        exchange_data = {}
        prices = []
        total_volume = 0
        
        for exchange_id, data in all_data.items():
            if 'error' not in data:
                ticker = data['ticker']
                exchange_data[exchange_id] = MarketData(
                    symbol=symbol,
                    exchange=exchange_id,
                    price=ticker['last'],
                    volume=ticker['volume'],
                    timestamp=ticker['timestamp'],
                    bid=ticker.get('bid'),
                    ask=ticker.get('ask'),
                    high=ticker.get('high'),
                    low=ticker.get('low')
                )
                prices.append(ticker['last'])
                total_volume += ticker['volume']
        
        if not exchange_data:
            raise HTTPException(status_code=404, detail="No valid market data found")
            
        # Calculate price spread
        price_spread = max(prices) - min(prices) if prices else 0
        
        return MarketComparison(
            symbol=symbol,
            timestamp=int(time.time() * 1000),
            exchanges=exchange_data,
            price_spread=price_spread,
            volume_total=total_volume
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{exchange_id}/{symbol}/analysis", response_model=TechnicalAnalysis)
async def get_technical_analysis(
    exchange_id: str,
    symbol: str,
    timeframe: str = Query("1h", regex="^[0-9]+[mhd]$"),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> TechnicalAnalysis:
    """Get technical analysis for a symbol from a specific exchange"""
    try:
        # Get historical data for analysis
        klines = await exchange_manager.get_historical_data(
            symbol,
            exchange_id,
            timeframe,
            limit=100  # Get enough data for indicators
        )
        
        if not klines:
            raise HTTPException(status_code=404, detail="No historical data available")
            
        # TODO: Implement technical analysis calculation
        # This is a placeholder that should be replaced with actual analysis
        return TechnicalAnalysis(
            symbol=symbol,
            exchange=exchange_id,
            timestamp=int(time.time() * 1000),
            timeframe=timeframe,
            indicators={},
            signals={}
        )
        
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/futures-premium")
async def get_futures_premium_analysis(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)"),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get comprehensive futures premium analysis including contango/backwardation status.
    
    Returns:
    - Individual symbol premiums
    - Overall market contango/backwardation status  
    - Term structure analysis
    - Funding rate correlations
    """
    try:
        market_reporter = await get_market_reporter(request)
        
        # Use provided symbols or default to top pairs
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(',')]
        else:
            symbol_list = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
        
        # Calculate futures premium analysis
        futures_analysis = await market_reporter._calculate_futures_premium(symbol_list)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": futures_analysis,
            "metadata": {
                "symbols_analyzed": len(symbol_list),
                "data_quality": "high" if len(futures_analysis.get('premiums', {})) > 0 else "low"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting futures premium analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating futures premium: {str(e)}")

@router.get("/contango-status")
async def get_contango_status(
    request: Request = None
) -> Dict[str, Any]:
    """
    Get current market contango/backwardation status with actionable insights.
    
    Returns simplified status for dashboard widgets and trading decisions.
    """
    try:
        market_reporter = await get_market_reporter(request)
        
        # Get quick contango analysis for major pairs
        major_pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        futures_data = await market_reporter._calculate_futures_premium(major_pairs)
        
        # Extract key metrics
        contango_status = futures_data.get('contango_status', 'NEUTRAL')
        average_premium = futures_data.get('average_premium_value', 0.0)
        
        # Determine market sentiment and trading implications
        if contango_status == "CONTANGO":
            sentiment = "BULLISH_POSITIONING"
            implication = "Futures traders expect higher prices"
            emoji = "📈"
        elif contango_status == "BACKWARDATION":
            sentiment = "BEARISH_POSITIONING" 
            implication = "Futures traders expect lower prices"
            emoji = "📉"
        else:
            sentiment = "NEUTRAL"
            implication = "Balanced futures positioning"
            emoji = "⚖️"
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "contango_status": contango_status,
            "average_premium": f"{average_premium:.4f}%",
            "market_sentiment": sentiment,
            "trading_implication": implication,
            "display": {
                "emoji": emoji,
                "color": "green" if contango_status == "CONTANGO" else "red" if contango_status == "BACKWARDATION" else "gray",
                "badge_text": f"{emoji} {contango_status}"
            },
            "details": {
                "premium_breakdown": futures_data.get('premiums', {}),
                "symbols_count": len(futures_data.get('premiums', {}))
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting contango status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting contango status: {str(e)}")

@router.get("/term-structure")
async def get_term_structure_analysis(
    symbol: str = Query("BTC/USDT", description="Symbol to analyze (e.g., BTC/USDT)"),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get detailed term structure analysis for a specific symbol.
    
    Shows futures curve and expiration premiums for advanced trading insights.
    """
    try:
        market_reporter = await get_market_reporter(request)
        
        # Get detailed analysis for the symbol
        futures_data = await market_reporter._calculate_futures_premium([symbol])
        
        symbol_data = futures_data.get('premiums', {}).get(symbol, {})
        quarterly_data = futures_data.get('quarterly_futures', {}).get(symbol, [])
        
        return {
            "status": "success", 
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "spot_price": symbol_data.get('index_price', 0),
            "perpetual_price": symbol_data.get('mark_price', 0),
            "perpetual_premium": symbol_data.get('premium', '0.00%'),
            "term_structure": {
                "quarterly_contracts": quarterly_data,
                "curve_shape": "normal" if len(quarterly_data) > 0 else "unknown"
            },
            "analysis": {
                "premium_type": symbol_data.get('premium_type', 'Unknown'),
                "market_structure": futures_data.get('contango_status', 'NEUTRAL'),
                "funding_pressure": symbol_data.get('funding_rate', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting term structure for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting term structure: {str(e)}")

@router.get("/futures-premium/{symbol}")
async def get_single_futures_premium(
    symbol: str,
    request: Request = None
) -> Dict[str, Any]:
    """
    Get contango/backwardation analysis for a single symbol.
    
    Optimized endpoint for individual symbol analysis with quick response times.
    Perfect for real-time widgets and symbol-specific alerts.
    """
    try:
        market_reporter = await get_market_reporter(request)
        
        # Convert URL symbol format (e.g., BTCUSDT) to internal format (BTC/USDT)
        if '/' not in symbol:
            # Convert BTCUSDT to BTC/USDT format
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                symbol_formatted = f"{base}/USDT"
            else:
                symbol_formatted = symbol
        else:
            symbol_formatted = symbol
        
        # Get analysis for the single symbol
        futures_data = await market_reporter._calculate_futures_premium([symbol_formatted])
        
        symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})
        
        if not symbol_data:
            raise HTTPException(status_code=404, detail=f"No futures data available for {symbol}")
        
        # Extract individual symbol metrics
        spot_premium = symbol_data.get('spot_premium', 0.0)
        funding_rate = symbol_data.get('funding_rate', 0.0)
        contango_status = symbol_data.get('contango_status', 'NEUTRAL')
        
        # Determine alert conditions
        alert_conditions = []
        if abs(spot_premium) > 2.0:
            alert_type = 'extreme_contango' if spot_premium > 0 else 'extreme_backwardation'
            alert_conditions.append(alert_type)
        if abs(funding_rate) > 1.0:
            alert_conditions.append('extreme_funding')
        if contango_status != 'NEUTRAL':
            alert_conditions.append('status_change')
        
        # Determine display properties
        if contango_status == "CONTANGO":
            emoji = "📈"
            color = "green"
            sentiment = "BULLISH"
        elif contango_status == "BACKWARDATION":
            emoji = "📉"
            color = "red"
            sentiment = "BEARISH"
        else:
            emoji = "⚖️"
            color = "gray"
            sentiment = "NEUTRAL"
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol_formatted,
            "contango_analysis": {
                "spot_premium": f"{spot_premium:.4f}%",
                "spot_premium_value": spot_premium,
                "funding_rate": f"{funding_rate:.4f}%",
                "funding_rate_value": funding_rate,
                "contango_status": contango_status,
                "market_sentiment": sentiment
            },
            "prices": {
                "spot_price": symbol_data.get('spot_price', 0),
                "perp_price": symbol_data.get('perp_price', 0),
                "index_price": symbol_data.get('index_price', 0),
                "mark_price": symbol_data.get('mark_price', 0)
            },
            "alerts": {
                "conditions": alert_conditions,
                "count": len(alert_conditions),
                "has_alerts": len(alert_conditions) > 0
            },
            "display": {
                "emoji": emoji,
                "color": color,
                "badge_text": f"{emoji} {contango_status}",
                "short_status": contango_status.replace('_', ' ').title()
            },
            "metadata": {
                "quarterly_available": symbol_formatted in futures_data.get('quarterly_futures', {}),
                "data_quality": "high" if spot_premium is not None else "low",
                "last_updated": symbol_data.get('timestamp', int(time.time() * 1000))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting futures premium for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating futures premium for {symbol}: {str(e)}")

@router.get("/analysis/{symbol}")
async def get_comprehensive_symbol_analysis(
    symbol: str,
    exchange_id: str = Query("bybit", description="Exchange to use for analysis"),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get comprehensive analysis for a single symbol including all available data.
    
    This is the one-stop endpoint for complete symbol analysis combining:
    - Real-time market data (price, volume, spread)
    - Contango/backwardation analysis (if futures symbol)
    - Technical indicators and signals
    - Order book summary
    - Recent trading activity
    - Risk metrics and alerts
    
    Perfect for symbol detail pages, comprehensive dashboards, and trading decisions.
    """
    try:
        # Get dependencies
        exchange_manager = await get_exchange_manager(request)
        market_reporter = await get_market_reporter(request)
        
        # Convert symbol format if needed
        if '/' not in symbol:
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                symbol_formatted = f"{base}/USDT"
                symbol_clean = symbol
            else:
                symbol_formatted = symbol
                symbol_clean = symbol
        else:
            symbol_formatted = symbol
            symbol_clean = symbol.replace('/', '')
        
        # Initialize response structure
        analysis = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol_formatted,
            "symbol_clean": symbol_clean,
            "exchange": exchange_id,
            "data_sources": [],
            "analysis": {}
        }
        
        # 1. GET BASIC MARKET DATA
        try:
            market_data = await exchange_manager.get_market_data(symbol_formatted, exchange_id)
            if exchange_id in market_data and 'error' not in market_data[exchange_id]:
                ticker = market_data[exchange_id]['ticker']
                
                analysis["analysis"]["market_data"] = {
                    "price": ticker.get('last', 0),
                    "price_change_24h": ticker.get('change', 0),
                    "price_change_percent_24h": ticker.get('percentage', 0),
                    "volume_24h": ticker.get('volume', 0),
                    "high_24h": ticker.get('high', 0),
                    "low_24h": ticker.get('low', 0),
                    "bid": ticker.get('bid', 0),
                    "ask": ticker.get('ask', 0),
                    "spread": (ticker.get('ask', 0) - ticker.get('bid', 0)) if ticker.get('ask') and ticker.get('bid') else 0,
                    "spread_percent": ((ticker.get('ask', 0) - ticker.get('bid', 0)) / ticker.get('last', 1) * 100) if ticker.get('ask') and ticker.get('bid') and ticker.get('last') else 0,
                    "timestamp": ticker.get('timestamp', int(time.time() * 1000))
                }
                analysis["data_sources"].append("market_data")
                
        except Exception as e:
            logger.warning(f"Could not fetch market data for {symbol}: {e}")
            analysis["analysis"]["market_data"] = {"error": f"Market data unavailable: {str(e)}"}
        
        # 2. GET ORDERBOOK SUMMARY
        try:
            orderbook = await exchange_manager.get_orderbook(symbol_formatted, exchange_id, limit=20)
            
            # Calculate orderbook metrics
            bid_volume = sum(float(bid[1]) for bid in orderbook.get('bids', [])[:10])
            ask_volume = sum(float(ask[1]) for ask in orderbook.get('asks', [])[:10])
            
            analysis["analysis"]["orderbook"] = {
                "best_bid": float(orderbook['bids'][0][0]) if orderbook.get('bids') else 0,
                "best_ask": float(orderbook['asks'][0][0]) if orderbook.get('asks') else 0,
                "bid_volume_top10": bid_volume,
                "ask_volume_top10": ask_volume,
                "volume_imbalance": (bid_volume - ask_volume) / (bid_volume + ask_volume) * 100 if (bid_volume + ask_volume) > 0 else 0,
                "depth_analysis": {
                    "strong_support": bid_volume > ask_volume * 1.5,
                    "strong_resistance": ask_volume > bid_volume * 1.5,
                    "balanced": abs(bid_volume - ask_volume) / (bid_volume + ask_volume) < 0.2 if (bid_volume + ask_volume) > 0 else True
                }
            }
            analysis["data_sources"].append("orderbook")
            
        except Exception as e:
            logger.warning(f"Could not fetch orderbook for {symbol}: {e}")
            analysis["analysis"]["orderbook"] = {"error": f"Orderbook unavailable: {str(e)}"}
        
        # 3. GET CONTANGO ANALYSIS (if futures symbol)
        try:
            # Check if it's a futures symbol
            is_futures = symbol_clean.endswith('USDT') and not any(pattern in symbol_clean.upper() for pattern in ['DEC', 'MAR', 'JUN', 'SEP', '25', '26', '27', '28', '29'])
            
            if is_futures:
                futures_data = await market_reporter._calculate_futures_premium([symbol_formatted])
                symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})
                
                if symbol_data:
                    spot_premium = symbol_data.get('spot_premium', 0.0)
                    funding_rate = symbol_data.get('funding_rate', 0.0)
                    contango_status = symbol_data.get('contango_status', 'NEUTRAL')
                    
                    # Determine alert conditions
                    alert_conditions = []
                    if abs(spot_premium) > 2.0:
                        alert_conditions.append('extreme_premium')
                    if abs(funding_rate) > 1.0:
                        alert_conditions.append('extreme_funding')
                    if contango_status != 'NEUTRAL':
                        alert_conditions.append('status_change')
                    
                    analysis["analysis"]["contango"] = {
                        "is_futures": True,
                        "spot_premium": spot_premium,
                        "spot_premium_formatted": f"{spot_premium:.4f}%",
                        "funding_rate": funding_rate,
                        "funding_rate_formatted": f"{funding_rate:.4f}%",
                        "contango_status": contango_status,
                        "market_sentiment": "BULLISH" if contango_status == "CONTANGO" else "BEARISH" if contango_status == "BACKWARDATION" else "NEUTRAL",
                        "alert_conditions": alert_conditions,
                        "has_alerts": len(alert_conditions) > 0,
                        "prices": {
                            "spot_price": symbol_data.get('spot_price', 0),
                            "perp_price": symbol_data.get('perp_price', 0),
                            "index_price": symbol_data.get('index_price', 0),
                            "mark_price": symbol_data.get('mark_price', 0)
                        },
                        "quarterly_available": symbol_formatted in futures_data.get('quarterly_futures', {})
                    }
                    analysis["data_sources"].append("contango")
                else:
                    analysis["analysis"]["contango"] = {"is_futures": True, "error": "Futures data unavailable"}
            else:
                analysis["analysis"]["contango"] = {"is_futures": False, "message": "Not a futures symbol"}
                
        except Exception as e:
            logger.warning(f"Could not fetch contango analysis for {symbol}: {e}")
            analysis["analysis"]["contango"] = {"error": f"Contango analysis unavailable: {str(e)}"}
        
        # 4. GET CONFLUENCE ANALYSIS (COMPREHENSIVE TECHNICAL ANALYSIS)
        try:
            # Initialize confluence analyzer
            confluence_analyzer = ConfluenceAnalyzer()
            
            # Prepare market data for confluence analysis
            confluence_market_data = {
                "symbol": symbol_formatted,
                "exchange": exchange_id,
                "timestamp": int(time.time() * 1000)
            }
            
            # Add ticker data if available
            if analysis["analysis"]["market_data"].get("price"):
                confluence_market_data["ticker"] = {
                    "last": analysis["analysis"]["market_data"]["price"],
                    "volume": analysis["analysis"]["market_data"]["volume_24h"],
                    "high": analysis["analysis"]["market_data"]["high_24h"],
                    "low": analysis["analysis"]["market_data"]["low_24h"],
                    "bid": analysis["analysis"]["market_data"]["bid"],
                    "ask": analysis["analysis"]["market_data"]["ask"]
                }
            
            # Add orderbook data if available
            if "orderbook" in analysis["analysis"] and "error" not in analysis["analysis"]["orderbook"]:
                confluence_market_data["orderbook"] = {
                    "bids": [[analysis["analysis"]["orderbook"]["best_bid"], analysis["analysis"]["orderbook"]["bid_volume_top10"]]],
                    "asks": [[analysis["analysis"]["orderbook"]["best_ask"], analysis["analysis"]["orderbook"]["ask_volume_top10"]]]
                }
            
            # Get confluence analysis
            if not (confluence_analyzer and hasattr(confluence_analyzer, 'analyze') and callable(getattr(confluence_analyzer, 'analyze'))):
                return {
                    "error": "confluence_analyzer not available",
                    "symbol": symbol,
                    "message": "Confluence analysis service is currently unavailable"
                }

            try:
                confluence_result = await confluence_analyzer.analyze(confluence_market_data)
            except Exception as e:
                logger.debug(f"confluence_analyzer.analyze error for {symbol}: {e}")
                return {
                    "error": f"analysis failed: {e}",
                    "symbol": symbol,
                    "message": "Failed to perform confluence analysis"
                }
            
            if confluence_result and "error" not in confluence_result:
                # Extract key confluence metrics
                confluence_score = confluence_result.get("confluence_score", 50.0)
                reliability = confluence_result.get("reliability", 0.0)
                components = confluence_result.get("components", {})
                
                # Determine overall signal
                if confluence_score >= 70:
                    overall_signal = "STRONG_BUY"
                elif confluence_score >= 60:
                    overall_signal = "BUY"
                elif confluence_score >= 45:
                    overall_signal = "NEUTRAL"
                elif confluence_score >= 30:
                    overall_signal = "SELL"
                else:
                    overall_signal = "STRONG_SELL"
                
                # Count component signals
                buy_signals = sum(1 for comp in components.values() if isinstance(comp, dict) and comp.get("score", 50) > 60)
                sell_signals = sum(1 for comp in components.values() if isinstance(comp, dict) and comp.get("score", 50) < 40)
                neutral_signals = len(components) - buy_signals - sell_signals
                
                analysis["analysis"]["confluence"] = {
                    "confluence_score": confluence_score,
                    "confluence_score_formatted": f"{confluence_score:.1f}/100",
                    "reliability": reliability,
                    "reliability_formatted": f"{reliability:.1f}%",
                    "overall_signal": overall_signal,
                    "signal_strength": "HIGH" if reliability > 80 else "MEDIUM" if reliability > 60 else "LOW",
                    "components": {
                        "technical": components.get("technical", {}).get("score", 50) if "technical" in components else 50,
                        "volume": components.get("volume", {}).get("score", 50) if "volume" in components else 50,
                        "orderflow": components.get("orderflow", {}).get("score", 50) if "orderflow" in components else 50,
                        "sentiment": components.get("sentiment", {}).get("score", 50) if "sentiment" in components else 50,
                        "orderbook": components.get("orderbook", {}).get("score", 50) if "orderbook" in components else 50,
                        "price_structure": components.get("price_structure", {}).get("score", 50) if "price_structure" in components else 50
                    },
                    "signals": {
                        "buy_signals": buy_signals,
                        "sell_signals": sell_signals,
                        "neutral_signals": neutral_signals,
                        "total_components": len(components)
                    },
                    "analysis_timestamp": confluence_result.get("timestamp", int(time.time() * 1000)),
                    "data_quality": len([c for c in components.values() if isinstance(c, dict) and c.get("score") is not None]) / max(len(components), 1) * 100
                }
                analysis["data_sources"].append("confluence")
                
            else:
                analysis["analysis"]["confluence"] = {"error": "Confluence analysis unavailable - insufficient data"}
            
        except Exception as e:
            logger.warning(f"Confluence analysis error for {symbol}: {e}")
            analysis["analysis"]["confluence"] = {"error": f"Confluence analysis unavailable: {str(e)}"}
        
        # 5. RISK ASSESSMENT
        try:
            current_price = analysis["analysis"]["market_data"].get("price", 0)
            volume_24h = analysis["analysis"]["market_data"].get("volume_24h", 0)
            spread_percent = analysis["analysis"]["market_data"].get("spread_percent", 0)
            
            # Calculate risk metrics
            risk_score = 0
            risk_factors = []
            
            # Volume risk
            if volume_24h < 100000:  # Low volume threshold
                risk_score += 2
                risk_factors.append("low_volume")
            
            # Spread risk
            if spread_percent > 0.1:  # High spread threshold
                risk_score += 1
                risk_factors.append("wide_spread")
            
            # Contango risk
            if analysis["analysis"]["contango"].get("has_alerts", False):
                risk_score += 1
                risk_factors.append("contango_alerts")
            
            # Confluence risk
            confluence_data = analysis["analysis"].get("confluence", {})
            if "error" not in confluence_data:
                confluence_score = confluence_data.get("confluence_score", 50)
                reliability = confluence_data.get("reliability", 0)
                
                # High risk if extreme signals with low reliability
                if (confluence_score > 80 or confluence_score < 20) and reliability < 50:
                    risk_score += 2
                    risk_factors.append("unreliable_extreme_signals")
                elif reliability < 30:
                    risk_score += 1
                    risk_factors.append("low_signal_reliability")
            
            # Risk classification
            if risk_score >= 4:
                risk_level = "HIGH"
            elif risk_score >= 2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            analysis["analysis"]["risk_assessment"] = {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "liquidity": "HIGH" if volume_24h > 1000000 else "MEDIUM" if volume_24h > 100000 else "LOW",
                "spread_quality": "TIGHT" if spread_percent < 0.05 else "NORMAL" if spread_percent < 0.1 else "WIDE"
            }
            analysis["data_sources"].append("risk_assessment")
            
        except Exception as e:
            logger.warning(f"Risk assessment error for {symbol}: {e}")
            analysis["analysis"]["risk_assessment"] = {"error": f"Risk assessment unavailable: {str(e)}"}
        
        # 6. SUMMARY AND DISPLAY DATA
        try:
            # Create display-ready summary
            price = analysis["analysis"]["market_data"].get("price", 0)
            price_change = analysis["analysis"]["market_data"].get("price_change_percent_24h", 0)
            contango_status = analysis["analysis"]["contango"].get("contango_status", "NEUTRAL")
            risk_level = analysis["analysis"]["risk_assessment"].get("risk_level", "UNKNOWN")
            
            # Get confluence information
            confluence_data = analysis["analysis"].get("confluence", {})
            confluence_signal = confluence_data.get("overall_signal", "NEUTRAL") if "error" not in confluence_data else "UNKNOWN"
            confluence_score = confluence_data.get("confluence_score", 50) if "error" not in confluence_data else 50
            
            # Determine primary color and emoji
            if price_change > 2:
                price_emoji = "🚀"
                price_color = "green"
            elif price_change > 0:
                price_emoji = "📈"
                price_color = "green"
            elif price_change < -2:
                price_emoji = "📉"
                price_color = "red"
            elif price_change < 0:
                price_emoji = "🔻"
                price_color = "red"
            else:
                price_emoji = "➡️"
                price_color = "gray"
            
            analysis["summary"] = {
                "symbol": symbol_formatted,
                "price": f"${price:,.2f}" if price > 1 else f"${price:.4f}",
                "price_change": f"{price_change:+.2f}%",
                "contango_status": contango_status,
                "confluence_signal": confluence_signal,
                "confluence_score": confluence_score,
                "risk_level": risk_level,
                "data_quality": len(analysis["data_sources"]),
                "alerts_active": analysis["analysis"]["contango"].get("has_alerts", False),
                "display": {
                    "price_emoji": price_emoji,
                    "price_color": price_color,
                    "primary_badge": f"{price_emoji} {price_change:+.2f}%",
                    "risk_badge": f"Risk: {risk_level}",
                    "contango_badge": f"Status: {contango_status}",
                    "confluence_badge": f"Signal: {confluence_signal} ({confluence_score:.0f}/100)",
                    "title": f"{symbol_formatted} Analysis"
                }
            }
            
        except Exception as e:
            logger.warning(f"Summary generation error for {symbol}: {e}")
            analysis["summary"] = {"error": f"Summary unavailable: {str(e)}"}
        
        # 7. METADATA
        analysis["metadata"] = {
            "data_sources_count": len(analysis["data_sources"]),
            "data_sources": analysis["data_sources"],
            "analysis_completeness": len(analysis["data_sources"]) / 6 * 100,  # 6 expected sources: market_data, orderbook, contango, confluence, risk_assessment, summary
            "last_updated": int(time.time() * 1000),
            "cache_duration": 30000,  # 30 seconds cache recommendation
            "api_version": "1.1",
            "features": [
                "real_time_market_data",
                "contango_backwardation_analysis", 
                "confluence_technical_analysis",
                "orderbook_depth_analysis",
                "risk_assessment",
                "display_ready_formatting"
            ]
        }
        
        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in comprehensive analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating comprehensive analysis for {symbol}: {str(e)}")


@router.get("/data")

@router.get("/symbols")
async def get_market_symbols() -> Dict[str, Any]:
    """Get list of all tracked symbols with basic info."""
    try:
        # Use shared cache bridge for live data
        from src.core.cache.web_service_adapter import get_web_service_cache_adapter
        web_cache = get_web_service_cache_adapter()

        if web_cache:
            try:
                symbols_data = await web_cache.get_symbols_list()
                if symbols_data:
                    return symbols_data
            except Exception as e:
                logger.error(f"Error fetching symbols from cache: {e}")

        # Fallback: Get from Bybit directly
        import aiohttp
        async with aiohttp.ClientSession() as session:
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('retCode') == 0 and 'result' in data:
                        tickers = data['result']['list']
                        symbols = [
                            {
                                "symbol": t['symbol'],
                                "price": float(t['lastPrice']),
                                "change_24h": float(t['price24hPcnt']) * 100,
                                "volume_24h": float(t['volume24h'])
                            }
                            for t in tickers
                            if t['symbol'].endswith('USDT') and float(t['turnover24h']) > 1000000
                        ]
                        return {
                            "symbols": symbols[:50],  # Top 50 by volume
                            "count": len(symbols),
                            "timestamp": datetime.utcnow().isoformat()
                        }

        return {
            "symbols": [],
            "count": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "no_data"
        }
    except Exception as e:
        logger.error(f"Error in get_market_symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_general_market_data(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get general market data overview across exchanges"""
    try:
        from datetime import datetime
        import time

        overview = {
            'status': 'operational',
            'exchanges': {},
            'top_symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time()
        }

        if hasattr(exchange_manager, 'exchanges'):
            for exchange_id, exchange in exchange_manager.exchanges.items():
                try:
                    # Get basic market info
                    markets = await exchange.load_markets()
                    overview['exchanges'][exchange_id] = {
                        'status': 'connected',
                        'market_count': len(markets),
                        'name': exchange.name if hasattr(exchange, 'name') else exchange_id
                    }
                except Exception as e:
                    overview['exchanges'][exchange_id] = {
                        'status': 'error',
                        'error': str(e),
                        'market_count': 0
                    }

        return overview

    except Exception as e:
        logger.error(f"Error getting general market data: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'exchanges': {},
            'timestamp': datetime.now().isoformat()
        }