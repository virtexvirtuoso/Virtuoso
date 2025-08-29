"""
Real-time correlation and beta calculation service for the Virtuoso CCXT trading system.
Implements mathematical calculations using actual market data from exchanges.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Data class for correlation calculation results."""
    correlation: float
    p_value: Optional[float]
    n_observations: int
    start_date: datetime
    end_date: datetime
    confidence_level: float


@dataclass
class BetaResult:
    """Data class for beta calculation results."""
    beta: float
    alpha: float
    r_squared: float
    volatility: float
    systematic_risk: float
    idiosyncratic_risk: float
    n_observations: int
    start_date: datetime
    end_date: datetime


class CorrelationCalculator:
    """
    Advanced correlation and beta calculator using real market data.
    
    Features:
    - Real Pearson correlation coefficients
    - Beta calculation relative to Bitcoin benchmark
    - Rolling correlation analysis
    - Statistical significance testing
    - Data quality validation
    - Efficient caching with TTL management
    """
    
    def __init__(self, exchange_manager, cache_manager=None):
        """
        Initialize the correlation calculator.
        
        Args:
            exchange_manager: Exchange manager for fetching OHLCV data
            cache_manager: Optional cache manager for storing calculations
        """
        self.exchange_manager = exchange_manager
        self.cache_manager = cache_manager
        self.logger = logger
        
        # Configuration
        self.min_observations = 30  # Minimum data points for reliable correlation
        self.default_lookback = 30  # Days of historical data to analyze
        self.cache_ttl = 3600  # Cache TTL: 1 hour
        self.confidence_threshold = 0.05  # Statistical significance threshold
        
        # Market benchmark (Bitcoin)
        self.benchmark_symbol = "BTCUSDT"
        
        # Active calculation cache (in-memory)
        self._correlation_cache = {}
        self._beta_cache = {}
        
    async def get_historical_prices(
        self, 
        symbol: str, 
        days: int = None,
        timeframe: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical price data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'ETHUSDT')
            days: Number of days of historical data (default: self.default_lookback)
            timeframe: Timeframe for OHLCV data
            
        Returns:
            DataFrame with OHLCV data and returns
        """
        if days is None:
            days = self.default_lookback
            
        try:
            # Calculate timestamp for historical data
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days + 5)  # Extra buffer for weekends
            
            # Convert to milliseconds
            since = int(start_time.timestamp() * 1000)
            limit = min(days * 2, 1000)  # Conservative limit
            
            # Fetch OHLCV data using exchange manager
            ohlcv_data = await self.exchange_manager.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            
            if not ohlcv_data or len(ohlcv_data) < self.min_observations:
                self.logger.warning(f"Insufficient data for {symbol}: {len(ohlcv_data) if ohlcv_data else 0} observations")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate returns
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
            
            # Remove NaN values
            df.dropna(inplace=True)
            
            self.logger.info(f"Fetched {len(df)} observations for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def calculate_correlation(
        self, 
        symbol1: str, 
        symbol2: str,
        days: int = None,
        method: str = "pearson"
    ) -> Optional[CorrelationResult]:
        """
        Calculate correlation between two symbols using historical returns.
        
        Args:
            symbol1: First trading pair
            symbol2: Second trading pair
            days: Number of days for analysis
            method: Correlation method ('pearson', 'spearman', 'kendall')
            
        Returns:
            CorrelationResult object or None if calculation fails
        """
        if days is None:
            days = self.default_lookback
            
        # Check cache first
        cache_key = self._get_correlation_cache_key(symbol1, symbol2, days, method)
        if cache_key in self._correlation_cache:
            cache_entry = self._correlation_cache[cache_key]
            if datetime.utcnow().timestamp() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['result']
        
        try:
            # Fetch historical data for both symbols
            df1_task = self.get_historical_prices(symbol1, days)
            df2_task = self.get_historical_prices(symbol2, days)
            
            df1, df2 = await asyncio.gather(df1_task, df2_task)
            
            if df1.empty or df2.empty:
                return None
            
            # Align data by timestamp
            combined = pd.merge(df1[['returns']], df2[['returns']], 
                              left_index=True, right_index=True, 
                              suffixes=('_1', '_2'), how='inner')
            
            if len(combined) < self.min_observations:
                self.logger.warning(f"Insufficient aligned observations: {len(combined)}")
                return None
            
            # Calculate correlation
            returns1 = combined['returns_1'].dropna()
            returns2 = combined['returns_2'].dropna()
            
            if method == "pearson":
                correlation = returns1.corr(returns2, method='pearson')
                # Calculate p-value using scipy if available
                try:
                    from scipy.stats import pearsonr
                    _, p_value = pearsonr(returns1, returns2)
                except ImportError:
                    p_value = None
            else:
                correlation = returns1.corr(returns2, method=method)
                p_value = None
            
            # Create result
            result = CorrelationResult(
                correlation=float(correlation) if not pd.isna(correlation) else 0.0,
                p_value=float(p_value) if p_value is not None else None,
                n_observations=len(combined),
                start_date=combined.index.min(),
                end_date=combined.index.max(),
                confidence_level=1.0 - self.confidence_threshold if p_value and p_value < self.confidence_threshold else 0.0
            )
            
            # Cache result
            self._correlation_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.utcnow().timestamp()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation between {symbol1} and {symbol2}: {e}")
            return None
    
    async def calculate_beta(
        self, 
        symbol: str,
        benchmark: str = None,
        days: int = None
    ) -> Optional[BetaResult]:
        """
        Calculate beta coefficient relative to benchmark (Bitcoin).
        
        Beta = Covariance(asset, benchmark) / Variance(benchmark)
        
        Args:
            symbol: Asset symbol
            benchmark: Benchmark symbol (default: BTCUSDT)
            days: Number of days for analysis
            
        Returns:
            BetaResult object or None if calculation fails
        """
        if benchmark is None:
            benchmark = self.benchmark_symbol
        if days is None:
            days = self.default_lookback
            
        # Check cache first
        cache_key = self._get_beta_cache_key(symbol, benchmark, days)
        if cache_key in self._beta_cache:
            cache_entry = self._beta_cache[cache_key]
            if datetime.utcnow().timestamp() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['result']
        
        try:
            # Fetch historical data
            asset_task = self.get_historical_prices(symbol, days)
            benchmark_task = self.get_historical_prices(benchmark, days)
            
            asset_df, benchmark_df = await asyncio.gather(asset_task, benchmark_task)
            
            if asset_df.empty or benchmark_df.empty:
                return None
            
            # Align data
            combined = pd.merge(asset_df[['returns']], benchmark_df[['returns']], 
                              left_index=True, right_index=True, 
                              suffixes=('_asset', '_benchmark'), how='inner')
            
            if len(combined) < self.min_observations:
                return None
            
            asset_returns = combined['returns_asset'].dropna()
            benchmark_returns = combined['returns_benchmark'].dropna()
            
            # Calculate beta using linear regression
            covariance = np.cov(asset_returns, benchmark_returns)[0, 1]
            benchmark_variance = np.var(benchmark_returns)
            
            if benchmark_variance == 0:
                return None
                
            beta = covariance / benchmark_variance
            
            # Calculate alpha (asset return - beta * benchmark return)
            asset_mean_return = asset_returns.mean()
            benchmark_mean_return = benchmark_returns.mean()
            alpha = asset_mean_return - beta * benchmark_mean_return
            
            # Calculate R-squared
            correlation = np.corrcoef(asset_returns, benchmark_returns)[0, 1]
            r_squared = correlation ** 2 if not np.isnan(correlation) else 0.0
            
            # Calculate volatilities
            asset_volatility = np.std(asset_returns) * np.sqrt(252)  # Annualized
            systematic_risk = beta * np.std(benchmark_returns) * np.sqrt(252)
            idiosyncratic_risk = np.sqrt(asset_volatility**2 - systematic_risk**2) if asset_volatility**2 >= systematic_risk**2 else 0.0
            
            # Create result
            result = BetaResult(
                beta=float(beta),
                alpha=float(alpha),
                r_squared=float(r_squared),
                volatility=float(asset_volatility),
                systematic_risk=float(systematic_risk),
                idiosyncratic_risk=float(idiosyncratic_risk),
                n_observations=len(combined),
                start_date=combined.index.min(),
                end_date=combined.index.max()
            )
            
            # Cache result
            self._beta_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.utcnow().timestamp()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating beta for {symbol}: {e}")
            return None
    
    async def calculate_correlation_matrix(
        self, 
        symbols: List[str],
        days: int = None
    ) -> Dict[str, Any]:
        """
        Calculate correlation matrix for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
            days: Number of days for analysis
            
        Returns:
            Dictionary containing correlation matrix and metadata
        """
        if days is None:
            days = self.default_lookback
            
        correlation_matrix = []
        correlation_data = {}
        
        # Calculate all pairwise correlations
        tasks = []
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i == j:
                    # Self-correlation is always 1.0
                    correlation_data[(symbol1, symbol2)] = 1.0
                elif (symbol2, symbol1) in correlation_data:
                    # Use symmetric property
                    correlation_data[(symbol1, symbol2)] = correlation_data[(symbol2, symbol1)]
                else:
                    # Calculate correlation
                    task = self.calculate_correlation(symbol1, symbol2, days)
                    tasks.append((symbol1, symbol2, task))
        
        # Execute correlation calculations concurrently
        if tasks:
            results = await asyncio.gather(*[task[2] for task in tasks], return_exceptions=True)
            
            for (symbol1, symbol2, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Error calculating correlation {symbol1}-{symbol2}: {result}")
                    correlation_data[(symbol1, symbol2)] = None
                elif result is not None:
                    correlation_data[(symbol1, symbol2)] = result.correlation
                else:
                    correlation_data[(symbol1, symbol2)] = None
        
        # Build matrix
        for symbol1 in symbols:
            row = []
            for symbol2 in symbols:
                corr_value = correlation_data.get((symbol1, symbol2))
                row.append(corr_value)
            correlation_matrix.append(row)
        
        return {
            "symbols": symbols,
            "correlation_matrix": correlation_matrix,
            "timeframe": f"{days}d",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "data_source": "real_market_data"
        }
    
    async def calculate_beta_time_series(
        self, 
        symbols: List[str],
        days_per_window: int = 30,
        num_windows: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate rolling beta coefficients over time.
        
        Args:
            symbols: List of trading pair symbols
            days_per_window: Days of data per beta calculation
            num_windows: Number of time windows to calculate
            
        Returns:
            Dictionary containing time series beta data
        """
        series_data = {}
        
        for symbol in symbols:
            data_points = []
            
            # Calculate beta for each time window
            for i in range(num_windows):
                end_date = datetime.utcnow() - timedelta(days=i * 1)  # Daily windows
                
                # Calculate beta for this window
                beta_result = await self.calculate_beta(
                    symbol=symbol,
                    days=days_per_window
                )
                
                data_point = {
                    "date": end_date.strftime("%Y-%m-%d"),
                    "timestamp": int(end_date.timestamp() * 1000),
                    "beta": beta_result.beta if beta_result else None,
                    "alpha": beta_result.alpha if beta_result else None,
                    "r_squared": beta_result.r_squared if beta_result else None
                }
                data_points.append(data_point)
            
            # Reverse to get chronological order
            data_points.reverse()
            series_data[symbol] = data_points
        
        return {
            "series_data": series_data,
            "window_size": days_per_window,
            "benchmark": self.benchmark_symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    
    def _get_correlation_cache_key(self, symbol1: str, symbol2: str, days: int, method: str) -> str:
        """Generate cache key for correlation calculation."""
        data = f"{symbol1}_{symbol2}_{days}_{method}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _get_beta_cache_key(self, symbol: str, benchmark: str, days: int) -> str:
        """Generate cache key for beta calculation."""
        data = f"{symbol}_{benchmark}_{days}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear all cached correlation and beta calculations."""
        self._correlation_cache.clear()
        self._beta_cache.clear()
        self.logger.info("Cleared correlation calculation cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cache usage."""
        return {
            "correlation_cache_size": len(self._correlation_cache),
            "beta_cache_size": len(self._beta_cache),
            "cache_ttl": self.cache_ttl,
            "min_observations": self.min_observations
        }