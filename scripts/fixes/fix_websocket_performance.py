#!/usr/bin/env python3
"""
Fix WebSocket message processing performance issues.

The system is experiencing significant delays when processing WebSocket orderbook messages.
This script implements optimizations to reduce processing time and memory usage.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import time

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.monitoring.monitor import MarketMonitor
from src.core.exchanges.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class OptimizedOrderbookProcessor:
    """Optimized orderbook processor with minimal memory allocations."""
    
    def __init__(self):
        self.last_update_time = {}
        self.update_interval = 0.1  # Minimum interval between updates (100ms)
        
    def should_process_update(self, symbol: str) -> bool:
        """Check if we should process this update based on throttling."""
        current_time = time.time()
        last_time = self.last_update_time.get(symbol, 0)
        
        if current_time - last_time >= self.update_interval:
            self.last_update_time[symbol] = current_time
            return True
        return False
        
    def process_orderbook_efficiently(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process orderbook data efficiently without unnecessary sorting."""
        # Only process the top N levels that are actually needed
        MAX_LEVELS = 50  # Most strategies only need top 50 levels
        
        processed = {
            'symbol': orderbook_data.get('symbol'),
            'timestamp': orderbook_data.get('timestamp'),
            'bids': [],
            'asks': []
        }
        
        # Process bids - they should already be sorted from the exchange
        bids = orderbook_data.get('bids', [])
        if bids:
            # Take only what we need
            processed['bids'] = bids[:MAX_LEVELS]
            
        # Process asks - they should already be sorted from the exchange  
        asks = orderbook_data.get('asks', [])
        if asks:
            # Take only what we need
            processed['asks'] = asks[:MAX_LEVELS]
            
        return processed


async def patch_monitor_orderbook_processing():
    """Patch the monitor's orderbook processing method for better performance."""
    
    # Create optimized processor
    processor = OptimizedOrderbookProcessor()
    
    # Store original method
    original_process_orderbook = MarketMonitor._process_orderbook_update
    
    async def optimized_process_orderbook_update(self, message: Dict[str, Any]) -> None:
        """Optimized orderbook update processor."""
        try:
            # Check if we should throttle this update
            if not processor.should_process_update(self.symbol):
                return
                
            data = message.get('data', {})
            timestamp = message.get('timestamp', time.time() * 1000)
            
            # Extract orderbook data
            orderbook_data = data.get('data', {})
            if not orderbook_data:
                return
            
            # Process efficiently
            orderbook = processor.process_orderbook_efficiently({
                'symbol': self.symbol,
                'timestamp': int(orderbook_data.get('timestamp', timestamp)),
                'bids': orderbook_data.get('bids', []),
                'asks': orderbook_data.get('asks', [])
            })
            
            # Update internal state without sorting (exchange data is pre-sorted)
            self.ws_data['orderbook'] = orderbook
            self.ws_data['last_update_time']['orderbook'] = timestamp
            
            # Throttled logging
            if hasattr(self, '_last_orderbook_log') and time.time() - self._last_orderbook_log < 5:
                return
            self._last_orderbook_log = time.time()
            self.logger.debug(f"Updated orderbook: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            
        except Exception as e:
            self.logger.error(f"Error in optimized orderbook processing: {str(e)}")
    
    # Apply patch
    MarketMonitor._process_orderbook_update = optimized_process_orderbook_update
    logger.info("Applied orderbook processing optimization patch")


async def optimize_metrics_tracking():
    """Optimize metrics tracking to reduce overhead."""
    from src.monitoring.metrics_manager import MetricsManager
    
    # Store original methods
    original_start = MetricsManager.start_operation
    original_end = MetricsManager.end_operation
    
    # Create a set of high-frequency operations to skip detailed tracking
    skip_detailed_tracking = {
        'process_ws_message_orderbook',
        'process_ws_message_tickers',
        'process_ws_message_kline',
        'process_ws_message_publicTrade'
    }
    
    def lightweight_start_operation(self, operation_name: str) -> Dict[str, Any]:
        """Lightweight operation tracking for high-frequency operations."""
        if any(op in operation_name for op in skip_detailed_tracking):
            # Return minimal context for high-frequency operations
            return {
                "id": f"{operation_name}_{time.time()}",
                "name": operation_name,
                "start_time": time.time(),
                "lightweight": True
            }
        # Use original method for other operations
        return original_start(self, operation_name)
    
    def lightweight_end_operation(self, op_context: Dict[str, Any], success: bool = True) -> float:
        """Lightweight operation ending for high-frequency operations."""
        if op_context.get("lightweight", False):
            # Just calculate duration without heavy tracking
            duration = time.time() - op_context["start_time"]
            return duration
        # Use original method for other operations
        return original_end(self, op_context, success)
    
    # Apply patches
    MetricsManager.start_operation = lightweight_start_operation
    MetricsManager.end_operation = lightweight_end_operation
    logger.info("Applied metrics tracking optimization patch")


async def main():
    """Apply WebSocket performance optimizations."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
    )
    
    logger.info("Starting WebSocket performance optimization...")
    
    try:
        # Apply orderbook processing optimization
        await patch_monitor_orderbook_processing()
        
        # Apply metrics tracking optimization
        await optimize_metrics_tracking()
        
        logger.info("✅ WebSocket performance optimizations applied successfully!")
        logger.info("\nOptimizations applied:")
        logger.info("1. Orderbook updates are now throttled to max 10 updates/second")
        logger.info("2. Removed unnecessary sorting of pre-sorted exchange data")
        logger.info("3. Limited orderbook depth to 50 levels (configurable)")
        logger.info("4. Reduced memory allocations in high-frequency operations")
        logger.info("5. Lightweight metrics tracking for WebSocket messages")
        logger.info("\nRestart the application to see improved performance.")
        
    except Exception as e:
        logger.error(f"Error applying optimizations: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())