#!/usr/bin/env python3
"""
Enhanced Memory Monitor with improved accuracy through:
- Trend analysis and pattern recognition
- Adaptive thresholds based on system behavior
- Intelligent alerting with context awareness
- Memory leak detection
- Process-specific monitoring
"""

import logging
import time
import psutil
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import threading
from datetime import datetime, timedelta

@dataclass
class MemoryTrend:
    """Track memory usage trends over time."""
    values: deque = field(default_factory=lambda: deque(maxlen=60))  # 1 hour of data
    timestamps: deque = field(default_factory=lambda: deque(maxlen=60))
    trend_direction: str = "stable"  # "increasing", "decreasing", "stable"
    trend_strength: float = 0.0  # 0.0 to 1.0
    volatility: float = 0.0  # Standard deviation of recent values
    
    def add_value(self, value: float, timestamp: Optional[float] = None) -> None:
        """Add a new memory usage value."""
        self.values.append(value)
        self.timestamps.append(timestamp or time.time())
        self._update_trend()
    
    def _update_trend(self) -> None:
        """Update trend analysis."""
        if len(self.values) < 10:
            return
        
        values = list(self.values)
        
        # Calculate trend direction using linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Determine trend direction and strength
        if slope > 0.1:  # Increasing trend
            self.trend_direction = "increasing"
            self.trend_strength = min(abs(slope) / 10.0, 1.0)  # Normalize slope
        elif slope < -0.1:  # Decreasing trend
            self.trend_direction = "decreasing"
            self.trend_strength = min(abs(slope) / 10.0, 1.0)
        else:
            self.trend_direction = "stable"
            self.trend_strength = 0.0
        
        # Calculate volatility (standard deviation of recent values)
        if len(values) >= 5:
            self.volatility = np.std(values[-5:])
    
    def get_recent_average(self, window: int = 10) -> Optional[float]:
        """Get average of recent values."""
        if len(self.values) < window:
            return None
        return np.mean(list(self.values)[-window:])
    
    def is_trending_up(self, threshold: float = 0.3) -> bool:
        """Check if memory usage is trending upward."""
        return self.trend_direction == "increasing" and self.trend_strength > threshold
    
    def is_volatile(self, threshold: float = 5.0) -> bool:
        """Check if memory usage is volatile."""
        return self.volatility > threshold

@dataclass
class ProcessMemoryInfo:
    """Track memory usage for specific processes."""
    pid: int
    name: str
    memory_mb: float
    memory_percent: float
    timestamp: float
    trend: MemoryTrend = field(default_factory=MemoryTrend)
    
    def update(self, memory_mb: float, memory_percent: float) -> None:
        """Update process memory information."""
        self.memory_mb = memory_mb
        self.memory_percent = memory_percent
        self.timestamp = time.time()
        self.trend.add_value(memory_mb)

@dataclass
class MemoryAlertContext:
    """Context information for memory alerts."""
    current_usage: float
    available_memory: float
    total_memory: float
    trend_direction: str
    trend_strength: float
    volatility: float
    top_processes: List[ProcessMemoryInfo]
    swap_usage: float
    system_load: float
    uptime_hours: float
    alert_reason: str
    confidence_score: float  # 0.0 to 1.0

