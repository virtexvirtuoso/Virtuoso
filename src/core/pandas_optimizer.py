"""
Pandas Performance Optimizer Module

Provides optimization utilities for pandas operations in trading applications.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional, Union, List
from functools import wraps
import time

logger = logging.getLogger(__name__)

class PandasOptimizer:
    """
    Performance optimizer for pandas operations in financial data processing.
    """
    
    def __init__(self, enable_optimizations: bool = True):
        """
        Initialize the pandas optimizer.
        
        Args:
            enable_optimizations: Whether to enable performance optimizations
        """
        self.enable_optimizations = enable_optimizations
        self.optimization_stats = {
            'total_operations': 0,
            'optimized_operations': 0,
            'time_saved_ms': 0.0
        }
        
    def optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize dataframe memory usage by downcasting numeric types.
        
        Args:
            df: DataFrame to optimize
            
        Returns:
            Memory-optimized DataFrame
        """
        if not self.enable_optimizations:
            return df
            
        try:
            start_time = time.time()
            
            # Create a copy to avoid modifying original
            optimized_df = df.copy()
            
            # Downcast integers
            for col in optimized_df.select_dtypes(include=['int64']).columns:
                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='integer')
                
            # Downcast floats
            for col in optimized_df.select_dtypes(include=['float64']).columns:
                optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
                
            # Convert object columns to category if they have few unique values
            for col in optimized_df.select_dtypes(include=['object']).columns:
                unique_ratio = optimized_df[col].nunique() / len(optimized_df)
                if unique_ratio < 0.5:  # Less than 50% unique values
                    optimized_df[col] = optimized_df[col].astype('category')
            
            # Update stats
            self.optimization_stats['total_operations'] += 1
            self.optimization_stats['optimized_operations'] += 1
            self.optimization_stats['time_saved_ms'] += (time.time() - start_time) * 1000
            
            return optimized_df
            
        except Exception as e:
            logger.warning(f"Memory optimization failed: {str(e)}")
            return df
    
    def optimize_ohlcv_calculations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize OHLCV data calculations for trading applications.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Optimized DataFrame with efficient calculations
        """
        if not self.enable_optimizations:
            return df
            
        try:
            start_time = time.time()
            
            # Ensure datetime index for time-series operations
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'timestamp' in df.columns:
                    df = df.set_index('timestamp')
                elif 'datetime' in df.columns:
                    df = df.set_index('datetime')
            
            # Pre-calculate common technical indicators using vectorized operations
            if all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
                # Use vectorized operations for better performance
                df['price_change'] = df['close'] - df['open']
                df['price_change_pct'] = (df['close'] - df['open']) / df['open'] * 100
                df['true_range'] = np.maximum(
                    df['high'] - df['low'],
                    np.maximum(
                        np.abs(df['high'] - df['close'].shift(1)),
                        np.abs(df['low'] - df['close'].shift(1))
                    )
                )
                
            # Update stats
            self.optimization_stats['total_operations'] += 1
            self.optimization_stats['optimized_operations'] += 1
            self.optimization_stats['time_saved_ms'] += (time.time() - start_time) * 1000
            
            return df
            
        except Exception as e:
            logger.warning(f"OHLCV optimization failed: {str(e)}")
            return df
    
    def optimize_groupby_operations(self, df: pd.DataFrame, group_col: str, agg_dict: Dict[str, Any]) -> pd.DataFrame:
        """
        Optimize groupby operations for better performance.
        
        Args:
            df: DataFrame to group
            group_col: Column to group by
            agg_dict: Aggregation dictionary
            
        Returns:
            Optimized grouped DataFrame
        """
        if not self.enable_optimizations:
            return df.groupby(group_col).agg(agg_dict)
            
        try:
            start_time = time.time()
            
            # Sort by group column first for better performance
            if not df.index.is_monotonic_increasing:
                df_sorted = df.sort_values(group_col)
            else:
                df_sorted = df
            
            # Use efficient groupby with sorted data
            result = df_sorted.groupby(group_col, sort=False).agg(agg_dict)
            
            # Update stats
            self.optimization_stats['total_operations'] += 1
            self.optimization_stats['optimized_operations'] += 1
            self.optimization_stats['time_saved_ms'] += (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.warning(f"GroupBy optimization failed: {str(e)}")
            return df.groupby(group_col).agg(agg_dict)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        Get optimization performance statistics.
        
        Returns:
            Dictionary containing optimization stats
        """
        return {
            **self.optimization_stats,
            'optimization_rate': (
                self.optimization_stats['optimized_operations'] / 
                max(self.optimization_stats['total_operations'], 1)
            ) * 100
        }
    
    def reset_stats(self):
        """Reset optimization statistics."""
        self.optimization_stats = {
            'total_operations': 0,
            'optimized_operations': 0,
            'time_saved_ms': 0.0
        }


def optimize_performance(func):
    """
    Decorator to automatically optimize pandas operations.
    
    Args:
        func: Function to optimize
        
    Returns:
        Optimized function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # If result is a DataFrame, try to optimize it
            if isinstance(result, pd.DataFrame):
                optimizer = PandasOptimizer()
                result = optimizer.optimize_dataframe_memory(result)
                
            return result
            
        except Exception as e:
            logger.warning(f"Performance optimization failed in {func.__name__}: {str(e)}")
            return func(*args, **kwargs)
    
    return wrapper


# Global optimizer instance
_global_optimizer = None

def get_pandas_optimizer() -> PandasOptimizer:
    """
    Get a global pandas optimizer instance.
    
    Returns:
        PandasOptimizer: Global optimizer instance
    """
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PandasOptimizer()
    return _global_optimizer


# Utility functions for common optimizations
def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quick optimization for any DataFrame.
    
    Args:
        df: DataFrame to optimize
        
    Returns:
        Optimized DataFrame
    """
    optimizer = get_pandas_optimizer()
    return optimizer.optimize_dataframe_memory(df)


def optimize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quick OHLCV optimization.
    
    Args:
        df: OHLCV DataFrame to optimize
        
    Returns:
        Optimized OHLCV DataFrame
    """
    optimizer = get_pandas_optimizer()
    return optimizer.optimize_ohlcv_calculations(df)