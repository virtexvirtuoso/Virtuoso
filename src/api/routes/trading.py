from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from ..models.trading import OrderRequest, OrderResponse, Position, PortfolioSummary
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request

router = APIRouter()

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

@router.post("/{exchange_id}/order", response_model=OrderResponse)
async def place_order(
    exchange_id: str,
    order: OrderRequest,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> OrderResponse:
    """Place a new order on a specific exchange"""
    try:
        if exchange_id not in exchange_manager.exchanges:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
            
        exchange = exchange_manager.exchanges[exchange_id]
        response = await exchange.create_order(
            symbol=order.symbol,
            type=order.type,
            side=order.side,
            amount=order.amount,
            price=order.price,
            params=order.params or {}
        )
        
        return OrderResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{exchange_id}/orders", response_model=List[OrderResponse])
async def get_orders(
    exchange_id: str,
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[OrderResponse]:
    """Get orders from a specific exchange"""
    try:
        if exchange_id not in exchange_manager.exchanges:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
            
        exchange = exchange_manager.exchanges[exchange_id]
        orders = await exchange.fetch_orders(symbol=symbol, limit=limit)
        
        # Filter by status if specified
        if status:
            orders = [order for order in orders if order['status'] == status]
            
        return [OrderResponse(**order) for order in orders[:limit]]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{exchange_id}/positions", response_model=List[Position])
async def get_positions(
    exchange_id: str,
    symbol: Optional[str] = None,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[Position]:
    """Get open positions from a specific exchange"""
    try:
        if exchange_id not in exchange_manager.exchanges:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
            
        exchange = exchange_manager.exchanges[exchange_id]
        positions = await exchange.fetch_positions()
        
        # Filter by symbol if specified
        if symbol:
            positions = [pos for pos in positions if pos['symbol'] == symbol]
            
        return [Position(**pos) for pos in positions]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{exchange_id}/position/update")
async def update_position(
    exchange_id: str,
    symbol: str,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
):
    """Update position parameters (stop loss, take profit)"""
    try:
        if exchange_id not in exchange_manager.exchanges:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
            
        exchange = exchange_manager.exchanges[exchange_id]
        
        # Get current position
        positions = await exchange.fetch_positions()
        position = next((pos for pos in positions if pos['symbol'] == symbol), None)
        
        if not position:
            raise HTTPException(status_code=404, detail=f"No open position found for {symbol}")
            
        # Update position parameters
        params = {}
        if stop_loss is not None:
            params['stopLoss'] = stop_loss
        if take_profit is not None:
            params['takeProfit'] = take_profit
            
        if params:
            await exchange.update_position(symbol, params)
            return {"message": "Position updated successfully"}
        else:
            return {"message": "No parameters to update"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> PortfolioSummary:
    """Get portfolio summary across all exchanges"""
    try:
        summary = {
            'total_equity': 0.0,
            'total_pnl': 0.0,
            'positions_count': 0,
            'exchanges': {}
        }
        
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                # Get balance and positions
                balance = await exchange.fetch_balance()
                positions = await exchange.fetch_positions()
                
                exchange_summary = {
                    'equity': sum(float(bal['total']) for bal in balance.values()),
                    'pnl': sum(float(pos['unrealizedPnl']) for pos in positions),
                    'positions': len(positions)
                }
                
                summary['exchanges'][exchange_id] = exchange_summary
                summary['total_equity'] += exchange_summary['equity']
                summary['total_pnl'] += exchange_summary['pnl']
                summary['positions_count'] += exchange_summary['positions']
                
            except Exception as e:
                logger.error(f"Error getting data from {exchange_id}: {str(e)}")
                continue
                
        return PortfolioSummary(**summary)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 