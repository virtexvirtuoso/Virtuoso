"""
Optimization objective functions for Virtuoso trading system.
Implements comprehensive performance metrics for parameter optimization.
"""

import optuna
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass

from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationMetrics:
    """Comprehensive metrics for optimization evaluation."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    sortino_ratio: float
    calmar_ratio: float
    total_trades: int
    avg_trade_duration: float
    volatility: float
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'total_trades': self.total_trades,
            'avg_trade_duration': self.avg_trade_duration,
            'volatility': self.volatility
        }


class OptimizationObjectives:
    """
    Comprehensive objective functions for Virtuoso parameter optimization.
    
    Implements multiple optimization targets:
    - Risk-adjusted returns (Sharpe, Sortino, Calmar)
    - Signal quality metrics
    - Multi-objective optimization
    - Market regime specific objectives
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_free_rate = config.get('risk_free_rate', 0.02)  # 2% annual
        self.min_trades_threshold = config.get('min_trades', 100)
        self.evaluation_period_days = config.get('evaluation_period_days', 90)
        
        # Objective weights for multi-objective optimization
        self.objective_weights = {
            'return': 0.3,
            'sharpe': 0.25,
            'drawdown': 0.2,  # Minimize drawdown (negative weight)
            'win_rate': 0.15,
            'trades': 0.1  # Ensure sufficient trades
        }
        
        logger.info(f"Initialized optimization objectives with {len(self.objective_weights)} metrics")
    
    def risk_adjusted_return_objective(self, trial: optuna.Trial, 
                                     parameter_space: str) -> float:
        """
        Primary objective function optimizing for risk-adjusted returns.
        
        This is the main objective that balances return, risk, and drawdown
        to find optimal parameter sets for real trading.
        """
        try:
            # Get suggested parameters from trial
            from .parameter_spaces import ComprehensiveParameterSpaces
            parameters = ComprehensiveParameterSpaces.suggest_parameters(trial, parameter_space)
            
            # Run backtesting simulation with suggested parameters
            metrics = self._run_backtest_simulation(parameters, parameter_space)
            
            # Implement multi-objective scoring
            objective_score = self._calculate_multi_objective_score(metrics)
            
            # Report intermediate values for pruning
            trial.report(objective_score, step=0)
            
            # Prune unpromising trials early
            if trial.should_prune():
                raise optuna.TrialPruned()
            
            logger.debug(f"Trial {trial.number} scored {objective_score:.4f} for {parameter_space}")
            return objective_score
            
        except Exception as e:
            logger.error(f"Trial {trial.number} failed: {e}")
            # Return very low score for failed trials
            return -1000.0
    
    def signal_quality_objective(self, trial: optuna.Trial,
                                parameter_space: str) -> float:
        """
        Objective function focused on signal quality metrics.
        Optimizes for accuracy, precision, and signal timing.
        """
        try:
            parameters = ComprehensiveParameterSpaces.suggest_parameters(trial, parameter_space)
            
            # Simulate signal generation with parameters
            signal_metrics = self._evaluate_signal_quality(parameters, parameter_space)
            
            # Calculate signal quality score
            quality_score = (
                signal_metrics['precision'] * 0.4 +
                signal_metrics['recall'] * 0.3 +  
                signal_metrics['f1_score'] * 0.2 +
                signal_metrics['signal_timing_accuracy'] * 0.1
            )
            
            return quality_score
            
        except Exception as e:
            logger.error(f"Signal quality evaluation failed: {e}")
            return 0.0
    
    def market_regime_objective(self, trial: optuna.Trial,
                               parameter_space: str,
                               market_regime: str = 'trending') -> float:
        """
        Objective function optimized for specific market regimes.
        
        Args:
            market_regime: 'trending', 'ranging', 'volatile', or 'low_volatility'
        """
        try:
            parameters = ComprehensiveParameterSpaces.suggest_parameters(trial, parameter_space)
            
            # Filter historical data by market regime
            regime_data = self._filter_by_market_regime(market_regime)
            
            # Run simulation on regime-specific data
            metrics = self._run_backtest_simulation(parameters, parameter_space, regime_data)
            
            # Market regime specific scoring
            if market_regime == 'trending':
                score = metrics.total_return * 0.4 + metrics.sharpe_ratio * 0.6
            elif market_regime == 'ranging':
                score = metrics.win_rate * 0.5 + (1.0 - metrics.max_drawdown) * 0.5
            elif market_regime == 'volatile':
                score = metrics.sortino_ratio * 0.6 + (1.0 - metrics.max_drawdown) * 0.4
            else:  # low_volatility
                score = metrics.total_return * 0.7 + metrics.profit_factor * 0.3
            
            return score
            
        except Exception as e:
            logger.error(f"Market regime optimization failed: {e}")
            return -100.0
    
    def _run_backtest_simulation(self, parameters: Dict[str, Any], 
                                parameter_space: str,
                                data: Optional[pd.DataFrame] = None) -> OptimizationMetrics:
        """
        Run backtesting simulation with given parameters.
        
        This is a simplified simulation for optimization purposes.
        In production, this would interface with the full backtesting engine.
        """
        # Mock simulation results for now
        # In full implementation, this would:
        # 1. Apply parameters to indicators
        # 2. Generate signals
        # 3. Simulate trades
        # 4. Calculate comprehensive metrics
        
        # Generate realistic mock metrics based on parameter quality
        np.random.seed(hash(str(parameters)) % 2**31)  # Deterministic based on params
        
        # Simulate trading results
        base_return = np.random.normal(0.08, 0.15)  # 8% annual return, 15% volatility
        daily_returns = np.random.normal(base_return/252, 0.15/np.sqrt(252), 252)
        
        # Calculate comprehensive metrics
        total_return = np.prod(1 + daily_returns) - 1
        volatility = np.std(daily_returns) * np.sqrt(252)
        
        # Sharpe ratio
        excess_returns = daily_returns - self.risk_free_rate/252
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        # Max drawdown
        cumulative = np.cumprod(1 + daily_returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(np.min(drawdown))
        
        # Additional metrics
        win_rate = len(daily_returns[daily_returns > 0]) / len(daily_returns)
        
        # Sortino ratio (downside deviation)
        negative_returns = daily_returns[daily_returns < 0]
        downside_deviation = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else 0.01
        sortino_ratio = (total_return - self.risk_free_rate) / downside_deviation
        
        # Calmar ratio
        calmar_ratio = total_return / max(max_drawdown, 0.01)
        
        # Profit factor (simplified)
        profitable_trades = daily_returns[daily_returns > 0]
        losing_trades = daily_returns[daily_returns < 0]
        profit_factor = abs(np.sum(profitable_trades)) / abs(np.sum(losing_trades)) if len(losing_trades) > 0 else 2.0
        
        return OptimizationMetrics(
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=len(daily_returns),
            avg_trade_duration=1.0,  # Daily trades
            volatility=volatility
        )
    
    def _calculate_multi_objective_score(self, metrics: OptimizationMetrics) -> float:
        """Calculate weighted multi-objective optimization score."""
        
        # Normalize metrics to [0, 1] scale
        normalized_return = max(0, min(1, (metrics.total_return + 0.5) / 1.0))  # -50% to +50%
        normalized_sharpe = max(0, min(1, (metrics.sharpe_ratio + 2) / 4))  # -2 to +2
        normalized_drawdown = max(0, min(1, 1 - metrics.max_drawdown))  # Inverse (less is better)
        normalized_win_rate = max(0, min(1, metrics.win_rate))  # Already 0-1
        normalized_trades = max(0, min(1, metrics.total_trades / 500))  # Up to 500 trades
        
        # Apply objective weights
        weighted_score = (
            self.objective_weights['return'] * normalized_return +
            self.objective_weights['sharpe'] * normalized_sharpe +
            self.objective_weights['drawdown'] * normalized_drawdown +
            self.objective_weights['win_rate'] * normalized_win_rate +
            self.objective_weights['trades'] * normalized_trades
        )
        
        # Penalty for insufficient trades
        if metrics.total_trades < self.min_trades_threshold:
            weighted_score *= (metrics.total_trades / self.min_trades_threshold) * 0.5
        
        return weighted_score
    
    def _evaluate_signal_quality(self, parameters: Dict[str, Any],
                                parameter_space: str) -> Dict[str, float]:
        """Evaluate signal quality metrics."""
        # Mock signal quality evaluation
        # In full implementation, this would analyze:
        # 1. Signal accuracy vs actual price movements
        # 2. Signal timing precision
        # 3. False positive/negative rates
        
        np.random.seed(hash(str(parameters)) % 2**31)
        
        return {
            'precision': np.random.uniform(0.6, 0.9),
            'recall': np.random.uniform(0.5, 0.8),
            'f1_score': np.random.uniform(0.55, 0.85),
            'signal_timing_accuracy': np.random.uniform(0.6, 0.85)
        }
    
    def _filter_by_market_regime(self, regime: str) -> pd.DataFrame:
        """Filter historical data by market regime."""
        # Mock regime filtering
        # In full implementation, this would:
        # 1. Analyze historical market conditions
        # 2. Classify periods by regime
        # 3. Return filtered dataset
        
        # For now, return empty DataFrame indicating mock data
        return pd.DataFrame()
    
    def evaluate_parameter_set(self, parameters: Dict[str, Any], 
                              parameter_space: str) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a parameter set.
        Used for detailed analysis outside of optimization trials.
        """
        metrics = self._run_backtest_simulation(parameters, parameter_space)
        signal_quality = self._evaluate_signal_quality(parameters, parameter_space)
        
        evaluation = {
            'parameters': parameters,
            'parameter_space': parameter_space,
            'performance_metrics': metrics.to_dict(),
            'signal_quality': signal_quality,
            'multi_objective_score': self._calculate_multi_objective_score(metrics),
            'evaluation_timestamp': datetime.now().isoformat()
        }
        
        return evaluation
    
    def compare_parameter_sets(self, parameter_sets: List[Dict[str, Any]],
                              parameter_space: str) -> pd.DataFrame:
        """Compare multiple parameter sets and rank them."""
        evaluations = []
        
        for i, params in enumerate(parameter_sets):
            logger.info(f"Evaluating parameter set {i+1}/{len(parameter_sets)}")
            evaluation = self.evaluate_parameter_set(params, parameter_space)
            evaluations.append(evaluation)
        
        # Convert to DataFrame for easy analysis
        comparison_data = []
        for eval_result in evaluations:
            row = eval_result['parameters'].copy()
            row.update(eval_result['performance_metrics'])
            row.update(eval_result['signal_quality'])
            row['multi_objective_score'] = eval_result['multi_objective_score']
            comparison_data.append(row)
        
        df = pd.DataFrame(comparison_data)
        df = df.sort_values('multi_objective_score', ascending=False)
        
        return df