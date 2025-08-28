#!/usr/bin/env python3

"""
Real-Time Alpha Opportunity Scanner

Lightweight alpha opportunity detection for integration with monitor.py.
Uses cached market data for frequent scanning without additional API calls.
"""

import logging
import asyncio
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import uuid

try:
    from src.reports.bitcoin_beta_alpha_detector import DivergenceType, AlphaOpportunity
    BETA_DETECTOR_AVAILABLE = True
except ImportError:
    # Fallback definitions if full beta detector not available
    from enum import Enum
    from dataclasses import dataclass
    
    class DivergenceType(Enum):
        CORRELATION_BREAKDOWN = "correlation_breakdown"
        BETA_EXPANSION = "beta_expansion"
        ALPHA_BREAKOUT = "alpha_breakout"
    
    @dataclass
    class AlphaOpportunity:
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
                'divergence_type': self.divergence_type.value if hasattr(self.divergence_type, 'value') else str(self.divergence_type),
                'confidence': float(self.confidence),
                'alpha_potential': float(self.alpha_potential),
                'timeframe_signals': dict(self.timeframe_signals),
                'trading_insight': str(self.trading_insight),
                'recommended_action': str(self.recommended_action),
                'risk_level': str(self.risk_level),
                'expected_duration': str(self.expected_duration),
                'entry_conditions': list(self.entry_conditions),
                'exit_conditions': list(self.exit_conditions),
                'timestamp': self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp)
            }
    
    BETA_DETECTOR_AVAILABLE = False

