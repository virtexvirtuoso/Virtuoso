from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertType(str, Enum):
    """Alert types"""
    SIGNAL = "signal"
    ALPHA = "alpha"
    LIQUIDATION = "liquidation"
    WHALE_ACTIVITY = "whale_activity"
    LARGE_ORDER = "large_order"
    MANIPULATION = "manipulation"
    TRADE_EXECUTION = "trade_execution"
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    PERFORMANCE = "performance"
    MARKET_REPORT = "market_report"

class AlertFilter(BaseModel):
    """Filter criteria for alerts"""
    level: Optional[AlertLevel] = None
    alert_type: Optional[AlertType] = None
    symbol: Optional[str] = None
    source: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    resolved: Optional[bool] = None
    acknowledged: Optional[bool] = None

class RecentAlert(BaseModel):
    """Recent alert data for dashboard"""
    id: str
    level: AlertLevel
    message: str
    timestamp: float
    alert_type: Optional[str] = None
    symbol: Optional[str] = None
    priority: str = "medium"

class AlertResponse(BaseModel):
    """Standard alert response"""
    id: str
    level: AlertLevel
    message: str
    details: Dict[str, Any] = {}
    timestamp: float
    source: Optional[str] = None
    alert_type: Optional[str] = None
    symbol: Optional[str] = None
    resolved: bool = False
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AlertSummary(BaseModel):
    """Alert summary statistics"""
    total_alerts: int
    by_level: Dict[str, int]
    by_type: Dict[str, int]
    by_symbol: Dict[str, int]
    period_hours: int
    most_recent: Optional[Dict[str, Any]] = None
    most_critical: Optional[Dict[str, Any]] = None

class AlertStats(BaseModel):
    """Alert system statistics"""
    total: int = 0
    sent: int = 0
    throttled: int = 0
    duplicates: int = 0
    errors: int = 0
    handler_errors: int = 0
    handler_success: int = 0
    processing_errors: int = 0
    info: int = 0
    warning: int = 0
    error: int = 0
    critical: int = 0
    success_rate: float = 0.0
    error_rate: float = 0.0 