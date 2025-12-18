import asyncio
import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from collections import defaultdict, deque
import json

from src.core.exchanges.manager import ExchangeManager
from src.core.models.liquidation import LiquidationEvent, LiquidationType, LiquidationSeverity
from src.utils.task_tracker import create_tracked_task

@dataclass
class RawLiquidationData:
    """Raw liquidation data from exchange."""
    symbol: str
    exchange: str
    side: str  # 'buy' or 'sell'
    price: float
    quantity: float
    timestamp: int  # milliseconds
    liquidation_id: Optional[str] = None
    raw_data: Optional[Dict] = None

class LiquidationDataCollector:
    """Collects real liquidation data from exchanges via WebSocket and REST APIs."""
    
    def __init__(self, exchange_manager: ExchangeManager, storage_callback: Optional[Callable] = None):
        self.exchange_manager = exchange_manager
        self.storage_callback = storage_callback
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage for recent liquidations
        self.recent_liquidations = defaultdict(lambda: deque(maxlen=1000))
        
        # WebSocket connections and subscriptions
        self.websocket_connections = {}
        self.subscribed_symbols = set()
        
        # Collection statistics
        self.collection_stats = {
            'total_liquidations': 0,
            'liquidations_per_exchange': defaultdict(int),
            'last_update': None
        }

        # Running flag
        self.is_collecting = False

        # Background collection tasks
        self.collection_tasks = []
    
    async def start_collection(self, symbols: List[str]):
        """Start collecting liquidation data for specified symbols."""
        self.logger.info(f"Starting liquidation data collection for {len(symbols)} symbols")
        
        self.is_collecting = True
        self.subscribed_symbols.update(symbols)
        
        # Start collection tasks for each exchange
        tasks = []
        for exchange_id, exchange in self.exchange_manager.exchanges.items():
            if hasattr(exchange, 'subscribe_liquidations'):
                task = create_tracked_task(
                    self._collect_from_exchange(exchange_id, exchange, symbols), name="_collect_from_exchange_task"
                )
                tasks.append(task)

        # Start periodic REST API collection for exchanges that don't support WebSocket
        tasks.append(create_tracked_task(self._periodic_rest_collection(symbols), name="_periodic_rest_collection_task"))

        # Don't await the tasks - they run forever in the background
        # Just store them so we can manage them later
        self.collection_tasks = tasks

        self.logger.info(f"✅ Started {len(tasks)} background liquidation collection tasks")

        # Return immediately - tasks run in background
        return True
    
    async def stop_collection(self):
        """Stop all liquidation data collection."""
        self.logger.info("Stopping liquidation data collection")
        self.is_collecting = False
        
        # Close WebSocket connections
        for connection in self.websocket_connections.values():
            if hasattr(connection, 'close'):
                await connection.close()
        
        self.websocket_connections.clear()
    
    async def _collect_from_exchange(self, exchange_id: str, exchange, symbols: List[str]):
        """Collect liquidation data from a specific exchange."""
        try:
            if exchange_id.lower() == 'bybit':
                await self._collect_bybit_liquidations(exchange, symbols)
            elif exchange_id.lower() == 'binance':
                await self._collect_binance_liquidations(exchange, symbols)
            elif exchange_id.lower() == 'okx':
                await self._collect_okx_liquidations(exchange, symbols)
            else:
                self.logger.warning(f"Liquidation collection not implemented for {exchange_id}")
        
        except Exception as e:
            self.logger.error(f"Error collecting from {exchange_id}: {e}")
    
    async def _collect_bybit_liquidations(self, exchange, symbols: List[str]):
        """Collect liquidation data from Bybit WebSocket."""
        try:
            # Try to subscribe to WebSocket liquidations if available (optional)
            if hasattr(exchange, 'subscribe_liquidations'):
                try:
                    result = await exchange.subscribe_liquidations(symbols)
                    if result:
                        self.logger.info(f"✅ Subscribed to Bybit liquidations via WebSocket for {len(symbols)} symbols")
                    else:
                        self.logger.info(f"WebSocket liquidation subscription unavailable, using REST polling fallback")
                except Exception as e:
                    self.logger.info(f"WebSocket liquidation subscription failed, using REST polling fallback: {e}")

            # Poll for REST API liquidation data (primary mechanism)
            while self.is_collecting:
                for symbol in symbols:
                    try:
                        # Get recent liquidations via REST if available
                        if hasattr(exchange, 'get_recent_liquidations'):
                            liquidations = exchange.get_recent_liquidations(symbol, hours=1)
                            for liq_data in liquidations:
                                await self._process_raw_liquidation(
                                    RawLiquidationData(
                                        symbol=liq_data['symbol'],
                                        exchange='bybit',
                                        side=liq_data['side'],
                                        price=liq_data['price'],
                                        quantity=liq_data['size'],
                                        timestamp=liq_data['timestamp'],
                                        raw_data=liq_data
                                    )
                                )
                    except Exception as e:
                        self.logger.debug(f"Error getting Bybit liquidations for {symbol}: {e}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            self.logger.error(f"Error in Bybit liquidation collection: {e}")
    
    async def _collect_binance_liquidations(self, exchange, symbols: List[str]):
        """Collect liquidation data from Binance."""
        try:
            # Binance provides liquidation data via force order stream
            while self.is_collecting:
                for symbol in symbols:
                    try:
                        # Binance uses forceOrder endpoint for liquidation data
                        if hasattr(exchange, 'fapiPublicGetForceOrder'):
                            liquidations = await exchange.fapiPublicGetForceOrder({
                                'symbol': symbol.replace('/', ''),
                                'limit': 100
                            })
                            
                            for liq in liquidations:
                                await self._process_raw_liquidation(
                                    RawLiquidationData(
                                        symbol=symbol,
                                        exchange='binance',
                                        side=liq['side'].lower(),
                                        price=float(liq['price']),
                                        quantity=float(liq['origQty']),
                                        timestamp=int(liq['time']),
                                        liquidation_id=str(liq['orderId']),
                                        raw_data=liq
                                    )
                                )
                    except Exception as e:
                        self.logger.debug(f"Error getting Binance liquidations for {symbol}: {e}")
                
                await asyncio.sleep(60)  # Check every minute for Binance
                
        except Exception as e:
            self.logger.error(f"Error in Binance liquidation collection: {e}")
    
    async def _collect_okx_liquidations(self, exchange, symbols: List[str]):
        """Collect liquidation data from OKX."""
        try:
            # OKX provides liquidation data via WebSocket and REST
            while self.is_collecting:
                for symbol in symbols:
                    try:
                        # OKX liquidation orders endpoint
                        if hasattr(exchange, 'publicGetMarketLiquidationOrders'):
                            liquidations = await exchange.publicGetMarketLiquidationOrders({
                                'instId': symbol.replace('/', '-'),
                                'limit': 100
                            })
                            
                            for liq in liquidations.get('data', []):
                                await self._process_raw_liquidation(
                                    RawLiquidationData(
                                        symbol=symbol,
                                        exchange='okx',
                                        side=liq['side'].lower(),
                                        price=float(liq['bkPx']),
                                        quantity=float(liq['bkSz']),
                                        timestamp=int(liq['ts']),
                                        raw_data=liq
                                    )
                                )
                    except Exception as e:
                        self.logger.debug(f"Error getting OKX liquidations for {symbol}: {e}")
                
                await asyncio.sleep(45)  # Check every 45 seconds for OKX
                
        except Exception as e:
            self.logger.error(f"Error in OKX liquidation collection: {e}")
    
    async def _periodic_rest_collection(self, symbols: List[str]):
        """Periodic collection via REST APIs for exchanges without WebSocket support."""
        while self.is_collecting:
            try:
                # Collect from exchanges that don't have WebSocket liquidation feeds
                for exchange_id, exchange in self.exchange_manager.exchanges.items():
                    if not hasattr(exchange, 'subscribe_liquidations'):
                        # Use REST API collection methods
                        pass
                
                await asyncio.sleep(120)  # Every 2 minutes for REST collection
                
            except Exception as e:
                self.logger.error(f"Error in periodic REST collection: {e}")
    
    async def _handle_bybit_liquidation(self, message: Dict):
        """Handle incoming Bybit liquidation WebSocket message."""
        try:
            if not message or not isinstance(message, dict):
                self.logger.warning("Invalid liquidation message format received")
                return
                
            if not message.get('topic', '').startswith('allLiquidation'):
                return
                
            data = message.get('data', [])
            if not data:
                self.logger.debug("Empty liquidation data received")
                return
                
            # Handle array of liquidation events (official Bybit format)
            for liq in data:
                try:
                    # Validate required fields
                    if not liq.get('s'):
                        self.logger.warning(f"Liquidation data missing symbol: {liq}")
                        continue
                        
                    # Safely convert numeric fields
                    try:
                        price = float(liq.get('p', 0))
                        quantity = float(liq.get('v', 0))
                        timestamp = int(liq.get('T', 0))
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Invalid numeric data in liquidation: {liq}, error: {e}")
                        continue
                        
                    if price <= 0 or quantity <= 0:
                        self.logger.warning(f"Invalid price/quantity in liquidation: price={price}, quantity={quantity}")
                        continue
                        
                    await self._process_raw_liquidation(
                        RawLiquidationData(
                            symbol=liq.get('s'),
                            exchange='bybit',
                            side=liq.get('S', '').lower(),
                            price=price,
                            quantity=quantity,
                            timestamp=timestamp,
                            raw_data=liq
                        )
                    )
                except Exception as e:
                    self.logger.error(f"Error processing individual liquidation: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error handling Bybit liquidation message: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    async def _process_raw_liquidation(self, raw_liquidation: RawLiquidationData):
        """Process and store raw liquidation data."""
        try:
            # Validate input data
            if not raw_liquidation.symbol or not raw_liquidation.exchange:
                self.logger.warning(f"Invalid liquidation data: missing symbol or exchange: {raw_liquidation}")
                return
                
            if raw_liquidation.price <= 0 or raw_liquidation.quantity <= 0:
                self.logger.warning(f"Invalid liquidation amounts: price={raw_liquidation.price}, quantity={raw_liquidation.quantity}")
                return
            
            # Convert raw data to structured liquidation event
            try:
                liquidation_event = await self._convert_to_liquidation_event(raw_liquidation)
            except Exception as e:
                self.logger.error(f"Error converting liquidation event: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
                return
            
            # Store in memory for immediate access
            try:
                symbol_key = f"{raw_liquidation.symbol}:{raw_liquidation.exchange}"
                self.recent_liquidations[symbol_key].append(liquidation_event)
                
                # Limit memory usage by keeping only recent events
                max_events_per_symbol = 1000
                if len(self.recent_liquidations[symbol_key]) > max_events_per_symbol:
                    # Remove oldest events
                    self.recent_liquidations[symbol_key] = deque(
                        list(self.recent_liquidations[symbol_key])[-max_events_per_symbol:],
                        maxlen=max_events_per_symbol
                    )
                    
            except Exception as e:
                self.logger.error(f"Error storing liquidation in memory: {e}")
                # Don't return here - continue with other processing
            
            # Update statistics
            try:
                self.collection_stats['total_liquidations'] += 1
                self.collection_stats['liquidations_per_exchange'][raw_liquidation.exchange] += 1
                self.collection_stats['last_update'] = datetime.now(timezone.utc)
            except Exception as e:
                self.logger.error(f"Error updating liquidation statistics: {e}")
            
            # Store to database if callback provided
            if self.storage_callback:
                try:
                    await self.storage_callback(liquidation_event)
                except Exception as e:
                    self.logger.error(f"Error in storage callback: {e}")
                    # Don't fail the entire process if storage fails
            
            self.logger.debug(f"Processed liquidation: {raw_liquidation.symbol} - {raw_liquidation.side} - ${raw_liquidation.price}")
            
        except Exception as e:
            self.logger.error(f"Error processing liquidation data: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    async def _convert_to_liquidation_event(self, raw_liquidation: RawLiquidationData) -> LiquidationEvent:
        """Convert raw liquidation data to structured LiquidationEvent."""
        
        # Determine liquidation type based on side
        if raw_liquidation.side.lower() in ['sell', 'short']:
            liquidation_type = LiquidationType.LONG_LIQUIDATION
        elif raw_liquidation.side.lower() in ['buy', 'long']:
            liquidation_type = LiquidationType.SHORT_LIQUIDATION
        else:
            liquidation_type = LiquidationType.FLASH_CRASH
        
        # Calculate severity based on quantity and current market conditions
        severity = await self._calculate_liquidation_severity(raw_liquidation)
        
        # Calculate estimated USD value
        liquidated_amount_usd = raw_liquidation.price * raw_liquidation.quantity
        
        return LiquidationEvent(
            event_id=f"liq_{raw_liquidation.exchange}_{raw_liquidation.timestamp}",
            symbol=raw_liquidation.symbol,
            exchange=raw_liquidation.exchange,
            timestamp=datetime.fromtimestamp(raw_liquidation.timestamp / 1000),
            liquidation_type=liquidation_type,
            severity=severity,
            confidence_score=1.0,  # High confidence for real liquidation data
            trigger_price=raw_liquidation.price,
            price_impact=0.0,  # Would need market data to calculate
            volume_spike_ratio=1.0,  # Would need historical volume data
            liquidated_amount_usd=liquidated_amount_usd,
            bid_ask_spread_pct=0.0,  # Would need order book data
            order_book_imbalance=0.0,
            market_depth_impact=0.0,
            volatility_spike=1.0,  # Baseline volatility (no spike data from exchange feed)
            duration_seconds=0,  # Instantaneous for real liquidations
            suspected_triggers=['exchange_liquidation'],
            market_conditions={'data_source': 'exchange_feed'},
            # Optional fields - not available from raw exchange liquidation feed
            rsi=None,
            volume_weighted_price=None,
            funding_rate=None,
            open_interest_change=None,
            recovery_time_seconds=None
        )
    
    async def _calculate_liquidation_severity(self, raw_liquidation: RawLiquidationData) -> LiquidationSeverity:
        """Calculate severity of liquidation based on size and market conditions."""
        
        usd_value = raw_liquidation.price * raw_liquidation.quantity
        
        # Simple severity classification based on USD value
        if usd_value >= 1000000:  # $1M+
            return LiquidationSeverity.CRITICAL
        elif usd_value >= 100000:  # $100K+
            return LiquidationSeverity.HIGH
        elif usd_value >= 10000:   # $10K+
            return LiquidationSeverity.MEDIUM
        else:
            return LiquidationSeverity.LOW
    
    def get_recent_liquidations(self, symbol: str, exchange: str = None, minutes: int = 60) -> List[LiquidationEvent]:
        """Get recent liquidations for a symbol from memory cache."""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_events = []
        
        if exchange:
            symbol_key = f"{symbol}:{exchange}"
            if symbol_key in self.recent_liquidations:
                events = [e for e in self.recent_liquidations[symbol_key] 
                         if e.timestamp >= cutoff_time]
                recent_events.extend(events)
        else:
            # Search across all exchanges for this symbol
            for symbol_key, events in self.recent_liquidations.items():
                if symbol_key.startswith(f"{symbol}:"):
                    filtered_events = [e for e in events if e.timestamp >= cutoff_time]
                    recent_events.extend(filtered_events)
        
        return sorted(recent_events, key=lambda x: x.timestamp, reverse=True)
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics."""
        return {
            **self.collection_stats,
            'active_symbols': len(self.subscribed_symbols),
            'cached_liquidations': sum(len(deque_) for deque_ in self.recent_liquidations.values()),
            'exchanges_connected': len(self.websocket_connections)
        } 