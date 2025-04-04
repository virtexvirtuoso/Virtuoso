import asyncio
import logging
import sys
import json
from pprint import pprint
from datetime import datetime

from src.core.exchanges.bybit import BybitExchange

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("bybit_test")

# Sample config
CONFIG = {
    'exchanges': {
        'bybit': {
            'name': 'bybit',
            'enabled': True,
            'testnet': False,
            'rest_endpoint': 'https://api.bybit.com',
            'websocket': {
                'enabled': False,
                'mainnet_endpoint': 'wss://stream.bybit.com/v5/public',
                'testnet_endpoint': 'wss://stream-testnet.bybit.com/v5/public'
            },
            'api_credentials': {
                'api_key': 'dummy_key',
                'api_secret': 'dummy_secret'
            }
        }
    }
}

# Test symbols
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

async def test_fetch_order_book(exchange):
    """Test order book fetching and parsing"""
    logger.info("\n===== Testing Order Book Fetching =====")
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching order book for {symbol}...")
            order_book = await exchange.fetch_order_book(symbol)
            
            # Validate response
            if not order_book:
                logger.error(f"Empty order book response for {symbol}")
                continue
                
            # Check structure
            expected_keys = ['bids', 'asks']
            missing_keys = [k for k in expected_keys if k not in order_book]
            if missing_keys:
                logger.error(f"Missing keys in order book: {missing_keys}")
                continue
                
            # Check data
            bids_count = len(order_book['bids'])
            asks_count = len(order_book['asks'])
            
            logger.info(f"Order book for {symbol}:")
            logger.info(f"  Bids count: {bids_count}")
            logger.info(f"  Asks count: {asks_count}")
            
            if bids_count > 0:
                logger.info(f"  Sample bid: {order_book['bids'][0]}")
            if asks_count > 0:
                logger.info(f"  Sample ask: {order_book['asks'][0]}")
                
            logger.info(f"✅ Order book test passed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}", exc_info=True)

async def test_fetch_ohlcv(exchange):
    """Test OHLCV data fetching and parsing"""
    logger.info("\n===== Testing OHLCV Data Fetching =====")
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching OHLCV data for {symbol}...")
            ohlcv_data = await exchange._fetch_all_timeframes(symbol)
            
            # Validate response
            if not ohlcv_data:
                logger.error(f"Empty OHLCV response for {symbol}")
                continue
                
            # Check timeframes
            expected_timeframes = ['base', 'ltf', 'mtf', 'htf']
            missing_timeframes = [tf for tf in expected_timeframes if tf not in ohlcv_data]
            if missing_timeframes:
                logger.error(f"Missing timeframes in OHLCV data: {missing_timeframes}")
                continue
                
            # Check each timeframe
            for timeframe, df in ohlcv_data.items():
                logger.info(f"  {timeframe} timeframe:")
                logger.info(f"    Shape: {df.shape}")
                logger.info(f"    Empty: {df.empty}")
                
                if not df.empty:
                    expected_columns = ['open', 'high', 'low', 'close', 'volume']
                    missing_columns = [col for col in expected_columns if col not in df.columns]
                    if missing_columns:
                        logger.error(f"Missing columns in {timeframe} DataFrame: {missing_columns}")
                        continue
                    
                    logger.info(f"    Data types: {df.dtypes.to_dict()}")
                    logger.info(f"    Contains nulls: {df.isnull().values.any()}")
                    if not df.empty:
                        logger.info(f"    First timestamp: {df.index[0]}")
                        logger.info(f"    Last timestamp: {df.index[-1]}")
                
            logger.info(f"✅ OHLCV test passed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}", exc_info=True)

async def test_fetch_ticker(exchange):
    """Test ticker data fetching and parsing"""
    logger.info("\n===== Testing Ticker Fetching =====")
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching ticker for {symbol}...")
            
            # Assuming there's a fetch_ticker method
            response = await exchange._make_request('GET', '/v5/market/tickers', {
                'category': 'linear',
                'symbol': symbol
            })
            
            # Log raw response for debugging
            logger.debug(f"Raw API response for ticker: {json.dumps(response, indent=2)[:500]}...")
            
            # Check response status
            if not response or response.get('retCode') != 0:
                logger.error(f"Invalid ticker response: {response.get('retMsg', 'Unknown error')}")
                continue
                
            # Check ticker list
            ticker_list = response.get('result', {}).get('list', [])
            if not ticker_list:
                logger.error("Empty ticker list")
                continue
                
            ticker = ticker_list[0]
            logger.info(f"Ticker for {symbol}:")
            
            # Display important fields
            important_fields = [
                'symbol', 'lastPrice', 'highPrice24h', 'lowPrice24h', 'volume24h', 
                'turnover24h', 'fundingRate', 'nextFundingTime'
            ]
            
            for field in important_fields:
                if field in ticker:
                    logger.info(f"  {field}: {ticker[field]}")
                else:
                    logger.warning(f"  {field} not found in ticker")
                    
            logger.info(f"✅ Ticker test passed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}", exc_info=True)

