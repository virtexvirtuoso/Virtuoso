"""
Error Tracking System for Virtuoso Trading Bot

This module provides comprehensive error tracking and categorization
to help identify and resolve issues.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better organization"""
    TEMPLATE_RENDERING = "template_rendering"
    STRING_FORMATTING = "string_formatting"
    ALERT_MANAGER = "alert_manager"
    SYMBOL_CACHE = "symbol_cache"
    WEBHOOK_DELIVERY = "webhook_delivery"
    DATA_PROCESSING = "data_processing"
    API_COMMUNICATION = "api_communication"
    CONFIGURATION = "configuration"

@dataclass
class ErrorEvent:
    """Represents a single error event"""
    timestamp: int
    error_type: str
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    component: str
    details: Dict[str, Any]
    count: int = 1
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None

class ErrorTracker:
    """Comprehensive error tracking and analysis system"""
    
    def __init__(self, max_events: int = 10000, retention_hours: int = 168):  # 7 days
        self.logger = logging.getLogger(__name__)
        self.max_events = max_events
        self.retention_ms = retention_hours * 60 * 60 * 1000
        
        # Error storage
        self.error_events: deque = deque(maxlen=max_events)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Known error patterns from June 15, 2025
        self.known_patterns = {
            "template_variable_missing": {
                "pattern": "generated_at.*is undefined",
                "category": ErrorCategory.TEMPLATE_RENDERING,
                "severity": ErrorSeverity.HIGH,
                "solution": "Add missing template variables to context"
            },
            "string_format_error": {
                "pattern": "Unknown format code.*for object of type.*str",
                "category": ErrorCategory.STRING_FORMATTING,
                "severity": ErrorSeverity.HIGH,
                "solution": "Convert string to numeric type before formatting"
            },
            "discord_handler_duplicate": {
                "pattern": "Discord handler.*registered multiple times",
                "category": ErrorCategory.ALERT_MANAGER,
                "severity": ErrorSeverity.MEDIUM,
                "solution": "Add duplicate check in register_handler method"
            },
            "symbol_cache_missing": {
                "pattern": "Symbol.*not in cache",
                "category": ErrorCategory.SYMBOL_CACHE,
                "severity": ErrorSeverity.MEDIUM,
                "solution": "Implement lazy loading for symbol cache"
            },
            "webhook_delivery_failed": {
                "pattern": "Failed to send.*webhook",
                "category": ErrorCategory.WEBHOOK_DELIVERY,
                "severity": ErrorSeverity.MEDIUM,
                "solution": "Add retry logic with exponential backoff"
            }
        }
        
        self.logger.info("ErrorTracker initialized with comprehensive monitoring")
    
    def track_error(self, 
                   error_type: str,
                   message: str,
                   component: str,
                   severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                   category: ErrorCategory = ErrorCategory.DATA_PROCESSING,
                   details: Optional[Dict[str, Any]] = None) -> None:
        """Track a new error event"""
        
        timestamp = int(time.time() * 1000)
        details = details or {}
        
        # Check for known patterns
        detected_pattern = self._detect_pattern(message)
        if detected_pattern:
            category = detected_pattern["category"]
            severity = detected_pattern["severity"]
            details["known_pattern"] = detected_pattern["pattern"]
            details["suggested_solution"] = detected_pattern["solution"]
        
        # Create error event
        error_event = ErrorEvent(
            timestamp=timestamp,
            error_type=error_type,
            severity=severity,
            category=category,
            message=message,
            component=component,
            details=details,
            first_seen=timestamp,
            last_seen=timestamp
        )
        
        # Check for duplicate recent errors
        duplicate_key = f"{error_type}:{component}:{message[:100]}"
        recent_duplicate = self._find_recent_duplicate(duplicate_key, timestamp)
        
        if recent_duplicate:
            # Update existing error
            recent_duplicate.count += 1
            recent_duplicate.last_seen = timestamp
            self.logger.debug(f"Updated duplicate error count: {duplicate_key} (count: {recent_duplicate.count})")
        else:
            # Add new error
            self.error_events.append(error_event)
            self.error_counts[error_type] += 1
            
            # Track error rate
            self.error_rates[error_type].append(timestamp)
            
            # Log based on severity
            if severity == ErrorSeverity.CRITICAL:
                self.logger.critical(f"CRITICAL ERROR: {component} - {message}")
            elif severity == ErrorSeverity.HIGH:
                self.logger.error(f"HIGH SEVERITY: {component} - {message}")
            elif severity == ErrorSeverity.MEDIUM:
                self.logger.warning(f"MEDIUM SEVERITY: {component} - {message}")
            else:
                self.logger.info(f"LOW SEVERITY: {component} - {message}")
        
        # Clean old events
        self._cleanup_old_events()
    
    def _detect_pattern(self, message: str) -> Optional[Dict[str, Any]]:
        """Detect known error patterns in message"""
        import re
        
        for pattern_name, pattern_info in self.known_patterns.items():
            if re.search(pattern_info["pattern"], message, re.IGNORECASE):
                return pattern_info
        return None
    
    def _find_recent_duplicate(self, duplicate_key: str, timestamp: int) -> Optional[ErrorEvent]:
        """Find recent duplicate error within 5 minutes"""
        cutoff = timestamp - (5 * 60 * 1000)  # 5 minutes
        
        for event in reversed(self.error_events):
            if event.timestamp < cutoff:
                break
            
            event_key = f"{event.error_type}:{event.component}:{event.message[:100]}"
            if event_key == duplicate_key:
                return event
        
        return None
    
    def _cleanup_old_events(self) -> None:
        """Remove events older than retention period"""
        cutoff = int(time.time() * 1000) - self.retention_ms
        
        # Remove old events
        while self.error_events and self.error_events[0].timestamp < cutoff:
            old_event = self.error_events.popleft()
            self.error_counts[old_event.error_type] = max(0, self.error_counts[old_event.error_type] - 1)
        
        # Clean error rates
        for error_type, rates in self.error_rates.items():
            while rates and rates[0] < cutoff:
                rates.popleft()
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive error summary for specified time period"""
        cutoff = int(time.time() * 1000) - (hours * 60 * 60 * 1000)
        
        # Filter recent events
        recent_events = [e for e in self.error_events if e.timestamp >= cutoff]
        
        # Categorize errors
        by_category = defaultdict(list)
        by_severity = defaultdict(list)
        by_component = defaultdict(list)
        
        for event in recent_events:
            by_category[event.category.value].append(event)
            by_severity[event.severity.value].append(event)
            by_component[event.component].append(event)
        
        # Calculate error rates
        total_errors = len(recent_events)
        error_rate = total_errors / hours if hours > 0 else 0
        
        # Find top error types
        error_type_counts = defaultdict(int)
        for event in recent_events:
            error_type_counts[event.error_type] += event.count
        
        top_errors = sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Identify critical issues
        critical_issues = [e for e in recent_events if e.severity == ErrorSeverity.CRITICAL]
        high_severity_issues = [e for e in recent_events if e.severity == ErrorSeverity.HIGH]
        
        return {
            "summary": {
                "time_period_hours": hours,
                "total_errors": total_errors,
                "error_rate_per_hour": round(error_rate, 2),
                "unique_error_types": len(error_type_counts),
                "critical_issues": len(critical_issues),
                "high_severity_issues": len(high_severity_issues)
            },
            "by_category": {cat: len(events) for cat, events in by_category.items()},
            "by_severity": {sev: len(events) for sev, events in by_severity.items()},
            "by_component": {comp: len(events) for comp, events in by_component.items()},
            "top_errors": top_errors,
            "critical_issues": [self._serialize_event(e) for e in critical_issues[:5]],
            "high_severity_issues": [self._serialize_event(e) for e in high_severity_issues[:5]],
            "recommendations": self._generate_recommendations(recent_events)
        }
    
    def _serialize_event(self, event: ErrorEvent) -> Dict[str, Any]:
        """Serialize error event for JSON output"""
        return {
            "timestamp": event.timestamp,
            "datetime": datetime.fromtimestamp(event.timestamp / 1000, tz=timezone.utc).isoformat(),
            "error_type": event.error_type,
            "severity": event.severity.value,
            "category": event.category.value,
            "message": event.message,
            "component": event.component,
            "count": event.count,
            "details": event.details
        }
    
    def _generate_recommendations(self, events: List[ErrorEvent]) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []
        
        # Count by category
        category_counts = defaultdict(int)
        for event in events:
            category_counts[event.category] += event.count
        
        # Generate specific recommendations
        if category_counts[ErrorCategory.TEMPLATE_RENDERING] > 5:
            recommendations.append("High template rendering errors detected. Review template variable passing and add missing context variables.")
        
        if category_counts[ErrorCategory.STRING_FORMATTING] > 3:
            recommendations.append("String formatting errors detected. Add type checking before string formatting operations.")
        
        if category_counts[ErrorCategory.ALERT_MANAGER] > 10:
            recommendations.append("Alert manager issues detected. Review handler registration and add duplicate checks.")
        
        if category_counts[ErrorCategory.WEBHOOK_DELIVERY] > 5:
            recommendations.append("Webhook delivery failures detected. Implement retry logic with exponential backoff.")
        
        # General recommendations
        total_errors = sum(category_counts.values())
        if total_errors > 50:
            recommendations.append("High error volume detected. Consider implementing circuit breakers and graceful degradation.")
        
        return recommendations
    
    def export_error_report(self, filepath: str, hours: int = 24) -> bool:
        """Export detailed error report to file"""
        try:
            summary = self.get_error_summary(hours)
            
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.logger.info(f"Error report exported to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export error report: {e}")
            return False

# Global error tracker instance
_error_tracker = None

def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker

def track_error(error_type: str, message: str, component: str, 
               severity: ErrorSeverity = ErrorSeverity.MEDIUM,
               category: ErrorCategory = ErrorCategory.DATA_PROCESSING,
               details: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function to track errors"""
    tracker = get_error_tracker()
    tracker.track_error(error_type, message, component, severity, category, details) 