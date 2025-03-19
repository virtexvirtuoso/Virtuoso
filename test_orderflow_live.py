import pandas as pd
import numpy as np
import logging
import ccxt
import time
from datetime import datetime, timedelta
from src.indicators.orderflow_indicators import OrderflowIndicators

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create config
config = {
    'component_weights': {'cvd': 0.3, 'trade_flow_score': 0.3, 'imbalance_score': 0.2, 'open_interest_score': 0.1, 'pressure_score': 0.1},
    'timeframes': {
        'base': {'interval': 1, 'weight': 0.4, 'validation': {'min_candles': 10}},
        'ltf': {'interval': 5, 'weight': 0.3, 'validation': {'min_candles': 10}},
        'mtf': {'interval': 30, 'weight': 0.2, 'validation': {'min_candles': 10}},
        'htf': {'interval': 240, 'weight': 0.1, 'validation': {'min_candles': 10}}
    },
    'min_trades': 5  # Reduced for testing
}

# Print the component weights for debugging
logger.info(f"Component weights in config: {config['component_weights']}")

def fetch_live_data(symbol='BTC/USDT', exchange_id='binance'):
    """Fetch live market data from a crypto exchange."""
    try:
        logger.info(f"Fetching live data for {symbol} from {exchange_id}")
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'  # For futures markets with open interest
            }
        })

        # Check if exchange is available
        if not exchange.has['fetchOHLCV']:
            logger.error(f"{exchange_id} does not support fetching OHLCV data")
            return None
        
        if not exchange.has['fetchOrderBook']:
            logger.error(f"{exchange_id} does not support fetching orderbook data")
            return None
            
        if not exchange.has['fetchTrades']:
            logger.error(f"{exchange_id} does not support fetching trades data")
            return None
            
        # Fetch OHLCV data for different timeframes
        ohlcv_data = {}
        timeframes = {
            'base': '1m',
            'ltf': '5m',
            'mtf': '30m',
            'htf': '4h'
        }
        
        for tf_name, tf_value in timeframes.items():
            if tf_value in exchange.timeframes:
                # Get candles for the timeframe
                since = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)  # 1 day ago
                candles = exchange.fetch_ohlcv(symbol, tf_value, since, limit=100)
                
                # Convert to DataFrame
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                ohlcv_data[tf_name] = df
                logger.info(f"Fetched {len(df)} candles for {tf_name} timeframe ({tf_value})")
            else:
                logger.warning(f"Timeframe {tf_value} not available on {exchange_id}")
        
        # Fetch orderbook data
        orderbook = exchange.fetch_order_book(symbol)
        logger.info(f"Fetched orderbook with {len(orderbook['bids'])} bids and {len(orderbook['asks'])} asks")
        
        # Fetch recent trades
        trades = exchange.fetch_trades(symbol, limit=100)
        logger.info(f"Fetched {len(trades)} recent trades")
        
        # Process trades into standard format
        processed_trades = []
        for trade in trades:
            processed_trades.append({
                'id': trade['id'],
                'price': trade['price'],
                'amount': trade['amount'],
                'side': trade['side'],
                'time': trade['timestamp']
            })
        
        # Fetch open interest data directly using the Binance futures API
        open_interest = None
        try:
            # Convert symbol to format required by futures API (remove the '/')
            futures_symbol = symbol.replace('/', '')
            
            # Try direct futures API method for open interest
            if hasattr(exchange, 'fapiPublicGetOpenInterest'):
                futures_oi = exchange.fapiPublicGetOpenInterest({'symbol': futures_symbol})
                
                # Get current open interest
                current_oi = float(futures_oi['openInterest'])
                
                # Fetch historical open interest data for previous values
                # Note: In a real implementation, you might want to fetch actual historical data
                # For this example, we'll estimate the previous value as 98% of current
                previous_oi = current_oi * 0.98
                
                # Create the properly structured open interest data
                open_interest = {
                    'current': current_oi,
                    'previous': previous_oi,
                    'history': [
                        {'timestamp': int(time.time()) * 1000 - 3600000, 'value': previous_oi},
                        {'timestamp': int(time.time()) * 1000 - 2400000, 'value': current_oi * 0.99},
                        {'timestamp': int(time.time()) * 1000 - 1200000, 'value': current_oi * 0.995},
                        {'timestamp': int(time.time()) * 1000, 'value': current_oi}
                    ]
                }
                
                logger.info(f"Fetched open interest: {current_oi}")
            else:
                # If direct API is not available, try fetchOpenInterest method
                if 'fetchOpenInterest' in dir(exchange) and callable(getattr(exchange, 'fetchOpenInterest')):
                    oi_data = exchange.fetchOpenInterest(symbol)
                    
                    if isinstance(oi_data, dict) and 'openInterestAmount' in oi_data:
                        current_oi = float(oi_data['openInterestAmount'])
                        previous_oi = current_oi * 0.98
                        
                        open_interest = {
                            'current': current_oi,
                            'previous': previous_oi,
                            'history': [
                                {'timestamp': int(time.time()) * 1000 - 3600000, 'value': previous_oi},
                                {'timestamp': int(time.time()) * 1000 - 2400000, 'value': current_oi * 0.99},
                                {'timestamp': int(time.time()) * 1000 - 1200000, 'value': current_oi * 0.995},
                                {'timestamp': int(time.time()) * 1000, 'value': current_oi}
                            ]
                        }
                        
                        logger.info(f"Fetched open interest: {current_oi}")
                    else:
                        raise ValueError("Open interest data missing expected fields")
                else:
                    raise ValueError("Exchange does not support open interest fetching")
                    
        except Exception as e:
            logger.warning(f"Error fetching real open interest: {str(e)}")
            # Fallback: create mock open interest data
            ticker = exchange.fetch_ticker(symbol)
            estimated_oi = ticker['quoteVolume'] * 100 if 'quoteVolume' in ticker else 1000000
            
            open_interest = {
                'current': estimated_oi,
                'previous': estimated_oi * 0.98,
                'history': [
                    {'timestamp': int(time.time()) * 1000 - 3600000, 'value': estimated_oi * 0.98},
                    {'timestamp': int(time.time()) * 1000 - 2400000, 'value': estimated_oi * 0.99},
                    {'timestamp': int(time.time()) * 1000 - 1200000, 'value': estimated_oi * 0.995},
                    {'timestamp': int(time.time()) * 1000, 'value': estimated_oi}
                ]
            }
            logger.info(f"Using estimated open interest: {estimated_oi}")
        
        # Assemble market data
        market_data = {
            'symbol': symbol.replace('/', ''),
            'orderbook': orderbook,
            'trades': processed_trades,
            'ohlcv': ohlcv_data,
            'open_interest': open_interest
        }
        
        logger.info(f"Successfully fetched live market data for {symbol}")
        return market_data
        
    except Exception as e:
        logger.error(f"Error fetching live data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    # Create indicator
    indicator = OrderflowIndicators(config, logger)
    logger.info('Indicator initialized successfully!')
    
    # Fetch live data
    market_data = fetch_live_data(symbol='BTC/USDT', exchange_id='binance')
    
    if not market_data:
        logger.error("Failed to fetch live market data")
        return
    
    # Calculate indicators
    try:
        logger.info("Calculating orderflow indicators on live data...")
        result = indicator.calculate(market_data)
        
        logger.info('\nCalculation result:')
        logger.info(f'Score: {result.get("score")}')
        logger.info(f'Components: {result.get("components")}')
        logger.info(f'Signals: {result.get("signals")}')
        logger.info(f'Metadata: {result.get("metadata")}')
        
        # Print interpretation
        signal_type = result.get('signals', {}).get('interpretation', {}).get('signal', 'neutral')
        logger.info(f"\nSignal: {signal_type.upper()}")
        
        # Check divergences - Fixed to handle None values properly
        divergences = result.get('signals', {}).get('divergences', {})
        found_divergences = False
        
        if divergences:
            logger.info("\nDivergences detected:")
            for div_type, div_data in divergences.items():
                if isinstance(div_data, dict) and div_data.get('type') and div_data.get('type') != 'neutral':
                    strength = div_data.get('strength')
                    if strength is not None:
                        logger.info(f"- {div_type}: {div_data.get('type')} (strength: {strength:.2f})")
                        found_divergences = True
                    else:
                        logger.info(f"- {div_type}: {div_data.get('type')} (strength: N/A)")
                        found_divergences = True
            
            if not found_divergences:
                logger.info("No significant divergences found")
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 