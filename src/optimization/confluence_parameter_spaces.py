"""
Confluence Engine Optuna Parameter Spaces for Virtuoso Trading System
Specialized parameter optimization for confluence scoring and component weighting.
"""

from typing import Dict, Any, List, Tuple
import optuna
import numpy as np
from pathlib import Path
import yaml

from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)


class ConfluenceParameterSpaces:
    """
    Specialized parameter spaces for optimizing the Confluence Engine.
    
    This class defines the parameter spaces for optimizing all aspects of the
    confluence scoring system, including component weights, thresholds, and 
    algorithmic parameters.
    
    Focus: 100+ confluence-specific parameters for systematic optimization.
    """
    
    def __init__(self):
        self.logger = logger
        self.logger.info("Initialized Confluence Parameter Spaces")
    
    @staticmethod
    def confluence_component_weights(trial: optuna.Trial) -> Dict[str, float]:
        """
        Optimize main component weights with constraint that they sum to 1.0.
        Uses Dirichlet distribution sampling to ensure valid probability distribution.
        """
        # Sample Dirichlet concentration parameters (higher = more concentrated)
        concentrations = {
            'orderbook': trial.suggest_float('orderbook_concentration', 0.5, 3.0),
            'orderflow': trial.suggest_float('orderflow_concentration', 0.5, 3.0),
            'price_structure': trial.suggest_float('price_structure_concentration', 0.3, 2.5),
            'technical': trial.suggest_float('technical_concentration', 0.3, 2.0),
            'volume': trial.suggest_float('volume_concentration', 0.3, 2.5),
            'sentiment': trial.suggest_float('sentiment_concentration', 0.2, 1.5)
        }
        
        # Sample from Dirichlet distribution
        alpha_values = list(concentrations.values())
        weights = np.random.dirichlet(alpha_values)
        
        # Map back to component names
        component_names = list(concentrations.keys())
        component_weights = {name: float(weight) for name, weight in zip(component_names, weights)}
        
        # Log the generated weights for debugging
        logger.debug(f"Generated component weights: {component_weights}")
        logger.debug(f"Sum check: {sum(component_weights.values()):.6f}")
        
        return component_weights
    
    @staticmethod
    def confluence_sub_component_weights(trial: optuna.Trial) -> Dict[str, Dict[str, float]]:
        """
        Optimize sub-component weights within each main component.
        Each sub-component group must sum to 1.0.
        """
        sub_weights = {}
        
        # Technical Indicators Sub-weights
        technical_concentrations = {
            'rsi': trial.suggest_float('tech_rsi_conc', 0.5, 2.5),
            'ao': trial.suggest_float('tech_ao_conc', 0.5, 2.5),
            'macd': trial.suggest_float('tech_macd_conc', 0.3, 2.0),
            'williams_r': trial.suggest_float('tech_williams_conc', 0.3, 2.0),
            'atr': trial.suggest_float('tech_atr_conc', 0.3, 2.0),
            'cci': trial.suggest_float('tech_cci_conc', 0.3, 2.0)
        }
        tech_weights = np.random.dirichlet(list(technical_concentrations.values()))
        sub_weights['technical'] = {name: float(weight) for name, weight in 
                                   zip(technical_concentrations.keys(), tech_weights)}
        
        # Orderbook Indicators Sub-weights
        orderbook_concentrations = {
            'depth': trial.suggest_float('ob_depth_conc', 0.8, 3.0),
            'imbalance': trial.suggest_float('ob_imbalance_conc', 0.6, 2.5),
            'oir': trial.suggest_float('ob_oir_conc', 0.6, 2.5),
            'liquidity': trial.suggest_float('ob_liquidity_conc', 0.4, 2.0),
            'mpi': trial.suggest_float('ob_mpi_conc', 0.3, 1.8),
            'absorption_exhaustion': trial.suggest_float('ob_absorption_conc', 0.2, 1.5),
            'di': trial.suggest_float('ob_di_conc', 0.1, 1.2)
        }
        ob_weights = np.random.dirichlet(list(orderbook_concentrations.values()))
        sub_weights['orderbook'] = {name: float(weight) for name, weight in 
                                   zip(orderbook_concentrations.keys(), ob_weights)}
        
        # Volume Indicators Sub-weights
        volume_concentrations = {
            'volume_delta': trial.suggest_float('vol_delta_conc', 0.6, 2.5),
            'adl': trial.suggest_float('vol_adl_conc', 0.4, 2.0),
            'cmf': trial.suggest_float('vol_cmf_conc', 0.4, 2.0),
            'relative_volume': trial.suggest_float('vol_rel_conc', 0.4, 2.0),
            'obv': trial.suggest_float('vol_obv_conc', 0.4, 2.0),
            'volume_profile': trial.suggest_float('vol_profile_conc', 0.3, 1.5),
            'vwap': trial.suggest_float('vol_vwap_conc', 0.3, 1.5)
        }
        vol_weights = np.random.dirichlet(list(volume_concentrations.values()))
        sub_weights['volume'] = {name: float(weight) for name, weight in 
                                zip(volume_concentrations.keys(), vol_weights)}
        
        return sub_weights
    
    @staticmethod
    def confluence_signal_thresholds(trial: optuna.Trial) -> Dict[str, float]:
        """
        Optimize signal generation thresholds for buy/sell decisions.
        Critical parameters that directly affect signal generation.
        """
        return {
            'buy_threshold': trial.suggest_float('buy_threshold', 65.0, 75.0, step=0.5),
            'sell_threshold': trial.suggest_float('sell_threshold', 30.0, 40.0, step=0.5),
            'neutral_buffer': trial.suggest_float('neutral_buffer', 0.0, 5.0, step=0.5),
            
            # Additional confidence thresholds
            'high_confidence_threshold': trial.suggest_float('high_conf_threshold', 80.0, 90.0, step=1.0),
            'low_confidence_threshold': trial.suggest_float('low_conf_threshold', 20.0, 30.0, step=1.0),
            
            # Signal quality filters
            'min_component_agreement': trial.suggest_float('min_component_agreement', 0.6, 0.9, step=0.05),
            'reliability_threshold': trial.suggest_float('reliability_threshold', 0.7, 0.95, step=0.05)
        }
    
    @staticmethod
    def confluence_transformation_parameters(trial: optuna.Trial) -> Dict[str, float]:
        """
        Optimize data transformation and normalization parameters.
        These affect how raw indicator values are converted to scores.
        """
        return {
            # Sigmoid transformation parameters
            'sigmoid_steepness': trial.suggest_float('sigmoid_steepness', 0.05, 0.25, step=0.01),
            'sigmoid_center': trial.suggest_float('sigmoid_center', 0.4, 0.6, step=0.02),
            
            # Tanh transformation parameters  
            'tanh_sensitivity': trial.suggest_float('tanh_sensitivity', 0.5, 2.5, step=0.1),
            'tanh_scaling': trial.suggest_float('tanh_scaling', 0.8, 1.5, step=0.05),
            
            # Normalization parameters
            'z_score_clipping': trial.suggest_float('z_score_clipping', 2.0, 4.0, step=0.2),
            'percentile_clipping': trial.suggest_float('percentile_clipping', 0.95, 0.99, step=0.01),
            
            # Smoothing parameters
            'ema_smoothing_alpha': trial.suggest_float('ema_smoothing_alpha', 0.1, 0.5, step=0.02),
            'rolling_window_size': trial.suggest_int('rolling_window_size', 5, 20, step=1)
        }
    
    @staticmethod
    def confluence_orderbook_parameters(trial: optuna.Trial) -> Dict[str, Any]:
        """
        Optimize orderbook-specific parameters that affect confluence scoring.
        """
        return {
            # Imbalance parameters
            'imbalance_threshold': trial.suggest_float('ob_imbalance_threshold', 0.1, 0.4, step=0.02),
            'imbalance_sensitivity': trial.suggest_float('ob_imbalance_sensitivity', 0.10, 0.25, step=0.01),
            'imbalance_extreme_threshold': trial.suggest_float('ob_imbalance_extreme', 0.3, 0.7, step=0.05),
            
            # Pressure parameters
            'pressure_threshold': trial.suggest_float('ob_pressure_threshold', 0.15, 0.40, step=0.02),
            'pressure_sensitivity': trial.suggest_float('ob_pressure_sensitivity', 0.5, 1.2, step=0.05),
            'pressure_momentum_factor': trial.suggest_float('ob_pressure_momentum', 0.8, 1.5, step=0.05),
            
            # Depth parameters
            'depth_weight_decay': trial.suggest_float('ob_depth_decay', 0.85, 0.98, step=0.01),
            'depth_significance_threshold': trial.suggest_float('ob_depth_significance', 0.05, 0.2, step=0.01),
            
            # Liquidity parameters
            'liquidity_threshold': trial.suggest_float('ob_liquidity_threshold', 1.0, 2.5, step=0.1),
            'liquidity_depth_weight': trial.suggest_float('ob_liquidity_depth_weight', 0.5, 0.9, step=0.05),
            'liquidity_spread_weight': trial.suggest_float('ob_liquidity_spread_weight', 0.1, 0.5, step=0.05),
            
            # Spread parameters
            'spread_relative_threshold': trial.suggest_float('ob_spread_threshold', 0.0005, 0.005, step=0.0001),
            'spread_volatility_adjustment': trial.suggest_categorical('ob_spread_vol_adj', [True, False]),
        }
    
    @staticmethod
    def confluence_volume_parameters(trial: optuna.Trial) -> Dict[str, Any]:
        """
        Optimize volume-specific parameters for confluence scoring.
        """
        return {
            # Relative volume parameters
            'rel_vol_significant_threshold': trial.suggest_float('vol_rel_significant', 1.5, 3.0, step=0.1),
            'rel_vol_strong_threshold': trial.suggest_float('vol_rel_strong', 2.5, 4.0, step=0.1),
            'rel_vol_extreme_threshold': trial.suggest_float('vol_rel_extreme', 3.0, 5.0, step=0.2),
            'rel_vol_price_weight': trial.suggest_float('vol_rel_price_weight', 0.4, 0.8, step=0.05),
            
            # Volume delta parameters
            'vol_delta_threshold': trial.suggest_float('vol_delta_threshold', 1.0, 2.5, step=0.1),
            'vol_delta_smoothing': trial.suggest_int('vol_delta_smoothing', 3, 8, step=1),
            
            # CMF parameters
            'cmf_smoothing': trial.suggest_float('cmf_smoothing', 0.2, 0.8, step=0.05),
            'cmf_threshold': trial.suggest_float('cmf_threshold', -0.1, 0.1, step=0.02),
            
            # OBV parameters
            'obv_smoothing': trial.suggest_int('obv_smoothing', 3, 10, step=1),
            'obv_trend_lookback': trial.suggest_int('obv_trend_lookback', 10, 20, step=2),
            
            # Volume profile parameters
            'vol_profile_value_area': trial.suggest_float('vol_profile_value_area', 0.6, 0.8, step=0.02)
        }
    
    @staticmethod
    def confluence_technical_parameters(trial: optuna.Trial) -> Dict[str, Any]:
        """
        Optimize technical indicator parameters for confluence scoring.
        """
        return {
            # RSI parameters
            'rsi_overbought': trial.suggest_float('rsi_overbought', 65.0, 80.0, step=1.0),
            'rsi_oversold': trial.suggest_float('rsi_oversold', 20.0, 35.0, step=1.0),
            'rsi_period': trial.suggest_int('rsi_period', 10, 20, step=1),
            
            # MACD parameters  
            'macd_fast_period': trial.suggest_int('macd_fast', 8, 16, step=1),
            'macd_slow_period': trial.suggest_int('macd_slow', 20, 35, step=1),
            'macd_signal_period': trial.suggest_int('macd_signal', 6, 12, step=1),
            
            # Williams %R parameters
            'williams_period': trial.suggest_int('williams_period', 10, 20, step=1),
            'williams_overbought': trial.suggest_float('williams_overbought', -25.0, -15.0, step=1.0),
            'williams_oversold': trial.suggest_float('williams_oversold', -85.0, -75.0, step=1.0),
            
            # ATR parameters
            'atr_period': trial.suggest_int('atr_period', 10, 20, step=1),
            'atr_multiplier': trial.suggest_float('atr_multiplier', 1.5, 3.0, step=0.1),
            
            # CCI parameters
            'cci_period': trial.suggest_int('cci_period', 15, 25, step=1),
            'cci_overbought': trial.suggest_float('cci_overbought', 80.0, 120.0, step=5.0),
            'cci_oversold': trial.suggest_float('cci_oversold', -120.0, -80.0, step=5.0),
            
            # Divergence parameters
            'divergence_impact': trial.suggest_float('divergence_impact', 0.1, 0.4, step=0.02),
            'divergence_lookback': trial.suggest_int('divergence_lookback', 10, 30, step=2)
        }
    
    @staticmethod
    def confluence_timeframe_weights(trial: optuna.Trial) -> Dict[str, float]:
        """
        Optimize timeframe weighting with constraint that they sum to 1.0.
        """
        # Sample Dirichlet concentration parameters
        concentrations = {
            'base': trial.suggest_float('base_timeframe_conc', 1.0, 4.0),
            'ltf': trial.suggest_float('ltf_timeframe_conc', 0.8, 3.0), 
            'mtf': trial.suggest_float('mtf_timeframe_conc', 0.5, 2.5),
            'htf': trial.suggest_float('htf_timeframe_conc', 0.3, 2.0)
        }
        
        # Sample from Dirichlet distribution
        alpha_values = list(concentrations.values())
        weights = np.random.dirichlet(alpha_values)
        
        # Map back to timeframe names
        timeframe_names = list(concentrations.keys())
        timeframe_weights = {name: float(weight) for name, weight in zip(timeframe_names, weights)}
        
        return timeframe_weights
    
    @staticmethod
    def confluence_comprehensive_optimization(trial: optuna.Trial) -> Dict[str, Any]:
        """
        Comprehensive parameter optimization for entire confluence system.
        This is the main optimization function that combines all parameter spaces.
        """
        parameters = {}
        
        # Component weights (most important)
        parameters['component_weights'] = ConfluenceParameterSpaces.confluence_component_weights(trial)
        
        # Sub-component weights
        parameters['sub_component_weights'] = ConfluenceParameterSpaces.confluence_sub_component_weights(trial)
        
        # Signal thresholds (critical for performance)
        parameters['signal_thresholds'] = ConfluenceParameterSpaces.confluence_signal_thresholds(trial)
        
        # Transformation parameters
        parameters['transformation_params'] = ConfluenceParameterSpaces.confluence_transformation_parameters(trial)
        
        # Timeframe weights
        parameters['timeframe_weights'] = ConfluenceParameterSpaces.confluence_timeframe_weights(trial)
        
        # Component-specific parameters
        parameters['orderbook_params'] = ConfluenceParameterSpaces.confluence_orderbook_parameters(trial)
        parameters['volume_params'] = ConfluenceParameterSpaces.confluence_volume_parameters(trial)
        parameters['technical_params'] = ConfluenceParameterSpaces.confluence_technical_parameters(trial)
        
        # Log parameter count for monitoring
        total_params = sum(len(v) if isinstance(v, dict) else 1 for v in parameters.values())
        logger.info(f"Generated {total_params} confluence parameters for trial {trial.number}")
        
        return parameters
    
    @staticmethod
    def validate_parameter_constraints(parameters: Dict[str, Any]) -> bool:
        """
        Validate that generated parameters meet all constraints.
        """
        try:
            # Check component weights sum to 1.0
            if 'component_weights' in parameters:
                weight_sum = sum(parameters['component_weights'].values())
                if not (0.99 <= weight_sum <= 1.01):  # Allow small floating point errors
                    logger.warning(f"Component weights sum to {weight_sum}, not 1.0")
                    return False
            
            # Check sub-component weights sum to 1.0
            if 'sub_component_weights' in parameters:
                for component, sub_weights in parameters['sub_component_weights'].items():
                    sub_sum = sum(sub_weights.values())
                    if not (0.99 <= sub_sum <= 1.01):
                        logger.warning(f"{component} sub-weights sum to {sub_sum}, not 1.0")
                        return False
            
            # Check timeframe weights sum to 1.0
            if 'timeframe_weights' in parameters:
                tf_sum = sum(parameters['timeframe_weights'].values())
                if not (0.99 <= tf_sum <= 1.01):
                    logger.warning(f"Timeframe weights sum to {tf_sum}, not 1.0")
                    return False
            
            # Check signal thresholds are logical
            if 'signal_thresholds' in parameters:
                thresholds = parameters['signal_thresholds']
                if thresholds.get('buy_threshold', 70) <= thresholds.get('sell_threshold', 35):
                    logger.warning("Buy threshold must be higher than sell threshold")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            return False
    
    def export_parameter_ranges(self, output_path: Path) -> None:
        """Export parameter ranges for documentation and analysis."""
        ranges_doc = {
            'confluence_optimization_parameters': {
                'component_weights': {
                    'orderbook': {'range': [0.10, 0.40], 'current': 0.25},
                    'orderflow': {'range': [0.10, 0.40], 'current': 0.25},
                    'price_structure': {'range': [0.05, 0.30], 'current': 0.16},
                    'technical': {'range': [0.05, 0.25], 'current': 0.11},
                    'volume': {'range': [0.05, 0.30], 'current': 0.16},
                    'sentiment': {'range': [0.02, 0.20], 'current': 0.07}
                },
                'signal_thresholds': {
                    'buy_threshold': {'range': [65.0, 75.0], 'current': 69.5},
                    'sell_threshold': {'range': [30.0, 40.0], 'current': 35.0},
                    'neutral_buffer': {'range': [0.0, 5.0], 'current': 0.0}
                },
                'total_parameters': '100+',
                'optimization_impact': 'High - directly affects signal generation and scoring'
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(ranges_doc, f, default_flow_style=False)
        
        logger.info(f"Exported confluence parameter ranges to {output_path}")


# Convenience function for easy access
def suggest_confluence_parameters(trial: optuna.Trial, parameter_category: str = 'comprehensive') -> Dict[str, Any]:
    """
    Convenience function to suggest confluence parameters for a trial.
    
    Args:
        trial: Optuna trial object
        parameter_category: Which parameter set to optimize
            - 'comprehensive': All confluence parameters (default)
            - 'weights': Only component and sub-component weights
            - 'thresholds': Only signal thresholds
            - 'technical': Only technical indicator parameters
            - 'orderbook': Only orderbook parameters
            - 'volume': Only volume parameters
    """
    if parameter_category == 'comprehensive':
        return ConfluenceParameterSpaces.confluence_comprehensive_optimization(trial)
    elif parameter_category == 'weights':
        return {
            'component_weights': ConfluenceParameterSpaces.confluence_component_weights(trial),
            'sub_component_weights': ConfluenceParameterSpaces.confluence_sub_component_weights(trial)
        }
    elif parameter_category == 'thresholds':
        return ConfluenceParameterSpaces.confluence_signal_thresholds(trial)
    elif parameter_category == 'technical':
        return ConfluenceParameterSpaces.confluence_technical_parameters(trial)
    elif parameter_category == 'orderbook':
        return ConfluenceParameterSpaces.confluence_orderbook_parameters(trial)
    elif parameter_category == 'volume':
        return ConfluenceParameterSpaces.confluence_volume_parameters(trial)
    else:
        raise ValueError(f"Unknown parameter category: {parameter_category}")