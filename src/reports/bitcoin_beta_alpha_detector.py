#!/usr/bin/env python3
"""
Bitcoin Beta Alpha Generation Detector

This module detects alpha generation opportunities by analyzing divergence patterns
in Bitcoin beta relationships across multiple timeframes.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DivergenceType(Enum):
    """Types of beta divergence patterns."""
    CROSS_TIMEFRAME = "cross_timeframe"
    ALPHA_BREAKOUT = "alpha_breakout"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    BETA_EXPANSION = "beta_expansion"
    BETA_COMPRESSION = "beta_compression"
    REVERSION_SETUP = "reversion_setup"
    SECTOR_ROTATION = "sector_rotation"

@dataclass
class AlphaOpportunity:
    """Represents an alpha generation opportunity."""
    symbol: str
    divergence_type: DivergenceType
    confidence: float
    alpha_potential: float
    timeframe_signals: Dict[str, float]
    trading_insight: str
    recommended_action: str
    risk_level: str
    expected_duration: str
    entry_conditions: List[str]
    exit_conditions: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AlphaOpportunity to JSON-serializable dictionary."""
        return {
            'symbol': self.symbol,
            'divergence_type': self.divergence_type.value if isinstance(self.divergence_type, DivergenceType) else str(self.divergence_type),
            'confidence': float(self.confidence),
            'alpha_potential': float(self.alpha_potential),
            'timeframe_signals': dict(self.timeframe_signals),
            'trading_insight': str(self.trading_insight),
            'recommended_action': str(self.recommended_action),
            'risk_level': str(self.risk_level),
            'expected_duration': str(self.expected_duration),
            'entry_conditions': list(self.entry_conditions),
            'exit_conditions': list(self.exit_conditions),
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)
        }

