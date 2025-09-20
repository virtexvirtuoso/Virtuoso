"""Error handling models."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

class ErrorSeverity(Enum):
    """Error severity levels."""
    
    DEBUG = "debug"         # Development-time issues
    INFO = "info"           # Informational messages
    WARNING = "warning"     # Non-critical issues
    ERROR = "error"         # Serious issues that need attention
    CRITICAL = "critical"   # System-threatening issues
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class ErrorContext:
    """Context information for errors."""
    
    component: str = "unknown"
    operation: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add detail to context."""
        self.details[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'component': self.component,
            'operation': self.operation,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }

@dataclass
class ErrorEvent:
    """Represents an error event in the system."""
    
    error: Exception
    context: ErrorContext
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    handled: bool = False
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error event to dictionary."""
        return {
            'error_type': self.error.__class__.__name__,
            'error_message': str(self.error),
            'context': self.context.to_dict(),
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'handled': self.handled,
            'resolution': self.resolution
        }

@dataclass
class ErrorRecord:
    """Persistent record of an error event."""
    
    event: ErrorEvent
    record_id: str = field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the error record."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the error record."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error record to dictionary."""
        return {
            'record_id': self.record_id,
            'event': self.event.to_dict(),
            'tags': self.tags,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 