class AlphaOpportunityScanner:
    """
    Lightweight real-time alpha opportunity scanner.
    
    Designed to work with monitor.py's cached market data for frequent
    alpha opportunity detection without additional API overhead.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the alpha opportunity scanner.
        
        Args:
            config: System configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Get alpha scanning configuration
        self.alpha_config = config.get('alpha_scanning', {})
        
        # Scanning settings
        self.enabled = self.alpha_config.get('enabled', True)
        self.interval_minutes = self.alpha_config.get('interval_minutes', 15)
        self.use_cached_data = self.alpha_config.get('use_cached_data', True)
        self.max_symbols_per_scan = self.alpha_config.get('max_symbols_per_scan', 10)
        self.skip_low_volume = self.alpha_config.get('skip_low_volume_symbols', True)
        
        # Thresholds (default values, can be overridden per timeframe)
        thresholds = self.alpha_config.get('thresholds', {})
        self.min_confidence = thresholds.get('min_confidence', 0.75)
        self.correlation_threshold = thresholds.get('correlation_breakdown', 0.25)
        self.beta_threshold = thresholds.get('beta_divergence', 0.25)
        self.alpha_threshold = thresholds.get('alpha_threshold', 0.03)
        self.min_data_points = self.alpha_config.get('min_data_points', 50)
        
        # Timeframe-specific thresholds for optimized alpha detection
        self.timeframe_thresholds = self.alpha_config.get('timeframe_thresholds', {})
        
        # Performance tiers for different urgency levels
        self.performance_tiers = self.alpha_config.get('performance_tiers', {
            'ultra_fast': ['base', 'ltf'],  # 1m, 5m - immediate opportunities
            'fast': ['mtf'],                # 30m - short-term moves  
            'stable': ['htf']               # 4h - confirmed trends
        })
        
        # Alert settings
        alert_config = self.alpha_config.get('alerts', {})
        self.alerts_enabled = alert_config.get('enabled', True)
        self.cooldown_minutes = alert_config.get('cooldown_minutes', 60)
        self.max_alerts_per_scan = alert_config.get('max_alerts_per_scan', 3)
        
        # Timeframes for scanning (now includes all timeframes for comprehensive detection)
        self.timeframes = self.alpha_config.get('timeframes', ['htf', 'mtf', 'ltf', 'base'])
        self.pattern_types = self.alpha_config.get('pattern_types', [
            'correlation_breakdown', 'beta_expansion', 'alpha_breakout'
        ])
        
        # State tracking
        self.last_scan_time = 0
        self.last_alerts = {}  # symbol -> timestamp
        self.scan_count = 0
        self.total_opportunities_found = 0
        self.total_alerts_sent = 0
        
        self.logger.info(f"AlphaOpportunityScanner initialized: interval={self.interval_minutes}min, "
                        f"confidence_threshold={self.min_confidence}, timeframes={self.timeframes}")
        self.logger.info(f"Performance tiers: ultra_fast={self.performance_tiers.get('ultra_fast', [])}, "
                        f"fast={self.performance_tiers.get('fast', [])}, stable={self.performance_tiers.get('stable', [])}")
    
    def should_scan(self) -> bool:
        """Check if it's time to perform an alpha scan."""
        if not self.enabled:
            return False
            
        current_time = time.time()
        time_since_last_scan = (current_time - self.last_scan_time) / 60  # Convert to minutes
        
        return time_since_last_scan >= self.interval_minutes
    
    async def scan_for_opportunities(self, monitor_instance) -> List[AlphaOpportunity]:
        """
        Scan for alpha opportunities using monitor's cached market data.
        
        Args:
            monitor_instance: MarketMonitor instance with cached market data
            
        Returns:
            List of detected alpha opportunities
        """
        if not self.should_scan():
            return []
            
        try:
            self.scan_count += 1
            current_time = time.time()
            self.last_scan_time = current_time
            
            self.logger.debug(f"Starting alpha opportunity scan #{self.scan_count}")
            
            # Get symbols to scan
            symbols = self._get_symbols_to_scan(monitor_instance)
            if not symbols:
                self.logger.warning("No symbols available for alpha scanning")
                return []
            
            # Get market data for analysis
            market_data = await self._collect_market_data(monitor_instance, symbols)
            if not market_data:
                self.logger.warning("No market data available for alpha scanning")
                return []
            
            # Perform alpha analysis
            opportunities = self._analyze_alpha_opportunities(market_data)
            
            # Filter high-confidence opportunities
            filtered_opportunities = [
                opp for opp in opportunities 
                if opp.confidence >= self.min_confidence
            ]
            
            # Apply cooldown filtering
            actionable_opportunities = self._apply_cooldown_filter(filtered_opportunities)
            
            # Limit to max alerts per scan
            final_opportunities = actionable_opportunities[:self.max_alerts_per_scan]
            
            self.total_opportunities_found += len(opportunities)
            
            if final_opportunities:
                self.logger.info(f"Alpha scan #{self.scan_count}: Found {len(opportunities)} opportunities, "
                               f"{len(filtered_opportunities)} high-confidence, "
                               f"{len(final_opportunities)} actionable")
            else:
                self.logger.debug(f"Alpha scan #{self.scan_count}: No actionable opportunities found")
            
            return final_opportunities
            
        except Exception as e:
            self.logger.error(f"Error in alpha opportunity scan: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return []
    
    def _get_symbols_to_scan(self, monitor_instance) -> List[str]:
        """Get list of symbols to scan for alpha opportunities."""
        try:
            # Try to get symbols from monitor's configuration
            if hasattr(monitor_instance, 'get_monitored_symbols'):
                symbols = monitor_instance.get_monitored_symbols()
            elif hasattr(monitor_instance, 'top_symbols_manager') and monitor_instance.top_symbols_manager:
                # Get from top symbols manager
                symbols_data = monitor_instance.top_symbols_manager.get_symbols_sync()
                if isinstance(symbols_data, list):
                    symbols = [s['symbol'] if isinstance(s, dict) else str(s) for s in symbols_data]
                else:
                    symbols = []
            else:
                # Fallback to default symbols
                symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT']
            
            # Ensure BTCUSDT is included as reference
            if 'BTCUSDT' not in symbols:
                symbols.insert(0, 'BTCUSDT')
            
            # Limit to max symbols for performance
            symbols = symbols[:self.max_symbols_per_scan]
            
            self.logger.debug(f"Scanning symbols: {symbols}")
            return symbols
            
        except Exception as e:
            self.logger.error(f"Error getting symbols to scan: {str(e)}")
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']  # Fallback
    
    async def _collect_market_data(self, monitor_instance, symbols: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Collect market data from monitor's cache for analysis."""
        try:
            market_data = {}
            
            for symbol in symbols:
                symbol_data = {}
                
                for timeframe in self.timeframes:
                    try:
                        # Get cached OHLCV data from monitor using abstract timeframe names
                        # The monitor expects timeframe names like 'base', 'ltf', 'mtf', 'htf'
                        # which are mapped to specific intervals in the config
                        if hasattr(monitor_instance, 'get_ohlcv_for_report'):
                            df = monitor_instance.get_ohlcv_for_report(symbol, timeframe)
                        else:
                            df = None
                        
                        if df is not None and len(df) >= self.min_data_points:
                            # Calculate returns for analysis
                            df = df.copy()
                            df['returns'] = df['close'].pct_change()
                            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
                            
                            symbol_data[timeframe] = df
                            
                        else:
                            self.logger.debug(f"Insufficient data for {symbol} {timeframe}: "
                                            f"{len(df) if df is not None else 0} points")
                            
                    except Exception as e:
                        self.logger.debug(f"Error getting {symbol} {timeframe} data: {str(e)}")
                        continue
                
                if symbol_data:
                    market_data[symbol] = symbol_data
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error collecting market data: {str(e)}")
            return {}
    
    def _analyze_alpha_opportunities(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> List[AlphaOpportunity]:
        """Analyze market data for alpha opportunities."""
        opportunities = []
        
        try:
            # Get Bitcoin reference data
            btc_data = market_data.get('BTCUSDT', {})
            if not btc_data:
                self.logger.warning("No Bitcoin data available for alpha analysis")
                return []
            
            for symbol, symbol_data in market_data.items():
                if symbol == 'BTCUSDT':
                    continue  # Skip Bitcoin itself
                    
                try:
                    symbol_opportunities = self._analyze_symbol_for_alpha(symbol, symbol_data, btc_data)
                    opportunities.extend(symbol_opportunities)
                    
                except Exception as e:
                    self.logger.debug(f"Error analyzing {symbol} for alpha: {str(e)}")
                    continue
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error in alpha analysis: {str(e)}")
            return []
    
    def _analyze_symbol_for_alpha(self, symbol: str, symbol_data: Dict[str, pd.DataFrame], 
                                  btc_data: Dict[str, pd.DataFrame]) -> List[AlphaOpportunity]:
        """Analyze a symbol for alpha opportunities across multiple timeframes."""
        opportunities = []
        
        try:
            analysis = {}
            
            # Analyze each timeframe
            for timeframe in self.timeframes:
                if timeframe not in symbol_data or timeframe not in btc_data:
                    continue
                
                symbol_df = symbol_data[timeframe]
                btc_df = btc_data[timeframe]
                
                # Align data for analysis
                aligned_data = self._align_data(symbol_df, btc_df)
                if aligned_data is None:
                    continue
                
                # Calculate metrics for this timeframe
                metrics = self._calculate_metrics(aligned_data)
                analysis[timeframe] = metrics
            
            if not analysis:
                return []
            
            # Detect patterns using timeframe-specific analysis
            for pattern_type in self.pattern_types:
                if pattern_type == 'correlation_breakdown':
                    opp = self._detect_correlation_breakdown_enhanced(symbol, analysis)
                elif pattern_type == 'beta_expansion':
                    opp = self._detect_beta_expansion_enhanced(symbol, analysis)
                elif pattern_type == 'alpha_breakout':
                    opp = self._detect_alpha_breakout_enhanced(symbol, analysis)
                else:
                    continue
                
                if opp:
                    opportunities.append(opp)
            
            return opportunities
            
        except Exception as e:
            self.logger.debug(f"Error analyzing {symbol} for alpha: {str(e)}")
            return []
    
    def _align_data(self, symbol_df: pd.DataFrame, btc_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Align symbol and Bitcoin data for analysis."""
        try:
            # Merge on timestamp index
            aligned = pd.merge(
                symbol_df[['close', 'returns', 'log_returns']],
                btc_df[['close', 'returns', 'log_returns']],
                left_index=True,
                right_index=True,
                suffixes=('_symbol', '_btc'),
                how='inner'
            )
            
            # Drop rows with NaN values
            aligned = aligned.dropna()
            
            return aligned if len(aligned) >= self.min_data_points else None
            
        except Exception as e:
            self.logger.debug(f"Error aligning data: {str(e)}")
            return None
    
    def _calculate_metrics(self, aligned_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate beta, correlation, and alpha metrics."""
        try:
            symbol_returns = aligned_data['returns_symbol']
            btc_returns = aligned_data['returns_btc']
            
            # Calculate correlation
            correlation = symbol_returns.corr(btc_returns)
            
            # Calculate beta using covariance
            covariance = symbol_returns.cov(btc_returns)
            btc_variance = btc_returns.var()
            beta = covariance / btc_variance if btc_variance > 0 else 0
            
            # Calculate R-squared
            r_squared = correlation ** 2 if not pd.isna(correlation) else 0
            
            # Calculate alpha (excess return)
            symbol_mean_return = symbol_returns.mean()
            btc_mean_return = btc_returns.mean()
            alpha = symbol_mean_return - (beta * btc_mean_return)
            
            # Annualize alpha (approximate)
            alpha_annualized = alpha * 365 * 24 * 60  # Assuming 1-minute data
            
            return {
                'beta': float(beta) if not pd.isna(beta) else 0,
                'correlation': float(correlation) if not pd.isna(correlation) else 0,
                'r_squared': float(r_squared) if not pd.isna(r_squared) else 0,
                'alpha': float(alpha_annualized) if not pd.isna(alpha_annualized) else 0,
                'volatility_ratio': float(symbol_returns.std() / btc_returns.std()) if btc_returns.std() > 0 else 1
            }
            
        except Exception as e:
            self.logger.debug(f"Error calculating metrics: {str(e)}")
            return {'beta': 0, 'correlation': 0, 'r_squared': 0, 'alpha': 0, 'volatility_ratio': 1}
    
    def _detect_correlation_breakdown_enhanced(self, symbol: str, analysis: Dict[str, Dict[str, float]]) -> Optional[AlphaOpportunity]:
        """Enhanced correlation breakdown detection with timeframe-specific thresholds."""
        try:
            detected_timeframes = []
            confidence_scores = []
            alpha_potentials = []
            
            for timeframe, data in analysis.items():
                # Get timeframe-specific thresholds
                thresholds = self._get_timeframe_thresholds(timeframe)
                correlation = data.get('correlation', 0)
                alpha = data.get('alpha', 0)
                
                # Check if correlation breakdown occurs for this timeframe
                if correlation < thresholds['correlation_breakdown']:
                    # Calculate timeframe-specific confidence
                    confidence = min(0.95, (thresholds['correlation_breakdown'] - correlation) / thresholds['correlation_breakdown'])
                    
                    if confidence >= thresholds['min_confidence']:
                        detected_timeframes.append(timeframe)
                        confidence_scores.append(confidence)
                        alpha_potentials.append(abs(alpha))
            
            if detected_timeframes:
                # Get the strongest signal (highest confidence)
                max_confidence_idx = np.argmax(confidence_scores)
                primary_timeframe = detected_timeframes[max_confidence_idx]
                primary_confidence = confidence_scores[max_confidence_idx]
                avg_alpha = np.mean(alpha_potentials)
                
                # Determine urgency and trading parameters based on timeframes
                priority = self._get_alert_priority(primary_timeframe)
                risk_level, duration, entry_conditions, exit_conditions = self._get_trading_parameters(
                    primary_timeframe, 'correlation_breakdown'
                )
                
                return AlphaOpportunity(
                    symbol=symbol,
                    divergence_type=DivergenceType.CORRELATION_BREAKDOWN,
                    confidence=primary_confidence,
                    alpha_potential=avg_alpha,
                    timeframe_signals={tf: analysis[tf].get('correlation', 0) for tf in detected_timeframes},
                    trading_insight=f"{symbol} correlation breakdown detected on {', '.join(detected_timeframes)} "
                                  f"(strongest: {primary_timeframe}, priority: {priority})",
                    recommended_action=f"Consider {symbol} for independent movement - {priority} priority",
                    risk_level=risk_level,
                    expected_duration=duration,
                    entry_conditions=entry_conditions,
                    exit_conditions=exit_conditions,
                    timestamp=datetime.now(timezone.utc)
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error detecting correlation breakdown for {symbol}: {str(e)}")
            return None
    
    def _detect_beta_expansion_enhanced(self, symbol: str, analysis: Dict[str, Dict[str, float]]) -> Optional[AlphaOpportunity]:
        """Enhanced beta expansion detection with timeframe-specific thresholds."""
        try:
            detected_timeframes = []
            confidence_scores = []
            alpha_potentials = []
            
            for timeframe, data in analysis.items():
                thresholds = self._get_timeframe_thresholds(timeframe)
                beta = data.get('beta', 0)
                alpha = data.get('alpha', 0)
                
                # Check for significant beta expansion
                if beta > (1.0 + thresholds['beta_divergence']):
                    confidence = min(0.9, (beta - 1.0) / 2.0)
                    
                    if confidence >= thresholds['min_confidence']:
                        detected_timeframes.append(timeframe)
                        confidence_scores.append(confidence)
                        alpha_potentials.append(abs(alpha))
            
            if detected_timeframes:
                max_confidence_idx = np.argmax(confidence_scores)
                primary_timeframe = detected_timeframes[max_confidence_idx]
                primary_confidence = confidence_scores[max_confidence_idx]
                avg_alpha = np.mean(alpha_potentials)
                
                priority = self._get_alert_priority(primary_timeframe)
                risk_level, duration, entry_conditions, exit_conditions = self._get_trading_parameters(
                    primary_timeframe, 'beta_expansion'
                )
                
                return AlphaOpportunity(
                    symbol=symbol,
                    divergence_type=DivergenceType.BETA_EXPANSION,
                    confidence=primary_confidence,
                    alpha_potential=avg_alpha,
                    timeframe_signals={tf: analysis[tf].get('beta', 0) for tf in detected_timeframes},
                    trading_insight=f"{symbol} beta expansion on {', '.join(detected_timeframes)} "
                                  f"(strongest: {primary_timeframe}, priority: {priority})",
                    recommended_action=f"Consider {symbol} for momentum play - {priority} priority",
                    risk_level=risk_level,
                    expected_duration=duration,
                    entry_conditions=entry_conditions,
                    exit_conditions=exit_conditions,
                    timestamp=datetime.now(timezone.utc)
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error detecting beta expansion for {symbol}: {str(e)}")
            return None
    
    def _detect_alpha_breakout_enhanced(self, symbol: str, analysis: Dict[str, Dict[str, float]]) -> Optional[AlphaOpportunity]:
        """Enhanced alpha breakout detection with timeframe-specific thresholds."""
        try:
            detected_timeframes = []
            confidence_scores = []
            alpha_values = []
            
            for timeframe, data in analysis.items():
                thresholds = self._get_timeframe_thresholds(timeframe)
                alpha = data.get('alpha', 0)
                
                if abs(alpha) > thresholds['alpha_threshold']:
                    confidence = min(0.95, abs(alpha) / (thresholds['alpha_threshold'] * 3))
                    
                    if confidence >= thresholds['min_confidence']:
                        detected_timeframes.append(timeframe)
                        confidence_scores.append(confidence)
                        alpha_values.append(alpha)
            
            if detected_timeframes:
                max_confidence_idx = np.argmax(confidence_scores)
                primary_timeframe = detected_timeframes[max_confidence_idx]
                primary_confidence = confidence_scores[max_confidence_idx]
                primary_alpha = alpha_values[max_confidence_idx]
                
                priority = self._get_alert_priority(primary_timeframe)
                risk_level, duration, entry_conditions, exit_conditions = self._get_trading_parameters(
                    primary_timeframe, 'alpha_breakout'
                )
                
                return AlphaOpportunity(
                    symbol=symbol,
                    divergence_type=DivergenceType.ALPHA_BREAKOUT,
                    confidence=primary_confidence,
                    alpha_potential=abs(primary_alpha),
                    timeframe_signals={tf: analysis[tf].get('alpha', 0) for tf in detected_timeframes},
                    trading_insight=f"{symbol} alpha breakout {primary_alpha:.1%} on {', '.join(detected_timeframes)} "
                                  f"(strongest: {primary_timeframe}, priority: {priority})",
                    recommended_action=f"Consider {symbol} for alpha generation - {priority} priority",
                    risk_level=risk_level,
                    expected_duration=duration,
                    entry_conditions=entry_conditions,
                    exit_conditions=exit_conditions,
                    timestamp=datetime.now(timezone.utc)
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error detecting alpha breakout for {symbol}: {str(e)}")
            return None
    
    def _get_trading_parameters(self, timeframe: str, pattern_type: str) -> tuple:
        """Get trading parameters based on timeframe and pattern type."""
        timeframe_map = {
            'base': {'duration_multiplier': 0.25, 'risk_multiplier': 1.4},    # 1m: Quick but risky
            'ltf': {'duration_multiplier': 0.5, 'risk_multiplier': 1.2},     # 5m: Fast with moderate risk  
            'mtf': {'duration_multiplier': 1.0, 'risk_multiplier': 1.0},     # 30m: Standard
            'htf': {'duration_multiplier': 2.0, 'risk_multiplier': 0.8}      # 4h: Longer, more stable
        }
        
        params = timeframe_map.get(timeframe, timeframe_map['mtf'])
        duration_mult = params['duration_multiplier']
        risk_mult = params['risk_multiplier']
        
        if pattern_type == 'correlation_breakdown':
            base_duration = 120  # 2 hours
            risk_level = "Medium" if risk_mult <= 1.0 else "High"
            entry_conditions = ["Volume confirmation", "Technical setup", "Momentum validation"]
            exit_conditions = ["Correlation recovery", "Technical breakdown", "Time-based exit"]
            
        elif pattern_type == 'beta_expansion':
            base_duration = 60   # 1 hour
            risk_level = "High" if risk_mult >= 1.0 else "Medium"
            entry_conditions = ["Momentum confirmation", "Volume spike", "Breakout validation"]
            exit_conditions = ["Beta normalization", "Momentum loss", "Profit target"]
            
        elif pattern_type == 'alpha_breakout':
            base_duration = 180  # 3 hours
            risk_level = "Medium"
            entry_conditions = ["Alpha trend confirmation", "Technical setup", "Risk management"]
            exit_conditions = ["Alpha decay", "Reversal signals", "Profit target"]
            
        else:
            base_duration = 120
            risk_level = "Medium"
            entry_conditions = ["Technical confirmation"]
            exit_conditions = ["Pattern invalidation"]
        
        duration_minutes = int(base_duration * duration_mult)
        duration = f"{duration_minutes//60}h {duration_minutes%60}m" if duration_minutes >= 60 else f"{duration_minutes}m"
        
        # Adjust risk level based on timeframe
        if timeframe in ['base', 'ltf'] and risk_level == "Medium":
            risk_level = "High"
        elif timeframe == 'htf' and risk_level == "High":
            risk_level = "Medium"
        
        return risk_level, duration, entry_conditions, exit_conditions
    
    def _apply_cooldown_filter(self, opportunities: List[AlphaOpportunity]) -> List[AlphaOpportunity]:
        """Apply cooldown filtering to prevent alert spam."""
        current_time = time.time()
        filtered = []
        
        for opp in opportunities:
            last_alert_time = self.last_alerts.get(opp.symbol, 0)
            time_since_last = (current_time - last_alert_time) / 60  # Convert to minutes
            
            if time_since_last >= self.cooldown_minutes:
                filtered.append(opp)
                self.last_alerts[opp.symbol] = current_time
            else:
                self.logger.debug(f"Skipping {opp.symbol} alert (cooldown: {time_since_last:.1f}min)")
        
        return filtered
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            'enabled': self.enabled,
            'interval_minutes': self.interval_minutes,
            'scan_count': self.scan_count,
            'total_opportunities_found': self.total_opportunities_found,
            'total_alerts_sent': self.total_alerts_sent,
            'last_scan_time': datetime.fromtimestamp(self.last_scan_time).isoformat() if self.last_scan_time else None,
            'timeframes': self.timeframes,
            'pattern_types': self.pattern_types,
            'thresholds': {
                'min_confidence': self.min_confidence,
                'correlation_threshold': self.correlation_threshold,
                'beta_threshold': self.beta_threshold,
                'alpha_threshold': self.alpha_threshold
            }
        }
    
    def _get_timeframe_thresholds(self, timeframe: str) -> Dict[str, float]:
        """Get thresholds specific to a timeframe for optimized detection."""
        timeframe_config = self.timeframe_thresholds.get(timeframe, {})
        
        return {
            'min_confidence': timeframe_config.get('min_confidence', self.min_confidence),
            'correlation_breakdown': timeframe_config.get('correlation_breakdown', self.correlation_threshold),
            'beta_divergence': timeframe_config.get('beta_divergence', self.beta_threshold),
            'alpha_threshold': timeframe_config.get('alpha_threshold', self.alpha_threshold)
        }
    
    def _get_alert_priority(self, timeframe: str) -> str:
        """Determine alert priority based on timeframe tier."""
        for tier, timeframes in self.performance_tiers.items():
            if timeframe in timeframes:
                return tier
        return 'medium' 