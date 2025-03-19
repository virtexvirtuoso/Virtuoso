import pandas as pd
import numpy as np
from src.indicators.orderflow_indicators import OrderflowIndicators
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Create config
config = {
    'component_weights': {'cvd': 0.3, 'trade_flow': 0.2, 'imbalance': 0.2, 'open_interest': 0.2, 'pressure': 0.1},
    'timeframes': {
        'base': {'interval': 1, 'weight': 0.4, 'validation': {'min_candles': 10}},
        'ltf': {'interval': 5, 'weight': 0.3, 'validation': {'min_candles': 10}},
        'mtf': {'interval': 30, 'weight': 0.2, 'validation': {'min_candles': 10}},
        'htf': {'interval': 240, 'weight': 0.1, 'validation': {'min_candles': 10}}
    },
    'min_trades': 5  # Set minimum trades to 5 for testing
}

# Create indicator
indicator = OrderflowIndicators(config, logger)
print('Indicator initialized successfully!')

# Generate 100 mock trades
import random
trades = []
timestamp = 1630000000000
for i in range(1, 101):
    side = 'buy' if random.random() > 0.5 else 'sell'
    price = 19000 + random.randint(-100, 100)
    amount = round(random.uniform(0.1, 1.0), 2)
    trades.append({
        'id': i,
        'price': price,
        'amount': amount,
        'side': side,
        'time': timestamp
    })
    timestamp += 1000  # 1 second increment

# Create mock market data
market_data = {
    'symbol': 'BTCUSDT',
    'orderbook': {
        'bids': [[19000, 1.5], [18900, 2.0], [18800, 3.0]],
        'asks': [[19100, 1.0], [19200, 2.5], [19300, 3.5]]
    },
    'trades': trades,
    'ohlcv': {
        'base': pd.DataFrame({
            'open': [19000, 19050, 19100, 19050, 19000, 19050, 19100, 19050, 19000, 19050],
            'high': [19100, 19150, 19200, 19150, 19100, 19150, 19200, 19150, 19100, 19150],
            'low': [18950, 19000, 19050, 19000, 18950, 19000, 19050, 19000, 18950, 19000],
            'close': [19050, 19100, 19050, 19000, 19050, 19100, 19050, 19000, 19050, 19100],
            'volume': [10, 15, 12, 8, 11, 10, 15, 12, 8, 11]
        }),
        'ltf': pd.DataFrame({
            'open': [19000, 19100, 19050, 19000, 19100, 19050, 19000, 19100, 19050, 19000],
            'high': [19200, 19250, 19150, 19200, 19250, 19150, 19200, 19250, 19150, 19200],
            'low': [18950, 19050, 19000, 18950, 19050, 19000, 18950, 19050, 19000, 18950],
            'close': [19100, 19050, 19100, 19100, 19050, 19100, 19100, 19050, 19100, 19100],
            'volume': [30, 25, 20, 30, 25, 20, 30, 25, 20, 30]
        })
    },
    'open_interest': {
        'current': 1000,
        'previous': 950,
        'history': [
            {'timestamp': 1630000000000, 'value': 950},
            {'timestamp': 1630000060000, 'value': 970},
            {'timestamp': 1630000120000, 'value': 990},
            {'timestamp': 1630000180000, 'value': 1000}
        ]
    }
}

# Calculate indicators
try:
    result = indicator.calculate(market_data)
    print('\nCalculation result:')
    print(f'Score: {result.get("score")}')
    print(f'Components: {result.get("components")}')
    print(f'Signals: {result.get("signals")}')
    print(f'Metadata: {result.get("metadata")}')
except Exception as e:
    print(f'Error calculating indicators: {str(e)}')
    import traceback
    print(traceback.format_exc()) 