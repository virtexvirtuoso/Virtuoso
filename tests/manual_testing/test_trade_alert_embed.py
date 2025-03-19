import os
import json
import aiohttp
import asyncio
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("trade_alert_embed_test")

async def send_trade_alert_embed():
    """Send a test trade alert embed to Discord webhook"""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable not set!")
        return
    
    logger.info(f"Using webhook URL: {webhook_url[:20]}...")
    
    # Create a trade alert embed that matches our _format_risk_management_alert method
    symbol = "BTCUSDT"
    signal_type = "BUY"
    score = 71.5
    price = 60123.45
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Calculate default targets
    stop_loss = price * 0.97
    t1_price = price * 1.02
    t2_price = price * 1.045
    t3_price = price * 1.07
    
    targets_text = (
        f"T1: ${t1_price:.2f} (2.00%) - 25%\n"
        f"T2: ${t2_price:.2f} (4.50%) - 50%\n"
        f"T3: ${t3_price:.2f} (7.00%) - 25%"
    )
    
    # Format interpretations
    interpretation_text = (
        "**VOLUME (72.0)**: Volume indicates strong buying pressure\n"
        "**ORDERBOOK (68.0)**: Bid support stronger than asks\n"
        "**ORDERFLOW (76.0)**: Recent large buys detected\n"
        "**TECHNICAL (65.0)**: Multiple indicators showing bullish reversal\n"
        "**PRICE_STRUCTURE (69.0)**: Higher lows forming on 1h timeframe"
    )
    
    # Calculate risk/reward ratio
    risk = price - stop_loss
    reward = t3_price - price
    risk_reward = reward / risk
    
    # Create the embed payload
    embed = {
        "title": f"🟢 TRADE ALERT: {symbol} 🟢",
        "description": f"**{signal_type} SIGNAL | CONFLUENCE SCORE: {score:.1f}/100**\n\nCurrent Price: ${price:.2f}\n\nTimestamp: {timestamp}",
        "color": 3066993,  # Green
        "fields": [
            {
                "name": "📊 ENTRY & EXITS",
                "value": f"**Stop Loss:** ${stop_loss:.2f} ({abs((stop_loss / price) - 1) * 100:.2f}%)\n**Targets:**\n{targets_text}",
                "inline": True
            },
            {
                "name": "⚖️ RISK MANAGEMENT",
                "value": f"**Risk/Reward Ratio:** {risk_reward:.2f}\n**Recommended Leverage:** 1.0x\n**Position Size:** 5.0%",
                "inline": True
            },
            {
                "name": "🔍 DETAILED ANALYSIS",
                "value": interpretation_text
            }
        ],
        "footer": {
            "text": "Virtuoso Trading Bot"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Final webhook payload
    payload = {
        "embeds": [embed]
    }
    
    logger.info(f"Sending trade alert payload:\n{json.dumps(payload, indent=2)}")
    
    # Send the webhook
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json=payload) as response:
                status = response.status
                logger.info(f"Discord API response: {status}")
                
                if status == 204:
                    logger.info("✅ Success! The trade alert embed was sent correctly.")
                else:
                    error_text = await response.text()
                    logger.error(f"Discord error: {error_text}")
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")

async def main():
    await send_trade_alert_embed()
    logger.info("Trade alert embed test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 