async def test_fetch_trades(exchange):
    """Test recent trades fetching and parsing"""
    logger.info("\n===== Testing Recent Trades Fetching =====")
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching recent trades for {symbol}...")
            
            # Access the API directly
            response = await exchange._make_request('GET', '/v5/market/recent-trade', {
                'category': 'linear',
                'symbol': symbol,
                'limit': 10
            })
            
            # Check response status
            if not response or response.get('retCode') != 0:
                logger.error(f"Invalid trades response: {response.get('retMsg', 'Unknown error')}")
                continue
                
            # Check trades list
            trades = response.get('result', {}).get('list', [])
            if not trades:
                logger.error("Empty trades list")
                continue
                
            logger.info(f"Recent trades for {symbol}:")
            logger.info(f"  Count: {len(trades)}")
            
            if trades:
                # Show sample trade
                sample_trade = trades[0]
                logger.info("  Sample trade:")
                for key, value in sample_trade.items():
                    logger.info(f"    {key}: {value}")
                    
            logger.info(f"✅ Recent trades test passed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {e}", exc_info=True)

async def test_fetch_long_short_ratio(exchange):
    """Test long-short ratio fetching and parsing"""
    logger.info("\n===== Testing Long-Short Ratio Fetching =====")
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching long-short ratio for {symbol}...")
            
            # Access the API directly
            response = await exchange._make_request('GET', '/v5/market/account-ratio', {
                'category': 'linear',
                'symbol': symbol,
                'period': '1d'
            })
            
            # Check response status
            if not response or response.get('retCode') != 0:
                logger.error(f"Invalid long-short ratio response: {response.get('retMsg', 'Unknown error')}")
                continue
                
            # Check data list
            data_list = response.get('result', {}).get('list', [])
            if not data_list:
                logger.error("Empty long-short ratio list")
                continue
                
            logger.info(f"Long-short ratio for {symbol}:")
            logger.info(f"  Count: {len(data_list)}")
            
            if data_list:
                # Show sample data
                sample_data = data_list[0]
                logger.info("  Sample data:")
                for key, value in sample_data.items():
                    logger.info(f"    {key}: {value}")
                    
                # Calculate long-short ratio
                buy_ratio = float(sample_data.get('buyRatio', 0))
                sell_ratio = float(sample_data.get('sellRatio', 0))
                logger.info(f"  Buy/Sell ratio: {buy_ratio/sell_ratio:.2f}")
                    
            logger.info(f"✅ Long-short ratio test passed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching long-short ratio for {symbol}: {e}", exc_info=True)

async def test_fetch_risk_limits(exchange):
    """Test risk limits fetching and parsing"""
    logger.info("\n===== Testing Risk Limits Fetching =====")
    
    for symbol in SYMBOLS:
        try:
            logger.info(f"Fetching risk limits for {symbol}...")
            
            # Access the API directly
            response = await exchange._make_request('GET', '/v5/market/risk-limit', {
                'category': 'linear',
                'symbol': symbol
            })
            
            # Check response status
            if not response or response.get('retCode') != 0:
                logger.error(f"Invalid risk limits response: {response.get('retMsg', 'Unknown error')}")
                continue
                
            # Check risk limits list
            limits = response.get('result', {}).get('list', [])
            if not limits:
                logger.error("Empty risk limits list")
                continue
                
            logger.info(f"Risk limits for {symbol}:")
            logger.info(f"  Count: {len(limits)}")
            
            if limits:
                # Show sample limit
                sample_limit = limits[0]
                logger.info("  Sample risk limit:")
                for key, value in sample_limit.items():
                    logger.info(f"    {key}: {value}")
                    
            logger.info(f"✅ Risk limits test passed for {symbol}")
            
        except Exception as e:
            logger.error(f"Error fetching risk limits for {symbol}: {e}", exc_info=True)

