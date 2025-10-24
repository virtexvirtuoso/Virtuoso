"""Complete signal data schema definition."""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class SignalDirection(str, Enum):
    """Signal direction enumeration."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class SignalStrength(str, Enum):
    """Signal strength enumeration."""
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"

class SignalType(str, Enum):
    """Signal type enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class SignalComponent(BaseModel):
    """Individual signal component structure."""
    score: float = Field(..., ge=0, le=100, description="Signal strength score 0-100")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level 0-1")
    direction: SignalDirection = Field(..., description="Signal direction")
    strength: SignalStrength = Field(..., description="Signal strength")
    raw_value: Optional[float] = Field(None, description="Raw calculated value")
    calculation_method: Optional[str] = Field(None, description="Method used for calculation")
    timestamp: Optional[int] = Field(None, description="Component calculation timestamp")
    
    @validator('score')
    def validate_score(cls, v):
        """Ensure score is within valid range."""
        return max(0.0, min(100.0, v))
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is within valid range."""
        return max(0.0, min(1.0, v))

class TechnicalResults(BaseModel):
    """Technical analysis results."""
    rsi: Optional[float] = None
    macd: Optional[str] = None
    bollinger_position: Optional[float] = None
    moving_averages: Optional[Dict[str, float]] = None
    support_resistance: Optional[Dict[str, float]] = None

class VolumeResults(BaseModel):
    """Volume analysis results."""
    volume_spike: Optional[bool] = None
    volume_ratio: Optional[float] = None
    volume_profile: Optional[Dict[str, Any]] = None
    vwap_position: Optional[float] = None

class SentimentResults(BaseModel):
    """Sentiment analysis results."""
    social_score: Optional[float] = None
    news_score: Optional[float] = None
    fear_greed_index: Optional[float] = None
    trader_sentiment: Optional[float] = None

class OrderflowResults(BaseModel):
    """Order flow analysis results."""
    buy_sell_ratio: Optional[float] = None
    large_order_flow: Optional[float] = None
    market_impact: Optional[float] = None
    flow_direction: Optional[str] = None

class OrderbookResults(BaseModel):
    """Order book analysis results."""
    spread: Optional[float] = None
    depth_ratio: Optional[float] = None
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None
    imbalance: Optional[float] = None

class WhaleResults(BaseModel):
    """Whale activity results."""
    large_transactions: Optional[int] = None
    net_flow: Optional[float] = None
    whale_direction: Optional[str] = None
    transaction_size_avg: Optional[float] = None

class LiquidationResults(BaseModel):
    """Liquidation analysis results."""
    long_liquidations: Optional[float] = None
    short_liquidations: Optional[float] = None
    liquidation_ratio: Optional[float] = None
    liquidation_pressure: Optional[str] = None

class CompleteSignalData(BaseModel):
    """Complete signal data structure with all 11 components."""
    
    # Metadata
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    signal_type: SignalType = Field(..., description="Overall signal type")
    confluence_score: float = Field(..., ge=0, le=100, description="Overall confluence score")
    price: float = Field(..., gt=0, description="Current price")
    timestamp: int = Field(..., description="Signal generation timestamp")
    transaction_id: str = Field(..., description="Unique transaction identifier")
    signal_id: str = Field(..., description="Unique signal identifier")
    
    # All 11 signal components
    components: Dict[str, SignalComponent] = Field(
        ..., 
        description="All 11 signal components with scores and metadata"
    )
    
    # Detailed results for each component
    results: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed calculation results for each component"
    )
    
    # Performance metrics
    performance: Optional[Dict[str, float]] = Field(
        None,
        description="Historical performance metrics"
    )
    
    # Market context
    market_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional market context data"
    )
    
    @validator('components')
    def validate_all_components(cls, v):
        """Validate that all 11 required components are present."""
        required_components = {
            'momentum', 'technical', 'volume', 'orderflow', 
            'orderbook', 'sentiment', 'price_action', 'beta_exp', 
            'confluence', 'whale_act', 'liquidation'
        }
        
        missing_components = required_components - set(v.keys())
        if missing_components:
            raise ValueError(f"Missing required components: {missing_components}")
        
        return v
    
    @validator('confluence_score')
    def validate_confluence_score(cls, v):
        """Ensure confluence score is within valid range."""
        return max(0.0, min(100.0, v))
    
    def get_component_scores(self) -> Dict[str, float]:
        """Get scores for all components."""
        return {name: comp.score for name, comp in self.components.items()}
    
    def get_strong_signals(self) -> List[str]:
        """Get list of components with strong signals."""
        return [
            name for name, comp in self.components.items() 
            if comp.strength == SignalStrength.STRONG
        ]
    
    def get_bullish_signals(self) -> List[str]:
        """Get list of components with bullish direction."""
        return [
            name for name, comp in self.components.items() 
            if comp.direction == SignalDirection.BULLISH
        ]
    
    def get_bearish_signals(self) -> List[str]:
        """Get list of components with bearish direction."""
        return [
            name for name, comp in self.components.items() 
            if comp.direction == SignalDirection.BEARISH
        ]
    
    def calculate_weighted_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate weighted confluence score based on component weights."""
        if not weights:
            # Default equal weights
            weights = {comp: 1.0 for comp in self.components.keys()}
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return self.confluence_score
        
        weighted_sum = sum(
            self.components[comp].score * weights.get(comp, 0)
            for comp in self.components.keys()
        )
        
        return weighted_sum / total_weight

