"""
Simple correlation service that works without dependency injection.
Directly uses exchange manager from app state for immediate functionality.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio

from ..data import get_real_market_data_service
from ..resilience import handle_errors, RetryConfig

logger = logging.getLogger(__name__)


class SimpleCorrelationService:
    """
    Simplified correlation service that calculates real correlations and betas
    using direct market data access without complex dependency injection.
    """
    
    def __init__(self, exchange_manager=None):
        self.logger = logger
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize real market data service
        self.market_data_service = get_real_market_data_service(exchange_manager)
        
        # Default symbols for analysis
        self.default_symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", 
            "ADAUSDT", "DOTUSDT", "AVAXUSDT"
        ]
        
    @handle_errors(
        operation='get_price_data',
        component='correlation_service',
        retry_config=RetryConfig(max_attempts=3, base_delay=1.0)
    )
    async def get_price_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get real historical price data for symbol."""
        try:
            # Use real market data service to fetch OHLCV data
            df = await self.market_data_service.fetch_historical_ohlcv(
                symbol=symbol,
                timeframe='1d',
                days=days
            )
            
            if df.empty:
                raise ValueError(f"No historical data available for {symbol}")
            
            self.logger.info(f"✅ Retrieved {len(df)} days of real data for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to get real price data for {symbol}: {e}")
            raise ValueError(f"Real market data unavailable for {symbol}: {e}")
    
    async def get_price_data_from_integration(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Legacy method - delegates to main get_price_data method."""
        return await self.get_price_data(symbol, days)
    
    # Synthetic data generation methods removed for production safety
    # All market data must come from real exchange APIs
    
    @handle_errors(
        operation='calculate_correlation_matrix',
        component='correlation_service',
        retry_config=RetryConfig(max_attempts=2, base_delay=2.0)
    )
    async def calculate_correlation_matrix(self, symbols: List[str], days: int = 30) -> Dict[str, Any]:
        """
        Calculate correlation matrix using real market data.
        """
        try:
            # Fetch price data for all symbols concurrently
            self.logger.info(f"Fetching real market data for {len(symbols)} symbols over {days} days")
            
            symbol_data = {}
            successful_symbols = []
            failed_symbols = []
            
            # Fetch data for all symbols
            for symbol in symbols:
                try:
                    df = await self.get_price_data(symbol, days)
                    if not df.empty and 'returns' in df.columns and len(df) >= 10:
                        symbol_data[symbol] = df['returns'].dropna()
                        successful_symbols.append(symbol)
                        self.logger.info(f"✅ Got {len(df)} data points for {symbol}")
                    else:
                        failed_symbols.append(symbol)
                        self.logger.warning(f"⚠️ Insufficient data for {symbol} (got {len(df) if not df.empty else 0} points)")
                except Exception as e:
                    failed_symbols.append(symbol)
                    self.logger.error(f"❌ Failed to get data for {symbol}: {e}")
            
            if not symbol_data:
                return self._fallback_correlation_matrix(symbols, "No real market data available for any symbol")
            
            if len(symbol_data) < len(symbols):
                self.logger.warning(f"Only {len(symbol_data)}/{len(symbols)} symbols have data. Failed: {failed_symbols}")
            
            # Calculate correlation matrix using only symbols with data
            correlations = []
            working_symbols = list(symbol_data.keys())
            
            for i, sym1 in enumerate(symbols):
                row = []
                for j, sym2 in enumerate(symbols):
                    if i == j:
                        corr = 1.0
                    elif sym1 in symbol_data and sym2 in symbol_data:
                        # Calculate real correlation
                        returns1 = symbol_data[sym1]
                        returns2 = symbol_data[sym2]
                        
                        # Align the series by time index
                        aligned_data = pd.DataFrame({
                            'returns1': returns1,
                            'returns2': returns2
                        }).dropna()
                        
                        if len(aligned_data) >= 10:  # Need at least 10 observations
                            corr = aligned_data['returns1'].corr(aligned_data['returns2'])
                            if pd.isna(corr):
                                corr = 0.0
                        else:
                            corr = 0.0
                    else:
                        corr = None  # No data available
                    
                    row.append(round(float(corr), 3) if corr is not None else None)
                correlations.append(row)
            
            return {
                "symbols": symbols,
                "correlation_matrix": correlations,
                "timeframe": f"{days}d",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success" if len(failed_symbols) == 0 else "partial",
                "data_source": "real_market_data",
                "successful_symbols": successful_symbols,
                "failed_symbols": failed_symbols,
                "data_points_used": {sym: len(data) for sym, data in symbol_data.items()}
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation matrix: {e}")
            return self._fallback_correlation_matrix(symbols, str(e))
    
    async def calculate_beta_time_series(self, symbols: List[str], window_days: int = 30, num_windows: int = 7) -> Dict[str, Any]:
        """
        Calculate beta time series relative to Bitcoin.
        """
        try:
            # Get Bitcoin data first (benchmark)
            btc_df = await self.get_price_data_from_integration("BTCUSDT", window_days + num_windows)
            if btc_df.empty or 'returns' not in btc_df.columns:
                return self._fallback_beta_series(symbols, num_windows)
            
            series_data = {}
            
            for symbol in symbols:
                if symbol == "BTCUSDT":
                    continue  # Skip Bitcoin itself
                
                # Get asset data
                asset_df = await self.get_price_data_from_integration(symbol, window_days + num_windows)
                if asset_df.empty or 'returns' not in asset_df.columns:
                    continue
                
                data_points = []
                
                for i in range(num_windows):
                    end_date = datetime.utcnow() - timedelta(days=i)
                    
                    # Calculate beta for this window
                    if len(asset_df) >= window_days and len(btc_df) >= window_days:
                        # Get returns for the window
                        asset_returns = asset_df['returns'].iloc[-(window_days+i):-(i) if i > 0 else None]
                        btc_returns = btc_df['returns'].iloc[-(window_days+i):-(i) if i > 0 else None]
                        
                        # Align the data
                        min_len = min(len(asset_returns), len(btc_returns))
                        if min_len >= 10:
                            asset_returns = asset_returns.iloc[-min_len:]
                            btc_returns = btc_returns.iloc[-min_len:]
                            
                            # Calculate beta
                            covariance = np.cov(asset_returns, btc_returns)[0, 1]
                            btc_variance = np.var(btc_returns)
                            
                            if btc_variance > 0:
                                beta = covariance / btc_variance
                            else:
                                beta = 1.0
                        else:
                            beta = 1.0
                    else:
                        beta = 1.0
                    
                    data_points.append({
                        "date": end_date.strftime("%Y-%m-%d"),
                        "timestamp": int(end_date.timestamp() * 1000),
                        "beta": round(float(beta), 3)
                    })
                
                # Reverse for chronological order
                data_points.reverse()
                series_data[symbol] = data_points
            
            return {
                "series_data": series_data,
                "benchmark": "BTCUSDT",
                "window_size": f"{window_days}d",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating beta time series: {e}")
            return self._fallback_beta_series(symbols, num_windows)
    
    async def get_correlation_heatmap(self, symbols: List[str], days: int = 30) -> Dict[str, Any]:
        """
        Get correlation data formatted for heatmap visualization.
        """
        try:
            # Get correlation matrix
            matrix_result = await self.calculate_correlation_matrix(symbols, days)
            
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
                        "color_intensity": correlation_value
                    })
            
            # Calculate min/max for color scaling
            values = [d["value"] for d in heatmap_data if d["value"] is not None]
            min_corr = min(values) if values else 0
            max_corr = max(values) if values else 1
            
            return {
                "heatmap_data": heatmap_data,
                "symbols": symbols,
                "min_correlation": round(min_corr, 3),
                "max_correlation": round(max_corr, 3),
                "timestamp": matrix_result["timestamp"],
                "status": "success",
                "data_source": "calculated_from_available_data"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting correlation heatmap: {e}")
            return self._fallback_heatmap(symbols)
    
    def _fallback_correlation_matrix(self, symbols: List[str], error_msg: str = "Data unavailable") -> Dict[str, Any]:
        """Fallback correlation matrix with null values when real data fails."""
        correlations = []
        for i, sym1 in enumerate(symbols):
            row = []
            for j, sym2 in enumerate(symbols):
                if i == j:
                    row.append(1.0)
                else:
                    row.append(None)
            correlations.append(row)
        
        return {
            "symbols": symbols,
            "correlation_matrix": correlations,
            "timeframe": "unavailable",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "data_source": "fallback_null_values",
            "error_message": error_msg,
            "successful_symbols": [],
            "failed_symbols": symbols
        }
    
    def _fallback_beta_series(self, symbols: List[str], num_windows: int) -> Dict[str, Any]:
        """Fallback beta series with null values."""
        series_data = {}
        for symbol in symbols:
            if symbol == "BTCUSDT":
                continue
            
            data_points = []
            for i in range(num_windows):
                end_date = datetime.utcnow() - timedelta(days=i)
                data_points.append({
                    "date": end_date.strftime("%Y-%m-%d"),
                    "timestamp": int(end_date.timestamp() * 1000),
                    "beta": None
                })
            
            data_points.reverse()
            series_data[symbol] = data_points
        
        return {
            "series_data": series_data,
            "status": "partial",
            "message": "Real beta data temporarily unavailable"
        }
    
    def _fallback_heatmap(self, symbols: List[str]) -> Dict[str, Any]:
        """Fallback heatmap with null values."""
        heatmap_data = []
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                correlation = 1.0 if i == j else None
                heatmap_data.append({
                    "x": sym1,
                    "y": sym2,
                    "value": correlation,
                    "color_intensity": correlation if correlation is not None else 0
                })
        
        return {
            "heatmap_data": heatmap_data,
            "symbols": symbols,
            "min_correlation": 0.0,
            "max_correlation": 1.0,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "partial",
            "data_source": "fallback_null_values"
        }


# Global instance
_simple_correlation_service: Optional[SimpleCorrelationService] = None


def get_simple_correlation_service(exchange_manager=None) -> SimpleCorrelationService:
    """Get or create the simple correlation service singleton."""
    global _simple_correlation_service
    if _simple_correlation_service is None:
        _simple_correlation_service = SimpleCorrelationService(exchange_manager)
        logger.info("✅ Simple correlation service initialized with real market data")
    return _simple_correlation_service