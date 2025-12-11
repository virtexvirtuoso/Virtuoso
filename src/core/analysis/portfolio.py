from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import logging

from src.config.manager import ConfigManager

logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    """Portfolio Analysis and Management"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize portfolio analyzer with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.portfolio_config = config.get('portfolio', {})  # Changed from get_value to get
        self.risk_config = config.get('risk', {})
        
        # Initialize from config
        self.risk_free_rate = self.risk_config.get('risk_free_rate', 0.02)
        self.target_allocation = self.portfolio_config.get('target_allocation', {})
        self.rebalancing_config = self.portfolio_config.get('rebalancing', {})
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialized PortfolioAnalyzer with config")
        
    async def analyze_portfolio(self, balances: Dict[str, float]) -> Dict[str, Any]:
        """Analyze current portfolio state and generate insights.
        
        Args:
            balances: Dictionary of asset balances
            
        Returns:
            Dictionary containing portfolio analysis results
        """
        try:
            # Basic portfolio metrics
            total_value = sum(balances.values())
            current_allocation = {
                asset: value/total_value 
                for asset, value in balances.items()
            }
            
            # Calculate deviation from target
            allocation_diff = {}
            for asset in self.target_allocation:
                target = self.target_allocation.get(asset, 0)
                current = current_allocation.get(asset, 0)
                allocation_diff[asset] = current - target
            
            return {
                'total_value': total_value,
                'current_allocation': current_allocation,
                'target_allocation': self.target_allocation,
                'allocation_diff': allocation_diff,
                'needs_rebalancing': any(
                    abs(diff) > self.rebalancing_config.get('threshold', 0.05)
                    for diff in allocation_diff.values()
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing portfolio: {str(e)}")
            return {
                'error': str(e),
                'total_value': 0,
                'current_allocation': {},
                'needs_rebalancing': False
            }
            
    async def _check_rebalancing_needs(self, current_allocation: Dict[str, float]) -> bool:
        """Check if portfolio needs rebalancing based on config thresholds"""
        if not self.rebalancing_config.get('enabled', False):
            return False
            
        threshold = self.rebalancing_config.get('threshold', 0.05)
        for asset, target in self.target_allocation.items():
            current = current_allocation.get(asset, 0)
            if abs(target - current) > threshold * 100:  # Convert threshold to percentage
                return True
        return False
            
    def _calculate_exchange_value(self, balance: Dict) -> float:
        """Calculate total value of assets in an exchange"""
        try:
            total_value = 0
            for asset, data in balance.items():
                if isinstance(data, dict):
                    # Handle structured balance data
                    free = float(data.get('free', 0))
                    used = float(data.get('used', 0))
                    total = float(data.get('total', free + used))
                    price_usd = float(data.get('usd_value', 0))
                    total_value += total * price_usd
                else:
                    # Handle simple balance values
                    total_value += float(data)
            return total_value
        except Exception as e:
            logger.error(f"Error calculating exchange value: {str(e)}")
            return 0
            
    async def calculate_risk_metrics(self, balances: Dict[str, Dict]) -> Dict:
        """Calculate portfolio risk metrics"""
        try:
            # Get risk limits from config
            risk_limits = self.risk_config.get('risk_limits', {})
            
            # Calculate portfolio volatility
            volatility = await self._calculate_portfolio_volatility(balances)
            
            # Calculate Value at Risk (VaR)
            var_95 = volatility * 1.645  # 95% confidence level
            var_99 = volatility * 2.326  # 99% confidence level
            
            # Calculate maximum drawdown
            max_drawdown = await self._calculate_max_drawdown(balances)
            
            # Calculate Sharpe Ratio
            sharpe_ratio = await self._calculate_sharpe_ratio(balances)
            
            # Calculate Sortino Ratio
            sortino_ratio = await self._calculate_sortino_ratio(balances)
            
            # Check risk limits
            risk_warnings = []
            if max_drawdown > risk_limits.get('max_drawdown', 0.25):
                risk_warnings.append('Maximum drawdown exceeded limit')
            
            return {
                'volatility': volatility,
                'var_95': var_95,
                'var_99': var_99,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'risk_warnings': risk_warnings
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            raise
            
    async def calculate_performance_metrics(self, balances: Dict[str, Dict]) -> Dict:
        """Calculate portfolio performance metrics"""
        try:
            # Get performance thresholds from config
            perf_config = self.portfolio_config.get('performance', {})
            
            # Calculate returns
            daily_return = 0.0  # Placeholder for actual daily return calculation
            weekly_return = 0.0  # Placeholder for actual weekly return calculation
            monthly_return = 0.0  # Placeholder for actual monthly return calculation
            
            # Calculate turnover ratio
            turnover_ratio = await self._calculate_turnover_ratio(balances)
            
            # Calculate win rate
            win_rate = await self._calculate_win_rate(balances)
            
            # Performance warnings
            warnings = []
            if turnover_ratio > perf_config.get('max_turnover', 2.0):
                warnings.append('High portfolio turnover')
            
            return {
                'daily_return': daily_return,
                'weekly_return': weekly_return,
                'monthly_return': monthly_return,
                'turnover_ratio': turnover_ratio,
                'win_rate': win_rate,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {str(e)}")
            raise
            
    async def _calculate_portfolio_volatility(self, balances: Dict[str, Dict]) -> float:
        """Calculate portfolio volatility"""
        try:
            # Placeholder for actual volatility calculation
            # Would typically use historical price data and calculate standard deviation
            return 0.15  # Example annualized volatility of 15%
        except Exception as e:
            logger.error(f"Error calculating portfolio volatility: {str(e)}")
            return 0
            
    async def _calculate_max_drawdown(self, balances: Dict[str, Dict]) -> float:
        """Calculate maximum drawdown"""
        try:
            # Placeholder for actual max drawdown calculation
            # Would typically use historical portfolio values
            return 0.25  # Example maximum drawdown of 25%
        except Exception as e:
            logger.error(f"Error calculating maximum drawdown: {str(e)}")
            return 0
            
    async def _calculate_sharpe_ratio(self, balances: Dict[str, Dict]) -> float:
        """Calculate Sharpe ratio"""
        try:
            # Placeholder for actual Sharpe ratio calculation
            # Would typically use historical returns and volatility
            return 1.5  # Example Sharpe ratio
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0
            
    async def _calculate_sortino_ratio(self, balances: Dict[str, Dict]) -> float:
        """Calculate Sortino ratio"""
        try:
            # Placeholder for actual Sortino ratio calculation
            # Would typically use historical returns and downside deviation
            return 2.0  # Example Sortino ratio
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {str(e)}")
            return 0
            
    async def _calculate_turnover_ratio(self, balances: Dict[str, Dict]) -> float:
        """Calculate portfolio turnover ratio"""
        try:
            # Placeholder for actual turnover ratio calculation
            # Would typically use historical trading volume and portfolio value
            return 0.5  # Example turnover ratio of 50%
        except Exception as e:
            logger.error(f"Error calculating turnover ratio: {str(e)}")
            return 0
            
    async def _calculate_win_rate(self, balances: Dict[str, Dict]) -> float:
        """Calculate trading win rate"""
        try:
            # Placeholder for actual win rate calculation
            # Would typically use historical trade data
            return 0.6  # Example win rate of 60%
        except Exception as e:
            logger.error(f"Error calculating win rate: {str(e)}")
            return 0
            
    async def rebalance_portfolio(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Optional[Dict[str, float]] = None,
        tolerance: Optional[float] = None
    ) -> Dict:
        """Calculate rebalancing trades needed"""
        try:
            if target_allocation is None:
                target_allocation = self.target_allocation
            if tolerance is None:
                tolerance = self.rebalancing_config.get('threshold', 0.05)
                
            rebalancing_trades = []
            
            for asset, target in target_allocation.items():
                current = current_allocation.get(asset, 0)
                difference = target - current
                
                # Only rebalance if difference exceeds tolerance
                if abs(difference) > tolerance * 100:  # Convert tolerance to percentage
                    rebalancing_trades.append({
                        'asset': asset,
                        'current_allocation': current,
                        'target_allocation': target,
                        'difference': difference,
                        'action': 'buy' if difference > 0 else 'sell',
                        'timestamp': datetime.now(timezone.utc)
                    })
                    
            return {
                'trades': rebalancing_trades,
                'timestamp': datetime.now(timezone.utc),
                'config_used': {
                    'target_allocation': target_allocation,
                    'tolerance': tolerance
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating rebalancing trades: {str(e)}")
            raise 