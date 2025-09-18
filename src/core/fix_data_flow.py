"""
Fix Data Flow Issues

This module fixes data flow breaks caused by naming inconsistencies.
It integrates the naming mapper into key components to ensure data
flows correctly between producers and consumers.
"""

import logging
from typing import Dict, Any, List
from .naming_mapper import naming_mapper, get_sentiment_components

logger = logging.getLogger(__name__)


def patch_market_data_manager():
    """
    Patch MarketDataManager to use naming mapper for data normalization.
    """
    from src.core.market.market_data_manager import MarketDataManager
    
    # Store original methods
    original_fetch = MarketDataManager.fetch_market_data if hasattr(MarketDataManager, 'fetch_market_data') else None
    original_process = MarketDataManager._process_exchange_data if hasattr(MarketDataManager, '_process_exchange_data') else None
    
    async def patched_fetch_market_data(self, symbol: str, *args, **kwargs):
        """Fetch market data with naming normalization."""
        # Call original
        data = await original_fetch(self, symbol, *args, **kwargs) if original_fetch else {}
        
        # Normalize the data
        normalized = naming_mapper.normalize_dict(data, context='exchange_api')
        
        # Log normalization
        logger.debug(f"Normalized market data for {symbol}")
        
        return normalized
    
    def patched_process_exchange_data(self, data: Dict[str, Any], exchange: str = 'bybit'):
        """Process exchange data with naming normalization."""
        # Normalize incoming data
        normalized = naming_mapper.map_exchange_response(data, exchange)
        
        # Call original processing if exists
        if original_process:
            result = original_process(self, normalized)
        else:
            result = normalized
        
        return result
    
    # Apply patches
    if original_fetch:
        MarketDataManager.fetch_market_data = patched_fetch_market_data
        logger.info("Patched MarketDataManager.fetch_market_data with naming normalization")
    
    if original_process:
        MarketDataManager._process_exchange_data = patched_process_exchange_data
        logger.info("Patched MarketDataManager._process_exchange_data with naming normalization")


def patch_confluence_analyzer():
    """
    Patch ConfluenceAnalyzer to handle naming variations in sentiment data.
    """
    from src.core.analysis.confluence import ConfluenceAnalyzer
    
    # Store original method
    original_analyze = ConfluenceAnalyzer.analyze_confluence if hasattr(ConfluenceAnalyzer, 'analyze_confluence') else None
    
    async def patched_analyze_confluence(self, symbol: str, data: Dict[str, Any], *args, **kwargs):
        """Analyze confluence with naming normalization."""
        # Normalize incoming data
        normalized_data = naming_mapper.normalize_dict(data)
        
        # Ensure sentiment components are available
        if 'sentiment' in normalized_data:
            sentiment = normalized_data['sentiment']
            
            # Fix common naming issues
            if 'market_mood' in sentiment and 'market_sentiment' not in sentiment:
                sentiment['market_sentiment'] = sentiment['market_mood']
            
            if 'risk_limits' in sentiment and 'risk' not in sentiment:
                sentiment['risk'] = sentiment['risk_limits']
            
            # Ensure all expected components exist
            for component in get_sentiment_components():
                if component not in sentiment:
                    logger.warning(f"Missing sentiment component: {component}")
        
        # Call original
        result = await original_analyze(self, symbol, normalized_data, *args, **kwargs) if original_analyze else normalized_data
        
        return result
    
    # Apply patch
    if original_analyze:
        ConfluenceAnalyzer.analyze_confluence = patched_analyze_confluence
        logger.info("Patched ConfluenceAnalyzer.analyze_confluence with naming normalization")


