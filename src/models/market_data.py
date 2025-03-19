"""Market data models for standardized data structures."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from decimal import Decimal

@dataclass
class Trade:
    """Standardized trade data structure"""
    id: str
    order_id: Optional[str]
    symbol: str
    side: str
    price: float
    amount: float
    timestamp: datetime
    fee: Optional[float] = None
    fee_currency: Optional[str] = None
    taker_or_maker: Optional[str] = None
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate trade data"""
        if not self.id:
            raise ValueError("Trade ID is required")
        if not self.symbol:
            raise ValueError("Symbol is required")
        if self.side not in ['buy', 'sell']:
            raise ValueError("Side must be 'buy' or 'sell'")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if self.fee is not None and self.fee < 0:
            raise ValueError("Fee cannot be negative")

@dataclass
class OrderBook:
    """Standardized orderbook data structure"""
    symbol: str
    timestamp: datetime
    bids: List[List[float]]  # [[price, amount], ...]
    asks: List[List[float]]  # [[price, amount], ...]
    nonce: Optional[int] = None
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate orderbook data"""
        if not self.symbol:
            raise ValueError("Symbol is required")
        if not self.bids:
            raise ValueError("Bids are required")
        if not self.asks:
            raise ValueError("Asks are required")
        for bid in self.bids:
            if len(bid) != 2 or bid[0] <= 0 or bid[1] <= 0:
                raise ValueError("Invalid bid format")
        for ask in self.asks:
            if len(ask) != 2 or ask[0] <= 0 or ask[1] <= 0:
                raise ValueError("Invalid ask format")

@dataclass
class Ticker:
    """Standardized ticker data structure"""
    symbol: str
    timestamp: datetime
    high: float
    low: float
    bid: Optional[float] = None
    bid_volume: Optional[float] = None
    ask: Optional[float] = None
    ask_volume: Optional[float] = None
    vwap: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    last: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    percentage: Optional[float] = None
    average: Optional[float] = None
    base_volume: Optional[float] = None
    quote_volume: Optional[float] = None
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate ticker data"""
        if not self.symbol:
            raise ValueError("Symbol is required")
        if self.high < self.low:
            raise ValueError("High price cannot be lower than low price")
        if self.bid is not None and self.bid <= 0:
            raise ValueError("Bid price must be positive")
        if self.ask is not None and self.ask <= 0:
            raise ValueError("Ask price must be positive")

@dataclass
class OHLCV:
    """Standardized OHLCV data structure"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate OHLCV data"""
        if self.high < self.low:
            raise ValueError("High price cannot be lower than low price")
        if self.high < self.open or self.high < self.close:
            raise ValueError("High price must be highest")
        if self.low > self.open or self.low > self.close:
            raise ValueError("Low price must be lowest")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")

@dataclass
class Balance:
    """Standardized balance data structure"""
    currency: str
    free: float
    used: float
    total: float
    usd_value: Optional[float] = None
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate balance data"""
        if not self.currency:
            raise ValueError("Currency is required")
        if self.free < 0:
            raise ValueError("Free balance cannot be negative")
        if self.used < 0:
            raise ValueError("Used balance cannot be negative")
        if abs(self.total - (self.free + self.used)) > Decimal('1e-8'):
            raise ValueError("Total must equal free + used")

@dataclass
class Position:
    """Standardized position data structure"""
    symbol: str
    side: str
    contracts: float
    contract_size: float
    entry_price: float
    mark_price: float
    notional: float
    leverage: float
    collateral: float
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float
    realized_pnl: float
    margin_mode: str
    liquidation_price: float
    timestamp: datetime
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate position data"""
        if not self.symbol:
            raise ValueError("Symbol is required")
        if self.side not in ['long', 'short', 'none']:
            raise ValueError("Side must be 'long', 'short', or 'none'")
        if self.contracts < 0:
            raise ValueError("Contracts cannot be negative")
        if self.contract_size <= 0:
            raise ValueError("Contract size must be positive")
        if self.leverage <= 0:
            raise ValueError("Leverage must be positive")
        if self.margin_mode not in ['isolated', 'cross']:
            raise ValueError("Margin mode must be 'isolated' or 'cross'")

