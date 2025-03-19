import asyncio
import logging
import yaml
from datetime import datetime
from typing import Dict, Any

from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.exchanges.manager import ExchangeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def load_config() -> Dict[str, Any]:
    """Load configuration from YAML files."""
    try:
        with open('config/analysis_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

async def get_market_data(exchange_manager: ExchangeManager, symbol: str) -> Dict[str, Any]:
    """Fetch market data from exchanges."""
    try:
        # Fetch data from all exchanges
        market_data = await exchange_manager.fetch_all_market_data(symbol)
        
        # Combine and format data
        combined_data = {
            'symbol': symbol,
            'timestamp': int(datetime.now().timestamp() * 1000),
            'exchanges': market_data,
            'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
            'ohlcv': {},  # Will be populated with OHLCV data
            'orderbook': {},  # Will be populated with orderbook data
            'trades': []  # Will be populated with recent trades
        }
        
        # Process data from the first available exchange
        for exchange_id, exchange_data in market_data.items():
            if 'ticker' in exchange_data:
                combined_data['ohlcv'] = {
                    'open': float(exchange_data['ticker'].get('open', 0)),
                    'high': float(exchange_data['ticker'].get('high', 0)),
                    'low': float(exchange_data['ticker'].get('low', 0)),
                    'close': float(exchange_data['ticker'].get('last', 0)),
                    'volume': float(exchange_data['ticker'].get('volume', 0))
                }
                break
        
        # Get orderbook from the first available exchange
        for exchange_id, exchange_data in market_data.items():
            if 'orderbook' in exchange_data:
                combined_data['orderbook'] = exchange_data['orderbook']
                break
        
        # Get recent trades from the first available exchange
        for exchange_id, exchange_data in market_data.items():
            if 'recent_trades' in exchange_data:
                combined_data['trades'] = exchange_data['recent_trades']
                break
        
        return combined_data
        
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
        raise

async def main():
    try:
        # Load configuration
        config = await load_config()
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config)
        await exchange_manager.initialize_exchanges()
        
        # Initialize analysis engine
        analysis_engine = ConfluenceAnalyzer(config)
        
        # Symbol to analyze
        symbol = "BTC/USDT"
        
        # Initialize analysis for the symbol
        init_result = await analysis_engine.initialize(symbol)
        logger.info(f"Analysis initialization result: {init_result}")
        
        # Get market data
        market_data = await get_market_data(exchange_manager, symbol)
        
        # Perform analysis
        analysis_result = await analysis_engine.analyze(market_data)
        
        # Print analysis results
        logger.info("\n=== Analysis Results ===")
        logger.info(f"Symbol: {analysis_result.symbol}")
        logger.info(f"Timestamp: {analysis_result.timestamp}")
        logger.info("\nComponent Scores:")
        logger.info(f"Momentum Score: {analysis_result.momentum_score:.2f}")
        logger.info(f"Orderflow Score: {analysis_result.orderflow_score:.2f}")
        logger.info(f"Position Score: {analysis_result.position_score:.2f}")
        logger.info(f"Orderbook Score: {analysis_result.orderbook_score:.2f}")
        logger.info(f"Volume Score: {analysis_result.volume_score:.2f}")
        logger.info(f"Sentiment Score: {analysis_result.sentiment_score:.2f}")
        logger.info(f"\nConfluence Score: {analysis_result.confluence_score:.2f}")
        
        # Print signal agreement
        agreement = analysis_result.signals.get('agreement', {})
        logger.info("\nSignal Agreement:")
        logger.info(f"Overall Bias: {agreement.get('overall_bias', 'unknown')}")
        logger.info(f"Agreement Percentage: {agreement.get('agreement_percentage', 0):.2f}%")
        
        # Print data quality metrics
        quality = analysis_result.metadata.get('data_quality', {})
        logger.info("\nData Quality Metrics:")
        logger.info(f"Completeness: {quality.get('completeness', 0):.2f}%")
        logger.info(f"Timeliness: {quality.get('timeliness', 0):.2f}%")
        logger.info(f"Reliability: {quality.get('reliability', 0):.2f}%")
        logger.info(f"Overall Quality: {quality.get('overall', 0):.2f}%")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 