"""
Cache Data Aggregator - Direct Cache Population Service

This module fixes the circular dependency in the monitoring → cache → dashboard data flow
by providing a service that allows the monitoring system to push data DIRECTLY to cache
without relying on API calls that depend on cached data.

Key Features:
- Direct cache population for critical market data keys
- Market data aggregation and processing
- Signal aggregation and processing
- Market movers calculation
- Independent data generation without API dependencies

Solves the circular dependency: monitoring generates → pushes to cache → dashboard retrieves
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque
import statistics
import math
import aiohttp

# Import unified cache writer
from .cache_writer import MonitoringCacheWriter

# Import unified regime enum for consistent labels
from src.core.analysis.market_regime_detector import MarketRegime

logger = logging.getLogger(__name__)


# =============================================================================
# CoinGecko API Integration - Comprehensive Global Market Data
# =============================================================================
_coingecko_global_cache = {
    # Dominance metrics
    'btc_dominance': 57.0,
    'btc_dominance_prev': 57.0,  # For calculating 24h change
    'eth_dominance': 11.5,
    'stablecoin_dominance': 8.0,  # USDT + USDC combined
    # Market cap metrics
    'total_market_cap': 3_000_000_000_000,  # $3T default
    'market_cap_change_24h': 0.0,
    # Volume metrics
    'total_volume_24h': 100_000_000_000,  # $100B default
    # Ecosystem metrics
    'active_cryptocurrencies': 15000,
    'markets': 1000,
    # Metadata
    'last_updated': 0,
    'cache_ttl': 300  # 5 minutes cache
}

_fear_greed_cache = {
    'value': 50,  # 0-100 scale
    'classification': 'Neutral',
    'last_updated': 0,
    'cache_ttl': 3600  # 1 hour cache (updates daily)
}

_defi_cache = {
    'defi_market_cap': 100_000_000_000,  # $100B default
    'defi_dominance': 3.0,
    'defi_volume_24h': 5_000_000_000,  # $5B default
    'top_defi_protocol': 'Lido',
    'top_defi_dominance': 25.0,
    'last_updated': 0,
    'cache_ttl': 600  # 10 minutes cache
}

# =============================================================================
# NEW CoinGecko Integrations (2025-12-16)
# See: docs/08-features/COINGECKO_INTEGRATION_ROADMAP.md
# =============================================================================

_trending_cache = {
    'coins': [],  # Top 7 trending coins
    'nfts': [],   # Top 3 trending NFTs
    'last_updated': 0,
    'cache_ttl': 900  # 15 minutes (trending updates every ~15 min)
}

_derivatives_cache = {
    'contracts': [],         # Top derivative contracts by OI
    'by_symbol': {},         # Contracts grouped by symbol for comparison
    'funding_spreads': {},   # Cross-exchange funding rate spreads
    'total_open_interest': 0,
    'last_updated': 0,
    'cache_ttl': 300  # 5 minutes (funding rates update frequently)
}

_categories_cache = {
    'categories': [],        # Category performance data
    'top_performers': [],    # Top 3 performing categories
    'bottom_performers': [], # Bottom 3 categories
    'rotation_signal': '',   # Sector rotation signal
    'last_updated': 0,
    'cache_ttl': 600  # 10 minutes
}

_exchanges_cache = {
    'exchanges': [],         # Exchange data with volume/trust
    'total_volume_btc': 0,   # Total 24h volume in BTC
    'concentration': {},     # Market concentration metrics
    'last_updated': 0,
    'cache_ttl': 600  # 10 minutes
}

# Global lock to prevent concurrent CoinGecko API calls (rate limit prevention)
# CoinGecko free tier: ~30 requests/minute. Multiple concurrent fetches cause 429 errors.
_coingecko_fetch_lock = asyncio.Lock()


async def fetch_coingecko_global_data() -> dict:
    """
    Fetch comprehensive global market data from CoinGecko's free API.

    Returns all available metrics including:
    - BTC/ETH/Stablecoin dominance
    - Total market cap and 24h change
    - Total volume
    - Active cryptocurrencies count

    Implements retry logic with exponential backoff for resilience.
    """
    global _coingecko_global_cache

    current_time = time.time()

    # Return cached values if still valid
    if current_time - _coingecko_global_cache['last_updated'] < _coingecko_global_cache['cache_ttl']:
        return _coingecko_global_cache.copy()

    # Retry logic with exponential backoff
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.coingecko.com/api/v3/global',
                    timeout=aiohttp.ClientTimeout(total=30)  # Increased from 10 to 30 seconds
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        global_data = data.get('data', {})
                        market_cap_pct = global_data.get('market_cap_percentage', {})

                        # Store previous BTC dominance for calculating change
                        _coingecko_global_cache['btc_dominance_prev'] = _coingecko_global_cache['btc_dominance']

                        # Extract dominance metrics
                        btc_dom = market_cap_pct.get('btc', 0)
                        eth_dom = market_cap_pct.get('eth', 0)
                        usdt_dom = market_cap_pct.get('usdt', 0)
                        usdc_dom = market_cap_pct.get('usdc', 0)

                        if btc_dom > 0:
                            _coingecko_global_cache['btc_dominance'] = round(btc_dom, 2)
                            _coingecko_global_cache['eth_dominance'] = round(eth_dom, 2)
                            _coingecko_global_cache['stablecoin_dominance'] = round(usdt_dom + usdc_dom, 2)

                            # Market cap metrics
                            _coingecko_global_cache['total_market_cap'] = global_data.get('total_market_cap', {}).get('usd', 0)
                            _coingecko_global_cache['market_cap_change_24h'] = round(
                                global_data.get('market_cap_change_percentage_24h_usd', 0), 2
                            )

                            # Volume metrics
                            _coingecko_global_cache['total_volume_24h'] = global_data.get('total_volume', {}).get('usd', 0)

                            # Ecosystem metrics
                            _coingecko_global_cache['active_cryptocurrencies'] = global_data.get('active_cryptocurrencies', 0)
                            _coingecko_global_cache['markets'] = global_data.get('markets', 0)

                            _coingecko_global_cache['last_updated'] = current_time

                            logger.info(
                                f"✅ CoinGecko Global: BTC {btc_dom:.1f}% | ETH {eth_dom:.1f}% | "
                                f"MCap ${_coingecko_global_cache['total_market_cap']/1e12:.2f}T "
                                f"({_coingecko_global_cache['market_cap_change_24h']:+.1f}%)"
                            )
                            return _coingecko_global_cache.copy()  # Success - return immediately
                    else:
                        logger.warning(f"CoinGecko Global API returned status {response.status} (attempt {attempt + 1}/{max_retries})")

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"⏱️ CoinGecko Global API timeout (attempt {attempt + 1}/{max_retries}) - retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                logger.warning("⚠️ CoinGecko Global API timeout after all retries - using cached values")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"CoinGecko Global API error (attempt {attempt + 1}/{max_retries}): {e} - retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                logger.warning(f"⚠️ CoinGecko Global API error after all retries: {e} - using cached values")

    return _coingecko_global_cache.copy()


async def fetch_fear_greed_index() -> dict:
    """
    Fetch Fear & Greed Index from Alternative.me (FREE API).

    Returns:
        dict with 'value' (0-100) and 'classification' (Extreme Fear/Fear/Neutral/Greed/Extreme Greed)

    Implements retry logic with exponential backoff for resilience.
    """
    global _fear_greed_cache

    current_time = time.time()

    # Return cached value if still valid
    if current_time - _fear_greed_cache['last_updated'] < _fear_greed_cache['cache_ttl']:
        return _fear_greed_cache.copy()

    # Retry logic with exponential backoff
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.alternative.me/fng/',
                    timeout=aiohttp.ClientTimeout(total=30)  # Increased from 10 to 30 seconds
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        fng_data = data.get('data', [{}])[0]

                        value = int(fng_data.get('value', 50))
                        classification = fng_data.get('value_classification', 'Neutral')

                        _fear_greed_cache['value'] = value
                        _fear_greed_cache['classification'] = classification
                        _fear_greed_cache['last_updated'] = current_time

                        logger.info(f"✅ Fear & Greed Index: {value} ({classification})")
                        return _fear_greed_cache.copy()  # Success - return immediately
                    else:
                        logger.warning(f"Fear & Greed API returned status {response.status} (attempt {attempt + 1}/{max_retries})")

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"⏱️ Fear & Greed API timeout (attempt {attempt + 1}/{max_retries}) - retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                logger.warning("⚠️ Fear & Greed API timeout after all retries - using cached value")
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Fear & Greed API error (attempt {attempt + 1}/{max_retries}): {e} - retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                logger.warning(f"⚠️ Fear & Greed API error after all retries: {e} - using cached value")

    return _fear_greed_cache.copy()


async def fetch_defi_data() -> dict:
    """
    Fetch DeFi market data from CoinGecko's DeFi endpoint.

    Returns:
        dict with DeFi market cap, dominance, volume, and top protocol
    """
    global _defi_cache

    current_time = time.time()

    # Return cached value if still valid
    if current_time - _defi_cache['last_updated'] < _defi_cache['cache_ttl']:
        return _defi_cache.copy()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/global/decentralized_finance_defi',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    defi_data = data.get('data', {})

                    # Parse string values to floats
                    defi_mcap = float(defi_data.get('defi_market_cap', '0') or '0')
                    defi_dom = float(defi_data.get('defi_dominance', '0') or '0')
                    defi_vol = float(defi_data.get('trading_volume_24h', '0') or '0')
                    top_coin = defi_data.get('top_coin_name', 'Unknown')
                    top_dom = float(defi_data.get('top_coin_defi_dominance', 0) or 0)

                    _defi_cache['defi_market_cap'] = defi_mcap
                    _defi_cache['defi_dominance'] = round(defi_dom, 2)
                    _defi_cache['defi_volume_24h'] = defi_vol
                    _defi_cache['top_defi_protocol'] = top_coin
                    _defi_cache['top_defi_dominance'] = round(top_dom, 1)
                    _defi_cache['last_updated'] = current_time

                    logger.info(
                        f"✅ DeFi Data: MCap ${defi_mcap/1e9:.1f}B | "
                        f"Dom {defi_dom:.1f}% | Top: {top_coin} ({top_dom:.1f}%)"
                    )
                else:
                    logger.warning(f"DeFi API returned status {response.status}")
    except asyncio.TimeoutError:
        logger.warning("DeFi API timeout - using cached value")
    except Exception as e:
        logger.warning(f"DeFi API error: {e}")

    return _defi_cache.copy()


# =============================================================================
# NEW FETCH FUNCTIONS: Trending, Derivatives, Categories, Exchanges
# =============================================================================

async def fetch_trending_coins() -> dict:
    """
    Fetch trending coins from CoinGecko's search/trending endpoint.

    Returns top 7 trending coins and top 3 trending NFTs.
    Updates every ~15 minutes on CoinGecko's side.

    Trading Value: Early signal detection for momentum plays.
    Coins appearing on trending often see 10-30% pumps within 24-48 hours.
    """
    global _trending_cache

    current_time = time.time()

    # Return cached value if still valid
    if current_time - _trending_cache['last_updated'] < _trending_cache['cache_ttl']:
        return _trending_cache.copy()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/search/trending',
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    trending_coins = []
                    for coin in data.get('coins', [])[:7]:
                        item = coin.get('item', {})
                        coin_data = item.get('data', {})
                        price_change = coin_data.get('price_change_percentage_24h', {})

                        trending_coins.append({
                            'symbol': item.get('symbol', '').upper(),
                            'name': item.get('name'),
                            'market_cap_rank': item.get('market_cap_rank'),
                            'price_change_24h': price_change.get('usd', 0) if isinstance(price_change, dict) else 0,
                            'score': item.get('score', 0),
                            'thumb': item.get('thumb', '')
                        })

                    trending_nfts = [n.get('name') for n in data.get('nfts', [])[:3]]

                    _trending_cache['coins'] = trending_coins
                    _trending_cache['nfts'] = trending_nfts
                    _trending_cache['last_updated'] = current_time

                    # Log top 3 trending
                    top_3 = ', '.join([f"{c['symbol']}" for c in trending_coins[:3]])
                    logger.info(f"🔥 Trending: {top_3}")
                else:
                    logger.warning(f"Trending API returned status {response.status}")

    except asyncio.TimeoutError:
        logger.warning("Trending API timeout - using cached value")
    except Exception as e:
        logger.warning(f"Trending API error: {e}")

    return _trending_cache.copy()


async def fetch_derivatives_data() -> dict:
    """
    Fetch derivatives (perpetual futures) data from CoinGecko.

    Returns funding rates, open interest, and cross-exchange comparisons.

    Trading Value: Cross-exchange funding rate arbitrage detection.
    When Bybit funding is 0.01% and Binance is -0.02%, there's a 3bp spread to capture.
    """
    global _derivatives_cache

    current_time = time.time()

    # Return cached value if still valid
    if current_time - _derivatives_cache['last_updated'] < _derivatives_cache['cache_ttl']:
        return _derivatives_cache.copy()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/derivatives',
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if not isinstance(data, list):
                        logger.warning("Derivatives API returned unexpected format")
                        return _derivatives_cache.copy()

                    # Group by symbol for cross-exchange comparison
                    by_symbol = {}
                    for contract in data:
                        symbol = contract.get('index_id', '').upper()
                        if not symbol:
                            continue

                        if symbol not in by_symbol:
                            by_symbol[symbol] = []

                        by_symbol[symbol].append({
                            'exchange': contract.get('market', ''),
                            'funding_rate': float(contract.get('funding_rate', 0) or 0),
                            'open_interest': float(contract.get('open_interest', 0) or 0),
                            'index_price': float(contract.get('index', 0) or 0),
                            'volume_24h': float(contract.get('volume_24h', 0) or 0)
                        })

                    # Calculate funding rate spreads for arbitrage detection
                    spreads = {}
                    for symbol, contracts in by_symbol.items():
                        if len(contracts) >= 2:
                            rates = [c['funding_rate'] for c in contracts if c['funding_rate'] != 0]
                            if len(rates) >= 2:
                                spreads[symbol] = {
                                    'max_rate': max(rates),
                                    'min_rate': min(rates),
                                    'spread_bps': round((max(rates) - min(rates)) * 100, 4),
                                    'exchange_count': len(contracts)
                                }

                    # Sort spreads by magnitude for trading opportunities
                    top_spreads = dict(sorted(
                        spreads.items(),
                        key=lambda x: x[1]['spread_bps'],
                        reverse=True
                    )[:10])

                    # Calculate total OI
                    total_oi = sum(
                        float(c.get('open_interest', 0) or 0) for c in data
                    )

                    _derivatives_cache['contracts'] = data[:50]  # Top 50 by OI
                    _derivatives_cache['by_symbol'] = {k: v[:5] for k, v in list(by_symbol.items())[:20]}
                    _derivatives_cache['funding_spreads'] = top_spreads
                    _derivatives_cache['total_open_interest'] = total_oi
                    _derivatives_cache['last_updated'] = current_time

                    logger.info(
                        f"📊 Derivatives: {len(data)} contracts | "
                        f"OI ${total_oi/1e9:.1f}B | "
                        f"{len(top_spreads)} arb opportunities"
                    )
                else:
                    logger.warning(f"Derivatives API returned status {response.status}")

    except asyncio.TimeoutError:
        logger.warning("Derivatives API timeout - using cached value")
    except Exception as e:
        logger.warning(f"Derivatives API error: {e}")

    return _derivatives_cache.copy()


# Categories to track for sector rotation signals
TRACKED_CATEGORIES = [
    'layer-1', 'decentralized-finance-defi', 'meme-token',
    'artificial-intelligence', 'gaming', 'real-world-assets-rwa',
    'liquid-staking-tokens', 'stablecoins'
]


def _detect_rotation_signal(categories: list) -> str:
    """Detect sector rotation signal from category performance."""
    cat_by_id = {c.get('id', ''): c for c in categories}

    defi = cat_by_id.get('decentralized-finance-defi', {})
    l1 = cat_by_id.get('layer-1', {})
    meme = cat_by_id.get('meme-token', {})
    ai = cat_by_id.get('artificial-intelligence', {})

    meme_change = meme.get('change_24h', 0) or 0
    defi_change = defi.get('change_24h', 0) or 0
    l1_change = l1.get('change_24h', 0) or 0
    ai_change = ai.get('change_24h', 0) or 0

    if meme_change > 5:
        return "RISK_ON: Meme coins leading - high risk appetite"
    elif defi_change > l1_change + 2:
        return "DEFI_ROTATION: Capital flowing to DeFi"
    elif ai_change > 3:
        return "AI_NARRATIVE: AI tokens outperforming"
    elif l1_change < -3:
        return "RISK_OFF: L1s declining - defensive positioning"

    return "NEUTRAL: No clear rotation signal"


async def fetch_category_performance() -> dict:
    """
    Fetch category (sector) performance from CoinGecko.

    Returns market cap and 24h change for each category.

    Trading Value: Sector rotation signals for identifying where capital is flowing.
    When DeFi outperforms L1s, rotate into DeFi plays.
    """
    global _categories_cache

    current_time = time.time()

    # Return cached value if still valid
    if current_time - _categories_cache['last_updated'] < _categories_cache['cache_ttl']:
        return _categories_cache.copy()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/coins/categories',
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    categories = []
                    for cat in data:
                        cat_id = cat.get('id', '')
                        market_cap = cat.get('market_cap', 0) or 0
                        volume = cat.get('volume_24h', 0) or 0

                        # Include tracked categories + top 15 by market cap
                        if cat_id in TRACKED_CATEGORIES or len(categories) < 15:
                            categories.append({
                                'id': cat_id,
                                'name': cat.get('name'),
                                'market_cap': market_cap,
                                'change_24h': round(cat.get('market_cap_change_24h', 0) or 0, 2),
                                'volume_24h': volume,
                                'volume_mcap_ratio': round((volume / market_cap * 100), 2) if market_cap > 0 else 0
                            })

                    # Sort by 24h change for rotation signals
                    categories.sort(key=lambda x: x['change_24h'], reverse=True)

                    top_performers = [c['name'] for c in categories[:3]]
                    bottom_performers = [c['name'] for c in categories[-3:]]
                    rotation_signal = _detect_rotation_signal(categories)

                    _categories_cache['categories'] = categories
                    _categories_cache['top_performers'] = top_performers
                    _categories_cache['bottom_performers'] = bottom_performers
                    _categories_cache['rotation_signal'] = rotation_signal
                    _categories_cache['last_updated'] = current_time

                    logger.info(
                        f"🔄 Categories: {len(categories)} tracked | "
                        f"Top: {', '.join(top_performers[:2])} | "
                        f"{rotation_signal.split(':')[0]}"
                    )
                else:
                    logger.warning(f"Categories API returned status {response.status}")

    except asyncio.TimeoutError:
        logger.warning("Categories API timeout - using cached value")
    except Exception as e:
        logger.warning(f"Categories API error: {e}")

    return _categories_cache.copy()


async def fetch_exchange_distribution() -> dict:
    """
    Fetch exchange volume distribution from CoinGecko.

    Returns volume by exchange and concentration metrics.

    Trading Value: Liquidity concentration analysis for execution optimization.
    If 60% of ETH volume is on Binance, that's where you get best execution.
    """
    global _exchanges_cache

    current_time = time.time()

    # Return cached value if still valid
    if current_time - _exchanges_cache['last_updated'] < _exchanges_cache['cache_ttl']:
        return _exchanges_cache.copy()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.coingecko.com/api/v3/exchanges',
                params={'per_page': 20},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    total_volume = sum(
                        float(e.get('trade_volume_24h_btc', 0) or 0) for e in data
                    )

                    exchanges = []
                    for exch in data:
                        vol = float(exch.get('trade_volume_24h_btc', 0) or 0)
                        exchanges.append({
                            'name': exch.get('name'),
                            'id': exch.get('id'),
                            'trust_score': exch.get('trust_score'),
                            'rank': exch.get('trust_score_rank'),
                            'volume_24h_btc': round(vol, 2),
                            'market_share': round(vol / total_volume * 100, 2) if total_volume else 0,
                            'country': exch.get('country')
                        })

                    # Calculate concentration metrics (Herfindahl index)
                    shares = [e['market_share'] for e in exchanges]
                    top_3_share = sum(shares[:3])
                    top_5_share = sum(shares[:5])
                    hhi = sum(s**2 for s in shares) / 100 if shares else 0

                    _exchanges_cache['exchanges'] = exchanges
                    _exchanges_cache['total_volume_btc'] = round(total_volume, 2)
                    _exchanges_cache['concentration'] = {
                        'top_3_share': round(top_3_share, 1),
                        'top_5_share': round(top_5_share, 1),
                        'herfindahl_index': round(hhi, 2)
                    }
                    _exchanges_cache['last_updated'] = current_time

                    logger.info(
                        f"🏦 Exchanges: {len(exchanges)} | "
                        f"Vol {total_volume:,.0f} BTC | "
                        f"Top3 share: {top_3_share:.1f}%"
                    )
                else:
                    logger.warning(f"Exchanges API returned status {response.status}")

    except asyncio.TimeoutError:
        logger.warning("Exchanges API timeout - using cached value")
    except Exception as e:
        logger.warning(f"Exchanges API error: {e}")

    return _exchanges_cache.copy()


async def fetch_btc_dominance_from_coingecko() -> float:
    """
    Legacy function for backward compatibility.
    Now calls the comprehensive fetch and returns just BTC dominance.
    """
    global_data = await fetch_coingecko_global_data()
    return global_data.get('btc_dominance', 57.0)


class CacheDataAggregator:
    """
    Aggregates monitoring data and pushes it directly to cache.

    This service eliminates the circular dependency by allowing the monitoring
    system to populate cache keys directly with generated analysis data.
    """

    def __init__(self, cache_adapter, config: Optional[Dict[str, Any]] = None, exchange=None, shared_cache=None):
        """
        Initialize the cache data aggregator.

        Args:
            cache_adapter: Direct cache adapter instance
            config: Configuration dictionary
            exchange: CCXT exchange instance for fetching market-wide data
            shared_cache: Optional SharedCacheBridge for cross-process communication
        """
        self.cache_adapter = cache_adapter
        self.config = config or {}
        self.exchange = exchange
        self.shared_cache = shared_cache

        # Initialize unified cache writer with shared cache support
        self.cache_writer = MonitoringCacheWriter(cache_adapter, config, shared_cache)

        # Data aggregation storage
        self.signal_buffer = deque(maxlen=100)  # Store recent signals
        self.market_data_buffer = {}  # Store recent market data by symbol
        self.analysis_results_buffer = deque(maxlen=50)  # Store recent analysis results

        # Market movers tracking
        self.price_changes = defaultdict(list)  # Track price changes for movers
        self.volume_changes = defaultdict(list)  # Track volume changes

        # Market-wide data (fetched from exchange)
        self.market_wide_tickers = {}  # All perpetual tickers from exchange
        self.last_ticker_fetch = 0  # Last time we fetched market-wide tickers
        self.ticker_fetch_interval = 60  # Fetch tickers every 60 seconds

        # Volatility history for calculating average (rolling 24-hour window)
        self.volatility_history = deque(maxlen=1440)  # 1440 minutes = 24 hours (1 sample/min)

        # BTC price history for realized volatility (rolling 30-day window)
        # Store daily snapshots: {timestamp, price}
        self.btc_price_history = deque(maxlen=30)  # 30 days of daily prices
        self.last_btc_snapshot = 0  # Last time we took a BTC price snapshot

        # Statistics
        self.aggregation_count = 0
        self.last_aggregation_time = 0
        self.cache_push_count = 0
        self.cache_push_errors = 0

        # Initialization flag
        self._initialized = False

    async def initialize(self) -> None:
        """
        Pre-warm cache on startup with critical market data.

        Strategy:
        1. First, try to warm cache from Redis (instant - persisted data from last run)
        2. Then, fetch fresh market data to update the cache

        This provides instant data availability while ensuring fresh data flows in.
        """
        logger.info("🔥 Cache Aggregator: Pre-warming cache on startup...")
        start_time = time.time()

        try:
            # PHASE 1: Try to warm from Redis (instant data from last run)
            # This makes cached data available immediately without waiting for API calls
            if hasattr(self.cache_adapter, 'warm_from_redis'):
                try:
                    warm_results = await self.cache_adapter.warm_from_redis()
                    warmed = sum(1 for v in warm_results.values() if v)
                    if warmed > 0:
                        logger.info(f"⚡ Instant cache: {warmed} keys restored from Redis in {time.time() - start_time:.2f}s")
                    else:
                        logger.info("📭 No cached data in Redis - fetching fresh data")
                except Exception as e:
                    logger.warning(f"Redis warm-up failed (will fetch fresh): {e}")

            # PHASE 2: Fetch fresh market data (updates the cached data)
            # Bypass the 60-second rate limit for initial fetch
            self.last_ticker_fetch = 0

            # Fetch market-wide tickers immediately
            ticker_success = await self._fetch_market_wide_tickers()

            if ticker_success:
                # Immediately populate market movers cache
                await self._update_market_movers()
                logger.info(f"✅ Pre-warmed market:movers with {len(self.market_wide_tickers)} symbols")
            else:
                logger.warning("⚠️ Could not fetch initial tickers - using Redis cache if available")

            # Take initial BTC snapshot for volatility calculations
            await self._track_btc_price()

            # Set initial market overview (even with minimal data)
            await self._update_market_overview()

            elapsed = time.time() - start_time
            self._initialized = True
            logger.info(f"✅ Cache pre-warming complete in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Error during cache pre-warming: {e}", exc_info=True)
            # Don't fail startup, just log the error
            self._initialized = True  # Mark as initialized anyway to proceed

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the cache data aggregator.

        Returns:
            Dict with health status including:
            - initialized: bool - whether aggregator is initialized
            - healthy: bool - overall health status
            - cache_push_count: int - total successful cache pushes
            - cache_push_errors: int - total cache push errors
            - last_aggregation: float - timestamp of last aggregation
            - symbols_in_buffer: int - number of symbols with data
            - signals_in_buffer: int - number of signals buffered
            - error_rate: float - cache push error rate (0-1)
        """
        now = time.time()
        age_seconds = now - self.last_aggregation_time if self.last_aggregation_time > 0 else 0

        # Calculate error rate
        total_pushes = self.cache_push_count + self.cache_push_errors
        error_rate = self.cache_push_errors / total_pushes if total_pushes > 0 else 0.0

        # Health criteria:
        # - Must be initialized
        # - Must have recent aggregation (within 5 minutes)
        # - Error rate should be < 20%
        is_healthy = (
            self._initialized and
            (age_seconds < 300 or self.last_aggregation_time == 0) and  # Allow 0 at startup
            error_rate < 0.2
        )

        # Determine status string
        if not self._initialized:
            status = "not_initialized"
        elif age_seconds > 300 and self.last_aggregation_time > 0:
            status = "stale"
        elif error_rate >= 0.2:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "initialized": self._initialized,
            "healthy": is_healthy,
            "status": status,
            "cache_push_count": self.cache_push_count,
            "cache_push_errors": self.cache_push_errors,
            "error_rate": round(error_rate, 4),
            "last_aggregation": self.last_aggregation_time,
            "aggregation_age_seconds": round(age_seconds, 1),
            "symbols_in_buffer": len(self.market_data_buffer),
            "signals_in_buffer": len(self.signal_buffer),
            "analysis_results_buffered": len(self.analysis_results_buffer),
            "market_wide_tickers": len(self.market_wide_tickers),
            "timestamp": now
        }

    async def add_analysis_result(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """
        Add analysis result and trigger cache updates.

        This is called by the monitoring system after each symbol analysis.
        """
        try:
            # DEBUG: Log first few analysis results to understand structure
            if self.aggregation_count < 3:
                logger.info(f"DEBUG: Analysis result keys for {symbol}: {list(analysis_result.keys())}")
                if 'confluence_score' in analysis_result:
                    logger.info(f"DEBUG: Confluence score for {symbol}: {analysis_result['confluence_score']}")

            # Add to buffer with timestamp
            timestamped_result = {
                **analysis_result,
                'symbol': symbol,
                'timestamp': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat()
            }

            self.analysis_results_buffer.append(timestamped_result)

            # Update market data buffer - extract from market_data structure
            market_data = None
            price = None

            if 'market_data' in analysis_result:
                raw_market_data = analysis_result['market_data']

                # Extract price from ticker (primary source)
                ticker = raw_market_data.get('ticker', {})
                if ticker:
                    price = ticker.get('last') or ticker.get('close') or ticker.get('lastPrice')

                # If no ticker, try ohlcv
                if not price:
                    ohlcv = raw_market_data.get('ohlcv')
                    if ohlcv is not None and isinstance(ohlcv, list) and len(ohlcv) > 0:
                        # OHLCV format: [timestamp, open, high, low, close, volume]
                        price = ohlcv[-1][4] if len(ohlcv[-1]) > 4 else None

                # Build market data dict if we have price
                if price:
                    market_data = {
                        'price': float(price),
                        'price_change_24h': ticker.get('change', 0),
                        'price_change_percent_24h': ticker.get('percentage', 0),
                        'volume_24h': ticker.get('baseVolume', 0) or ticker.get('volume', 0),
                        'high_24h': ticker.get('high', 0),
                        'low_24h': ticker.get('low', 0)
                    }
                elif self.aggregation_count < 3:
                    logger.warning(f"DEBUG: market_data found but no price extracted from ticker/ohlcv for {symbol}")
                    logger.warning(f"DEBUG: ticker keys: {list(ticker.keys()) if ticker else 'No ticker'}")

            elif 'price' in analysis_result:  # Fallback: use direct price data
                market_data = {
                    'price': analysis_result.get('price'),
                    'price_change_24h': analysis_result.get('price_change_24h', 0),
                    'price_change_percent_24h': analysis_result.get('price_change_percent_24h', 0),
                    'volume_24h': analysis_result.get('volume_24h', 0)
                }
            else:
                # DEBUG: Log why market data wasn't extracted
                if self.aggregation_count < 3:
                    logger.warning(f"DEBUG: No market_data or price found for {symbol}. Keys: {list(analysis_result.keys())[:10]}")

            if market_data:
                self.market_data_buffer[symbol] = {
                    **market_data,
                    'last_updated': time.time()
                }
                logger.debug(f"✅ Market data buffered for {symbol}: price={market_data.get('price')}")

            # Track price changes for market movers
            await self._track_price_changes(symbol, analysis_result)

            # Add ALL signals to buffer (dashboard should show all monitored symbols)
            confluence_score = analysis_result.get('confluence_score', 0)
            await self._add_signal_to_buffer(symbol, analysis_result)

            # Log high-quality signals separately
            if confluence_score >= 60:
                logger.info(f"✨ High-quality signal for {symbol} with score {confluence_score:.1f}")
            else:
                logger.debug(f"Added signal for {symbol} with score {confluence_score:.1f}")

            # Update aggregated cache keys
            await self._update_cache_keys()

            self.aggregation_count += 1

        except Exception as e:
            logger.error(f"Error adding analysis result for {symbol}: {e}")

    async def _add_signal_to_buffer(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Add trading signal to buffer."""
        try:
            signal_data = {
                'symbol': symbol,
                'signal_type': analysis_result.get('signal_type', 'NEUTRAL'),
                'confluence_score': analysis_result.get('confluence_score', 0),
                'reliability': analysis_result.get('reliability', 0),
                'components': analysis_result.get('components', {}),
                'trade_parameters': analysis_result.get('trade_parameters', {}),
                'timestamp': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat(),
                'signal_id': analysis_result.get('signal_id', ''),
                'transaction_id': analysis_result.get('transaction_id', '')
            }

            self.signal_buffer.append(signal_data)
            logger.info(f"Added signal to buffer: {symbol} {signal_data['signal_type']} (score: {signal_data['confluence_score']:.1f})")

        except Exception as e:
            logger.error(f"Error adding signal to buffer for {symbol}: {e}")

    async def _track_price_changes(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Track price changes for market movers calculation."""
        try:
            # DEBUG: Log function entry
            if len(self.price_changes) < 5:  # Only log first few calls
                logger.info(f"[DEBUG] _track_price_changes called for {symbol}")

            # Try to get market_data, fallback to direct keys
            market_data = analysis_result.get('market_data', analysis_result)

            # DEBUG: Check what keys are available
            if len(self.price_changes) < 5:
                logger.info(f"[DEBUG] {symbol}: market_data type={type(market_data)}")
                if isinstance(market_data, dict):
                    logger.info(f"[DEBUG] {symbol}: market_data keys={list(market_data.keys())[:10]}")
                    if 'ticker' in market_data:
                        logger.info(f"[DEBUG] {symbol}: ticker keys={list(market_data['ticker'].keys())[:10]}")

            price = market_data.get('price') or analysis_result.get('price')

            # CRITICAL FIX: Extract price from ticker if not directly available
            if not price and isinstance(market_data, dict) and 'ticker' in market_data:
                ticker = market_data['ticker']
                price = ticker.get('last') or ticker.get('close') or ticker.get('lastPrice')
                if len(self.price_changes) < 5:
                    logger.info(f"[DEBUG] {symbol}: Extracted price from ticker: {price}")

            if price:
                if len(self.price_changes) < 5:
                    logger.info(f"[DEBUG] {symbol}: Found price: {price}")
                current_price = float(price)
                price_change_24h = market_data.get('price_change_24h', 0) or analysis_result.get('price_change_24h', 0)
                volume_24h = market_data.get('volume_24h', 0) or analysis_result.get('volume_24h', 0)
                price_change_percent = market_data.get('price_change_percent_24h', 0) or analysis_result.get('price_change_percent_24h', 0)

                # CRITICAL FIX: Calculate price change from OHLCV if not provided
                if price_change_percent == 0:
                    if len(self.price_changes) < 5:
                        logger.info(f"[DEBUG] {symbol}: price_change_percent is 0, trying OHLCV calculation")

                    # Try to calculate from OHLCV data (24h ago vs now)
                    if 'market_data' in analysis_result:
                        ohlcv = analysis_result['market_data'].get('ohlcv')
                        if len(self.price_changes) < 5:
                            logger.info(f"[DEBUG] {symbol}: ohlcv type={type(ohlcv)}, is dict={isinstance(ohlcv, dict)}")

                        if ohlcv is not None and isinstance(ohlcv, dict):
                            base_ohlcv = ohlcv.get('base', [])
                            if len(self.price_changes) < 5:
                                logger.info(f"[DEBUG] {symbol}: base_ohlcv length={len(base_ohlcv) if base_ohlcv is not None else 0}")

                            if base_ohlcv is not None and len(base_ohlcv) > 24:  # Need at least 24 candles for 24h change
                                # Handle both DataFrame and list formats
                                try:
                                    import pandas as pd
                                    if isinstance(base_ohlcv, pd.DataFrame):
                                        price_24h_ago = base_ohlcv.iloc[-24, 4]  # Close price (index 4) 24 candles ago
                                    else:
                                        price_24h_ago = base_ohlcv[-24][4]  # List format

                                    if price_24h_ago > 0:
                                        price_change_percent = ((current_price - price_24h_ago) / price_24h_ago) * 100
                                        logger.info(f"✅ Calculated 24h change for {symbol}: {price_change_percent:.2f}%")
                                except (IndexError, KeyError, ValueError) as idx_err:
                                    logger.debug(f"{symbol}: Could not calculate 24h change from OHLCV: {idx_err}")
                else:
                    if len(self.price_changes) < 5:
                        logger.info(f"[DEBUG] {symbol}: Already has price_change_percent={price_change_percent}")

                # Store price change data
                price_data = {
                    'price': current_price,
                    'price_change_24h': float(price_change_24h),
                    'price_change_percent': float(price_change_percent),
                    'volume_24h': float(volume_24h),
                    'timestamp': time.time()
                }

                # Keep last 10 data points for each symbol
                if len(self.price_changes[symbol]) >= 10:
                    self.price_changes[symbol].pop(0)

                self.price_changes[symbol].append(price_data)

                if len(self.price_changes) < 5:
                    logger.info(f"[DEBUG] {symbol}: Stored price change data. Buffer now has {len(self.price_changes)} symbols")

        except Exception as e:
            logger.error(f"Error tracking price changes for {symbol}: {e}")

    async def _fetch_market_wide_tickers(self) -> bool:
        """
        Fetch all perpetual futures tickers from exchange for market-wide metrics.

        This provides TRUE market sentiment based on hundreds of perpetual contracts,
        not just the 15 symbols we're actively analyzing.

        Returns:
            bool: True if tickers were successfully fetched and updated
        """
        try:
            # Rate limit: only fetch every 60 seconds
            current_time = time.time()
            if current_time - self.last_ticker_fetch < self.ticker_fetch_interval:
                return False

            if not self.exchange:
                logger.warning("No exchange available for fetching market-wide tickers")
                return False

            # DEBUG: Log exchange info
            exchange_id = getattr(self.exchange, 'exchange_id', getattr(self.exchange, 'id', 'unknown'))
            logger.info(f"Fetching market-wide perpetual tickers from {exchange_id} for true market sentiment...")

            # Check if exchange has fetch_tickers method
            if not hasattr(self.exchange, 'fetch_tickers'):
                logger.error(f"Exchange {exchange_id} does not have fetch_tickers method")
                return False

            # Fetch all linear/perpetual tickers (Bybit specific)
            # For other exchanges, adjust parameters as needed
            # Bybit uses 'category' parameter: linear = perpetual futures
            tickers = await self.exchange.fetch_tickers(category='linear')

            if not tickers:
                logger.warning("No tickers returned from exchange")
                return False

            # Filter for valid tickers with price change data
            # Note: tickers is a list of dicts, not a dict
            valid_tickers = {}
            for ticker in tickers:
                # Only include tickers with valid price change data
                symbol = ticker.get('symbol')
                if symbol and ticker.get('priceChangePercent') is not None and ticker.get('lastPrice') is not None:
                    valid_tickers[symbol] = ticker

            self.market_wide_tickers = valid_tickers
            self.last_ticker_fetch = current_time

            logger.info(f"✅ Fetched {len(valid_tickers)} perpetual tickers for market-wide metrics")
            return True

        except Exception as e:
            logger.error(f"Error fetching market-wide tickers: {e}", exc_info=True)
            return False

    def _calculate_market_wide_metrics(self) -> Dict[str, Any]:
        """
        Calculate market-wide metrics from fetched tickers.

        Returns:
            dict: Market metrics including gainers, losers, volatility, avg_change
        """
        try:
            if not self.market_wide_tickers:
                logger.debug("No market-wide tickers available for metrics calculation")
                return {
                    'gainers': 0,
                    'losers': 0,
                    'volatility': 0.0,
                    'avg_change_percent': 0.0,
                    'total_symbols': 0
                }

            price_changes = []
            gainers = 0
            losers = 0
            neutral = 0

            for symbol, ticker in self.market_wide_tickers.items():
                pct_change = ticker.get('priceChangePercent', 0)

                if pct_change > 0:
                    gainers += 1
                elif pct_change < 0:
                    losers += 1
                else:
                    neutral += 1

                # Collect all price changes for volatility calculation
                if pct_change != 0:
                    price_changes.append(pct_change)

            # Calculate volatility (standard deviation of price changes)
            volatility = 0.0
            if len(price_changes) > 1:
                volatility = abs(statistics.stdev(price_changes))

            # Calculate average price change
            avg_change = 0.0
            if price_changes:
                avg_change = statistics.mean(price_changes)

            total = len(self.market_wide_tickers)

            logger.info(
                f"📊 Market-wide metrics: {gainers} gainers, {losers} losers "
                f"({total} total) | Volatility: {volatility:.2f}% | Avg Change: {avg_change:.2f}%"
            )

            return {
                'gainers': gainers,
                'losers': losers,
                'neutral': neutral,
                'volatility': round(volatility, 2),
                'avg_change_percent': round(avg_change, 2),
                'total_symbols': total
            }

        except Exception as e:
            logger.error(f"Error calculating market-wide metrics: {e}", exc_info=True)
            return {
                'gainers': 0,
                'losers': 0,
                'volatility': 0.0,
                'avg_change_percent': 0.0,
                'total_symbols': 0
            }

    def _calculate_btc_realized_volatility(self) -> Dict[str, float]:
        """
        Calculate BTC realized volatility (annualized).

        This is TRUE crypto volatility - the standard deviation of BTC's
        daily returns over the past 30 days, annualized.

        Returns:
            dict: {
                'btc_volatility': Annualized volatility % (e.g., 52.0),
                'btc_daily_volatility': Daily volatility % (e.g., 2.7),
                'btc_current_price': Current BTC price,
                'days_of_data': Number of days in calculation
            }
        """
        try:
            # CRITICAL FIX: Always get current BTC price from live tickers
            current_btc_price = 0.0
            if 'BTCUSDT' in self.market_wide_tickers:
                current_btc_price = float(self.market_wide_tickers['BTCUSDT'].get('lastPrice', 0))

            # Need at least 2 days of data to calculate volatility
            if len(self.btc_price_history) < 2:
                return {
                    'btc_volatility': 0.0,
                    'btc_daily_volatility': 0.0,
                    'btc_current_price': current_btc_price,  # Use live price instead of 0
                    'days_of_data': 0
                }

            # Calculate daily log returns
            daily_returns = []
            prices = list(self.btc_price_history)

            for i in range(1, len(prices)):
                prev_price = prices[i-1]['price']
                curr_price = prices[i]['price']

                if prev_price > 0 and curr_price > 0:
                    # Log return: ln(P_t / P_{t-1})
                    log_return = math.log(curr_price / prev_price)
                    daily_returns.append(log_return)

            if len(daily_returns) < 2:
                return {
                    'btc_volatility': 0.0,
                    'btc_daily_volatility': 0.0,
                    'btc_current_price': current_btc_price,  # Use live price instead of historical
                    'days_of_data': len(prices)
                }

            # Calculate standard deviation of daily returns
            daily_volatility = statistics.stdev(daily_returns)

            # Annualize: σ_annual = σ_daily × sqrt(365)
            annualized_volatility = daily_volatility * math.sqrt(365)

            # Convert to percentage
            daily_volatility_pct = daily_volatility * 100
            annualized_volatility_pct = annualized_volatility * 100

            logger.info(
                f"📊 BTC Realized Volatility: {annualized_volatility_pct:.1f}% annualized "
                f"({daily_volatility_pct:.2f}% daily, {len(daily_returns)} days) | "
                f"Current BTC Price: ${current_btc_price:,.2f}"
            )

            return {
                'btc_volatility': round(annualized_volatility_pct, 2),
                'btc_daily_volatility': round(daily_volatility_pct, 2),
                'btc_current_price': current_btc_price,  # Always use live price
                'days_of_data': len(daily_returns)
            }

        except Exception as e:
            logger.error(f"Error calculating BTC realized volatility: {e}", exc_info=True)
            # Try to at least return current price even if volatility calculation fails
            try:
                current_btc_price = 0.0
                if 'BTCUSDT' in self.market_wide_tickers:
                    current_btc_price = float(self.market_wide_tickers['BTCUSDT'].get('lastPrice', 0))
            except:
                current_btc_price = 0.0

            return {
                'btc_volatility': 0.0,
                'btc_daily_volatility': 0.0,
                'btc_current_price': current_btc_price,
                'days_of_data': 0
            }

    async def _track_btc_price(self) -> None:
        """
        Track BTC price once per day for realized volatility calculation.

        Stores daily price snapshots in a rolling 30-day buffer.
        """
        try:
            current_time = time.time()
            time_since_last_snapshot = current_time - self.last_btc_snapshot

            # Only take snapshot once per day (86400 seconds)
            if time_since_last_snapshot < 86400 and self.last_btc_snapshot > 0:
                return

            # Get BTC price from market-wide tickers
            if 'BTCUSDT' in self.market_wide_tickers:
                btc_ticker = self.market_wide_tickers['BTCUSDT']
                btc_price = btc_ticker.get('lastPrice', 0)

                if btc_price > 0:
                    price_snapshot = {
                        'timestamp': current_time,
                        'price': btc_price,
                        'date': datetime.now(timezone.utc).date().isoformat()
                    }

                    self.btc_price_history.append(price_snapshot)
                    self.last_btc_snapshot = current_time

                    logger.info(
                        f"📸 BTC price snapshot: ${btc_price:,.2f} "
                        f"({len(self.btc_price_history)} days of history)"
                    )
            else:
                logger.warning("BTCUSDT not found in market-wide tickers for volatility calculation")

        except Exception as e:
            logger.error(f"Error tracking BTC price: {e}", exc_info=True)

    async def _update_cache_keys(self) -> None:
        """Update all critical cache keys with aggregated data."""
        try:
            # Fetch market-wide tickers for true market sentiment (rate-limited to once per minute)
            await self._fetch_market_wide_tickers()

            # Track BTC price for realized volatility calculation (once per day)
            await self._track_btc_price()

            # Update market:overview
            await self._update_market_overview()

            # Update analysis:signals
            await self._update_analysis_signals()

            # Update market:movers
            await self._update_market_movers()

            # Update NEW CoinGecko data (trending, derivatives, categories, exchanges)
            await self._update_coingecko_extended_data()

            self.last_aggregation_time = time.time()

        except Exception as e:
            logger.error(f"Error updating cache keys: {e}")

    async def _update_market_overview(self) -> None:
        """Generate and cache market overview data using unified schema."""
        try:
            # Calculate market statistics from buffered data
            total_symbols = len(self.market_data_buffer)
            active_signals = len([s for s in self.signal_buffer if time.time() - s['timestamp'] < 3600])  # Last hour

            # Calculate average confluence score with BTC fallback for startup
            if self.analysis_results_buffer and len(self.analysis_results_buffer) >= 5:
                # Use real confluence scores once we have enough data
                recent_scores = [r.get('confluence_score', 0) for r in list(self.analysis_results_buffer)[-20:]]
                avg_confluence = statistics.mean(recent_scores) if recent_scores else 0
                max_confluence = max(recent_scores) if recent_scores else 0
            else:
                # STARTUP FALLBACK: Use BTC price action for initial regime indication
                # This provides meaningful data immediately instead of "Initializing"
                if 'BTCUSDT' in self.market_wide_tickers:
                    btc_ticker = self.market_wide_tickers['BTCUSDT']
                    btc_change = float(btc_ticker.get('priceChangePercent', 0))
                    # Map BTC momentum to pseudo-confluence score
                    # -5% BTC = 25 confluence, 0% = 50, +5% = 75
                    avg_confluence = max(0, min(100, 50 + (btc_change * 5)))
                    max_confluence = avg_confluence
                    logger.debug(f"📊 Using BTC-based initial regime: {avg_confluence:.1f} (BTC: {btc_change:+.2f}%)")
                else:
                    avg_confluence = 50  # Neutral default
                    max_confluence = 50

            # Calculate market trend
            bullish_signals = len([s for s in self.signal_buffer if s['signal_type'] == 'LONG'])
            bearish_signals = len([s for s in self.signal_buffer if s['signal_type'] == 'SHORT'])

            # Calculate total volume from buffered market data
            total_volume = sum(
                data.get('volume_24h', 0)
                for data in self.market_data_buffer.values()
            )

            # CRITICAL FIX: Use market-wide metrics from exchange tickers (TRUE market sentiment)
            # This replaces the limited local buffer approach with exchange-wide data
            market_metrics = self._calculate_market_wide_metrics()

            # RENAME: This is market dispersion, not volatility
            market_dispersion = market_metrics['volatility']  # Cross-sectional dispersion of returns
            avg_change_percent = market_metrics['avg_change_percent']
            gainers_count = market_metrics['gainers']
            losers_count = market_metrics['losers']

            # Calculate TRUE BTC realized volatility (annualized)
            btc_vol_data = self._calculate_btc_realized_volatility()
            btc_volatility = btc_vol_data['btc_volatility']  # Annualized %
            btc_daily_vol = btc_vol_data['btc_daily_volatility']
            btc_price = btc_vol_data['btc_current_price']
            btc_vol_days = btc_vol_data['days_of_data']

            # Log market-wide vs monitored comparison
            if market_metrics['total_symbols'] > 0:
                logger.debug(
                    f"Market-wide: {gainers_count}/{losers_count} ({market_metrics['total_symbols']} symbols) | "
                    f"Monitored: {total_symbols} symbols | "
                    f"Dispersion: {market_dispersion}% | Avg Change: {avg_change_percent}%"
                )

            # Track dispersion history for average calculation
            self.volatility_history.append(market_dispersion)

            # Calculate average market dispersion from history
            if len(self.volatility_history) > 0:
                avg_dispersion = statistics.mean(self.volatility_history)
            else:
                avg_dispersion = 8.0  # Fallback default (more realistic than 20%)

            # =================================================================
            # Fetch ALL external market data from CoinGecko & Alternative.me
            # =================================================================
            # CoinGecko Global Data (BTC/ETH dominance, market cap, volume)
            coingecko_data = await fetch_coingecko_global_data()
            btc_dominance = coingecko_data.get('btc_dominance', 57.0)
            eth_dominance = coingecko_data.get('eth_dominance', 11.5)
            stablecoin_dominance = coingecko_data.get('stablecoin_dominance', 8.0)
            total_market_cap = coingecko_data.get('total_market_cap', 0)
            market_cap_change_24h = coingecko_data.get('market_cap_change_24h', 0)
            coingecko_volume = coingecko_data.get('total_volume_24h', 0)
            active_cryptos = coingecko_data.get('active_cryptocurrencies', 0)

            # Fear & Greed Index (Alternative.me)
            fear_greed_data = await fetch_fear_greed_index()
            fear_greed_value = fear_greed_data.get('value', 50)
            fear_greed_label = fear_greed_data.get('classification', 'Neutral')

            # DeFi Data (CoinGecko DeFi endpoint)
            defi_data = await fetch_defi_data()
            defi_market_cap = defi_data.get('defi_market_cap', 0)
            defi_dominance = defi_data.get('defi_dominance', 0)
            defi_volume = defi_data.get('defi_volume_24h', 0)
            top_defi = defi_data.get('top_defi_protocol', 'Unknown')
            top_defi_dom = defi_data.get('top_defi_dominance', 0)

            # Calculate derived metrics
            altcoin_dominance = round(100 - btc_dominance, 2)
            # Altcoin season: BTC dom < 50% or falling trend
            altcoin_season = 'Active' if btc_dominance < 50 else 'Emerging' if btc_dominance < 55 else 'Dormant'

            # Volume/Market Cap ratio (liquidity indicator)
            volume_mcap_ratio = round((coingecko_volume / total_market_cap * 100), 2) if total_market_cap > 0 else 0

            # =================================================================
            # ENHANCED REGIME CLASSIFICATION (v1.2)
            # Uses multiple data sources for rich, descriptive labels
            # =================================================================
            btc_dom_prev = coingecko_data.get('btc_dominance_prev', btc_dominance)
            enhanced_regime = self._classify_enhanced_regime(
                avg_confluence=avg_confluence,
                gainers=gainers_count,
                losers=losers_count,
                fear_greed=fear_greed_value,
                market_dispersion=market_dispersion,
                btc_dominance=btc_dominance,
                btc_dom_prev=btc_dom_prev
            )
            market_regime = enhanced_regime['regime']  # e.g., "Neutral: Bottoming Formation"

            logger.debug(
                f"Market Dispersion: current={market_dispersion:.2f}%, avg={avg_dispersion:.2f}% "
                f"(based on {len(self.volatility_history)} samples)"
            )

            logger.info(
                f"📊 BTC Volatility: {btc_volatility:.1f}% annualized "
                f"({btc_daily_vol:.2f}% daily, {btc_vol_days} days) | "
                f"Market Dispersion: {market_dispersion:.2f}% | "
                f"Fear & Greed: {fear_greed_value} ({fear_greed_label})"
            )

            # Build monitoring format data (old schema format)
            monitoring_data = {
                'total_symbols_monitored': total_symbols,
                'active_signals_1h': active_signals,
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals,
                'avg_confluence_score': round(avg_confluence, 2),
                'max_confluence_score': round(max_confluence, 2),
                'market_state': market_regime,  # Enhanced label e.g., "🚀 Broad Rally"
                'market_regime_details': enhanced_regime,  # Full regime data with components
                'signal_quality': 'High' if avg_confluence > 65 else 'Medium' if avg_confluence > 55 else 'Low',
                'total_volume': total_volume,

                # RENAMED: Market Dispersion (cross-sectional volatility)
                'market_dispersion': round(market_dispersion, 2),  # Current dispersion of returns
                'avg_market_dispersion': round(avg_dispersion, 2),  # Rolling 24-hour average

                # TRUE Crypto Volatility (BTC realized volatility)
                'btc_volatility': round(btc_volatility, 2),  # Annualized BTC volatility %
                'btc_daily_volatility': round(btc_daily_vol, 2),  # Daily BTC volatility %
                'btc_price': round(btc_price, 2) if btc_price else 0,
                'btc_vol_days': btc_vol_days,  # Days of data used in calculation

                # Keep old field names for backward compatibility (will be deprecated)
                'volatility': round(market_dispersion, 2),  # DEPRECATED: Use market_dispersion
                'avg_volatility': round(avg_dispersion, 2),  # DEPRECATED: Use avg_market_dispersion

                'avg_change_percent': round(avg_change_percent, 2),
                'gainers': gainers_count,
                'losers': losers_count,

                # =================================================================
                # CoinGecko Global Data - Dominance Metrics
                # =================================================================
                'btc_dom': btc_dominance,  # Real BTC dominance from CoinGecko
                'eth_dominance': eth_dominance,  # ETH market cap dominance
                'stablecoin_dominance': stablecoin_dominance,  # USDT + USDC combined
                'altcoin_dominance': altcoin_dominance,  # 100 - BTC dominance
                'altcoin_season': altcoin_season,  # Active/Emerging/Dormant

                # =================================================================
                # CoinGecko Global Data - Market Cap Metrics
                # =================================================================
                # IMPORTANT: These metrics represent GLOBAL cryptocurrency market data from CoinGecko,
                # NOT exchange-specific data from Bybit/Binance/etc.
                #
                # Data Source: CoinGecko Free API (https://api.coingecko.com/api/v3/global)
                # Update Frequency: Every 3-5 seconds via cache_data_aggregator
                # Cache TTL: 60 seconds (L1=memory, L2=memcached, L3=Redis)
                #
                # Why CoinGecko for Market Overview?
                # - Aggregates data across ALL major exchanges (Binance, Coinbase, Bybit, etc.)
                # - Provides true market-wide metrics (not just one exchange)
                # - Includes BTC/ETH dominance, total market cap, global trading volume
                # - Free tier sufficient for our needs (50 calls/min)
                #
                # Note: crypto-perps-tracker service (port 8050) is used separately for
                # derivatives analysis (funding rates, basis) but NOT for market overview data.
                # =================================================================
                'total_market_cap': total_market_cap,  # Total crypto market cap (USD)
                'market_cap_change_24h': market_cap_change_24h,  # 24h market cap change %
                'coingecko_volume_24h': coingecko_volume,  # CoinGecko global 24h volume (all exchanges)
                'total_volume_24h': coingecko_volume,  # GLOBAL crypto market volume from CoinGecko (NOT Bybit-specific)
                'volume_mcap_ratio': volume_mcap_ratio,  # Volume/Market Cap ratio (liquidity indicator)
                'active_cryptocurrencies': active_cryptos,  # Number of active cryptos tracked by CoinGecko

                # =================================================================
                # Fear & Greed Index (Alternative.me)
                # =================================================================
                'fear_greed_value': fear_greed_value,  # 0-100 scale
                'fear_greed_label': fear_greed_label,  # Extreme Fear/Fear/Neutral/Greed/Extreme Greed

                # =================================================================
                # DeFi Data (CoinGecko DeFi endpoint)
                # =================================================================
                'defi_market_cap': defi_market_cap,  # DeFi sector market cap
                'defi_dominance': defi_dominance,  # DeFi % of total market
                'defi_volume_24h': defi_volume,  # DeFi 24h trading volume
                'top_defi_protocol': top_defi,  # Leading DeFi protocol name
                'top_defi_dominance': top_defi_dom,  # Leading protocol's % of DeFi

                'last_updated': time.time(),
                'datetime': datetime.now(timezone.utc).isoformat(),
                'data_points': len(self.analysis_results_buffer),
                'buffer_size': len(self.signal_buffer)
            }

            # Use unified cache writer (automatically transforms to unified schema)
            # TTL increased to 300s (5 min) to survive gaps between analysis cycles
            # Previous 60s TTL caused cache expiration between update batches
            success = await self.cache_writer.write_market_overview(
                monitoring_data,
                ttl=300
            )

            if success:
                logger.debug(
                    f"✅ Updated market:overview with UNIFIED SCHEMA - "
                    f"{total_symbols} symbols, {active_signals} signals"
                )
            else:
                logger.error("Failed to write market overview with unified schema")

        except Exception as e:
            logger.error(f"Error updating market overview cache: {e}", exc_info=True)

    async def _update_analysis_signals(self) -> None:
        """Generate and cache analysis signals data using unified schema."""
        try:
            # Get recent signals (last 10 minutes - matches current monitoring window)
            # CRITICAL FIX: Reduced from 7200s (2 hours) to 600s (10 minutes)
            # This prevents mixing old high-scoring signals with current top symbols
            # 10 minutes = 2x cache TTL (300s) and 2x symbol selection interval (300s)
            cutoff_time = time.time() - 600
            recent_signals = [s for s in self.signal_buffer if s['timestamp'] > cutoff_time]

            # Sort by confluence score (highest first)
            recent_signals.sort(key=lambda x: x['confluence_score'], reverse=True)

            # CRITICAL FIX: Deduplicate by symbol, keeping only highest score per symbol
            # This ensures all 15 monitored symbols appear in cache (not just top 20 signals)
            seen_symbols = {}
            for signal in recent_signals:
                symbol = signal['symbol']
                if symbol not in seen_symbols:
                    seen_symbols[symbol] = signal

            # Get unique symbols sorted by score
            unique_signals = list(seen_symbols.values())
            unique_signals.sort(key=lambda x: x['confluence_score'], reverse=True)

            # Log signal filtering for debugging
            logger.debug(
                f"Signal buffer: {len(self.signal_buffer)} total signals, "
                f"{len(recent_signals)} from last 10 minutes, "
                f"{len(unique_signals)} unique symbols, "
                f"writing top {min(len(unique_signals), 20)}"
            )

            # Prepare signals for unified schema (convert to expected format)
            formatted_signals = []
            for signal in unique_signals[:20]:  # Top 20 unique symbols
                # Get market data for the symbol
                market_data = self.market_data_buffer.get(signal['symbol'], {})

                formatted_signal = {
                    'symbol': signal['symbol'],
                    'confluence_score': signal['confluence_score'],
                    'signal_type': signal['signal_type'],
                    'reliability': signal.get('reliability', 75.0),
                    'sentiment': signal['signal_type'],  # BUY/SELL maps to sentiment
                    'components': signal.get('components', {}),
                    'price': market_data.get('price', 0.0),
                    'change_24h': market_data.get('price_change_percent_24h', 0.0),
                    'volume_24h': market_data.get('volume_24h', 0.0),
                    'high_24h': market_data.get('high_24h', 0.0),
                    'low_24h': market_data.get('low_24h', 0.0),
                    'timestamp': signal['timestamp'],
                    'datetime': signal['datetime']
                }
                formatted_signals.append(formatted_signal)

            # Use unified cache writer
            # TTL increased from 120s to 300s to match symbol selection cache
            # This ensures all 15 symbols remain visible until next refresh
            success = await self.cache_writer.write_signals(
                formatted_signals,
                ttl=300  # 5 minutes - matches symbol selection cache TTL
            )

            if success:
                unique_symbols = len(set(s['symbol'] for s in formatted_signals))
                logger.debug(
                    f"✅ Updated analysis:signals with UNIFIED SCHEMA - "
                    f"{len(formatted_signals)} signals ({unique_symbols} unique symbols)"
                )
            else:
                logger.error("Failed to write signals with unified schema")

        except Exception as e:
            logger.error(f"Error updating analysis signals cache: {e}", exc_info=True)

    async def _update_market_movers(self) -> None:
        """Generate and cache market movers data using EXCHANGE-WIDE ticker data."""
        try:
            movers_data = []

            # CRITICAL: Use market-wide tickers (585 symbols) instead of just monitored symbols (15)
            if self.market_wide_tickers:
                # Process all exchange-wide tickers
                for symbol, ticker in self.market_wide_tickers.items():
                    try:
                        price_change_pct = ticker.get('priceChangePercent', 0)

                        mover_entry = {
                            'symbol': symbol,
                            'display_symbol': symbol,  # For frontend display
                            'price': ticker.get('lastPrice', 0),
                            'change': price_change_pct,  # Frontend expects 'change'
                            'change_24h': price_change_pct,
                            'price_change_percent': price_change_pct,
                            'percentage': price_change_pct,
                            'volume': ticker.get('quoteVolume', 0),
                            'volume_24h': ticker.get('quoteVolume', 0),
                            'timestamp': time.time()
                        }

                        movers_data.append(mover_entry)
                    except Exception as e:
                        logger.debug(f"Error processing ticker for {symbol}: {e}")
                        continue

                logger.info(f"📊 Processing {len(movers_data)} tickers for top movers")
            else:
                # Fallback to monitored symbols if exchange-wide data not available
                logger.warning("⚠️ No market-wide tickers available, using monitored symbols")
                for symbol, price_history in self.price_changes.items():
                    if not price_history:
                        continue

                    latest_data = price_history[-1]

                    mover_entry = {
                        'symbol': symbol,
                        'display_symbol': symbol,
                        'price': latest_data['price'],
                        'change': latest_data['price_change_percent'],
                        'price_change_24h': latest_data['price_change_24h'],
                        'price_change_percent': latest_data['price_change_percent'],
                        'volume_24h': latest_data['volume_24h'],
                        'timestamp': latest_data['timestamp']
                    }

                    movers_data.append(mover_entry)

            # Sort by absolute price change percentage
            movers_data.sort(key=lambda x: abs(x.get('price_change_percent', 0)), reverse=True)

            # Get top gainers and losers
            gainers = [m for m in movers_data if m['price_change_percent'] > 0][:10]
            losers = [m for m in movers_data if m['price_change_percent'] < 0][:10]

            # Volume leaders
            volume_leaders = sorted(movers_data, key=lambda x: x.get('volume_24h', 0), reverse=True)[:10]

            # Use unified cache writer
            success = await self.cache_writer.write_market_movers(
                gainers=gainers,
                losers=losers,
                volume_leaders=volume_leaders,
                ttl=90
            )

            if success:
                logger.info(
                    f"✅ Updated market:movers with EXCHANGE-WIDE DATA - "
                    f"{len(gainers)} gainers, {len(losers)} losers from {len(movers_data)} total symbols"
                )
                if gainers:
                    top_gainer = gainers[0]
                    logger.info(f"   Top Gainer: {top_gainer['symbol']} +{top_gainer['price_change_percent']:.2f}%")
                if losers:
                    top_loser = losers[0]
                    logger.info(f"   Top Loser: {top_loser['symbol']} {top_loser['price_change_percent']:.2f}%")
            else:
                logger.error("Failed to write market movers with unified schema")

        except Exception as e:
            logger.error(f"Error updating market movers cache: {e}", exc_info=True)

    async def _update_coingecko_extended_data(self) -> None:
        """
        Fetch and cache extended CoinGecko data (trending, derivatives, categories, exchanges).

        These are NEW integrations added 2025-12-16.
        See: docs/08-features/COINGECKO_INTEGRATION_ROADMAP.md

        IMPORTANT: Uses global lock to prevent concurrent CoinGecko calls which cause 429 rate limits.
        Fetches are staggered with 2-second delays to respect CoinGecko's free tier limits.
        """
        logger.debug("🔄 _update_coingecko_extended_data called - acquiring lock...")

        # Use global lock to prevent concurrent fetches from multiple symbol analyzers
        # This is critical because CoinGecko free tier limits to ~30 req/min
        async with _coingecko_fetch_lock:
            logger.debug("🔒 Lock acquired - fetching CoinGecko extended data")
            try:
                # Fetch SEQUENTIALLY with delays to avoid rate limiting (CoinGecko 429 errors)
                # The module-level caches handle deduplication, but concurrent calls at startup
                # were all passing TTL check simultaneously and hitting rate limits.

                trending = await fetch_trending_coins()
                await asyncio.sleep(2)  # 2 second delay between calls

                derivatives = await fetch_derivatives_data()
                await asyncio.sleep(2)

                categories = await fetch_category_performance()
                await asyncio.sleep(2)

                exchanges = await fetch_exchange_distribution()

                # Process and cache each data type
                cache_results = {}

                # 1. Trending coins
                if isinstance(trending, dict) and trending.get('coins'):
                    trending_data = {
                        'coins': trending.get('coins', []),
                        'nfts': trending.get('nfts', []),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    success = await self._push_to_cache('coingecko:trending', trending_data, expiry=900)
                    cache_results['trending'] = success
                else:
                    cache_results['trending'] = False

                # 2. Derivatives (funding rates, OI)
                if isinstance(derivatives, dict) and derivatives.get('contracts'):
                    derivatives_data = {
                        'contracts': derivatives.get('contracts', [])[:30],  # Top 30 for API response
                        'by_symbol': derivatives.get('by_symbol', {}),
                        'funding_spreads': derivatives.get('funding_spreads', {}),
                        'total_open_interest': derivatives.get('total_open_interest', 0),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    success = await self._push_to_cache('coingecko:derivatives', derivatives_data, expiry=300)
                    cache_results['derivatives'] = success
                else:
                    cache_results['derivatives'] = False

                # 3. Category performance
                if isinstance(categories, dict) and categories.get('categories'):
                    categories_data = {
                        'categories': categories.get('categories', []),
                        'top_performers': categories.get('top_performers', []),
                        'bottom_performers': categories.get('bottom_performers', []),
                        'rotation_signal': categories.get('rotation_signal', ''),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    success = await self._push_to_cache('coingecko:categories', categories_data, expiry=600)
                    cache_results['categories'] = success
                else:
                    cache_results['categories'] = False

                # 4. Exchange distribution
                if isinstance(exchanges, dict) and exchanges.get('exchanges'):
                    exchanges_data = {
                        'exchanges': exchanges.get('exchanges', []),
                        'total_volume_btc': exchanges.get('total_volume_btc', 0),
                        'concentration': exchanges.get('concentration', {}),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    success = await self._push_to_cache('coingecko:exchanges', exchanges_data, expiry=600)
                    cache_results['exchanges'] = success
                else:
                    cache_results['exchanges'] = False

                # Log summary
                successful = sum(1 for v in cache_results.values() if v)
                total = len(cache_results)
                logger.info(
                    f"✅ CoinGecko Extended: {successful}/{total} updated | "
                    f"trending={cache_results.get('trending')}, "
                    f"derivatives={cache_results.get('derivatives')}, "
                    f"categories={cache_results.get('categories')}, "
                    f"exchanges={cache_results.get('exchanges')}"
                )

            except Exception as e:
                logger.error(f"Error updating CoinGecko extended data: {e}", exc_info=True)

    async def _push_to_cache(self, key: str, data: Dict[str, Any], expiry: int = 300) -> bool:
        """Push data directly to cache."""
        try:
            # Convert to JSON string
            json_data = json.dumps(data, default=str)

            # Use the multi-tier cache system (DirectCacheAdapter uses 'ttl' parameter)
            await self.cache_adapter.set(key, json_data, ttl=expiry)

            self.cache_push_count += 1
            logger.debug(f"Successfully pushed {key} to cache ({len(json_data)} bytes)")
            return True

        except Exception as e:
            self.cache_push_errors += 1
            logger.error(f"Failed to push {key} to cache: {e}")
            return False

    async def force_cache_update(self) -> Dict[str, bool]:
        """Force update of all cache keys (for testing/debugging)."""
        results = {}

        try:
            # Force market overview update
            await self._update_market_overview()
            results['market:overview'] = True
        except Exception as e:
            logger.error(f"Failed to force update market:overview: {e}")
            results['market:overview'] = False

        try:
            # Force signals update
            await self._update_analysis_signals()
            results['analysis:signals'] = True
        except Exception as e:
            logger.error(f"Failed to force update analysis:signals: {e}")
            results['analysis:signals'] = False

        try:
            # Force movers update
            await self._update_market_movers()
            results['market:movers'] = True
        except Exception as e:
            logger.error(f"Failed to force update market:movers: {e}")
            results['market:movers'] = False

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            'aggregation_count': self.aggregation_count,
            'cache_push_count': self.cache_push_count,
            'cache_push_errors': self.cache_push_errors,
            'last_aggregation_time': self.last_aggregation_time,
            'signal_buffer_size': len(self.signal_buffer),
            'market_data_symbols': len(self.market_data_buffer),
            'analysis_results_count': len(self.analysis_results_buffer),
            'price_tracking_symbols': len(self.price_changes)
        }

    def _classify_aggregate_regime(
        self,
        avg_confluence: float,
        market_dispersion: float
    ) -> MarketRegime:
        """
        Classify aggregate market regime using unified regime labels.

        This method applies the Unified Regime System (v1.1) classification
        at the aggregate level (across all monitored symbols).

        Classification Logic:
        - Confluence is the PRIMARY directional signal (0=bearish, 100=bullish)
        - Market dispersion serves as volatility proxy (high dispersion = high volatility)
        - Without per-symbol ADX, we use confidence-adjusted thresholds

        Thresholds (adapted for aggregate data):
        - Strong Bullish: confluence >= 70 (strong bullish indicator consensus)
        - Bullish: confluence >= 60 (majority bullish)
        - Sideways: confluence 40-60 (mixed/uncertain signals)
        - Bearish: confluence <= 40 (majority bearish)
        - Strong Bearish: confluence <= 30 (strong bearish consensus)
        - High Volatility: market_dispersion > 15% (safety override)

        Args:
            avg_confluence: Average confluence score across all symbols (0-100)
            market_dispersion: Cross-sectional volatility of returns (%)

        Returns:
            MarketRegime enum value with display_name property
        """
        # Safety override: High volatility
        if market_dispersion > 15.0:
            logger.debug(
                f"Aggregate regime: HIGH_VOLATILITY (dispersion={market_dispersion:.1f}%)"
            )
            return MarketRegime.HIGH_VOLATILITY

        # Strong Bullish: High confluence consensus
        if avg_confluence >= 70:
            regime = MarketRegime.STRONG_BULLISH
        # Bullish: Good confluence
        elif avg_confluence >= 60:
            regime = MarketRegime.BULLISH
        # Strong Bearish: Very low confluence (bearish consensus)
        elif avg_confluence <= 30:
            regime = MarketRegime.STRONG_BEARISH
        # Bearish: Low confluence
        elif avg_confluence <= 40:
            regime = MarketRegime.BEARISH
        # Sideways: Neutral zone (40-60)
        else:
            regime = MarketRegime.SIDEWAYS

        logger.debug(
            f"Aggregate regime: {regime.display_name} "
            f"(confluence={avg_confluence:.1f}, dispersion={market_dispersion:.1f}%)"
        )

        return regime

    def _classify_enhanced_regime(
        self,
        avg_confluence: float,
        gainers: int,
        losers: int,
        fear_greed: int,
        market_dispersion: float,
        btc_dominance: float,
        btc_dom_prev: float = None
    ) -> Dict[str, Any]:
        """
        Enhanced regime classification using multiple data sources.

        Produces rich, descriptive labels that incorporate:
        - Confluence score (indicator consensus direction)
        - Market breadth (gainers vs losers ratio)
        - Fear & Greed sentiment
        - Market dispersion (volatility)
        - BTC dominance trend (rotation indicator)

        Returns:
            Dict with 'regime', 'label', 'emoji', 'description', and component scores
        """
        total = gainers + losers if (gainers + losers) > 0 else 1
        breadth_ratio = gainers / total  # 0-1, higher = more bullish breadth

        # Determine direction from confluence
        if avg_confluence >= 70:
            direction = 'strong_bullish'
        elif avg_confluence >= 60:
            direction = 'bullish'
        elif avg_confluence <= 30:
            direction = 'strong_bearish'
        elif avg_confluence <= 40:
            direction = 'bearish'
        else:
            direction = 'neutral'

        # Determine breadth condition
        if breadth_ratio >= 0.6:
            breadth = 'broad'  # Many gainers
        elif breadth_ratio <= 0.3:
            breadth = 'narrow'  # Many losers
        else:
            breadth = 'mixed'

        # Determine sentiment from Fear & Greed
        if fear_greed >= 75:
            sentiment = 'extreme_greed'
        elif fear_greed >= 55:
            sentiment = 'greed'
        elif fear_greed <= 25:
            sentiment = 'extreme_fear'
        elif fear_greed <= 45:
            sentiment = 'fear'
        else:
            sentiment = 'neutral'

        # Determine volatility condition
        if market_dispersion > 15:
            volatility = 'high'
        elif market_dispersion > 8:
            volatility = 'elevated'
        else:
            volatility = 'normal'

        # BTC dominance trend (rotation indicator)
        btc_trend = 'stable'
        if btc_dom_prev and btc_dom_prev > 0:
            dom_change = btc_dominance - btc_dom_prev
            if dom_change > 1.0:
                btc_trend = 'rising'  # Flight to BTC
            elif dom_change < -1.0:
                btc_trend = 'falling'  # Alt rotation

        # =================================================================
        # ENHANCED LABEL CLASSIFICATION MATRIX
        # =================================================================

        # High volatility override
        if volatility == 'high':
            if direction in ('strong_bearish', 'bearish'):
                label = "Volatile Selloff"
                emoji = "🌪️📉"
                desc = "High volatility with bearish pressure - risk management critical"
            elif direction in ('strong_bullish', 'bullish'):
                label = "Volatile Rally"
                emoji = "🌪️📈"
                desc = "High volatility with bullish momentum - use caution on entries"
            else:
                label = "Choppy Waters"
                emoji = "🌊"
                desc = "High volatility, no clear direction - wait for clarity"

        # Strong bullish scenarios
        elif direction == 'strong_bullish':
            if breadth == 'broad' and sentiment in ('greed', 'extreme_greed'):
                label = "Euphoric Rally"
                emoji = "🚀🎉"
                desc = "Strong broad-based rally with extreme optimism - watch for exhaustion"
            elif breadth == 'broad':
                label = "Broad Rally"
                emoji = "🚀"
                desc = "Strong uptrend with wide market participation"
            elif breadth == 'narrow':
                label = "Selective Strength"
                emoji = "📈⚡"
                desc = "Strong indicators but concentrated gains - rotation possible"
            else:
                label = "Bullish Momentum"
                emoji = "📈"
                desc = "Strong bullish consensus across indicators"

        # Bullish scenarios
        elif direction == 'bullish':
            if breadth == 'broad' and btc_trend == 'falling':
                label = "Alt Season"
                emoji = "🌈💰"
                desc = "Bullish with altcoin rotation - BTC dominance declining"
            elif breadth == 'broad':
                label = "Risk-On"
                emoji = "✅📈"
                desc = "Healthy bullish conditions with broad participation"
            elif sentiment in ('fear', 'extreme_fear'):
                label = "Accumulation Zone"
                emoji = "🐋📥"
                desc = "Bullish indicators despite fearful sentiment - smart money buying"
            else:
                label = "Mild Uptrend"
                emoji = "📈"
                desc = "Moderately bullish conditions"

        # Strong bearish scenarios
        elif direction == 'strong_bearish':
            if breadth == 'narrow' and sentiment == 'extreme_fear':
                label = "Capitulation"
                emoji = "💀📉"
                desc = "Extreme bearish with panic selling - potential bottom forming"
            elif breadth == 'narrow':
                label = "Broad Selloff"
                emoji = "🔴📉"
                desc = "Strong selling pressure across the market"
            elif btc_trend == 'rising':
                label = "Flight to BTC"
                emoji = "₿🛡️"
                desc = "Bearish alts with BTC dominance rising - defensive rotation"
            else:
                label = "Bearish Momentum"
                emoji = "📉"
                desc = "Strong bearish consensus across indicators"

        # Bearish scenarios
        elif direction == 'bearish':
            if sentiment in ('greed', 'extreme_greed'):
                label = "Distribution Zone"
                emoji = "🐋📤"
                desc = "Bearish indicators despite greedy sentiment - smart money selling"
            elif breadth == 'narrow':
                label = "Risk-Off"
                emoji = "⚠️📉"
                desc = "Bearish conditions - reduce exposure"
            else:
                label = "Mild Downtrend"
                emoji = "📉"
                desc = "Moderately bearish conditions"

        # Neutral/sideways scenarios
        else:
            if volatility == 'elevated':
                label = "Choppy Range"
                emoji = "↔️🌊"
                desc = "Ranging with elevated volatility - range trading conditions"
            elif breadth == 'broad' and sentiment in ('greed', 'extreme_greed'):
                label = "Topping Formation"
                emoji = "⚠️🔝"
                desc = "Neutral indicators but greedy sentiment - potential reversal"
            elif breadth == 'narrow' and sentiment in ('fear', 'extreme_fear'):
                label = "Bottoming Formation"
                emoji = "👀🔻"
                desc = "Neutral indicators but fearful sentiment - potential reversal"
            elif btc_trend == 'falling':
                label = "Alt Accumulation"
                emoji = "🔄💎"
                desc = "Sideways with altcoin rotation beginning"
            else:
                label = "Consolidation"
                emoji = "⏸️"
                desc = "Range-bound market - wait for breakout"

        # Map direction to display-friendly category name
        category_names = {
            'strong_bullish': 'Strong Bullish',
            'bullish': 'Bullish',
            'neutral': 'Neutral',
            'bearish': 'Bearish',
            'strong_bearish': 'Strong Bearish'
        }
        category = category_names.get(direction, 'Unknown')

        # Build result (no emojis - clean labels only)
        result = {
            'regime': f"{category}: {label}",  # Full display format
            'label': label,  # Clean label only
            'category': category,  # Category name
            'description': desc,
            'base_regime': direction,
            'components': {
                'confluence': round(avg_confluence, 1),
                'breadth_ratio': round(breadth_ratio * 100, 1),
                'fear_greed': fear_greed,
                'dispersion': round(market_dispersion, 1),
                'btc_dominance': round(btc_dominance, 1) if btc_dominance else None,
                'btc_trend': btc_trend
            },
            'conditions': {
                'direction': direction,
                'breadth': breadth,
                'sentiment': sentiment,
                'volatility': volatility
            }
        }

        logger.info(
            f"Enhanced regime: {category}: {label} | "
            f"confluence={avg_confluence:.1f}, breadth={breadth_ratio:.1%}, "
            f"F&G={fear_greed}, dispersion={market_dispersion:.1f}%"
        )

        return result