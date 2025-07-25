"""
Market Data Wrapper to ensure complete data for indicators

This module wraps market data collection to ensure:
1. All required timeframes are present with correct labels
2. Trade data is fetched for orderflow analysis
3. Data validation before passing to indicators
"""

import pandas as pd
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MarketDataWrapper:
    """Wrapper to ensure complete market data for confluence analysis."""
    
    @staticmethod
    async def ensure_complete_market_data(exchange, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure market data has all required components.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            market_data: Existing market data
            
        Returns:
            Complete market data with all required fields
        """
        try:
            # Ensure OHLCV data has correct timeframe labels
            if 'ohlcv' in market_data:
                ohlcv = market_data['ohlcv']
                
                # Map common timeframe labels to standard ones
                timeframe_mapping = {
                    '1m': 'base',
                    '5m': 'ltf',
                    '15m': 'ltf',  # 15m maps to ltf (lower timeframe)
                    '30m': 'mtf',
                    '1h': 'mtf',   # 1h maps to mtf (medium timeframe)
                    '4h': 'htf',
                    '240': 'htf'
                }
                
                # Create properly mapped OHLCV data
                mapped_ohlcv = {}
                for tf_key, tf_data in ohlcv.items():
                    if tf_key in timeframe_mapping:
                        standard_key = timeframe_mapping[tf_key]
                        if standard_key not in mapped_ohlcv:
                            mapped_ohlcv[standard_key] = tf_data
                    elif tf_key in ['base', 'ltf', 'mtf', 'htf']:
                        # Already in standard format
                        mapped_ohlcv[tf_key] = tf_data
                
                # Ensure we have base timeframe (fallback to ltf if missing)
                if 'base' not in mapped_ohlcv and 'ltf' in mapped_ohlcv:
                    logger.warning(f"Missing base timeframe for {symbol}, using ltf as fallback")
                    mapped_ohlcv['base'] = mapped_ohlcv['ltf']
                
                market_data['ohlcv'] = mapped_ohlcv
            
            # Ensure trade data is present
            if 'trades' not in market_data or not market_data['trades']:
                logger.info(f"Fetching trade data for {symbol}...")
                try:
                    trades = await exchange.fetch_trades(symbol, limit=1000)
                    if trades:
                        market_data['trades'] = trades
                        logger.info(f"Fetched {len(trades)} trades for {symbol}")
                    else:
                        market_data['trades'] = []
                        logger.warning(f"No trades available for {symbol}")
                except Exception as e:
                    logger.error(f"Failed to fetch trades for {symbol}: {e}")
                    market_data['trades'] = []
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error ensuring complete market data: {e}")
            return market_data

    @staticmethod
    def validate_market_data(market_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate market data completeness.
        
        Returns:
            Dictionary of validation results
        """
        validation = {
            'has_ohlcv': False,
            'has_base_timeframe': False,
            'has_all_timeframes': False,
            'has_trades': False,
            'has_orderbook': False,
            'is_complete': False
        }
        
        try:
            # Check OHLCV
            if 'ohlcv' in market_data and market_data['ohlcv']:
                validation['has_ohlcv'] = True
                
                ohlcv = market_data['ohlcv']
                if 'base' in ohlcv:
                    validation['has_base_timeframe'] = True
                
                required_timeframes = ['base', 'ltf', 'mtf', 'htf']
                if all(tf in ohlcv for tf in required_timeframes):
                    validation['has_all_timeframes'] = True
            
            # Check trades
            if 'trades' in market_data and market_data['trades']:
                validation['has_trades'] = True
            
            # Check orderbook
            if 'orderbook' in market_data and market_data['orderbook']:
                validation['has_orderbook'] = True
            
            # Overall completeness
            validation['is_complete'] = (
                validation['has_ohlcv'] and
                validation['has_base_timeframe'] and
                validation['has_trades'] and
                validation['has_orderbook']
            )
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            return validation
