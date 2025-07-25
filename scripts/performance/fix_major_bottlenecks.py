#!/usr/bin/env python3
"""
Major Performance Bottleneck Fixes

This script contains specific fixes for the most critical performance bottlenecks
identified in the codebase analysis.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def create_optimized_swing_detection():
    """
    Create optimized version of swing detection that removes O(n²) complexity.
    
    Original code has nested loops that create O(n²) complexity:
    - Outer loop: for i in range(window, len(data) - window)
    - Inner loop: any(highs[i] > highs[j] * (1 + threshold) for j in range(...))
    
    Optimized approach uses vectorized operations.
    """
    return '''
def _find_support_resistance_levels_optimized(self, data: pd.DataFrame, timeframe: str = 'base') -> List[float]:
    """
    Optimized version of support/resistance level detection.
    Removes O(n²) nested loops and uses vectorized operations.
    """
    try:
        if len(data) < 20:
            return []
        
        highs = data['high'].values
        lows = data['low'].values  
        closes = data['close'].values
        
        # Parameters
        window = min(10, len(data) // 4)
        threshold = 0.002  # 0.2% threshold
        
        # Vectorized approach using scipy.signal.find_peaks
        from scipy.signal import find_peaks
        
        # Find peaks (swing highs)
        peak_indices, peak_properties = find_peaks(
            highs, 
            distance=window,
            prominence=np.std(highs) * 0.1  # Dynamic prominence based on volatility
        )
        
        # Find troughs (swing lows) by inverting the data
        trough_indices, trough_properties = find_peaks(
            -lows,
            distance=window, 
            prominence=np.std(lows) * 0.1
        )
        
        # Get the actual levels
        swing_highs = [(i, highs[i]) for i in peak_indices]
        swing_lows = [(i, lows[i]) for i in trough_indices]
        
        # Combine levels
        all_levels = [level for _, level in swing_highs] + [level for _, level in swing_lows]
        
        if not all_levels:
            return []
        
        # Vectorized clustering to group nearby levels
        all_levels = np.array(all_levels)
        current_price = closes[-1]
        
        # Group levels within 0.5% of each other using numpy operations
        sorted_levels = np.sort(all_levels)
        grouped_levels = []
        
        if len(sorted_levels) > 0:
            current_group = [sorted_levels[0]]
            
            for level in sorted_levels[1:]:
                if abs(level - current_group[-1]) / current_group[-1] < 0.005:  # 0.5%
                    current_group.append(level)
                else:
                    # Take average of group
                    grouped_levels.append(np.mean(current_group))
                    current_group = [level]
            
            # Add final group
            if current_group:
                grouped_levels.append(np.mean(current_group))
        
        # Filter levels by significance (distance from current price)
        significant_levels = []
        for level in grouped_levels:
            distance_pct = abs(level - current_price) / current_price
            if 0.001 < distance_pct < 0.05:  # Between 0.1% and 5%
                significant_levels.append(level)
        
        return significant_levels[:10]  # Limit to top 10 levels
        
    except Exception as e:
        self.logger.error(f"Error in optimized SR detection: {str(e)}")
        return []
'''

def create_optimized_order_blocks():
    """Create optimized order block detection."""
    return '''
def _detect_order_blocks_optimized(self, data: pd.DataFrame, volume_data: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
    """
    Optimized order block detection using vectorized operations.
    Eliminates nested loops for better performance.
    """
    try:
        if len(data) < 50:
            return []
        
        highs = data['high'].values
        lows = data['low'].values
        closes = data['close'].values
        opens = data['open'].values
        volumes = data['volume'].values if 'volume' in data.columns else np.ones(len(data))
        
        # Vectorized candle analysis
        body_size = np.abs(closes - opens)
        candle_range = highs - lows
        
        # Identify significant candles (large body relative to range)
        significant_mask = (body_size / candle_range) > 0.7
        large_volume_mask = volumes > np.percentile(volumes, 80)
        
        # Combine conditions
        order_block_candidates = significant_mask & large_volume_mask
        candidate_indices = np.where(order_block_candidates)[0]
        
        order_blocks = []
        min_distance = 20  # Minimum distance between order blocks
        
        # Filter candidates by distance (vectorized)
        if len(candidate_indices) > 0:
            # Calculate distances between candidates
            distances = np.diff(candidate_indices)
            valid_indices = [candidate_indices[0]]  # Always include first
            
            for i, distance in enumerate(distances):
                if distance >= min_distance:
                    valid_indices.append(candidate_indices[i + 1])
        
            # Create order block data
            for idx in valid_indices[-10:]:  # Last 10 order blocks
                ob_type = 'bullish' if closes[idx] > opens[idx] else 'bearish'
                
                order_blocks.append({
                    'index': idx,
                    'type': ob_type,
                    'top': highs[idx],
                    'bottom': lows[idx],
                    'volume': volumes[idx],
                    'strength': body_size[idx] / candle_range[idx] if candle_range[idx] > 0 else 0
                })
        
        return order_blocks
        
    except Exception as e:
        self.logger.error(f"Error in optimized order block detection: {str(e)}")
        return []
'''

def create_optimized_range_analysis():
    """Create optimized range analysis."""
    return '''
def _analyze_range_structure_optimized(self, data: pd.DataFrame, timeframe: str = 'base') -> Dict[str, Any]:
    """
    Optimized range analysis using vectorized operations.
    """
    try:
        if len(data) < 50:
            return {'in_range': False, 'range_strength': 0}
        
        highs = data['high'].values
        lows = data['low'].values
        closes = data['close'].values
        
        # Use rolling windows for efficient range detection
        window = min(50, len(data) // 2)
        
        # Vectorized rolling max/min
        rolling_highs = pd.Series(highs).rolling(window=window).max().values
        rolling_lows = pd.Series(lows).rolling(window=window).min().values
        
        # Calculate range boundaries
        range_top = np.nanmax(rolling_highs[-20:])  # Last 20 periods
        range_bottom = np.nanmin(rolling_lows[-20:])
        
        current_price = closes[-1]
        range_height = range_top - range_bottom
        
        if range_height == 0:
            return {'in_range': False, 'range_strength': 0}
        
        # Position within range (0 = bottom, 1 = top)
        position_in_range = (current_price - range_bottom) / range_height
        
        # Range strength (how well price respects the range)
        touches_top = np.sum((highs[-50:] >= range_top * 0.99) & (highs[-50:] <= range_top * 1.01))
        touches_bottom = np.sum((lows[-50:] <= range_bottom * 1.01) & (lows[-50:] >= range_bottom * 0.99))
        
        range_strength = min(100, (touches_top + touches_bottom) * 10)
        
        return {
            'in_range': 0.1 < position_in_range < 0.9,
            'range_strength': range_strength,
            'position_in_range': position_in_range,
            'range_top': range_top,
            'range_bottom': range_bottom,
            'range_height': range_height
        }
        
    except Exception as e:
        self.logger.error(f"Error in optimized range analysis: {str(e)}")
        return {'in_range': False, 'range_strength': 0}
'''

def create_psutil_async_wrapper():
    """Create async wrapper for psutil operations."""
    return '''
import asyncio
import psutil
from typing import Dict, Any

class AsyncPsutilWrapper:
    """Async wrapper for psutil operations to prevent blocking."""
    
    @staticmethod
    async def get_cpu_percent(interval: float = 1.0) -> float:
        """Get CPU percentage asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, psutil.cpu_percent, interval)
    
    @staticmethod 
    async def get_memory_info() -> Dict[str, Any]:
        """Get memory information asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _get_memory():
            vm = psutil.virtual_memory()
            return {
                'percent': vm.percent,
                'total': vm.total,
                'available': vm.available,
                'used': vm.used
            }
        
        return await loop.run_in_executor(None, _get_memory)
    
    @staticmethod
    async def get_system_info() -> Dict[str, Any]:
        """Get comprehensive system info asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _get_info():
            try:
                cpu_times = psutil.cpu_times()
                cpu_freq = psutil.cpu_freq()  
                cpu_stats = psutil.cpu_stats()
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()
                
                return {
                    'cpu': {
                        'percent': psutil.cpu_percent(interval=1),
                        'times': cpu_times._asdict(),
                        'freq': cpu_freq._asdict() if cpu_freq else {},
                        'stats': cpu_stats._asdict()
                    },
                    'memory': {
                        'virtual': memory._asdict(),
                        'swap': swap._asdict()
                    },
                    'io': {
                        'disk': disk_io._asdict() if disk_io else {},
                        'network': net_io._asdict() if net_io else {}
                    }
                }
            except Exception as e:
                return {'error': str(e)}
        
        return await loop.run_in_executor(None, _get_info)

