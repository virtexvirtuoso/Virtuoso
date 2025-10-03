from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from ..models.trading import OrderRequest, OrderResponse, Position, PortfolioSummary
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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

@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> PortfolioSummary:
    """Get portfolio summary across all exchanges (alias for /portfolio/summary)."""
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

@router.get("/orders")
async def get_all_orders(
    limit: int = Query(default=50, ge=1, le=500),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[OrderResponse]:
    """Get orders from all exchanges."""
    try:
        all_orders = []
        
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                orders = await exchange.fetch_orders(limit=limit)
                for order in orders:
                    order['exchange'] = exchange_id  # Add exchange info
                    all_orders.append(OrderResponse(**order))
            except Exception as e:
                logger.error(f"Error getting orders from {exchange_id}: {str(e)}")
                continue
                
        # Sort by timestamp (most recent first)
        all_orders.sort(key=lambda x: x.timestamp or 0, reverse=True)
        return all_orders[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/positions")
async def get_all_positions(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> List[Position]:
    """Get open positions from all exchanges."""
    try:
        all_positions = []
        
        for exchange_id, exchange in exchange_manager.exchanges.items():
            try:
                positions = await exchange.fetch_positions()
                for pos in positions:
                    pos['exchange'] = exchange_id  # Add exchange info
                    all_positions.append(Position(**pos))
            except Exception as e:
                logger.error(f"Error getting positions from {exchange_id}: {str(e)}")
                continue
                
        return all_positions
        
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


@router.get("/status")
async def get_trading_status(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict:
    """Get trading system status and exchange connectivity"""
    try:
        status = {
            'system_status': 'operational',
            'exchanges': {},
            'total_exchanges': 0,
            'connected_exchanges': 0,
            'timestamp': None
        }

        from datetime import datetime
        status['timestamp'] = datetime.now().isoformat()

        if hasattr(exchange_manager, 'exchanges'):
            status['total_exchanges'] = len(exchange_manager.exchanges)

            for exchange_id, exchange in exchange_manager.exchanges.items():
                try:
                    # Test connectivity with a simple health check
                    await exchange.load_markets()
                    status['exchanges'][exchange_id] = {
                        'status': 'connected',
                        'name': exchange.name if hasattr(exchange, 'name') else exchange_id,
                        'has_markets': True
                    }
                    status['connected_exchanges'] += 1
                except Exception as e:
                    status['exchanges'][exchange_id] = {
                        'status': 'error',
                        'error': str(e),
                        'has_markets': False
                    }

        # Update overall status based on connectivity
        if status['connected_exchanges'] == 0:
            status['system_status'] = 'no_exchanges_connected'
        elif status['connected_exchanges'] < status['total_exchanges']:
            status['system_status'] = 'partial_connectivity'

        return status

    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        return {
            'system_status': 'error',
            'error': str(e),
            'exchanges': {},
            'total_exchanges': 0,
            'connected_exchanges': 0,
            'timestamp': datetime.now().isoformat()
        }