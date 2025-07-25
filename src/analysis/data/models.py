"""Analysis data models."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

@dataclass
class AnalysisResult:
    """Container for analysis results."""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

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
    
    def get_timeframe_data(self, timeframe: str) -> pd.DataFrame:
        """Get OHLCV data for a specific timeframe."""
        if timeframe not in self.ohlcv:
            raise KeyError(f"Timeframe {timeframe} not found")
        return self.ohlcv[timeframe]
    
    def has_sufficient_data(self, min_periods: int = 50) -> bool:
        """Check if there's sufficient data for analysis."""
        return all(
            len(df) >= min_periods 
            for df in self.ohlcv.values()
        )