#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify market report feature with Discord alerts and PDF generation using mock market data.
This script generates synthetic market data to test the PDF generation and Discord alert functionality.
"""

import os
import sys
import time
import json
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_market_report_mock")

# Ensure the current directory is in the path for imports
sys.path.append('.')

def generate_mock_market_data() -> Dict[str, Any]:
    """Generate mock market data for testing purposes that matches the real format."""
    timestamp = int(time.time() * 1000)
    
    # Create mock market overview
    market_overview = {
        'regime': random.choice(['BULLISH', 'BEARISH', 'NEUTRAL', 'RANGING']),
        'trend_strength': f"{random.uniform(30, 110):.1f}%",
        'volatility': random.uniform(0.2, 8.5),
        'volatility_classification': random.choice(['Low', 'Normal', 'High', 'Extreme']),
        'total_volume': random.uniform(5e9, 50e9),
        'total_turnover': random.uniform(3e9, 30e9),
        'daily_change': random.uniform(-5, 5),
        'btc_dominance': f"{random.uniform(40, 60):.1f}%",
        'liquidity_score': random.uniform(0, 100),
        'liquidity_classification': random.choice(['Low', 'Medium', 'High']),
        'momentum': random.choice(['INCREASING', 'DECREASING', 'FLAT']),
        'btc_support': random.uniform(59000, 62000),
        'btc_resistance': random.uniform(63000, 68000),
        'sentiment': random.choice(['Bullish', 'Bearish', 'Neutral']),
        'market_flows': random.choice([
            "Institutional inflows observed in BTC and ETH",
            "Retail outflows seen across most altcoins",
            "Balanced flows with no significant direction",
            "No flow data available"
        ])
    }
    
    # Create mock smart money index
    smart_money_index = {
        'index': random.uniform(30, 70),
        'sentiment': random.choice(['BULLISH', 'BEARISH', 'NEUTRAL']),
        'institutional_flow': f"{random.uniform(-3, 3):.1f}%",
        'otc_volume': random.uniform(1000, 5000),
        'futures_premium': random.uniform(-0.5, 2.5),
        'futures_premium_classification': random.choice(['Low', 'Normal', 'High']),
        'funding_rates': random.uniform(-0.1, 0.1),
        'funding_rates_classification': random.choice(['Negative', 'Neutral', 'Positive']),
        'key_zones': [
            {
                'symbol': 'BTC/USDT',
                'type': 'accumulation' if random.random() > 0.5 else 'distribution',
                'strength': random.uniform(50, 90),
                'buy_volume': random.uniform(500, 2000),
                'sell_volume': random.uniform(300, 1500)
            },
            {
                'symbol': 'ETH/USDT',
                'type': 'accumulation' if random.random() > 0.5 else 'distribution',
                'strength': random.uniform(40, 85),
                'buy_volume': random.uniform(2000, 8000),
                'sell_volume': random.uniform(1500, 6000)
            }
        ]
    }
    
    # Create mock futures premium data
    futures_premium = {
        'average_premium': f"{random.uniform(-1, 3):.2f}%",
        'contango_status': random.choice(['Normal Contango', 'Steep Contango', 'Backwardation', 'Flat']),
        'data': [
            {
                'symbol': 'BTC-PERP',
                'spot_price': random.uniform(60000, 65000),
                'futures_price': random.uniform(60000, 66000),
                'premium_percent': random.uniform(-0.5, 3)
            },
            {
                'symbol': 'ETH-PERP',
                'spot_price': random.uniform(2900, 3200),
                'futures_price': random.uniform(2900, 3300),
                'premium_percent': random.uniform(-0.5, 3.5)
            }
        ]
    }
    
    # Create mock whale activity data
    whale_activity = {
        'has_significant_activity': True,
        'significant_activity': {
            'BTC/USDT': {
                'net_whale_volume': random.uniform(-500, 500),
                'usd_value': random.uniform(-25000000, 25000000),
                'transaction_count': random.randint(5, 20)
            },
            'ETH/USDT': {
                'net_whale_volume': random.uniform(-2000, 2000),
                'usd_value': random.uniform(-15000000, 15000000),
                'transaction_count': random.randint(10, 30)
            },
            'SOL/USDT': {
                'net_whale_volume': random.uniform(-10000, 10000),
                'usd_value': random.uniform(-8000000, 8000000),
                'transaction_count': random.randint(5, 15)
            }
        },
        'large_transactions': [
            {
                'symbol': 'BTC/USDT',
                'usd_value': random.uniform(5000000, 20000000) * (1 if random.random() > 0.5 else -1),
                'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 12))).strftime("%H:%M:%S"),
                'exchange': random.choice(['Binance', 'Coinbase', 'Bybit', 'OKX'])
            },
            {
                'symbol': 'ETH/USDT',
                'usd_value': random.uniform(3000000, 10000000) * (1 if random.random() > 0.5 else -1),
                'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 12))).strftime("%H:%M:%S"),
                'exchange': random.choice(['Binance', 'Coinbase', 'Bybit', 'OKX'])
            },
            {
                'symbol': 'SOL/USDT',
                'usd_value': random.uniform(1000000, 5000000) * (1 if random.random() > 0.5 else -1),
                'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 12))).strftime("%H:%M:%S"),
                'exchange': random.choice(['Binance', 'Coinbase', 'Bybit', 'OKX'])
            }
        ]
    }
    
    # Create mock top performers
    top_performers = []
    symbols = ['SOL/USDT', 'AVAX/USDT', 'MATIC/USDT', 'DOT/USDT', 'ADA/USDT', 'LINK/USDT', 'XRP/USDT', 'BNB/USDT']
    for symbol in random.sample(symbols, 5):
        top_performers.append({
            'symbol': symbol,
            'price': random.uniform(0.5, 500),
            'change_percent': random.uniform(-10, 15),
            'volume': random.uniform(50000000, 5000000000),
            'high_24h': random.uniform(0.5, 550),
            'low_24h': random.uniform(0.4, 450)
        })
    
    # Sort by change percent descending
    top_performers.sort(key=lambda x: x['change_percent'], reverse=True)
    
    return {
        'timestamp': timestamp,
        'market_overview': market_overview,
        'smart_money_index': smart_money_index,
        'whale_activity': whale_activity,
        'top_performers': top_performers,
        'futures_premium': futures_premium,
        'date': datetime.now().strftime("%b %d, %Y"),
        'time': datetime.now().strftime("%H:%M:%S UTC")
    }

async def format_market_report(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format market data for Discord embed to match the real-world format."""
    market_overview = market_data['market_overview']
    top_performers = market_data['top_performers']
    smart_money = market_data['smart_money_index']
    whale_activity = market_data['whale_activity']
    futures_premium = market_data['futures_premium']
    date = market_data['date']
    time = market_data['time']
    
    # Determine color based on market regime
    if market_overview['regime'] == 'BULLISH':
        color = 0x00FF00  # Green
    elif market_overview['regime'] == 'BEARISH':
        color = 0xFF0000  # Red
    elif market_overview['regime'] == 'RANGING':
        color = 0xFFAA00  # Amber/Yellow
    else:
        color = 0xAAAAAA  # Grey for neutral
    
    # Format BTC 24h change with correct sign
    btc_change = market_overview['daily_change']
    btc_change_str = f"+{btc_change:.2f}%" if btc_change >= 0 else f"{btc_change:.2f}%"
    
    # Create main market overview embed
    market_overview_embed = {
        'title': '📊 Global Market Overview | ' + date,
        'color': color,
        'fields': [
            {
                'name': 'Market Metrics',
                'value': (
                    f"📈 BTC 24h: {btc_change_str} | 💰 Vol: ${market_overview['total_volume']/1e9:.1f}B | "
                    f"📊 BTC Dom: {market_overview['btc_dominance']}"
                ),
                'inline': False
            },
            {
                'name': '💪 Strength',
                'value': (
                    f"{market_overview['trend_strength']}\n"
                    f"{market_overview['regime']}"
                ),
                'inline': True
            },
            {
                'name': '📊 Volatility',
                'value': (
                    f"{market_overview['volatility']:.1f}%\n"
                    f"{market_overview['volatility_classification']}"
                ),
                'inline': True
            },
            {
                'name': '💧 Liquidity',
                'value': (
                    f"{market_overview['liquidity_score']:.0f}\n"
                    f"{market_overview['liquidity_classification']}"
                ),
                'inline': True
            },
            {
                'name': 'BTC Support 🛡️',
                'value': f"${market_overview['btc_support']:,.0f}",
                'inline': True
            },
            {
                'name': 'BTC Resistance 🧱',
                'value': f"${market_overview['btc_resistance']:,.0f}",
                'inline': True
            },
            {
                'name': 'Sentiment 🧠',
                'value': market_overview['sentiment'],
                'inline': True
            },
            {
                'name': '💰 Market Flows (24h)',
                'value': market_overview['market_flows'],
                'inline': False
            }
        ],
        'footer': {
            'text': f"Virtuoso Engine | Data as of {time}"
        }
    }
    
    # Create futures premium embed
    futures_premium_embed = {
        'title': '🔄 Futures Premium Analysis',
        'color': color,
        'description': futures_premium['data'] and 
                      f"BTC Futures Premium: {futures_premium['data'][0]['premium_percent']:.2f}% ({futures_premium['contango_status']})" or
                      "Could not retrieve detailed BTC futures premium data at this time.",
        'footer': {
            'text': f"Virtuoso Engine | Data as of {time}"
        }
    }
    
    # Add futures premium fields if data is available
    if futures_premium['data']:
        fields = []
        for contract in futures_premium['data']:
            fields.append({
                'name': contract['symbol'],
                'value': (
                    f"Spot: ${contract['spot_price']:,.2f}\n"
                    f"Futures: ${contract['futures_price']:,.2f}\n"
                    f"Premium: {contract['premium_percent']:+.2f}%"
                ),
                'inline': True
            })
        futures_premium_embed['fields'] = fields
    
    # Create smart money embed
    smart_money_embed = {
        'title': '🧠 Smart Money Analysis',
        'color': color,
        'fields': [
            {
                'name': 'Smart Money Index',
                'value': f"{smart_money['index']:.1f}/100",
                'inline': True
            },
            {
                'name': 'Sentiment',
                'value': smart_money['sentiment'],
                'inline': True
            },
            {
                'name': 'Institutional Flow',
                'value': smart_money['institutional_flow'],
                'inline': True
            },
            {
                'name': 'Funding Rates',
                'value': f"{smart_money['funding_rates']*100:.3f}% ({smart_money['funding_rates_classification']})",
                'inline': True
            }
        ],
        'footer': {
            'text': f"Virtuoso Engine | Data as of {time}"
        }
    }
    
    # Create whale activity embed if there is significant activity
    whale_embeds = []
    if whale_activity['has_significant_activity']:
        whale_embed = {
            'title': '🐋 Whale Activity Detected',
            'color': color,
            'fields': [
                {
                    'name': 'Significant Activity',
                    'value': '\n'.join([
                        f"**{symbol}**: {data['net_whale_volume']:.1f} {'BUY' if data['net_whale_volume'] > 0 else 'SELL'} (${abs(data['usd_value'])/1e6:.1f}M)"
                        for symbol, data in whale_activity['significant_activity'].items()
                    ]),
                    'inline': False
                },
                {
                    'name': 'Large Transactions',
                    'value': '\n'.join([
                        f"{tx['symbol']}: ${abs(tx['usd_value'])/1e6:.1f}M {'BUY' if tx['usd_value'] > 0 else 'SELL'} ({tx['exchange']})"
                        for tx in whale_activity['large_transactions'][:3]  # Show top 3
                    ]),
                    'inline': False
                }
            ],
            'footer': {
                'text': f"Virtuoso Engine | Data as of {time}"
            }
        }
        
        whale_embeds.append(whale_embed)
    
    # Create top performers embed
    top_performers_embed = {
        'title': '🏆 Top Performers (24h)',
        'color': color,
        'fields': []
    }
    
    # Add top performers
    for i, performer in enumerate(top_performers[:5]):  # Show top 5
        symbol = performer['symbol'].replace('/USDT', '')
        price = performer['price']
        change = performer['change_percent']
        volume = performer['volume']
        
        field_name = f"{i+1}. {symbol}"
        field_value = f"${price:.2f} ({change:+.2f}%)\nVolume: ${volume/1e6:.1f}M"
        
        top_performers_embed['fields'].append({
            'name': field_name,
            'value': field_value,
            'inline': True
        })
    
    top_performers_embed['footer'] = {
        'text': f"Virtuoso Engine | Data as of {time}"
    }
    
    # Combine all embeds
    formatted_report = {
        'content': '🚨 **MARKET REPORT** - ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'embeds': [market_overview_embed, futures_premium_embed, smart_money_embed] + whale_embeds + [top_performers_embed]
    }
    
    return formatted_report

