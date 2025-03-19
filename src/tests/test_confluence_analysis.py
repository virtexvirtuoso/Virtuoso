import asyncio
import logging
import traceback
from datetime import datetime
from src.core.exchanges.hyperliquid import HyperliquidExchange
from src.core.analysis.confluence_analysis import ConfluenceAnalysis

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_confluence_analysis():
    """Test the confluence analysis engine."""
    config = {
        'analysis': {
            'weights': {
                'volume': 0.15,
                'orderbook': 0.15,
                'orderflow': 0.15,
                'position': 0.15,
                'momentum': 0.20,
                'sentiment': 0.20
            }
        }
    }
    
    analysis_engine = ConfluenceAnalysis(config)
    
    # Initialize Hyperliquid exchange
    exchange_config = {
        'api': {
            'key': 'test_key',
            'secret': 'test_secret'
        },
        'testnet': True
    }
    
    # Initialize exchange
    exchange = HyperliquidExchange(exchange_config)
    initialized = await exchange.initialize()
    if not initialized:
        logger.error("Failed to initialize exchange")
        return
        
    # Test symbols
    symbols = ['BTC-PERP', 'ETH-PERP', 'SOL-PERP']
    
    for symbol in symbols:
        logger.info(f"\nAnalyzing {symbol}...")
        
        try:
            # Initialize analysis for symbol
            init_result = await analysis_engine.initialize(symbol)
            logger.info(f"Analysis initialization result: {init_result}")
            
            # Fetch market data
            market_data = await exchange.fetch_market_data(symbol)
            logger.debug(f"Fetched market data: {market_data}")
            
            # Add required fields for analysis
            market_data['symbol'] = symbol
            market_data['timestamp'] = int(datetime.now().timestamp() * 1000)
            market_data['timeframes'] = ['1m', '5m', '15m', '1h', '4h', '1d']
            
            # Structure OHLCV data
            ticker = market_data.get('ticker', {})
            market_data['ohlcv'] = {
                'open': float(ticker.get('open', ticker.get('last', 0))),
                'high': float(ticker.get('high', ticker.get('last', 0))),
                'low': float(ticker.get('low', ticker.get('last', 0))),
                'close': float(ticker.get('last', 0)),
                'volume': float(ticker.get('baseVolume', 0))
            }
            
            logger.debug(f"Structured market data: {market_data}")
            
            # Perform integrated analysis
            analysis_result = await analysis_engine.analyze(market_data)
            
            # Log analysis results
            logger.info(f"\n=== {symbol} Analysis Results ===")
            logger.info(f"Timestamp: {analysis_result.timestamp}")
            logger.info(f"\nComponent Scores:")
            logger.info(f"Momentum Score: {analysis_result.momentum_score:.2f}")
            logger.info(f"Orderflow Score: {analysis_result.orderflow_score:.2f}")
            logger.info(f"Position Score: {analysis_result.position_score:.2f}")
            logger.info(f"Orderbook Score: {analysis_result.orderbook_score:.2f}")
            logger.info(f"Volume Score: {analysis_result.volume_score:.2f}")
            logger.info(f"Sentiment Score: {analysis_result.sentiment_score:.2f}")
            logger.info(f"Confluence Score: {analysis_result.confluence_score:.2f}")
            
            logger.info(f"\nSignal Agreement Analysis:")
            if 'agreement' in analysis_result.signals:
                agreement = analysis_result.signals['agreement']
                logger.info(f"Overall Bias: {agreement['overall_bias']}")
                logger.info(f"Agreement Percentage: {agreement['agreement_percentage']:.2f}%")
                logger.info(f"Signal Distribution: {agreement['signal_distribution']}")
            
            logger.info(f"\nData Quality Metrics:")
            quality = analysis_result.metadata['data_quality']
            logger.info(f"Completeness: {quality['completeness']:.2f}%")
            logger.info(f"Timeliness: {quality['timeliness']:.2f}%")
            logger.info(f"Reliability: {quality['reliability']:.2f}%")
            logger.info(f"Overall Quality: {quality['overall']:.2f}%")
            
            logger.info("\n" + "="*50)
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            continue
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_confluence_analysis()) 