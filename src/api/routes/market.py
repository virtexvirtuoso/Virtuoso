from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from ..models.market import MarketData, OrderBook, Trade, MarketComparison, TechnicalAnalysis
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request
import time

router = APIRouter()

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

@router.get("/exchanges")
async def list_exchanges(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[str]:
    """List all available exchanges"""
    return list(exchange_manager.exchanges.keys())

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
    """Get orderbook data for a symbol from a specific exchange"""
    try:
        data = await exchange_manager.get_orderbook(symbol, exchange_id, limit)
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