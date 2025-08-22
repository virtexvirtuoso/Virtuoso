#!/usr/bin/env python3
"""Sync real confluence scores with full component breakdown to dashboard cache."""

import asyncio
import aiomcache
import json
import logging
import time
import subprocess
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def parse_confluence_breakdown():
    """Parse the detailed confluence breakdown from logs."""
    try:
        # Get recent confluence analysis
        cmd = "sudo journalctl -u virtuoso --since '2 minutes ago' | grep -A100 'CONFLUENCE ANALYSIS'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if not result.stdout:
            return None
        
        lines = result.stdout.split('\n')
        
        # Parse the structured output
        breakdown = {
            'symbol': None,
            'overall_score': None,
            'sentiment': None,
            'reliability': None,
            'components': {},
            'sub_components': {},
            'interpretations': {},
            'timestamp': int(time.time())
        }
        
        parsing_components = False
        parsing_sub_components = False
        parsing_interpretations = False
        current_interpretation = None
        interpretation_text = []
        
        for line in lines:
            # Parse symbol
            if 'CONFLUENCE ANALYSIS' in line:
                match = re.search(r'(\w+USDT) CONFLUENCE ANALYSIS', line)
                if match:
                    breakdown['symbol'] = match.group(1)
            
            # Parse overall score
            elif 'Overall Score:' in line:
                match = re.search(r'Overall Score: ([\d.]+) \((\w+)\)', line)
                if match:
                    breakdown['overall_score'] = float(match.group(1))
                    breakdown['sentiment'] = match.group(2)
            
            # Parse reliability
            elif 'Reliability:' in line:
                match = re.search(r'Reliability: (\d+)% \((\w+)\)', line)
                if match:
                    breakdown['reliability'] = int(match.group(1))
                    breakdown['reliability_level'] = match.group(2)
            
            # Parse component breakdown table
            elif 'Component Breakdown' in line:
                parsing_components = True
                parsing_sub_components = False
                parsing_interpretations = False
            
            elif parsing_components and '║' in line and 'Component' not in line and '═' not in line:
                # Parse component row: Aug 21 02:58:40 virtuoso virtuoso[18241]: ║ Orderbook       ║ 59.99 ║   15.0 ║
                # Extract just the table part after the journal prefix
                table_part = line.split('virtuoso[')[1].split(']: ', 1)[1] if 'virtuoso[' in line else line
                parts = [p.strip() for p in table_part.split('║') if p.strip()]
                if len(parts) >= 3:
                    component_name = parts[0].lower().replace(' ', '_')
                    try:
                        score = float(re.sub(r'\x1b\[[0-9;]+m', '', parts[1]))  # Remove color codes
                        impact = float(parts[2])
                        breakdown['components'][component_name] = {
                            'score': score,
                            'impact': impact,
                            'weight': impact / 100.0  # Convert to weight
                        }
                    except (ValueError, IndexError):
                        pass
            
            # Parse sub-components
            elif 'Top Influential Individual Components' in line:
                parsing_components = False
                parsing_sub_components = True
                parsing_interpretations = False
            
            elif parsing_sub_components and '║' in line and 'Component' not in line and '═' not in line:
                # Parse sub-component row: Aug 21 02:58:40 virtuoso virtuoso[18241]: ║ manipulation          ║ Orderbook ║  92.50 ║   ↑   ║
                table_part = line.split('virtuoso[')[1].split(']: ', 1)[1] if 'virtuoso[' in line else line
                parts = [p.strip() for p in table_part.split('║') if p.strip()]
                if len(parts) >= 4:
                    sub_name = parts[0].lower().replace(' ', '_')
                    parent = parts[1].lower().replace(' ', '_')
                    try:
                        score = float(re.sub(r'\x1b\[[0-9;]+m', '', parts[2]))
                        trend = parts[3].strip()
                        breakdown['sub_components'][sub_name] = {
                            'score': score,
                            'parent': parent,
                            'trend': trend
                        }
                    except (ValueError, IndexError):
                        pass
            
            # Parse interpretations
            elif 'Market Interpretations' in line:
                parsing_components = False
                parsing_sub_components = False
                parsing_interpretations = True
            
            elif parsing_interpretations and '║' in line and '═' not in line:
                table_part = line.split('virtuoso[')[1].split(']: ', 1)[1] if 'virtuoso[' in line else line
                parts = [p.strip() for p in table_part.split('║') if p.strip()]
                if len(parts) >= 2:
                    if parts[0] and parts[0] != 'Component':
                        # New component interpretation
                        if current_interpretation and interpretation_text:
                            breakdown['interpretations'][current_interpretation] = ' '.join(interpretation_text)
                        current_interpretation = parts[0].lower().replace(' ', '_')
                        interpretation_text = [parts[1]] if len(parts) > 1 and parts[1] else []
                    elif len(parts) == 1 and current_interpretation:
                        # Continuation of previous interpretation
                        interpretation_text.append(parts[0])
                elif len(parts) == 1 and current_interpretation and 'virtuoso[' in line:
                    # Handle continuation lines that only have content
                    interpretation_text.append(parts[0])
        
        # Save last interpretation
        if current_interpretation and interpretation_text:
            breakdown['interpretations'][current_interpretation] = ' '.join(interpretation_text)
        
        return breakdown if breakdown['symbol'] else None
        
    except Exception as e:
        logger.error(f"Failed to parse confluence breakdown: {e}")
        import traceback
        traceback.print_exc()
        return None

