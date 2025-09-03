"""Core API endpoints for standard data access."""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, List, Optional, Any
import logging
import time
from datetime import datetime
from src.core.exchanges.manager import ExchangeManager

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

@router.get("/symbols")
async def get_symbols(
    exchange: str = "bybit",
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
):
    """Get list of available trading symbols."""
    try:
        start_time = time.time()
        
        # Get symbols from exchange manager
        if hasattr(exchange_manager, 'get_available_symbols'):
            symbols = await exchange_manager.get_available_symbols(exchange)
        else:
            # Fallback to exchange direct access
            exchange_instance = None
            if hasattr(exchange_manager, 'exchanges') and exchange in exchange_manager.exchanges:
                exchange_instance = exchange_manager.exchanges[exchange]
            elif hasattr(exchange_manager, 'get_primary_exchange'):
                exchange_instance = await exchange_manager.get_primary_exchange()
            
            if exchange_instance and hasattr(exchange_instance, 'load_markets'):
                await exchange_instance.load_markets()
                symbols = list(exchange_instance.markets.keys())
            else:
                # Hard-coded fallback for reliability
                symbols = [
                    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
                    "DOGEUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "BCHUSDT",
                    "EOSUSDT", "TRXUSDT", "XLMUSDT", "ATOMUSDT", "VETUSDT"
                ]
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "symbols": symbols,
            "count": len(symbols),
            "exchange": exchange,
            "timestamp": int(time.time()),
            "response_time_ms": response_time
        }
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        return {
            "symbols": [],
            "count": 0,
            "exchange": exchange,
            "error": str(e),
            "timestamp": int(time.time())
        }

@router.get("/market_data")
async def get_market_data(
    symbol: str = "BTCUSDT",
    exchange: str = "bybit",
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
):
    """Get market data for a specific symbol."""
    try:
        start_time = time.time()
        
        # Get market data from exchange
        exchange_instance = None
        if hasattr(exchange_manager, 'exchanges') and exchange in exchange_manager.exchanges:
            exchange_instance = exchange_manager.exchanges[exchange]
        elif hasattr(exchange_manager, 'get_primary_exchange'):
            exchange_instance = await exchange_manager.get_primary_exchange()
        
        if not exchange_instance:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
        
        # Get ticker data
        ticker = None
        orderbook = None
        trades = None
        
        try:
            if hasattr(exchange_instance, 'fetch_ticker'):
                ticker = await exchange_instance.fetch_ticker(symbol)
        except Exception as e:
            logger.warning(f"Failed to fetch ticker for {symbol}: {e}")
        
        try:
            if hasattr(exchange_instance, 'fetch_order_book'):
                orderbook = await exchange_instance.fetch_order_book(symbol, limit=10)
        except Exception as e:
            logger.warning(f"Failed to fetch orderbook for {symbol}: {e}")
        
        try:
            if hasattr(exchange_instance, 'fetch_trades'):
                trades = await exchange_instance.fetch_trades(symbol, limit=10)
        except Exception as e:
            logger.warning(f"Failed to fetch trades for {symbol}: {e}")
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "ticker": ticker,
            "orderbook": orderbook,
            "trades": trades,
            "timestamp": int(time.time()),
            "response_time_ms": response_time
        }
        
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")

@router.get("/status")
async def get_api_status():
    """Get API status and health information."""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "timestamp": int(time.time()),
        "endpoints": {
            "/api/symbols": "Get trading symbols",
            "/api/market_data": "Get market data for symbol",
            "/api/status": "Get API status"
        }
    }