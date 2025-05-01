#!/usr/bin/env python3
"""
Test script to send a market report alert to Discord with PDF attachment only.

Usage: python test_discord_alert.py [discord_webhook_url]
"""

import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_alert_test')

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
            {'symbol': 'BNB/USDT', 'price': 447.32, 'change_percent': '+3.8%', 'volume': '$1.1B'}
        ],
        'trading_signals': [
            {'symbol': 'BTC/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '4h'},
            {'symbol': 'ETH/USDT', 'direction': 'Buy', 'strength': 'Moderate', 'timeframe': '1h'},
            {'symbol': 'SOL/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '1d'}
        ],
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
            }
        ]
    }
    
    return market_data

async def format_market_report_for_discord(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the market data into a Discord webhook message with embeds following the MarketReporter format.
    
    Args:
        market_data: The market data to format
    
    Returns:
        Discord webhook message with embeds
    """
    # Create a timestamp for the report
    utc_now = datetime.now()
    timestamp = utc_now.isoformat() + 'Z'
    
    # Virtuoso branding
    virtuoso_logo_url = "https://example.com/icon.png"  # Replace with your logo URL
    dashboard_base_url = "https://virtuoso.internal-dashboard.com"
    
    # Create the Discord webhook message structure
    message = {
        "content": f"📊 **Market Summary Report** - {utc_now.strftime('%Y-%m-%d %H:%M UTC')}",
        "embeds": []
    }
    
    # --- Market Overview Embed (Blue) ---
    overview = market_data.get('market_overview', {})
    market_desc = (
        f"**Global Market Overview | {utc_now.strftime('%B %d, %Y')}**\n\n"
        f"{'📈' if overview.get('market_trend', '') == 'Bullish' else '📉'} "
        f"BTC 24h: **{overview.get('btc_dominance', '0.0')}%** | "
        f"💰 Vol: **${overview.get('daily_volume', '0')}** | "
        f"📊 BTC Dom: **{overview.get('btc_dominance', '0.0')}%**"
    )
    
    overview_embed = {
        "title": "🌍 Market Overview",
        "color": 3447003,  # Blue
        "url": f"{dashboard_base_url}/overview",
        "description": market_desc,
        "fields": []
    }
    
    # Add fields for Market Overview
    overview_embed["fields"].append({
        "name": "💪 Strength",
        "value": f"**{overview.get('strength', '0')}%**\n{overview.get('market_trend', 'Neutral')}",
        "inline": True
    })
    
    overview_embed["fields"].append({
        "name": "📊 Volatility",
        "value": f"**{overview.get('volatility', '0')}%**\nNormal",
        "inline": True
    })
    
    overview_embed["fields"].append({
        "name": "💧 Liquidity",
        "value": f"**{overview.get('liquidity', '0')}**\n{'High' if int(overview.get('liquidity', 0)) > 75 else 'Medium' if int(overview.get('liquidity', 0)) > 50 else 'Low'}",
        "inline": True
    })
    
    # Add Risk Level field
    overview_embed["fields"].append({
        "name": "⚠️ Risk Level",
        "value": f"**{overview.get('risk_level', 'Medium')}**",
        "inline": True
    })
    
    # Add Footer
    overview_embed["footer"] = {
        "text": f"Virtuoso Trading System | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
        "icon_url": virtuoso_logo_url
    }
    overview_embed["timestamp"] = timestamp
    
    message["embeds"].append(overview_embed)
    
    # --- Top Performers Embed (Green) ---
    performers = market_data.get('top_performers', [])
    performers_text = ""
    for performer in performers:
        symbol = performer.get('symbol', 'N/A')
        price = performer.get('price', 'N/A')
        change = performer.get('change_percent', 'N/A')
        volume = performer.get('volume', 'N/A')
        performers_text += f"**{symbol}** • ${price} • {change} • Vol: {volume}\n"
    
    performers_embed = {
        "title": "🚀 Top Performers",
        "color": 5763719,  # Green
        "url": f"{dashboard_base_url}/markets",
        "description": performers_text or "No data available",
        "fields": [],
        "footer": {
            "text": f"Virtuoso Trading System | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
            "icon_url": virtuoso_logo_url
        },
        "timestamp": timestamp
    }
    
    message["embeds"].append(performers_embed)
    
    # --- Trading Signals Embed (Purple) ---
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
    
    signals_embed = {
        "title": "📈 Trading Signals",
        "color": 10181046,  # Purple
        "url": f"{dashboard_base_url}/signals",
        "description": signals_text or "No signals available",
        "fields": [],
        "footer": {
            "text": f"Virtuoso Trading System | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
            "icon_url": virtuoso_logo_url
        },
        "timestamp": timestamp
    }
    
    message["embeds"].append(signals_embed)
    
    # --- Notable News Embed (Yellow) ---
    news_items = market_data.get('notable_news', [])
    if news_items:
        news_text = ""
        for item in news_items:
            title = item.get('title', 'N/A')
            source = item.get('source', 'N/A')
            impact = item.get('impact', 'N/A')
            
            # Add emoji based on impact
            emoji = "🟢" if "bullish" in impact.lower() else "🔴" if "bearish" in impact.lower() else "⚪"
            news_text += f"{emoji} **{title}**\n   Source: {source} | Impact: {impact}\n\n"
        
        news_embed = {
            "title": "📰 Notable News",
            "color": 16776960,  # Yellow
            "url": f"{dashboard_base_url}/news",
            "description": news_text or "No news available",
            "fields": [],
            "footer": {
                "text": f"Virtuoso Trading System | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
                "icon_url": virtuoso_logo_url
            },
            "timestamp": timestamp
        }
        
        message["embeds"].append(news_embed)
    
    return message

async def test_discord_alert(webhook_url: Optional[str] = None):
    """
    Test sending a market report alert to Discord with PDF attachment only.
    
    Args:
        webhook_url: Discord webhook URL to use for testing
    """
    # Use provided webhook URL or get from environment
    if not webhook_url:
        # Try different environment variable names that might contain the webhook URL
        webhook_url = (
            os.environ.get('DISCORD_WEBHOOK_URL') or 
            os.environ.get('DISCORD_WEBHOOK') or 
            os.environ.get('DISCORD_WEBHOOK_URL_VIRTUOSO') or
            os.environ.get('DISCORD_NETWORK_WEBHOOK')
        )
        
        if webhook_url:
            logger.info(f"Found Discord webhook URL in environment variable: {webhook_url[:20]}...")
    
    if not webhook_url:
        logger.error("Discord webhook URL not provided")
        print("Error: Discord webhook URL not provided.")
        print("Please set with one of these environment variables:")
        print("  export DISCORD_WEBHOOK_URL='your_webhook_url'")
        print("  export DISCORD_WEBHOOK='your_webhook_url'")
        print("  export DISCORD_WEBHOOK_URL_VIRTUOSO='your_webhook_url'")
        print("  export DISCORD_NETWORK_WEBHOOK='your_webhook_url'")
        print("Or pass as argument: python test_discord_alert.py 'your_webhook_url'")
        sys.exit(1)
    
    try:
        # Import required modules
        sys.path.append('.')
        from src.monitoring.alert_manager import AlertManager
        from src.core.reporting.report_manager import ReportManager
        from src.core.reporting.pdf_generator import ReportGenerator
        
        logger.info("Starting Discord alert test")
        
        # Create minimal config with the webhook URL
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
        
        # Initialize AlertManager with the webhook URL
        logger.info("Initializing AlertManager with webhook URL")
        alert_manager = AlertManager(config)
        await alert_manager.start()
        
        # Initialize ReportManager
        logger.info("Initializing ReportManager")
        report_manager = ReportManager()
        await report_manager.start()
        
        # Generate sample market data
        logger.info("Generating sample market data")
        market_data = await generate_sample_market_data()
        
        # Format the market report for Discord
        logger.info("Formatting market report for Discord")
        formatted_report = await format_market_report_for_discord(market_data)
        
        # Create an exports directory if it doesn't exist
        exports_dir = 'exports'
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"discord_alert_{timestamp_str}.pdf"
        pdf_path = os.path.join(exports_dir, pdf_filename)
        
        # Generate the PDF report
        logger.info(f"Generating PDF report at path: {pdf_path}")
        
        try:
            # Create a ReportGenerator instance directly
            report_generator = ReportGenerator()
            
            # Generate the PDF market report
            await report_generator.generate_market_html_report(
                market_data=market_data,
                output_path=pdf_path
            )
            
            # Check if PDF file was created successfully
            if os.path.exists(pdf_path):
                logger.info(f"Successfully generated PDF report: {pdf_path}")
                pdf_file_size = os.path.getsize(pdf_path)
                logger.info(f"PDF file size: {pdf_file_size} bytes")
                
                # Initialize content if not present
                if 'content' not in formatted_report:
                    formatted_report['content'] = ""
                
                # Only mention PDF attachment
                formatted_report['content'] += "\n\n📑 PDF report attached"
                
                # Set up files list with only the PDF
                files = [{
                    'path': pdf_path,
                    'filename': os.path.basename(pdf_path),
                    'description': "Market Report PDF"
                }]
                
                logger.info(f"Added PDF file to attachment list: {pdf_path}")
                
                # Send the market report to Discord
                logger.info(f"Sending market report to Discord with PDF attachment")
                send_success, response = await alert_manager.send_discord_webhook_message(formatted_report, files)
                
                if send_success:
                    logger.info("Successfully sent market report to Discord")
                    print("Market report with PDF attachment sent successfully to Discord!")
                    print(f"PDF: {pdf_path}")
                else:
                    logger.error(f"Failed to send market report to Discord: {response}")
                    print(f"Error sending market report to Discord: {response}")
            else:
                logger.error(f"PDF file not found at {pdf_path}")
                print(f"Error: PDF file not found at {pdf_path}")
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}", exc_info=True)
            print(f"Error generating PDF report: {e}")
        
        # Clean up
        await alert_manager.stop()
        await report_manager.stop()
        logger.info("Test completed")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if webhook URL provided as argument
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run the test
    asyncio.run(test_discord_alert(webhook_url)) 