# Usage in async functions:
# async def get_system_metrics():
#     wrapper = AsyncPsutilWrapper()
#     cpu_percent = await wrapper.get_cpu_percent()
#     memory_info = await wrapper.get_memory_info()
#     return {'cpu': cpu_percent, 'memory': memory_info}
'''

def main():
    """Generate optimization fixes."""
    print("🔧 Generating performance optimization fixes...")
    
    output_dir = Path("performance_analysis/optimizations")
    output_dir.mkdir(exist_ok=True)
    
    # Create optimized swing detection
    with open(output_dir / "optimized_swing_detection.py", "w") as f:
        f.write(create_optimized_swing_detection())
    
    # Create optimized order blocks  
    with open(output_dir / "optimized_order_blocks.py", "w") as f:
        f.write(create_optimized_order_blocks())
    
    # Create optimized range analysis
    with open(output_dir / "optimized_range_analysis.py", "w") as f:
        f.write(create_optimized_range_analysis())
    
    # Create async psutil wrapper
    with open(output_dir / "async_psutil_wrapper.py", "w") as f:
        f.write(create_psutil_async_wrapper())
    
    print("✅ Optimization fixes generated!")
    print(f"📁 Files saved to: {output_dir}")
    print("\nKey optimizations:")
    print("1. 🚀 Swing detection: O(n²) → O(n log n)")
    print("2. 🚀 Order blocks: Nested loops → Vectorized operations") 
    print("3. 🚀 Range analysis: Improved efficiency with rolling windows")
    print("4. 🚀 Psutil operations: Blocking → Async with thread pool")
    
    return output_dir

if __name__ == "__main__":
    main()