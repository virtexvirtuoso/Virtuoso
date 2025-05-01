"""
Data utility functions for signal processing and alert systems.

This module provides centralized data processing functions 
to ensure consistent handling across components.
"""

import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

def resolve_price(signal_data: Dict[str, Any], symbol: str = None) -> Optional[float]:
    """
    Resolve price from various data sources with a consistent priority order.
    
    This is a central utility to standardize price extraction across the application.
    
    Args:
        signal_data: Signal data dictionary that may contain price information
        symbol: Optional symbol for logging purposes
        
    Returns:
        Resolved price as float or None if not available
    """
    price = None
    source = "unknown"
    symbol_str = f" for {symbol}" if symbol else ""

    # Priority hierarchy for price resolution
    
    # 1. Direct price field (highest priority)
    if 'price' in signal_data and signal_data['price'] is not None:
        price = signal_data['price']
        source = "direct price field"
        
    # 2. Current price field 
    elif 'current_price' in signal_data and signal_data['current_price'] is not None:
        price = signal_data['current_price']
        source = "current_price field"
        
    # 3. Price in market data ticker
    elif 'market_data' in signal_data and isinstance(signal_data['market_data'], dict):
        market_data = signal_data['market_data']
        if 'ticker' in market_data and market_data['ticker']:
            ticker = market_data['ticker']
            if 'last' in ticker and ticker['last'] is not None:
                price = ticker['last']
                source = "market_data.ticker.last"
            elif 'close' in ticker and ticker['close'] is not None:
                price = ticker['close']
                source = "market_data.ticker.close"
    
    # 4. Price in components dictionary
    elif 'components' in signal_data and isinstance(signal_data['components'], dict):
        components = signal_data['components']
        if 'price' in components and components['price'] is not None:
            price = components['price']
            source = "components.price"
    
    # 5. Price in results or metadata
    if price is None and 'results' in signal_data and isinstance(signal_data['results'], dict):
        results = signal_data['results']
        
        # Direct price in results
        if 'price' in results and results['price'] is not None:
            price = results['price']
            source = "results.price"
            
        # Try common price field names
        else:
            price_fields = ['last_price', 'close_price', 'current_price']
            for field in price_fields:
                if field in results and results[field] is not None:
                    price = results[field]
                    source = f"results.{field}"
                    break
        
        # Check in metadata if present
        if price is None and 'metadata' in results and isinstance(results['metadata'], dict):
            metadata = results['metadata']
            if 'price' in metadata and metadata['price'] is not None:
                price = metadata['price']
                source = "results.metadata.price"
            elif 'last_price' in metadata and metadata['last_price'] is not None:
                price = metadata['last_price']
                source = "results.metadata.last_price"
    
    # Log the result of price resolution
    if price is not None:
        logger.debug(f"Resolved price{symbol_str}: {price} (source: {source})")
        
        # Convert to float if needed
        try:
            return float(price)
        except (ValueError, TypeError):
            logger.warning(f"Invalid price format{symbol_str}: {price} - cannot convert to float")
            return None
    else:
        logger.warning(f"Failed to resolve price{symbol_str} from any source")
        return None

def format_price_string(price: Optional[float]) -> str:
    """
    Format price as a readable string with appropriate decimal places.
    
    Args:
        price: Price value to format
        
    Returns:
        Formatted price string
    """
    if price is None:
        return "Price not available"
        
    # Format based on price magnitude
    if price < 1:
        return f"${price:.5f}"
    elif price < 1000:
        return f"${price:.2f}"
    else:
        return f"${price:,.2f}"  # Add commas for thousands 