class BitcoinBetaAlphaDetector:
    """
    Detects alpha generation opportunities from Bitcoin beta analysis.
    
    Analyzes beta divergence patterns to identify trading opportunities where
    assets may generate returns independent of Bitcoin movements.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the alpha detector.
        
        Args:
            config: System configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get bitcoin beta analysis configuration
        beta_config = config.get('bitcoin_beta_analysis', {})
        alpha_detection_config = beta_config.get('alpha_detection', {})
        threshold_config = alpha_detection_config.get('thresholds', {})
        
        # Detection thresholds from config with fallbacks
        self.thresholds = {
            'beta_divergence_threshold': threshold_config.get('beta_divergence', 0.3),
            'alpha_threshold': threshold_config.get('alpha_threshold', 0.05),
            'correlation_breakdown_threshold': threshold_config.get('correlation_breakdown', 0.3),
            'confidence_threshold': threshold_config.get('confidence_threshold', 0.7),
            'timeframe_consensus_threshold': threshold_config.get('timeframe_consensus', 0.6),
            'rolling_beta_change_threshold': threshold_config.get('rolling_beta_change', 0.5),
            'reversion_beta_threshold': threshold_config.get('reversion_beta', 1.5),
            'sector_correlation_threshold': threshold_config.get('sector_correlation', 0.8)
        }
        
        # Log the loaded thresholds
        self.logger.info(f"Alpha detection thresholds loaded: {self.thresholds}")
        
        # Historical tracking for pattern recognition
        self._beta_history = {}
        self._alpha_history = {}
        self._opportunity_cache = {}
        
    def detect_alpha_opportunities(self, beta_analysis: Dict[str, Dict[str, Dict[str, float]]]) -> List[AlphaOpportunity]:
        """
        Detect alpha generation opportunities from beta analysis.
        
        Args:
            beta_analysis: Beta analysis results from BitcoinBetaReport
            
        Returns:
            List of alpha opportunities ranked by confidence
        """
        try:
            opportunities = []
            
            # Track current analysis for pattern detection
            self._update_historical_data(beta_analysis)
            
            # Analyze each symbol for divergence patterns
            for symbol in self._get_analyzed_symbols(beta_analysis):
                if symbol == 'BTCUSDT':  # Skip Bitcoin reference
                    continue
                    
                symbol_opportunities = self._analyze_symbol_for_alpha(symbol, beta_analysis)
                opportunities.extend(symbol_opportunities)
                
            # Detect sector rotation patterns
            sector_opportunities = self._detect_sector_rotation(beta_analysis)
            opportunities.extend(sector_opportunities)
            
            # Rank by confidence and alpha potential
            opportunities.sort(key=lambda x: (x.confidence, x.alpha_potential), reverse=True)
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error detecting alpha opportunities: {str(e)}")
            return []
            
    def _analyze_symbol_for_alpha(self, symbol: str, beta_analysis: Dict) -> List[AlphaOpportunity]:
        """Analyze a single symbol for alpha opportunities."""
        opportunities = []
        
        try:
            # Get symbol data across timeframes
            symbol_data = self._extract_symbol_data(symbol, beta_analysis)
            if not symbol_data:
                return []
                
            # 1. Cross-timeframe beta divergence
            divergence_opp = self._detect_cross_timeframe_divergence(symbol, symbol_data)
            if divergence_opp:
                opportunities.append(divergence_opp)
                
            # 2. Alpha breakout pattern
            alpha_opp = self._detect_alpha_breakout(symbol, symbol_data)
            if alpha_opp:
                opportunities.append(alpha_opp)
                
            # 3. Correlation breakdown
            correlation_opp = self._detect_correlation_breakdown(symbol, symbol_data)
            if correlation_opp:
                opportunities.append(correlation_opp)
                
            # 4. Beta expansion/compression
            beta_opp = self._detect_beta_expansion_compression(symbol, symbol_data)
            if beta_opp:
                opportunities.append(beta_opp)
                
            # 5. Mean reversion setup
            reversion_opp = self._detect_reversion_setup(symbol, symbol_data)
            if reversion_opp:
                opportunities.append(reversion_opp)
                
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol} for alpha: {str(e)}")
            return []
            
    def _detect_cross_timeframe_divergence(self, symbol: str, data: Dict) -> Optional[AlphaOpportunity]:
        """Detect cross-timeframe beta divergence patterns."""
        try:
            betas = {tf: data[tf]['beta'] for tf in data.keys()}
            
            # Calculate beta spread
            beta_values = list(betas.values())
            beta_spread = max(beta_values) - min(beta_values)
            
            if beta_spread > self.thresholds['beta_divergence_threshold']:
                # Analyze pattern
                short_term_betas = [betas.get('base', 0), betas.get('ltf', 0)]
                long_term_betas = [betas.get('mtf', 0), betas.get('htf', 0)]
                
                short_avg = np.mean([b for b in short_term_betas if b != 0])
                long_avg = np.mean([b for b in long_term_betas if b != 0])
                
                if short_avg < long_avg * 0.7:  # Short-term decoupling
                    confidence = min(0.9, beta_spread / 0.5)
                    alpha_potential = self._calculate_alpha_potential(data)
                    
                    return AlphaOpportunity(
                        symbol=symbol,
                        divergence_type=DivergenceType.CROSS_TIMEFRAME,
                        confidence=confidence,
                        alpha_potential=alpha_potential,
                        timeframe_signals=betas,
                        trading_insight=f"{symbol} showing short-term decoupling from Bitcoin (β spread: {beta_spread:.2f})",
                        recommended_action=f"Long {symbol}, consider hedging with BTC short",
                        risk_level="Medium",
                        expected_duration="1-3 days",
                        entry_conditions=[
                            f"Short-term beta < {short_avg:.2f}",
                            "Positive momentum confirmation",
                            "Volume above average"
                        ],
                        exit_conditions=[
                            "Beta convergence to long-term average",
                            "Negative alpha development",
                            "Stop loss at -5%"
                        ],
                        timestamp=datetime.now()
                    )
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting cross-timeframe divergence for {symbol}: {str(e)}")
            return None
            
    def _detect_alpha_breakout(self, symbol: str, data: Dict) -> Optional[AlphaOpportunity]:
        """Detect alpha breakout patterns."""
        try:
            # Calculate alpha values for each timeframe
            timeframe_alphas = {}
            
            for tf_name, tf_data in data.items():
                beta = tf_data.get('beta', 0)
                correlation = tf_data.get('correlation', 0)
                
                if abs(beta) > 0:
                    beta_divergence = abs(beta - 1.0)
                    independence_factor = max(0, 1.0 - abs(correlation))
                    timeframe_alpha = beta_divergence * independence_factor * 0.1
                    timeframe_alpha = min(0.15, timeframe_alpha)
                    timeframe_alphas[tf_name] = timeframe_alpha
                else:
                    timeframe_alphas[tf_name] = 0.0
            
            # Calculate average alpha
            avg_alpha = sum(timeframe_alphas.values()) / len(timeframe_alphas) if timeframe_alphas else 0.0
            
            if avg_alpha > self.thresholds['alpha_threshold']:
                # Check if alpha is increasing across timeframes
                alpha_trend = self._calculate_alpha_trend(data)
                
                if alpha_trend > 0:  # Positive alpha trend
                    confidence = min(0.9, avg_alpha / 0.1)  # Normalize to 10%
                    
                    return AlphaOpportunity(
                        symbol=symbol,
                        divergence_type=DivergenceType.ALPHA_BREAKOUT,
                        confidence=confidence,
                        alpha_potential=avg_alpha,
                        timeframe_signals=timeframe_alphas,
                        trading_insight=f"{symbol} generating positive alpha ({avg_alpha:.1%}) with strengthening trend",
                        recommended_action=f"Long {symbol} for independent returns",
                        risk_level="Low",
                        expected_duration="5-10 days",
                        entry_conditions=[
                            f"Alpha > {avg_alpha:.1%}",
                            "Upward alpha trend",
                            "Technical confirmation"
                        ],
                        exit_conditions=[
                            "Alpha turns negative",
                            "Trend reversal signals",
                            "Target: +15% or alpha decay"
                        ],
                        timestamp=datetime.now()
                    )
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting alpha breakout for {symbol}: {str(e)}")
            return None
            
    def _detect_correlation_breakdown(self, symbol: str, data: Dict) -> Optional[AlphaOpportunity]:
        """Detect correlation breakdown patterns - enhanced for independence detection."""
        try:
            correlations = {tf: data[tf].get('correlation', 0) for tf in data.keys()}
            avg_correlation = np.mean(list(correlations.values()))
            
            # Calculate current alpha for validation
            current_alpha = 0.0
            current_beta = np.mean([data[tf].get('beta', 0) for tf in data.keys()])
            
            # Calculate alpha properly from beta and correlation data
            alpha_values = []
            for tf_name, tf_data in data.items():
                beta = tf_data.get('beta', 0)
                correlation = tf_data.get('correlation', 0)
                
                if abs(beta) > 0:
                    beta_divergence = abs(beta - 1.0)
                    independence_factor = max(0, 1.0 - abs(correlation))
                    timeframe_alpha = beta_divergence * independence_factor * 0.1
                    timeframe_alpha = min(0.15, timeframe_alpha)
                    alpha_values.append(timeframe_alpha)
                else:
                    alpha_values.append(0.0)
            
            current_alpha = sum(alpha_values) / len(alpha_values) if alpha_values else 0.0
            
            # Historical correlation for comparison
            historical_correlation = self._get_historical_correlation(symbol)
            
            # Enhanced detection with multiple triggers
            correlation_dropped = False
            independence_trigger = None
            
            # Trigger 1: Historical correlation breakdown
            if historical_correlation and avg_correlation < historical_correlation - self.thresholds['correlation_breakdown_threshold']:
                correlation_dropped = True
                independence_trigger = f"Historical correlation drop: {avg_correlation:.2f} vs {historical_correlation:.2f}"
            
            # Trigger 2: Absolute low correlation with positive alpha
            elif avg_correlation < 0.4 and current_alpha > 0.015:  # Low correlation + positive independent returns
                correlation_dropped = True
                independence_trigger = f"Low Bitcoin correlation ({avg_correlation:.2f}) with independent gains ({current_alpha:.1%})"
            
            # Trigger 3: Negative correlation (moving opposite to Bitcoin)
            elif avg_correlation < -0.2:  # Negative correlation
                correlation_dropped = True
                independence_trigger = f"Negative correlation ({avg_correlation:.2f}) - moving opposite to Bitcoin"
            
            if correlation_dropped:
                # Calculate independence strength
                if historical_correlation:
                    independence_strength = abs(historical_correlation - avg_correlation)
                    confidence_base = min(0.9, independence_strength / 0.5)
                else:
                    independence_strength = abs(avg_correlation)
                    confidence_base = min(0.8, (1 - abs(avg_correlation)))
                
                # Boost confidence based on alpha generation
                alpha_boost = min(0.15, abs(current_alpha) * 5)  # Up to 15% boost for strong alpha
                confidence = min(0.95, confidence_base + alpha_boost)
                
                # Determine independence type and risk
                if avg_correlation < -0.3:  # Strong negative correlation
                    movement_type = "INVERSE"
                    risk_level = "High"
                    insight = f"🔄 {symbol} INVERSE correlation breakdown: {avg_correlation:.2f} (moving opposite to Bitcoin)"
                    action = f"CONTRARIAN OPPORTUNITY: {symbol} showing strong inverse Bitcoin relationship - high risk/reward"
                    expected_duration = "1-3 days"
                    
                elif avg_correlation < 0.2:  # Very low correlation
                    movement_type = "INDEPENDENT"
                    risk_level = "Medium" if current_alpha > 0 else "Medium-High"
                    insight = f"🎯 {symbol} INDEPENDENT movement: correlation {avg_correlation:.2f} (decoupled from Bitcoin)"
                    action = f"ALPHA OPPORTUNITY: {symbol} moving independently - pure alpha play"
                    expected_duration = "2-5 days"
                    
                else:  # Moderate correlation breakdown
                    movement_type = "REDUCED_CORRELATION"
                    risk_level = "Medium"
                    insight = f"📊 {symbol} correlation weakening: {avg_correlation:.2f}"
                    action = f"EMERGING INDEPENDENCE: {symbol} showing reduced Bitcoin sensitivity"
                    expected_duration = "3-7 days"
                
                # Add alpha context
                if current_alpha > 0.03:
                    insight += f" with strong alpha generation ({current_alpha:.1%})"
                elif current_alpha > 0:
                    insight += f" with positive alpha ({current_alpha:.1%})"
                elif current_alpha < -0.02:
                    insight += f" with negative alpha ({current_alpha:.1%}) - caution"
                
                # Add beta context for full picture
                if abs(current_beta) > 1.5:
                    insight += f" and high beta ({current_beta:.2f}x)"
                elif abs(current_beta) < 0.5:
                    insight += f" and low beta ({current_beta:.2f}x)"
                
                return AlphaOpportunity(
                    symbol=symbol,
                    divergence_type=DivergenceType.CORRELATION_BREAKDOWN,
                    confidence=confidence,
                    alpha_potential=max(independence_strength, abs(current_alpha)),
                    timeframe_signals=correlations,
                    trading_insight=insight,
                    recommended_action=action,
                    risk_level=risk_level,
                    expected_duration=expected_duration,
                    entry_conditions=[
                        "Volume spike confirmation (2x+ average)",
                        "News catalyst identification or macro event",
                        "Technical momentum validation",
                        f"Correlation sustained below {avg_correlation + 0.1:.1f}",
                        "Position size appropriate for independence risk"
                    ],
                    exit_conditions=[
                        "Correlation normalization above 0.5",
                        "Alpha decay or reversal",
                        "Catalyst resolution or news fade",
                        "Technical breakdown or profit target",
                        "Risk management stop (3-5% for independent moves)"
                    ],
                    timestamp=datetime.now()
                )
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting correlation breakdown for {symbol}: {str(e)}")
            return None
            
    def _detect_beta_expansion_compression(self, symbol: str, data: Dict) -> Optional[AlphaOpportunity]:
        """Detect beta expansion or compression patterns - enhanced for aggressive moves."""
        try:
            betas = {tf: data[tf]['beta'] for tf in data.keys()}
            avg_beta = np.mean(list(betas.values()))
            
            # Calculate current alpha for validation
            alpha_values = []
            for tf_name, tf_data in data.items():
                beta = tf_data.get('beta', 0)
                correlation = tf_data.get('correlation', 0)
                
                if abs(beta) > 0:
                    beta_divergence = abs(beta - 1.0)
                    independence_factor = max(0, 1.0 - abs(correlation))
                    timeframe_alpha = beta_divergence * independence_factor * 0.1
                    timeframe_alpha = min(0.15, timeframe_alpha)
                    alpha_values.append(timeframe_alpha)
                else:
                    alpha_values.append(0.0)
            
            current_alpha = sum(alpha_values) / len(alpha_values) if alpha_values else 0.0
            
            # Historical beta for comparison
            historical_beta = self._get_historical_beta(symbol)
            
            if historical_beta and abs(avg_beta) > 0.1:  # Minimum meaningful beta
                beta_change = avg_beta / historical_beta - 1 if historical_beta != 0 else avg_beta
                
                # Enhanced thresholds for more sensitive detection
                if abs(beta_change) > self.thresholds['rolling_beta_change_threshold'] * 0.7:  # Lower threshold
                    
                    if avg_beta > historical_beta * 1.3:  # Beta expansion - more aggressive detection
                        pattern_type = DivergenceType.BETA_EXPANSION
                        
                        # Calculate aggressiveness score
                        aggressiveness = (avg_beta / historical_beta) if historical_beta != 0 else abs(avg_beta)
                        
                        if aggressiveness > 2.0:  # Very aggressive movement
                            risk_level = "High"
                            insight = f"🚀 {symbol} AGGRESSIVE beta expansion: {avg_beta:.2f}x vs historical {historical_beta:.2f}x (moving {aggressiveness:.1f}x more aggressively than Bitcoin)"
                            action = f"HIGH MOMENTUM: {symbol} outpacing Bitcoin significantly - consider momentum play with tight stops"
                        else:
                            risk_level = "Medium-High"
                            insight = f"📈 {symbol} beta expansion: {avg_beta:.2f}x vs historical {historical_beta:.2f}x (moving {aggressiveness:.1f}x more than Bitcoin)"
                            action = f"MOMENTUM OPPORTUNITY: {symbol} showing increased Bitcoin sensitivity - potential breakout"
                        
                        confidence = min(0.9, abs(beta_change) * 1.5)  # Boost confidence for clear signals
                        
                        # Add alpha validation
                        if current_alpha > 0.02:  # Positive alpha confirms independent strength
                            confidence = min(0.95, confidence + 0.15)
                            insight += f" with positive alpha ({current_alpha:.1%})"
                        
                    elif avg_beta < historical_beta * 0.7:  # Beta compression
                        pattern_type = DivergenceType.BETA_COMPRESSION
                        independence_score = 1 - (avg_beta / historical_beta) if historical_beta != 0 else 1 - abs(avg_beta)
                        
                        risk_level = "Medium"
                        insight = f"📉 {symbol} beta compression: {avg_beta:.2f}x vs historical {historical_beta:.2f}x (reducing Bitcoin correlation by {independence_score:.1%})"
                        action = f"INDEPENDENCE OPPORTUNITY: {symbol} showing reduced Bitcoin sensitivity - potential alpha generation"
                        confidence = min(0.85, abs(beta_change) * 1.2)
                        
                        # Boost confidence if showing positive alpha during compression
                        if current_alpha > 0:
                            confidence = min(0.9, confidence + 0.1)
                            insight += f" with independent gains ({current_alpha:.1%})"
                    
                    else:
                        return None  # No clear pattern
                    
                    return AlphaOpportunity(
                        symbol=symbol,
                        divergence_type=pattern_type,
                        confidence=confidence,
                        alpha_potential=max(abs(beta_change), abs(current_alpha)),
                        timeframe_signals=betas,
                        trading_insight=insight,
                        recommended_action=action,
                        risk_level=risk_level,
                        expected_duration="2-5 days" if pattern_type == DivergenceType.BETA_EXPANSION else "3-7 days",
                        entry_conditions=[
                            "Volume confirmation above 1.5x average",
                            "Price momentum validation",
                            "Risk management stops in place",
                            "Bitcoin trend alignment check"
                        ],
                        exit_conditions=[
                            "Beta normalization to historical range",
                            "Volume divergence or exhaustion",
                            "Technical resistance/support levels",
                            "Risk limit hit (5-8% stop loss)"
                        ],
                        timestamp=datetime.now()
                    )
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting beta expansion/compression for {symbol}: {str(e)}")
            return None
            
    def _detect_reversion_setup(self, symbol: str, data: Dict) -> Optional[AlphaOpportunity]:
        """Detect mean reversion setups."""
        try:
            betas = {tf: data[tf]['beta'] for tf in data.keys()}
            
            # Calculate alpha values for each timeframe
            timeframe_alphas = {}
            for tf_name, tf_data in data.items():
                beta = tf_data.get('beta', 0)
                correlation = tf_data.get('correlation', 0)
                
                if abs(beta) > 0:
                    beta_divergence = abs(beta - 1.0)
                    independence_factor = max(0, 1.0 - abs(correlation))
                    timeframe_alpha = beta_divergence * independence_factor * 0.1
                    timeframe_alpha = min(0.15, timeframe_alpha)
                    timeframe_alphas[tf_name] = timeframe_alpha
                else:
                    timeframe_alphas[tf_name] = 0.0
            
            avg_beta = np.mean(list(betas.values()))
            avg_alpha = sum(timeframe_alphas.values()) / len(timeframe_alphas) if timeframe_alphas else 0.0
            
            # Historical beta for comparison
            historical_beta = self._get_historical_beta(symbol)
            
            if historical_beta and avg_beta > self.thresholds['reversion_beta_threshold'] * historical_beta and avg_alpha < 0:
                # Extreme beta with negative alpha suggests reversion opportunity
                confidence = min(0.9, (avg_beta / historical_beta - 1))
                
                return AlphaOpportunity(
                    symbol=symbol,
                    divergence_type=DivergenceType.REVERSION_SETUP,
                    confidence=confidence,
                    alpha_potential=abs(avg_alpha),
                    timeframe_signals=betas,
                    trading_insight=f"{symbol} extreme beta ({avg_beta:.2f}) with negative alpha suggests oversold",
                    recommended_action=f"Long {symbol} for mean reversion",
                    risk_level="Medium-High",
                    expected_duration="2-5 days",
                    entry_conditions=[
                        "Technical oversold confirmation",
                        "Support level test",
                        "Volume capitulation"
                    ],
                    exit_conditions=[
                        "Beta normalization",
                        "Alpha turns positive",
                        "Resistance level reached"
                    ],
                    timestamp=datetime.now()
                )
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting reversion setup for {symbol}: {str(e)}")
            return None
            
    def _detect_sector_rotation(self, beta_analysis: Dict) -> List[AlphaOpportunity]:
        """Detect sector rotation patterns."""
        opportunities = []
        
        try:
            # Group symbols by sector (simplified)
            defi_symbols = ['ETHUSDT', 'AVAXUSDT', 'ADAUSDT']
            layer1_symbols = ['SOLUSDT', 'DOTUSDT', 'MATICUSDT']
            
            # Analyze each sector
            for sector_name, symbols in [('DeFi', defi_symbols), ('Layer1', layer1_symbols)]:
                sector_opp = self._analyze_sector_divergence(sector_name, symbols, beta_analysis)
                if sector_opp:
                    opportunities.append(sector_opp)
                    
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error detecting sector rotation: {str(e)}")
            return []
            
    def _analyze_sector_divergence(self, sector_name: str, symbols: List[str], beta_analysis: Dict) -> Optional[AlphaOpportunity]:
        """Analyze divergence within a sector."""
        try:
            # Calculate average sector metrics
            sector_correlations = []
            sector_alphas = []
            
            for symbol in symbols:
                symbol_data = self._extract_symbol_data(symbol, beta_analysis)
                if symbol_data:
                    correlations = [data.get('correlation', 0) for data in symbol_data.values()]
                    alphas = [data.get('alpha', 0) for data in symbol_data.values()]
                    
                    sector_correlations.extend(correlations)
                    sector_alphas.extend(alphas)
                    
            if sector_correlations:
                avg_correlation = np.mean(sector_correlations)
                avg_alpha = np.mean(sector_alphas)
                
                # Check if sector is diverging from Bitcoin
                if avg_correlation < 0.6 and avg_alpha > 0.03:  # Low correlation, positive alpha
                    confidence = 0.7
                    
                    return AlphaOpportunity(
                        symbol=f"{sector_name}_SECTOR",
                        divergence_type=DivergenceType.SECTOR_ROTATION,
                        confidence=confidence,
                        alpha_potential=avg_alpha,
                        timeframe_signals={'correlation': avg_correlation, 'alpha': avg_alpha},
                        trading_insight=f"{sector_name} sector showing independence from Bitcoin",
                        recommended_action=f"Consider {sector_name} allocation increase",
                        risk_level="Low-Medium",
                        expected_duration="1-2 weeks",
                        entry_conditions=[
                            "Sector momentum confirmation",
                            "Individual symbol validation",
                            "Portfolio rebalancing"
                        ],
                        exit_conditions=[
                            "Sector correlation increase",
                            "Alpha decay",
                            "Risk management limits"
                        ],
                        timestamp=datetime.now()
                    )
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing sector divergence for {sector_name}: {str(e)}")
            return None
            
    # Helper methods
    def _extract_symbol_data(self, symbol: str, beta_analysis: Dict) -> Dict:
        """Extract data for a symbol across all timeframes."""
        data = {}
        for tf_name, tf_data in beta_analysis.items():
            if symbol in tf_data:
                data[tf_name] = tf_data[symbol]
        return data
        
    def _get_analyzed_symbols(self, beta_analysis: Dict) -> List[str]:
        """Get list of symbols in the analysis."""
        symbols = set()
        for tf_data in beta_analysis.values():
            symbols.update(tf_data.keys())
        return list(symbols)
        
    def _calculate_alpha_potential(self, data: Dict) -> float:
        """Calculate alpha potential from multi-timeframe data."""
        try:
            # Calculate alpha from beta and correlation data
            alphas = []
            
            for tf_name, tf_data in data.items():
                beta = tf_data.get('beta', 0)
                correlation = tf_data.get('correlation', 0)
                
                # Calculate alpha estimate based on beta divergence from 1.0
                # Alpha represents excess return independent of market (Bitcoin) movements
                if abs(beta) > 0:
                    # Higher alpha when beta deviates significantly from 1.0
                    beta_divergence = abs(beta - 1.0)
                    
                    # Lower correlation suggests more independent movement (higher alpha potential)
                    independence_factor = max(0, 1.0 - abs(correlation))
                    
                    # Combine beta divergence and independence for alpha estimate
                    timeframe_alpha = beta_divergence * independence_factor * 0.1  # Scale to reasonable percentage
                    
                    # Cap maximum alpha at 15% for any single timeframe
                    timeframe_alpha = min(0.15, timeframe_alpha)
                    
                    alphas.append(timeframe_alpha)
                else:
                    alphas.append(0.0)
            
            # Return average alpha across timeframes
            if alphas:
                avg_alpha = sum(alphas) / len(alphas)
                self.logger.debug(f"Calculated alpha potential: {avg_alpha:.3f} from {len(alphas)} timeframes")
                return avg_alpha
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating alpha potential: {str(e)}")
            return 0.0
        
    def _calculate_alpha_trend(self, data: Dict) -> float:
        """Calculate alpha trend across timeframes."""
        try:
            # Calculate alpha values for each timeframe first
            timeframe_alphas = {}
            
            for tf_name, tf_data in data.items():
                beta = tf_data.get('beta', 0)
                correlation = tf_data.get('correlation', 0)
                
                if abs(beta) > 0:
                    beta_divergence = abs(beta - 1.0)
                    independence_factor = max(0, 1.0 - abs(correlation))
                    timeframe_alpha = beta_divergence * independence_factor * 0.1
                    timeframe_alpha = min(0.15, timeframe_alpha)
                    timeframe_alphas[tf_name] = timeframe_alpha
                else:
                    timeframe_alphas[tf_name] = 0.0
            
            # Calculate trend across timeframes (simple approach)
            # Order timeframes by typical duration: base < ltf < mtf < htf
            timeframe_order = ['base', 'ltf', 'mtf', 'htf']
            ordered_alphas = []
            
            for tf in timeframe_order:
                if tf in timeframe_alphas:
                    ordered_alphas.append(timeframe_alphas[tf])
            
            # Calculate trend as difference between longer and shorter timeframes
            if len(ordered_alphas) >= 2:
                trend = (ordered_alphas[-1] - ordered_alphas[0]) / len(ordered_alphas)
                return trend
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating alpha trend: {str(e)}")
            return 0.0
        
    def _update_historical_data(self, beta_analysis: Dict):
        """Update historical tracking data."""
        timestamp = datetime.now()
        
        for tf_name, tf_data in beta_analysis.items():
            for symbol, stats in tf_data.items():
                if symbol not in self._beta_history:
                    self._beta_history[symbol] = []
                if symbol not in self._alpha_history:
                    self._alpha_history[symbol] = []
                    
                self._beta_history[symbol].append({
                    'timestamp': timestamp,
                    'beta': stats.get('beta', 0),
                    'correlation': stats.get('correlation', 0)
                })
                
                self._alpha_history[symbol].append({
                    'timestamp': timestamp,
                    'alpha': stats.get('alpha', 0)
                })
                
                # Keep only last 100 entries
                self._beta_history[symbol] = self._beta_history[symbol][-100:]
                self._alpha_history[symbol] = self._alpha_history[symbol][-100:]
                
    def _get_historical_beta(self, symbol: str) -> Optional[float]:
        """Get historical average beta for a symbol."""
        if symbol in self._beta_history and len(self._beta_history[symbol]) > 5:
            betas = [entry['beta'] for entry in self._beta_history[symbol][-10:]]
            return np.mean(betas)
        return None
        
    def _get_historical_correlation(self, symbol: str) -> Optional[float]:
        """Get historical average correlation for a symbol."""
        if symbol in self._beta_history and len(self._beta_history[symbol]) > 5:
            correlations = [entry['correlation'] for entry in self._beta_history[symbol][-10:]]
            return np.mean(correlations)
        return None 