
# General Optimization Patterns for All Indicators

import numpy as np
import pandas as pd
from functools import lru_cache
from typing import Union, Optional

class GeneralOptimizations:
    """General optimization patterns for indicator calculations."""
    
    @staticmethod
    def replace_iterrows_with_vectorization(df: pd.DataFrame, 
                                          calculation_func) -> pd.Series:
        """
        Replace df.iterrows() with vectorized operations.
        
        Example:
        # Slow (100x slower):
        results = []
        for idx, row in df.iterrows():
            result = calculation_func(row)
            results.append(result)
        
        # Fast (vectorized):
        results = df.apply(calculation_func, axis=1)  # Still not ideal
        
        # Fastest (fully vectorized):
        results = vectorized_calculation_func(df)
        """
        # If possible, create a fully vectorized version
        # Otherwise, use apply as intermediate step
        return df.apply(calculation_func, axis=1)
    
    @staticmethod
    def optimize_rolling_calculations(data: pd.Series, 
                                    window: int,
                                    func_name: str = 'mean') -> pd.Series:
        """
        Optimize rolling calculations using built-in pandas functions.
        
        Use pandas built-in rolling functions instead of apply(lambda).
        """
        rolling_obj = data.rolling(window=window, min_periods=1)
        
        # Use built-in functions when possible
        if func_name == 'mean':
            return rolling_obj.mean()
        elif func_name == 'std':
            return rolling_obj.std()
        elif func_name == 'max':
            return rolling_obj.max()
        elif func_name == 'min':
            return rolling_obj.min()
        elif func_name == 'sum':
            return rolling_obj.sum()
        else:
            # For custom functions, use apply as fallback
            return rolling_obj.apply(func_name)
    
    @staticmethod
    @lru_cache(maxsize=128)
    def cached_calculation(data_hash: str, 
                          calculation_params: tuple) -> Union[float, np.ndarray]:
        """
        Cache expensive calculations to avoid recomputation.
        
        Use for calculations that are called frequently with same parameters.
        """
        # This is a template - implement specific caching logic
        pass
    
    @staticmethod
    def vectorize_condition_checks(data: pd.DataFrame, 
                                 conditions: dict) -> pd.Series:
        """
        Vectorize multiple condition checks.
        
        Instead of:
        mask = []
        for idx, row in df.iterrows():
            if condition1(row) and condition2(row):
                mask.append(True)
            else:
                mask.append(False)
        
        Use:
        mask1 = df[col1] > threshold1
        mask2 = df[col2] < threshold2
        combined_mask = mask1 & mask2
        """
        combined_mask = pd.Series(True, index=data.index)
        
        for column, condition in conditions.items():
            if isinstance(condition, dict):
                if 'gt' in condition:
                    combined_mask &= data[column] > condition['gt']
                if 'lt' in condition:
                    combined_mask &= data[column] < condition['lt']
                if 'eq' in condition:
                    combined_mask &= data[column] == condition['eq']
        
        return combined_mask
    
    @staticmethod
    def optimize_groupby_operations(df: pd.DataFrame,
                                  groupby_col: str,
                                  agg_functions: dict) -> pd.DataFrame:
        """
        Optimize groupby operations using efficient aggregation.
        
        Use built-in aggregation functions when possible.
        """
        # Use built-in agg functions for speed
        optimized_agg = {}
        for col, func in agg_functions.items():
            if func in ['mean', 'sum', 'count', 'std', 'min', 'max']:
                optimized_agg[col] = func
            else:
                # For custom functions, use apply
                optimized_agg[col] = lambda x: func(x)
        
        return df.groupby(groupby_col).agg(optimized_agg)

# Performance Testing Utilities
class PerformanceTimer:
    """Utility for timing optimization improvements."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        print(f"{self.name}: {duration:.4f}s")

# Usage:
# with PerformanceTimer("Optimized calculation"):
#     result = optimized_function(data)
