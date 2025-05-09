#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to generate market reports with real live data from Bybit's public endpoints that don't require authentication
"""

import os
import sys
import time
import json
import asyncio
import logging
import aiohttp
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_live_market_report")

# Ensure the current directory is in the path for imports
sys.path.append('.')

class BybitPublicAPI:
    """Simple class to fetch public data from Bybit API without authentication."""
    
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.session = None
    
    async def initialize(self):
        """Initialize the API session."""
        self.session = aiohttp.ClientSession()
        return True
    
    async def close(self):
        """Close the API session."""
        if self.session:
            await self.session.close()
    
    async def fetch_tickers(self, symbols=None):
        """Fetch ticker data for specified symbols or all available."""
        endpoint = "/v5/market/tickers"
        params = {"category": "spot"}
        
        all_tickers = []
        
        if symbols:
            # Fetch each symbol individually
            for symbol in symbols:
                params["symbol"] = symbol
                
                url = f"{self.base_url}{endpoint}"
                
                try:
                    async with self.session.get(url, params=params) as response:
                        data = await response.json()
                        if data.get("retCode") == 0:
                            tickers = data.get("result", {}).get("list", [])
                            all_tickers.extend(tickers)
                        else:
                            logger.error(f"Error fetching ticker for {symbol}: {data.get('retMsg', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"Exception fetching ticker for {symbol}: {str(e)}")
        else:
            # Fetch all available tickers
            url = f"{self.base_url}{endpoint}"
            
            try:
                async with self.session.get(url, params=params) as response:
                    data = await response.json()
                    if data.get("retCode") == 0:
                        all_tickers = data.get("result", {}).get("list", [])
                    else:
                        logger.error(f"Error fetching tickers: {data.get('retMsg', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Exception fetching tickers: {str(e)}")
        
        return all_tickers
    
    async def fetch_klines(self, symbol, interval="60", limit=200):
        """Fetch OHLCV data for a symbol."""
        endpoint = "/v5/market/kline"
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                if data.get("retCode") == 0:
                    return data.get("result", {}).get("list", [])
                else:
                    logger.error(f"Error fetching klines: {data.get('retMsg', 'Unknown error')}")
                    return []
        except Exception as e:
            logger.error(f"Exception fetching klines: {str(e)}")
            return []
    
    async def fetch_order_book(self, symbol, limit=50):
        """Fetch order book data for a symbol."""
        endpoint = "/v5/market/orderbook"
        params = {
            "category": "spot",
            "symbol": symbol,
            "limit": limit
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                if data.get("retCode") == 0:
                    return data.get("result", {})
                else:
                    logger.error(f"Error fetching order book: {data.get('retMsg', 'Unknown error')}")
                    return {}
        except Exception as e:
            logger.error(f"Exception fetching order book: {str(e)}")
            return {}
    
    async def fetch_market_data(self, symbols):
        """Fetch comprehensive market data for a list of symbols."""
        if not symbols:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
        
        # Normalize symbols for API requests
        api_symbols = [s.replace("/", "").replace(":", "") for s in symbols]
        
        # Collect data from multiple endpoints
        tickers = await self.fetch_tickers(api_symbols)
        
        # Create a market data structure
        market_data = {
            "timestamp": int(time.time() * 1000),
            "market_overview": {},
            "symbols_data": {},
            "date": datetime.now().strftime("%b %d, %Y"),
            "time": datetime.now().strftime("%H:%M:%S UTC")
        }
        
        # Process ticker data
        ticker_by_symbol = {t.get("symbol"): t for t in tickers}
        
        # Calculate market overview metrics
        total_volume = sum(float(t.get("volume24h", 0)) for t in tickers)
        price_changes = [float(t.get("price24hPcnt", 0)) * 100 for t in tickers if t.get("price24hPcnt")]
        btc_ticker = ticker_by_symbol.get("BTCUSDT", {})
        
        # Calculate market regime
        if price_changes:
            avg_change = sum(price_changes) / len(price_changes)
            volatility = (max(price_changes) - min(price_changes)) if price_changes else 0
            
            if avg_change > 2:
                regime = "BULLISH"
            elif avg_change < -2:
                regime = "BEARISH"
            elif volatility > 10:
                regime = "RANGING"
            else:
                regime = "NEUTRAL"
                
            # Classify volatility
            if volatility < 5:
                volatility_class = "Low"
            elif volatility < 10:
                volatility_class = "Normal"
            elif volatility < 20:
                volatility_class = "High"
            else:
                volatility_class = "Extreme"
        else:
            avg_change = 0
            volatility = 0
            regime = "NEUTRAL"
            volatility_class = "Unknown"
        
        # Create market overview
        market_overview = {
            "regime": regime,
            "trend_strength": f"{min(abs(avg_change) * 10, 100):.1f}%",
            "volatility": volatility,
            "volatility_classification": volatility_class,
            "total_volume": total_volume,
            "total_turnover": total_volume * 0.9,  # Estimate
            "daily_change": float(btc_ticker.get("price24hPcnt", 0)) * 100 if btc_ticker else 0,
            "btc_dominance": "55.2%",  # This would need another API call to calculate properly
            "liquidity_score": 75.0,  # Placeholder
            "liquidity_classification": "Medium",
            "momentum": "INCREASING" if avg_change > 0 else "DECREASING",
            "btc_support": float(btc_ticker.get("lastPrice", 0)) * 0.97 if btc_ticker else 0,
            "btc_resistance": float(btc_ticker.get("lastPrice", 0)) * 1.03 if btc_ticker else 0,
            "sentiment": "Bullish" if avg_change > 0 else "Bearish" if avg_change < 0 else "Neutral",
            "market_flows": "Based on current market conditions, institutional flows appear balanced."
        }
        
        market_data["market_overview"] = market_overview
        
        # Process individual symbols
        for symbol, ticker in ticker_by_symbol.items():
            price = float(ticker.get("lastPrice", 0))
            price_change = float(ticker.get("price24hPcnt", 0)) * 100
            high_24h = float(ticker.get("highPrice24h", 0))
            low_24h = float(ticker.get("lowPrice24h", 0))
            volume = float(ticker.get("volume24h", 0))
            
            market_data["symbols_data"][symbol] = {
                "price": price,
                "change_percent": price_change,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "volume": volume
            }
        
        # Create top performers list
        top_performers = []
        for symbol, data in market_data["symbols_data"].items():
            # Convert back to standard symbol format for display
            display_symbol = symbol
            if display_symbol.endswith("USDT"):
                display_symbol = f"{display_symbol[:-4]}/USDT"
                
            top_performers.append({
                "symbol": display_symbol,
                "price": data["price"],
                "change_percent": data["change_percent"],
                "volume": data["volume"],
                "high_24h": data["high_24h"],
                "low_24h": data["low_24h"]
            })
        
        # Sort by change percent descending
        top_performers.sort(key=lambda x: x["change_percent"], reverse=True)
        market_data["top_performers"] = top_performers[:10]  # Keep top 10
        
        # Create smart money index (estimated based on available data)
        sentiment_score = 50 + (avg_change * 2)  # Scale to 0-100
        market_data["smart_money_index"] = {
            "index": max(0, min(100, sentiment_score)),
            "sentiment": "BULLISH" if sentiment_score > 60 else "BEARISH" if sentiment_score < 40 else "NEUTRAL",
            "institutional_flow": f"{avg_change:.1f}%",
            "otc_volume": 2500,  # Placeholder
            "futures_premium": 0.75,  # Placeholder
            "futures_premium_classification": "Normal",
            "funding_rates": 0.01,  # Placeholder
            "funding_rates_classification": "Positive" if avg_change > 0 else "Negative",
            "key_zones": [
                {
                    "symbol": "BTC/USDT",
                    "type": "accumulation" if avg_change > 0 else "distribution",
                    "strength": 75 if avg_change > 0 else 65,
                    "buy_volume": total_volume * 0.6 if avg_change > 0 else total_volume * 0.4,
                    "sell_volume": total_volume * 0.4 if avg_change > 0 else total_volume * 0.6
                }
            ]
        }
        
        # Create placeholder whale activity data
        market_data["whale_activity"] = {
            "has_significant_activity": False,
            "significant_activity": {},
            "large_transactions": []
        }
        
        # Create futures premium data (estimated)
        futures_premium_value = random_value = 0.25 + (avg_change / 20)
        market_data["futures_premium"] = {
            "average_premium": f"{futures_premium_value:.2f}%",
            "contango_status": "Normal Contango" if futures_premium_value > 0 else "Backwardation",
            "data": [
                {
                    "symbol": "BTC-PERP",
                    "spot_price": float(btc_ticker.get("lastPrice", 0)) if btc_ticker else 0,
                    "futures_price": float(btc_ticker.get("lastPrice", 0)) * (1 + futures_premium_value/100) if btc_ticker else 0,
                    "premium_percent": futures_premium_value
                }
            ]
        }
        
        return market_data

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
                    ]) or "No significant whale activity detected.",
                    'inline': False
                }
            ],
            'footer': {
                'text': f"Virtuoso Engine | Data as of {time}"
            }
        }
        
        if whale_activity['large_transactions']:
            whale_embed['fields'].append({
                'name': 'Large Transactions',
                'value': '\n'.join([
                    f"{tx['symbol']}: ${abs(tx['usd_value'])/1e6:.1f}M {'BUY' if tx['usd_value'] > 0 else 'SELL'} ({tx['exchange']})"
                    for tx in whale_activity['large_transactions'][:3]  # Show top 3
                ]),
                'inline': False
            })
        
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

async def test_live_market_report():
    """
    Test market report generation with live data:
    1. Fetch live data from Bybit public API
    2. Format report for Discord
    3. Create HTML and PDF
    4. Send to Discord if webhook URL is available
    """
    try:
        # Import required modules
        from src.core.reporting.pdf_generator import ReportGenerator
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Starting market report test with live Bybit data...")
        
        # Initialize Bybit public API client
        bybit_api = BybitPublicAPI()
        await bybit_api.initialize()
        
        # Define symbols to analyze
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT"]
        logger.info(f"Analyzing the following symbols: {symbols}")
        
        # Fetch live market data
        logger.info("Fetching live market data from Bybit...")
        live_data = await bybit_api.fetch_market_data(symbols)
        
        logger.info(f"Live market overview regime: {live_data['market_overview']['regime']}")
        logger.info(f"Live smart money index: {live_data['smart_money_index']['index']}")
        logger.info(f"Live top performers count: {len(live_data['top_performers'])}")
        
        # Format report for Discord
        logger.info("Formatting market report for Discord...")
        formatted_report = await format_market_report(live_data)
        
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
        html_path = f"reports/pdf/market_report_live_{timestamp}.html"
        pdf_path = f"reports/pdf/market_report_live_{timestamp}.pdf"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        logger.info(f"Generating HTML report: {html_path}")
        
        # Prepare data for the HTML template - add additional sections
        full_report_data = dict(live_data)
        full_report_data["additional_sections"] = {
            "market_sentiment": {
                "overall": "Bullish" if live_data['market_overview']['regime'] == 'BULLISH' else 
                          "Bearish" if live_data['market_overview']['regime'] == 'BEARISH' else 
                          "Ranging" if live_data['market_overview']['regime'] == 'RANGING' else "Neutral",
                "volume_sentiment": "Increasing" if live_data['market_overview']['daily_change'] > 0 else "Decreasing",
                "funding_rates": "Positive" if live_data['smart_money_index']['funding_rates'] > 0 else "Negative",
                "btc_support": f"${live_data['market_overview']['btc_support']:,.0f}",
                "btc_resistance": f"${live_data['market_overview']['btc_resistance']:,.0f}"
            },
            "futures_premium_analysis": {
                "btc_premium": f"{live_data['futures_premium']['data'][0]['premium_percent']:+.2f}%" if live_data['futures_premium']['data'] else "N/A",
                "contango_status": live_data['futures_premium']['contango_status'],
                "funding_situation": f"Current funding rates are {live_data['smart_money_index']['funding_rates_classification'].lower()}"
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
        
        # Close Bybit API session
        await bybit_api.close()
        
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
    success = await test_live_market_report()
    
    if success:
        logger.info("✅ Live market report test with PDF generation passed!")
        return 0
    else:
        logger.error("❌ Live market report test failed!")
        return 1

if __name__ == "__main__":
    # Add flag for testing Discord webhook
    if len(sys.argv) > 1 and sys.argv[1] == "--discord":
        # Ask for webhook URL
        webhook_url = input("Enter your Discord webhook URL: ").strip()
        if webhook_url:
            os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
    
    result = asyncio.run(main())
    sys.exit(result) 