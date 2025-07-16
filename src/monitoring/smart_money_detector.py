"""
Smart Money Detection System

This module detects sophisticated trading patterns and institutional behaviors
that complement the existing whale detection system.

Smart Money vs Whale Detection:
- Whale: Focuses on SIZE (large orders/trades)
- Smart Money: Focuses on SOPHISTICATION (execution patterns, timing, market microstructure)

Event Types:
- orderflow_imbalance: Coordinated order flow patterns
- volume_spike: Strategic volume at key technical levels
- depth_change: Sophisticated liquidity provision/removal
- position_change: Institutional position adjustments
"""

import logging
import time
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict

class SmartMoneyEventType(Enum):
    """Types of smart money events."""
    ORDERFLOW_IMBALANCE = "orderflow_imbalance"
    VOLUME_SPIKE = "volume_spike"
    DEPTH_CHANGE = "depth_change"
    POSITION_CHANGE = "position_change"

class SophisticationLevel(Enum):
    """Sophistication levels for smart money detection."""
    LOW = "low"           # 1-3: Basic patterns
    MEDIUM = "medium"     # 4-6: Intermediate patterns
    HIGH = "high"         # 7-8: Advanced patterns
    EXPERT = "expert"     # 9-10: Institutional-grade patterns

@dataclass
class SmartMoneyEvent:
    """Represents a detected smart money event."""
    event_type: SmartMoneyEventType
    symbol: str
    timestamp: float
    sophistication_score: float  # 1-10 scale
    confidence: float           # 0-1 scale
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def sophistication_level(self) -> SophisticationLevel:
        """Get sophistication level based on score."""
        if self.sophistication_score >= 9:
            return SophisticationLevel.EXPERT
        elif self.sophistication_score >= 7:
            return SophisticationLevel.HIGH
        elif self.sophistication_score >= 4:
            return SophisticationLevel.MEDIUM
        else:
            return SophisticationLevel.LOW

