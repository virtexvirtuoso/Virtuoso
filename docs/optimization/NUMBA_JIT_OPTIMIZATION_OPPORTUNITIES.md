# Numba JIT Optimization Opportunities in `/src/indicators/`

Based on analysis of your indicator modules, here are the specific algorithms that would benefit most from Numba JIT compilation, organized by potential performance gain.

## High Priority Optimizations (50-100x speedup potential)

### 1. `price_structure_indicators.py` - Custom Algorithms

#### **Support/Resistance Level Detection**
```python
# Current implementation has nested loops - perfect for JIT
def _find_sr_levels(self, data):
    # Multiple nested loops for peak detection
    for timeframe in timeframes:
        for i in range(len(data)):
            for lookback in windows:
                # Nested calculations
```

**JIT Optimization:**
```python
import numba
from numba import jit, prange, types

@jit(nopython=True, parallel=True)
def fast_sr_detection(highs, lows, closes, volumes, lookback_periods):
    """Ultra-fast support/resistance detection with parallel processing"""
    n = len(highs)
    num_periods = len(lookback_periods)
    
    # Pre-allocate results arrays
    support_levels = np.zeros((n, num_periods))
    resistance_levels = np.zeros((n, num_periods))
    level_strengths = np.zeros((n, num_periods))
    
    # Parallel processing across different lookback periods
    for period_idx in prange(num_periods):
        lookback = lookback_periods[period_idx]
        
        for i in range(lookback, n):
            # Vectorized peak detection
            window_highs = highs[i-lookback:i+1]
            window_lows = lows[i-lookback:i+1]
            window_volumes = volumes[i-lookback:i+1]
            
            # Find resistance (local maxima)
            max_idx = 0
            max_val = window_highs[0]
            for j in range(1, len(window_highs)):
                if window_highs[j] > max_val:
                    max_val = window_highs[j]
                    max_idx = j
            
            # Validate resistance with volume confirmation
            if max_idx > 0 and max_idx < len(window_highs) - 1:
                left_lower = window_highs[max_idx-1] < max_val
                right_lower = window_highs[max_idx+1] < max_val
                volume_confirm = window_volumes[max_idx] > np.mean(window_volumes)
                
                if left_lower and right_lower and volume_confirm:
                    resistance_levels[i, period_idx] = max_val
                    level_strengths[i, period_idx] = window_volumes[max_idx] / np.mean(window_volumes)
            
            # Find support (local minima) - similar logic
            min_idx = 0
            min_val = window_lows[0]
            for j in range(1, len(window_lows)):
                if window_lows[j] < min_val:
                    min_val = window_lows[j]
                    min_idx = j
            
            if min_idx > 0 and min_idx < len(window_lows) - 1:
                left_higher = window_lows[min_idx-1] > min_val
                right_higher = window_lows[min_idx+1] > min_val
                volume_confirm = window_volumes[min_idx] > np.mean(window_volumes)
                
                if left_higher and right_higher and volume_confirm:
                    support_levels[i, period_idx] = min_val
                    level_strengths[i, period_idx] = window_volumes[min_idx] / np.mean(window_volumes)
    
    return support_levels, resistance_levels, level_strengths

# Integration into existing class
class OptimizedPriceStructureIndicators(PriceStructureIndicators):
    def _find_sr_levels_optimized(self, data):
        """JIT-optimized support/resistance detection"""
        df = data['ohlcv']['base']  # Assuming base timeframe
        
        highs = df['high'].values.astype(np.float64)
        lows = df['low'].values.astype(np.float64)
        closes = df['close'].values.astype(np.float64)
        volumes = df['volume'].values.astype(np.float64)
        
        lookback_periods = np.array([10, 20, 50, 100], dtype=np.int64)
        
        support_levels, resistance_levels, strengths = fast_sr_detection(
            highs, lows, closes, volumes, lookback_periods
        )
        
        # Convert back to expected format
        return self._format_sr_results(support_levels, resistance_levels, strengths)
```

