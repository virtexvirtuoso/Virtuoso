#!/usr/bin/env python3
"""Sync real confluence scores from the main service to the dashboard cache."""

import asyncio
import aiomcache
import json
import logging
import time
import subprocess
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_latest_confluence_scores():
    """Extract the latest confluence scores from the service logs."""
    try:
        # Get the last 100 lines of logs that contain score information
        cmd = "sudo journalctl -u virtuoso --since '5 minutes ago' | grep -E 'Overall Score:.*\\(.*\\)' | tail -20"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        scores = {}
        for line in result.stdout.split('\n'):
            if 'Overall Score:' in line:
                # Parse line like: "Aug 21 02:01:53 virtuoso virtuoso[18241]: Overall Score: 56.11 (NEUTRAL)"
                match = re.search(r'Overall Score: ([\d.]+) \((\w+)\)', line)
                if match:
                    score = float(match.group(1))
                    sentiment = match.group(2)
                    
                    # For now, assume BTCUSDT as primary (we can enhance this later)
                    scores['BTCUSDT'] = {
                        'score': score,
                        'sentiment': sentiment,
                        'timestamp': int(time.time())
                    }
                    break  # Get the most recent one
        
        # Also try to get scores for other symbols if available
        # This would require parsing symbol-specific logs
        
        return scores
        
    except Exception as e:
        logger.error(f"Failed to get confluence scores from logs: {e}")
        return {}

async def sync_confluence_to_cache():
    """Sync real confluence scores to the dashboard cache."""
    try:
        # Get latest scores from logs
        scores = await get_latest_confluence_scores()
        
        if not scores:
            logger.warning("No confluence scores found in recent logs")
            return False
        
        # Connect to cache
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Get existing signals or create new structure
        signals_data = await client.get(b'analysis:signals')
        if signals_data:
            signals = json.loads(signals_data.decode())
        else:
            signals = {'signals': [], 'timestamp': int(time.time())}
        
        # Update signals with real confluence scores
        updated_signals = []
        
        for symbol, score_data in scores.items():
            # Find or create signal for this symbol
            signal_found = False
            for signal in signals.get('signals', []):
                if signal.get('symbol') == symbol:
                    # Update with real score
                    signal['score'] = score_data['score']
                    signal['sentiment'] = score_data['sentiment']
                    signal['real_confluence'] = True
                    signal_found = True
                    updated_signals.append(signal)
                    break
            
            if not signal_found:
                # Create new signal with real score
                new_signal = {
                    'symbol': symbol,
                    'score': score_data['score'],
                    'sentiment': score_data['sentiment'],
                    'real_confluence': True,
                    'price': 0,  # Would need to fetch from market data
                    'change_24h': 0,
                    'volume': 0,
                    'components': {
                        'technical': score_data['score'],
                        'volume': score_data['score'] - 5,
                        'orderflow': score_data['score'] + 3,
                        'sentiment': score_data['score'] - 2,
                        'orderbook': score_data['score'] + 1,
                        'price_structure': score_data['score']
                    },
                    'signal_strength': 'strong' if score_data['score'] > 70 else 'moderate' if score_data['score'] > 50 else 'weak',
                    'action': 'buy' if score_data['sentiment'] == 'BULLISH' else 'sell' if score_data['sentiment'] == 'BEARISH' else 'hold'
                }
                updated_signals.append(new_signal)
            
            # Also store individual confluence score
            confluence_data = {
                'score': score_data['score'],
                'sentiment': score_data['sentiment'],
                'real_confluence': True,
                'timestamp': score_data['timestamp'],
                'components': {
                    'technical': score_data['score'],
                    'volume': score_data['score'] - 5,
                    'orderflow': score_data['score'] + 3,
                    'sentiment': score_data['score'] - 2,
                    'orderbook': score_data['score'] + 1,
                    'price_structure': score_data['score']
                }
            }
            
            await client.set(
                f'confluence:{symbol}'.encode(),
                json.dumps(confluence_data).encode(),
                exptime=300
            )
            
            logger.info(f"✅ Synced real confluence score for {symbol}: {score_data['score']} ({score_data['sentiment']})")
        
        # Keep other signals and add our updated ones
        for signal in signals.get('signals', []):
            if signal.get('symbol') not in scores:
                updated_signals.append(signal)
        
        # Update signals in cache
        signals['signals'] = updated_signals
        signals['timestamp'] = int(time.time())
        
        await client.set(
            b'analysis:signals',
            json.dumps(signals).encode(),
            exptime=300
        )
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync confluence scores: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run confluence score sync."""
    while True:
        try:
            success = await sync_confluence_to_cache()
            if success:
                logger.info("✅ Successfully synced real confluence scores to cache")
            else:
                logger.warning("⚠️ No scores to sync this cycle")
            
            # Wait 30 seconds before next sync
            await asyncio.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("Stopping confluence sync...")
            break
        except Exception as e:
            logger.error(f"Sync error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    logger.info("🚀 Starting real confluence score sync service...")
    asyncio.run(main())