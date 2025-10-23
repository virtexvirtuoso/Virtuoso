#!/usr/bin/env python3
"""Confluence Cache Service - Proper caching integration for confluence analysis results."""

import asyncio
import aiomcache
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.core.cache_keys import CacheKeys, CacheTTL


class ConfluenceCacheService:
    """Service to handle caching of confluence analysis results."""
    
    def __init__(self, memcached_host: str = "localhost", memcached_port: int = 11211):
        """Initialize the confluence cache service.
        
        Args:
            memcached_host: Memcached server host
            memcached_port: Memcached server port
        """
        self.memcached_host = memcached_host
        self.memcached_port = memcached_port
        self.logger = logging.getLogger(__name__)
        self._client = None
    
    async def get_client(self) -> aiomcache.Client:
        """Get or create memcached client."""
        if self._client is None:
            self._client = aiomcache.Client(self.memcached_host, self.memcached_port, pool_size=2)
        return self._client
    
    async def close_client(self):
        """Close memcached client."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def cache_confluence_breakdown(self, symbol: str, analysis_result: Dict[str, Any]) -> bool:
        """Cache confluence analysis breakdown in the expected format.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            analysis_result: Full confluence analysis result
            
        Returns:
            bool: True if caching successful, False otherwise
        """
        try:
            client = await self.get_client()
            
            # Extract key data from analysis result
            confluence_score = analysis_result.get('confluence_score', 0)
            reliability = analysis_result.get('reliability', 0)
            components = analysis_result.get('components', {})
            sub_components = analysis_result.get('sub_components', {})
            
            # Determine sentiment based on score
            if confluence_score >= 70:
                sentiment = "BULLISH"
            elif confluence_score <= 30:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"
            
            # Extract interpretations - preserve existing ones
            interpretations = analysis_result.get('interpretations', {})

            # DEBUG: Log what we received
            self.logger.info(f"[INTERP-CACHE] {symbol} - Received interpretations at top level: {list(interpretations.keys()) if interpretations else 'NONE'}")

            # Check for market_interpretations which contains proper formatted interpretations
            if not interpretations and 'results' in analysis_result:
                results = analysis_result.get('results', {})
                if 'market_interpretations' in results:
                    # Convert market_interpretations list to dict format
                    market_interps = results['market_interpretations']
                    self.logger.info(f"[INTERP-CACHE] {symbol} - Found {len(market_interps)} market_interpretations in results")
                    interpretations = {}
                    for interp in market_interps:
                        comp_name = interp.get('component', '')
                        interp_text = interp.get('interpretation', '')
                        if comp_name and interp_text:
                            interpretations[comp_name] = interp_text
                            # Ensure interp_text is a string before slicing
                            interp_str = str(interp_text) if not isinstance(interp_text, str) else interp_text
                            self.logger.debug(f"[INTERP-CACHE] {symbol} - Extracted {comp_name}: {interp_str[:80]}")
                    self.logger.info(f"[INTERP-CACHE] {symbol} - Converted to dict with keys: {list(interpretations.keys())}")
            
            # Only generate basic interpretations if absolutely none exist
            if not interpretations:
                # Generate basic interpretations if not present
                self.logger.warning(f"[INTERP-CACHE] {symbol} - No interpretations found, generating basic fallbacks")
                interpretations = self._generate_basic_interpretations(
                    symbol, confluence_score, sentiment, components
                )
            else:
                self.logger.info(f"[INTERP-CACHE] {symbol} - Using {len(interpretations)} interpretations from analysis_result")
            
            # Create the breakdown structure expected by mobile-data endpoint
            breakdown = {
                "overall_score": round(confluence_score, 2),
                "sentiment": sentiment,
                "reliability": reliability,
                "components": self._normalize_components(components),
                "sub_components": sub_components,
                "interpretations": interpretations,
                "timestamp": int(time.time()),
                "cached_at": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "has_breakdown": True,
                "real_confluence": True
            }
            
            # Cache the breakdown with the centralized key format
            breakdown_key = CacheKeys.confluence_breakdown(symbol)
            await client.set(
                breakdown_key.encode(),
                json.dumps(breakdown).encode(),
                exptime=CacheTTL.LONG  # 5 minutes TTL
            )

            # DEBUG: Log what we're actually caching
            cached_interp_keys = list(breakdown.get('interpretations', {}).keys())
            self.logger.info(f"[INTERP-CACHE] {symbol} - CACHED breakdown with {len(cached_interp_keys)} interpretations: {cached_interp_keys}")
            if cached_interp_keys:
                sample_key = cached_interp_keys[0]
                sample_text = breakdown['interpretations'][sample_key]
                # Ensure sample_text is a string before slicing
                sample_str = str(sample_text) if not isinstance(sample_text, str) else sample_text
                self.logger.info(f"[INTERP-CACHE] {symbol} - Sample cached {sample_key}: {sample_str[:100]}")

            # Also cache a simple score version
            simple_key = CacheKeys.confluence_score(symbol)
            simple_data = {
                "score": confluence_score,
                "sentiment": sentiment,
                "timestamp": int(time.time())
            }
            await client.set(
                simple_key.encode(),
                json.dumps(simple_data).encode(),
                exptime=CacheTTL.LONG
            )

            self.logger.info(f"✅ Cached confluence breakdown for {symbol}: {confluence_score:.2f} ({sentiment})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache confluence breakdown for {symbol}: {e}")
            return False
    
    def _normalize_components(self, components: Dict[str, Any]) -> Dict[str, float]:
        """Normalize component scores to expected format.
        
        Args:
            components: Raw component data from analysis
            
        Returns:
            Normalized component scores
        """
        normalized = {
            "technical": 50.0,
            "volume": 50.0,
            "orderflow": 50.0,
            "sentiment": 50.0,
            "orderbook": 50.0,
            "price_structure": 50.0
        }
        
        # Map component names and extract scores
        for key, value in components.items():
            score = value if isinstance(value, (int, float)) else value.get('score', 50.0) if isinstance(value, dict) else 50.0
            
            # Normalize component names
            normalized_key = key.lower().replace('_', '').replace(' ', '')
            
            if 'technical' in normalized_key or 'rsi' in normalized_key or 'ema' in normalized_key:
                normalized['technical'] = round(float(score), 2)
            elif 'volume' in normalized_key:
                normalized['volume'] = round(float(score), 2)
            elif 'orderflow' in normalized_key or 'flow' in normalized_key:
                normalized['orderflow'] = round(float(score), 2)
            elif 'sentiment' in normalized_key:
                normalized['sentiment'] = round(float(score), 2)
            elif 'orderbook' in normalized_key or 'book' in normalized_key:
                normalized['orderbook'] = round(float(score), 2)
            elif 'price' in normalized_key or 'structure' in normalized_key:
                normalized['price_structure'] = round(float(score), 2)
        
        return normalized
    
    def _generate_basic_interpretations(
        self, 
        symbol: str, 
        score: float, 
        sentiment: str, 
        components: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate basic interpretations when none are provided.
        
        Args:
            symbol: Trading symbol
            score: Overall confluence score
            sentiment: Market sentiment
            components: Component scores
            
        Returns:
            Basic interpretations for each component
        """
        interpretations = {}
        
        # Overall interpretation
        if score >= 70:
            interpretations['overall'] = f"Strong {sentiment.lower()} confluence detected for {symbol}. Multiple indicators align for high-confidence signal."
        elif score >= 50:
            interpretations['overall'] = f"Moderate {sentiment.lower()} bias for {symbol}. Some indicators support this direction."
        else:
            interpretations['overall'] = f"Weak or conflicting signals for {symbol}. Market shows uncertainty."
        
        # Component interpretations
        for component, value in components.items():
            comp_score = value if isinstance(value, (int, float)) else value.get('score', 50.0) if isinstance(value, dict) else 50.0
            
            if comp_score >= 70:
                interpretations[component] = f"{component.title()} shows strong bullish signals with score {comp_score:.1f}"
            elif comp_score <= 30:
                interpretations[component] = f"{component.title()} indicates bearish pressure with score {comp_score:.1f}"
            else:
                interpretations[component] = f"{component.title()} remains neutral with score {comp_score:.1f}"
        
        return interpretations
    
    async def get_cached_breakdown(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached confluence breakdown for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Cached breakdown data or None if not found
        """
        try:
            client = await self.get_client()
            breakdown_key = CacheKeys.confluence_breakdown(symbol)
            data = await client.get(breakdown_key.encode())
            
            if data:
                return json.loads(data.decode())
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached breakdown for {symbol}: {e}")
            return None
    
    async def cache_multiple_symbols(self, analysis_results: Dict[str, Dict[str, Any]]) -> int:
        """Cache confluence breakdowns for multiple symbols.
        
        Args:
            analysis_results: Dictionary mapping symbols to analysis results
            
        Returns:
            Number of successfully cached symbols
        """
        cached_count = 0
        
        for symbol, result in analysis_results.items():
            if await self.cache_confluence_breakdown(symbol, result):
                cached_count += 1
        
        return cached_count
    
    async def cleanup_expired_cache(self):
        """Clean up expired cache entries (handled by memcached TTL)."""
        # Memcached handles TTL automatically, but we can log cache status
        try:
            client = await self.get_client()
            # Could add cache statistics here if needed
            self.logger.debug("Cache cleanup completed")
        except Exception as e:
            self.logger.error(f"Cache cleanup error: {e}")


# Global instance for easy import
confluence_cache_service = ConfluenceCacheService()