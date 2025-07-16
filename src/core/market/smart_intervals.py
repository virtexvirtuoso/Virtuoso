import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import statistics

logger = logging.getLogger(__name__)

@dataclass
class MarketActivity:
    """Market activity metrics for smart interval calculation."""
    volume_ratio: float = 1.0  # Current vs average volume
    volatility: float = 0.0    # Price volatility (standard deviation)
    active_symbols: int = 0    # Number of actively traded symbols
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class SmartIntervalsManager:
    """
    Manages dynamic update intervals based on market activity.
    
    Features:
    - Adjusts intervals based on volume and volatility
    - Reduces intervals during high activity (30s)
    - Increases intervals during low activity (60s)
    - Configurable thresholds and limits
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the smart intervals manager."""
        self.config = config
        self.logger = logger
        
        # Smart intervals configuration
        intervals_config = config.get('smart_intervals', {})
        self.enabled = intervals_config.get('enabled', True)
        
        # Interval limits (seconds)
        self.min_interval = intervals_config.get('min_interval', 30)
        self.max_interval = intervals_config.get('max_interval', 60)
        self.default_interval = intervals_config.get('default_interval', 45)
        
        # Activity thresholds
        thresholds = intervals_config.get('thresholds', {})
        self.high_volume_threshold = thresholds.get('high_volume_ratio', 1.5)  # 50% above average
        self.high_volatility_threshold = thresholds.get('high_volatility', 0.02)  # 2% volatility
        self.low_volume_threshold = thresholds.get('low_volume_ratio', 0.7)  # 30% below average
        self.low_volatility_threshold = thresholds.get('low_volatility', 0.005)  # 0.5% volatility
        
        # Activity tracking
        self.activity_history: List[MarketActivity] = []
        self.history_limit = intervals_config.get('history_limit', 100)
        self.current_interval = self.default_interval
        self.last_update = 0
        
        # Statistics
        self.stats = {
            'total_adjustments': 0,
            'high_activity_periods': 0,
            'low_activity_periods': 0,
            'average_interval': self.default_interval
        }
        
        self.logger.info(f"SmartIntervalsManager initialized: min={self.min_interval}s, max={self.max_interval}s, default={self.default_interval}s")
    
    def update_market_activity(self, activity: MarketActivity) -> None:
        """Update market activity metrics."""
        if not self.enabled:
            return
            
        # Add to history
        self.activity_history.append(activity)
        
        # Trim history to limit
        if len(self.activity_history) > self.history_limit:
            self.activity_history = self.activity_history[-self.history_limit:]
        
        # Calculate new interval
        new_interval = self._calculate_optimal_interval(activity)
        
        if new_interval != self.current_interval:
            self.logger.debug(f"Adjusting interval from {self.current_interval}s to {new_interval}s "
                            f"(volume_ratio={activity.volume_ratio:.2f}, volatility={activity.volatility:.4f})")
            self.current_interval = new_interval
            self.stats['total_adjustments'] += 1
        
        self.last_update = time.time()
    
    def _calculate_optimal_interval(self, activity: MarketActivity) -> int:
        """Calculate optimal interval based on current market activity."""
        if not self.enabled:
            return self.default_interval
        
        # Determine activity level
        is_high_activity = (
            activity.volume_ratio >= self.high_volume_threshold or
            activity.volatility >= self.high_volatility_threshold
        )
        
        is_low_activity = (
            activity.volume_ratio <= self.low_volume_threshold and
            activity.volatility <= self.low_volatility_threshold
        )
        
        if is_high_activity:
            # High activity: use minimum interval
            self.stats['high_activity_periods'] += 1
            return self.min_interval
        elif is_low_activity:
            # Low activity: use maximum interval
            self.stats['low_activity_periods'] += 1
            return self.max_interval
        else:
            # Medium activity: use default interval
            return self.default_interval
    
    def get_current_interval(self, component: str = 'default') -> int:
        """Get current interval for a specific component."""
        if not self.enabled:
            return self.default_interval
        
        # Component-specific adjustments
        component_multipliers = {
            'ticker': 1.0,
            'orderbook': 1.0,
            'trades': 1.2,  # Slightly longer for trades
            'ohlcv': 2.0,   # Much longer for OHLCV data
            'analysis': 1.5  # Longer for analysis
        }
        
        multiplier = component_multipliers.get(component, 1.0)
        adjusted_interval = int(self.current_interval * multiplier)
        
        # Ensure within bounds
        return max(self.min_interval, min(self.max_interval * 2, adjusted_interval))
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of current market activity."""
        if not self.activity_history:
            return {
                'status': 'no_data',
                'current_interval': self.current_interval,
                'activity_level': 'unknown'
            }
        
        recent_activity = self.activity_history[-10:]  # Last 10 readings
        
        avg_volume_ratio = statistics.mean(a.volume_ratio for a in recent_activity)
        avg_volatility = statistics.mean(a.volatility for a in recent_activity)
        
        # Determine activity level
        if avg_volume_ratio >= self.high_volume_threshold or avg_volatility >= self.high_volatility_threshold:
            activity_level = 'high'
        elif avg_volume_ratio <= self.low_volume_threshold and avg_volatility <= self.low_volatility_threshold:
            activity_level = 'low'
        else:
            activity_level = 'medium'
        
        return {
            'status': 'active',
            'current_interval': self.current_interval,
            'activity_level': activity_level,
            'avg_volume_ratio': round(avg_volume_ratio, 2),
            'avg_volatility': round(avg_volatility, 4),
            'active_symbols': recent_activity[-1].active_symbols if recent_activity else 0,
            'last_update': datetime.fromtimestamp(self.last_update).isoformat() if self.last_update else None,
            'stats': self.stats.copy()
        }
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            'total_adjustments': 0,
            'high_activity_periods': 0,
            'low_activity_periods': 0,
            'average_interval': self.current_interval
        }
        self.logger.info("Smart intervals statistics reset")
    
    async def activity_monitor_loop(self, exchange_manager, symbols: List[str]) -> None:
        """Background loop to monitor market activity and adjust intervals."""
        if not self.enabled:
            return
        
        self.logger.info("Starting smart intervals activity monitor")
        
        while True:
            try:
                # Calculate current market activity
                activity = await self._calculate_market_activity(exchange_manager, symbols)
                
                # Update intervals based on activity
                self.update_market_activity(activity)
                
                # Sleep for monitoring interval
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in activity monitor loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _calculate_market_activity(self, exchange_manager, symbols: List[str]) -> MarketActivity:
        """Calculate current market activity metrics."""
        try:
            volume_ratios = []
            volatilities = []
            active_count = 0
            
            # Sample a subset of symbols to avoid overloading
            sample_symbols = symbols[:10] if len(symbols) > 10 else symbols
            
            for symbol in sample_symbols:
                try:
                    # Get recent market data
                    market_data = await exchange_manager.get_market_data(symbol)
                    
                    if not market_data or 'bybit' not in market_data:
                        continue
                    
                    ticker = market_data['bybit'].get('ticker', {})
                    if not ticker:
                        continue
                    
                    # Calculate volume ratio (current vs 24h average)
                    current_volume = float(ticker.get('volume', 0))
                    if current_volume > 0:
                        # Use a simple heuristic: assume current hour volume * 24 vs actual 24h volume
                        volume_ratios.append(min(current_volume / max(current_volume / 24, 1), 5.0))  # Cap at 5x
                        active_count += 1
                    
                    # Calculate volatility (high-low range as percentage of price)
                    high = float(ticker.get('high', 0))
                    low = float(ticker.get('low', 0))
                    price = float(ticker.get('last', 0))
                    
                    if price > 0 and high > low:
                        volatility = (high - low) / price
                        volatilities.append(volatility)
                
                except Exception as e:
                    self.logger.debug(f"Error calculating activity for {symbol}: {e}")
                    continue
            
            # Calculate average metrics
            avg_volume_ratio = statistics.mean(volume_ratios) if volume_ratios else 1.0
            avg_volatility = statistics.mean(volatilities) if volatilities else 0.01
            
            return MarketActivity(
                volume_ratio=avg_volume_ratio,
                volatility=avg_volatility,
                active_symbols=active_count
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating market activity: {e}")
            return MarketActivity()  # Return default activity 