async def test_fetch_market_info(exchange):
    """Test fetching market information."""
    try:
        logger.info("Fetching market information...")
        
        # Access the API directly
        response = await exchange._make_request('GET', '/v5/market/instruments-info', {
            'category': 'linear'
        })
        
        # Check response status
        if not response or response.get('retCode') != 0:
            logger.error(f"Invalid market info response: {response.get('retMsg', 'Unknown error')}")
            return
            
        # Check instrument list
        instruments = response.get('result', {}).get('list', [])
        if not instruments:
            logger.error("Empty instruments list")
            return
            
        # Verify structure
        assert isinstance(instruments, list), "Instruments should be a list"
        assert len(instruments) > 0, "Should have at least one instrument"
        
        # Log sample data
        logger.info("Market instruments:")
        logger.info(f"  Count: {len(instruments)}")
        
        # Find BTC and ETH instruments
        btc_instrument = next((i for i in instruments if i.get('baseCoin') == 'BTC'), None)
        eth_instrument = next((i for i in instruments if i.get('baseCoin') == 'ETH'), None)
        
        if btc_instrument:
            logger.info("  Sample BTC instrument:")
            for key, value in btc_instrument.items():
                logger.info(f"    {key}: {value}")
        
        if eth_instrument:
            logger.info("  Sample ETH instrument:")
            for key, value in eth_instrument.items():
                logger.info(f"    {key}: {value}")
        
        logger.info("✅ Market info test passed")
        
    except Exception as e:
        logger.error(f"Error fetching market info: {e}", exc_info=True)
        raise e

async def test_market_data(exchange):
    """Test fetching comprehensive market data including volatility."""
    try:
        symbols = ['BTCUSDT', 'ETHUSDT']
        for symbol in symbols:
            logger.info(f"\nTesting market data for {symbol}...")
            
            # Fetch market data
            market_data = await exchange.fetch_market_data(symbol)
            
            # Verify structure
            assert isinstance(market_data, dict), "Market data should be a dictionary"
            assert 'sentiment' in market_data, "Market data should contain sentiment"
            assert 'volatility' in market_data['sentiment'], "Sentiment should contain volatility"
            
            # Verify volatility data structure
            volatility_data = market_data['sentiment']['volatility']
            assert isinstance(volatility_data, dict), "Volatility data should be a dictionary"
            
            # Check required fields
            required_fields = ['value', 'window', 'timeframe', 'timestamp', 'trend', 'period_minutes']
            for field in required_fields:
                assert field in volatility_data, f"Volatility data missing {field}"
            
            # Validate field types and values
            assert isinstance(volatility_data['value'], (int, float)), "Volatility value should be numeric"
            assert volatility_data['value'] >= 0, "Volatility value should be non-negative"
            assert isinstance(volatility_data['window'], int), "Window should be integer"
            assert isinstance(volatility_data['timeframe'], str), "Timeframe should be string"
            assert isinstance(volatility_data['timestamp'], int), "Timestamp should be integer"
            assert isinstance(volatility_data['trend'], str), "Trend should be string"
            assert isinstance(volatility_data['period_minutes'], int), "Period minutes should be integer"
            
            # Log volatility data
            logger.info(f"Volatility data for {symbol}:")
            for key, value in volatility_data.items():
                logger.info(f"  {key}: {value}")
            
            logger.info(f"✅ Market data test passed for {symbol}")
            
    except Exception as e:
        logger.error(f"Error testing market data: {e}", exc_info=True)
        raise e

async def main():
    try:
        # Create exchange instance
        exchange = BybitExchange(CONFIG)
        
        # Initialize exchange
        logger.info("Initializing Bybit exchange...")
        success = await exchange.initialize()
        if not success:
            logger.error("Failed to initialize Bybit exchange")
            return
        
        # Run all tests
        await test_fetch_order_book(exchange)
        await test_fetch_ohlcv(exchange)
        await test_fetch_ticker(exchange)
        await test_fetch_trades(exchange)
        await test_fetch_long_short_ratio(exchange)
        await test_fetch_risk_limits(exchange)
        await test_fetch_market_info(exchange)
        await test_market_data(exchange)
        
        # Summary
        logger.info("\n===== Test Summary =====")
        logger.info("All market data tests completed.")
        
        # Clean up
        await exchange.close()
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 