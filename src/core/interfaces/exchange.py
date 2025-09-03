"""
Exchange interfaces for dependency injection and type safety.
"""
from abc import ABC, abstractmethod
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from decimal import Decimal

@runtime_checkable
class ExchangeInterface(Protocol):
    """Interface for exchange connections."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from exchange."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data for symbol."""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get orderbook for symbol."""
        pass
    
    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades for symbol."""
        pass
    
    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List[Any]]:
        """Get kline/candlestick data."""
        pass
    
    @abstractmethod
    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information."""
        pass

@runtime_checkable
class TradingInterface(Protocol):
    """Interface for trading operations."""
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get order details."""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders."""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Any]:
        """Get account balance."""
        pass

@runtime_checkable
class WebSocketInterface(Protocol):
    """Interface for WebSocket connections."""
    
    @abstractmethod
    async def connect(self, streams: List[str]) -> None:
        """Connect to WebSocket streams."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        pass
    
    @abstractmethod
    async def subscribe(self, stream: str) -> None:
        """Subscribe to a stream."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, stream: str) -> None:
        """Unsubscribe from a stream."""
        pass
    
    @abstractmethod
    def on_message(self, callback: Any) -> None:
        """Set message callback."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass

@runtime_checkable
class MarketDataInterface(Protocol):
    """Interface for market data providers."""
    
    @abstractmethod
    async def get_market_data(self, symbol: str, data_type: str) -> Dict[str, Any]:
        """
        Get market data.
        
        Args:
            symbol: Trading symbol
            data_type: Type of data (ticker, orderbook, trades, etc.)
            
        Returns:
            Market data
        """
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, interval: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get historical market data."""
        pass
    
    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported symbols."""
        pass
    
    @abstractmethod
    def get_supported_intervals(self) -> List[str]:
        """Get list of supported time intervals."""
        pass

class ExchangeAdapter:
    """Adapter to make existing exchanges compatible with ExchangeInterface."""
    
    def __init__(self, exchange: Any):
        self.exchange = exchange
        
    async def connect(self) -> None:
        """Connect to exchange."""
        if hasattr(self.exchange, 'connect'):
            await self.exchange.connect()
        elif hasattr(self.exchange, 'load_markets'):
            await self.exchange.load_markets()
            
    async def disconnect(self) -> None:
        """Disconnect from exchange."""
        if hasattr(self.exchange, 'disconnect'):
            await self.exchange.disconnect()
        elif hasattr(self.exchange, 'close'):
            await self.exchange.close()
            
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data for symbol."""
        if hasattr(self.exchange, 'get_ticker'):
            return await self.exchange.get_ticker(symbol)
        elif hasattr(self.exchange, 'fetch_ticker'):
            return await self.exchange.fetch_ticker(symbol)
        else:
            raise NotImplementedError(f"Exchange {type(self.exchange)} has no ticker method")
            
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get orderbook for symbol."""
        if hasattr(self.exchange, 'get_orderbook'):
            return await self.exchange.get_orderbook(symbol, limit)
        elif hasattr(self.exchange, 'fetch_order_book'):
            return await self.exchange.fetch_order_book(symbol, limit)
        else:
            raise NotImplementedError(f"Exchange {type(self.exchange)} has no orderbook method")