import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class IndicatorUtils:
    @staticmethod
    def normalize_series(series: pd.Series, window: int = 100, min_val: float = None, max_val: float = None) -> pd.Series:
        """Standardized indicator normalization to 0-100 scale.
        
        Args:
            series: Series to normalize
            window: Rolling window size for dynamic normalization
            min_val: Fixed minimum value for normalization (optional)
            max_val: Fixed maximum value for normalization (optional)
        """
        if series.empty or series.isnull().all():
            return pd.Series(50.0, index=series.index)
        
        try:
            if min_val is not None and max_val is not None:
                # Fixed range normalization
                range_val = max_val - min_val
                if range_val == 0:
                    range_val = 1
                normalized = ((series - min_val) / range_val * 100)
            else:
                # Rolling window normalization
                min_series = series.rolling(window=window, min_periods=1).min()
                max_series = series.rolling(window=window, min_periods=1).max()
                
                # Avoid division by zero
                range_val = (max_series - min_series).replace(0, 1)
                
                # Normalize to 0-100 scale
                normalized = ((series - min_series) / range_val * 100)
            
            # Ensure values are within bounds
            normalized = normalized.clip(1, 100)
            
            return normalized.fillna(50.0)
            
        except Exception as e:
            logger.error(f"Error normalizing series: {str(e)}")
            return pd.Series(50.0, index=series.index)
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
        """Validate DataFrame has required columns and data."""
        if df is None or df.empty:
            logger.warning("DataFrame is empty or None")
            return False
            
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
            return False
            
        return True
    
    @staticmethod
    def calculate_historical_average(series: pd.Series, window: int = 20) -> float:
        """Calculate historical average with validation."""
        try:
            if series.empty:
                return 0.0
            return float(series.rolling(window=window, min_periods=1).mean().iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating historical average: {str(e)}")
            return 0.0
    
    @staticmethod
    def prepare_ohlcv_data(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Prepare OHLCV data with type conversion and validation."""
        try:
            ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
            if not IndicatorUtils.validate_dataframe(df, ohlcv_columns):
                return {}
                
            return {
                col: pd.to_numeric(df[col], errors='coerce')
                for col in ohlcv_columns
            }
        except Exception as e:
            logger.error(f"Error preparing OHLCV data: {str(e)}")
            return {} 
    
    @staticmethod
    def normalize_value(value: float, min_val: float, max_val: float) -> float:
        """Normalize a single value to 0-1 range."""
        try:
            if min_val == max_val:
                return 0.5
            return (value - min_val) / (max_val - min_val)
        except Exception as e:
            logger.error(f"Error normalizing value: {str(e)}")
            return 0.5 