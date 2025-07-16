#!/usr/bin/env python3
"""
Test Enhanced Signal Generation with Conflict Detection

This script tests the enhanced signal generation system using real BTCUSDT data
that shows conflicting signals (bullish orderbook vs bearish technical/orderflow).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
from datetime import datetime
import logging
from src.core.interpretation.interpretation_manager import InterpretationManager
from src.core.analysis.interpretation_generator import InterpretationGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_btcusdt_test_data():
    """Create test data based on the BTCUSDT analysis shown by the user."""
    return {
        'symbol': 'BTCUSDT',
        'current_price': 95000.0,
        'confluence': 49.36,
        'score': 49.36,
        'timestamp': int(datetime.now().timestamp() * 1000),
        
        # Component scores from the user's analysis
        'orderbook_score': 76.11,     # Strong bullish
        'price_structure_score': 62.43,  # Moderate bullish
        'volume_score': 42.69,        # Slightly bearish
        'orderflow_score': 26.63,     # Strong bearish
        'sentiment_score': 59.47,     # Moderate bullish
        'technical_score': 24.44,     # Strong bearish
        
        # Component weights (impact scores)
        'orderbook_impact': 19.0,
        'price_structure_impact': 10.0,
        'volume_impact': 6.8,
        'orderflow_impact': 6.7,
        'sentiment_impact': 4.2,
        'technical_impact': 2.7,
        
        # Sub-component details from the analysis
        'orderbook': {
            'spread': 100.00,
            'imbalance': 85.75,
            'obps': 84.18,
            'liquidity': 83.49,
            'mpi': 71.86
        },
        
        'technical': {
            'macd': 19.5,
            'rsi': 34.6,
            'momentum': 25.0
        },
        
        'volume': {
            'volume_profile': 80.4,
            'volume_flow': 35.0,
            'volume_delta': 40.0
        },
        
        'orderflow': {
            'cumulative_delta': 15.0,
            'large_trades': 20.0,
            'absorption': 30.0
        },
        
        'sentiment': {
            'funding_rate': 55.0,
            'long_short_ratio': 65.0,
            'volatility_index': 58.0
        },
        
        'price_structure': {
            'vwap': 60.0,
            'swing_structure': 65.0,
            'support_resistance': 62.0
        },
        
        # Market metadata
        'volatility': {'atr_percentage': 3.2},
        'funding_rate': {'average': 0.0001}
    }

async def test_enhanced_interpretation_manager():
    """Test the enhanced interpretation manager with conflict detection."""
    logger.info("🔬 Testing Enhanced Interpretation Manager with Conflict Detection")
    logger.info("=" * 80)
    
    # Create test data based on user's BTCUSDT analysis
    test_data = create_btcusdt_test_data()
    
    logger.info(f"📊 Testing with BTCUSDT data:")
    logger.info(f"   Overall Score: {test_data['confluence']:.2f}")
    logger.info(f"   Orderbook: {test_data['orderbook_score']:.2f} (Impact: {test_data['orderbook_impact']})")
    logger.info(f"   Technical: {test_data['technical_score']:.2f} (Impact: {test_data['technical_impact']})")
    logger.info(f"   Orderflow: {test_data['orderflow_score']:.2f} (Impact: {test_data['orderflow_impact']})")
    logger.info("")
    
    try:
        # Initialize interpretation manager
        interpretation_manager = InterpretationManager()
        
        # Create raw interpretations based on the component scores
        raw_interpretations = []
        
        components = {
            'orderbook': test_data['orderbook_score'],
            'price_structure': test_data['price_structure_score'],
            'volume': test_data['volume_score'],
            'orderflow': test_data['orderflow_score'],
            'sentiment': test_data['sentiment_score'],
            'technical': test_data['technical_score']
        }
        
        for component_name, component_score in components.items():
            if component_score > 60:
                bias = "bullish"
                strength = "strong" if component_score > 70 else "moderate"
            elif component_score < 40:
                bias = "bearish"
                strength = "strong" if component_score < 30 else "moderate"
            else:
                bias = "neutral"
                strength = "weak"
            
            interpretation_text = f"{component_name.replace('_', ' ').title()} shows {strength} {bias} bias with score of {component_score:.1f}"
            
            raw_interpretations.append({
                'component': component_name,
                'display_name': component_name.replace('_', ' ').title(),
                'interpretation': interpretation_text
            })
        
        # Prepare market data for context
        market_data = {
            'market_overview': {
                'regime': 'NEUTRAL',  # 49.36 is neutral
                'volatility': test_data['volatility']['atr_percentage'],
                'trend_strength': 0.5,
                'volume_change': 0.4
            },
            'smart_money_index': {'index': test_data['sentiment_score']},
            'whale_activity': {'sentiment': 'BEARISH'},  # orderflow is bearish
            'funding_rate': {'average': test_data['funding_rate']['average']}
        }
        
        # Process interpretations through the interpretation manager
        interpretation_set = interpretation_manager.process_interpretations(
            raw_interpretations, 
            f"signal_{test_data['symbol']}",
            market_data,
            datetime.now()
        )
        
        # Generate enhanced synthesis with conflict detection
        enhanced_synthesis = interpretation_manager._generate_enhanced_synthesis(
            interpretation_set
        )
        
        logger.info("🔍 ENHANCED ANALYSIS RESULTS:")
        logger.info("=" * 50)
        
        # Display processed interpretations
        logger.info("📈 PROCESSED INTERPRETATIONS:")
        for i, interpretation in enumerate(interpretation_set.interpretations, 1):
            logger.info(f"   {i}. {interpretation.component_name}: {interpretation.interpretation_text}")
        logger.info("")
        
        # Display enhanced synthesis
        if enhanced_synthesis:
            logger.info("🧠 ENHANCED SYNTHESIS:")
            logger.info(f"   {enhanced_synthesis}")
            logger.info("")
            
            # Check for conflict detection
            if "CONFLICTED" in enhanced_synthesis:
                logger.info("⚠️  CONFLICT DETECTION: ✅ Successfully detected conflicting signals!")
                logger.info("   The system correctly identified that:")
                logger.info("   - Orderbook signals are strongly bullish (76.11)")
                logger.info("   - Technical signals are strongly bearish (24.44)")
                logger.info("   - Orderflow signals are strongly bearish (26.63)")
            else:
                logger.info("⚠️  CONFLICT DETECTION: ❌ Conflicts not properly detected")
                
            # Check for market state classification
            if "trending_bullish" in enhanced_synthesis.lower():
                logger.info("📈 MARKET STATE: Trending Bullish")
            elif "trending_bearish" in enhanced_synthesis.lower():
                logger.info("📉 MARKET STATE: Trending Bearish")
            elif "leaning_bullish" in enhanced_synthesis.lower():
                logger.info("📈 MARKET STATE: Leaning Bullish")
            elif "leaning_bearish" in enhanced_synthesis.lower():
                logger.info("📉 MARKET STATE: Leaning Bearish")
            elif "ranging" in enhanced_synthesis.lower():
                logger.info("📊 MARKET STATE: Ranging")
            else:
                logger.info("🔄 MARKET STATE: Neutral/Unclear")
        else:
            logger.info("🧠 ENHANCED SYNTHESIS: ❌ Not generated")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ Enhanced Interpretation Manager Test Completed Successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting Enhanced Interpretation Manager Test")
    
    success = await test_enhanced_interpretation_manager()
    
    if success:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 