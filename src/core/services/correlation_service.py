"""
Correlation Service for Virtuoso CCXT Trading System
Integrates with dependency injection system and provides real correlation calculations.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from src.core.analysis.correlation_calculator import CorrelationCalculator
from src.core.interfaces.services import IExchangeManagerService

logger = logging.getLogger(__name__)


class CorrelationService:
    """
    Service class for managing correlation and beta calculations.
    Integrates with the dependency injection system.
    """
    
    def __init__(self, exchange_manager: IExchangeManagerService):
        """
        Initialize the correlation service.
        
        Args:
            exchange_manager: Exchange manager service from DI container
        """
        self.exchange_manager = exchange_manager
        self.calculator = CorrelationCalculator(exchange_manager)
        self.logger = logger
        
        # Default symbols for correlation analysis
        self.default_symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", 
            "ADAUSDT", "DOTUSDT", "AVAXUSDT"
        ]
        
    async def get_correlation_matrix(
        self, 
        symbols: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get real correlation matrix for symbols.
        
        Args:
            symbols: List of symbols (defaults to predefined list)
            days: Number of days for analysis
            
        Returns:
            Dictionary with correlation matrix data
        """
        if symbols is None:
            symbols = self.default_symbols
            
        try:
            result = await self.calculator.calculate_correlation_matrix(symbols, days)
            return result
        except Exception as e:
            self.logger.error(f"Error getting correlation matrix: {e}")
            return {
                "status": "error",
                "error": str(e),
                "symbols": symbols,
                "correlation_matrix": [[None for _ in symbols] for _ in symbols],
                "data_source": "error_fallback"
            }
    
    async def get_beta_time_series(
        self, 
        symbols: Optional[List[str]] = None,
        window_days: int = 30,
        num_windows: int = 7
    ) -> Dict[str, Any]:
        """
        Get beta time series data.
        
        Args:
            symbols: List of symbols (defaults to predefined list)
            window_days: Days per calculation window
            num_windows: Number of time windows
            
        Returns:
            Dictionary with time series beta data
        """
        if symbols is None:
            symbols = [s for s in self.default_symbols if s != "BTCUSDT"]  # Exclude Bitcoin benchmark
            
        try:
            result = await self.calculator.calculate_beta_time_series(
                symbols, window_days, num_windows
            )
            return result
        except Exception as e:
            self.logger.error(f"Error getting beta time series: {e}")
            return {
                "status": "error",
                "error": str(e),
                "series_data": {}
            }
    
    async def get_correlation_heatmap(
        self, 
        symbols: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get correlation data formatted for heatmap visualization.
        
        Args:
            symbols: List of symbols (defaults to predefined list)
            days: Number of days for analysis
            
        Returns:
            Dictionary with heatmap-formatted correlation data
        """
        if symbols is None:
            symbols = self.default_symbols
            
        try:
            # Get correlation matrix
            matrix_result = await self.get_correlation_matrix(symbols, days)
            
            if matrix_result["status"] != "success":
                return matrix_result
            
            # Format for heatmap
            heatmap_data = []
            correlation_matrix = matrix_result["correlation_matrix"]
            
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols):
                    correlation_value = correlation_matrix[i][j]
                    
                    heatmap_data.append({
                        "x": sym1,
                        "y": sym2,
                        "value": correlation_value,
                        "color_intensity": correlation_value if correlation_value is not None else 0
                    })
            
            return {
                "heatmap_data": heatmap_data,
                "symbols": symbols,
                "min_correlation": min([d["value"] for d in heatmap_data if d["value"] is not None], default=0),
                "max_correlation": max([d["value"] for d in heatmap_data if d["value"] is not None], default=1),
                "timestamp": matrix_result["timestamp"],
                "status": "success",
                "data_source": "real_market_data"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting correlation heatmap: {e}")
            return {
                "status": "error",
                "error": str(e),
                "heatmap_data": [],
                "symbols": symbols
            }
    
    async def get_individual_beta(self, symbol: str, days: int = 30) -> Optional[float]:
        """
        Get beta coefficient for a single symbol.
        
        Args:
            symbol: Trading pair symbol
            days: Number of days for analysis
            
        Returns:
            Beta coefficient or None if calculation fails
        """
        try:
            beta_result = await self.calculator.calculate_beta(symbol, days=days)
            return beta_result.beta if beta_result else None
        except Exception as e:
            self.logger.error(f"Error getting beta for {symbol}: {e}")
            return None
    
    async def get_performance_vs_beta_data(
        self,
        symbols: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance vs beta scatter plot data.
        
        Args:
            symbols: List of symbols
            days: Number of days for analysis
            
        Returns:
            Dictionary with scatter plot data
        """
        if symbols is None:
            symbols = self.default_symbols
            
        try:
            scatter_data = []
            
            for symbol in symbols:
                # Get beta
                beta_result = await self.calculator.calculate_beta(symbol, days=days)
                beta_value = beta_result.beta if beta_result else 1.0 if symbol == "BTCUSDT" else None
                
                # Get recent performance (placeholder - would need price data)
                # For now, we'll use a simple calculation or default
                performance = 0.0  # This would be calculated from recent price changes
                
                if beta_value is not None:
                    scatter_data.append({
                        "symbol": symbol,
                        "beta": round(beta_value, 3),
                        "performance": round(performance, 2),
                        "market_cap": 100  # Placeholder
                    })
            
            # Calculate averages
            if scatter_data:
                avg_beta = sum(d['beta'] for d in scatter_data) / len(scatter_data)
                avg_performance = sum(d['performance'] for d in scatter_data) / len(scatter_data)
            else:
                avg_beta = avg_performance = 0
            
            return {
                "scatter_data": scatter_data,
                "averages": {
                    "beta": round(avg_beta, 2),
                    "performance": round(avg_performance, 2)
                },
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance vs beta data: {e}")
            return {
                "status": "error",
                "error": str(e),
                "scatter_data": []
            }
    
    def clear_cache(self):
        """Clear correlation calculation cache."""
        self.calculator.clear_cache()
        self.logger.info("Correlation service cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.calculator.get_cache_stats()


# Singleton instance - will be initialized by dependency injection
_correlation_service: Optional[CorrelationService] = None


async def get_correlation_service(exchange_manager: IExchangeManagerService = None) -> CorrelationService:
    """
    Get or create the correlation service singleton.
    
    Args:
        exchange_manager: Exchange manager service (optional, for DI)
        
    Returns:
        CorrelationService instance
    """
    global _correlation_service
    
    if _correlation_service is None and exchange_manager is not None:
        _correlation_service = CorrelationService(exchange_manager)
        logger.info("✅ Correlation service initialized")
    
    return _correlation_service