class EnhancedMemoryMonitor:
    """Enhanced memory monitoring with improved accuracy."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize enhanced memory monitor."""
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Memory tracking
        self.memory_trend = MemoryTrend()
        self.process_memory = {}  # pid -> ProcessMemoryInfo
        self.alert_history = deque(maxlen=100)
        
        # Configuration with intelligent defaults
        self.warning_threshold = self.config.get('warning_threshold_percent', 85)
        self.critical_threshold = self.config.get('critical_threshold_percent', 95)
        self.min_warning_size_mb = self.config.get('min_warning_size_mb', 1024)  # 1GB
        self.trend_sensitivity = self.config.get('trend_sensitivity', 0.3)
        self.volatility_threshold = self.config.get('volatility_threshold', 5.0)
        self.process_threshold_mb = self.config.get('process_threshold_mb', 100)  # Alert if process uses >100MB
        self.memory_leak_threshold = self.config.get('memory_leak_threshold', 0.5)  # 50% increase over 1 hour
        
        # Adaptive thresholds
        self.adaptive_warning = self.warning_threshold
        self.adaptive_critical = self.critical_threshold
        
        # Monitoring state
        self.last_check = time.time()
        self.consecutive_high_usage = 0
        self.memory_leak_detected = False
        
        self.logger.info("Enhanced Memory Monitor initialized")
    
    def update_memory_usage(self) -> MemoryAlertContext:
        """Update memory usage and return context for alerting."""
        # Get current memory information
        memory = psutil.virtual_memory()
        current_usage = memory.percent
        available_memory = memory.available / (1024 * 1024)  # MB
        total_memory = memory.total / (1024 * 1024)  # MB
        
        # Update memory trend
        self.memory_trend.add_value(current_usage)
        
        # Get system load
        try:
            system_load = psutil.getloadavg()[0]  # 1-minute load average
        except:
            system_load = 0.0
        
        # Get uptime
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_hours = uptime_seconds / 3600
        
        # Update process memory information
        self._update_process_memory()
        
        # Get top memory-consuming processes
        top_processes = self._get_top_processes()
        
        # Get swap information
        swap = psutil.swap_memory()
        swap_usage = swap.percent
        
        # Determine alert reason and confidence
        alert_reason, confidence_score = self._analyze_memory_situation(
            current_usage, available_memory, total_memory, top_processes
        )
        
        # Create context
        context = MemoryAlertContext(
            current_usage=current_usage,
            available_memory=available_memory,
            total_memory=total_memory,
            trend_direction=self.memory_trend.trend_direction,
            trend_strength=self.memory_trend.trend_strength,
            volatility=self.memory_trend.volatility,
            top_processes=top_processes,
            swap_usage=swap_usage,
            system_load=system_load,
            uptime_hours=uptime_hours,
            alert_reason=alert_reason,
            confidence_score=confidence_score
        )
        
        return context
    
    def _update_process_memory(self) -> None:
        """Update memory information for tracked processes."""
        current_time = time.time()
        
        # Get all processes
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                memory_info = proc.info['memory_info']
                
                if memory_info:
                    memory_mb = memory_info.rss / (1024 * 1024)
                    memory_percent = (memory_mb / (psutil.virtual_memory().total / (1024 * 1024))) * 100
                    
                    # Only track processes using significant memory
                    if memory_mb > 50:  # 50MB threshold
                        if pid not in self.process_memory:
                            self.process_memory[pid] = ProcessMemoryInfo(
                                pid=pid, name=name, memory_mb=memory_mb, 
                                memory_percent=memory_percent, timestamp=current_time
                            )
                        else:
                            self.process_memory[pid].update(memory_mb, memory_percent)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Clean up old process entries
        cutoff_time = current_time - 300  # 5 minutes
        self.process_memory = {
            pid: proc for pid, proc in self.process_memory.items()
            if proc.timestamp > cutoff_time
        }
    
    def _get_top_processes(self, limit: int = 5) -> List[ProcessMemoryInfo]:
        """Get top memory-consuming processes."""
        processes = list(self.process_memory.values())
        processes.sort(key=lambda p: p.memory_mb, reverse=True)
        return processes[:limit]
    
    def _analyze_memory_situation(self, current_usage: float, available_memory: float, 
                                 total_memory: float, top_processes: List[ProcessMemoryInfo]) -> Tuple[str, float]:
        """Analyze memory situation and determine alert reason and confidence."""
        confidence_score = 0.0
        alert_reason = "normal"
        
        # Check for critical memory usage
        if current_usage >= self.adaptive_critical:
            confidence_score = 0.9
            alert_reason = "critical_usage"
        elif current_usage >= self.adaptive_warning:
            confidence_score = 0.7
            alert_reason = "high_usage"
        
        # Check for memory leak patterns
        if self.memory_trend.is_trending_up(self.trend_sensitivity):
            if self.memory_trend.trend_strength > 0.5:
                confidence_score = max(confidence_score, 0.8)
                alert_reason = "memory_leak_detected"
            else:
                confidence_score = max(confidence_score, 0.6)
                alert_reason = "increasing_trend"
        
        # Check for volatile memory usage
        if self.memory_trend.is_volatile(self.volatility_threshold):
            confidence_score = max(confidence_score, 0.5)
            alert_reason = "volatile_usage"
        
        # Check for process-specific issues
        for process in top_processes:
            if process.memory_mb > self.process_threshold_mb * 10:  # 10x threshold
                confidence_score = max(confidence_score, 0.7)
                alert_reason = f"process_high_usage:{process.name}"
                break
        
        # Check for low available memory
        if available_memory < 500:  # Less than 500MB available
            confidence_score = max(confidence_score, 0.8)
            alert_reason = "low_available_memory"
        
        # Check for swap usage
        if hasattr(psutil, 'swap_memory'):
            swap = psutil.swap_memory()
            if swap.percent > 80:
                confidence_score = max(confidence_score, 0.6)
                alert_reason = "high_swap_usage"
        
        return alert_reason, confidence_score
    
    def should_alert(self, context: MemoryAlertContext) -> Tuple[bool, str, str]:
        """Determine if an alert should be triggered."""
        # Don't alert if confidence is too low
        if context.confidence_score < 0.5:
            return False, "normal", "Low confidence score"
        
        # Check for critical conditions
        if context.current_usage >= self.adaptive_critical:
            return True, "critical", f"Critical memory usage: {context.current_usage:.1f}%"
        
        # Check for warning conditions
        if context.current_usage >= self.adaptive_warning:
            return True, "warning", f"High memory usage: {context.current_usage:.1f}%"
        
        # Check for trend-based alerts
        if context.trend_direction == "increasing" and context.trend_strength > 0.5:
            return True, "warning", f"Memory trending up: {context.trend_strength:.2f} strength"
        
        # Check for process-specific alerts
        for process in context.top_processes:
            if process.memory_mb > self.process_threshold_mb * 5:
                return True, "warning", f"Process {process.name} using {process.memory_mb:.0f}MB"
        
        return False, "normal", "No alert conditions met"
    
    def update_adaptive_thresholds(self, context: MemoryAlertContext) -> None:
        """Update adaptive thresholds based on system behavior."""
        # Adjust thresholds based on system load
        if context.system_load > 2.0:  # High system load
            self.adaptive_warning = min(self.warning_threshold + 5, 95)
            self.adaptive_critical = min(self.critical_threshold + 5, 98)
        elif context.system_load < 0.5:  # Low system load
            self.adaptive_warning = max(self.warning_threshold - 5, 75)
            self.adaptive_critical = max(self.critical_threshold - 5, 85)
        else:
            self.adaptive_warning = self.warning_threshold
            self.adaptive_critical = self.critical_threshold
        
        # Adjust based on uptime
        if context.uptime_hours > 24:  # System running for more than 24 hours
            self.adaptive_warning = min(self.adaptive_warning + 2, 95)
            self.adaptive_critical = min(self.adaptive_critical + 2, 98)
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory summary."""
        context = self.update_memory_usage()
        should_alert, alert_level, alert_message = self.should_alert(context)
        
        return {
            'current_usage': context.current_usage,
            'available_memory_mb': context.available_memory,
            'total_memory_mb': context.total_memory,
            'trend_direction': context.trend_direction,
            'trend_strength': context.trend_strength,
            'volatility': context.volatility,
            'swap_usage': context.swap_usage,
            'system_load': context.system_load,
            'uptime_hours': context.uptime_hours,
            'alert_reason': context.alert_reason,
            'confidence_score': context.confidence_score,
            'should_alert': should_alert,
            'alert_level': alert_level,
            'alert_message': alert_message,
            'adaptive_warning': self.adaptive_warning,
            'adaptive_critical': self.adaptive_critical,
            'top_processes': [
                {
                    'name': p.name,
                    'pid': p.pid,
                    'memory_mb': p.memory_mb,
                    'memory_percent': p.memory_percent
                }
                for p in context.top_processes
            ]
        }
    
    def get_detailed_memory_info(self) -> str:
        """Get detailed memory information for alerts."""
        context = self.update_memory_usage()
        
        # Format top processes
        process_info = "\nTop Memory-Consuming Processes:\n"
        for i, proc in enumerate(context.top_processes[:5]):
            process_info += f"{i+1}. {proc.name} (PID: {proc.pid}): {proc.memory_mb:.1f}MB ({proc.memory_percent:.1f}%)\n"
        
        # Add trend information
        trend_info = f"\nMemory Trend Analysis:\n"
        trend_info += f"Direction: {context.trend_direction}\n"
        trend_info += f"Strength: {context.trend_strength:.2f}\n"
        trend_info += f"Volatility: {context.volatility:.2f}\n"
        
        # Add system information
        system_info = f"\nSystem Information:\n"
        system_info += f"Load Average: {context.system_load:.2f}\n"
        system_info += f"Uptime: {context.uptime_hours:.1f} hours\n"
        system_info += f"Swap Usage: {context.swap_usage:.1f}%\n"
        
        # Add alert context
        alert_info = f"\nAlert Context:\n"
        alert_info += f"Reason: {context.alert_reason}\n"
        alert_info += f"Confidence: {context.confidence_score:.2f}\n"
        alert_info += f"Adaptive Warning: {self.adaptive_warning:.1f}%\n"
        alert_info += f"Adaptive Critical: {self.adaptive_critical:.1f}%\n"
        
        return process_info + trend_info + system_info + alert_info 