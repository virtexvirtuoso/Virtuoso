"""Market manipulation detection system.

This module provides detection functionality for potential market manipulation:
- Open Interest (OI) change detection
- Volume spike detection  
- Price movement analysis
- OI vs price divergence detection
- Alert generation for suspicious activity

The system analyzes multiple market metrics simultaneously to identify
coordinated or manipulative trading patterns.
"""

import logging
import time
import asyncio
import traceback
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

# Standard logging setup
def get_logger(name):
    """Get logger for the module."""
    return logging.getLogger(name)


@dataclass
class ManipulationAlert:
    """Data class for manipulation alerts."""
    symbol: str
    timestamp: int
    manipulation_type: str
    confidence_score: float
    metrics: Dict[str, Any]
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'


class ManipulationDetector:
    """
    Market manipulation detection system.
    
    Analyzes market data to detect patterns indicative of coordinated
    or manipulative trading activity based on:
    - Open Interest changes
    - Volume spikes 
    - Price movements
    - OI vs price divergences
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize manipulation detector.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        self.config = config or {}
        self.logger = logger or get_logger(__name__)
        
        # Extract manipulation detection config
        self.manipulation_config = self.config.get('monitoring', {}).get('manipulation_detection', {
            'enabled': True,
            'cooldown': 900,  # 15 minutes between alerts for same symbol
            
            # OI change thresholds
            'oi_change_15m_threshold': 0.02,    # 2% OI change in 15 minutes
            'oi_change_1h_threshold': 0.05,     # 5% OI change in 1 hour
            'oi_absolute_threshold': 1000000,   # $1M absolute OI change
            
            # Volume spike thresholds
            'volume_spike_threshold': 2.0,      # 2x above 15-min average
            'volume_spike_duration': 15,        # Minutes to consider for spike
            
            # Price movement thresholds  
            'price_change_15m_threshold': 0.01, # 1% price change in 15 minutes
            'price_change_5m_threshold': 0.005, # 0.5% price change in 5 minutes
            
            # OI vs price divergence thresholds
            'divergence_oi_threshold': 0.01,    # 1% OI increase
            'divergence_price_threshold': 0.005, # 0.5% price decrease (opposite direction)
            
            # Confidence scoring weights
            'weights': {
                'oi_change': 0.3,
                'volume_spike': 0.25,
                'price_movement': 0.25,
                'divergence': 0.2
            },
            
            # Alert thresholds
            'alert_confidence_threshold': 0.7,  # Minimum confidence for alert
            'high_confidence_threshold': 0.85,  # High confidence threshold
            'critical_confidence_threshold': 0.95, # Critical confidence threshold
            
            # Data requirements
            'min_data_points': 15,              # Minimum data points for analysis
            'lookback_periods': {
                '5m': 5,
                '15m': 15, 
                '1h': 60
            }
        })
        
        # Initialize data storage for historical analysis
        self._historical_data = {}
        self._last_alerts = {}
        self._manipulation_history = {}
        
        # Initialize metrics
        self.stats = {
            'total_analyses': 0,
            'alerts_generated': 0,
            'manipulation_detected': 0,
            'false_positives': 0,
            'avg_confidence': 0.0
        }
        
        self.logger.info("ManipulationDetector initialized with configuration")
        
    async def analyze_market_data(self, symbol: str, market_data: Dict[str, Any]) -> Optional[ManipulationAlert]:
        """
        Analyze market data for manipulation patterns.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data dictionary containing OHLCV, orderbook, trades, etc.
            
        Returns:
            ManipulationAlert if manipulation detected, None otherwise
        """
        try:
            # Skip if disabled
            if not self.manipulation_config.get('enabled', True):
                return None
                
            # Check cooldown period
            if self._is_in_cooldown(symbol):
                return None
                
            # Validate market data
            if not self._validate_market_data(market_data):
                return None
                
            # Update historical data
            self._update_historical_data(symbol, market_data)
            
            # Check if we have enough data
            if not self._has_sufficient_data(symbol):
                return None
                
            # Perform manipulation analysis
            metrics = await self._analyze_manipulation_metrics(symbol, market_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(metrics)
            
            # Update stats
            self.stats['total_analyses'] += 1
            self.stats['avg_confidence'] = (
                (self.stats['avg_confidence'] * (self.stats['total_analyses'] - 1) + confidence_score) 
                / self.stats['total_analyses']
            )
            
            # Check if confidence exceeds alert threshold
            alert_threshold = self.manipulation_config.get('alert_confidence_threshold', 0.7)
            
            if confidence_score >= alert_threshold:
                # Generate manipulation alert
                alert = self._create_manipulation_alert(symbol, metrics, confidence_score)
                
                # Update alert tracking
                self._last_alerts[symbol] = time.time()
                self.stats['alerts_generated'] += 1
                
                if confidence_score >= 0.8:
                    self.stats['manipulation_detected'] += 1
                    
                self.logger.warning(f"Manipulation detected for {symbol}: {alert.description} (confidence: {confidence_score:.2f})")
                
                return alert
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing manipulation for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None
            
    async def _analyze_manipulation_metrics(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze specific manipulation metrics.
        
        Args:
            symbol: Trading pair symbol
            market_data: Current market data
            
        Returns:
            Dictionary containing calculated metrics
        """
        historical_data = self._historical_data.get(symbol, [])
        current_time = int(time.time())
        
        # Get current values
        current_price = float(market_data.get('ticker', {}).get('last', 0))
        current_volume = float(market_data.get('ticker', {}).get('baseVolume', 0))
        
        # Extract open interest if available
        funding_data = market_data.get('funding', {})
        current_oi = float(funding_data.get('openInterest', 0)) if funding_data else 0
        
        metrics = {
            'timestamp': current_time,
            'price': current_price,
            'volume': current_volume,
            'open_interest': current_oi,
            'oi_change_15m': 0,
            'oi_change_1h': 0,
            'oi_change_15m_pct': 0,
            'oi_change_1h_pct': 0,
            'volume_spike_ratio': 0,
            'volume_15m_avg': 0,
            'price_change_15m': 0,
            'price_change_5m': 0,
            'price_change_15m_pct': 0,
            'price_change_5m_pct': 0,
            'divergence_detected': False,
            'divergence_strength': 0
        }
        
        if len(historical_data) < 2:
            return metrics
            
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(historical_data)
        
        # Calculate OI changes
        if current_oi > 0 and 'open_interest' in df.columns:
            # 15-minute OI change
            time_15m_ago = current_time - (15 * 60)
            recent_15m = df[df['timestamp'] >= time_15m_ago]
            if not recent_15m.empty:
                oi_15m_ago = recent_15m.iloc[0]['open_interest']
                if oi_15m_ago > 0:
                    metrics['oi_change_15m'] = current_oi - oi_15m_ago
                    metrics['oi_change_15m_pct'] = (current_oi - oi_15m_ago) / oi_15m_ago
                    
            # 1-hour OI change
            time_1h_ago = current_time - (60 * 60)
            recent_1h = df[df['timestamp'] >= time_1h_ago]
            if not recent_1h.empty:
                oi_1h_ago = recent_1h.iloc[0]['open_interest']
                if oi_1h_ago > 0:
                    metrics['oi_change_1h'] = current_oi - oi_1h_ago
                    metrics['oi_change_1h_pct'] = (current_oi - oi_1h_ago) / oi_1h_ago
        
        # Calculate volume spike
        time_15m_ago = current_time - (15 * 60)
        recent_15m = df[df['timestamp'] >= time_15m_ago]
        if not recent_15m.empty and len(recent_15m) >= 2:
            volume_15m_avg = recent_15m['volume'].mean()
            metrics['volume_15m_avg'] = volume_15m_avg
            if volume_15m_avg > 0:
                metrics['volume_spike_ratio'] = current_volume / volume_15m_avg
                
        # Calculate price changes
        # 15-minute price change
        if not recent_15m.empty:
            price_15m_ago = recent_15m.iloc[0]['price']
            if price_15m_ago > 0:
                metrics['price_change_15m'] = current_price - price_15m_ago
                metrics['price_change_15m_pct'] = (current_price - price_15m_ago) / price_15m_ago
                
        # 5-minute price change
        time_5m_ago = current_time - (5 * 60)
        recent_5m = df[df['timestamp'] >= time_5m_ago]
        if not recent_5m.empty:
            price_5m_ago = recent_5m.iloc[0]['price']
            if price_5m_ago > 0:
                metrics['price_change_5m'] = current_price - price_5m_ago
                metrics['price_change_5m_pct'] = (current_price - price_5m_ago) / price_5m_ago
                
        # Check for OI vs price divergence
        if abs(metrics['oi_change_15m_pct']) > 0:
            oi_threshold = self.manipulation_config.get('divergence_oi_threshold', 0.01)
            price_threshold = self.manipulation_config.get('divergence_price_threshold', 0.005)
            
            # Divergence: OI increases while price decreases significantly (or vice versa)
            oi_increase = metrics['oi_change_15m_pct'] > oi_threshold
            price_decrease = metrics['price_change_15m_pct'] < -price_threshold
            oi_decrease = metrics['oi_change_15m_pct'] < -oi_threshold
            price_increase = metrics['price_change_15m_pct'] > price_threshold
            
            if (oi_increase and price_decrease) or (oi_decrease and price_increase):
                metrics['divergence_detected'] = True
                metrics['divergence_strength'] = abs(metrics['oi_change_15m_pct']) + abs(metrics['price_change_15m_pct'])
                
        return metrics
        
    def _calculate_confidence_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate confidence score for manipulation detection.
        
        Args:
            metrics: Calculated metrics dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        weights = self.manipulation_config.get('weights', {})
        score = 0.0
        
        # OI change score
        oi_weight = weights.get('oi_change', 0.3)
        oi_15m_threshold = self.manipulation_config.get('oi_change_15m_threshold', 0.02)
        oi_1h_threshold = self.manipulation_config.get('oi_change_1h_threshold', 0.05)
        
        oi_score = 0
        if abs(metrics.get('oi_change_15m_pct', 0)) > oi_15m_threshold:
            oi_score += 0.5
        if abs(metrics.get('oi_change_1h_pct', 0)) > oi_1h_threshold:
            oi_score += 0.5
            
        score += oi_weight * oi_score
        
        # Volume spike score
        volume_weight = weights.get('volume_spike', 0.25)
        volume_threshold = self.manipulation_config.get('volume_spike_threshold', 2.0)
        
        volume_ratio = metrics.get('volume_spike_ratio', 0)
        if volume_ratio > volume_threshold:
            volume_score = min(1.0, (volume_ratio - volume_threshold) / volume_threshold)
            score += volume_weight * volume_score
            
        # Price movement score
        price_weight = weights.get('price_movement', 0.25)
        price_15m_threshold = self.manipulation_config.get('price_change_15m_threshold', 0.01)
        price_5m_threshold = self.manipulation_config.get('price_change_5m_threshold', 0.005)
        
        price_score = 0
        if abs(metrics.get('price_change_15m_pct', 0)) > price_15m_threshold:
            price_score += 0.5
        if abs(metrics.get('price_change_5m_pct', 0)) > price_5m_threshold:
            price_score += 0.5
            
        score += price_weight * price_score
        
        # Divergence score
        divergence_weight = weights.get('divergence', 0.2)
        if metrics.get('divergence_detected', False):
            divergence_score = min(1.0, metrics.get('divergence_strength', 0) / 0.02)  # Normalize to 2%
            score += divergence_weight * divergence_score
            
        return min(1.0, score)
        
    def _create_manipulation_alert(self, symbol: str, metrics: Dict[str, Any], confidence_score: float) -> ManipulationAlert:
        """
        Create manipulation alert from metrics and confidence score.
        
        Args:
            symbol: Trading pair symbol
            metrics: Calculated metrics
            confidence_score: Confidence score
            
        Returns:
            ManipulationAlert instance
        """
        # Determine manipulation type and severity
        manipulation_types = []
        
        if abs(metrics.get('oi_change_15m_pct', 0)) > self.manipulation_config.get('oi_change_15m_threshold', 0.02):
            manipulation_types.append('OI_SPIKE')
            
        if metrics.get('volume_spike_ratio', 0) > self.manipulation_config.get('volume_spike_threshold', 2.0):
            manipulation_types.append('VOLUME_SPIKE')
            
        if abs(metrics.get('price_change_15m_pct', 0)) > self.manipulation_config.get('price_change_15m_threshold', 0.01):
            manipulation_types.append('PRICE_MOVEMENT')
            
        if metrics.get('divergence_detected', False):
            manipulation_types.append('OI_PRICE_DIVERGENCE')
            
        manipulation_type = '+'.join(manipulation_types) if manipulation_types else 'UNKNOWN'
        
        # Determine severity
        high_threshold = self.manipulation_config.get('high_confidence_threshold', 0.85)
        critical_threshold = self.manipulation_config.get('critical_confidence_threshold', 0.95)
        
        if confidence_score >= critical_threshold:
            severity = 'critical'
        elif confidence_score >= high_threshold:
            severity = 'high'
        elif confidence_score >= 0.75:
            severity = 'medium'
        else:
            severity = 'low'
            
        # Create description
        description_parts = []
        
        if 'OI_SPIKE' in manipulation_type:
            oi_pct = metrics.get('oi_change_15m_pct', 0) * 100
            description_parts.append(f"OI change: {oi_pct:+.1f}%")
            
        if 'VOLUME_SPIKE' in manipulation_type:
            volume_ratio = metrics.get('volume_spike_ratio', 0)
            description_parts.append(f"Volume spike: {volume_ratio:.1f}x average")
            
        if 'PRICE_MOVEMENT' in manipulation_type:
            price_pct = metrics.get('price_change_15m_pct', 0) * 100
            description_parts.append(f"Price change: {price_pct:+.1f}%")
            
        if 'OI_PRICE_DIVERGENCE' in manipulation_type:
            description_parts.append("OI-Price divergence detected")
            
        description = f"Potential manipulation detected: {', '.join(description_parts)}"
        
        return ManipulationAlert(
            symbol=symbol,
            timestamp=int(time.time()),
            manipulation_type=manipulation_type,
            confidence_score=confidence_score,
            metrics=metrics.copy(),
            description=description,
            severity=severity
        )
        
    def _update_historical_data(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """Update historical data for analysis."""
        if symbol not in self._historical_data:
            self._historical_data[symbol] = []
            
        current_time = int(time.time())
        ticker = market_data.get('ticker', {})
        funding_data = market_data.get('funding', {})
        
        data_point = {
            'timestamp': current_time,
            'price': float(ticker.get('last', 0)),
            'volume': float(ticker.get('baseVolume', 0)),
            'open_interest': float(funding_data.get('openInterest', 0)) if funding_data else 0
        }
        
        self._historical_data[symbol].append(data_point)
        
        # Keep only recent data (last 2 hours)
        cutoff_time = current_time - (2 * 60 * 60)
        self._historical_data[symbol] = [
            dp for dp in self._historical_data[symbol] 
            if dp['timestamp'] >= cutoff_time
        ]
        
    def _validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data for manipulation analysis."""
        if not market_data:
            return False
            
        ticker = market_data.get('ticker', {})
        if not ticker or not ticker.get('last'):
            return False
            
        return True
        
    def _has_sufficient_data(self, symbol: str) -> bool:
        """Check if we have sufficient historical data for analysis."""
        min_points = self.manipulation_config.get('min_data_points', 15)
        return len(self._historical_data.get(symbol, [])) >= min_points
        
    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period."""
        last_alert_time = self._last_alerts.get(symbol, 0)
        cooldown_period = self.manipulation_config.get('cooldown', 900)
        return (time.time() - last_alert_time) < cooldown_period
        
    def get_stats(self) -> Dict[str, Any]:
        """Get manipulation detection statistics."""
        return self.stats.copy()
        
    def get_manipulation_history(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get manipulation detection history."""
        if symbol:
            return self._manipulation_history.get(symbol, [])
        return self._manipulation_history.copy()
        
    def clear_historical_data(self, symbol: Optional[str] = None) -> None:
        """Clear historical data."""
        if symbol:
            self._historical_data.pop(symbol, None)
        else:
            self._historical_data.clear()
    
    async def get_recent_alerts(self, since: datetime, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent manipulation alerts.
        
        Args:
            since: Get alerts since this datetime
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent manipulation alerts
        """
        try:
            since_timestamp = int(since.timestamp())
            alerts = []
            
            # Get alerts from manipulation history
            for symbol, symbol_history in self._manipulation_history.items():
                for alert_data in symbol_history:
                    if isinstance(alert_data, dict) and alert_data.get('timestamp', 0) >= since_timestamp:
                        alerts.append({
                            "id": f"{symbol}_{alert_data.get('timestamp', 0)}",
                            "timestamp": datetime.fromtimestamp(alert_data.get('timestamp', 0)).isoformat(),
                            "symbol": symbol,
                            "exchange": "unknown",
                            "type": alert_data.get('manipulation_type', 'unknown'),
                            "severity": alert_data.get('severity', 'medium'),
                            "confidence": alert_data.get('confidence_score', 0.0),
                            "description": alert_data.get('description', ''),
                            "metrics": alert_data.get('metrics', {}),
                            "price_impact": alert_data.get('metrics', {}).get('price_change_15m_pct', 0.0),
                            "volume_anomaly": alert_data.get('metrics', {}).get('volume_spike_ratio', 0.0)
                        })
                    elif isinstance(alert_data, ManipulationAlert) and alert_data.timestamp >= since_timestamp:
                        alerts.append({
                            "id": f"{alert_data.symbol}_{alert_data.timestamp}",
                            "timestamp": datetime.fromtimestamp(alert_data.timestamp).isoformat(),
                            "symbol": alert_data.symbol,
                            "exchange": "unknown",
                            "type": alert_data.manipulation_type,
                            "severity": alert_data.severity,
                            "confidence": alert_data.confidence_score,
                            "description": alert_data.description,
                            "metrics": alert_data.metrics,
                            "price_impact": alert_data.metrics.get('price_change_15m_pct', 0.0),
                            "volume_anomaly": alert_data.metrics.get('volume_spike_ratio', 0.0)
                        })
            
            # Sort by timestamp descending and limit results
            alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            return alerts[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {e}")
            return []
    
    async def get_detection_stats(self) -> Dict[str, Any]:
        """
        Get manipulation detection statistics.
        
        Returns:
            Dictionary with detection statistics
        """
        try:
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            
            yesterday_timestamp = int(yesterday.timestamp())
            week_ago_timestamp = int(week_ago.timestamp())
            
            # Count alerts by time period and confidence
            alerts_24h = 0
            alerts_7d = 0
            high_confidence = 0
            medium_confidence = 0
            low_confidence = 0
            
            symbol_counts = {}
            
            for symbol, symbol_history in self._manipulation_history.items():
                for alert_data in symbol_history:
                    if isinstance(alert_data, dict):
                        timestamp = alert_data.get('timestamp', 0)
                        confidence = alert_data.get('confidence_score', 0.0)
                    elif isinstance(alert_data, ManipulationAlert):
                        timestamp = alert_data.timestamp
                        confidence = alert_data.confidence_score
                    else:
                        continue
                    
                    # Count by time periods
                    if timestamp >= yesterday_timestamp:
                        alerts_24h += 1
                    if timestamp >= week_ago_timestamp:
                        alerts_7d += 1
                    
                    # Count by confidence levels
                    if confidence >= 0.85:
                        high_confidence += 1
                    elif confidence >= 0.7:
                        medium_confidence += 1
                    else:
                        low_confidence += 1
                    
                    # Count by symbol
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            
            # Get top affected symbols
            top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_symbols = [{"symbol": symbol, "count": count} for symbol, count in top_symbols]
            
            return {
                "alerts_24h": alerts_24h,
                "alerts_7d": alerts_7d,
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence,
                "top_symbols": top_symbols,
                "accuracy": self.stats.get('avg_confidence', 0.0),
                "false_positive_rate": max(0.0, 1.0 - self.stats.get('avg_confidence', 0.0)),
                "avg_detection_time": 15.0,  # Mock value in seconds
                "exchanges": ["unknown"],  # Mock value
                "symbol_count": len(self._historical_data)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting detection stats: {e}")
            return {
                "alerts_24h": 0,
                "alerts_7d": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "top_symbols": [],
                "accuracy": 0.0,
                "false_positive_rate": 0.0,
                "avg_detection_time": 0.0,
                "exchanges": [],
                "symbol_count": 0
            }
    
    async def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a specific symbol for manipulation patterns.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Analysis results for the symbol
        """
        try:
            symbol = symbol.upper()
            
            # Get historical data for this symbol
            historical_data = self._historical_data.get(symbol, [])
            
            if not historical_data:
                return {
                    "status": "no_data",
                    "message": f"No historical data available for {symbol}",
                    "manipulation_risk": "unknown",
                    "confidence": 0.0,
                    "last_analysis": None
                }
            
            # Check if we have sufficient data
            if len(historical_data) < self.manipulation_config.get('min_data_points', 15):
                return {
                    "status": "insufficient_data",
                    "message": f"Insufficient data points for analysis ({len(historical_data)} available, need {self.manipulation_config.get('min_data_points', 15)})",
                    "manipulation_risk": "unknown",
                    "confidence": 0.0,
                    "data_points": len(historical_data),
                    "last_analysis": None
                }
            
            # Analyze recent data patterns
            recent_data = historical_data[-20:]  # Last 20 data points
            
            # Calculate basic metrics
            prices = [dp['price'] for dp in recent_data if dp['price'] > 0]
            volumes = [dp['volume'] for dp in recent_data if dp['volume'] > 0]
            oi_values = [dp['open_interest'] for dp in recent_data if dp['open_interest'] > 0]
            
            if not prices:
                return {
                    "status": "invalid_data",
                    "message": "No valid price data available",
                    "manipulation_risk": "unknown",
                    "confidence": 0.0
                }
            
            # Calculate volatility and anomalies
            price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            avg_price_change = np.mean(price_changes) if price_changes else 0.0
            
            volume_avg = np.mean(volumes) if volumes else 0.0
            volume_spikes = [v for v in volumes if v > volume_avg * 2] if volume_avg > 0 else []
            
            # Determine manipulation risk
            risk_factors = 0
            risk_details = []
            
            if avg_price_change > 0.02:  # > 2% average price change
                risk_factors += 1
                risk_details.append(f"High price volatility: {avg_price_change*100:.1f}%")
            
            if len(volume_spikes) > 0:
                risk_factors += 1
                risk_details.append(f"Volume spikes detected: {len(volume_spikes)}")
            
            if len(oi_values) > 5:
                oi_changes = [abs(oi_values[i] - oi_values[i-1]) / oi_values[i-1] for i in range(1, len(oi_values)) if oi_values[i-1] > 0]
                avg_oi_change = np.mean(oi_changes) if oi_changes else 0.0
                if avg_oi_change > 0.05:  # > 5% average OI change
                    risk_factors += 1
                    risk_details.append(f"High OI volatility: {avg_oi_change*100:.1f}%")
            
            # Calculate confidence and risk level
            if risk_factors >= 3:
                manipulation_risk = "high"
                confidence = 0.8 + (risk_factors - 3) * 0.05
            elif risk_factors >= 2:
                manipulation_risk = "medium"
                confidence = 0.6 + (risk_factors - 2) * 0.1
            elif risk_factors >= 1:
                manipulation_risk = "low"
                confidence = 0.3 + (risk_factors - 1) * 0.15
            else:
                manipulation_risk = "minimal"
                confidence = 0.1
            
            confidence = min(0.95, confidence)  # Cap at 95%
            
            return {
                "status": "analyzed",
                "manipulation_risk": manipulation_risk,
                "confidence": round(confidence, 2),
                "risk_factors": risk_factors,
                "risk_details": risk_details,
                "data_points": len(historical_data),
                "analysis_period": "recent_20_points",
                "metrics": {
                    "avg_price_volatility": round(avg_price_change * 100, 2),
                    "volume_spikes": len(volume_spikes),
                    "avg_oi_volatility": round(np.mean([abs(oi_values[i] - oi_values[i-1]) / oi_values[i-1] for i in range(1, len(oi_values)) if oi_values[i-1] > 0]) * 100, 2) if len(oi_values) > 1 else 0.0
                },
                "last_analysis": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing symbol {symbol}: {e}")
            return {
                "status": "error",
                "message": f"Error analyzing symbol: {str(e)}",
                "manipulation_risk": "unknown",
                "confidence": 0.0,
                "last_analysis": datetime.utcnow().isoformat()
            } 