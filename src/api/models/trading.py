from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"
    PENDING = "pending"

class OrderRequest(BaseModel):
    symbol: str
    type: OrderType
    side: OrderSide
    amount: Optional[float] = None
    price: Optional[float] = None
    stop_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    trailing_stop: Optional[float] = None
    post_only: Optional[bool] = False
    reduce_only: Optional[bool] = False
    time_in_force: Optional[str] = "GTC"
    calculate_position_size: Optional[bool] = False
    risk_percentage: Optional[float] = Field(None, ge=0, le=100)
    params: Optional[Dict] = None

class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    exchange: str
    type: OrderType
    side: OrderSide
    amount: float
    price: float
    status: OrderStatus
    filled: Optional[float] = None
    remaining: Optional[float] = None
    average: Optional[float] = None
    cost: Optional[float] = None
    fee: Optional[Dict] = None
    timestamp: datetime
    trades: Optional[List[Dict]] = None

class Position(BaseModel):
    symbol: str
    exchange: str
    side: OrderSide
    amount: float
    entry_price: float
    current_price: float
    liquidation_price: Optional[float] = None
    margin: Optional[float] = None
    leverage: Optional[float] = None
    pnl: float
    pnl_percentage: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime

class PositionUpdate(BaseModel):
    symbol: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None

class TradeHistory(BaseModel):
    trade_id: str
    symbol: str
    exchange: str
    order_id: str
    side: OrderSide
    amount: float
    price: float
    cost: float
    fee: Dict
    timestamp: datetime

class PortfolioSummary(BaseModel):
    total_value: float
    asset_allocation: Dict[str, float]
    risk_metrics: Dict[str, float]
    performance: Dict[str, float]
    timestamp: datetime

class RiskMetrics(BaseModel):
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    var_95: float
    var_99: float
    timestamp: datetime 