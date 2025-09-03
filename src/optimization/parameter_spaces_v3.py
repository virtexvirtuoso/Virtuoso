"""
Enhanced parameter space definitions for Virtuoso 6-dimensional analysis system.
Optimized for production trading with safety constraints and VPS resource limits.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import optuna
import numpy as np
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logging_extensions import get_logger

logger = get_logger(__name__)


class ParameterType(Enum):
    """Parameter types for optimization."""
    INTEGER = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    DISCRETE = "discrete"
    LOGARITHMIC = "logarithmic"


@dataclass
class ParameterDefinition:
    """Enhanced parameter definition with constraints and metadata."""
    name: str
    param_type: ParameterType
    range: Union[Tuple[float, float], List[Any]]
    default: Any
    step: Optional[float] = None
    log_scale: bool = False
    constraints: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0  # Parameter importance weight
    safe_range: Optional[Tuple[float, float]] = None  # Safe production range
    description: str = ""
    
    def suggest(self, trial: optuna.Trial, prefix: str = "") -> Any:
        """Suggest parameter value using Optuna trial."""
        param_name = f"{prefix}{self.name}" if prefix else self.name
        
        # Apply safety constraints for production
        actual_range = self.safe_range if self.safe_range else self.range
        
        if self.param_type == ParameterType.INTEGER:
            return trial.suggest_int(
                param_name, 
                int(actual_range[0]), 
                int(actual_range[1]),
                step=int(self.step) if self.step else 1,
                log=self.log_scale
            )
        elif self.param_type == ParameterType.FLOAT:
            if self.step:
                return trial.suggest_float(
                    param_name,
                    actual_range[0],
                    actual_range[1],
                    step=self.step,
                    log=self.log_scale
                )
            else:
                return trial.suggest_float(
                    param_name,
                    actual_range[0],
                    actual_range[1],
                    log=self.log_scale
                )
        elif self.param_type == ParameterType.CATEGORICAL:
            return trial.suggest_categorical(param_name, actual_range)
        elif self.param_type == ParameterType.DISCRETE:
            return trial.suggest_discrete_uniform(
                param_name,
                actual_range[0],
                actual_range[1],
                self.step or 1.0
            )
        else:
            return self.default


class SixDimensionalParameterSpaces:
    """
    Enhanced parameter spaces for Virtuoso's 6-dimensional analysis system.
    
    Dimensions:
    1. Order Flow Analysis - Volume patterns, buy/sell pressure
    2. Sentiment Analysis - Market mood indicators
    3. Liquidity Analysis - Support/resistance zones
    4. Bitcoin Beta - BTC correlation tracking
    5. Smart Money Flow - Institutional activity
    6. Machine Learning - Predictive patterns
    """
    
    def __init__(self, production_mode: bool = True):
        self.production_mode = production_mode
        self.parameter_registry = self._build_comprehensive_registry()
        
        total_params = sum(len(params) for params in self.parameter_registry.values())
        logger.info(f"Initialized 6-dimensional parameter spaces with {total_params} parameters")
    
    def _build_comprehensive_registry(self) -> Dict[str, List[ParameterDefinition]]:
        """Build comprehensive parameter registry for all 6 dimensions."""
        return {
            'order_flow': self._order_flow_parameters(),
            'sentiment': self._sentiment_parameters(),
            'liquidity': self._liquidity_parameters(),
            'bitcoin_beta': self._bitcoin_beta_parameters(),
            'smart_money': self._smart_money_parameters(),
            'machine_learning': self._ml_parameters(),
            'technical_indicators': self._technical_parameters(),
            'risk_management': self._risk_parameters(),
            'confluence': self._confluence_parameters()
        }
    
    def _order_flow_parameters(self) -> List[ParameterDefinition]:
        """Order Flow Analysis parameters."""
        return [
            ParameterDefinition(
                name="volume_ma_period",
                param_type=ParameterType.INTEGER,
                range=(5, 50),
                default=20,
                safe_range=(10, 30) if self.production_mode else None,
                importance=1.2,
                description="Moving average period for volume analysis"
            ),
            ParameterDefinition(
                name="volume_spike_threshold",
                param_type=ParameterType.FLOAT,
                range=(1.5, 5.0),
                default=2.5,
                step=0.1,
                safe_range=(2.0, 3.5) if self.production_mode else None,
                importance=1.5,
                description="Threshold for detecting volume spikes"
            ),
            ParameterDefinition(
                name="buy_sell_ratio_period",
                param_type=ParameterType.INTEGER,
                range=(5, 30),
                default=14,
                safe_range=(10, 20) if self.production_mode else None,
                importance=1.3,
                description="Period for buy/sell ratio calculation"
            ),
            ParameterDefinition(
                name="order_imbalance_threshold",
                param_type=ParameterType.FLOAT,
                range=(0.5, 0.9),
                default=0.7,
                step=0.05,
                safe_range=(0.6, 0.8) if self.production_mode else None,
                importance=1.4,
                description="Threshold for order imbalance detection"
            ),
            ParameterDefinition(
                name="vwap_bands_multiplier",
                param_type=ParameterType.FLOAT,
                range=(1.0, 3.0),
                default=2.0,
                step=0.1,
                safe_range=(1.5, 2.5) if self.production_mode else None,
                importance=1.1,
                description="VWAP bands standard deviation multiplier"
            ),
            ParameterDefinition(
                name="delta_smoothing_period",
                param_type=ParameterType.INTEGER,
                range=(3, 15),
                default=7,
                safe_range=(5, 10) if self.production_mode else None,
                importance=1.0,
                description="Smoothing period for delta calculations"
            )
        ]
    
    def _sentiment_parameters(self) -> List[ParameterDefinition]:
        """Sentiment Analysis parameters."""
        return [
            ParameterDefinition(
                name="fear_greed_weight",
                param_type=ParameterType.FLOAT,
                range=(0.1, 1.0),
                default=0.5,
                step=0.05,
                safe_range=(0.3, 0.7) if self.production_mode else None,
                importance=1.2,
                description="Weight for fear & greed index"
            ),
            ParameterDefinition(
                name="social_sentiment_lag",
                param_type=ParameterType.INTEGER,
                range=(1, 24),
                default=6,
                safe_range=(3, 12) if self.production_mode else None,
                importance=0.8,
                description="Lag hours for social sentiment"
            ),
            ParameterDefinition(
                name="news_impact_decay",
                param_type=ParameterType.FLOAT,
                range=(0.5, 0.99),
                default=0.9,
                step=0.01,
                safe_range=(0.85, 0.95) if self.production_mode else None,
                importance=0.9,
                description="Decay factor for news impact"
            ),
            ParameterDefinition(
                name="market_mood_threshold",
                param_type=ParameterType.FLOAT,
                range=(0.3, 0.8),
                default=0.5,
                step=0.05,
                safe_range=(0.4, 0.6) if self.production_mode else None,
                importance=1.1,
                description="Threshold for market mood changes"
            ),
            ParameterDefinition(
                name="sentiment_smoothing_alpha",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.3),
                default=0.15,
                step=0.01,
                safe_range=(0.1, 0.2) if self.production_mode else None,
                importance=0.7,
                description="EMA smoothing for sentiment"
            )
        ]
    
    def _liquidity_parameters(self) -> List[ParameterDefinition]:
        """Liquidity Analysis parameters."""
        return [
            ParameterDefinition(
                name="liquidity_zone_sensitivity",
                param_type=ParameterType.FLOAT,
                range=(0.001, 0.01),
                default=0.005,
                step=0.0005,
                log_scale=True,
                safe_range=(0.003, 0.007) if self.production_mode else None,
                importance=1.6,
                description="Sensitivity for liquidity zone detection"
            ),
            ParameterDefinition(
                name="support_resistance_lookback",
                param_type=ParameterType.INTEGER,
                range=(20, 200),
                default=100,
                step=10,
                safe_range=(50, 150) if self.production_mode else None,
                importance=1.4,
                description="Lookback period for S/R levels"
            ),
            ParameterDefinition(
                name="liquidity_pool_min_size",
                param_type=ParameterType.FLOAT,
                range=(0.01, 0.1),
                default=0.05,
                step=0.01,
                log_scale=True,
                safe_range=(0.03, 0.07) if self.production_mode else None,
                importance=1.3,
                description="Minimum size for liquidity pools"
            ),
            ParameterDefinition(
                name="order_book_depth_levels",
                param_type=ParameterType.INTEGER,
                range=(5, 50),
                default=20,
                step=5,
                safe_range=(10, 30) if self.production_mode else None,
                importance=1.2,
                description="Number of order book levels to analyze"
            ),
            ParameterDefinition(
                name="liquidity_imbalance_ratio",
                param_type=ParameterType.FLOAT,
                range=(1.5, 4.0),
                default=2.5,
                step=0.1,
                safe_range=(2.0, 3.0) if self.production_mode else None,
                importance=1.5,
                description="Ratio for liquidity imbalance detection"
            )
        ]
    
    def _bitcoin_beta_parameters(self) -> List[ParameterDefinition]:
        """Bitcoin Beta correlation parameters."""
        return [
            ParameterDefinition(
                name="beta_calculation_period",
                param_type=ParameterType.INTEGER,
                range=(10, 100),
                default=30,
                step=5,
                safe_range=(20, 50) if self.production_mode else None,
                importance=1.3,
                description="Period for beta calculation"
            ),
            ParameterDefinition(
                name="correlation_threshold",
                param_type=ParameterType.FLOAT,
                range=(0.3, 0.9),
                default=0.6,
                step=0.05,
                safe_range=(0.5, 0.7) if self.production_mode else None,
                importance=1.4,
                description="Minimum correlation threshold"
            ),
            ParameterDefinition(
                name="beta_smoothing_factor",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.3),
                default=0.15,
                step=0.01,
                safe_range=(0.1, 0.2) if self.production_mode else None,
                importance=1.0,
                description="Smoothing factor for beta values"
            ),
            ParameterDefinition(
                name="regime_change_sensitivity",
                param_type=ParameterType.FLOAT,
                range=(0.1, 0.5),
                default=0.25,
                step=0.05,
                safe_range=(0.2, 0.3) if self.production_mode else None,
                importance=1.2,
                description="Sensitivity to correlation regime changes"
            ),
            ParameterDefinition(
                name="btc_dominance_weight",
                param_type=ParameterType.FLOAT,
                range=(0.1, 0.5),
                default=0.3,
                step=0.05,
                safe_range=(0.2, 0.4) if self.production_mode else None,
                importance=1.1,
                description="Weight for BTC dominance in calculations"
            )
        ]
    
    def _smart_money_parameters(self) -> List[ParameterDefinition]:
        """Smart Money Flow parameters."""
        return [
            ParameterDefinition(
                name="whale_threshold_btc",
                param_type=ParameterType.FLOAT,
                range=(1.0, 100.0),
                default=10.0,
                step=1.0,
                log_scale=True,
                safe_range=(5.0, 20.0) if self.production_mode else None,
                importance=1.5,
                description="Threshold for whale transactions (BTC)"
            ),
            ParameterDefinition(
                name="accumulation_lookback",
                param_type=ParameterType.INTEGER,
                range=(10, 100),
                default=30,
                step=5,
                safe_range=(20, 50) if self.production_mode else None,
                importance=1.3,
                description="Lookback for accumulation patterns"
            ),
            ParameterDefinition(
                name="distribution_sensitivity",
                param_type=ParameterType.FLOAT,
                range=(0.5, 2.0),
                default=1.0,
                step=0.1,
                safe_range=(0.8, 1.2) if self.production_mode else None,
                importance=1.4,
                description="Sensitivity for distribution detection"
            ),
            ParameterDefinition(
                name="institutional_flow_weight",
                param_type=ParameterType.FLOAT,
                range=(0.3, 0.8),
                default=0.6,
                step=0.05,
                safe_range=(0.5, 0.7) if self.production_mode else None,
                importance=1.6,
                description="Weight for institutional flow signals"
            ),
            ParameterDefinition(
                name="smart_money_divergence_threshold",
                param_type=ParameterType.FLOAT,
                range=(0.1, 0.5),
                default=0.3,
                step=0.05,
                safe_range=(0.2, 0.4) if self.production_mode else None,
                importance=1.2,
                description="Threshold for smart money divergence"
            )
        ]
    
    def _ml_parameters(self) -> List[ParameterDefinition]:
        """Machine Learning model parameters."""
        return [
            ParameterDefinition(
                name="ml_lookback_periods",
                param_type=ParameterType.INTEGER,
                range=(10, 100),
                default=30,
                step=5,
                safe_range=(20, 50) if self.production_mode else None,
                importance=1.3,
                description="Lookback periods for ML features"
            ),
            ParameterDefinition(
                name="feature_importance_threshold",
                param_type=ParameterType.FLOAT,
                range=(0.01, 0.1),
                default=0.05,
                step=0.01,
                safe_range=(0.03, 0.07) if self.production_mode else None,
                importance=1.2,
                description="Minimum feature importance threshold"
            ),
            ParameterDefinition(
                name="ensemble_weight_decay",
                param_type=ParameterType.FLOAT,
                range=(0.8, 0.99),
                default=0.95,
                step=0.01,
                safe_range=(0.9, 0.97) if self.production_mode else None,
                importance=1.0,
                description="Weight decay for ensemble models"
            ),
            ParameterDefinition(
                name="prediction_confidence_threshold",
                param_type=ParameterType.FLOAT,
                range=(0.5, 0.9),
                default=0.7,
                step=0.05,
                safe_range=(0.6, 0.8) if self.production_mode else None,
                importance=1.5,
                description="Minimum confidence for predictions"
            ),
            ParameterDefinition(
                name="adaptive_learning_rate",
                param_type=ParameterType.FLOAT,
                range=(0.001, 0.1),
                default=0.01,
                log_scale=True,
                safe_range=(0.005, 0.02) if self.production_mode else None,
                importance=1.1,
                description="Learning rate for online adaptation"
            )
        ]
    
    def _technical_parameters(self) -> List[ParameterDefinition]:
        """Enhanced technical indicators parameters."""
        return [
            # RSI Parameters
            ParameterDefinition(
                name="rsi_period",
                param_type=ParameterType.INTEGER,
                range=(7, 21),
                default=14,
                safe_range=(12, 16) if self.production_mode else None,
                importance=1.4,
                description="RSI calculation period"
            ),
            ParameterDefinition(
                name="rsi_overbought",
                param_type=ParameterType.FLOAT,
                range=(65.0, 80.0),
                default=70.0,
                step=1.0,
                safe_range=(68.0, 72.0) if self.production_mode else None,
                importance=1.2,
                description="RSI overbought threshold"
            ),
            ParameterDefinition(
                name="rsi_oversold",
                param_type=ParameterType.FLOAT,
                range=(20.0, 35.0),
                default=30.0,
                step=1.0,
                safe_range=(28.0, 32.0) if self.production_mode else None,
                importance=1.2,
                description="RSI oversold threshold"
            ),
            
            # MACD Parameters
            ParameterDefinition(
                name="macd_fast",
                param_type=ParameterType.INTEGER,
                range=(8, 15),
                default=12,
                safe_range=(11, 13) if self.production_mode else None,
                importance=1.3,
                description="MACD fast EMA period"
            ),
            ParameterDefinition(
                name="macd_slow",
                param_type=ParameterType.INTEGER,
                range=(20, 30),
                default=26,
                safe_range=(24, 28) if self.production_mode else None,
                importance=1.3,
                description="MACD slow EMA period"
            ),
            ParameterDefinition(
                name="macd_signal",
                param_type=ParameterType.INTEGER,
                range=(7, 12),
                default=9,
                safe_range=(8, 10) if self.production_mode else None,
                importance=1.2,
                description="MACD signal line period"
            ),
            
            # Bollinger Bands
            ParameterDefinition(
                name="bb_period",
                param_type=ParameterType.INTEGER,
                range=(15, 25),
                default=20,
                safe_range=(18, 22) if self.production_mode else None,
                importance=1.3,
                description="Bollinger Bands period"
            ),
            ParameterDefinition(
                name="bb_std_dev",
                param_type=ParameterType.FLOAT,
                range=(1.5, 2.5),
                default=2.0,
                step=0.1,
                safe_range=(1.8, 2.2) if self.production_mode else None,
                importance=1.4,
                description="Bollinger Bands standard deviation"
            ),
            
            # ATR for volatility
            ParameterDefinition(
                name="atr_period",
                param_type=ParameterType.INTEGER,
                range=(10, 20),
                default=14,
                safe_range=(12, 16) if self.production_mode else None,
                importance=1.1,
                description="ATR period for volatility"
            ),
            ParameterDefinition(
                name="atr_multiplier",
                param_type=ParameterType.FLOAT,
                range=(1.0, 3.0),
                default=2.0,
                step=0.1,
                safe_range=(1.5, 2.5) if self.production_mode else None,
                importance=1.2,
                description="ATR multiplier for stops"
            )
        ]
    
    def _risk_parameters(self) -> List[ParameterDefinition]:
        """Risk management parameters."""
        return [
            ParameterDefinition(
                name="max_position_size",
                param_type=ParameterType.FLOAT,
                range=(0.01, 0.1),
                default=0.05,
                step=0.01,
                safe_range=(0.02, 0.05) if self.production_mode else None,
                importance=2.0,  # Critical for safety
                description="Maximum position size as fraction of capital"
            ),
            ParameterDefinition(
                name="stop_loss_percent",
                param_type=ParameterType.FLOAT,
                range=(0.01, 0.05),
                default=0.02,
                step=0.005,
                safe_range=(0.015, 0.025) if self.production_mode else None,
                importance=2.0,  # Critical for safety
                description="Stop loss percentage"
            ),
            ParameterDefinition(
                name="take_profit_ratio",
                param_type=ParameterType.FLOAT,
                range=(1.5, 4.0),
                default=2.5,
                step=0.1,
                safe_range=(2.0, 3.0) if self.production_mode else None,
                importance=1.5,
                description="Take profit to stop loss ratio"
            ),
            ParameterDefinition(
                name="max_drawdown_percent",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.2),
                default=0.1,
                step=0.01,
                safe_range=(0.08, 0.12) if self.production_mode else None,
                importance=2.0,  # Critical for safety
                description="Maximum allowed drawdown"
            ),
            ParameterDefinition(
                name="risk_per_trade",
                param_type=ParameterType.FLOAT,
                range=(0.005, 0.02),
                default=0.01,
                step=0.001,
                safe_range=(0.008, 0.012) if self.production_mode else None,
                importance=1.8,
                description="Risk per trade as fraction of capital"
            )
        ]
    
    def _confluence_parameters(self) -> List[ParameterDefinition]:
        """Confluence scoring weights."""
        return [
            ParameterDefinition(
                name="order_flow_weight",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.3),
                default=0.2,
                step=0.01,
                safe_range=(0.15, 0.25) if self.production_mode else None,
                importance=1.5,
                description="Weight for order flow signals"
            ),
            ParameterDefinition(
                name="sentiment_weight",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.25),
                default=0.15,
                step=0.01,
                safe_range=(0.1, 0.2) if self.production_mode else None,
                importance=1.2,
                description="Weight for sentiment signals"
            ),
            ParameterDefinition(
                name="liquidity_weight",
                param_type=ParameterType.FLOAT,
                range=(0.1, 0.3),
                default=0.2,
                step=0.01,
                safe_range=(0.15, 0.25) if self.production_mode else None,
                importance=1.4,
                description="Weight for liquidity signals"
            ),
            ParameterDefinition(
                name="bitcoin_beta_weight",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.25),
                default=0.15,
                step=0.01,
                safe_range=(0.1, 0.2) if self.production_mode else None,
                importance=1.3,
                description="Weight for Bitcoin beta signals"
            ),
            ParameterDefinition(
                name="smart_money_weight",
                param_type=ParameterType.FLOAT,
                range=(0.1, 0.35),
                default=0.2,
                step=0.01,
                safe_range=(0.15, 0.25) if self.production_mode else None,
                importance=1.6,
                description="Weight for smart money signals"
            ),
            ParameterDefinition(
                name="ml_signal_weight",
                param_type=ParameterType.FLOAT,
                range=(0.05, 0.25),
                default=0.1,
                step=0.01,
                safe_range=(0.08, 0.15) if self.production_mode else None,
                importance=1.1,
                description="Weight for ML predictions"
            ),
            ParameterDefinition(
                name="min_confluence_score",
                param_type=ParameterType.FLOAT,
                range=(0.5, 0.8),
                default=0.65,
                step=0.05,
                safe_range=(0.6, 0.7) if self.production_mode else None,
                importance=1.8,
                description="Minimum confluence score for signals"
            )
        ]
    
    def suggest_parameters(self, trial: optuna.Trial, category: str) -> Dict[str, Any]:
        """Suggest parameters for a specific category."""
        if category not in self.parameter_registry:
            raise ValueError(f"Unknown parameter category: {category}")
        
        params = {}
        for param_def in self.parameter_registry[category]:
            # Apply importance-based sampling probability
            if np.random.random() < param_def.importance:
                params[param_def.name] = param_def.suggest(trial, prefix=f"{category}_")
            else:
                params[param_def.name] = param_def.default
        
        return params
    
    def suggest_all_parameters(self, trial: optuna.Trial) -> Dict[str, Dict[str, Any]]:
        """Suggest all parameters for complete system optimization."""
        all_params = {}
        for category in self.parameter_registry:
            all_params[category] = self.suggest_parameters(trial, category)
        return all_params
    
    def get_default_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get default parameters for all categories."""
        defaults = {}
        for category, param_defs in self.parameter_registry.items():
            defaults[category] = {
                param.name: param.default for param in param_defs
            }
        return defaults
    
    def get_safe_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get safe production parameters."""
        safe_params = {}
        for category, param_defs in self.parameter_registry.items():
            safe_params[category] = {}
            for param in param_defs:
                if param.safe_range:
                    # Use middle of safe range
                    if param.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                        safe_params[category][param.name] = (param.safe_range[0] + param.safe_range[1]) / 2
                        if param.param_type == ParameterType.INTEGER:
                            safe_params[category][param.name] = int(safe_params[category][param.name])
                else:
                    safe_params[category][param.name] = param.default
        return safe_params
    
    def validate_parameters(self, parameters: Dict[str, Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate parameters against constraints."""
        errors = []
        
        for category, params in parameters.items():
            if category not in self.parameter_registry:
                errors.append(f"Unknown category: {category}")
                continue
            
            param_defs = {p.name: p for p in self.parameter_registry[category]}
            
            for param_name, value in params.items():
                if param_name not in param_defs:
                    errors.append(f"Unknown parameter: {category}.{param_name}")
                    continue
                
                param_def = param_defs[param_name]
                
                # Check range constraints
                if param_def.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                    min_val, max_val = param_def.safe_range if self.production_mode and param_def.safe_range else param_def.range
                    if not min_val <= value <= max_val:
                        errors.append(f"{category}.{param_name}={value} outside range [{min_val}, {max_val}]")
                
                # Check categorical constraints
                elif param_def.param_type == ParameterType.CATEGORICAL:
                    if value not in param_def.range:
                        errors.append(f"{category}.{param_name}={value} not in allowed values {param_def.range}")
        
        # Check cross-parameter constraints
        if 'confluence' in parameters:
            weights = parameters['confluence']
            total_weight = sum(v for k, v in weights.items() if k.endswith('_weight'))
            if abs(total_weight - 1.0) > 0.02:
                errors.append(f"Confluence weights sum to {total_weight}, should be 1.0")
        
        return len(errors) == 0, errors
    
    def export_parameter_definitions(self) -> Dict[str, Any]:
        """Export parameter definitions for documentation."""
        export = {}
        for category, param_defs in self.parameter_registry.items():
            export[category] = []
            for param in param_defs:
                export[category].append({
                    'name': param.name,
                    'type': param.param_type.value,
                    'range': param.range,
                    'default': param.default,
                    'safe_range': param.safe_range,
                    'importance': param.importance,
                    'description': param.description
                })
        return export