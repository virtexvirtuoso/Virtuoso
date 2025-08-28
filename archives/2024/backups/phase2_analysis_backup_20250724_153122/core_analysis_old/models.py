from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

@dataclass
class AnalysisPayload:
    """Standardized data structure for all analysis components."""
    
    # Core market data
    symbol: str
    timestamp: int
    
    # OHLCV data for different timeframes
    ohlcv: Dict[str, pd.DataFrame]  # Keys: 'base', 'ltf', 'mtf', 'htf'
    
    # Order book data
    orderbook: Dict[str, List[List[float]]]  # {bids: [[price, size], ...], asks: [...]}
    
    # Trade data
    trades: List[Dict[str, float]]  # [{price, size, side, timestamp}, ...]
    
    # Pre-calculated features
    derived_features: Dict[str, pd.DataFrame] = None
    
    def __post_init__(self):
        """Validate and initialize derived features."""
        self.derived_features = self.derived_features or {}
        self._validate_data()
    
    def _validate_data(self) -> None:
        """Validate the data structure."""
        # Validate OHLCV
        required_timeframes = ['base', 'ltf', 'mtf', 'htf']
        for tf in required_timeframes:
            if tf not in self.ohlcv:
                raise ValueError(f"Missing required timeframe: {tf}")
            df = self.ohlcv[tf]
            if not isinstance(df, pd.DataFrame):
                raise ValueError(f"Invalid OHLCV data type for {tf}")
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing columns in {tf}: {missing_cols}")
        
        # Validate orderbook
        required_ob_fields = ['bids', 'asks']
        for field in required_ob_fields:
            if field not in self.orderbook:
                raise ValueError(f"Missing orderbook field: {field}")
            if not isinstance(self.orderbook[field], list):
                raise ValueError(f"Invalid orderbook {field} type")
            if len(self.orderbook[field]) < 10:  # Minimum depth
                raise ValueError(f"Insufficient {field} depth")
        
        # Validate trades
        if not self.trades:
            raise ValueError("Empty trades list")
        required_trade_fields = ['price', 'size', 'side', 'timestamp']
        sample_trade = self.trades[0]
        missing_fields = [f for f in required_trade_fields if f not in sample_trade]
        if missing_fields:
            raise ValueError(f"Missing trade fields: {missing_fields}")
    
    def to_indicator_format(self, indicator_type: str) -> Dict:
        """Convert data to format expected by specific indicator type."""
        base_data = {
            'symbol': self.symbol,
            'timestamp': self.timestamp
        }
        
        if indicator_type == 'technical':
            return {
                **base_data,
                'ohlcv': self.ohlcv,
                'derived_features': self.derived_features.get('technical', {})
            }
        
        elif indicator_type == 'orderflow':
            return {
                **base_data,
                'trades': self.trades,
                'orderbook': self.orderbook,
                'derived_features': self.derived_features.get('orderflow', {})
            }
        
        elif indicator_type == 'orderbook':
            return {
                **base_data,
                'orderbook': self.orderbook,
                'trades': self.trades[-100:],  # Last 100 trades for context
                'derived_features': self.derived_features.get('orderbook', {})
            }
        
        elif indicator_type == 'price_structure':
            return {
                **base_data,
                'ohlcv': self.ohlcv,
                'trades': self.trades,
                'derived_features': self.derived_features.get('price_structure', {})
            }
        
        else:
            raise ValueError(f"Unsupported indicator type: {indicator_type}")
    
    def add_derived_feature(self, indicator_type: str, feature_name: str, data: pd.DataFrame) -> None:
        """Add a derived feature for a specific indicator type."""
        if indicator_type not in self.derived_features:
            self.derived_features[indicator_type] = {}
        self.derived_features[indicator_type][feature_name] = data
    
    def get_timeframe_data(self, timeframe: str) -> pd.DataFrame:
        """Get OHLCV data for a specific timeframe."""
        if timeframe not in self.ohlcv:
            raise ValueError(f"Invalid timeframe: {timeframe}")
        return self.ohlcv[timeframe]
    
    def get_recent_trades(self, n: int = 100) -> List[Dict[str, float]]:
        """Get the n most recent trades."""
        return sorted(self.trades, key=lambda x: x['timestamp'])[-n:]
    
    def get_orderbook_imbalance(self) -> float:
        """Calculate order book imbalance."""
        bid_volume = sum(level[1] for level in self.orderbook['bids'])
        ask_volume = sum(level[1] for level in self.orderbook['asks'])
        total_volume = bid_volume + ask_volume
        return (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0.0 