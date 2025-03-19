from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict

class MarketData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    symbol: str
    exchange: str
    price: float
    volume: float
    timestamp: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None

class OrderBookEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    price: float
    amount: float

class OrderBook(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    symbol: str
    exchange: str
    timestamp: int
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]

class Trade(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    symbol: str
    exchange: str
    timestamp: int
    price: float
    amount: float
    side: str
    trade_id: str

class MarketComparison(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    symbol: str
    timestamp: int
    exchanges: Dict[str, MarketData]
    price_spread: float
    volume_total: float

class TechnicalIndicator(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    value: Any
    timestamp: int
    parameters: Dict[str, Any]

class TechnicalAnalysis(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    symbol: str
    exchange: str
    timestamp: int
    timeframe: str
    indicators: Dict[str, TechnicalIndicator]
    signals: Dict[str, Any] 