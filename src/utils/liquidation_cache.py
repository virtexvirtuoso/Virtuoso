import os
import json
import time
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CACHE_DIR = "cache"
DEFAULT_CACHE_EXPIRY = 60 * 60  # 1 hour in seconds

class LiquidationCache:
    """
    Utility class for caching liquidation events.
    
    Provides file-based caching for liquidation events with expiry handling,
    validation, and multiple data source options.
    """
    
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, cache_expiry: int = DEFAULT_CACHE_EXPIRY):
        """
        Initialize the liquidation cache.
        
        Args:
            cache_dir: Directory to store cache files
            cache_expiry: Cache expiry time in seconds
        """
        self.cache_dir = cache_dir
        self.cache_expiry = cache_expiry
        os.makedirs(cache_dir, exist_ok=True)
        logger.debug(f"Initialized liquidation cache in {cache_dir} with {cache_expiry}s expiry")

    def save(self, liquidations: List[Dict[str, Any]], symbol: str) -> bool:
        """
        Save liquidation events to cache.
        
        Args:
            liquidations: List of liquidation events
            symbol: Trading pair symbol
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not liquidations:
            logger.debug(f"No liquidation events to cache for {symbol}")
            return False
            
        try:
            cache_file = os.path.join(self.cache_dir, f"liquidations_{symbol}.json")
            
            cache_data = {
                "timestamp": int(time.time()),
                "symbol": symbol,
                "data": liquidations
            }
            
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
                
            logger.info(f"Saved {len(liquidations)} liquidation events to cache for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving liquidations to cache: {e}")
            return False
    
    def load(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load liquidation events from cache if available and not expired.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of liquidation events or None if cache is invalid/expired
        """
        try:
            cache_file = os.path.join(self.cache_dir, f"liquidations_{symbol}.json")
            
            if not os.path.exists(cache_file):
                logger.debug(f"No cache file found for {symbol}")
                return None
                
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            cache_time = cache_data.get("timestamp", 0)
            cache_age_seconds = time.time() - cache_time
            if cache_age_seconds > self.cache_expiry:
                logger.debug(f"Cache for {symbol} is expired (age: {cache_age_seconds:.1f}s)")
                return None
                
            # Check if symbol matches
            if cache_data.get("symbol") != symbol:
                logger.debug(f"Cache symbol mismatch: {cache_data.get('symbol')} vs {symbol}")
                return None
                
            liquidations = cache_data.get("data", [])
            if liquidations:
                logger.info(f"Loaded {len(liquidations)} liquidation events from cache (age: {cache_age_seconds / 60:.1f} min)")
                return liquidations
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading liquidations from cache: {e}")
            return None
    
    def append(self, liquidation: Dict[str, Any], symbol: str = None) -> None:
        """
        Append a liquidation event to the existing cache file for the specified symbol.
        
        Args:
            liquidation: Liquidation event to append
            symbol: Symbol to append to (if None, uses the symbol from the liquidation)
        """
        try:
            logger.debug(f"Appending liquidation to cache for {symbol}")
            
            if symbol is None:
                symbol = liquidation.get('symbol', 'unknown')
                
            if not symbol:
                logger.warning("No symbol provided for liquidation cache append")
                return
                
            # Normalize symbol
            symbol = symbol.lower()
            
            # Create cache file name
            cache_file = os.path.join(self.cache_dir, f"{symbol}_liquidations.json")
            
            # Load existing data
            existing_data = []
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        existing_data = json.load(f)
                    logger.debug(f"Loaded {len(existing_data)} existing liquidation events from cache")
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse existing cache file: {cache_file}")
                    existing_data = []
                except Exception as e:
                    logger.warning(f"Error loading existing cache: {str(e)}")
                    existing_data = []
            
            # Append new data
            if not isinstance(existing_data, list):
                existing_data = []
                
            # Add timestamp if missing
            if 'timestamp' not in liquidation:
                liquidation['timestamp'] = int(time.time() * 1000)
                
            # Ensure required fields
            if 'side' not in liquidation:
                liquidation['side'] = 'unknown'
                
            existing_data.append(liquidation)
            
            # Clean expired events
            now = time.time() * 1000
            expiry_time = now - (self.cache_expiry * 1000)
            valid_data = [
                event for event in existing_data
                if event.get('timestamp', 0) > expiry_time
            ]
            
            # Save updated cache
            with open(cache_file, 'w') as f:
                json.dump(valid_data, f)
                
            cleaned_count = len(existing_data) - len(valid_data)
            logger.debug(f"Saved {len(valid_data)} liquidation events to cache (removed {cleaned_count} expired)")
            
            # Log statistics about the liquidation data
            long_count = sum(1 for e in valid_data if e.get('side', '').lower() == 'long')
            short_count = sum(1 for e in valid_data if e.get('side', '').lower() == 'short')
            logger.debug(f"Cache now contains: {len(valid_data)} events ({long_count} long, {short_count} short)")
            
        except Exception as e:
            logger.error(f"Error appending to liquidation cache: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def clean_expired(self) -> int:
        """
        Clean up expired cache files.
        
        Returns:
            int: Number of files removed
        """
        try:
            removed = 0
            current_time = time.time()
            
            for filename in os.listdir(self.cache_dir):
                if not filename.startswith("liquidations_"):
                    continue
                    
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        cache_data = json.load(f)
                    
                    # Check if cache is expired
                    cache_time = cache_data.get("timestamp", 0)
                    if current_time - cache_time > self.cache_expiry:
                        os.remove(filepath)
                        removed += 1
                        logger.debug(f"Removed expired cache file: {filename}")
                        
                except Exception as inner_e:
                    logger.warning(f"Error processing cache file {filename}: {inner_e}")
                    
            return removed
            
        except Exception as e:
            logger.error(f"Error cleaning expired cache files: {e}")
            return 0

# Global instance for easy access
liquidation_cache = LiquidationCache() 