#### **Order Block Detection**
```python
@jit(nopython=True)
def fast_order_block_detection(ohlc, volumes, min_volume_ratio=2.0, min_wick_ratio=1.5):
    """JIT-compiled order block detection with volume confirmation"""
    n = len(ohlc)
    order_blocks = np.zeros((n, 4))  # [is_block, strength, price_level, block_type]
    
    for i in range(10, n - 5):  # Need lookback and lookahead
        # Calculate volume statistics
        current_vol = volumes[i]
        avg_vol = 0.0
        for j in range(i-10, i):
            avg_vol += volumes[j]
        avg_vol /= 10.0
        
        # Volume spike condition
        if current_vol > avg_vol * min_volume_ratio:
            open_price = ohlc[i, 0]
            high_price = ohlc[i, 1]
            low_price = ohlc[i, 2]
            close_price = ohlc[i, 3]
            
            # Calculate wick and body sizes
            body_size = abs(close_price - open_price)
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low_price
            
            # Order block criteria
            has_upper_rejection = upper_wick > body_size * min_wick_ratio
            has_lower_rejection = lower_wick > body_size * min_wick_ratio
            
            if has_upper_rejection or has_lower_rejection:
                # Calculate block strength
                volume_strength = current_vol / avg_vol
                wick_strength = max(upper_wick, lower_wick) / (body_size + 1e-8)
                overall_strength = (volume_strength + wick_strength) / 2.0
                
                # Determine block type and level
                if has_upper_rejection:
                    block_type = 1.0  # Bearish (supply zone)
                    price_level = high_price
                else:
                    block_type = -1.0  # Bullish (demand zone)
                    price_level = low_price
                
                order_blocks[i, 0] = 1.0  # Is order block
                order_blocks[i, 1] = min(overall_strength, 10.0)  # Strength (capped)
                order_blocks[i, 2] = price_level
                order_blocks[i, 3] = block_type
    
    return order_blocks
```

### 2. `volume_indicators.py` - Rolling Calculations

#### **OBV Calculation with JIT**
```python
@jit(nopython=True)
def fast_obv_calculation(closes, volumes):
    """JIT-optimized On-Balance Volume calculation"""
    n = len(closes)
    obv = np.zeros(n)
    obv[0] = volumes[0]
    
    for i in range(1, n):
        price_change = closes[i] - closes[i-1]
        if price_change > 0:
            obv[i] = obv[i-1] + volumes[i]
        elif price_change < 0:
            obv[i] = obv[i-1] - volumes[i]
        else:
            obv[i] = obv[i-1]
    
    return obv

# Integration
def calculate_obv_optimized(self, df: pd.DataFrame) -> pd.Series:
    """Optimized OBV calculation using Numba JIT"""
    closes = df['close'].values.astype(np.float64)
    volumes = df['volume'].values.astype(np.float64)
    
    obv_values = fast_obv_calculation(closes, volumes)
    return pd.Series(obv_values, index=df.index)
```

#### **Volume Delta with JIT**
```python
@jit(nopython=True)
def fast_volume_delta(trade_prices, trade_volumes, reference_prices):
    """High-performance volume delta calculation"""
    n = len(trade_prices)
    buy_volume = 0.0
    sell_volume = 0.0
    volume_delta = np.zeros(len(reference_prices))
    
    ref_idx = 0
    cumulative_buy = 0.0
    cumulative_sell = 0.0
    
    for i in range(n):
        trade_price = trade_prices[i]
        trade_vol = trade_volumes[i]
        
        # Advance reference index if needed
        while ref_idx < len(reference_prices) - 1 and trade_price > reference_prices[ref_idx]:
            volume_delta[ref_idx] = cumulative_buy - cumulative_sell
            ref_idx += 1
        
        # Classify trade as buy or sell
        if ref_idx > 0:
            mid_price = (reference_prices[ref_idx] + reference_prices[ref_idx-1]) / 2.0
            if trade_price >= mid_price:
                cumulative_buy += trade_vol
            else:
                cumulative_sell += trade_vol
    
    # Fill remaining values
    for i in range(ref_idx, len(reference_prices)):
        volume_delta[i] = cumulative_buy - cumulative_sell
    
    return volume_delta
```

### 3. `orderflow_indicators.py` - Trade Analysis

#### **Cumulative Volume Delta (CVD)**
```python
@jit(nopython=True)
def fast_cvd_calculation(trade_data, price_levels, time_windows):
    """JIT-compiled CVD calculation across multiple timeframes"""
    n_trades = len(trade_data)
    n_levels = len(price_levels)
    n_windows = len(time_windows)
    
    # Output arrays
    cvd_values = np.zeros((n_levels, n_windows))
    trade_counts = np.zeros((n_levels, n_windows))
    
    for window_idx in range(n_windows):
        window_size = time_windows[window_idx]
        
        for level_idx in range(n_levels):
            price_level = price_levels[level_idx]
            buy_volume = 0.0
            sell_volume = 0.0
            trades_count = 0
            
            # Process trades within time window
            for trade_idx in range(max(0, n_trades - window_size), n_trades):
                trade_price = trade_data[trade_idx, 0]  # price
                trade_volume = trade_data[trade_idx, 1]  # volume
                trade_side = trade_data[trade_idx, 2]    # side (1=buy, -1=sell)
                
                # Check if trade is relevant to this price level
                price_tolerance = price_level * 0.001  # 0.1% tolerance
                if abs(trade_price - price_level) <= price_tolerance:
                    if trade_side > 0:
                        buy_volume += trade_volume
                    else:
                        sell_volume += trade_volume
                    trades_count += 1
            
            cvd_values[level_idx, window_idx] = buy_volume - sell_volume
            trade_counts[level_idx, window_idx] = trades_count
    
    return cvd_values, trade_counts

@jit(nopython=True)
def fast_order_flow_imbalance(bid_volumes, ask_volumes, time_weights):
    """Fast order flow imbalance calculation with time decay"""
    n = len(bid_volumes)
    imbalances = np.zeros(n)
    
    for i in range(n):
        weighted_bid = 0.0
        weighted_ask = 0.0
        total_weight = 0.0
        
        # Apply time decay weights
        for j in range(max(0, i-len(time_weights)+1), i+1):
            weight_idx = i - j
            if weight_idx < len(time_weights):
                weight = time_weights[weight_idx]
                weighted_bid += bid_volumes[j] * weight
                weighted_ask += ask_volumes[j] * weight
                total_weight += weight
        
        if total_weight > 0:
            avg_bid = weighted_bid / total_weight
            avg_ask = weighted_ask / total_weight
            total_flow = avg_bid + avg_ask
            
            if total_flow > 0:
                imbalances[i] = (avg_bid - avg_ask) / total_flow
            else:
                imbalances[i] = 0.0
    
    return imbalances
```