def fix_sentiment_default_components():
    """
    Fix the default sentiment components list to include all components.
    """
    # Import the module that defines default components
    try:
        import src.core.exchanges.bybit as bybit_module
        
        # Update default sentiment indicators
        if hasattr(bybit_module, 'DEFAULT_SENTIMENT_INDICATORS'):
            original = bybit_module.DEFAULT_SENTIMENT_INDICATORS
            updated = get_sentiment_components()
            
            # Update the module attribute
            bybit_module.DEFAULT_SENTIMENT_INDICATORS = updated
            logger.info(f"Updated DEFAULT_SENTIMENT_INDICATORS from {original} to {updated}")
        
        # Also update in BybitExchange class if it exists
        if hasattr(bybit_module, 'BybitExchange'):
            BybitExchange = bybit_module.BybitExchange
            
            # Store original method
            original_get_sentiment = BybitExchange.get_sentiment_indicators if hasattr(BybitExchange, 'get_sentiment_indicators') else None
            
            async def patched_get_sentiment_indicators(self, symbol: str, indicators: List[str] = None):
                """Get sentiment indicators with all components."""
                # Use all components if not specified
                if not indicators:
                    indicators = get_sentiment_components()
                
                # Call original
                result = await original_get_sentiment(self, symbol, indicators) if original_get_sentiment else {}
                
                # Normalize the result
                normalized = naming_mapper.normalize_dict(result)
                
                return normalized
            
            # Apply patch
            if original_get_sentiment:
                BybitExchange.get_sentiment_indicators = patched_get_sentiment_indicators
                logger.info("Patched BybitExchange.get_sentiment_indicators to include all components")
    
    except ImportError as e:
        logger.warning(f"Could not import bybit module for patching: {e}")


def patch_cache_adapter():
    """
    Patch cache adapter to handle naming variations when storing/retrieving data.
    """
    try:
        from src.api.cache_adapter_direct import CacheAdapterDirect
        
        # Store original methods
        original_get = CacheAdapterDirect.get if hasattr(CacheAdapterDirect, 'get') else None
        original_set = CacheAdapterDirect.set if hasattr(CacheAdapterDirect, 'set') else None
        
        async def patched_get(self, key: str):
            """Get from cache with key normalization."""
            # Try with original key
            result = await original_get(self, key) if original_get else None
            
            # If not found, try normalized key
            if result is None:
                normalized_key = naming_mapper.normalize_key(key)
                if normalized_key != key:
                    result = await original_get(self, normalized_key) if original_get else None
                    if result:
                        logger.debug(f"Found data under normalized key: {key} -> {normalized_key}")
            
            # Normalize the result if it's a dict
            if isinstance(result, dict):
                result = naming_mapper.normalize_dict(result)
            
            return result
        
        async def patched_set(self, key: str, value: Any, ttl: int = None):
            """Set in cache with key normalization."""
            # Normalize the key
            normalized_key = naming_mapper.normalize_key(key)
            
            # Normalize value if it's a dict
            if isinstance(value, dict):
                value = naming_mapper.normalize_dict(value)
            
            # Store under both original and normalized keys for compatibility
            if original_set:
                await original_set(self, key, value, ttl)
                if normalized_key != key:
                    await original_set(self, normalized_key, value, ttl)
                    logger.debug(f"Stored under both keys: {key} and {normalized_key}")
        
        # Apply patches
        if original_get:
            CacheAdapterDirect.get = patched_get
            logger.info("Patched CacheAdapterDirect.get with naming normalization")
        
        if original_set:
            CacheAdapterDirect.set = patched_set
            logger.info("Patched CacheAdapterDirect.set with naming normalization")
    
    except ImportError as e:
        logger.warning(f"Could not import cache adapter for patching: {e}")


def apply_all_data_flow_fixes():
    """
    Apply all data flow fixes to ensure components can communicate.
    """
    logger.info("Applying all data flow fixes...")
    
    # Fix MarketDataManager
    patch_market_data_manager()
    
    # Fix ConfluenceAnalyzer
    patch_confluence_analyzer()
    
    # Fix default sentiment components
    fix_sentiment_default_components()
    
    # Fix cache adapter
    patch_cache_adapter()
    
    logger.info("All data flow fixes applied successfully")
    
    # Log summary of fixes
    logger.info("Summary of fixes applied:")
    logger.info("- MarketDataManager: Normalized exchange data")
    logger.info("- ConfluenceAnalyzer: Fixed sentiment naming")
    logger.info("- Sentiment components: Added missing defaults")
    logger.info("- Cache adapter: Normalized key access")
    logger.info(f"- Total naming mappings: {len(naming_mapper.NAMING_MAPPINGS)}")


# Auto-apply fixes on import
apply_all_data_flow_fixes()