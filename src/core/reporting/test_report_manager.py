#!/usr/bin/env python3
"""
Test script for ReportManager class.

This script demonstrates how to use the ReportManager to generate PDF reports
and attach them to Discord messages.
"""

import os
import sys
import json
import logging
import random
import pandas as pd
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))))

from src.core.reporting.report_manager import ReportManager


def create_sample_signal_data():
    """Create sample trading signal data for testing."""
    return {
        'symbol': 'ETHUSDT',
        'score': 68.2,
        'reliability': 0.92,
        'price': 3245.75,
        'timestamp': datetime.now(),
        'components': {
            'RSI': {'score': 76, 'impact': 2.8, 'interpretation': 'Approaching overbought levels but still has room to grow'},
            'MACD': {'score': 65, 'impact': 2.2, 'interpretation': 'Recent bullish crossover with histogram expanding'},
            'Bollinger Bands': {'score': 72, 'impact': 2.0, 'interpretation': 'Price moving above middle band with bands expanding'},
            'Volume': {'score': 58, 'impact': 1.3, 'interpretation': 'Volume increasing but below recent average'},
            'Moving Averages': {'score': 74, 'impact': 2.8, 'interpretation': 'All short-term MAs above long-term, bullish alignment'},
            'Support/Resistance': {'score': 70, 'impact': 1.8, 'interpretation': 'Successfully retested previous resistance as support'},
            'Ichimoku Cloud': {'score': 68, 'impact': 1.6, 'interpretation': 'Price trading above the cloud with bullish cross'},
            'Fibonacci': {'score': 62, 'impact': 1.2, 'interpretation': 'Retracement to 0.618 level complete, resuming uptrend'}
        },
        'insights': [
            'Ethereum showing strong momentum with multiple indicators confirming',
            'Accumulation pattern forming with higher lows over the past week',
            'Institutional interest increasing based on options data',
            'ETH/BTC ratio improving, showing relative strength'
        ],
        'actionable_insights': [
            'Consider buying dips near the $3150 support zone',
            'Set stop loss below recent consolidation at $3000',
            'First take profit target at previous high of $3400',
            'Monitor gas fees and network activity for confirmation of usage uptick'
        ],
        'entry_price': 3245.75,
        'stop_loss': 3000.00,
        'targets': [
            {'name': 'Target 1', 'price': 3400.00, 'size': 40},
            {'name': 'Target 2', 'price': 3600.00, 'size': 35},
            {'name': 'Target 3', 'price': 3800.00, 'size': 25}
        ],
        'signal_type': 'BULLISH'
    }


def create_sample_ohlcv_data(symbol='ETHUSDT', periods=60):
    """Create sample OHLCV price data for testing."""
    base_price = 3000
    volatility = 0.02
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods/24)  # Assuming hourly data
    
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # Initialize with random price movements
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [base_price * (1 + random.uniform(-volatility/2, volatility/2)) for _ in range(periods)],
        'close': [base_price * (1 + random.uniform(-volatility/2, volatility/2)) for _ in range(periods)]
    })
    
    # Add high and low values
    for i in range(periods):
        if df.loc[i, 'open'] > df.loc[i, 'close']:
            df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + random.uniform(0, volatility/4))
            df.loc[i, 'low'] = df.loc[i, 'close'] * (1 - random.uniform(0, volatility/4))
        else:
            df.loc[i, 'high'] = df.loc[i, 'close'] * (1 + random.uniform(0, volatility/4))
            df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - random.uniform(0, volatility/4))
    
    # Generate random volume
    df['volume'] = [random.uniform(1000, 5000) for _ in range(periods)]
    
    # Make data more realistic with a trend
    # Simulate a consolidation followed by a breakout in the last 20% of data
    trend_start = int(periods * 0.8)
    
    # Create a more realistic price path
    for i in range(1, periods):
        if i < trend_start:
            # Consolidation with small movements around base price
            change = random.uniform(-0.005, 0.005)
            df.loc[i, 'close'] = df.loc[i-1, 'close'] * (1 + change)
            df.loc[i, 'open'] = df.loc[i-1, 'close']
        else:
            # Bullish trend in the last periods
            change = random.uniform(0.002, 0.012)  # Stronger upward bias
            df.loc[i, 'close'] = df.loc[i-1, 'close'] * (1 + change)
            df.loc[i, 'open'] = df.loc[i-1, 'close'] * (1 + random.uniform(-0.003, 0.005))
            df.loc[i, 'volume'] = df.loc[i-1, 'volume'] * (1 + random.uniform(0, 0.25))  # Increasing volume during breakout
    
    # Recalculate high and low based on open/close
    for i in range(periods):
        price_range = abs(df.loc[i, 'close'] - df.loc[i, 'open']) * 1.5
        if df.loc[i, 'open'] > df.loc[i, 'close']:  # Bearish candle
            df.loc[i, 'high'] = df.loc[i, 'open'] + price_range * random.uniform(0.1, 0.5)
            df.loc[i, 'low'] = df.loc[i, 'close'] - price_range * random.uniform(0.1, 0.5)
        else:  # Bullish candle
            df.loc[i, 'high'] = df.loc[i, 'close'] + price_range * random.uniform(0.1, 0.5)
            df.loc[i, 'low'] = df.loc[i, 'open'] - price_range * random.uniform(0.1, 0.5)
    
    # Ensure the last price matches the signal price
    df.loc[periods-1, 'close'] = 3245.75
    
    return df


