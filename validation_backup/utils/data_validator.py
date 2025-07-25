"""
Data Validator for Market Data Completeness

Ensures all required data is present before indicator calculations.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates market data completeness for indicators."""
    
    @staticmethod
    def validate_for_confluence(market_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate market data has all required components for confluence analysis.
        
        Returns:
            Dict with validation results for each component
        """
        results = {
            'has_ohlcv': False,
            'has_base_timeframe': False,
            'has_trades': False,
            'has_orderbook': False,
            'has_ticker': False,
            'is_valid': False
        }
        
        try:
            # Check OHLCV data
            if 'ohlcv' in market_data and market_data['ohlcv']:
                results['has_ohlcv'] = True
                
                # Check for base timeframe
                ohlcv = market_data['ohlcv']
                if any(key in ohlcv for key in ['base', '1m', '1']):
                    results['has_base_timeframe'] = True
                    
            # Check trades
            if 'trades' in market_data and market_data['trades'] and len(market_data['trades']) > 0:
                results['has_trades'] = True
                
            # Check orderbook
            if 'orderbook' in market_data and market_data['orderbook']:
                ob = market_data['orderbook']
                if 'bids' in ob and 'asks' in ob and ob['bids'] and ob['asks']:
                    results['has_orderbook'] = True
                    
            # Check ticker
            if 'ticker' in market_data and market_data['ticker']:
                results['has_ticker'] = True
                
            # Overall validity
            results['is_valid'] = (
                results['has_ohlcv'] and 
                results['has_trades'] and 
                results['has_orderbook']
            )
            
            # Log validation results
            if not results['is_valid']:
                missing = [k for k, v in results.items() if not v and k != 'is_valid']
                logger.warning(f"Market data validation failed. Missing: {missing}")
                
        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            
        return results
    
    @staticmethod
    async def ensure_complete_data(exchange, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure market data is complete, fetching missing components.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            market_data: Existing market data
            
        Returns:
            Complete market data
        """
        try:
            # Validate current data
            validation = DataValidator.validate_for_confluence(market_data)
            
            # Fetch missing trades
            if not validation['has_trades']:
                logger.info(f"Fetching missing trade data for {symbol}...")
                try:
                    trades = await exchange.fetch_trades(symbol, limit=1000)
                    if trades:
                        market_data['trades'] = trades
                        logger.info(f"Fetched {len(trades)} trades")
                except Exception as e:
                    logger.error(f"Failed to fetch trades: {e}")
                    market_data['trades'] = []
                    
            # Ensure base timeframe exists
            if not validation['has_base_timeframe'] and 'ohlcv' in market_data:
                ohlcv = market_data['ohlcv']
                
                # Map 1m to base if it exists
                if '1m' in ohlcv:
                    ohlcv['base'] = ohlcv['1m']
                    logger.info("Mapped 1m data to base timeframe")
                elif '1' in ohlcv:
                    ohlcv['base'] = ohlcv['1']
                    logger.info("Mapped 1 data to base timeframe")
                elif 'ltf' in ohlcv:
                    # Use ltf as fallback
                    ohlcv['base'] = ohlcv['ltf']
                    logger.warning("Using ltf as fallback for base timeframe")
                    
            return market_data
            
        except Exception as e:
            logger.error(f"Error ensuring complete data: {e}")
            return market_data