class SignalValidationError(Exception):
    """Raised when signal data validation fails."""
    pass

class SignalDataValidator:
    """Validator for signal data integrity and completeness."""
    
    @staticmethod
    def validate_signal_file(file_path: str) -> bool:
        """Validate a signal file against the complete schema."""
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate against schema
            CompleteSignalData(**data)
            return True
            
        except Exception as e:
            raise SignalValidationError(f"Validation failed for {file_path}: {e}")
    
    @staticmethod
    def get_missing_components(data: Dict[str, Any]) -> List[str]:
        """Get list of missing signal components."""
        required_components = {
            'momentum', 'technical', 'volume', 'orderflow', 
            'orderbook', 'sentiment', 'price_action', 'beta_exp', 
            'confluence', 'whale_act', 'liquidation'
        }
        
        existing_components = set(data.get('components', {}).keys())
        return list(required_components - existing_components)
    
    @staticmethod
    def estimate_missing_component(
        component_name: str, 
        existing_data: Dict[str, Any]
    ) -> SignalComponent:
        """Estimate a missing component based on existing data."""
        base_score = existing_data.get('confluence_score', 50.0)
        
        # Component-specific estimation rules
        estimation_multipliers = {
            'momentum': 0.9,
            'technical': 1.0,
            'volume': 0.95,
            'orderflow': 1.1,
            'orderbook': 0.95,
            'sentiment': 0.8,
            'price_action': 1.0,
            'beta_exp': 0.7,  # More neutral
            'confluence': 1.0,
            'whale_act': 0.8,
            'liquidation': 0.85
        }
        
        multiplier = estimation_multipliers.get(component_name, 1.0)
        estimated_score = base_score * multiplier
        estimated_score = max(0, min(100, estimated_score))
        
        return SignalComponent(
            score=estimated_score,
            confidence=0.5,  # Lower confidence for estimated data
            direction=SignalDirection.BULLISH if estimated_score > 60 else 
                     SignalDirection.BEARISH if estimated_score < 40 else 
                     SignalDirection.NEUTRAL,
            strength=SignalStrength.STRONG if abs(estimated_score - 50) > 20 else 
                    SignalStrength.MEDIUM,
            calculation_method="estimated",
            timestamp=int(datetime.now().timestamp() * 1000)
        ) 