## Medium Priority Optimizations (20-50x speedup potential)

### 4. `technical_indicators.py` - Custom RSI Implementation

```python
@jit(nopython=True)
def fast_rsi_wilder(closes, period=14):
    """Wilder's RSI calculation with JIT compilation"""
    n = len(closes)
    if n < period + 1:
        return np.full(n, 50.0)
    
    rsi_values = np.zeros(n)
    gains = np.zeros(n-1)
    losses = np.zeros(n-1)
    
    # Calculate price changes
    for i in range(1, n):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains[i-1] = change
            losses[i-1] = 0.0
        else:
            gains[i-1] = 0.0
            losses[i-1] = -change
    
    # Initial average
    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(period):
        avg_gain += gains[i]
        avg_loss += losses[i]
    avg_gain /= period
    avg_loss /= period
    
    # Calculate RSI values
    for i in range(period, n):
        if i == period:
            # First RSI value
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))
        else:
            # Wilder's smoothing
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
            
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))
    
    return rsi_values

@jit(nopython=True)
def fast_macd_calculation(closes, fast_period=12, slow_period=26, signal_period=9):
    """JIT-compiled MACD calculation"""
    n = len(closes)
    
    # EMA calculations
    fast_ema = np.zeros(n)
    slow_ema = np.zeros(n)
    macd_line = np.zeros(n)
    signal_line = np.zeros(n)
    
    # Initialize first values
    fast_ema[0] = closes[0]
    slow_ema[0] = closes[0]
    
    # Calculate EMAs
    fast_alpha = 2.0 / (fast_period + 1)
    slow_alpha = 2.0 / (slow_period + 1)
    signal_alpha = 2.0 / (signal_period + 1)
    
    for i in range(1, n):
        fast_ema[i] = fast_alpha * closes[i] + (1 - fast_alpha) * fast_ema[i-1]
        slow_ema[i] = slow_alpha * closes[i] + (1 - slow_alpha) * slow_ema[i-1]
        macd_line[i] = fast_ema[i] - slow_ema[i]
    
    # Calculate signal line
    signal_line[0] = macd_line[0]
    for i in range(1, n):
        signal_line[i] = signal_alpha * macd_line[i] + (1 - signal_alpha) * signal_line[i-1]
    
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram
```

### 5. `orderbook_indicators.py` - Market Depth Analysis

```python
@jit(nopython=True)
def fast_orderbook_imbalance(bid_prices, bid_sizes, ask_prices, ask_sizes, depth_levels=10):
    """High-performance order book imbalance calculation"""
    n = len(bid_prices)
    imbalances = np.zeros(n)
    
    for i in range(n):
        if i >= depth_levels:
            # Calculate weighted imbalance
            total_bid_value = 0.0
            total_ask_value = 0.0
            
            for level in range(min(depth_levels, len(bid_prices[i]), len(ask_prices[i]))):
                # Distance weighting (closer levels have more weight)
                weight = 1.0 / (level + 1.0)
                
                total_bid_value += bid_sizes[i][level] * weight
                total_ask_value += ask_sizes[i][level] * weight
            
            total_value = total_bid_value + total_ask_value
            if total_value > 0:
                imbalances[i] = (total_bid_value - total_ask_value) / total_value
    
    return imbalances

@jit(nopython=True) 
def fast_spread_analysis(bid_prices, ask_prices, volumes):
    """JIT-compiled spread analysis with volume weighting"""
    n = len(bid_prices)
    spread_metrics = np.zeros((n, 3))  # [spread, relative_spread, volume_weighted_spread]
    
    for i in range(n):
        if len(bid_prices[i]) > 0 and len(ask_prices[i]) > 0:
            best_bid = bid_prices[i][0]
            best_ask = ask_prices[i][0]
            
            # Basic spread
            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2.0
            
            # Relative spread
            if mid_price > 0:
                relative_spread = spread / mid_price
            else:
                relative_spread = 0.0
            
            # Volume-weighted spread
            if i > 0 and volumes[i] > 0:
                volume_weight = volumes[i] / (volumes[i-1] + volumes[i] + 1e-8)
                volume_weighted_spread = spread * volume_weight
            else:
                volume_weighted_spread = spread
            
            spread_metrics[i, 0] = spread
            spread_metrics[i, 1] = relative_spread
            spread_metrics[i, 2] = volume_weighted_spread
    
    return spread_metrics
```

