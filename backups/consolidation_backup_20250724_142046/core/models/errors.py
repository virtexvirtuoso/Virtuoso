"""Error related models."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

class ErrorSeverity(Enum):
    """Severity levels for errors."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ErrorDetails:
    """Detailed error information."""
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    component: str
    error_type: str
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    correlation_id: Optional[str] = None 