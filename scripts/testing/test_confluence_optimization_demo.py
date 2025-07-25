#!/usr/bin/env python3
"""
Confluence Engine Optimization Demo
Demonstrates how to use Optuna to optimize the confluence engine parameters.
"""

import os
import sys
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import optuna
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.optimization.confluence_parameter_spaces import suggest_confluence_parameters
from src.analysis.core.confluence import ConfluenceAnalyzer
from src.optimization.optuna_engine import VirtuosoOptunaEngine
from src.core.logger import Logger

logger = Logger(__name__)

class ConfluenceOptimizationDemo:
    """Demonstration of confluence engine parameter optimization."""
    
    def __init__(self):
        self.logger = logger
        # Provide minimal config for Optuna engine
        optuna_config = {
            'optuna': {
                'storage_url': 'sqlite:///test_optimization.db',
                'enable_pruning': True,
                'n_jobs': 1
            }
        }
        self.optuna_engine = VirtuosoOptunaEngine(optuna_config)
        self.mock_data = self._generate_mock_market_data()
        
        # Track optimization results
        self.optimization_results = []
        
    def _generate_mock_market_data(self) -> Dict[str, Any]:
        """Generate realistic mock market data for testing."""
        
        # Generate 100 data points for testing
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Generate realistic OHLCV data
        base_price = 50000.0
        prices = []
        volumes = []
        
        for i in range(100):
            # Add some trend and randomness
            trend = 0.001 * i  # Slight upward trend
            noise = np.random.normal(0, 0.02)  # 2% volatility
            price = base_price * (1 + trend + noise)
            prices.append(price)
            
            # Generate volume with some correlation to price changes
            if i > 0:
                price_change = abs(prices[i] - prices[i-1]) / prices[i-1]
                volume = np.random.lognormal(15, 0.5) * (1 + price_change * 10)
            else:
                volume = np.random.lognormal(15, 0.5)
            volumes.append(volume)
        
        # Create DataFrame
        ohlcv_df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': volumes
        })
        ohlcv_df.set_index('timestamp', inplace=True)
        
        # Create mock orderbook
        current_price = prices[-1]
        bids = [[current_price * (1 - i * 0.001), np.random.uniform(0.1, 2.0)] for i in range(1, 21)]
        asks = [[current_price * (1 + i * 0.001), np.random.uniform(0.1, 2.0)] for i in range(1, 21)]
        
        return {
            'ohlcv': {'1h': ohlcv_df},
            'orderbook': {'bids': bids, 'asks': asks},
            'symbol': 'BTCUSDT',
            'exchange': 'binance'
        }
    
    def objective_function(self, trial: optuna.Trial) -> float:
        """
        Objective function for Optuna optimization.
        This would normally connect to actual backtesting results.
        """
        try:
            # Get optimized parameters from confluence parameter spaces
            parameters = suggest_confluence_parameters(trial, 'comprehensive')
            
            # Validate parameter constraints
            from src.optimization.confluence_parameter_spaces import ConfluenceParameterSpaces
            if not ConfluenceParameterSpaces.validate_parameter_constraints(parameters):
                self.logger.warning(f"Invalid parameters generated for trial {trial.number}")
                return 0.0
            
            # For demo purposes, simulate confluence analysis without full analyzer
            # In production, this would use actual ConfluenceAnalyzer
            base_score = self._simulate_confluence_score(parameters)
            reliability = np.random.uniform(0.4, 0.9)  # Simulate reliability score
            
            # Simulate performance metrics
            simulated_returns = self._simulate_performance(parameters, base_score, reliability)
            
            # Multi-objective scoring
            fitness_score = (
                0.40 * base_score +  # Confluence score quality
                0.30 * (simulated_returns['sharpe_ratio'] * 10) +  # Risk-adjusted returns
                0.20 * (100 - simulated_returns['max_drawdown']) +  # Drawdown control
                0.10 * simulated_returns['win_rate']  # Win rate
            )
            
            # Store results for analysis
            self.optimization_results.append({
                'trial': trial.number,
                'parameters': parameters,
                'confluence_score': base_score,
                'reliability': reliability,
                'fitness_score': fitness_score,
                'simulated_returns': simulated_returns
            })
            
            self.logger.info(f"Trial {trial.number}: fitness={fitness_score:.2f}, confluence={base_score:.2f}")
            
            return fitness_score
            
        except Exception as e:
            self.logger.error(f"Error in objective function for trial {trial.number}: {e}")
            return 0.0
    
    def _build_config_from_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Build confluence analyzer configuration from optimized parameters."""
        
        return {
            'confluence': {
                'weights': {
                    'components': parameters.get('component_weights', {}),
                    'sub_components': parameters.get('sub_component_weights', {}),
                    'timeframes': parameters.get('timeframe_weights', {})
                },
                'thresholds': parameters.get('signal_thresholds', {}),
                'transformation': parameters.get('transformation_params', {}),
                'orderbook': parameters.get('orderbook_params', {}),
                'volume': parameters.get('volume_params', {}),
                'technical': parameters.get('technical_params', {})
            }
        }
    
    def _simulate_confluence_score(self, parameters: Dict[str, Any]) -> float:
        """Simulate confluence score based on parameter quality."""
        
        # Base score with some randomness
        base_score = np.random.uniform(45.0, 85.0)
        
        # Adjust based on parameter quality
        signal_thresholds = parameters.get('signal_thresholds', {})
        buy_threshold = signal_thresholds.get('buy_threshold', 70.0)
        sell_threshold = signal_thresholds.get('sell_threshold', 30.0)
        
        # Better thresholds around 70/30 get bonus
        threshold_bonus = 0
        if 68.0 <= buy_threshold <= 72.0:
            threshold_bonus += 5
        if 28.0 <= sell_threshold <= 32.0:
            threshold_bonus += 5
            
        # Component balance bonus
        component_weights = parameters.get('component_weights', {})
        if component_weights:
            weight_variance = np.var(list(component_weights.values()))
            if weight_variance < 0.01:  # Well balanced
                threshold_bonus += 3
        
        return min(95.0, base_score + threshold_bonus)
    
    def _simulate_performance(self, parameters: Dict[str, Any], 
                            confluence_score: float, reliability: float) -> Dict[str, float]:
        """Simulate trading performance based on parameters."""
        
        # This is a simplified simulation - in practice, you'd use actual backtesting
        np.random.seed(42)  # For reproducible results
        
        # Base performance metrics influenced by parameter quality
        base_return = np.random.normal(0.05, 0.15)  # 5% average with 15% volatility
        
        # Parameter quality adjustments
        quality_factor = (confluence_score / 100.0) * reliability
        
        # Signal thresholds influence performance
        signal_thresholds = parameters.get('signal_thresholds', {})
        buy_threshold = signal_thresholds.get('buy_threshold', 70.0)
        sell_threshold = signal_thresholds.get('sell_threshold', 30.0)
        
        # Better thresholds = better performance
        threshold_quality = 1.0 - abs(buy_threshold - 70.0) / 10.0  # Optimal around 70
        threshold_quality *= 1.0 - abs(sell_threshold - 30.0) / 10.0  # Optimal around 30
        
        # Component weight balance
        component_weights = parameters.get('component_weights', {})
        weight_balance = 1.0 - np.std(list(component_weights.values()))  # Prefer balanced weights
        
        # Calculate final metrics
        adjusted_return = base_return * quality_factor * threshold_quality * weight_balance
        volatility = max(0.1, 0.2 - quality_factor * 0.1)  # Better parameters = lower volatility
        sharpe_ratio = adjusted_return / volatility
        max_drawdown = max(5.0, 25.0 - quality_factor * 15.0)  # Better parameters = lower drawdown
        win_rate = min(95.0, 45.0 + quality_factor * 30.0)  # Better parameters = higher win rate
        
        return {
            'annual_return': adjusted_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate
        }
    
    def run_optimization(self, n_trials: int = 50) -> optuna.Study:
        """Run the optimization process."""
        
        self.logger.info(f"Starting confluence optimization with {n_trials} trials")
        
        # Create study
        study = self.optuna_engine.create_study(
            study_name=f"confluence_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            direction='maximize',
            sampler='TPE'
        )
        
        # Run optimization
        study.optimize(self.objective_function, n_trials=n_trials)
        
        # Log best results
        best_trial = study.best_trial
        self.logger.info(f"Best trial: {best_trial.number}")
        self.logger.info(f"Best value: {best_trial.value:.4f}")
        self.logger.info(f"Best parameters summary:")
        
        # Print best parameters in organized format
        best_params = best_trial.params
        component_weights = {}
        signal_thresholds = {}
        technical_params = {}
        
        for key, value in best_params.items():
            if 'concentration' in key:
                component_weights[key] = value
            elif 'threshold' in key or 'confidence' in key or 'agreement' in key:
                signal_thresholds[key] = value
            elif any(tech in key for tech in ['rsi', 'macd', 'williams', 'atr', 'cci']):
                technical_params[key] = value
        
        if component_weights:
            self.logger.info("Component concentrations:")
            for key, value in component_weights.items():
                self.logger.info(f"  {key}: {value:.3f}")
        
        if signal_thresholds:
            self.logger.info("Signal thresholds:")
            for key, value in signal_thresholds.items():
                self.logger.info(f"  {key}: {value:.3f}")
        
        return study
    
    def analyze_results(self, study: optuna.Study) -> Dict[str, Any]:
        """Analyze optimization results and provide insights."""
        
        # Get parameter importance (handle zero variance case)
        try:
            importance = optuna.importance.get_param_importances(study)
        except RuntimeError as e:
            self.logger.warning(f"Could not calculate parameter importance: {e}")
            importance = {}
        
        # Find top performing trials
        top_trials = sorted(study.trials, key=lambda t: t.value or 0, reverse=True)[:5]
        
        # Calculate performance statistics
        all_values = [t.value for t in study.trials if t.value is not None]
        performance_stats = {
            'mean_performance': np.mean(all_values),
            'std_performance': np.std(all_values),
            'best_performance': max(all_values),
            'improvement': max(all_values) - np.mean(all_values[:10])  # Improvement over first 10 trials
        }
        
        analysis = {
            'study_summary': {
                'total_trials': len(study.trials),
                'completed_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
                'best_value': study.best_value,
                'best_trial': study.best_trial.number
            },
            'parameter_importance': importance,
            'performance_stats': performance_stats,
            'top_trials': [
                {
                    'trial': t.number,
                    'value': t.value,
                    'key_params': {k: v for k, v in t.params.items() 
                                 if k in list(importance.keys())[:5]}
                }
                for t in top_trials
            ]
        }
        
        # Log analysis
        self.logger.info("\n=== OPTIMIZATION ANALYSIS ===")
        self.logger.info(f"Completed {analysis['study_summary']['completed_trials']} trials")
        self.logger.info(f"Best performance: {analysis['study_summary']['best_value']:.4f}")
        self.logger.info(f"Average performance: {performance_stats['mean_performance']:.4f}")
        self.logger.info(f"Performance improvement: {performance_stats['improvement']:.4f}")
        
        self.logger.info("\nTop 5 most important parameters:")
        for param, importance_score in list(importance.items())[:5]:
            self.logger.info(f"  {param}: {importance_score:.4f}")
        
        return analysis
    
    def export_best_parameters(self, study: optuna.Study, output_path: str) -> None:
        """Export best parameters for production use."""
        
        # Get best parameters
        best_params = study.best_trial.params
        
        # Reconstruct parameter structure
        best_confluence_params = suggest_confluence_parameters(study.best_trial, 'comprehensive')
        
        # Create production configuration
        production_config = {
            'confluence_optimization': {
                'enabled': True,
                'optimization_date': datetime.now().isoformat(),
                'best_trial': study.best_trial.number,
                'best_score': study.best_value,
                'optimized_parameters': best_confluence_params,
                'raw_optuna_parameters': best_params
            }
        }
        
        # Write to file
        import yaml
        with open(output_path, 'w') as f:
            yaml.dump(production_config, f, default_flow_style=False)
        
        self.logger.info(f"Exported best parameters to {output_path}")

def main():
    """Run the confluence optimization demonstration."""
    
    print("=== Confluence Engine Optimization Demo ===\n")
    
    # Initialize demo
    demo = ConfluenceOptimizationDemo()
    
    # Run optimization
    study = demo.run_optimization(n_trials=30)  # Reduced for demo
    
    # Analyze results
    analysis = demo.analyze_results(study)
    
    # Export best parameters
    output_path = os.path.join(
        os.path.dirname(__file__), 
        f"confluence_best_params_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    )
    demo.export_best_parameters(study, output_path)
    
    print(f"\n=== Demo Complete ===")
    print(f"Best optimization score: {study.best_value:.4f}")
    print(f"Trials completed: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
    print(f"Best parameters exported to: {output_path}")

if __name__ == "__main__":
    main()