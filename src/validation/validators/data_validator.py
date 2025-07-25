"""
Merged validation module
Merged from: utils/data_validator.py and validation/validators/data_validator.py
"""

from ..core.base import ValidationResult, ValidationContext
from ..core.models import ValidationLevel
from typing import Dict, Any, List, Optional
from typing import Dict, Any, List, Optional, Union
import logging
import numpy as np
import pandas as pd

class DataValidator:
    """Validates market data completeness for indicators."""

    @staticmethod
    def validate_for_confluence(market_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate market data has all required components for confluence analysis.
        
        Returns:
            Dict with validation results for each component
        """
        results = {'has_ohlcv': False, 'has_base_timeframe': False, 'has_trades': False, 'has_orderbook': False, 'has_ticker': False, 'is_valid': False}
        try:
            if 'ohlcv' in market_data and market_data['ohlcv']:
                results['has_ohlcv'] = True
                ohlcv = market_data['ohlcv']
                if any((key in ohlcv for key in ['base', '1m', '1'])):
                    results['has_base_timeframe'] = True
            if 'trades' in market_data and market_data['trades'] and (len(market_data['trades']) > 0):
                results['has_trades'] = True
            if 'orderbook' in market_data and market_data['orderbook']:
                ob = market_data['orderbook']
                if 'bids' in ob and 'asks' in ob and ob['bids'] and ob['asks']:
                    results['has_orderbook'] = True
            if 'ticker' in market_data and market_data['ticker']:
                results['has_ticker'] = True
            results['is_valid'] = results['has_ohlcv'] and results['has_trades'] and results['has_orderbook']
            if not results['is_valid']:
                missing = [k for k, v in results.items() if not v and k != 'is_valid']
                logger.warning(f'Market data validation failed. Missing: {missing}')
        except Exception as e:
            logger.error(f'Error validating market data: {e}')
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
            validation = DataValidator.validate_for_confluence(market_data)
            if not validation['has_trades']:
                logger.info(f'Fetching missing trade data for {symbol}...')
                try:
                    trades = await exchange.fetch_trades(symbol, limit=1000)
                    if trades:
                        market_data['trades'] = trades
                        logger.info(f'Fetched {len(trades)} trades')
                except Exception as e:
                    logger.error(f'Failed to fetch trades: {e}')
                    market_data['trades'] = []
            if not validation['has_base_timeframe'] and 'ohlcv' in market_data:
                ohlcv = market_data['ohlcv']
                if '1m' in ohlcv:
                    ohlcv['base'] = ohlcv['1m']
                    logger.info('Mapped 1m data to base timeframe')
                elif '1' in ohlcv:
                    ohlcv['base'] = ohlcv['1']
                    logger.info('Mapped 1 data to base timeframe')
                elif 'ltf' in ohlcv:
                    ohlcv['base'] = ohlcv['ltf']
                    logger.warning('Using ltf as fallback for base timeframe')
            return market_data
        except Exception as e:
            logger.error(f'Error ensuring complete data: {e}')
            return market_data

@staticmethod
def validate_for_confluence(market_data: Dict[str, Any]) -> Dict[str, bool]:
    """
        Validate market data has all required components for confluence analysis.
        
        Returns:
            Dict with validation results for each component
        """
    results = {'has_ohlcv': False, 'has_base_timeframe': False, 'has_trades': False, 'has_orderbook': False, 'has_ticker': False, 'is_valid': False}
    try:
        if 'ohlcv' in market_data and market_data['ohlcv']:
            results['has_ohlcv'] = True
            ohlcv = market_data['ohlcv']
            if any((key in ohlcv for key in ['base', '1m', '1'])):
                results['has_base_timeframe'] = True
        if 'trades' in market_data and market_data['trades'] and (len(market_data['trades']) > 0):
            results['has_trades'] = True
        if 'orderbook' in market_data and market_data['orderbook']:
            ob = market_data['orderbook']
            if 'bids' in ob and 'asks' in ob and ob['bids'] and ob['asks']:
                results['has_orderbook'] = True
        if 'ticker' in market_data and market_data['ticker']:
            results['has_ticker'] = True
        results['is_valid'] = results['has_ohlcv'] and results['has_trades'] and results['has_orderbook']
        if not results['is_valid']:
            missing = [k for k, v in results.items() if not v and k != 'is_valid']
            logger.warning(f'Market data validation failed. Missing: {missing}')
    except Exception as e:
        logger.error(f'Error validating market data: {e}')
    return results

@staticmethod
def validate_market_data(data: Dict[str, Any], context: Optional[ValidationContext]=None) -> ValidationResult:
    """Validate market data structure and content with flexible validation.
        
        Args:
            data: Market data dictionary
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result with errors/warnings
        """
    result = ValidationResult(success=True)
    try:
        core_keys = ['symbol']
        missing_core = [key for key in core_keys if key not in data]
        if missing_core:
            result.add_error(f'Missing core keys in market data: {missing_core}')
            return result
        recommended_keys = ['timestamp', 'exchange']
        missing_recommended = [key for key in recommended_keys if key not in data]
        if missing_recommended:
            result.add_warning(f'Missing recommended keys in market data: {missing_recommended}')
        if 'price_data' in data and data['price_data']:
            price_result = DataValidator.validate_price_data(data['price_data'], context)
            if not price_result.success:
                result.add_warning('Price data validation failed, but continuing')
        elif 'ohlcv' in data and data['ohlcv']:
            logger.debug('Using alternative OHLCV structure for price data')
        if 'trades' in data and data['trades']:
            trades_result = DataValidator.validate_trades_data(data['trades'], context)
            if not trades_result.success:
                result.add_warning('Trades data validation failed, but continuing')
        if 'orderbook' in data and data['orderbook']:
            orderbook_result = DataValidator.validate_orderbook_data(data['orderbook'], context)
            if not orderbook_result.success:
                result.add_warning('Orderbook data validation failed, but continuing')
        return result
    except Exception as e:
        result.add_error(f'Error validating market data: {str(e)}')
        return result

@staticmethod
def validate_ohlc_relationships(df: pd.DataFrame) -> bool:
    """Validate OHLC price relationships.
        
        Args:
            df: OHLC DataFrame
            
        Returns:
            bool: True if relationships are valid, False otherwise
        """
    try:
        if not ((df['high'] >= df['open']) & (df['high'] >= df['low']) & (df['high'] >= df['close'])).all():
            return False
        if not ((df['low'] <= df['open']) & (df['low'] <= df['high']) & (df['low'] <= df['close'])).all():
            return False
        return True
    except Exception as e:
        logger.error(f'Error validating OHLC relationships: {str(e)}')
        return False

@staticmethod
def validate_orderbook_data(orderbook, context: Optional[ValidationContext]=None) -> ValidationResult:
    """Validate orderbook data structure and content.
        
        Args:
            orderbook: Orderbook data (DataFrame, dict, or list)
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
    result = ValidationResult(success=True)
    try:
        if isinstance(orderbook, pd.DataFrame):
            if orderbook.empty:
                result.add_warning('Empty orderbook data')
                return result
        elif isinstance(orderbook, dict):
            if not orderbook:
                result.add_warning('Empty orderbook data')
                return result
            if 'bids' in orderbook or 'asks' in orderbook:
                return result
            if 'price' in orderbook and 'size' in orderbook:
                orderbook = pd.DataFrame([orderbook])
            else:
                return result
        elif isinstance(orderbook, (list, tuple)):
            if not orderbook:
                result.add_warning('Empty orderbook data')
                return result
            return result
        else:
            result.add_warning(f'Unsupported orderbook data type: {type(orderbook)}')
            return result
        required_columns = ['price', 'size', 'side']
        if not all((col in orderbook.columns for col in required_columns)):
            result.add_error('Missing required columns in orderbook data')
            return result
        if orderbook[required_columns].isna().any().any():
            result.add_error('NaN values found in orderbook data')
            return result
        if (orderbook[['price', 'size']] < 0).any().any():
            result.add_error('Negative values found in orderbook data')
            return result
        valid_sides = ['bid', 'ask']
        if not orderbook['side'].isin(valid_sides).all():
            result.add_error('Invalid side values in orderbook data')
            return result
        bids = orderbook[orderbook['side'] == 'bid']['price']
        asks = orderbook[orderbook['side'] == 'ask']['price']
        if not bids.empty and (not asks.empty):
            if bids.max() >= asks.min():
                result.add_error('Invalid price ordering in orderbook')
                return result
        return result
    except Exception as e:
        result.add_error(f'Error validating orderbook data: {str(e)}')
        return result

@staticmethod
def validate_price_data(price_data: Dict[str, pd.DataFrame], context: Optional[ValidationContext]=None) -> ValidationResult:
    """Validate price data structure and content.
        
        Args:
            price_data: Dictionary of price data DataFrames
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
    result = ValidationResult(success=True)
    try:
        if not price_data:
            result.add_error('Empty price data')
            return result
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for timeframe, df in price_data.items():
            if not isinstance(df, pd.DataFrame):
                result.add_error(f'Invalid data type for timeframe {timeframe}')
                continue
            if not all((col in df.columns for col in required_columns)):
                result.add_error(f'Missing required columns in timeframe {timeframe}')
                continue
            if df[required_columns].isna().any().any():
                result.add_error(f'NaN values found in timeframe {timeframe}')
                continue
            if not DataValidator.validate_ohlc_relationships(df):
                result.add_error(f'Invalid OHLC relationships in timeframe {timeframe}')
                continue
            if (df[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
                result.add_error(f'Negative values found in timeframe {timeframe}')
                continue
        return result
    except Exception as e:
        result.add_error(f'Error validating price data: {str(e)}')
        return result

@staticmethod
def validate_trades_data(trades, context: Optional[ValidationContext]=None) -> ValidationResult:
    """Validate trades data structure and content.
        
        Args:
            trades: Trades data (DataFrame, list, or dict)
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
    result = ValidationResult(success=True)
    try:
        if isinstance(trades, pd.DataFrame):
            if trades.empty:
                result.add_warning('Empty trades data')
                return result
        elif isinstance(trades, (list, tuple)):
            if not trades:
                result.add_warning('Empty trades data')
                return result
            if all((isinstance(item, dict) for item in trades)):
                trades = pd.DataFrame(trades)
            else:
                return result
        elif isinstance(trades, dict):
            if not trades:
                result.add_warning('Empty trades data')
                return result
            trades = pd.DataFrame([trades])
        else:
            result.add_warning(f'Unsupported trades data type: {type(trades)}')
            return result
        required_columns = ['symbol', 'side', 'price', 'amount']
        if not all((col in trades.columns for col in required_columns)):
            result.add_error('Missing required columns in trades data')
            return result
        if trades[required_columns].isna().any().any():
            result.add_error('NaN values found in trades data')
            return result
        if (trades[['price', 'amount']] < 0).any().any():
            result.add_error('Negative values found in trades data')
            return result
        valid_sides = ['buy', 'sell']
        if not trades['side'].isin(valid_sides).all():
            result.add_error('Invalid side values in trades data')
            return result
        return result
    except Exception as e:
        result.add_error(f'Error validating trades data: {str(e)}')
        return result
