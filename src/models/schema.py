"""
Data validation schemas using Pydantic models.

These models enforce data structure validation across the application
to catch errors early and ensure consistency.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator, field_validator
from enum import Enum
from datetime import datetime

class SignalType(str, Enum):
    """Signal type enumeration for strict validation."""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"
    
class SignalDirection(str, Enum):
    """Signal direction enumeration for UI representation."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class ComponentScore(BaseModel):
    """Individual component score model."""
    score: float = Field(..., ge=0, le=100)
    components: Optional[Dict[str, float]] = None
    interpretation: Optional[Union[str, Dict[str, str]]] = None

class SignalData(BaseModel):
    """Validated signal data structure."""
    symbol: str
    score: float = Field(..., ge=0, le=100)
    price: Optional[float] = None
    signal: Optional[SignalType] = None
    components: Dict[str, float] = {}
    results: Dict[str, Any] = {}
    reliability: Optional[float] = Field(None, ge=0, le=100)  # Keep as 0-100 scale
    timestamp: Optional[Union[int, float, datetime]] = None
    # Enhanced data fields
    influential_components: Optional[List[Dict[str, Any]]] = None
    market_interpretations: Optional[List[str]] = None
    actionable_insights: Optional[List[str]] = None
    
    @field_validator('score', mode='before')
    @classmethod
    def validate_score(cls, v):
        """Validate and normalize score to be between 0 and 100."""
        if v is None:
            return 50.0  # Default value
        
        try:
            # Convert to float
            value = float(v)
            # Ensure value is between 0 and 100
            return max(0, min(100, value))
        except (TypeError, ValueError):
            # If conversion fails, use default
            return 50.0
            
    @field_validator('reliability', mode='before')
    @classmethod
    def validate_reliability(cls, v):
        """Validate and normalize reliability to be between 0 and 100."""
        if v is None:
            return 100.0  # Default to 100% reliability
        
        try:
            value = float(v)
            if value <= 1:  # If given in 0-1 scale
                value = value * 100
            return max(0, min(100, value))
        except (TypeError, ValueError):
            return 100.0
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls, v):
        """Validate and normalize timestamp formats."""
        if v is None:
            return datetime.now().timestamp()
        
        # Convert datetime object to timestamp
        if isinstance(v, datetime):
            return v.timestamp()
            
        # Handle int/float timestamps in milliseconds
        if isinstance(v, (int, float)) and v > 1000000000000:  # 13+ digits (milliseconds)
            return v / 1000
            
        return v

class AlertPayload(BaseModel):
    """Alert payload for transmission to notification systems."""
    level: str = Field(..., pattern=r'^(INFO|WARNING|ERROR|CRITICAL)$')
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    
class ConfluenceAlert(BaseModel):
    """Specialized structure for confluence alerts."""
    symbol: str
    confluence_score: float = Field(..., ge=0, le=100)
    components: Dict[str, float]
    results: Dict[str, Any]
    reliability: float = Field(..., ge=0, le=100)
    signal_type: SignalDirection
    price: Optional[float] = None
    long_threshold: Optional[float] = None
    short_threshold: Optional[float] = None
    emoji: Optional[str] = None
    color: Optional[int] = None
    # New fields for enhanced formatting data
    influential_components: Optional[List[Dict[str, Any]]] = None
    market_interpretations: Optional[List[str]] = None
    actionable_insights: Optional[List[str]] = None
    
    @field_validator('signal_type', mode='before')
    @classmethod
    def validate_signal_type(cls, v, values):
        """Derive signal type from confluence score if not provided."""
        if v is not None:
            return v

        # Auto-determine signal type based on score and thresholds
        score = values.get('confluence_score', 50)
        # Support both new and old field names for backward compatibility
        long_threshold = values.get('long_threshold', values.get('buy_threshold'))
        short_threshold = values.get('short_threshold', values.get('sell_threshold'))

        if long_threshold is not None and score >= long_threshold:
            return SignalDirection.BULLISH
        elif short_threshold is not None and score <= short_threshold:
            return SignalDirection.BEARISH
        else:
            return SignalDirection.NEUTRAL 