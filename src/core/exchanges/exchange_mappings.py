"""Exchange field mappings and standardization functions."""

import time
from typing import Dict, Any, List
from datetime import datetime

# CCXT standard field mappings
EXCHANGE_TO_CCXT_MAPPINGS = {
    'bybit': {
        'timeframe': {
            '1': '1m',
            '3': '3m',
            '5': '5m',
            '15': '15m',
            '30': '30m',
            '60': '1h',
            '120': '2h',
            '240': '4h',
            '360': '6h',
            '720': '12h',
            'D': '1d',
            'W': '1w',
            'M': '1M'
        },
        'order_status': {
            'NEW': 'open',
            'PARTIALLY_FILLED': 'open',
            'FILLED': 'closed',
            'CANCELED': 'canceled',
            'PENDING_CANCEL': 'canceling',
            'REJECTED': 'rejected',
            'PENDING_NEW': 'open',
            'EXPIRED': 'expired',
            'STOPPED': 'closed',
            'UNTRIGGERED': 'open',
            'TRIGGERED': 'open',
            'DEACTIVATED': 'canceled'
        },
        'order_type': {
            'LIMIT': 'limit',
            'MARKET': 'market',
            'LIMIT_MAKER': 'limit_maker',
            'STOP': 'stop',
            'STOP_MARKET': 'stop_market',
            'STOP_LIMIT': 'stop_limit',
            'TAKE_PROFIT': 'take_profit',
            'TAKE_PROFIT_MARKET': 'take_profit_market',
            'TRAILING_STOP_MARKET': 'trailing_stop_market'
        },
        'position_side': {
            'Buy': 'long',
            'Sell': 'short',
            'None': 'none'
        },
        'position_mode': {
            'MergedSingle': 'one-way',
            'BothSide': 'hedge'
        },
        'margin_mode': {
            'ISOLATED': 'isolated',
            'CROSS': 'cross'
        },
        'trade_fields': {
            'symbol': 'symbol',
            'id': 'id',  # Default spot trade ID
            'orderId': 'order',
            'side': 'side',
            'price': 'price',
            'qty': 'amount',
            'time': 'timestamp',
            'fee': 'fee',
            'feeCurrency': 'feeCurrency',
            'execType': 'takerOrMaker',
            'execId': 'id',  # Contract trades ID
            'tradeId': 'id',  # Some private trade responses
            'T': 'id',  # WebSocket trade ID
            'i': 'id',  # Alternative WebSocket trade ID
            'execPrice': 'execPrice',
            'execQty': 'execQty',
            'execFee': 'execFee',
            'execRealizedPnl': 'realizedPnl'
        },
        'orderbook_fields': {
            'symbol': 'symbol',
            'timestamp': 'timestamp',
            'datetime': 'datetime',
            'bids': 'bids',
            'asks': 'asks',
            'nonce': 'nonce'
        },
        'ticker_fields': {
            'symbol': 'symbol',
            'timestamp': 'timestamp',
            'datetime': 'datetime',
            'high': 'high',
            'low': 'low',
            'bid': 'bid',
            'bidVolume': 'bidVolume',
            'ask': 'ask',
            'askVolume': 'askVolume',
            'vwap': 'vwap',
            'open': 'open',
            'close': 'close',
            'last': 'last',
            'previousClose': 'previousClose',
            'change': 'change',
            'percentage': 'percentage',
            'average': 'average',
            'baseVolume': 'baseVolume',
            'quoteVolume': 'quoteVolume'
        },
        'ohlcv_fields': {
            'timestamp': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'turnover': 'turnover'
        },
        'balance_fields': {
            'coin': 'currency',
            'walletBalance': 'total',
            'availableToWithdraw': 'free',
            'locked': 'used',
            'usdValue': 'usd'
        },
        'position_fields': {
            'symbol': 'symbol',
            'side': 'side',
            'size': 'contracts',
            'entryPrice': 'entryPrice',
            'leverage': 'leverage',
            'markPrice': 'markPrice',
            'liquidationPrice': 'liquidationPrice',
            'margin': 'margin',
            'marginMode': 'marginMode',
            'unrealisedPnl': 'unrealizedPnl',
            'realisedPnl': 'realizedPnl',
            'stopLoss': 'stopLoss',
            'takeProfit': 'takeProfit',
            'trailingStop': 'trailingStop'
        },
        'ws_channels': {
            'trade': 'trade',
            'orderbook': 'orderbook',
            'ticker': 'ticker',
            'kline': 'kline',
            'position': 'position',
            'execution': 'execution',
            'order': 'order',
            'wallet': 'wallet'
        },
        'error_codes': {
            '10001': 'System error',
            '10002': 'System not available',
            '10003': 'Invalid request',
            '10004': 'Invalid parameter',
            '10005': 'Operation failed',
            '10006': 'Too many requests',
            '10007': 'Authentication required',
            '10008': 'Invalid API key',
            '10009': 'Invalid signature',
            '10010': 'IP not allowed',
            '10011': 'Unauthorized',
            '10012': 'Account not found',
            '10013': 'Permission denied',
            '10014': 'Invalid request source',
            '10015': 'Invalid request timing',
            '10016': 'Request frequency exceeded',
            '10017': 'Invalid symbol',
            '10018': 'Invalid order type',
            '10019': 'Invalid side',
            '10020': 'Invalid quantity',
            '10021': 'Invalid price',
            '10022': 'Insufficient balance',
            '10023': 'Position not found',
            '10024': 'Order not found',
            '10025': 'Order already exists',
            '10026': 'Order canceled',
            '10027': 'Order filled',
            '10028': 'Order rejected',
            '10029': 'Order expired',
            '10030': 'Order amendment rejected',
            '10031': 'Position mode not allowed',
            '10032': 'Position side not allowed',
            '10033': 'Position leverage not allowed',
            '10034': 'Position risk limit exceeded',
            '10035': 'Position margin mode not allowed',
            '10036': 'Position close failed',
            '10037': 'Position liquidation in progress',
            '10038': 'Position ADL in progress',
            '10039': 'Invalid stop price',
            '10040': 'Invalid trigger price',
            '10041': 'Invalid trailing stop',
            '10042': 'Invalid take profit',
            '10043': 'Invalid stop loss',
            '10044': 'Invalid time in force',
            '10045': 'Invalid reduce only flag',
            '10046': 'Invalid close on trigger flag',
            '10047': 'Invalid position idx',
            '10048': 'Invalid settlement currency',
            '10049': 'Invalid withdrawal amount',
            '10050': 'Withdrawal suspended',
            '10051': 'Transfer suspended',
            '10052': 'Network not available',
            '10053': 'Address not whitelisted',
            '10054': 'Address not valid',
            '10055': 'Tag not valid'
        }
    }
}

