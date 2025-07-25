#!/usr/bin/env python3
"""
Test script for enhanced transform methods.

This script tests the enhanced transform methods that were recently implemented:
- Orderbook Indicators: Enhanced transforms for OIR, DI, Liquidity, Price Impact, Depth
- Orderflow Indicators: Enhanced transforms for CVD, Trade Flow, Trades Imbalance, Trades Pressure, Liquidity Zones
- Sentiment Indicators: Enhanced transforms for Funding, LSR, Liquidation, Volatility, Open Interest
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
from src.config.manager import ConfigManager
from src.core.logger import Logger

logger = Logger(__name__)

class EnhancedTransformTester:
    """Tester for enhanced transform methods."""
    
    def __init__(self):
        """Initialize the tester."""
        self.config = self._load_config()
        self.logger = Logger(__name__)
        
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
    
    def test_orderbook_transforms(self):
        """Test enhanced orderbook transform methods."""
        logger.info("📖 Testing Orderbook Enhanced Transforms")
        
        orderbook_indicators = OrderbookIndicators(self.config)
        
        # Create mock orderbook data
        mid_price = 50000
        bids = np.array([[mid_price - i * 10, np.random.exponential(1)] for i in range(1, 21)])
        asks = np.array([[mid_price + i * 10, np.random.exponential(1)] for i in range(1, 21)])
        
        # Test enhanced OIR transform
        try:
            oir_value = 0.6  # Mock OIR value
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            oir_score = orderbook_indicators._enhanced_oir_transform(oir_value, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced OIR Transform: {oir_value:.3f} → {oir_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced OIR Transform failed: {e}")
        
        # Test enhanced DI transform
        try:
            di_value = 0.3  # Mock DI value
            total_volume = 1000.0
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            di_score = orderbook_indicators._enhanced_di_transform(di_value, total_volume, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced DI Transform: {di_value:.3f} → {di_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced DI Transform failed: {e}")
        
        # Test enhanced Liquidity transform
        try:
            spread = 0.001  # 0.1% spread
            depth_ratio = 1.5
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            liquidity_score = orderbook_indicators._enhanced_liquidity_transform(spread, depth_ratio, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced Liquidity Transform: spread={spread:.3f}, depth={depth_ratio:.2f} → {liquidity_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Liquidity Transform failed: {e}")
        
        # Test enhanced Price Impact transform
        try:
            price_impact = 0.005  # 0.5% impact
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            impact_score = orderbook_indicators._enhanced_price_impact_transform(price_impact, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced Price Impact Transform: {price_impact:.3f} → {impact_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Price Impact Transform failed: {e}")
        
        # Test enhanced Depth transform
        try:
            depth_ratio = 0.2  # 20% ratio
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            depth_score = orderbook_indicators._enhanced_depth_transform(depth_ratio, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced Depth Transform: ratio={depth_ratio:.3f} → {depth_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Depth Transform failed: {e}")
    
    def test_orderflow_transforms(self):
        """Test enhanced orderflow transform methods."""
        logger.info("🌊 Testing Orderflow Enhanced Transforms")
        
        orderflow_indicators = OrderflowIndicators(self.config)
        
        # Test enhanced CVD transform
        try:
            cvd_value = 1500  # Mock CVD value
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            cvd_score = orderflow_indicators._enhanced_cvd_transform(cvd_value, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced CVD Transform: {cvd_value} → {cvd_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced CVD Transform failed: {e}")
        
        # Test enhanced Trade Flow transform
        try:
            buy_volume = 1000.0
            sell_volume = 800.0
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            trade_flow_score = orderflow_indicators._enhanced_trade_flow_transform(buy_volume, sell_volume, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced Trade Flow Transform: buy={buy_volume}, sell={sell_volume} → {trade_flow_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Trade Flow Transform failed: {e}")
        
        # Test enhanced Trades Imbalance transform
        try:
            recent_imbalance = 0.7
            medium_imbalance = 0.6
            overall_imbalance = 0.55
            imbalance_score = orderflow_indicators._enhanced_trades_imbalance_transform(recent_imbalance, medium_imbalance, overall_imbalance)
            logger.info(f"✅ Enhanced Trades Imbalance Transform: recent={recent_imbalance:.2f}, medium={medium_imbalance:.2f}, overall={overall_imbalance:.2f} → {imbalance_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Trades Imbalance Transform failed: {e}")
        
        # Test enhanced Trades Pressure transform
        try:
            aggression_score = 0.75
            volume_pressure = 0.8
            size_pressure = 0.6
            pressure_score = orderflow_indicators._enhanced_trades_pressure_transform(aggression_score, volume_pressure, size_pressure)
            logger.info(f"✅ Enhanced Trades Pressure Transform: aggression={aggression_score:.2f}, volume={volume_pressure:.2f}, size={size_pressure:.2f} → {pressure_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Trades Pressure Transform failed: {e}")
        
        # Test enhanced Liquidity Zones transform
        try:
            proximity_score = 0.85
            sweep_score = 0.7
            strength_score = 0.8
            zones_score = orderflow_indicators._enhanced_liquidity_zones_transform(proximity_score, sweep_score, strength_score)
            logger.info(f"✅ Enhanced Liquidity Zones Transform: proximity={proximity_score:.2f}, sweep={sweep_score:.2f}, strength={strength_score:.2f} → {zones_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Liquidity Zones Transform failed: {e}")
    
    def test_sentiment_transforms(self):
        """Test enhanced sentiment transform methods."""
        logger.info("💭 Testing Sentiment Enhanced Transforms")
        
        sentiment_indicators = SentimentIndicators(self.config)
        
        # Test enhanced Funding transform
        try:
            funding_rate = 0.0002  # 0.02% funding rate
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            funding_score = sentiment_indicators._enhanced_funding_transform(funding_rate, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced Funding Transform: {funding_rate:.4f} → {funding_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Funding Transform failed: {e}")
        
        # Test enhanced LSR transform
        try:
            long_ratio = 60.0  # 60% long
            short_ratio = 40.0  # 40% short
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            lsr_score = sentiment_indicators._enhanced_lsr_transform(long_ratio, short_ratio, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced LSR Transform: long={long_ratio:.1f}%, short={short_ratio:.1f}% → {lsr_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced LSR Transform failed: {e}")
        
        # Test enhanced Liquidation transform
        try:
            liquidation_ratio = 0.65  # 65% long liquidations
            liquidation_volume = 1000.0
            volatility_context = 0.02
            liquidation_score = sentiment_indicators._enhanced_liquidation_transform(liquidation_ratio, liquidation_volume, volatility_context=volatility_context)
            logger.info(f"✅ Enhanced Liquidation Transform: ratio={liquidation_ratio:.2f}, volume={liquidation_volume} → {liquidation_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Liquidation Transform failed: {e}")
        
        # Test enhanced Volatility transform
        try:
            volatility = 0.025  # 2.5% volatility
            market_regime = {"type": "TREND_BULL", "volatility": 0.02}
            volatility_score = sentiment_indicators._enhanced_volatility_transform(volatility, market_regime=market_regime, volatility_context=0.02)
            logger.info(f"✅ Enhanced Volatility Transform: {volatility:.3f} → {volatility_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Volatility Transform failed: {e}")
        
        # Test enhanced Open Interest transform
        try:
            oi_change = 0.05  # 5% OI change
            oi_volume = 1000.0
            volatility_context = 0.02
            oi_score = sentiment_indicators._enhanced_open_interest_transform(oi_change, oi_volume, volatility_context=volatility_context)
            logger.info(f"✅ Enhanced Open Interest Transform: change={oi_change:.3f}, volume={oi_volume} → {oi_score:.2f}")
        except Exception as e:
            logger.error(f"❌ Enhanced Open Interest Transform failed: {e}")
    
    def run_test(self):
        """Run the enhanced transform test."""
        try:
            logger.info("🚀 Starting Enhanced Transform Methods Test")
            logger.info("="*60)
            
            # Test all transform categories
            self.test_orderbook_transforms()
            logger.info("")
            self.test_orderflow_transforms()
            logger.info("")
            self.test_sentiment_transforms()
            
            logger.info("="*60)
            logger.info("✅ Enhanced Transform Methods Test Completed!")
            
        except Exception as e:
            logger.error(f"❌ Enhanced transform test failed: {e}")
            raise

def main():
    """Main test runner."""
    tester = EnhancedTransformTester()
    tester.run_test()

if __name__ == "__main__":
    main() 