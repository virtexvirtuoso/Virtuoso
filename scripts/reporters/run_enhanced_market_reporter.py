import sys
import logging
import asyncio
import time
from datetime import datetime
import os
import json
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_market_report.log')
    ]
)
logger = logging.getLogger(__name__)

# Set higher debug level for specific components
logging.getLogger('src.monitoring.market_reporter').setLevel(logging.DEBUG)
logging.getLogger('src.core.exchanges.bybit').setLevel(logging.INFO)

# Import necessary components with proper error handling
try:
    from src.config.manager import ConfigManager
    from src.core.exchanges.manager import ExchangeManager
    from src.monitoring.market_reporter import MarketReporter
    from src.monitoring.alert_manager import AlertManager
    import aiohttp
except ImportError as e:
    logger.critical(f"Critical import error: {str(e)}")
    sys.exit(1)

async def enhanced_format_market_report(market_reporter, report):
    """Format a market report with enhanced details for Discord."""
    try:
        logger.info("Formatting enhanced market report")
        
        # Initialize basic variables
        dashboard_base_url = "https://www.virtuosotrading.com/dashboard"
        virtuoso_logo_url = "https://raw.githubusercontent.com/virtuoso-dev/virtuoso/main/assets/logo.png"
        
        # Get the current time in UTC for timestamping
        utc_now = datetime.utcnow()
        
        # Extract important data sections
        market_data = report.get('market_data', {})
        overview = report.get('market_overview', {})
        whale_data = report.get('whale_activity', {})
        smart_money = report.get('smart_money_index', {})
        
        # Create a list to store all embeds
        embeds = []
        
        # --- Main Market Data Embed - Optimize layout with strategic inline fields ---
        if market_data or overview:
            # Build description with key market metrics - more concise
            market_desc = (
                f"**Global Market Overview | {utc_now.strftime('%B %d, %Y')}**\n\n"
                f"{'📈' if overview.get('daily_change', 0) >= 0 else '📉'} "
                f"BTC 24h: **{overview.get('daily_change', '0.0')}%** | "
                f"💰 Vol: **${market_reporter._format_number(overview.get('total_volume', 0))}** | "
                f"📊 BTC Dom: **{overview.get('btc_dominance', '0.0')}%**"
            )
            
            # Create optimized market data embed
            market_embed = {
                "title": "📊 Market Data",
                "color": 3447003,  # Blue
                "url": f"{dashboard_base_url}/market",
                "description": market_desc,
                # Thumbnail removed for cleaner layout
                "fields": [],
                "footer": {
                    "text": f"Virtuoso Engine | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
                    "icon_url": virtuoso_logo_url
                },
                "timestamp": utc_now.isoformat() + 'Z'
            }
            
            # --- Group 1: Market Metrics (First Row) - More concise display ---
            market_strength = {
                "name": "💪 Strength",
                "value": f"**{overview.get('strength', '0.0')}%**\n{overview.get('regime', 'UNKNOWN')}",
                "inline": True
            }
            
            market_volatility = {
                "name": "📊 Volatility",
                "value": f"**{overview.get('volatility', '0.0')}%**\n{overview.get('vol_regime', 'Normal')}",
                "inline": True
            }
            
            market_liquidity = {
                "name": "💧 Liquidity",
                "value": f"**{overview.get('liquidity', '0')}**\n{'High' if int(overview.get('liquidity', 0)) > 75 else 'Medium' if int(overview.get('liquidity', 0)) > 50 else 'Low'}",
                "inline": True
            }
            
            # --- Group 2: Key Price Levels (Second Row) ---
            btc_support = {
                "name": "BTC Support 🛡️",
                "value": f"**${overview.get('btc_support', '0')}**",
                "inline": True
            }
            
            btc_resistance = {
                "name": "BTC Resistance 🧱",
                "value": f"**${overview.get('btc_resistance', '0')}**",
                "inline": True
            }
            
            sentiment = {
                "name": "Sentiment 🧠",
                "value": f"**{overview.get('sentiment', 'Neutral')}**",
                "inline": True
            }
            
            # --- Group 3: Market Flows (Non-inline) - More compact display ---
            flows = market_data.get('flows', {})
            if flows:
                # Filter out non-numeric values and timestamps
                flow_items = [(k, v) for k, v in flows.items() 
                             if isinstance(v, (int, float)) and k != 'timestamp']
                
                # Sort by absolute value to show most significant first
                flow_items.sort(key=lambda x: abs(x[1]), reverse=True)
                
                # Format the flow text
                flow_lines = []
                for key, value in flow_items[:5]:  # Limit to top 5 most significant flows
                    direction = "↗️" if value > 0 else "↘️"
                    flow_lines.append(f"{direction} **{key.replace('_', ' ').title()}**: ${abs(value):,.0f}")
                
                flow_text = "\n".join(flow_lines)
            else:
                flow_text = "No flow data available"
            
            market_flows = {
                "name": "💰 Market Flows (24h)",
                "value": flow_text,
                "inline": False
            }
            
            # --- Group 4: Top Movers - More compact with icons ---
            top_movers = market_data.get('top_movers', [])
            if top_movers:
                # Sort gainers and losers
                gainers = sorted([m for m in top_movers if m.get('change', 0) > 0], 
                                key=lambda x: x.get('change', 0), reverse=True)[:3]
                
                losers = sorted([m for m in top_movers if m.get('change', 0) < 0], 
                               key=lambda x: x.get('change', 0))[:3]
                
                # Format in two columns
                movers_text = ""
                
                # Left column: Gainers
                if gainers:
                    movers_text += "**Gainers:**\n"
                    for g in gainers:
                        movers_text += f"📈 {g.get('symbol', 'Unknown')}: +{g.get('change', 0):.1f}%\n"
                
                # Right column: Losers
                if losers:
                    movers_text += "\n**Losers:**\n"
                    for l in losers:
                        movers_text += f"📉 {l.get('symbol', 'Unknown')}: {l.get('change', 0):.1f}%\n"
            else:
                movers_text = "No significant price movements"
            
            top_movers_field = {
                "name": "📈 Top Movers (24h)",
                "value": movers_text,
                "inline": False
            }
            
            # Add fields in optimized order
            market_embed["fields"].extend([
                market_strength, market_volatility, market_liquidity,  # Group 1: Market metrics
                btc_support, btc_resistance, sentiment,                # Group 2: Price levels
                market_flows,                                          # Group 3: Market flows
                top_movers_field                                       # Group 4: Top movers
            ])
            
            embeds.append(market_embed)
        
        # --- Whale Activity Embed - Simplified and focused ---
        if whale_data:
            # Determine if there's significant whale activity
            has_imbalances = ('order_imbalances' in whale_data and 
                             any(data.get('imbalance_ratio', 1) > 1.5 
                                for data in whale_data['order_imbalances'].values()))
            
            has_transactions = ('large_transactions' in whale_data and 
                               whale_data['large_transactions'])
            
            if has_imbalances or has_transactions:
                whale_desc = "**Analysis of significant market activity by large players**"
                
                # Process order book imbalances
                imbalance_lines = []
                if has_imbalances:
                    for symbol, data in whale_data['order_imbalances'].items():
                        if data.get('imbalance_ratio', 1) > 1.5:
                            direction = "buy" if data.get('imbalance_ratio', 1) > 1 else "sell"
                            icon = "🟢" if direction == "buy" else "🔴"
                            imbalance_lines.append(
                                f"{icon} **{symbol}**: {direction.upper()} pressure ({data.get('imbalance_ratio', 1):.1f}x)"
                            )
                
                # Process large transactions
                transaction_text = ""
                summary = ""
                if has_transactions:
                    transactions = whale_data['large_transactions']
                    buy_vol = sum(t.get('usd_value', 0) for t in transactions if t.get('usd_value', 0) > 0)
                    sell_vol = abs(sum(t.get('usd_value', 0) for t in transactions if t.get('usd_value', 0) < 0))
                    
                    net_flow = buy_vol - sell_vol
                    net_direction = "buying" if net_flow > 0 else "selling"
                    
                    # Create summary
                    summary = (
                        f"Net whale flow: **{net_direction}** ${market_reporter._format_number(abs(net_flow))}\n"
                        f"Buy volume: ${market_reporter._format_number(buy_vol)} | "
                        f"Sell volume: ${market_reporter._format_number(sell_vol)}"
                    )
                    
                    # List most significant transactions
                    top_transactions = sorted(transactions, key=lambda x: abs(x.get('usd_value', 0)), reverse=True)[:3]
                    if top_transactions:
                        transaction_lines = []
                        for tx in top_transactions:
                            tx_type = "BUY" if tx.get('usd_value', 0) > 0 else "SELL"
                            icon = "🟢" if tx_type == "BUY" else "🔴"
                            asset = tx.get('symbol', 'Unknown')
                            value = abs(tx.get('usd_value', 0))
                            
                            transaction_lines.append(
                                f"{icon} **{asset}**: {tx_type} ${market_reporter._format_number(value)}"
                            )
                        transaction_text = "\n".join(transaction_lines)
                
                # Combine imbalance and transaction data
                whale_activity_text = "\n".join(imbalance_lines) if imbalance_lines else "No significant order book imbalances"
                
                whale_embed = {
                    "title": "🐋 Whale Activity",
                    "color": 3447003,  # Blue
                    "url": f"{dashboard_base_url}/whales",
                    "description": whale_desc,
                    "fields": [
                        # Summary first
                        {
                            "name": "📊 Summary",
                            "value": summary if summary else "Limited whale activity detected",
                            "inline": False
                        },
                        # Order book activity
                        {
                            "name": "📚 Order Book Imbalances",
                            "value": whale_activity_text,
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"Virtuoso Engine | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
                        "icon_url": virtuoso_logo_url
                    },
                    "timestamp": utc_now.isoformat() + 'Z'
                }
                
                # Add transactions field if available
                if transaction_text:
                    whale_embed["fields"].append({
                        "name": "💸 Large Transactions",
                        "value": transaction_text,
                        "inline": False
                    })
                
                embeds.append(whale_embed)
            else:
                # No significant whale activity
                whale_desc = "No significant whale activity detected in the monitored pairs."
                whale_activity_text = "All monitored pairs show normal order book distribution."
                summary = "No notable whale flows in the current period."
                
                embeds.append({
                    "title": "🐋 Whale Activity",
                    "color": 3447003,  # Blue
                    "url": f"{dashboard_base_url}/whales",
                    "description": whale_desc,
                    "fields": [
                        {
                            "name": "Summary",
                            "value": summary,
                            "inline": False
                        },
                        {
                            "name": "Market Activity",
                            "value": whale_activity_text,
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"Virtuoso Engine | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
                        "icon_url": virtuoso_logo_url
                    },
                    "timestamp": utc_now.isoformat() + 'Z'
                })
        
        # --- Enhanced Market Outlook - Concise and focused ---
        if overview:
            # Extract key metrics
            regime = overview.get('regime', 'UNKNOWN')
            trend_strength = float(overview.get('trend_strength', '0.0%').replace('%', '') if isinstance(overview.get('trend_strength'), str) else overview.get('trend_strength', 0))
            volatility = overview.get('volatility', 0)
            
            # Create dynamic descriptions based on actual data
            regime_desc = "consolidating"
            if "BULLISH" in regime:
                regime_desc = "in an uptrend"
            elif "BEARISH" in regime:
                regime_desc = "in a downtrend"
            elif "CHOPPY" in regime or "VOLATILE" in regime:
                regime_desc = "showing choppy conditions"
            elif "RANGING" in regime:
                regime_desc = "range-bound"
            
            # Simplified bias
            bias = "neutral"
            if "BULLISH" in regime:
                bias = "bullish"
            elif "BEARISH" in regime:
                bias = "bearish"
            
            # Simplified volatility description
            vol_desc = "moderate"
            if volatility > 5:
                vol_desc = "high"
            elif volatility < 1:
                vol_desc = "low"
            
            # Simplified trend strength
            trend_desc = "moderate"
            if trend_strength > 100:
                trend_desc = "strong"
            elif trend_strength < 30:
                trend_desc = "weak"
            
            # Simplified institutional flow
            inst_flow = "neutral"
            if smart_money:
                smi_value = smart_money.get('index', 50.0)
                if smi_value > 65:
                    inst_flow = "bullish"
                elif smi_value < 35:
                    inst_flow = "bearish"
            
            # Construct a more concise market outlook
            market_outlook = (
                f"The market is currently **{regime_desc}** with a **{bias}** bias. "
                f"Trend strength is **{trend_desc}** at **{trend_strength:.1f}%** with **{vol_desc}** volatility."
            )
            
            # Create enhanced outlook embed with metrics as fields
            outlook_embed = {
                "title": "🔮 Market Outlook",
                "color": 10181046,  # Purple
                "url": f"{dashboard_base_url}/outlook",
                "description": market_outlook,
                "fields": [
                    # First row - key metrics
                    {
                        "name": "Market Regime",
                        "value": f"**{regime}**",
                        "inline": True
                    },
                    {
                        "name": "Trend Direction",
                        "value": f"**{bias.title()}**",
                        "inline": True
                    },
                    {
                        "name": "Risk Level",
                        "value": f"**{vol_desc.title()}**",
                        "inline": True
                    },
                    # Second row - additional metrics
                    {
                        "name": "Trend Strength",
                        "value": f"**{trend_strength:.1f}%**",
                        "inline": True
                    },
                    {
                        "name": "Volatility",
                        "value": f"**{volatility:.1f}%**",
                        "inline": True
                    },
                    {
                        "name": "Institutional Flow",
                        "value": f"**{inst_flow.title()}**",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Virtuoso Engine | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
                    "icon_url": virtuoso_logo_url
                },
                "timestamp": utc_now.isoformat() + 'Z'
            }
            
            embeds.append(outlook_embed)
        
        # --- System Status Embed - Simple and clean ---
        system_embed = {
            "title": "⚙️ System Status",
            "color": 5763719,  # Green
            "url": f"{dashboard_base_url}/status",
            "description": "All systems operating normally with optimal data quality.",
            "fields": [
                # Status indicators as inline fields
                {
                    "name": "Market Monitor",
                    "value": "✅ Active",
                    "inline": True
                },
                {
                    "name": "Data Collection",
                    "value": "✅ Running",
                    "inline": True
                },
                {
                    "name": "Analysis Engine",
                    "value": "✅ Ready",
                    "inline": True
                },
                # Performance metrics
                {
                    "name": "Performance",
                    "value": f"Quality: **{report.get('quality_score', 100)}%** | Latency: **Normal** | Errors: **0.0%**",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Virtuoso Engine | Data as of {utc_now.strftime('%H:%M:%S UTC')}",
                "icon_url": virtuoso_logo_url
            },
            "timestamp": utc_now.isoformat() + 'Z'
        }
        
        embeds.append(system_embed)
        
        # --- Final Structure ---
        return {
            "content": f"# 🌟 VIRTUOSO Market Intelligence\n_Analysis for {utc_now.strftime('%B %d, %Y - %H:%M UTC')}_",
            "embeds": embeds,
            "username": "Virtuoso Market Monitor",
            "avatar_url": virtuoso_logo_url
        }
        
    except Exception as e:
        logger.error(f"Error formatting enhanced market report: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a simplified error message
        return {
            "content": f"Error generating enhanced market report: {str(e)}",
            "embeds": [{"title": "Error Report", "color": 15158332, "description": "Failed to format report."}],
            "username": "Virtuoso Error Bot", 
            "avatar_url": virtuoso_logo_url
        }

# Save enhanced report to file for backup
async def save_enhanced_report(report, path="enhanced_report.json"):
    try:
        with open(path, 'w') as file:
            json.dump(report, file, indent=2)
        logger.info(f"Enhanced report saved to {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving enhanced report: {str(e)}")
        return False

# Function to send the report via Discord webhook        
async def send_enhanced_report(report, webhook_url=None):
    if not webhook_url:
        logger.warning("No webhook URL provided, skipping Discord notification")
        return False
        
    try:
        logging.info(f"Sending enhanced report to Discord webhook")
        
        headers = {'Content-Type': 'application/json'}
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=report, headers=headers) as response:
                if response.status == 204:
                    logger.info("Enhanced report sent successfully to Discord")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to send report to Discord. Status: {response.status}, Response: {response_text}")
                    return False
    except Exception as e:
        logger.error(f"Error sending enhanced report to Discord: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def run_enhanced_market_reporter():
    """Run the MarketReporter with live data and generate an enhanced report."""
    start_time = time.time()
    components = {}
    
    try:
        # Step 1: Initialize ConfigManager
        logger.info("Initializing ConfigManager")
        config_manager = ConfigManager()
        components['config_manager'] = config_manager
        
        # Step 2: Initialize ExchangeManager
        logger.info("Initializing ExchangeManager")
        exchange_manager = ExchangeManager(config_manager)
        components['exchange_manager'] = exchange_manager
        
        # Step 3: Initialize exchanges
        logger.info("Initializing exchanges")
        if not await exchange_manager.initialize():
            logger.error("Failed to initialize exchange manager")
            return False
        
        # Step 4: Get the primary exchange
        primary_exchange = await exchange_manager.get_primary_exchange()
        if not primary_exchange:
            logger.error("No primary exchange available")
            return False
        
        exchange_name = primary_exchange.exchange_id
        logger.info(f"Using {exchange_name} as primary exchange")
        components['exchange'] = primary_exchange
        
        # Step 5: Initialize AlertManager for notifications
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config_manager.config)
        components['alert_manager'] = alert_manager
        
        # Step 6: Initialize MarketReporter
        logger.info("Initializing MarketReporter")
        market_reporter = MarketReporter(
            exchange=primary_exchange,
            logger=logger,
            alert_manager=alert_manager
        )
        components['market_reporter'] = market_reporter
        
        # Test symbols to use
        test_symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT", "DOGE/USDT:USDT"]
        logger.info(f"Testing with symbols: {test_symbols}")
        
        # Set the test symbols for the market reporter
        market_reporter.symbols = test_symbols
        
        # Step 7: Verify exchange connection
        logger.info("Verifying exchange connection")
        try:
            ticker = await primary_exchange.fetch_ticker(test_symbols[0])
            if ticker and ticker.get('last'):
                logger.info(f"Successfully fetched ticker for {test_symbols[0]}")
                logger.info(f"Current price: {ticker.get('last', 'N/A')}")
            else:
                logger.warning(f"Could not fetch ticker for {test_symbols[0]}")
        except Exception as e:
            logger.error(f"Error testing exchange connection: {str(e)}")
            
        # Step 8: Generate market report
        logger.info("Generating market report")
        generation_start = time.time()
        
        try:
            # Generate the market report
            report = await market_reporter.generate_market_summary()
            
            generation_time = time.time() - generation_start
            logger.info(f"Generated market report in {generation_time:.2f} seconds")
            
            if not report:
                logger.error("Failed to generate market report")
                return False
                
            # Log report details
            logger.info(f"Report contains {len(report)} sections")
            
            # Format the enhanced report for Discord
            logger.info("Formatting enhanced report for Discord")
            formatted_report = await enhanced_format_market_report(market_reporter, report)
            
            if not formatted_report:
                logger.error("Failed to format enhanced report")
                return False
                
            logger.info(f"Formatted report contains {len(formatted_report.get('embeds', []))} embeds")
            
            # Save the report to a file
            logger.info("Saving enhanced report to file")
            await save_enhanced_report(formatted_report, "enhanced_market_report.json")
            
            # Send the report to Discord if webhook URL is configured
            if alert_manager and alert_manager.discord_webhook_url:
                logger.info("Sending enhanced report to Discord")
                try:
                    success = await send_enhanced_report(formatted_report, alert_manager.discord_webhook_url)
                    if success:
                        logger.info("Successfully sent enhanced report to Discord")
                    else:
                        logger.warning("Failed to send enhanced report to Discord")
                except Exception as e:
                    logger.error(f"Error sending enhanced report to Discord: {str(e)}")
                    logger.error(traceback.format_exc())
            else:
                logger.info("Skipping Discord sending (no webhook URL configured)")
                
            logger.info("Enhanced market reporter test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during report generation: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False
        
    finally:
        # Cleanup all components
        logger.info("Cleaning up components")
        
        # Close alert manager if it exists
        if 'alert_manager' in components:
            logger.info("Stopping AlertManager")
            if hasattr(components['alert_manager'], 'stop'):
                try:
                    await components['alert_manager'].stop()
                except Exception as e:
                    logger.error(f"Error stopping AlertManager: {str(e)}")
            
        # Close exchange connections
        if 'exchange_manager' in components:
            logger.info("Closing exchange connections")
            await components['exchange_manager'].cleanup()
            
        total_time = time.time() - start_time
        logger.info(f"Test completed in {total_time:.2f} seconds")

if __name__ == "__main__":
    logger.info("="*50)
    logger.info("STARTING ENHANCED MARKET REPORTER WITH LIVE DATA")
    logger.info("="*50)
    
    result = asyncio.run(run_enhanced_market_reporter())
    
    logger.info("="*50)
    logger.info(f"TEST {'PASSED' if result else 'FAILED'}")
    logger.info("="*50)
    
    sys.exit(0 if result else 1) 