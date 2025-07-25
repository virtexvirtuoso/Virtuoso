
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
