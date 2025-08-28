"""Technical indicators module for market analysis.

This module provides a comprehensive set of technical analysis indicators
for analyzing market data and generating trading signals.
"""

import pandas as pd
import talib
import numpy as np
from typing import Dict, Any, Union, List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback
import time
import math

from src.utils.indicators import IndicatorUtils
from src.utils.error_handling import handle_calculation_error, handle_indicator_error, validate_input
from src.utils.performance import track_performance, track_async_performance
from src.utils.caching import cache_result, cache_async_result, generate_cache_key
from src.validation import DataValidator
from src.config.manager import ConfigManager
from .base_indicator import BaseIndicator
from .debug_template import DebugLoggingMixin
from ..core.logger import Logger
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details, log_multi_timeframe_analysis
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.core.analysis.indicator_utils import log_indicator_results as centralized_log_indicator_results

logger = logging.getLogger(__name__)

class TechnicalIndicators(BaseIndicator, DebugLoggingMixin):
    """Technical analysis indicators for market analysis.
    
    This class implements various technical analysis indicators and methods
    for analyzing market momentum, trends and generating trading signals.
    
    Enhanced with comprehensive debug logging following OrderbookIndicators model.
    """
    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        # Set required attributes before calling super().__init__
        self.indicator_type = 'technical'
        
        # Default component weights
        default_weights = {
            'rsi': 0.20,
            'ao': 0.20,
            'macd': 0.15,
            'williams_r': 0.15,
            'atr': 0.15,
            'cci': 0.15
        }
        
        # **** IMPORTANT: Must set component_weights BEFORE calling super().__init__ ****
        # Initialize component weights dictionary with defaults
        self.component_weights = default_weights.copy()
        
        # Now call super().__init__
        super().__init__(config, logger)
        
        # Get technical specific config
        technical_config = config.get('analysis', {}).get('indicators', {}).get('technical', {})
        
        # Read component weights from config if available
        components_config = technical_config.get('components', {})
        
        # Try to get weights from confluence section first (most accurate)
        confluence_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('technical', {})
        
        # Override defaults with weights from config
        for component, default_weight in default_weights.items():
            # First try to get from confluence configuration (most reliable source)
            if confluence_weights and component in confluence_weights:
                self.component_weights[component] = confluence_weights[component]
            # Then try from component config 
            elif component in components_config:
                self.component_weights[component] = components_config.get(component, {}).get('weight', default_weight)
        
        # Normalize weights to ensure they sum to 1.0
        weight_sum = sum(self.component_weights.values())
        if weight_sum != 0:
            for component in self.component_weights:
                self.component_weights[component] /= weight_sum
        
        # Get timeframe config
        self.timeframe_weights = {
            tf: self.config['timeframes'][tf]['weight']
            for tf in ['base', 'ltf', 'mtf', 'htf']
        }
        
        # Normalize weights
        total_weight = sum(self.timeframe_weights.values())
        if total_weight == 0:
            raise ValueError("All timeframe weights are zero")
        self.timeframe_weights = {k: v/total_weight for k,v in self.timeframe_weights.items()}
        
        # Timeframe mapping from config
        self.timeframe_map = {
            tf: str(self.config['timeframes'][tf]['interval'])
            for tf in ['base', 'ltf', 'mtf', 'htf']
        }
        
        # Initialize indicator-specific parameters
        self.rsi_period = 14
        self.macd_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        }
        self.ao_fast = 5
        self.ao_slow = 34
        self.williams_period = 14
        self.atr_period = 14
        self.cci_period = 20
        
        # Divergence settings
        self.divergence_impact = 0.2  # Maximum impact of divergence on final score
        self.divergence_lookback = 14  # Periods to look back for divergence

    @property
    def required_data(self) -> List[str]:
        """Required data fields for technical analysis."""
        return ['ohlcv']

    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate technical indicators and derive a composite score with comprehensive debug logging.
        
        Args:
            market_data: Dictionary containing OHLCV data for different timeframes
            
        Returns:
            Dictionary with technical score components and overall score
        """
        start_time = time.time()
        
        try:
            symbol = market_data.get('symbol', '')
            self.logger.info(f"\n=== TECHNICAL INDICATORS Detailed Calculation ===")
            self.logger.info(f"Symbol: {symbol}")
            
            # 1. Log data quality metrics
            self._log_data_quality_metrics(market_data)
            
            # Extract OHLCV data
            base_ohlcv = market_data.get('ohlcv', {}).get('base')
            ltf_ohlcv = market_data.get('ohlcv', {}).get('ltf')
            mtf_ohlcv = market_data.get('ohlcv', {}).get('mtf')
            htf_ohlcv = market_data.get('ohlcv', {}).get('htf')
            
            # 2. Enhanced data validation logging
            self._log_calculation_step("OHLCV Data Extraction", {
                "base_timeframe_length": len(base_ohlcv) if base_ohlcv is not None else 0,
                "ltf_timeframe_length": len(ltf_ohlcv) if ltf_ohlcv is not None else 0,
                "mtf_timeframe_length": len(mtf_ohlcv) if mtf_ohlcv is not None else 0,
                "htf_timeframe_length": len(htf_ohlcv) if htf_ohlcv is not None else 0,
                "total_timeframes": sum(1 for tf in [base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv] if tf is not None)
            })
            
            # Validate input data
            validation_result = self._validate_input(base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv)
            if not validation_result.get('valid', False):
                self.logger.error(f"Technical indicators validation failed: {validation_result.get('reason', 'Unknown reason')}")
                return {
                    'score': 50.0, 
                    'components': {}, 
                    'signals': {},
                    'metadata': {
                        'timestamp': int(time.time() * 1000),
                        'status': 'ERROR',
                        'error': validation_result.get('reason', 'Unknown reason')
                    },
                    'valid': False
                }
            
            self.logger.info("✓ Data validation passed successfully")
            
            # Calculate main indicator values
            indicators_data = self._calculate_indicator_values(base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv)
            
            # Calculate component scores for each timeframe
            timeframe_scores = {}
            
            # Base timeframe (1-minute)
            base_scores = {
                'rsi': self._calculate_rsi_score(base_ohlcv, 'base'),
                'macd': self._calculate_macd_score(base_ohlcv, 'base'),
                'ao': self._calculate_ao_score(base_ohlcv, 'base'),
                'williams_r': self._calculate_williams_r_score(base_ohlcv, 'base'),
                'atr': self._calculate_atr_score(base_ohlcv, 'base'),
                'cci': self._calculate_cci_score(base_ohlcv, 'base')
            }
            timeframe_scores['base'] = base_scores
            
            # Lower timeframe (5-minute)
            ltf_scores = {
                'rsi': self._calculate_rsi_score(ltf_ohlcv, 'ltf'),
                'macd': self._calculate_macd_score(ltf_ohlcv, 'ltf'),
                'ao': self._calculate_ao_score(ltf_ohlcv, 'ltf'),
                'williams_r': self._calculate_williams_r_score(ltf_ohlcv, 'ltf'),
                'atr': self._calculate_atr_score(ltf_ohlcv, 'ltf'),
                'cci': self._calculate_cci_score(ltf_ohlcv, 'ltf')
            }
            timeframe_scores['ltf'] = ltf_scores
            
            # Medium timeframe (30-minute)
            mtf_scores = {
                'rsi': self._calculate_rsi_score(mtf_ohlcv, 'mtf'),
                'macd': self._calculate_macd_score(mtf_ohlcv, 'mtf'),
                'ao': self._calculate_ao_score(mtf_ohlcv, 'mtf'),
                'williams_r': self._calculate_williams_r_score(mtf_ohlcv, 'mtf'),
                'atr': self._calculate_atr_score(mtf_ohlcv, 'mtf'),
                'cci': self._calculate_cci_score(mtf_ohlcv, 'mtf')
            }
            timeframe_scores['mtf'] = mtf_scores
            
            # Higher timeframe (4-hour)
            htf_scores = {
                'rsi': self._calculate_rsi_score(htf_ohlcv, 'htf'),
                'macd': self._calculate_macd_score(htf_ohlcv, 'htf'),
                'ao': self._calculate_ao_score(htf_ohlcv, 'htf'),
                'williams_r': self._calculate_williams_r_score(htf_ohlcv, 'htf'),
                'atr': self._calculate_atr_score(htf_ohlcv, 'htf'),
                'cci': self._calculate_cci_score(htf_ohlcv, 'htf')
            }
            timeframe_scores['htf'] = htf_scores
            
            # Analyze divergences between timeframes using indicator data
            # First visualize the data (this also handles NaN values properly)
            viz_data = self._visualize_timeframe_divergence(base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv, indicators_data)
            
            # Then analyze the divergences
            divergence_data = self._analyze_timeframe_divergences(base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv, indicators_data, viz_data)
            
            # Calculate final component scores with weighted average across timeframes
            component_scores = self._calculate_component_scores(timeframe_scores)
            
            # Apply divergence bonuses/penalties
            adjusted_component_scores = self._apply_divergence_adjustments(component_scores, divergence_data)
            
            # Calculate final technical score
            valid_scores = [val for val in adjusted_component_scores.values() if not pd.isna(val)]
            total_score = sum(valid_scores)
            average_score = total_score / len(valid_scores) if valid_scores else 50.0
            
            # Replace any NaN values with 50.0 (neutral) to avoid display issues
            for component in adjusted_component_scores:
                if pd.isna(adjusted_component_scores[component]):
                    adjusted_component_scores[component] = 50.0
            
            # 3. Calculate component timing (mock timing for existing components)
            component_times = {}
            for component in adjusted_component_scores:
                # Mock timing based on component complexity
                if component == 'macd':
                    component_times[component] = 15.0  # MACD is more complex
                elif component == 'rsi':
                    component_times[component] = 10.0  # RSI is simpler
                else:
                    component_times[component] = 12.0  # Default timing
            
            # 4. Log performance metrics
            total_time = (time.time() - start_time) * 1000
            self._log_performance_metrics(component_times, total_time)
            
            # 5. Log the results with enhanced formatting
            symbol = market_data.get('symbol', '')
            centralized_log_indicator_results(
                logger=self.logger,
                indicator_name="Technical",
                final_score=average_score,
                component_scores=adjusted_component_scores,
                weights=self.component_weights,
                symbol=symbol,
                divergence_adjustments=divergence_data.get('score_adjustments')
            )
            
            # 6. Add enhanced trading context logging
            self._log_trading_context(average_score, adjusted_component_scores, symbol, "Technical")
            
            # Create signals
            signals = {}
            # Add bullish/bearish signals based on score
            if average_score >= 70:
                signals['trend'] = 'bullish'
                signals['strength'] = (average_score - 50) / 50  # 0.4 to 1.0
            elif average_score <= 30:
                signals['trend'] = 'bearish'
                signals['strength'] = (50 - average_score) / 50  # 0.4 to 1.0
            else:
                signals['trend'] = 'neutral'
                signals['strength'] = 0.0
                
            # Add divergence signals if any
            if divergence_data['bullish']:
                signals['divergences_bullish'] = divergence_data['bullish']
            if divergence_data['bearish']:
                signals['divergences_bearish'] = divergence_data['bearish']
                
            # Create metadata
            metadata = {
                'timestamp': int(time.time() * 1000),
                'status': 'SUCCESS',
                'timeframes_analyzed': list(timeframe_scores.keys()),
                'calculation_time_ms': total_time,
                'component_times_ms': component_times,
                'raw_values': indicators_data
            }
            
            # Generate interpretation using centralized interpreter
            try:
                interpreter = InterpretationGenerator()
                interpretation_data = {
                    'score': average_score,
                    'components': adjusted_component_scores,
                    'signals': signals,
                    'metadata': metadata
                }
                interpretation = interpreter._interpret_technical(interpretation_data)
            except Exception as e:
                self.logger.error(f"Error generating technical interpretation: {str(e)}")
                # Fallback interpretation
                if average_score > 65:
                    interpretation = f"Strong bullish technical indicators (score: {average_score:.1f})"
                elif average_score < 35:
                    interpretation = f"Strong bearish technical indicators (score: {average_score:.1f})"
                else:
                    interpretation = f"Neutral technical conditions (score: {average_score:.1f})"
            
            return {
                'score': average_score,
                'components': adjusted_component_scores,
                'timeframe_scores': timeframe_scores,
                'divergences': divergence_data,
                'raw_data': indicators_data,
                'signals': signals,
                'interpretation': interpretation,
                'metadata': metadata,
                'valid': True
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                'score': 50.0, 
                'components': {}, 
                'signals': {},
                'metadata': {
                    'timestamp': int(time.time() * 1000),
                    'status': 'ERROR',
                    'error': str(e)
                },
                'valid': False
            }

    def _analyze_timeframe_divergences(self, base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv, indicators_data, viz_data=None):
        """
        Analyze divergences between timeframes using indicator data.
        
        Args:
            base_ohlcv: Base timeframe data
            ltf_ohlcv: Lower timeframe data
            mtf_ohlcv: Medium timeframe data 
            htf_ohlcv: Higher timeframe data
            indicators_data: Dict containing all calculated indicator values
            viz_data: Optional DataFrame containing visualization data with NaN values handled
        
        Returns:
            Dictionary with divergence information
        """
        try:
            divergences = {
                'bullish': [],
                'bearish': [],
                'score_adjustments': {}
            }
            
            # If viz_data is None or doesn't have the expected structure, use a safer approach
            if viz_data is None or not isinstance(viz_data, pd.DataFrame) or viz_data.empty:
                self.logger.debug("No valid visualization data available for divergence analysis")
                return divergences
                
            # Helper function to safely get indicator value
            def safe_get_value(tf, indicator):
                try:
                    if tf in viz_data.index and indicator in viz_data.columns:
                        val = viz_data.loc[tf, indicator]
                        return None if pd.isna(val) else val
                    return None
                except Exception as e:
                    self.logger.debug(f"Error accessing {indicator} for {tf} timeframe: {str(e)}")
                    return None
            
            # Compare 1m to other timeframes for divergences
            # MACD divergence analysis
            try:
                # Get base timeframe MACD values
                base_macd = safe_get_value('base', 'MACD')
                ltf_macd = safe_get_value('ltf', 'MACD')
                
                # If we have valid values for both timeframes
                if base_macd is not None and ltf_macd is not None:
                    # Bullish divergence: base negative, ltf positive
                    if base_macd < 0 and ltf_macd > 0:
                        divergences['bullish'].append(f"MACD: 1m negative ({base_macd:.6f}), 5m positive ({ltf_macd:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['macd'] = 10.0  # Bullish bonus
                        
                    # Bearish divergence: base positive, ltf negative    
                    elif base_macd > 0 and ltf_macd < 0:
                        divergences['bearish'].append(f"MACD: 1m positive ({base_macd:.6f}), 5m negative ({ltf_macd:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['macd'] = -10.0  # Bearish penalty
                        
            except Exception as e:
                self.logger.debug(f"Could not calculate MACD divergence: {str(e)}")
            
            # Awesome Oscillator divergence analysis
            try:
                # Get base timeframe and other timeframe AO values
                base_ao = safe_get_value('base', 'AO')
                ltf_ao = safe_get_value('ltf', 'AO')
                
                # If we have valid values for both timeframes
                if base_ao is not None and ltf_ao is not None:
                    # Bullish divergence: base negative, ltf positive
                    if base_ao < 0 and ltf_ao > 0:
                        divergences['bullish'].append(f"AO: 1m negative ({base_ao:.6f}), 5m positive ({ltf_ao:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['ao'] = 10.0  # Bullish bonus
                        
                    # Bearish divergence: base positive, ltf negative    
                    elif base_ao > 0 and ltf_ao < 0:
                        divergences['bearish'].append(f"AO: 1m positive ({base_ao:.6f}), 5m negative ({ltf_ao:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['ao'] = -10.0  # Bearish penalty
                        
            except Exception as e:
                self.logger.debug(f"Could not calculate AO divergence: {str(e)}")
            
            # Williams %R divergence analysis
            try:
                # Get base timeframe and other timeframe Williams %R values
                base_williams_r = safe_get_value('base', 'Williams %R')
                ltf_williams_r = safe_get_value('ltf', 'Williams %R')
                
                # If we have valid values for both timeframes
                if base_williams_r is not None and ltf_williams_r is not None:
                    # Using an arbitrary threshold to determine divergence 
                    # (Williams %R ranges from -100 to 0)
                    williams_r_threshold = -50
                    
                    # Bullish divergence: base below threshold, ltf above threshold
                    if base_williams_r < williams_r_threshold and ltf_williams_r > williams_r_threshold:
                        divergences['bullish'].append(f"Williams %R: 1m oversold ({base_williams_r:.6f}), 5m overbought ({ltf_williams_r:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['williams_r'] = 10.0  # Bullish bonus
                        
                    # Bearish divergence: base above threshold, ltf below threshold
                    elif base_williams_r > williams_r_threshold and ltf_williams_r < williams_r_threshold:
                        divergences['bearish'].append(f"Williams %R: 1m overbought ({base_williams_r:.6f}), 5m oversold ({ltf_williams_r:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['williams_r'] = -10.0  # Bearish penalty
                        
            except Exception as e:
                self.logger.debug(f"Could not calculate Williams %R divergence: {str(e)}")
            
            # ATR divergence analysis
            try:
                # Get base timeframe and other timeframe ATR values
                base_atr = safe_get_value('base', 'ATR')
                ltf_atr = safe_get_value('ltf', 'ATR')
                
                # If we have valid values for both timeframes
                if base_atr is not None and ltf_atr is not None:
                    # For ATR, we're looking at relative volatility between timeframes
                    if base_atr > 0 and ltf_atr > 0:
                        # Calculate the ratio of base ATR to LTF ATR
                        atr_ratio = base_atr / ltf_atr if ltf_atr != 0 else 0
                        
                        # High short-term volatility compared to medium-term (might signal reversal)
                        if atr_ratio > 1.5:
                            divergences['bullish'].append(f"ATR: 1m volatility ({base_atr:.6f}) significantly higher than 5m ({ltf_atr:.6f})")
                            # Add score adjustment
                            divergences['score_adjustments']['atr'] = 5.0  # Small bullish bonus
                        
                        # Low short-term volatility compared to medium-term (might signal continuation)
                        elif atr_ratio < 0.5:
                            divergences['bearish'].append(f"ATR: 1m volatility ({base_atr:.6f}) significantly lower than 5m ({ltf_atr:.6f})")
                            # Add score adjustment
                            divergences['score_adjustments']['atr'] = -5.0  # Small bearish penalty
                            
            except Exception as e:
                self.logger.debug(f"Could not calculate ATR divergence: {str(e)}")
            
            # CCI divergence analysis
            try:
                # Get base timeframe and other timeframe CCI values
                base_cci = safe_get_value('base', 'CCI')
                ltf_cci = safe_get_value('ltf', 'CCI')
                
                # If we have valid values for both timeframes
                if base_cci is not None and ltf_cci is not None:
                    # CCI values above 100 indicate overbought, below -100 indicate oversold
                    
                    # Bullish divergence: base oversold, ltf not oversold
                    if base_cci < -100 and ltf_cci > -100:
                        divergences['bullish'].append(f"CCI: 1m oversold ({base_cci:.6f}), 5m not oversold ({ltf_cci:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['cci'] = 10.0  # Bullish bonus
                        
                    # Bearish divergence: base overbought, ltf not overbought
                    elif base_cci > 100 and ltf_cci < 100:
                        divergences['bearish'].append(f"CCI: 1m overbought ({base_cci:.6f}), 5m not overbought ({ltf_cci:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['cci'] = -10.0  # Bearish penalty
            except Exception as e:
                self.logger.debug(f"Could not calculate CCI divergence: {str(e)}")
            
            # RSI divergence analysis
            try:
                # Get base timeframe and other timeframe RSI values
                base_rsi = safe_get_value('base', 'RSI')
                ltf_rsi = safe_get_value('ltf', 'RSI')
                
                # If we have valid values for both timeframes
                if base_rsi is not None and ltf_rsi is not None:
                    # RSI values above 70 indicate overbought, below 30 indicate oversold
                    
                    # Bullish divergence: base oversold, ltf not oversold
                    if base_rsi < 30 and ltf_rsi > 30:
                        divergences['bullish'].append(f"RSI: 1m oversold ({base_rsi:.6f}), 5m not oversold ({ltf_rsi:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['rsi'] = 10.0  # Bullish bonus
                        
                    # Bearish divergence: base overbought, ltf not overbought
                    elif base_rsi > 70 and ltf_rsi < 70:
                        divergences['bearish'].append(f"RSI: 1m overbought ({base_rsi:.6f}), 5m not overbought ({ltf_rsi:.6f})")
                        # Add score adjustment
                        divergences['score_adjustments']['rsi'] = -10.0  # Bearish penalty
            except Exception as e:
                self.logger.debug(f"Could not calculate RSI divergence: {str(e)}")
            
            # Log the divergences
            if divergences['bullish']:
                self.logger.info(f"Detected {len(divergences['bullish'])} bullish divergences: {divergences['bullish']}")
            if divergences['bearish']:
                self.logger.info(f"Detected {len(divergences['bearish'])} bearish divergences: {divergences['bearish']}")
            
            # Log divergence analysis results
            self.logger.info("\nDivergence Analysis:")
            self.logger.info(f"- Bullish Divergences: {len(divergences['bullish'])}")
            self.logger.info(f"- Bearish Divergences: {len(divergences['bearish'])}")
            self.logger.info(f"- Score Adjustments: {divergences['score_adjustments']}")
            
            return divergences
            
        except Exception as e:
            self.logger.error(f"Error analyzing timeframe divergences: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                'bullish': [],
                'bearish': [],
                'score_adjustments': {}
            }

    def _calculate_component_scores(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate component scores from timeframe scores.
        
        Args:
            data: Dictionary with timeframe scores, where keys are timeframe names
                and values are dictionaries of indicator scores for that timeframe
                
        Returns:
            Dictionary with final component scores combined across timeframes
        """
        try:
            # Initialize component scores
            component_scores = {comp: 0.0 for comp in self.component_weights}
            
            # If data is empty or invalid, return default scores
            if not data or not isinstance(data, dict):
                self.logger.warning("Invalid timeframe scores provided")
                return component_scores
            
            # Track how many valid timeframes we process
            valid_timeframes = 0
            
            # Process scores for each timeframe
            for tf_name, tf_scores in data.items():
                # Ensure we have a valid timeframe weight
                if tf_name not in self.timeframe_weights:
                    self.logger.warning(f"Missing weight for timeframe: {tf_name}")
                    continue
                
                tf_weight = self.timeframe_weights[tf_name]
                
                # Skip if no scores for this timeframe
                if not isinstance(tf_scores, dict) or not tf_scores:
                    self.logger.warning(f"Invalid scores for timeframe: {tf_name}")
                    continue
                
                # Add weighted contribution to component scores
                for component, score in tf_scores.items():
                    if component in component_scores:
                        component_scores[component] += score * tf_weight
                
                valid_timeframes += 1
            
            # If no valid timeframes were processed, return default scores
            if valid_timeframes == 0:
                self.logger.warning("No valid timeframe scores were found")
                return {comp: 50.0 for comp in self.component_weights}
            
            # Log timeframe analysis
            self.logger.debug("\n=== Timeframe Analysis ===")
            for tf_name, tf_scores in data.items():
                if isinstance(tf_scores, dict) and tf_scores:
                    self.logger.debug(f"\n{tf_name} Timeframe Scores:")
                    for comp, score in tf_scores.items():
                        self.logger.debug(f"- {comp}: {score:.2f}")
            
            return component_scores
            
        except Exception as e:
            self.logger.error(f"Error calculating component scores: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {comp: 50.0 for comp in self.component_weights}

    def _calculate_rsi_score(self, df: pd.DataFrame, timeframe: str = 'base') -> float:
        """Calculate RSI score with comprehensive debug logging."""
        start_time = time.time()
        
        try:
            # 1. Log calculation header
            self._log_component_calculation_header(
                f"RSI ({timeframe})", 
                f"Data points: {len(df)}, Period: {self.rsi_period}"
            )
            
            # 2. Data validation with detailed logging
            self._log_calculation_step("Data Validation", {
                "input_length": len(df),
                "required_minimum": self.rsi_period + 1,
                "timeframe": timeframe,
                "has_close_column": 'close' in df.columns if not df.empty else False
            })
            
            # Check if we have enough data for RSI calculation
            if len(df) < self.rsi_period + 1:
                self.logger.warning(f"Insufficient data for RSI calculation on {timeframe} timeframe: {len(df)} < {self.rsi_period + 1}")
                return 50.0
            
            # 3. RSI calculation with detailed logging
            self._log_calculation_step("RSI Calculation", {
                "period": self.rsi_period,
                "close_price_current": float(df['close'].iloc[-1]),
                "close_price_previous": float(df['close'].iloc[-2]),
                "price_change": float(df['close'].iloc[-1] - df['close'].iloc[-2])
            })
            
            rsi = talib.RSI(df['close'], timeperiod=self.rsi_period)
            
            # Check for NaN in the result
            if pd.isna(rsi.iloc[-1]):
                self.logger.warning(f"NaN value in RSI calculation for {timeframe} timeframe")
                return 50.0
                
            current_rsi = float(rsi.iloc[-1])
            
            # 4. Log RSI interpretation analysis
            if current_rsi > 70:
                interpretation = "Overbought (bearish signal)"
                zone = "Overbought"
            elif current_rsi < 30:
                interpretation = "Oversold (bullish signal)"
                zone = "Oversold"
            else:
                interpretation = "Neutral zone"
                zone = "Neutral"
            
            self._log_interpretation_analysis(
                current_rsi, 
                interpretation,
                {
                    "Overbought": (70.0, "Bearish signal - potential reversal down"),
                    "Oversold": (30.0, "Bullish signal - potential reversal up"),
                    "Neutral": (30.0, "No clear directional bias")
                }
            )
            
            # 5. Score calculation with step-by-step logging
            if current_rsi > 70:
                # Overbought: 50 → 0 as RSI goes from 70 → 100
                raw_score = max(0, 50 - ((current_rsi - 70) / 30) * 50)
                self._log_formula_calculation(
                    "Overbought RSI Score",
                    "score = max(0, 50 - ((rsi - 70) / 30) * 50)",
                    {"rsi": current_rsi},
                    raw_score
                )
            elif current_rsi < 30:
                # Oversold: 50 → 100 as RSI goes from 30 → 0
                raw_score = min(100, 50 + ((30 - current_rsi) / 30) * 50)
                self._log_formula_calculation(
                    "Oversold RSI Score",
                    "score = min(100, 50 + ((30 - rsi) / 30) * 50)",
                    {"rsi": current_rsi},
                    raw_score
                )
            else:
                # Neutral: Linear scaling between 30-70
                raw_score = 50 + ((current_rsi - 50) / 20) * 25
                self._log_formula_calculation(
                    "Neutral RSI Score",
                    "score = 50 + ((rsi - 50) / 20) * 25",
                    {"rsi": current_rsi},
                    raw_score
                )
            
            final_score = float(np.clip(raw_score, 0, 100))
            
            # 6. Log significant events
            if current_rsi > 80 or current_rsi < 20:
                self._log_significant_event(
                    f"RSI {zone}", 
                    current_rsi, 
                    80 if current_rsi > 50 else 20,
                    f"Extreme RSI level - {interpretation}"
                )
            
            # 7. Log timing and final result
            execution_time = self._log_component_timing(f"RSI ({timeframe})", start_time)
            
            self.logger.debug(f"Final RSI score: {final_score:.2f} (RSI: {current_rsi:.2f}, Zone: {zone})")
            
            return final_score
            
        except Exception as e:
            self._log_calculation_error(f"RSI ({timeframe})", e)
            return 50.0

    def _calculate_macd_score(self, df: pd.DataFrame, timeframe: str = 'base') -> float:
        """Calculate MACD score with comprehensive debug logging."""
        start_time = time.time()
        
        try:
            # 1. Log calculation header
            self._log_component_calculation_header(
                f"MACD ({timeframe})",
                f"Data points: {len(df)}, Fast: {self.macd_params['fast_period']}, Slow: {self.macd_params['slow_period']}, Signal: {self.macd_params['signal_period']}"
            )
            
            # 2. Input validation with detailed logging
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.error("Invalid or empty DataFrame passed to _calculate_macd_score")
                return 50.0
            
            if 'close' not in df.columns:
                self.logger.error("Missing required column (close) for MACD calculation")
                return 50.0
            
            # 3. Data requirements analysis
            baseline_req = self.macd_params['slow_period'] + self.macd_params['signal_period']
            timeframe_min_points = {
                'base': max(baseline_req, 50),
                'ltf': max(int(baseline_req * 0.8), 30),   # 20% reduction for LTF
                'mtf': max(int(baseline_req * 0.7), 20),   # 30% reduction for MTF
                'htf': max(int(baseline_req * 0.5), 5)     # 50% reduction for HTF
            }
            
            min_data_points = timeframe_min_points.get(timeframe, timeframe_min_points['base'])
            actual_points = len(df)
            close_enough = actual_points >= int(min_data_points * 0.95)
            
            self._log_calculation_step("Data Requirements Analysis", {
                "baseline_requirement": baseline_req,
                "timeframe_minimum": min_data_points,
                "actual_points": actual_points,
                "close_enough_threshold": int(min_data_points * 0.95),
                "meets_requirement": actual_points >= min_data_points or close_enough
            })
            
            # Ensure we have enough data
            if actual_points < min_data_points and not close_enough:
                self.logger.warning(f"Insufficient data for MACD calculation on {timeframe} timeframe: {actual_points} < {min_data_points}")
                return 50.0
            
            # 4. MACD calculation with detailed logging
            self._log_calculation_step("MACD Calculation", {
                "fast_period": self.macd_params['fast_period'],
                "slow_period": self.macd_params['slow_period'],
                "signal_period": self.macd_params['signal_period'],
                "close_price_current": float(df['close'].iloc[-1]),
                "close_price_previous": float(df['close'].iloc[-2])
            })
            
            macd, signal, histogram = talib.MACD(
                df['close'],
                fastperiod=self.macd_params['fast_period'],
                slowperiod=self.macd_params['slow_period'],
                signalperiod=self.macd_params['signal_period']
            )
            
            # Check for NaN values
            if pd.isna(macd.iloc[-1]) or pd.isna(signal.iloc[-1]) or pd.isna(histogram.iloc[-1]):
                self.logger.warning(f"NaN values in MACD calculation for {timeframe} timeframe")
                return 50.0
            
            # 5. Current values analysis
            latest_macd = float(macd.iloc[-1])
            latest_signal = float(signal.iloc[-1])
            latest_histogram = float(histogram.iloc[-1])
            
            self._log_calculation_step("Current MACD Values", {
                "macd_line": latest_macd,
                "signal_line": latest_signal,
                "histogram": latest_histogram,
                "macd_above_signal": latest_macd > latest_signal,
                "macd_above_zero": latest_macd > 0
            })
            
            # 6. Score calculation with detailed logging
            score = 50.0
            score_adjustments = []
            
            # Calculate the strength of the MACD signal
            signal_strength = min(abs(latest_macd) * 5, 20)
            
            # Check if MACD is above or below signal line
            if latest_macd > latest_signal:
                score += signal_strength
                score_adjustments.append(f"MACD above signal: +{signal_strength:.2f}")
            else:
                score -= signal_strength
                score_adjustments.append(f"MACD below signal: -{signal_strength:.2f}")
            
            # Check histogram trend
            if len(histogram) > 5:
                recent_histogram = histogram.iloc[-5:-1]
                if not recent_histogram.empty:
                    if not all(pd.isna(val) for val in recent_histogram):
                        recent_histogram = recent_histogram.dropna()
                        
                        if len(recent_histogram) > 0:
                            avg_recent = recent_histogram.mean()
                            histogram_change = latest_histogram - avg_recent
                            
                            histogram_factor = min(abs(histogram_change) * 10, 20)
                            if histogram_change > 0:
                                score += histogram_factor
                                score_adjustments.append(f"Histogram increasing: +{histogram_factor:.2f}")
                            else:
                                score -= histogram_factor
                                score_adjustments.append(f"Histogram decreasing: -{histogram_factor:.2f}")
            
            # 7. Crossover analysis
            crossover_detected = False
            if len(macd) > 2 and len(signal) > 2:
                prev_macd = float(macd.iloc[-2])
                prev_signal = float(signal.iloc[-2])
                
                if not pd.isna(prev_macd) and not pd.isna(prev_signal):
                    # MACD crossed above signal line (bullish crossover)
                    if prev_macd < prev_signal and latest_macd > latest_signal:
                        score += 15
                        score_adjustments.append("Bullish crossover: +15.00")
                        crossover_detected = True
                        self._log_significant_event("MACD Bullish Crossover", latest_macd - latest_signal, 0.001, "MACD crossed above signal line")
                        
                    # MACD crossed below signal line (bearish crossover)
                    elif prev_macd > prev_signal and latest_macd < latest_signal:
                        score -= 15
                        score_adjustments.append("Bearish crossover: -15.00")
                        crossover_detected = True
                        self._log_significant_event("MACD Bearish Crossover", latest_signal - latest_macd, 0.001, "MACD crossed below signal line")
            
            # 8. Zero line crossover analysis
            zero_line_cross = False
            if len(macd) > 2:
                prev_macd = float(macd.iloc[-2])
                
                if not pd.isna(prev_macd):
                    # MACD crossed above zero (bullish signal)
                    if prev_macd < 0 and latest_macd > 0:
                        score += 20
                        score_adjustments.append("Zero line bullish cross: +20.00")
                        zero_line_cross = True
                        self._log_significant_event("MACD Zero Line Cross", latest_macd, 0.001, "MACD crossed above zero line (bullish)")
                        
                    # MACD crossed below zero (bearish signal)
                    elif prev_macd > 0 and latest_macd < 0:
                        score -= 20
                        score_adjustments.append("Zero line bearish cross: -20.00")
                        zero_line_cross = True
                        self._log_significant_event("MACD Zero Line Cross", abs(latest_macd), 0.001, "MACD crossed below zero line (bearish)")
            
            # 9. Log score adjustments
            self._log_calculation_step("Score Adjustments", {
                "base_score": 50.0,
                "adjustments": score_adjustments,
                "crossover_detected": crossover_detected,
                "zero_line_cross": zero_line_cross
            })
            
            # 10. Final score calculation
            final_score = float(np.clip(score, 0, 100))
            
            # 11. Interpretation
            if final_score > 70:
                interpretation = "Strong bullish momentum"
            elif final_score > 55:
                interpretation = "Moderate bullish momentum"
            elif final_score > 45:
                interpretation = "Neutral momentum"
            elif final_score > 30:
                interpretation = "Moderate bearish momentum"
            else:
                interpretation = "Strong bearish momentum"
            
            self._log_interpretation_analysis(
                final_score,
                interpretation,
                {
                    "Strong Bullish": (70.0, "Strong upward momentum"),
                    "Moderate Bullish": (55.0, "Moderate upward momentum"),
                    "Neutral": (45.0, "No clear momentum direction"),
                    "Moderate Bearish": (30.0, "Moderate downward momentum")
                }
            )
            
            # 12. Log timing and final result
            execution_time = self._log_component_timing(f"MACD ({timeframe})", start_time)
            
            self.logger.debug(f"Final MACD score: {final_score:.2f} (MACD: {latest_macd:.6f}, Signal: {latest_signal:.6f}, Histogram: {latest_histogram:.6f})")
            
            return final_score
            
        except Exception as e:
            self._log_calculation_error(f"MACD ({timeframe})", e)
            return 50.0
            return 50.0

    def _calculate_ao_score(self, df: pd.DataFrame, timeframe: str = 'base') -> float:
        """Calculate Awesome Oscillator score."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.error("Invalid or empty DataFrame passed to _calculate_ao_score")
                return 50.0
            
            if 'high' not in df.columns or 'low' not in df.columns:
                self.logger.error("Missing required columns (high or low) for AO calculation")
                return 50.0
            
            # Calculate AO manually since talib doesn't have it directly
            median_price = (df['high'] + df['low']) / 2
            
            # Need at least 34 data points for AO calculation
            if len(df) < 34:
                self.logger.debug(f"Insufficient data for AO calculation on {timeframe} timeframe: {len(df)} < 34")
                return 50.0
            
            # Calculate AO as 5-period SMA - 34-period SMA of median price
            fast_sma = talib.SMA(median_price, timeperiod=5)
            slow_sma = talib.SMA(median_price, timeperiod=34)
            ao = fast_sma - slow_sma
            
            # Check for NaN values
            if pd.isna(ao.iloc[-1]):
                self.logger.debug(f"NaN value in AO calculation for {timeframe} timeframe")
                return 50.0
            
            # Calculate score based on latest value
            latest_ao = ao.iloc[-1]
            
            # Initialize score at 50 (neutral)
            score = 50.0
            
            # Calculate the strength of the AO signal (absolute value of AO)
            signal_strength = min(abs(latest_ao) * 5, 20)
            
            # Check if AO is positive or negative
            if latest_ao > 0:
                score += signal_strength  # Bullish
            else:
                score -= signal_strength  # Bearish
            
            # Check if AO is increasing or decreasing
            # Compare current AO to recent history
            if len(ao) > 5:
                recent_ao = ao.iloc[-5:-1]
                if not recent_ao.empty:
                    if not all(pd.isna(val) for val in recent_ao):
                        recent_ao = recent_ao.dropna()
                        
                        # Only consider valid values
                        if len(recent_ao) > 0:
                            avg_recent = recent_ao.mean()
                            ao_change = latest_ao - avg_recent
                            
                            # Normalize and add to score
                            ao_factor = min(abs(ao_change) * 10, 20)
                            if ao_change > 0:
                                score += ao_factor  # Increasing AO is bullish
                            else:
                                score -= ao_factor  # Decreasing AO is bearish
            
            # Check for zero-line crossover (strongest signal)
            if len(ao) > 2:
                prev_ao = ao.iloc[-2]
                if not pd.isna(prev_ao):
                    # Bullish cross above zero
                    if prev_ao < 0 and latest_ao > 0:
                        score += 20
                        self.logger.info(f"AO crossed above zero line on {timeframe} timeframe (bullish)")
                    # Bearish cross below zero
                    elif prev_ao > 0 and latest_ao < 0:
                        score -= 20
                        self.logger.info(f"AO crossed below zero line on {timeframe} timeframe (bearish)")
            
            # Ensure score is within valid range
            final_score = max(0, min(100, score))
            
            self.logger.debug(f"AO score for {timeframe}: {final_score:.2f} (AO: {latest_ao:.6f})")
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating AO score: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 50.0

    def _calculate_williams_r_score(self, df: pd.DataFrame, timeframe: str = 'base') -> float:
        """Calculate Williams %R score."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.error("Invalid or empty DataFrame passed to _calculate_williams_r_score")
                return 50.0

            if 'high' not in df.columns or 'low' not in df.columns or 'close' not in df.columns:
                self.logger.error("Missing required columns (high, low, or close) for Williams %R calculation")
                return 50.0

            # Calculate Williams %R - note the required parameters
            williams_r = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=14)
            
            # Check for NaN values
            if pd.isna(williams_r.iloc[-1]):
                self.logger.debug(f"NaN value in Williams %R calculation for {timeframe} timeframe")
                return 50.0

            # Calculate score based on latest value
            latest_williams_r = williams_r.iloc[-1]
            
            # Williams %R ranges from -100 to 0
            # Above -20 is considered overbought (bearish)
            # Below -80 is considered oversold (bullish)
            
            # Convert to 0-100 scale (0-100 instead of -100-0)
            williams_r_score = 100 + latest_williams_r
            
            # Ensure score is within valid range
            final_score = float(np.clip(williams_r_score, 0, 100))
            
            self.logger.debug(f"Williams %R score for {timeframe}: {final_score:.2f} (Williams %R: {latest_williams_r:.6f})")
            return final_score

        except Exception as e:
            self.logger.error(f"Error calculating Williams %R score: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 50.0

    def _calculate_atr_score(self, df: pd.DataFrame, timeframe: str = 'base') -> float:
        """Calculate ATR score."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.error("Invalid or empty DataFrame passed to _calculate_atr_score")
                return 50.0
            
            if 'high' not in df.columns or 'low' not in df.columns:
                self.logger.error("Missing required columns (high or low) for ATR calculation")
                return 50.0
            
            # Calculate ATR
            atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.atr_period)
            
            # Check for NaN values
            if pd.isna(atr.iloc[-1]):
                self.logger.debug(f"NaN value in ATR calculation for {timeframe} timeframe")
                return 50.0
            
            # Calculate score based on latest value
            latest_atr = atr.iloc[-1]
            
            # Initialize score at 50 (neutral)
            score = 50.0
            
            # Calculate the strength of the ATR signal (absolute value of ATR)
            signal_strength = min(abs(latest_atr) * 5, 20)
            
            # Check if ATR is positive or negative
            if latest_atr > 0:
                score += signal_strength  # Bullish
            else:
                score -= signal_strength  # Bearish
            
            # Check if ATR is increasing or decreasing
            # Compare current ATR to recent history
            if len(atr) > 5:
                recent_atr = atr.iloc[-5:-1]
                if not recent_atr.empty:
                    if not all(pd.isna(val) for val in recent_atr):
                        recent_atr = recent_atr.dropna()
                        
                        # Only consider valid values
                        if len(recent_atr) > 0:
                            avg_recent = recent_atr.mean()
                            atr_change = latest_atr - avg_recent
                            
                            # Normalize and add to score
                            atr_factor = min(abs(atr_change) * 10, 20)
                            if atr_change > 0:
                                score += atr_factor  # Increasing ATR is bullish
                            else:
                                score -= atr_factor  # Decreasing ATR is bearish
            
            # Ensure score is within valid range
            final_score = max(0, min(100, score))
            
            self.logger.debug(f"ATR score for {timeframe}: {final_score:.2f} (ATR: {latest_atr:.6f})")
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR score: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 50.0

    def _calculate_cci_score(self, df: pd.DataFrame, timeframe: str = 'base') -> float:
        """Calculate CCI score."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.error("Invalid or empty DataFrame passed to _calculate_cci_score")
                return 50.0
            
            if 'high' not in df.columns or 'low' not in df.columns:
                self.logger.error("Missing required columns (high or low) for CCI calculation")
                return 50.0
            
            # Calculate CCI
            cci = talib.CCI(df['high'], df['low'], df['close'], timeperiod=self.cci_period)
            
            # Check for NaN values
            if pd.isna(cci.iloc[-1]):
                self.logger.debug(f"NaN value in CCI calculation for {timeframe} timeframe")
                return 50.0
            
            # Calculate score based on latest value
            latest_cci = cci.iloc[-1]
            
            # Initialize score at 50 (neutral)
            score = 50.0
            
            # Calculate the strength of the CCI signal (absolute value of CCI)
            signal_strength = min(abs(latest_cci) * 5, 20)
            
            # Check if CCI is positive or negative
            if latest_cci > 0:
                score += signal_strength  # Bullish
            else:
                score -= signal_strength  # Bearish
            
            # Check if CCI is increasing or decreasing
            # Compare current CCI to recent history
            if len(cci) > 5:
                recent_cci = cci.iloc[-5:-1]
                if not recent_cci.empty:
                    if not all(pd.isna(val) for val in recent_cci):
                        recent_cci = recent_cci.dropna()
                        
                        # Only consider valid values
                        if len(recent_cci) > 0:
                            avg_recent = recent_cci.mean()
                            cci_change = latest_cci - avg_recent
                            
                            # Normalize and add to score
                            cci_factor = min(abs(cci_change) * 10, 20)
                            if cci_change > 0:
                                score += cci_factor  # Increasing CCI is bullish
                            else:
                                score -= cci_factor  # Decreasing CCI is bearish
            
            # Ensure score is within valid range
            final_score = max(0, min(100, score))
            
            self.logger.debug(f"CCI score for {timeframe}: {final_score:.2f} (CCI: {latest_cci:.6f})")
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating CCI score: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 50.0

    def _calculate_rsi_divergence(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate RSI divergence."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError("Invalid or empty DataFrame passed to _calculate_rsi_divergence")
            
            # Calculate RSI
            rsi = talib.RSI(df['close'], timeperiod=self.rsi_period)
            
            # Check for NaN values
            if pd.isna(rsi.iloc[-1]):
                self.logger.debug("NaN value in RSI calculation")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate divergence
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            
            if current_rsi > 70 and prev_rsi <= 70:
                return {'strength': 100.0, 'type': 'bullish'}
            elif current_rsi < 30 and prev_rsi >= 30:
                return {'strength': 100.0, 'type': 'bearish'}
            else:
                return {'strength': 50.0, 'type': 'neutral'}
        
        except Exception as e:
            self.logger.error(f"Error calculating RSI divergence: {str(e)}")
            return {'strength': 50.0, 'type': 'neutral'}

    def _calculate_ao_divergence(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate AO divergence."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError("Invalid or empty DataFrame passed to _calculate_ao_divergence")
            
            # Calculate AO manually since talib doesn't have it directly
            median_price = (df['high'] + df['low']) / 2
            
            # Need at least 34 data points for AO calculation
            if len(df) < 34:
                self.logger.debug(f"Insufficient data for AO calculation: {len(df)} < 34")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate AO as 5-period SMA - 34-period SMA of median price
            fast_sma = talib.SMA(median_price, timeperiod=5)
            slow_sma = talib.SMA(median_price, timeperiod=34)
            ao = fast_sma - slow_sma
            
            # Check for NaN values
            if pd.isna(ao.iloc[-1]):
                self.logger.debug(f"NaN value in AO calculation: {len(df)}")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate divergence
            current_ao = ao.iloc[-1]
            prev_ao = ao.iloc[-2]
            
            if current_ao > 0 and prev_ao <= 0:
                return {'strength': 100.0, 'type': 'bullish'}
            elif current_ao < 0 and prev_ao >= 0:
                return {'strength': 100.0, 'type': 'bearish'}
            else:
                return {'strength': 50.0, 'type': 'neutral'}
            
        except Exception as e:
            self.logger.error(f"Error calculating AO divergence: {str(e)}")
            return {'strength': 50.0, 'type': 'neutral'}

    def _apply_divergence_adjustments(self, component_scores: Dict[str, float], divergence_data: Dict[str, Any]) -> Dict[str, float]:
        """Apply divergence adjustments to component scores."""
        try:
            # For empty or None input, return default scores
            if not component_scores:
                return {comp: 50.0 for comp in self.component_weights}

            adjusted_scores = {}
            
            for comp, score in component_scores.items():
                # Handle NaN values by using 50.0 as base
                if pd.isna(score):
                    base_score = 50.0
                else:
                    base_score = score
                    
                # Apply adjustment if available
                if comp in divergence_data['score_adjustments']:
                    adjustment = divergence_data['score_adjustments'][comp]
                    adjusted_scores[comp] = np.clip(base_score + adjustment, 0, 100)
                else:
                    adjusted_scores[comp] = base_score
            
            return adjusted_scores
            
        except Exception as e:
            self.logger.error(f"Error applying divergence adjustments: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {comp: 50.0 for comp in self.component_weights}

    def _validate_input(self, *args) -> Dict[str, Any]:
        """
        Validate the input OHLCV data for technical analysis with improved logging.
        
        Args:
            Either:
                - market_data: Dictionary containing 'ohlcv' data with timeframes
            Or:
                - base_ohlcv: Base timeframe DataFrame
                - ltf_ohlcv: Lower timeframe DataFrame
                - mtf_ohlcv: Medium timeframe DataFrame
                - htf_ohlcv: Higher timeframe DataFrame
            
        Returns:
            Dictionary with validation result and reason if failed
        """
        try:
            # Define validation result structure
            result = {
                'valid': True,
                'reason': None
            }
            
            # Handle different input types for backward compatibility
            if len(args) == 1 and isinstance(args[0], dict):
                # Called with market_data dictionary
                market_data = args[0]
                if 'ohlcv' not in market_data:
                    result['valid'] = False
                    result['reason'] = "Missing 'ohlcv' key in market data"
                    self.logger.error(result['reason'])
                    return result
                
                ohlcv_data = market_data.get('ohlcv', {})
                timeframes = {
                    'base': ohlcv_data.get('base'),
                    'ltf': ohlcv_data.get('ltf'),
                    'mtf': ohlcv_data.get('mtf'),
                    'htf': ohlcv_data.get('htf')
                }
            elif len(args) == 4:
                # Called with individual dataframes
                timeframes = {
                    'base': args[0],  # base_ohlcv
                    'ltf': args[1],   # ltf_ohlcv
                    'mtf': args[2],   # mtf_ohlcv
                    'htf': args[3]    # htf_ohlcv
                }
            else:
                result['valid'] = False
                result['reason'] = f"Invalid arguments: expected either market_data dict or 4 DataFrame arguments"
                self.logger.error(result['reason'])
                return result
            
            # Validate each timeframe
            for tf_name, df in timeframes.items():
                # Check DataFrame is valid
                if not isinstance(df, pd.DataFrame):
                    result['valid'] = False
                    result['reason'] = f"Invalid {tf_name} timeframe: not a DataFrame"
                    self.logger.error(result['reason'])
                    return result
                
                # Check DataFrame is not empty
                if df.empty:
                    result['valid'] = False
                    result['reason'] = f"Empty {tf_name} timeframe DataFrame"
                    self.logger.error(result['reason'])
                    return result
                
                # Check required columns
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    result['valid'] = False
                    result['reason'] = f"Missing columns in {tf_name} timeframe: {missing_columns}"
                    self.logger.error(result['reason'])
                    return result
                
                # Check minimum data points based on timeframe
                min_points = self.TIMEFRAME_CONFIG.get(tf_name, {}).get('validation', {}).get('min_candles', 50)
                if tf_name == 'base' and len(df) < min_points:
                    result['valid'] = False
                    result['reason'] = f"Insufficient data points in {tf_name} timeframe: {len(df)} < {min_points}"
                    self.logger.error(result['reason'])
                    return result
                # For other timeframes, be more lenient (warning only for less data)
                elif tf_name != 'base' and len(df) < min_points:
                    self.logger.warning(f"Fewer than ideal data points in {tf_name} timeframe: {len(df)} < {min_points}")
            
            # Log successful validation
            self.logger.debug(f"Market data validation successful: all timeframes have required columns and sufficient data")
            
            # Return just True for backward compatibility when called from test script
            if len(args) == 1 and isinstance(args[0], dict):
                return result['valid']
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during input validation: {str(e)}")
            self.logger.error(traceback.format_exc())
            if len(args) == 1 and isinstance(args[0], dict):
                return False
            return {'valid': False, 'reason': f"Validation error: {str(e)}"}

    def _calculate_indicator_values(self, base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv):
        """Calculate all indicator values for the given timeframes."""
        return {
            'ohlcv': {
                'base': base_ohlcv,
                'ltf': ltf_ohlcv,
                'mtf': mtf_ohlcv,
                'htf': htf_ohlcv
            }
        }

    def _visualize_timeframe_divergence(self, base_ohlcv, ltf_ohlcv, mtf_ohlcv, htf_ohlcv, indicators_data):
        """Visualize indicator data for divergence analysis."""
        try:
            # Calculate all the indicators for each timeframe
            indicators = {}
            
            # Calculate indicator values for base timeframe
            if isinstance(base_ohlcv, pd.DataFrame) and not base_ohlcv.empty:
                base_macd, base_signal, _ = talib.MACD(base_ohlcv['close'], 
                                                      fastperiod=self.macd_params['fast_period'], 
                                                      slowperiod=self.macd_params['slow_period'],
                                                      signalperiod=self.macd_params['signal_period'])
                
                # Calculate AO manually
                base_median_price = (base_ohlcv['high'] + base_ohlcv['low']) / 2
                if len(base_ohlcv) >= 34:
                    base_fast_sma = talib.SMA(base_median_price, timeperiod=5)
                    base_slow_sma = talib.SMA(base_median_price, timeperiod=34)
                    base_ao = base_fast_sma - base_slow_sma
                else:
                    base_ao = pd.Series([np.nan])
                
                base_williams_r = talib.WILLR(base_ohlcv['high'], base_ohlcv['low'], base_ohlcv['close'], timeperiod=14)
                base_atr = talib.ATR(base_ohlcv['high'], base_ohlcv['low'], base_ohlcv['close'], timeperiod=self.atr_period)
                base_cci = talib.CCI(base_ohlcv['high'], base_ohlcv['low'], base_ohlcv['close'], timeperiod=self.cci_period)
                base_rsi = talib.RSI(base_ohlcv['close'], timeperiod=self.rsi_period)
                
                # Get the latest values
                indicators['base'] = {
                    'MACD': base_macd.iloc[-1] if not base_macd.empty and not pd.isna(base_macd.iloc[-1]) else np.nan,
                    'AO': base_ao.iloc[-1] if not base_ao.empty and not pd.isna(base_ao.iloc[-1]) else np.nan,
                    'Williams %R': base_williams_r.iloc[-1] if not base_williams_r.empty and not pd.isna(base_williams_r.iloc[-1]) else np.nan,
                    'ATR': base_atr.iloc[-1] if not base_atr.empty and not pd.isna(base_atr.iloc[-1]) else np.nan,
                    'CCI': base_cci.iloc[-1] if not base_cci.empty and not pd.isna(base_cci.iloc[-1]) else np.nan,
                    'RSI': base_rsi.iloc[-1] if not base_rsi.empty and not pd.isna(base_rsi.iloc[-1]) else np.nan,
                    'UO': np.nan  # Placeholder for Ultimate Oscillator
                }
            else:
                indicators['base'] = {
                    'MACD': np.nan, 'AO': np.nan, 'Williams %R': np.nan, 
                    'ATR': np.nan, 'CCI': np.nan, 'RSI': np.nan, 'UO': np.nan
                }
            
            # Calculate indicator values for LTF timeframe
            if isinstance(ltf_ohlcv, pd.DataFrame) and not ltf_ohlcv.empty:
                ltf_macd, ltf_signal, _ = talib.MACD(ltf_ohlcv['close'], 
                                                    fastperiod=self.macd_params['fast_period'], 
                                                    slowperiod=self.macd_params['slow_period'],
                                                    signalperiod=self.macd_params['signal_period'])
                
                # Calculate AO manually
                ltf_median_price = (ltf_ohlcv['high'] + ltf_ohlcv['low']) / 2
                if len(ltf_ohlcv) >= 34:
                    ltf_fast_sma = talib.SMA(ltf_median_price, timeperiod=5)
                    ltf_slow_sma = talib.SMA(ltf_median_price, timeperiod=34)
                    ltf_ao = ltf_fast_sma - ltf_slow_sma
                else:
                    ltf_ao = pd.Series([np.nan])
                
                ltf_williams_r = talib.WILLR(ltf_ohlcv['high'], ltf_ohlcv['low'], ltf_ohlcv['close'], timeperiod=14)
                ltf_atr = talib.ATR(ltf_ohlcv['high'], ltf_ohlcv['low'], ltf_ohlcv['close'], timeperiod=self.atr_period)
                ltf_cci = talib.CCI(ltf_ohlcv['high'], ltf_ohlcv['low'], ltf_ohlcv['close'], timeperiod=self.cci_period)
                ltf_rsi = talib.RSI(ltf_ohlcv['close'], timeperiod=self.rsi_period)
                
                # Get the latest values
                indicators['ltf'] = {
                    'MACD': ltf_macd.iloc[-1] if not ltf_macd.empty and not pd.isna(ltf_macd.iloc[-1]) else np.nan,
                    'AO': ltf_ao.iloc[-1] if not ltf_ao.empty and not pd.isna(ltf_ao.iloc[-1]) else np.nan,
                    'Williams %R': ltf_williams_r.iloc[-1] if not ltf_williams_r.empty and not pd.isna(ltf_williams_r.iloc[-1]) else np.nan,
                    'ATR': ltf_atr.iloc[-1] if not ltf_atr.empty and not pd.isna(ltf_atr.iloc[-1]) else np.nan,
                    'CCI': ltf_cci.iloc[-1] if not ltf_cci.empty and not pd.isna(ltf_cci.iloc[-1]) else np.nan,
                    'RSI': ltf_rsi.iloc[-1] if not ltf_rsi.empty and not pd.isna(ltf_rsi.iloc[-1]) else np.nan,
                    'UO': np.nan  # Placeholder for Ultimate Oscillator
                }
            else:
                indicators['ltf'] = {
                    'MACD': np.nan, 'AO': np.nan, 'Williams %R': np.nan, 
                    'ATR': np.nan, 'CCI': np.nan, 'RSI': np.nan, 'UO': np.nan
                }
            
            # Calculate indicator values for MTF timeframe
            if isinstance(mtf_ohlcv, pd.DataFrame) and not mtf_ohlcv.empty:
                mtf_macd, mtf_signal, _ = talib.MACD(mtf_ohlcv['close'], 
                                                    fastperiod=self.macd_params['fast_period'], 
                                                    slowperiod=self.macd_params['slow_period'],
                                                    signalperiod=self.macd_params['signal_period'])
                
                # Calculate AO manually
                mtf_median_price = (mtf_ohlcv['high'] + mtf_ohlcv['low']) / 2
                if len(mtf_ohlcv) >= 34:
                    mtf_fast_sma = talib.SMA(mtf_median_price, timeperiod=5)
                    mtf_slow_sma = talib.SMA(mtf_median_price, timeperiod=34)
                    mtf_ao = mtf_fast_sma - mtf_slow_sma
                else:
                    mtf_ao = pd.Series([np.nan])
                
                mtf_williams_r = talib.WILLR(mtf_ohlcv['high'], mtf_ohlcv['low'], mtf_ohlcv['close'], timeperiod=14)
                mtf_atr = talib.ATR(mtf_ohlcv['high'], mtf_ohlcv['low'], mtf_ohlcv['close'], timeperiod=self.atr_period)
                mtf_cci = talib.CCI(mtf_ohlcv['high'], mtf_ohlcv['low'], mtf_ohlcv['close'], timeperiod=self.cci_period)
                mtf_rsi = talib.RSI(mtf_ohlcv['close'], timeperiod=self.rsi_period)
                
                # Get the latest values
                indicators['mtf'] = {
                    'MACD': mtf_macd.iloc[-1] if not mtf_macd.empty and not pd.isna(mtf_macd.iloc[-1]) else np.nan,
                    'AO': mtf_ao.iloc[-1] if not mtf_ao.empty and not pd.isna(mtf_ao.iloc[-1]) else np.nan,
                    'Williams %R': mtf_williams_r.iloc[-1] if not mtf_williams_r.empty and not pd.isna(mtf_williams_r.iloc[-1]) else np.nan,
                    'ATR': mtf_atr.iloc[-1] if not mtf_atr.empty and not pd.isna(mtf_atr.iloc[-1]) else np.nan,
                    'CCI': mtf_cci.iloc[-1] if not mtf_cci.empty and not pd.isna(mtf_cci.iloc[-1]) else np.nan,
                    'RSI': mtf_rsi.iloc[-1] if not mtf_rsi.empty and not pd.isna(mtf_rsi.iloc[-1]) else np.nan,
                    'UO': np.nan  # Placeholder for Ultimate Oscillator
                }
            else:
                indicators['mtf'] = {
                    'MACD': np.nan, 'AO': np.nan, 'Williams %R': np.nan, 
                    'ATR': np.nan, 'CCI': np.nan, 'RSI': np.nan, 'UO': np.nan
                }
            
            # Calculate indicator values for HTF timeframe
            if isinstance(htf_ohlcv, pd.DataFrame) and not htf_ohlcv.empty:
                htf_macd, htf_signal, _ = talib.MACD(htf_ohlcv['close'], 
                                                    fastperiod=self.macd_params['fast_period'], 
                                                    slowperiod=self.macd_params['slow_period'],
                                                    signalperiod=self.macd_params['signal_period'])
                
                # Calculate AO manually
                htf_median_price = (htf_ohlcv['high'] + htf_ohlcv['low']) / 2
                if len(htf_ohlcv) >= 34:
                    htf_fast_sma = talib.SMA(htf_median_price, timeperiod=5)
                    htf_slow_sma = talib.SMA(htf_median_price, timeperiod=34)
                    htf_ao = htf_fast_sma - htf_slow_sma
                else:
                    htf_ao = pd.Series([np.nan])
                
                htf_williams_r = talib.WILLR(htf_ohlcv['high'], htf_ohlcv['low'], htf_ohlcv['close'], timeperiod=14)
                htf_atr = talib.ATR(htf_ohlcv['high'], htf_ohlcv['low'], htf_ohlcv['close'], timeperiod=self.atr_period)
                htf_cci = talib.CCI(htf_ohlcv['high'], htf_ohlcv['low'], htf_ohlcv['close'], timeperiod=self.cci_period)
                htf_rsi = talib.RSI(htf_ohlcv['close'], timeperiod=self.rsi_period)
                
                # Get the latest values
                indicators['htf'] = {
                    'MACD': htf_macd.iloc[-1] if not htf_macd.empty and not pd.isna(htf_macd.iloc[-1]) else np.nan,
                    'AO': htf_ao.iloc[-1] if not htf_ao.empty and not pd.isna(htf_ao.iloc[-1]) else np.nan,
                    'Williams %R': htf_williams_r.iloc[-1] if not htf_williams_r.empty and not pd.isna(htf_williams_r.iloc[-1]) else np.nan,
                    'ATR': htf_atr.iloc[-1] if not htf_atr.empty and not pd.isna(htf_atr.iloc[-1]) else np.nan,
                    'CCI': htf_cci.iloc[-1] if not htf_cci.empty and not pd.isna(htf_cci.iloc[-1]) else np.nan,
                    'RSI': htf_rsi.iloc[-1] if not htf_rsi.empty and not pd.isna(htf_rsi.iloc[-1]) else np.nan,
                    'UO': np.nan  # Placeholder for Ultimate Oscillator
                }
            else:
                indicators['htf'] = {
                    'MACD': np.nan, 'AO': np.nan, 'Williams %R': np.nan, 
                    'ATR': np.nan, 'CCI': np.nan, 'RSI': np.nan, 'UO': np.nan
                }
            
            # Create a DataFrame from the indicators
            df = pd.DataFrame.from_dict(indicators, orient='index')
            
            # Log what indicators we have calculated
            non_nan_counts = df.notna().sum()
            self.logger.debug(f"Available indicators for divergence analysis: {non_nan_counts.to_dict()}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error visualizing timeframe divergence: {str(e)}")
            self.logger.error(traceback.format_exc())
            # Return an empty DataFrame with the expected structure
            return pd.DataFrame(columns=['MACD', 'AO', 'Williams %R', 'ATR', 'CCI', 'RSI', 'UO'],
                               index=['base', 'ltf', 'mtf', 'htf'])
    
    def _log_component_specific_alerts(self, component_scores: Dict[str, float], 
                                     alerts: List[str], indicator_name: str) -> None:
        """Log Technical Indicators specific alerts."""
        # RSI alerts
        rsi_score = component_scores.get('rsi', 50)
        if rsi_score >= 80:
            alerts.append("❌ RSI Extremely Overbought - Strong reversal signal expected")
        elif rsi_score <= 20:
            alerts.append("✅ RSI Extremely Oversold - Strong bounce signal expected")
        
        # MACD alerts
        macd_score = component_scores.get('macd', 50)
        if macd_score >= 75:
            alerts.append("MACD Strong Bullish Momentum - Consider momentum plays")
        elif macd_score <= 25:
            alerts.append("MACD Strong Bearish Momentum - Consider defensive positions")
        
        # AO alerts
        ao_score = component_scores.get('ao', 50)
        if ao_score >= 75:
            alerts.append("Awesome Oscillator Strong Bullish - Momentum acceleration")
        elif ao_score <= 25:
            alerts.append("Awesome Oscillator Strong Bearish - Momentum deceleration")
        
        # Williams %R alerts
        williams_score = component_scores.get('williams_r', 50)
        if williams_score >= 80:
            alerts.append("⚠️ Williams %R Overbought - Watch for reversal")
        elif williams_score <= 20:
            alerts.append("Williams %R Oversold - Potential buying opportunity")
        
        # ATR alerts (volatility)
        atr_score = component_scores.get('atr', 50)
        if atr_score >= 75:
            alerts.append("High Volatility Environment - Adjust position sizing")
        elif atr_score <= 25:
            alerts.append("Low Volatility Environment - Potential breakout setup")
        
        # CCI alerts
        cci_score = component_scores.get('cci', 50)
        if cci_score >= 75:
            alerts.append("CCI Strong Bullish - Trend acceleration signal")
        elif cci_score <= 25:
            alerts.append("CCI Strong Bearish - Trend deceleration signal")
