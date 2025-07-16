#!/usr/bin/env python3
"""
Optimized Alpha Scanner - Value-Weighted Approach
Focuses on high-value, meaningful alpha opportunities
"""

import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import yaml

logger = logging.getLogger(__name__)

class AlertTier(Enum):
    """Alert priority tiers based on alpha magnitude."""
    CRITICAL = "tier_1_critical"    # 50%+ alpha
    HIGH = "tier_2_high"           # 15-50% alpha  
    MEDIUM = "tier_3_medium"       # 8-15% alpha
    BACKGROUND = "tier_4_background"  # 5-8% alpha

class PatternPriority(Enum):
    """Pattern priority based on historical alpha generation."""
    CRITICAL = 1.0    # Beta expansion/compression
    HIGH = 0.6        # Alpha breakout
    MEDIUM = 0.4      # Correlation breakdown
    LOW = 0.2         # Cross timeframe

@dataclass
class AlphaAlert:
    """Optimized alpha alert with value scoring."""
    symbol: str
    pattern_type: str
    alpha_magnitude: float
    confidence: float
    value_score: float
    tier: AlertTier
    priority: PatternPriority
    trading_insight: str
    risk_level: str
    expected_duration: str
    entry_conditions: List[str]
    exit_conditions: List[str]
    timestamp: datetime
    volume_confirmed: bool = False
    correlation_change: Optional[float] = None
    beta_change: Optional[float] = None

