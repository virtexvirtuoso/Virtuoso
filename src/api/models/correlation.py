"""Correlation API models."""

from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime

class SignalMatrixData(BaseModel):
    """Individual signal data point in the matrix."""
    score: float
    direction: str  # bullish, bearish, neutral
    strength: str   # strong, medium, weak

class AssetSignalMatrix(BaseModel):
    """Signal matrix for a single asset."""
    symbol: str
    momentum: Optional[SignalMatrixData] = None
    technical: Optional[SignalMatrixData] = None
    volume: Optional[SignalMatrixData] = None
    orderflow: Optional[SignalMatrixData] = None
    orderbook: Optional[SignalMatrixData] = None
    sentiment: Optional[SignalMatrixData] = None
    price_action: Optional[SignalMatrixData] = None
    beta_exp: Optional[SignalMatrixData] = None
    confluence: Optional[SignalMatrixData] = None
    whale_act: Optional[SignalMatrixData] = None
    liquidation: Optional[SignalMatrixData] = None
    composite_score: float

class CorrelationStats(BaseModel):
    """Correlation statistics."""
    mean_correlation: float
    max_correlation: float
    min_correlation: float
    std_correlation: float

class CorrelationAnalysis(BaseModel):
    """Complete correlation analysis response."""
    signal_correlations: Dict[str, Dict[str, float]]
    asset_correlations: Dict[str, Dict[str, float]]
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]

class SignalConfluenceMatrix(BaseModel):
    """Signal confluence matrix response."""
    matrix_data: Dict[str, Dict[str, Any]]
    correlations: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]

class HeatmapData(BaseModel):
    """Heatmap visualization data."""
    correlation_matrix: List[List[float]]
    labels: List[str]
    correlation_type: str
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]

class LiveMatrixResponse(BaseModel):
    """Live signal matrix response."""
    live_matrix: Dict[str, Dict[str, Any]]
    performance_metrics: Dict[str, str]
    real_time_status: Dict[str, Any]
    signal_types: List[str]
    metadata: Dict[str, Any] 