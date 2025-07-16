"""
Centralized Interpretation Schema

This module defines the standardized data structures for market interpretations
to ensure consistency across alerts, PDF reports, JSON exports, and all other
output systems.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
import uuid


class ComponentType(Enum):
    """Enumeration of valid component types."""
    TECHNICAL_INDICATOR = "technical_indicator"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    FUNDING_ANALYSIS = "funding_analysis"
    VOLUME_ANALYSIS = "volume_analysis"
    PRICE_ANALYSIS = "price_analysis"
    WHALE_ANALYSIS = "whale_analysis"
    GENERAL_ANALYSIS = "general_analysis"
    UNKNOWN = "unknown"


class InterpretationSeverity(Enum):
    """Enumeration of interpretation severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class ConfidenceLevel(Enum):
    """Enumeration of confidence levels."""
    VERY_LOW = 0.0
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    VERY_HIGH = 1.0


class SignalDirection(Enum):
    """Enumeration of signal directions."""
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


@dataclass
class SubComponent:
    """Represents a sub-component within a main component."""
    name: str
    display_name: str
    score: float
    weight: float = 1.0
    description: Optional[str] = None
    
    def __post_init__(self):
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {self.score}")
        if not self.name:
            raise ValueError("SubComponent name cannot be empty")


@dataclass
class ComponentInterpretation:
    """Standardized interpretation for a single component."""
    component_type: ComponentType
    component_name: str
    interpretation_text: str
    severity: InterpretationSeverity
    confidence_score: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not 0 <= self.confidence_score <= 1:
            raise ValueError(f"Confidence score must be between 0 and 1, got {self.confidence_score}")
        if not self.interpretation_text.strip():
            raise ValueError("Interpretation text cannot be empty")
    
    def __eq__(self, other):
        """Check equality for testing purposes."""
        if not isinstance(other, ComponentInterpretation):
            return False
        return (
            self.component_type == other.component_type and
            self.component_name == other.component_name and
            self.interpretation_text == other.interpretation_text and
            self.severity == other.severity and
            abs(self.confidence_score - other.confidence_score) < 0.001
        )


@dataclass
class ActionableInsight:
    """Represents an actionable trading insight."""
    insight_text: str
    priority: int = 1  # 1=highest, 5=lowest
    signal_direction: Optional[SignalDirection] = None
    confidence: float = 0.75
    conditions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not 1 <= self.priority <= 5:
            raise ValueError(f"Priority must be between 1 and 5, got {self.priority}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class MarketInterpretationSet:
    """Complete set of interpretations for a market analysis."""
    timestamp: datetime
    source_component: str
    interpretations: List[ComponentInterpretation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.source_component.strip():
            raise ValueError("Source component cannot be empty")
    
    def get_critical_interpretations(self) -> List[ComponentInterpretation]:
        """Get interpretations with critical severity."""
        return [interp for interp in self.interpretations if interp.severity == InterpretationSeverity.CRITICAL]
    
    def get_warning_interpretations(self) -> List[ComponentInterpretation]:
        """Get interpretations with warning severity."""
        return [interp for interp in self.interpretations if interp.severity == InterpretationSeverity.WARNING]
    
    def get_high_confidence_interpretations(self, threshold: float = 0.8) -> List[ComponentInterpretation]:
        """Get interpretations with high confidence scores."""
        return [interp for interp in self.interpretations if interp.confidence_score >= threshold]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'source_component': self.source_component,
            'interpretations': [
                {
                    'component_type': interp.component_type.value,
                    'component_name': interp.component_name,
                    'interpretation_text': interp.interpretation_text,
                    'severity': interp.severity.value,
                    'confidence_score': interp.confidence_score,
                    'timestamp': interp.timestamp.isoformat(),
                    'metadata': interp.metadata
                }
                for interp in self.interpretations
            ],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketInterpretationSet':
        """Create instance from dictionary."""
        interpretations = []
        for interp_data in data.get('interpretations', []):
            interpretations.append(
                ComponentInterpretation(
                    component_type=ComponentType(interp_data['component_type']),
                    component_name=interp_data['component_name'],
                    interpretation_text=interp_data['interpretation_text'],
                    severity=InterpretationSeverity(interp_data['severity']),
                    confidence_score=interp_data['confidence_score'],
                    timestamp=datetime.fromisoformat(interp_data['timestamp']),
                    metadata=interp_data.get('metadata', {})
                )
            )
        
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            source_component=data['source_component'],
            interpretations=interpretations,
            metadata=data.get('metadata', {})
        )


@dataclass
class InterpretationProcessingResult:
    """Result of interpretation processing operations."""
    success: bool
    interpretation_set: Optional[MarketInterpretationSet] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning) 