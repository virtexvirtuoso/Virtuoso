# src/indicators/orderflow_indicators.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Tuple, List, Union, Optional
from src.utils.error_handling import handle_indicator_error
import time
import traceback
from src.core.analysis.confluence import DataValidator
from .base_indicator import BaseIndicator, DebugLevel, debug_method
from .debug_template import DebugLoggingMixin
from ..core.logger import Logger
from scipy import stats
import json
# Move InterpretationGenerator import to top level to avoid dynamic imports
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.core.analysis.indicator_utils import log_indicator_results as centralized_log_indicator_results

# Get module logger
logger = logging.getLogger('OrderflowIndicators')

class DataUnavailableError(Exception):
    pass

class OrderflowIndicators(BaseIndicator, DebugLoggingMixin):
    """Orderflow-based trading indicators.
    
    Enhanced with comprehensive debug logging following OrderbookIndicators model.
    """

    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        """Initialize OrderflowIndicators."""
        # Set required attributes before calling super().__init__
        self.indicator_type = 'orderflow'
        
        # Initialize component weights with defaults - use the same keys as component scores
        default_weights = {
            'cvd': 0.25,                  # Cumulative Volume Delta (buy vs sell volume)
            'trade_flow_score': 0.20,     # Buy vs sell trade flow
            'imbalance_score': 0.15,      # Trades-based imbalance (temporal flow analysis)
            'open_interest_score': 0.15,   # Open interest analysis
            'pressure_score': 0.10,       # Trades-based pressure (trade aggression analysis)
            'liquidity_score': 0.10,      # Liquidity score based on trade frequency and volume
            'liquidity_zones': 0.05       # Smart Money Concepts - Liquidity Zones
        }
        
        # Cache for computed values to avoid redundant calculations
        self._cache = {}
        
        # **** IMPORTANT: Must set component_weights BEFORE calling super().__init__ ****
        # Initialize component weights dictionary with defaults
        self.component_weights = default_weights.copy()
        
        # Now that component_weights is set, call super().__init__
        super().__init__(config, logger)
        
        # Try to load weights from the confluence configuration
        confluence_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('orderflow', {})
        
        # Map config weight names to component weight keys
        weight_mapping = {
            'cvd': 'cvd',
            'trade_flow': 'trade_flow_score',
            'imbalance': 'imbalance_score',
            'open_interest': 'open_interest_score',
            'pressure': 'pressure_score',
            'liquidity': 'liquidity_score',
            'liquidity_zones': 'liquidity_zones'
        }
        
        # Override default weights with those from confluence config if available
        if confluence_weights:
            for config_key, component_key in weight_mapping.items():
                if config_key in confluence_weights:
                    self.component_weights[component_key] = float(confluence_weights[config_key])
        
        # Now validate and normalize weights
        self._validate_weights()
        
        # Configure lookback periods
        self.divergence_lookback = config.get('divergence_lookback', 20)
        self.min_trades = config.get('min_trades', 100)
        self.cvd_normalization = config.get('cvd_normalization', 'total_volume')
        
        # Configure debug levels
        self.debug_level = config.get('debug_level', 1)
        
        # Configure timeframe weights for multi-timeframe analysis
        self.timeframe_weights = {
            'base': 0.4,  # Base timeframe (usually 1 minute)
            'ltf': 0.3,   # Lower timeframe (usually 5 minutes)
            'mtf': 0.2,   # Medium timeframe (usually 30 minutes)
            'htf': 0.1    # Higher timeframe (usually 4 hours)
        }
        
        # Apply any custom timeframe weights from config
        if 'timeframe_weights' in config:
            for tf, weight in config['timeframe_weights'].items():
                if tf in self.timeframe_weights:
                    self.timeframe_weights[tf] = float(weight)
                    
        # Configure interpretation thresholds
        self.thresholds = {
            'strong_buy': 70,
            'buy': 60,
            'neutral_high': 55,
            'neutral': 50,
            'neutral_low': 45,
            'sell': 40,
            'strong_sell': 30
        }
        
        # Apply any custom thresholds from config
        if 'thresholds' in config:
            for label, value in config['thresholds'].items():
                if label in self.thresholds:
                    self.thresholds[label] = float(value)
        
        # Initialize parameters
        self.volume_threshold = config.get('volume_threshold', 1.5)
        self.flow_window = config.get('flow_window', 20)
        self.momentum_lookback = config.get('momentum_lookback', 10)
        
        # Initialize divergence parameters
        divergence_config = config.get('divergence', {})
        self.divergence_strength_threshold = divergence_config.get('strength_threshold', 20.0)
        self.divergence_impact = divergence_config.get('impact_multiplier', 0.2)
        self.time_weighting_enabled = divergence_config.get('time_weighting', True)
        self.recency_factor = divergence_config.get('recency_factor', 1.2)
        
        # Initialize tracking variables
        self.last_component_scores = {}
        self.trade_history = []
        
        # Intelligent debug tracking
        self._debug_stats = {
            'calculation_counts': {},
            'cache_hits': {},
            'performance_metrics': {},
            'threshold_hits': {},
            'scenario_counts': {
                'oi_scenario_1': 0,  # OI↑ + Price↑ = Bullish
                'oi_scenario_2': 0,  # OI↓ + Price↑ = Bearish
                'oi_scenario_3': 0,  # OI↑ + Price↓ = Bearish
                'oi_scenario_4': 0,  # OI↓ + Price↓ = Bullish
                'oi_neutral': 0,     # Minimal changes
                'cvd_bullish_confirmation': 0,
                'cvd_bearish_confirmation': 0,
                'cvd_bullish_divergence': 0,
                'cvd_bearish_divergence': 0
            }
        }
        
        # Validate weights
        self._validate_weights()

    @property
    def required_data(self) -> List[str]:
        """Required data fields for orderflow analysis."""
        return ['orderbook', 'trades', 'ohlcv']
    
    def _log_intelligent_debug(self, component: str, message: str, level: str = "DEBUG", 
                              track_performance: bool = False, scenario: str = None):
        """Intelligent debug logging with performance tracking and scenario counting.
        
        Args:
            component: Component name (e.g., 'OI', 'CVD', 'FLOW')
            message: Debug message
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            track_performance: Whether to track performance metrics
            scenario: Scenario name for counting (e.g., 'oi_scenario_1')
        """
        # Track calculation counts
        if component not in self._debug_stats['calculation_counts']:
            self._debug_stats['calculation_counts'][component] = 0
        self._debug_stats['calculation_counts'][component] += 1
        
        # Track scenario counts
        if scenario and scenario in self._debug_stats['scenario_counts']:
            self._debug_stats['scenario_counts'][scenario] += 1
        
        # Enhanced message with context
        count = self._debug_stats['calculation_counts'][component]
        enhanced_message = f"[{component}#{count}] {message}"
        
        # Add scenario info if provided
        if scenario:
            scenario_count = self._debug_stats['scenario_counts'].get(scenario, 0)
            enhanced_message += f" [Scenario: {scenario}#{scenario_count}]"
        
        # Log based on level
        if level == "INFO":
            self.logger.info(enhanced_message)
        elif level == "WARNING":
            self.logger.warning(enhanced_message)
        elif level == "ERROR":
            self.logger.error(enhanced_message)
        else:
            self.logger.debug(enhanced_message)
    
    def _log_cache_hit(self, component: str, cache_key: str):
        """Log cache hit with tracking."""
        if component not in self._debug_stats['cache_hits']:
            self._debug_stats['cache_hits'][component] = 0
        self._debug_stats['cache_hits'][component] += 1
        
        hit_count = self._debug_stats['cache_hits'][component]
        self._log_intelligent_debug(component, f"Cache hit #{hit_count} for key: {cache_key[:50]}...")
    
    def _log_performance_summary(self):
        """Log performance summary with intelligent insights."""
        if not self._debug_stats['calculation_counts']:
            return
            
        self.logger.info("\n" + "="*60)
        self.logger.info("ORDERFLOW INDICATORS PERFORMANCE SUMMARY")
        self.logger.info("="*60)
        
        # Calculation counts
        self.logger.info("Component Calculation Counts:")
        for component, count in self._debug_stats['calculation_counts'].items():
            cache_hits = self._debug_stats['cache_hits'].get(component, 0)
            cache_ratio = (cache_hits / count * 100) if count > 0 else 0
            self.logger.info(f"  {component}: {count} calculations, {cache_hits} cache hits ({cache_ratio:.1f}%)")
        
        # Scenario analysis
        self.logger.info("\nScenario Distribution:")
        total_oi_scenarios = sum([
            self._debug_stats['scenario_counts']['oi_scenario_1'],
            self._debug_stats['scenario_counts']['oi_scenario_2'],
            self._debug_stats['scenario_counts']['oi_scenario_3'],
            self._debug_stats['scenario_counts']['oi_scenario_4'],
            self._debug_stats['scenario_counts']['oi_neutral']
        ])
        
        if total_oi_scenarios > 0:
            self.logger.info("  Open Interest Scenarios:")
            for scenario, count in self._debug_stats['scenario_counts'].items():
                if scenario.startswith('oi_'):
                    percentage = (count / total_oi_scenarios * 100) if total_oi_scenarios > 0 else 0
                    scenario_name = {
                        'oi_scenario_1': 'OI↑ + Price↑ = Bullish',
                        'oi_scenario_2': 'OI↓ + Price↑ = Bearish',
                        'oi_scenario_3': 'OI↑ + Price↓ = Bearish',
                        'oi_scenario_4': 'OI↓ + Price↓ = Bullish',
                        'oi_neutral': 'Minimal Changes'
                    }.get(scenario, scenario)
                    self.logger.info(f"    {scenario_name}: {count} ({percentage:.1f}%)")
        
        total_cvd_scenarios = sum([
            self._debug_stats['scenario_counts']['cvd_bullish_confirmation'],
            self._debug_stats['scenario_counts']['cvd_bearish_confirmation'],
            self._debug_stats['scenario_counts']['cvd_bullish_divergence'],
            self._debug_stats['scenario_counts']['cvd_bearish_divergence']
        ])
        
        if total_cvd_scenarios > 0:
            self.logger.info("  CVD Scenarios:")
            for scenario, count in self._debug_stats['scenario_counts'].items():
                if scenario.startswith('cvd_'):
                    percentage = (count / total_cvd_scenarios * 100) if total_cvd_scenarios > 0 else 0
                    scenario_name = {
                        'cvd_bullish_confirmation': 'Price↑ + CVD↑ = Bullish Confirmation',
                        'cvd_bearish_confirmation': 'Price↓ + CVD↓ = Bearish Confirmation',
                        'cvd_bullish_divergence': 'Price↓ + CVD↑ = Bullish Divergence',
                        'cvd_bearish_divergence': 'Price↑ + CVD↓ = Bearish Divergence'
                    }.get(scenario, scenario)
                    self.logger.info(f"    {scenario_name}: {count} ({percentage:.1f}%)")
        
        self.logger.info("="*60)

    @debug_method(DebugLevel.DETAILED)
    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate all orderflow indicators with comprehensive debug logging.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            dict: Dictionary of calculated indicators
        """
        start_time = time.time()
        
        try:
            # Reset cache for new calculation
            self._cache = {}
            
            symbol = market_data.get('symbol', '')
            self.logger.info(f"\n=== ORDERFLOW INDICATORS Detailed Calculation ===")
            self.logger.info(f"Symbol: {symbol}")
            
            # 1. Log data quality metrics
            self._log_data_quality_metrics(market_data)
            
            # 2. Validate input with detailed logging
            self._log_calculation_step("Input Validation", {
                "market_data_keys": list(market_data.keys()),
                "has_trades": 'trades' in market_data,
                "has_orderbook": 'orderbook' in market_data,
                "has_ohlcv": 'ohlcv' in market_data,
                "ohlcv_timeframes": list(market_data.get('ohlcv', {}).keys()) if 'ohlcv' in market_data else []
            })
            
            if not market_data:
                self.logger.error("❌ No market data provided")
                return self.create_error_result("No market data provided")
            
            if not self.validate_input(market_data):
                self.logger.error("❌ Input validation failed")
                return self.create_error_result("Invalid input data")
            
            self.logger.info("✅ Input validation passed successfully")
            
            # 3. Component calculation with timing
            component_times = {}
            component_scores = {}
            
            # CVD calculation
            start_component = time.time()
            self._log_component_calculation_header("Cumulative Volume Delta", f"Analyzing buy vs sell volume flow")
            
            cvd_value = self._calculate_cvd(market_data)
            component_scores['cvd'] = cvd_value
            
            self._log_calculation_step("CVD Results", {
                "cvd_value": cvd_value,
                "interpretation": "Bullish flow" if cvd_value > 60 else "Bearish flow" if cvd_value < 40 else "Neutral flow"
            })
            
            component_times['cvd'] = self._log_component_timing("CVD", start_component)
            
            # Trade Flow calculation
            start_component = time.time()
            self._log_component_calculation_header("Trade Flow", f"Analyzing buy/sell trade distribution")
            
            trade_flow_score = self._calculate_trade_flow_score(market_data)
            component_scores['trade_flow_score'] = trade_flow_score
            
            self._log_calculation_step("Trade Flow Results", {
                "trade_flow_score": trade_flow_score,
                "interpretation": "Buy dominated" if trade_flow_score > 60 else "Sell dominated" if trade_flow_score < 40 else "Balanced"
            })
            
            component_times['trade_flow_score'] = self._log_component_timing("Trade Flow", start_component)
            
            # Imbalance calculation
            start_component = time.time()
            self._log_component_calculation_header("Trade Imbalance", f"Analyzing temporal flow imbalances")
            
            imbalance_score = self._calculate_trades_imbalance_score(market_data)
            component_scores['imbalance_score'] = imbalance_score
            
            self._log_calculation_step("Imbalance Results", {
                "imbalance_score": imbalance_score,
                "interpretation": "Strong imbalance" if abs(imbalance_score - 50) > 20 else "Moderate imbalance" if abs(imbalance_score - 50) > 10 else "Balanced"
            })
            
            component_times['imbalance_score'] = self._log_component_timing("Trade Imbalance", start_component)
            
            # Open Interest calculation
            start_component = time.time()
            self._log_component_calculation_header("Open Interest", f"Analyzing futures position changes")
            
            open_interest_score = self._calculate_open_interest_score(market_data)
            component_scores['open_interest_score'] = open_interest_score
            
            self._log_calculation_step("Open Interest Results", {
                "oi_score": open_interest_score,
                "interpretation": "OI increasing" if open_interest_score > 60 else "OI decreasing" if open_interest_score < 40 else "OI stable"
            })
            
            component_times['open_interest_score'] = self._log_component_timing("Open Interest", start_component)
            
            # Pressure calculation
            start_component = time.time()
            self._log_component_calculation_header("Trade Pressure", f"Analyzing trade aggression patterns")
            
            pressure_score = self._calculate_trades_pressure_score(market_data)
            component_scores['pressure_score'] = pressure_score
            
            self._log_calculation_step("Pressure Results", {
                "pressure_score": pressure_score,
                "interpretation": "Aggressive buying" if pressure_score > 60 else "Aggressive selling" if pressure_score < 40 else "Neutral pressure"
            })
            
            component_times['pressure_score'] = self._log_component_timing("Trade Pressure", start_component)
            
            # Liquidity calculation
            start_component = time.time()
            self._log_component_calculation_header("Liquidity", f"Analyzing market liquidity conditions")
            
            liquidity_score = self._calculate_liquidity_score(market_data)
            component_scores['liquidity_score'] = liquidity_score
            
            self._log_calculation_step("Liquidity Results", {
                "liquidity_score": liquidity_score,
                "interpretation": "High liquidity" if liquidity_score > 60 else "Low liquidity" if liquidity_score < 40 else "Normal liquidity"
            })
            
            component_times['liquidity_score'] = self._log_component_timing("Liquidity", start_component)
            
            # Liquidity Zones calculation
            start_component = time.time()
            self._log_component_calculation_header("Liquidity Zones", f"Analyzing smart money liquidity zones")
            
            liquidity_zones_score = self._calculate_liquidity_zones_score(market_data)
            component_scores['liquidity_zones'] = liquidity_zones_score
            
            self._log_calculation_step("Liquidity Zones Results", {
                "zones_score": liquidity_zones_score,
                "interpretation": "Near liquidity zones" if abs(liquidity_zones_score - 50) > 20 else "Away from zones"
            })
            
            component_times['liquidity_zones'] = self._log_component_timing("Liquidity Zones", start_component)
            
            # 4. Calculate divergences
            self._log_calculation_step("Divergence Analysis", {
                "checking_price_cvd_divergence": True,
                "checking_price_oi_divergence": True,
                "checking_timeframe_divergence": True
            })
            
            # Calculate price-CVD and price-OI divergences
            price_cvd_divergence = self._calculate_price_cvd_divergence(market_data)
            price_oi_divergence = self._calculate_price_oi_divergence(market_data)
            
            # Multi-timeframe divergence analysis
            timeframe_divergences = {}
            if 'ohlcv' in market_data and isinstance(market_data['ohlcv'], dict):
                if len(market_data['ohlcv']) > 1:
                    timeframe_divergences = self._analyze_timeframe_divergence(market_data['ohlcv'])
            
            divergences = {
                'price_cvd': price_cvd_divergence,
                'price_oi': price_oi_divergence,
                'timeframe': timeframe_divergences
            }
            
            # Log divergences if found
            if any(divergences.values()):
                self.logger.info(f"Divergences detected: {divergences}")
            
            # 5. Apply divergence bonuses
            adjusted_scores = self._apply_divergence_bonuses(component_scores, divergences)
            
            # 6. Calculate final weighted score
            final_score = self._compute_weighted_score(adjusted_scores)
            
            # 7. Log performance metrics
            total_time = (time.time() - start_time) * 1000
            self._log_performance_metrics(component_times, total_time)
            
            # 8. Enhanced logging with centralized formatting
            centralized_log_indicator_results(
                logger=self.logger,
                indicator_name="Orderflow",
                final_score=final_score,
                component_scores=adjusted_scores,
                weights=self.component_weights,
                symbol=symbol
            )
            
            # 9. Add enhanced trading context logging
            self._log_trading_context(final_score, adjusted_scores, symbol, "Orderflow")
            
            # 10. Generate interpretation
            try:
                interpreter = InterpretationGenerator()
                interpretation_data = {
                    'score': final_score,
                    'components': adjusted_scores,
                    'signals': {
                        'cvd': cvd_value,
                        'imbalance_score': imbalance_score,
                        'trade_flow_score': trade_flow_score,
                        'open_interest_score': open_interest_score,
                        'liquidity_score': liquidity_score
                    }
                }
                interpretation = interpreter._interpret_orderflow(interpretation_data)
            except Exception as e:
                self.logger.error(f"Error generating orderflow interpretation: {str(e)}")
                # Fallback interpretation
                if final_score > 65:
                    interpretation = f"Strong bullish orderflow (score: {final_score:.1f})"
                elif final_score < 35:
                    interpretation = f"Strong bearish orderflow (score: {final_score:.1f})"
                else:
                    interpretation = f"Neutral orderflow conditions (score: {final_score:.1f})"
            
            # 11. Create signals
            signals = {
                'score': final_score,
                'interpretation': interpretation,
                'divergences': divergences
            }
            
            # 12. Format the final result
            result = self.create_result(
                score=final_score,
                components=adjusted_scores,
                signals=signals,
                metadata={
                    'timestamp': int(time.time() * 1000),
                    'calculation_time': total_time,
                    'component_times_ms': component_times,
                    'status': 'SUCCESS'
                }
            )
            
            # Log performance summary periodically (every 10th calculation)
            if hasattr(self, '_debug_stats') and self._debug_stats['calculation_counts'].get('TOTAL', 0) % 10 == 0:
                self._log_performance_summary()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating orderflow indicators: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Add execution time to error report
            execution_time = time.time() - start_time
            
            # Return default result with error info
            return {
                'score': 50.0,
                'components': {comp: 50.0 for comp in self.component_weights},
                'signals': {},
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'execution_time': execution_time,
                    'status': 'ERROR',
                    'error': str(e)
                }
            }

    def _get_timeframe_display_name(self, timeframe: str) -> str:
        """Convert timeframe code to display name."""
        if timeframe == 'base':
            return '1 minute'
        elif timeframe == 'ltf':
            return '5 minute'
        elif timeframe == 'mtf':
            return '30 minute'
        elif timeframe == 'htf':
            return '240 minute'
        elif timeframe.isdigit():
            return f"{timeframe} minute"
        else:
            return timeframe

    def _compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Compute weighted score from component scores.
        
        Args:
            scores: Dictionary of component scores
            
        Returns:
            float: Weighted score
        """
        try:
            self.logger.debug("Computing weighted score with component mapping")
            self.logger.debug(f"Input scores: {scores}")
            self.logger.debug(f"Component weights: {self.component_weights}")
            
            # Define component mappings 
            component_mapping = {
                # Score key -> Weight key
                'cvd': 'cvd',
                'imbalance_score': 'imbalance',
                'trade_flow_score': 'trade_flow',
                'open_interest_score': 'open_interest',
                'pressure_score': 'pressure'
            }
            
            weighted_sum = 0
            total_weight = 0
            
            for score_key, score_value in scores.items():
                # Map the score key to the weight key if necessary
                weight_key = component_mapping.get(score_key, score_key)
                
                # Get the weight for this component if it exists
                if weight_key in self.component_weights:
                    weight = self.component_weights[weight_key]
                    
                    # Log the component contribution
                    self.logger.debug(f"Component: {score_key} -> {weight_key}, Score: {score_value:.2f}, Weight: {weight:.2f}")
                    
                    # Add to the weighted sum
                    weighted_sum += score_value * weight
                    total_weight += weight
            
            # Safety check for zero weight
            if total_weight <= 0:
                self.logger.warning(f"Total weight is 0 or negative: {total_weight}. Defaulting to 50.0")
                return 50.0
                
            # Calculate the final weighted score
            final_score = weighted_sum / total_weight
            self.logger.debug(f"Final weighted score: {final_score:.2f} (sum: {weighted_sum:.2f}, weight: {total_weight:.2f})")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error computing weighted score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def log_indicator_results(self, final_score: float, component_scores: Dict[str, float], symbol: str = '') -> None:
        """Log indicator results with divergence adjustments using the enhanced formatter."""
        if self.debug_level >= 1:
            # Get divergence adjustments if available
            divergence_adjustments = getattr(self, '_divergence_adjustments', {})
            
            # Create contributions list
            contributions = []
            for component, score in component_scores.items():
                weight = self.component_weights.get(component, 0)
                contribution = score * weight
                contributions.append((component, score, weight, contribution))
            
            # Sort by contribution (highest first)
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Use enhanced formatter with divergence support
            from src.core.formatting.formatter import LogFormatter
            formatted_section = LogFormatter.format_score_contribution_section(
                title="Orderflow Score Contribution Breakdown",
                contributions=contributions,
                symbol=symbol,
                divergence_adjustments=divergence_adjustments,
                final_score=final_score,
                border_style="single"
            )
            self.logger.info(formatted_section)
            
        if self.debug_level >= 2:
            self._log_performance_summary()

    async def get_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get orderflow-based trading signals."""
        try:
            orderbook = market_data.get('orderbook', {})
            
            signals = {
                'trade_flow': 'buy' if self._calculate_trade_flow(market_data['trades']) > 60 else 'sell',
                'trade_size': 'buy' if self._calculate_trade_size(market_data['trades']) > 60 else 'sell',
                'trade_frequency': 'buy' if self._calculate_trade_frequency(market_data['trades']) > 60 else 'sell',
                'trade_impact': self._detect_trade_impact(orderbook)
            }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error getting orderflow signals: {str(e)}")
            return {}

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data for orderflow analysis."""
        try:
            # First check base requirements
            if not self._validate_base_requirements(data):
                return False
                
            # Orderflow-specific validation
            orderbook = data.get('orderbook', {})
            trades = data.get('trades', [])
            
            # Validate orderbook
            if not orderbook:
                self.logger.error("Missing orderbook data")
                return False
                
            required_fields = ['bids', 'asks']
            missing_fields = [f for f in required_fields if f not in orderbook]
            if missing_fields:
                self.logger.error(f"Missing orderbook fields: {missing_fields}")
                return False
                
            # Validate trades
            if not trades:
                self.logger.error("Missing trades data")
                return False
                
            if len(trades) < self.min_trades:
                self.logger.error(f"Insufficient trade history. Required: {self.min_trades}, Got: {len(trades)}")
                return False
                
            # Validate trade structure
            required_trade_fields = ['id', 'price', 'size', 'side', 'time']
            field_mappings = {
                'id': ['id', 'trade_id', 'execId', 'i'],
                'price': ['price', 'execPrice', 'p'],
                'size': ['size', 'amount', 'execQty', 'v'],
                'side': ['side', 'S', 'direction'],
                'time': ['time', 'timestamp', 'T']
            }
            
            for trade in trades[:1]:  # Check first trade only
                missing_fields = []
                for req_field in required_trade_fields:
                    alternatives = field_mappings.get(req_field, [req_field])
                    if not any(alt in trade for alt in alternatives):
                        missing_fields.append(req_field)
                
                if missing_fields:
                    self.logger.error(f"Missing trade fields: {missing_fields}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error in orderflow data validation: {str(e)}")
            return False

    def _validate_input(self, data: Dict[str, Any]) -> bool:
        """Internal method to validate orderflow data input."""
        try:
            # Check required data components
            required_keys = ['trades', 'orderbook', 'ticker']
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                self.logger.error(f"Missing required data keys: {missing_keys}")
                return False
                
            trades = data.get('trades', [])
            if not isinstance(trades, (list, pd.DataFrame)):
                self.logger.error("Trades must be a list or DataFrame")
                return False
                
            if len(trades) < self.min_trades:
                self.logger.error(f"Insufficient trade data: {len(trades)} < {self.min_trades}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating orderflow data: {str(e)}")
            return False

    def _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in orderflow analysis."""
        try:
            trades = market_data.get('trades', [])
            
            # Check data quality
            if len(trades) < self.min_trades:
                return 0.5
                
            # Check for consistent trade data
            if not all(isinstance(t, dict) and 'price' in t and 'amount' in t for t in trades):
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    async def _calculate_component_scores(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate orderflow-based component scores."""
        try:
            # Use the cache if components are already calculated
            if 'component_scores' in self._cache:
                return self._cache['component_scores']
                
            scores = {}
            
            # Calculate CVD score - use caching internally
            scores['cvd'] = self._calculate_cvd(data)
            
            # Calculate open interest score - use caching internally
            scores['open_interest_score'] = self._calculate_open_interest_score(data)
            
            # Calculate trade flow score - use caching internally
            scores['trade_flow_score'] = self._calculate_trade_flow_score(data)
            
            # Calculate imbalance score - use caching internally
            scores['imbalance_score'] = self._calculate_imbalance_score(data)
            
            # Calculate liquidity score - use caching internally
            scores['liquidity_score'] = self._calculate_liquidity_score(data)
            
            # Store in cache before returning
            self._cache['component_scores'] = scores
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating orderflow scores: {str(e)}")
            return {comp: 50.0 for comp in self.component_weights}

    def _validate_weights(self):
        """Validate component weights and normalize if needed."""
        try:
            # Calculate sum of weights
            weight_sum = sum(self.component_weights.values())
            
            # If weights don't sum to 1.0, normalize them
            if not np.isclose(weight_sum, 1.0, rtol=1e-5):
                # Use safe logging to avoid AttributeError
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Component weights sum to {weight_sum:.4f}, normalizing.")
                
                # Normalize weights
                for component in self.component_weights:
                    self.component_weights[component] /= weight_sum
            
            # Log the final weights
            if hasattr(self, 'logger'):
                self.logger.info("OrderflowIndicators component weights:")
                for component, weight in self.component_weights.items():
                    self.logger.info(f"  - {component}: {weight:.4f}")
                    
            return True
        except Exception as e:
            # Use safe logging to avoid AttributeError
            if hasattr(self, 'logger'):
                self.logger.error(f"Error validating weights: {str(e)}")
            else:
                print(f"Error validating weights: {str(e)}")
                
            # Set default weights
            self.component_weights = {
                'cvd': 0.3,
                'trade_flow_score': 0.2,
                'imbalance_score': 0.2,
                'open_interest_score': 0.1,
                'liquidity_score': 0.2
            }
            return False

    def _cached_compute(self, key: str, compute_func, *args, **kwargs):
        """Compute a value with caching to avoid redundant calculations.
        
        Args:
            key: Cache key for this computation
            compute_func: Function to compute the value
            *args, **kwargs: Arguments to pass to compute_func
            
        Returns:
            The computed value, either from cache or freshly calculated
        """
        if key not in self._cache:
            self._cache[key] = compute_func(*args, **kwargs)
        return self._cache[key]
    
    def _get_processed_trades(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """Get processed trades with caching - process once, use everywhere.
        
        This method consolidates all trade data processing to eliminate redundant operations.
        It extracts trades from various possible locations, standardizes the format,
        and pre-calculates commonly used values.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            pd.DataFrame: Processed trades with standardized columns and pre-calculated values
        """
        cache_key = 'processed_trades_df'
        
        # Return cached if available
        if cache_key in self._cache:
            self._log_cache_hit("TRADES", cache_key)
            return self._cache[cache_key]
        
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("PROCESSING TRADES DATA (CENTRALIZED)")
        self.logger.debug("=" * 50)
        
        try:
            # Extract trades from various possible locations
            trades = None
            source = "unknown"
            
            # Priority order: processed_trades > trades_df > trades
            if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list) and len(market_data['processed_trades']) > 0:
                trades = market_data['processed_trades']
                source = "processed_trades"
                self.logger.debug(f"Using processed_trades list with {len(trades)} items")
            elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame) and not market_data['trades_df'].empty:
                trades = market_data['trades_df']
                source = "trades_df"
                self.logger.debug(f"Using trades_df DataFrame with {len(trades)} rows")
            elif 'trades' in market_data:
                if isinstance(market_data['trades'], list) and len(market_data['trades']) > 0:
                    trades = market_data['trades']
                    source = "trades"
                    self.logger.debug(f"Using trades list with {len(trades)} items")
                elif isinstance(market_data['trades'], pd.DataFrame) and not market_data['trades'].empty:
                    trades = market_data['trades']
                    source = "trades"
                    self.logger.debug(f"Using trades DataFrame with {len(trades)} rows")
            
            if trades is None:
                self.logger.warning("No valid trade data found")
                return pd.DataFrame()
            
            # Convert to DataFrame if needed
            if isinstance(trades, pd.DataFrame):
                df = trades.copy()
                self.logger.debug(f"Using existing DataFrame from {source}")
            else:
                df = pd.DataFrame(trades)
                self.logger.debug(f"Converted {source} list to DataFrame")
            
            if df.empty:
                self.logger.warning("Empty trades DataFrame after conversion")
                return df
            
            self.logger.debug(f"Initial DataFrame: {len(df)} rows, columns: {list(df.columns)}")
            
            # Standardize column names ONCE
            column_mappings = {
                'S': 'side', 's': 'side',
                'v': 'amount', 'size': 'amount', 'volume': 'amount', 'qty': 'amount', 'quantity': 'amount',
                'p': 'price', 'execPrice': 'price',
                'T': 'time', 'timestamp': 'time', 'datetime': 'time',
                'i': 'id', 'trade_id': 'id', 'execId': 'id'
            }
            
            # Apply column mappings
            mapped_columns = []
            for old_col, new_col in column_mappings.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]
                    mapped_columns.append(f"{old_col}->{new_col}")
            
            if mapped_columns:
                self.logger.debug(f"Mapped columns: {', '.join(mapped_columns)}")
            
            # Ensure required columns exist
            required_cols = ['side', 'amount', 'price']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self.logger.error(f"Missing required columns after mapping: {missing_cols}")
                self.logger.error(f"Available columns: {list(df.columns)}")
                return pd.DataFrame()
            
            # Ensure numeric types ONCE with error handling
            try:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                if 'time' in df.columns:
                    df['time'] = pd.to_numeric(df['time'], errors='coerce')
            except Exception as e:
                self.logger.error(f"Error converting columns to numeric: {str(e)}")
                return pd.DataFrame()
            
            # Drop rows with invalid data
            initial_len = len(df)
            df = df.dropna(subset=['amount', 'price'])
            dropped_rows = initial_len - len(df)
            if dropped_rows > 0:
                self.logger.debug(f"Dropped {dropped_rows} rows with invalid amount/price data")
            
            if df.empty:
                self.logger.warning("No valid trades after cleaning numeric data")
                return df
            
            # Normalize sides ONCE using vectorized operations
            df['side'] = df['side'].astype(str).str.lower().str.strip()
            
            # Create boolean masks for buy/sell (more efficient than string comparisons)
            buy_values = {'buy', 'b', 'bid', '1', 'true', 'long'}
            sell_values = {'sell', 's', 'ask', 'offer', '-1', 'false', 'short'}
            
            buy_mask = df['side'].isin(buy_values)
            sell_mask = df['side'].isin(sell_values)
            
            # Add boolean columns for efficient filtering
            df['is_buy'] = buy_mask
            df['is_sell'] = sell_mask
            
            # Handle unknown sides
            unknown_mask = ~(buy_mask | sell_mask)
            unknown_count = unknown_mask.sum()
            
            if unknown_count > 0:
                unknown_pct = (unknown_count / len(df)) * 100
                self.logger.debug(f"Found {unknown_count} trades ({unknown_pct:.1f}%) with unknown sides")
                
                # Log sample of unknown sides for debugging
                unknown_sides = df[unknown_mask]['side'].unique()[:5]
                self.logger.debug(f"Sample unknown sides: {list(unknown_sides)}")
                
                # Randomly assign unknown sides to avoid bias
                random_assignments = np.random.choice([True, False], size=unknown_count)
                df.loc[unknown_mask, 'is_buy'] = random_assignments
                df.loc[unknown_mask, 'is_sell'] = ~random_assignments
                
                self.logger.debug(f"Randomly assigned {unknown_count} unknown sides")
            
            # Pre-calculate commonly used values ONCE
            # Signed volume (positive for buys, negative for sells)
            df['signed_volume'] = df['amount'] * np.where(df['is_buy'], 1, np.where(df['is_sell'], -1, 0))
            
            # Trade value (amount * price)
            df['value'] = df['amount'] * df['price']
            
            # Signed value (positive for buys, negative for sells)
            df['signed_value'] = df['value'] * np.where(df['is_buy'], 1, np.where(df['is_sell'], -1, 0))
            
            # Add size weights for large trade analysis (used in pressure calculations)
            if len(df) >= 10:
                df['size_percentile'] = df['amount'].rank(pct=True)
                df['is_large_trade'] = df['size_percentile'] >= 0.75  # Top 25%
            else:
                df['size_percentile'] = 0.5
                df['is_large_trade'] = False
            
            # Log final statistics
            buy_count = df['is_buy'].sum()
            sell_count = df['is_sell'].sum()
            total_volume = df['amount'].sum()
            buy_volume = df[df['is_buy']]['amount'].sum()
            sell_volume = df[df['is_sell']]['amount'].sum()
            
            processing_time = time.time() - start_time
            
            self.logger.debug(f"Processed trades summary:")
            self.logger.debug(f"- Total trades: {len(df)}")
            self.logger.debug(f"- Buy trades: {buy_count} ({buy_count/len(df)*100:.1f}%)")
            self.logger.debug(f"- Sell trades: {sell_count} ({sell_count/len(df)*100:.1f}%)")
            self.logger.debug(f"- Total volume: {total_volume:.2f}")
            self.logger.debug(f"- Buy volume: {buy_volume:.2f} ({buy_volume/total_volume*100:.1f}%)")
            self.logger.debug(f"- Sell volume: {sell_volume:.2f} ({sell_volume/total_volume*100:.1f}%)")
            self.logger.debug(f"- Processing time: {processing_time:.4f}s")
            self.logger.debug("=" * 50)
            
            # Cache the processed DataFrame
            self._cache[cache_key] = df
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing trades data: {str(e)}")
            self.logger.debug(traceback.format_exc())
            processing_time = time.time() - start_time
            self.logger.debug(f"Trade processing failed after {processing_time:.4f}s")
            return pd.DataFrame()

    def _calculate_cvd(self, market_data: Dict[str, Any]) -> float:
        """Calculate Cumulative Volume Delta (CVD) from trade data.
        
        Args:
            market_data: Market data dictionary containing trades
            
        Returns:
            float: CVD value
        """
        # Use caching to avoid redundant calculations
        cache_key = 'cvd'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING CVD CALCULATION (OPTIMIZED)")
        self.logger.debug("=" * 50)
        
        try:
            # Use the centralized processed trades
            trades_df = self._get_processed_trades(market_data)
            
            if trades_df.empty:
                self.logger.warning("No valid trade data available for CVD calculation")
                return 50.0
            
            # Now just use the pre-calculated signed_volume
            cvd = trades_df['signed_volume'].sum()
            total_volume = trades_df['amount'].sum()
            
            self.logger.debug(f"CVD calculation using processed trades:")
            self.logger.debug(f"- Raw CVD: {cvd:.2f}")
            self.logger.debug(f"- Total volume: {total_volume:.2f}")
            
            # Calculate CVD percentage
            if total_volume > 0:
                cvd_percentage = cvd / total_volume
            else:
                cvd_percentage = 0.0
            
            # Get price direction for CVD-Price divergence analysis
            price_change_pct = self._get_price_direction(market_data)
            
            self.logger.debug(f"CVD: {cvd:.2f}, CVD percentage: {cvd_percentage:.4f}, Price change: {price_change_pct:.3f}%")
            
            # Analyze CVD-Price relationship for divergences
            cvd_score = self._analyze_cvd_price_relationship(cvd, cvd_percentage, price_change_pct)
            
            self.logger.debug(f"Final CVD Score after price relationship analysis: {cvd_score:.2f}")
            
            # Log execution time
            execution_time = time.time() - start_time
            self.logger.debug(f"CVD calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            # Store result in cache
            self._cache[cache_key] = cvd_score
            return cvd_score
            
        except Exception as e:
            self.logger.error(f"Error calculating CVD: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"CVD calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 50.0
            
    def _analyze_cvd_price_relationship(self, cvd: float, cvd_percentage: float, price_change_pct: float) -> float:
        """Analyze CVD-Price relationship to detect divergences and confirmations.
        
        This implements proper CVD analysis considering price direction:
        1. Price Up + CVD Up = Bullish (aggressive buying driving price up)
        2. Price Up + CVD Down = Bearish Divergence (price rising without buying aggression)
        3. Price Down + CVD Down = Bearish (aggressive selling driving price down)
        4. Price Down + CVD Up = Bullish Divergence (aggressive buying despite falling price)
        
        Args:
            cvd: Raw CVD value
            cvd_percentage: CVD as percentage of total volume
            price_change_pct: Price change percentage
            
        Returns:
            float: CVD score (0-100) considering price relationship
        """
        try:
            # Get configuration parameters
            cvd_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('cvd', {})
            price_threshold = cvd_config.get('price_direction_threshold', 0.1)
            cvd_threshold = cvd_config.get('cvd_significance_threshold', 0.01)  # 1% of volume
            
            # Determine if changes are significant
            price_increasing = price_change_pct > price_threshold
            price_decreasing = price_change_pct < -price_threshold
            cvd_increasing = cvd_percentage > cvd_threshold  # Net buying pressure
            cvd_decreasing = cvd_percentage < -cvd_threshold  # Net selling pressure
            
            # Base CVD strength (how strong the buying/selling pressure is)
            cvd_strength = min(abs(cvd_percentage) / 0.1, 1.0)  # Normalize to 0-1, cap at 10% of volume
            
            # Base score from CVD direction
            base_cvd_score = 50 + (np.tanh(cvd_percentage * 3) * 50)
            
            # Apply the four scenarios with divergence detection
            score = base_cvd_score
            interpretation = "Neutral CVD"
            
            if price_increasing and cvd_increasing:
                # Scenario 1: Price Up + CVD Up = BULLISH CONFIRMATION
                # Aggressive buyers driving price up - strong bullish signal
                confirmation_strength = (cvd_strength + min(abs(price_change_pct) / 2.0, 1.0)) / 2
                score = 50 + (confirmation_strength * 50)
                interpretation = "Bullish confirmation (aggressive buying driving price up)"
                self._log_intelligent_debug("CVD", f"Scenario 1: Price↑ + CVD↑ = Bullish confirmation, strength: {confirmation_strength:.3f}", scenario="cvd_bullish_confirmation")
                
            elif price_increasing and cvd_decreasing:
                # Scenario 2: Price Up + CVD Down = BEARISH DIVERGENCE
                # Price rising without buying aggression - potential exhaustion/trap
                divergence_strength = (cvd_strength + min(abs(price_change_pct) / 2.0, 1.0)) / 2
                score = 50 - (divergence_strength * 35)  # Moderately bearish due to divergence
                interpretation = "Bearish divergence (price rising without buying aggression)"
                self._log_intelligent_debug("CVD", f"Scenario 2: Price↑ + CVD↓ = Bearish divergence, strength: {divergence_strength:.3f}", scenario="cvd_bearish_divergence")
                
            elif price_decreasing and cvd_decreasing:
                # Scenario 3: Price Down + CVD Down = BEARISH CONFIRMATION
                # Aggressive sellers in control - strong bearish signal
                confirmation_strength = (cvd_strength + min(abs(price_change_pct) / 2.0, 1.0)) / 2
                score = 50 - (confirmation_strength * 50)
                interpretation = "Bearish confirmation (aggressive selling driving price down)"
                self._log_intelligent_debug("CVD", f"Scenario 3: Price↓ + CVD↓ = Bearish confirmation, strength: {confirmation_strength:.3f}", scenario="cvd_bearish_confirmation")
                
            elif price_decreasing and cvd_increasing:
                # Scenario 4: Price Down + CVD Up = BULLISH DIVERGENCE
                # Aggressive buying despite falling price - potential accumulation/reversal
                divergence_strength = (cvd_strength + min(abs(price_change_pct) / 2.0, 1.0)) / 2
                score = 50 + (divergence_strength * 35)  # Moderately bullish due to divergence
                interpretation = "Bullish divergence (aggressive buying despite falling price)"
                self._log_intelligent_debug("CVD", f"Scenario 4: Price↓ + CVD↑ = Bullish divergence, strength: {divergence_strength:.3f}", scenario="cvd_bullish_divergence")
                
            else:
                # Minimal changes in price or CVD - use base CVD score
                if abs(price_change_pct) < price_threshold and abs(cvd_percentage) < cvd_threshold:
                    interpretation = "Neutral (minimal price and CVD changes)"
                    score = 50.0
                else:
                    # One significant, one not - weight towards the more significant signal
                    if abs(cvd_percentage) > abs(price_change_pct / 100):  # Convert price % to comparable scale
                        # CVD dominates
                        score = base_cvd_score
                        if cvd_percentage > 0:
                            interpretation = "Slightly bullish (CVD positive, price neutral)"
                        else:
                            interpretation = "Slightly bearish (CVD negative, price neutral)"
                    else:
                        # Price dominates, but CVD provides context
                        if price_change_pct > 0:
                            score = 52 + (cvd_strength * 8)  # Slightly bullish with CVD adjustment
                            interpretation = "Slightly bullish (price up, CVD context)"
                        else:
                            score = 48 - (cvd_strength * 8)  # Slightly bearish with CVD adjustment
                            interpretation = "Slightly bearish (price down, CVD context)"
            
            # Ensure score is within bounds
            score = max(0, min(100, score))
            
            self.logger.debug(f"CVD-Price analysis: {interpretation}, score: {score:.2f}")
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error in CVD-Price relationship analysis: {str(e)}")
            # Fallback to simple CVD scoring
            normalized_cvd = np.tanh(cvd_percentage * 3)
            return 50 + (normalized_cvd * 50)

    def _calculate_base_cvd_score(self, cvd_value):
        """
        Calculate a score based on the Cumulative Volume Delta (CVD) value.
        
        Args:
            cvd_value (float): The calculated CVD value
            
        Returns:
            float: Score between 0-100
        """
        try:
            # Simple normalization based on the magnitude of the CVD
            # Positive CVD indicates buying pressure (bullish)
            # Negative CVD indicates selling pressure (bearish)
            
            # Normalize to -1 to 1 range based on typical CVD values
            # May need adjustment for different markets/timeframes
            normalized_cvd = np.tanh(cvd_value / 1000)  # Adjust divisor based on typical values
            
            # Convert to 0-100 score
            score = 50 + (normalized_cvd * 50)
            
            self.logger.debug(f"Base CVD: {cvd_value:.4f}, Normalized: {normalized_cvd:.4f}, Score: {score:.2f}")
            
            return float(np.clip(score, 0, 100))
        except Exception as e:
            self.logger.error(f"Error calculating base CVD score: {str(e)}")
            return 50.0
            
    def _calculate_trade_flow_score(self, market_data):
        """Calculate trade flow score based on buy vs sell volume.
        
        Args:
            market_data: Market data dictionary or trade DataFrame
            
        Returns:
            float: Trade flow score (0-100)
        """
        # Use caching to avoid redundant calculations
        cache_key = 'trade_flow_score'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Try different possible locations for trade data
            trades = None
            
            # First check for processed_trades
            if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list):
                trades = market_data['processed_trades']
                self.logger.debug("Using processed_trades for trade flow calculation")
            
            # Fall back to regular trades if no processed trades
            elif 'trades' in market_data:
                if isinstance(market_data['trades'], list):
                    trades = market_data['trades']
                    self.logger.debug("Using trades list for trade flow calculation")
                elif isinstance(market_data['trades'], pd.DataFrame):
                    trades = market_data['trades']
                    self.logger.debug("Using trades DataFrame for trade flow calculation")
            
            # Check for trades_df as another option
            elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
                trades = market_data['trades_df']
                self.logger.debug("Using trades_df for trade flow calculation")
            
            # If no valid trades data found
            if not trades or (isinstance(trades, list) and len(trades) < 10):
                self.logger.warning("Insufficient trade data for trade flow calculation")
                return 50.0  # Neutral score
                
            # Calculate trade flow
            try:
                # Handle different types properly
                if isinstance(trades, pd.DataFrame):
                    flow = self._calculate_trade_flow(trades)
                elif isinstance(trades, list):
                    if not trades:
                        return 50.0
                    try:
                        trade_df = pd.DataFrame(trades)
                        flow = self._calculate_trade_flow(trade_df)
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list to DataFrame: {str(e)}")
                        return 50.0
                else:
                    self.logger.error(f"Unsupported trade data type: {type(trades)}")
                    return 50.0
                
                # Map flow to score (-1 to 1 -> 0 to 100)
                score = 50 + (flow * 50)
                
                # Ensure score is within bounds
                return max(0, min(100, score))
            except Exception as e:
                self.logger.error(f"Error in trade flow calculation: {str(e)}")
                return 50.0
        except Exception as e:
            self.logger.error(f"Error calculating trade flow score: {str(e)}")
            return 50.0  # Neutral score
            
        # Store in cache before returning
        self._cache['trade_flow_score'] = score
        return score



    def _calculate_trades_imbalance_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate trades-based imbalance score using temporal trade flow analysis.
        
        This method analyzes trade imbalances over multiple time windows to detect
        sustained buying or selling pressure, which is different from orderbook
        snapshot imbalance. It focuses on executed trades rather than resting orders.
        
        Args:
            market_data: Dictionary containing market data with trades
            
        Returns:
            float: Imbalance score (0-100) where:
                  0-25: Strong sell-side imbalance
                  25-45: Moderate sell-side imbalance  
                  45-55: Balanced trade flow
                  55-75: Moderate buy-side imbalance
                  75-100: Strong buy-side imbalance
        """
        # Use caching to avoid redundant calculations
        cache_key = 'trades_imbalance_score'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            # Use the centralized processed trades
            trades_df = self._get_processed_trades(market_data)
            
            if trades_df.empty or len(trades_df) < 30:
                self.logger.warning("Insufficient trade data for trades imbalance calculation")
                return 50.0  # Neutral score
                
            # Calculate multiple imbalance metrics over different time windows
            # Use the pre-calculated is_buy and is_sell boolean columns from processed trades
            
            # 1. Recent imbalance (last 25% of trades) - 40% weight
            recent_count = max(1, len(trades_df) // 4)
            recent_trades = trades_df.tail(recent_count)
            
            recent_buy_vol = recent_trades[recent_trades['is_buy']]['amount'].sum()
            recent_sell_vol = recent_trades[recent_trades['is_sell']]['amount'].sum()
            recent_total = recent_buy_vol + recent_sell_vol
            
            if recent_total > 0:
                recent_imbalance = (recent_buy_vol - recent_sell_vol) / recent_total
            else:
                recent_imbalance = 0.0
                
            # 2. Medium-term imbalance (last 50% of trades) - 35% weight
            medium_count = max(1, len(trades_df) // 2)
            medium_trades = trades_df.tail(medium_count)
            
            medium_buy_vol = medium_trades[medium_trades['is_buy']]['amount'].sum()
            medium_sell_vol = medium_trades[medium_trades['is_sell']]['amount'].sum()
            medium_total = medium_buy_vol + medium_sell_vol
            
            if medium_total > 0:
                medium_imbalance = (medium_buy_vol - medium_sell_vol) / medium_total
            else:
                medium_imbalance = 0.0
                
            # 3. Overall imbalance (all trades) - 25% weight
            overall_buy_vol = trades_df[trades_df['is_buy']]['amount'].sum()
            overall_sell_vol = trades_df[trades_df['is_sell']]['amount'].sum()
            overall_total = overall_buy_vol + overall_sell_vol
            
            if overall_total > 0:
                overall_imbalance = (overall_buy_vol - overall_sell_vol) / overall_total
            else:
                overall_imbalance = 0.0
                
            # 4. Trade frequency imbalance - analyze trade count patterns
            buy_count = trades_df['is_buy'].sum()
            sell_count = trades_df['is_sell'].sum()
            total_count = buy_count + sell_count
            
            if total_count > 0:
                frequency_imbalance = (buy_count - sell_count) / total_count
            else:
                frequency_imbalance = 0.0
                
            # 5. Size-weighted imbalance - larger trades get more weight
            if len(trades_df) >= 10:  # Need sufficient data for percentiles
                # Use the pre-calculated is_large_trade column if available, otherwise calculate
                if 'is_large_trade' not in trades_df.columns:
                    trades_df['size_weight'] = 1.0  # Default weight
                    size_75th = trades_df['amount'].quantile(0.75)
                    size_90th = trades_df['amount'].quantile(0.90)
                    trades_df.loc[trades_df['amount'] >= size_90th, 'size_weight'] = 3.0  # Top 10%
                    trades_df.loc[(trades_df['amount'] >= size_75th) & (trades_df['amount'] < size_90th), 'size_weight'] = 2.0  # 75-90%
                else:
                    # Use the pre-calculated large trade indicator
                    trades_df['size_weight'] = np.where(trades_df['is_large_trade'], 2.0, 1.0)
                
                # Calculate weighted volumes using boolean masks
                buy_mask = trades_df['is_buy']
                sell_mask = trades_df['is_sell']
                
                weighted_buy_vol = (trades_df[buy_mask]['amount'] * trades_df[buy_mask]['size_weight']).sum()
                weighted_sell_vol = (trades_df[sell_mask]['amount'] * trades_df[sell_mask]['size_weight']).sum()
                weighted_total = weighted_buy_vol + weighted_sell_vol
                
                if weighted_total > 0:
                    size_weighted_imbalance = (weighted_buy_vol - weighted_sell_vol) / weighted_total
                else:
                    size_weighted_imbalance = 0.0
            else:
                size_weighted_imbalance = overall_imbalance  # Fallback to overall
                
            # Combine all imbalance metrics with time-decay weighting (recent = more important)
            combined_imbalance = (
                recent_imbalance * 0.40 +      # Most recent trades
                medium_imbalance * 0.35 +      # Medium-term trend  
                overall_imbalance * 0.15 +     # Overall context
                size_weighted_imbalance * 0.10 # Large trade bias
            )
            
            # Convert to 0-100 score
            # -1 (all selling) = 0 score
            # 0 (balanced) = 50 score  
            # 1 (all buying) = 100 score
            imbalance_score = 50 + (combined_imbalance * 50)
            
            # Ensure within bounds
            imbalance_score = max(0, min(100, imbalance_score))
            
            # Log detailed breakdown
            self.logger.debug(f"Trades imbalance breakdown:")
            self.logger.debug(f"- Recent imbalance ({recent_count} trades): {recent_imbalance:.4f}")
            self.logger.debug(f"- Medium imbalance ({medium_count} trades): {medium_imbalance:.4f}")
            self.logger.debug(f"- Overall imbalance ({len(trades_df)} trades): {overall_imbalance:.4f}")
            self.logger.debug(f"- Size-weighted imbalance: {size_weighted_imbalance:.4f}")
            self.logger.debug(f"- Frequency imbalance: {frequency_imbalance:.4f} (buy: {buy_count}, sell: {sell_count})")
            self.logger.debug(f"- Combined imbalance: {combined_imbalance:.4f}")
            self.logger.debug(f"- Final imbalance score: {imbalance_score:.2f}")
            
            # Store in cache before returning
            self._cache[cache_key] = imbalance_score
            return imbalance_score
            
        except Exception as e:
            self.logger.error(f"Error calculating trades imbalance score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0  # Neutral score on error

    def _get_open_interest_values(self, market_data):
        """
        Get the current and previous open interest values.
        
        Args:
            market_data (dict): Dictionary containing market data with open interest data
            
        Returns:
            dict: Dictionary containing 'current' and 'previous' open interest values,
                  or None if data not available
        """
        try:
            # Check if we have open interest data at the top level
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                
                # Handle different formats of open interest data
                if isinstance(oi_data, dict):
                    # If we have a dictionary with current and previous values
                    if 'current' in oi_data and 'previous' in oi_data:
                        return oi_data  # Return the entire dictionary as is
                    # If we have a dictionary with just current value
                    elif 'current' in oi_data:
                        return {'current': float(oi_data['current']), 'previous': float(oi_data['current']) * 0.98}
                # If we have a simple numeric value
                elif isinstance(oi_data, (int, float)):
                    return {'current': float(oi_data), 'previous': float(oi_data) * 0.98}
            
            # Fallback: check if we have it under sentiment for backward compatibility
            if 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                
                # Handle different formats of open interest data
                if isinstance(oi_data, dict):
                    # If we have a dictionary with current and previous values
                    if 'current' in oi_data and 'previous' in oi_data:
                        return oi_data  # Return the entire dictionary as is
                    # If we have a dictionary with just current value
                    elif 'current' in oi_data:
                        return {'current': float(oi_data['current']), 'previous': float(oi_data['current']) * 0.98}
                # If we have a simple numeric value
                elif isinstance(oi_data, (int, float)):
                    return {'current': float(oi_data), 'previous': float(oi_data) * 0.98}
            
            # Last resort: try to get it from ticker data directly
            if 'ticker' in market_data and isinstance(market_data['ticker'], dict):
                ticker = market_data['ticker']
                current_oi = float(ticker.get('openInterest', 0))
                # We don't have previous value in this case
                return {'current': current_oi, 'previous': current_oi * 0.98}
                
            # If all else fails, return None
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting open interest values: {e}")
            return None

    def _calculate_open_interest_score(self, market_data):
        """Calculate open interest score based on OI changes AND price direction.
        
        This implements proper open interest analysis:
        1. Increasing OI + Price Up = Bullish (new money supporting uptrend)
        2. Decreasing OI + Price Up = Bearish (short covering, weak rally)
        3. Increasing OI + Price Down = Bearish (new shorts entering)
        4. Decreasing OI + Price Down = Bullish (shorts closing, selling pressure waning)
        
        Args:
            market_data: Dictionary containing open interest and price data
            
        Returns:
            float: Open interest score (0-100)
        """
        # Create a cache key that includes the actual data values to avoid incorrect caching
        oi_data = self._get_open_interest_values(market_data)
        price_change = self._get_price_direction(market_data)
        cache_key = f'open_interest_score_{oi_data}_{price_change:.6f}'
        if cache_key in self._cache:
            cached_score = self._cache[cache_key]
            self._log_cache_hit("OI", cache_key)
            return cached_score
            
        try:
            # Get open interest values
            oi_data = self._get_open_interest_values(market_data)
            
            # Check if we have valid open interest data
            if not oi_data or 'current' not in oi_data or 'previous' not in oi_data:
                self.logger.warning("Missing or invalid open interest data")
                return 50.0  # Return neutral score when data is missing
                
            current_oi = oi_data['current']
            previous_oi = oi_data['previous']
            
            # Calculate OI percentage change
            if previous_oi == 0 or previous_oi is None:
                oi_change_pct = 0
            else:
                oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100
            
            # Get price direction from OHLCV data
            price_change_pct = self._get_price_direction(market_data)
            
            self._log_intelligent_debug("OI", f"Open interest change: {oi_change_pct:.2f}%, Price change: {price_change_pct:.2f}%")
            
            # Get configuration parameters
            oi_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('open_interest', {})
            normalization_threshold = oi_config.get('normalization_threshold', 5.0)
            minimal_change_threshold = oi_config.get('minimal_change_threshold', 0.5)
            price_direction_threshold = oi_config.get('price_direction_threshold', 0.1)
            
            # Determine if changes are significant
            oi_increasing = oi_change_pct > minimal_change_threshold
            oi_decreasing = oi_change_pct < -minimal_change_threshold
            price_increasing = price_change_pct > price_direction_threshold
            price_decreasing = price_change_pct < -price_direction_threshold
            
            # Apply the four scenarios
            score = 50.0  # Default neutral
            interpretation = "Neutral"
            
            if oi_increasing and price_increasing:
                # Scenario 1: Increasing OI + Price Up = BULLISH
                # New money flowing in to support uptrend
                oi_strength = min(abs(oi_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                price_strength = min(abs(price_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                combined_strength = (oi_strength + price_strength) / 2
                score = 50 + (combined_strength * 50)
                interpretation = "Bullish (new money supporting uptrend)"
                self._log_intelligent_debug("OI", f"Scenario 1: OI↑ + Price↑ = Bullish, strength: {combined_strength:.3f}", scenario="oi_scenario_1")
                
            elif oi_decreasing and price_increasing:
                # Scenario 2: Decreasing OI + Price Up = BEARISH
                # Short covering or weak rally with position closure
                oi_strength = min(abs(oi_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                price_strength = min(abs(price_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                combined_strength = (oi_strength + price_strength) / 2
                score = 50 - (combined_strength * 30)  # Moderately bearish
                interpretation = "Bearish (short covering, weak rally)"
                self._log_intelligent_debug("OI", f"Scenario 2: OI↓ + Price↑ = Bearish, strength: {combined_strength:.3f}", scenario="oi_scenario_2")
                
            elif oi_increasing and price_decreasing:
                # Scenario 3: Increasing OI + Price Down = BEARISH
                # New shorts entering to support downtrend
                oi_strength = min(abs(oi_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                price_strength = min(abs(price_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                combined_strength = (oi_strength + price_strength) / 2
                score = 50 - (combined_strength * 50)
                interpretation = "Bearish (new shorts entering downtrend)"
                self._log_intelligent_debug("OI", f"Scenario 3: OI↑ + Price↓ = Bearish, strength: {combined_strength:.3f}", scenario="oi_scenario_3")
                
            elif oi_decreasing and price_decreasing:
                # Scenario 4: Decreasing OI + Price Down = BULLISH
                # Shorts closing, selling pressure waning
                oi_strength = min(abs(oi_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                price_strength = min(abs(price_change_pct) / 0.1, 1.0)  # More sensitive: 0.1% = full strength
                combined_strength = (oi_strength + price_strength) / 2
                score = 50 + (combined_strength * 30)  # Moderately bullish
                interpretation = "Bullish (shorts closing, selling pressure waning)"
                self._log_intelligent_debug("OI", f"Scenario 4: OI↓ + Price↓ = Bullish, strength: {combined_strength:.3f}", scenario="oi_scenario_4")
                
            else:
                # Minimal changes in both OI and price
                if abs(oi_change_pct) < minimal_change_threshold and abs(price_change_pct) < price_direction_threshold:
                    interpretation = "Neutral (minimal OI and price changes)"
                    self._log_intelligent_debug("OI", f"Minimal changes detected", scenario="oi_neutral")
                else:
                    # One significant, one not - use weighted approach
                    if abs(oi_change_pct) > abs(price_change_pct):
                        # OI change dominates
                        if oi_change_pct > 0:
                            score = 55  # Slightly bullish
                            interpretation = "Slightly bullish (OI increase, price neutral)"
                        else:
                            score = 45  # Slightly bearish
                            interpretation = "Slightly bearish (OI decrease, price neutral)"
                    else:
                        # Price change dominates
                        if price_change_pct > 0:
                            score = 52  # Slightly bullish
                            interpretation = "Slightly bullish (price up, OI neutral)"
                        else:
                            score = 48  # Slightly bearish
                            interpretation = "Slightly bearish (price down, OI neutral)"
            
            # Ensure score is within bounds
            score = max(0, min(100, score))
            
            self._log_intelligent_debug("OI", f"Open interest analysis: {interpretation}, score: {score:.2f}", level="INFO")
            
            # Store in cache before returning
            self._cache[cache_key] = score
            return score
            
        except Exception as e:
            self.logger.error(f"Error calculating open interest score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _get_price_direction(self, market_data: Dict[str, Any]) -> float:
        """Get price direction percentage change from OHLCV data.
        
        Args:
            market_data: Dictionary containing market data with OHLCV
            
        Returns:
            float: Price change percentage (positive = up, negative = down)
        """
        try:
            # Try to get OHLCV data
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                self.logger.debug("No OHLCV data available for price direction")
                return 0.0
            
            # Try different timeframes, prioritizing shorter ones for recent price action
            for tf in ['base', 'ltf', '1', '5', 'mtf']:
                if tf in ohlcv_data:
                    df = None
                    
                    # Handle different data structures
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        df = ohlcv_data[tf]
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf]:
                        if isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                            df = ohlcv_data[tf]['data']
                    
                    if df is not None and len(df) >= 2:
                        # Calculate price change from previous close to current close
                        current_close = df['close'].iloc[-1]
                        previous_close = df['close'].iloc[-2]
                        
                        if previous_close != 0:
                            price_change_pct = ((current_close - previous_close) / previous_close) * 100
                            self.logger.debug(f"Price direction from {tf}: {price_change_pct:.3f}% (current: {current_close:.2f}, previous: {previous_close:.2f})")
                            return price_change_pct
            
            # Fallback: try to get from ticker data
            if 'ticker' in market_data and isinstance(market_data['ticker'], dict):
                ticker = market_data['ticker']
                if 'percentage' in ticker:
                    price_change_pct = float(ticker['percentage'])
                    self.logger.debug(f"Price direction from ticker: {price_change_pct:.3f}%")
                    return price_change_pct
                elif 'last' in ticker and 'open' in ticker:
                    last_price = float(ticker['last'])
                    open_price = float(ticker['open'])
                    if open_price != 0:
                        price_change_pct = ((last_price - open_price) / open_price) * 100
                        self.logger.debug(f"Price direction calculated from ticker: {price_change_pct:.3f}%")
                        return price_change_pct
            
            self.logger.debug("Could not determine price direction, returning 0.0")
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error getting price direction: {str(e)}")
            return 0.0

    def _get_open_interest_change(self, market_data):
        """
        Calculate the open interest change percentage from market data.
        
        Args:
            market_data (dict): Dictionary containing market data with sentiment data
            
        Returns:
            float: Open interest change percentage or 0.0 if data not available
        """
        try:
            # Get current and previous values using the helper method
            current, previous = self._get_open_interest_values(market_data)
            
            # Calculate percentage change
            if previous == 0:
                return 0.0
            
            change_pct = ((current - previous) / previous) * 100
            self.logger.debug(f"Open interest change: {change_pct:.2f}% (Current: {current}, Previous: {previous})")
            return change_pct
            
        except Exception as e:
            self.logger.error(f"Error calculating open interest change: {e}")
            return 0.0

    def _get_trade_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        Get the buy and sell pressure values.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Tuple[float, float]: Buy pressure and sell pressure
        """
        try:
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < 10:
                return 1.0, 1.0  # Neutral values
                
            # Convert to DataFrame if not already
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Check if required columns exist
            required_cols = ['side', 'amount', 'price']
            if not all(col in trades_df.columns for col in required_cols):
                # Try alternative column names
                alt_cols = {'side': 'S', 'amount': 'v', 'price': 'p'}
                for req_col, alt_col in alt_cols.items():
                    if req_col not in trades_df.columns and alt_col in trades_df.columns:
                        trades_df[req_col] = trades_df[alt_col]
                
                # Check again after attempting to use alternative columns
                if not all(col in trades_df.columns for col in required_cols):
                    return 1.0, 1.0  # Neutral values
            
            # Calculate buy pressure (sum of buy volume * price)
            buy_df = trades_df[trades_df['side'] == 'buy']
            buy_pressure = (buy_df['amount'] * buy_df['price']).sum() if not buy_df.empty else 0
            
            # Calculate sell pressure (sum of sell volume * price)
            sell_df = trades_df[trades_df['side'] == 'sell']
            sell_pressure = (sell_df['amount'] * sell_df['price']).sum() if not sell_df.empty else 0
            
            # Normalize to reasonable values
            buy_pressure = buy_pressure / 1000000 if buy_pressure > 0 else 0.001
            sell_pressure = sell_pressure / 1000000 if sell_pressure > 0 else 0.001
            
            return buy_pressure, sell_pressure
        except Exception as e:
            self.logger.error(f"Error calculating trade pressure: {str(e)}")
            return 1.0, 1.0  # Neutral values

    def _calculate_trades_pressure_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate trades-based pressure score using trade aggression and volume analysis.
        
        This method analyzes recent trade data to determine buying vs selling pressure
        by examining trade aggression, volume-weighted pressure, and trade size distribution.
        
        Args:
            market_data: Dictionary containing market data with trades
            
        Returns:
            float: Pressure score (0-100) where:
                  0-25: Strong selling pressure
                  25-45: Moderate selling pressure  
                  45-55: Neutral pressure
                  55-75: Moderate buying pressure
                  75-100: Strong buying pressure
        """
        # Use caching to avoid redundant calculations
        cache_key = 'trades_pressure_score'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            # Extract trade data from different possible sources
            trades = None
            
            # First check for processed_trades
            if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list):
                trades = market_data['processed_trades']
                self.logger.debug("Using processed_trades for pressure calculation")
            
            # Fall back to regular trades
            elif 'trades' in market_data:
                if isinstance(market_data['trades'], list):
                    trades = market_data['trades']
                    self.logger.debug("Using trades list for pressure calculation")
                elif isinstance(market_data['trades'], pd.DataFrame):
                    trades = market_data['trades']
                    self.logger.debug("Using trades DataFrame for pressure calculation")
            
            # Check for trades_df as another option
            elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
                trades = market_data['trades_df']
                self.logger.debug("Using trades_df for pressure calculation")
            
            # If no valid trades data found
            if not trades or (isinstance(trades, list) and len(trades) < 20):
                self.logger.warning("Insufficient trade data for trades pressure calculation")
                return 50.0  # Neutral score
                
            # Convert to DataFrame if needed
            if isinstance(trades, list):
                try:
                    trades_df = pd.DataFrame(trades)
                except Exception as e:
                    self.logger.error(f"Failed to convert trades to DataFrame: {str(e)}")
                    return 50.0
            else:
                trades_df = trades.copy()
                
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity'],
                'price': ['price', 'p', 'execPrice'],
                'time': ['time', 'timestamp', 'T', 'datetime']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in trades_df.columns:
                    for col in possible_cols:
                        if col in trades_df.columns:
                            trades_df[std_col] = trades_df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}' for pressure calculation")
                            break
            
            # Check if we have the required columns after mapping
            required_cols = ['side', 'amount', 'price']
            missing_cols = [col for col in required_cols if col not in trades_df.columns]
            if missing_cols:
                self.logger.warning(f"Missing required columns for trades pressure: {missing_cols}")
                return 50.0
                
            # Ensure numeric columns
            try:
                trades_df['amount'] = pd.to_numeric(trades_df['amount'], errors='coerce')
                trades_df['price'] = pd.to_numeric(trades_df['price'], errors='coerce')
                
                # Drop rows with invalid data
                trades_df = trades_df.dropna(subset=['amount', 'price'])
                
                if trades_df.empty:
                    self.logger.warning("No valid trades after cleaning data")
                    return 50.0
                    
            except Exception as e:
                self.logger.error(f"Error converting trade data to numeric: {str(e)}")
                return 50.0
                
            # Normalize side values
            trades_df['side'] = trades_df['side'].astype(str).str.lower()
            
            # Map different side values to buy/sell
            buy_values = ['buy', 'b', 'bid', '1', 'true', 'long']
            sell_values = ['sell', 's', 'ask', 'offer', '-1', 'false', 'short']
            
            # Create normalized side column
            trades_df['norm_side'] = 'unknown'
            trades_df.loc[trades_df['side'].isin(buy_values), 'norm_side'] = 'buy'
            trades_df.loc[trades_df['side'].isin(sell_values), 'norm_side'] = 'sell'
            
            # Handle unknown sides by random assignment to avoid bias
            unknown_count = (trades_df['norm_side'] == 'unknown').sum()
            if unknown_count > 0:
                self.logger.debug(f"Randomly assigning {unknown_count} unknown trade sides")
                unknown_mask = trades_df['norm_side'] == 'unknown'
                random_sides = np.random.choice(['buy', 'sell'], size=unknown_count)
                trades_df.loc[unknown_mask, 'norm_side'] = random_sides
                
            # Calculate multiple pressure metrics
            
            # 1. Volume-weighted pressure (40% weight)
            buy_volume = trades_df[trades_df['norm_side'] == 'buy']['amount'].sum()
            sell_volume = trades_df[trades_df['norm_side'] == 'sell']['amount'].sum()
            total_volume = buy_volume + sell_volume
            
            if total_volume > 0:
                volume_pressure = (buy_volume - sell_volume) / total_volume
            else:
                volume_pressure = 0.0
                
            # 2. Value-weighted pressure (30% weight) 
            buy_value = (trades_df[trades_df['norm_side'] == 'buy']['amount'] * 
                        trades_df[trades_df['norm_side'] == 'buy']['price']).sum()
            sell_value = (trades_df[trades_df['norm_side'] == 'sell']['amount'] * 
                         trades_df[trades_df['norm_side'] == 'sell']['price']).sum()
            total_value = buy_value + sell_value
            
            if total_value > 0:
                value_pressure = (buy_value - sell_value) / total_value
            else:
                value_pressure = 0.0
                
            # 3. Trade count pressure (20% weight)
            buy_count = len(trades_df[trades_df['norm_side'] == 'buy'])
            sell_count = len(trades_df[trades_df['norm_side'] == 'sell'])
            total_count = buy_count + sell_count
            
            if total_count > 0:
                count_pressure = (buy_count - sell_count) / total_count
            else:
                count_pressure = 0.0
                
            # 4. Large trade bias (10% weight) - analyze if large trades are more buy or sell
            # Define large trades as those above 75th percentile
            if len(trades_df) >= 4:  # Need at least 4 trades for percentile
                large_threshold = trades_df['amount'].quantile(0.75)
                large_trades = trades_df[trades_df['amount'] >= large_threshold]
                
                if not large_trades.empty:
                    large_buy_volume = large_trades[large_trades['norm_side'] == 'buy']['amount'].sum()
                    large_sell_volume = large_trades[large_trades['norm_side'] == 'sell']['amount'].sum()
                    large_total_volume = large_buy_volume + large_sell_volume
                    
                    if large_total_volume > 0:
                        large_trade_pressure = (large_buy_volume - large_sell_volume) / large_total_volume
                    else:
                        large_trade_pressure = 0.0
                else:
                    large_trade_pressure = 0.0
            else:
                large_trade_pressure = 0.0
                
            # Combine all pressure metrics with weights
            combined_pressure = (
                volume_pressure * 0.4 +
                value_pressure * 0.3 +
                count_pressure * 0.2 +
                large_trade_pressure * 0.1
            )
            
            # Convert to 0-100 score
            # -1 (all selling) = 0 score
            # 0 (balanced) = 50 score  
            # 1 (all buying) = 100 score
            pressure_score = 50 + (combined_pressure * 50)
            
            # Ensure within bounds
            pressure_score = max(0, min(100, pressure_score))
            
            # Log detailed breakdown
            self.logger.debug(f"Trades pressure breakdown:")
            self.logger.debug(f"- Volume pressure: {volume_pressure:.4f} (buy: {buy_volume:.2f}, sell: {sell_volume:.2f})")
            self.logger.debug(f"- Value pressure: {value_pressure:.4f} (buy: {buy_value:.2f}, sell: {sell_value:.2f})")
            self.logger.debug(f"- Count pressure: {count_pressure:.4f} (buy: {buy_count}, sell: {sell_count})")
            self.logger.debug(f"- Large trade pressure: {large_trade_pressure:.4f}")
            self.logger.debug(f"- Combined pressure: {combined_pressure:.4f}")
            self.logger.debug(f"- Final pressure score: {pressure_score:.2f}")
            
            # Store in cache before returning
            self._cache[cache_key] = pressure_score
            return pressure_score
            
        except Exception as e:
            self.logger.error(f"Error calculating trades pressure score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0  # Neutral score on error

    def _calculate_liquidity_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate liquidity score based on trade frequency and volume.
        
        This method calculates a trade-based liquidity score that is distinct from the
        orderbook-based liquidity measure. While orderbook liquidity looks at available
        orders and depth, this score focuses on actual trade execution frequency and volume
        to measure realized market liquidity.
        
        The score is calculated using two components:
        1. Trade Frequency: How many trades occur per second
        2. Trade Volume: Total volume traded in the measurement window
        
        Both components are normalized and weighted according to configuration parameters.
        
        Args:
            market_data: Dictionary containing market data with trades, or a direct trades list/DataFrame
            
        Returns:
            float: Liquidity score between 0-100, where:
                  0-25: Low liquidity
                  25-75: Normal liquidity
                  75-100: High liquidity
        """
        
        # Use caching to avoid redundant calculations
        cache_key = 'liquidity_score'
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Get configuration parameters from config
            liquidity_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('parameters', {}).get('liquidity', {})
            
            # Extract parameters with defaults if not found in config
            window_minutes = liquidity_config.get('window_minutes', 5)
            max_trades_per_sec = liquidity_config.get('max_trades_per_sec', 5)
            max_volume = liquidity_config.get('max_volume', 1000)
            frequency_weight = liquidity_config.get('frequency_weight', 0.5)
            volume_weight = liquidity_config.get('volume_weight', 0.5)

            # Validate parameters
            if window_minutes <= 0:
                self.logger.warning(f"Invalid window_minutes: {window_minutes}, using default of 5")
                window_minutes = 5
            if max_trades_per_sec <= 0:
                self.logger.warning(f"Invalid max_trades_per_sec: {max_trades_per_sec}, using default of 5")
                max_trades_per_sec = 5
            if max_volume <= 0:
                self.logger.warning(f"Invalid max_volume: {max_volume}, using default of 1000")
                max_volume = 1000
                
            # Validate and normalize weights
            total_weight = frequency_weight + volume_weight
            if total_weight != 1.0:
                self.logger.warning(f"Liquidity weights don't sum to 1.0 ({total_weight}), normalizing")
                frequency_weight /= total_weight
                volume_weight /= total_weight

            # Extract trade data - handle different possible input types
            trades = None
            
            # If market_data is a dictionary
            if isinstance(market_data, dict):
                # First check for processed_trades (highest priority)
                if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list):
                    trades = market_data['processed_trades']
                    self.logger.debug("Using processed_trades for liquidity calculation")
                
                # Fall back to trades_df
                elif 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
                    trades_df = market_data['trades_df']
                    self.logger.debug(f"Using trades_df directly, shape: {trades_df.shape}, columns: {list(trades_df.columns)}")
                
                # Fall back to regular trades
                elif 'trades' in market_data:
                    trades = market_data['trades']
                    self.logger.debug(f"Using trades from market_data: {len(trades)} items")
            
            # If market_data is directly a list of trades
            elif isinstance(market_data, list):
                trades = market_data
                self.logger.debug(f"Using direct trades list: {len(trades)} items")
            
            # If market_data is directly a DataFrame
            elif isinstance(market_data, pd.DataFrame):
                trades_df = market_data
                self.logger.debug(f"Using direct DataFrame: {trades_df.shape}, columns: {list(trades_df.columns)}")
            
            # Check if we have valid trade data
            if trades is None and not 'trades_df' in locals():
                self.logger.warning("No valid trade data found for liquidity calculation")
                return 50.0  # Neutral score when data is missing
                
            # If we have trades list, convert to DataFrame
            if trades is not None:
                if not trades or len(trades) < 10:
                    self.logger.warning("Insufficient trade data for liquidity score calculation (< 10 trades)")
                    return 50.0  # Neutral score when data is missing
                
                # Convert trades to DataFrame
                trades_df = pd.DataFrame(trades)
                
                # Ensure required columns exist
                if 'time' not in trades_df.columns:
                    # Try different column names for time
                    time_column_variants = ['timestamp', 'time', 'datetime']
                    for col in time_column_variants:
                        if col in trades_df.columns:
                            trades_df['time'] = trades_df[col]
                            self.logger.debug(f"Mapped '{col}' to 'time' column")
                            break
                
                if 'size' not in trades_df.columns:
                    # Try different column names for size
                    size_column_variants = ['amount', 'volume', 'quantity', 'size']
                    for col in size_column_variants:
                        if col in trades_df.columns:
                            trades_df['size'] = trades_df[col]
                            self.logger.debug(f"Mapped '{col}' to 'size' column")
                            break
            
            # Final check for required columns
            if 'time' not in trades_df.columns or 'size' not in trades_df.columns:
                self.logger.warning("Missing required trade data columns for liquidity calculation")
                return 50.0

            # Ensure numeric conversion of size column (it may come as strings)
            try:
                trades_df['size'] = pd.to_numeric(trades_df['size'])
            except Exception as e:
                self.logger.warning(f"Error converting 'size' to numeric: {str(e)}")
                # Try fallback method using apply
                try:
                    trades_df['size'] = trades_df['size'].apply(lambda x: float(x) if isinstance(x, str) else x)
                except Exception as e:
                    self.logger.error(f"Failed to convert trade sizes to numeric values: {str(e)}")
                    return 50.0  # Return neutral score if conversion fails

            # Convert time column to datetime with appropriate error handling
            try:
                # If time is already numeric, use unit='ms'
                if pd.api.types.is_numeric_dtype(trades_df['time']):
                    trades_df['time'] = pd.to_datetime(trades_df['time'], unit='ms')
                # If time is string, first convert to numeric then to datetime
                else:
                    trades_df['time'] = pd.to_numeric(trades_df['time'])
                    trades_df['time'] = pd.to_datetime(trades_df['time'], unit='ms')
            except Exception as e:
                self.logger.error(f"Error converting time to datetime: {str(e)}")
                return 50.0  # Return neutral score if conversion fails
            
            # Log sample data for debugging
            if len(trades_df) > 0:
                self.logger.debug(f"Sample trade data: {trades_df.iloc[0].to_dict()}")

            # Set rolling window for liquidity measurement based on config
            latest_time = trades_df['time'].max()
            window_start = latest_time - pd.Timedelta(minutes=window_minutes)

            # Filter trades within the time window
            recent_trades = trades_df[trades_df['time'] >= window_start]
            
            if len(recent_trades) < 5:
                self.logger.warning(f"Only {len(recent_trades)} trades in the last {window_minutes} minutes, insufficient for reliable liquidity calculation")
                return 50.0  # Neutral score for insufficient recent data

            # Calculate trade frequency (trades per second)
            trade_frequency = len(recent_trades) / (window_minutes * 60)
            
            # Calculate trade volume
            total_volume = recent_trades['size'].sum()
            
            # Log detailed statistics - safely format numeric values
            self.logger.debug(f"Liquidity calculation statistics:")
            self.logger.debug(f"- Time window: {window_minutes} minutes")
            self.logger.debug(f"- Total trades: {len(recent_trades)}")
            self.logger.debug(f"- Trade frequency: {trade_frequency:.2f} trades/sec (max: {max_trades_per_sec})")
            self.logger.debug(f"- Total volume: {float(total_volume):.2f} (max: {max_volume})")

            # Normalize trade frequency (using configured max value)
            normalized_frequency = min(1, trade_frequency / max_trades_per_sec) * 100
            
            # Normalize trade volume (using configured max value)
            normalized_volume = min(1, float(total_volume) / max_volume) * 100
            
            # Log normalized values
            self.logger.debug(f"Normalized values:")
            self.logger.debug(f"- Frequency score: {normalized_frequency:.2f} (weight: {frequency_weight:.2f})")
            self.logger.debug(f"- Volume score: {normalized_volume:.2f} (weight: {volume_weight:.2f})")

            # Compute final liquidity score with configured weights
            liquidity_score = (normalized_frequency * frequency_weight) + (normalized_volume * volume_weight)
            
            self.logger.debug(f"Final liquidity score: {liquidity_score:.2f}")
            if liquidity_score > 75:
                self.logger.debug("High liquidity detected")
            elif liquidity_score < 25:
                self.logger.debug("Low liquidity detected")
            else:
                self.logger.debug("Normal liquidity levels")

            # Store in cache before returning
            self._cache[cache_key] = liquidity_score

            return round(liquidity_score, 2)

        except Exception as e:
            self.logger.error(f"Error calculating liquidity score: {str(e)}")
            if self.debug_level >= 3:
                import traceback
                self.logger.error(traceback.format_exc())
            return 50.0  # Return neutral score if error occurs

    def _calculate_price_cvd_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and CVD.
        
        This method detects when price is moving in one direction but CVD is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and trades
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_cvd_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        calculation_start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-CVD DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < self.min_trades:
                self.logger.warning(f"Insufficient trade data for price-CVD divergence calculation: {len(trades)} trades, minimum required: {self.min_trades}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Convert trades to DataFrame if needed
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Log trades DataFrame info
            self.logger.debug(f"Trades DataFrame: shape={trades_df.shape}, columns={list(trades_df.columns)}")
            
            # Ensure we have timestamp in trades
            if 'time' not in trades_df.columns and 'timestamp' in trades_df.columns:
                trades_df['time'] = trades_df['timestamp']
                self.logger.debug("Mapped 'timestamp' to 'time' in trades DataFrame")
            elif 'time' not in trades_df.columns and 'T' in trades_df.columns:
                trades_df['time'] = trades_df['T']
                self.logger.debug("Mapped 'T' to 'time' in trades DataFrame")
                
            if 'time' not in trades_df.columns:
                self.logger.warning("Missing time/timestamp in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure time column is numeric
            try:
                trades_df['time'] = pd.to_numeric(trades_df['time'])
                self.logger.debug(f"Converted time column to numeric. Sample values: {trades_df['time'].head(3).tolist()}")
            except Exception as e:
                self.logger.warning(f"Failed to convert time column to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have side in trades
            if 'side' not in trades_df.columns and 'S' in trades_df.columns:
                trades_df['side'] = trades_df['S']
                self.logger.debug("Mapped 'S' to 'side' in trades DataFrame")
                
            if 'side' not in trades_df.columns:
                self.logger.warning("Missing side in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have amount/size in trades
            if 'amount' not in trades_df.columns:
                for col in ['size', 'v', 'volume', 'qty', 'quantity']:
                    if col in trades_df.columns:
                        trades_df['amount'] = trades_df[col]
                        self.logger.debug(f"Mapped '{col}' to 'amount' in trades DataFrame")
                        break
                        
            if 'amount' not in trades_df.columns:
                self.logger.warning("Missing amount/size in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Get price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate CVD for each candle period
            candle_cvds = []
            candle_timestamps = []
            
            # Ensure proper time tracking for candle processing
            candle_start_time = time.time()
            
            for i in range(1, lookback + 1):
                if i >= len(ohlcv_df):
                    break
                    
                # Get timestamp range for this candle
                # Check if we have a timestamp column or need to use the index
                if 'timestamp' in ohlcv_df.columns:
                    candle_end_time = ohlcv_df.iloc[-i]['timestamp']
                    candle_start_time_ts = ohlcv_df.iloc[-(i+1)]['timestamp'] if i+1 < len(ohlcv_df) else ohlcv_df.iloc[-i]['timestamp'] - 60000  # Fallback: 1 minute earlier
                    self.logger.debug(f"Candle {i} timestamp from column: start={candle_start_time_ts}, end={candle_end_time}")
                    # Save the timestamp for potential interpolation later
                    candle_timestamps.append(candle_end_time)
                else:
                    # Try to use index as timestamp
                    try:
                        candle_end_time = ohlcv_df.index[-i]
                        candle_start_time_ts = ohlcv_df.index[-(i+1)] if i+1 < len(ohlcv_df) else candle_end_time - pd.Timedelta(minutes=1)
                        self.logger.debug(f"Candle {i} timestamp from index: start={candle_start_time_ts}, end={candle_end_time}")
                        # Save the timestamp for potential interpolation later
                        candle_timestamps.append(candle_end_time)
                    except Exception as e:
                        self.logger.debug(f"Failed to get timestamp from index: {str(e)}")
                        continue
                
                # Ensure start_time and end_time are numeric
                try:
                    # Convert pandas Timestamp to milliseconds since epoch
                    if isinstance(candle_start_time_ts, pd.Timestamp):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = int(candle_start_time_ts.timestamp() * 1000)
                        self.logger.debug(f"Converted start_time from pd.Timestamp {start_time_orig} to {candle_start_time_ts}")
                    elif isinstance(candle_start_time_ts, str):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = pd.to_numeric(candle_start_time_ts)
                        self.logger.debug(f"Converted start_time from string {start_time_orig} to {candle_start_time_ts}")
                    
                    if isinstance(candle_end_time, pd.Timestamp):
                        end_time_orig = candle_end_time
                        candle_end_time = int(candle_end_time.timestamp() * 1000)
                        self.logger.debug(f"Converted end_time from pd.Timestamp {end_time_orig} to {candle_end_time}")
                    elif isinstance(candle_end_time, str):
                        end_time_orig = candle_end_time
                        candle_end_time = pd.to_numeric(candle_end_time)
                        self.logger.debug(f"Converted end_time from string {end_time_orig} to {candle_end_time}")
                except Exception as e:
                    self.logger.debug(f"Failed to convert timestamp to numeric: {str(e)}")
                    continue
                
                # Filter trades for this candle
                candle_trades_filtered = trades_df[(trades_df['time'] >= candle_start_time_ts) & (trades_df['time'] < candle_end_time)]
                
                if candle_trades_filtered.empty:
                    self.logger.debug(f"No trades found for candle {i} (time range: {candle_start_time_ts} to {candle_end_time})")
                    candle_cvds.append(0)
                    continue
                
                # Create a copy to avoid SettingWithCopyWarning
                candle_trades = candle_trades_filtered.copy()
                
                self.logger.debug(f"Found {len(candle_trades)} trades for candle {i}")
                    
                # Calculate CVD for this candle
                try:
                    # Log the unique side values to aid in debugging
                    unique_sides = candle_trades['side'].astype(str).unique()
                    self.logger.debug(f"Unique side values in candle {i} trades: {unique_sides}")
                    
                    # Ensure amount column is numeric
                    try:
                        candle_trades.loc[:, 'amount'] = pd.to_numeric(candle_trades['amount'], errors='coerce')
                    except Exception as e:
                        self.logger.warning(f"Error converting amount to numeric: {str(e)}, trying fallback")
                        candle_trades.loc[:, 'amount'] = candle_trades['amount'].apply(lambda x: float(x) if isinstance(x, str) else x)
                    
                    # More robust way to determine buy/sell sides
                    def is_buy_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['buy', 'b', '1', 'true', 'bid', 'long']
                    
                    def is_sell_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['sell', 's', '-1', 'false', 'ask', 'short']
                    
                    # Apply the side detection functions
                    candle_trades.loc[:, 'is_buy'] = candle_trades['side'].apply(is_buy_side)
                    candle_trades.loc[:, 'is_sell'] = candle_trades['side'].apply(is_sell_side)
                    
                    # Log side detection results
                    buy_count = candle_trades['is_buy'].sum()
                    sell_count = candle_trades['is_sell'].sum()
                    unclassified = len(candle_trades) - buy_count - sell_count
                    self.logger.debug(f"Side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    if unclassified > 0 and len(unique_sides) > 0:
                        # If we have unclassified trades, try a more flexible approach
                        if all(side.lower() in ['buy', 'sell'] for side in unique_sides if isinstance(side, str)):
                            self.logger.debug(f"Using simpler case-insensitive matching for side values")
                            candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower() == 'buy'
                            candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower() == 'sell'
                            buy_count = candle_trades['is_buy'].sum()
                            sell_count = candle_trades['is_sell'].sum()
                            unclassified = len(candle_trades) - buy_count - sell_count
                            self.logger.debug(f"Updated side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    # Check for any remaining unclassified trades
                    if unclassified > 0 and buy_count == 0 and sell_count == 0:
                        # Last resort attempt - case-insensitive partial matching
                        self.logger.debug(f"Attempting case-insensitive partial matching for sides")
                        candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower().str.contains('buy', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('bid', na=False)
                        candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower().str.contains('sell', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('ask', na=False)
                        buy_count = candle_trades['is_buy'].sum()
                        sell_count = candle_trades['is_sell'].sum()
                        self.logger.debug(f"Final side classification: buy={buy_count}, sell={sell_count}, unclassified={len(candle_trades) - buy_count - sell_count}")
                    
                    # Calculate buy and sell volumes
                    buy_volume = candle_trades[candle_trades['is_buy']]['amount'].sum()
                    sell_volume = candle_trades[candle_trades['is_sell']]['amount'].sum()
                    
                    # Replace NaN with 0
                    buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                    sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                    
                    # Additional diagnostic for debugging
                    if buy_volume == 0 and sell_volume == 0:
                        # This shouldn't happen if we have trades and properly classified sides
                        # Log a sample of the trades to diagnose the issue
                        if not candle_trades.empty:
                            sample_trades = candle_trades.head(3)
                            self.logger.warning(f"Both buy and sell volumes are 0 despite having {len(candle_trades)} trades. Sample trades:")
                            for idx, trade in sample_trades.iterrows():
                                self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")
                            
                            # Check for data quality issues
                            amounts = candle_trades['amount'].tolist()
                            amount_stats = {
                                'min': candle_trades['amount'].min() if not candle_trades['amount'].empty else 'N/A',
                                'max': candle_trades['amount'].max() if not candle_trades['amount'].empty else 'N/A',
                                'mean': candle_trades['amount'].mean() if not candle_trades['amount'].empty else 'N/A',
                                'nan_count': candle_trades['amount'].isna().sum(),
                                'zero_count': (candle_trades['amount'] == 0).sum()
                            }
                            self.logger.warning(f"Amount stats: {amount_stats}")
                    
                    self.logger.debug(f"Candle {i} CVD calculation: buy_volume={buy_volume:.4f}, sell_volume={sell_volume:.4f}, types: {type(buy_volume)}, {type(sell_volume)}")
                    
                    candle_cvd = buy_volume - sell_volume
                    candle_cvds.append(candle_cvd)
                    self.logger.debug(f"Candle {i} CVD: {candle_cvd:.4f}")
                except Exception as e:
                    self.logger.warning(f"Error calculating candle {i} CVD: {str(e)}, using 0 instead")
                    # Log more details about the error for debugging
                    import traceback
                    self.logger.debug(f"Error details: {traceback.format_exc()}")
                    
                    # Try to get information about the candle_trades DataFrame
                    try:
                        if 'candle_trades' in locals() and not candle_trades.empty:
                            self.logger.debug(f"Candle trades info: shape={candle_trades.shape}, columns={list(candle_trades.columns)}")
                            self.logger.debug(f"Sample trades: {candle_trades.head(2).to_dict('records')}")
                            self.logger.debug(f"Side values: {candle_trades['side'].value_counts().to_dict()}")
                    except Exception as inner_e:
                        self.logger.debug(f"Failed to log candle trades information: {str(inner_e)}")
                    
                    candle_cvds.append(0)
            
            # Check if we have enough candle CVD values
            if len(candle_cvds) < 2:
                self.logger.warning(f"Insufficient candle CVD data: {len(candle_cvds)} values")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Interpolate for candles without trades if enabled
            if getattr(self, 'interpolate_missing_cvd', True) and 0 in candle_cvds:
                self.logger.debug("Interpolating CVD values for candles without trades")
                # Create a series with timestamps and CVD values
                cvd_series = pd.Series(candle_cvds, index=candle_timestamps[:len(candle_cvds)])
                
                # Find indices of non-zero values
                non_zero_indices = [i for i, cvd in enumerate(candle_cvds) if cvd != 0]
                if not non_zero_indices:
                    self.logger.debug("No non-zero CVD values found for interpolation")
                else:
                    self.logger.debug(f"Found {len(non_zero_indices)} non-zero values at indices: {non_zero_indices}")
                    
                    # Handle zeros before first non-zero (backfill)
                    first_non_zero_idx = non_zero_indices[0]
                    first_non_zero_val = candle_cvds[first_non_zero_idx]
                    if first_non_zero_idx > 0:
                        self.logger.debug(f"Backfilling {first_non_zero_idx} initial zeros before first value {first_non_zero_val}")
                        for j in range(0, first_non_zero_idx):
                            # Use a linear ramp up to the first value
                            candle_cvds[j] = first_non_zero_val * (j + 1) / (first_non_zero_idx + 1)
                    
                    # Handle zeros between non-zero values (interpolation)
                    for idx_pos in range(len(non_zero_indices) - 1):
                        start_idx = non_zero_indices[idx_pos]
                        end_idx = non_zero_indices[idx_pos + 1]
                        start_val = candle_cvds[start_idx]
                        end_val = candle_cvds[end_idx]
                        
                        if end_idx - start_idx > 1:  # If there are zeros between
                            self.logger.debug(f"Interpolating between index {start_idx} ({start_val}) and {end_idx} ({end_val})")
                            for j in range(start_idx + 1, end_idx):
                                # Linear interpolation
                                ratio = (j - start_idx) / (end_idx - start_idx)
                                candle_cvds[j] = start_val + (end_val - start_val) * ratio
                    
                    # Handle zeros after last non-zero (extrapolation)
                    last_non_zero_idx = non_zero_indices[-1]
                    last_non_zero_val = candle_cvds[last_non_zero_idx]
                    
                    if last_non_zero_idx < len(candle_cvds) - 1:
                        # Calculate trend from available non-zero values
                        if len(non_zero_indices) >= 2:
                            # Use the last two non-zero values to determine trend
                            prev_idx = non_zero_indices[-2]
                            prev_val = candle_cvds[prev_idx]
                            last_idx = non_zero_indices[-1]
                            last_val = candle_cvds[last_idx]
                            
                            # Calculate slope (per candle)
                            trend_slope = (last_val - prev_val) / (last_idx - prev_idx)
                            self.logger.debug(f"Extrapolating with slope {trend_slope:.4f} based on last values {prev_val:.4f} and {last_val:.4f}")
                            
                            # Apply diminishing trend after last value (decay factor reduces impact over time)
                            decay_factor = 0.8  # Reduce impact by 20% each candle
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Calculate diminishing effect with distance
                                decay = decay_factor ** steps
                                extrapolated_val = last_non_zero_val + (trend_slope * steps * decay)
                                candle_cvds[j] = extrapolated_val
                        else:
                            # Only one non-zero value, use decay from that value
                            self.logger.debug(f"Only one non-zero value ({last_non_zero_val:.4f}), using decay extrapolation")
                            decay_factor = 0.7  # Stronger decay when we have less information
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Apply decay from last known value
                                candle_cvds[j] = last_non_zero_val * (decay_factor ** steps)
                        
                        self.logger.debug(f"Extrapolated {len(candle_cvds) - last_non_zero_idx - 1} values after last non-zero value")
                
                zero_count = candle_cvds.count(0)
                self.logger.debug(f"After interpolation, zero values remaining: {zero_count}")
                if zero_count > 0:
                    zero_indices = [i for i, val in enumerate(candle_cvds) if val == 0]
                    self.logger.debug(f"Remaining zeros at indices: {zero_indices}")
                    # Last attempt to fill any remaining zeros with small random values
                    for idx in zero_indices:
                        # Use a small percentage of the max absolute CVD as a fallback
                        max_abs_cvd = max(abs(cvd) for cvd in candle_cvds if cvd != 0) if any(cvd != 0 for cvd in candle_cvds) else 1.0
                        candle_cvds[idx] = max_abs_cvd * 0.01  # 1% of max as fallback
            
            self.logger.debug(f"Calculated CVD for {len(candle_cvds)} candles")
            self.logger.debug(f"Candle CVDs: min={min(candle_cvds):.4f}, max={max(candle_cvds):.4f}, mean={sum(candle_cvds)/len(candle_cvds):.4f}")
            
            # Apply time weighting if enabled
            weighted_candle_cvds = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, cvd in enumerate(candle_cvds):
                    # Apply exponential weighting - more recent candles get higher weight
                    # i=0 is the most recent candle
                    weight = self.recency_factor ** (len(candle_cvds) - 1 - i)
                    weighted_candle_cvds.append(cvd * weight)
                    self.logger.debug(f"Candle {i} CVD: {cvd:.2f}, Weight: {weight:.2f}, Weighted: {cvd * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw CVD values")
                weighted_candle_cvds = candle_cvds
            
            # Calculate CVD trend with time weighting
            cvd_trend = sum(weighted_candle_cvds)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_candle_cvds)
            
            self.logger.debug(f"CVD trend: {cvd_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            if (price_trend > 0 and cvd_trend < 0):
                # Bearish divergence: Price up, CVD down
                divergence_type = 'bearish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), CVD trend={cvd_trend:.4f} (down)")
            elif (price_trend < 0 and cvd_trend > 0):
                # Bullish divergence: Price down, CVD up
                divergence_type = 'bullish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), CVD trend={cvd_trend:.4f} (up)")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, CVD trend={cvd_trend:.4f}")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                calculation_end_time = time.time()
                execution_time = calculation_end_time - calculation_start_time
                self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.info(f"Price-CVD divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Fix time tracking for candle processing
            candle_processing_end_time = time.time()
            candle_processing_time = candle_processing_end_time - candle_start_time
            self.logger.debug(f"Processed {lookback} candles in {candle_processing_time:.4f} seconds")
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating price-CVD divergence: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_price_oi_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and open interest.
        
        This method detects when price is moving in one direction but open interest is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and open interest data
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_oi_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Enhanced debugging: Log market_data top-level keys
        self.logger.debug(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
        
        # Check if open interest data is available before proceeding
        if ('open_interest' not in market_data and 
            ('sentiment' not in market_data or 'open_interest' not in market_data.get('sentiment', {}))):
            self.logger.warning("Missing open interest data for price-OI divergence calculation")
            
            # Enhanced debugging: More details about the structure if data is missing
            if 'sentiment' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Sentiment keys available: {list(market_data['sentiment'].keys())}")
            if 'open_interest' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Open interest appears empty or malformed: {market_data['open_interest']}")
                
            return {'type': 'neutral', 'strength': 0.0}
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-OI DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        # Enhanced debugging: Log concise OI structure info
        if 'open_interest' in market_data:
            oi_dump = market_data['open_interest']
            if isinstance(oi_dump, dict):
                # Log only essential info instead of full structure
                history_count = len(oi_dump.get('history', []))
                current_oi = oi_dump.get('current', 'N/A')
                previous_oi = oi_dump.get('previous', 'N/A')
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI data - current: {current_oi}, previous: {previous_oi}, history entries: {history_count}")
            else:
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI not a dictionary: {type(oi_dump)}")
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Check if we have open interest data at the top level
            oi_data = None
            oi_history = []
            
            # First check for open interest at the top level (new structure)
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                self.logger.debug("Found open interest data at top level")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            # Fallback to sentiment.open_interest for backward compatibility
            elif 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                self.logger.debug("Found open interest data in sentiment section")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            else:
                self.logger.warning("Missing open interest data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Get open interest history
            if 'open_interest_history' in market_data and isinstance(market_data['open_interest_history'], list):
                # ADDED: Check for direct reference first
                oi_history = market_data['open_interest_history']
                self.logger.debug(f"Using direct open_interest_history reference with {len(oi_history)} entries")
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"First OI entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"First OI entry: {first_entry}")
            elif isinstance(oi_data, dict) and 'history' in oi_data and isinstance(oi_data['history'], list):
                oi_history = oi_data['history']
                self.logger.debug(f"Using open interest history from 'history' key with {len(oi_history)} entries")
                # Enhanced debugging: Sample of history data
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: {first_entry}")
                    
                    if len(oi_history) > 1:
                        second_entry = oi_history[1]
                        if isinstance(second_entry, dict):
                            timestamp = second_entry.get('timestamp', 'N/A')
                            value = second_entry.get('value', 'N/A')
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: timestamp={timestamp}, value={value}")
                        else:
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: {second_entry}")
            elif isinstance(oi_data, list):
                # If OI data is already a list
                oi_history = oi_data
                self.logger.debug(f"Using open interest data directly as list with {len(oi_history)} entries")
            else:
                # Enhanced debugging: Log what was found in the structure
                self.logger.warning(f"OI-PRICE DIVERGENCE: No proper history found. OI data type: {type(oi_data)}")
                if isinstance(oi_data, dict):
                    self.logger.warning(f"OI-PRICE DIVERGENCE: OI data keys: {list(oi_data.keys())}")
                # If we don't have history, we can't calculate divergence
                self.logger.warning("No open interest history available for divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            if len(oi_history) < 2:
                self.logger.warning(f"Insufficient open interest history for divergence calculation: {len(oi_history)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Log sample of OI history
            if len(oi_history) > 0:
                sample_entry = oi_history[0]
                self.logger.debug(f"OI history sample entry: {sample_entry}")
                if isinstance(sample_entry, dict):
                    self.logger.debug(f"OI history entry keys: {list(sample_entry.keys())}")
            
            # Get timestamps for alignment
            # Check if we have a timestamp column or need to use the index
            if 'timestamp' in ohlcv_df.columns:
                start_timestamp = ohlcv_df.iloc[-lookback]['timestamp']
                self.logger.debug(f"Using timestamp column for alignment, start_timestamp: {start_timestamp}")
            else:
                # Try to use index as timestamp
                try:
                    start_timestamp = ohlcv_df.index[-lookback]
                    self.logger.debug(f"Using index for alignment, start_timestamp: {start_timestamp}")
                except Exception as e:
                    self.logger.warning(f"Failed to get start timestamp from OHLCV data: {str(e)}")
                    return {'type': 'neutral', 'strength': 0.0}
            
            # Ensure start_timestamp is numeric
            try:
                # Convert pandas Timestamp to milliseconds since epoch
                if isinstance(start_timestamp, pd.Timestamp):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = int(start_timestamp.timestamp() * 1000)
                    self.logger.debug(f"Converted start_timestamp from pd.Timestamp {start_timestamp_orig} to {start_timestamp}")
                elif isinstance(start_timestamp, str):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = pd.to_numeric(start_timestamp)
                    self.logger.debug(f"Converted start_timestamp from string {start_timestamp_orig} to {start_timestamp}")
            except Exception as e:
                self.logger.warning(f"Failed to convert start_timestamp to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Filter OI history to match the same time period as price data
            aligned_oi_values = []
            aligned_timestamps = []
            
            self.logger.debug(f"Aligning OI history with price data, start_timestamp: {start_timestamp}")
            
            for entry in oi_history:
                entry_timestamp = entry['timestamp'] if isinstance(entry, dict) and 'timestamp' in entry else None
                
                # Ensure entry_timestamp is numeric for comparison
                try:
                    if entry_timestamp is not None:
                        entry_timestamp = pd.to_numeric(entry_timestamp) if isinstance(entry_timestamp, (str, pd.Timestamp)) else entry_timestamp
                        
                        if entry_timestamp >= start_timestamp:
                            entry_value = float(entry['value']) if isinstance(entry, dict) and 'value' in entry else float(entry)
                            aligned_oi_values.append(entry_value)
                            aligned_timestamps.append(entry_timestamp)
                except Exception as e:
                    self.logger.debug(f"Failed to process OI entry timestamp: {str(e)}")
                    continue
            
            # Continue with aligned OI values
            if len(aligned_oi_values) < 2:
                self.logger.warning(f"Insufficient aligned OI data for divergence calculation: {len(aligned_oi_values)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Successfully aligned {len(aligned_oi_values)} OI entries with price data")
            self.logger.debug(f"Aligned OI values: min={min(aligned_oi_values):.2f}, max={max(aligned_oi_values):.2f}, mean={sum(aligned_oi_values)/len(aligned_oi_values):.2f}")
            
            # Calculate price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate OI changes
            oi_changes = [aligned_oi_values[i] - aligned_oi_values[i-1] for i in range(1, len(aligned_oi_values))]
            
            self.logger.debug(f"OI changes: {len(oi_changes)} entries")
            self.logger.debug(f"OI changes: min={min(oi_changes):.2f}, max={max(oi_changes):.2f}, mean={sum(oi_changes)/len(oi_changes):.2f}")
            
            # Enhanced debugging: Detailed OI change data (only show first few entries)
            if self.debug_level >= 3:  # Only show detailed changes at highest debug level
                self.logger.debug("OI-PRICE DIVERGENCE: Detailed OI changes (first 3 entries):")
                for i, change in enumerate(oi_changes[:3]):  # Only show first 3 entries
                    self.logger.debug(f"  Entry {i}: Value: {aligned_oi_values[i]:.2f}, Previous: {aligned_oi_values[i-1]:.2f}, Change: {change:.2f}")
                if len(oi_changes) > 3:
                    self.logger.debug(f"  ... and {len(oi_changes) - 3} more entries")
            
            # Apply time weighting if enabled
            weighted_oi_changes = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, change in enumerate(oi_changes):
                    # Apply exponential weighting - more recent changes get higher weight
                    weight = self.recency_factor ** (len(oi_changes) - 1 - i)
                    weighted_oi_changes.append(change * weight)
                    # Only log detailed weighting at highest debug level
                    if self.debug_level >= 3:
                        self.logger.debug(f"OI Change {i}: {change:.2f}, Weight: {weight:.2f}, Weighted: {change * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw OI changes")
                weighted_oi_changes = oi_changes
            
            # Calculate OI trend with time weighting
            oi_trend = sum(weighted_oi_changes)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_oi_changes)
            
            self.logger.debug(f"OI trend: {oi_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            # Enhanced debugging: Detailed comparison
            self.logger.debug(f"OI-PRICE DIVERGENCE: Final comparison - Price trend: {price_trend:.4f}, OI trend: {oi_trend:.4f}")
            
            if (price_trend > 0 and oi_trend < 0):
                # Bearish divergence: Price up, OI down
                divergence_type = 'bearish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), OI trend={oi_trend:.4f} (down)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bearish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            elif (price_trend < 0 and oi_trend > 0):
                # Bullish divergence: Price down, OI up
                divergence_type = 'bullish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), OI trend={oi_trend:.4f} (up)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bullish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, OI trend={oi_trend:.4f}")
                # Enhanced debugging: Why no divergence was detected (only at highest debug level)
                if self.debug_level >= 3:
                    if price_trend > 0 and oi_trend >= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending up (no divergence)")
                    elif price_trend < 0 and oi_trend <= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending down (no divergence)")
                    elif price_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No price trend detected")
                    elif oi_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No OI trend detected")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                execution_time = time.time() - start_time
                self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
                
            self.logger.info(f"Price-OI divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Log execution time
            execution_time = time.time() - start_time
            self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error calculating price-OI divergence: {str(e)}")
            self.logger.error(f"OI-PRICE DIVERGENCE Error traceback: {traceback.format_exc()}")
            
            # Log market data structure for debugging (concise version)
            try:
                if 'open_interest' in market_data:
                    oi_data = market_data['open_interest']
                    if isinstance(oi_data, dict):
                        history_count = len(oi_data.get('history', []))
                        current_oi = oi_data.get('current', 'N/A')
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - current: {current_oi}, history entries: {history_count}")
                    else:
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - type: {type(oi_data)}")
                self.logger.error(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
            except Exception as json_err:
                self.logger.error(f"OI-PRICE DIVERGENCE: Could not log market data structure due to error: {str(json_err)}")
                
            # Log execution time even in error case
            execution_time = time.time() - start_time if 'start_time' in locals() else -1
            self.logger.debug(f"Price-OI divergence calculation failed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_trade_flow(self, trades_df: Union[pd.DataFrame, Dict, List]) -> float:
        """Calculate trade flow indicator (buy vs sell pressure).
        
        Args:
            trades_df: DataFrame, dictionary or list containing trade data
            
        Returns:
            float: Trade flow value between -1 and 1
        """
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING TRADE FLOW CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Initialize variables
            df = None
            
            # Log input data type
            self.logger.debug(f"Input trades_df type: {type(trades_df)}")
            
            # Handle different input types
            if isinstance(trades_df, pd.DataFrame):
                # Input is already a DataFrame
                df = trades_df.copy()
                self.logger.debug(f"Using trades DataFrame directly, shape: {df.shape}, columns: {list(df.columns)}")
            
            elif isinstance(trades_df, list) and trades_df:
                # Input is a list of trade dictionaries
                try:
                    self.logger.debug(f"Input is a list with {len(trades_df)} trade records")
                    if len(trades_df) > 0:
                        self.logger.debug(f"First trade sample: {trades_df[0]}")
                    df = pd.DataFrame(trades_df)
                    self.logger.debug(f"Converted trades list to DataFrame with {len(trades_df)} records, columns: {list(df.columns)}")
                except Exception as e:
                    self.logger.error(f"Failed to convert trades list to DataFrame: {e}")
                    self.logger.debug(traceback.format_exc())
                    return 0.0
            
            elif isinstance(trades_df, dict):
                # Input is a dictionary, try to find trades data
                self.logger.debug(f"Input is a dictionary with keys: {list(trades_df.keys())}")
                
                if 'trades_df' in trades_df and isinstance(trades_df['trades_df'], pd.DataFrame):
                    df = trades_df['trades_df'].copy()
                    self.logger.debug(f"Using trades_df from dictionary, shape: {df.shape}, columns: {list(df.columns)}")
                
                elif 'trades' in trades_df and isinstance(trades_df['trades'], list) and trades_df['trades']:
                    try:
                        self.logger.debug(f"Using trades list from dictionary with {len(trades_df['trades'])} records")
                        if len(trades_df['trades']) > 0:
                            self.logger.debug(f"First trade sample: {trades_df['trades'][0]}")
                        df = pd.DataFrame(trades_df['trades'])
                        self.logger.debug(f"Converted trades list from dictionary to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list from dictionary to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                elif 'processed_trades' in trades_df and isinstance(trades_df['processed_trades'], list) and trades_df['processed_trades']:
                    try:
                        self.logger.debug(f"Using processed_trades from dictionary with {len(trades_df['processed_trades'])} records")
                        if len(trades_df['processed_trades']) > 0:
                            self.logger.debug(f"First processed trade sample: {trades_df['processed_trades'][0]}")
                        df = pd.DataFrame(trades_df['processed_trades'])
                        self.logger.debug(f"Converted processed_trades to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert processed_trades to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                else:
                    self.logger.warning("No valid trade data found in dictionary")
                    return 0.0
            
            else:
                self.logger.error(f"Unsupported trades_df type: {type(trades_df)}")
                return 0.0
            
            # Check if we have a valid DataFrame
            if df is None or df.empty:
                self.logger.warning("No trade data available for trade flow calculation")
                return 0.0
            
            # Log DataFrame info
            self.logger.debug(f"Trade DataFrame info: {len(df)} rows, columns: {list(df.columns)}")
            
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in df.columns:
                    for col in possible_cols:
                        if col in df.columns:
                            df[std_col] = df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}'")
                            break
            
            # Check if we have the required columns after mapping
            if 'side' not in df.columns or 'amount' not in df.columns:
                missing = []
                if 'side' not in df.columns:
                    missing.append('side')
                if 'amount' not in df.columns:
                    missing.append('amount')
                self.logger.warning(f"Missing required columns after mapping: {missing}. Available columns: {list(df.columns)}")
                return 0.0
            
            # Normalize side values
            try:
                # Convert to string first to handle numeric side values
                df['side'] = df['side'].astype(str)
                self.logger.debug(f"Side value counts before normalization: {df['side'].value_counts().to_dict()}")
                
                # Ensure amount column is numeric
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # Log amount statistics before dropping NaN values
                amount_stats_before = {
                    'count': len(df),
                    'nan_count': df['amount'].isna().sum(),
                    'min': df['amount'].min() if not df['amount'].isna().all() else 'N/A',
                    'max': df['amount'].max() if not df['amount'].isna().all() else 'N/A',
                    'mean': df['amount'].mean() if not df['amount'].isna().all() else 'N/A',
                    'sum': df['amount'].sum() if not df['amount'].isna().all() else 'N/A'
                }
                self.logger.debug(f"Amount statistics before dropping NaN: {amount_stats_before}")
                
                # Drop rows with non-numeric amounts
                df = df.dropna(subset=['amount'])
                
                # Log amount statistics after dropping NaN values
                amount_stats_after = {
                    'count': len(df),
                    'min': df['amount'].min() if not df.empty else 'N/A',
                    'max': df['amount'].max() if not df.empty else 'N/A',
                    'mean': df['amount'].mean() if not df.empty else 'N/A',
                    'sum': df['amount'].sum() if not df.empty else 'N/A'
                }
                self.logger.debug(f"Amount statistics after dropping NaN: {amount_stats_after}")
                
                # Normalize to lowercase
                df['side'] = df['side'].str.lower()
                
                # Map different side values to buy/sell
                buy_values = ['buy', 'b', 'bid', '1', 'true', 'long']
                sell_values = ['sell', 's', 'ask', 'offer', '-1', 'false', 'short']
                
                # Create a normalized side column
                df['norm_side'] = 'unknown'
                df.loc[df['side'].isin(buy_values), 'norm_side'] = 'buy'
                df.loc[df['side'].isin(sell_values), 'norm_side'] = 'sell'
                
                # Log normalized side value counts
                norm_side_counts = df['norm_side'].value_counts().to_dict()
                self.logger.debug(f"Normalized side value counts: {norm_side_counts}")
                
                # Log unknown sides
                unknown_count = (df['norm_side'] == 'unknown').sum()
                if unknown_count > 0:
                    unknown_pct = (unknown_count / len(df)) * 100
                    self.logger.warning(f"Found {unknown_count} trades ({unknown_pct:.2f}%) with unknown side values")
                    
                    # Log some examples of unknown side values
                    unknown_sides = df[df['norm_side'] == 'unknown']['side'].unique()
                    self.logger.debug(f"Examples of unknown side values: {unknown_sides[:10]}")
                    
                    # Randomly assign sides to unknown values to avoid bias
                    unknown_mask = df['norm_side'] == 'unknown'
                    random_sides = np.random.choice(['buy', 'sell'], size=unknown_count)
                    df.loc[unknown_mask, 'norm_side'] = random_sides
                    self.logger.debug(f"Randomly assigned sides to {unknown_count} trades")
                    
                    # Log updated normalized side value counts
                    updated_norm_side_counts = df['norm_side'].value_counts().to_dict()
                    self.logger.debug(f"Updated normalized side value counts after random assignment: {updated_norm_side_counts}")
                
                # Calculate buy and sell volumes
                buy_volume = pd.to_numeric(df[df['norm_side'] == 'buy']['amount'].sum(), errors='coerce')
                sell_volume = pd.to_numeric(df[df['norm_side'] == 'sell']['amount'].sum(), errors='coerce')
                
                # Replace NaN with 0
                buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                
                self.logger.debug(f"Trade flow volumes: buy_volume={buy_volume}, sell_volume={sell_volume}, types: {type(buy_volume)}, {type(sell_volume)}")
                
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    # Calculate trade flow: range from -1 (all sells) to 1 (all buys)
                    trade_flow = (buy_volume - sell_volume) / total_volume
                    buy_pct = (buy_volume / total_volume) * 100
                    sell_pct = (sell_volume / total_volume) * 100
                    self.logger.debug(f"Trade flow calculated: {trade_flow:.4f} (buy: {buy_volume:.4f} [{buy_pct:.2f}%], sell: {sell_volume:.4f} [{sell_pct:.2f}%])")
                    
                    # Log execution time
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds")
                    self.logger.debug("=" * 50)
                    
                    return float(trade_flow)
                else:
                    self.logger.warning("Zero total volume, cannot calculate trade flow")
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds with zero volume")
                    self.logger.debug("=" * 50)
                    return 0.0
                    
            except Exception as e:
                self.logger.error(f"Error calculating trade flow volumes: {str(e)}")
                self.logger.debug(traceback.format_exc())
                execution_time = time.time() - start_time
                self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error in trade flow calculation: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 0.0

    # ===== SMART MONEY CONCEPTS - LIQUIDITY ZONES =====
    # Moved from price_structure_indicators.py as this is pure order flow analysis
    
    def _calculate_liquidity_zones_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate liquidity zones score across timeframes for order flow analysis."""
        try:
            # Extract OHLCV data from market_data
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                self.logger.warning("No OHLCV data available for liquidity zones analysis")
                return 50.0
            
            scores = []
            weights = {'htf': 0.4, 'mtf': 0.35, 'ltf': 0.25, 'base': 0.3}  # Include base timeframe
            
            for tf, weight in weights.items():
                if tf not in ohlcv_data:
                    continue
                    
                df = ohlcv_data[tf]
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                
                # Detect liquidity zones
                liquidity_zones = self._detect_liquidity_zones(df)
                
                # Calculate score based on proximity and sweeps
                current_price = df['close'].iloc[-1]
                tf_score = self._score_liquidity_proximity(current_price, liquidity_zones)
                
                scores.append(tf_score * weight)
                self.logger.debug(f"Liquidity zones score for {tf}: {tf_score:.2f}")
            
            final_score = float(np.sum(scores)) if scores else 50.0
            self.logger.debug(f"Final liquidity zones score: {final_score:.2f}")
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity zones score: {str(e)}")
            return 50.0

    def _detect_liquidity_zones(self, df: pd.DataFrame, swing_length: int = 50, range_percent: float = 0.01) -> Dict[str, Any]:
        """
        Detect liquidity zones where multiple swing highs/lows cluster.
        
        This is pure order flow analysis - identifying where stop losses cluster
        and where institutional players target retail liquidity.
        
        Args:
            df: OHLCV DataFrame
            swing_length: Length for swing detection
            range_percent: Percentage range for clustering
            
        Returns:
            Dict containing liquidity zone information
        """
        try:
            # First detect swing highs and lows
            swing_data = self._detect_swing_highs_lows(df, swing_length)
            
            # Group nearby swings into liquidity zones
            liquidity_zones = {
                'bullish': [],  # Areas of liquidity below price (support/buy stops)
                'bearish': []   # Areas of liquidity above price (resistance/sell stops)
            }
            
            # Process swing lows for bullish liquidity (where buy stops cluster)
            swing_lows = [(idx, level) for idx, level, swing_type in swing_data if swing_type == -1]
            if swing_lows:
                low_clusters = self._cluster_swing_points(swing_lows, range_percent)
                for cluster in low_clusters:
                    if len(cluster) >= 2:  # At least 2 swing lows
                        zone = self._create_liquidity_zone(df, cluster, 'bullish')
                        liquidity_zones['bullish'].append(zone)
            
            # Process swing highs for bearish liquidity (where sell stops cluster)
            swing_highs = [(idx, level) for idx, level, swing_type in swing_data if swing_type == 1]
            if swing_highs:
                high_clusters = self._cluster_swing_points(swing_highs, range_percent)
                for cluster in high_clusters:
                    if len(cluster) >= 2:  # At least 2 swing highs
                        zone = self._create_liquidity_zone(df, cluster, 'bearish')
                        liquidity_zones['bearish'].append(zone)
            
            # Check for liquidity sweeps (smart money hunting retail stops)
            self._check_liquidity_sweeps(df, liquidity_zones)
            
            return liquidity_zones
            
        except Exception as e:
            self.logger.error(f"Error detecting liquidity zones: {str(e)}")
            return {'bullish': [], 'bearish': []}

    def _detect_swing_highs_lows(self, df: pd.DataFrame, swing_length: int) -> List[Tuple[int, float, int]]:
        """Detect swing highs and lows for liquidity zone analysis."""
        swings = []
        
        for i in range(swing_length, len(df) - swing_length):
            # Check for swing high
            current_high = df['high'].iloc[i]
            is_swing_high = True
            
            for j in range(i - swing_length, i + swing_length + 1):
                if j != i and df['high'].iloc[j] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swings.append((i, current_high, 1))  # 1 for swing high
            
            # Check for swing low
            current_low = df['low'].iloc[i]
            is_swing_low = True
            
            for j in range(i - swing_length, i + swing_length + 1):
                if j != i and df['low'].iloc[j] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swings.append((i, current_low, -1))  # -1 for swing low
        
        return swings

    def _cluster_swing_points(self, swing_points: List[Tuple[int, float]], range_percent: float) -> List[List[Tuple[int, float]]]:
        """Cluster swing points that are within range_percent of each other."""
        if not swing_points:
            return []
            
        # Sort by price level
        sorted_swings = sorted(swing_points, key=lambda x: x[1])
        clusters = []
        current_cluster = [sorted_swings[0]]
        
        for i in range(1, len(sorted_swings)):
            current_price = sorted_swings[i][1]
            cluster_avg = np.mean([s[1] for s in current_cluster])
            
            # Check if within range
            if abs(current_price - cluster_avg) / cluster_avg <= range_percent:
                current_cluster.append(sorted_swings[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [sorted_swings[i]]
        
        # Add last cluster
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
            
        return clusters

    def _create_liquidity_zone(self, df: pd.DataFrame, cluster: List[Tuple[int, float]], zone_type: str) -> Dict[str, Any]:
        """Create a liquidity zone from a cluster of swing points."""
        levels = [point[1] for point in cluster]
        indices = [point[0] for point in cluster]
        
        return {
            'type': zone_type,
            'level': np.mean(levels),
            'high': max(levels),
            'low': min(levels),
            'strength': len(cluster),  # Number of stop clusters
            'indices': indices,
            'swept': False,
            'sweep_index': None,
            'last_test': max(indices),
            'liquidity_type': 'buy_stops' if zone_type == 'bullish' else 'sell_stops'
        }

    def _check_liquidity_sweeps(self, df: pd.DataFrame, liquidity_zones: Dict[str, List]) -> None:
        """
        Check if liquidity zones have been swept by smart money.
        
        A liquidity sweep occurs when price breaks through a zone (taking stops)
        and then reverses, indicating institutional order flow.
        """
        try:
            # Check bullish liquidity sweeps (smart money hunting buy stops below support)
            for zone in liquidity_zones['bullish']:
                if zone['swept']:
                    continue
                    
                start_idx = zone['last_test']
                for i in range(start_idx, len(df)):
                    # Check if price swept below the zone (taking buy stops)
                    if df['low'].iloc[i] < zone['low']:
                        # Look for reversal (smart money buying after taking stops)
                        for j in range(i + 1, min(i + 10, len(df))):
                            if df['close'].iloc[j] > zone['level']:
                                zone['swept'] = True
                                zone['sweep_index'] = i
                                zone['sweep_type'] = 'buy_stops_taken'
                                break
                        break
            
            # Check bearish liquidity sweeps (smart money hunting sell stops above resistance)
            for zone in liquidity_zones['bearish']:
                if zone['swept']:
                    continue
                    
                start_idx = zone['last_test']
                for i in range(start_idx, len(df)):
                    # Check if price swept above the zone (taking sell stops)
                    if df['high'].iloc[i] > zone['high']:
                        # Look for reversal (smart money selling after taking stops)
                        for j in range(i + 1, min(i + 10, len(df))):
                            if df['close'].iloc[j] < zone['level']:
                                zone['swept'] = True
                                zone['sweep_index'] = i
                                zone['sweep_type'] = 'sell_stops_taken'
                                break
                        break
                        
        except Exception as e:
            self.logger.error(f"Error checking liquidity sweeps: {str(e)}")

    def _score_liquidity_proximity(self, current_price: float, liquidity_zones: Dict[str, List]) -> float:
        """
        Score based on proximity to liquidity zones and sweep patterns.
        
        This is order flow analysis - higher scores indicate bullish order flow
        (price near swept resistance or above support liquidity).
        """
        try:
            bullish_scores = []
            bearish_scores = []
            
            # Score bullish liquidity (support zones where buy stops were clustered)
            for zone in liquidity_zones['bullish']:
                distance = abs(current_price - zone['level']) / current_price
                proximity_score = max(0, 100 - (distance * 200))
                strength_weighted = proximity_score * (zone['strength'] / 10)  # Normalize strength
                
                # Major bonus for swept zones (smart money already took liquidity)
                if zone['swept']:
                    strength_weighted *= 2.0  # Higher multiplier for order flow analysis
                
                if current_price > zone['level']:  # Price above support liquidity
                    bullish_scores.append(strength_weighted)
            
            # Score bearish liquidity (resistance zones where sell stops were clustered)
            for zone in liquidity_zones['bearish']:
                distance = abs(current_price - zone['level']) / current_price
                proximity_score = max(0, 100 - (distance * 200))
                strength_weighted = proximity_score * (zone['strength'] / 10)
                
                # Major bonus for swept zones (smart money already took liquidity)
                if zone['swept']:
                    strength_weighted *= 2.0  # Higher multiplier for order flow analysis
                
                if current_price < zone['level']:  # Price below resistance liquidity
                    bearish_scores.append(strength_weighted)
            
            # Calculate final score with order flow bias
            max_bullish = max(bullish_scores) if bullish_scores else 0
            max_bearish = max(bearish_scores) if bearish_scores else 0
            
            if max_bullish > max_bearish:
                # Bullish order flow - smart money likely buying
                return 50 + min(max_bullish * 0.4, 50)  # Stronger signal for order flow
            elif max_bearish > max_bullish:
                # Bearish order flow - smart money likely selling
                return 50 - min(max_bearish * 0.4, 50)  # Stronger signal for order flow
            else:
                return 50.0
            
        except Exception as e:
            self.logger.error(f"Error scoring liquidity proximity: {str(e)}")
            return 50.0

    def _apply_divergence_bonuses(self, component_scores: Dict[str, float], divergences: Dict[str, Any]) -> Dict[str, float]:
        """Apply divergence bonuses to component scores.
        
        Args:
            component_scores: Dictionary of component scores
            divergences: Dictionary of detected divergences
            
        Returns:
            Dict[str, float]: Adjusted component scores with divergence bonuses applied
        """
        try:
            # Create a copy of the original scores to avoid modifying the original
            adjusted_scores = component_scores.copy()
            
            # Initialize divergence adjustments tracking
            self._divergence_adjustments = {comp: 0.0 for comp in component_scores}
            
            # Apply price-CVD divergence bonuses
            price_cvd_divergence = divergences.get('price_cvd', {})
            if price_cvd_divergence.get('type') != 'neutral':
                divergence_strength = price_cvd_divergence.get('strength', 0.0)
                divergence_type = price_cvd_divergence.get('type', 'neutral')
                
                # Apply bonus/penalty based on divergence type and strength
                if divergence_type == 'bullish':
                    # Bullish divergence: price down but CVD up - potential reversal
                    bonus = (divergence_strength / 100) * self.divergence_impact * 15  # Max 3 point bonus
                    adjusted_scores['cvd'] = min(100, adjusted_scores.get('cvd', 50) + bonus)
                    self._divergence_adjustments['cvd'] += bonus
                    self.logger.debug(f"Applied bullish CVD divergence bonus: +{bonus:.2f} points")
                elif divergence_type == 'bearish':
                    # Bearish divergence: price up but CVD down - potential reversal
                    penalty = (divergence_strength / 100) * self.divergence_impact * 15  # Max 3 point penalty
                    adjusted_scores['cvd'] = max(0, adjusted_scores.get('cvd', 50) - penalty)
                    self._divergence_adjustments['cvd'] -= penalty
                    self.logger.debug(f"Applied bearish CVD divergence penalty: -{penalty:.2f} points")
            
            # Apply price-OI divergence bonuses
            price_oi_divergence = divergences.get('price_oi', {})
            if price_oi_divergence.get('type') != 'neutral':
                divergence_strength = price_oi_divergence.get('strength', 0.0)
                divergence_type = price_oi_divergence.get('type', 'neutral')
                
                # Apply bonus/penalty based on divergence type and strength
                if divergence_type == 'bullish':
                    # Bullish divergence: price down but OI up - potential reversal
                    bonus = (divergence_strength / 100) * self.divergence_impact * 15  # Max 3 point bonus
                    adjusted_scores['open_interest_score'] = min(100, adjusted_scores.get('open_interest_score', 50) + bonus)
                    self._divergence_adjustments['open_interest_score'] += bonus
                    self.logger.debug(f"Applied bullish OI divergence bonus: +{bonus:.2f} points")
                elif divergence_type == 'bearish':
                    # Bearish divergence: price up but OI down - potential reversal
                    penalty = (divergence_strength / 100) * self.divergence_impact * 15  # Max 3 point penalty
                    adjusted_scores['open_interest_score'] = max(0, adjusted_scores.get('open_interest_score', 50) - penalty)
                    self._divergence_adjustments['open_interest_score'] -= penalty
                    self.logger.debug(f"Applied bearish OI divergence penalty: -{penalty:.2f} points")
            
            # Apply timeframe divergence bonuses
            timeframe_divergences = divergences.get('timeframe', {})
            if timeframe_divergences:
                for tf, tf_divergence in timeframe_divergences.items():
                    if tf_divergence.get('type') != 'neutral':
                        divergence_strength = tf_divergence.get('strength', 0.0)
                        divergence_type = tf_divergence.get('type', 'neutral')
                        
                        # Apply smaller bonus/penalty for timeframe divergences
                        if divergence_type == 'bullish':
                            bonus = (divergence_strength / 100) * self.divergence_impact * 10  # Max 2 point bonus
                            # Apply to multiple components for timeframe divergences
                            for component in ['cvd', 'trade_flow_score', 'imbalance_score']:
                                if component in adjusted_scores:
                                    component_bonus = bonus * 0.5
                                    adjusted_scores[component] = min(100, adjusted_scores[component] + component_bonus)
                                    self._divergence_adjustments[component] += component_bonus
                            self.logger.debug(f"Applied bullish {tf} timeframe divergence bonus: +{bonus:.2f} points")
                        elif divergence_type == 'bearish':
                            penalty = (divergence_strength / 100) * self.divergence_impact * 10  # Max 2 point penalty
                            # Apply to multiple components for timeframe divergences
                            for component in ['cvd', 'trade_flow_score', 'imbalance_score']:
                                if component in adjusted_scores:
                                    component_penalty = penalty * 0.5
                                    adjusted_scores[component] = max(0, adjusted_scores[component] - component_penalty)
                                    self._divergence_adjustments[component] -= component_penalty
                            self.logger.debug(f"Applied bearish {tf} timeframe divergence penalty: -{penalty:.2f} points")
            
            # Ensure all scores are within valid range
            for component in adjusted_scores:
                adjusted_scores[component] = max(0, min(100, adjusted_scores[component]))
            
            return adjusted_scores
            
        except Exception as e:
            self.logger.error(f"Error applying divergence bonuses: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Return original scores if error occurs
            return component_scores

    def _analyze_timeframe_divergence(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze divergences across different timeframes.
        
        Args:
            ohlcv_data: Dictionary containing OHLCV data for different timeframes
            
        Returns:
            Dict[str, Any]: Dictionary of timeframe divergences
        """
        try:
            divergences = {}
            
            if not ohlcv_data or len(ohlcv_data) < 2:
                self.logger.debug("Insufficient timeframe data for divergence analysis")
                return divergences
                
            # Available timeframes
            timeframes = ['base', 'ltf', 'mtf', 'htf']
            available_timeframes = [tf for tf in timeframes if tf in ohlcv_data]
            
            if len(available_timeframes) < 2:
                self.logger.debug("Need at least 2 timeframes for divergence analysis")
                return divergences
                
            # Compare adjacent timeframes
            for i in range(len(available_timeframes) - 1):
                tf1 = available_timeframes[i]
                tf2 = available_timeframes[i + 1]
                
                # Get data for both timeframes
                tf1_data = ohlcv_data[tf1]
                tf2_data = ohlcv_data[tf2]
                
                # Handle nested data structure
                if isinstance(tf1_data, dict) and 'data' in tf1_data:
                    tf1_data = tf1_data['data']
                if isinstance(tf2_data, dict) and 'data' in tf2_data:
                    tf2_data = tf2_data['data']
                    
                # Skip if data is not valid DataFrame
                if not isinstance(tf1_data, pd.DataFrame) or not isinstance(tf2_data, pd.DataFrame):
                    continue
                    
                if tf1_data.empty or tf2_data.empty:
                    continue
                    
                # Calculate price trends for both timeframes
                tf1_trend = self._calculate_price_trend(tf1_data)
                tf2_trend = self._calculate_price_trend(tf2_data)
                
                # Check for divergence
                divergence = self._detect_timeframe_divergence(tf1_trend, tf2_trend, tf1, tf2)
                
                if divergence['type'] != 'neutral':
                    divergences[f"{tf1}_{tf2}"] = divergence
                    
            return divergences
            
        except Exception as e:
            self.logger.error(f"Error analyzing timeframe divergences: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {}

    def _calculate_price_trend(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate price trend from OHLCV data.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Dict containing trend information
        """
        try:
            if df.empty or len(df) < 2:
                return {'trend': 0.0, 'strength': 0.0}
                
            # Calculate simple trend using close prices
            lookback = min(len(df), 20)  # Use last 20 candles
            recent_data = df.tail(lookback)
            
            # Calculate trend slope
            close_prices = recent_data['close'].values
            x = np.arange(len(close_prices))
            
            # Linear regression to find trend
            if len(close_prices) >= 2:
                slope, intercept = np.polyfit(x, close_prices, 1)
                
                # Normalize slope relative to price
                current_price = close_prices[-1]
                normalized_slope = (slope / current_price) * 100 if current_price > 0 else 0
                
                # Calculate trend strength (R-squared)
                y_pred = slope * x + intercept
                ss_res = np.sum((close_prices - y_pred) ** 2)
                ss_tot = np.sum((close_prices - np.mean(close_prices)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                return {
                    'trend': float(normalized_slope),
                    'strength': float(max(0, min(1, r_squared)))
                }
            else:
                return {'trend': 0.0, 'strength': 0.0}
                
        except Exception as e:
            self.logger.error(f"Error calculating price trend: {str(e)}")
            return {'trend': 0.0, 'strength': 0.0}

    def _detect_timeframe_divergence(self, tf1_trend: Dict[str, float], tf2_trend: Dict[str, float], 
                                   tf1_name: str, tf2_name: str) -> Dict[str, Any]:
        """Detect divergence between two timeframes.
        
        Args:
            tf1_trend: Trend data for first timeframe
            tf2_trend: Trend data for second timeframe
            tf1_name: Name of first timeframe
            tf2_name: Name of second timeframe
            
        Returns:
            Dict containing divergence information
        """
        try:
            tf1_direction = tf1_trend['trend']
            tf2_direction = tf2_trend['trend']
            
            # Define thresholds for significant trends
            trend_threshold = 0.1  # 0.1% trend threshold
            
            # Check for divergence
            if tf1_direction > trend_threshold and tf2_direction < -trend_threshold:
                # TF1 bullish, TF2 bearish - potential bearish divergence
                strength = min(abs(tf1_direction) + abs(tf2_direction), 100)
                return {
                    'type': 'bearish',
                    'strength': strength,
                    'tf1': tf1_name,
                    'tf2': tf2_name,
                    'tf1_trend': tf1_direction,
                    'tf2_trend': tf2_direction
                }
            elif tf1_direction < -trend_threshold and tf2_direction > trend_threshold:
                # TF1 bearish, TF2 bullish - potential bullish divergence
                strength = min(abs(tf1_direction) + abs(tf2_direction), 100)
                return {
                    'type': 'bullish',
                    'strength': strength,
                    'tf1': tf1_name,
                    'tf2': tf2_name,
                    'tf1_trend': tf1_direction,
                    'tf2_trend': tf2_direction
                }
            else:
                # No significant divergence
                return {
                    'type': 'neutral',
                    'strength': 0.0,
                    'tf1': tf1_name,
                    'tf2': tf2_name,
                    'tf1_trend': tf1_direction,
                    'tf2_trend': tf2_direction
                }
                
        except Exception as e:
            self.logger.error(f"Error detecting timeframe divergence: {str(e)}")
            return {
                'type': 'neutral',
                'strength': 0.0,
                'tf1': tf1_name if 'tf1_name' in locals() else None,
                'tf2': tf2_name if 'tf2_name' in locals() else None,
                'tf1_trend': tf1_direction if 'tf1_direction' in locals() else None,
                'tf2_trend': tf2_direction if 'tf2_direction' in locals() else None
            }

    def _log_component_specific_alerts(self, component_scores: Dict[str, float], 
                                     alerts: List[str], indicator_name: str) -> None:
        """Log Orderflow Indicators specific alerts."""
        # CVD alerts
        cvd_score = component_scores.get('cvd', 50)
        if cvd_score >= 75:
            alerts.append("CVD Extremely Bullish - Strong cumulative buying pressure")
        elif cvd_score <= 25:
            alerts.append("CVD Extremely Bearish - Strong cumulative selling pressure")
        
        # Trade Flow alerts
        trade_flow_score = component_scores.get('trade_flow_score', 50)
        if trade_flow_score >= 75:
            alerts.append("Trade Flow Extremely Bullish - Buy orders dominating")
        elif trade_flow_score <= 25:
            alerts.append("Trade Flow Extremely Bearish - Sell orders dominating")
        
        # Imbalance alerts
        imbalance_score = component_scores.get('imbalance_score', 50)
        if imbalance_score >= 75:
            alerts.append("Trade Imbalance Extremely Bullish - Strong temporal buying imbalance")
        elif imbalance_score <= 25:
            alerts.append("Trade Imbalance Extremely Bearish - Strong temporal selling imbalance")
        
        # Open Interest alerts
        oi_score = component_scores.get('open_interest_score', 50)
        if oi_score >= 75:
            alerts.append("Open Interest Extremely Bullish - Strong position building")
        elif oi_score <= 25:
            alerts.append("Open Interest Extremely Bearish - Strong position unwinding")
        
        # Pressure alerts
        pressure_score = component_scores.get('pressure_score', 50)
        if pressure_score >= 75:
            alerts.append("Trade Pressure Extremely Bullish - Aggressive buying activity")
        elif pressure_score <= 25:
            alerts.append("Trade Pressure Extremely Bearish - Aggressive selling activity")
        
        # Liquidity alerts
        liquidity_score = component_scores.get('liquidity_score', 50)
        if liquidity_score >= 75:
            alerts.append("Liquidity Extremely High - Deep market conditions")
        elif liquidity_score <= 25:
            alerts.append("Liquidity Extremely Low - Shallow market conditions")
        
        # Liquidity Zones alerts
        zones_score = component_scores.get('liquidity_zones', 50)
        if zones_score >= 75:
            alerts.append("Liquidity Zones Bullish - Near smart money support zones")
        elif zones_score <= 25:
            alerts.append("Liquidity Zones Bearish - Near smart money resistance zones")