from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


class ComponentDetail(BaseModel):
    """Detail of a signal component"""
    score: float
    impact: Optional[float] = None
    interpretation: Optional[str] = None


class SignalComponents(BaseModel):
    """Components that contribute to the signal"""
    price_action: Optional[ComponentDetail] = None
    momentum: Optional[ComponentDetail] = None
    technical: Optional[ComponentDetail] = None
    volume: Optional[ComponentDetail] = None
    orderbook: Optional[ComponentDetail] = None
    orderflow: Optional[ComponentDetail] = None
    sentiment: Optional[ComponentDetail] = None
    price_structure: Optional[ComponentDetail] = None
    
    # Allow additional fields for flexibility with different component types
    class Config:
        extra = "allow"


class Target(BaseModel):
    """Price target information"""
    price: float
    size: Optional[float] = None
    name: Optional[str] = None


class Signal(BaseModel):
    """Trading signal model"""
    symbol: str
    signal: str  # BULLISH, BEARISH, NEUTRAL
    score: float
    reliability: float
    price: Optional[float] = None
    timestamp: Optional[Union[int, str, datetime]] = None
    components: Optional[Union[SignalComponents, Dict[str, Any]]] = None
    interpretations: Optional[Dict[str, str]] = None
    insights: Optional[List[str]] = None
    actionable_insights: Optional[List[str]] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    targets: Optional[Union[Dict[str, Dict[str, float]], List[Target]]] = None
    filename: Optional[str] = None
    file_path: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields not defined in the model


class SignalList(BaseModel):
    """List of signals with pagination"""
    signals: List[Signal]
    total: int
    page: int
    size: int
    pages: int


class SymbolSignals(BaseModel):
    """Signals for a specific symbol"""
    symbol: str
    count: int
    signals: List[Signal]


class LatestSignals(BaseModel):
    """Latest signals across all symbols"""
    count: int
    signals: List[Signal] 