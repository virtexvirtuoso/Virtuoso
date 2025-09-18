#!/usr/bin/env python3
"""
Test chart generation for signal alerts
Tests the full flow from signal creation to chart generation
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime, timedelta
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitoring.alert_manager import AlertManager
from src.core.reporting.pdf_generator import ReportGenerator
from src.utils.config import load_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def generate_sample_ohlcv_data(symbol="ENAUSDT", num_candles=100):
    """Generate realistic OHLCV data for testing"""
    logger.info(f"Generating sample OHLCV data for {symbol}")

    # Start price around the mentioned price
    base_price = 0.70610
    ohlcv_data = []

    current_time = datetime.now()

    for i in range(num_candles):
        # Generate realistic price movement
        volatility = 0.002  # 0.2% volatility
        trend = 0.00001 * (i - 50)  # Slight trend

        open_price = base_price + np.random.normal(0, volatility) + trend
        close_price = open_price + np.random.normal(0, volatility/2)

        # High and low based on open/close
        high_price = max(open_price, close_price) + abs(np.random.normal(0, volatility/3))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, volatility/3))

        # Volume
        volume = 1000000 + np.random.normal(0, 100000)

        # Timestamp (5-minute candles going back)
        timestamp = current_time - timedelta(minutes=5 * (num_candles - i))

        ohlcv_data.append({
            'timestamp': int(timestamp.timestamp() * 1000),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

        # Update base price for next candle
        base_price = close_price

    return ohlcv_data

async def test_chart_generation():
    """Test the chart generation pipeline"""

    logger.info("=" * 60)
    logger.info("Testing Chart Generation for Signal Alerts")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

    # Initialize components
    logger.info("Initializing Alert Manager and PDF Generator...")
    alert_manager = AlertManager(config)

    # Check if PDF generator is available
    if not alert_manager.pdf_generator:
        logger.error("❌ PDF Generator not initialized in Alert Manager")
        logger.info("Attempting direct initialization...")

        try:
            pdf_generator = ReportGenerator(config)
            logger.info("✅ PDF Generator initialized directly")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PDF Generator: {e}")
            return
    else:
        pdf_generator = alert_manager.pdf_generator
        logger.info("✅ PDF Generator available from Alert Manager")

    # Generate sample OHLCV data
    symbol = "ENAUSDT"
    ohlcv_data = await generate_sample_ohlcv_data(symbol)
    logger.info(f"✅ Generated {len(ohlcv_data)} candles of OHLCV data")

    # Create sample signal data matching the alert format
    signal_data = {
        'symbol': symbol,
        'signal_type': 'BUY',
        'confluence_score': 57.67,
        'price': 0.70610,
        'entry_price': 0.70610,
        'stop_loss': 0.69200,  # ~2% below entry
        'targets': [0.71500, 0.72400, 0.73300],  # Progressive targets
        'ohlcv_data': ohlcv_data,
        'transaction_id': '02b3f075-c965-41f6-ba41-6751fb447b0b',
        'signal_id': '764304d5',
        'alert_id': '9718dc5f',
        'timestamp': datetime.now().isoformat(),
        'trade_params': {
            'entry_price': 0.70610,
            'stop_loss': 0.69200,
            'targets': [0.71500, 0.72400, 0.73300],
            'position_size': 0.02,  # 2% of portfolio
            'risk_reward_ratio': 2.5
        },
        'components': {
            'orderflow': {'score': 55, 'signal': 'neutral'},
            'orderbook': {'score': 60, 'signal': 'bullish'},
            'volume': {'score': 58, 'signal': 'neutral'},
            'price_structure': {'score': 62, 'signal': 'bullish'},
            'technical': {'score': 54, 'signal': 'neutral'},
            'sentiment': {'score': 56, 'signal': 'neutral'}
        }
    }

    logger.info(f"📊 Testing chart generation for {symbol}")
    logger.info(f"   Signal: {signal_data['signal_type']}")
    logger.info(f"   Confluence: {signal_data['confluence_score']}/100")
    logger.info(f"   Price: ${signal_data['price']:.5f}")

    # Test chart generation through alert manager
    if hasattr(alert_manager, '_generate_chart_from_signal_data'):
        logger.info("\n🧪 Testing Alert Manager chart generation...")

        try:
            chart_path = await alert_manager._generate_chart_from_signal_data(
                signal_data,
                signal_data['transaction_id'],
                signal_data['signal_id']
            )

            if chart_path and os.path.exists(chart_path):
                file_size = os.path.getsize(chart_path) / 1024  # KB
                logger.info(f"✅ Chart generated successfully!")
                logger.info(f"   Path: {chart_path}")
                logger.info(f"   Size: {file_size:.2f} KB")
            else:
                logger.warning("⚠️ Chart generation returned no path or file doesn't exist")

        except Exception as e:
            logger.error(f"❌ Chart generation failed: {e}")
            import traceback
            traceback.print_exc()

    # Test direct chart generation methods
    logger.info("\n🧪 Testing direct chart generation methods...")

    # Create output directory
    chart_dir = os.path.join(os.getcwd(), 'reports', 'charts', 'test')
    os.makedirs(chart_dir, exist_ok=True)

    # Test candlestick chart
    if hasattr(pdf_generator, '_create_candlestick_chart'):
        logger.info("Testing _create_candlestick_chart...")

        try:
            chart_path = pdf_generator._create_candlestick_chart(
                symbol=symbol,
                ohlcv_data=ohlcv_data,
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                targets=signal_data['targets'],
                output_dir=chart_dir
            )

            if chart_path and os.path.exists(chart_path):
                file_size = os.path.getsize(chart_path) / 1024
                logger.info(f"✅ Candlestick chart created!")
                logger.info(f"   Path: {chart_path}")
                logger.info(f"   Size: {file_size:.2f} KB")
            else:
                logger.warning("⚠️ Candlestick chart not created")

        except Exception as e:
            logger.error(f"❌ Candlestick chart failed: {e}")

    # Test simulated chart (fallback when no OHLCV)
    if hasattr(pdf_generator, '_create_simulated_chart'):
        logger.info("\nTesting _create_simulated_chart (fallback)...")

        try:
            chart_path = pdf_generator._create_simulated_chart(
                symbol=symbol,
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                targets=signal_data['targets'],
                output_dir=chart_dir
            )

            if chart_path and os.path.exists(chart_path):
                file_size = os.path.getsize(chart_path) / 1024
                logger.info(f"✅ Simulated chart created!")
                logger.info(f"   Path: {chart_path}")
                logger.info(f"   Size: {file_size:.2f} KB")
            else:
                logger.warning("⚠️ Simulated chart not created")

        except Exception as e:
            logger.error(f"❌ Simulated chart failed: {e}")

    # Test sending alert with chart
    logger.info("\n🚀 Testing full alert flow with chart...")

    if alert_manager.discord_webhook_url:
        logger.info("Discord webhook configured, preparing test alert...")

        # Create alert data
        alert_data = {
            'type': 'signal',
            'severity': 'info',
            'symbol': symbol,
            'signal_type': signal_data['signal_type'],
            'confluence_score': signal_data['confluence_score'],
            'price': signal_data['price'],
            'signal_data': signal_data,
            'message': f"TEST: {signal_data['signal_type']} Signal for {symbol}",
            'transaction_id': signal_data['transaction_id'],
            'signal_id': signal_data['signal_id']
        }

        logger.info("Sending test alert to Discord...")
        # Note: Commenting out actual send to avoid spam
        # await alert_manager.send_alert(alert_data)
        logger.info("⚠️ Alert send commented out to avoid Discord spam")
        logger.info("   Uncomment line in script to test actual webhook")
    else:
        logger.warning("⚠️ No Discord webhook configured")

    logger.info("\n" + "=" * 60)
    logger.info("Chart Generation Test Complete!")
    logger.info("=" * 60)

    # List generated charts
    if os.path.exists(chart_dir):
        charts = [f for f in os.listdir(chart_dir) if f.endswith('.png')]
        if charts:
            logger.info(f"\n📁 Generated charts in {chart_dir}:")
            for chart in charts:
                logger.info(f"   - {chart}")
        else:
            logger.info("\n⚠️ No charts were generated")

async def main():
    """Main entry point"""
    try:
        await test_chart_generation()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())