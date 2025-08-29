"""
Real-time Data Pipeline - Phase 3 Integration with Phase 2 Cache
Bridges cached data with real-time streaming for mobile optimization
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Set, List
from datetime import datetime
import time
import json
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class DataChangeEvent:
    """Represents a data change event"""
    data_type: str
    change_type: str  # 'update', 'new', 'delete'
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    priority: str = 'normal'  # 'critical', 'high', 'normal', 'low'

class RealtimeDataPipeline:
    """
    Real-time Data Pipeline for Phase 3
    Monitors Phase 2 cache for changes and streams to mobile clients
    """
    
    def __init__(self):
        self._cache_adapter = None
        self._mobile_stream_manager = None
        self._monitoring_active = False
        self._monitoring_tasks: List[asyncio.Task] = []
        
        # Data snapshots for change detection
        self._data_snapshots = {
            'confluence_scores': {},
            'market_overview': {},
            'signals': [],
            'alerts': [],
            'market_movers': {}
        }
        
        # Change thresholds
        self._change_thresholds = {
            'confluence_score_change': 5.0,    # 5% change triggers update
            'price_change': 2.0,                # 2% price change
            'volume_change': 20.0,              # 20% volume change
            'new_signal_confidence': 0.65       # Minimum confidence for streaming
        }
        
        # Update intervals (seconds)
        self._monitor_intervals = {
            'confluence': 3.0,      # Monitor confluence every 3 seconds
            'signals': 1.0,         # Monitor signals every second  
            'alerts': 2.0,          # Monitor alerts every 2 seconds
            'market_data': 5.0,     # Monitor market data every 5 seconds
            'health_check': 30.0    # Health check every 30 seconds
        }
        
    async def initialize(self):
        """Initialize the real-time pipeline with dependencies"""
        try:
            # Import dependencies
            from src.api.cache_adapter_direct import cache_adapter
            from src.api.websocket.mobile_stream_manager import mobile_stream_manager
            
            self._cache_adapter = cache_adapter
            self._mobile_stream_manager = mobile_stream_manager
            
            logger.info("✅ Real-time pipeline initialized with Phase 2 cache adapter")
            
        except Exception as e:
            logger.error(f"Failed to initialize real-time pipeline: {e}")
            raise
            
    async def start_monitoring(self):
        """Start monitoring data sources for changes"""
        if not self._cache_adapter or not self._mobile_stream_manager:
            await self.initialize()
            
        if self._monitoring_active:
            logger.debug("Real-time monitoring already active")
            return
            
        self._monitoring_active = True
        logger.info("🚀 Starting Phase 3 real-time data monitoring")
        
        # Start monitoring tasks
        self._monitoring_tasks = [
            asyncio.create_task(self._monitor_confluence_changes()),
            asyncio.create_task(self._monitor_signal_generation()),
            asyncio.create_task(self._monitor_alert_triggers()),
            asyncio.create_task(self._monitor_market_changes()),
            asyncio.create_task(self._monitor_system_health())
        ]
        
        # Wait for tasks to start
        await asyncio.sleep(1)
        
        logger.info("✅ Real-time monitoring started with 5 background tasks")
        
    async def stop_monitoring(self):
        """Stop all monitoring tasks"""
        self._monitoring_active = False
        
        for task in self._monitoring_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        logger.info("🛑 Real-time monitoring stopped")
        
    async def _monitor_confluence_changes(self):
        """Monitor confluence score changes and stream to mobile clients"""
        logger.info("📊 Starting confluence score monitoring")
        
        while self._monitoring_active:
            try:
                # Get current confluence data from Phase 2 cache
                mobile_data = await self._cache_adapter.get_mobile_data()
                
                if mobile_data and mobile_data.get('confluence_scores'):
                    current_scores = {
                        s.get('symbol', ''): s.get('confluence_score', 0)
                        for s in mobile_data['confluence_scores']
                        if isinstance(s, dict) and s.get('symbol')
                    }
                    
                    # Check for significant changes
                    changes = self._detect_confluence_changes(current_scores)
                    
                    if changes:
                        # Create streaming data
                        stream_data = {
                            'confluence_scores': mobile_data['confluence_scores'],
                            'changes': changes,
                            'market_overview': mobile_data.get('market_overview', {}),
                            'cache_source': mobile_data.get('cache_source', 'phase2_cache'),
                            'change_summary': {
                                'total_changes': len(changes),
                                'significant_moves': [c for c in changes if abs(c['change_pct']) > 10],
                                'timestamp': time.time()
                            }
                        }
                        
                        # Stream to mobile clients
                        from src.api.websocket.mobile_stream_manager import StreamChannel, MessageType, Priority
                        
                        priority = Priority.HIGH if any(abs(c['change_pct']) > 15 for c in changes) else Priority.NORMAL
                        
                        await self._mobile_stream_manager.broadcast_update(
                            channel=StreamChannel.CONFLUENCE_LIVE.value,
                            data=stream_data,
                            message_type=MessageType.CONFLUENCE_UPDATE,
                            priority=priority
                        )
                        
                        logger.info(f"📊 Streamed confluence changes: {len(changes)} symbols updated")
                    
                    # Update snapshot
                    self._data_snapshots['confluence_scores'] = current_scores
                
                await asyncio.sleep(self._monitor_intervals['confluence'])
                
            except Exception as e:
                logger.error(f"Error monitoring confluence changes: {e}")
                await asyncio.sleep(5)
                
    def _detect_confluence_changes(self, current_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect significant changes in confluence scores"""
        changes = []
        previous_scores = self._data_snapshots.get('confluence_scores', {})
        threshold = self._change_thresholds['confluence_score_change']
        
        for symbol, current_score in current_scores.items():
            previous_score = previous_scores.get(symbol, 0)
            
            if previous_score > 0:  # Only check if we have previous data
                change_pct = ((current_score - previous_score) / previous_score) * 100
                
                if abs(change_pct) >= threshold:
                    changes.append({
                        'symbol': symbol,
                        'previous_score': previous_score,
                        'current_score': current_score,
                        'change_pct': round(change_pct, 2),
                        'direction': 'up' if change_pct > 0 else 'down',
                        'significance': 'high' if abs(change_pct) > 15 else 'medium' if abs(change_pct) > 10 else 'normal'
                    })
        
        return changes
        
    async def _monitor_signal_generation(self):
        """Monitor for new trading signal generation"""
        logger.info("🎯 Starting signal generation monitoring")
        last_signal_count = 0
        
        while self._monitoring_active:
            try:
                # Get current signals from cache
                signals_data = await self._cache_adapter.get_signals()
                
                if signals_data and 'signals' in signals_data:
                    current_signals = signals_data['signals']
                    current_count = len(current_signals)
                    
                    # Check for new signals
                    if current_count > last_signal_count:
                        new_signals = current_signals[last_signal_count:]
                        
                        # Filter signals by confidence
                        high_confidence_signals = [
                            signal for signal in new_signals
                            if isinstance(signal, dict) and 
                            signal.get('confidence', 0) >= self._change_thresholds['new_signal_confidence']
                        ]
                        
                        if high_confidence_signals:
                            for signal in high_confidence_signals:
                                stream_data = {
                                    'signal': signal,
                                    'type': 'new_signal',
                                    'confidence': signal.get('confidence', 0),
                                    'symbol': signal.get('symbol', 'UNKNOWN'),
                                    'action': signal.get('action', 'HOLD'),
                                    'timestamp': time.time()
                                }
                                
                                # Determine priority based on confidence
                                confidence = signal.get('confidence', 0)
                                from src.api.websocket.mobile_stream_manager import StreamChannel, MessageType, Priority
                                
                                priority = Priority.CRITICAL if confidence > 0.85 else Priority.HIGH
                                
                                # Stream new signal immediately
                                await self._mobile_stream_manager.broadcast_update(
                                    channel=StreamChannel.SIGNAL_STREAM.value,
                                    data=stream_data,
                                    message_type=MessageType.SIGNAL_ALERT,
                                    priority=priority
                                )
                            
                            logger.info(f"🎯 Streamed {len(high_confidence_signals)} new high-confidence signals")
                    
                    last_signal_count = current_count
                    
                await asyncio.sleep(self._monitor_intervals['signals'])
                
            except Exception as e:
                logger.error(f"Error monitoring signal generation: {e}")
                await asyncio.sleep(3)
                
    async def _monitor_alert_triggers(self):
        """Monitor for new alert triggers"""
        logger.info("🚨 Starting alert monitoring")
        last_alert_count = 0
        
        while self._monitoring_active:
            try:
                # Get current alerts from cache
                alerts_data = await self._cache_adapter.get_market_analysis()
                
                # For now, create synthetic alerts based on market conditions
                current_alerts = await self._generate_synthetic_alerts()
                current_count = len(current_alerts)
                
                if current_count > last_alert_count:
                    new_alerts = current_alerts[last_alert_count:]
                    
                    for alert in new_alerts:
                        stream_data = {
                            'alert': alert,
                            'type': 'market_alert',
                            'severity': alert.get('severity', 'normal'),
                            'message': alert.get('message', ''),
                            'timestamp': time.time()
                        }
                        
                        # Determine priority
                        from src.api.websocket.mobile_stream_manager import StreamChannel, MessageType, Priority
                        
                        severity = alert.get('severity', 'normal')
                        priority = Priority.CRITICAL if severity == 'critical' else Priority.HIGH if severity == 'high' else Priority.NORMAL
                        
                        await self._mobile_stream_manager.broadcast_update(
                            channel=StreamChannel.ALERT_PRIORITY.value,
                            data=stream_data,
                            message_type=MessageType.SYSTEM_ALERT,
                            priority=priority
                        )
                    
                    logger.info(f"🚨 Streamed {len(new_alerts)} new alerts")
                
                last_alert_count = current_count
                
                await asyncio.sleep(self._monitor_intervals['alerts'])
                
            except Exception as e:
                logger.error(f"Error monitoring alerts: {e}")
                await asyncio.sleep(5)
                
    async def _generate_synthetic_alerts(self) -> List[Dict[str, Any]]:
        """Generate synthetic alerts based on market conditions (placeholder)"""
        alerts = []
        
        try:
            # Get market overview for alert generation
            mobile_data = await self._cache_adapter.get_mobile_data()
            
            if mobile_data and mobile_data.get('market_overview'):
                market_overview = mobile_data['market_overview']
                
                # Check for high volatility
                volatility = market_overview.get('volatility', 0)
                if volatility > 50:  # High volatility threshold
                    alerts.append({
                        'id': f"volatility_{int(time.time())}",
                        'type': 'volatility_alert',
                        'severity': 'high' if volatility > 70 else 'medium',
                        'message': f"High market volatility detected: {volatility}%",
                        'market_regime': market_overview.get('market_regime', 'UNKNOWN'),
                        'timestamp': time.time()
                    })
                
                # Check for trend changes
                regime = market_overview.get('market_regime', 'NEUTRAL')
                if regime != self._data_snapshots.get('market_regime'):
                    alerts.append({
                        'id': f"regime_{int(time.time())}",
                        'type': 'regime_change',
                        'severity': 'medium',
                        'message': f"Market regime changed to {regime}",
                        'previous_regime': self._data_snapshots.get('market_regime', 'UNKNOWN'),
                        'new_regime': regime,
                        'timestamp': time.time()
                    })
                    
                    # Update snapshot
                    self._data_snapshots['market_regime'] = regime
                    
        except Exception as e:
            logger.error(f"Error generating synthetic alerts: {e}")
            
        return alerts
        
    async def _monitor_market_changes(self):
        """Monitor market data changes"""
        logger.info("📈 Starting market data monitoring")
        
        while self._monitoring_active:
            try:
                # Get market movers data
                market_movers = await self._cache_adapter.get_market_movers()
                
                if market_movers and self._data_snapshots.get('market_movers') != market_movers:
                    # Detect significant market movements
                    movements = await self._detect_market_movements(market_movers)
                    
                    if movements:
                        stream_data = {
                            'market_movers': market_movers,
                            'significant_movements': movements,
                            'type': 'market_movement',
                            'timestamp': time.time()
                        }
                        
                        from src.api.websocket.mobile_stream_manager import StreamChannel, MessageType, Priority
                        
                        await self._mobile_stream_manager.broadcast_update(
                            channel=StreamChannel.MARKET_PULSE.value,
                            data=stream_data,
                            message_type=MessageType.MARKET_UPDATE,
                            priority=Priority.HIGH
                        )
                        
                        logger.info(f"📈 Streamed market movements: {len(movements)} significant changes")
                    
                    self._data_snapshots['market_movers'] = market_movers
                
                await asyncio.sleep(self._monitor_intervals['market_data'])
                
            except Exception as e:
                logger.error(f"Error monitoring market changes: {e}")
                await asyncio.sleep(5)
                
    async def _detect_market_movements(self, market_movers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect significant market movements"""
        movements = []
        threshold = self._change_thresholds['price_change']
        
        # Check top gainers for significant moves
        gainers = market_movers.get('gainers', [])
        for gainer in gainers[:5]:  # Top 5 gainers
            if isinstance(gainer, dict):
                change = gainer.get('change_24h', 0)
                if change > threshold:
                    movements.append({
                        'symbol': gainer.get('symbol', 'UNKNOWN'),
                        'type': 'significant_gain',
                        'change_24h': change,
                        'price': gainer.get('price', 0),
                        'volume': gainer.get('volume', 0)
                    })
        
        # Check top losers for significant moves
        losers = market_movers.get('losers', [])
        for loser in losers[:5]:  # Top 5 losers
            if isinstance(loser, dict):
                change = loser.get('change_24h', 0)
                if abs(change) > threshold:
                    movements.append({
                        'symbol': loser.get('symbol', 'UNKNOWN'),
                        'type': 'significant_loss',
                        'change_24h': change,
                        'price': loser.get('price', 0),
                        'volume': loser.get('volume', 0)
                    })
        
        return movements
        
    async def _monitor_system_health(self):
        """Monitor system health and performance"""
        logger.info("🔍 Starting system health monitoring")
        
        while self._monitoring_active:
            try:
                # Get system health from cache
                health_data = await self._cache_adapter.get_health_status()
                
                if health_data:
                    # Check for health issues
                    status = health_data.get('status', 'unknown')
                    
                    if status != 'healthy':
                        # Stream health alert
                        stream_data = {
                            'health_status': health_data,
                            'type': 'system_health',
                            'status': status,
                            'timestamp': time.time(),
                            'components': health_data.get('components', {})
                        }
                        
                        from src.api.websocket.mobile_stream_manager import StreamChannel, MessageType, Priority
                        
                        priority = Priority.CRITICAL if status == 'critical' else Priority.HIGH
                        
                        await self._mobile_stream_manager.broadcast_update(
                            channel=StreamChannel.DASHBOARD_SYNC.value,
                            data=stream_data,
                            message_type=MessageType.SYSTEM_ALERT,
                            priority=priority
                        )
                        
                        logger.warning(f"🔍 System health issue detected: {status}")
                
                await asyncio.sleep(self._monitor_intervals['health_check'])
                
            except Exception as e:
                logger.error(f"Error monitoring system health: {e}")
                await asyncio.sleep(30)
                
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'monitoring_active': self._monitoring_active,
            'active_tasks': len([t for t in self._monitoring_tasks if not t.done()]),
            'data_snapshots': {
                'confluence_symbols': len(self._data_snapshots.get('confluence_scores', {})),
                'market_regime': self._data_snapshots.get('market_regime', 'unknown'),
                'last_update': time.time()
            },
            'monitor_intervals': self._monitor_intervals,
            'change_thresholds': self._change_thresholds,
            'pipeline_uptime': time.time() if self._monitoring_active else 0
        }

# Global real-time pipeline instance
realtime_pipeline = RealtimeDataPipeline()