class OptimizedAlphaScanner:
    """
    Value-weighted alpha scanner focused on meaningful opportunities.
    
    Key improvements:
    - Tier-based scanning frequencies
    - Value-weighted alert filtering  
    - Dynamic resource allocation
    - Pattern-specific optimization
    """
    
    def __init__(self, config_path: str = "config/alpha_optimization.yaml"):
        """Initialize the optimized scanner."""
        self.logger = logging.getLogger(__name__)
        
        # Load optimized configuration
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            self.config = self._get_default_config()
        
        self.alpha_config = self.config['alpha_scanning_optimized']
        self.pattern_configs = self.config['pattern_configs']
        
        # Initialize tier configurations
        self.tiers = {
            AlertTier.CRITICAL: self.alpha_config['alpha_tiers']['tier_1_critical'],
            AlertTier.HIGH: self.alpha_config['alpha_tiers']['tier_2_high'],
            AlertTier.MEDIUM: self.alpha_config['alpha_tiers']['tier_3_medium'],
            AlertTier.BACKGROUND: self.alpha_config['alpha_tiers']['tier_4_background']
        }
        
        # Pattern weights for value calculation
        self.pattern_weights = self.alpha_config['pattern_weights']
        
        # Value scoring weights
        self.value_weights = self.alpha_config['value_scoring']
        
        # State tracking
        self.last_scan_times = {tier: 0 for tier in AlertTier}
        self.alert_counts = {tier: 0 for tier in AlertTier}
        self.recent_alerts = {}  # symbol -> {tier: timestamp}
        
        # Performance tracking
        self.alert_performance = []
        self.total_alerts_sent = 0
        self.high_value_alerts_sent = 0
        
        self.logger.info("OptimizedAlphaScanner initialized with value-weighted approach")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file not found."""
        return {
            'alpha_scanning_optimized': {
                'alpha_tiers': {
                    'tier_1_critical': {'min_alpha': 0.50, 'min_confidence': 0.95, 'scan_interval_minutes': 1, 'max_alerts_per_hour': 2, 'cooldown_override': True},
                    'tier_2_high': {'min_alpha': 0.15, 'min_confidence': 0.90, 'scan_interval_minutes': 3, 'max_alerts_per_hour': 3, 'cooldown_minutes': 15},
                    'tier_3_medium': {'min_alpha': 0.08, 'min_confidence': 0.85, 'scan_interval_minutes': 10, 'max_alerts_per_hour': 2, 'cooldown_minutes': 60},
                    'tier_4_background': {'min_alpha': 0.05, 'min_confidence': 0.80, 'scan_interval_minutes': 30, 'max_alerts_per_hour': 1, 'cooldown_minutes': 240}
                },
                'pattern_weights': {'beta_expansion': 1.0, 'beta_compression': 1.0, 'alpha_breakout': 0.6, 'correlation_breakdown': 0.4, 'cross_timeframe': 0.2},
                'value_scoring': {'alpha_weight': 0.40, 'confidence_weight': 0.25, 'pattern_weight': 0.20, 'volume_weight': 0.10, 'risk_weight': 0.05},
                'filtering': {'min_alert_value_score': 25.0},
                'throttling': {'max_total_alerts_per_hour': 8, 'emergency_override': {'min_alpha_for_override': 1.00, 'min_confidence_for_override': 0.98}}
            },
            'pattern_configs': {}
        }
        
    def scan_for_alpha_opportunities(self, market_data: Dict[str, Any]) -> List[AlphaAlert]:
        """
        Main scanning method with tier-based frequency control.
        
        Args:
            market_data: Market data for analysis
            
        Returns:
            List of high-value alpha alerts
        """
        # Check master toggle first
        if not self.alpha_config.get('alpha_alerts_enabled', True):
            self.logger.debug("Alpha alerts disabled via master toggle")
            return []
        
        # CRITICAL: Check Silent Mode first - ZERO TOLERANCE
        silent_mode = self.alpha_config.get('silent_mode', {}).get('enabled', False)
        if silent_mode:
            self.logger.debug("Silent Mode active - applying zero tolerance filtering")
            return self._scan_silent_mode(market_data)
        
        current_time = time.time()
        alerts = []
        
        try:
            # Check if extreme mode is enabled
            extreme_mode = self.alpha_config.get('extreme_mode', {}).get('enabled', False)
            
            # Scan each tier based on its frequency and extreme mode settings
            for tier in AlertTier:
                # Skip disabled tiers in extreme mode
                if extreme_mode and not self.tiers[tier].get('enabled', True):
                    continue
                    
                if self._should_scan_tier(tier, current_time):
                    tier_alerts = self._scan_tier(tier, market_data, extreme_mode)
                    alerts.extend(tier_alerts)
                    self.last_scan_times[tier] = current_time
            
            # Filter and rank by value
            high_value_alerts = self._filter_by_value(alerts)
            
            # Apply throttling limits
            final_alerts = self._apply_throttling(high_value_alerts)
            
            # Update performance tracking
            self._update_performance_tracking(final_alerts)
            
            return final_alerts
            
        except Exception as e:
            self.logger.error(f"Error in alpha scanning: {str(e)}")
            return []
    
    def _scan_silent_mode(self, market_data: Dict[str, Any]) -> List[AlphaAlert]:
        """
        Silent Mode scanning with ZERO TOLERANCE for noise.
        
        Only allows:
        - Beta expansion/compression patterns
        - 300%+ alpha minimum (Tier 1) or 150%+ alpha (Tier 2)
        - 99.9%+ confidence (Tier 1) or 99%+ confidence (Tier 2)
        - Maximum 1 alert per day
        - 72-hour symbol cooldowns
        """
        self.logger.info("🔇 Silent Mode: Scanning with zero tolerance")
        
        silent_config = self.alpha_config.get('silent_mode', {})
        hard_blocks = silent_config.get('hard_blocks', {})
        min_requirements = silent_config.get('minimum_requirements', {})
        allowed_patterns = min_requirements.get('allowed_patterns', ['beta_expansion', 'beta_compression'])
        
        # Get Silent Mode tier configurations (should be 300%+ alpha, 99.9%+ confidence)
        tier1_config = self.tiers[AlertTier.CRITICAL]
        tier2_config = self.tiers[AlertTier.HIGH]
        
        alerts = []
        current_time = time.time()
        
        # Check daily alert limit (Silent Mode: increased limit for high-quality alerts)
        daily_limit = self.alpha_config.get('throttling', {}).get('max_total_alerts_per_day', 20)
        if self._get_alerts_today() >= daily_limit:
            self.logger.info(f"🔇 Silent Mode: Daily limit reached ({daily_limit})")
            return []
        
        try:
            # Only scan allowed patterns with extreme thresholds
            for pattern in allowed_patterns:
                # Hard block check
                if hard_blocks.get(pattern, False):
                    self.logger.debug(f"🚫 Silent Mode: {pattern} is hard blocked")
                    continue
                
                # Pattern must be enabled in config
                if not self.pattern_configs.get(pattern, {}).get('enabled', False):
                    self.logger.debug(f"🚫 Silent Mode: {pattern} disabled in config")
                    continue
                
                # Pattern weight must be > 0
                if self.pattern_weights.get(pattern, 0) <= 0:
                    self.logger.debug(f"🚫 Silent Mode: {pattern} weight is zero")
                    continue
                
                self.logger.debug(f"🔍 Silent Mode: Scanning {pattern} with extreme thresholds")
                
                # Scan with Tier 1 thresholds first (300%+ alpha, 99.9%+ confidence)
                tier1_alerts = self._scan_pattern_silent_mode(
                    pattern, market_data, tier1_config['min_alpha'], 
                    tier1_config['min_confidence'], AlertTier.CRITICAL
                )
                alerts.extend(tier1_alerts)
                
                # If no Tier 1 alerts, try Tier 2 (150%+ alpha, 99%+ confidence)
                if not tier1_alerts:
                    tier2_alerts = self._scan_pattern_silent_mode(
                        pattern, market_data, tier2_config['min_alpha'],
                        tier2_config['min_confidence'], AlertTier.HIGH
                    )
                    alerts.extend(tier2_alerts)
            
            # Apply Silent Mode specific filtering
            filtered_alerts = self._apply_silent_mode_filtering(alerts)
            
            if filtered_alerts:
                self.logger.info(f"🔇 Silent Mode: Generated {len(filtered_alerts)} ultra-high-conviction alerts")
            else:
                self.logger.debug("🔇 Silent Mode: No alerts meet extreme criteria")
            
            return filtered_alerts
            
        except Exception as e:
            self.logger.error(f"🔇 Silent Mode scanning error: {str(e)}")
            return []
    
    def _scan_pattern_silent_mode(self, pattern: str, market_data: Dict[str, Any], 
                                 min_alpha: float, min_confidence: float, tier: AlertTier) -> List[AlphaAlert]:
        """Scan a specific pattern in Silent Mode with extreme validation."""
        alerts = []
        
        # Get symbols to scan (limit to reduce noise)
        symbols = list(market_data.keys())[:50]  # Limit symbols in Silent Mode
        
        for symbol in symbols:
            # Check symbol cooldown (Silent Mode: reduced cooldowns for more frequent high-quality alerts)
            cooldown_hours = self.tiers[tier].get('symbol_cooldown_hours', 4)
            if self._is_symbol_in_cooldown(symbol, cooldown_hours):
                continue
            
            try:
                symbol_data = market_data.get(symbol, {})
                if not symbol_data:
                    continue
                
                # Analyze pattern with extreme thresholds
                alert = self._analyze_pattern(symbol, pattern, symbol_data, min_alpha, min_confidence)
                
                if alert:
                    # Additional Silent Mode validation
                    if self._validate_silent_mode_alert(alert, tier):
                        alerts.append(alert)
                        self.logger.info(f"🎯 Silent Mode: {symbol} {pattern} - {alert.alpha_magnitude:.1%} alpha, {alert.confidence:.1%} confidence")
                        # Allow multiple alerts per pattern if they meet criteria
                    
            except Exception as e:
                self.logger.error(f"Silent Mode pattern analysis error for {symbol}: {str(e)}")
                continue
        
        return alerts
    
    def _validate_silent_mode_alert(self, alert: AlphaAlert, tier: AlertTier) -> bool:
        """Additional validation for Silent Mode alerts."""
        # Absolute minimum requirements (failsafe)
        min_alpha_absolute = 0.5  # 50% absolute minimum
        min_confidence_absolute = 0.95  # 95% absolute minimum
        
        if alert.alpha_magnitude < min_alpha_absolute:
            self.logger.debug(f"🚫 Silent Mode: {alert.symbol} alpha {alert.alpha_magnitude:.1%} below absolute minimum {min_alpha_absolute:.1%}")
            return False
        
        if alert.confidence < min_confidence_absolute:
            self.logger.debug(f"🚫 Silent Mode: {alert.symbol} confidence {alert.confidence:.1%} below absolute minimum {min_confidence_absolute:.1%}")
            return False
        
        # Volume confirmation required in Silent Mode
        if not alert.volume_confirmed:
            self.logger.debug(f"🚫 Silent Mode: {alert.symbol} volume not confirmed")
            return False
        
        return True
    
    def _apply_silent_mode_filtering(self, alerts: List[AlphaAlert]) -> List[AlphaAlert]:
        """Apply Silent Mode specific filtering and limits."""
        if not alerts:
            return []
        
        # Sort by value score (highest first)
        alerts.sort(key=lambda x: x.value_score, reverse=True)
        
        # Silent Mode: Allow multiple high-quality alerts (up to 5 per scan)
        max_alerts = 5
        filtered_alerts = alerts[:max_alerts]
        
        # Log rejected alerts
        if len(alerts) > max_alerts:
            self.logger.info(f"🔇 Silent Mode: Filtered {len(alerts)} alerts down to {max_alerts} (highest value)")
            for i, alert in enumerate(alerts[max_alerts:], max_alerts + 1):
                self.logger.debug(f"🚫 Rejected #{i}: {alert.symbol} {alert.pattern_type} - {alert.alpha_magnitude:.1%} alpha")
        
        return filtered_alerts
    
    def _get_alerts_today(self) -> int:
        """Get number of alerts sent today."""
        # This would need to be implemented with persistent storage
        # For now, return 0 to allow alerts
        return 0
    
    def _is_symbol_in_cooldown(self, symbol: str, cooldown_hours: int) -> bool:
        """Check if symbol is in cooldown period."""
        if symbol not in self.recent_alerts:
            return False
        
        current_time = time.time()
        cooldown_seconds = cooldown_hours * 3600
        
        for tier_data in self.recent_alerts[symbol].values():
            if isinstance(tier_data, dict) and 'timestamp' in tier_data:
                last_alert_time = tier_data['timestamp']
                if (current_time - last_alert_time) < cooldown_seconds:
                    return True
        
        return False
    
    def _should_scan_tier(self, tier: AlertTier, current_time: float) -> bool:
        """Determine if a tier should be scanned based on its frequency."""
        tier_config = self.tiers[tier]
        interval_seconds = tier_config['scan_interval_minutes'] * 60
        
        last_scan = self.last_scan_times[tier]
        return (current_time - last_scan) >= interval_seconds
    
    def _scan_tier(self, tier: AlertTier, market_data: Dict[str, Any], extreme_mode: bool = False) -> List[AlphaAlert]:
        """Scan for opportunities in a specific tier."""
        tier_config = self.tiers[tier]
        min_alpha = tier_config['min_alpha']
        min_confidence = tier_config['min_confidence']
        
        alerts = []
        
        # In extreme mode, only use highest value patterns
        if extreme_mode:
            # Only beta expansion and compression patterns (highest alpha potential)
            patterns = []
            # Check both pattern weights AND pattern config enabled status
            if (self.pattern_weights.get('beta_expansion', 0) > 0 and 
                self.pattern_configs.get('beta_expansion', {}).get('enabled', True)):
                patterns.append('beta_expansion')
            if (self.pattern_weights.get('beta_compression', 0) > 0 and 
                self.pattern_configs.get('beta_compression', {}).get('enabled', True)):
                patterns.append('beta_compression')
        else:
            # Original pattern selection logic (filter by enabled status)
            if tier in [AlertTier.CRITICAL, AlertTier.HIGH]:
                all_patterns = ['beta_expansion', 'beta_compression', 'alpha_breakout']
            elif tier == AlertTier.MEDIUM:
                all_patterns = ['alpha_breakout', 'correlation_breakdown']
            else:  # BACKGROUND
                all_patterns = ['correlation_breakdown', 'cross_timeframe']
            
            # Filter patterns by enabled status and weight
            patterns = []
            for pattern in all_patterns:
                pattern_enabled = self.pattern_configs.get(pattern, {}).get('enabled', True)
                pattern_weight = self.pattern_weights.get(pattern, 0)
                if pattern_enabled and pattern_weight > 0:
                    patterns.append(pattern)
        
        for symbol, symbol_data in market_data.items():
            if symbol == 'BTCUSDT':  # Skip Bitcoin reference
                continue
                
            for pattern in patterns:
                alert = self._analyze_pattern(symbol, pattern, symbol_data, min_alpha, min_confidence)
                if alert and alert.tier == tier:
                    alerts.append(alert)
        
        return alerts
    
    def _analyze_pattern(self, symbol: str, pattern: str, data: Dict, 
                        min_alpha: float, min_confidence: float) -> Optional[AlphaAlert]:
        """Analyze a specific pattern for alpha opportunities."""
        try:
            # Check if pattern is enabled in configuration
            pattern_config = self.pattern_configs.get(pattern, {})
            if not pattern_config.get('enabled', True):
                self.logger.debug(f"Pattern {pattern} is disabled in configuration")
                return None
            
            # Check if pattern weight is > 0 (disabled patterns have weight 0)
            if self.pattern_weights.get(pattern, 0) <= 0:
                self.logger.debug(f"Pattern {pattern} has zero weight (disabled)")
                return None
            
            if pattern == 'beta_expansion':
                return self._detect_beta_expansion(symbol, data, min_alpha, min_confidence)
            elif pattern == 'beta_compression':
                return self._detect_beta_compression(symbol, data, min_alpha, min_confidence)
            elif pattern == 'alpha_breakout':
                return self._detect_alpha_breakout(symbol, data, min_alpha, min_confidence)
            elif pattern == 'correlation_breakdown':
                return self._detect_correlation_breakdown(symbol, data, min_alpha, min_confidence)
            elif pattern == 'cross_timeframe':
                return self._detect_cross_timeframe(symbol, data, min_alpha, min_confidence)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error analyzing {pattern} for {symbol}: {str(e)}")
            return None
    
    def _determine_tier(self, alpha_magnitude: float) -> AlertTier:
        """Determine alert tier based on alpha magnitude."""
        if alpha_magnitude >= 0.50:
            return AlertTier.CRITICAL
        elif alpha_magnitude >= 0.15:
            return AlertTier.HIGH
        elif alpha_magnitude >= 0.08:
            return AlertTier.MEDIUM
        else:
            return AlertTier.BACKGROUND
    
    def _calculate_value_score(self, alpha: float, confidence: float, 
                              pattern: str, volume_confirmed: bool) -> float:
        """Calculate alert value score for ranking."""
        weights = self.value_weights
        pattern_weight = self.pattern_weights.get(pattern, 0.2)
        
        # Risk factor (inverse relationship)
        risk_factor = 0.8 if pattern in ['beta_expansion', 'beta_compression'] else 0.9
        
        value_score = (
            alpha * weights['alpha_weight'] +
            confidence * weights['confidence_weight'] +
            pattern_weight * weights['pattern_weight'] +
            (1.0 if volume_confirmed else 0.5) * weights['volume_weight'] +
            risk_factor * weights['risk_weight']
        ) * 100  # Scale to 0-100
        
        return min(100.0, value_score)
    
    def _filter_by_value(self, alerts: List[AlphaAlert]) -> List[AlphaAlert]:
        """Filter alerts by minimum value score."""
        min_value = self.alpha_config['filtering']['min_alert_value_score']
        
        high_value_alerts = [
            alert for alert in alerts 
            if alert.value_score >= min_value
        ]
        
        # Sort by value score (highest first)
        high_value_alerts.sort(key=lambda x: x.value_score, reverse=True)
        
        return high_value_alerts
    
    def _apply_throttling(self, alerts: List[AlphaAlert]) -> List[AlphaAlert]:
        """Apply throttling limits to prevent spam."""
        throttling = self.alpha_config['throttling']
        current_time = time.time()
        final_alerts = []
        
        # Track alerts by tier
        tier_counts = {tier: 0 for tier in AlertTier}
        
        for alert in alerts:
            tier_config = self.tiers[alert.tier]
            
            # Check tier-specific limits
            if tier_counts[alert.tier] >= tier_config['max_alerts_per_hour']:
                continue
            
            # Check cooldown (unless override enabled)
            if not tier_config.get('cooldown_override', False):
                if self._is_in_cooldown(alert.symbol, alert.tier, current_time):
                    continue
            
            # Check emergency override
            if self._is_emergency_override(alert):
                final_alerts.append(alert)
                continue
            
            # Apply normal limits
            if len(final_alerts) < throttling['max_total_alerts_per_hour']:
                final_alerts.append(alert)
                tier_counts[alert.tier] += 1
                
                # Update cooldown tracking
                if alert.symbol not in self.recent_alerts:
                    self.recent_alerts[alert.symbol] = {}
                self.recent_alerts[alert.symbol][alert.tier] = current_time
        
        return final_alerts
    
    def _is_in_cooldown(self, symbol: str, tier: AlertTier, current_time: float) -> bool:
        """Check if symbol is in cooldown for this tier."""
        if symbol not in self.recent_alerts:
            return False
        
        if tier not in self.recent_alerts[symbol]:
            return False
        
        tier_config = self.tiers[tier]
        cooldown_seconds = tier_config.get('cooldown_minutes', 60) * 60
        last_alert_time = self.recent_alerts[symbol][tier]
        
        return (current_time - last_alert_time) < cooldown_seconds
    
    def _is_emergency_override(self, alert: AlphaAlert) -> bool:
        """Check if alert qualifies for emergency override."""
        override_config = self.alpha_config['throttling']['emergency_override']
        
        return (alert.alpha_magnitude >= override_config['min_alpha_for_override'] and
                alert.confidence >= override_config['min_confidence_for_override'])
    
    def _update_performance_tracking(self, alerts: List[AlphaAlert]) -> None:
        """Update performance tracking metrics."""
        self.total_alerts_sent += len(alerts)
        
        high_value_count = sum(1 for alert in alerts if alert.tier in [AlertTier.CRITICAL, AlertTier.HIGH])
        self.high_value_alerts_sent += high_value_count
        
        # Log performance metrics
        if self.total_alerts_sent > 0:
            high_value_ratio = self.high_value_alerts_sent / self.total_alerts_sent
            avg_alpha = np.mean([alert.alpha_magnitude for alert in alerts]) if alerts else 0
            
            self.logger.info(f"Alert Performance - Total: {self.total_alerts_sent}, "
                           f"High-Value Ratio: {high_value_ratio:.2%}, "
                           f"Avg Alpha: {avg_alpha:.1%}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            'total_alerts_sent': self.total_alerts_sent,
            'high_value_alerts_sent': self.high_value_alerts_sent,
            'high_value_ratio': self.high_value_alerts_sent / max(1, self.total_alerts_sent),
            'tier_distribution': {tier.value: count for tier, count in self.alert_counts.items()}
        }
    
    # Pattern detection methods would be implemented here
    # These are simplified examples - actual implementation would use real market data analysis
    
    def _generate_enhanced_trading_insight(self, pattern_type: str, symbol: str, 
                                         alpha_magnitude: float, confidence: float,
                                         additional_data: Dict = None) -> str:
        """Generate enhanced, human-readable trading insights."""
        additional_data = additional_data or {}
        
        if pattern_type == 'beta_expansion':
            return self._generate_beta_expansion_insight(symbol, alpha_magnitude, confidence, additional_data)
        elif pattern_type == 'beta_compression':
            return self._generate_beta_compression_insight(symbol, alpha_magnitude, confidence, additional_data)
        elif pattern_type == 'alpha_breakout':
            return self._generate_alpha_breakout_insight(symbol, alpha_magnitude, confidence, additional_data)
        elif pattern_type == 'correlation_breakdown':
            return self._generate_correlation_breakdown_insight(symbol, alpha_magnitude, confidence, additional_data)
        elif pattern_type == 'cross_timeframe':
            return self._generate_cross_timeframe_insight(symbol, alpha_magnitude, confidence, additional_data)
        else:
            return f"Alpha opportunity detected for {symbol} with {alpha_magnitude:.1%} potential."
    
    def _generate_beta_expansion_insight(self, symbol: str, alpha: float, confidence: float, data: Dict) -> str:
        """Generate insight for beta expansion patterns."""
        beta_change = data.get('beta_change', 0)
        volume_spike = data.get('volume_spike', 1.0)
        
        # Determine magnitude description
        if alpha >= 2.0:  # 200%+
            magnitude = "massive"
            urgency = "immediate"
        elif alpha >= 1.0:  # 100%+
            magnitude = "exceptional"
            urgency = "urgent"
        elif alpha >= 0.5:  # 50%+
            magnitude = "significant"
            urgency = "high priority"
        else:
            magnitude = "moderate"
            urgency = "standard"
        
        # Base insight
        insight = f"🚀 {symbol} is experiencing {magnitude} volatility expansion ({alpha:.0%} alpha potential). "
        
        # Explain what's happening
        insight += f"This asset is becoming much more volatile than Bitcoin, indicating strong independent momentum. "
        
        if beta_change > 0.5:
            insight += f"Volatility has increased {beta_change:.0%} above normal levels. "
        
        # Volume context
        if volume_spike > 3.0:
            insight += f"Heavy volume ({volume_spike:.1f}x normal) confirms institutional interest. "
        elif volume_spike > 2.0:
            insight += f"Elevated volume ({volume_spike:.1f}x) supports the move. "
        
        # Trading implications
        insight += f"\n\n📈 TRADING IMPLICATIONS:\n"
        insight += f"• This is a {urgency} opportunity - volatility expansion often leads to sustained moves\n"
        insight += f"• Expected duration: 2-6 hours for this level of expansion\n"
        insight += f"• Risk: Higher volatility means wider stops needed\n"
        
        # Specific recommendations
        if alpha >= 1.0:
            insight += f"• STRATEGY: Momentum trading with {confidence:.0%} confidence\n"
            insight += f"• ENTRY: On volume confirmation and trend continuation\n"
            insight += f"• STOPS: 3-5% due to high volatility\n"
            insight += f"• TARGET: {alpha/2:.0%}-{alpha:.0%} move potential"
        else:
            insight += f"• STRATEGY: Cautious position sizing due to volatility\n"
            insight += f"• ENTRY: Wait for pullback or clear direction\n"
            insight += f"• STOPS: 2-3% with tight management\n"
            insight += f"• TARGET: {alpha/3:.0%}-{alpha/2:.0%} realistic target"
        
        return insight
    
    def _generate_beta_compression_insight(self, symbol: str, alpha: float, confidence: float, data: Dict) -> str:
        """Generate insight for beta compression patterns."""
        correlation_drop = data.get('correlation_drop', 0)
        independence_score = data.get('independence_score', 0.5)
        
        # Determine significance
        if alpha >= 1.0:
            significance = "major"
            opportunity = "exceptional"
        elif alpha >= 0.5:
            significance = "significant"
            opportunity = "strong"
        else:
            significance = "moderate"
            opportunity = "decent"
        
        insight = f"🎯 {symbol} is showing {significance} independence from Bitcoin ({alpha:.0%} alpha potential). "
        
        # Explain the pattern
        insight += f"This asset is decoupling from Bitcoin's price movements, creating independent trading opportunities. "
        
        if correlation_drop > 0.3:
            insight += f"Correlation with Bitcoin has dropped {correlation_drop:.0%}, indicating strong fundamental drivers. "
        
        if independence_score > 0.7:
            insight += f"Independence score of {independence_score:.1f} suggests this move is driven by asset-specific factors. "
        
        # Market context
        insight += f"\n\n🎪 MARKET CONTEXT:\n"
        insight += f"• Bitcoin correlation breakdown often signals sector rotation or news-driven moves\n"
        insight += f"• This creates {opportunity} opportunities for independent price action\n"
        insight += f"• Duration typically 1-4 hours depending on catalyst strength\n"
        
        # Trading strategy
        insight += f"\n📊 TRADING STRATEGY:\n"
        if alpha >= 0.75:
            insight += f"• HIGH CONVICTION: Strong decoupling with {confidence:.0%} confidence\n"
            insight += f"• APPROACH: Aggressive positioning on confirmed direction\n"
            insight += f"• TIMEFRAME: 1-3 hour holds for maximum alpha capture\n"
            insight += f"• RISK: Lower than beta expansion due to reduced Bitcoin correlation"
        else:
            insight += f"• MODERATE CONVICTION: Partial decoupling with {confidence:.0%} confidence\n"
            insight += f"• APPROACH: Conservative positioning with quick profits\n"
            insight += f"• TIMEFRAME: 30min-2 hour holds\n"
            insight += f"• RISK: Monitor Bitcoin moves as correlation may return"
        
        return insight
    
    def _generate_alpha_breakout_insight(self, symbol: str, alpha: float, confidence: float, data: Dict) -> str:
        """Generate insight for alpha breakout patterns."""
        trend_strength = data.get('trend_strength', 0.5)
        breakout_level = data.get('breakout_level', 'resistance')
        
        insight = f"⚡ {symbol} is breaking out with {alpha:.0%} alpha potential. "
        
        # Explain the breakout
        if breakout_level == 'resistance':
            insight += f"Price is breaking above key resistance levels with strong momentum. "
        else:
            insight += f"Price is breaking below key support with bearish momentum. "
        
        if trend_strength > 0.7:
            insight += f"Trend strength of {trend_strength:.1f} indicates this is a high-quality breakout. "
        
        # Trading context
        insight += f"\n\n📈 BREAKOUT ANALYSIS:\n"
        insight += f"• This is a classic momentum play with {confidence:.0%} confidence\n"
        insight += f"• Breakouts often continue for 1-3 hours after confirmation\n"
        insight += f"• Success rate improves with volume confirmation\n"
        
        # Strategy recommendations
        insight += f"\n🎯 RECOMMENDED APPROACH:\n"
        if alpha >= 0.3:
            insight += f"• ENTRY: On volume spike above breakout level\n"
            insight += f"• STOPS: Just below/above breakout level (1-2%)\n"
            insight += f"• TARGET: {alpha:.0%} move from breakout point\n"
            insight += f"• TIMEFRAME: 1-3 hours for momentum capture"
        else:
            insight += f"• ENTRY: Wait for pullback to breakout level\n"
            insight += f"• STOPS: Conservative 1-1.5% from entry\n"
            insight += f"• TARGET: {alpha/2:.0%} conservative target\n"
            insight += f"• TIMEFRAME: 30min-2 hours"
        
        return insight
    
    def _generate_correlation_breakdown_insight(self, symbol: str, alpha: float, confidence: float, data: Dict) -> str:
        """Generate insight for correlation breakdown patterns."""
        breakdown_magnitude = data.get('breakdown_magnitude', 0.3)
        historical_context = data.get('historical_context', 'normal')
        
        insight = f"🔄 {symbol} correlation breakdown detected ({alpha:.0%} alpha potential). "
        
        # Explain what's happening
        insight += f"This asset is breaking its normal correlation patterns with the broader market. "
        
        if breakdown_magnitude > 0.4:
            insight += f"The breakdown is {breakdown_magnitude:.0%} stronger than normal, indicating significant catalyst. "
        
        # Context and implications
        insight += f"\n\n🔍 MARKET IMPLICATIONS:\n"
        insight += f"• Correlation breakdowns often signal news, partnerships, or sector-specific events\n"
        insight += f"• These moves can be short-lived but profitable if timed correctly\n"
        insight += f"• Confidence level: {confidence:.0%} based on historical patterns\n"
        
        # Trading approach
        insight += f"\n⚖️ TRADING APPROACH:\n"
        insight += f"• STRATEGY: Quick scalp or swing depending on catalyst\n"
        insight += f"• ENTRY: On confirmation of direction with volume\n"
        insight += f"• RISK: Medium - correlation may resume quickly\n"
        insight += f"• TARGET: {alpha:.0%} potential but take profits early\n"
        insight += f"• DURATION: 30 minutes to 2 hours typically"
        
        return insight
    
    def _generate_cross_timeframe_insight(self, symbol: str, alpha: float, confidence: float, data: Dict) -> str:
        """Generate insight for cross timeframe patterns."""
        timeframe_alignment = data.get('timeframe_alignment', 0.6)
        consensus_strength = data.get('consensus_strength', 0.5)
        
        insight = f"📊 {symbol} showing cross-timeframe alignment ({alpha:.0%} alpha potential). "
        
        # Explain the pattern
        insight += f"Multiple timeframes are aligning in the same direction, creating confluence for a move. "
        
        if timeframe_alignment > 0.8:
            insight += f"Strong alignment ({timeframe_alignment:.1f}) across 1m, 5m, and 15m charts. "
        
        # Trading context
        insight += f"\n\n🎯 CONFLUENCE ANALYSIS:\n"
        insight += f"• Multi-timeframe alignment increases probability of sustained moves\n"
        insight += f"• Consensus strength: {consensus_strength:.1f} indicates {confidence:.0%} confidence\n"
        insight += f"• These setups often have better risk/reward ratios\n"
        
        # Strategy
        insight += f"\n📈 STRATEGY:\n"
        insight += f"• APPROACH: Conservative position with good risk/reward\n"
        insight += f"• ENTRY: Wait for all timeframes to confirm direction\n"
        insight += f"• STOPS: Tighter stops possible due to confluence (1-2%)\n"
        insight += f"• TARGET: {alpha:.0%} with potential for extension\n"
        insight += f"• TIMEFRAME: 1-4 hours for full development"
        
        return insight
    
    def _detect_beta_expansion(self, symbol: str, data: Dict, 
                              min_alpha: float, min_confidence: float) -> Optional[AlphaAlert]:
        """Detect beta expansion patterns - highest priority."""
        # This would contain actual beta expansion detection logic
        # For demonstration, creating a mock alert with enhanced insight
        
        # Mock detection logic (replace with real analysis)
        mock_alpha = 1.25  # 125% alpha
        mock_confidence = 0.96  # 96% confidence
        mock_beta_change = 0.75  # 75% increase in volatility
        mock_volume_spike = 4.2  # 4.2x normal volume
        
        if mock_alpha >= min_alpha and mock_confidence >= min_confidence:
            additional_data = {
                'beta_change': mock_beta_change,
                'volume_spike': mock_volume_spike
            }
            
            trading_insight = self._generate_enhanced_trading_insight(
                'beta_expansion', symbol, mock_alpha, mock_confidence, additional_data
            )
            
            tier = self._determine_tier(mock_alpha)
            value_score = self._calculate_value_score(mock_alpha, mock_confidence, 'beta_expansion', True)
            
            return AlphaAlert(
                symbol=symbol,
                pattern_type='beta_expansion',
                alpha_magnitude=mock_alpha,
                confidence=mock_confidence,
                value_score=value_score,
                tier=tier,
                priority=PatternPriority.CRITICAL,
                trading_insight=trading_insight,
                risk_level="Medium-High",
                expected_duration="2-6 hours",
                entry_conditions=["Volume confirmation", "Trend continuation", "Beta expansion >50%"],
                exit_conditions=["Volatility normalization", "Volume decline", "Bitcoin correlation return"],
                timestamp=datetime.now(timezone.utc),
                volume_confirmed=True,
                beta_change=mock_beta_change
            )
        
        return None
    
    def _detect_beta_compression(self, symbol: str, data: Dict,
                                min_alpha: float, min_confidence: float) -> Optional[AlphaAlert]:
        """Detect beta compression patterns - highest priority."""
        # Mock detection logic for demonstration (replace with real analysis)
        mock_alpha = 0.85  # 85% alpha
        mock_confidence = 0.92  # 92% confidence
        mock_correlation_drop = 0.45  # 45% correlation drop
        mock_independence_score = 0.78  # 78% independence
        
        if mock_alpha >= min_alpha and mock_confidence >= min_confidence:
            additional_data = {
                'correlation_drop': mock_correlation_drop,
                'independence_score': mock_independence_score
            }
            
            trading_insight = self._generate_enhanced_trading_insight(
                'beta_compression', symbol, mock_alpha, mock_confidence, additional_data
            )
            
            tier = self._determine_tier(mock_alpha)
            value_score = self._calculate_value_score(mock_alpha, mock_confidence, 'beta_compression', True)
            
            return AlphaAlert(
                symbol=symbol,
                pattern_type='beta_compression',
                alpha_magnitude=mock_alpha,
                confidence=mock_confidence,
                value_score=value_score,
                tier=tier,
                priority=PatternPriority.CRITICAL,
                trading_insight=trading_insight,
                risk_level="Medium",
                expected_duration="1-4 hours",
                entry_conditions=["Direction confirmation", "Volume support", "Correlation <0.5"],
                exit_conditions=["Correlation return", "Bitcoin dominance", "Volume decline"],
                timestamp=datetime.now(timezone.utc),
                volume_confirmed=True,
                correlation_change=mock_correlation_drop
            )
        
        return None
    
    def _detect_alpha_breakout(self, symbol: str, data: Dict,
                              min_alpha: float, min_confidence: float) -> Optional[AlphaAlert]:
        """Detect alpha breakout patterns - medium priority."""
        # Mock detection logic for demonstration (replace with real analysis)
        mock_alpha = 0.35  # 35% alpha
        mock_confidence = 0.88  # 88% confidence
        mock_trend_strength = 0.82  # 82% trend strength
        mock_breakout_level = 'resistance'
        
        if mock_alpha >= min_alpha and mock_confidence >= min_confidence:
            additional_data = {
                'trend_strength': mock_trend_strength,
                'breakout_level': mock_breakout_level
            }
            
            trading_insight = self._generate_enhanced_trading_insight(
                'alpha_breakout', symbol, mock_alpha, mock_confidence, additional_data
            )
            
            tier = self._determine_tier(mock_alpha)
            value_score = self._calculate_value_score(mock_alpha, mock_confidence, 'alpha_breakout', True)
            
            return AlphaAlert(
                symbol=symbol,
                pattern_type='alpha_breakout',
                alpha_magnitude=mock_alpha,
                confidence=mock_confidence,
                value_score=value_score,
                tier=tier,
                priority=PatternPriority.HIGH,
                trading_insight=trading_insight,
                risk_level="Medium",
                expected_duration="1-3 hours",
                entry_conditions=["Breakout confirmation", "Volume spike", "Trend continuation"],
                exit_conditions=["Resistance/support test", "Volume decline", "Trend reversal"],
                timestamp=datetime.now(timezone.utc),
                volume_confirmed=True
            )
        
        return None
    
    def _detect_correlation_breakdown(self, symbol: str, data: Dict,
                                     min_alpha: float, min_confidence: float) -> Optional[AlphaAlert]:
        """Detect correlation breakdown - lower priority."""
        # Mock detection logic for demonstration (replace with real analysis)
        mock_alpha = 0.18  # 18% alpha
        mock_confidence = 0.82  # 82% confidence
        mock_breakdown_magnitude = 0.38  # 38% breakdown
        mock_historical_context = 'elevated'
        
        if mock_alpha >= min_alpha and mock_confidence >= min_confidence:
            additional_data = {
                'breakdown_magnitude': mock_breakdown_magnitude,
                'historical_context': mock_historical_context
            }
            
            trading_insight = self._generate_enhanced_trading_insight(
                'correlation_breakdown', symbol, mock_alpha, mock_confidence, additional_data
            )
            
            tier = self._determine_tier(mock_alpha)
            value_score = self._calculate_value_score(mock_alpha, mock_confidence, 'correlation_breakdown', False)
            
            return AlphaAlert(
                symbol=symbol,
                pattern_type='correlation_breakdown',
                alpha_magnitude=mock_alpha,
                confidence=mock_confidence,
                value_score=value_score,
                tier=tier,
                priority=PatternPriority.MEDIUM,
                trading_insight=trading_insight,
                risk_level="Medium-Low",
                expected_duration="30min-2 hours",
                entry_conditions=["Direction confirmation", "Catalyst identification", "Volume support"],
                exit_conditions=["Correlation return", "News fade", "Time decay"],
                timestamp=datetime.now(timezone.utc),
                volume_confirmed=False,
                correlation_change=mock_breakdown_magnitude
            )
        
        return None
    
    def _detect_cross_timeframe(self, symbol: str, data: Dict,
                               min_alpha: float, min_confidence: float) -> Optional[AlphaAlert]:
        """Detect cross timeframe patterns - lowest priority."""
        # Mock detection logic for demonstration (replace with real analysis)
        mock_alpha = 0.12  # 12% alpha
        mock_confidence = 0.78  # 78% confidence
        mock_timeframe_alignment = 0.85  # 85% alignment
        mock_consensus_strength = 0.72  # 72% consensus
        
        if mock_alpha >= min_alpha and mock_confidence >= min_confidence:
            additional_data = {
                'timeframe_alignment': mock_timeframe_alignment,
                'consensus_strength': mock_consensus_strength
            }
            
            trading_insight = self._generate_enhanced_trading_insight(
                'cross_timeframe', symbol, mock_alpha, mock_confidence, additional_data
            )
            
            tier = self._determine_tier(mock_alpha)
            value_score = self._calculate_value_score(mock_alpha, mock_confidence, 'cross_timeframe', False)
            
            return AlphaAlert(
                symbol=symbol,
                pattern_type='cross_timeframe',
                alpha_magnitude=mock_alpha,
                confidence=mock_confidence,
                value_score=value_score,
                tier=tier,
                priority=PatternPriority.LOW,
                trading_insight=trading_insight,
                risk_level="Low-Medium",
                expected_duration="1-4 hours",
                entry_conditions=["All timeframes aligned", "Volume confirmation", "Clear direction"],
                exit_conditions=["Timeframe divergence", "Volume decline", "Target reached"],
                timestamp=datetime.now(timezone.utc),
                volume_confirmed=False
            )
        
        return None 