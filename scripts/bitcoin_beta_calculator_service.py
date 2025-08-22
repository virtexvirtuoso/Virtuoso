#!/usr/bin/env python3
"""
Bitcoin Beta Calculator Service
Calculates beta coefficients and correlations for all tracked symbols
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from scipy import stats
from aiomcache import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BitcoinBetaCalculator:
    """Service to calculate beta coefficients and correlations"""
    
    def __init__(self):
        self.cache = Client('localhost', 11211)
        
        # Symbols to calculate beta for (excluding BTC)
        self.symbols = [
            'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT',
            'NEARUSDT', 'ATOMUSDT', 'FTMUSDT', 'ALGOUSDT',
            'AAVEUSDT', 'UNIUSDT', 'SUSHIUSDT', 'COMPUSDT',
            'SNXUSDT', 'CRVUSDT', 'MKRUSDT'
        ]
        
        self.benchmark = 'BTCUSDT'
        
        # Windows for beta calculation (in days)
        self.windows = {
            '7d': 7,
            '30d': 30,
            '90d': 90
        }
        
        self.update_interval = 3600  # Update every hour
        
    async def get_kline_data(self, symbol: str, interval: str = '60') -> Optional[Dict]:
        """
        Get kline data from cache
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (default: hourly)
            
        Returns:
            Kline data dict or None
        """
        cache_key = f'beta:klines:{symbol}:{interval}'
        
        try:
            data = await self.cache.get(cache_key.encode())
            if data:
                return json.loads(data.decode())
        except Exception as e:
            logger.error(f"Error getting kline data for {symbol}: {e}")
        
        return None
    
    def calculate_returns(self, prices: List[float]) -> np.ndarray:
        """
        Calculate log returns from price series
        
        Args:
            prices: List of prices
            
        Returns:
            Array of log returns
        """
        prices_array = np.array(prices)
        # Remove any zeros or negative values
        prices_array = prices_array[prices_array > 0]
        
        if len(prices_array) < 2:
            return np.array([])
        
        # Calculate log returns
        returns = np.diff(np.log(prices_array))
        return returns
    
    def calculate_beta(self, asset_returns: np.ndarray, benchmark_returns: np.ndarray) -> float:
        """
        Calculate beta coefficient
        Beta = Covariance(Asset, Benchmark) / Variance(Benchmark)
        
        Args:
            asset_returns: Asset return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Beta coefficient
        """
        if len(asset_returns) < 2 or len(benchmark_returns) < 2:
            return 1.0
        
        # Ensure same length
        min_len = min(len(asset_returns), len(benchmark_returns))
        asset_returns = asset_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        # Calculate covariance and variance
        covariance = np.cov(asset_returns, benchmark_returns)[0, 1]
        variance = np.var(benchmark_returns)
        
        if variance > 0:
            beta = covariance / variance
            return round(beta, 3)
        
        return 1.0
    
    def calculate_correlation(self, asset_returns: np.ndarray, benchmark_returns: np.ndarray) -> float:
        """
        Calculate correlation coefficient
        
        Args:
            asset_returns: Asset return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Correlation coefficient
        """
        if len(asset_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        # Ensure same length
        min_len = min(len(asset_returns), len(benchmark_returns))
        asset_returns = asset_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        # Calculate correlation
        if len(asset_returns) > 1:
            correlation = np.corrcoef(asset_returns, benchmark_returns)[0, 1]
            return round(correlation, 3)
        
        return 0.0
    
    def calculate_alpha(self, asset_returns: np.ndarray, benchmark_returns: np.ndarray, 
                       beta: float, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Jensen's Alpha
        Alpha = Asset Return - (Risk-free Rate + Beta * (Market Return - Risk-free Rate))
        
        Args:
            asset_returns: Asset return series
            benchmark_returns: Benchmark return series
            beta: Beta coefficient
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Alpha value
        """
        if len(asset_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        # Calculate annualized returns
        # Assuming hourly data, ~8760 hours per year
        periods_per_year = 8760
        
        asset_return = np.mean(asset_returns) * periods_per_year
        benchmark_return = np.mean(benchmark_returns) * periods_per_year
        
        # Calculate alpha
        expected_return = risk_free_rate + beta * (benchmark_return - risk_free_rate)
        alpha = asset_return - expected_return
        
        return round(alpha, 4)
    
    def calculate_r_squared(self, asset_returns: np.ndarray, benchmark_returns: np.ndarray) -> float:
        """
        Calculate R-squared (coefficient of determination)
        
        Args:
            asset_returns: Asset return series
            benchmark_returns: Benchmark return series
            
        Returns:
            R-squared value
        """
        if len(asset_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        # Ensure same length
        min_len = min(len(asset_returns), len(benchmark_returns))
        asset_returns = asset_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        # Calculate R-squared
        correlation = np.corrcoef(asset_returns, benchmark_returns)[0, 1]
        r_squared = correlation ** 2
        
        return round(r_squared, 3)
    
    def categorize_risk(self, beta: float) -> Dict[str, str]:
        """
        Categorize asset by beta risk level
        
        Args:
            beta: Beta coefficient
            
        Returns:
            Risk category information
        """
        if beta < 0.5:
            return {
                'category': 'Defensive',
                'color': '#3B82F6',  # Blue
                'description': 'Low volatility, stable'
            }
        elif beta < 0.9:
            return {
                'category': 'Low Risk',
                'color': '#10B981',  # Green
                'description': 'Below market volatility'
            }
        elif beta < 1.1:
            return {
                'category': 'Market Neutral',
                'color': '#6B7280',  # Gray
                'description': 'Moves with BTC'
            }
        elif beta < 1.5:
            return {
                'category': 'Moderate Risk',
                'color': '#F59E0B',  # Yellow
                'description': 'Above market volatility'
            }
        else:
            return {
                'category': 'High Risk',
                'color': '#EF4444',  # Red
                'description': 'Highly volatile'
            }
    
    async def calculate_symbol_beta(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate all beta metrics for a single symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with beta metrics for all windows
        """
        # Get kline data for asset and benchmark
        asset_data = await self.get_kline_data(symbol)
        benchmark_data = await self.get_kline_data(self.benchmark)
        
        if not asset_data or not benchmark_data:
            logger.warning(f"Missing data for {symbol} or {self.benchmark}")
            return {}
        
        # Get price arrays
        asset_closes = asset_data.get('closes', [])
        benchmark_closes = benchmark_data.get('closes', [])
        
        if not asset_closes or not benchmark_closes:
            return {}
        
        # Calculate returns
        asset_returns = self.calculate_returns(asset_closes)
        benchmark_returns = self.calculate_returns(benchmark_closes)
        
        # Results dictionary
        result = {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'last_price': asset_closes[-1] if asset_closes else 0,
            'change_24h': 0,
            'volume_24h': 0
        }
        
        # Calculate 24h change
        if len(asset_closes) >= 24:
            change_24h = ((asset_closes[-1] - asset_closes[-24]) / asset_closes[-24]) * 100
            result['change_24h'] = round(change_24h, 2)
        
        # Calculate metrics for each window
        for window_name, days in self.windows.items():
            # Calculate number of hourly periods
            periods = days * 24
            
            if len(asset_returns) >= periods and len(benchmark_returns) >= periods:
                # Get returns for this window
                window_asset_returns = asset_returns[-periods:]
                window_benchmark_returns = benchmark_returns[-periods:]
                
                # Calculate metrics
                beta = self.calculate_beta(window_asset_returns, window_benchmark_returns)
                correlation = self.calculate_correlation(window_asset_returns, window_benchmark_returns)
                r_squared = self.calculate_r_squared(window_asset_returns, window_benchmark_returns)
                alpha = self.calculate_alpha(window_asset_returns, window_benchmark_returns, beta)
                
                # Store results
                result[f'beta_{window_name}'] = beta
                result[f'correlation_{window_name}'] = correlation
                result[f'r_squared_{window_name}'] = r_squared
                result[f'alpha_{window_name}'] = alpha
            else:
                # Not enough data for this window
                result[f'beta_{window_name}'] = 1.0
                result[f'correlation_{window_name}'] = 0.0
                result[f'r_squared_{window_name}'] = 0.0
                result[f'alpha_{window_name}'] = 0.0
        
        # Add risk categorization based on 30d beta
        beta_30d = result.get('beta_30d', 1.0)
        result['risk_category'] = self.categorize_risk(beta_30d)
        
        # Calculate volatility ratio (asset vol / benchmark vol)
        if len(asset_returns) >= 24 * 7 and len(benchmark_returns) >= 24 * 7:
            asset_vol = np.std(asset_returns[-24*7:])
            benchmark_vol = np.std(benchmark_returns[-24*7:])
            if benchmark_vol > 0:
                result['volatility_ratio'] = round(asset_vol / benchmark_vol, 2)
            else:
                result['volatility_ratio'] = 1.0
        else:
            result['volatility_ratio'] = 1.0
        
        return result
    
    async def store_beta_data(self, symbol: str, data: Dict[str, Any]):
        """
        Store beta calculation results in cache
        
        Args:
            symbol: Trading pair symbol
            data: Beta calculation results
        """
        if not data:
            return
        
        cache_key = f'beta:values:{symbol}'
        
        try:
            # Store with 1 hour TTL
            serialized = json.dumps(data)
            await self.cache.set(cache_key.encode(), serialized.encode(), exptime=3600)
            logger.info(f"Stored beta data for {symbol}: β30d={data.get('beta_30d', 'N/A')}")
        except Exception as e:
            logger.error(f"Error storing beta data for {symbol}: {e}")
    
    async def calculate_market_overview(self) -> Dict[str, Any]:
        """
        Calculate market-wide beta statistics
        
        Returns:
            Market overview statistics
        """
        overview = {
            'market_beta': 1.0,
            'btc_dominance': 0,
            'total_symbols': len(self.symbols),
            'high_beta_count': 0,
            'low_beta_count': 0,
            'neutral_beta_count': 0,
            'avg_correlation': 0,
            'market_regime': 'NEUTRAL',
            'timestamp': int(time.time() * 1000)
        }
        
        betas = []
        correlations = []
        
        for symbol in self.symbols:
            cache_key = f'beta:values:{symbol}'
            
            try:
                data = await self.cache.get(cache_key.encode())
                if data:
                    symbol_data = json.loads(data.decode())
                    beta_30d = symbol_data.get('beta_30d', 1.0)
                    correlation_30d = symbol_data.get('correlation_30d', 0)
                    
                    betas.append(beta_30d)
                    correlations.append(correlation_30d)
                    
                    # Count by category
                    if beta_30d >= 1.5:
                        overview['high_beta_count'] += 1
                    elif beta_30d <= 0.9:
                        overview['low_beta_count'] += 1
                    else:
                        overview['neutral_beta_count'] += 1
            except Exception as e:
                logger.error(f"Error reading beta data for {symbol}: {e}")
        
        # Calculate averages
        if betas:
            overview['market_beta'] = round(np.mean(betas), 2)
        
        if correlations:
            overview['avg_correlation'] = round(np.mean(correlations), 3)
        
        # Determine market regime
        high_beta_pct = overview['high_beta_count'] / max(overview['total_symbols'], 1)
        avg_corr = overview['avg_correlation']
        
        if high_beta_pct > 0.6 and avg_corr > 0.7:
            overview['market_regime'] = 'RISK_ON'
        elif high_beta_pct < 0.3 and avg_corr < 0.5:
            overview['market_regime'] = 'RISK_OFF'
        elif avg_corr > 0.85:
            overview['market_regime'] = 'CORRELATED_CRASH'
        else:
            overview['market_regime'] = 'NEUTRAL'
        
        # Get BTC dominance from market overview cache if available
        try:
            market_data = await self.cache.get(b'market:overview')
            if market_data:
                market_overview = json.loads(market_data.decode())
                overview['btc_dominance'] = market_overview.get('btc_dominance', 57.4)
        except Exception:
            overview['btc_dominance'] = 57.4  # Default value
        
        return overview
    
    async def store_market_overview(self, overview: Dict[str, Any]):
        """Store market overview in cache"""
        cache_key = 'beta:overview'
        
        try:
            serialized = json.dumps(overview)
            await self.cache.set(cache_key.encode(), serialized.encode(), exptime=3600)
            logger.info(f"Stored market overview: regime={overview['market_regime']}, avg_beta={overview['market_beta']}")
        except Exception as e:
            logger.error(f"Error storing market overview: {e}")
    
    async def store_historical_beta(self, symbol: str, beta: float, correlation: float):
        """
        Store historical beta values for charting
        
        Args:
            symbol: Trading pair symbol
            beta: Current beta value
            correlation: Current correlation value
        """
        cache_key = f'beta:history:{symbol}'
        
        try:
            # Get existing history
            data = await self.cache.get(cache_key.encode())
            if data:
                history = json.loads(data.decode())
            else:
                history = []
            
            # Add new entry
            history.append({
                'timestamp': int(time.time() * 1000),
                'beta': beta,
                'correlation': correlation
            })
            
            # Keep only last 7 days of hourly data (168 entries)
            if len(history) > 168:
                history = history[-168:]
            
            # Store updated history
            serialized = json.dumps(history)
            await self.cache.set(cache_key.encode(), serialized.encode(), exptime=604800)  # 7 days TTL
            
        except Exception as e:
            logger.error(f"Error storing historical beta for {symbol}: {e}")
    
    async def calculate_all_betas(self):
        """Calculate beta for all symbols"""
        logger.info(f"Calculating beta for {len(self.symbols)} symbols")
        
        # Calculate in parallel for speed
        tasks = []
        for symbol in self.symbols:
            task = asyncio.create_task(self.calculate_symbol_beta(symbol))
            tasks.append((symbol, task))
        
        # Wait for all calculations
        for symbol, task in tasks:
            try:
                result = await task
                if result:
                    # Store the results
                    await self.store_beta_data(symbol, result)
                    
                    # Store historical data
                    beta_30d = result.get('beta_30d', 1.0)
                    correlation_30d = result.get('correlation_30d', 0.0)
                    await self.store_historical_beta(symbol, beta_30d, correlation_30d)
            except Exception as e:
                logger.error(f"Error calculating beta for {symbol}: {e}")
        
        # Calculate and store market overview
        overview = await self.calculate_market_overview()
        await self.store_market_overview(overview)
        
        logger.info("Beta calculations complete")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        status = {
            'symbols_tracked': len(self.symbols),
            'symbols_with_data': 0,
            'last_update': None,
            'market_regime': None
        }
        
        # Check how many symbols have data
        for symbol in self.symbols:
            cache_key = f'beta:values:{symbol}'
            try:
                data = await self.cache.get(cache_key.encode())
                if data:
                    status['symbols_with_data'] += 1
                    symbol_data = json.loads(data.decode())
                    if symbol_data.get('timestamp'):
                        status['last_update'] = symbol_data['timestamp']
            except Exception:
                pass
        
        # Get market regime
        try:
            overview_data = await self.cache.get(b'beta:overview')
            if overview_data:
                overview = json.loads(overview_data.decode())
                status['market_regime'] = overview.get('market_regime')
        except Exception:
            pass
        
        return status
    
    async def run_continuous(self):
        """Run continuous beta calculation"""
        while True:
            try:
                # Calculate all betas
                await self.calculate_all_betas()
                
                # Log status
                status = await self.get_status()
                logger.info(f"Beta service status: {status['symbols_with_data']}/{status['symbols_tracked']} symbols, regime={status['market_regime']}")
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous run: {e}")
                await asyncio.sleep(60)  # Wait before retry

async def main():
    """Main entry point"""
    calculator = BitcoinBetaCalculator()
    
    # Check command line arguments
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--status':
        # Just show status
        status = await calculator.get_status()
        print(json.dumps(status, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once and exit
        await calculator.calculate_all_betas()
    else:
        # Run continuously
        await calculator.run_continuous()

if __name__ == '__main__':
    asyncio.run(main())