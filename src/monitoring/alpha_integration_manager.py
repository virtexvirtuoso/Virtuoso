from src.utils.task_tracker import create_tracked_task
#!/usr/bin/env python3
"""
Alpha Integration Manager - Safe Production Rollout
Manages transition between legacy and optimized alpha scanning systems
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

# Import both scanning systems
from src.monitoring.alpha_scanner import AlphaOpportunityScanner as LegacyScanner
from src.monitoring.optimized_alpha_scanner import OptimizedAlphaScanner, AlphaAlert, AlertTier

logger = logging.getLogger(__name__)

class ScannerMode(Enum):
    """Scanner operation modes."""
    LEGACY_ONLY = "legacy_only"
    OPTIMIZED_ONLY = "optimized_only"
    PARALLEL = "parallel"          # Run both, compare results
    A_B_TEST = "a_b_test"         # Split traffic between systems
    GRADUAL_ROLLOUT = "gradual_rollout"  # Gradually increase optimized usage

@dataclass
class ScannerPerformanceMetrics:
    """Performance comparison metrics."""
    scanner_type: str
    total_alerts: int
    high_value_alerts: int
    average_alpha: float
    average_confidence: float
    processing_time_ms: float
    memory_usage_mb: float
    error_count: int
    timestamp: datetime

class AlphaIntegrationManager:
    """
    Manages safe transition between legacy and optimized alpha scanning.
    
    Features:
    - Feature flag control
    - Parallel testing
    - Performance comparison
    - Gradual rollout
    - Automatic rollback on issues
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """Initialize the integration manager."""
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Get scanner configurations
        self.legacy_config = config.get('alpha_scanning', {})
        self.optimized_config = config.get('alpha_scanning_optimized', {})
        
        # Determine operation mode
        self.mode = self._determine_mode()
        
        # Initialize scanners based on mode
        self.legacy_scanner = None
        self.optimized_scanner = None
        self._initialize_scanners()
        
        # Performance tracking
        self.performance_history = []
        self.comparison_metrics = {}
        
        # Rollout control
        self.rollout_percentage = 0  # Start with 0% traffic to optimized
        self.rollout_increment = 10  # Increase by 10% each step
        self.rollout_interval_hours = 24  # Increase every 24 hours
        self.last_rollout_time = time.time()
        
        # Safety thresholds for automatic rollback
        self.safety_thresholds = {
            'max_error_rate': 0.05,      # 5% max error rate
            'min_alert_quality_ratio': 0.8,  # 80% of legacy quality minimum
            'max_processing_time_ratio': 2.0  # 2x legacy processing time max
        }
        
        self.logger.info(f"AlphaIntegrationManager initialized in {self.mode.value} mode")
    
    def _determine_mode(self) -> ScannerMode:
        """Determine operation mode based on configuration."""
        legacy_enabled = self.legacy_config.get('enabled', True)
        optimized_enabled = self.optimized_config.get('enabled', False)
        
        if optimized_enabled and legacy_enabled:
            return ScannerMode.PARALLEL
        elif optimized_enabled and not legacy_enabled:
            return ScannerMode.OPTIMIZED_ONLY
        else:
            return ScannerMode.LEGACY_ONLY
    
    def _initialize_scanners(self):
        """Initialize scanners based on operation mode."""
        try:
            if self.mode in [ScannerMode.LEGACY_ONLY, ScannerMode.PARALLEL, ScannerMode.A_B_TEST, ScannerMode.GRADUAL_ROLLOUT]:
                self.legacy_scanner = LegacyScanner(self.config, self.logger)
                self.logger.info("Legacy alpha scanner initialized")
            
            if self.mode in [ScannerMode.OPTIMIZED_ONLY, ScannerMode.PARALLEL, ScannerMode.A_B_TEST, ScannerMode.GRADUAL_ROLLOUT]:
                self.optimized_scanner = OptimizedAlphaScanner()
                self.logger.info("Optimized alpha scanner initialized")
                
        except Exception as e:
            self.logger.error(f"Error initializing scanners: {str(e)}")
            # Fallback to legacy only
            self.mode = ScannerMode.LEGACY_ONLY
            if not self.legacy_scanner:
                self.legacy_scanner = LegacyScanner(self.config, self.logger)
    
    async def scan_for_opportunities(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main scanning method that routes to appropriate scanner(s).
        
        Args:
            market_data: Market data for analysis
            
        Returns:
            List of alpha opportunities
        """
        # Check master toggle first
        alpha_alerts_enabled = self.optimized_config.get('alpha_alerts_enabled', True)
        if not alpha_alerts_enabled:
            self.logger.debug("Alpha alerts disabled via master toggle")
            return []
        
        start_time = time.time()
        
        try:
            if self.mode == ScannerMode.LEGACY_ONLY:
                return await self._scan_legacy_only(market_data)
            
            elif self.mode == ScannerMode.OPTIMIZED_ONLY:
                return await self._scan_optimized_only(market_data)
            
            elif self.mode == ScannerMode.PARALLEL:
                return await self._scan_parallel(market_data)
            
            elif self.mode == ScannerMode.GRADUAL_ROLLOUT:
                return await self._scan_gradual_rollout(market_data)
            
            else:
                self.logger.warning(f"Unknown scanner mode: {self.mode}")
                return await self._scan_legacy_only(market_data)
                
        except Exception as e:
            self.logger.error(f"Error in alpha scanning: {str(e)}")
            # Fallback to legacy scanner
            return await self._scan_legacy_only(market_data)
        
        finally:
            processing_time = (time.time() - start_time) * 1000
            self.logger.debug(f"Alpha scanning completed in {processing_time:.2f}ms")
    
    async def _scan_legacy_only(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan using legacy scanner only."""
        if not self.legacy_scanner:
            return []
        
        start_time = time.time()
        try:
            # Convert to legacy format if needed
            opportunities = self.legacy_scanner.scan_for_alpha_opportunities(market_data)
            
            # Track performance
            self._track_performance('legacy', opportunities, start_time)
            
            return self._convert_legacy_format(opportunities)
            
        except Exception as e:
            self.logger.error(f"Legacy scanner error: {str(e)}")
            return []
    
    async def _scan_optimized_only(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan using optimized scanner only."""
        if not self.optimized_scanner:
            return []
        
        start_time = time.time()
        try:
            alerts = self.optimized_scanner.scan_for_alpha_opportunities(market_data)
            
            # Track performance
            self._track_performance('optimized', alerts, start_time)
            
            return self._convert_optimized_format(alerts)
            
        except Exception as e:
            self.logger.error(f"Optimized scanner error: {str(e)}")
            return []
    
    async def _scan_parallel(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run both scanners in parallel for comparison."""
        legacy_task = create_tracked_task(self._scan_legacy_only, name="_scan_legacy_only_task")
        optimized_task = create_tracked_task(self._scan_optimized_only(market_data, name="auto_tracked_task")
        
        legacy_results, optimized_results = await asyncio.gather(
            legacy_task, optimized_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(legacy_results, Exception):
            self.logger.error(f"Legacy scanner failed: {legacy_results}")
            legacy_results = []
        
        if isinstance(optimized_results, Exception):
            self.logger.error(f"Optimized scanner failed: {optimized_results}")
            optimized_results = []
        
        # Compare results
        self._compare_results(legacy_results, optimized_results)
        
        # Return optimized results if available, otherwise legacy
        return optimized_results if optimized_results else legacy_results
    
    async def _scan_gradual_rollout(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gradually increase traffic to optimized scanner."""
        # Check if it's time to increase rollout percentage
        self._update_rollout_percentage()
        
        # Determine which scanner to use based on rollout percentage
        import random
        if random.randint(1, 100) <= self.rollout_percentage:
            return await self._scan_optimized_only(market_data)
        else:
            return await self._scan_legacy_only(market_data)
    
    def _update_rollout_percentage(self):
        """Update rollout percentage based on time and performance."""
        current_time = time.time()
        hours_since_last_update = (current_time - self.last_rollout_time) / 3600
        
        if hours_since_last_update >= self.rollout_interval_hours:
            # Check if it's safe to increase rollout
            if self._is_safe_to_increase_rollout():
                old_percentage = self.rollout_percentage
                self.rollout_percentage = min(100, self.rollout_percentage + self.rollout_increment)
                self.last_rollout_time = current_time
                
                self.logger.info(f"Rollout percentage increased from {old_percentage}% to {self.rollout_percentage}%")
            else:
                self.logger.warning("Rollout increase delayed due to performance concerns")
    
    def _is_safe_to_increase_rollout(self) -> bool:
        """Check if it's safe to increase rollout percentage."""
        if not self.comparison_metrics:
            return False
        
        latest_metrics = self.comparison_metrics.get('latest', {})
        optimized_metrics = latest_metrics.get('optimized', {})
        legacy_metrics = latest_metrics.get('legacy', {})
        
        if not optimized_metrics or not legacy_metrics:
            return False
        
        # Check error rate
        optimized_error_rate = optimized_metrics.get('error_rate', 0)
        if optimized_error_rate > self.safety_thresholds['max_error_rate']:
            return False
        
        # Check alert quality ratio
        optimized_quality = optimized_metrics.get('avg_alpha', 0)
        legacy_quality = legacy_metrics.get('avg_alpha', 1)
        quality_ratio = optimized_quality / max(legacy_quality, 0.01)
        
        if quality_ratio < self.safety_thresholds['min_alert_quality_ratio']:
            return False
        
        return True
    
    def _track_performance(self, scanner_type: str, results: List, start_time: float):
        """Track performance metrics for comparison."""
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate metrics
        total_alerts = len(results)
        high_value_alerts = 0
        total_alpha = 0
        total_confidence = 0
        
        for result in results:
            if isinstance(result, dict):
                alpha = result.get('alpha_potential', 0)
                confidence = result.get('confidence', 0)
            else:  # AlphaAlert object
                alpha = getattr(result, 'alpha_magnitude', 0)
                confidence = getattr(result, 'confidence', 0)
            
            total_alpha += alpha
            total_confidence += confidence
            
            if alpha > 0.15:  # 15%+ alpha considered high value
                high_value_alerts += 1
        
        avg_alpha = total_alpha / max(total_alerts, 1)
        avg_confidence = total_confidence / max(total_alerts, 1)
        
        metrics = ScannerPerformanceMetrics(
            scanner_type=scanner_type,
            total_alerts=total_alerts,
            high_value_alerts=high_value_alerts,
            average_alpha=avg_alpha,
            average_confidence=avg_confidence,
            processing_time_ms=processing_time,
            memory_usage_mb=self._get_memory_usage(),
            error_count=0,  # Would be tracked separately
            timestamp=datetime.now(timezone.utc)
        )
        
        self.performance_history.append(metrics)
        
        # Keep only last 100 entries
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def _compare_results(self, legacy_results: List, optimized_results: List):
        """Compare results from both scanners."""
        comparison = {
            'timestamp': datetime.now(timezone.utc),
            'legacy': {
                'count': len(legacy_results),
                'avg_alpha': self._calculate_avg_alpha(legacy_results),
                'high_value_count': self._count_high_value(legacy_results)
            },
            'optimized': {
                'count': len(optimized_results),
                'avg_alpha': self._calculate_avg_alpha(optimized_results),
                'high_value_count': self._count_high_value(optimized_results)
            }
        }
        
        self.comparison_metrics['latest'] = comparison
        
        # Log comparison
        self.logger.info(f"Scanner Comparison - Legacy: {comparison['legacy']}, "
                        f"Optimized: {comparison['optimized']}")
    
    def _calculate_avg_alpha(self, results: List) -> float:
        """Calculate average alpha from results."""
        if not results:
            return 0.0
        
        total_alpha = 0
        for result in results:
            if isinstance(result, dict):
                total_alpha += result.get('alpha_potential', 0)
            else:
                total_alpha += getattr(result, 'alpha_magnitude', 0)
        
        return total_alpha / len(results)
    
    def _count_high_value(self, results: List) -> int:
        """Count high-value alerts (>15% alpha)."""
        count = 0
        for result in results:
            if isinstance(result, dict):
                alpha = result.get('alpha_potential', 0)
            else:
                alpha = getattr(result, 'alpha_magnitude', 0)
            
            if alpha > 0.15:
                count += 1
        
        return count
    
    def _convert_legacy_format(self, opportunities: List) -> List[Dict[str, Any]]:
        """Convert legacy format to standard format."""
        return [self._opportunity_to_dict(opp) for opp in opportunities]
    
    def _convert_optimized_format(self, alerts: List[AlphaAlert]) -> List[Dict[str, Any]]:
        """Convert optimized format to standard format."""
        return [self._alert_to_dict(alert) for alert in alerts]
    
    def _opportunity_to_dict(self, opportunity) -> Dict[str, Any]:
        """Convert legacy opportunity to dict."""
        return {
            'symbol': getattr(opportunity, 'symbol', ''),
            'pattern_type': getattr(opportunity, 'divergence_type', ''),
            'alpha_potential': getattr(opportunity, 'alpha_potential', 0),
            'confidence': getattr(opportunity, 'confidence', 0),
            'trading_insight': getattr(opportunity, 'trading_insight', ''),
            'timestamp': getattr(opportunity, 'timestamp', datetime.now(timezone.utc)),
            'scanner_type': 'legacy'
        }
    
    def _alert_to_dict(self, alert: AlphaAlert) -> Dict[str, Any]:
        """Convert optimized alert to dict."""
        return {
            'symbol': alert.symbol,
            'pattern_type': alert.pattern_type,
            'alpha_potential': alert.alpha_magnitude,
            'confidence': alert.confidence,
            'value_score': alert.value_score,
            'tier': alert.tier.value,
            'trading_insight': alert.trading_insight,
            'risk_level': alert.risk_level,
            'expected_duration': alert.expected_duration,
            'entry_conditions': alert.entry_conditions,
            'exit_conditions': alert.exit_conditions,
            'timestamp': alert.timestamp,
            'volume_confirmed': alert.volume_confirmed,
            'scanner_type': 'optimized'
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        if not self.performance_history:
            return {}
        
        recent_metrics = self.performance_history[-10:]  # Last 10 scans
        
        legacy_metrics = [m for m in recent_metrics if m.scanner_type == 'legacy']
        optimized_metrics = [m for m in recent_metrics if m.scanner_type == 'optimized']
        
        summary = {
            'mode': self.mode.value,
            'rollout_percentage': self.rollout_percentage,
            'total_scans': len(self.performance_history),
            'comparison_metrics': self.comparison_metrics.get('latest', {}),
            'legacy_performance': self._summarize_metrics(legacy_metrics),
            'optimized_performance': self._summarize_metrics(optimized_metrics)
        }
        
        return summary
    
    def _summarize_metrics(self, metrics: List[ScannerPerformanceMetrics]) -> Dict[str, Any]:
        """Summarize performance metrics."""
        if not metrics:
            return {}
        
        return {
            'avg_alerts_per_scan': sum(m.total_alerts for m in metrics) / len(metrics),
            'avg_high_value_alerts': sum(m.high_value_alerts for m in metrics) / len(metrics),
            'avg_alpha': sum(m.average_alpha for m in metrics) / len(metrics),
            'avg_confidence': sum(m.average_confidence for m in metrics) / len(metrics),
            'avg_processing_time_ms': sum(m.processing_time_ms for m in metrics) / len(metrics),
            'total_errors': sum(m.error_count for m in metrics)
        }
    
    def force_rollback(self):
        """Force rollback to legacy scanner."""
        self.logger.warning("Forcing rollback to legacy scanner")
        self.mode = ScannerMode.LEGACY_ONLY
        self.rollout_percentage = 0
        
        # Update config to disable optimized scanner
        self.optimized_config['enabled'] = False
    
    def enable_optimized_only(self):
        """Switch to optimized scanner only (after successful rollout)."""
        self.logger.info("Switching to optimized scanner only")
        self.mode = ScannerMode.OPTIMIZED_ONLY
        self.rollout_percentage = 100
        
        # Update config
        self.legacy_config['enabled'] = False
        self.optimized_config['enabled'] = True 