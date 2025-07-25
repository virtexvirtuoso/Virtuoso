
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
