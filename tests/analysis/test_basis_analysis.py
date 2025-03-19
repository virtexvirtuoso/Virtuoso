import asyncio
import logging
from src.core.exchanges.bybit import BybitExchange
from src.core.exchanges.coinbase import CoinbaseExchange
from src.core.analysis.basis_analysis import BasisAnalysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basis_analysis():
    """Test spot vs futures basis analysis"""
    try:
        # Initialize exchanges
        bybit_config = {
            'testnet': False,
            'api_credentials': {
                'api_key': '',  # No API key needed for public data
                'api_secret': ''
            },
            'options': {
                'defaultType': 'linear'
            }
        }
        
        coinbase_config = {
            'testnet': False,
            'api_credentials': {
                'api_key': '',  # No API key needed for public data
                'api_secret': ''
            }
        }
        
        bybit = BybitExchange(bybit_config)
        coinbase = CoinbaseExchange(coinbase_config)
        
        # Initialize exchanges
        await bybit.initialize()
        await coinbase.initialize()
        
        # Initialize analysis
        analyzer = BasisAnalysis()
        
        # Test symbols
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for symbol in symbols:
            logger.info(f"\nAnalyzing {symbol} spot-futures basis...")
            
            try:
                # Fetch market data
                futures_data = await bybit.fetch_market_data(symbol)
                spot_data = await coinbase.fetch_market_data(symbol)
                
                # Analyze basis
                analysis = await analyzer.analyze_basis(spot_data, futures_data, symbol)
                
                # Log analysis results
                logger.info("\n=== Basis Analysis Results ===")
                logger.info(f"Symbol: {analysis['symbol']}")
                logger.info(f"Spot Price (Coinbase): {analysis['spot_price']:.2f}")
                logger.info(f"Futures Price (Bybit): {analysis['futures_price']:.2f}")
                logger.info(f"Basis: {analysis['basis']:.2f}")
                logger.info(f"Basis Percentage: {analysis['basis_percentage']:.4f}%")
                logger.info(f"Implied Funding Rate (Ann.): {analysis['implied_funding']:.2f}%")
                
                # Market depth analysis
                logger.info("\nMarket Depth Analysis:")
                logger.info("Spot Market:")
                logger.info(f"- Total Depth: {analysis['market_depth']['spot']['total_depth']:.4f}")
                logger.info(f"- Bid/Ask Ratio: {analysis['market_depth']['spot']['bid_ask_ratio']:.4f}")
                logger.info(f"- Spread (bps): {analysis['market_depth']['spot']['spread_bps']:.2f}")
                
                logger.info("\nFutures Market:")
                logger.info(f"- Total Depth: {analysis['market_depth']['futures']['total_depth']:.4f}")
                logger.info(f"- Bid/Ask Ratio: {analysis['market_depth']['futures']['bid_ask_ratio']:.4f}")
                logger.info(f"- Spread (bps): {analysis['market_depth']['futures']['spread_bps']:.2f}")
                
                # Trade flow analysis
                logger.info("\nTrade Flow Analysis:")
                logger.info("Spot Market:")
                logger.info(f"- Net Flow: {analysis['trade_flow']['spot']['net_flow']:.4f}")
                logger.info(f"- Buy/Sell Ratio: {analysis['trade_flow']['spot']['flow_ratio']:.4f}")
                
                logger.info("\nFutures Market:")
                logger.info(f"- Net Flow: {analysis['trade_flow']['futures']['net_flow']:.4f}")
                logger.info(f"- Buy/Sell Ratio: {analysis['trade_flow']['futures']['flow_ratio']:.4f}")
                
                # Execution costs
                logger.info("\nExecution Costs Analysis (1 BTC):")
                logger.info("Spot Market:")
                logger.info(f"- Avg Price: {analysis['execution_costs']['spot']['avg_price']:.2f}")
                logger.info(f"- Slippage (bps): {analysis['execution_costs']['spot']['slippage_bps']:.2f}")
                
                logger.info("\nFutures Market:")
                logger.info(f"- Avg Price: {analysis['execution_costs']['futures']['avg_price']:.2f}")
                logger.info(f"- Slippage (bps): {analysis['execution_costs']['futures']['slippage_bps']:.2f}")
                
                # Trading signals
                logger.info("\nTrading Signals:")
                logger.info(f"Basis Opportunity: {analysis['signals']['basis_opportunity']}")
                if analysis['signals']['basis_opportunity']:
                    logger.info(f"- Confidence: {analysis['signals']['confidence']:.2%}")
                    logger.info(f"- Recommended Size: {analysis['signals']['recommended_size']:.4f}")
                    logger.info(f"- Entry Threshold: {analysis['signals']['entry_threshold']:.4f}%")
                    logger.info(f"- Exit Threshold: {analysis['signals']['exit_threshold']:.4f}%")
                    logger.info(f"- Risk Score: {analysis['signals']['risk_score']:.2f}")
                    logger.info("Factors:")
                    for factor in analysis['signals']['factors']:
                        logger.info(f"  * {factor}")
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
                continue
                
            logger.info("\n" + "="*50)
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
    finally:
        await bybit.close()
        await coinbase.close()

if __name__ == "__main__":
    asyncio.run(test_basis_analysis()) 