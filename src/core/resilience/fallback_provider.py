"""Fallback data provider for graceful degradation."""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FallbackDataProvider:
    """Provides fallback data when external services are unavailable."""
    
    def __init__(self):
        """Initialize fallback data provider."""
        self.cache_dir = Path("cache/fallback")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Default fallback data
        self.default_ticker = {
            "symbol": "BTCUSDT",
            "last": 0,
            "bid": 0,
            "ask": 0,
            "volume": 0,
            "timestamp": int(time.time() * 1000),
            "status": "fallback"
        }
        
        self.default_market_overview = {
            "total_volume_24h": 0,
            "active_symbols": 0,
            "top_gainers": [],
            "top_losers": [],
            "status": "degraded",
            "message": "Using cached data - external services unavailable"
        }
        
        self.default_signals = {
            "signals": [],
            "total": 0,
            "strong": 0,
            "medium": 0,
            "weak": 0,
            "status": "cached"
        }
    
    async def get_ticker_fallback(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get fallback ticker data.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            Fallback ticker data
        """
        # Try to load from cache first
        cache_file = self.cache_dir / f"ticker_{exchange}_{symbol}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is not too old (1 hour)
                    if time.time() - data.get("cached_at", 0) < 3600:
                        data["status"] = "cached"
                        logger.info(f"Using cached ticker data for {symbol}")
                        return data
            except Exception as e:
                logger.error(f"Error loading cached ticker: {e}")
        
        # Return default with symbol
        fallback = self.default_ticker.copy()
        fallback["symbol"] = symbol
        fallback["exchange"] = exchange
        fallback["message"] = "External API unavailable - showing default values"
        logger.warning(f"Using default fallback for {symbol}")
        return fallback
    
    async def get_market_overview_fallback(self) -> Dict[str, Any]:
        """Get fallback market overview data.
        
        Returns:
            Fallback market overview
        """
        # Try to load from cache
        cache_file = self.cache_dir / "market_overview.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is not too old (15 minutes)
                    if time.time() - data.get("cached_at", 0) < 900:
                        data["status"] = "cached"
                        data["age_minutes"] = int((time.time() - data["cached_at"]) / 60)
                        logger.info("Using cached market overview")
                        return data
            except Exception as e:
                logger.error(f"Error loading cached market overview: {e}")
        
        # Return default
        logger.warning("Using default fallback for market overview")
        return self.default_market_overview.copy()
    
    async def get_signals_fallback(self) -> Dict[str, Any]:
        """Get fallback signals data.
        
        Returns:
            Fallback signals
        """
        # Try to load from cache
        cache_file = self.cache_dir / "signals.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is not too old (30 minutes)
                    if time.time() - data.get("cached_at", 0) < 1800:
                        data["status"] = "cached"
                        data["age_minutes"] = int((time.time() - data["cached_at"]) / 60)
                        logger.info("Using cached signals")
                        return data
            except Exception as e:
                logger.error(f"Error loading cached signals: {e}")
        
        # Return default
        logger.warning("Using default fallback for signals")
        return self.default_signals.copy()
    
    def save_to_cache(self, data_type: str, data: Dict[str, Any], key: Optional[str] = None):
        """Save data to cache for future fallback use.
        
        Args:
            data_type: Type of data (ticker, market_overview, signals)
            data: Data to cache
            key: Optional key for specific data (e.g., symbol for ticker)
        """
        try:
            data["cached_at"] = time.time()
            
            if data_type == "ticker" and key:
                cache_file = self.cache_dir / f"ticker_{key}.json"
            else:
                cache_file = self.cache_dir / f"{data_type}.json"
            
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            logger.debug(f"Saved {data_type} to cache")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of fallback system.
        
        Returns:
            Health status information
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        
        cache_stats = {}
        for file in cache_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    age = time.time() - data.get("cached_at", 0)
                    cache_stats[file.stem] = {
                        "age_seconds": int(age),
                        "age_readable": f"{int(age/60)}m {int(age%60)}s"
                    }
            except:
                pass
        
        return {
            "status": "operational",
            "cache_dir": str(self.cache_dir),
            "cached_files": len(cache_files),
            "cache_stats": cache_stats
        }


# Global instance
_fallback_provider: Optional[FallbackDataProvider] = None


def get_fallback_provider() -> FallbackDataProvider:
    """Get global fallback provider instance."""
    global _fallback_provider
    if _fallback_provider is None:
        _fallback_provider = FallbackDataProvider()
    return _fallback_provider