## Implementation Strategy by File

### Priority 1: `price_structure_indicators.py`
- **Target Methods**: `_find_sr_levels`, `_calculate_order_blocks`, `_analyze_market_structure`
- **Expected Speedup**: 50-100x
- **Impact**: High (complex nested loops with multiple timeframes)

### Priority 2: `volume_indicators.py`  
- **Target Methods**: `calculate_obv`, `calculate_volume_delta`, `_calculate_volume_trend_score`
- **Expected Speedup**: 20-50x
- **Impact**: Medium-High (many rolling calculations)

### Priority 3: `orderflow_indicators.py`
- **Target Methods**: CVD calculation, trade flow analysis, imbalance detection
- **Expected Speedup**: 30-70x
- **Impact**: High (real-time trade processing)

### Priority 4: `technical_indicators.py`
- **Target Methods**: Custom RSI, MACD, Bollinger Bands implementations
- **Expected Speedup**: 10-30x
- **Impact**: Medium (can use TA-Lib instead, but custom implementations benefit)

### Priority 5: `orderbook_indicators.py`
- **Target Methods**: Order book depth analysis, spread calculations
- **Expected Speedup**: 15-40x  
- **Impact**: Medium (frequent order book updates)

## Integration Approach

### 1. **Gradual Migration**
```python
class OptimizedPriceStructureIndicators(PriceStructureIndicators):
    """JIT-optimized version with fallback to original methods"""
    
    def __init__(self, config, logger=None, use_jit=True):
        super().__init__(config, logger)
        self.use_jit = use_jit
        
        # Warm up JIT functions
        if self.use_jit:
            self._warmup_jit_functions()
    
    def _find_sr_levels(self, data):
        """Use JIT version if available, fallback to original"""
        try:
            if self.use_jit:
                return self._find_sr_levels_jit(data)
            else:
                return super()._find_sr_levels(data)
        except Exception as e:
            self.logger.warning(f"JIT optimization failed, using original: {e}")
            return super()._find_sr_levels(data)
    
    def _warmup_jit_functions(self):
        """Pre-compile JIT functions with dummy data"""
        dummy_data = np.random.randn(100).astype(np.float64)
        _ = fast_sr_detection(dummy_data, dummy_data, dummy_data, dummy_data, np.array([10, 20]))
```

### 2. **Performance Monitoring**
```python
import time
from functools import wraps

def benchmark_jit(original_method):
    """Decorator to benchmark JIT vs original performance"""
    @wraps(original_method)
    def wrapper(self, *args, **kwargs):
        # Time original method
        start = time.time()
        original_result = original_method(self, *args, **kwargs)
        original_time = time.time() - start
        
        # Time JIT method if available
        jit_method_name = f"{original_method.__name__}_jit"
        if hasattr(self, jit_method_name) and self.use_jit:
            start = time.time()
            jit_result = getattr(self, jit_method_name)(*args, **kwargs)
            jit_time = time.time() - start
            
            speedup = original_time / jit_time
            self.logger.info(f"JIT speedup for {original_method.__name__}: {speedup:.1f}x")
            
            return jit_result
        
        return original_result
    return wrapper
```

## Expected Performance Improvements

| File | Method | Current Speed | JIT Speed | Speedup | Priority |
|------|---------|--------------|-----------|---------|----------|
| `price_structure_indicators.py` | `_find_sr_levels` | 100ms | 1-2ms | 50-100x | High |
| `price_structure_indicators.py` | `_calculate_order_blocks` | 80ms | 2-3ms | 25-40x | High |
| `volume_indicators.py` | `calculate_obv` | 50ms | 2ms | 25x | Medium |
| `volume_indicators.py` | `calculate_volume_delta` | 120ms | 3ms | 40x | High |
| `orderflow_indicators.py` | CVD calculation | 200ms | 3-5ms | 40-70x | High |
| `technical_indicators.py` | Custom RSI | 30ms | 2ms | 15x | Low |

The algorithms with nested loops and custom mathematical computations in `price_structure_indicators.py` and `orderflow_indicators.py` offer the highest optimization potential with Numba JIT compilation.