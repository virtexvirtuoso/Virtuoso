import asyncio
import logging
import json
import ccxt.async_support as ccxt
import re
from src.monitoring.market_reporter import MarketReporter

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('test_weekly_futures')

class MockExchange:
    """Mock exchange class for testing purposes"""
    
    async def fetch_markets(self):
        """Mock implementation to return test futures data"""
        return [
            # Weekly futures contracts
            {
                'id': 'SOLUSDT-04APR25',
                'symbol': 'SOLUSDT-04APR25',
                'type': 'future',
                'swap': False,
                'info': {
                    'deliveryTime': '1743753600000',
                    'contractType': 'LinearFutures'
                }
            },
            {
                'id': 'BTCUSDT-25APR25',
                'symbol': 'BTCUSDT-25APR25',
                'type': 'future',
                'swap': False,
                'info': {
                    'deliveryTime': '1745568000000',
                    'contractType': 'LinearFutures'
                }
            },
            # Quarterly futures contracts
            {
                'id': 'BTC-27JUN25',
                'symbol': 'BTC-27JUN25',
                'type': 'future',
                'swap': False,
                'info': {
                    'deliveryTime': '1751011200000',
                    'contractType': 'LinearFutures'
                }
            },
            {
                'id': 'BTC-26SEP25',
                'symbol': 'BTC-26SEP25',
                'type': 'future',
                'swap': False,
                'info': {
                    'deliveryTime': '1758873600000',
                    'contractType': 'LinearFutures'
                }
            },
            # Perpetual contract
            {
                'id': 'BTCUSDT',
                'symbol': 'BTC/USDT:USDT',
                'type': 'swap',
                'swap': True,
                'info': {
                    'deliveryTime': '0',
                    'contractType': 'LinearPerpetual'
                }
            },
            {
                'id': 'SOLUSDT',
                'symbol': 'SOL/USDT:USDT',
                'type': 'swap',
                'swap': True,
                'info': {
                    'deliveryTime': '0',
                    'contractType': 'LinearPerpetual'
                }
            }
        ]
    
    async def fetch_ticker(self, symbol):
        """Mock implementation to return test ticker data"""
        # Return a basic ticker response
        return {
            'symbol': symbol,
            'last': 1000.0 if 'BTC' in symbol else 100.0,
            'info': {
                'markPrice': 1000.0 if 'BTC' in symbol else 100.0,
                'indexPrice': 995.0 if 'BTC' in symbol else 99.5,
            }
        }

async def test_futures_premium_calculation():
    """Test the futures premium calculation with focus on weekly futures detection"""
    try:
        # Initialize reporter with mock exchange
        mock_exchange = MockExchange()
        reporter = MarketReporter(exchange=mock_exchange)
        
        # Test _calculate_futures_premium method directly
        logger.info("Testing futures premium calculation with weekly futures support")
        symbols = ['BTC/USDT:USDT', 'SOL/USDT:USDT']
        
        # Call the method
        result = await reporter._calculate_futures_premium(symbols)
        
        # Print the formatted result
        logger.info("Futures Premium Calculation Results:")
        print(json.dumps(result, indent=2))
        
        # Check results for weekly futures detection
        weekly_futures_detected = False
        quarterly_futures_detected = False
        
        for symbol, data in result['premiums'].items():
            logger.info(f"Results for {symbol}:")
            logger.info(f"  Weekly futures found: {data.get('weekly_futures_count', 0)}")
            logger.info(f"  Quarterly futures found: {data.get('quarterly_futures_count', 0)}")
            
            if data.get('weekly_futures_count', 0) > 0:
                weekly_futures_detected = True
            
            if data.get('quarterly_futures_count', 0) > 0:
                quarterly_futures_detected = True
            
            # Check if futures contracts are included
            if 'futures_contracts' in data:
                logger.info(f"  First few futures contracts detected:")
                for contract in data['futures_contracts']:
                    logger.info(f"    - {contract['symbol']} (Delivery: {contract.get('delivery_date', 'unknown')})")
        
        # Summary
        logger.info("\nTest Summary:")
        logger.info(f"Weekly futures detected: {weekly_futures_detected}")
        logger.info(f"Quarterly futures detected: {quarterly_futures_detected}")
        
        # Check regex pattern effectiveness
        logger.info("\nTesting regex pattern for futures contracts:")
        pattern = re.compile(r'([A-Z]+).*?(\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2})')
        test_symbols = [
            'BTCUSDT-04APR25', 'SOLUSDT-25APR25', 'BTC-27JUN25', 'BTC-26SEP25', 
            'ETHUSDT-11APR25', 'XRPUSDT-22MAR25'
        ]
        
        for symbol in test_symbols:
            match = pattern.search(symbol)
            logger.info(f"Symbol {symbol}: {'✓ Matched' if match else '✗ Not matched'}")
            if match:
                logger.info(f"  Base asset: {match.group(1)}, Date: {match.group(2)}")
                
    except Exception as e:
        logger.error(f"Error testing futures premium calculation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_futures_premium_calculation()) 