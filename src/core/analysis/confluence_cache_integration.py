#!/usr/bin/env python3
"""Confluence Analysis Cache Integration Patch.

This module patches the confluence analysis process to automatically cache
results in the expected format for the mobile dashboard.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from src.core.cache.confluence_cache_service import confluence_cache_service


class ConfluenceAnalysisIntegrator:
    """Integrates caching with confluence analysis results."""
    
    def __init__(self):
        """Initialize the integrator."""
        self.logger = logging.getLogger(__name__)
        self.cache_service = confluence_cache_service
    
    async def process_and_cache_confluence_result(
        self,
        symbol: str,
        analysis_result: Dict[str, Any],
        cache_breakdown: bool = True
    ) -> Dict[str, Any]:
        """Process confluence analysis result and cache it properly.
        
        Args:
            symbol: Trading symbol
            analysis_result: Raw confluence analysis result
            cache_breakdown: Whether to cache the full breakdown
            
        Returns:
            Enhanced analysis result with caching status
        """
        try:
            # Cache the breakdown if requested
            if cache_breakdown:
                cache_success = await self.cache_service.cache_confluence_breakdown(
                    symbol, analysis_result
                )
                analysis_result['cached'] = cache_success
                analysis_result['cache_timestamp'] = analysis_result.get('timestamp', 0)
            
            # Enhance result with mobile-friendly data
            confluence_score = analysis_result.get('confluence_score', 0)
            
            # Add sentiment determination
            if confluence_score >= 70:
                sentiment = "BULLISH"
            elif confluence_score <= 30:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"
            
            analysis_result['sentiment'] = sentiment
            analysis_result['mobile_ready'] = True
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error processing confluence result for {symbol}: {e}")
            analysis_result['cached'] = False
            analysis_result['cache_error'] = str(e)
            return analysis_result
    
    async def bulk_cache_symbols(self, symbols_data: Dict[str, Dict[str, Any]]) -> int:
        """Cache confluence data for multiple symbols.
        
        Args:
            symbols_data: Dictionary mapping symbols to analysis results
            
        Returns:
            Number of successfully cached symbols
        """
        try:
            cached_count = await self.cache_service.cache_multiple_symbols(symbols_data)
            self.logger.info(f"Cached confluence data for {cached_count}/{len(symbols_data)} symbols")
            return cached_count
        except Exception as e:
            self.logger.error(f"Error in bulk cache operation: {e}")
            return 0


# Global integrator instance
confluence_integrator = ConfluenceAnalysisIntegrator()