async def sync_detailed_confluence():
    """Sync detailed confluence analysis to cache."""
    try:
        # Parse the breakdown
        breakdown = await parse_confluence_breakdown()
        
        if not breakdown or not breakdown['symbol']:
            logger.warning("No confluence breakdown found in recent logs")
            return False
        
        # Connect to cache
        client = aiomcache.Client('localhost', 11211, pool_size=2)
        
        # Store detailed breakdown
        symbol = breakdown['symbol']
        
        # Create enhanced signal with full breakdown
        signal = {
            'symbol': symbol,
            'score': breakdown['overall_score'],
            'sentiment': breakdown['sentiment'],
            'reliability': breakdown['reliability'],
            'components': breakdown['components'],
            'sub_components': breakdown['sub_components'],
            'interpretations': breakdown['interpretations'],
            'signal_strength': 'strong' if breakdown['overall_score'] > 70 else 'moderate' if breakdown['overall_score'] > 50 else 'weak',
            'action': 'buy' if breakdown['sentiment'] == 'BULLISH' else 'sell' if breakdown['sentiment'] == 'BEARISH' else 'hold',
            'timestamp': breakdown['timestamp'],
            'real_confluence': True,
            'has_breakdown': True
        }
        
        # Store in multiple cache keys for different access patterns
        
        # 1. Full breakdown
        await client.set(
            f'confluence:breakdown:{symbol}'.encode(),
            json.dumps(breakdown).encode(),
            exptime=300
        )
        
        # 2. Simple confluence score
        await client.set(
            f'confluence:{symbol}'.encode(),
            json.dumps({
                'score': breakdown['overall_score'],
                'sentiment': breakdown['sentiment'],
                'components': breakdown['components'],
                'timestamp': breakdown['timestamp']
            }).encode(),
            exptime=300
        )
        
        # 3. Update signals list
        signals_data = await client.get(b'analysis:signals')
        if signals_data:
            signals = json.loads(signals_data.decode())
        else:
            signals = {'signals': [], 'timestamp': int(time.time())}
        
        # Update or add signal
        signal_found = False
        for i, existing_signal in enumerate(signals.get('signals', [])):
            if existing_signal.get('symbol') == symbol:
                signals['signals'][i] = signal
                signal_found = True
                break
        
        if not signal_found:
            signals['signals'].append(signal)
        
        signals['timestamp'] = int(time.time())
        
        await client.set(
            b'analysis:signals',
            json.dumps(signals).encode(),
            exptime=300
        )
        
        # 4. Store latest breakdown for dashboard
        await client.set(
            b'dashboard:latest_breakdown',
            json.dumps(breakdown).encode(),
            exptime=300
        )
        
        logger.info(f"✅ Synced detailed confluence for {symbol}:")
        logger.info(f"   Score: {breakdown['overall_score']} ({breakdown['sentiment']})")
        logger.info(f"   Reliability: {breakdown['reliability']}%")
        logger.info(f"   Components: {list(breakdown['components'].keys())}")
        logger.info(f"   Sub-components: {len(breakdown['sub_components'])} tracked")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync detailed confluence: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run detailed confluence sync service."""
    while True:
        try:
            success = await sync_detailed_confluence()
            if success:
                logger.info("✅ Successfully synced detailed confluence breakdown")
            else:
                logger.debug("No new breakdown to sync")
            
            # Wait 15 seconds before next sync
            await asyncio.sleep(15)
            
        except KeyboardInterrupt:
            logger.info("Stopping detailed confluence sync...")
            break
        except Exception as e:
            logger.error(f"Sync error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    logger.info("🚀 Starting detailed confluence breakdown sync service...")
    asyncio.run(main())