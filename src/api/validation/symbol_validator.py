"""
Symbol Validation Service
Prevents system status symbols from appearing in API responses
"""

import logging
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class SymbolValidator:
    """Validates trading symbols to prevent system status contamination"""
    
    # System symbols that should never appear in trading data
    FORBIDDEN_SYMBOLS = {
        'SYSTEM_STATUS',
        'INITIALIZING', 
        'ERROR_STATUS',
        'LOADING_DATA',
        'NO_DATA',
        'FALLBACK_DATA'
    }
    
    # Forbidden substrings in symbols
    FORBIDDEN_SUBSTRINGS = {
        'SYSTEM',
        'ERROR',
        'LOADING',
        'STATUS'
    }
    
    # Valid trading pair suffixes
    VALID_SUFFIXES = {'USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB'}
    
    @classmethod
    def is_valid_trading_symbol(cls, symbol: str) -> bool:
        """
        Check if a symbol is a valid trading pair (not system status)
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            True if valid trading symbol, False otherwise
        """
        if not symbol or not isinstance(symbol, str):
            return False
            
        # Check forbidden symbols
        if symbol.upper() in cls.FORBIDDEN_SYMBOLS:
            return False
            
        # Check forbidden substrings
        symbol_upper = symbol.upper()
        for forbidden in cls.FORBIDDEN_SUBSTRINGS:
            if forbidden in symbol_upper:
                return False
        
        # Check valid suffix (for crypto pairs)
        has_valid_suffix = any(symbol.upper().endswith(suffix) for suffix in cls.VALID_SUFFIXES)
        if not has_valid_suffix:
            return False
            
        # Minimum length check (e.g., BTCUSDT = 7 chars)
        if len(symbol) < 6:
            return False
            
        return True
    
    @classmethod
    def is_valid_sentiment(cls, sentiment: str) -> bool:
        """Check if sentiment is valid (not system status)"""
        if not sentiment or not isinstance(sentiment, str):
            return True  # Allow empty/null sentiments
            
        forbidden_sentiments = {'INITIALIZING', 'ERROR', 'LOADING', 'SYSTEM_STATUS'}
        return sentiment.upper() not in forbidden_sentiments
    
    @classmethod
    def validate_symbol_data(cls, symbol_data: Dict[str, Any]) -> bool:
        """
        Validate a complete symbol data object
        
        Args:
            symbol_data: Dictionary containing symbol information
            
        Returns:
            True if valid, False if contains system contamination
        """
        # Check symbol field
        symbol = symbol_data.get('symbol', '')
        if not cls.is_valid_trading_symbol(symbol):
            logger.warning(f"Invalid trading symbol detected: {symbol}")
            return False
            
        # Check sentiment if present
        sentiment = symbol_data.get('sentiment', '')
        if sentiment and not cls.is_valid_sentiment(sentiment):
            logger.warning(f"Invalid sentiment detected for {symbol}: {sentiment}")
            return False
            
        # Check for other system status indicators
        for key, value in symbol_data.items():
            if isinstance(value, str) and any(forbidden in value.upper() for forbidden in cls.FORBIDDEN_SUBSTRINGS):
                if key not in ['error', 'message', 'description']:  # Allow these fields to contain system terms
                    logger.warning(f"System status detected in {key} field: {value}")
                    return False
        
        return True
    
    @classmethod
    def filter_valid_symbols(cls, symbols_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out invalid symbols from a list
        
        Args:
            symbols_list: List of symbol dictionaries
            
        Returns:
            Filtered list with only valid trading symbols
        """
        if not symbols_list:
            return []
            
        valid_symbols = []
        filtered_count = 0
        
        for symbol_data in symbols_list:
            if isinstance(symbol_data, dict) and cls.validate_symbol_data(symbol_data):
                valid_symbols.append(symbol_data)
            else:
                filtered_count += 1
                if isinstance(symbol_data, dict):
                    logger.debug(f"Filtered out invalid symbol: {symbol_data.get('symbol', 'unknown')}")
        
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} invalid symbols, returning {len(valid_symbols)} valid symbols")
        
        return valid_symbols
    
    @classmethod
    def validate_api_response(cls, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean an entire API response
        
        Args:
            response_data: API response dictionary
            
        Returns:
            Cleaned response with invalid symbols removed
        """
        cleaned_response = response_data.copy()
        
        # Handle different response formats
        if 'symbols' in cleaned_response:
            cleaned_response['symbols'] = cls.filter_valid_symbols(cleaned_response['symbols'])
            
        if 'confluence_scores' in cleaned_response:
            cleaned_response['confluence_scores'] = cls.filter_valid_symbols(cleaned_response['confluence_scores'])
            
        if 'signals' in cleaned_response:
            cleaned_response['signals'] = cls.filter_valid_symbols(cleaned_response['signals'])
            
        # Update count fields if they exist
        for count_field in ['count', 'total', 'length']:
            if count_field in cleaned_response:
                if 'symbols' in cleaned_response:
                    cleaned_response[count_field] = len(cleaned_response['symbols'])
                elif 'confluence_scores' in cleaned_response:
                    cleaned_response[count_field] = len(cleaned_response['confluence_scores'])
                elif 'signals' in cleaned_response:
                    cleaned_response[count_field] = len(cleaned_response['signals'])
        
        return cleaned_response
    
    @classmethod 
    def log_validation_stats(cls, original_count: int, filtered_count: int, endpoint: str = "unknown"):
        """Log validation statistics for monitoring"""
        if filtered_count > 0:
            contamination_rate = (filtered_count / (original_count + filtered_count)) * 100
            logger.warning(
                f"Symbol validation for {endpoint}: "
                f"filtered {filtered_count} invalid symbols, "
                f"contamination rate: {contamination_rate:.1f}%"
            )
        else:
            logger.debug(f"Symbol validation for {endpoint}: all {original_count} symbols valid")

# Global validator instance
symbol_validator = SymbolValidator()