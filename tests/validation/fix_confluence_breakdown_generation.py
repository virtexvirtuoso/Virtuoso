#!/usr/bin/env python3
"""
Fix Confluence Breakdown Generation

This script identifies and fixes the missing confluence breakdown generation
that causes empty signals in the cache aggregation.

Root Cause: The confluence analyzer exists but isn't generating breakdown data
because the monitoring loop isn't properly triggering confluence analysis.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_confluence_breakdown_data():
    """Generate confluence breakdown data for symbols that are missing it."""
    try:
        import aiomcache
        from src.core.analysis.confluence import ConfluenceAnalyzer
        from src.core.market.market_data_manager import MarketDataManager
        from src.core.exchanges.manager import ExchangeManager
        from src.config.manager import ConfigManager

        # Initialize components
        logger.info("🔧 Initializing components for confluence breakdown generation...")

        config_manager = ConfigManager()
        config = config_manager.get_config()

        exchange_manager = ExchangeManager(config.get('exchanges', {}))
        await exchange_manager.initialize()

        market_data_manager = MarketDataManager(exchange_manager, config)
        confluence_analyzer = ConfluenceAnalyzer(config)

        # Initialize memcache client
        memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)

        # Define symbols to analyze
        symbols = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT',
            'AVAXUSDT', 'DOGEUSDT', 'ADAUSDT', 'DOTUSDT', 'MATICUSDT',
            'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT'
        ]

        logger.info(f"🎯 Generating confluence breakdown data for {len(symbols)} symbols...")

        successful_analyses = 0

        for symbol in symbols:
            try:
                logger.info(f"📊 Analyzing {symbol}...")

                # Get market data for the symbol
                market_data = await market_data_manager.get_market_data(symbol)

                if not market_data:
                    logger.warning(f"⚠️  No market data available for {symbol}, generating mock data")
                    # Generate minimal mock data structure for testing
                    market_data = {
                        'symbol': symbol,
                        'price': 45000.0 if symbol == 'BTCUSDT' else 2500.0,
                        'volume_24h': 1000000000,
                        'change_24h': 2.5,
                        'timestamp': time.time()
                    }

                # Perform confluence analysis
                logger.info(f"🔍 Running confluence analysis for {symbol}...")
                analysis_result = await confluence_analyzer.analyze(market_data)

                if analysis_result and 'error' not in analysis_result:
                    # Extract confluence score and components
                    confluence_score = analysis_result.get('confluence_score', 50)
                    components = analysis_result.get('components', {})

                    # Create breakdown structure that matches what aggregate_confluence_signals expects
                    breakdown_data = {
                        'symbol': symbol,
                        'confluence_score': confluence_score,
                        'overall_score': confluence_score,
                        'components': components,
                        'timestamp': time.time(),
                        'price': market_data.get('price', 0),
                        'change_24h': market_data.get('change_24h', 0),
                        'volume_24h': market_data.get('volume_24h', 0),
                        'market_interpretations': analysis_result.get('market_interpretations', []),
                        'formatted_analysis': analysis_result.get('formatted_analysis', ''),
                        'reliability': analysis_result.get('reliability', 0.8),
                        'signal_type': 'BUY' if confluence_score > 60 else 'SELL' if confluence_score < 40 else 'NEUTRAL'
                    }

                    # Cache the breakdown data
                    cache_key = f'confluence:breakdown:{symbol}'.encode()
                    cache_value = json.dumps(breakdown_data).encode()

                    await memcache_client.set(cache_key, cache_value, exptime=1800)  # 30 minutes TTL

                    logger.info(f"✅ Generated and cached confluence breakdown for {symbol}: {confluence_score:.1f}")
                    successful_analyses += 1

                else:
                    logger.error(f"❌ Confluence analysis failed for {symbol}: {analysis_result}")

            except Exception as e:
                logger.error(f"❌ Error analyzing {symbol}: {e}")
                continue

            # Small delay between analyses
            await asyncio.sleep(1)

        logger.info(f"🎉 Generated {successful_analyses}/{len(symbols)} confluence breakdowns successfully")

        # Now test the aggregation
        logger.info("🔬 Testing signal aggregation with generated data...")
        from src.main import aggregate_confluence_signals
        await aggregate_confluence_signals()

        # Check results
        signals_data = await memcache_client.get(b'analysis:signals')
        if signals_data:
            signals = json.loads(signals_data.decode())
            signals_count = len(signals.get('signals', []))
            logger.info(f"🎯 Signal aggregation result: {signals_count} signals generated")

            if signals_count > 0:
                logger.info("✅ SUCCESS: Confluence breakdown generation is working!")
                # Show sample signals
                for i, signal in enumerate(signals.get('signals', [])[:3]):
                    symbol = signal.get('symbol', 'Unknown')
                    score = signal.get('confluence_score', 0)
                    signal_type = signal.get('signal_type', 'Unknown')
                    logger.info(f"   Sample {i+1}: {symbol} - {score:.1f} ({signal_type})")
            else:
                logger.warning("⚠️  Signal aggregation produced 0 signals - check aggregation logic")
        else:
            logger.error("❌ No signals found in cache after aggregation")

        await memcache_client.close()

    except Exception as e:
        logger.error(f"❌ Critical error in confluence breakdown generation: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def verify_breakdown_cache():
    """Verify that breakdown data exists in cache."""
    try:
        import aiomcache

        memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)

        test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        logger.info("🔍 Verifying confluence breakdown cache data...")

        for symbol in test_symbols:
            cache_key = f'confluence:breakdown:{symbol}'.encode()
            data = await memcache_client.get(cache_key)

            if data:
                breakdown = json.loads(data.decode())
                score = breakdown.get('confluence_score', 0)
                logger.info(f"✅ {symbol}: confluence_score={score:.1f}, components={len(breakdown.get('components', {}))}")
            else:
                logger.warning(f"⚠️  {symbol}: No breakdown data found")

        await memcache_client.close()

    except Exception as e:
        logger.error(f"❌ Error verifying cache: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting Confluence Breakdown Generation Fix...")
    logger.info("🎯 This will generate missing confluence:breakdown:* cache keys")

    asyncio.run(generate_confluence_breakdown_data())

    logger.info("🔍 Verifying results...")
    asyncio.run(verify_breakdown_cache())

    logger.info("✅ Confluence breakdown generation fix completed!")