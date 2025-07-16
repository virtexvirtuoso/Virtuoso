from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

class AlphaStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate" 
    STRONG = "strong"
    EXCEPTIONAL = "exceptional"

class AlphaOpportunity(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange identifier")
    score: float = Field(..., ge=0, le=100, description="Alpha score (0-100)")
    strength: AlphaStrength = Field(..., description="Signal strength category")
    timeframe: str = Field(..., description="Primary analysis timeframe")
    
    # Confluence components
    technical_score: float = Field(..., ge=0, le=100)
    momentum_score: float = Field(..., ge=0, le=100)
    volume_score: float = Field(..., ge=0, le=100)
    sentiment_score: float = Field(..., ge=0, le=100)
    
    # Risk metrics
    volatility: float = Field(..., description="Historical volatility")
    liquidity_score: float = Field(..., ge=0, le=100)
    
    # Price levels
    current_price: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    
    # Analysis details
    indicators: Dict[str, float] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)

class AlphaScanRequest(BaseModel):
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to scan")
    exchanges: Optional[List[str]] = Field(None, description="Target exchanges")
    timeframes: List[str] = Field(default=["15m", "1h", "4h"], description="Analysis timeframes")
    min_score: float = Field(default=60.0, ge=0, le=100)
    max_results: int = Field(default=20, ge=1, le=100)
    
class AlphaScanResponse(BaseModel):
    opportunities: List[AlphaOpportunity]
    scan_timestamp: datetime
    total_symbols_scanned: int
    scan_duration_ms: int
    metadata: Dict[str, Union[str, int, float]] 