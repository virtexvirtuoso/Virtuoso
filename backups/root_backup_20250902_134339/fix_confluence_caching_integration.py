#!/usr/bin/env python3
"""
Fix for Confluence Caching Integration

This script adds proper confluence breakdown caching to the signal processor
so that confluence analysis results are cached with the expected format:
- Key: confluence:breakdown:{symbol}  
- Data: Includes interpretations and component breakdowns
"""

import os
import sys

def fix_signal_processor():
    """Add confluence caching integration to signal processor."""
    
    signal_processor_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/signal_processor.py"
    
    # Read current file
    with open(signal_processor_path, 'r') as f:
        content = f.read()
    
    # Check if the cache service is already imported
    if "from src.core.cache.confluence_cache_service import confluence_cache_service" in content:
        print("✅ Confluence cache service already imported")
        cache_integration_needed = True
    else:
        # Add import
        import_line = "from src.core.cache.confluence_cache_service import confluence_cache_service"
        
        # Find a good place to add the import (after existing imports)
        import_section_end = content.find("\nclass SignalProcessor:")
        if import_section_end != -1:
            content = content[:import_section_end] + f"\n{import_line}" + content[import_section_end:]
            print("✅ Added confluence cache service import")
            cache_integration_needed = True
        else:
            print("❌ Could not find insertion point for import")
            return False
    
    # Add caching to the process_analysis_result method
    cache_code = '''
            # Cache confluence breakdown for mobile dashboard
            try:
                cache_success = await confluence_cache_service.cache_confluence_breakdown(symbol, result)
                if cache_success:
                    self.logger.debug(f"✅ Cached confluence breakdown for {symbol}")
                else:
                    self.logger.warning(f"⚠️ Failed to cache confluence breakdown for {symbol}")
            except Exception as cache_error:
                self.logger.error(f"❌ Error caching confluence breakdown for {symbol}: {cache_error}")
'''
    
    # Find the place to insert caching (after confluence score extraction but before signal generation)
    insertion_point = content.find("# Update metrics\n            if self.metrics_manager:")
    
    if insertion_point != -1:
        content = content[:insertion_point] + cache_code + "\n            " + content[insertion_point:]
        print("✅ Added confluence caching integration to signal processor")
    else:
        # Alternative insertion point - after processing interpretations
        alt_insertion = content.find("# Display comprehensive confluence score table")
        if alt_insertion != -1:
            content = content[:alt_insertion] + cache_code + "\n            " + content[alt_insertion:]
            print("✅ Added confluence caching integration to signal processor (alternative position)")
        else:
            print("❌ Could not find insertion point for caching code")
            return False
    
    # Write back the modified content
    with open(signal_processor_path, 'w') as f:
        f.write(content)
    
    return True

def create_cache_service_if_missing():
    """Create the confluence cache service if it doesn't exist."""
    
    cache_service_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/cache/confluence_cache_service.py"
    
    if os.path.exists(cache_service_path):
        print("✅ Confluence cache service already exists")
        return True
    
    # Create the cache directory if it doesn't exist
    cache_dir = os.path.dirname(cache_service_path)
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create __init__.py for cache package
    init_file = os.path.join(cache_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("# Cache package\n")
    
    cache_service_content = '''#!/usr/bin/env python3
"""Confluence Cache Service - Proper caching integration for confluence analysis results."""

import asyncio
import aiomcache
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime


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
            
            # Extract or generate interpretations
            interpretations = analysis_result.get('interpretations', {})
            if not interpretations:
                # Check for market_interpretations from signal processor
                market_interpretations = analysis_result.get('market_interpretations', [])
                if market_interpretations:
                    interpretations['overall'] = market_interpretations[0] if market_interpretations else f"Confluence score of {confluence_score:.1f} indicates {sentiment.lower()} bias"
                else:
                    # Generate basic interpretations if not present
                    interpretations = self._generate_basic_interpretations(
                        symbol, confluence_score, sentiment, components
                    )
            
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
            
            # Cache the breakdown with the expected key format
            breakdown_key = f'confluence:breakdown:{symbol}'
            await client.set(
                breakdown_key.encode(),
                json.dumps(breakdown).encode(),
                exptime=300  # 5 minutes TTL
            )
            
            # Also cache a simple score version
            simple_key = f'confluence:score:{symbol}'
            simple_data = {
                "score": confluence_score,
                "sentiment": sentiment,
                "timestamp": int(time.time())
            }
            await client.set(
                simple_key.encode(),
                json.dumps(simple_data).encode(),
                exptime=300
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
            breakdown_key = f'confluence:breakdown:{symbol}'
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
'''
    
    with open(cache_service_path, 'w') as f:
        f.write(cache_service_content)
    
    print("✅ Created confluence cache service")
    return True

def main():
    """Main function to apply the confluence caching fix."""
    
    print("🚀 Applying Confluence Caching Integration Fix...")
    print("=" * 60)
    
    # Step 1: Create cache service if missing
    if not create_cache_service_if_missing():
        print("❌ Failed to create cache service")
        return False
    
    # Step 2: Fix signal processor
    if not fix_signal_processor():
        print("❌ Failed to fix signal processor")
        return False
    
    print("=" * 60)
    print("✅ Confluence caching integration fix completed successfully!")
    print()
    print("What this fix does:")
    print("- Integrates confluence cache service into signal processor")  
    print("- Caches confluence breakdowns with key format: confluence:breakdown:{symbol}")
    print("- Includes interpretations and component scores")
    print("- Uses 5-minute TTL for cached data")
    print()
    print("Next steps:")
    print("1. Deploy to Hetzner VPS")
    print("2. Restart virtuoso.service")
    print("3. Test mobile-data endpoint")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)