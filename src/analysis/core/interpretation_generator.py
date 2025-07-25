"""
Enhanced market interpretation generator for confluence analysis results.
Provides rich, context-aware interpretations across different market components.
"""

import logging
import textwrap
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from ...core.interfaces.services import IInterpretationService, IFormattingService, IValidationService

class InterpretationGenerator(IInterpretationService):
    """
    Generates enhanced market interpretations from confluence analysis results.
    
    Implements IInterpretationService interface with dependency injection support.
    """
    
    def __init__(
        self, 
        formatter: Optional[IFormattingService] = None,
        validator: Optional[IValidationService] = None
    ):
        """
        Initialize the interpretation generator with dependencies.
        
        Args:
            formatter: Formatting service for data presentation
            validator: Validation service for input validation
        """
        self.logger = logging.getLogger(__name__)
        self._formatter = formatter
        self._validator = validator
    
    def get_component_interpretation(self, component: str, data: Dict[str, Any]) -> str:
        """
        Generate enhanced interpretation for a specific component.
        
        Args:
            component: Name of the component (technical, volume, etc.)
            data: The component data containing scores, signals, etc.
            
        Returns:
            str: Enhanced interpretation string
        """
        try:
            # Call the appropriate interpreter based on component name
            if component == 'technical':
                return self._interpret_technical(data)
            elif component == 'volume':
                return self._interpret_volume(data)
            elif component == 'orderbook':
                return self._interpret_orderbook(data)
            elif component == 'orderflow':
                return self._interpret_orderflow(data)
            elif component == 'sentiment':
                return self._interpret_sentiment(data)
            elif component == 'price_structure':
                return self._interpret_price_structure(data)
            else:
                # Default fallback if component doesn't have specific handler
                return self._get_default_interpretation(component, data)
        except Exception as e:
            self.logger.error(f"Error generating interpretation for {component}: {str(e)}")
            # Provide a reasonable fallback if interpretation fails
            return self._get_default_interpretation(component, data)
    
    def _interpret_technical(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for technical analysis component."""
        try:
            # Validate input data
            if not isinstance(data, dict):
                self.logger.warning(f"Invalid data type for technical interpretation: {type(data)}")
                return "Unable to analyze technical indicators: invalid data format"
            
            # Extract key values with safe defaults
            score = float(data.get('score', 50))
            components = data.get('components', {})
            raw_values = data.get('metadata', {}).get('raw_values', {})
            
            # Extract key values from the data
            signals = data.get('signals', {})
            trend = signals.get('trend', 'neutral')
            strength = signals.get('strength', 0)
            
            # Handle trend_signal which can be either a string or a dictionary
            trend_signal = signals.get('trend', {})
            if isinstance(trend_signal, dict):
                trend_value = trend_signal.get('value', 50)
                trend_type = trend_signal.get('signal', 'neutral')
                trend_strength = trend_signal.get('strength', 0.5)
            else:
                # If trend_signal is a string, use it as trend_type and set defaults
                trend_value = 50
                trend_type = str(trend_signal) if trend_signal else 'neutral'
                trend_strength = 0.5
            
            # Identify strongest components and separate oscillators from trend indicators
            strongest_components = sorted(components.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Start with trend description
            if trend == 'bullish':
                strength_desc = 'strong' if strength > 0.6 else 'moderate' if strength > 0.3 else 'weak'
                message = f"Technical indicators show a {strength_desc} bullish trend"
            elif trend == 'bearish':
                strength_desc = 'strong' if abs(strength) > 0.6 else 'moderate' if abs(strength) > 0.3 else 'weak'
                message = f"Technical indicators show a {strength_desc} bearish trend"
            else:
                if score > 55:
                    message = "Technical indicators show slight bullish bias within overall neutrality"
                elif score < 45:
                    message = "Technical indicators show slight bearish bias within overall neutrality"
                else:
                    message = "Technical indicators reflect market indecision with no clear directional bias"
            
            # Add insights about strongest components with categorization
            trend_indicators = {}
            oscillators = {}
            
            # Categorize indicators
            for comp_name, comp_value in components.items():
                if comp_name.lower() in ['macd', 'adx', 'dmi', 'moving_averages', 'ichimoku', 'supertrend', 'trend', 'ma_cross']:
                    trend_indicators[comp_name] = comp_value
                elif comp_name.lower() in ['rsi', 'ao', 'stoch', 'cci', 'mfi', 'williams_r', 'stoch_rsi', 'ultimate_oscillator']:
                    oscillators[comp_name] = comp_value
            
            # Add trend indicator insights
            if trend_indicators:
                strongest_trend = sorted(trend_indicators.items(), key=lambda x: x[1], reverse=True)[0]
                trend_name, trend_value = strongest_trend
                trend_name = trend_name.upper()
                
                if trend_value > 65:
                    message += f". {trend_name} strongly confirms bullish trend ({trend_value:.1f})"
                elif trend_value < 35:
                    message += f". {trend_name} strongly confirms bearish trend ({trend_value:.1f})"
                else:
                    message += f". {trend_name} shows neutral trend conditions ({trend_value:.1f})"
                    
                # Add moving averages crossover context if available
                ma_cross = components.get('ma_cross', None)
                if ma_cross is not None:
                    if ma_cross > 65:
                        message += ". Moving averages showing bullish crossover pattern"
                    elif ma_cross < 35:
                        message += ". Moving averages showing bearish crossover pattern"
            
            # Add oscillator insights - prioritize RSI and AO due to their high weights (20% each)
            if oscillators:
                # Always include RSI interpretation if available (20% weight)
                if 'rsi' in components:
                    rsi_value = components['rsi']
                    if rsi_value > 70:
                        message += f". RSI indicates overbought conditions ({rsi_value:.1f}), potential reversal zone"
                    elif rsi_value < 30:
                        message += f". RSI indicates oversold conditions ({rsi_value:.1f}), potential reversal zone"
                    elif rsi_value > 60:
                        message += f". RSI shows bullish momentum without being overbought ({rsi_value:.1f})"
                    elif rsi_value < 40:
                        message += f". RSI shows bearish momentum without being oversold ({rsi_value:.1f})"
                    else:
                        message += f". RSI in neutral territory ({rsi_value:.1f})"
                
                # Always include AO interpretation if available (20% weight)
                if 'ao' in components:
                    ao_value = components['ao']
                    if ao_value > 65:
                        message += f". AO shows strong bullish momentum ({ao_value:.1f})"
                        if ao_value > 80:
                            message += " with potential zero-line crossover or saucer pattern"
                    elif ao_value < 35:
                        message += f". AO shows strong bearish momentum ({ao_value:.1f})"
                        if ao_value < 20:
                            message += " with potential zero-line crossover or saucer pattern"
                    elif ao_value > 55:
                        message += f". AO indicates bullish momentum building ({ao_value:.1f})"
                    elif ao_value < 45:
                        message += f". AO indicates bearish momentum building ({ao_value:.1f})"
                    else:
                        message += f". AO in neutral territory ({ao_value:.1f})"
                
                # Always include strongest oscillator interpretation (for comprehensive analysis)
                strongest_osc = sorted(oscillators.items(), key=lambda x: x[1], reverse=True)[0]
                osc_name, osc_value = strongest_osc
                osc_name = osc_name.upper()
                
                # Only add if it's not already covered by RSI or AO interpretations above
                if osc_name not in ['RSI', 'AO']:
                    if osc_value > 70:
                        message += f". {osc_name} indicates overbought conditions ({osc_value:.1f}), potential reversal zone"
                    elif osc_value < 30:
                        message += f". {osc_name} indicates oversold conditions ({osc_value:.1f}), potential reversal zone"
                    elif osc_value > 60:
                        message += f". {osc_name} shows bullish momentum without being overbought ({osc_value:.1f})"
                    elif osc_value < 40:
                        message += f". {osc_name} shows bearish momentum without being oversold ({osc_value:.1f})"
                    else:
                        message += f". {osc_name} in neutral territory ({osc_value:.1f})"
                elif osc_name == 'RSI' or osc_name == 'AO':
                    # If RSI or AO is the strongest, add emphasis to their existing interpretation
                    if osc_value > 70 or osc_value < 30:
                        message += f" (strongest oscillator signal)"
                    elif osc_value > 60 or osc_value < 40:
                        message += f" (leading oscillator momentum)"
            
            # Add momentum context
            momentum = components.get('momentum', 50)
            if momentum > 65:
                message += ". Strong positive momentum supporting price action"
                if 'rsi' in components and components['rsi'] > 65:
                    message += ", confirmed by RSI strength"
            elif momentum < 35:
                message += ". Weak momentum suggesting limited directional conviction"
                if 'rsi' in components and components['rsi'] < 35:
                    message += ", confirmed by RSI weakness"
            
            # Add pattern recognition insights if available
            patterns = data.get('signals', {}).get('patterns', [])
            if patterns and len(patterns) > 0:
                top_pattern = patterns[0]
                pattern_name = top_pattern.get('name', '')
                pattern_type = top_pattern.get('type', '')
                
                if pattern_name and pattern_type:
                    if pattern_type == 'bullish':
                        message += f". {pattern_name} pattern detected suggesting bullish continuation/reversal"
                    elif pattern_type == 'bearish':
                        message += f". {pattern_name} pattern detected suggesting bearish continuation/reversal"
            
            # Add divergence insights
            divergences_bearish = data.get('signals', {}).get('divergences_bearish', [])
            divergences_bullish = data.get('signals', {}).get('divergences_bullish', [])
            
            if divergences_bearish:
                message += f". Bearish divergence detected: {divergences_bearish[0]}"
                if score > 65:
                    message += ", signaling potential trend exhaustion despite overall bullish reading"
            elif divergences_bullish:
                message += f". Bullish divergence detected: {divergences_bullish[0]}"
                if score < 35:
                    message += ", signaling potential trend exhaustion despite overall bearish reading"
            
            # Add volatility context
            volatility = components.get('volatility', 50)
            if volatility > 65:
                message += ". Increased market volatility may amplify price movements"
                if trend == 'bullish':
                    message += " in the bullish direction"
                elif trend == 'bearish':
                    message += " in the bearish direction"
            elif volatility < 35:
                message += ". Low market volatility suggests consolidation before next directional move"
            
            # Add timeframe analysis if available
            timeframe_scores = data.get('timeframe_scores', {})
            if timeframe_scores:
                tf_insights = self._analyze_timeframes(timeframe_scores)
                if tf_insights:
                    message += f". {tf_insights}"
            
            # Add probabilistic context to make interpretation more actionable
            component_confidence = {name: score for name, score in components.items() if isinstance(score, (int, float))}
            enhanced_message = self._add_probabilistic_context(message, score, component_confidence)
            return enhanced_message
            
        except Exception as e:
            self.logger.error(f"Error generating technical interpretation: {str(e)}")
            return "Unable to analyze technical indicators: an error occurred"
    
    def _interpret_volume(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for volume analysis component."""
        # Extract key values
        score = data.get('score', 50)
        signals = data.get('signals', {})
        raw_values = data.get('metadata', {}).get('raw_values', {})
        
        # Safely extract volume signals
        volume_sma_data = signals.get('volume_sma', {})
        volume_sma = volume_sma_data.get('signal', 'neutral') if isinstance(volume_sma_data, dict) else str(volume_sma_data) if volume_sma_data else 'neutral'
        
        volume_trend_data = signals.get('volume_trend', {})
        volume_trend = volume_trend_data.get('signal', 'neutral') if isinstance(volume_trend_data, dict) else str(volume_trend_data) if volume_trend_data else 'neutral'
        
        volume_profile_data = signals.get('volume_profile', {})
        volume_profile = volume_profile_data.get('signal', 'neutral') if isinstance(volume_profile_data, dict) else str(volume_profile_data) if volume_profile_data else 'neutral'
        
        # Get strongest components
        components = data.get('components', {})
        strongest_component = max(components.items(), key=lambda x: x[1]) if components else None
        
        # Interpret volume patterns with enhanced detail
        if volume_profile == 'bearish' and volume_trend == 'decreasing':
            message = "Volume analysis indicates selling pressure with declining participation"
            message += ", typically seen in late-stage downtrends or profit-taking phases"
        elif volume_profile == 'bearish' and volume_trend == 'increasing':
            message = "Volume analysis shows increasing selling pressure with rising participation"
            message += ", a strong bearish signal indicating accelerating distribution"
        elif volume_profile == 'bullish' and volume_trend == 'increasing':
            message = "Volume analysis shows strong buying interest with increasing participation"
            message += ", a robust bullish signal suggesting accumulation and potential continuation"
        elif volume_profile == 'bullish' and volume_trend == 'decreasing':
            message = "Volume analysis indicates weakening buying pressure with declining participation"
            message += ", suggesting waning momentum despite bullish bias"
        elif volume_sma == 'high':
            message = "Above average volume suggests significant market interest at current levels"
            message += ", indicating strong conviction in the current price direction"
            if score > 60:
                message += " with primarily buying activity"
            elif score < 40:
                message += " with primarily selling activity"
        elif volume_sma == 'low':
            message = "Below average volume indicates lack of conviction in current price movement"
            message += ", suggesting caution as price moves may not be sustainable"
        else:
            message = "Volume patterns show typical market participation without clear directional bias"
            message += ", indicating neutral conditions or potential consolidation phase"
        
        # Add information about strongest volume component with enhanced context
        if strongest_component:
            comp_name, comp_value = strongest_component
            comp_name_formatted = comp_name.upper()
            
            # Provide specific insights based on component type
            if comp_name == 'obv' or comp_name == 'on_balance_volume':
                if comp_value > 70:
                    message += f". {comp_name_formatted} showing strong upward trajectory ({comp_value:.1f}), confirming price trend with accumulation"
                elif comp_value < 30:
                    message += f". {comp_name_formatted} showing strong downward trajectory ({comp_value:.1f}), confirming price trend with distribution"
                else:
                    message += f". {comp_name_formatted} trending sideways ({comp_value:.1f}), suggesting balanced buying and selling"
            elif comp_name == 'cmf' or comp_name == 'chaikin_money_flow':
                if comp_value > 70:
                    message += f". {comp_name_formatted} strongly positive ({comp_value:.1f}), indicating significant buying pressure and capital inflow"
                elif comp_value < 30:
                    message += f". {comp_name_formatted} strongly negative ({comp_value:.1f}), indicating significant selling pressure and capital outflow"
                else:
                    message += f". {comp_name_formatted} near neutral ({comp_value:.1f}), showing balanced capital flow"
            elif comp_name == 'vwap' or comp_name == 'volume_weighted_average_price':
                if comp_value > 70:
                    message += f". Price significantly above {comp_name_formatted} ({comp_value:.1f}), indicating bullish intraday strength"
                elif comp_value < 30:
                    message += f". Price significantly below {comp_name_formatted} ({comp_value:.1f}), indicating bearish intraday weakness"
                else:
                    message += f". Price near {comp_name_formatted} ({comp_value:.1f}), suggesting balanced intraday trading"
            else:
                # Generic strong/weak interpretation for other components
                if comp_value > 70:
                    message += f". {comp_name_formatted} is particularly strong ({comp_value:.1f}), reinforcing the volume analysis"
                elif comp_value < 30:
                    message += f". {comp_name_formatted} is particularly weak ({comp_value:.1f}), reinforcing the volume analysis"
                else:
                    message += f". {comp_name_formatted} is the most significant volume indicator ({comp_value:.1f}) with neutral readings"
        
        # Add volume profile distribution insights if available
        vol_distribution = components.get('volume_distribution', None)
        if vol_distribution is not None:
            if vol_distribution > 65:
                message += ". Volume distribution shows concentration at higher prices, indicating strong buying interest"
            elif vol_distribution < 35:
                message += ". Volume distribution shows concentration at lower prices, indicating strong selling interest"
            else:
                message += ". Volume distribution is balanced across price range, suggesting equilibrium"
        
        # Add institutional activity signals if available
        institutional = components.get('institutional_activity', None)
        if institutional is not None:
            if institutional > 65:
                message += ". High volume blocks suggest institutional accumulation"
                if volume_profile == 'bullish':
                    message += ", reinforcing bullish bias"
            elif institutional < 35:
                message += ". High volume blocks suggest institutional distribution"
                if volume_profile == 'bearish':
                    message += ", reinforcing bearish bias"
        
        # Add volume divergence insights if available
        vol_price_divergence = signals.get('volume_price_divergence', {})
        if vol_price_divergence:
            div_type = vol_price_divergence.get('type', '')
            div_strength = vol_price_divergence.get('strength', 0)
            
            if div_type == 'bullish' and div_strength > 40:
                message += ". Bullish volume-price divergence detected, suggesting potential trend reversal to the upside"
            elif div_type == 'bearish' and div_strength > 40:
                message += ". Bearish volume-price divergence detected, suggesting potential trend reversal to the downside"
        
        # Add any additional insights about volume delta with enhanced interpretations
        if raw_values:
            if 'volume_delta' in raw_values:
                vol_delta = raw_values['volume_delta']
                if vol_delta < -0.8:
                    message += ". Significant negative volume delta suggests strong selling pressure"
                    message += ", indicating aggressive distribution that may accelerate price decline"
                elif vol_delta > 0.8:
                    message += ". Significant positive volume delta suggests strong buying pressure"
                    message += ", indicating aggressive accumulation that may accelerate price advance"
                elif vol_delta < -0.5:
                    message += ". Moderate negative volume delta shows sellers in control"
                elif vol_delta > 0.5:
                    message += ". Moderate positive volume delta shows buyers in control"
            
            # Add Chaikin Money Flow insights with enhanced context
            if 'cmf' in raw_values:
                cmf = raw_values['cmf']
                if cmf < -0.1:
                    message += ". Money flow confirms distribution pattern"
                    if volume_profile == 'bearish':
                        message += ", reinforcing bearish pressure with capital outflows"
                elif cmf > 0.1:
                    message += ". Money flow confirms accumulation pattern"
                    if volume_profile == 'bullish':
                        message += ", reinforcing bullish pressure with capital inflows"
        
        # Add volume-based market phase assessment
        if score > 65 and 'cmf' in components and components['cmf'] > 65:
            message += ". Overall volume analysis suggests accumulation phase with strong buying conviction"
        elif score < 35 and 'cmf' in components and components['cmf'] < 35:
            message += ". Overall volume analysis suggests distribution phase with strong selling conviction"
        elif abs(score - 50) < 10:
            message += ". Overall volume analysis suggests consolidation phase with balanced trading activity"
        
        # Add probabilistic context to make interpretation more actionable
        component_confidence = {name: score for name, score in components.items() if isinstance(score, (int, float))}
        enhanced_message = self._add_probabilistic_context(message, score, component_confidence)
        return enhanced_message
    
    def _interpret_orderbook(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for orderbook analysis component."""
        # Extract key values
        score = data.get('score', 50)
        components = data.get('components', {})
        raw_values = data.get('metadata', {}).get('raw_values', {})
        signals = data.get('signals', {})
        
        # Interpret imbalance with more detail
        imbalance = components.get('imbalance', 50)
        imbalance_raw = raw_values.get('imbalance_ratio', 0.5)
        
        if imbalance > 60:
            if imbalance > 75:
                imbalance_msg = "Extreme bid-side dominance"
                imbalance_detail = "indicating strong buying pressure likely to drive prices higher"
            else:
                imbalance_msg = "Strong bid-side dominance"
                imbalance_detail = "suggesting buyers controlling price action"
            side = "bid"
        elif imbalance < 40:
            if imbalance < 25:
                imbalance_msg = "Extreme ask-side dominance"
                imbalance_detail = "indicating strong selling pressure likely to drive prices lower"
            else:
                imbalance_msg = "Strong ask-side dominance"
                imbalance_detail = "suggesting sellers controlling price action"
            side = "ask"
        else:
            imbalance_msg = "Balanced order book"
            imbalance_detail = "suggesting equilibrium between buyers and sellers"
            side = "neutral"
        
        # Interpret liquidity with more context
        liquidity = components.get('liquidity', 50)
        if liquidity > 70:
            liquidity_msg = f"high {side}-side liquidity"
            if side == "bid":
                liquidity_detail = "providing strong price support below current level"
            elif side == "ask":
                liquidity_detail = "indicating significant resistance above current level"
            else:
                liquidity_detail = "providing both support and resistance around current price"
        elif liquidity < 30:
            liquidity_msg = f"low {side}-side liquidity"
            if side == "bid":
                liquidity_detail = "suggesting weak support below current level"
            elif side == "ask":
                liquidity_detail = "indicating weak resistance above current level"
            else:
                liquidity_detail = "suggesting potential for increased volatility"
        else:
            liquidity_msg = "moderate liquidity"
            liquidity_detail = "providing average market depth"
        
        # Interpret spread with market microstructure context
        spread = components.get('spread', 50)
        if spread > 70:
            spread_msg = "tight spreads"
            spread_detail = "indicating high market efficiency and low execution costs"
        elif spread < 30:
            spread_msg = "wide spreads"
            spread_detail = "suggesting lower market efficiency and higher execution costs"
        else:
            spread_msg = "normal spreads"
            spread_detail = "with typical bid-ask differentials"
        
        # Compose main message with enhanced details
        message = f"Orderbook shows {imbalance_msg} with {liquidity_msg} and {spread_msg}"
        message += f". {imbalance_detail}, {liquidity_detail}, and {spread_detail}"
        
        # Add depth analysis with enhanced insights
        depth = components.get('depth', 50)
        if depth > 65:
            message += f". Strong order depth suggests stable price levels"
            if side == "bid":
                message += " with robust buy-side absorption capacity"
            elif side == "ask":
                message += " with significant sell-side supply"
        elif depth < 35:
            message += f". Shallow order depth indicates potential for price volatility"
            if imbalance > 60 or imbalance < 40:
                message += f" and increased susceptibility to {side} pressure"
        
        # Add market making pressure insight with enhanced details
        mpi = components.get('mpi', 50)
        if mpi > 65:
            message += ". Market makers showing bullish positioning"
            message += ", typically a leading indicator for potential upward movement"
        elif mpi < 35:
            message += ". Market makers showing bearish positioning"
            message += ", often precedes downward price movement"
        
        # Add OIR (Order Imbalance Ratio) insights - 
        oir = components.get('oir', None)
        if oir is not None:
            if oir > 70:
                message += ". Order Imbalance Ratio strongly bullish"
                message += ", indicating dominant buying pressure with high predictive power for short-term upward movement"
            elif oir > 60:
                message += ". Order Imbalance Ratio moderately bullish"
                message += ", suggesting buying pressure likely to support price advance"
            elif oir < 30:
                message += ". Order Imbalance Ratio strongly bearish"
                message += ", indicating dominant selling pressure with high predictive power for short-term downward movement"
            elif oir < 40:
                message += ". Order Imbalance Ratio moderately bearish"
                message += ", suggesting selling pressure likely to weigh on price"
            else:
                message += ". Order Imbalance Ratio neutral"
                message += ", indicating balanced order flow with no clear directional bias"
        
        # Add DI (Depth Imbalance) insights -
        di = components.get('di', None)
        if di is not None:
            if di > 65:
                message += ". Depth Imbalance shows significant bid-side volume excess"
                message += ", providing strong support foundation and absorption capacity"
            elif di < 35:
                message += ". Depth Imbalance shows significant ask-side volume excess"
                message += ", creating substantial resistance overhead and supply pressure"
            else:
                message += ". Depth Imbalance relatively balanced"
                message += ", suggesting proportional liquidity distribution"
        
        # Add hidden liquidity insights if available
        hidden_liquidity = components.get('hidden_liquidity', None)
        if hidden_liquidity is not None:
            if hidden_liquidity > 65:
                message += ". Significant hidden liquidity detected, suggesting institutional activity"
                if side == "bid":
                    message += " on the buy side"
                elif side == "ask":
                    message += " on the sell side"
            elif hidden_liquidity < 35:
                message += ". Minimal hidden liquidity, indicating primarily visible orderbook activity"
        
        # Add absorption/exhaustion insight with enhanced context
        exhaustion = components.get('exhaustion', 50)
        if exhaustion > 70:
            message += ". Signs of order exhaustion detected; potential reversal point"
            if side == "ask":
                message += " as selling pressure appears to be depleting"
            elif side == "bid":
                message += " as buying momentum may be reaching limits"
        
        # Add order clustering insights
        clustering = components.get('clustering', None)
        if clustering is not None:
            if clustering > 65:
                message += ". Orders showing significant clustering"
                if side == "bid":
                    message += " at support levels, reinforcing price floors"
                elif side == "ask":
                    message += " at resistance levels, creating potential price ceilings"
            elif clustering < 35:
                message += ". Orders broadly distributed without significant clustering"
        
        # Add potential market impact prediction
        if score > 65 and imbalance > 60:
            message += ". Overall orderbook structure strongly supports upward price movement"
        elif score < 35 and imbalance < 40:
            message += ". Overall orderbook structure strongly supports downward price movement"
        elif abs(score - 50) < 10 and abs(imbalance - 50) < 10:
            message += ". Overall orderbook structure suggests consolidation or sideways movement"
        
        # Add probabilistic context to make interpretation more actionable
        component_confidence = {name: score for name, score in components.items() if isinstance(score, (int, float))}
        enhanced_message = self._add_probabilistic_context(message, score, component_confidence)
        return enhanced_message
    
    def _interpret_orderflow(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for orderflow analysis component."""
        try:
            # Validate input data
            if not isinstance(data, dict):
                self.logger.warning(f"Invalid data type for orderflow interpretation: {type(data)}")
                return "Unable to analyze orderflow: invalid data format"
            
            # Extract key values with safe defaults
            score = float(data.get('score', 50))
            components = data.get('components', {})
            signals = data.get('signals', {})
            interpretation = signals.get('interpretation', {})
            raw_values = data.get('metadata', {}).get('raw_values', {})
            
            # Get the main interpretation message
            if isinstance(interpretation, dict) and 'message' in interpretation:
                message = interpretation['message']
            else:
                # Create detailed interpretation based on score with enhanced context
                if score > 65:
                    if score > 80:
                        message = "Extremely strong bullish orderflow indicating aggressive buying pressure"
                    else:
                        message = "Strong bullish orderflow indicating steady buying pressure"
                elif score < 35:
                    if score < 20:
                        message = "Extremely strong bearish orderflow indicating aggressive selling pressure"
                    else:
                        message = "Strong bearish orderflow indicating steady selling pressure"
                else:
                    if score > 55:
                        message = "Neutral orderflow with slight buying bias"
                    elif score < 45:
                        message = "Neutral orderflow with slight selling bias"
                    else:
                        message = "Balanced orderflow with equilibrium between buyers and sellers"
            
            # Add open interest insights with enhanced market context
            oi_score = components.get('open_interest_score', 50)
            oi_change = components.get('open_interest_change', 0)
            if oi_score > 65:
                message += ". Rising open interest confirms trend strength"
                if oi_change > 0.1:
                    message += " with significant new position creation"
                    if score > 60:
                        message += ", indicating fresh buying entering the market"
                    elif score < 40:
                        message += ", indicating fresh selling entering the market"
                message += ", typically seen in strong trend continuation"
            elif oi_score < 35:
                message += ". Declining open interest suggests trend exhaustion"
                if oi_change < -0.1:
                    message += " with significant position reduction"
                    if score < 40:
                        message += " and possible short covering"
                    elif score > 60:
                        message += " and possible profit taking"
                message += ", often precedes consolidation or reversal"
            
            # Add CVD (Cumulative Volume Delta) insights with enhanced price impact assessment
            cvd = components.get('cvd', 50)
            cvd_slope = components.get('cvd_slope', 0)
            if cvd > 65:
                message += ". Strong positive cumulative volume delta showing dominant buying activity"
                if cvd_slope > 0.1:
                    message += " with accelerating momentum"
                elif cvd_slope < -0.05:
                    message += " though momentum is slowing"
                
                if score < 50:
                    message += "; divergence between CVD and price action suggests potential bullish reversal"
            elif cvd < 35:
                message += ". Strong negative cumulative volume delta showing dominant selling activity"
                if cvd_slope < -0.1:
                    message += " with accelerating momentum"
                elif cvd_slope > 0.05:
                    message += " though momentum is slowing"
                
                if score > 50:
                    message += "; divergence between CVD and price action suggests potential bearish reversal"
            
            # Add trade flow insights with enhanced institutional analysis
            trade_flow = components.get('trade_flow_score', 50)
            large_trades = components.get('large_trades', 50)
            if trade_flow > 65:
                message += ". Large trades predominantly executed on the buy side"
                if large_trades > 70:
                    message += ", indicating likely institutional accumulation"
                if cvd > 60:
                    message += " with strong absorption of selling pressure"
            elif trade_flow < 35:
                message += ". Large trades predominantly executed on the sell side"
                if large_trades > 70:
                    message += ", indicating likely institutional distribution"
                if cvd < 40:
                    message += " with weak absorption of selling pressure"
            elif large_trades > 65:
                message += ". Significant large trade activity with balanced buying and selling"
            
            # Add market maker activity insights
            mm_activity = components.get('market_maker_activity', 50)
            if mm_activity is not None:
                if mm_activity > 65:
                    message += ". Market makers actively providing liquidity"
                    if score > 60:
                        message += " with bullish positioning"
                    elif score < 40:
                        message += " with bearish positioning"
                elif mm_activity < 35:
                    message += ". Limited market maker activity suggesting thin liquidity conditions"
            
            # Add aggressive orders analysis
            aggr_buys = components.get('aggressive_buys', 50)
            aggr_sells = components.get('aggressive_sells', 50)
            if aggr_buys > 65 and aggr_sells < 45:
                message += ". Buyers aggressively lifting offers, indicating urgent demand"
                if score > 65:
                    message += " and potential for upside acceleration"
            elif aggr_sells > 65 and aggr_buys < 45:
                message += ". Sellers aggressively hitting bids, indicating urgent liquidation"
                if score < 35:
                    message += " and potential for downside acceleration"
            elif aggr_buys > 60 and aggr_sells > 60:
                message += ". High aggression on both sides indicating volatile, two-way trading"
            
            # Add volume profile distribution insights
            vol_concentration = components.get('volume_concentration', None)
            if vol_concentration is not None:
                if vol_concentration > 65:
                    message += ". Volume concentrated at specific price levels"
                    vol_nodes = components.get('volume_nodes', [])
                    if isinstance(vol_nodes, list) and len(vol_nodes) > 0:
                        if vol_nodes[0].get('type') == 'HVN' and vol_nodes[0].get('proximity', 1) < 0.05:
                            message += ", with high volume node near current price suggesting significant interest"
                        elif vol_nodes[0].get('type') == 'LVN' and vol_nodes[0].get('proximity', 1) < 0.05:
                            message += ", with low volume node near current price suggesting potential for quick price movement"
                elif vol_concentration < 35:
                    message += ". Volume evenly distributed across price range, lacking clear reference points"
            
            # Add order book sweep insights
            sweeps = components.get('sweeps', 50)
            if sweeps > 65:
                message += ". Multiple orderbook sweeps detected"
                if score > 60:
                    message += ", with buy-side sweeps dominating"
                elif score < 40:
                    message += ", with sell-side sweeps dominating"
                message += " - often signals strong conviction and potential for price acceleration"
            
            # Add iceberg order detection
            icebergs = components.get('iceberg_orders', None)
            if icebergs is not None and icebergs > 65:
                message += ". Iceberg order activity detected"
                if components.get('iceberg_side', 'neutral') == 'buy':
                    message += " on the buy side, suggesting hidden support"
                elif components.get('iceberg_side', 'neutral') == 'sell':
                    message += " on the sell side, suggesting hidden resistance"
            
            # Add divergence insights with enhanced implications
            divergences = signals.get('divergences', {})
            if divergences:
                price_cvd = divergences.get('price_cvd', {})
                if price_cvd.get('type') == 'bullish' and price_cvd.get('strength', 0) > 30:
                    message += ". Bullish divergence between price and orderflow detected"
                    message += ", suggesting potential upside reversal as price declines despite improving flows"
                elif price_cvd.get('type') == 'bearish' and price_cvd.get('strength', 0) > 30:
                    message += ". Bearish divergence between price and orderflow detected"
                    message += ", suggesting potential downside reversal as price rises despite deteriorating flows"
            
            # Add tape reading signals
            tape_signals = signals.get('tape_signals', [])
            if tape_signals and len(tape_signals) > 0:
                top_signal = tape_signals[0]
                if isinstance(top_signal, dict) and 'type' in top_signal and 'strength' in top_signal:
                    if top_signal['type'] == 'absorption' and top_signal['strength'] > 0.6:
                        message += ". Strong absorption of selling pressure detected on the tape"
                    elif top_signal['type'] == 'distribution' and top_signal['strength'] > 0.6:
                        message += ". Strong distribution pattern detected on the tape"
                    elif top_signal['type'] == 'climax' and top_signal['strength'] > 0.7:
                        message += ". Volume climax detected, suggesting potential exhaustion and reversal"
            
            # Add trading imbalance assessment
            if 'imbalance' in components:
                imbalance = components['imbalance']
                if imbalance > 70:
                    message += ". Significant order imbalance favoring buyers"
                    if 'absorption' in components and components['absorption'] > 65:
                        message += ", with strong absorption of incoming supply"
                elif imbalance < 30:
                    message += ". Significant order imbalance favoring sellers"
                    if 'absorption' in components and components['absorption'] > 65:
                        message += ", with strong absorption of incoming demand"
            
            # Add overall market structure context
            if score > 65 and components.get('persistence', 50) > 65:
                message += ". Overall orderflow structure indicates strong buying pressure likely to continue"
            elif score < 35 and components.get('persistence', 50) > 65:
                message += ". Overall orderflow structure indicates strong selling pressure likely to continue"
            elif abs(score - 50) < 10:
                message += ". Overall orderflow structure indicates balanced conditions with no clear directional edge"
            
            # Add probabilistic context to make interpretation more actionable
            component_confidence = {name: score for name, score in components.items() if isinstance(score, (int, float))}
            enhanced_message = self._add_probabilistic_context(message, score, component_confidence)
            return enhanced_message
            
        except Exception as e:
            self.logger.error(f"Error generating orderflow interpretation: {str(e)}")
            return "Unable to analyze orderflow: an error occurred"
    
    def _interpret_sentiment(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for sentiment analysis component."""
        try:
            # Validate input data
            if not isinstance(data, dict):
                self.logger.warning(f"Invalid data type for sentiment interpretation: {type(data)}")
                return "Unable to analyze sentiment: invalid data format"
            
            # Extract key values with safe defaults
            score = float(data.get('score', 50))
            components = data.get('components', {})
            interpretation = data.get('interpretation', {})
            raw_values = data.get('metadata', {}).get('raw_values', {})
            
            # Use provided interpretation summary if available
            if isinstance(interpretation, dict) and 'summary' in interpretation:
                return interpretation['summary']
            
            # Otherwise, generate a new interpretation
            if score > 65:
                sentiment_msg = "Strongly bullish market sentiment"
            elif score > 55:
                sentiment_msg = "Moderately bullish market sentiment"
            elif score < 35:
                sentiment_msg = "Strongly bearish market sentiment"
            elif score < 45:
                sentiment_msg = "Moderately bearish market sentiment"
            else:
                sentiment_msg = "Neutral market sentiment"
            
            # Add risk assessment with more detailed context
            risk = components.get('risk', 50)
            if risk > 65:
                risk_msg = "high risk conditions"
                risk_detail = "suggesting potential for sharp reversals"
            elif risk < 35:
                risk_msg = "favorable risk conditions"
                risk_detail = "supporting sustainable price action"
            else:
                risk_msg = "moderate risk conditions"
                risk_detail = "with balanced risk/reward profile"
            
            # Add funding rate insight with more details
            funding_rate = components.get('funding_rate', 50)
            if funding_rate > 65:
                funding_msg = "positive funding rates indicating long bias"
                funding_detail = "showing market willingness to pay premiums for long positions"
            elif funding_rate < 35:
                funding_msg = "negative funding rates indicating short bias"
                funding_detail = "signaling bearish positioning in the futures market"
            else:
                funding_msg = "neutral funding rates"
                funding_detail = "indicating balanced long/short positioning"
            
            # Compose the initial message
            message = f"{sentiment_msg} with {risk_msg} and {funding_msg}"
            
            # Add detailed risk and funding context
            message += f". {risk_detail}, {funding_detail}"
            
            # Add long/short ratio insight with more context
            lsr = components.get('long_short_ratio', 50)
            if lsr > 60:
                message += ". Traders positioned primarily long"
                if lsr > 75:
                    message += ", showing potential crowding on the bullish side which may indicate a contrarian signal"
                else:
                    message += ", confirming directional bias with moderate conviction"
            elif lsr < 40:
                message += ". Traders positioned primarily short"
                if lsr < 25: 
                    message += ", showing extreme bearish positioning which may act as a contrarian signal"
                else:
                    message += ", indicating moderate bearish conviction"
            
            # Add market activity insight
            market_activity = components.get('market_activity', 50)
            if market_activity > 65:
                message += ". Very high market activity with strong participation (bullish)"
                if funding_rate > 60:
                    message += ", reinforcing bullish conviction across market segments"
            elif market_activity < 35:
                message += ". Low market activity showing limited participation (cautious)"
                if funding_rate < 40:
                    message += ", suggesting a hesitant market backdrop for new positions"
            
            # Add volatility context
            volatility = components.get('volatility', 50)
            if volatility > 65:
                message += ". Market showing above-average volatility"
                if risk > 60:
                    message += ", increasing both opportunity and risk factors"
            elif volatility < 35:
                message += ". Market showing below-average volatility"
                if score > 55 or score < 45:
                    message += ", which may precede a volatility expansion"
            
            # Add market mood insight with more detail
            mood = components.get('market_mood', 50)
            if mood > 60 and score < 50:
                message += ". Sentiment diverging from market mood, suggesting potential reversal to the upside"
                if lsr < 40:
                    message += " with shorts potentially vulnerable to a squeeze"
            elif mood < 40 and score > 50:
                message += ". Sentiment diverging from market mood, suggesting potential reversal to the downside"
                if lsr > 60:
                    message += " with longs potentially vulnerable to profit-taking"
            
            # Add social sentiment if available
            social = components.get('social_sentiment', 50)
            if social > 65:
                message += ". Social media sentiment notably bullish, typically a forward-looking indicator"
            elif social < 35:
                message += ". Social media sentiment notably bearish, may indicate negative retail sentiment"
            
            # Add probabilistic context to make interpretation more actionable
            component_confidence = {name: score for name, score in components.items()} if components else None
            enhanced_message = self._add_probabilistic_context(message, score, component_confidence)
            
            return enhanced_message
            
        except Exception as e:
            self.logger.error(f"Error generating sentiment interpretation: {str(e)}")
            return "Unable to analyze sentiment: an error occurred"
    
    def _interpret_price_structure(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for price structure analysis component."""
        # Extract key values
        score = data.get('score', 50)
        components = data.get('components', {})
        signals = data.get('signals', {})
        raw_values = data.get('metadata', {}).get('raw_values', {})
        
        # Get trend signals with enhanced analysis
        trend_signal = signals.get('trend', {})
        
        # Safe conversion of values that might be descriptive strings
        def safe_float_convert(value, default=50):
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    # Handle descriptive strings
                    strength_map = {
                        'strong': 0.8,
                        'moderate': 0.5,
                        'weak': 0.3,
                        'very_strong': 0.9,
                        'very_weak': 0.1
                    }
                    return strength_map.get(value.lower(), default)
            return default
        
        # Safely extract trend data
        if isinstance(trend_signal, dict):
            trend_value = safe_float_convert(trend_signal.get('value', 50))
            trend_type = trend_signal.get('signal', 'neutral')
            trend_strength = safe_float_convert(trend_signal.get('strength', 0.5))
        else:
            # If trend_signal is a string, use it as trend_type
            trend_value = 50
            trend_type = str(trend_signal) if trend_signal else 'neutral'
            trend_strength = 0.5
        
        # Get support/resistance signals with enhanced context
        sr_signal = signals.get('support_resistance', {})
        if isinstance(sr_signal, dict):
            sr_value = safe_float_convert(sr_signal.get('value', 50))
            sr_type = sr_signal.get('signal', 'neutral')
            sr_bias = sr_signal.get('bias', 'neutral')
            sr_distance = safe_float_convert(sr_signal.get('distance', 0))
        else:
            sr_value = 50
            sr_type = str(sr_signal) if sr_signal else 'neutral'
            sr_bias = 'neutral'
            sr_distance = 0
        
        # Get order block signals with enhanced detail
        ob_signal = signals.get('orderblock', {})
        if isinstance(ob_signal, dict):
            ob_value = safe_float_convert(ob_signal.get('value', 50))
            ob_type = ob_signal.get('signal', 'neutral')
            ob_bias = ob_signal.get('bias', 'neutral')
            ob_strength = safe_float_convert(ob_signal.get('strength', 0.5))
        else:
            ob_value = 50
            ob_type = str(ob_signal) if ob_signal else 'neutral'
            ob_bias = 'neutral'
            ob_strength = 0.5
        
        # Start with detailed trend description
        if trend_type == 'uptrend':
            if trend_strength > 0.7:
                message = "Price structure shows strong established uptrend with consistent higher highs and higher lows"
            else:
                message = "Price structure shows developing uptrend with emerging higher highs and higher lows"
        elif trend_type == 'downtrend':
            if trend_strength > 0.7:
                message = "Price structure shows strong established downtrend with consistent lower highs and lower lows"
            else:
                message = "Price structure shows developing downtrend with emerging lower highs and lower lows"
        elif trend_type == 'sideways':
            message = "Price structure indicates sideways consolidation within a defined range"
            # Add range characterization
            range_width = safe_float_convert(components.get('range_width', 50))
            if range_width > 65:
                message += ", showing wide choppy price action suggesting accumulation/distribution"
            elif range_width < 35:
                message += ", showing tight price action suggesting coiling for potential breakout"
        else:
            if score > 55:
                message = "Price structure has a bullish bias without clear trend definition"
            elif score < 45:
                message = "Price structure has a bearish bias without clear trend definition"
            else:
                message = "Price structure is neutral, showing balanced forces without clear direction"
        
        # Add support/resistance insight with enhanced trading context
        if sr_type == 'strong_level' and sr_bias == 'bullish':
            message += f". Strong support level identified"
            if sr_distance < 0.05:
                message += " very close to current price, providing immediate price floor"
            elif sr_distance < 0.1:
                message += " nearby, potentially limiting downside risk"
        elif sr_type == 'strong_level' and sr_bias == 'bearish':
            message += f". Strong resistance level identified"
            if sr_distance < 0.05:
                message += " very close to current price, potentially capping upside movement"
            elif sr_distance < 0.1:
                message += " overhead, representing significant barrier to upward movement"
        elif sr_type == 'weak_level' and sr_bias == 'bullish':
            message += f". Minor support level identified"
            if sr_distance < 0.05:
                message += ", which may only provide temporary support on downward moves"
        elif sr_type == 'weak_level' and sr_bias == 'bearish':
            message += f". Minor resistance level identified"
            if sr_distance < 0.05:
                message += ", which may be overcome on strong upward momentum"
        
        # Add order block insight with enhanced institutional context
        if ob_type == 'strong' and ob_bias == 'bullish':
            message += f". Strong bullish order block detected - significant support zone"
            if ob_strength > 0.7:
                message += " likely representing institutional buying interest"
            message += ", watch for potential reaction if price revisits this area"
        elif ob_type == 'strong' and ob_bias == 'bearish':
            message += f". Strong bearish order block detected - significant resistance zone"
            if ob_strength > 0.7:
                message += " likely representing institutional selling interest"
            message += ", watch for potential reaction if price revisits this area"
        elif ob_type == 'weak' and (ob_bias == 'bullish' or ob_bias == 'bearish'):
            message += f". Weak {ob_bias} order block detected with minor significance"
        
        # Add VWAP insight with enhanced intraday context
        vwap = safe_float_convert(components.get('vwap', 50))
        if vwap > 65:
            message += ". Price well above VWAP showing strong intraday buying pressure"
            if trend_type == 'uptrend':
                message += ", reinforcing the bullish trend bias"
        elif vwap < 35:
            message += ". Price well below VWAP showing strong intraday selling pressure"
            if trend_type == 'downtrend':
                message += ", reinforcing the bearish trend bias"
        elif 45 <= vwap <= 55:
            message += ". Price oscillating near VWAP indicating equilibrium between buyers and sellers"
        
        # Add market structure insight with swing analysis
        ms = safe_float_convert(components.get('market_structure', 50))
        if ms > 65:
            message += ". Higher highs and higher lows confirming bullish structure"
            swing_strength = safe_float_convert(components.get('swing_strength', 50))
            if swing_strength > 65:
                message += " with strong swing momentum, suggesting trend continuation"
        elif ms < 35:
            message += ". Lower highs and lower lows confirming bearish structure"
            swing_strength = safe_float_convert(components.get('swing_strength', 50))
            if swing_strength > 65:
                message += " with strong swing momentum, suggesting trend continuation"
        elif 45 <= ms <= 55:
            message += ". Mixed swing structure without clear directional bias"
        
        # Add range analysis insight with RektProof PA and Hsaka strategy context
        range_analysis = safe_float_convert(components.get('range_analysis', 50))
        range_signal = signals.get('range_analysis', {})
        
        if isinstance(range_signal, dict):
            range_bias = range_signal.get('bias', 'neutral')
            range_strength = range_signal.get('strength', 'moderate')
            range_signal_type = range_signal.get('signal', 'neutral_range')
            
            if range_analysis > 65:
                if range_bias == 'bullish':
                    message += f". Range analysis shows strong bullish bias - price positioned in lower quarters"
                    if range_signal_type == 'bullish_range':
                        message += " with sweep/MSB confirmation, suggesting upward movement from range"
                elif range_bias == 'bearish':
                    message += f". Range analysis shows strong bearish bias - price positioned in upper quarters"
                    if range_signal_type == 'bearish_range':
                        message += " with sweep/MSB confirmation, suggesting downward movement from range"
            elif range_analysis < 35:
                if range_bias == 'bearish':
                    message += f". Range analysis shows strong bearish structure - price vulnerable in upper range"
                elif range_bias == 'bullish':
                    message += f". Range analysis shows strong bullish structure - price supported in lower range"
            elif 45 <= range_analysis <= 55:
                message += f". Range analysis neutral - price in mid-range with no clear directional bias"
                if range_signal_type == 'neutral_range':
                    message += ", suggesting consolidation or accumulation/distribution phase"
        elif range_analysis > 60:
            message += f". Range analysis favors bullish bias with price positioned favorably for upward movement"
        elif range_analysis < 40:
            message += f". Range analysis favors bearish bias with price positioned for potential downward movement"
        
        # Add pattern recognition if available
        patterns = signals.get('patterns', [])
        if patterns and len(patterns) > 0:
            top_pattern = patterns[0]
            pattern_name = top_pattern.get('name', '')
            pattern_type = top_pattern.get('type', '')
            pattern_reliability = safe_float_convert(top_pattern.get('reliability', 0.5))
            
            if pattern_name and pattern_type:
                pattern_desc = f". {pattern_name} pattern detected"
                if pattern_type == 'reversal' and pattern_reliability > 0.7:
                    pattern_desc += f" suggesting high-probability trend reversal"
                elif pattern_type == 'continuation' and pattern_reliability > 0.7:
                    pattern_desc += f" suggesting high-probability trend continuation"
                elif pattern_type == 'reversal':
                    pattern_desc += f" suggesting potential trend reversal"
                elif pattern_type == 'continuation':
                    pattern_desc += f" suggesting potential trend continuation"
                
                message += pattern_desc
        
        # Add liquidity zones if available
        liquidity_zones = components.get('liquidity_zones', [])
        if isinstance(liquidity_zones, list) and len(liquidity_zones) > 0:
            top_zone = liquidity_zones[0]
            if isinstance(top_zone, dict):
                zone_type = top_zone.get('type', '')
                zone_distance = safe_float_convert(top_zone.get('distance', 0))
                
                if zone_type == 'buy_side' and zone_distance < 0.1:
                    message += ". Buy-side liquidity zone detected below current price, potential target for price discovery"
                elif zone_type == 'sell_side' and zone_distance < 0.1:
                    message += ". Sell-side liquidity zone detected above current price, potential target for price discovery"
        
        # Add divergence insights with enhanced implications
        divergences = data.get('divergences', {})
        if divergences:
            # Get strongest divergence
            strongest_div = None
            max_strength = 0
            
            for div_name, div_data in divergences.items():
                strength = safe_float_convert(div_data.get('strength', 0))
                if strength > max_strength:
                    max_strength = strength
                    strongest_div = div_data
            
            if strongest_div and max_strength > 40:
                div_type = strongest_div.get('type', 'neutral')
                div_component = strongest_div.get('component', '')
                div_tf = strongest_div.get('timeframe', '')
                
                if div_tf and div_component:
                    div_message = f". {div_type.capitalize()} divergence detected in {div_tf.upper()} {div_component.replace('_', ' ')}"
                    if div_type == 'bullish' and trend_type == 'downtrend':
                        div_message += ", suggesting potential trend exhaustion and reversal opportunity"
                    elif div_type == 'bearish' and trend_type == 'uptrend':
                        div_message += ", suggesting potential trend exhaustion and reversal opportunity"
                    message += div_message
        
        # Add key level confluence if multiple supports/resistances align
        key_level_confluence = components.get('key_level_confluence', None)
        if key_level_confluence is not None:
            key_level_float = safe_float_convert(key_level_confluence)
            if key_level_float > 65:
                message += ". Multiple technical levels aligning at similar price points, creating a high-significance zone"
        
        # Add breakout/breakdown potential assessment
        if (trend_type == 'sideways' or trend_type == 'neutral') and sr_type == 'strong_level':
            range_compression = safe_float_convert(components.get('range_compression', 50))
            if range_compression > 65:
                message += ". Price compressed near range boundary, suggesting imminent breakout potential"
            volatility_contraction = components.get('volatility_contraction', None)
            if volatility_contraction is not None:
                volatility_float = safe_float_convert(volatility_contraction)
                if volatility_float > 65:
                    message += ". Significant volatility contraction observed, often preceding explosive moves"
        
        # Add probabilistic context to make interpretation more actionable
        component_confidence = {name: score for name, score in components.items() if isinstance(score, (int, float))}
        enhanced_message = self._add_probabilistic_context(message, score, component_confidence)
        return enhanced_message
    
    def _get_default_interpretation(self, component_name: str, data: Dict[str, Any]) -> str:
        """Provide a fallback interpretation for unknown components."""
        # Try to extract any existing interpretation
        if isinstance(data, dict):
            if 'interpretation' in data:
                interp = data['interpretation']
                if isinstance(interp, str):
                    return interp
                elif isinstance(interp, dict) and 'summary' in interp:
                    return interp['summary']
            
            # Extract score and determine general leaning
            score = data.get('score', 50)
            if score > 60:
                return f"{component_name.replace('_', ' ').title()} showing bullish indications ({score:.2f})"
            elif score < 40:
                return f"{component_name.replace('_', ' ').title()} showing bearish indications ({score:.2f})"
            else:
                return f"{component_name.replace('_', ' ').title()} is currently neutral ({score:.2f})"
        
        # Extremely basic fallback
        return f"{component_name.replace('_', ' ').title()}: No detailed interpretation available"
    
    def _analyze_timeframes(self, timeframe_scores: Dict[str, Dict[str, float]]) -> str:
        """Analyze scores across different timeframes for insights."""
        # Check for significant divergences between timeframes
        if not all(tf in timeframe_scores for tf in ['base', 'ltf', 'mtf', 'htf']):
            return ""
        
        base_avg = self._average_components(timeframe_scores.get('base', {}))
        ltf_avg = self._average_components(timeframe_scores.get('ltf', {}))
        mtf_avg = self._average_components(timeframe_scores.get('mtf', {}))
        htf_avg = self._average_components(timeframe_scores.get('htf', {}))
        
        # Look for significant divergences
        if htf_avg > 65 and ltf_avg < 35:
            return "Higher timeframes bullish while lower timeframes bearish - potential short-term pullback in larger uptrend"
        elif htf_avg < 35 and ltf_avg > 65:
            return "Higher timeframes bearish while lower timeframes bullish - potential short-term bounce in larger downtrend"
        elif abs(mtf_avg - ltf_avg) > 25:
            if mtf_avg > ltf_avg:
                return "Medium timeframe stronger than lower timeframe - trend may be strengthening"
            else:
                return "Lower timeframe stronger than medium timeframe - watch for possible trend shift"
        
        return ""
    
    def _average_components(self, component_dict: Dict[str, float]) -> float:
        """Calculate the average score of component dictionary values."""
        if not component_dict:
            return 50.0
        
        values = [v for v in component_dict.values() if isinstance(v, (int, float))]
        if not values:
            return 50.0
        
        return sum(values) / len(values)
    
    def generate_cross_component_insights(self, results: Dict[str, Any]) -> List[str]:
        """
        Generate insights by analyzing relationships between different components.
        
        Args:
            results: Complete analysis results with all components
            
        Returns:
            List[str]: List of cross-component insights
        """
        insights = []
        
        # Extract key component scores for easier reference
        technical_score = results.get('technical', {}).get('score', 50)
        volume_score = results.get('volume', {}).get('score', 50)
        orderbook_score = results.get('orderbook', {}).get('score', 50)
        orderflow_score = results.get('orderflow', {}).get('score', 50)
        sentiment_score = results.get('sentiment', {}).get('score', 50)
        price_structure_score = results.get('price_structure', {}).get('score', 50)
        
        # Check for significant divergences between components
        
        # Technical vs Orderflow divergence
        if abs(technical_score - orderflow_score) > 25:
            if technical_score > 60 and orderflow_score < 40:
                insights.append("Conflicting signals: Technical indicators bullish while orderflow bearish - possible distribution phase")
            elif technical_score < 40 and orderflow_score > 60:
                insights.append("Conflicting signals: Technical indicators bearish while orderflow bullish - possible accumulation phase")
        
        # Price Structure vs Volume divergence
        if price_structure_score > 60 and volume_score < 40:
            insights.append("Price structure bullish with weak volume support - watch for potential failed breakout")
        elif price_structure_score < 40 and volume_score > 60:
            insights.append("Price structure bearish despite strong volume - possible capitulation or reversal brewing")
        
        # Sentiment vs Technical divergence
        if abs(sentiment_score - technical_score) > 20:
            if sentiment_score > 60 and technical_score < 40:
                insights.append("Market sentiment remains bullish despite bearish technicals - potential complacency")
            elif sentiment_score < 40 and technical_score > 60:
                insights.append("Market sentiment bearish despite bullish technicals - potential opportunity")
        
        # Orderbook vs Price Structure convergence
        if orderbook_score > 60 and price_structure_score > 60:
            insights.append("Strong orderbook support aligned with bullish price structure - reinforced bullish case")
        elif orderbook_score < 40 and price_structure_score < 40:
            insights.append("Weak orderbook support aligned with bearish price structure - reinforced bearish case")
        
        # Technical and Volume confirmation
        tech_trend = results.get('technical', {}).get('signals', {}).get('trend', 'neutral')
        vol_profile = results.get('volume', {}).get('signals', {}).get('volume_profile', {}).get('signal', 'neutral')
        
        if tech_trend == 'bullish' and vol_profile == 'bullish':
            insights.append("Technical trend confirmed by volume profile - strong bullish confluence")
        elif tech_trend == 'bearish' and vol_profile == 'bearish':
            insights.append("Technical trend confirmed by volume profile - strong bearish confluence")
        elif tech_trend == 'bullish' and vol_profile == 'bearish':
            insights.append("Bullish technical trend with bearish volume profile - potential trend exhaustion")
        elif tech_trend == 'bearish' and vol_profile == 'bullish':
            insights.append("Bearish technical trend with bullish volume profile - potential trend exhaustion")
        
        # Orderflow and Sentiment alignment
        if orderflow_score > 60 and sentiment_score > 60:
            insights.append("Bullish orderflow aligned with positive sentiment - strong buying conviction")
        elif orderflow_score < 40 and sentiment_score < 40:
            insights.append("Bearish orderflow aligned with negative sentiment - strong selling conviction")
        
        return insights
    
    def generate_actionable_insights(self, results: Dict[str, Any], confluence_score: float, 
                                    buy_threshold: float = 65, sell_threshold: float = 35) -> List[str]:
        """
        Generate actionable trading insights based on the overall analysis.
        
        Args:
            results: Complete analysis results with all components
            confluence_score: The overall confluence score
            buy_threshold: Score threshold for buy signals
            sell_threshold: Score threshold for sell signals
            
        Returns:
            List[str]: List of actionable trading insights
        """
        insights = []
        
        # Determine overall market bias
        if confluence_score >= buy_threshold:
            insights.append(f"BULLISH BIAS: Overall confluence score ({confluence_score:.2f}) above buy threshold ({buy_threshold})")
        elif confluence_score <= sell_threshold:
            insights.append(f"BEARISH BIAS: Overall confluence score ({confluence_score:.2f}) below sell threshold ({sell_threshold})")
        else:
            # Calculate how close we are to thresholds
            buy_distance = buy_threshold - confluence_score
            sell_distance = confluence_score - sell_threshold
            
            if buy_distance < 10:
                insights.append(f"NEUTRAL-BULLISH BIAS: Score ({confluence_score:.2f}) approaching buy threshold - monitor for confirmation")
            elif sell_distance < 10:
                insights.append(f"NEUTRAL-BEARISH BIAS: Score ({confluence_score:.2f}) approaching sell threshold - monitor for confirmation")
            else:
                insights.append(f"NEUTRAL STANCE: Range-bound conditions likely - consider mean-reversion strategies")
        
        # Add risk assessment
        risk_level = self._assess_risk(results)
        risk_recommendation = self._get_risk_recommendation(risk_level, confluence_score)
        insights.append(f"RISK ASSESSMENT: {risk_level} - {risk_recommendation}")
        
        # Identify key price levels
        key_levels = self._identify_key_levels(results)
        if key_levels:
            insights.append(f"KEY LEVELS: {key_levels}")
        
        # Timing insights
        timing_insight = self._generate_timing_insight(results)
        if timing_insight:
            insights.append(f"TIMING: {timing_insight}")
        
        # Strategy recommendation
        strategy = self._recommend_strategy(results, confluence_score, buy_threshold, sell_threshold)
        if strategy:
            insights.append(f"STRATEGY: {strategy}")
        
        return insights
    
    def _assess_risk(self, results: Dict[str, Any]) -> str:
        """Assess the overall risk level based on analysis components."""
        # Check for explicit risk component in sentiment
        sentiment = results.get('sentiment', {})
        if 'risk' in sentiment.get('components', {}):
            risk_score = sentiment['components']['risk']
            if risk_score > 65:
                return "HIGH"
            elif risk_score < 35:
                return "LOW"
            else:
                return "MODERATE"
        
        # Calculate risk based on multiple factors
        risk_factors = []
        
        # Volatility factor (from technical)
        technical = results.get('technical', {})
        if 'components' in technical and 'atr' in technical['components']:
            atr_score = technical['components']['atr']
            risk_factors.append(2 if atr_score > 65 else 1 if atr_score > 45 else 0)
        
        # Liquidity factor (from orderbook)
        orderbook = results.get('orderbook', {})
        if 'components' in orderbook and 'liquidity' in orderbook['components']:
            liquidity_score = orderbook['components']['liquidity']
            risk_factors.append(0 if liquidity_score > 65 else 1 if liquidity_score > 45 else 2)
        
        # Sentiment risk
        sentiment = results.get('sentiment', {})
        if 'score' in sentiment:
            sent_score = sentiment['score']
            # Extreme sentiment in either direction can indicate risk
            risk_factors.append(1 if 40 <= sent_score <= 60 else 2)
        
        # Calculate average risk
        if not risk_factors:
            return "MODERATE"  # Default
        
        avg_risk = sum(risk_factors) / len(risk_factors)
        if avg_risk > 1.5:
            return "HIGH"
        elif avg_risk < 0.7:
            return "LOW"
        else:
            return "MODERATE"
    
    def _get_risk_recommendation(self, risk_level: str, confluence_score: float) -> str:
        """Generate risk management recommendations based on risk level."""
        if risk_level == "HIGH":
            if confluence_score > 60:
                return "Reduce position size despite bullish bias and use tighter stops"
            elif confluence_score < 40:
                return "Reduce position size despite bearish bias and use tighter stops"
            else:
                return "Avoid new positions until risk conditions improve"
        elif risk_level == "LOW":
            if confluence_score > 60:
                return "Standard or slightly larger position size appropriate for bullish strategies"
            elif confluence_score < 40:
                return "Standard or slightly larger position size appropriate for bearish strategies"
            else:
                return "Favorable conditions for mean-reversion strategies with standard position sizing"
        else:  # MODERATE
            return "Standard position sizing recommended with normal stop distances"
    
    def _identify_key_levels(self, results: Dict[str, Any]) -> str:
        """Identify and describe key price levels from the analysis."""
        key_levels = []
        
        # Check price structure for support/resistance
        price_structure = results.get('price_structure', {})
        signals = price_structure.get('signals', {})
        
        # Support/Resistance
        sr_signal = signals.get('support_resistance', {})
        if isinstance(sr_signal, dict) and 'value' in sr_signal:
            try:
                sr_value = float(sr_signal['value'])
                if sr_value > 50:
                    level_type = sr_signal.get('bias', 'neutral')
                    strength = sr_signal.get('strength', 'moderate')  # This can be a string like 'moderate'
                    
                    if level_type == 'bullish':
                        key_levels.append(f"Support level ({strength} strength)")
                    elif level_type == 'bearish':
                        key_levels.append(f"Resistance level ({strength} strength)")
            except (ValueError, TypeError):
                # Handle case where value can't be converted to float
                pass
        
        # Order blocks
        ob_signal = signals.get('orderblock', {})
        if isinstance(ob_signal, dict) and 'value' in ob_signal:
            try:
                ob_value = float(ob_signal['value'])
                if ob_value > 60:
                    ob_type = ob_signal.get('bias', 'neutral')
                    
                    if ob_type == 'bullish':
                        key_levels.append(f"Bullish order block (potential support)")
                    elif ob_type == 'bearish':
                        key_levels.append(f"Bearish order block (potential resistance)")
            except (ValueError, TypeError):
                # Handle case where value can't be converted to float
                pass
        
        # Orderbook liquidity levels
        orderbook = results.get('orderbook', {})
        components = orderbook.get('components', {})
        
        if 'liquidity' in components:
            try:
                liquidity = float(components['liquidity'])
                if liquidity > 65:
                    liquidity_type = "bid" if orderbook.get('score', 50) > 55 else "ask"
                    key_levels.append(f"Strong {liquidity_type} liquidity cluster")
            except (ValueError, TypeError):
                # Handle case where liquidity can't be converted to float
                pass
        
        if not key_levels:
            return ""
        
        return ", ".join(key_levels)
    
    def _generate_timing_insight(self, results: Dict[str, Any]) -> str:
        """Generate insights about timing of potential trades."""
        # Check for oversold/overbought conditions
        technical = results.get('technical', {})
        components = technical.get('components', {})
        
        if 'rsi' in components and components['rsi'] < 30:
            return "Potential oversold condition; watch for reversal confirmation"
        elif 'rsi' in components and components['rsi'] > 70:
            return "Potential overbought condition; watch for reversal confirmation"
        
        # Check for momentum signals
        if 'macd' in components and components['macd'] > 60:
            return "Bullish momentum building; favorable for trend-following entries"
        elif 'macd' in components and components['macd'] < 40:
            return "Bearish momentum building; favorable for trend-following entries"
        
        # Check orderflow for exhaustion
        orderflow = results.get('orderflow', {})
        if 'pressure_score' in orderflow.get('components', {}) and orderflow['components']['pressure_score'] < 30:
            return "Declining sell pressure; potential for reversal"
        elif 'pressure_score' in orderflow.get('components', {}) and orderflow['components']['pressure_score'] > 70:
            return "Strong buying pressure; favorable timing for bullish strategies"
        
        return ""
    
    def _recommend_strategy(self, results: Dict[str, Any], confluence_score: float, 
                           buy_threshold: float, sell_threshold: float) -> str:
        """Recommend specific trading strategies based on the analysis."""
        technical = results.get('technical', {})
        trend = technical.get('signals', {}).get('trend', 'neutral')
        
        # Strong trend strategies
        if confluence_score >= buy_threshold:
            if trend == 'bullish':
                return "Consider breakout entries above local resistance with trailing stops"
            return "Consider bullish strategies: swing longs or breakouts with defined risk"
        elif confluence_score <= sell_threshold:
            if trend == 'bearish':
                return "Consider breakdown entries below local support with trailing stops"
            return "Consider bearish strategies: swing shorts or breakdowns with defined risk"
        
        # Range/neutral strategies
        price_structure = results.get('price_structure', {})
        sr_signal = price_structure.get('signals', {}).get('support_resistance', {})
        
        if isinstance(sr_signal, dict) and 'value' in sr_signal and sr_signal['value'] > 60:
            return "Range-bound conditions likely; consider mean-reversion trades at support/resistance levels"
        
        # Volatility-based strategies
        atr = technical.get('components', {}).get('atr', 50)
        if atr < 35:
            return "Low volatility environment; consider breakout anticipation strategies or premium collection"
        elif atr > 65:
            return "High volatility environment; consider wider stops and reduced position sizing"
        
        return "Monitor for further confirmation before implementing directional strategies"
    
    def _add_probabilistic_context(self, base_message: str, score: float, component_confidence: Dict[str, float] = None) -> str:
        """
        Enhance interpretation with probabilistic language and confidence levels.
        
        Args:
            base_message: The basic interpretation message
            score: The component score (0-100)
            component_confidence: Optional confidence metrics for components
            
        Returns:
            Enhanced message with probability and confidence information
        """
        try:
            # Calculate probability based on score distance from neutral (50)
            score_deviation = abs(score - 50)
            
            # Convert score to probability (more extreme scores = higher probability)
            if score > 50:
                # Bullish probability
                probability = 50 + (score_deviation * 0.8)  # Max ~90% probability
                direction = "upward movement"
                bias = "bullish"
            else:
                # Bearish probability  
                probability = 50 + (score_deviation * 0.8)  # Max ~90% probability
                direction = "downward movement"
                bias = "bearish"
            
            # Calculate confidence based on component alignment
            confidence = self._calculate_interpretation_confidence(score, component_confidence)
            
            # Generate probability language
            prob_language = self._get_probability_language(probability)
            conf_language = self._get_confidence_language(confidence)
            
            # Enhance the base message
            enhanced_message = f"{base_message}. "
            
            # Add probabilistic context
            if score_deviation > 15:  # Only add for significant deviations
                enhanced_message += f"Analysis suggests {prob_language} of {direction} "
                enhanced_message += f"with {conf_language} confidence ({confidence:.0f}%)"
            
            return enhanced_message
            
        except Exception as e:
            self.logger.error(f"Error adding probabilistic context: {str(e)}")
            return base_message  # Return original message if enhancement fails
    
    def _calculate_interpretation_confidence(self, score: float, component_confidence: Dict[str, float] = None) -> float:
        """Calculate confidence level for interpretation."""
        try:
            # Base confidence from score certainty
            score_deviation = abs(score - 50)
            base_confidence = min(90, 60 + score_deviation)  # 60-90% range
            
            # Adjust based on component alignment if available
            if component_confidence:
                # Higher confidence when components agree
                component_std = np.std(list(component_confidence.values())) if len(component_confidence) > 1 else 0
                alignment_bonus = max(-10, 10 - component_std)  # Penalty for divergent components
                base_confidence += alignment_bonus
            
            return max(55, min(95, base_confidence))  # Clamp to reasonable range
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence score: {str(e)}", exc_info=True)
            return 75.0  # Default moderate confidence
    
    def _get_probability_language(self, probability: float) -> str:
        """Convert probability to natural language."""
        if probability >= 80:
            return "high probability (>80%)"
        elif probability >= 70:
            return "strong likelihood (~75%)"  
        elif probability >= 60:
            return "moderate probability (~65%)"
        elif probability >= 55:
            return "slight probability (~60%)"
        else:
            return "uncertain probability"
    
    def _get_confidence_language(self, confidence: float) -> str:
        """Convert confidence to natural language."""
        if confidence >= 90:
            return "very high"
        elif confidence >= 80:
            return "high"
        elif confidence >= 70:
            return "moderate"
        elif confidence >= 60:
            return "fair"
        else:
            return "low"
    
    # Dependency injection helper methods
    
    def _validate_input_data(self, data: Any, data_type: str = "component_data") -> bool:
        """
        Validate input data using injected validator service.
        
        Args:
            data: Data to validate
            data_type: Type of data being validated
            
        Returns:
            True if valid, False otherwise
        """
        if self._validator is None:
            # Basic validation if no validator injected
            return isinstance(data, dict) and len(data) > 0
        
        try:
            # Use injected validator service
            validation_rules = {
                'required_fields': ['score'] if data_type == "component_data" else [],
                'data_type': dict,
                'min_length': 1
            }
            return self._validator.validate_data(data, validation_rules)
        except Exception as e:
            self.logger.warning(f"Validation failed for {data_type}: {e}")
            return False
    
    def _format_score(self, score: float, precision: int = 1) -> str:
        """
        Format score using injected formatter service.
        
        Args:
            score: Score to format
            precision: Decimal precision
            
        Returns:
            Formatted score string
        """
        if self._formatter is None:
            # Basic formatting if no formatter injected
            return f"{score:.{precision}f}"
        
        try:
            return self._formatter.format_number(score, precision, use_thousands_separator=False)
        except Exception as e:
            self.logger.warning(f"Formatting failed for score {score}: {e}")
            return f"{score:.{precision}f}"
    
    def _format_percentage(self, value: float, precision: int = 1) -> str:
        """
        Format percentage using injected formatter service.
        
        Args:
            value: Value to format as percentage
            precision: Decimal precision
            
        Returns:
            Formatted percentage string
        """
        if self._formatter is None:
            # Basic formatting if no formatter injected
            return f"{value:.{precision}f}%"
        
        try:
            # Convert to percentage (0.65 -> 65%)
            return self._formatter.format_percentage(value / 100, precision)
        except Exception as e:
            self.logger.warning(f"Percentage formatting failed for {value}: {e}")
            return f"{value:.{precision}f}%"
    
    # IInterpretationService interface implementation
    
    def generate_interpretation(
        self, 
        component_name: str, 
        analysis_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate interpretation for analysis data (IInterpretationService interface).
        
        Args:
            component_name: Name of the component being analyzed
            analysis_data: Analysis data to interpret
            context: Optional context information
            
        Returns:
            Generated interpretation string
        """
        return self.get_component_interpretation(component_name, analysis_data)
    
    def generate_cross_component_interpretation(
        self, 
        components_data: Dict[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate cross-component interpretations (IInterpretationService interface).
        
        Args:
            components_data: Data for all components
            context: Optional context information
            
        Returns:
            List of cross-component insights
        """
        return self.generate_cross_component_insights(components_data)
    
    def generate_actionable_summary(
        self, 
        analysis_results: Dict[str, Any],
        confluence_score: float,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate actionable summary (IInterpretationService interface).
        
        Args:
            analysis_results: Complete analysis results
            confluence_score: Overall confluence score
            context: Optional context information
            
        Returns:
            List of actionable insights
        """
        # Extract thresholds from context or use defaults
        buy_threshold = 65
        sell_threshold = 35
        
        if context:
            buy_threshold = context.get('buy_threshold', 65)
            sell_threshold = context.get('sell_threshold', 35)
        
        return self.generate_actionable_insights(
            analysis_results, 
            confluence_score, 
            buy_threshold, 
            sell_threshold
        )
    
    # Additional IInterpretationService interface methods
    
    def get_market_interpretation(self, analysis_result: Dict[str, Any]) -> str:
        """Generate interpretation for overall market analysis."""
        try:
            # Extract overall score
            overall_score = analysis_result.get('confluence_score', 50)
            components = analysis_result.get('components', {})
            
            # Generate market-level interpretation
            if overall_score > 70:
                sentiment = "strongly bullish"
            elif overall_score > 60:
                sentiment = "moderately bullish"
            elif overall_score < 30:
                sentiment = "strongly bearish"
            elif overall_score < 40:
                sentiment = "moderately bearish"
            else:
                sentiment = "neutral"
            
            interpretation = f"Market analysis indicates {sentiment} conditions with confluence score of {overall_score:.1f}"
            
            # Add component summary
            if components:
                strong_components = [name for name, data in components.items() 
                                   if isinstance(data, dict) and data.get('score', 50) > 65]
                if strong_components:
                    interpretation += f". Strong signals from: {', '.join(strong_components)}"
            
            return interpretation
            
        except Exception as e:
            self.logger.error(f"Error generating market interpretation: {e}")
            return "Unable to generate market interpretation"
    
    def get_signal_interpretation(self, signal_data: Dict[str, Any]) -> str:
        """Generate interpretation for trading signals."""
        try:
            signal_type = signal_data.get('signal', 'NEUTRAL')
            score = signal_data.get('score', 50)
            confidence = signal_data.get('confidence', 'moderate')
            
            if signal_type == 'BUY':
                return f"BUY signal detected with {confidence} confidence (score: {score:.1f})"
            elif signal_type == 'SELL':
                return f"SELL signal detected with {confidence} confidence (score: {score:.1f})"
            else:
                return f"NEUTRAL signal - no clear directional bias (score: {score:.1f})"
                
        except Exception as e:
            self.logger.error(f"Error generating signal interpretation: {e}")
            return "Unable to interpret trading signal"
    
    def get_indicator_interpretation(self, indicator_name: str, values: Dict[str, float]) -> str:
        """Generate interpretation for specific indicator values."""
        try:
            if indicator_name.lower() == 'rsi':
                rsi_value = values.get('rsi', 50)
                if rsi_value > 70:
                    return f"RSI ({rsi_value:.1f}) indicates overbought conditions"
                elif rsi_value < 30:
                    return f"RSI ({rsi_value:.1f}) indicates oversold conditions"
                else:
                    return f"RSI ({rsi_value:.1f}) shows neutral momentum"
            
            elif indicator_name.lower() == 'macd':
                macd = values.get('macd', 0)
                signal = values.get('signal', 0)
                if macd > signal:
                    return "MACD shows bullish momentum (above signal line)"
                else:
                    return "MACD shows bearish momentum (below signal line)"
            
            else:
                # Generic interpretation
                return f"{indicator_name} analysis: {', '.join([f'{k}={v:.2f}' for k, v in values.items()])}"
                
        except Exception as e:
            self.logger.error(f"Error interpreting {indicator_name}: {e}")
            return f"Unable to interpret {indicator_name} indicator"
    
    def set_interpretation_config(self, config: Dict[str, Any]) -> None:
        """Update interpretation configuration."""
        try:
            # Store configuration for future use
            if not hasattr(self, '_config'):
                self._config = {}
            self._config.update(config)
            self.logger.info(f"Updated interpretation config with {len(config)} settings")
        except Exception as e:
            self.logger.error(f"Error setting interpretation config: {e}") 