def create_discord_message(signal_data):
    """Create a sample Discord message with the signal data."""
    # Determine color based on signal type
    if signal_data.get('signal_type', '').upper() == 'BULLISH':
        color = 0x4CAF50  # Green
        emoji = "💹"
    elif signal_data.get('signal_type', '').upper() == 'BEARISH':
        color = 0xF44336  # Red
        emoji = "📉"
    else:
        color = 0xFFC107  # Amber/yellow for neutral
        emoji = "📊"
    
    # Calculate risk/reward ratio
    entry = signal_data.get('entry_price', 0)
    stop = signal_data.get('stop_loss', 0)
    target1 = signal_data.get('targets', [{'price': 0}])[0].get('price', 0)
    
    if entry and stop and target1 and entry != stop:
        risk = entry - stop if entry > stop else stop - entry
        reward = target1 - entry if target1 > entry else entry - target1
        risk_reward = f"1:{abs(reward/risk):.1f}" if risk else "N/A"
    else:
        risk_reward = "N/A"
    
    # Create Discord message with embed
    return {
        'content': f"🚨 **New Trading Signal Detected!**",
        'embeds': [{
            'title': f"{emoji} {signal_data['symbol']}: {signal_data.get('signal_type', 'SIGNAL')} (Score: {signal_data['score']})",
            'description': signal_data.get('insights', [""])[0],
            'color': color,
            'fields': [
                {
                    'name': "Current Price",
                    'value': f"${signal_data['price']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Reliability",
                    'value': f"{signal_data['reliability']*100:.0f}%",
                    'inline': True
                },
                {
                    'name': "Entry Price",
                    'value': f"${signal_data['entry_price']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Stop Loss",
                    'value': f"${signal_data['stop_loss']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Target 1",
                    'value': f"${signal_data['targets'][0]['price']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Risk/Reward",
                    'value': risk_reward,
                    'inline': True
                }
            ],
            'footer': {
                'text': f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} • Virtuoso Crypto"
            }
        }]
    }


def main():
    """Main test function for the ReportManager."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create ReportManager instance
    report_manager = ReportManager()
    
    # Get sample data
    signal_data = create_sample_signal_data()
    
    # Add custom watermark (optional)
    signal_data['watermark_text'] = "VIRTUOSO CRYPTO • CONFIDENTIAL"
    
    ohlcv_data = create_sample_ohlcv_data(symbol=signal_data['symbol'])
    webhook_message = create_discord_message(signal_data)
    
    # Get webhook URL from environment or use a test URL
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        print("⚠️ No webhook URL found. Set the DISCORD_WEBHOOK_URL environment variable.")
        print("🔍 Generating reports locally without sending...")
        
        # Generate reports without sending
        success, pdf_path, json_path = report_manager.generate_and_send_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            webhook_url=None  # This will prevent sending
        )
    else:
        print(f"Using webhook URL: {webhook_url[:30]}..." if webhook_url else "No webhook URL provided")
        
        # Generate and send report with message
        success, pdf_path, json_path = report_manager.sync_send_report_with_message(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            webhook_message=webhook_message,
            webhook_url=webhook_url
        )
    
    # Report results
    if success:
        print("✅ Operation completed successfully!")
        print(f"📄 PDF report: {pdf_path}")
        print(f"📊 JSON data: {json_path}")
        
        # Print JSON data for inspection
        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
                print("\n📝 JSON data preview:")
                print(json.dumps(json_data, indent=2)[:500] + "...\n")
            except Exception as e:
                print(f"❌ Error reading JSON file: {str(e)}")
    else:
        print("❌ Operation failed. Check logs for details.")


if __name__ == "__main__":
    main() 