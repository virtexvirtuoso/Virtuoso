"""Consolidated Market API Routes - Phase 1 API Consolidation

This module consolidates the following endpoints:
- Market data (original market.py)
- Correlation analysis (correlation.py) 
- Bitcoin Beta analysis (bitcoin_beta.py)
- Market sentiment (sentiment.py)

Backward compatibility maintained for all existing endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from typing import Dict, List, Optional, Any
from ..models.market import MarketData, OrderBook, Trade, MarketComparison, TechnicalAnalysis
from src.core.exchanges.manager import ExchangeManager
from datetime import datetime, timedelta
import time
import logging
import asyncio
import json
import numpy as np
import pandas as pd
from pathlib import Path
from pydantic import BaseModel
from aiomcache import Client
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.cache.unified_cache import get_cache

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
    """Get general market overview with regime analysis using LIVE data."""
    try:
        # Check cache first
        cache_key = "market_overview"
        cached_data = market_cache.get(cache_key, ttl_seconds=30)
        if cached_data:
            cached_data["cached"] = True
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
            confluence_result = await confluence_analyzer.analyze(confluence_market_data)
            
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

# =============================================================================
# CORRELATION ANALYSIS ENDPOINTS (from correlation.py)
# =============================================================================

# Signal types for correlation analysis
SIGNAL_TYPES = [
    "momentum", "technical", "volume", "orderflow", 
    "orderbook", "sentiment", "price_action", "beta_exp", 
    "confluence", "whale_act", "liquidation"
]

DEFAULT_ASSETS = [
    "BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", 
    "AVAXUSDT", "NEARUSDT", "SOLUSDT", "ALGOUSDT", 
    "ATOMUSDT", "FTMUSDT"
]

class SignalCorrelationCalculator:
    """Calculate correlations between different signals and assets."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def calculate_signal_correlations(
        self, 
        symbols: List[str], 
        timeframe: str = "1h",
        lookback_periods: int = 100
    ) -> Dict[str, Any]:
        """Calculate correlation matrix between signals across assets."""
        try:
            # Get recent signal data for analysis
            signal_data = await self._get_recent_signals(symbols, lookback_periods)
            
            if not signal_data:
                return {"error": "No signal data available"}
            
            # Calculate signal correlations
            correlations = self._compute_signal_correlations(signal_data)
            
            # Calculate cross-asset correlations
            asset_correlations = self._compute_asset_correlations(signal_data)
            
            # Generate correlation statistics
            stats = self._calculate_correlation_stats(correlations, asset_correlations)
            
            return {
                "signal_correlations": correlations,
                "asset_correlations": asset_correlations,
                "statistics": stats,
                "metadata": {
                    "symbols": symbols,
                    "timeframe": timeframe,
                    "lookback_periods": lookback_periods,
                    "calculation_time": datetime.utcnow().isoformat(),
                    "data_points": len(signal_data)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating signal correlations: {e}")
            raise
    
    async def _get_recent_signals(self, symbols: List[str], periods: int) -> List[Dict[str, Any]]:
        """Get recent signal data from stored signals."""
        try:
            signals_dir = Path("reports/json")
            all_signals = []
            
            if not signals_dir.exists():
                return []
            
            # Get signal files for specified symbols
            for symbol in symbols:
                symbol_files = list(signals_dir.glob(f"{symbol}_*.json"))
                symbol_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                # Take recent files
                for file_path in symbol_files[:periods]:
                    try:
                        with open(file_path, 'r') as f:
                            signal_data = json.load(f)
                        signal_data['symbol'] = symbol
                        signal_data['timestamp'] = file_path.stat().st_mtime
                        all_signals.append(signal_data)
                    except Exception as e:
                        self.logger.warning(f"Error reading signal file {file_path}: {e}")
                        continue
            
            return all_signals
            
        except Exception as e:
            self.logger.error(f"Error getting recent signals: {e}")
            return []
    
    def _compute_signal_correlations(self, signal_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Compute correlations between different signal types."""
        try:
            # Create DataFrame with signal scores
            df_data = []
            
            for signal in signal_data:
                row = {"symbol": signal.get("symbol"), "timestamp": signal.get("timestamp")}
                
                # Extract component scores
                components = signal.get("components", {})
                for signal_type in SIGNAL_TYPES:
                    if signal_type in components:
                        comp_data = components[signal_type]
                        if isinstance(comp_data, dict):
                            row[signal_type] = comp_data.get("score", 50.0)
                        else:
                            row[signal_type] = float(comp_data) if comp_data is not None else 50.0
                    else:
                        row[signal_type] = 50.0  # Default neutral score
                
                df_data.append(row)
            
            if not df_data:
                return {}
            
            df = pd.DataFrame(df_data)
            
            # Calculate correlation matrix for signal types
            signal_cols = [col for col in df.columns if col in SIGNAL_TYPES]
            if len(signal_cols) < 2:
                return {}
            
            corr_matrix = df[signal_cols].corr()
            
            # Convert to nested dict
            correlations = {}
            for i, signal1 in enumerate(signal_cols):
                correlations[signal1] = {}
                for j, signal2 in enumerate(signal_cols):
                    correlations[signal1][signal2] = float(corr_matrix.iloc[i, j])
            
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error computing signal correlations: {e}")
            return {}
    
    def _compute_asset_correlations(self, signal_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Compute correlations between assets based on their signal patterns."""
        try:
            # Group signals by symbol
            symbol_signals = {}
            for signal in signal_data:
                symbol = signal.get("symbol")
                if symbol:
                    if symbol not in symbol_signals:
                        symbol_signals[symbol] = []
                    symbol_signals[symbol].append(signal)
            
            # Calculate average signal scores per symbol
            symbol_averages = {}
            for symbol, signals in symbol_signals.items():
                avg_scores = {}
                for signal_type in SIGNAL_TYPES:
                    scores = []
                    for signal in signals:
                        components = signal.get("components", {})
                        if signal_type in components:
                            comp_data = components[signal_type]
                            if isinstance(comp_data, dict):
                                scores.append(comp_data.get("score", 50.0))
                            else:
                                scores.append(float(comp_data) if comp_data is not None else 50.0)
                    
                    avg_scores[signal_type] = np.mean(scores) if scores else 50.0
                
                symbol_averages[symbol] = avg_scores
            
            # Create correlation matrix between symbols
            symbols = list(symbol_averages.keys())
            if len(symbols) < 2:
                return {}
            
            df_assets = pd.DataFrame(symbol_averages).T
            corr_matrix = df_assets.corr()
            
            # Convert to nested dict
            asset_correlations = {}
            for i, symbol1 in enumerate(symbols):
                asset_correlations[symbol1] = {}
                for j, symbol2 in enumerate(symbols):
                    asset_correlations[symbol1][symbol2] = float(corr_matrix.iloc[i, j])
            
            return asset_correlations
            
        except Exception as e:
            self.logger.error(f"Error computing asset correlations: {e}")
            return {}
    
    def _calculate_correlation_stats(self, signal_corr: Dict, asset_corr: Dict) -> Dict[str, Any]:
        """Calculate correlation statistics."""
        try:
            stats = {}
            
            # Signal correlation stats
            if signal_corr:
                all_signal_corrs = []
                for s1, correlations in signal_corr.items():
                    for s2, corr in correlations.items():
                        if s1 != s2 and not pd.isna(corr):
                            all_signal_corrs.append(abs(corr))
                
                if all_signal_corrs:
                    stats["signal_correlation_stats"] = {
                        "mean_correlation": float(np.mean(all_signal_corrs)),
                        "max_correlation": float(np.max(all_signal_corrs)),
                        "min_correlation": float(np.min(all_signal_corrs)),
                        "std_correlation": float(np.std(all_signal_corrs))
                    }
            
            # Asset correlation stats
            if asset_corr:
                all_asset_corrs = []
                for s1, correlations in asset_corr.items():
                    for s2, corr in correlations.items():
                        if s1 != s2 and not pd.isna(corr):
                            all_asset_corrs.append(abs(corr))
                
                if all_asset_corrs:
                    stats["asset_correlation_stats"] = {
                        "mean_correlation": float(np.mean(all_asset_corrs)),
                        "max_correlation": float(np.max(all_asset_corrs)),
                        "min_correlation": float(np.min(all_asset_corrs)),
                        "std_correlation": float(np.std(all_asset_corrs))
                    }
            
            # Summary
            stats["summary"] = {
                "total_signals": len(signal_corr),
                "total_assets": len(asset_corr),
                "analysis_quality": "high" if len(asset_corr) > 5 else "medium" if len(asset_corr) > 2 else "low"
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation stats: {e}")
            return {}

# Initialize correlation calculator
correlation_calculator = SignalCorrelationCalculator()

@router.get("/correlation/matrix")
async def get_signal_confluence_matrix(
    symbols: Optional[str] = Query(default=None),
    timeframe: str = Query(default="1h"),
    include_correlations: bool = Query(default=True)
) -> Dict[str, Any]:
    """Get the signal confluence matrix data matching the dashboard display."""
    try:
        # Parse symbols parameter
        if symbols:
            symbols_list = [s.strip() for s in symbols.split(',') if s.strip()]
        else:
            symbols_list = DEFAULT_ASSETS
        
        logger.info(f"Generating signal confluence matrix for {len(symbols_list)} symbols")
        
        # Get dashboard integration service
        try:
            from src.dashboard.dashboard_integration import get_dashboard_integration
            integration = get_dashboard_integration()
        except ImportError:
            integration = None
        
        matrix_data = {}
        
        if integration:
            # Get real signal data from dashboard integration
            try:
                dashboard_data = await integration.get_dashboard_overview()
                signals_data = dashboard_data.get("signals", []) if isinstance(dashboard_data, dict) else []
                
                # Process signals into matrix format
                for symbol in symbols_list:
                    matrix_data[symbol] = {}
                    
                    # Find signal data for this symbol
                    symbol_signal = None
                    for signal in signals_data:
                        if isinstance(signal, dict) and signal.get("symbol") == symbol:
                            symbol_signal = signal
                            break
                    
                    if symbol_signal and isinstance(symbol_signal, dict) and "confluence_signals" in symbol_signal:
                        # Use real signal data
                        confluence_signals = symbol_signal["confluence_signals"]
                        if isinstance(confluence_signals, dict):
                            for signal_type in SIGNAL_TYPES:
                                if signal_type in confluence_signals:
                                    signal_data = confluence_signals[signal_type]
                                    if isinstance(signal_data, dict):
                                        matrix_data[symbol][signal_type] = {
                                            "score": float(signal_data.get("confidence", 50.0)),
                                            "direction": signal_data.get("direction", "neutral"),
                                            "strength": signal_data.get("strength", "medium")
                                        }
                                    else:
                                        # Handle string or numeric signal data
                                        try:
                                            score = float(signal_data) if signal_data is not None else 50.0
                                        except (ValueError, TypeError):
                                            score = 50.0
                                        
                                        direction = "bullish" if score > 60 else "bearish" if score < 40 else "neutral"
                                        strength = "strong" if score > 70 or score < 30 else "medium"
                                        
                                        matrix_data[symbol][signal_type] = {
                                            "score": score,
                                            "direction": direction,
                                            "strength": strength
                                        }
                                else:
                                    # Default neutral signal
                                    matrix_data[symbol][signal_type] = {
                                        "score": 50.0,
                                        "direction": "neutral", 
                                        "strength": "medium"
                                    }
                        else:
                            # confluence_signals is not a dict, create default signals
                            for signal_type in SIGNAL_TYPES:
                                matrix_data[symbol][signal_type] = {
                                    "score": 50.0,
                                    "direction": "neutral", 
                                    "strength": "medium"
                                }
                    else:
                        # No signal data found, create default signals
                        for signal_type in SIGNAL_TYPES:
                            matrix_data[symbol][signal_type] = {
                                "score": 50.0,
                                "direction": "neutral", 
                                "strength": "medium"
                            }
                    
                    # Calculate composite score
                    if matrix_data[symbol]:
                        scores = [data["score"] for data in matrix_data[symbol].values() if isinstance(data, dict)]
                        composite_score = sum(scores) / len(scores) if scores else 50.0
                        matrix_data[symbol]["composite_score"] = composite_score
                    else:
                        matrix_data[symbol]["composite_score"] = 50.0
                        
            except Exception as e:
                logger.warning(f"Error getting dashboard data: {e}, falling back to mock data")
                integration = None  # Force fallback to mock data
        
        if not integration:
            # Fallback to mock data when dashboard integration is not available
            logger.warning("Dashboard integration not available, using mock data")
            for symbol in symbols_list:
                matrix_data[symbol] = {}
                for signal_type in SIGNAL_TYPES:
                    # Generate realistic mock data
                    score = np.random.uniform(30, 85)
                    direction = "bullish" if score > 60 else "bearish" if score < 40 else "neutral"
                    strength = "strong" if score > 70 or score < 30 else "medium"
                    
                    matrix_data[symbol][signal_type] = {
                        "score": round(score, 1),
                        "direction": direction,
                        "strength": strength
                    }
                
                # Calculate composite score
                scores = [data["score"] for data in matrix_data[symbol].values()]
                matrix_data[symbol]["composite_score"] = sum(scores) / len(scores)
        
        # Calculate correlations if requested
        correlations = {}
        if include_correlations:
            try:
                correlations = await correlation_calculator.calculate_signal_correlations(symbols_list, timeframe)
            except Exception as e:
                logger.warning(f"Error calculating correlations: {e}")
                correlations = {}
        
        return {
            "matrix_data": matrix_data,
            "correlations": correlations,
            "metadata": {
                "symbols": symbols_list,
                "signal_types": SIGNAL_TYPES,
                "timeframe": timeframe,
                "timestamp": datetime.utcnow().isoformat(),
                "total_symbols": len(symbols_list),
                "total_signals": len(SIGNAL_TYPES)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating signal confluence matrix: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating matrix: {str(e)}")

@router.get("/correlation/signals")
async def get_signal_correlations(
    symbols: Optional[str] = Query(default=None),
    timeframe: str = Query(default="1h"),
    lookback_periods: int = Query(default=100, ge=10, le=500)
) -> Dict[str, Any]:
    """Calculate correlations between different signal types."""
    try:
        # Parse symbols parameter
        if symbols:
            symbols_list = [s.strip() for s in symbols.split(',') if s.strip()]
        else:
            symbols_list = DEFAULT_ASSETS
        
        correlations = await correlation_calculator.calculate_signal_correlations(
            symbols_list, timeframe, lookback_periods
        )
        
        return correlations
        
    except Exception as e:
        logger.error(f"Error calculating signal correlations: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating correlations: {str(e)}")

@router.get("/correlation/assets")
async def get_asset_correlations(
    symbols: Optional[str] = Query(default=None),
    timeframe: str = Query(default="1h"),
    lookback_periods: int = Query(default=100, ge=10, le=500)
) -> Dict[str, Any]:
    """Calculate correlations between assets based on their signal patterns."""
    try:
        if symbols:
            symbols_list = [s.strip() for s in symbols.split(',') if s.strip()]
        else:
            symbols_list = DEFAULT_ASSETS
        
        correlations = await correlation_calculator.calculate_signal_correlations(
            symbols_list, timeframe, lookback_periods
        )
        
        return {
            "asset_correlations": correlations.get("asset_correlations", {}),
            "statistics": correlations.get("statistics", {}).get("asset_correlation_stats", {}),
            "metadata": correlations.get("metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Error calculating asset correlations: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating correlations: {str(e)}")

# =============================================================================
# BITCOIN BETA ENDPOINTS (from bitcoin_beta.py)
# =============================================================================

# Cache client for bitcoin beta
btc_cache = Client('localhost', 11211)

@router.get("/bitcoin-beta/status")
async def get_bitcoin_beta_status() -> Dict[str, Any]:
    """Get Bitcoin Beta analysis status and latest metrics."""
    try:
        # Import here to avoid circular imports
        from src.reports.bitcoin_beta_report import BitcoinBetaReport
        
        # Initialize reporter
        reporter = BitcoinBetaReport()
        
        # Get latest beta analysis
        try:
            beta_data = await reporter.get_latest_beta_analysis()
            
            return {
                "status": "active",
                "timestamp": datetime.utcnow().isoformat(),
                "beta_coefficient": beta_data.get("beta_coefficient", 0.0),
                "correlation": beta_data.get("correlation", 0.0),
                "r_squared": beta_data.get("r_squared", 0.0),
                "alpha": beta_data.get("alpha", 0.0),
                "volatility_ratio": beta_data.get("volatility_ratio", 0.0),
                "last_update": beta_data.get("timestamp", datetime.utcnow().isoformat()),
                "analysis_period": beta_data.get("analysis_period", "30d"),
                "market_regime": beta_data.get("market_regime", "neutral"),
                "confidence_level": beta_data.get("confidence_level", 0.0)
            }
            
        except Exception as e:
            logger.warning(f"Could not get latest beta analysis: {e}")
            # Return default/mock data if analysis fails
            return {
                "status": "inactive",
                "timestamp": datetime.utcnow().isoformat(),
                "beta_coefficient": 0.0,
                "correlation": 0.0,
                "r_squared": 0.0,
                "alpha": 0.0,
                "volatility_ratio": 0.0,
                "last_update": datetime.utcnow().isoformat(),
                "analysis_period": "30d",
                "market_regime": "neutral",
                "confidence_level": 0.0,
                "message": "Beta analysis temporarily unavailable"
            }
            
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Bitcoin Beta status: {str(e)}")

@router.get("/bitcoin-beta/analysis")
async def get_bitcoin_beta_analysis() -> Dict[str, Any]:
    """Get detailed Bitcoin Beta analysis."""
    try:
        from src.reports.bitcoin_beta_report import BitcoinBetaReporter
        
        reporter = BitcoinBetaReporter()
        analysis = await reporter.generate_analysis()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis: {str(e)}")

@router.get("/bitcoin-beta/realtime")
async def get_realtime_beta() -> Dict[str, Any]:
    """Get real-time beta values from cache"""
    try:
        # Get market overview
        overview_data = await btc_cache.get(b'beta:overview')
        if overview_data:
            overview = json.loads(overview_data.decode())
        else:
            overview = {
                'market_beta': 1.0,
                'btc_dominance': 57.4,
                'total_symbols': 20,
                'high_beta_count': 0,
                'low_beta_count': 0,
                'neutral_beta_count': 0,
                'avg_correlation': 0.0,
                'market_regime': 'NEUTRAL',
                'timestamp': int(datetime.utcnow().timestamp() * 1000)
            }
        
        # Get all symbol betas
        symbols = []
        symbol_list = [
            'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT',
            'NEARUSDT', 'ATOMUSDT', 'FTMUSDT', 'ALGOUSDT',
            'AAVEUSDT', 'UNIUSDT', 'SUSHIUSDT', 'COMPUSDT',
            'SNXUSDT', 'CRVUSDT', 'MKRUSDT'
        ]
        
        for symbol in symbol_list:
            cache_key = f'beta:values:{symbol}'.encode()
            beta_data = await btc_cache.get(cache_key)
            
            if beta_data:
                symbol_data = json.loads(beta_data.decode())
                symbols.append(symbol_data)
        
        # Sort by 30d beta value (highest first)
        symbols.sort(key=lambda x: x.get('beta_30d', 1.0), reverse=True)
        
        return {
            'status': 'success',
            'overview': overview,
            'symbols': symbols,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime beta data: {e}")
        # Return minimal valid response
        return {
            'status': 'error',
            'overview': {
                'market_beta': 1.0,
                'btc_dominance': 57.4,
                'total_symbols': 0,
                'market_regime': 'NEUTRAL'
            },
            'symbols': [],
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }

@router.get("/bitcoin-beta/history/{symbol}")
async def get_beta_history(symbol: str) -> Dict[str, Any]:
    """Get historical beta values for charting"""
    try:
        cache_key = f'beta:history:{symbol}'.encode()
        history_data = await btc_cache.get(cache_key)
        
        if history_data:
            history = json.loads(history_data.decode())
        else:
            history = []
        
        # Get current beta value
        current_beta = 1.0
        beta_cache_key = f'beta:values:{symbol}'.encode()
        beta_data = await btc_cache.get(beta_cache_key)
        
        if beta_data:
            beta_values = json.loads(beta_data.decode())
            current_beta = beta_values.get('beta_30d', 1.0)
        
        return {
            'status': 'success',
            'symbol': symbol,
            'history': history,
            'current_beta': current_beta,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting beta history for {symbol}: {e}")
        return {
            'status': 'error',
            'symbol': symbol,
            'history': [],
            'current_beta': 1.0,
            'error': str(e)
        }

# =============================================================================
# MARKET SENTIMENT ENDPOINTS (from sentiment.py)
# =============================================================================

class SentimentData(BaseModel):
    """Market sentiment data model."""
    symbol: str
    overall_sentiment: str  # 'extremely_fearful', 'fearful', 'neutral', 'greedy', 'extremely_greedy'
    sentiment_score: float  # 0-100 scale
    fear_greed_index: float  # 0-100 scale
    social_sentiment: float  # -1 to 1 scale
    news_sentiment: float   # -1 to 1 scale
    technical_sentiment: float  # -1 to 1 scale
    volume_sentiment: float     # -1 to 1 scale
    timestamp: int

class MarketMood(BaseModel):
    """Overall market mood model."""
    overall_mood: str
    mood_score: float
    dominant_emotion: str
    volatility_sentiment: str
    trend_sentiment: str
    momentum_sentiment: str
    timestamp: int

@router.get("/sentiment/market")
async def get_market_sentiment():
    """Get market sentiment analysis."""
    return {
        "overall_sentiment": "cautiously_optimistic",
        "sentiment_score": 62,
        "fear_greed_index": 58,
        "market_mood": "bullish",
        "social_sentiment": 0.25,
        "news_sentiment": 0.15,
        "technical_sentiment": 0.35,
        "timestamp": int(time.time() * 1000)
    }

@router.get("/sentiment/symbols")
async def get_symbol_sentiments(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of symbols"),
    sort_by: str = Query("sentiment_score", description="Sort by: sentiment_score, volume, mentions")
) -> List[SentimentData]:
    """Get sentiment data for multiple symbols."""
    try:
        logger.info(f"Getting symbol sentiments: limit={limit}, sort_by={sort_by}")
        
        current_time = int(time.time() * 1000)
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'ATOMUSDT', 'NEARUSDT']
        
        sentiments = []
        for i, symbol in enumerate(symbols[:limit]):
            base_score = 35 + (i * 6) + (hash(symbol) % 15)  # Vary scores
            
            sentiment = SentimentData(
                symbol=symbol,
                overall_sentiment=_get_sentiment_label(base_score),
                sentiment_score=base_score,
                fear_greed_index=base_score + (i % 10) - 5,
                social_sentiment=(base_score - 50) / 50,
                news_sentiment=(base_score - 48) / 50,
                technical_sentiment=(base_score - 52) / 50,
                volume_sentiment=(base_score - 45) / 50,
                timestamp=current_time
            )
            sentiments.append(sentiment)
        
        # Sort by requested criteria
        if sort_by == "sentiment_score":
            sentiments.sort(key=lambda x: x.sentiment_score, reverse=True)
        elif sort_by == "fear_greed_index":
            sentiments.sort(key=lambda x: x.fear_greed_index, reverse=True)
        
        logger.info(f"Returning sentiment data for {len(sentiments)} symbols")
        return sentiments
        
    except Exception as e:
        logger.error(f"Error getting symbol sentiments: {str(e)}")
        return []

@router.get("/sentiment/fear-greed")
async def get_fear_greed_index(
    days: int = Query(7, ge=1, le=30, description="Number of days of historical data")
) -> Dict[str, Any]:
    """Get Fear & Greed Index data and historical trends."""
    try:
        logger.info(f"Getting fear & greed index for {days} days")
        
        current_time = int(time.time() * 1000)
        current_index = 62  # Moderate greed
        
        # Generate historical data
        historical_data = []
        for i in range(days):
            day_offset = i * 24 * 60 * 60 * 1000
            timestamp = current_time - day_offset
            # Simulate some variation in the index
            index_value = current_index + (i % 7 - 3) * 5 + (hash(str(i)) % 10 - 5)
            index_value = max(0, min(100, index_value))  # Clamp to 0-100
            
            historical_data.append({
                "timestamp": timestamp,
                "index": index_value,
                "label": _get_sentiment_label(index_value),
                "date": datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
            })
        
        # Reverse to get chronological order
        historical_data.reverse()
        
        fear_greed_data = {
            "current": {
                "value": current_index,
                "label": _get_sentiment_label(current_index),
                "classification": _get_fear_greed_classification(current_index),
                "timestamp": current_time
            },
            "components": {
                "volatility": {"value": 58, "weight": 25},
                "market_momentum": {"value": 67, "weight": 25},
                "social_media": {"value": 55, "weight": 15},
                "surveys": {"value": 60, "weight": 15},
                "dominance": {"value": 72, "weight": 10},
                "trends": {"value": 45, "weight": 10}
            },
            "historical": historical_data,
            "statistics": {
                "period_days": days,
                "average": sum(h["index"] for h in historical_data) / len(historical_data),
                "min": min(h["index"] for h in historical_data),
                "max": max(h["index"] for h in historical_data),
                "volatility": _calculate_volatility([h["index"] for h in historical_data])
            },
            "insights": {
                "trend": "increasing" if historical_data[-1]["index"] > historical_data[0]["index"] else "decreasing",
                "dominant_emotion": _get_fear_greed_classification(current_index),
                "market_cycle_stage": "accumulation" if current_index < 50 else "distribution",
                "contrarian_signal": current_index > 75 or current_index < 25
            }
        }
        
        logger.info(f"Returning fear & greed index data")
        return fear_greed_data
        
    except Exception as e:
        logger.error(f"Error getting fear & greed index: {str(e)}")
        return {
            "error": "Unable to fetch fear & greed index",
            "timestamp": int(time.time() * 1000)
        }

@router.get("/sentiment/social")
async def get_social_sentiment(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    platform: Optional[str] = Query(None, description="Filter by platform: twitter, reddit, telegram"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
) -> Dict[str, Any]:
    """Get social media sentiment analysis."""
    try:
        logger.info(f"Getting social sentiment: symbol={symbol}, platform={platform}, hours={hours}")
        
        current_time = int(time.time() * 1000)
        
        social_data = {
            "period_hours": hours,
            "platforms": {
                "twitter": {
                    "mentions": 15420,
                    "sentiment_score": 0.23,
                    "positive_ratio": 0.65,
                    "negative_ratio": 0.35,
                    "engagement_rate": 0.087,
                    "trending_hashtags": ["#BTC", "#crypto", "#bullrun", "#DeFi"]
                },
                "reddit": {
                    "mentions": 8940,
                    "sentiment_score": 0.15,
                    "positive_ratio": 0.58,
                    "negative_ratio": 0.42,
                    "upvote_ratio": 0.78,
                    "trending_subreddits": ["cryptocurrency", "bitcoin", "ethtrader"]
                },
                "telegram": {
                    "mentions": 3250,
                    "sentiment_score": 0.31,
                    "positive_ratio": 0.72,
                    "negative_ratio": 0.28,
                    "active_groups": 125,
                    "message_volume": "high"
                }
            },
            "overall_metrics": {
                "total_mentions": 27610,
                "weighted_sentiment": 0.21,
                "sentiment_trend": "improving",
                "viral_coefficient": 1.34,
                "influence_score": 0.67
            },
            "trending_topics": [
                {"topic": "bitcoin etf", "mentions": 2140, "sentiment": 0.45},
                {"topic": "defi yield", "mentions": 1890, "sentiment": 0.32},
                {"topic": "altcoin season", "mentions": 1560, "sentiment": 0.28},
                {"topic": "regulation", "mentions": 1230, "sentiment": -0.15}
            ],
            "influencer_sentiment": {
                "crypto_influencers": 0.25,
                "financial_analysts": 0.18,
                "tech_leaders": 0.31,
                "institutional_voices": 0.22
            },
            "timestamp": current_time
        }
        
        # Filter by symbol if specified
        if symbol:
            symbol_hash = hash(symbol) % 1000
            social_data["symbol_specific"] = {
                "symbol": symbol,
                "mentions": 500 + symbol_hash,
                "sentiment_score": (symbol_hash % 100 - 50) / 100,
                "trend": "bullish" if symbol_hash % 2 == 0 else "bearish",
                "community_size": 10000 + symbol_hash * 10
            }
        
        logger.info(f"Returning social sentiment data")
        return social_data
        
    except Exception as e:
        logger.error(f"Error getting social sentiment: {str(e)}")
        return {
            "error": "Unable to fetch social sentiment",
            "timestamp": int(time.time() * 1000)
        }

# Helper functions for sentiment
def _get_sentiment_label(score: float) -> str:
    """Convert sentiment score to label."""
    if score >= 75:
        return "extremely_greedy"
    elif score >= 55:
        return "greedy"
    elif score >= 45:
        return "neutral"
    elif score >= 25:
        return "fearful"
    else:
        return "extremely_fearful"

def _get_fear_greed_classification(score: float) -> str:
    """Get fear & greed classification."""
    if score >= 75:
        return "extreme_greed"
    elif score >= 55:
        return "greed"
    elif score >= 45:
        return "neutral"
    elif score >= 25:
        return "fear"
    else:
        return "extreme_fear"

def _calculate_volatility(values: List[float]) -> float:
    """Calculate simple volatility of a list of values."""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return (variance ** 0.5) / mean if mean != 0 else 0.0