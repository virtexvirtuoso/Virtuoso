"""Confluence Service for Dashboard Integration."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from src.core.analysis.confluence import ConfluenceAnalyzer


class ConfluenceService:
    """Service for managing confluence analysis requests."""
    
    def __init__(self):
        """Initialize the confluence service."""
        self.logger = logging.getLogger(__name__)
        self._confluence_analyzer = None
    
    @property
    def confluence_analyzer(self):
        """Get or create confluence analyzer."""
        if self._confluence_analyzer is None:
            self._confluence_analyzer = ConfluenceAnalyzer()
        return self._confluence_analyzer
    
    async def get_confluence_data(self, symbol: str) -> Dict[str, Any]:
        """Get confluence analysis for a symbol."""
        try:
            # Return cached or compute confluence analysis
            result = await self.confluence_analyzer.get_confluence_breakdown(symbol)
            return result if result else {}
        except Exception as e:
            self.logger.error(f"Error getting confluence data for {symbol}: {e}")
            return {}
    
    async def get_confluence_breakdown(self, symbol: str) -> Dict[str, Any]:
        """Get detailed confluence breakdown for a symbol."""
        try:
            result = await self.confluence_analyzer.get_confluence_breakdown(symbol)
            return result if result else {}
        except Exception as e:
            self.logger.error(f"Error getting confluence breakdown for {symbol}: {e}")
            return {}
    
    def get_cached_confluence(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached confluence data if available."""
        try:
            # Check if confluence analyzer has cached data
            if hasattr(self.confluence_analyzer, 'get_cached_data'):
                return self.confluence_analyzer.get_cached_data(symbol)
            return None
        except Exception as e:
            self.logger.error(f"Error getting cached confluence for {symbol}: {e}")
            return None


# Global instance
confluence_service = ConfluenceService()