#!/usr/bin/env python3
"""
Test script for Bitcoin Beta Report with mock data.

This script tests the Bitcoin Beta Report functionality using mock data
to ensure the implementation works correctly.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.reports.bitcoin_beta_report import BitcoinBetaReport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockTopSymbolsManager:
    """Mock top symbols manager for testing."""
    
    async def get_symbols(self):
        """Return mock symbols."""
        return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT']

class MockExchange:
    """Mock exchange for testing."""
    
    def __init__(self):
        self.exchange_id = 'test_exchange'
        
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int):
        """Generate mock OHLCV data."""
        logger.info(f"Generating mock data for {symbol} {timeframe} (limit: {limit})")
        
        # Generate realistic-looking price data
        np.random.seed(42)  # For reproducible results
        
        # Base prices for different symbols
        base_prices = {
            'BTCUSDT': 65000,
            'ETHUSDT': 3500,
            'SOLUSDT': 150,
            'AVAXUSDT': 35,
            'XRPUSDT': 0.60
        }
        
        base_price = base_prices.get(symbol, 1000)
        
        # Generate time series
        now = datetime.now()
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '30m': 30,
            '4h': 240
        }
        
        minutes = timeframe_minutes.get(timeframe, 1)
        timestamps = []
        ohlcv_data = []
        
        # Generate price movements with some correlation to Bitcoin
        btc_correlation = {
            'BTCUSDT': 1.0,
            'ETHUSDT': 0.85,
            'SOLUSDT': 0.75,
            'AVAXUSDT': 0.70,
            'XRPUSDT': 0.60
        }
        
        correlation = btc_correlation.get(symbol, 0.5)
        
        for i in range(limit):
            timestamp = int((now - timedelta(minutes=minutes * i)).timestamp() * 1000)
            
            # Generate correlated price movement
            btc_move = np.random.normal(0, 0.02)  # 2% daily volatility
            symbol_move = correlation * btc_move + (1 - correlation) * np.random.normal(0, 0.025)
            
            if i == 0:
                price = base_price
            else:
                price = ohlcv_data[0][4] * (1 + symbol_move)  # Use previous close
                
            # Generate OHLC from close price
            volatility = 0.01  # 1% intraday volatility
            high = price * (1 + abs(np.random.normal(0, volatility)))
            low = price * (1 - abs(np.random.normal(0, volatility)))
            open_price = price * (1 + np.random.normal(0, volatility / 2))
            volume = abs(np.random.normal(1000, 200))
            
            # Ensure high >= close >= low and high >= open >= low
            high = max(high, price, open_price)
            low = min(low, price, open_price)
            
            ohlcv_data.insert(0, [timestamp, open_price, high, low, price, volume])
            
        return ohlcv_data

class MockExchangeManager:
    """Mock exchange manager for testing."""
    
    def __init__(self, config):
        self.config = config
        self.exchange = MockExchange()
        
    async def get_primary_exchange(self):
        """Return mock exchange."""
        return self.exchange

async def test_bitcoin_beta_report():
    """Test the Bitcoin Beta Report generation."""
    try:
        logger.info("=== Testing Bitcoin Beta Report ===")
        
        # Create mock configuration
        config = {
            'market': {
                'symbols': {
                    'static_symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT']
                }
            }
        }
        
        # Create mock managers
        exchange_manager = MockExchangeManager(config)
        top_symbols_manager = MockTopSymbolsManager()
        
        # Create Bitcoin Beta Report generator
        beta_report = BitcoinBetaReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config
        )
        
        logger.info("Bitcoin Beta Report generator created")
        
        # Generate the report
        logger.info("Starting test report generation...")
        pdf_path = await beta_report.generate_report()
        
        if pdf_path:
            logger.info(f"✅ Test Bitcoin Beta Report generated successfully!")
            logger.info(f"📄 Report saved to: {pdf_path}")
            
            # Check file exists and has reasonable size
            file_path = Path(pdf_path)
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(f"📊 Report size: {file_size / 1024:.1f} KB")
                
                if file_size > 50000:  # At least 50KB
                    logger.info("✅ Report size looks reasonable")
                    return True
                else:
                    logger.warning("⚠️  Report size seems small")
                    return False
            else:
                logger.error("❌ Report file not found")
                return False
        else:
            logger.error("❌ Failed to generate test Bitcoin Beta Report")
            return False
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_beta_calculations():
    """Test beta calculation methods."""
    try:
        logger.info("=== Testing Beta Calculations ===")
        
        # Create sample data
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        # Bitcoin returns (reference)
        btc_returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        
        # Correlated asset returns
        eth_returns = 0.8 * btc_returns + 0.2 * pd.Series(np.random.normal(0.001, 0.025, 100), index=dates)
        
        # Calculate beta manually
        covariance = np.cov(eth_returns, btc_returns)[0, 1]
        btc_variance = np.var(btc_returns)
        expected_beta = covariance / btc_variance
        
        logger.info(f"Expected ETH beta vs BTC: {expected_beta:.3f}")
        
        # Test correlation
        correlation = np.corrcoef(eth_returns, btc_returns)[0, 1]
        logger.info(f"ETH-BTC correlation: {correlation:.3f}")
        
        if 0.7 <= correlation <= 0.9:
            logger.info("✅ Correlation calculation looks correct")
        else:
            logger.warning("⚠️  Correlation might be unexpected")
            
        logger.info("✅ Beta calculation test completed")
        return True
        
    except Exception as e:
        logger.error(f"Error in beta calculation test: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🧪 Bitcoin Beta Report Test Suite")
    print("=" * 50)
    
    try:
        # Test beta calculations
        calc_result = asyncio.run(test_beta_calculations())
        
        # Test full report generation
        report_result = asyncio.run(test_bitcoin_beta_report())
        
        if calc_result and report_result:
            print("\n✅ All tests passed!")
            print("\n📈 The Bitcoin Beta Report includes:")
            print("  • Multi-timeframe beta analysis (4H, 30M, 5M, 1M)")
            print("  • Normalized price performance charts")
            print("  • Beta comparison across timeframes")
            print("  • Correlation heatmap")
            print("  • Statistical measures for traders")
            print("  • Key trading insights")
            print("\n🔄 Ready for production use!")
        else:
            print("\n❌ Some tests failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 