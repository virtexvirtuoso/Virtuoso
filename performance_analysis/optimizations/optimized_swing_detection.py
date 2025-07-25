
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