async def test_market_report_with_discord():
    """
    Test the market report feature end-to-end using mock data:
    1. Generate mock market data
    2. Format report for Discord
    3. Create HTML and PDF
    4. Send to Discord if webhook URL is available
    """
    try:
        # Import required modules
        from src.core.reporting.pdf_generator import ReportGenerator
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Starting market report test with mock data...")
        
        # Generate mock market data
        logger.info("Generating mock market data...")
        mock_data = generate_mock_market_data()
        
        logger.info(f"Mock market overview regime: {mock_data['market_overview']['regime']}")
        logger.info(f"Mock smart money index: {mock_data['smart_money_index']['index']}")
        logger.info(f"Mock whale activity: {mock_data['whale_activity']['has_significant_activity']}")
        logger.info(f"Mock top performers count: {len(mock_data['top_performers'])}")
        
        # Format report for Discord
        logger.info("Formatting market report for Discord...")
        formatted_report = await format_market_report(mock_data)
        
        logger.info("Market report formatted successfully for Discord")
        
        # Initialize PDF generator with proper template directory
        template_dir = os.path.join(os.getcwd(), "templates")
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found at {template_dir}")
            template_dir = os.path.join(os.getcwd(), "src/core/reporting/templates")
            if not os.path.exists(template_dir):
                logger.error("Could not find template directory")
                return False
        
        logger.info(f"Using template directory: {template_dir}")
        pdf_generator = ReportGenerator(template_dir=template_dir)
        pdf_generator.template_dir = template_dir  # Ensure template_dir is set properly
        
        # Initialize report manager
        report_manager = ReportManager()
        report_manager.pdf_generator = pdf_generator
        
        # Generate HTML report
        timestamp = int(time.time())
        html_path = f"reports/pdf/market_report_mock_{timestamp}.html"
        pdf_path = f"reports/pdf/market_report_mock_{timestamp}.pdf"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        logger.info(f"Generating HTML report: {html_path}")
        
        # Prepare data for the HTML template - add additional sections
        full_report_data = dict(mock_data)
        full_report_data["additional_sections"] = {
            "market_sentiment": {
                "overall": "Bullish" if mock_data['market_overview']['regime'] == 'BULLISH' else 
                          "Bearish" if mock_data['market_overview']['regime'] == 'BEARISH' else 
                          "Ranging" if mock_data['market_overview']['regime'] == 'RANGING' else "Neutral",
                "volume_sentiment": "Increasing" if mock_data['market_overview']['daily_change'] > 0 else "Decreasing",
                "funding_rates": "Positive" if random.random() > 0.5 else "Negative",
                "btc_support": f"${mock_data['market_overview']['btc_support']:,.0f}",
                "btc_resistance": f"${mock_data['market_overview']['btc_resistance']:,.0f}"
            },
            "futures_premium_analysis": {
                "btc_premium": f"{mock_data['futures_premium']['data'][0]['premium_percent']:+.2f}%",
                "eth_premium": f"{mock_data['futures_premium']['data'][1]['premium_percent']:+.2f}%",
                "contango_status": mock_data['futures_premium']['contango_status'],
                "funding_situation": f"Current funding rates are {mock_data['smart_money_index']['funding_rates_classification'].lower()}"
            }
        }
        
        # Generate HTML report
        html_success = await pdf_generator.generate_market_html_report(
            market_data=full_report_data,
            output_path=html_path,
            generate_pdf=False
        )
        
        if not html_success:
            logger.error("Failed to generate HTML report")
            return False
            
        logger.info(f"HTML report generated: {html_path}")
        
        # Generate PDF from HTML
        logger.info(f"Generating PDF report: {pdf_path}")
        pdf_success = await pdf_generator.generate_pdf(html_path, pdf_path)
        
        if not pdf_success:
            logger.error("Failed to generate PDF report")
            return False
            
        logger.info(f"PDF report generated: {pdf_path}")
        
        # Send Discord alert with PDF attachment
        logger.info("Sending Discord alert with PDF attachment...")
        
        # Check if DISCORD_WEBHOOK_URL env variable exists
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL environment variable not set")
            logger.info("Test completed (Discord alert not sent). PDF was created successfully.")
            return True
        
        # Import Discord webhook
        try:
            from discord_webhook import DiscordWebhook, DiscordEmbed
            
            # Create Discord webhook
            webhook = DiscordWebhook(url=webhook_url)
            
            # Add embeds from formatted report
            for embed_data in formatted_report.get('embeds', []):
                embed = DiscordEmbed(
                    title=embed_data.get('title', ''),
                    description=embed_data.get('description', ''),
                    color=embed_data.get('color', 0x00ff00)
                )
                
                # Add fields
                for field in embed_data.get('fields', []):
                    embed.add_embed_field(
                        name=field.get('name', ''),
                        value=field.get('value', ''),
                        inline=field.get('inline', False)
                    )
                
                # Add footer
                if 'footer' in embed_data:
                    embed.set_footer(text=embed_data['footer'].get('text', ''))
                
                # Add timestamp
                if 'timestamp' in embed_data:
                    embed.set_timestamp()
                
                webhook.add_embed(embed)
            
            # Add PDF file attachment
            with open(pdf_path, 'rb') as pdf_file:
                webhook.add_file(file=pdf_file.read(), filename=os.path.basename(pdf_path))
            
            # Send webhook
            response = webhook.execute()
            
            if response and response.status_code in (200, 204):
                logger.info("Discord alert sent successfully")
                return True
            else:
                logger.error(f"Failed to send Discord alert: {response.status_code if response else 'No response'}")
                return False
        except ImportError:
            logger.warning("discord_webhook module not installed, skipping Discord notification")
            logger.info("Test completed (Discord alert not sent). PDF was created successfully.")
            return True
        
    except Exception as e:
        logger.error(f"Error during market report test: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main entry point for the test script."""
    success = await test_market_report_with_discord()
    
    if success:
        logger.info("✅ Market report test with Discord alerts and PDF generation passed!")
        return 0
    else:
        logger.error("❌ Market report test with Discord alerts and PDF generation failed!")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result) 