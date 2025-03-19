"""
Enhanced market interpretation generator for confluence analysis results.
Provides rich, context-aware interpretations across different market components.
"""

import logging
import textwrap
from typing import Dict, Any, List, Optional, Tuple

class InterpretationGenerator:
    """Generates enhanced market interpretations from confluence analysis results."""
    
    def __init__(self):
        """Initialize the interpretation generator."""
        self.logger = logging.getLogger(__name__)
    
    def get_component_interpretation(self, component_name: str, component_data: Dict[str, Any]) -> str:
        """
        Generate enhanced interpretation for a specific component.
        
        Args:
            component_name: Name of the component (technical, volume, etc.)
            component_data: The component data containing scores, signals, etc.
            
        Returns:
            str: Enhanced interpretation string
        """
        try:
            # Call the appropriate interpreter based on component name
            if component_name == 'technical':
                return self._interpret_technical(component_data)
            elif component_name == 'volume':
                return self._interpret_volume(component_data)
            elif component_name == 'orderbook':
                return self._interpret_orderbook(component_data)
            elif component_name == 'orderflow':
                return self._interpret_orderflow(component_data)
            elif component_name == 'sentiment':
                return self._interpret_sentiment(component_data)
            elif component_name == 'price_structure':
                return self._interpret_price_structure(component_data)
            else:
                # Default fallback if component doesn't have specific handler
                return self._get_default_interpretation(component_name, component_data)
        except Exception as e:
            self.logger.error(f"Error generating interpretation for {component_name}: {str(e)}")
            # Provide a reasonable fallback if interpretation fails
            return self._get_default_interpretation(component_name, component_data)
    
    def _interpret_technical(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for technical analysis component."""
        # Extract key values from the data
        trend = data.get('signals', {}).get('trend', 'neutral')
        strength = data.get('signals', {}).get('strength', 0)
        score = data.get('score', 50)
        
        # Identify strongest components
        components = data.get('components', {})
        strongest_components = sorted(components.items(), key=lambda x: x[1], reverse=True)[:2]
        
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
        
        # Add insights about strongest components
        if strongest_components:
            comp_name, comp_value = strongest_components[0]
            comp_name = comp_name.upper()
            if comp_value > 65:
                message += f". {comp_name} is significantly bullish ({comp_value:.1f})"
            elif comp_value < 35:
                message += f". {comp_name} is significantly bearish ({comp_value:.1f})"
            else:
                message += f". {comp_name} is the most influential indicator ({comp_value:.1f})"
        
        # Add divergence insights
        divergences_bearish = data.get('signals', {}).get('divergences_bearish', [])
        divergences_bullish = data.get('signals', {}).get('divergences_bullish', [])
        
        if divergences_bearish:
            message += f". Bearish divergence detected: {divergences_bearish[0]}"
        elif divergences_bullish:
            message += f". Bullish divergence detected: {divergences_bullish[0]}"
        
        # Add timeframe analysis if available
        timeframe_scores = data.get('timeframe_scores', {})
        if timeframe_scores:
            tf_insights = self._analyze_timeframes(timeframe_scores)
            if tf_insights:
                message += f". {tf_insights}"
        
        return message
    
    def _interpret_volume(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for volume analysis component."""
        # Extract key values
        score = data.get('score', 50)
        volume_sma = data.get('signals', {}).get('volume_sma', {}).get('signal', 'neutral')
        volume_trend = data.get('signals', {}).get('volume_trend', {}).get('signal', 'neutral')
        volume_profile = data.get('signals', {}).get('volume_profile', {}).get('signal', 'neutral')
        
        # Get strongest components
        components = data.get('components', {})
        strongest_component = max(components.items(), key=lambda x: x[1]) if components else None
        
        # Interpret volume patterns
        if volume_profile == 'bearish' and volume_trend == 'decreasing':
            message = "Volume analysis indicates selling pressure with declining participation"
        elif volume_profile == 'bearish' and volume_trend == 'increasing':
            message = "Volume analysis shows increasing selling pressure with rising participation"
        elif volume_profile == 'bullish' and volume_trend == 'increasing':
            message = "Volume analysis shows strong buying interest with increasing participation"
        elif volume_profile == 'bullish' and volume_trend == 'decreasing':
            message = "Volume analysis indicates weakening buying pressure with declining participation"
        elif volume_sma == 'high':
            message = "Above average volume suggests significant market interest at current levels"
        elif volume_sma == 'low':
            message = "Below average volume indicates lack of conviction in current price movement"
        else:
            message = "Volume patterns show typical market participation without clear directional bias"
        
        # Add information about strongest volume component
        if strongest_component:
            comp_name, comp_value = strongest_component
            comp_name = comp_name.upper()
            if comp_value > 70:
                message += f". {comp_name} is particularly strong ({comp_value:.1f})"
            elif comp_value < 30:
                message += f". {comp_name} is particularly weak ({comp_value:.1f})"
            else:
                message += f". {comp_name} is the most significant volume indicator ({comp_value:.1f})"
        
        # Add any additional insights about volume divergences
        raw_values = data.get('metadata', {}).get('raw_values', {})
        if raw_values:
            if 'volume_delta' in raw_values and raw_values['volume_delta'] < -0.8:
                message += ". Significant negative volume delta suggests strong selling pressure"
            elif 'volume_delta' in raw_values and raw_values['volume_delta'] > 0.8:
                message += ". Significant positive volume delta suggests strong buying pressure"
            
            if 'cmf' in raw_values:
                cmf = raw_values['cmf']
                if cmf < -0.1:
                    message += ". Money flow confirms distribution pattern"
                elif cmf > 0.1:
                    message += ". Money flow confirms accumulation pattern"
        
        return message
    
    def _interpret_orderbook(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for orderbook analysis component."""
        # Extract key values
        score = data.get('score', 50)
        components = data.get('components', {})
        raw_values = data.get('metadata', {}).get('raw_values', {})
        
        # Interpret imbalance
        imbalance = components.get('imbalance', 50)
        imbalance_raw = raw_values.get('imbalance_ratio', 0.5)
        
        if imbalance > 60:
            imbalance_msg = "Strong bid-side dominance"
            side = "bid"
        elif imbalance < 40:
            imbalance_msg = "Strong ask-side dominance" 
            side = "ask"
        else:
            imbalance_msg = "Balanced order book"
            side = "neutral"
        
        # Interpret liquidity
        liquidity = components.get('liquidity', 50)
        if liquidity > 70:
            liquidity_msg = f"high {side}-side liquidity"
        elif liquidity < 30:
            liquidity_msg = f"low {side}-side liquidity"
        else:
            liquidity_msg = "moderate liquidity"
        
        # Interpret spread
        spread = components.get('spread', 50)
        if spread > 70:
            spread_msg = "tight spreads"
        elif spread < 30:
            spread_msg = "wide spreads"
        else:
            spread_msg = "normal spreads"
        
        # Compose main message
        message = f"Orderbook shows {imbalance_msg} with {liquidity_msg} and {spread_msg}"
        
        # Add depth analysis
        depth = components.get('depth', 50)
        if depth > 65:
            message += f". Strong order depth suggests stable price levels"
        elif depth < 35:
            message += f". Shallow order depth indicates potential for price volatility"
        
        # Add market making pressure insight if available
        mpi = components.get('mpi', 50)
        if mpi > 65:
            message += ". Market makers showing bullish positioning"
        elif mpi < 35:
            message += ". Market makers showing bearish positioning"
        
        # Add absorption/exhaustion insight if available
        exhaustion = components.get('exhaustion', 50)
        if exhaustion > 70:
            message += ". Signs of order exhaustion detected; potential reversal point"
        
        return message
    
    def _interpret_orderflow(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for orderflow analysis component."""
        # Extract key values
        score = data.get('score', 50)
        components = data.get('components', {})
        signals = data.get('signals', {})
        interpretation = signals.get('interpretation', {})
        
        # Get the main interpretation message
        if isinstance(interpretation, dict) and 'message' in interpretation:
            message = interpretation['message']
        else:
            # Create interpretation based on score
            if score > 65:
                message = "Strong bullish orderflow indicating buying pressure"
            elif score < 35:
                message = "Strong bearish orderflow indicating selling pressure"
            else:
                message = "Neutral orderflow with balanced buying and selling"
        
        # Add component-specific insights
        oi_score = components.get('open_interest_score', 50)
        if oi_score > 65:
            message += ". Rising open interest confirms trend strength"
        elif oi_score < 35:
            message += ". Declining open interest suggests trend exhaustion"
        
        # Add CVD (Cumulative Volume Delta) insights
        cvd = components.get('cvd', 50)
        if cvd > 65:
            message += ". Positive cumulative volume delta showing buying dominance"
        elif cvd < 35:
            message += ". Negative cumulative volume delta showing selling dominance"
        
        # Add trade flow insights
        trade_flow = components.get('trade_flow_score', 50)
        if trade_flow > 65:
            message += ". Large trades predominantly on the buy side"
        elif trade_flow < 35:
            message += ". Large trades predominantly on the sell side"
        
        # Add divergence insights
        divergences = signals.get('divergences', {})
        if divergences:
            price_cvd = divergences.get('price_cvd', {})
            if price_cvd.get('type') == 'bullish' and price_cvd.get('strength', 0) > 30:
                message += ". Bullish divergence between price and orderflow detected"
            elif price_cvd.get('type') == 'bearish' and price_cvd.get('strength', 0) > 30:
                message += ". Bearish divergence between price and orderflow detected"
        
        return message
    
    def _interpret_sentiment(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for sentiment analysis component."""
        # Extract key values
        score = data.get('score', 50)
        components = data.get('components', {})
        interpretation = data.get('interpretation', {})
        
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
        
        # Add risk assessment
        risk = components.get('risk', 50)
        if risk > 65:
            risk_msg = "high risk conditions"
        elif risk < 35:
            risk_msg = "favorable risk conditions"
        else:
            risk_msg = "moderate risk conditions"
        
        # Add funding rate insight
        funding_rate = components.get('funding_rate', 50)
        if funding_rate > 65:
            funding_msg = "positive funding rates indicating long bias"
        elif funding_rate < 35:
            funding_msg = "negative funding rates indicating short bias"
        else:
            funding_msg = "neutral funding rates"
        
        # Compose the message
        message = f"{sentiment_msg} with {risk_msg} and {funding_msg}"
        
        # Add long/short ratio insight
        lsr = components.get('long_short_ratio', 50)
        if lsr > 60:
            message += ". Traders positioned primarily long"
        elif lsr < 40:
            message += ". Traders positioned primarily short"
        
        # Add market mood insight
        mood = components.get('market_mood', 50)
        if mood > 60 and score < 50:
            message += ". Sentiment diverging from market mood, suggesting potential reversal"
        elif mood < 40 and score > 50:
            message += ". Sentiment diverging from market mood, suggesting potential reversal"
        
        return message
    
    def _interpret_price_structure(self, data: Dict[str, Any]) -> str:
        """Generate rich interpretation for price structure analysis component."""
        # Extract key values
        score = data.get('score', 50)
        components = data.get('components', {})
        signals = data.get('signals', {})
        
        # Get trend signals
        trend_signal = signals.get('trend', {})
        trend_value = trend_signal.get('value', 50)
        trend_type = trend_signal.get('signal', 'neutral')
        
        # Get support/resistance signals
        sr_signal = signals.get('support_resistance', {})
        sr_value = sr_signal.get('value', 50)
        sr_type = sr_signal.get('signal', 'neutral')
        sr_bias = sr_signal.get('bias', 'neutral')
        
        # Get order block signals
        ob_signal = signals.get('orderblock', {})
        ob_value = ob_signal.get('value', 50)
        ob_type = ob_signal.get('signal', 'neutral')
        ob_bias = ob_signal.get('bias', 'neutral')
        
        # Start with trend description
        if trend_type == 'uptrend':
            message = "Price structure shows established uptrend"
        elif trend_type == 'downtrend':
            message = "Price structure shows established downtrend"
        elif trend_type == 'sideways':
            message = "Price structure indicates sideways consolidation"
        else:
            if score > 55:
                message = "Price structure has a bullish bias"
            elif score < 45:
                message = "Price structure has a bearish bias"
            else:
                message = "Price structure is neutral without clear direction"
        
        # Add support/resistance insight
        if sr_type == 'strong_level' and sr_bias == 'bullish':
            message += ". Strong support level identified"
        elif sr_type == 'strong_level' and sr_bias == 'bearish':
            message += ". Strong resistance level identified"
        elif sr_type == 'weak_level' and sr_bias == 'bullish':
            message += ". Minor support level identified"
        elif sr_type == 'weak_level' and sr_bias == 'bearish':
            message += ". Minor resistance level identified"
        
        # Add order block insight
        if ob_type == 'strong' and ob_bias == 'bullish':
            message += ". Strong bullish order block detected - potential support zone"
        elif ob_type == 'strong' and ob_bias == 'bearish':
            message += ". Strong bearish order block detected - potential resistance zone"
        
        # Add VWAP insight
        vwap = components.get('vwap', 50)
        if vwap > 65:
            message += ". Price above VWAP showing short-term strength"
        elif vwap < 35:
            message += ". Price below VWAP showing short-term weakness"
        
        # Add market structure insight
        ms = components.get('market_structure', 50)
        if ms > 65:
            message += ". Higher highs and higher lows confirming bullish structure"
        elif ms < 35:
            message += ". Lower highs and lower lows confirming bearish structure"
        
        # Add divergence insights if available
        divergences = data.get('divergences', {})
        if divergences:
            # Get strongest divergence
            strongest_div = None
            max_strength = 0
            
            for div_name, div_data in divergences.items():
                strength = div_data.get('strength', 0)
                if strength > max_strength:
                    max_strength = strength
                    strongest_div = div_data
            
            if strongest_div and max_strength > 40:
                div_type = strongest_div.get('type', 'neutral')
                div_component = strongest_div.get('component', '')
                div_tf = strongest_div.get('timeframe', '')
                
                if div_tf and div_component:
                    message += f". {div_type.capitalize()} divergence detected in {div_tf.upper()} {div_component.replace('_', ' ')}"
        
        return message
    
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
        if isinstance(sr_signal, dict) and 'value' in sr_signal and sr_signal['value'] > 50:
            level_type = sr_signal.get('bias', 'neutral')
            strength = sr_signal.get('strength', 'moderate')
            
            if level_type == 'bullish':
                key_levels.append(f"Support level ({strength} strength)")
            elif level_type == 'bearish':
                key_levels.append(f"Resistance level ({strength} strength)")
        
        # Order blocks
        ob_signal = signals.get('orderblock', {})
        if isinstance(ob_signal, dict) and 'value' in ob_signal and ob_signal['value'] > 60:
            ob_type = ob_signal.get('bias', 'neutral')
            
            if ob_type == 'bullish':
                key_levels.append(f"Bullish order block (potential support)")
            elif ob_type == 'bearish':
                key_levels.append(f"Bearish order block (potential resistance)")
        
        # Orderbook liquidity levels
        orderbook = results.get('orderbook', {})
        components = orderbook.get('components', {})
        
        if 'liquidity' in components and components['liquidity'] > 65:
            liquidity_type = "bid" if orderbook.get('score', 50) > 55 else "ask"
            key_levels.append(f"Strong {liquidity_type} liquidity cluster")
        
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