#!/usr/bin/env python3
"""Add market breadth indicator to dashboard showing up/down market counts."""

import asyncio
import aiomcache
import json
import logging
import time
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_market_breadth():
    """Update dashboard with market breadth data."""
    try:
        # Get real market data from Bybit
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.bybit.com/v5/market/tickers?category=linear&limit=500') as response:
                data = await response.json()
        
        tickers = data['result']['list']
        
        # Count market breadth
        up_count = 0
        down_count = 0
        flat_count = 0
        total_usdt_pairs = 0
        
        for ticker in tickers:
            symbol = ticker['symbol']
            if 'USDT' in symbol:
                total_usdt_pairs += 1
                change = float(ticker['price24hPcnt']) * 100
                
                if change > 0:
                    up_count += 1
                elif change < 0:
                    down_count += 1
                else:
                    flat_count += 1
        
        # Calculate breadth metrics
        breadth_ratio = up_count / (up_count + down_count) if (up_count + down_count) > 0 else 0.5
        breadth_percentage = breadth_ratio * 100
        
        # Determine market sentiment based on breadth
        if breadth_percentage > 70:
            market_sentiment = "strongly_bullish"
            sentiment_emoji = "🚀"
        elif breadth_percentage > 55:
            market_sentiment = "bullish"
            sentiment_emoji = "📈"
        elif breadth_percentage > 45:
            market_sentiment = "neutral"
            sentiment_emoji = "➡️"
        elif breadth_percentage > 30:
            market_sentiment = "bearish"
            sentiment_emoji = "📉"
        else:
            market_sentiment = "strongly_bearish"
            sentiment_emoji = "🔻"
        
        # Connect to cache
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Get existing market overview
        overview_data = await client.get(b'market:overview')
        if overview_data:
            overview = json.loads(overview_data.decode())
        else:
            overview = {}
        
        # Add market breadth data
        overview['market_breadth'] = {
            'up': up_count,
            'down': down_count,
            'flat': flat_count,
            'total': total_usdt_pairs,
            'breadth_ratio': breadth_ratio,
            'breadth_percentage': breadth_percentage,
            'sentiment': market_sentiment,
            'sentiment_emoji': sentiment_emoji,
            'display_text': f"{up_count} ↑ / {down_count} ↓",
            'display_percentage': f"{breadth_percentage:.1f}% Bullish"
        }
        
        # Update timestamp
        overview['timestamp'] = int(time.time())
        
        # Push back to cache
        await client.set(
            b'market:overview',
            json.dumps(overview).encode(),
            exptime=300
        )
        
        # Also create a dedicated market breadth entry for easy access
        breadth_data = {
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'total_markets': total_usdt_pairs,
            'breadth_percentage': breadth_percentage,
            'market_sentiment': market_sentiment,
            'timestamp': int(time.time()),
            # Visual representations
            'bar_chart': {
                'up_width': (up_count / total_usdt_pairs * 100),
                'down_width': (down_count / total_usdt_pairs * 100),
                'flat_width': (flat_count / total_usdt_pairs * 100)
            },
            # Text displays for different contexts
            'displays': {
                'compact': f"{up_count}↑ {down_count}↓",
                'detailed': f"{up_count} up / {down_count} down / {flat_count} flat",
                'percentage': f"{breadth_percentage:.1f}% bullish",
                'ratio': f"{up_count}:{down_count}",
                'sentiment_text': f"{sentiment_emoji} {market_sentiment.replace('_', ' ').title()}"
            }
        }
        
        await client.set(
            b'market:breadth',
            json.dumps(breadth_data).encode(),
            exptime=300
        )
        
        logger.info(f"✅ Market Breadth Updated:")
        logger.info(f"   {up_count} markets up ({up_count/total_usdt_pairs*100:.1f}%)")
        logger.info(f"   {down_count} markets down ({down_count/total_usdt_pairs*100:.1f}%)")
        logger.info(f"   {flat_count} markets flat")
        logger.info(f"   Market sentiment: {sentiment_emoji} {market_sentiment}")
        logger.info(f"   Breadth ratio: {breadth_percentage:.1f}% bullish")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update market breadth: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run market breadth update."""
    success = await update_market_breadth()
    if success:
        logger.info("✅ Market breadth successfully updated!")
    else:
        logger.error("❌ Failed to update market breadth")

if __name__ == "__main__":
    asyncio.run(main())