# Reverse mappings for API calls
CCXT_TO_EXCHANGE_MAPPINGS = {
    'bybit': {
        'timeframe': {v: k for k, v in EXCHANGE_TO_CCXT_MAPPINGS['bybit']['timeframe'].items()},
        'order_status': {v: k for k, v in EXCHANGE_TO_CCXT_MAPPINGS['bybit']['order_status'].items()},
        'order_type': {v: k for k, v in EXCHANGE_TO_CCXT_MAPPINGS['bybit']['order_type'].items()},
        'position_side': {v: k for k, v in EXCHANGE_TO_CCXT_MAPPINGS['bybit']['position_side'].items()},
        'position_mode': {v: k for k, v in EXCHANGE_TO_CCXT_MAPPINGS['bybit']['position_mode'].items()},
        'margin_mode': {v: k for k, v in EXCHANGE_TO_CCXT_MAPPINGS['bybit']['margin_mode'].items()}
    }
}

def get_exchange_timeframe(timeframe: str, exchange_id: str) -> str:
    """Convert CCXT timeframe to exchange format."""
    return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)

def get_ccxt_timeframe(timeframe: str, exchange_id: str) -> str:
    """Convert exchange timeframe to CCXT format."""
    return EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)

def standardize_trade_data(trades: List[Dict[str, Any]], exchange_id: str) -> Dict[str, Any]:
    """Standardize trade data to CCXT format."""
    mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['trade_fields']
    standardized = []
    
    for trade in trades:
        std_trade = {}
        for exchange_field, ccxt_field in mappings.items():
            if exchange_field in trade:
                std_trade[ccxt_field] = trade[exchange_field]
                
        # Convert timestamp to milliseconds if needed
        if 'timestamp' in std_trade and isinstance(std_trade['timestamp'], int):
            if std_trade['timestamp'] < 2e10:  # Assuming seconds
                std_trade['timestamp'] *= 1000
                
        standardized.append(std_trade)
        
    return {
        'trades': standardized,
        'timestamp': int(time.time() * 1000),
        'datetime': datetime.now().isoformat()
    }

