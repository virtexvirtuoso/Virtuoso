#!/usr/bin/env python3
"""
Test script for generating and sending an enhanced market report with PDF attachment.

Usage: python test_enhanced_report.py [discord_webhook_url]
"""

import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='enhanced_report_test.log'
)
logger = logging.getLogger('enhanced_report_test')

async def generate_sample_market_data() -> Dict[str, Any]:
    """Generate sample market data for testing."""
    
    # Create a sample market report data structure
    market_data = {
        'timestamp': int(time.time() * 1000),
        'market_overview': {
            'total_market_cap': '$1.92T',
            'btc_dominance': '49.2%',
            'daily_volume': '$78.5B',
            'market_trend': 'Bullish',
            'volatility': 'Moderate',
            'risk_level': 'Medium'
        },
        'market_sentiment': {
            'overall_sentiment': 'Bullish',
            'fear_greed_index': 72,
            'social_sentiment': 'Positive',
            'institutional_activity': 'Accumulation',
            'futures_sentiment': 'Long-biased'
        },
        'top_performers': [
            {'symbol': 'ETH/USDT', 'price': 3245.78, 'change_percent': '+5.2%', 'volume': '$2.1B'},
            {'symbol': 'SOL/USDT', 'price': 132.45, 'change_percent': '+4.7%', 'volume': '$1.5B'},
            {'symbol': 'BNB/USDT', 'price': 447.32, 'change_percent': '+3.8%', 'volume': '$1.1B'},
            {'symbol': 'MATIC/USDT', 'price': 0.91, 'change_percent': '+3.5%', 'volume': '$325M'},
            {'symbol': 'AVAX/USDT', 'price': 34.56, 'change_percent': '+3.1%', 'volume': '$412M'}
        ],
        'underperformers': [
            {'symbol': 'DOGE/USDT', 'price': 0.142, 'change_percent': '-2.1%', 'volume': '$521M'},
            {'symbol': 'XRP/USDT', 'price': 0.587, 'change_percent': '-1.8%', 'volume': '$387M'},
            {'symbol': 'ADA/USDT', 'price': 0.398, 'change_percent': '-1.5%', 'volume': '$212M'}
        ],
        'trading_signals': [
            {'symbol': 'BTC/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '4h'},
            {'symbol': 'ETH/USDT', 'direction': 'Buy', 'strength': 'Moderate', 'timeframe': '1h'},
            {'symbol': 'SOL/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '1d'},
            {'symbol': 'XRP/USDT', 'direction': 'Sell', 'strength': 'Weak', 'timeframe': '4h'}
        ],
        'market_regime': {
            'current_regime': 'Bull Market',
            'trend_strength': 'Strong',
            'momentum_state': 'Bullish',
            'risk_regime': 'Risk-On'
        },
        'notable_news': [
            {
                'title': 'SEC Approves Spot Ethereum ETF Applications',
                'source': 'Bloomberg',
                'impact': 'Highly Bullish'
            },
            {
                'title': 'Federal Reserve Signals No Rate Hikes in Next Meeting',
                'source': 'Wall Street Journal',
                'impact': 'Moderately Bullish'
            },
            {
                'title': 'Major DeFi Protocol Launches New Token Staking Program',
                'source': 'CoinDesk',
                'impact': 'Neutral'
            }
        ],
        'smart_money_index': {
            'overall_score': 72.5,
            'institutional_flows': 'Positive',
            'whale_accumulation': 'Strong',
            'otc_activity': 'High'
        },
        'whale_activity': {
            'btc_whales': 'Accumulating',
            'eth_whales': 'Accumulating',
            'stablecoin_whales': 'Deploying',
            'significant_transactions': [
                {'amount': '12,500 BTC', 'from': 'Unknown', 'to': 'Exchange', 'timestamp': '2 hours ago'},
                {'amount': '95,000 ETH', 'from': 'Exchange', 'to': 'Unknown', 'timestamp': '4 hours ago'}
            ]
        },
        'defi_metrics': {
            'total_value_locked': '$48.7B',
            'daily_volume': '$5.2B',
            'top_protocol': 'Uniswap',
            'yield_farming_trend': 'Increasing'
        },
        'correlations': {
            'btc_sp500': 0.62,
            'btc_gold': -0.21,
            'btc_nasdaq': 0.78,
            'btc_dxy': -0.54
        },
        'key_levels': {
            'btc_support': ['$51,200', '$48,600', '$46,800'],
            'btc_resistance': ['$53,500', '$55,800', '$58,200'],
            'eth_support': ['$3,120', '$2,950', '$2,780'],
            'eth_resistance': ['$3,350', '$3,520', '$3,780']
        }
    }
    
    return market_data

async def format_enhanced_market_report(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the market data into a Discord webhook message with embeds.
    
    Args:
        market_data: The market data to format
    
    Returns:
        Discord webhook message with embeds
    """
    # Create a timestamp for the report
    timestamp = datetime.now().isoformat()
    
    # Create the Discord webhook message structure
    message = {
        "content": f"📊 **Market Summary Report** - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        "embeds": []
    }
    
    # Market overview embed
    overview_embed = {
        "title": "🌍 Market Overview",
        "color": 3447003,  # Blue
        "fields": []
    }
    
    # Add market overview data
    overview = market_data.get('market_overview', {})
    for key, value in overview.items():
        overview_embed["fields"].append({
            "name": key.replace('_', ' ').title(),
            "value": str(value),
                "inline": True
        })
    
    message["embeds"].append(overview_embed)
    
    # Market sentiment embed
    sentiment_embed = {
        "title": "🧠 Market Sentiment",
        "color": 15105570,  # Orange
        "fields": []
    }
    
    sentiment = market_data.get('market_sentiment', {})
    for key, value in sentiment.items():
        sentiment_embed["fields"].append({
            "name": key.replace('_', ' ').title(),
            "value": str(value),
                "inline": True
        })
    
    message["embeds"].append(sentiment_embed)
    
    # Top performers embed
    performers_embed = {
        "title": "🚀 Top Performers",
        "color": 5763719,  # Green
        "description": "Best performing assets in the last 24 hours"
    }
    
    performers = market_data.get('top_performers', [])
    performers_text = ""
    for performer in performers:
        symbol = performer.get('symbol', 'N/A')
        price = performer.get('price', 'N/A')
        change = performer.get('change_percent', 'N/A')
        volume = performer.get('volume', 'N/A')
        performers_text += f"**{symbol}** • {price} • {change} • Vol: {volume}\n"
    
    performers_embed["description"] = performers_text
    message["embeds"].append(performers_embed)
    
    # Trading signals embed
    signals_embed = {
        "title": "📈 Trading Signals",
        "color": 10181046,  # Purple
        "fields": []
    }
    
    signals = market_data.get('trading_signals', [])
    signals_text = ""
    for signal in signals:
        symbol = signal.get('symbol', 'N/A')
        direction = signal.get('direction', 'N/A')
        strength = signal.get('strength', 'N/A')
        timeframe = signal.get('timeframe', 'N/A')
        
        # Add emoji based on direction
        emoji = "🟢" if direction.lower() == "buy" else "🔴"
        signals_text += f"{emoji} **{symbol}** • {direction} • {strength} • {timeframe}\n"
    
    signals_embed["description"] = signals_text
    message["embeds"].append(signals_embed)
    
    # Notable news embed
    if 'notable_news' in market_data:
        news_embed = {
            "title": "📰 Notable News",
            "color": 15844367,  # Gold
            "fields": []
        }
        
        news_items = market_data.get('notable_news', [])
        for item in news_items:
            title = item.get('title', 'N/A')
            source = item.get('source', 'N/A')
            impact = item.get('impact', 'N/A')
            
            # Add colored circle based on impact
            if 'bullish' in impact.lower():
                impact_emoji = "🟢"
            elif 'bearish' in impact.lower():
                impact_emoji = "🔴"
            else:
                impact_emoji = "⚪"
            
            news_embed["fields"].append({
                "name": f"{impact_emoji} {title}",
                "value": f"Source: {source} | Impact: {impact}",
                            "inline": False
            })
        
        message["embeds"].append(news_embed)
    
    # Footer for all embeds
    footer = {
        "text": "Generated by Virtuoso Trading System",
        "icon_url": "https://example.com/icon.png"  # Replace with your icon URL
    }
    
    # Add footer to all embeds
    for embed in message["embeds"]:
        embed["footer"] = footer
        embed["timestamp"] = timestamp
    
    return message

async def test_enhanced_market_report(webhook_url: Optional[str] = None):
    """
    Test generating and sending an enhanced market report with PDF attachment.
    
    Args:
        webhook_url: Discord webhook URL to use for testing
    """
    # Use provided webhook URL or get from environment
    if not webhook_url:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        logger.error("Discord webhook URL not provided")
        print("Error: Discord webhook URL not provided.")
        print("Please set with: export DISCORD_WEBHOOK_URL='your_webhook_url'")
        print("Or pass as argument: python test_enhanced_report.py 'your_webhook_url'")
        sys.exit(1)
    
    try:
        # Import required modules
        sys.path.append('.')
        from src.monitoring.alert_manager import AlertManager
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Starting enhanced market report test")
        
        # Create minimal config
        config = {
            'monitoring': {
                'discord': {
                    'webhook_url': webhook_url,
                    'enabled': True
                },
                'alerts': {
                    'handlers': ['discord'],
                    'levels': ['info', 'warning', 'error']
                }
            }
        }
        
        # Initialize AlertManager
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config)
        await alert_manager.start()
        
        # Initialize ReportManager
        logger.info("Initializing ReportManager")
        report_manager = ReportManager()
        
        # Generate sample market data
        logger.info("Generating sample market data")
        market_data = await generate_sample_market_data()
        
        # Format the enhanced market report for Discord
        logger.info("Formatting enhanced market report for Discord")
        formatted_report = await format_enhanced_market_report(market_data)
        
        # Save the formatted report to JSON for reference
        logger.info("Saving formatted report to JSON")
        with open('enhanced_report.json', 'w') as f:
            json.dump(formatted_report, f, indent=2)
        
        # Save the market data to JSON for reference
        logger.info("Saving market data to JSON")
        with open('enhanced_market_report.json', 'w') as f:
            json.dump(market_data, f, indent=2)
        
        # Generate PDF report using ReportManager
        logger.info("Generating PDF report")
        
        # Create an exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Generate timestamp for filename
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"market_report_{timestamp_str}.pdf"
        pdf_path = os.path.join('exports', pdf_filename)
        
        # Generate the PDF report
        success, pdf_path, json_path = await report_manager.generate_and_attach_report(
            signal_data=market_data,
            webhook_message=formatted_report,
            webhook_url=webhook_url,
            signal_type='market_report',
            output_path=pdf_path
        )
        
        if success:
            logger.info(f"Successfully generated PDF report: {pdf_path}")
            
            # Add note about attached files to the message content
            if 'content' not in formatted_report:
                formatted_report['content'] = ""
                
            formatted_report['content'] += "\n\n📑 PDF report attached | 📊 JSON data attached"
            
            # Send the enhanced report to Discord
            logger.info("Sending enhanced report to Discord")
            success, response = await alert_manager.send_discord_webhook_message(formatted_report)
            
            if success:
                logger.info("Successfully sent enhanced report to Discord")
                print("Enhanced market report with PDF attachment sent successfully!")
            else:
                logger.error(f"Failed to send enhanced report to Discord: {response}")
                print(f"Error sending enhanced report to Discord: {response}")
        else:
            logger.error("Failed to generate PDF report")
            print("Error: Failed to generate PDF report")
        
        # Clean up
        await alert_manager.stop()
        await report_manager.stop()
        logger.info("Test completed")
                
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Check if webhook URL provided as argument
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run the test
    asyncio.run(test_enhanced_market_report(webhook_url)) 