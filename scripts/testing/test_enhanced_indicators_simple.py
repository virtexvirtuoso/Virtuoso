#!/usr/bin/env python3
"""
Simple test script for enhanced indicator methods.

This script tests the enhanced methods that actually exist in the codebase:
- Technical Indicators: Enhanced RSI
- Volume Indicators: Enhanced Volume Trend, Volume Volatility, Relative Volume
- Orderbook Indicators: Enhanced OIR, DI, Liquidity, Price Impact, Depth
- Orderflow Indicators: Enhanced CVD, Trade Flow, Trades Imbalance, Trades Pressure, Liquidity Zones
- Sentiment Indicators: Enhanced Funding, LSR, Liquidation, Volatility, Open Interest
"""

import sys
import os
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
from src.config.manager import ConfigManager
from src.core.logger import Logger

logger = Logger(__name__)

class SimpleEnhancedIndicatorTester:
    """Simple tester for enhanced indicator methods."""
    
    def __init__(self):
        """Initialize the tester."""
        self.config = self._load_config()
        self.logger = Logger(__name__)
        self.test_results = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        try:
            config_manager = ConfigManager()
            return config_manager.config
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {
                'exchanges': {'bybit': {'enabled': True}},
                'analysis': {'indicators': {}}
            }
    
    def create_mock_data(self) -> Dict[str, Any]:
        """Create mock market data for testing."""
        # Create mock OHLCV data
        timestamps = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        base_price = 50000
        
        ohlcv_data = {}
        for tf_name in ['base', 'ltf', 'mtf', 'htf']:
            prices = []
            volumes = []
            
            for i in range(100):
                price = base_price + np.random.normal(0, base_price * 0.001)
                volume = np.random.exponential(10)
                prices.append(price)
                volumes.append(volume)
            
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': prices,
                'high': [p + abs(np.random.normal(0, p * 0.0005)) for p in prices],
                'low': [p - abs(np.random.normal(0, p * 0.0005)) for p in prices],
                'close': [p + np.random.normal(0, p * 0.0003) for p in prices],
                'volume': volumes
            })
            df.set_index('timestamp', inplace=True)
            ohlcv_data[tf_name] = df
        
        # Create mock orderbook data
        mid_price = base_price
        bids = []
        asks = []
        
        for i in range(20):
            bid_price = mid_price - (i + 1) * 10
            ask_price = mid_price + (i + 1) * 10
            bid_size = np.random.exponential(1)
            ask_size = np.random.exponential(1)
            
            bids.append([bid_price, bid_size])
            asks.append([ask_price, ask_size])
        
        orderbook = {
            'bids': bids,
            'asks': asks,
            'timestamp': datetime.now(timezone.utc).timestamp() * 1000
        }
        
        # Create mock trades data
        trades = []
        for i in range(100):
            trade = {
                'id': str(i),
                'timestamp': datetime.now(timezone.utc).timestamp() * 1000 - i * 1000,
                'price': mid_price + np.random.normal(0, mid_price * 0.0001),
                'amount': np.random.exponential(0.1),
                'side': 'buy' if np.random.random() > 0.5 else 'sell'
            }
            trades.append(trade)
        
        trades_df = pd.DataFrame(trades)
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='ms')
        
        return {
            'symbol': 'BTCUSDT',
            'ohlcv': ohlcv_data,
            'orderbook': orderbook,
            'ticker': {'last': mid_price, 'bid': mid_price - 5, 'ask': mid_price + 5},
            'trades': trades,
            'processed_trades': trades_df,
            'timestamp': datetime.now(timezone.utc)
        }
    
    def test_technical_indicators(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Test enhanced technical indicators."""
        try:
            logger.info("🔧 Testing Technical Indicators")
            
            tech_indicators = TechnicalIndicators(self.config)
            results = {}
            
            # Test enhanced RSI
            try:
                df = market_data['ohlcv']['base']
                rsi_score = tech_indicators._calculate_enhanced_rsi_score(df)
                results['enhanced_rsi'] = rsi_score
                logger.info(f"✅ Enhanced RSI Score: {rsi_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced RSI failed: {e}")
                results['enhanced_rsi'] = None
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Technical indicators test failed: {e}")
            return {}
    
    def test_volume_indicators(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Test enhanced volume indicators."""
        try:
            logger.info("📊 Testing Volume Indicators")
            
            volume_indicators = VolumeIndicators(self.config)
            results = {}
            
            # Test enhanced Volume Trend
            try:
                trades_df = market_data['processed_trades']
                volume_trend_score = volume_indicators._calculate_enhanced_volume_trend_score(trades_df)
                results['enhanced_volume_trend'] = volume_trend_score
                logger.info(f"✅ Enhanced Volume Trend Score: {volume_trend_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Volume Trend failed: {e}")
                results['enhanced_volume_trend'] = None
            
            # Test enhanced Volume Volatility
            try:
                trades_df = market_data['processed_trades']
                volume_volatility_score = volume_indicators._calculate_enhanced_volume_volatility_score(trades_df)
                results['enhanced_volume_volatility'] = volume_volatility_score
                logger.info(f"✅ Enhanced Volume Volatility Score: {volume_volatility_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Volume Volatility failed: {e}")
                results['enhanced_volume_volatility'] = None
            
            # Test enhanced Relative Volume
            try:
                relative_volume_score = volume_indicators._calculate_enhanced_relative_volume_score(market_data)
                results['enhanced_relative_volume'] = relative_volume_score
                logger.info(f"✅ Enhanced Relative Volume Score: {relative_volume_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Relative Volume failed: {e}")
                results['enhanced_relative_volume'] = None
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Volume indicators test failed: {e}")
            return {}
    
    def test_orderbook_indicators(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Test enhanced orderbook indicators."""
        try:
            logger.info("📖 Testing Orderbook Indicators")
            
            orderbook_indicators = OrderbookIndicators(self.config)
            results = {}
            
            # Prepare orderbook data
            orderbook = market_data.get('orderbook', {})
            bids = np.array(orderbook.get('bids', []))
            asks = np.array(orderbook.get('asks', []))
            
            if len(bids) == 0 or len(asks) == 0:
                logger.warning("⚠️ No orderbook data available")
                return results
            
            # Test enhanced OIR
            try:
                oir_score = orderbook_indicators._calculate_enhanced_oir_score(bids, asks)
                results['enhanced_oir'] = oir_score
                logger.info(f"✅ Enhanced OIR Score: {oir_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced OIR failed: {e}")
                results['enhanced_oir'] = None
            
            # Test enhanced DI
            try:
                di_score = orderbook_indicators._calculate_enhanced_di_score(bids, asks)
                results['enhanced_di'] = di_score
                logger.info(f"✅ Enhanced DI Score: {di_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced DI failed: {e}")
                results['enhanced_di'] = None
            
            # Test enhanced Liquidity
            try:
                liquidity_score = orderbook_indicators._calculate_enhanced_liquidity_score(market_data)
                results['enhanced_liquidity'] = liquidity_score
                logger.info(f"✅ Enhanced Liquidity Score: {liquidity_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Liquidity failed: {e}")
                results['enhanced_liquidity'] = None
            
            # Test enhanced Price Impact
            try:
                price_impact_score = orderbook_indicators._calculate_enhanced_price_impact_score(market_data)
                results['enhanced_price_impact'] = price_impact_score
                logger.info(f"✅ Enhanced Price Impact Score: {price_impact_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Price Impact failed: {e}")
                results['enhanced_price_impact'] = None
            
            # Test enhanced Depth
            try:
                depth_score = orderbook_indicators._calculate_enhanced_depth_score(bids, asks)
                results['enhanced_depth'] = depth_score
                logger.info(f"✅ Enhanced Depth Score: {depth_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Depth failed: {e}")
                results['enhanced_depth'] = None
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Orderbook indicators test failed: {e}")
            return {}
    
    def test_orderflow_indicators(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Test enhanced orderflow indicators."""
        try:
            logger.info("🌊 Testing Orderflow Indicators")
            
            orderflow_indicators = OrderflowIndicators(self.config)
            results = {}
            
            # Test enhanced CVD
            try:
                cvd_value = np.random.normal(0, 1000)  # Mock CVD value
                cvd_score = orderflow_indicators._calculate_enhanced_cvd_score(cvd_value)
                results['enhanced_cvd'] = cvd_score
                logger.info(f"✅ Enhanced CVD Score: {cvd_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced CVD failed: {e}")
                results['enhanced_cvd'] = None
            
            # Test enhanced Trade Flow
            try:
                trade_flow_score = orderflow_indicators._calculate_enhanced_trade_flow_score(market_data)
                results['enhanced_trade_flow'] = trade_flow_score
                logger.info(f"✅ Enhanced Trade Flow Score: {trade_flow_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Trade Flow failed: {e}")
                results['enhanced_trade_flow'] = None
            
            # Test enhanced Trades Imbalance
            try:
                trades_imbalance_score = orderflow_indicators._calculate_enhanced_trades_imbalance_score(market_data)
                results['enhanced_trades_imbalance'] = trades_imbalance_score
                logger.info(f"✅ Enhanced Trades Imbalance Score: {trades_imbalance_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Trades Imbalance failed: {e}")
                results['enhanced_trades_imbalance'] = None
            
            # Test enhanced Trades Pressure
            try:
                trades_pressure_score = orderflow_indicators._calculate_enhanced_trades_pressure_score(market_data)
                results['enhanced_trades_pressure'] = trades_pressure_score
                logger.info(f"✅ Enhanced Trades Pressure Score: {trades_pressure_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Trades Pressure failed: {e}")
                results['enhanced_trades_pressure'] = None
            
            # Test enhanced Liquidity Zones
            try:
                liquidity_zones_score = orderflow_indicators._calculate_enhanced_liquidity_zones_score(market_data)
                results['enhanced_liquidity_zones'] = liquidity_zones_score
                logger.info(f"✅ Enhanced Liquidity Zones Score: {liquidity_zones_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Liquidity Zones failed: {e}")
                results['enhanced_liquidity_zones'] = None
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Orderflow indicators test failed: {e}")
            return {}
    
    def test_sentiment_indicators(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Test enhanced sentiment indicators."""
        try:
            logger.info("💭 Testing Sentiment Indicators")
            
            sentiment_indicators = SentimentIndicators(self.config)
            results = {}
            
            # Create mock sentiment data
            sentiment_data = {
                'funding_rate': np.random.normal(0, 0.0001),
                'long_short_ratio': {'long': 60, 'short': 40},
                'liquidations': {
                    'long_liquidations': np.random.exponential(10000),
                    'short_liquidations': np.random.exponential(8000),
                    'total_volume': np.random.exponential(20000)
                },
                'volatility': {'current': np.random.uniform(0.01, 0.05)},
                'open_interest': {
                    'current': np.random.uniform(100000, 500000),
                    'previous': np.random.uniform(95000, 480000)
                }
            }
            
            # Test enhanced Funding Rate
            try:
                funding_score = sentiment_indicators._calculate_enhanced_funding_score(sentiment_data)
                results['enhanced_funding'] = funding_score
                logger.info(f"✅ Enhanced Funding Score: {funding_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Funding failed: {e}")
                results['enhanced_funding'] = None
            
            # Test enhanced LSR
            try:
                lsr_score = sentiment_indicators._calculate_enhanced_lsr_score(sentiment_data['long_short_ratio'])
                results['enhanced_lsr'] = lsr_score
                logger.info(f"✅ Enhanced LSR Score: {lsr_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced LSR failed: {e}")
                results['enhanced_lsr'] = None
            
            # Test enhanced Liquidation
            try:
                liquidation_score = sentiment_indicators._calculate_enhanced_liquidation_score(sentiment_data)
                results['enhanced_liquidation'] = liquidation_score
                logger.info(f"✅ Enhanced Liquidation Score: {liquidation_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Liquidation failed: {e}")
                results['enhanced_liquidation'] = None
            
            # Test enhanced Volatility
            try:
                volatility_score = sentiment_indicators._calculate_enhanced_volatility_score(sentiment_data)
                results['enhanced_volatility'] = volatility_score
                logger.info(f"✅ Enhanced Volatility Score: {volatility_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Volatility failed: {e}")
                results['enhanced_volatility'] = None
            
            # Test enhanced Open Interest
            try:
                oi_score = sentiment_indicators._calculate_enhanced_open_interest_score(sentiment_data)
                results['enhanced_open_interest'] = oi_score
                logger.info(f"✅ Enhanced Open Interest Score: {oi_score:.2f}")
            except Exception as e:
                logger.error(f"❌ Enhanced Open Interest failed: {e}")
                results['enhanced_open_interest'] = None
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Sentiment indicators test failed: {e}")
            return {}
    
    def analyze_results(self, results: Dict[str, Dict[str, float]]):
        """Analyze test results."""
        logger.info("\n" + "="*80)
        logger.info("📊 ENHANCED INDICATORS TEST RESULTS ANALYSIS")
        logger.info("="*80)
        
        total_tests = 0
        successful_tests = 0
        
        for category, category_results in results.items():
            logger.info(f"\n📈 {category.upper()}:")
            
            for indicator, score in category_results.items():
                total_tests += 1
                if score is not None:
                    successful_tests += 1
                    # Determine score interpretation
                    if score >= 75:
                        interpretation = "🟢 BULLISH"
                    elif score >= 55:
                        interpretation = "🟡 NEUTRAL-BULLISH"
                    elif score >= 45:
                        interpretation = "⚪ NEUTRAL"
                    elif score >= 25:
                        interpretation = "🟠 NEUTRAL-BEARISH"
                    else:
                        interpretation = "🔴 BEARISH"
                    
                    logger.info(f"  ✅ {indicator}: {score:.2f} ({interpretation})")
                else:
                    logger.info(f"  ❌ {indicator}: FAILED")
        
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Successful: {successful_tests}")
        logger.info(f"  Failed: {total_tests - successful_tests}")
        logger.info(f"  Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            logger.info("🎉 EXCELLENT! All enhanced indicators are working well!")
        elif success_rate >= 75:
            logger.info("✅ GOOD! Most enhanced indicators are working correctly!")
        elif success_rate >= 50:
            logger.info("⚠️ MODERATE! Some enhanced indicators need attention!")
        else:
            logger.info("❌ POOR! Many enhanced indicators are failing!")
    
    def run_test(self):
        """Run simple test of enhanced indicators."""
        try:
            logger.info("🚀 Starting Simple Enhanced Indicators Test")
            
            # Create mock data
            market_data = self.create_mock_data()
            logger.info("✅ Created mock market data")
            
            # Test all indicator categories
            results = {
                'technical': self.test_technical_indicators(market_data),
                'volume': self.test_volume_indicators(market_data),
                'orderbook': self.test_orderbook_indicators(market_data),
                'orderflow': self.test_orderflow_indicators(market_data),
                'sentiment': self.test_sentiment_indicators(market_data)
            }
            
            # Analyze results
            self.analyze_results(results)
            
        except Exception as e:
            logger.error(f"❌ Simple test failed: {e}")
            raise

def main():
    """Main test runner."""
    tester = SimpleEnhancedIndicatorTester()
    tester.run_test()

if __name__ == "__main__":
    main() 