def standardize_orderbook_data(orderbook: Dict[str, Any], exchange_id: str) -> Dict[str, Any]:
    """Standardize orderbook data to CCXT format."""
    mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['orderbook_fields']
    standardized = {}
    
    for exchange_field, ccxt_field in mappings.items():
        if exchange_field in orderbook:
            standardized[ccxt_field] = orderbook[exchange_field]
            
    # Convert bids and asks to float arrays
    if 'bids' in standardized:
        standardized['bids'] = [[float(price), float(amount)] for price, amount in standardized['bids']]
    if 'asks' in standardized:
        standardized['asks'] = [[float(price), float(amount)] for price, amount in standardized['asks']]
        
    # Add timestamp if not present
    if 'timestamp' not in standardized:
        standardized['timestamp'] = int(time.time() * 1000)
        standardized['datetime'] = datetime.now().isoformat()
        
    return standardized

def standardize_ticker_data(ticker: Dict[str, Any], exchange_id: str) -> Dict[str, Any]:
    """Standardize ticker data to CCXT format."""
    mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['ticker_fields']
    standardized = {}
    
    for exchange_field, ccxt_field in mappings.items():
        if exchange_field in ticker:
            standardized[ccxt_field] = ticker[exchange_field]
            
    # Convert numeric fields to float
    numeric_fields = ['high', 'low', 'bid', 'bidVolume', 'ask', 'askVolume', 'vwap',
                     'open', 'close', 'last', 'previousClose', 'change', 'percentage',
                     'average', 'baseVolume', 'quoteVolume']
                     
    for field in numeric_fields:
        if field in standardized:
            standardized[field] = float(standardized[field])
            
    # Add timestamp if not present
    if 'timestamp' not in standardized:
        standardized['timestamp'] = int(time.time() * 1000)
        standardized['datetime'] = datetime.now().isoformat()
        
    return standardized

def standardize_ohlcv_data(ohlcv: List[Dict[str, Any]], exchange_id: str) -> Dict[str, Any]:
    """Standardize OHLCV data to CCXT format."""
    mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['ohlcv_fields']
    standardized = []
    
    for candle in ohlcv:
        std_candle = {}
        for exchange_field, ccxt_field in mappings.items():
            if exchange_field in candle:
                std_candle[ccxt_field] = float(candle[exchange_field])
                
        # Convert timestamp to milliseconds if needed
        if 'timestamp' in std_candle and isinstance(std_candle['timestamp'], int):
            if std_candle['timestamp'] < 2e10:  # Assuming seconds
                std_candle['timestamp'] *= 1000
                
        standardized.append([
            std_candle['timestamp'],
            std_candle['open'],
            std_candle['high'],
            std_candle['low'],
            std_candle['close'],
            std_candle['volume']
        ])
        
    return {
        'ohlcv': standardized,
        'timestamp': int(time.time() * 1000),
        'datetime': datetime.now().isoformat()
    }

def standardize_balance_data(balance: Dict[str, Any], exchange_id: str) -> Dict[str, Any]:
    """Standardize balance data to CCXT format."""
    mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['balance_fields']
    standardized = {}
    
    for currency_data in balance.get('balances', []):
        currency = currency_data[mappings['coin']]
        standardized[currency] = {
            'free': float(currency_data[mappings['availableToWithdraw']]),
            'used': float(currency_data[mappings['locked']]),
            'total': float(currency_data[mappings['walletBalance']]),
        }
        if mappings['usdValue'] in currency_data:
            standardized[currency]['usd'] = float(currency_data[mappings['usdValue']])
            
    return {
        'info': balance,
        'balances': standardized,
        'timestamp': int(time.time() * 1000),
        'datetime': datetime.now().isoformat()
    }

def standardize_position_data(position: Dict[str, Any], exchange_id: str) -> Dict[str, Any]:
    """Standardize position data to CCXT format."""
    mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['position_fields']
    standardized = {}
    
    for exchange_field, ccxt_field in mappings.items():
        if exchange_field in position:
            standardized[ccxt_field] = position[exchange_field]
            
    # Convert numeric fields to float
    numeric_fields = ['contracts', 'entryPrice', 'leverage', 'markPrice',
                     'liquidationPrice', 'margin', 'unrealizedPnl', 'realizedPnl',
                     'stopLoss', 'takeProfit', 'trailingStop']
                     
    for field in numeric_fields:
        if field in standardized:
            standardized[field] = float(standardized[field])
            
    # Convert side to standard format
    if 'side' in standardized:
        side_mappings = EXCHANGE_TO_CCXT_MAPPINGS[exchange_id]['position_side']
        standardized['side'] = side_mappings.get(standardized['side'], 'none')
        
    return standardized 