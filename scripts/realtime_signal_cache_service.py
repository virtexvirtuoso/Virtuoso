#!/usr/bin/env python3
"""
Real-time Signal Cache Service
Monitors for new signals/alerts and immediately updates the cache for dashboard display
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import deque

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import memcache client
try:
    from pymemcache.client.base import Client
    from pymemcache import serde
except ImportError:
    logger.error("pymemcache not installed. Run: pip install pymemcache")
    exit(1)

class SignalCacheService:
    """Service to maintain real-time signals in cache"""
    
    def __init__(self, cache_host: str = "localhost", cache_port: int = 11211):
        self.cache = Client((cache_host, cache_port), serde=serde.pickle_serde)
        self.logger = logging.getLogger(__name__)
        self.signals_buffer = deque(maxlen=100)  # Keep last 100 signals
        self.last_update = time.time()
        
    def add_signal(self, signal: Dict) -> None:
        """Add a new signal to the buffer"""
        # Ensure signal has required fields
        if 'timestamp' not in signal:
            signal['timestamp'] = time.time()
        if 'symbol' not in signal:
            signal['symbol'] = 'UNKNOWN'
            
        self.signals_buffer.append(signal)
        self.logger.info(f"Added signal for {signal.get('symbol')}: {signal.get('direction', 'neutral')}")
        
    def update_cache(self) -> bool:
        """Update cache with current signals"""
        try:
            # Convert buffer to list (most recent first)
            signals = list(reversed(self.signals_buffer))
            
            # Prepare cache data
            cache_data = {
                'signals': signals[:50],  # Limit to 50 most recent
                'count': len(signals),
                'timestamp': int(time.time()),
                'source': 'realtime_service'
            }
            
            # Store in cache with 5 minute TTL
            self.cache.set('analysis:signals', cache_data, expire=300)
            
            # Also update individual symbol signals
            symbol_signals = {}
            for signal in signals:
                symbol = signal.get('symbol')
                if symbol and symbol != 'UNKNOWN':
                    if symbol not in symbol_signals:
                        symbol_signals[symbol] = signal
            
            # Store top symbol signals
            for symbol, signal in list(symbol_signals.items())[:20]:
                key = f"signal:{symbol}"
                self.cache.set(key, signal, expire=300)
            
            self.last_update = time.time()
            self.logger.debug(f"Updated cache with {len(signals)} signals")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating cache: {e}")
            return False
    
    def generate_demo_signals(self) -> List[Dict]:
        """Generate demo signals for testing"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
        signals = []
        
        for i, symbol in enumerate(symbols):
            score = 70 - (i * 10)  # Descending scores
            direction = 'buy' if score > 50 else 'sell'
            strength = 'strong' if abs(score - 50) > 20 else 'medium'
            
            signal = {
                'symbol': symbol,
                'type': 'confluence',
                'direction': direction,
                'strength': strength,
                'score': score,
                'timestamp': time.time() - (i * 60),  # Stagger timestamps
                'message': f"{direction.upper()} signal for {symbol} - Confluence score: {score}",
                'price': 50000 - (i * 5000),  # Mock prices
                'components': {
                    'momentum': score + 5,
                    'volume': score - 5,
                    'orderflow': score,
                    'sentiment': score + 2
                }
            }
            signals.append(signal)
            
        return signals
    
    async def monitor_alerts(self):
        """Monitor for new alerts (placeholder for integration)"""
        # This would integrate with your alert system
        # For now, we'll generate demo signals periodically
        
        while True:
            try:
                # Generate demo signals every 30 seconds
                await asyncio.sleep(30)
                
                # Add a new demo signal
                symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'MATIC/USDT']
                import random
                
                symbol = random.choice(symbols)
                score = random.randint(20, 80)
                direction = 'buy' if score > 50 else 'sell'
                
                signal = {
                    'symbol': symbol,
                    'type': 'realtime',
                    'direction': direction,
                    'score': score,
                    'timestamp': time.time(),
                    'message': f"New {direction} signal for {symbol}",
                    'strength': 'strong' if abs(score - 50) > 20 else 'medium'
                }
                
                self.add_signal(signal)
                self.update_cache()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)
    
    async def run(self, demo_mode: bool = False):
        """Run the service"""
        self.logger.info("Starting Signal Cache Service")
        
        if demo_mode:
            # Initialize with demo signals
            self.logger.info("Running in demo mode - generating sample signals")
            demo_signals = self.generate_demo_signals()
            for signal in demo_signals:
                self.add_signal(signal)
            self.update_cache()
            self.logger.info(f"Initialized with {len(demo_signals)} demo signals")
        
        # Start monitoring task
        monitor_task = asyncio.create_task(self.monitor_alerts())
        
        # Periodic cache update task
        try:
            while True:
                await asyncio.sleep(10)  # Update cache every 10 seconds
                if time.time() - self.last_update > 10:
                    self.update_cache()
        except KeyboardInterrupt:
            self.logger.info("Service interrupted")
        finally:
            monitor_task.cancel()
            await monitor_task

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time Signal Cache Service')
    parser.add_argument('--demo', action='store_true', 
                       help='Run in demo mode with sample signals')
    parser.add_argument('--cache-host', default='localhost',
                       help='Memcached host')
    parser.add_argument('--cache-port', type=int, default=11211,
                       help='Memcached port')
    
    args = parser.parse_args()
    
    # Create service
    service = SignalCacheService(
        cache_host=args.cache_host,
        cache_port=args.cache_port
    )
    
    # Run service
    try:
        asyncio.run(service.run(demo_mode=args.demo))
    except KeyboardInterrupt:
        logger.info("Service stopped")

if __name__ == "__main__":
    main()