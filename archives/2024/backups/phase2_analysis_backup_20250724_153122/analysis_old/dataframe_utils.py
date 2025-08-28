"""DataFrame optimization utilities."""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

class DataFrameOptimizer:
    """Optimizes DataFrame memory usage and performance."""
    
    INT_TYPES = [np.int8, np.int16, np.int32, np.int64]
    FLOAT_TYPES = [np.float32, np.float64]
    
    @staticmethod
    def optimize_numeric_types(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize numeric types to minimize memory usage."""
        result = df.copy()
        
        for column in result.select_dtypes(include=['int']).columns:
            column_min = result[column].min()
            column_max = result[column].max()
            
            # Find the smallest int type that can hold the data
            for dtype in DataFrameOptimizer.INT_TYPES:
                type_info = np.iinfo(dtype)
                if column_min >= type_info.min and column_max <= type_info.max:
                    result[column] = result[column].astype(dtype)
                    break
        
        for column in result.select_dtypes(include=['float']).columns:
            # Check if float32 precision is sufficient
            float64_data = result[column].values
            float32_data = float64_data.astype(np.float32)
            
            if np.allclose(float64_data, float32_data, rtol=1e-7):
                result[column] = result[column].astype(np.float32)
        
        return result
    
    @staticmethod
    def efficient_resample(df: pd.DataFrame,
                          freq: str,
                          agg_funcs: Dict[str, str]) -> pd.DataFrame:
        """Efficiently resample time series data."""
        try:
            # Ensure index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError("DataFrame index must be DatetimeIndex")
            
            # Group data for resampling
            resampler = df.resample(freq)
            
            # Apply aggregation functions efficiently
            result = pd.DataFrame()
            for column, func in agg_funcs.items():
                if column in df.columns:
                    if func == 'first':
                        result[column] = resampler[column].first()
                    elif func == 'last':
                        result[column] = resampler[column].last()
                    elif func == 'mean':
                        result[column] = resampler[column].mean()
                    elif func == 'sum':
                        result[column] = resampler[column].sum()
                    else:
                        result[column] = getattr(resampler[column], func)()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in efficient_resample: {e}")
            raise
    
    @staticmethod
    def calculate_metrics(df: pd.DataFrame,
                         windows: List[int] = [20, 50, 200]) -> pd.DataFrame:
        """Calculate technical metrics efficiently."""
        result = df.copy()
        
        # Pre-calculate common values
        result['returns'] = result['close'].pct_change()
        result['log_returns'] = np.log(result['close']).diff()
        
        # Vectorized calculations for all windows
        for window in windows:
            # Moving averages
            result[f'ma_{window}'] = result['close'].rolling(
                window=window, min_periods=1
            ).mean()
            
            # Volatility
            result[f'vol_{window}'] = result['returns'].rolling(
                window=window, min_periods=1
            ).std() * np.sqrt(252)
            
            # Volume metrics
            result[f'volume_ma_{window}'] = result['volume'].rolling(
                window=window, min_periods=1
            ).mean()
            
            # Momentum
            result[f'momentum_{window}'] = result['returns'].rolling(
                window=window, min_periods=1
            ).mean() * np.sqrt(252)
        
        return result
    
    @staticmethod
    @lru_cache(maxsize=100)
    def get_optimal_batch_size(row_count: int) -> int:
        """Calculate optimal batch size based on data size."""
        if row_count < 1000:
            return row_count
        elif row_count < 10000:
            return 1000
        elif row_count < 100000:
            return 5000
        else:
            return 10000
    
    @staticmethod
    def process_in_batches(df: pd.DataFrame,
                          func: callable,
                          batch_size: Optional[int] = None) -> pd.DataFrame:
        """Process large DataFrames in batches."""
        if batch_size is None:
            batch_size = DataFrameOptimizer.get_optimal_batch_size(len(df))
        
        result_frames = []
        for start_idx in range(0, len(df), batch_size):
            end_idx = min(start_idx + batch_size, len(df))
            batch = df.iloc[start_idx:end_idx]
            
            try:
                processed_batch = func(batch)
                result_frames.append(processed_batch)
            except Exception as e:
                logger.error(f"Error processing batch {start_idx}-{end_idx}: {e}")
                raise
        
        return pd.concat(result_frames) if result_frames else pd.DataFrame()
    
    @staticmethod
    def analyze_volume_profile(df: pd.DataFrame,
                             price_col: str = 'close',
                             volume_col: str = 'volume',
                             n_bins: int = 50) -> Tuple[pd.Series, Dict[str, float]]:
        """Analyze volume profile efficiently."""
        try:
            # Validate inputs
            if not all(col in df.columns for col in [price_col, volume_col]):
                raise ValueError(f"Required columns {price_col} and {volume_col} not found")
            
            # Calculate price bins
            price_min = df[price_col].min()
            price_max = df[price_col].max()
            
            if price_min == price_max:
                raise ValueError("Price range is zero")
            
            bin_edges = np.linspace(price_min, price_max, n_bins + 1)
            
            # Vectorized volume profile calculation
            indices = np.digitize(df[price_col], bin_edges) - 1
            volume_profile = pd.Series(
                np.bincount(indices, weights=df[volume_col], minlength=n_bins),
                index=range(n_bins)
            )
            
            # Calculate metrics
            total_volume = df[volume_col].sum()
            if total_volume == 0:
                raise ValueError("Total volume is zero")
            
            vwap = (df[price_col] * df[volume_col]).sum() / total_volume
            
            metrics = {
                'total_volume': total_volume,
                'vwap': vwap,
                'price_range': price_max - price_min,
                'volume_concentration': volume_profile.max() / total_volume,
                'price_levels': np.count_nonzero(volume_profile),
                'volume_skew': float(pd.Series(df[volume_col]).skew()),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return volume_profile, metrics
            
        except Exception as e:
            logger.error(f"Error in volume profile analysis: {str(e)}")
            raise 