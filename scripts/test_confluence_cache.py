#!/usr/bin/env python3
"""Test confluence data in cache"""

import asyncio
import json
import aiomcache

async def check_confluence():
    """Check if confluence data is in cache"""
    client = aiomcache.Client('localhost', 11211)
    
    print("Checking confluence data in cache...")
    print("-" * 40)
    
    try:
        # Check dedicated confluence key
        confluence = await client.get(b'analysis:confluence')
        if confluence:
            data = json.loads(confluence.decode())
            scores = data.get('confluence_scores', [])
            print(f"✓ analysis:confluence: {len(scores)} scores")
            if scores:
                first_score = scores[0]
                symbol = first_score.get('symbol', '')
                score = first_score.get('score', 0)
                signal = first_score.get('signal', 'unknown')
                print(f"  Example: {symbol} = {score:.1f} ({signal})")
        else:
            print("✗ analysis:confluence: empty")
        
        # Check enhanced tickers
        tickers = await client.get(b'market:tickers')
        if tickers:
            data = json.loads(tickers.decode())
            confluence_count = 0
            example_symbol = None
            example_score = None
            
            for symbol, ticker_data in data.items():
                if 'confluence_score' in ticker_data:
                    confluence_count += 1
                    if not example_symbol:
                        example_symbol = symbol
                        example_score = ticker_data['confluence_score']
            
            print(f"✓ market:tickers: {len(data)} symbols, {confluence_count} with confluence")
            if example_symbol:
                print(f"  Example: {example_symbol} = {example_score:.1f}")
        else:
            print("✗ market:tickers: empty")
        
        # Check enhanced signals
        signals = await client.get(b'analysis:signals')
        if signals:
            data = json.loads(signals.decode())
            signals_list = data.get('signals', [])
            confluence_signals = len([s for s in signals_list if 'confluence_score' in s])
            print(f"✓ analysis:signals: {len(signals_list)} signals, {confluence_signals} with confluence")
            if confluence_signals > 0:
                conf_signal = next((s for s in signals_list if 'confluence_score' in s), None)
                if conf_signal:
                    symbol = conf_signal.get('symbol', '')
                    score = conf_signal.get('confluence_score', 0)
                    signal = conf_signal.get('confluence_signal', 'unknown')
                    print(f"  Example: {symbol} = {score:.1f} ({signal})")
        else:
            print("✗ analysis:signals: empty")
        
        await client.close()
        
    except Exception as e:
        print(f"Error: {e}")
        await client.close()

if __name__ == "__main__":
    asyncio.run(check_confluence())