@dataclass
class Order:
    """Standardized order data structure"""
    id: str
    symbol: str
    type: str
    side: str
    price: float
    amount: float
    filled: float
    remaining: float
    status: str
    timestamp: datetime
    info: Optional[Dict] = None

    def validate(self) -> None:
        """Validate order data"""
        if not self.id:
            raise ValueError("Order ID is required")
        if not self.symbol:
            raise ValueError("Symbol is required")
        if self.side not in ['buy', 'sell']:
            raise ValueError("Side must be 'buy' or 'sell'")
        if self.type not in ['limit', 'market', 'stop', 'stop_limit']:
            raise ValueError("Invalid order type")
        if self.price <= 0 and self.type != 'market':
            raise ValueError("Price must be positive for non-market orders")
        if self.amount <= 0:
            raise ValueError("Amount must be positive")
        if self.filled < 0:
            raise ValueError("Filled amount cannot be negative")
        if self.remaining < 0:
            raise ValueError("Remaining amount cannot be negative")
        if abs(self.amount - (self.filled + self.remaining)) > Decimal('1e-8'):
            raise ValueError("Amount must equal filled + remaining")

def from_exchange_data(data: Dict[str, Any], data_type: str) -> Union[
    Trade, OrderBook, Ticker, OHLCV, Balance, Position, Order
]:
    """Convert exchange data to standardized model"""
    try:
        if data_type == 'trade':
            model = Trade(
                id=data['id'],
                order_id=data.get('order'),
                symbol=data['symbol'],
                side=data['side'],
                price=float(data['price']),
                amount=float(data['amount']),
                timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                fee=float(data['fee']) if 'fee' in data else None,
                fee_currency=data.get('feeCurrency'),
                taker_or_maker=data.get('takerOrMaker'),
                info=data.get('info')
            )
        elif data_type == 'orderbook':
            model = OrderBook(
                symbol=data['symbol'],
                timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                bids=[[float(p), float(a)] for p, a in data['bids']],
                asks=[[float(p), float(a)] for p, a in data['asks']],
                nonce=data.get('nonce'),
                info=data.get('info')
            )
        elif data_type == 'ticker':
            model = Ticker(
                symbol=data['symbol'],
                timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                high=float(data['high']),
                low=float(data['low']),
                bid=float(data['bid']) if 'bid' in data else None,
                bid_volume=float(data['bidVolume']) if 'bidVolume' in data else None,
                ask=float(data['ask']) if 'ask' in data else None,
                ask_volume=float(data['askVolume']) if 'askVolume' in data else None,
                vwap=float(data['vwap']) if 'vwap' in data else None,
                open=float(data['open']) if 'open' in data else None,
                close=float(data['close']) if 'close' in data else None,
                last=float(data['last']) if 'last' in data else None,
                previous_close=float(data['previousClose']) if 'previousClose' in data else None,
                change=float(data['change']) if 'change' in data else None,
                percentage=float(data['percentage']) if 'percentage' in data else None,
                average=float(data['average']) if 'average' in data else None,
                base_volume=float(data['baseVolume']) if 'baseVolume' in data else None,
                quote_volume=float(data['quoteVolume']) if 'quoteVolume' in data else None,
                info=data.get('info')
            )
        elif data_type == 'ohlcv':
            model = OHLCV(
                timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                open=float(data['open']),
                high=float(data['high']),
                low=float(data['low']),
                close=float(data['close']),
                volume=float(data['volume']),
                info=data.get('info')
            )
        elif data_type == 'balance':
            model = Balance(
                currency=data['currency'],
                free=float(data['free']),
                used=float(data['used']),
                total=float(data['total']),
                usd_value=float(data['usd']) if 'usd' in data else None,
                info=data.get('info')
            )
        elif data_type == 'position':
            model = Position(
                symbol=data['symbol'],
                side=data['side'],
                contracts=float(data['contracts']),
                contract_size=float(data['contractSize']),
                entry_price=float(data['entryPrice']),
                mark_price=float(data['markPrice']),
                notional=float(data['notional']),
                leverage=float(data['leverage']),
                collateral=float(data['collateral']),
                initial_margin=float(data['initialMargin']),
                maintenance_margin=float(data['maintenanceMargin']),
                unrealized_pnl=float(data['unrealizedPnl']),
                realized_pnl=float(data['realizedPnl']),
                margin_mode=data['marginMode'],
                liquidation_price=float(data['liquidationPrice']),
                timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                info=data.get('info')
            )
        elif data_type == 'order':
            model = Order(
                id=data['id'],
                symbol=data['symbol'],
                type=data['type'],
                side=data['side'],
                price=float(data['price']),
                amount=float(data['amount']),
                filled=float(data['filled']),
                remaining=float(data['remaining']),
                status=data['status'],
                timestamp=datetime.fromtimestamp(data['timestamp'] / 1000),
                info=data.get('info')
            )
        else:
            raise ValueError(f"Unknown data type: {data_type}")
            
        # Validate the model
        model.validate()
        return model
        
    except KeyError as e:
        raise ValueError(f"Missing required field: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Invalid data: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error converting data: {str(e)}") 