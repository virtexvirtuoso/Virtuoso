import asyncio
import logging
import json
import aiohttp
from datetime import datetime, timezone
from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.monitoring.market_reporter import MarketReporter
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('test')

class TopSymbolsManager:
    def __init__(self, exchange_mgr):
        self.exchange_mgr = exchange_mgr
        self._market_data_cache = {}
        self._symbols_cache = None
        self._symbols_cache_time = 0
        self.CACHE_TTL = 300  # 5 minutes
    
    def _format_symbol(self, symbol: str, reverse=False) -> str:
        """Format symbol for API calls."""
        if reverse:
            # Convert BTCUSDT to BTC/USDT
            if 'USDT' in symbol:
                return f"{symbol[:-4]}/USDT"
            return symbol
        else:
            # Convert BTC/USDT to BTCUSDT
            return symbol.replace('/', '')
    
    async def get_top_traded_symbols(self, limit=20):
        """Get top traded symbols by volume."""
        try:
            # Check cache
            current_time = time.time()
            if self._symbols_cache and (current_time - self._symbols_cache_time) < self.CACHE_TTL:
                return self._symbols_cache[:limit]
            
            exchange = await self.exchange_mgr.get_primary_exchange()
            markets = await exchange.get_markets()
            
            # Sort markets by volume
            sorted_markets = sorted(
                [(market['symbol'], float(market.get('volume', 0))) for market in markets],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Format symbols and store in cache
            self._symbols_cache = [self._format_symbol(symbol, reverse=True) for symbol, _ in sorted_markets]
            self._symbols_cache_time = current_time
            
            return self._symbols_cache[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top traded symbols: {str(e)}")
            return []
    
    async def get_market_data(self, symbol, timeframe='1h', limit=100):
        """Get market data for a symbol."""
        try:
            exchange = await self.exchange_mgr.get_primary_exchange()
            
            # Format symbol for API call
            formatted_symbol = self._format_symbol(symbol)
            
            # Check cache
            cache_key = f"{formatted_symbol}_{timeframe}"
            current_time = time.time()
            if cache_key in self._market_data_cache:
                cached_data, cache_time = self._market_data_cache[cache_key]
                if current_time - cache_time < self.CACHE_TTL:
                    return cached_data
            
            # Get current ticker data
            ticker = await exchange.get_ticker(formatted_symbol)
            
            if not ticker:
                logger.warning(f"No ticker data returned for {symbol}")
                return None
            
            # Format the data
            market_data = {
                'timestamp': [ticker['timestamp']],
                'open': [float(ticker['open'])],
                'high': [float(ticker['high'])],
                'low': [float(ticker['low'])],
                'close': [float(ticker['last'])],
                'volume': [float(ticker['volume'])]
            }
            
            # Cache the data
            self._market_data_cache[cache_key] = (market_data, current_time)
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            return None

class AlertManager:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        self.webhook_url = config_mgr.get_value("monitoring.alerts.discord_webhook_url", None)
    
    async def send_alert(self, content):
        if not self.webhook_url:
            logger.error("No Discord webhook URL provided")
            return False
        
        async with aiohttp.ClientSession() as session:
            payload = {"content": content}
            headers = {"Content-Type": "application/json"}
            
            try:
                async with session.post(self.webhook_url, json=payload, headers=headers) as response:
                    if response.status == 204:
                        logger.info("Successfully sent alert to Discord")
                        return True
                    else:
                        logger.error(f"Failed to send to Discord: {response.status}")
                        return False
            except Exception as e:
                logger.error(f"Error sending to Discord: {str(e)}")
                return False

async def send_to_discord(webhook_url: str, content: str) -> None:
    """Send a message to Discord using a webhook."""
    if not webhook_url:
        logger.error("No Discord webhook URL provided")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json={'content': content}) as response:
                if response.status == 204:
                    logger.info("Successfully sent message to Discord")
                else:
                    logger.error(f"Failed to send message to Discord. Status: {response.status}")
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")

async def main():
    # Initialize dependencies
    config_mgr = ConfigManager()
    exchange_mgr = ExchangeManager(config_mgr)
    await exchange_mgr.initialize()
    
    # Get Discord webhook URL from config
    webhook_url = config_mgr.get_value("monitoring.alerts.discord_webhook_url", None)
    logger.info(f"Using Discord webhook URL: {webhook_url}")

    # Schedule market reports
    report_times = ["00:00", "08:00", "16:00", "20:00"]
    logger.info(f"Market reports scheduled for: {', '.join(t + ' UTC' for t in report_times)}")

    # Generate market report
    logger.info("Generating market report...")
    logger.info(f"Starting market report generation at {datetime.now(timezone.utc)}")

    # Get top traded symbols
    logger.info("Getting top traded symbols...")
    exchange = await exchange_mgr.get_primary_exchange()
    
    try:
        # Directly make API request to get tickers 
        response = await exchange._make_request('GET', '/v5/market/tickers', {'category': 'linear'})
        
        # Also get spot BTC ticker
        spot_response = await exchange._make_request('GET', '/v5/market/tickers', {'category': 'spot', 'symbol': 'BTCUSDT'})
        
        # Process tickers to get top pairs by volume
        ticker_list = []
        markets = []
        
        if isinstance(response, dict) and 'result' in response and 'list' in response['result']:
            ticker_list = response['result']['list']
            
            # Process all tickers without filtering by validation
            for ticker in ticker_list:
                try:
                    # Skip pairs that don't have required fields
                    if not all(key in ticker for key in ['symbol', 'volume24h', 'turnover24h', 'lastPrice']):
                        continue
                        
                    # Skip zero volume markets
                    volume24h = float(ticker.get('volume24h', 0))
                    if volume24h <= 0:
                        continue
                        
                    turnover24h = float(ticker.get('turnover24h', 0))
                    markets.append({
                        'symbol': ticker['symbol'],
                        'volume24h': volume24h,
                        'turnover24h': turnover24h,
                        'last_price': float(ticker.get('lastPrice', 0)),
                        'high24h': float(ticker.get('highPrice24h', 0)),
                        'low24h': float(ticker.get('lowPrice24h', 0)),
                        'price_change_24h': float(ticker.get('price24hPcnt', 0)) * 100
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error processing ticker {ticker.get('symbol', 'unknown')}: {e}")
                    continue
        
        # Sort by volume and get top 20
        top_pairs = sorted(markets, key=lambda x: x['volume24h'], reverse=True)[:20]
        logger.info(f"Found {len(top_pairs)} top traded pairs")

        # Calculate market overview
        logger.info("Calculating market overview...")
        total_volume = sum(market['volume24h'] for market in markets) if markets else 0
        total_turnover = sum(market['turnover24h'] for market in markets) if markets else 0
        total_open_interest = sum(float(ticker.get('openInterestValue', 0)) for ticker in ticker_list) if ticker_list else 0
        logger.debug(f"Historical metrics: volume={total_volume}, turnover={total_turnover}, open_interest={total_open_interest}")

        # Calculate market regime
        logger.info("Calculating market regime...")
        market_regime = {}
        btc_price = 0
        btc_24h_change = 0
        
        try:
            btc_ticker = next((t for t in ticker_list if t['symbol'] == 'BTCUSDT'), None)
            if btc_ticker:
                btc_price = float(btc_ticker['lastPrice'])
                btc_24h_change = float(btc_ticker['price24hPcnt']) * 100
                regime_status = "Bullish" if btc_24h_change > 0 else "Bearish"
                market_regime = {
                    'status': regime_status,
                    'btc_price': btc_price,
                    'btc_change_24h': btc_24h_change,
                    'volatility': abs(btc_24h_change) * 0.1,  # Simplified volatility calculation
                    'strength': abs(btc_24h_change) * 2,      # Simplified strength calculation
                    'trend_confirmation': True if abs(btc_24h_change) > 2 else False
                }
            else:
                market_regime = {
                    'status': 'Unknown',
                    'btc_price': 0,
                    'btc_change_24h': 0,
                    'volatility': 0,
                    'strength': 0,
                    'trend_confirmation': False
                }
        except Exception as e:
            logger.error(f"Error calculating market regime: {e}")
            market_regime = {
                'status': 'Unknown',
                'btc_price': 0,
                'btc_change_24h': 0,
                'volatility': 0,
                'strength': 0,
                'trend_confirmation': False
            }

        # Calculate BTC Futures Premium (Contango/Backwardation)
        logger.info("Calculating BTC futures premium...")
        futures_premium = {
            'spot_price': 0,
            'futures_price': 0,
            'premium_percent': 0,
            'status': 'Unknown',
            'quarterly_futures': 0,
            'basis': 0
        }
        
        try:
            # Get spot BTC price
            spot_btc = None
            if spot_response and isinstance(spot_response, dict) and 'result' in spot_response and 'list' in spot_response['result']:
                spot_list = spot_response['result']['list']
                if spot_list:
                    spot_btc = spot_list[0]
            
            # Get futures BTC price (perpetual)
            futures_btc = next((t for t in ticker_list if t['symbol'] == 'BTCUSDT'), None)
            
            # Get quarterly futures if available
            quarterly_futures = next((t for t in ticker_list if t['symbol'] == 'BTCUSD0628'), None)
            if not quarterly_futures:
                quarterly_futures = next((t for t in ticker_list if 'BTCUSD' in t['symbol'] and t['symbol'] != 'BTCUSDT'), None)
            
            if spot_btc and futures_btc:
                spot_price = float(spot_btc['lastPrice'])
                futures_price = float(futures_btc['lastPrice'])
                premium_percent = ((futures_price - spot_price) / spot_price) * 100
                
                quarterly_price = 0
                if quarterly_futures:
                    quarterly_price = float(quarterly_futures['lastPrice'])
                
                futures_premium = {
                    'spot_price': spot_price,
                    'futures_price': futures_price,
                    'premium_percent': premium_percent,
                    'status': 'Contango' if premium_percent > 0 else 'Backwardation',
                    'quarterly_futures': quarterly_price,
                    'basis': ((quarterly_price - spot_price) / spot_price) * 100 if quarterly_price > 0 else 0
                }
        except Exception as e:
            logger.error(f"Error calculating futures premium: {e}")

        # Calculate performance metrics
        logger.info("Calculating performance metrics...")
        performance_metrics = {
            'gainers': [],
            'losers': [],
            'most_volatile': [],
            'volume_leaders': [],
            'market_cap_leaders': []
        }
        
        # Find gainers and losers
        sorted_by_change = sorted(markets, key=lambda x: x['price_change_24h'], reverse=True)
        performance_metrics['gainers'] = sorted_by_change[:5]
        performance_metrics['losers'] = sorted_by_change[-5:][::-1]
        
        # Find most volatile
        sorted_by_volatility = sorted(markets, key=lambda x: abs(x['price_change_24h']), reverse=True)
        performance_metrics['most_volatile'] = sorted_by_volatility[:5]
        
        # Volume leaders are already in top_pairs
        performance_metrics['volume_leaders'] = top_pairs[:5]

        # Format report
        logger.info("Formatting market report...")
        
        # Market Overview Section
        market_overview = f"""# 🌟 **MARKET REPORT** - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

## 📊 **MARKET OVERVIEW**
• **Volume (24h)**: ${total_volume:,.0f}
• **Turnover (24h)**: ${total_turnover:,.0f}
• **Open Interest**: ${total_open_interest:,.0f}
"""

        # Market Regime Section
        regime_emoji = "🟢" if market_regime['status'] == "Bullish" else "🔴" if market_regime['status'] == "Bearish" else "⚪"
        market_regime_section = f"""
## {regime_emoji} **MARKET REGIME: {market_regime['status'].upper()}**
• **BTC Price**: ${market_regime['btc_price']:,.2f}
• **24h Change**: {market_regime['btc_change_24h']:+.2f}%
• **Volatility**: {'High' if market_regime['volatility'] > 2 else 'Medium' if market_regime['volatility'] > 1 else 'Low'}
• **Trend Strength**: {'Strong' if market_regime['strength'] > 5 else 'Moderate' if market_regime['strength'] > 2 else 'Weak'}
"""

        # Futures Premium Section (Contango/Backwardation)
        premium_emoji = "📈" if futures_premium['status'] == "Contango" else "📉" if futures_premium['status'] == "Backwardation" else "⚖️"
        futures_section = f"""
## {premium_emoji} **BTC FUTURES PREMIUM: {futures_premium['status'].upper()}**
• **Spot Price**: ${futures_premium['spot_price']:,.2f}
• **Perp Price**: ${futures_premium['futures_price']:,.2f}
• **Premium**: {futures_premium['premium_percent']:+.4f}%
"""
        if futures_premium['quarterly_futures'] > 0:
            futures_section += f"• **Quarterly Price**: ${futures_premium['quarterly_futures']:,.2f}\n"
            futures_section += f"• **Quarterly Basis**: {futures_premium['basis']:+.4f}%\n"

        # Top Trading Pairs Section
        top_pairs_section = f"""
## 💹 **TOP TRADING PAIRS (24h)**
"""
        if top_pairs:
            for i, pair in enumerate(top_pairs, 1):
                change_emoji = "🟢" if pair['price_change_24h'] > 0 else "🔴"
                top_pairs_section += f"{i}. {pair['symbol']}: ${pair['volume24h']:,.0f} | {change_emoji} {pair['price_change_24h']:+.2f}%\n"
        else:
            top_pairs_section += "No trading pairs data available\n"
            
        # Performance Metrics Section
        performance_section = f"""
## 📈 **PERFORMANCE METRICS**

### Top Gainers (24h)
"""
        for i, gainer in enumerate(performance_metrics['gainers'], 1):
            performance_section += f"{i}. {gainer['symbol']}: {gainer['price_change_24h']:+.2f}%\n"
            
        performance_section += f"""
### Top Losers (24h)
"""
        for i, loser in enumerate(performance_metrics['losers'], 1):
            performance_section += f"{i}. {loser['symbol']}: {loser['price_change_24h']:+.2f}%\n"
            
        performance_section += f"""
### Most Volatile (24h)
"""
        for i, volatile in enumerate(performance_metrics['most_volatile'], 1):
            performance_section += f"{i}. {volatile['symbol']}: {abs(volatile['price_change_24h']):.2f}% volatility\n"

        # Combine all sections
        report = market_overview + market_regime_section + futures_section + top_pairs_section + performance_section

        # Send report to Discord
        if webhook_url:
            await send_to_discord(webhook_url, report)
        else:
            print(report)

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main()) 