class SmartMoneyDetector:
    """
    Detects sophisticated trading patterns and institutional behaviors.
    
    This system analyzes market microstructure to identify:
    1. Coordinated order flow patterns
    2. Strategic volume placement
    3. Sophisticated depth manipulation
    4. Institutional position building/unwinding
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        
        # Smart money configuration
        self.smart_money_config = config.get('smart_money_detection', {
            'enabled': True,
            'min_sophistication_score': 6.0,  # Minimum score for alerts
            'min_confidence': 0.7,            # Minimum confidence for alerts
            'cooldown_minutes': 15,           # Cooldown between alerts per symbol
            'max_alerts_per_hour': 10,       # Global rate limiting
            
            # Detection thresholds
            'orderflow_imbalance_threshold': 0.65,    # 65% imbalance
            'volume_spike_multiplier': 3.0,           # 3x average volume
            'depth_change_threshold': 0.20,           # 20% depth change
            'position_change_threshold': 0.15,        # 15% position change
            
            # Sophistication scoring weights
            'sophistication_weights': {
                'execution_quality': 0.25,     # How well-executed the trades are
                'timing_precision': 0.20,      # Timing relative to technical levels
                'market_impact': 0.20,         # Minimal market impact = higher sophistication
                'pattern_complexity': 0.15,    # Complexity of the pattern
                'coordination': 0.10,          # Evidence of coordination
                'stealth': 0.10               # Attempts to hide activity
            }
        })
        
        # Historical data storage for pattern analysis
        self.orderflow_history = defaultdict(lambda: deque(maxlen=100))
        self.volume_history = defaultdict(lambda: deque(maxlen=100))
        self.depth_history = defaultdict(lambda: deque(maxlen=50))
        self.position_history = defaultdict(lambda: deque(maxlen=50))
        
        # Alert tracking
        self.last_alerts = {}  # symbol -> timestamp
        self.alert_counts = defaultdict(int)  # hourly alert counting
        self.alert_history = deque(maxlen=1000)
        
        # Performance metrics
        self.detection_stats = {
            'total_detections': 0,
            'alerts_sent': 0,
            'sophistication_distribution': defaultdict(int),
            'event_type_counts': defaultdict(int)
        }
        
        self.logger.info("SmartMoneyDetector initialized with sophisticated pattern detection")
    
    async def analyze_market_data(self, symbol: str, market_data: Dict[str, Any]) -> List[SmartMoneyEvent]:
        """
        Analyze market data for smart money patterns.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data including orderbook, trades, ticker
            
        Returns:
            List of detected smart money events
        """
        if not self.smart_money_config.get('enabled', True):
            return []
        
        events = []
        current_time = time.time()
        
        try:
            # Update historical data
            self._update_historical_data(symbol, market_data, current_time)
            
            # Check if we have sufficient data for analysis
            if not self._has_sufficient_data(symbol):
                return []
            
            # Detect different types of smart money events
            orderflow_events = await self._detect_orderflow_imbalance(symbol, market_data, current_time)
            volume_events = await self._detect_volume_spikes(symbol, market_data, current_time)
            depth_events = await self._detect_depth_changes(symbol, market_data, current_time)
            position_events = await self._detect_position_changes(symbol, market_data, current_time)
            
            # Combine all events
            events.extend(orderflow_events)
            events.extend(volume_events)
            events.extend(depth_events)
            events.extend(position_events)
            
            # Filter events by sophistication and confidence thresholds
            filtered_events = self._filter_events(events)
            
            # Update statistics
            self.detection_stats['total_detections'] += len(events)
            for event in filtered_events:
                self.detection_stats['event_type_counts'][event.event_type.value] += 1
                self.detection_stats['sophistication_distribution'][event.sophistication_level.value] += 1
            
            self.logger.debug(f"Smart money analysis for {symbol}: {len(events)} events detected, {len(filtered_events)} passed filters")
            
            return filtered_events
            
        except Exception as e:
            self.logger.error(f"Error in smart money analysis for {symbol}: {str(e)}")
            return []
    
    def _update_historical_data(self, symbol: str, market_data: Dict[str, Any], timestamp: float) -> None:
        """Update historical data for pattern analysis."""
        try:
            # Update orderflow history
            orderbook = market_data.get('orderbook', {})
            if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                bid_volume = sum(float(bid[1]) for bid in orderbook['bids'][:10])
                ask_volume = sum(float(ask[1]) for ask in orderbook['asks'][:10])
                total_volume = bid_volume + ask_volume
                
                if total_volume > 0:
                    orderflow_imbalance = (bid_volume - ask_volume) / total_volume
                    self.orderflow_history[symbol].append({
                        'timestamp': timestamp,
                        'imbalance': orderflow_imbalance,
                        'bid_volume': bid_volume,
                        'ask_volume': ask_volume,
                        'total_volume': total_volume
                    })
            
            # Update volume history
            ticker = market_data.get('ticker', {})
            if ticker:
                volume = float(ticker.get('baseVolume', 0))
                if volume > 0:
                    self.volume_history[symbol].append({
                        'timestamp': timestamp,
                        'volume': volume,
                        'price': float(ticker.get('last', 0))
                    })
            
            # Update depth history
            if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                bid_depth = sum(float(bid[1]) * float(bid[0]) for bid in orderbook['bids'][:20])
                ask_depth = sum(float(ask[1]) * float(ask[0]) for ask in orderbook['asks'][:20])
                
                self.depth_history[symbol].append({
                    'timestamp': timestamp,
                    'bid_depth': bid_depth,
                    'ask_depth': ask_depth,
                    'total_depth': bid_depth + ask_depth
                })
            
            # Update position history (using OI if available)
            oi = market_data.get('open_interest', 0)
            if oi and oi > 0:
                self.position_history[symbol].append({
                    'timestamp': timestamp,
                    'open_interest': float(oi),
                    'price': float(ticker.get('last', 0)) if ticker else 0
                })
                
        except Exception as e:
            self.logger.debug(f"Error updating historical data for {symbol}: {str(e)}")
    
    def _has_sufficient_data(self, symbol: str) -> bool:
        """Check if we have sufficient historical data for analysis."""
        return (len(self.orderflow_history[symbol]) >= 10 and
                len(self.volume_history[symbol]) >= 10 and
                len(self.depth_history[symbol]) >= 10)
    
    async def _detect_orderflow_imbalance(self, symbol: str, market_data: Dict[str, Any], timestamp: float) -> List[SmartMoneyEvent]:
        """Detect sophisticated orderflow imbalance patterns."""
        events = []
        
        try:
            orderflow_data = list(self.orderflow_history[symbol])
            if len(orderflow_data) < 10:
                return events
            
            # Get recent orderflow pattern
            recent_data = orderflow_data[-10:]
            current_imbalance = recent_data[-1]['imbalance']
            
            # Calculate moving average and volatility
            imbalances = [d['imbalance'] for d in recent_data]
            avg_imbalance = np.mean(imbalances)
            imbalance_std = np.std(imbalances)
            
            # Detect significant imbalance
            threshold = self.smart_money_config['orderflow_imbalance_threshold']
            if abs(current_imbalance) > threshold:
                
                # Calculate sophistication score
                sophistication_score = self._calculate_orderflow_sophistication(
                    symbol, recent_data, current_imbalance, avg_imbalance, imbalance_std
                )
                
                # Calculate confidence based on pattern consistency
                confidence = min(abs(current_imbalance) / threshold, 1.0)
                
                # Create event
                event = SmartMoneyEvent(
                    event_type=SmartMoneyEventType.ORDERFLOW_IMBALANCE,
                    symbol=symbol,
                    timestamp=timestamp,
                    sophistication_score=sophistication_score,
                    confidence=confidence,
                    data={
                        'side': 'buy' if current_imbalance > 0 else 'sell',
                        'imbalance': current_imbalance,
                        'avg_imbalance': avg_imbalance,
                        'imbalance_std': imbalance_std,
                        'pattern_consistency': self._calculate_pattern_consistency(imbalances),
                        'execution_quality': self._assess_execution_quality(recent_data),
                        'stealth_score': self._assess_stealth_level(recent_data)
                    }
                )
                
                events.append(event)
                
        except Exception as e:
            self.logger.debug(f"Error detecting orderflow imbalance for {symbol}: {str(e)}")
        
        return events
    
    async def _detect_volume_spikes(self, symbol: str, market_data: Dict[str, Any], timestamp: float) -> List[SmartMoneyEvent]:
        """Detect strategic volume spikes at key levels."""
        events = []
        
        try:
            volume_data = list(self.volume_history[symbol])
            if len(volume_data) < 20:
                return events
            
            # Calculate volume metrics
            recent_volumes = [d['volume'] for d in volume_data[-20:]]
            current_volume = recent_volumes[-1]
            avg_volume = np.mean(recent_volumes[:-1])  # Exclude current
            
            # Detect volume spike
            spike_multiplier = self.smart_money_config['volume_spike_multiplier']
            if current_volume > avg_volume * spike_multiplier:
                
                # Calculate sophistication score
                sophistication_score = self._calculate_volume_sophistication(
                    symbol, volume_data, current_volume, avg_volume, market_data
                )
                
                # Calculate confidence
                spike_ratio = current_volume / avg_volume
                confidence = min((spike_ratio - spike_multiplier) / spike_multiplier, 1.0)
                
                # Create event
                event = SmartMoneyEvent(
                    event_type=SmartMoneyEventType.VOLUME_SPIKE,
                    symbol=symbol,
                    timestamp=timestamp,
                    sophistication_score=sophistication_score,
                    confidence=confidence,
                    data={
                        'spike_ratio': spike_ratio,
                        'current_volume': current_volume,
                        'avg_volume': avg_volume,
                        'timing_score': self._assess_timing_quality(symbol, market_data),
                        'technical_level_proximity': self._assess_technical_proximity(symbol, market_data),
                        'coordination_evidence': self._detect_coordination_evidence(volume_data)
                    }
                )
                
                events.append(event)
                
        except Exception as e:
            self.logger.debug(f"Error detecting volume spikes for {symbol}: {str(e)}")
        
        return events
    
    async def _detect_depth_changes(self, symbol: str, market_data: Dict[str, Any], timestamp: float) -> List[SmartMoneyEvent]:
        """Detect sophisticated depth manipulation patterns."""
        events = []
        
        try:
            depth_data = list(self.depth_history[symbol])
            if len(depth_data) < 15:
                return events
            
            # Calculate depth change
            current_depth = depth_data[-1]
            previous_depth = depth_data[-2]
            
            bid_change = (current_depth['bid_depth'] - previous_depth['bid_depth']) / previous_depth['bid_depth']
            ask_change = (current_depth['ask_depth'] - previous_depth['ask_depth']) / previous_depth['ask_depth']
            
            threshold = self.smart_money_config['depth_change_threshold']
            
            # Detect significant depth changes
            if abs(bid_change) > threshold or abs(ask_change) > threshold:
                
                # Determine dominant side
                if abs(bid_change) > abs(ask_change):
                    side = 'bid'
                    change_ratio = bid_change
                else:
                    side = 'ask'
                    change_ratio = ask_change
                
                # Calculate sophistication score
                sophistication_score = self._calculate_depth_sophistication(
                    symbol, depth_data, change_ratio, side, market_data
                )
                
                # Calculate confidence
                confidence = min(abs(change_ratio) / threshold, 1.0)
                
                # Create event
                event = SmartMoneyEvent(
                    event_type=SmartMoneyEventType.DEPTH_CHANGE,
                    symbol=symbol,
                    timestamp=timestamp,
                    sophistication_score=sophistication_score,
                    confidence=confidence,
                    data={
                        'side': side,
                        'change_ratio': change_ratio,
                        'bid_change': bid_change,
                        'ask_change': ask_change,
                        'manipulation_score': self._assess_manipulation_sophistication(depth_data),
                        'liquidity_provision_pattern': self._analyze_liquidity_patterns(depth_data),
                        'market_impact_minimization': self._assess_impact_minimization(depth_data)
                    }
                )
                
                events.append(event)
                
        except Exception as e:
            self.logger.debug(f"Error detecting depth changes for {symbol}: {str(e)}")
        
        return events
    
    async def _detect_position_changes(self, symbol: str, market_data: Dict[str, Any], timestamp: float) -> List[SmartMoneyEvent]:
        """Detect institutional position adjustments."""
        events = []
        
        try:
            position_data = list(self.position_history[symbol])
            if len(position_data) < 10:
                return events
            
            # Calculate position change
            current_oi = position_data[-1]['open_interest']
            previous_oi = position_data[-2]['open_interest']
            
            change_ratio = (current_oi - previous_oi) / previous_oi
            threshold = self.smart_money_config['position_change_threshold']
            
            if abs(change_ratio) > threshold:
                
                # Calculate sophistication score
                sophistication_score = self._calculate_position_sophistication(
                    symbol, position_data, change_ratio, market_data
                )
                
                # Calculate confidence
                confidence = min(abs(change_ratio) / threshold, 1.0)
                
                # Determine direction
                direction = 'increase' if change_ratio > 0 else 'decrease'
                
                # Create event
                event = SmartMoneyEvent(
                    event_type=SmartMoneyEventType.POSITION_CHANGE,
                    symbol=symbol,
                    timestamp=timestamp,
                    sophistication_score=sophistication_score,
                    confidence=confidence,
                    data={
                        'direction': direction,
                        'change_ratio': change_ratio,
                        'change_value': current_oi - previous_oi,
                        'current_oi': current_oi,
                        'previous_oi': previous_oi,
                        'institutional_pattern': self._detect_institutional_pattern(position_data),
                        'timing_coordination': self._assess_position_timing(position_data, market_data)
                    }
                )
                
                events.append(event)
                
        except Exception as e:
            self.logger.debug(f"Error detecting position changes for {symbol}: {str(e)}")
        
        return events
    
    def _calculate_orderflow_sophistication(self, symbol: str, recent_data: List[Dict], 
                                         current_imbalance: float, avg_imbalance: float, 
                                         imbalance_std: float) -> float:
        """Calculate sophistication score for orderflow patterns."""
        score = 5.0  # Base score
        
        try:
            # Execution quality: consistent imbalance suggests coordination
            consistency = 1.0 - (imbalance_std / (abs(avg_imbalance) + 0.01))
            score += consistency * 2.0
            
            # Timing precision: check if imbalance occurs at round numbers or technical levels
            timing_score = self._assess_timing_quality(symbol, {'orderflow': recent_data})
            score += timing_score * 1.5
            
            # Market impact: lower volatility during imbalance = higher sophistication
            impact_score = self._assess_market_impact_minimization(recent_data)
            score += impact_score * 1.5
            
            # Pattern complexity: sophisticated patterns show gradual buildup
            complexity_score = self._assess_pattern_complexity(recent_data)
            score += complexity_score * 1.0
            
        except Exception as e:
            self.logger.debug(f"Error calculating orderflow sophistication: {str(e)}")
        
        return min(max(score, 1.0), 10.0)
    
    def _calculate_volume_sophistication(self, symbol: str, volume_data: List[Dict], 
                                       current_volume: float, avg_volume: float, 
                                       market_data: Dict[str, Any]) -> float:
        """Calculate sophistication score for volume patterns."""
        score = 5.0  # Base score
        
        try:
            # Timing precision: volume spikes at key technical levels
            timing_score = self._assess_timing_quality(symbol, market_data)
            score += timing_score * 2.5
            
            # Execution quality: gradual volume increase vs sudden spike
            execution_score = self._assess_volume_execution_quality(volume_data)
            score += execution_score * 2.0
            
            # Coordination evidence: multiple coordinated volume events
            coordination_score = self._detect_coordination_evidence(volume_data)
            score += coordination_score * 1.5
            
        except Exception as e:
            self.logger.debug(f"Error calculating volume sophistication: {str(e)}")
        
        return min(max(score, 1.0), 10.0)
    
    def _calculate_depth_sophistication(self, symbol: str, depth_data: List[Dict], 
                                      change_ratio: float, side: str, 
                                      market_data: Dict[str, Any]) -> float:
        """Calculate sophistication score for depth manipulation."""
        score = 5.0  # Base score
        
        try:
            # Manipulation sophistication: gradual vs sudden changes
            manipulation_score = self._assess_manipulation_sophistication(depth_data)
            score += manipulation_score * 2.0
            
            # Stealth level: attempts to hide large orders
            stealth_score = self._assess_stealth_level(depth_data)
            score += stealth_score * 2.0
            
            # Market impact minimization
            impact_score = self._assess_impact_minimization(depth_data)
            score += impact_score * 1.5
            
            # Timing with market events
            timing_score = self._assess_timing_quality(symbol, market_data)
            score += timing_score * 0.5
            
        except Exception as e:
            self.logger.debug(f"Error calculating depth sophistication: {str(e)}")
        
        return min(max(score, 1.0), 10.0)
    
    def _calculate_position_sophistication(self, symbol: str, position_data: List[Dict], 
                                         change_ratio: float, market_data: Dict[str, Any]) -> float:
        """Calculate sophistication score for position changes."""
        score = 5.0  # Base score
        
        try:
            # Institutional pattern recognition
            institutional_score = self._detect_institutional_pattern(position_data)
            score += institutional_score * 2.5
            
            # Timing coordination with market events
            timing_score = self._assess_position_timing(position_data, market_data)
            score += timing_score * 2.0
            
            # Gradual vs sudden position changes
            execution_score = self._assess_position_execution_quality(position_data)
            score += execution_score * 1.5
            
        except Exception as e:
            self.logger.debug(f"Error calculating position sophistication: {str(e)}")
        
        return min(max(score, 1.0), 10.0)
    
    # Helper methods for sophistication assessment
    def _assess_timing_quality(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Assess timing quality relative to technical levels."""
        # Simplified implementation - in production, integrate with technical analysis
        return 0.5  # Neutral score
    
    def _assess_execution_quality(self, data: List[Dict]) -> float:
        """Assess execution quality based on consistency and gradual changes."""
        if len(data) < 5:
            return 0.0
        
        # Check for gradual vs sudden changes
        changes = []
        for i in range(1, len(data)):
            if 'imbalance' in data[i] and 'imbalance' in data[i-1]:
                change = abs(data[i]['imbalance'] - data[i-1]['imbalance'])
                changes.append(change)
        
        if not changes:
            return 0.0
        
        # Lower variance = better execution quality
        variance = np.var(changes)
        return max(0.0, 1.0 - variance * 10)  # Scale appropriately
    
    def _assess_stealth_level(self, data: List[Dict]) -> float:
        """Assess stealth level of trading activity."""
        # Simplified implementation - check for attempts to hide activity
        return 0.5  # Neutral score
    
    def _calculate_pattern_consistency(self, values: List[float]) -> float:
        """Calculate consistency of pattern."""
        if len(values) < 3:
            return 0.0
        
        # Check for consistent direction
        positive_count = sum(1 for v in values if v > 0)
        negative_count = len(values) - positive_count
        
        consistency = abs(positive_count - negative_count) / len(values)
        return consistency
    
    def _assess_technical_proximity(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Assess proximity to technical levels."""
        # Simplified implementation
        return 0.5  # Neutral score
    
    def _detect_coordination_evidence(self, data: List[Dict]) -> float:
        """Detect evidence of coordinated activity."""
        # Simplified implementation - look for synchronized patterns
        return 0.5  # Neutral score
    
    def _assess_manipulation_sophistication(self, data: List[Dict]) -> float:
        """Assess sophistication of manipulation techniques."""
        return 0.5  # Neutral score
    
    def _analyze_liquidity_patterns(self, data: List[Dict]) -> str:
        """Analyze liquidity provision patterns."""
        return "gradual_provision"  # Simplified
    
    def _assess_impact_minimization(self, data: List[Dict]) -> float:
        """Assess market impact minimization techniques."""
        return 0.5  # Neutral score
    
    def _detect_institutional_pattern(self, data: List[Dict]) -> float:
        """Detect institutional trading patterns."""
        return 0.5  # Neutral score
    
    def _assess_position_timing(self, position_data: List[Dict], market_data: Dict[str, Any]) -> float:
        """Assess timing of position changes."""
        return 0.5  # Neutral score
    
    def _assess_volume_execution_quality(self, data: List[Dict]) -> float:
        """Assess volume execution quality."""
        return 0.5  # Neutral score
    
    def _assess_market_impact_minimization(self, data: List[Dict]) -> float:
        """Assess market impact minimization."""
        return 0.5  # Neutral score
    
    def _assess_pattern_complexity(self, data: List[Dict]) -> float:
        """Assess pattern complexity."""
        return 0.5  # Neutral score
    
    def _assess_position_execution_quality(self, data: List[Dict]) -> float:
        """Assess position execution quality."""
        return 0.5  # Neutral score
    
    def _filter_events(self, events: List[SmartMoneyEvent]) -> List[SmartMoneyEvent]:
        """Filter events by sophistication and confidence thresholds."""
        min_sophistication = self.smart_money_config['min_sophistication_score']
        min_confidence = self.smart_money_config['min_confidence']
        
        filtered = []
        for event in events:
            if (event.sophistication_score >= min_sophistication and 
                event.confidence >= min_confidence):
                filtered.append(event)
        
        return filtered
    
    def should_send_alert(self, symbol: str, event: SmartMoneyEvent) -> bool:
        """Check if we should send an alert for this event."""
        current_time = time.time()
        cooldown_minutes = self.smart_money_config['cooldown_minutes']
        
        # Check symbol-specific cooldown
        last_alert_time = self.last_alerts.get(symbol, 0)
        if current_time - last_alert_time < cooldown_minutes * 60:
            return False
        
        # Check global rate limiting
        hour_ago = current_time - 3600
        recent_alerts = sum(1 for t in self.alert_history if t > hour_ago)
        max_alerts = self.smart_money_config['max_alerts_per_hour']
        
        if recent_alerts >= max_alerts:
            return False
        
        return True
    
    def record_alert_sent(self, symbol: str, event: SmartMoneyEvent) -> None:
        """Record that an alert was sent."""
        current_time = time.time()
        self.last_alerts[symbol] = current_time
        self.alert_history.append(current_time)
        self.detection_stats['alerts_sent'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            'detection_stats': dict(self.detection_stats),
            'sophistication_distribution': dict(self.detection_stats['sophistication_distribution']),
            'event_type_counts': dict(self.detection_stats['event_type_counts']),
            'recent_alert_rate': len([t for t in self.alert_history if time.time() - t < 3600]),
            'active_symbols': len(self.last_alerts)
        } 