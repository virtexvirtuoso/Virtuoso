from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional, List
import json
import asyncio
import logging
from datetime import datetime
from src.core.interfaces.exchange import ExchangeInterface
from src.core.analysis.technical import TechnicalAnalysis
from src.core.analysis.portfolio import PortfolioAnalyzer
from src.utils.task_tracker import create_tracked_task

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # symbol -> set of client_ids
        self._lock = asyncio.Lock()
        
    async def connect(
        self,
        websocket: WebSocket,
        client_id: str
    ):
        """Connect a new client"""
        await websocket.accept()
        async with self._lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = set()
            self.active_connections[client_id].add(websocket)
            logger.info(f"Client {client_id} connected")
            
    async def disconnect(
        self,
        websocket: WebSocket,
        client_id: str
    ):
        """Disconnect a client"""
        async with self._lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].remove(websocket)
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]
                    
            # Clean up subscriptions
            for symbol in list(self.subscriptions.keys()):
                if client_id in self.subscriptions[symbol]:
                    self.subscriptions[symbol].remove(client_id)
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
                    
            logger.info(f"Client {client_id} disconnected")
            
    async def subscribe(
        self,
        client_id: str,
        symbol: str
    ):
        """Subscribe a client to a symbol"""
        async with self._lock:
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            self.subscriptions[symbol].add(client_id)
            logger.info(f"Client {client_id} subscribed to {symbol}")
            
    async def unsubscribe(
        self,
        client_id: str,
        symbol: str
    ):
        """Unsubscribe a client from a symbol"""
        async with self._lock:
            if symbol in self.subscriptions and client_id in self.subscriptions[symbol]:
                self.subscriptions[symbol].remove(client_id)
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
                logger.info(f"Client {client_id} unsubscribed from {symbol}")
                
    async def broadcast(
        self,
        message: Dict,
        symbol: Optional[str] = None
    ):
        """Broadcast message to subscribed clients"""
        if symbol:
            # Broadcast to clients subscribed to the symbol
            client_ids = self.subscriptions.get(symbol, set())
        else:
            # Broadcast to all connected clients
            client_ids = set(self.active_connections.keys())
            
        for client_id in client_ids:
            if client_id in self.active_connections:
                dead_connections = set()
                for websocket in self.active_connections[client_id]:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to send to client {client_id}: {str(e)}")
                        dead_connections.add(websocket)
                        
                # Clean up dead connections
                self.active_connections[client_id] -= dead_connections

class MarketDataStream:
    def __init__(
        self,
        manager: ConnectionManager,
        exchange: ExchangeInterface,
        analysis: TechnicalAnalysis,
        portfolio: PortfolioAnalyzer
    ):
        self.manager = manager
        self.exchange = exchange
        self.analysis = analysis
        self.portfolio = portfolio
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
    async def start_symbol_stream(
        self,
        symbol: str,
        interval: float = 1.0
    ):
        """Start streaming market data for a symbol"""
        if symbol in self.running_tasks:
            return
            
        task = create_tracked_task(
            self._stream_symbol_data(symbol, interval, name="auto_tracked_task")
        )
        self.running_tasks[symbol] = task
        
    async def stop_symbol_stream(self, symbol: str):
        """Stop streaming market data for a symbol"""
        if symbol in self.running_tasks:
            self.running_tasks[symbol].cancel()
            del self.running_tasks[symbol]
            
    async def _stream_symbol_data(
        self,
        symbol: str,
        interval: float
    ):
        """Stream market data and analysis for a symbol"""
        try:
            while True:
                # Fetch market data
                market_data = await self.exchange.fetch_market_data(symbol)
                
                # Calculate real-time analysis
                klines = await self.exchange.fetch_historical_klines(
                    symbol=symbol,
                    interval='1m',
                    limit=100
                )
                
                prices = [float(k['close']) for k in klines]
                volumes = [float(k['volume']) for k in klines]
                
                analysis_data = {
                    'moving_averages': self.analysis.calculate_moving_averages(prices),
                    'rsi': self.analysis.calculate_rsi(prices).tolist(),
                    'macd': self.analysis.calculate_macd(prices),
                    'signals': self.analysis.generate_signals(prices, volumes)
                }
                
                # Get position data if exists
                position_data = None
                if symbol in self.portfolio.positions:
                    position = self.portfolio.positions[symbol]
                    position_data = self.portfolio.update_position(
                        symbol=symbol,
                        quantity=position['quantity'],
                        entry_price=position['entry_price'],
                        current_price=float(market_data['ticker']['last']),
                        leverage=position['leverage']
                    )
                
                # Prepare and broadcast message
                message = {
                    'type': 'market_update',
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'market_data': market_data,
                    'analysis': analysis_data,
                    'position': position_data
                }
                
                await self.manager.broadcast(message, symbol)
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info(f"Stopped streaming {symbol}")
        except Exception as e:
            logger.error(f"Error streaming {symbol}: {str(e)}")
            
    async def handle_client_message(
        self,
        client_id: str,
        message: Dict
    ):
        """Handle incoming client messages"""
        try:
            message_type = message.get('type')
            symbol = message.get('symbol')
            
            if message_type == 'subscribe' and symbol:
                await self.manager.subscribe(client_id, symbol)
                await self.start_symbol_stream(symbol)
                
            elif message_type == 'unsubscribe' and symbol:
                await self.manager.unsubscribe(client_id, symbol)
                
                # Check if we can stop the stream
                if symbol in self.manager.subscriptions:
                    if not self.manager.subscriptions[symbol]:
                        await self.stop_symbol_stream(symbol)
                        
        except Exception as e:
            logger.error(f"Error handling client message: {str(e)}")

async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    stream: MarketDataStream
):
    """WebSocket endpoint handler"""
    try:
        await stream.manager.connect(websocket, client_id)
        
        while True:
            message = await websocket.receive_json()
            await stream.handle_client_message(client_id, message)
            
    except WebSocketDisconnect:
        await stream.manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await stream.manager.disconnect(websocket, client_id) 