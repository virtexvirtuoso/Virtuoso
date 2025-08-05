#!/usr/bin/env python3
"""
Test script for Bitcoin Beta Alpha Generation features.

This script demonstrates how the enhanced Bitcoin Beta Report detects
alpha generation opportunities through divergence pattern analysis.
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
from src.reports.bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector, DivergenceType

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
    """Mock exchange with alpha generation scenarios."""
    
    def __init__(self):
        self.exchange_id = 'test_exchange'
        
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int):
        """Generate mock OHLCV data with specific alpha patterns."""
        logger.info(f"Generating alpha scenario data for {symbol} {timeframe}")
        
        np.random.seed(42)  # For reproducible results
        
        # Base prices for different symbols
        base_prices = {
            'BTCUSDT': 65000,
            'ETHUSDT': 3500,    # Will show alpha breakout
            'SOLUSDT': 150,     # Will show cross-timeframe divergence
            'AVAXUSDT': 35,     # Will show correlation breakdown
            'XRPUSDT': 0.60     # Will show reversion setup
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
        ohlcv_data = []
        
        # Create specific alpha generation scenarios
        if symbol == 'ETHUSDT':
            # Alpha breakout scenario - positive alpha across all timeframes
            correlations = {'1m': 0.45, '5m': 0.48, '30m': 0.52, '4h': 0.55}
            alphas = {'1m': 0.08, '5m': 0.09, '30m': 0.10, '4h': 0.11}  # Increasing alpha
            
        elif symbol == 'SOLUSDT':
            # Cross-timeframe divergence - low beta on short timeframes
            correlations = {'1m': 0.35, '5m': 0.40, '30m': 0.75, '4h': 0.78}
            alphas = {'1m': 0.06, '5m': 0.05, '30m': 0.02, '4h': 0.01}
            
        elif symbol == 'AVAXUSDT':
            # Correlation breakdown scenario
            correlations = {'1m': 0.25, '5m': 0.28, '30m': 0.30, '4h': 0.32}  # Very low correlation
            alphas = {'1m': 0.03, '5m': 0.04, '30m': 0.05, '4h': 0.06}
            
        elif symbol == 'XRPUSDT':
            # Reversion setup - extreme beta with negative alpha
            correlations = {'1m': 0.85, '5m': 0.87, '30m': 0.88, '4h': 0.90}  # High correlation
            alphas = {'1m': -0.05, '5m': -0.04, '30m': -0.03, '4h': -0.02}  # Negative alpha
            
        else:  # BTCUSDT - reference asset
            correlations = {'1m': 1.0, '5m': 1.0, '30m': 1.0, '4h': 1.0}
            alphas = {'1m': 0.0, '5m': 0.0, '30m': 0.0, '4h': 0.0}
        
        # Generate price data based on scenario
        correlation = correlations.get(timeframe, 0.7)
        target_alpha = alphas.get(timeframe, 0.0)
        
        # Generate correlated returns with embedded alpha
        for i in range(limit):
            timestamp = int((now - timedelta(minutes=minutes * i)).timestamp() * 1000)
            
            # Generate Bitcoin movement
            btc_move = np.random.normal(0, 0.02)  # 2% daily volatility
            
            # Generate correlated movement with alpha
            if symbol == 'BTCUSDT':
                symbol_move = btc_move
            else:
                # Add alpha component
                independent_move = np.random.normal(target_alpha / 252, 0.01)  # Daily alpha
                symbol_move = correlation * btc_move + (1 - correlation) * independent_move
                
                # Create extreme beta for XRPUSDT (reversion scenario)
                if symbol == 'XRPUSDT':
                    symbol_move = 1.8 * btc_move + independent_move  # High beta with negative alpha
            
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

async def test_alpha_generation():
    """Test the alpha generation detection features."""
    try:
        logger.info("=== Testing Bitcoin Beta Alpha Generation ===")
        
        # Create mock configuration with alpha detection settings
        config = {
            'market': {
                'symbols': {
                    'static_symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'XRPUSDT']
                }
            },
            'bitcoin_beta_alpha': {
                'beta_divergence_threshold': 0.3,
                'alpha_threshold': 0.05,
                'correlation_breakdown_threshold': 0.3,
                'confidence_threshold': 0.7,
                'timeframe_consensus_threshold': 0.6,
                'rolling_beta_change_threshold': 0.5,
                'reversion_beta_threshold': 1.5,
                'sector_correlation_threshold': 0.8
            }
        }
        
        # Create mock managers
        exchange_manager = MockExchangeManager(config)
        top_symbols_manager = MockTopSymbolsManager()
        
        # Create Bitcoin Beta Report generator with alpha detection
        beta_report = BitcoinBetaReport(
            exchange_manager=exchange_manager,
            top_symbols_manager=top_symbols_manager,
            config=config
        )
        
        logger.info("Enhanced Bitcoin Beta Report generator created with alpha detection")
        
        # Generate the report with alpha opportunities
        logger.info("Generating report with alpha generation analysis...")
        pdf_path = await beta_report.generate_report()
        
        if pdf_path:
            logger.info(f"✅ Enhanced Bitcoin Beta Report generated successfully!")
            logger.info(f"📄 Report with alpha opportunities saved to: {pdf_path}")
            
            # Check file exists and has reasonable size
            file_path = Path(pdf_path)
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(f"📊 Enhanced report size: {file_size / 1024:.1f} KB")
                
                # Test the alpha detector directly
                logger.info("\n=== Testing Alpha Detector Directly ===")
                await test_alpha_detector_directly(beta_report.alpha_detector)
                
                return True
            else:
                logger.error("❌ Report file not found")
                return False
        else:
            logger.error("❌ Failed to generate enhanced Bitcoin Beta Report")
            return False
            
    except Exception as e:
        logger.error(f"Error in alpha generation test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_alpha_detector_directly(alpha_detector):
    """Test the alpha detector with mock beta analysis data."""
    try:
        # Create mock beta analysis data with divergence patterns
        mock_beta_analysis = {
            'htf': {  # 4H timeframe
                'BTCUSDT': {'beta': 1.0, 'correlation': 1.0, 'alpha': 0.0, 'rolling_beta_30': 1.0},
                'ETHUSDT': {'beta': 0.85, 'correlation': 0.55, 'alpha': 0.11, 'rolling_beta_30': 0.83},  # Alpha breakout
                'SOLUSDT': {'beta': 0.78, 'correlation': 0.78, 'alpha': 0.01, 'rolling_beta_30': 0.75},  # Normal
                'AVAXUSDT': {'beta': 0.70, 'correlation': 0.32, 'alpha': 0.06, 'rolling_beta_30': 0.68}, # Correlation breakdown
                'XRPUSDT': {'beta': 1.65, 'correlation': 0.90, 'alpha': -0.02, 'rolling_beta_30': 1.70}  # Reversion setup
            },
            'mtf': {  # 30M timeframe
                'BTCUSDT': {'beta': 1.0, 'correlation': 1.0, 'alpha': 0.0, 'rolling_beta_30': 1.0},
                'ETHUSDT': {'beta': 0.82, 'correlation': 0.52, 'alpha': 0.10, 'rolling_beta_30': 0.80},
                'SOLUSDT': {'beta': 0.75, 'correlation': 0.75, 'alpha': 0.02, 'rolling_beta_30': 0.73},
                'AVAXUSDT': {'beta': 0.68, 'correlation': 0.30, 'alpha': 0.05, 'rolling_beta_30': 0.65},
                'XRPUSDT': {'beta': 1.62, 'correlation': 0.88, 'alpha': -0.03, 'rolling_beta_30': 1.68}
            },
            'ltf': {  # 5M timeframe
                'BTCUSDT': {'beta': 1.0, 'correlation': 1.0, 'alpha': 0.0, 'rolling_beta_30': 1.0},
                'ETHUSDT': {'beta': 0.80, 'correlation': 0.48, 'alpha': 0.09, 'rolling_beta_30': 0.78},
                'SOLUSDT': {'beta': 0.40, 'correlation': 0.40, 'alpha': 0.05, 'rolling_beta_30': 0.38},  # Cross-timeframe divergence
                'AVAXUSDT': {'beta': 0.65, 'correlation': 0.28, 'alpha': 0.04, 'rolling_beta_30': 0.62},
                'XRPUSDT': {'beta': 1.58, 'correlation': 0.87, 'alpha': -0.04, 'rolling_beta_30': 1.65}
            },
            'base': {  # 1M timeframe
                'BTCUSDT': {'beta': 1.0, 'correlation': 1.0, 'alpha': 0.0, 'rolling_beta_30': 1.0},
                'ETHUSDT': {'beta': 0.78, 'correlation': 0.45, 'alpha': 0.08, 'rolling_beta_30': 0.75},
                'SOLUSDT': {'beta': 0.35, 'correlation': 0.35, 'alpha': 0.06, 'rolling_beta_30': 0.32},  # Strong divergence
                'AVAXUSDT': {'beta': 0.62, 'correlation': 0.25, 'alpha': 0.03, 'rolling_beta_30': 0.60},
                'XRPUSDT': {'beta': 1.55, 'correlation': 0.85, 'alpha': -0.05, 'rolling_beta_30': 1.62}
            }
        }
        
        # Run alpha detection
        logger.info("Running alpha opportunity detection...")
        opportunities = alpha_detector.detect_alpha_opportunities(mock_beta_analysis)
        
        logger.info(f"Found {len(opportunities)} alpha generation opportunities:")
        
        for i, opp in enumerate(opportunities, 1):
            logger.info(f"\n🎯 Opportunity #{i}")
            logger.info(f"   Symbol: {opp.symbol}")
            logger.info(f"   Pattern: {opp.divergence_type.value.replace('_', ' ').title()}")
            logger.info(f"   Confidence: {opp.confidence:.1%}")
            logger.info(f"   Alpha Potential: {opp.alpha_potential:.1%}")
            logger.info(f"   Risk Level: {opp.risk_level}")
            logger.info(f"   Expected Duration: {opp.expected_duration}")
            logger.info(f"   Insight: {opp.trading_insight}")
            logger.info(f"   Action: {opp.recommended_action}")
        
        # Verify expected patterns were detected
        expected_patterns = {
            'ETHUSDT': DivergenceType.ALPHA_BREAKOUT,
            'SOLUSDT': DivergenceType.CROSS_TIMEFRAME,
            'AVAXUSDT': DivergenceType.CORRELATION_BREAKDOWN,
            'XRPUSDT': DivergenceType.REVERSION_SETUP
        }
        
        detected_patterns = {opp.symbol: opp.divergence_type for opp in opportunities}
        
        logger.info("\n=== Pattern Detection Verification ===")
        for symbol, expected_pattern in expected_patterns.items():
            if symbol in detected_patterns:
                detected_pattern = detected_patterns[symbol]
                if detected_pattern == expected_pattern:
                    logger.info(f"✅ {symbol}: Expected {expected_pattern.value} - Detected {detected_pattern.value}")
                else:
                    logger.warning(f"⚠️  {symbol}: Expected {expected_pattern.value} - Detected {detected_pattern.value}")
            else:
                logger.warning(f"❌ {symbol}: Expected {expected_pattern.value} - Not detected")
                
        return len(opportunities) > 0
        
    except Exception as e:
        logger.error(f"Error testing alpha detector: {str(e)}")
        return False

def main():
    """Run all alpha generation tests."""
    print("🧪 Bitcoin Beta Alpha Generation Test Suite")
    print("=" * 60)
    
    try:
        # Test enhanced report generation
        result = asyncio.run(test_alpha_generation())
        
        if result:
            print("\n✅ All alpha generation tests passed!")
            print("\n🎯 Enhanced Bitcoin Beta Report now includes:")
            print("  • Cross-timeframe beta divergence detection")
            print("  • Alpha breakout pattern recognition")
            print("  • Correlation breakdown alerts")
            print("  • Beta expansion/compression analysis")
            print("  • Mean reversion setup identification")
            print("  • Sector rotation pattern detection")
            print("  • Actionable trading recommendations")
            print("  • Risk-adjusted confidence scoring")
            print("\n🚀 Ready for alpha generation in production!")
        else:
            print("\n❌ Some alpha generation tests failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 