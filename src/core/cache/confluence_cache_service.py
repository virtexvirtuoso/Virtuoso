#!/usr/bin/env python3
"""Confluence Cache Service - Proper caching integration for confluence analysis results."""

import asyncio
import aiomcache
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
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
        # Score history for sparkline visualization
        self._score_history: Dict[str, List[float]] = {}
        self._score_history_max_size = 24  # Keep last 24 readings (~12 mins at 30s intervals)
    
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

            # Standardize interpretations - convert dicts to prose and enrich short ones
            interpretations = self._standardize_interpretations(interpretations, components)

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
            
            # Update score history for sparkline visualization
            # Only append if score changed (avoids duplicate consecutive values)
            if symbol not in self._score_history:
                self._score_history[symbol] = []
            rounded_score = round(confluence_score, 1)
            # Only add if history is empty or score differs from the last recorded value
            if not self._score_history[symbol] or self._score_history[symbol][-1] != rounded_score:
                self._score_history[symbol].append(rounded_score)
                # Maintain rolling buffer
                if len(self._score_history[symbol]) > self._score_history_max_size:
                    self._score_history[symbol] = self._score_history[symbol][-self._score_history_max_size:]

            # Create the breakdown structure expected by mobile-data endpoint
            breakdown = {
                "overall_score": round(confluence_score, 2),
                "sentiment": sentiment,
                "reliability": reliability,
                "components": self._normalize_components(components),
                "sub_components": sub_components,
                "interpretations": interpretations,
                "timestamp": int(time.time()),
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "has_breakdown": True,
                "real_confluence": True,
                "score_history": self._score_history[symbol].copy()  # Include score history for sparklines
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

            history_len = len(self._score_history.get(symbol, []))
            self.logger.info(f"✅ Cached confluence breakdown for {symbol}: {confluence_score:.2f} ({sentiment}) [history: {history_len} pts]")
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

    def _standardize_interpretations(
        self,
        interpretations: Dict[str, Any],
        components: Dict[str, Any]
    ) -> Dict[str, str]:
        """Standardize interpretations to ensure consistent, rich prose output.

        Fixes:
        1. Converts dict interpretations (like sentiment) to prose
        2. Enriches short interpretations with score-based context

        Args:
            interpretations: Raw interpretations dict (may contain dicts or short strings)
            components: Component scores for context

        Returns:
            Standardized interpretations as strings
        """
        if not interpretations:
            return {}

        result = {}
        for comp, interp in interpretations.items():
            comp_score = components.get(comp, 50)
            if isinstance(comp_score, dict):
                comp_score = comp_score.get('score', 50)
            comp_score = float(comp_score) if comp_score else 50

            # Handle sentiment dict -> prose conversion
            if comp == 'sentiment' and isinstance(interp, dict):
                parts = []
                if interp.get('sentiment'):
                    parts.append(str(interp['sentiment']))
                if interp.get('funding_rate'):
                    parts.append(f"with {str(interp['funding_rate']).lower()}")
                if interp.get('long_short_ratio'):
                    parts.append(f"and {str(interp['long_short_ratio']).lower()}")
                if interp.get('market_activity'):
                    parts.append(f"amid {str(interp['market_activity']).lower()}")

                base = ". ".join(parts) + "." if parts else "Neutral market sentiment."

                # Add score-based context
                if comp_score >= 65:
                    base += " Strong bullish sentiment suggests continuation of upward momentum with high conviction from market participants."
                elif comp_score >= 55:
                    base += " Moderately bullish sentiment supports upward price action with reasonable conviction."
                elif comp_score <= 35:
                    base += " Strong bearish sentiment suggests continuation of downward momentum with high conviction from market participants."
                elif comp_score <= 45:
                    base += " Moderately bearish sentiment supports downward price action with reasonable conviction."
                else:
                    base += " Neutral sentiment indicates market indecision with no clear directional bias."
                result[comp] = base

            # Enrich short orderflow interpretation
            elif comp == 'orderflow' and isinstance(interp, str) and len(interp) < 250:
                if comp_score >= 60:
                    extra = " Buying pressure dominates with strong accumulation patterns. Large orders are predominantly on the bid side, suggesting institutional buying interest. Volume-weighted order flow supports upward price movement."
                elif comp_score <= 40:
                    extra = " Selling pressure dominates with distribution patterns evident. Large orders are predominantly on the ask side, suggesting institutional selling interest. Volume-weighted order flow supports downward price movement."
                else:
                    extra = " Order flow shows equilibrium between buyers and sellers. Large orders are evenly distributed across both sides. This balance suggests potential consolidation or range-bound price action."
                result[comp] = interp + extra

            # Enrich short price_structure interpretation
            elif comp == 'price_structure' and isinstance(interp, str) and len(interp) < 150:
                if comp_score >= 60:
                    extra = " Key support levels are holding firm with higher lows forming. Resistance levels are being tested with increasing momentum. The overall structure favors bullish continuation with well-defined risk levels."
                elif comp_score <= 40:
                    extra = " Key support levels are breaking down with lower highs forming. Resistance levels are capping price advances. The overall structure favors bearish continuation with breakdown targets in focus."
                else:
                    extra = " Price is consolidating within a defined range. Support and resistance levels are well-established, creating a balanced trading environment. Breakout direction will likely determine the next trend."
                result[comp] = interp + extra
            else:
                # Ensure string type
                result[comp] = str(interp) if not isinstance(interp, str) else interp

        return result

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
                breakdown = json.loads(data.decode())
                # Apply standardization on read to fix any legacy cached data
                if 'interpretations' in breakdown and 'components' in breakdown:
                    breakdown['interpretations'] = self._standardize_interpretations(
                        breakdown.get('interpretations', {}),
                        breakdown.get('components', {})
                    )
                return breakdown
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